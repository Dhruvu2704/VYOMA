"""Deterministic safety-rule evaluator for the VYOMA pipeline.

Pipeline position::

    GraphFacts
        ↓
    Safety Rules
        ↓
    RuleVerdict

Consumes :class:`~shared.contracts.GraphFacts`-compatible dicts and
(optional) :class:`~shared.contracts.StructuredPTW`-compatible dicts.
Produces a :class:`~shared.contracts.RuleVerdict`-compatible dict.

All evaluation is purely deterministic.  No LLM, no randomness, no
timestamps generated at evaluation time, no external calls.  The same
inputs always produce the same output.  Inputs are never mutated.
"""

from __future__ import annotations

from typing import Any, Dict, List

from shared.contracts import RuleVerdict


# ---------------------------------------------------------------------------
# Rule identifiers — match existing fixture/repository conventions
# ---------------------------------------------------------------------------

UNRESOLVED_TAGS = "unresolved-tags"
PERMIT_CONFLICT = "permit-conflict"
HOT_WORK_OVERLAP = "hot-work-overlap"
ISOLATION_OVERLAP_TIME_WINDOW = "isolation-overlap-time-window"
NO_CONFLICT = "no-conflict"
TAGS_RESOLVED = "tags-resolved"
SUBMITTED_TAGS_CLEAN = "submitted-tags-clean"

# Ordered list of deterministic rule identifiers for deterministic iteration.
_RULE_ORDER: List[str] = [
    UNRESOLVED_TAGS,
    PERMIT_CONFLICT,
    HOT_WORK_OVERLAP,
    ISOLATION_OVERLAP_TIME_WINDOW,
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def evaluate(
    graph_facts: Dict[str, Any],
    ptw: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Evaluate deterministic safety rules and return a RuleVerdict dict.

    Args:
        graph_facts: A :class:`~shared.contracts.GraphFacts`-compatible dict
            containing topology, resolution, and overlap evidence.
        ptw: Optional :class:`~shared.contracts.StructuredPTW`-compatible
            dict.  When supplied, ``work_type`` is used for the hot-work
            overlap rule.

    Returns:
        A dict matching the :class:`~shared.contracts.RuleVerdict` shape.

    Raises:
        TypeError: if *graph_facts* is not a dict.
    """
    if not isinstance(graph_facts, dict):
        raise TypeError("graph_facts must be a dict")

    if not isinstance(ptw, dict):
        ptw = {}

    permit_id = _permit_id(graph_facts, ptw)
    overlapping = _overlapping_permits(graph_facts)
    active_isolations = _active_isolations(graph_facts)
    unresolved = _unresolved_tags(graph_facts)
    work_type = _work_type(ptw)

    triggered: List[str] = []
    conflicting_ids: List[str] = []

    _check_unresolved_tags(unresolved, triggered)
    _check_permit_conflict(overlapping, triggered, conflicting_ids)
    _check_hot_work_overlap(work_type, overlapping, triggered, conflicting_ids)
    _check_isolation_overlap(
        overlapping, active_isolations, triggered, conflicting_ids
    )

    conflicting_ids = _dedup_preserve_order(conflicting_ids)
    rule_result = "FLAGGED" if triggered else "PASS"
    confidence = _derive_confidence(triggered, unresolved, overlapping)
    explanation = _build_explanation(
        triggered, conflicting_ids, unresolved, overlapping
    )

    # Append informational (non-flagging) rule identifiers for PASS output.
    if not triggered:
        if unresolved:
            triggered.append(SUBMITTED_TAGS_CLEAN)
        else:
            triggered.append(NO_CONFLICT)
            triggered.append(TAGS_RESOLVED)

    verdict: Dict[str, Any] = {
        "permit_id": permit_id,
        "conflicting_permit_ids": conflicting_ids,
        "rules_triggered": triggered,
        "rule_result": rule_result,
        "explanation": explanation,
        "confidence": confidence,
    }
    return verdict


# ---------------------------------------------------------------------------
# Individual rule checks (pure functions, no side effects)
# ---------------------------------------------------------------------------


def _check_unresolved_tags(
    unresolved: List[str],
    triggered: List[str],
) -> None:
    """Trigger UNRESOLVED_TAGS if any equipment/tag evidence is unresolved."""
    if unresolved:
        triggered.append(UNRESOLVED_TAGS)


def _check_permit_conflict(
    overlapping: List[str],
    triggered: List[str],
    conflicting_ids: List[str],
) -> None:
    """Trigger PERMIT_CONFLICT if overlapping permits are indicated."""
    if overlapping:
        triggered.append(PERMIT_CONFLICT)
        conflicting_ids.extend(overlapping)


def _check_hot_work_overlap(
    work_type: str,
    overlapping: List[str],
    triggered: List[str],
    conflicting_ids: List[str],
) -> None:
    """Trigger HOT_WORK_OVERLAP only when hot-work overlaps an active permit."""
    if work_type == "hot-work" and overlapping:
        triggered.append(HOT_WORK_OVERLAP)
        conflicting_ids.extend(overlapping)


def _check_isolation_overlap(
    overlapping: List[str],
    active_isolations: List[str],
    triggered: List[str],
    conflicting_ids: List[str],
) -> None:
    """Trigger ISOLATION_OVERLAP_TIME_WINDOW for isolation during overlapping window."""
    if overlapping and active_isolations:
        triggered.append(ISOLATION_OVERLAP_TIME_WINDOW)
        conflicting_ids.extend(overlapping)


# ---------------------------------------------------------------------------
# Evidence extractors (read-only, no mutation)
# ---------------------------------------------------------------------------


def _permit_id(graph_facts: Dict[str, Any], ptw: Dict[str, Any]) -> str:
    return graph_facts.get("permit_id") or ptw.get("permit_id") or ""


def _overlapping_permits(graph_facts: Dict[str, Any]) -> List[str]:
    """Extract overlapping permit IDs, preserving first-seen order."""
    overlap = graph_facts.get("overlap_check")
    if not isinstance(overlap, dict):
        return []
    raw = overlap.get("overlapping_permits")
    if not isinstance(raw, list):
        return []
    return list(raw)


def _active_isolations(graph_facts: Dict[str, Any]) -> List[str]:
    raw = graph_facts.get("active_isolations")
    return list(raw) if isinstance(raw, list) else []


def _unresolved_tags(graph_facts: Dict[str, Any]) -> List[str]:
    raw = graph_facts.get("unresolved_tags")
    return list(raw) if isinstance(raw, list) else []


def _work_type(ptw: Dict[str, Any]) -> str:
    raw = ptw.get("work_type")
    return str(raw) if isinstance(raw, str) else ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dedup_preserve_order(items: List[str]) -> List[str]:
    """Deduplicate while preserving first-seen order."""
    seen: set = set()
    out: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _derive_confidence(
    triggered: List[str],
    unresolved: List[str],
    overlapping: List[str],
) -> str:
    """Derive a deterministic confidence label from available evidence.

    Confidence conventions follow the existing fixture/repository pattern:

    * HIGH — concrete deterministic evidence of conflict or flag.
    * MEDIUM — partial evidence: overlapping permits exist but the
      submitted tag list itself is clean.
    * LOW — insufficient evidence: unresolved tags and/or P&ID symbols
      mean the system cannot fully verify safety.

    The label is chosen based on what the evidence provides, not on
    what is missing.  ``triggered`` may be empty before this is called
    when building the PASS path; this is handled correctly.
    """
    if unresolved:
        return "LOW"

    if overlapping:
        return "HIGH"

    if not triggered:
        return "HIGH"

    return "MEDIUM"


def _build_explanation(
    triggered: List[str],
    conflicting_ids: List[str],
    unresolved: List[str],
    overlapping: List[str],
) -> str:
    """Build a deterministic explanation string from evaluated evidence.

    All values come from the inputs.  No external text or timestamps are
    generated.  The wording is stable and deterministic.
    """
    parts: List[str] = []

    if UNRESOLVED_TAGS in triggered:
        count = len(unresolved)
        tags_str = ", ".join(unresolved)
        parts.append(
            f"{count} required equipment/tag reference(s) could not be "
            f"resolved (unresolved equipment/tag evidence): {tags_str}"
        )

    if PERMIT_CONFLICT in triggered:
        ids_str = ", ".join(conflicting_ids)
        parts.append(
            f"Permit {ids_str} conflicts with active permit(s) "
            f"in the same operational window"
        )

    if HOT_WORK_OVERLAP in triggered:
        ids_str = ", ".join(conflicting_ids)
        parts.append(
            f"Hot work overlaps with conflicting permit(s) "
            f"{ids_str} in the same area"
        )

    if ISOLATION_OVERLAP_TIME_WINDOW in triggered:
        ids_str = ", ".join(conflicting_ids)
        parts.append(
            f"Active isolation(s) overlap the time window of "
            f"conflicting permit(s) {ids_str}"
        )

    if not parts:
        parts.append(
            "All equipment tags resolved, no overlapping permits "
            "in the same area, and no active isolations conflict"
        )

    return ". ".join(parts) + "."


def _deduplicate(items: List[str]) -> List[str]:
    """Deduplicate while preserving first-seen order."""
    seen: set = set()
    out: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out
