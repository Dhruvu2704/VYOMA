"""Real local-model provider backed by Ollama's local HTTP interface.

This provider talks ONLY to a local Ollama endpoint and performs pure model
inference. It contains no safety-verdict logic and wires in no cloud/remote AI
endpoint (no OpenAI, Gemini, Anthropic, Azure, or remote HuggingFace API).

The provider implements the clean ``ModelProvider`` interface from
``model_provider.py`` so the router and provider-backed reasoning engine can
use it exactly like the mock provider.

Design / isolation:

- The HTTP transport is isolated behind ``transport`` (a callable) with a
  default standard-library implementation. Tests inject a stub transport, so
  the unit suite never requires a running Ollama server and never touches the
  network.
- Every failure (connection refused, timeout, HTTP error, malformed JSON,
  empty/missing model output, model-not-found) is surfaced as a
  ``ProviderError``. A failure is never turned into a successful
  ``ModelResponse``.
- Treat the model's output as untrusted data: returned only as ``content``,
  never executed or treated as instructions.

Security:
- The base URL is taken from configuration (default ``127.0.0.1``); the
  provider never performs dynamic/surprise URL fetching — the endpoint is a
  fixed configured value, not derived from model output.
- No shell execution, no remote command execution.
"""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    List,
    Optional,
    Tuple,
)

from ai_agent.config import OllamaConfig, load_ollama_config
from ai_agent.router.model_provider import (
    ModelProvider,
    ModelResponse,
    ProviderError,
)


class _OllamaError(ProviderError):
    """Base for Ollama-specific provider failures carrying diagnostic detail."""

    def __init__(self, message: str, *, detail: Optional[str] = None) -> None:
        super().__init__(message)
        self.detail = detail


class OllamaResponseError(_OllamaError):
    """Raised when Ollama replies with a non-2xx HTTP status."""


class OllamaTimeoutError(_OllamaError):
    """Raised when an inference request to Ollama times out."""


class OllamaConnectionError(_OllamaError):
    """Raised when the local Ollama endpoint cannot be reached."""


class OllamaModelError(_OllamaError):
    """Raised when the requested model is unavailable."""


# A transport callable: performs a single POST request and returns
# (http_status, body_bytes). Raising is allowed and handled by the provider.
HTTPTransport = Callable[[str, bytes, Dict[str, str], float], Tuple[int, bytes]]

# Local Ollama status-probe timeout: checks reachability only, unlike
# full-context inference which uses the configured (larger) timeout.
_LOCAL_MODELS_TIMEOUT_S = 3.0

# A GET transport for the read-only model-list probe.
ModelsGetTransport = Callable[[str, float], Tuple[int, bytes]]


def _default_get_models(url: str, timeout: float) -> Tuple[int, bytes]:
    """Standard-library GET client for ``list_local_models``."""
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed configured local endpoint
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def list_local_models(
    config: Optional[OllamaConfig] = None,
    *,
    transport: Optional[ModelsGetTransport] = None,
) -> Dict[str, Any]:
    """Best-effort, read-only listing of models installed on local Ollama.

    Returns ``{"status": "online", "models": [...], "detail": None}`` on a
    successful probe and ``{"status": "unreachable", "models": [],
    "detail": ...}`` on any failure. Never raises and never fabricates model
    names. ``transport`` is injectable for tests; it defaults to a local-only
    standard-library client.
    """
    cfg = config or load_ollama_config()
    url = f"{cfg.base_url.rstrip('/')}/api/tags"
    do_get = transport or _default_get_models
    try:
        status, body = do_get(url, _LOCAL_MODELS_TIMEOUT_S)
    except Exception as exc:  # noqa: BLE001 - any failure means unreachable
        return {
            "status": "unreachable",
            "models": [],
            "detail": f"{type(exc).__name__}: {exc}",
        }
    if status != 200:
        return {
            "status": "unreachable",
            "models": [],
            "detail": f"Ollama responded with HTTP {status}",
        }

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        return {
            "status": "unreachable",
            "models": [],
            "detail": f"{type(exc).__name__}: {exc}",
        }

    names: List[str] = []
    entries = payload.get("models") if isinstance(payload, dict) else None
    if isinstance(entries, list):
        for entry in entries:
            name = entry.get("name") if isinstance(entry, dict) else None
            if name:
                names.append(str(name))
    return {"status": "online", "models": sorted(names), "detail": None}


def _default_transport(
    url: str, data: bytes, headers: Dict[str, str], timeout: float
) -> Tuple[int, bytes]:
    """Standard-library HTTP client isolated for testability.

    Maps transport-level failures to the provider's typed errors so the public
    contract is consistent:

    - timeout / ``socket.timeout`` -> ``OllamaTimeoutError``
    - connection refusal / ``URLError`` / connection ``OSError`` ->
      ``OllamaConnectionError``
    - a raised ``ProviderError`` is passed through unchanged.
    """
    request = urllib.request.Request(
        url, data=data, headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed configured local endpoint
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read()
        return exc.code, body
    except (socket.timeout, TimeoutError) as exc:
        raise OllamaTimeoutError(
            f"Ollama request timed out after {timeout}s ({url}).", detail=str(exc)
        ) from exc
    except ProviderError:
        raise
    except (urllib.error.URLError, OSError) as exc:
        raise OllamaConnectionError(
            f"Could not connect to Ollama at {url}: {exc}", detail=str(exc)
        ) from exc


class OllamaModelProvider(ModelProvider):
    """Local Ollama-backed ``ModelProvider``.

    Args:
        config: ``OllamaConfig``; if ``None`` it is loaded from environment
            variables / defaults.
        transport: HTTP transport callable used for tests (see
            ``HTTPTransport``). Defaults to the standard-library client.
    """

    def __init__(
        self,
        config: Optional[OllamaConfig] = None,
        transport: Optional[HTTPTransport] = None,
    ) -> None:
        self._config: OllamaConfig = config or load_ollama_config()
        self.name = f"ollama:{self._config.model}"
        self.capabilities: FrozenSet[str] = frozenset({"reasoning"})
        self._transport: HTTPTransport = transport or _default_transport
        self.last_payload: Optional[dict] = None

    @property
    def config(self) -> OllamaConfig:
        """The configuration this provider is bound to."""
        return self._config

    def __repr__(self) -> str:  # pragma: no cover - convenience only
        return (
            f"OllamaModelProvider(base_url={self._config.base_url!r}, "
            f"model={self._config.model!r})"
        )

    def _endpoint(self) -> str:
        return f"{self._config.base_url}/api/chat"

    def _build_payload(
        self,
        prompt: str,
        *,
        capability: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> dict:
        """Build the Ollama ``/api/chat`` request body.

        Only fields supported by Ollama's documented API are serialized:

        - ``model``
        - ``messages``
        - ``stream``

        The VYOMA ``capability`` (``reasoning``, ``vision``, ...) is an
        internal routing concept and is intentionally NOT sent to Ollama. All
        content sent here is untrusted data passed through verbatim.
        """
        chat_messages: List[Dict[str, Any]]
        if messages:
            chat_messages = [dict(m) for m in messages]
        else:
            chat_messages = [{"role": "user", "content": prompt}]
        payload: Dict[str, Any] = {
            "model": self._config.model,
            "messages": chat_messages,
            "stream": False,
        }
        return payload

    def generate(
        self,
        prompt: str,
        *,
        capability: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """Perform inference against the local Ollama endpoint.

        Raises:
            ProviderError: (or a subclass) for any connection, HTTP, timeout,
                model, or malformed-response failure. Never returns a
                successful response for an inference failure.
        """
        payload = self._build_payload(prompt, capability=capability, messages=messages)
        self.last_payload = payload
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        url = self._endpoint()

        try:
            status, raw = self._transport(url, body, headers, self._config.timeout)
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 - surface transport failures
            raise ProviderError(f"Ollama transport failed: {exc}") from exc
        if status != 200:
            detail = _decode_for_diagnostic(raw)
            if "not found" in detail.lower() or "model" in detail.lower():
                raise OllamaModelError(
                    f"Ollama model {self._config.model!r} is unavailable on "
                    f"{self._config.base_url}",
                    detail=detail,
                )
            raise OllamaResponseError(
                f"Ollama returned HTTP {status} for model "
                f"{self._config.model!r} (base_url={self._config.base_url}).",
                detail=_truncate(detail),
            )

        return self._parse_success(raw)

    def _parse_success(self, raw: bytes) -> ModelResponse:
        """Parse a 200 Ollama chat response into a ``ModelResponse``.

        Raises ``ProviderError`` for malformed JSON and missing/empty content.
        """
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderError(
                f"Ollama returned a malformed (non-JSON) response: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise ProviderError("Ollama returned a malformed response (not an object).")

        content = _extract_content(data)
        if content is None:
            raise ProviderError(
                "Ollama returned an empty/missing model response; no content."
            )

        metadata = _extract_metadata(data)
        metadata["provider"] = "ollama"
        metadata["model"] = data.get("model") or self._config.model
        metadata["transport"] = "https"
        if str(self._config.base_url).startswith("http://"):
            metadata["transport"] = "http"

        return ModelResponse(content=content, ok=True, metadata=metadata)


def _extract_content(data: dict) -> Optional[str]:
    """Best-effort content extraction for common Ollama chat shapes."""
    message = data.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content
    # Some endpoints/versions put content at the top level.
    top = data.get("content")
    if isinstance(top, str) and top.strip():
        return top
    # ``done`` may be False only when streaming; a non-streamed reply should
    # carry content. If we reached here there is no usable text.
    return None


def _extract_metadata(data: dict) -> Dict[str, Any]:
    """Pull useful non-authoritative metadata from the Ollama response."""
    meta: Dict[str, Any] = {}
    for key in (
        "model",
        "created_at",
        "total_duration",
        "load_duration",
        "prompt_eval_count",
        "eval_count",
        "eval_duration",
        "done_reason",
    ):
        if key in data:
            meta[key] = data[key]
    return meta


def _decode_for_diagnostic(raw: bytes) -> str:
    try:
        return raw.decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001 - diagnostics only
        return ""


def _truncate(text: str, limit: int = 500) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "..."
