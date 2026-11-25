"""Model failures reach the browser as a readable message.

Real regression: Ollama couldn't load the configured model, the provider's
raise_for_status() went unhandled, FastAPI returned a bare 500 without CORS
headers, the browser discarded it, and the frontend reported "Cannot reach
the CareerKit API" while the backend was running fine.
"""
import asyncio
import unittest

import httpx
from fastapi.testclient import TestClient

from app.ai.base import ModelError
from app.ai.ollama_provider import OllamaProvider
from app.main import app

ORIGIN = {"Origin": "http://localhost:3000"}


def _provider(handler) -> OllamaProvider:
    p = OllamaProvider("http://ollama.test", "inkling-2-mini")
    real_client = httpx.AsyncClient

    class _Client(real_client):
        def __init__(self, *a, **kw):
            kw["transport"] = httpx.MockTransport(handler)
            super().__init__(*a, **kw)

    p._client_cls = _Client
    return p


def _chat_error(handler) -> str:
    p = _provider(handler)
    original = httpx.AsyncClient
    httpx.AsyncClient = p._client_cls
    try:
        asyncio.run(p._chat([{"role": "user", "content": "hi"}]))
    except ModelError as e:
        return str(e)
    finally:
        httpx.AsyncClient = original
    raise AssertionError("expected ModelError")


class ProviderErrorTests(unittest.TestCase):
    def test_ollama_load_failure_message_is_passed_through(self):
        msg = _chat_error(lambda r: httpx.Response(500, json={
            "error": 'mlx runner failed: Error: Inkling2 tensor "model.llm.unembed.weight" is missing'}))
        self.assertEqual(msg, "The AI model 'inkling-2-mini' failed: mlx runner failed: Error: Inkling2 tensor "
                              '"model.llm.unembed.weight" is missing')

    def test_missing_model_says_how_to_install_it(self):
        msg = _chat_error(lambda r: httpx.Response(404, json={"error": "model 'inkling-2-mini' not found"}))
        self.assertIn("ollama pull inkling-2-mini", msg)

    def test_ollama_not_running(self):
        def refuse(request):
            raise httpx.ConnectError("refused", request=request)
        self.assertIn("Cannot connect to Ollama at http://ollama.test", _chat_error(refuse))

    def test_timeout(self):
        def slow(request):
            raise httpx.ReadTimeout("slow", request=request)
        self.assertIn("didn't respond within", _chat_error(slow))


class ApiErrorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        async def model_fails():
            raise ModelError("The AI model 'x' failed: boom")

        async def bug():
            raise KeyError("message")

        app.add_api_route("/__test__/model-fails", model_fails)
        app.add_api_route("/__test__/bug", bug)
        cls.client = TestClient(app, raise_server_exceptions=False)

    def test_model_error_is_a_readable_502_with_cors(self):
        r = self.client.get("/__test__/model-fails", headers=ORIGIN)
        self.assertEqual(r.status_code, 502)
        self.assertEqual(r.json(), {"detail": "The AI model 'x' failed: boom"})
        self.assertEqual(r.headers.get("access-control-allow-origin"), "http://localhost:3000")

    def test_unexpected_error_is_a_readable_500_with_cors(self):
        r = self.client.get("/__test__/bug", headers=ORIGIN)
        self.assertEqual(r.status_code, 500)
        self.assertIn("KeyError", r.json()["detail"])
        self.assertEqual(r.headers.get("access-control-allow-origin"), "http://localhost:3000")


if __name__ == "__main__":
    unittest.main()
