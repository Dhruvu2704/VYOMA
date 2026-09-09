"""Executable fixture runner for the VYOMA integrated Role 1 + Role 3 pipeline.

Runs ANY existing fixture JSON (e.g. ``ai_agent/fixtures/conflict_case.json``)
end-to-end through the real integrated pipeline:

    StructuredPTW + StructuredPID
        -> USE TOOL  (Role 3 deterministic plant-safety)
        -> RuleVerdict
        -> REASON    (local Ollama model, independent reasoning)
        -> VERIFY    (deterministic RuleVerdict vs reasoning)
        -> ACT       (FinalVerdict)
        -> LOG       (AuditTrace)

The runner uses the SAME orchestrator path as ``smoke_run.py``:
``build_provider_orchestrator(..., plant_safety=True)``.  No parallel pipeline,
no new data format, no cloud.

Usage (from repo root):

    python -m ai_agent.orchestrator.fixture_run ai_agent/fixtures/conflict_case.json

The fixture's ``graph_facts.overlap_check`` is preserved and passed to Role 3
as externally supplied overlap evidence (the Role 4 active-permit layer), so
cross-permit conflicts are detected deterministically.  When the fixture
carries no overlap evidence, Role 3 simply evaluates the submitted evidence
(no invented conflicts).

Safety boundary: the LLM can never override the deterministic verdict.  The
reasoning engine grounds PASS/FLAGGED strictly in the structured evidence and
a disagreement always escalates to DISAGREE / REVIEW_REQUIRED / human review.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from ai_agent.config import load_ollama_config
from ai_agent.orchestrator.orchestrator import load_fixture

USAGE = (
    "usage: python -m ai_agent.orchestrator.fixture_run "
    "<fixture_json_path> [example: ai_agent/fixtures/conflict_case.json]"
)


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def execute_fixture(
    fixture: Dict[str, Any],
    *,
    config: Optional[object] = None,
    transport: Optional[Callable[..., Tuple[int, bytes]]] = None,
    orchestrator: Optional[object] = None,
) -> Dict[str, Any]:
    """Run an existing fixture envelope through the integrated pipeline.

    Builds ``build_provider_orchestrator(..., plant_safety=True)`` (the same
    path as ``smoke_run.py``) unless an explicit ``orchestrator`` is injected.

    The fixture's ``graph_facts.overlap_check`` is preserved automatically:
    the orchestrator reads it from the supplied envelope and passes it to the
    Role 3 pipeline as overlap evidence.

    Args:
        fixture: An existing fixture dict (task_request + structured_ptw +
            structured_pid + optional graph_facts envelope).
        config: ``OllamaConfig``; loaded from environment/defaults if None.
        transport: optional HTTP transport stub (testing only).
        orchestrator: optional pre-built integrated orchestrator (testing).

    Returns:
        The ``OrchestratorResult`` from the existing orchestrator.
    """
    if orchestrator is None:
        from ai_agent.orchestrator.orchestrator import build_provider_orchestrator

        cfg = config if config is not None else load_ollama_config()
        orchestrator = build_provider_orchestrator(
            config=cfg, transport=transport, plant_safety=True
        )
    return orchestrator.run(fixture)


def run_fixture_path(
    path: str | Path,
    *,
    config: Optional[object] = None,
    transport: Optional[Callable[..., Tuple[int, bytes]]] = None,
    orchestrator: Optional[object] = None,
) -> Dict[str, Any]:
    """Load and run a fixture file through the integrated pipeline."""
    return execute_fixture(
        load_fixture(path),
        config=config,
        transport=transport,
        orchestrator=orchestrator,
    )


# ---------------------------------------------------------------------------
# Summary output
# ---------------------------------------------------------------------------


def _value(value: Any, default: str = "n/a") -> str:
    return default if value is None else str(value)


def print_summary(
    result: Dict[str, Any],
    scenario: str,
    source: str,
) -> None:
    """Print a concise, human-readable execution summary.

    All deterministic values come from the audit trace (Role 3 output), and
    all reasoning/verification values come from the existing contracts.
    """
    stages: Dict[str, Any] = (result.get("audit") or {}).get("stages") or {}
    verdict: Dict[str, Any] = stages.get("rule_verdict") or {}
    verification: Dict[str, Any] = result.get("verification") or {}
    final_verdict: Dict[str, Any] = result.get("final_verdict") or {}

    print("-" * 64)
    print("VYOMA INTEGRATED FIXTURE RUN")
    print("-" * 64)
    print(f"fixture                     : {Path(source).as_posix()}")
    print(f"scenario                    : {scenario}")
    print(f"permit_id                   : {_value(result.get('permit_id'))}")
    print(f"deterministic safety eval.  : {stages.get('deterministic_safety_evaluated', False)}")
    print(f"deterministic rule_result   : {_value(verdict.get('rule_result'))}")
    print(f"rules_triggered             : {_value(verdict.get('rules_triggered'))}")
    print(f"conflicting_permit_ids      : {_value(verdict.get('conflicting_permit_ids'))}")
    print(f"model provider              : {_value(stages.get('reasoning_provider'))}")
    print(f"reasoning result            : {_value(result.get('llm_reasoning', {}).get('llm_result'))}")
    print(f"verification result         : {_value(verification.get('agreement'))}")
    print(f"final decision              : {_value(final_verdict.get('final_decision'))}")
    print(f"human review                : {_value(final_verdict.get('requires_human_review'))}")
    print(f"audit reference             : {_value((result.get('audit') or {}).get('audit_ref'))}")

    if result.get("failed_stage"):
        print("-" * 64)
        print(
            f"RUN BLOCKED AT STAGE {result.get('failed_stage')} "
            f"-> no final verdict produced"
        )
        for err in result.get("errors") or []:
            print(f"  error: [{err.get('error_type')}] {err.get('message')}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point.  Usage:

        python -m ai_agent.orchestrator.fixture_run <fixture_json_path>

    Returns:
        0 on a completed run (even if it ended FLAGGED_FOR_REVIEW).
        2 when the pipeline was blocked by a stage failure (no verdict).
        3 when the fixture path cannot be loaded.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(USAGE, file=sys.stderr)
        return 2

    path = Path(args[0])
    if not path.exists():
        print(f"FIXTURE NOT FOUND: {path}", file=sys.stderr)
        return 3
    try:
        fixture = load_fixture(path)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FIXTURE LOAD FAILED: {exc}", file=sys.stderr)
        return 3

    scenario = str(fixture.get("scenario") or path.stem)
    result = execute_fixture(fixture)
    print_summary(result, scenario, str(path))

    if result.get("failed_stage"):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())