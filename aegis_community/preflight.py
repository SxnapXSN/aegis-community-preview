"""Local readiness checks that do not disclose machine-specific details."""

from __future__ import annotations

import sys
from typing import Any

from .document_md import document_status
from .md import md_status


def run_preflight() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    runtime_ready = sys.version_info >= (3, 10)
    checks.append(
        {
            "id": "runtime",
            "status": "ready" if runtime_ready else "blocked",
            "detail": "Python runtime is supported." if runtime_ready else "Python 3.10 or newer is required.",
        }
    )
    checks.extend(
        [
            {
                "id": "mcp_transport",
                "status": "ready",
                "detail": "Local stdio transport is available.",
            },
            {
                "id": "network_policy",
                "status": "ready",
                "detail": "No network connection is required by Community.",
            },
            {
                "id": "privacy_boundary",
                "status": "ready",
                "detail": "Machine paths, addresses, credentials, and telemetry are not returned.",
            },
        ]
    )
    md = md_status()
    checks.append(
        {
            "id": "md_backend",
            "status": md["status"],
            "detail": (
                "A local MD adapter is available."
                if md["status"] == "ready"
                else "MD remains optional until a local adapter is configured."
            ),
        }
    )

    documents = document_status()
    checks.extend(
        [
            {
                "id": "document_pipeline",
                "status": documents["status"],
                "detail": "Built-in document-to-Markdown parsers are available.",
            },
            {
                "id": "ocr_backend",
                "status": "ready" if documents["optional_backends"]["image_ocr"] else "optional",
                "detail": (
                    "A local OCR adapter is available."
                    if documents["optional_backends"]["image_ocr"]
                    else "OCR remains optional for scanned images and PDF pages."
                ),
            },
        ]
    )

    required = [check for check in checks if check["id"] not in {"md_backend", "ocr_backend"}]
    status = "ready" if all(check["status"] == "ready" for check in required) else "blocked"
    return {
        "status": status,
        "service_ready": status == "ready",
        "e2e_ready": False,
        "checks": checks,
        "notice": "A ready preflight proves local contract readiness, not full private-engine coverage.",
    }
