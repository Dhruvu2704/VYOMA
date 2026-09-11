"""Configuration for the VYOMA Role 1 agent.

Day 3: centralises configuration for the local (Ollama) model integration so
the reasoning model name and endpoint are not hardcoded throughout the
application. All values have sensible local-development defaults and can be
overridden via environment variables.

Nothing here downloads or installs a model; it only describes how to reach a
local endpoint that the operator is expected to provide.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


# Environment variable names (single source of truth).
ENV_OLLAMA_BASE_URL = "VYOMA_OLLAMA_BASE_URL"
ENV_OLLAMA_MODEL = "VYOMA_OLLAMA_MODEL"
ENV_OLLAMA_TIMEOUT = "VYOMA_OLLAMA_TIMEOUT"


@dataclass(frozen=True)
class OllamaConfig:
    """Configuration for the local Ollama model endpoint.

    Attributes:
        base_url: Base URL of the local Ollama HTTP endpoint
            (e.g. ``http://127.0.0.1:11434``, no trailing slash).
        model: The reasoning model name served by Ollama.
        timeout: Request timeout in seconds.
    """

    base_url: str = "http://127.0.0.1:11434"
    model: str = "llama3"
    # Full-context reasoning against the local model commonly runs ~50s
    # (or longer when the model is cold-loaded); 60s was too tight and
    # caused spurious OllamaTimeoutError failures of the reason stage.
    timeout: float = 300.0


def load_ollama_config(
    *,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    timeout: Optional[float] = None,
    environ: Optional[dict] = None,
) -> OllamaConfig:
    """Build an ``OllamaConfig``.

    Resolution order (highest priority first):
      1. Explicit keyword arguments.
      2. Environment variables (see ``ENV_OLLAMA_*``).
      3. Sensible local-development defaults (``OllamaConfig`` defaults).

    Args:
        base_url: Override for the endpoint base URL.
        model: Override for the reasoning model name.
        timeout: Override for the request timeout (seconds).
        environ: Environment mapping to read from (defaults to ``os.environ``).
    """
    env = dict(os.environ if environ is None else environ)

    resolved_base = base_url or env.get(ENV_OLLAMA_BASE_URL)
    resolved_model = model or env.get(ENV_OLLAMA_MODEL)
    raw_timeout = timeout if timeout is not None else env.get(ENV_OLLAMA_TIMEOUT)

    default = OllamaConfig()
    base = resolved_base.rstrip("/") if resolved_base else default.base_url
    resolved_timeout: float = default.timeout
    if raw_timeout is not None:
        try:
            resolved_timeout = float(raw_timeout)
        except (TypeError, ValueError):
            resolved_timeout = default.timeout
    return OllamaConfig(
        base_url=base,
        model=resolved_model or default.model,
        timeout=resolved_timeout,
    )
