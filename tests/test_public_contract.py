from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aegis_community.manifest import build_manifest
from aegis_community.mcp_server import handle_message
from aegis_community.md import build_md_plan, execute_md, md_status
from aegis_community.preflight import run_preflight
from aegis_community.task_contract import TaskEnvelope, build_execution_brief
from scripts.verify_preview_boundary import find_violations


class PublicContractTests(unittest.TestCase):
    def test_manifest_is_discovery_first_and_privacy_safe(self) -> None:
        manifest = build_manifest()
        encoded = json.dumps(manifest, sort_keys=True)

        self.assertEqual("aegis.manifest/v1", manifest["schema"])
        self.assertEqual("1.1.0", manifest["release"]["version"])
        self.assertEqual(
            [
                "aegis_manifest",
                "aegis_capabilities",
                "aegis_system_map",
                "aegis_preflight",
            ],
            manifest["startup"]["first_calls"],
        )
        self.assertFalse(manifest["privacy"]["addresses_exposed"])
        self.assertFalse(manifest["privacy"]["local_paths_exposed"])
        loopback = ".".join(["127", "0", "0", "1"])
        local_host = "local" + "host"
        self.assertNotIn(loopback, encoded)
        self.assertNotIn(local_host, encoded.lower())

    def test_task_brief_redacts_machine_values(self) -> None:
        local_path = "C:" + "\\" + "private" + "\\" + "draft.txt"
        local_url = "http://" + ".".join(["127", "0", "0", "1"]) + ":8765"
        secret_value = "not-for-output"
        task = TaskEnvelope.from_mapping(
            {
                "task_id": "private-task",
                "title": "Review " + local_path,
                "objective": "Check " + local_url + " and api_key='" + secret_value + "'",
                "risk_level": "low",
                "allowed_actions": ["prepare_review"],
            }
        )

        encoded = json.dumps(build_execution_brief(task), sort_keys=True)

        self.assertIn("[redacted-path]", encoded)
        self.assertIn("[redacted-url]", encoded)
        self.assertNotIn(local_path, encoded)
        self.assertNotIn(local_url, encoded)
        self.assertNotIn(secret_value, encoded)

    def test_mcp_initialize_and_discovery_tools(self) -> None:
        initialized = handle_message(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        )
        listed = handle_message(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        )

        self.assertEqual("aegis-community", initialized["result"]["serverInfo"]["name"])
        names = {tool["name"] for tool in listed["result"]["tools"]}
        self.assertTrue(
            {
                "aegis_manifest",
                "aegis_capabilities",
                "aegis_system_map",
                "aegis_preflight",
                "aegis_plan_task",
                "aegis_md_plan",
                "aegis_document_capability",
                "aegis_document_plan",
                "aegis_document_convert",
                "aegis_context_plan",
                "aegis_context_pack",
            }.issubset(names)
        )

    def test_mcp_plan_tool_is_real_and_non_executing(self) -> None:
        response = handle_message(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "aegis_plan_task",
                    "arguments": {
                        "task_id": "task-1",
                        "title": "Review draft",
                        "objective": "Prepare a local review.",
                        "risk_level": "high",
                        "allowed_actions": ["prepare_review"],
                    },
                },
            }
        )

        result = response["result"]["structuredContent"]
        self.assertFalse(response["result"]["isError"])
        self.assertEqual("requires_human_review", result["status"])
        self.assertEqual("plan_only", result["execution"])
        self.assertEqual([], result["enabled_actions"])

    def test_md_status_hides_configuration_details(self) -> None:
        with patch.dict(
            os.environ,
            {
                "AEGIS_MD_COMMAND": "C:" + "\\" + "private" + "\\" + "md-provider.exe --serve",
                "AEGIS_MD_ROOT": "",
            },
            clear=False,
        ):
            status = md_status()

        encoded = json.dumps(status, sort_keys=True)
        self.assertEqual("ready", status["status"])
        self.assertNotIn("md-provider.exe", encoded.lower())

    def test_md_status_detects_a_colocated_backend_without_returning_its_location(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "aegis_md_adapter.py").write_text("# test adapter\n", encoding="utf-8")
            with patch.dict(
                os.environ,
                {"AEGIS_MD_COMMAND": "", "AEGIS_MD_ROOT": str(root)},
                clear=False,
            ):
                status = md_status()

        encoded = json.dumps(status, sort_keys=True)
        self.assertEqual("ready", status["status"])
        self.assertEqual("local_md_backend", status["source"])
        self.assertNotIn(str(root), encoded)

    def test_md_run_requires_approval(self) -> None:
        with self.assertRaisesRegex(PermissionError, "approval"):
            execute_md({}, approved=False)

    def test_md_run_executes_adapter_and_reads_back_artifact(self) -> None:
        provider = chr(10).join(
            [
                "import json",
                "import pathlib",
                "import sys",
                "request = json.load(sys.stdin)",
                "out = pathlib.Path(request['output_dir']) / ('model.' + request['output_format'])",
                "if request['output_format'] == 'glb':",
                "    chunk = b'{}  '",
                "    out.write_bytes(b'glTF' + (2).to_bytes(4, 'little') + (24).to_bytes(4, 'little') + (4).to_bytes(4, 'little') + b'JSON' + chunk)",
                "else:",
                "    out.write_text('v 0 0 0\\nv 1 0 0\\nv 0 1 0\\nf 1 2 3\\n', encoding='utf-8')",
                "print(json.dumps({'status': 'completed', 'artifact_path': str(out)}))",
            ]
        ) + chr(10)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            provider_path = root / "provider.py"
            image_path = root / "input.png"
            destination = root / "saved.glb"
            provider_path.write_text(provider, encoding="utf-8")
            image_path.write_bytes(b"test image")
            command = json.dumps([sys.executable, str(provider_path)])
            with patch.dict(
                os.environ,
                {
                    "AEGIS_MD_COMMAND": command,
                    "AEGIS_MD_ROOT": "",
                    "AEGIS_MD_AUTO_DISCOVER": "0",
                },
                clear=False,
            ):
                result = execute_md(
                    {
                        "image_path": str(image_path),
                        "output_format": "glb",
                        "quality": "balanced",
                        "output_path": str(destination),
                    },
                    approved=True,
                )
            self.assertTrue(destination.is_file())

        self.assertEqual("completed", result["status"])
        self.assertTrue(result["artifact"]["read_back"])
        self.assertTrue(result["artifact"]["saved"])
        self.assertEqual("model.glb", result["artifact"]["name"])
        self.assertFalse(result["privacy"]["paths_returned"])

    def test_md_plan_rejects_non_boolean_texture_flag(self) -> None:
        with self.assertRaisesRegex(ValueError, "texture"):
            build_md_plan({"texture": "yes"})

    def test_mcp_document_plan_and_conversion_keep_approval_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "notes.txt"
            output = root / "output"
            source.write_text("hello document", encoding="utf-8")
            plan_response = handle_message(
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": "aegis_document_plan",
                        "arguments": {"paths": [str(source)]},
                    },
                }
            )
            self.assertEqual("ready_for_review", plan_response["result"]["structuredContent"]["status"])

            denied = handle_message(
                {
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "tools/call",
                    "params": {
                        "name": "aegis_document_convert",
                        "arguments": {
                            "paths": [str(source)],
                            "output_dir": str(output),
                            "approved": False,
                        },
                    },
                }
            )
            self.assertTrue(denied["result"]["isError"])
            self.assertFalse(output.exists())

            allowed = handle_message(
                {
                    "jsonrpc": "2.0",
                    "id": 6,
                    "method": "tools/call",
                    "params": {
                        "name": "aegis_document_convert",
                        "arguments": {
                            "paths": [str(source)],
                            "output_dir": str(output),
                            "approved": True,
                        },
                    },
                }
            )
            encoded = json.dumps(allowed, sort_keys=True)
            self.assertFalse(allowed["result"]["isError"])
            self.assertEqual("completed", allowed["result"]["structuredContent"]["status"])
            self.assertTrue(allowed["result"]["structuredContent"]["documents"][0]["read_back"])
            self.assertNotIn(str(root), encoded)

    def test_preflight_keeps_optional_md_separate_from_service_readiness(self) -> None:
        with patch.dict(
            os.environ,
            {
                "AEGIS_MD_COMMAND": "",
                "AEGIS_MD_ROOT": "",
                "AEGIS_MD_AUTO_DISCOVER": "0",
            },
            clear=False,
        ):
            result = run_preflight()

        self.assertTrue(result["service_ready"])
        self.assertFalse(result["e2e_ready"])
        md_check = next(check for check in result["checks"] if check["id"] == "md_backend")
        self.assertEqual("optional", md_check["status"])

    def test_boundary_checker_catches_machine_disclosures(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            local_path = "C:" + "\\" + "private" + "\\" + "file.txt"
            local_url = "http://" + ".".join(["127", "0", "0", "1"]) + ":8080"
            (root / "README.md").write_text(
                "internal " + local_path + " at " + local_url + "\n",
                encoding="utf-8",
            )

            violations = find_violations(root)

        self.assertIn("machine path in public text: README.md", violations)
        self.assertIn("IP address in public text: README.md", violations)
