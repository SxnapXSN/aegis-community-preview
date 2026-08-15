"""Validated task envelopes with intentionally conservative planning rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


class TaskValidationError(ValueError):
    """Raised when a task envelope does not meet the public contract."""


_RISK_LEVELS = {"low", "medium", "high"}


def _required_text(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise TaskValidationError(f"{field} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True)
class TaskEnvelope:
    """A local task description that never grants execution capability."""

    task_id: str
    title: str
    objective: str
    risk_level: str
    allowed_actions: tuple[str, ...]

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "TaskEnvelope":
        if not isinstance(payload, Mapping):
            raise TaskValidationError("task envelope must be a JSON object")

        risk_level = _required_text(payload, "risk_level").lower()
        if risk_level not in _RISK_LEVELS:
            expected = ", ".join(sorted(_RISK_LEVELS))
            raise TaskValidationError(f"risk_level must be one of: {expected}")

        raw_actions = payload.get("allowed_actions")
        if not isinstance(raw_actions, list) or not raw_actions:
            raise TaskValidationError("allowed_actions must be a non-empty array")

        actions = tuple(
            action.strip() if isinstance(action, str) else "" for action in raw_actions
        )
        if any(not action for action in actions):
            raise TaskValidationError("allowed_actions must contain non-empty strings")

        return cls(
            task_id=_required_text(payload, "task_id"),
            title=_required_text(payload, "title"),
            objective=_required_text(payload, "objective"),
            risk_level=risk_level,
            allowed_actions=actions,
        )


def build_execution_brief(task: TaskEnvelope) -> dict[str, Any]:
    """Return a non-executing plan that preserves human control for risky work."""

    requires_human_review = task.risk_level == "high"
    return {
        "task_id": task.task_id,
        "title": task.title,
        "objective": task.objective,
        "risk_level": task.risk_level,
        "status": "requires_human_review" if requires_human_review else "ready_for_review",
        "requires_human_review": requires_human_review,
        "enabled_actions": [] if requires_human_review else list(task.allowed_actions),
        "notice": (
            "This preview produces a plan only; it never executes actions."
            if not requires_human_review
            else "High-risk task: a human must review before any action is considered."
        ),
    }
