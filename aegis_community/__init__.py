"""Privacy-safe public contracts for Aegis Community."""

from .manifest import build_capabilities, build_manifest, build_system_map
from .md import build_md_plan, execute_md, md_status
from .context_pack import build_context_pack, build_context_plan, execute_context_pack
from .document_md import (
    build_document_plan,
    convert_document,
    convert_documents,
    document_status,
    execute_document_conversion,
)
from .preflight import run_preflight
from .task_contract import TaskEnvelope, TaskValidationError, build_execution_brief
from .watch import discover_documents, watch_folder, watch_once

__all__ = [
    "TaskEnvelope",
    "TaskValidationError",
    "build_execution_brief",
    "build_capabilities",
    "build_manifest",
    "build_md_plan",
    "execute_md",
    "build_context_pack",
    "build_context_plan",
    "execute_context_pack",
    "build_document_plan",
    "convert_document",
    "convert_documents",
    "document_status",
    "execute_document_conversion",
    "discover_documents",
    "watch_folder",
    "watch_once",
    "build_system_map",
    "md_status",
    "run_preflight",
]
