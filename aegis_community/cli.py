"""Human-friendly command-line entry point for Aegis Community."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from .manifest import (
    COMMUNITY_VERSION,
    PRODUCT_NAME,
    build_capabilities,
    build_manifest,
    build_system_map,
)
from .context_pack import build_context_plan, execute_context_pack
from .document_md import (
    DocumentConversionError,
    build_document_plan,
    document_status,
    execute_document_conversion,
)
from .md import build_md_plan, execute_md, md_status
from .preflight import run_preflight
from .task_contract import TaskEnvelope, TaskValidationError, build_execution_brief
from .watch import discover_documents, watch_folder


_COMMANDS = (
    "run",
    "manifest",
    "capabilities",
    "system-map",
    "preflight",
    "doctor",
    "documents",
    "documents-plan",
    "documents-convert",
    "context-plan",
    "context-pack",
    "watch",
    "md",
    "md-plan",
    "md-run",
    "mcp",
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aegis-community",
        description="Connect an AI client to the public Aegis contract safely.",
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=_COMMANDS,
        help="manifest, capabilities, system-map, preflight, documents, context-pack, md, mcp, or run",
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="JSON request input for tasks, documents, context packs, or MD",
    )
    parser.add_argument(
        "--approve",
        action="store_true",
        help="explicitly approve a bounded local write or MD generation run",
    )
    parser.add_argument(
        "--image",
        type=Path,
        help="local image for md-run; keeps the image path out of the request template",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="destination .glb or .obj file for md-run",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="allow md-run to replace an existing output file",
    )
    parser.add_argument(
        "--path",
        action="append",
        type=Path,
        help="local document path; repeat for a batch conversion",
    )
    parser.add_argument(
        "--folder",
        type=Path,
        help="local folder to scan for a document conversion or bounded watch",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="local destination directory for Markdown artifacts",
    )
    parser.add_argument(
        "--ocr",
        action="store_true",
        help="request a separately configured local OCR adapter",
    )
    parser.add_argument(
        "--no-redact",
        action="store_true",
        help="keep source text unredacted in locally written artifacts",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=None,
        help="maximum context-pack characters",
    )
    parser.add_argument(
        "--chunk-chars",
        type=int,
        default=None,
        help="maximum characters per context chunk",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="bounded watch interval in seconds",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=1,
        help="bounded watch iterations (1-60)",
    )
    parser.add_argument(
        "--non-recursive",
        action="store_true",
        help="scan only the selected folder, not its subfolders",
    )
    parser.add_argument(
        "--format",
        choices=("pretty", "json"),
        help="Output format; JSON is best for automation",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{PRODUCT_NAME} {COMMUNITY_VERSION}",
    )
    return parser


def _read_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as error:
        raise SystemExit("Input error: unable to read the local JSON input.") from error
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise SystemExit(f"Input error: invalid JSON at line {error.lineno}.") from error
    if not isinstance(value, dict):
        raise SystemExit("Input error: the JSON input must be an object.")
    return value


def _document_payload(args: argparse.Namespace, *, require_output: bool) -> dict[str, Any]:
    payload: dict[str, Any] = _read_json(args.input) if args.input is not None else {}
    paths = list(payload.get("paths", [])) if isinstance(payload.get("paths", []), list) else []
    if args.path:
        paths.extend(str(path) for path in args.path)
    if args.folder:
        discovered = discover_documents(
            args.folder,
            recursive=not args.non_recursive,
            output_dir=args.output_dir,
        )
        paths.extend(str(path) for path in discovered)
    payload["paths"] = paths
    if args.output_dir is not None:
        payload["output_dir"] = str(args.output_dir)
    if args.ocr:
        payload["ocr"] = True
    if args.no_redact:
        payload["redact"] = False
    if args.max_chars is not None:
        payload["max_chars"] = args.max_chars
    if args.chunk_chars is not None:
        payload["chunk_chars"] = args.chunk_chars
    if require_output and not payload.get("output_dir"):
        raise SystemExit("Input error: --output-dir or output_dir is required.")
    return payload


def _pretty(command: str, payload: dict[str, Any] | list[dict[str, Any]]) -> None:
    print(f"{PRODUCT_NAME} | Community {COMMUNITY_VERSION}")
    print("=" * 44)

    if command in {"preflight", "doctor"}:
        assert isinstance(payload, dict)
        print(f"Status: {payload.get('status', 'unknown')}")
        print(f"Service ready: {payload.get('service_ready', False)}")
        print(f"Full-engine e2e: {payload.get('e2e_ready', False)}")
        for check in payload.get("checks", []):
            print(f"[{check['status'].upper():7}] {check['id']}: {check['detail']}")
        return

    if command == "manifest":
        assert isinstance(payload, dict)
        release = payload["release"]
        transport = payload["transport"]
        print(f"Contract: {payload['contract_version']}")
        print(f"Stage: {release['stage']}")
        print(f"Transport: {transport['kind']} / local-only")
        print(f"Network required: {transport['network_required']}")
        print("First calls: " + ", ".join(payload["startup"]["first_calls"]))
        return

    if command == "capabilities":
        assert isinstance(payload, list)
        for capability in payload:
            print(f"[{capability['status'].upper():7}] {capability['id']}")
            print(f"          {capability['description']}")
        return

    if command == "system-map":
        assert isinstance(payload, dict)
        for layer in payload["layers"]:
            print(f"{layer['id']}: {layer['role']}")
        print(f"private_core: {payload['private_core']['status']}")
        return

    if command == "md":
        assert isinstance(payload, dict)
        print(f"MD status: {payload['status']}")
        print(f"Quality band: {payload['quality_band']}")
        print(f"Network required: {payload['network_required']}")
        print("Inputs: " + ", ".join(payload["inputs"]))
        print("Outputs: " + ", ".join(payload["outputs"]))
        return

    if command == "documents":
        assert isinstance(payload, dict)
        print(f"Document status: {payload['status']}")
        print(f"Protocol: {payload['protocol']}")
        print("Inputs: " + ", ".join(payload["inputs"]))
        print("Outputs: " + ", ".join(payload["outputs"]))
        print("Formats: " + ", ".join(payload["supported_extensions"]))
        print(f"Local PDF parser: {payload['optional_backends']['pdf_pypdf']}")
        print(f"Local OCR: {payload['optional_backends']['image_ocr']}")
        return

    if command in {"documents-plan", "context-plan"}:
        assert isinstance(payload, dict)
        print(f"Plan status: {payload['status']}")
        print(f"Documents: {payload.get('documents_requested', 'unknown')}")
        print(f"Human approval: {payload['requires_human_review']}")
        print(payload["notice"])
        return

    if command == "documents-convert":
        assert isinstance(payload, dict)
        print(f"Document conversion: {payload['status']}")
        print(f"Processed: {payload.get('processed', 0)}")
        print(f"Succeeded: {payload.get('succeeded', 0)}")
        print(f"Failed: {payload.get('failed', 0)}")
        for item in payload.get("documents", []):
            print(f"- {item.get('source_name', 'document')}: {item.get('status', 'unknown')}")
        return

    if command == "context-pack":
        assert isinstance(payload, dict)
        print(f"Context pack: {payload['status']}")
        print(f"Documents: {len(payload.get('documents', []))}")
        print(f"Chunks: {payload.get('chunk_count', 0)}")
        print(f"Read-back: {payload.get('read_back', False)}")
        return

    if command == "watch":
        assert isinstance(payload, dict)
        print(f"Bounded watch: {payload['status']}")
        print(f"Iterations: {payload.get('iterations', 0)}")
        return

    if command == "md-plan":
        assert isinstance(payload, dict)
        print(f"MD plan: {payload['status']}")
        print(f"Output: {payload['output_format']} / {payload['quality']}")
        print(f"Human approval: {payload['requires_human_review']}")
        print(payload["notice"])
        return

    if command == "md-run":
        assert isinstance(payload, dict)
        artifact = payload["artifact"]
        print(f"MD run: {payload['status']}")
        print(f"Artifact: {artifact['name']} ({artifact['format']})")
        print(f"Bytes: {artifact['bytes']}")
        print(f"SHA-256: {artifact['sha256']}")
        print(f"Read-back: {artifact['read_back']}")
        print(f"Saved: {artifact['saved']}")
        return

    assert isinstance(payload, dict)
    print(f"Task status: {payload.get('status', 'unknown')}")
    print(f"Risk: {payload.get('risk_level', 'unknown')}")
    print(f"Human approval: {payload.get('requires_human_review', True)}")
    actions = payload.get("enabled_actions", [])
    print("Enabled actions: " + (", ".join(actions) if actions else "none"))
    print(payload.get("notice", ""))


def _emit(
    command: str,
    payload: dict[str, Any] | list[dict[str, Any]],
    output_format: str,
) -> None:
    if output_format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        _pretty(command, payload)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    command = args.command or ("run" if args.input else None)

    if command is None:
        parser.print_help()
        return 0

    if command == "mcp":
        from .mcp_server import serve_stdio

        return serve_stdio()

    if command in {"run", "md-plan", "md-run"}:
        if args.input is None:
            parser.error(f"{command} requires --input")
        if command == "md-run" and not args.approve:
            parser.error("md-run requires --approve for the explicit human approval step")
        payload = _read_json(args.input)
        if command == "md-run" and args.image is not None:
            payload["image_path"] = str(args.image)
        if command == "md-run" and args.output is not None:
            payload["output_path"] = str(args.output)
        if command == "md-run" and args.overwrite:
            payload["overwrite"] = True
        try:
            if command == "md-plan":
                result = build_md_plan(payload)
            elif command == "md-run":
                result = execute_md(payload, approved=True)
            else:
                result = build_execution_brief(TaskEnvelope.from_mapping(payload))
        except (PermissionError, RuntimeError, TaskValidationError, ValueError) as error:
            raise SystemExit(f"Input error: {error}") from error
    elif command == "manifest":
        result = build_manifest()
    elif command == "capabilities":
        result = build_capabilities()
    elif command == "system-map":
        result = build_system_map()
    elif command in {"preflight", "doctor"}:
        result = run_preflight()
    elif command == "documents":
        result = document_status()
    elif command == "documents-plan":
        try:
            result = build_document_plan(_document_payload(args, require_output=False))
        except (DocumentConversionError, ValueError) as error:
            raise SystemExit(f"Input error: {error}") from error
    elif command == "documents-convert":
        if not args.approve:
            parser.error("documents-convert requires --approve for the explicit local write step")
        try:
            result = execute_document_conversion(
                _document_payload(args, require_output=True),
                approved=True,
            )
        except (DocumentConversionError, PermissionError, OSError, ValueError) as error:
            raise SystemExit(f"Input error: {error}") from error
    elif command == "context-plan":
        try:
            result = build_context_plan(_document_payload(args, require_output=True))
        except (DocumentConversionError, ValueError) as error:
            raise SystemExit(f"Input error: {error}") from error
    elif command == "context-pack":
        if not args.approve:
            parser.error("context-pack requires --approve for the explicit local write step")
        try:
            result = execute_context_pack(
                _document_payload(args, require_output=True),
                approved=True,
            )
        except (DocumentConversionError, PermissionError, OSError, ValueError) as error:
            raise SystemExit(f"Input error: {error}") from error
    elif command == "watch":
        if not args.approve:
            parser.error("watch requires --approve for the explicit local write step")
        if args.folder is None or args.output_dir is None:
            parser.error("watch requires --folder and --output-dir")
        try:
            result = watch_folder(
                args.folder,
                args.output_dir,
                interval_seconds=args.interval,
                iterations=args.iterations,
                recursive=not args.non_recursive,
                ocr=args.ocr,
                redact=not args.no_redact,
            )
        except (OSError, ValueError) as error:
            raise SystemExit(f"Input error: {error}") from error
    elif command == "md":
        result = md_status()
    else:
        parser.error(f"unsupported command: {command}")

    default_format = "json" if args.input else "pretty"
    _emit(command, result, args.format or default_format)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
