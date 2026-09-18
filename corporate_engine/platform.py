"""OpenAI Platform gateway. Transport, identity, poll, recover. No intelligence."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import os
import threading
import time
import urllib.error
import urllib.request

from corporate_engine.classify import split_turn
from corporate_engine.store import dump_json, load_json

API = "https://api.openai.com/v1"
BETA = "agents=v1"
POLL_SECONDS = 3.0
WAIT_SECONDS = int(os.getenv("OPENAI_AGENTS_WAIT_SECONDS") or "5400")
GET_TIMEOUT = 60
POST_TIMEOUT = int(os.getenv("OPENAI_AGENTS_POST_TIMEOUT") or "330")
SESSION_TOOLS = [{"type": "web_search", "mode": "live"}]
SESSION_MULTI_AGENT = {"enabled": True, "max_concurrent_subagents": 4}
TERMINAL_OK = {"completed", "complete", "succeeded"}
TERMINAL_FAIL = {"failed", "cancelled", "canceled"}
RETRYABLE_HTTP = {408, 409, 425, 429, 500, 502, 503, 504}
EXECUTION_FILE = "PLATFORM_EXECUTION.json"
SUBMIT_SUBMITTING = "SUBMITTING"
SUBMIT_ACKNOWLEDGED = "ACKNOWLEDGED"
SUBMIT_UNKNOWN = "UNKNOWN"
SUBMIT_NOT_ACCEPTED = "CONFIRMED_NOT_ACCEPTED"
RECOVERY_MESSAGE = (
    "Conexión interrumpida después del envío. Verificando el estado de la ejecución en Platform."
)


class RecoveryPending(Exception):
    """Submit ACK lost or remote turn not terminal yet. Do not resend."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def windows_user_env(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if value:
        return value
    if os.name != "nt":
        return ""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            raw, _ = winreg.QueryValueEx(key, name)
            return str(raw or "").strip()
    except OSError:
        return ""


def application_key() -> str:
    return windows_user_env("OPENAI_API_KEY")


def prompt_hash(text: str) -> str:
    return sha256((text or "").encode("utf-8")).hexdigest()


def load_execution(case_dir: Path | None) -> dict:
    if not case_dir:
        return {}
    return load_json(Path(case_dir) / EXECUTION_FILE, {}) or {}


def save_execution(case_dir: Path | None, payload: dict) -> dict:
    if not case_dir:
        return payload
    row = dict(payload)
    row["updated_at"] = _now()
    dump_json(Path(case_dir) / EXECUTION_FILE, row)
    return row


def official_turn_error(turn: dict | None) -> dict:
    if not isinstance(turn, dict):
        return {}
    error = turn.get("error")
    if isinstance(error, dict):
        return {"code": str(error.get("code") or ""), "message": str(error.get("message") or "")}
    if error:
        return {"code": "", "message": str(error)}
    return {}


def format_turn_failure(actor: str, status: str, turn: dict | None) -> str:
    error = official_turn_error(turn)
    code = error.get("code") or ""
    message = error.get("message") or ""
    if code or message:
        return f"{actor} fallo en OpenAI Platform ({status}): {code or 'error'} - {message}"
    return f"{actor} falló el giro en OpenAI Platform: {status}"


def classify_platform_error(error: BaseException) -> str:
    text = str(error).casefold()
    if "credit_balance_exhausted" in text or "no credits remaining" in text:
        return "CREDIT_BALANCE_EXHAUSTED"
    if isinstance(error, TimeoutError) or "timed out" in text or "timeout" in text:
        return "timeout"
    if "429" in text or "rate limit" in text:
        return "rate_limit"
    if "dns" in text or "name or service not known" in text or "getaddrinfo" in text:
        return "dns"
    if "connection reset" in text or "connection aborted" in text or "broken pipe" in text:
        return "connection_reset"
    if any(token in text for token in ("http 500", "http 502", "http 503", "http 504")):
        return "http_5xx"
    if "http 4" in text:
        return "http_4xx"
    return "platform_error"


def is_retryable(error: BaseException) -> bool:
    return classify_platform_error(error) in {
        "timeout", "rate_limit", "dns", "connection_reset", "http_5xx", "platform_error",
    }


class UrlLibHttp:
    def request(self, url: str, key: str, method: str = "GET", payload=None, timeout: float = 60):
        data = None
        headers = {"Authorization": "Bearer " + key, "Accept": "application/json", "OpenAI-Beta": BETA}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw = response.read().decode("utf-8", "replace")
                return response.status, json.loads(raw) if raw.strip() else {}
        except urllib.error.HTTPError as error:
            raw = error.read().decode("utf-8", "replace")
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                body = {"raw": raw[:800]}
            raise RuntimeError(f"OpenAI HTTP {error.code} en {url}: {(body.get('error') or body)}") from error

    def get_bytes(self, url: str, key: str, timeout: float = 60) -> bytes:
        headers = {"Authorization": "Bearer " + key, "Accept": "*/*", "OpenAI-Beta": BETA}
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            raw = error.read().decode("utf-8", "replace")
            raise RuntimeError(f"OpenAI HTTP {error.code} en {url}: {raw[:800]}") from error

    def stream_sse(self, url: str, key: str, timeout: float = 330):
        headers = {
            "Authorization": "Bearer " + key,
            "Accept": "text/event-stream",
            "OpenAI-Beta": BETA,
        }
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            while True:
                raw = response.readline()
                if not raw:
                    break
                yield raw.decode("utf-8", "replace")


def _created_stamp(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), timezone.utc).isoformat()
    text = str(value).strip()
    if text.isdigit():
        return datetime.fromtimestamp(int(text), timezone.utc).isoformat()
    return text


def _ids(payload: dict) -> set[str]:
    return {str(item.get("id")) for item in (payload.get("data") or []) if isinstance(item, dict) and item.get("id")}


def _message_events(text: str) -> dict:
    return {
        "events": [{
            "type": "agent.session.input.message",
            "input": [{"role": "user", "content": [{"type": "input_text", "text": text}]}],
        }]
    }


def items_for_turn(all_items: list, known_item_ids: set[str], turn_id: str | None) -> list:
    fresh = [item for item in all_items if isinstance(item, dict) and str(item.get("id") or "") not in known_item_ids]
    if turn_id:
        matched = [item for item in fresh if str(item.get("turn_id") or item.get("turn") or "") == str(turn_id)]
        if matched:
            return matched
    return fresh


class PlatformGateway:
    """Minimum gateway: session, send once, poll, recover, normalize."""

    def __init__(self, *, http=None, sleep=time.sleep, wait_seconds: int | None = None, key: str | None = None):
        self.http = http or UrlLibHttp()
        self.sleep = sleep
        self.wait_seconds = int(wait_seconds if wait_seconds is not None else WAIT_SECONDS)
        self._key = key

    def key(self) -> str:
        return self._key if self._key is not None else application_key()

    def _get(self, url: str, timeout: float = GET_TIMEOUT):
        last = None
        delay = 1.0
        for attempt in range(4):
            try:
                return self.http.request(url, self.key(), "GET", None, timeout)
            except Exception as error:
                last = error
                if attempt == 3 or (isinstance(error, RuntimeError) and "HTTP 4" in str(error) and "429" not in str(error)):
                    raise
                if not is_retryable(error) and not isinstance(error, (TimeoutError, urllib.error.URLError, OSError)):
                    raise
                self.sleep(delay)
                delay *= 2
        raise last

    def _post_once(self, url: str, payload: dict, timeout: float = POST_TIMEOUT):
        return self.http.request(url, self.key(), "POST", payload, timeout)

    def retrieve_session(self, session: str) -> dict:
        _, payload = self._get(f"{API}/agents/sessions/{session}")
        return payload if isinstance(payload, dict) else {}

    def session_usable(self, session: str) -> bool:
        try:
            row = self.retrieve_session(session)
        except Exception:
            return False
        status = str(row.get("status") or "").lower()
        if status in {"failed", "expired", "cancelled", "canceled"}:
            return False
        actions = row.get("required_actions") or []
        for action in actions:
            if isinstance(action, dict) and action.get("type") == "environment_connection":
                return False
        return bool(row.get("id"))

    def create_session(self, platform_agent_id: str, environment: dict, *, metadata: dict | None = None) -> str:
        env = dict(environment or {})
        if env.get("type") == "self_hosted":
            env = {"type": "openai_hosted"}
        if not env.get("type"):
            env = {"type": "openai_hosted"}
        payload = {
            "agent_id": platform_agent_id,
            "agent": {"tools": SESSION_TOOLS, "multi_agent": SESSION_MULTI_AGENT},
            "environment": env,
        }
        if metadata:
            payload["metadata"] = metadata
        _, created = self._post_once(f"{API}/agents/sessions", payload, timeout=60)
        session = str(created.get("id") or "")
        if not session:
            raise RuntimeError("OpenAI Platform no devolvió session id.")
        return session

    def subscribe_events(self, session: str) -> None:
        stream = getattr(self.http, "stream_sse", None)
        if not callable(stream):
            return

        def _read():
            try:
                for _line in stream(
                    f"{API}/agents/sessions/{session}/events?stream=true",
                    self.key(),
                    max(POST_TIMEOUT, 120),
                ):
                    pass
            except Exception:
                return

        threading.Thread(target=_read, daemon=True).start()
        self.sleep(0.4)

    def list_items(self, session: str) -> list:
        collected = []
        after = None
        for _ in range(20):
            url = f"{API}/agents/sessions/{session}/items?limit=100&order=asc"
            if after:
                url += "&after=" + after
            _, payload = self._get(url)
            rows = [item for item in (payload.get("data") or []) if isinstance(item, dict)]
            if not rows:
                break
            collected.extend(rows)
            after = str(rows[-1].get("id") or "")
            if payload.get("has_more") is False or len(rows) < 100 or not after:
                break
        return collected

    def list_artifacts(self, session: str) -> list[dict]:
        try:
            _, payload = self._get(f"{API}/agents/sessions/{session}/artifacts")
        except Exception:
            return []
        return [row for row in (payload.get("data") or []) if isinstance(row, dict)]

    def download_artifact(self, session: str, artifact_id: str) -> str:
        getter = getattr(self.http, "get_bytes", None)
        url = f"{API}/agents/sessions/{session}/artifacts/{artifact_id}/content"
        if callable(getter):
            raw = getter(url, self.key(), GET_TIMEOUT)
        else:
            _, payload = self._get(url)
            raw = payload if isinstance(payload, (bytes, bytearray)) else str(payload or "").encode("utf-8")
        text = raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else str(raw)
        return text

    def snapshot(self, session: str) -> tuple[set[str], set[str]]:
        base = f"{API}/agents/sessions/{session}"
        _, prior_items = self._get(base + "/items?limit=100&order=desc")
        _, prior_turns = self._get(base + "/turns?limit=100&order=desc")
        return _ids(prior_items), _ids(prior_turns)

    def current_turns(self, session: str) -> list[dict]:
        _, turns = self._get(f"{API}/agents/sessions/{session}/turns?limit=100&order=desc")
        return [row for row in (turns.get("data") or []) if isinstance(row, dict)]

    def reuse_or_create_session(self, configured: str, platform_agent_id: str, environment: dict, case_dir: Path | None) -> str:
        stored = load_execution(case_dir)
        session = str(stored.get("session_id") or "").strip()
        case_name = Path(case_dir).name if case_dir else ""
        bound = False
        if session:
            try:
                row = self.retrieve_session(session)
                meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
                bound = str(meta.get("lnh_case_id") or "") == case_name and self.session_usable(session)
            except Exception:
                bound = False
        if bound:
            return session
        session = self.create_session(
            platform_agent_id, environment,
            metadata={
                "lnh_case_id": case_name,
                "client_request_id": str(stored.get("client_request_id") or ""),
            },
        )
        if case_dir:
            dump_json(Path(case_dir) / "SESSION_BIND.json", {
                "stored_session_id": stored.get("session_id"),
                "bound": bound,
                "created_session_id": session,
                "case_name": case_name,
            })
        save_execution(case_dir, {**stored, "session_id": session, "platform_agent_id": platform_agent_id})
        return session

    def _normalize(self, session: str, turn: dict, known_items: set[str], *, actor: str, platform_agent_id: str | None) -> dict:
        turn_id = str(turn.get("id") or "")
        selected = [
            item for item in self.list_items(session)
            if isinstance(item, dict) and str(item.get("id") or "") not in known_items
        ]
        split = split_turn(selected)
        assistant = str(split.get("assistant_output_raw") or "").strip()
        for artifact in self.list_artifacts(session):
            path = str(artifact.get("path") or "")
            if artifact.get("turn_id") and str(artifact.get("turn_id")) != turn_id:
                continue
            if not path.lower().endswith((".md", ".txt")):
                continue
            try:
                body = self.download_artifact(session, str(artifact.get("id") or "")).strip()
            except Exception:
                continue
            if len(body) > len(assistant):
                assistant = body
        agent_obj = turn.get("agent") if isinstance(turn.get("agent"), dict) else {}
        usage = turn.get("usage") if isinstance(turn.get("usage"), dict) else {}
        usage = usage or split.get("usage") or {}
        return {
            "actor": actor,
            "operation": "execute",
            "model": agent_obj.get("model"),
            "provider": "openai-platform",
            "prompt_eval_count": usage.get("input_tokens") or usage.get("prompt_tokens"),
            "eval_count": usage.get("output_tokens") or usage.get("completion_tokens"),
            "cost_usd": usage.get("cost_usd"),
            "tools_used": split["tools_used"],
            "tool_events": split["events"],
            "tool_sources": split["tool_sources"],
            "session_id": session,
            "turn_id": turn_id,
            "execution_id": turn_id,
            "turn_status": str(turn.get("status") or ""),
            "platform_agent_id": platform_agent_id or agent_obj.get("id"),
            "started_at": turn.get("created_at") or _now(),
            "finished_at": _now(),
            "assistant_output_raw": assistant or split["assistant_output_raw"],
            "items": selected,
        }

    def _fresh_turn(self, rows: list[dict], known_turns: set[str], submitted_at: str | None):
        fresh = [row for row in rows if str(row.get("id") or "") not in known_turns]
        if not fresh:
            return None
        if submitted_at:
            after = [
                row for row in fresh
                if _created_stamp(row.get("created_at")) >= _created_stamp(submitted_at)
            ]
            if after:
                fresh = after
        fresh.sort(key=lambda row: (str(row.get("created_at") or ""), str(row.get("id") or "")))
        return fresh[0]

    def recover_turn(self, session: str, known_turns: set[str], known_items: set[str], *, actor: str,
                     platform_agent_id: str | None, submitted_at: str | None = None):
        rows = self.current_turns(session)
        current = self._fresh_turn(rows, known_turns, submitted_at)
        if not current:
            return None
        status = str(current.get("status") or "").lower()
        if status in TERMINAL_FAIL:
            return {"failed": True, "turn": current, "status": status, "error": official_turn_error(current)}
        if status in TERMINAL_OK:
            return {"failed": False, "turn": current, "status": status,
                    "result": self._normalize(session, current, known_items, actor=actor, platform_agent_id=platform_agent_id)}
        return {"failed": False, "turn": current, "status": status, "result": None}

    def wait_for_result(self, session: str, known_turns: set[str], known_items: set[str], *, actor: str,
                        platform_agent_id: str | None, case_dir: Path | None):
        deadline = time.time() + self.wait_seconds
        last_status = ""
        turn_id = ""
        submitted_at = (load_execution(case_dir) or {}).get("submitted_at")
        while time.time() < deadline:
            recovered = self.recover_turn(
                session, known_turns, known_items, actor=actor, platform_agent_id=platform_agent_id,
                submitted_at=submitted_at,
            )
            if recovered:
                current = recovered["turn"]
                turn_id = str(current.get("id") or "")
                last_status = recovered["status"]
                save_execution(case_dir, {
                    **load_execution(case_dir),
                    "session_id": session,
                    "turn_id": turn_id,
                    "turn_status": last_status,
                    "execution_id": current.get("execution_id") or turn_id,
                    "submit_status": SUBMIT_ACKNOWLEDGED,
                    "recovery_required": False,
                    "allow_resend": last_status in TERMINAL_FAIL,
                    "platform_error": recovered.get("error") or official_turn_error(current),
                })
                if recovered.get("failed"):
                    raise RuntimeError(format_turn_failure(actor, last_status, current))
                if recovered.get("result"):
                    return recovered["result"]
            try:
                from corporate_engine.progress import emit as progress
                progress(
                    case_dir, "platform_poll",
                    f"Seguimiento Platform turn={turn_id or 'pendiente'} status={last_status or 'sin turn'}.",
                    actor=actor, phase="platform",
                )
            except Exception:
                pass
            self.sleep(POLL_SECONDS)
        raise RecoveryPending(
            f"{RECOVERY_MESSAGE} Estado remoto: {last_status!r}. turn_id={turn_id!r}."
        )

    def send_instruction(self, session: str, prompt: str, *, case_dir: Path | None, client_request_id: str) -> dict:
        state = load_execution(case_dir)
        digest = prompt_hash(prompt)
        same = state.get("client_request_id") == client_request_id
        prior_status = str(state.get("turn_status") or "").lower()
        if same and prior_status in TERMINAL_FAIL:
            pass
        elif same and state.get("submit_status") == SUBMIT_NOT_ACCEPTED and state.get("allow_resend"):
            pass
        elif same and (state.get("post_attempted") or state.get("turn_id") or state.get("submit_status") in {
            SUBMIT_ACKNOWLEDGED, SUBMIT_UNKNOWN, SUBMIT_SUBMITTING,
        }):
            return state
        known_items, known_turns = self.snapshot(session)
        submitted_at = _now()
        state = save_execution(case_dir, {
            **state,
            "client_request_id": client_request_id,
            "session_id": session,
            "prompt_sha256": digest,
            "known_item_ids": sorted(known_items),
            "known_turn_ids": sorted(known_turns),
            "submitted_at": submitted_at,
            "submit_status": SUBMIT_SUBMITTING,
            "post_attempted": False,
            "post_acknowledged": False,
            "allow_resend": False,
            "recovery_required": False,
            "turn_id": None,
        })
        state = save_execution(case_dir, {**state, "post_attempted": True})
        self.subscribe_events(session)
        try:
            status, payload = self._post_once(
                f"{API}/agents/sessions/{session}/events",
                _message_events(prompt),
                timeout=POST_TIMEOUT,
            )
        except Exception as error:
            kind = classify_platform_error(error)
            text = str(error)
            if kind == "timeout":
                return save_execution(case_dir, {
                    **load_execution(case_dir),
                    "post_attempted": True,
                    "post_acknowledged": False,
                    "submit_status": SUBMIT_UNKNOWN,
                    "recovery_required": True,
                    "allow_resend": False,
                    "last_transport_error": text,
                    "last_transport_kind": kind,
                })
            http_code = None
            if "OpenAI HTTP " in text:
                token = text.split("OpenAI HTTP ", 1)[-1].split(" ", 1)[0]
                if token.isdigit():
                    http_code = int(token)
            not_accepted = http_code in {400, 401, 403, 404, 422}
            saved = save_execution(case_dir, {
                **load_execution(case_dir),
                "post_attempted": True,
                "post_acknowledged": False,
                "submit_status": SUBMIT_NOT_ACCEPTED if not_accepted else SUBMIT_UNKNOWN,
                "recovery_required": not not_accepted,
                "allow_resend": bool(not_accepted),
                "last_transport_error": text,
                "last_transport_kind": kind,
            })
            if not_accepted:
                return saved
            if kind in {"http_5xx", "rate_limit", "connection_reset", "dns"}:
                return saved
            raise
        returned_ids = {}
        if isinstance(payload, dict):
            for key in ("id", "turn_id", "execution_id"):
                if payload.get(key):
                    returned_ids[key] = payload.get(key)
        return save_execution(case_dir, {
            **load_execution(case_dir),
            "post_attempted": True,
            "post_acknowledged": True,
            "submit_status": SUBMIT_ACKNOWLEDGED,
            "recovery_required": False,
            "allow_resend": False,
            "http_status": status,
            "sent_at": _now(),
            **returned_ids,
        })

    def run_mission(self, *, session: str, prompt: str, case_dir: Path, actor: str,
                    platform_agent_id: str | None, client_request_id: str) -> dict:
        if not session or not self.key():
            raise RuntimeError(f"{actor} en OpenAI Platform no está disponible: falta sesión u OPENAI_API_KEY.")
        state = self.send_instruction(session, prompt, case_dir=case_dir, client_request_id=client_request_id)
        if state.get("submit_status") == SUBMIT_NOT_ACCEPTED:
            raise RuntimeError(state.get("last_transport_error") or "OpenAI Platform rechazó el envío.")
        known_items = set(state.get("known_item_ids") or [])
        known_turns = set(state.get("known_turn_ids") or [])
        result = self.wait_for_result(
            session, known_turns, known_items, actor=actor, platform_agent_id=platform_agent_id, case_dir=case_dir,
        )
        if not str(result.get("assistant_output_raw") or "").strip():
            raise RuntimeError(f"{actor} cerró el giro en OpenAI Platform sin texto de asistente.")
        save_execution(case_dir, {
            **load_execution(case_dir),
            "session_id": result["session_id"],
            "turn_id": result["turn_id"],
            "execution_id": result["execution_id"],
            "turn_status": result["turn_status"],
            "post_acknowledged": True,
            "submit_status": SUBMIT_ACKNOWLEDGED,
            "recovery_required": False,
            "allow_resend": False,
            "completed_at": result["finished_at"],
        })
        return result


def create_session(platform_agent_id: str, environment: dict, key: str | None = None) -> str:
    return PlatformGateway(key=key).create_session(platform_agent_id, environment)


def run_turn(session: str, prompt: str, *, actor: str, operation: str = "execute",
             case_dir: Path | None = None, wait_seconds: int | None = None,
             platform_agent_id: str | None = None, client_request_id: str | None = None) -> dict:
    from uuid import uuid4
    request_id = client_request_id or (load_execution(case_dir).get("client_request_id") if case_dir else None) or uuid4().hex
    gateway = PlatformGateway(wait_seconds=wait_seconds)
    return gateway.run_mission(
        session=session, prompt=prompt, case_dir=Path(case_dir) if case_dir else Path("."),
        actor=actor, platform_agent_id=platform_agent_id, client_request_id=request_id,
    )
