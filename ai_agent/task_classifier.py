"""Deterministic task classifier for the Role 1 agent pipeline.

Classifies incoming tasks into one of the known task types without using
any LLM.  The classification drives the planner to produce a relevant
pipeline sequence.

Supported task types
--------------------
- ``ptw_conflict_analysis``  — permit-to-work conflict / overlap analysis
- ``document_question``      — question about a specific document
- ``general_industrial_reasoning`` — general industrial safety reasoning
- ``deliverable_request``    — request to generate a deliverable (report, …)

Security principle: classification is purely rule-based on fixture metadata.
No document content can influence the classification.
"""

from __future__ import annotations

from typing import Any, Dict, FrozenSet

TaskType = str

VALID_TASK_TYPES: FrozenSet[str] = frozenset(
    {
        "ptw_conflict_analysis",
        "document_question",
        "general_industrial_reasoning",
        "deliverable_request",
    }
)


class TaskClassificationError(Exception):
    """Raised when the classifier cannot determine a task type."""


class TaskClassifier:
    """Deterministic, rule-based task classifier for Milestone 1.

    Examines the fixture's ``task_request`` (and optional ``context``) to
    determine the task type.  No LLM is used; classification is entirely
    deterministic.
    """

    def classify(self, fixture: Dict[str, Any]) -> TaskType:
        """Classify the task based on the fixture data.

        Args:
            fixture: The raw fixture dict containing ``task_request`` and
                other data.

        Returns:
            One of the ``VALID_TASK_TYPES`` strings.

        Raises:
            TaskClassificationError: if the fixture cannot be classified.
        """
        task_request = fixture.get("task_request")
        if not isinstance(task_request, dict):
            raise TaskClassificationError(
                "Fixture missing 'task_request'; cannot classify task"
            )

        task_type_raw = str(task_request.get("task_type", "")).strip().lower()
        context = task_request.get("context") or {}

        # --- Explicit, unambiguous task-type mapping -----------------------

        if task_type_raw in ("document_question",):
            return "document_question"

        if task_type_raw in ("deliverable", "deliverable_request"):
            return "deliverable_request"

        # --- Context-based heuristics -------------------------------------
        # Deeper task signals (a specific question, or a requested
        # deliverable) take precedence over a generic ptw_review envelope,
        # so a "ptw_review" task carrying a question is a document question,
        # not a conflict analysis.

        if isinstance(context, dict):
            if context.get("question") or context.get("document_question"):
                return "document_question"
            if context.get("deliverable") or context.get("deliverable_type"):
                return "deliverable_request"

        # --- Permit-review / default mapping -------------------------------

        if task_type_raw in ("ptw_review", "ptw_conflict_analysis"):
            return "ptw_conflict_analysis"

        if task_type_raw in ("general_industrial_reasoning", "general", ""):
            return "general_industrial_reasoning"

        # Unknown but non-empty task_type — still classify as general.
        return "general_industrial_reasoning"
