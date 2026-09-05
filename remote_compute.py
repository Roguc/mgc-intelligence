"""Single, self-healing private transport for Mission Control remote inference.

This module is the only operational route to Vast/Ollama.  It discovers the
current SSH endpoint from Vast's authenticated instance API, starts a private
SSH forward, and verifies the required Ollama model.  It never exposes Ollama
on a public interface and it never performs model inference itself.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Callable
from urllib.error import URLError
from urllib.request import Request, urlopen


MODEL = "qwen3:14b"
LOCAL_HOST = "127.0.0.1"
LOCAL_PORT = 11435
API_ROOT = "https://console.vast.ai/api/v0"
DEFAULT_KEY = Path.home() / ".ssh" / "id_ed25519_lnh_vastai"
DEFAULT_KNOWN_HOSTS = Path.home() / ".lnh" / "mission-control-vast-known-hosts"


@dataclass(frozen=True)
class ComputeStatus:
    state: str
    executive_message: str
    detail: str = ""
    endpoint: str = ""
    model: str = MODEL

    @property
    def ready(self) -> bool:
        return self.state == "READY"

    def to_dict(self) -> dict[str, object]:
        return asdict(self) | {"ready": self.ready}


@dataclass(frozen=True)
class VastEndpoint:
    instance_id: str
    host: str
    port: int
    status: str


class RemoteComputeError(RuntimeError):
    """Expected, safely-presentable remote compute failure."""


class VastDiscovery:
    """Discover a running Vast instance without persisting credentials in Git."""

    def __init__(self, token: str | None = None, instance_id: str | None = None,
                 api_get: Callable[[str, dict[str, str]], object] | None = None):
        self.token = token or os.getenv("LNH_VAST_API_KEY")
        self.instance_id = instance_id or os.getenv("LNH_VAST_INSTANCE_ID")
        self.api_get = api_get or self._get

    @staticmethod
    def _get(url: str, headers: dict[str, str]) -> object:
        request = Request(url, headers=headers)
        with urlopen(request, timeout=12) as response:
            return json.loads(response.read().decode("utf-8"))

    def discover(self) -> VastEndpoint:
        if not self.token:
            raise RemoteComputeError("No hay una credencial corporativa de Vast configurada en este equipo.")
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}
        try:
            if self.instance_id:
                body = self.api_get(f"{API_ROOT}/instances/{self.instance_id}/", headers)
                candidate = body.get("instances", body) if isinstance(body, dict) else body
            else:
                body = self.api_get(f"{API_ROOT}/instances/", headers)
                candidates = body.get("instances", []) if isinstance(body, dict) else body
                candidate = next((item for item in candidates if str(item.get("actual_status", "")).casefold() == "running"), None)
                if candidate is None:
                    raise RemoteComputeError("No existe una instancia corporativa de Vast en ejecución.")
        except (URLError, OSError, ValueError) as error:
            raise RemoteComputeError(f"No fue posible consultar el estado de Vast: {error}") from error
        if not isinstance(candidate, dict):
            raise RemoteComputeError("Vast no devolvió datos válidos de la instancia.")
        state = str(candidate.get("actual_status", candidate.get("status", ""))).casefold()
        if state != "running":
            raise RemoteComputeError("Cómputo remoto no disponible. Inicie Vast.")
        host, port = candidate.get("ssh_host"), candidate.get("ssh_port")
        if not host or not port:
            raise RemoteComputeError("Vast está iniciando y aún no publicó un endpoint de cómputo.")
        return VastEndpoint(str(candidate.get("id", candidate.get("contract_id", self.instance_id or ""))), str(host), int(port), state)


class RemoteComputeLifecycle:
    """Idempotent lifecycle manager used by the UI and Inference Gateway."""

    def __init__(self, discovery: VastDiscovery | None = None, *, runner: Callable[..., object] = subprocess.run,
                 probe: Callable[[str], object] | None = None, sleep: Callable[[float], None] = time.sleep,
                 key_path: Path = DEFAULT_KEY, known_hosts: Path = DEFAULT_KNOWN_HOSTS):
        self.discovery = discovery or VastDiscovery()
        self.runner, self.probe, self.sleep = runner, probe or self._probe, sleep
        self.key_path, self.known_hosts = key_path, known_hosts

    @staticmethod
    def _probe(url: str) -> object:
        with urlopen(url, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    @property
    def endpoint_url(self) -> str:
        return f"http://{LOCAL_HOST}:{LOCAL_PORT}"

    def inspect(self) -> ComputeStatus:
        try:
            tags = self.probe(f"{self.endpoint_url}/api/tags")
            names = [item.get("name") for item in tags.get("models", [])]
            if MODEL in names:
                return ComputeStatus("READY", "Motor de inteligencia listo.", endpoint=self.endpoint_url)
            return ComputeStatus("PREPARING", "Preparando motor de inteligencia.", "El modelo requerido aún no está disponible.")
        except Exception:
            return ComputeStatus("UNAVAILABLE", "Cómputo remoto no disponible. Inicie Vast.")

    def _tunnel_alive(self) -> bool:
        return self.inspect().state in {"READY", "PREPARING"}

    def _ssh(self, endpoint: VastEndpoint, remote_command: str | None = None) -> None:
        if not self.key_path.is_file():
            raise RemoteComputeError("No está disponible la clave segura de acceso al cómputo remoto.")
        self.known_hosts.parent.mkdir(parents=True, exist_ok=True)
        arguments = [
            "ssh", "-i", str(self.key_path), "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes",
            "-o", "StrictHostKeyChecking=accept-new", "-o", f"UserKnownHostsFile={self.known_hosts}",
            "-o", "ConnectTimeout=12", "-o", "ServerAliveInterval=20", "-o", "ServerAliveCountMax=3",
            "-p", str(endpoint.port), f"root@{endpoint.host}",
        ]
        if remote_command:
            arguments.append(remote_command)
        else:
            arguments[1:1] = ["-f", "-N", "-o", "ExitOnForwardFailure=yes", "-L", f"{LOCAL_HOST}:{LOCAL_PORT}:127.0.0.1:11434"]
        result = self.runner(arguments, capture_output=True, text=True, check=False)
        if getattr(result, "returncode", 1) != 0:
            raise RemoteComputeError("No fue posible establecer el transporte privado de cómputo remoto.")

    def _ensure_remote_ollama(self, endpoint: VastEndpoint) -> None:
        # No endpoint public is created: Ollama remains on the remote loopback.
        command = (
            "command -v ollama >/dev/null 2>&1 || exit 24; "
            "(supervisorctl start mgc-ollama >/dev/null 2>&1 || true); "
            "curl --fail --silent http://127.0.0.1:11434/api/tags >/dev/null 2>&1 || "
            "(OLLAMA_HOST=127.0.0.1:11434 nohup ollama serve >/tmp/mgc-ollama.log 2>&1 &); "
            "sleep 2; curl --fail --silent http://127.0.0.1:11434/api/tags >/dev/null"
        )
        self._ssh(endpoint, command)

    def prepare(self, timeout_seconds: int = 45) -> ComputeStatus:
        """Recover discovery, SSH transport and Ollama automatically within a bounded wait."""
        current = self.inspect()
        if current.ready:
            return current
        try:
            endpoint = self.discovery.discover()
            deadline = time.monotonic() + timeout_seconds
            last_error = ""
            while time.monotonic() < deadline:
                try:
                    self._ensure_remote_ollama(endpoint)
                    if not self._tunnel_alive():
                        self._ssh(endpoint)
                except RemoteComputeError as error:
                    last_error = str(error)
                    self.sleep(2)
                    continue
                current = self.inspect()
                if current.ready:
                    return current
                self.sleep(2)
            detail = last_error or "El motor aún no completó su inicio."
            return ComputeStatus("PREPARING", "Preparando motor de inteligencia.", detail)
        except RemoteComputeError as error:
            message = str(error)
            executive = "Cómputo remoto no disponible. Inicie Vast." if "Inicie Vast" in message else "Preparando motor de inteligencia."
            return ComputeStatus("UNAVAILABLE", executive, message)


_runtime: RemoteComputeLifecycle | None = None


def runtime() -> RemoteComputeLifecycle:
    global _runtime
    if _runtime is None:
        _runtime = RemoteComputeLifecycle()
    return _runtime
