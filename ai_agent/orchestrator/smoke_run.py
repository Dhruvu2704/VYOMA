"""Manual smoke-run path for the VYOMA Role 1 local model pipeline.

Executes ONE harmless industrial reasoning example end-to-end through the real
local pipeline:

    Task -> Classifier -> Planner -> ModelRouter -> OllamaModelProvider
    -> LOCAL OLLAMA MODEL -> ProviderReasoningEngine -> Verification
    -> FinalVerdict -> ExecutionTrace / AuditEvent

It uses the fixture/mock structured evidence already present in the repository
(``ai_agent/fixtures/safe_case.json``) and does NOT invent new safety rules or
claim actual plant safety conclusions.

The run is a demonstration that the local reasoning pipeline works; the
authoritative PASS/FLAGGED judgement is always grounded in the supplied
deterministic evidence, never in arbitrary model text.

Usage (from repo root):

    python -m ai_agent.orchestrator.smoke_run

Environment:

    VYOMA_OLLAMA_BASE_URL  (default http://127.0.0.1:11434)
    VYOMA_OLLAMA_MODEL     (default llama3)
    VYOMA_OLLAMA_TIMEOUT   (default 60.0)

Does not install Ollama, download models, or contact any external endpoint.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

from ai_agent.config import load_ollama_config
from ai_agent.orchestrator.orchestrator import AgentOrchestrator, load_fixture
from ai_agent.reasoning.reasoning_engine import ReasoningError


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURES_DIR = REPO_ROOT / "ai_agent" / "fixtures"

SMOKE_FIXTURE = "safe_case.json"

SMOKE_TASK = (
    "Analyze the supplied permit evidence and explain whether the available "
    "evidence indicates a conflict requiring human review."
)


def _print_banner() -> None:
    print("=" * 64)
    print("VYOMA Role 1 -- LOCAL MODEL SMOKE RUN (harmless example)")
    print("=" * 64)


def _print_stage(label: str, detail: str = "") -> None:
    print(f"[{label}] {detail}")


def run_smoke() -> Dict[str, Any]:
    """Run the local pipeline against the safe fixture and return the result."""
    cfg = load_ollama_config()
    _print_banner()
    _print_stage("CONFIG", f"base_url={cfg.base_url} model={cfg.model} timeout={cfg.timeout}")
    _print_stage("TASK", SMOKE_TASK)

    fixture_path = FIXTURES_DIR / SMOKE_FIXTURE
    if not fixture_path.exists():
        raise FileNotFoundError(f"Missing smoke fixture: {fixture_path}")

    fixture = load_fixture(fixture_path)

    from ai_agent.orchestrator.orchestrator import build_provider_orchestrator

    orchestrator = build_provider_orchestrator(config=cfg)

    print("-" * 64)
    print("Pipeline stages:")
    for stage in AgentOrchestrator.PIPELINE_STAGES:
        _print_stage(stage.upper(), "->")

    result = orchestrator.run(fixture)
    if result.get("failed_stage"):
        _print_stage(
            "REASONING BLOCKED",
            f"stage={result.get('failed_stage')} errors={result.get('errors')}",
        )
        raise ReasoningError(
            f"Local model unavailable; stage failed: {result.get('failed_stage')}"
        )

    _print_stage("MODEL RESPONSE", _describe_reasoning(result))
    _print_stage(
        "REASONING COMPLETED",
        (result.get("llm_reasoning") or {}).get("llm_result"),
    )
    _print_stage(
        "VERIFICATION COMPLETED",
        (result.get("verification") or {}).get("agreement"),
    )
    _print_stage(
        "FINAL VERDICT CREATED",
        (result.get("final_verdict") or {}).get("final_decision"),
    )
    _print_stage(
        "AUDIT TRACE CREATED",
        (result.get("audit") or {}).get("audit_ref"),
    )
    return result


def _describe_reasoning(result: Dict[str, Any]) -> str:
    reasoning = result.get("llm_reasoning") or {}
    explanation = reasoning.get("explanation") or ""
    provider = result.get("audit", {}).get("stages", {}).get("reasoning_provider")
    parts: list[str] = []
    if provider:
        parts.append(f"provider={provider}")
    note = _extract_model_note(explanation)
    if note:
        parts.append(f"note={note!r}")
    return ", ".join(parts) if parts else "no model note"


def _extract_model_note(explanation: str) -> str:
    """Pull the non-authoritative model note out of the explanation, if any."""
    marker = "Model note:"
    if marker in explanation:
        return explanation.split(marker, 1)[1].strip()
    return ""


def main() -> int:
    try:
        run_smoke()
        print("-" * 64)
        print("SMOKE RUN COMPLETED")
        return 0
    except ReasoningError as exc:
        print(f"SMOKE RUN BLOCKED: reasoning provider failed: {exc}")
        print("Confirm Ollama is running and the configured model is available.")
        return 2
    except Exception as exc:  # noqa: BLE001 - manual smoke script
        print(f"SMOKE RUN FAILED: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())