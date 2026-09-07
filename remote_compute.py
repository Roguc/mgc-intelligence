"""Provider-neutral runtime selection for Mission Control inference.

The legacy Tailscale/Ollama appliance and configured external adapters share the
same lifecycle contract so callers never depend on a provider-specific route.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
import json, os, shutil, subprocess
from pathlib import Path
from typing import Callable
from urllib.request import urlopen

MODEL = "qwen3:14b"
NODE_NAME = os.getenv("LNH_QWEN_NODE", "lnh-qwen")
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
        if not executable and os.name == "nt":
            candidate = Path(os.environ.get("ProgramFiles", r"C:\\Program Files")) / "Tailscale" / "tailscale.exe"
            if candidate.is_file():
                executable = str(candidate)
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

    provider_name = "ollama-tailscale"

    def generate(self, prompt: str, execution_id: str, attempt: int) -> tuple[dict, str]:
        from urllib.request import Request
        payload = {'model': MODEL, 'prompt': prompt, 'stream': False, 'think': False, 'options': {'temperature': 0.1, 'num_ctx': 8192}}
        request = Request(f'{self.endpoint_url}/api/generate', data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urlopen(request, timeout=600) as response:
                result = json.loads(response.read().decode('utf-8'))
        except Exception as error:
            raise RuntimeError(f'Ollama no pudo generar el informe (intento {attempt}, {execution_id}): {error}') from error
        if not isinstance(result, dict):
            raise RuntimeError('Ollama devolvió una respuesta con formato no reconocido.')
        text = result.get('response')
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError('Ollama devolvió una respuesta sin texto.')
        return result, text.strip()

_runtime: object | None = None
def runtime() -> object:
    global _runtime
    if _runtime is None:
        if os.getenv("MGC_INFERENCE_PROVIDER", "ollama").casefold() == "alibaba":
            from alibaba_model_studio import AlibabaModelStudioLifecycle
            _runtime = AlibabaModelStudioLifecycle()
        else:
            _runtime = TailscaleComputeLifecycle()
    return _runtime
