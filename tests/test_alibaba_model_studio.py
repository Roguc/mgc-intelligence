import os
import unittest
from unittest.mock import patch

from alibaba_model_studio import AlibabaModelStudioLifecycle
import remote_compute


class _Response:
    def __init__(self, payload): self.payload = payload
    def read(self): import json; return json.dumps(self.payload).encode("utf-8")
    def __enter__(self): return self
    def __exit__(self, *args): return False


class AlibabaModelStudioTests(unittest.TestCase):
    def env(self):
        return {
            "MGC_ALIBABA_API_KEY": "test-secret-never-sent",
            "MGC_ALIBABA_BASE_URL": "https://workspace.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
            "MGC_ALIBABA_MODEL": "qwen-plus",
        }

    def test_missing_configuration_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual("OFFLINE", AlibabaModelStudioLifecycle().inspect().state)

    def test_models_health_is_ready_without_generation(self):
        calls = []
        def opener(request, timeout):
            calls.append((request.full_url, request.get_method()))
            return _Response({"data": [{"id": "qwen-plus"}]})
        with patch.dict(os.environ, self.env(), clear=True):
            status = AlibabaModelStudioLifecycle(opener=opener).inspect()
        self.assertTrue(status.ready)
        self.assertEqual([("https://workspace.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1/models", "GET")], calls)

    def test_generation_uses_openai_compatible_chat_shape(self):
        def opener(request, timeout):
            return _Response({"model": "qwen-plus", "choices": [{"message": {"content": "Informe real."}}], "usage": {"prompt_tokens": 2, "completion_tokens": 3}})
        with patch.dict(os.environ, self.env(), clear=True):
            result, text = AlibabaModelStudioLifecycle(opener=opener).generate("hola", "execution", 1)
        self.assertEqual("Informe real.", text)
        self.assertEqual(2, result["prompt_eval_count"])

    def test_runtime_selects_alibaba_adapter(self):
        with patch.dict(os.environ, {"MGC_INFERENCE_PROVIDER": "alibaba"}, clear=True):
            remote_compute._runtime = None
            self.assertIsInstance(remote_compute.runtime(), AlibabaModelStudioLifecycle)
        remote_compute._runtime = None
