"""Alibaba Cloud Model Studio adapter for the approved inference gateway.

Configuration is read only from environment variables. Credentials are never
persisted, logged, or exposed to Mission Control.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from typing import Callable
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


PROVIDER_NAME = "alibaba-model-studio"
DEFAULT_MODEL = "qwen-plus"


@dataclass(frozen=True)
class ModelStudioStatus:
    state: str
    executive_message: str
    detail: str = ""
    endpoint: str = ""
    model: str = DEFAULT_MODEL

    @property
    def ready(self) -> bool:
        return self.state == "READY"

    def to_dict(self) -> dict[str, object]:
        return asdict(self) | {"ready": self.ready}


class AlibabaModelStudioLifecycle:
    """OpenAI-compatible Model Studio client; ``/models`` is its health check."""

    provider_name = PROVIDER_NAME

    def __init__(self, *, opener: Callable[..., object] = urlopen):
        self.opener = opener

    @property
    def model(self) -> str:
        return os.getenv("MGC_ALIBABA_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL

    @property
    def _base_url(self) -> str:
        return os.getenv("MGC_ALIBABA_BASE_URL", "").strip().rstrip("/")

    @property
    def endpoint_url(self) -> str:
        """Safe display label; the configured API host never leaves this adapter."""
        return "Alibaba Model Studio (ap-southeast-1)" if self._base_url else ""

    @property
    def api_key(self) -> str:
        return os.getenv("MGC_ALIBABA_API_KEY", "").strip()

    def _configuration_error(self) -> str:
        if not self.api_key:
            return "Falta la credencial de Alibaba Model Studio."
        if not self._base_url:
            return "Falta el API host de Alibaba Model Studio para ap-southeast-1."
        parsed = urlparse(self._base_url)
        if parsed.scheme != "https" or not parsed.netloc:
            return "El API host de Alibaba Model Studio debe ser una URL HTTPS válida."
        if ".ap-southeast-1." not in parsed.netloc:
            return "El API host no corresponde a la región ap-southeast-1."
        if not parsed.path.endswith("/compatible-mode/v1"):
            return "El API host debe terminar en /compatible-mode/v1."
        return ""

    def _request(self, suffix: str, *, body: dict | None = None, timeout: int = 30) -> dict:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = Request(f"{self._base_url}{suffix}", data=data, headers=headers, method="POST" if body is not None else "GET")
        try:
            with self.opener(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise RuntimeError(f"Alibaba Model Studio rechazó el health check ({error.code}).") from error
        except Exception as error:
            raise RuntimeError(f"No fue posible conectar con Alibaba Model Studio: {error}") from error
        if not isinstance(payload, dict):
            raise RuntimeError("Alibaba Model Studio devolvió una respuesta no reconocida.")
        return payload

    def inspect(self) -> ModelStudioStatus:
        problem = self._configuration_error()
        if problem:
            return ModelStudioStatus("OFFLINE", "Motor de inteligencia no configurado.", problem, self.endpoint_url, self.model)
        try:
            payload = self._request("/models")
        except RuntimeError as error:
            return ModelStudioStatus("OFFLINE", "Motor de inteligencia no disponible.", str(error), self.endpoint_url, self.model)
        models = {str(item.get("id", "")) for item in payload.get("data", []) if isinstance(item, dict)}
        if self.model not in models:
            return ModelStudioStatus("STARTING", "Motor de inteligencia preparando modelo.", f"El modelo configurado no está disponible: {self.model}.", self.endpoint_url, self.model)
        return ModelStudioStatus("READY", "Motor de inteligencia listo.", endpoint=self.endpoint_url, model=self.model)

    def prepare(self, timeout_seconds: int = 45) -> ModelStudioStatus:
        del timeout_seconds
        return self.inspect()

    def generate(self, prompt: str, execution_id: str, attempt: int) -> tuple[dict, str]:
        del execution_id
        payload = self._request("/chat/completions", body={
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }, timeout=600)
        choices = payload.get("choices", [])
        content = choices[0].get("message", {}).get("content") if choices and isinstance(choices[0], dict) else None
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError(f"Alibaba Model Studio devolvió una respuesta sin texto (intento {attempt}).")
        usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
        return {
            "model": payload.get("model", self.model),
            "prompt_eval_count": usage.get("prompt_tokens"),
            "eval_count": usage.get("completion_tokens"),
            "total_duration": None,
            "load_duration": None,
        }, content.strip()
