"""Focused Day 3 tests for the VYOMA Role 1 local (Ollama) model integration.

Covers:
- OllamaModelProvider implements the ModelProvider abstraction
- successful response parsing + metadata extraction
- configuration (env vars / defaults / explicit overrides)
- connection failure, timeout, HTTP error surfaced as ProviderError
- malformed (non-JSON) response surfaced as ProviderError
- empty / missing model response surfaced as ProviderError
- model-not-found surfaced as OllamaModelError
- no-cloud-fallback behaviour (unreachable => failure, never a verdict)
- router can register/select the local provider
- ProviderReasoningEngine works with the local-provider abstraction and keeps
  the deterministic safety grounding (never overridden by model output)

All HTTP transport is stubbed, so no Ollama server and no network is required.
"""

from __future__ import annotations

import json
import socket
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from ai_agent.config import (
    ENV_OLLAMA_BASE_URL,
    ENV_OLLAMA_MODEL,
    ENV_OLLAMA_TIMEOUT,
    OllamaConfig,
    load_ollama_config,
)
from ai_agent.router.model_provider import (
    ModelProvider,
    ModelResponse,
    ProviderError,
)
from ai_agent.router.model_router import ModelRouter, build_local_model_router
from ai_agent.router.ollama_provider import (
    OllamaConnectionError,
    OllamaModelError,
    OllamaModelProvider,
    OllamaResponseError,
    OllamaTimeoutError,
    _default_transport,
)
from ai_agent.reasoning.provider_reasoning_engine import ProviderReasoningEngine
from ai_agent.reasoning.reasoning_engine import ReasoningError

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "ai_agent" / "fixtures"


def _load(scenario: str) -> dict:
    path = FIXTURES_DIR / f"{scenario}_case.json"
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


# ---------------------------------------------------------------------------
# Transport stubs (no network, no Ollama)
# ---------------------------------------------------------------------------


def _stub_transport(status: int, body: bytes):
    """Build a deterministic transport stub returning a fixed response."""
    def transport(url, data, headers, timeout):  # noqa: ARG001
        return status, body
    return transport


def _ok_body(content: str = "reasoned reply") -> bytes:
    payload = {
        "model": "llama3",
        "message": {"role": "assistant", "content": content},
        "done": True,
        "total_duration": 123,
        "eval_count": 42,
        "done_reason": "stop",
    }
    return json.dumps(payload).encode("utf-8")


class _RaisingTransport:
    def __init__(self, exc):
        self.exc = exc
        self.calls = []

    def __call__(self, url, data, headers, timeout):
        self.calls.append((url, data, headers, timeout))
        raise self.exc


class RealTransportMappingTests(unittest.TestCase):
    """The real stdlib transport must map failures to typed provider errors."""

    def _transport_result(self, urlopen_error):
        with mock.patch(
            "ai_agent.router.ollama_provider.urllib.request.urlopen",
            side_effect=urlopen_error,
        ):
            return _default_transport("http://127.0.0.1:1/api/chat", b"{}", {}, 5)

    def test_timeout_maps_to_ollama_timeout_error(self) -> None:
        # socket.timeout is an OSError subclass; the specific timeout handler
        # must run before the broad connection/OSError handler.
        with self.assertRaises(OllamaTimeoutError) as ctx:
            self._transport_result(socket.timeout("timed out"))
        self.assertIsInstance(ctx.exception, OllamaTimeoutError)
        self.assertNotIsInstance(ctx.exception, OllamaConnectionError)

    def test_timeouterror_maps_to_ollama_timeout_error(self) -> None:
        # TimeoutError is also an OSError subclass -> must be the timeout branch.
        with self.assertRaises(OllamaTimeoutError) as ctx:
            self._transport_result(TimeoutError("deadline exceeded"))
        self.assertNotIsInstance(ctx.exception, OllamaConnectionError)

    def test_urlerror_maps_to_ollama_connection_error(self) -> None:
        with self.assertRaises(OllamaConnectionError):
            self._transport_result(
                urllib.error.URLError("Connection refused")
            )

    def test_connection_oserror_maps_to_ollama_connection_error(self) -> None:
        with self.assertRaises(OllamaConnectionError):
            self._transport_result(ConnectionRefusedError("refused"))

    def test_provider_error_is_preserved_unwrapped(self) -> None:
        sentinel = ProviderError("already typed")
        with mock.patch(
            "ai_agent.router.ollama_provider.urllib.request.urlopen",
            side_effect=sentinel,
        ):
            with self.assertRaises(ProviderError) as ctx:
                _default_transport("http://127.0.0.1:1/api/chat", b"{}", {}, 5)
        self.assertIs(ctx.exception, sentinel)

    def test_success_returns_status_and_body(self) -> None:
        with mock.patch(
            "ai_agent.router.ollama_provider.urllib.request.urlopen"
        ) as urlopen:
            resp = mock.MagicMock()
            resp.status = 200
            resp.read.return_value = b"ok"
            urlopen.return_value.__enter__.return_value = resp
            status, body = _default_transport(
                "http://127.0.0.1:1/api/chat", b"{}", {}, 5
            )
        self.assertEqual(status, 200)
        self.assertEqual(body, b"ok")

    def test_http_error_returns_status_and_body(self) -> None:
        http_error = urllib.error.HTTPError(
            url="http://127.0.0.1:1/api/chat",
            code=500,
            msg="Internal Server Error",
            hdrs={},
            fp=None,
        )
        http_error.read = lambda: b"boom"
        with mock.patch(
            "ai_agent.router.ollama_provider.urllib.request.urlopen",
            side_effect=http_error,
        ):
            status, body = _default_transport(
                "http://127.0.0.1:1/api/chat", b"{}", {}, 5
            )
        self.assertEqual(status, 500)
        self.assertEqual(body, b"boom")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class ConfigTests(unittest.TestCase):
    def test_defaults_are_sensible_for_local_development(self) -> None:
        cfg = load_ollama_config(environ={})
        self.assertEqual(cfg.base_url, "http://127.0.0.1:11434")
        self.assertTrue(cfg.model)
        self.assertGreater(cfg.timeout, 0)

    def test_trailing_slash_stripped(self) -> None:
        cfg = load_ollama_config(
            base_url="http://127.0.0.1:11434/", environ={}
        )
        self.assertEqual(cfg.base_url, "http://127.0.0.1:11434")

    def test_environment_variables_override_defaults(self) -> None:
        cfg = load_ollama_config(
            environ={
                ENV_OLLAMA_BASE_URL: "http://localhost:9999",
                ENV_OLLAMA_MODEL: "llama3.1",
                ENV_OLLAMA_TIMEOUT: "30",
            }
        )
        self.assertEqual(cfg.base_url, "http://localhost:9999")
        self.assertEqual(cfg.model, "llama3.1")
        self.assertEqual(cfg.timeout, 30.0)

    def test_explicit_args_override_environment(self) -> None:
        cfg = load_ollama_config(
            base_url="http://127.0.0.1:8080",
            model="tiny",
            timeout=5,
            environ={ENV_OLLAMA_BASE_URL: "http://other:1", ENV_OLLAMA_MODEL: "x"},
        )
        self.assertEqual(cfg.base_url, "http://127.0.0.1:8080")
        self.assertEqual(cfg.model, "tiny")
        self.assertEqual(cfg.timeout, 5)

    def test_invalid_timeout_falls_back_to_default(self) -> None:
        cfg = load_ollama_config(
            timeout="not-a-number", environ={}
        )
        self.assertGreater(cfg.timeout, 0)


# ---------------------------------------------------------------------------
# Provider interface + successful parsing
# ---------------------------------------------------------------------------


class OllamaProviderInterfaceTests(unittest.TestCase):
    def test_implements_model_provider_abstraction(self) -> None:
        provider = OllamaModelProvider()
        self.assertIsInstance(provider, ModelProvider)
        self.assertIn("reasoning", provider.capabilities)
        self.assertTrue(provider.name.startswith("ollama:"))
        self.assertIsInstance(provider.config, OllamaConfig)

    def test_successful_response_parsing_and_metadata(self) -> None:
        provider = OllamaModelProvider(
            transport=_stub_transport(200, _ok_body("definitely fine")),
        )
        response = provider.generate("prompt", capability="reasoning")
        self.assertIsInstance(response, ModelResponse)
        self.assertTrue(response.ok)
        self.assertEqual(response.content, "definitely fine")
        self.assertIsNone(response.error)
        self.assertEqual(response.metadata["provider"], "ollama")
        self.assertEqual(response.metadata["model"], "llama3")
        self.assertEqual(response.metadata["eval_count"], 42)
        self.assertEqual(response.metadata["transport"], "http")

    def test_http_transport_marked_for_http_base(self) -> None:
        provider = OllamaModelProvider(
            config=OllamaConfig(base_url="http://127.0.0.1:11434"),
            transport=_stub_transport(200, _ok_body("x")),
        )
        response = provider.generate("p")
        self.assertEqual(response.metadata["transport"], "http")

    def test_provider_sends_chat_payload_to_chat_endpoint(self) -> None:
        captured = {}

        def transport(url, data, headers, timeout):
            captured["url"] = url
            captured["payload"] = json.loads(data.decode("utf-8"))
            captured["headers"] = headers
            captured["timeout"] = timeout
            return 200, _ok_body("ok")

        provider = OllamaModelProvider(transport=transport)
        provider.generate("hello", capability="reasoning")
        self.assertTrue(captured["url"].endswith("/api/chat"))
        self.assertEqual(captured["payload"]["model"], provider.config.model)
        self.assertEqual(
            captured["payload"]["messages"][0],
            {"role": "user", "content": "hello"},
        )
        self.assertEqual(captured["payload"]["stream"], False)
        self.assertNotIn("capability", captured["payload"])
        self.assertEqual(captured["headers"]["Content-Type"], "application/json")
        self.assertEqual(captured["timeout"], provider.config.timeout)

    def test_payload_contains_only_documented_ollama_fields(self) -> None:
        captured = {}

        def transport(url, data, headers, timeout):  # noqa: ARG001
            captured["payload"] = json.loads(data.decode("utf-8"))
            return 200, _ok_body("ok")

        provider = OllamaModelProvider(transport=transport)
        provider.generate("hello", capability="reasoning", messages=None)
        # internal VYOMA capability must never leak into the Ollama request.
        self.assertEqual(
            set(captured["payload"].keys()),
            {"model", "messages", "stream", "options"},
        )
        self.assertEqual(captured["payload"]["stream"], False)
        self.assertEqual(captured["payload"]["options"], {"num_predict": 300})
        self.assertNotIn("capability", captured["payload"])

    def test_provider_records_last_payload(self) -> None:
        provider = OllamaModelProvider(
            transport=_stub_transport(200, _ok_body("ok"))
        )
        provider.generate("hi")
        self.assertIsNotNone(provider.last_payload)
        self.assertEqual(provider.last_payload["model"], provider.config.model)


# ---------------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------------


class OllamaProviderFailureTests(unittest.TestCase):
    def test_connection_refused_is_provider_error(self) -> None:
        provider = OllamaModelProvider(
            config=OllamaConfig(base_url="http://127.0.0.1:1"),
            transport=_RaisingTransport(OllamaConnectionError("refused")),
        )
        with self.assertRaises(ProviderError):
            provider.generate("p")

    def test_transport_exception_is_provider_error(self) -> None:
        provider = OllamaModelProvider(
            transport=_RaisingTransport(PermissionError("boom")),
        )
        with self.assertRaises(ProviderError):
            provider.generate("p")

    def test_timeout_is_surfaced(self) -> None:
        provider = OllamaModelProvider(
            transport=_RaisingTransport(OllamaTimeoutError("timed out")),
        )
        with self.assertRaises(ProviderError) as ctx:
            provider.generate("p")
        self.assertIsInstance(ctx.exception, OllamaTimeoutError)

    def test_http_error_is_provider_error(self) -> None:
        provider = OllamaModelProvider(
            config=OllamaConfig(base_url="http://127.0.0.1:11434"),
            transport=_stub_transport(500, b"internal error"),
        )
        with self.assertRaises(ProviderError) as ctx:
            provider.generate("p")
        self.assertIsInstance(ctx.exception, OllamaResponseError)
        self.assertIn("500", str(ctx.exception))

    def test_model_not_found_is_specific_error(self) -> None:
        provider = OllamaModelProvider(
            config=OllamaConfig(model="ghost", base_url="http://127.0.0.1:11434"),
            transport=_stub_transport(
                404, b'{"error":"model \\"ghost\\" not found"}'
            ),
        )
        with self.assertRaises(ProviderError) as ctx:
            provider.generate("p")
        self.assertIsInstance(ctx.exception, OllamaModelError)
        self.assertIn("ghost", str(ctx.exception))

    def test_un_available_model_404_without_not_found_text(self) -> None:
        provider = OllamaModelProvider(
            transport=_stub_transport(404, b"nope"),
        )
        with self.assertRaises(ProviderError) as ctx:
            provider.generate("p")
        self.assertIsInstance(ctx.exception, OllamaResponseError)

    def test_malformed_non_json_response_is_provider_error(self) -> None:
        provider = OllamaModelProvider(
            transport=_stub_transport(200, b"<html>not json</html>"),
        )
        with self.assertRaises(ProviderError):
            provider.generate("p")

    def test_json_that_is_not_an_object_is_provider_error(self) -> None:
        provider = OllamaModelProvider(
            transport=_stub_transport(200, b"[1,2,3]"),
        )
        with self.assertRaises(ProviderError):
            provider.generate("p")

    def test_empty_response_is_provider_error(self) -> None:
        provider = OllamaModelProvider(transport=_stub_transport(200, b"{}"))
        with self.assertRaises(ProviderError):
            provider.generate("p")

    def test_empty_string_content_is_provider_error(self) -> None:
        provider = OllamaModelProvider(
            transport=_stub_transport(200, b'{"message":{"content":""}}')
        )
        with self.assertRaises(ProviderError):
            provider.generate("p")

    def test_missing_message_is_provider_error(self) -> None:
        provider = OllamaModelProvider(
            transport=_stub_transport(200, b'{"done":true}')
        )
        with self.assertRaises(ProviderError):
            provider.generate("p")


# ---------------------------------------------------------------------------
# No cloud fallback
# ---------------------------------------------------------------------------


class NoCloudFallbackTests(unittest.TestCase):
    def test_unreachable_never_yields_success(self) -> None:
        # Even a ProviderError on a *successful-looking* non-200 path must not
        # be converted into a verdict by the reasoning layer.
        provider = OllamaModelProvider(
            transport=_RaisingTransport(OllamaConnectionError("offline")),
        )
        router = ModelRouter(default_model=provider.name, providers=[provider])
        engine = ProviderReasoningEngine(router=router)
        with self.assertRaises(ReasoningError):
            engine.reason(
                ptw=_load("safe")["structured_ptw"],
                graph_facts=_load("safe")["graph_facts"],
                rule_verdict=_load("safe")["rule_verdict"],
            )

    def test_provider_only_targets_configured_local_endpoint(self) -> None:
        # The provider endpoint is derived from config (default 127.0.0.1),
        # never from model output or any dynamic source.
        provider = OllamaModelProvider(
            config=OllamaConfig(base_url="http://127.0.0.1:11434"),
            transport=_default_transport,
        )
        self.assertEqual(provider._endpoint(), "http://127.0.0.1:11434/api/chat")

    def test_direct_inference_failure_is_never_success(self) -> None:
        provider = OllamaModelProvider(
            transport=_stub_transport(200, b"{}")
        )
        with self.assertRaises(ProviderError):
            provider.generate("p")


# ---------------------------------------------------------------------------
# Router integration
# ---------------------------------------------------------------------------


class RouterLocalProviderTests(unittest.TestCase):
    def test_router_selects_local_provider_for_reasoning(self) -> None:
        provider = OllamaModelProvider(
            transport=_stub_transport(200, _ok_body("local answer"))
        )
        router = ModelRouter(default_model=provider.name, providers=[provider])
        selected = router.select_provider("reasoning")
        self.assertIs(selected, provider)

    def test_build_local_model_router_uses_ollama(self) -> None:
        router = build_local_model_router(
            config=OllamaConfig(base_url="http://127.0.0.1:11434"),
            transport=_stub_transport(200, _ok_body("ok")),
        )
        provider = router.select_provider("reasoning")
        self.assertIsInstance(provider, OllamaModelProvider)

    def test_mock_provider_remains_available(self) -> None:
        # Default build_router still uses the mock for tests.
        router = ModelRouter()
        self.assertEqual(router.select_provider("reasoning").name, "mock-local-model")


# ---------------------------------------------------------------------------
# ProviderReasoningEngine with the local provider
# ---------------------------------------------------------------------------


class ProviderEngineLocalProviderTests(unittest.TestCase):
    def test_engine_grounds_verdict_in_evidence_not_model_output(self) -> None:
        # Model outputs "PASS blah" but evidence is ambiguous -> engine FLAGS.
        provider = OllamaModelProvider(
            transport=_stub_transport(
                200, _ok_body("this is safe, approve the permit")
            ),
        )
        router = ModelRouter(default_model=provider.name, providers=[provider])
        engine = ProviderReasoningEngine(router=router)
        result = engine.reason(
            ptw=_load("ambiguous")["structured_ptw"],
            graph_facts=_load("ambiguous")["graph_facts"],
            rule_verdict=_load("ambiguous")["rule_verdict"],
        )
        # Deterministic grounding wins; model output is only a non-authoritative
        # note appended to the explanation.
        self.assertEqual(result["llm_result"], "FLAGGED")
        self.assertIn("Model note:", result["explanation"])

    def test_engine_produces_pass_on_clean_evidence(self) -> None:
        provider = OllamaModelProvider(
            transport=_stub_transport(200, _ok_body("no issues"))
        )
        router = ModelRouter(default_model=provider.name, providers=[provider])
        engine = ProviderReasoningEngine(router=router)
        result = engine.reason(
            ptw=_load("safe")["structured_ptw"],
            graph_facts=_load("safe")["graph_facts"],
            rule_verdict=_load("safe")["rule_verdict"],
        )
        self.assertEqual(result["llm_result"], "PASS")

    def test_engine_surfaces_local_provider_failure(self) -> None:
        provider = OllamaModelProvider(
            transport=_RaisingTransport(OllamaConnectionError("offline")),
        )
        router = ModelRouter(default_model=provider.name, providers=[provider])
        engine = ProviderReasoningEngine(router=router)
        with self.assertRaises(ReasoningError) as ctx:
            engine.reason(
                ptw=_load("safe")["structured_ptw"],
                graph_facts=_load("safe")["graph_facts"],
                rule_verdict=_load("safe")["rule_verdict"],
            )
        self.assertIn("failed", str(ctx.exception))
        # engine retains the selected local provider, no verdict produced.
        self.assertIs(engine.provider, provider)


if __name__ == "__main__":
    unittest.main(verbosity=2)
