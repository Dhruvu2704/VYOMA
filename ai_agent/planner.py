"""Classification-aware pipeline planner.

Produces a ``PlanStep`` sequence tailored to the task type.  The plan
determines which stages execute and which tools are invoked.

For Milestone 1 plans are deterministic templates; later, a more dynamic
planner may adjust based on evidence quality or other signals.
"""

from __future__ import annotations

from typing import List, Optional

from shared.contracts import PlanStep

from ai_agent.task_classifier import TaskType
from ai_agent.router.model_router import ModelRouter, build_router


class TaskAwarePlanner:
    """Produces ``PlanStep`` sequences based on task classification."""

    def __init__(self, router: Optional[ModelRouter] = None) -> None:
        self.router = router or build_router()

    def plan(self, task_type: TaskType, permit_id: str) -> List[PlanStep]:
        """Produce a plan appropriate for the given task type.

        Args:
            task_type: One of the ``VALID_TASK_TYPES``.
            permit_id: The permit / task identifier for the plan.

        Returns:
            A list of ``PlanStep`` dicts describing the pipeline sequence.
        """
        if task_type == "ptw_conflict_analysis":
            return self._plan_ptw_conflict(permit_id)
        elif task_type == "document_question":
            return self._plan_document_question(permit_id)
        elif task_type == "deliverable_request":
            return self._plan_deliverable(permit_id)
        else:
            return self._plan_general(permit_id)

    # ------------------------------------------------------------------
    # Task-type specific plans
    # ------------------------------------------------------------------

    def _plan_ptw_conflict(self, permit_id: str) -> List[PlanStep]:
        """Full safety-analysis pipeline: retrieve, conflict-check, reason,
        verify, and produce a verdict."""
        return [
            PlanStep(step="perceive", tool=None, model_category=None, status="done"),
            PlanStep(step="understand", tool=None, model_category=None, status="done"),
            PlanStep(step="plan", tool=None, model_category=None, status="done"),
            PlanStep(
                step="retrieve",
                tool="search_knowledge",
                model_category=None,
                status="planned",
            ),
            PlanStep(
                step="use_tool",
                tool="check_conflict",
                model_category=None,
                status="planned",
            ),
            PlanStep(
                step="reason",
                tool=None,
                model_category=self.router.resolve("reasoning"),
                status="planned",
            ),
            PlanStep(step="verify", tool=None, model_category=None, status="planned"),
            PlanStep(step="act", tool=None, model_category=None, status="planned"),
            PlanStep(
                step="log",
                tool="log_event",
                model_category=None,
                status="planned",
            ),
        ]

    def _plan_document_question(self, permit_id: str) -> List[PlanStep]:
        """Retrieve and reason over document content; no safety verification
        required for a pure question-answering task."""
        return [
            PlanStep(step="perceive", tool=None, model_category=None, status="done"),
            PlanStep(step="understand", tool=None, model_category=None, status="done"),
            PlanStep(step="plan", tool=None, model_category=None, status="done"),
            PlanStep(
                step="retrieve",
                tool="search_knowledge",
                model_category=None,
                status="planned",
            ),
            PlanStep(
                step="use_tool",
                tool="search_knowledge",
                model_category=None,
                status="planned",
            ),
            PlanStep(
                step="reason",
                tool=None,
                model_category=self.router.resolve("reasoning"),
                status="planned",
            ),
            PlanStep(step="act", tool=None, model_category=None, status="planned"),
            PlanStep(
                step="log",
                tool="log_event",
                model_category=None,
                status="planned",
            ),
        ]

    def _plan_deliverable(self, permit_id: str) -> List[PlanStep]:
        """Retrieve, reason, and generate a deliverable (Word / Excel / PDF)."""
        return [
            PlanStep(step="perceive", tool=None, model_category=None, status="done"),
            PlanStep(step="understand", tool=None, model_category=None, status="done"),
            PlanStep(step="plan", tool=None, model_category=None, status="done"),
            PlanStep(
                step="retrieve",
                tool="search_knowledge",
                model_category=None,
                status="planned",
            ),
            PlanStep(
                step="use_tool",
                tool="generate_word",
                model_category=None,
                status="planned",
            ),
            PlanStep(
                step="reason",
                tool=None,
                model_category=self.router.resolve("reasoning"),
                status="planned",
            ),
            PlanStep(step="act", tool=None, model_category=None, status="planned"),
            PlanStep(
                step="log",
                tool="log_event",
                model_category=None,
                status="planned",
            ),
        ]

    def _plan_general(self, permit_id: str) -> List[PlanStep]:
        """General industrial reasoning: retrieve, reason, and act."""
        return [
            PlanStep(step="perceive", tool=None, model_category=None, status="done"),
            PlanStep(step="understand", tool=None, model_category=None, status="done"),
            PlanStep(step="plan", tool=None, model_category=None, status="done"),
            PlanStep(
                step="retrieve",
                tool="search_knowledge",
                model_category=None,
                status="planned",
            ),
            PlanStep(
                step="reason",
                tool=None,
                model_category=self.router.resolve("reasoning"),
                status="planned",
            ),
            PlanStep(step="act", tool=None, model_category=None, status="planned"),
            PlanStep(
                step="log",
                tool="log_event",
                model_category=None,
                status="planned",
            ),
        ]
