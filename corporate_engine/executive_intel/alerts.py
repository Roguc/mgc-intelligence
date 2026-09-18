"""Fase 2C-3 — Alertas ejecutivas determinísticas (sin IA / Platform).

Reglas documentadas de severidad
--------------------------------
ALTA:
  - HUMAN_GATE_PENDIENTE (piso requiere decisión)
  - TAREA_VENCIDA (encargo con vencimiento materializado)
  - EXPEDIENTE_VENCIDO (fecha_objetivo < ahora UTC)
  - DIRECTORIO_PENDIENTE_PRESIDENCIA (sesión en PENDIENTE_PRESIDENCIA)
  - CASE_PLATFORM_ERROR (status técnico de expediente de piso)

MEDIA:
  - EXPEDIENTE_PROXIMO (fecha_objetivo dentro de PROXIMITY_DAYS=7, ventana operativa documentada)
  - COMM_PENDIENTE_APROBACION (comunicación EMAIL/WHATSAPP en PENDIENTE_APROBACION)
  - INTEGRACION_INDISPONIBLE (proveedor ERROR / FAILED / NOT_CONFIGURED cuando se espera uso)
  - EXEC_INTEL_NO_DISPONIBLE (clima/economía/mercados en NO_DISPONIBLE)

BAJA:
  - EXEC_INTEL_DESACTUALIZADO (clima/economía/mercados en DESACTUALIZADO)

INFORMATIVA (nunca crítica sin umbral corporativo aprobado):
  - INDICADOR_CAMBIO (valor 2C-1 distinto al snapshot previo; sin umbral → solo señal)
  - NOTICIA_PALABRA_CLAVE (categoría 2C-2 + contención literal de keyword documentada)

Estados: ACTIVA | ATENDIDA | RESUELTA | DESCARTADA
platform_calls = 0
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

from corporate_engine import corporate_board as board
from corporate_engine import corporate_communications as communications
from corporate_engine import corporate_expediente as corp
from corporate_engine import corporate_workflow as workflow
from corporate_engine import providers as connectors
from corporate_engine.executive_intel import (
    STATUS_DESACTUALIZADO,
    STATUS_NO_DISPONIBLE,
)
from corporate_engine.executive_intel import chile_indicators as exec_chile
from corporate_engine.executive_intel import news as exec_news
from corporate_engine.executive_intel import weather as exec_weather
from corporate_engine.store import dump_json, load_json, now

# —— Constantes documentadas ——
PROXIMITY_DAYS = 7  # ventana operativa de proximidad a fecha_objetivo (no umbral de mercado)
ALERT_STATES = frozenset({"ACTIVA", "ATENDIDA", "RESUELTA", "DESCARTADA"})
SEVERITIES = frozenset({"ALTA", "MEDIA", "BAJA", "INFORMATIVA"})

NEWS_KEYWORDS = {
    "mineria": ("codelco", "cobre", "cochilco", "copper", "commodit"),
    "nacional": ("inversión", "inversion", "regulación", "regulacion", "banco central", "tpm", "ipc"),
}

PLATFORM_ERROR_STATUSES = frozenset({
    "PLATFORM_CONNECTION_ERROR",
    "PLATFORM_EXECUTION_ERROR",
    "RECOVERY_PENDING",
    "INCOMPLETE",
})

INTEGRATION_BAD = frozenset({
    "ERROR", "FAILED", "NOT_CONFIGURED", "DISCONNECTED", "EXPIRED",
})


def _alerts_dir(corporate_root: Path | None) -> Path:
    if corporate_root is not None:
        path = Path(corporate_root) / "_executive_intel" / "alerts"
    else:
        path = Path(__file__).resolve().parents[2] / "outputs" / "lnh_corporate" / "_executive_intel" / "alerts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _store_path(corporate_root: Path | None) -> Path:
    return _alerts_dir(corporate_root) / "alerts.json"


def _indicator_snap_path(corporate_root: Path | None) -> Path:
    return _alerts_dir(corporate_root) / "indicator_snapshot.json"


def _load_store(corporate_root: Path | None) -> dict:
    data = load_json(_store_path(corporate_root), default=None)
    if not isinstance(data, dict):
        return {"alerts": [], "updated_at": None, "platform_calls": 0}
    data.setdefault("alerts", [])
    data.setdefault("platform_calls", 0)
    return data


def _save_store(corporate_root: Path | None, store: dict) -> dict:
    store["updated_at"] = now()
    store["platform_calls"] = 0
    dump_json(_store_path(corporate_root), store)
    return store


def _parse_dt(value) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        # date-only
        try:
            dt = datetime.strptime(text[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None


def _alert_id(idempotency_key: str) -> str:
    digest = hashlib.sha1(idempotency_key.encode("utf-8")).hexdigest()[:12]
    return f"ALT-{digest}"


def _history_entry(estado: str, *, actor: str, note: str = "") -> dict:
    return {"at": now(), "estado": estado, "actor": actor, "note": note or ""}


def _make_alert(
    *,
    rule_id: str,
    idempotency_key: str,
    tipo: str,
    severidad: str,
    titulo: str,
    descripcion: str,
    origen: str,
    expediente_id: str | None = None,
    entidad: str | None = None,
    area: str | None = None,
    evidencia: dict | None = None,
    referencia: str | None = None,
    responsable: str = "Presidencia LNH",
    accion: dict | None = None,
) -> dict:
    aid = _alert_id(idempotency_key)
    ts = now()
    return {
        "alert_id": aid,
        "idempotency_key": idempotency_key,
        "rule_id": rule_id,
        "tipo": tipo,
        "severidad": severidad if severidad in SEVERITIES else "INFORMATIVA",
        "titulo": titulo,
        "descripcion": descripcion,
        "origen": origen,
        "expediente_id": expediente_id,
        "entidad": entidad,
        "area": area,
        "evidencia": evidencia or {},
        "referencia": referencia,
        "detected_at": ts,
        "updated_at": ts,
        "estado": "ACTIVA",
        "responsable": responsable,
        "accion": accion or {},
        "history": [_history_entry("ACTIVA", actor="SYSTEM", note="Detectada por regla determinística")],
        "platform_calls": 0,
    }


def _index_by_key(alerts: list[dict]) -> dict[str, dict]:
    out = {}
    for item in alerts:
        key = item.get("idempotency_key")
        if key:
            out[key] = item
    return out


def _upsert_active(store: dict, candidate: dict) -> None:
    """Keep one record per idempotency_key; reopen if previously closed and condition returns."""
    by_key = _index_by_key(store["alerts"])
    key = candidate["idempotency_key"]
    existing = by_key.get(key)
    if not existing:
        store["alerts"].append(candidate)
        return
    prev = existing.get("estado")
    existing["titulo"] = candidate["titulo"]
    existing["descripcion"] = candidate["descripcion"]
    existing["evidencia"] = candidate.get("evidencia") or existing.get("evidencia") or {}
    existing["referencia"] = candidate.get("referencia") or existing.get("referencia")
    existing["accion"] = candidate.get("accion") or existing.get("accion") or {}
    existing["severidad"] = candidate.get("severidad") or existing.get("severidad")
    existing["updated_at"] = now()
    existing["platform_calls"] = 0
    if prev == "DESCARTADA":
        # Operator discard is sticky; record stays in history without reopening.
        pass
    elif prev == "RESUELTA":
        existing["estado"] = "ACTIVA"
        existing["detected_at"] = candidate["detected_at"]
        existing.setdefault("history", []).append(
            _history_entry("ACTIVA", actor="SYSTEM", note="Condición reapareció; alerta reabierta")
        )
    elif prev == "ATENDIDA":
        # Keep ATENDIDA while condition persists unless operator changes it
        pass
    else:
        existing["estado"] = "ACTIVA"


def _resolve_missing(store: dict, active_keys: set[str], *, note: str) -> None:
    for item in store["alerts"]:
        if item.get("estado") != "ACTIVA":
            continue
        if item.get("idempotency_key") in active_keys:
            continue
        item["estado"] = "RESUELTA"
        item["updated_at"] = now()
        item.setdefault("history", []).append(
            _history_entry("RESUELTA", actor="SYSTEM", note=note)
        )


# —— Collectors ——

def _collect_human_gates(floor_cases: list[dict] | None) -> list[dict]:
    out = []
    for row in floor_cases or []:
        if not row.get("requires_decision"):
            continue
        case_id = row.get("case_id")
        floor_id = row.get("floor_id")
        if not case_id or not floor_id:
            continue
        key = f"HUMAN_GATE:{floor_id}:{case_id}"
        out.append(_make_alert(
            rule_id="R-HG-01",
            idempotency_key=key,
            tipo="HUMAN_GATE_PENDIENTE",
            severidad="ALTA",
            titulo="Human Gate pendiente",
            descripcion=f"El expediente de piso {floor_id}/{case_id} requiere decisión humana.",
            origen="INTERNAL",
            entidad=f"{floor_id}/{case_id}",
            area=floor_id,
            evidencia={"case_id": case_id, "floor_id": floor_id, "status": row.get("status")},
            referencia=f"{floor_id}/{case_id}",
            accion={"kind": "case", "label": "Abrir expediente", "floor_id": floor_id, "case_id": case_id},
        ))
    return out


def _collect_platform_errors(floor_cases: list[dict] | None) -> list[dict]:
    out = []
    for row in floor_cases or []:
        status = str(row.get("status") or "")
        if status not in PLATFORM_ERROR_STATUSES:
            continue
        case_id = row.get("case_id")
        floor_id = row.get("floor_id")
        if not case_id or not floor_id:
            continue
        key = f"CASE_PLATFORM:{floor_id}:{case_id}:{status}"
        out.append(_make_alert(
            rule_id="R-PLAT-01",
            idempotency_key=key,
            tipo="CASE_PLATFORM_ERROR",
            severidad="ALTA",
            titulo=f"Estado técnico {status}",
            descripcion=f"Expediente {floor_id}/{case_id} registra estado {status}.",
            origen="INTERNAL",
            entidad=f"{floor_id}/{case_id}",
            area=floor_id,
            evidencia={"case_id": case_id, "floor_id": floor_id, "status": status},
            accion={"kind": "case", "label": "Abrir expediente", "floor_id": floor_id, "case_id": case_id},
        ))
    return out


def _collect_overdues(corporate_root: Path) -> list[dict]:
    out = []
    for item in corp.list_expedientes(corporate_root):
        exp_id = item["expediente_id"]
        try:
            case = corp.directory(corporate_root, exp_id)
            overdue_rows = workflow.overdues_view(case)
        except Exception:
            continue
        for overdue in overdue_rows:
            task_id = overdue.get("task_id") or overdue.get("encargos_id") or overdue.get("id") or "task"
            key = f"TAREA_VENCIDA:{exp_id}:{task_id}"
            out.append(_make_alert(
                rule_id="R-TASK-01",
                idempotency_key=key,
                tipo="TAREA_VENCIDA",
                severidad="ALTA",
                titulo="Tarea vencida",
                descripcion=f"La tarea {task_id} del expediente {exp_id} figura vencida.",
                origen="INTERNAL",
                expediente_id=exp_id,
                entidad=str(task_id),
                area=item.get("ambito") or "LNH",
                evidencia=dict(overdue) if isinstance(overdue, dict) else {"raw": overdue},
                accion={"kind": "expediente", "label": "Abrir expediente", "expediente_id": exp_id},
            ))
    return out


def _collect_expediente_due(corporate_root: Path) -> list[dict]:
    out = []
    now_dt = datetime.now(timezone.utc)
    horizon = now_dt + timedelta(days=PROXIMITY_DAYS)
    for item in corp.list_expedientes(corporate_root):
        due = _parse_dt(item.get("fecha_objetivo"))
        if not due:
            continue
        exp_id = item["expediente_id"]
        asunto = item.get("asunto") or exp_id
        if due.date() < now_dt.date():
            key = f"EXPEDIENTE_VENCIDO:{exp_id}:{due.date().isoformat()}"
            out.append(_make_alert(
                rule_id="R-EXP-01",
                idempotency_key=key,
                tipo="EXPEDIENTE_VENCIDO",
                severidad="ALTA",
                titulo="Expediente con fecha objetivo vencida",
                descripcion=f"El expediente {exp_id} ({asunto}) tiene fecha_objetivo {due.date().isoformat()} ya superada.",
                origen="INTERNAL",
                expediente_id=exp_id,
                entidad=exp_id,
                area=item.get("ambito") or "LNH",
                evidencia={"fecha_objetivo": item.get("fecha_objetivo"), "estado_actual": item.get("estado_actual")},
                accion={"kind": "expediente", "label": "Abrir expediente", "expediente_id": exp_id},
            ))
        elif now_dt.date() <= due.date() <= horizon.date():
            key = f"EXPEDIENTE_PROXIMO:{exp_id}:{due.date().isoformat()}"
            out.append(_make_alert(
                rule_id="R-EXP-02",
                idempotency_key=key,
                tipo="EXPEDIENTE_PROXIMO",
                severidad="MEDIA",
                titulo="Expediente próximo a fecha objetivo",
                descripcion=(
                    f"El expediente {exp_id} ({asunto}) vence el {due.date().isoformat()} "
                    f"(ventana operativa {PROXIMITY_DAYS} días)."
                ),
                origen="INTERNAL",
                expediente_id=exp_id,
                entidad=exp_id,
                area=item.get("ambito") or "LNH",
                evidencia={
                    "fecha_objetivo": item.get("fecha_objetivo"),
                    "proximity_days": PROXIMITY_DAYS,
                    "estado_actual": item.get("estado_actual"),
                },
                accion={"kind": "expediente", "label": "Abrir expediente", "expediente_id": exp_id},
            ))
    return out


def _collect_board(corporate_root: Path) -> list[dict]:
    out = []
    for session in board.list_board_sessions(corporate_root):
        estado = str(session.get("estado") or "")
        sid = session.get("board_session_id")
        if not sid:
            continue
        if estado != "PENDIENTE_PRESIDENCIA":
            continue
        key = f"DIRECTORIO_PENDIENTE:{sid}"
        exp_ids = session.get("expediente_ids") or []
        out.append(_make_alert(
            rule_id="R-DIR-01",
            idempotency_key=key,
            tipo="DIRECTORIO_PENDIENTE_PRESIDENCIA",
            severidad="ALTA",
            titulo="Directorio pendiente de Presidencia",
            descripcion=f"La sesión de Directorio {sid} está en PENDIENTE_PRESIDENCIA.",
            origen="INTERNAL",
            expediente_id=(exp_ids[0] if exp_ids else None),
            entidad=sid,
            area="DIRECTORIO",
            evidencia={"board_session_id": sid, "estado": estado, "tipo": session.get("tipo")},
            accion={"kind": "board", "label": "Abrir sesión", "board_session_id": sid},
        ))
    return out


def _collect_communications(corporate_root: Path) -> list[dict]:
    out = []
    rows = communications.list_communications(corporate_root, status="PENDIENTE_APROBACION")
    for item in rows:
        cid = item.get("communication_id") or item.get("id")
        if not cid:
            continue
        key = f"COMM_PENDIENTE:{cid}"
        out.append(_make_alert(
            rule_id="R-COMM-01",
            idempotency_key=key,
            tipo="COMM_PENDIENTE_APROBACION",
            severidad="MEDIA",
            titulo="Comunicación pendiente de aprobación",
            descripcion=(
                f"Comunicación {cid} ({item.get('channel') or '—'}) "
                f"en estado PENDIENTE_APROBACION."
            ),
            origen="INTERNAL",
            expediente_id=item.get("expediente_id"),
            entidad=cid,
            area=item.get("channel") or "COMUNICACIONES",
            evidencia={
                "communication_id": cid,
                "status": item.get("status"),
                "human_gate_status": item.get("human_gate_status"),
                "channel": item.get("channel"),
            },
            accion={"kind": "communication", "label": "Abrir comunicación", "communication_id": cid},
        ))
    return out


def _collect_integrations() -> list[dict]:
    out = []
    board_data = connectors.providers_board()
    checks = [
        ("google_oauth", board_data.get("google_oauth") or {}, "Google OAuth"),
        ("gmail", board_data.get("gmail") or board_data.get("email") or {}, "Gmail"),
        ("google_calendar", board_data.get("google_calendar") or board_data.get("calendar") or {}, "Google Calendar"),
        ("whatsapp", board_data.get("whatsapp") or {}, "WhatsApp Meta"),
    ]
    # Normalize: providers_board may nest differently
    google = board_data.get("google_oauth") or {}
    if isinstance(google, dict) and google.get("status"):
        status = str(google.get("status") or "")
        if status in INTEGRATION_BAD or status == "PENDING_AUTH":
            # PENDING_AUTH is incomplete setup — treat as indisponible operativa
            key = f"INTEGRACION:google_oauth:{status}"
            out.append(_make_alert(
                rule_id="R-INT-01",
                idempotency_key=key,
                tipo="INTEGRACION_INDISPONIBLE",
                severidad="MEDIA",
                titulo="Integración Google no disponible",
                descripcion=f"Google OAuth reporta estado {status}.",
                origen="INTERNAL",
                entidad="google_oauth",
                area="INTEGRACIONES",
                evidencia={"provider": "google_oauth", "status": status},
                accion={"kind": "config", "label": "Abrir configuración", "route": "Configuracion"},
            ))
    wa = board_data.get("whatsapp") or {}
    if isinstance(wa, dict) and wa.get("status"):
        status = str(wa.get("status") or "")
        if status in INTEGRATION_BAD or status in {"PENDING_AUTH", "NOT_CONFIGURED"}:
            # Only alert if WhatsApp is explicitly ERROR/FAILED; NOT_CONFIGURED is common
            if status in {"ERROR", "FAILED", "EXPIRED", "DISCONNECTED"}:
                key = f"INTEGRACION:whatsapp:{status}"
                out.append(_make_alert(
                    rule_id="R-INT-02",
                    idempotency_key=key,
                    tipo="INTEGRACION_INDISPONIBLE",
                    severidad="MEDIA",
                    titulo="Integración WhatsApp no disponible",
                    descripcion=f"WhatsApp Meta reporta estado {status}.",
                    origen="INTERNAL",
                    entidad="whatsapp",
                    area="INTEGRACIONES",
                    evidencia={"provider": "whatsapp", "status": status},
                    accion={"kind": "config", "label": "Abrir configuración", "route": "Configuracion"},
                ))
    # Generic scan of status fields
    for name, payload, label in checks:
        if not isinstance(payload, dict):
            continue
        status = str(payload.get("status") or "")
        if status in {"ERROR", "FAILED", "EXPIRED", "DISCONNECTED"}:
            key = f"INTEGRACION:{name}:{status}"
            if any(a["idempotency_key"] == key for a in out):
                continue
            out.append(_make_alert(
                rule_id="R-INT-03",
                idempotency_key=key,
                tipo="INTEGRACION_INDISPONIBLE",
                severidad="MEDIA",
                titulo=f"Integración {label} no disponible",
                descripcion=f"{label} reporta estado {status}.",
                origen="INTERNAL",
                entidad=name,
                area="INTEGRACIONES",
                evidencia={"provider": name, "status": status},
                accion={"kind": "config", "label": "Abrir configuración", "route": "Configuracion"},
            ))
    return out


def _collect_exec_intel(corporate_root: Path) -> list[dict]:
    out = []
    sections = [
        ("weather", exec_weather.fetch_santiago_weather(corporate_root=corporate_root, force=False), "Clima Santiago"),
        ("economy", exec_chile.fetch_chile_economy(corporate_root=corporate_root, force=False), "Economía Chile"),
        ("markets", exec_chile.fetch_copper_market(corporate_root=corporate_root, force=False), "Mercados / cobre"),
    ]
    for key, payload, label in sections:
        status = str((payload or {}).get("status") or "")
        if status == STATUS_NO_DISPONIBLE:
            ik = f"EXEC_INTEL_NO_DISP:{key}"
            out.append(_make_alert(
                rule_id="R-INTEL-01",
                idempotency_key=ik,
                tipo="EXEC_INTEL_NO_DISPONIBLE",
                severidad="MEDIA",
                titulo=f"{label} no disponible",
                descripcion=f"La fuente de {label} reporta estado NO_DISPONIBLE.",
                origen="INTERNAL",
                entidad=key,
                area="EJECUTIVO",
                evidencia={"domain": key, "status": status, "error": (payload or {}).get("error")},
                accion={"kind": "source", "label": "Ver Mi Oficina", "route": "Inicio"},
            ))
        elif status == STATUS_DESACTUALIZADO:
            ik = f"EXEC_INTEL_STALE:{key}"
            out.append(_make_alert(
                rule_id="R-INTEL-02",
                idempotency_key=ik,
                tipo="EXEC_INTEL_DESACTUALIZADO",
                severidad="BAJA",
                titulo=f"{label} desactualizado",
                descripcion=f"La fuente de {label} reporta estado DESACTUALIZADO.",
                origen="INTERNAL",
                entidad=key,
                area="EJECUTIVO",
                evidencia={"domain": key, "status": status, "fetched_at": (payload or {}).get("fetched_at")},
                accion={"kind": "source", "label": "Ver Mi Oficina", "route": "Inicio"},
            ))
    return out


def _collect_indicator_changes(corporate_root: Path) -> list[dict]:
    """Informational only: no approved corporate thresholds → never ALTA/MEDIA crítica."""
    out = []
    economy = exec_chile.fetch_chile_economy(corporate_root=corporate_root, force=False)
    markets = exec_chile.fetch_copper_market(corporate_root=corporate_root, force=False)
    current = {}
    for item in (economy.get("indicators") or []) + (markets.get("indicators") or []):
        key = item.get("key")
        if not key or item.get("value") is None:
            continue
        current[key] = {
            "value": item.get("value"),
            "label": item.get("label") or key,
            "unit": item.get("unit"),
            "observed_at": item.get("observed_at"),
            "source": item.get("source"),
        }
    snap_path = _indicator_snap_path(corporate_root)
    previous = load_json(snap_path, default={}) or {}
    prev_values = previous.get("values") if isinstance(previous, dict) else {}
    if not isinstance(prev_values, dict):
        prev_values = {}
    for key, meta in current.items():
        prev = prev_values.get(key)
        if prev is None:
            continue
        prev_val = prev.get("value") if isinstance(prev, dict) else prev
        if prev_val == meta["value"]:
            continue
        ik = f"INDICADOR_CAMBIO:{key}:{meta.get('observed_at') or meta['value']}"
        out.append(_make_alert(
            rule_id="R-EXT-01",
            idempotency_key=ik,
            tipo="INDICADOR_CAMBIO",
            severidad="INFORMATIVA",
            titulo=f"Cambio registrado en {meta['label']}",
            descripcion=(
                f"{meta['label']} pasó de {prev_val} a {meta['value']}"
                f"{(' ' + str(meta.get('unit'))) if meta.get('unit') else ''} "
                f"(sin umbral corporativo aprobado; señal informativa)."
            ),
            origen="EXTERNAL",
            entidad=key,
            area="MERCADOS",
            evidencia={"previous": prev_val, "current": meta["value"], "source": meta.get("source")},
            referencia=meta.get("source"),
            accion={"kind": "source", "label": "Ver indicadores", "route": "Inicio"},
        ))
    dump_json(snap_path, {"saved_at": now(), "values": current, "platform_calls": 0})
    return out


def _collect_news_signals(corporate_root: Path) -> list[dict]:
    out = []
    news = exec_news.fetch_executive_news(corporate_root=corporate_root, force=False, limit=8)
    by_cat = news.get("by_category") or {}
    for category, keywords in NEWS_KEYWORDS.items():
        section = by_cat.get(category) or {}
        for item in section.get("items") or []:
            title = str(item.get("title") or "")
            title_l = title.lower()
            hit = next((kw for kw in keywords if kw in title_l), None)
            if not hit:
                continue
            url = item.get("url") or item.get("feed_url") or ""
            fp = item.get("id") or hashlib.sha1((title + url).encode("utf-8")).hexdigest()[:12]
            ik = f"NOTICIA_KW:{category}:{fp}"
            out.append(_make_alert(
                rule_id="R-NEWS-01",
                idempotency_key=ik,
                tipo="NOTICIA_PALABRA_CLAVE",
                severidad="INFORMATIVA",
                titulo=f"Noticia {category}: coincidencia «{hit}»",
                descripcion=f"Titular verificado: {title}",
                origen="EXTERNAL",
                entidad=item.get("source") or category,
                area=category.upper(),
                evidencia={
                    "category": category,
                    "keyword": hit,
                    "published_at": item.get("published_at"),
                    "source": item.get("source"),
                },
                referencia=url,
                accion={"kind": "url", "label": "Abrir fuente", "url": url},
            ))
    return out


def scan_executive_alerts(
    corporate_root: Path | None = None,
    *,
    floor_cases: list[dict] | None = None,
    include_external: bool = True,
) -> dict:
    root = Path(corporate_root) if corporate_root is not None else (
        Path(__file__).resolve().parents[2] / "outputs" / "lnh_corporate"
    )
    store = _load_store(root)
    candidates: list[dict] = []
    candidates.extend(_collect_human_gates(floor_cases))
    candidates.extend(_collect_platform_errors(floor_cases))
    candidates.extend(_collect_overdues(root))
    candidates.extend(_collect_expediente_due(root))
    candidates.extend(_collect_board(root))
    candidates.extend(_collect_communications(root))
    candidates.extend(_collect_integrations())
    candidates.extend(_collect_exec_intel(root))
    if include_external:
        candidates.extend(_collect_indicator_changes(root))
        candidates.extend(_collect_news_signals(root))

    active_keys = {c["idempotency_key"] for c in candidates}
    for cand in candidates:
        _upsert_active(store, cand)
    _resolve_missing(store, active_keys, note="Condición ya no aplica en el último escaneo")
    _save_store(root, store)

    activa = [a for a in store["alerts"] if a.get("estado") == "ACTIVA"]
    return {
        "block": "F2C-3",
        "title": "Alertas ejecutivas — Presidencia",
        "scanned_at": now(),
        "status": "ACTUALIZADO",
        "counts": {
            "total": len(store["alerts"]),
            "activa": len(activa),
            "atendida": sum(1 for a in store["alerts"] if a.get("estado") == "ATENDIDA"),
            "resuelta": sum(1 for a in store["alerts"] if a.get("estado") == "RESUELTA"),
            "descartada": sum(1 for a in store["alerts"] if a.get("estado") == "DESCARTADA"),
        },
        "rules": [
            {"rule_id": "R-HG-01", "tipo": "HUMAN_GATE_PENDIENTE", "severidad": "ALTA"},
            {"rule_id": "R-PLAT-01", "tipo": "CASE_PLATFORM_ERROR", "severidad": "ALTA"},
            {"rule_id": "R-TASK-01", "tipo": "TAREA_VENCIDA", "severidad": "ALTA"},
            {"rule_id": "R-EXP-01", "tipo": "EXPEDIENTE_VENCIDO", "severidad": "ALTA"},
            {"rule_id": "R-EXP-02", "tipo": "EXPEDIENTE_PROXIMO", "severidad": "MEDIA", "proximity_days": PROXIMITY_DAYS},
            {"rule_id": "R-DIR-01", "tipo": "DIRECTORIO_PENDIENTE_PRESIDENCIA", "severidad": "ALTA"},
            {"rule_id": "R-COMM-01", "tipo": "COMM_PENDIENTE_APROBACION", "severidad": "MEDIA"},
            {"rule_id": "R-INT-01", "tipo": "INTEGRACION_INDISPONIBLE", "severidad": "MEDIA"},
            {"rule_id": "R-INTEL-01", "tipo": "EXEC_INTEL_NO_DISPONIBLE", "severidad": "MEDIA"},
            {"rule_id": "R-INTEL-02", "tipo": "EXEC_INTEL_DESACTUALIZADO", "severidad": "BAJA"},
            {"rule_id": "R-EXT-01", "tipo": "INDICADOR_CAMBIO", "severidad": "INFORMATIVA"},
            {"rule_id": "R-NEWS-01", "tipo": "NOTICIA_PALABRA_CLAVE", "severidad": "INFORMATIVA"},
        ],
        "platform_calls": 0,
    }


def list_executive_alerts(
    corporate_root: Path | None = None,
    *,
    estado: str | None = None,
    include_history_closed: bool = True,
    limit: int = 50,
) -> dict:
    root = Path(corporate_root) if corporate_root is not None else (
        Path(__file__).resolve().parents[2] / "outputs" / "lnh_corporate"
    )
    store = _load_store(root)
    rows = list(store.get("alerts") or [])
    if estado:
        rows = [a for a in rows if a.get("estado") == estado]
    elif not include_history_closed:
        rows = [a for a in rows if a.get("estado") in {"ACTIVA", "ATENDIDA"}]
    severity_rank = {"ALTA": 0, "MEDIA": 1, "BAJA": 2, "INFORMATIVA": 3}
    state_rank = {"ACTIVA": 0, "ATENDIDA": 1, "RESUELTA": 2, "DESCARTADA": 3}
    rows.sort(key=lambda a: (
        state_rank.get(a.get("estado"), 9),
        severity_rank.get(a.get("severidad"), 9),
        a.get("detected_at") or "",
    ))
    if limit:
        rows = rows[: max(1, min(int(limit), 200))]
    return {
        "block": "F2C-3",
        "generated_at": now(),
        "updated_at": store.get("updated_at"),
        "alerts": rows,
        "counts": {
            "returned": len(rows),
            "activa": sum(1 for a in (store.get("alerts") or []) if a.get("estado") == "ACTIVA"),
            "total": len(store.get("alerts") or []),
        },
        "platform_calls": 0,
    }


def set_alert_state(
    corporate_root: Path | None,
    alert_id: str,
    *,
    estado: str,
    actor: str = "Presidencia LNH",
    note: str = "",
) -> dict:
    if estado not in ALERT_STATES:
        raise ValueError(f"Estado no válido: {estado}")
    root = Path(corporate_root) if corporate_root is not None else (
        Path(__file__).resolve().parents[2] / "outputs" / "lnh_corporate"
    )
    store = _load_store(root)
    found = None
    for item in store["alerts"]:
        if item.get("alert_id") == alert_id:
            found = item
            break
    if not found:
        raise FileNotFoundError("Alerta no encontrada.")
    found["estado"] = estado
    found["updated_at"] = now()
    found.setdefault("history", []).append(_history_entry(estado, actor=actor, note=note))
    found["platform_calls"] = 0
    _save_store(root, store)
    return found
