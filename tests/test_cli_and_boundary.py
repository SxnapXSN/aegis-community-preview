from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from aegis_community.cli import main
from scripts.verify_preview_boundary import find_violations


class CliAndBoundaryTests(unittest.TestCase):
    def test_cli_prints_a_valid_execution_brief(self) -> None:
        payload = {
            "task_id": "cli-1",
            "title": "Review draft",
            "objective": "Prepare a local review brief.",
            "risk_level": "medium",
            "allowed_actions": ["prepare_review"],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "task.json"
            input_path.write_text(json.dumps(payload), encoding="utf-8")
            output = io.StringIO()

            with redirect_stdout(output):
                exit_code = main(["--input", str(input_path)])

        brief = json.loads(output.getvalue())
        self.assertEqual(0, exit_code)
        self.assertEqual("cli-1", brief["task_id"])
        self.assertEqual("ready_for_review", brief["status"])

    def test_boundary_checker_flags_environment_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".env").write_text("EXAMPLE=value\n", encoding="utf-8")

            violations = find_violations(root)

        self.assertIn("environment file: .env", violations)

    def test_boundary_checker_flags_unapproved_source_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            private_module = root / "aegis_core"
            private_module.mkdir()
            (private_module / "internal.py").write_text("value = 1\n", encoding="utf-8")

            violations = find_violations(root)

        self.assertIn(
            "path is outside the public allow-list: aegis_core\\internal.py",
            violations,
        )
