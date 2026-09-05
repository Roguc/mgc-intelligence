"""Private Tailscale transport for Mission Control inference.

The sole operational route to the remote Qwen appliance: no Vast API, dynamic
endpoint, public IP, SSH or local tunnel is present in this module.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
import json, os, shutil, subprocess
from typing import Callable
from urllib.request import urlopen

MODEL = "qwen3:14b"
NODE_NAME = os.getenv("LNH_QWEN_NODE", "lnh-mgc-qwen")
OLLAMA_PORT = int(os.getenv("LNH_QWEN_PORT", "11434"))

@dataclass(frozen=True)
class ComputeStatus:
    state: str
    executive_message: str
    detail: str = ""
    endpoint: str = ""
    model: str = MODEL
    @property
    def ready(self) -> bool: return self.state == "READY"
    def to_dict(self) -> dict[str, object]: return asdict(self) | {"ready": self.ready}

class TailscaleComputeLifecycle:
    def __init__(self, *, runner: Callable[..., object] = subprocess.run, probe: Callable[[str], object] | None = None, tailscale_path: str | None = None):
        self.runner, self.probe, self.tailscale_path = runner, probe or self._probe, tailscale_path
    @property
    def endpoint_url(self) -> str: return f"http://{NODE_NAME}:{OLLAMA_PORT}"
    @staticmethod
    def _probe(url: str) -> object:
        with urlopen(url, timeout=6) as response: return json.loads(response.read().decode("utf-8"))
    def _tailnet_ready(self) -> bool:
        executable = self.tailscale_path or shutil.which("tailscale")
        if not executable: return False
        result = self.runner([executable, "status", "--json"], capture_output=True, text=True, check=False)
        if getattr(result, "returncode", 1) != 0: return False
        try: return json.loads(getattr(result, "stdout", "{}")).get("BackendState") == "Running"
        except ValueError: return False
    def inspect(self) -> ComputeStatus:
        if not self._tailnet_ready(): return ComputeStatus("OFFLINE", "Red privada de inteligencia no disponible.")
        try: names = [item.get("name") for item in self.probe(f"{self.endpoint_url}/api/tags").get("models", [])]
        except Exception: return ComputeStatus("STARTING", "Preparando motor de inteligencia.", endpoint=self.endpoint_url)
        if MODEL not in names: return ComputeStatus("STARTING", "Preparando motor de inteligencia.", "El modelo requerido aún no está disponible.", self.endpoint_url)
        return ComputeStatus("READY", "Motor de inteligencia listo.", endpoint=self.endpoint_url)
    def prepare(self, timeout_seconds: int = 45) -> ComputeStatus: return self.inspect()

_runtime: TailscaleComputeLifecycle | None = None
def runtime() -> TailscaleComputeLifecycle:
    global _runtime
    if _runtime is None: _runtime = TailscaleComputeLifecycle()
    return _runtime
