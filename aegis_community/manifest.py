"""The public, machine-readable contract that AI clients read first."""

from __future__ import annotations

from typing import Any

from .document_md import document_status
from .md import md_status


COMMUNITY_VERSION = "1.1.0"
CONTRACT_VERSION = "1.0"
PRODUCT_NAME = "Aegis Community"


def build_capabilities() -> list[dict[str, Any]]:
    md = md_status()
    documents = document_status()
    return [
        {
            "id": "architecture_context",
            "status": "ready",
            "mode": "public_manifest",
            "description": "Explain the exposed Community architecture before planning.",
        },
        {
            "id": "task_contract",
            "status": "ready",
            "mode": "local_validation",
            "description": "Validate task identity, objective, risk, and allowed actions.",
        },
        {
            "id": "safe_planning",
            "status": "ready",
            "mode": "plan_only",
            "description": "Produce a conservative brief without executing actions.",
        },
        {
            "id": "evidence_summary",
            "status": "ready",
            "mode": "per_run",
            "description": "Return a structured summary of checks and approval state.",
        },
        {
            "id": md["id"],
            "status": md["status"],
            "mode": "local_adapter",
            "description": "Plan or run an approved high-quality public MD image-to-3D workflow.",
        },
        {
            "id": documents["id"],
            "status": documents["status"],
            "mode": "local_document_conversion",
            "description": "Convert supported local text, Office, PDF, CSV, and image inputs into bounded AI-readable Markdown.",
        },
        {
            "id": "document.context_pack",
            "status": "ready",
            "mode": "local_context_pack",
            "description": "Build a redacted, chunked Markdown context pack with source hashes and read-back evidence.",
        },
        {
            "id": "document.folder_watch",
            "status": "ready",
            "mode": "bounded_polling",
            "description": "Scan a local folder for supported documents in an explicit bounded run.",
        },
    ]


def build_system_map() -> dict[str, Any]:
    """Return only the public topology, never private paths or module names."""

    return {
        "name": PRODUCT_NAME,
        "scope": "community_public_surface",
        "layers": [
            {
                "id": "ai_client",
                "role": "Codex, Claude, or another MCP-compatible client",
            },
            {
                "id": "bootstrap_bridge",
                "role": "Local connection and capability discovery",
            },
            {
                "id": "public_contract",
                "role": "Manifest, task schema, preflight, and safe planner",
            },
            {
                "id": "md_adapter",
                "role": "Optional local MD provider contract",
            },
            {
                "id": "document_pipeline",
                "role": "Local document parsing, Markdown artifacts, and deterministic metadata",
            },
            {
                "id": "context_pack",
                "role": "Redacted, bounded Markdown context prepared for an AI client",
            },
            {
                "id": "evidence_boundary",
                "role": "Privacy-safe result and approval summary",
            },
        ],
        "private_core": {
            "status": "not_public",
            "details": "Private Stable capabilities are not described or exported.",
        },
    }


def build_manifest() -> dict[str, Any]:
    md = md_status()
    return {
        "schema": "aegis.manifest/v1",
        "contract_version": CONTRACT_VERSION,
        "product": PRODUCT_NAME,
        "release": {
            "channel": "community",
            "version": COMMUNITY_VERSION,
            "stage": "release_candidate",
        },
        "transport": {
            "kind": "stdio",
            "network_required": False,
            "local_only": True,
        },
        "startup": {
            "first_calls": [
                "aegis_manifest",
                "aegis_capabilities",
                "aegis_system_map",
                "aegis_preflight",
            ],
            "unknown_capability_policy": "fail_closed",
        },
        "capabilities": build_capabilities(),
        "md": md,
        "documents": document_status(),
        "limits": [
            "One local user and one active workspace.",
            "High-risk tasks require human approval.",
            "The Community runtime does not execute arbitrary actions.",
            "Private Stable modules, models, policies, and operational data are excluded.",
        ],
        "privacy": {
            "network_access": False,
            "machine_identifiers_exposed": False,
            "local_paths_exposed": False,
            "addresses_exposed": False,
            "credentials_collected": False,
            "telemetry_collected": False,
        },
    }
