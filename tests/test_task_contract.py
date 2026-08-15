from __future__ import annotations

import unittest

from aegis_community.task_contract import (
    TaskEnvelope,
    TaskValidationError,
    build_execution_brief,
)


class TaskContractTests(unittest.TestCase):
    def test_low_risk_task_is_ready_for_review(self) -> None:
        task = TaskEnvelope.from_mapping(
            {
                "task_id": "task-1",
                "title": "Document a feature",
                "objective": "Write a short technical outline.",
                "risk_level": "low",
                "allowed_actions": ["draft_outline"],
            }
        )

        brief = build_execution_brief(task)

        self.assertEqual("ready_for_review", brief["status"])
        self.assertFalse(brief["requires_human_review"])
        self.assertEqual(["draft_outline"], brief["enabled_actions"])

    def test_high_risk_task_requires_human_review(self) -> None:
        task = TaskEnvelope.from_mapping(
            {
                "task_id": "task-2",
                "title": "Review deployment change",
                "objective": "Assess a potentially impactful change.",
                "risk_level": "high",
                "allowed_actions": ["prepare_review"],
            }
        )

        brief = build_execution_brief(task)

        self.assertEqual("requires_human_review", brief["status"])
        self.assertTrue(brief["requires_human_review"])
        self.assertEqual([], brief["enabled_actions"])

    def test_rejects_invalid_risk_level(self) -> None:
        with self.assertRaisesRegex(TaskValidationError, "risk_level"):
            TaskEnvelope.from_mapping(
                {
                    "task_id": "task-3",
                    "title": "Invalid task",
                    "objective": "Check validation.",
                    "risk_level": "critical",
                    "allowed_actions": ["review"],
                }
            )

    def test_rejects_empty_actions(self) -> None:
        with self.assertRaisesRegex(TaskValidationError, "allowed_actions"):
            TaskEnvelope.from_mapping(
                {
                    "task_id": "task-4",
                    "title": "Invalid task",
                    "objective": "Check validation.",
                    "risk_level": "medium",
                    "allowed_actions": [],
                }
            )
