"""A bounded stdio MCP server for Aegis Community."""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from typing import Any

from .context_pack import build_context_plan, execute_context_pack
from .document_md import (
    DocumentConversionError,
    build_document_plan,
    document_status,
    execute_document_conversion,
)
from .manifest import COMMUNITY_VERSION, build_capabilities, build_manifest, build_system_map
from .md import build_md_plan, md_status
from .preflight import run_preflight
from .task_contract import TaskEnvelope, TaskValidationError, build_execution_brief


_SERVER_NAME = "aegis-community"


def _tools() -> list[dict[str, Any]]:
    empty = {"type": "object", "properties": {}, "additionalProperties": False}
    task_schema = {
        "type": "object",
        "required": ["task_id", "title", "objective", "risk_level", "allowed_actions"],
        "properties": {
            "task_id": {"type": "string", "minLength": 1},
            "title": {"type": "string", "minLength": 1},
            "objective": {"type": "string", "minLength": 1},
            "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
            "allowed_actions": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
            },
        },
        "additionalProperties": False,
    }
    md_schema = {
        "type": "object",
        "properties": {
            "input_kind": {"type": "string", "enum": ["image"]},
            "output_format": {"type": "string", "enum": ["glb", "obj"]},
            "quality": {"type": "string", "enum": ["balanced", "high"]},
            "texture": {"type": "boolean"},
        },
        "additionalProperties": False,
    }
    document_plan_schema = {
        "type": "object",
        "required": ["paths"],
        "properties": {
            "paths": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "ocr": {"type": "boolean", "default": False},
            "redact": {"type": "boolean", "default": True},
        },
        "additionalProperties": False,
    }
    document_convert_schema = {
        "type": "object",
        "required": ["paths", "output_dir", "approved"],
        "properties": {
            "paths": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "output_dir": {"type": "string", "minLength": 1},
            "ocr": {"type": "boolean", "default": False},
            "redact": {"type": "boolean", "default": True},
            "approved": {"type": "boolean"},
        },
        "additionalProperties": False,
    }
    context_schema = {
        "type": "object",
        "required": ["paths", "output_dir", "approved"],
        "properties": {
            "paths": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "output_dir": {"type": "string", "minLength": 1},
            "ocr": {"type": "boolean", "default": False},
            "redact": {"type": "boolean", "default": True},
            "max_chars": {"type": "integer", "minimum": 4000, "maximum": 2000000},
            "chunk_chars": {"type": "integer", "minimum": 2000, "maximum": 200000},
            "approved": {"type": "boolean"},
        },
        "additionalProperties": False,
    }
    context_plan_schema = dict(context_schema)
    context_plan_schema["required"] = ["paths", "output_dir"]
    context_plan_schema["properties"] = dict(context_schema["properties"])
    context_plan_schema["properties"].pop("approved", None)
    return [
        {
            "name": "aegis_manifest",
            "description": "Read the public Aegis contract before using any other tool.",
            "inputSchema": empty,
        },
        {
            "name": "aegis_capabilities",
            "description": "List public capabilities, modes, and current availability.",
            "inputSchema": empty,
        },
        {
            "name": "aegis_system_map",
            "description": "Read the privacy-safe public system map; private internals are omitted.",
            "inputSchema": empty,
        },
        {
            "name": "aegis_preflight",
            "description": "Check local contract readiness without exposing machine details.",
            "inputSchema": empty,
        },
        {
            "name": "aegis_plan_task",
            "description": "Validate a task and create a non-executing safety brief.",
            "inputSchema": task_schema,
        },
        {
            "name": "aegis_md_capability",
            "description": "Read the public high-quality MD image-to-3D capability.",
            "inputSchema": empty,
        },
        {
            "name": "aegis_md_plan",
            "description": "Prepare a privacy-safe MD generation plan; MCP never runs the model.",
            "inputSchema": md_schema,
        },
        {
            "name": "aegis_document_capability",
            "description": "Read the universal local document-to-Markdown capability and format limits.",
            "inputSchema": empty,
        },
        {
            "name": "aegis_document_plan",
            "description": "Validate a document conversion request without reading or writing local files.",
            "inputSchema": document_plan_schema,
        },
        {
            "name": "aegis_document_convert",
            "description": "Run an explicitly approved bounded local document-to-Markdown conversion.",
            "inputSchema": document_convert_schema,
        },
        {
            "name": "aegis_context_plan",
            "description": "Plan a redacted, chunked Markdown context pack without writing local files.",
            "inputSchema": context_plan_schema,
        },
        {
            "name": "aegis_context_pack",
            "description": "Build an explicitly approved redacted Markdown context pack with read-back evidence.",
            "inputSchema": context_schema,
        },
    ]


def _json_result(request_id: Any, payload: Any) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(payload, indent=2, sort_keys=True),
                }
            ],
            "structuredContent": payload,
            "isError": False,
        },
    }


def _tool_error(request_id: Any, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "content": [{"type": "text", "text": message}],
            "isError": True,
        },
    }


def _rpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def _call_tool(name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
    if name == "aegis_manifest":
        return build_manifest()
    if name == "aegis_capabilities":
        return {"capabilities": build_capabilities()}
    if name == "aegis_system_map":
        return build_system_map()
    if name == "aegis_preflight":
        return run_preflight()
    if name == "aegis_md_capability":
        return md_status()
    if name == "aegis_plan_task":
        return build_execution_brief(TaskEnvelope.from_mapping(arguments))
    if name == "aegis_md_plan":
        return build_md_plan(arguments)
    if name == "aegis_document_capability":
        return document_status()
    if name == "aegis_document_plan":
        return build_document_plan(arguments)
    if name == "aegis_document_convert":
        return execute_document_conversion(arguments, approved=arguments.get("approved") is True)
    if name == "aegis_context_plan":
        return build_context_plan(arguments)
    if name == "aegis_context_pack":
        return execute_context_pack(arguments, approved=arguments.get("approved") is True)
    raise KeyError(name)


def handle_message(message: Mapping[str, Any]) -> dict[str, Any] | None:
    """Handle one JSON-RPC message and return its response, if any."""

    request_id = message.get("id")
    method = message.get("method")
    if not isinstance(method, str):
        return _rpc_error(request_id, -32600, "Invalid JSON-RPC request")
    if method.startswith("notifications/"):
        return None
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": _SERVER_NAME, "version": COMMUNITY_VERSION},
                "instructions": "Call aegis_manifest, aegis_capabilities, aegis_system_map, and aegis_preflight first; plan document work before approval.",
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": _tools()}}
    if method != "tools/call":
        return _rpc_error(request_id, -32601, "Method is not available in Community")

    params = message.get("params")
    if not isinstance(params, Mapping):
        return _rpc_error(request_id, -32602, "tools/call params must be an object")
    name = params.get("name")
    arguments = params.get("arguments", {})
    if not isinstance(name, str) or not isinstance(arguments, Mapping):
        return _rpc_error(request_id, -32602, "Tool name and arguments are required")
    try:
        return _json_result(request_id, _call_tool(name, arguments))
    except KeyError:
        return _tool_error(request_id, "Tool is not available in Community")
    except (DocumentConversionError, PermissionError, TaskValidationError, ValueError) as error:
        return _tool_error(request_id, f"Tool input error: {error}")


def serve_stdio() -> int:
    """Serve newline-delimited JSON-RPC without other stdout output."""

    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
            if not isinstance(message, Mapping):
                response = _rpc_error(None, -32600, "Invalid JSON-RPC request")
            else:
                response = handle_message(message)
        except json.JSONDecodeError:
            response = _rpc_error(None, -32700, "Parse error")
        if response is not None:
            print(json.dumps(response, separators=(",", ":")), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(serve_stdio())
