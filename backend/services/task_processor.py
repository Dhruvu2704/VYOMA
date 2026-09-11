"""Task processing bridge.

The backend orchestrates the life of a task:
CREATED -> PROCESSING -> COMPLETED / FAILED.

Every processing run hands the submitted contract envelope to the existing
KAVACH AgentOrchestrator and persists its authoritative result. No safety
decision is computed here.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from backend.config import OUTPUT_DIR
from backend.db.models import Deliverable, Permit, Task, Verdict
from backend.services.audit_logger import AuditLogger
from backend.services.kavach import KavachConnector
from backend.services.overlap import (
    build_overlap_check,
    permit_to_active_permit,
)


class TaskProcessingError(Exception):
    """Raised when processing cannot be driven to a KAVACH verdict."""


def _resolve_task_id(task_id: str) -> int:
    if not task_id.startswith("TASK-"):
        raise ValueError("Invalid task ID format")
    return int(task_id.replace("TASK-", ""))


def _build_envelope_with_overlap(
    task: Task,
    db,
) -> Dict[str, Any]:
    envelope = json.loads(task.input_json or "{}")
    ptw = envelope.get("structured_ptw")
    if not isinstance(ptw, dict):
        raise TaskProcessingError(
            "Task input has no structured_ptw contract",
        )
    graph_facts = envelope.get("graph_facts")
    if not isinstance(graph_facts, dict):
        graph_facts = {}
        envelope["graph_facts"] = graph_facts
    if not isinstance(graph_facts.get("overlap_check"), dict):
        active_permits = (
            db.query(Permit).filter(Permit.status == "ACTIVE").all()
        )
        graph_facts["overlap_check"] = build_overlap_check(
            ptw,
            [permit_to_active_permit(p) for p in active_permits],
        )
    return envelope


def _persist_result(db, task: Task, result: Dict[str, Any]) -> None:
    final_verdict = result.get("final_verdict") or {}
    audit = result.get("audit") or {}
    stages = audit.get("stages") or {}
    rule_verdict = stages.get("rule_verdict") or {}
    verification = result.get("verification") or {}
    llm_reasoning = result.get("llm_reasoning") or {}

    task.permit_id = result.get("permit_id")
    task.audit_ref = audit.get("audit_ref")
    task.result_json = json.dumps(
        {
            "deterministic_safety_evaluated": bool(
                stages.get("deterministic_safety_evaluated")
            ),
            "rule_result": rule_verdict.get("rule_result"),
            "rules_triggered": rule_verdict.get("rules_triggered"),
            "conflicting_permit_ids": rule_verdict.get(
                "conflicting_permit_ids"
            ),
            "rule_explanation": rule_verdict.get("explanation"),
            "llm_result": llm_reasoning.get("llm_result"),
            "reasoning_provider": stages.get("reasoning_provider"),
            "reasoning_explanation": llm_reasoning.get("explanation"),
            "agreement": verification.get("agreement"),
            "final_decision": final_verdict.get("final_decision"),
            "requires_human_review": final_verdict.get(
                "requires_human_review"
            ),
            "explanation": final_verdict.get("explanation"),
            "generated_at": final_verdict.get("generated_at"),
            "retrieved_context": [
                dict(item)
                for item in (result.get("retrieved_context") or [])
                if isinstance(item, dict)
            ],
        }
    )

    db.add(
        Verdict(
            task_id=task.id,
            final_verdict=json.dumps(final_verdict),
        )
    )

    audit_ref = audit.get("audit_ref")
    if audit_ref:
        AuditLogger().save_event(
            db,
            AuditLogger().create_event(
                audit_ref=audit_ref,
                permit_id=task.permit_id or "",
                timestamp=audit.get("timestamp")
                or datetime.utcnow().isoformat(),
                pipeline=[str(x) for x in (audit.get("pipeline") or [])],
                stages=json.dumps(stages),
                sequence=json.dumps(audit.get("sequence") or []),
            ),
        )

    task.status = "COMPLETED"
    db.commit()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _generate_deliverables(
    db,
    task: Task,
    result: Dict[str, Any],
    output_dir: Optional[str],
) -> None:
    final_verdict = result.get("final_verdict") or {}
    stages = (result.get("audit") or {}).get("stages") or {}
    rule_verdict = stages.get("rule_verdict") or {}

    directory = Path(output_dir or OUTPUT_DIR) / f"task-{task.id:03d}"
    references = []

    if final_verdict:
        try:
            from ai_agent.deliverables.excel_matrix import generate_excel
            from ai_agent.deliverables.word_memo import generate_word

            references.append(
                generate_word(final_verdict, str(directory))
            )
            if rule_verdict:
                references.append(
                    generate_excel(rule_verdict, str(directory))
                )
        except Exception:
            pass

    for reference in references:
        path = Path(reference["path"])
        db.add(
            Deliverable(
                task_id=task.id,
                filename=path.name,
                file_type=reference.get("type"),
                file_path=str(path),
                sha256=_sha256(path),
            )
        )
    db.commit()


def process_task(
    db,
    task: Task,
    connector: KavachConnector,
    output_dir: Optional[str] = None,
) -> Task:
    """Drive a task through KAVACH; the connector decides the verdict."""
    task.status = "PROCESSING"
    db.commit()

    try:
        envelope = _build_envelope_with_overlap(task, db)
        result = connector.run(envelope)
    except Exception as exc:  # noqa: BLE001 - surface as FAILED
        task.status = "FAILED"
        task.error = f"{type(exc).__name__}: {exc}"
        db.commit()
        db.refresh(task)
        return task

    if result.get("failed_stage"):
        task.status = "FAILED"
        task.error = (
            "KAVACH blocked at stage "
            f"{result['failed_stage']}: {result.get('errors')}"
        )
        db.commit()
        db.refresh(task)
        return task

    try:
        _persist_result(db, task, result)
        _generate_deliverables(db, task, result, output_dir)
    except Exception as exc:  # noqa: BLE001 - surface as FAILED
        task.status = "FAILED"
        task.error = f"{type(exc).__name__}: {exc}"
        db.commit()
        db.refresh(task)
        return task

    db.refresh(task)
    return task