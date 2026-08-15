"""Local-only task-contract utilities for the Aegis Community Preview."""

from .task_contract import TaskEnvelope, TaskValidationError, build_execution_brief

__all__ = ["TaskEnvelope", "TaskValidationError", "build_execution_brief"]
