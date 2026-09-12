"""AI-ready Markdown context packs built from local document artifacts."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from .document_md import (
    DocumentConversionError,
    convert_document,
)
from .public_text import redact_public_text


_DEFAULT_MAX_CHARS = 200_000
_DEFAULT_CHUNK_CHARS = 30_000


def _atomic_write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    os.replace(temporary, path)


def _safe_number(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(number, maximum))


def _chunk_text(value: str, max_chars: int) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", value) if part.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_size = 0
    for paragraph in paragraphs:
        pieces = [paragraph[index : index + max_chars] for index in range(0, len(paragraph), max_chars)] or [""]
        for piece in pieces:
            if current and current_size + len(piece) + 2 > max_chars:
                chunks.append("\n\n".join(current))
                current = []
                current_size = 0
            current.append(piece)
            current_size += len(piece) + 2
    if current:
        chunks.append("\n\n".join(current))
    return chunks or ["# Empty context pack\n"]


def _truncate(value: str, limit: int) -> tuple[str, bool]:
    if len(value) <= limit:
        return value, False
    marker = "\n\n[Content truncated by the Community context budget.]\n"
    return value[: max(0, limit - len(marker))] + marker, True


def _document_row(index: int, item: Mapping[str, Any]) -> list[str]:
    metadata = item.get("metadata") if isinstance(item.get("metadata"), Mapping) else {}
    tokens = metadata.get("estimated_tokens", "unknown")
    return [
        str(index),
        redact_public_text(str(item.get("source_name", "document"))),
        str(item.get("source_type", "unknown")),
        str(item.get("status", "unknown")),
        str(item.get("content_hash", "unknown"))[:16],
        str(tokens),
    ]


def _table(rows: list[list[str]]) -> str:
    backslash = chr(92)
    rows = [[cell.replace("|", backslash + "|").replace(chr(10), " ") for cell in row] for row in rows]
    width = max((len(row) for row in rows), default=1)
    normalised = [(row + [""] * width)[:width] for row in rows]
    lines = ["| " + " | ".join(normalised[0]) + " |", "| " + " | ".join("---" for _ in range(width)) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in normalised[1:])
    return "\n".join(lines)


def build_context_pack(
    paths: Iterable[str | Path],
    output_dir: str | Path,
    *,
    ocr: bool = False,
    redact: bool = True,
    max_chars: int = _DEFAULT_MAX_CHARS,
    chunk_chars: int = _DEFAULT_CHUNK_CHARS,
) -> dict[str, Any]:
    """Convert documents and write one bounded context pack for an AI client."""

    root = Path(output_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    max_chars = _safe_number(max_chars, _DEFAULT_MAX_CHARS, 4_000, 2_000_000)
    chunk_chars = _safe_number(chunk_chars, _DEFAULT_CHUNK_CHARS, 2_000, 200_000)
    converted: list[dict[str, Any]] = []
    contents: list[tuple[dict[str, Any], str]] = []
    for path in paths:
        try:
            item = convert_document(path, root, ocr=ocr, redact=redact, include_content=True)
            converted.append({key: value for key, value in item.items() if key not in {"markdown", "summary"}})
            contents.append((item, str(item.get("markdown", ""))))
        except (DocumentConversionError, OSError) as error:
            converted.append(
                {
                    "source_name": redact_public_text(Path(path).name),
                    "status": "failed",
                    "error": redact_public_text(str(error)),
                }
            )

    rows = [["#", "Document", "Type", "Status", "Hash", "Tokens"]]
    rows.extend(_document_row(index, item) for index, item in enumerate(converted, start=1))
    body: list[str] = [
        "# Aegis Community Context Pack",
        "",
        "This pack contains bounded, provenance-bearing Markdown for an AI client.",
        "It is generated locally and can be regenerated when source hashes change.",
        "",
        "## Pack Metadata",
        "",
        f"- Documents requested: `{len(converted)}`",
        f"- Documents converted: `{sum(1 for item in converted if item.get('status') in {'complete', 'cached', 'partial'})}`",
        f"- Redaction enabled: `{redact}`",
        f"- Context character budget: `{max_chars}`",
        f"- Chunk character budget: `{chunk_chars}`",
        "",
        "## Document Index",
        "",
        _table(rows),
        "",
        "## Documents",
        "",
    ]
    truncated_count = 0
    remaining = max_chars
    for index, (item, content) in enumerate(contents, start=1):
        name = redact_public_text(str(item.get("source_name", f"document-{index}")))
        summary = str(item.get("summary", "")).strip()
        section = f"### {index}. {name}\n\n{summary}\n\n{content.strip()}\n"
        section, truncated = _truncate(section, max(500, remaining))
        body.append(section)
        remaining -= len(section)
        if truncated:
            truncated_count += 1
            break
    context_text = "\n".join(body).strip() + "\n"
    context_path = root / "context.md"
    _atomic_write(context_path, context_text)

    chunks = _chunk_text(context_text, chunk_chars)
    chunk_names: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        name = f"context-{index:04d}.md"
        chunk_names.append(f"chunks/{name}")
        _atomic_write(root / "chunks" / name, chunk.rstrip() + "\n")

    manifest = {
        "schema": "aegis.context-pack/v1",
        "workflow": "document.to_markdown.context_pack",
        "status": "completed" if converted and all(item.get("status") != "failed" for item in converted) else "partial" if converted else "failed",
        "documents": converted,
        "context_file": "context.md",
        "chunk_files": chunk_names,
        "truncated_documents": truncated_count,
        "redacted": redact,
        "privacy": {"paths_returned": False, "addresses_returned": False, "credentials_returned": False},
    }
    _atomic_write(root / "context.manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    read_back = context_path.is_file() and (root / "context.manifest.json").is_file() and all((root / name).is_file() for name in chunk_names)
    return {
        "workflow": "document.to_markdown.context_pack",
        "status": manifest["status"],
        "documents": converted,
        "output_files": ["context.md", "context.manifest.json", *chunk_names],
        "chunk_count": len(chunk_names),
        "truncated_documents": truncated_count,
        "read_back": read_back,
        "privacy": manifest["privacy"],
    }


def build_context_plan(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise DocumentConversionError("context request must be a JSON object")
    paths = payload.get("paths")
    if not isinstance(paths, list) or not paths or not all(isinstance(item, str) and item.strip() for item in paths):
        raise DocumentConversionError("paths must be a non-empty array of local document names")
    output_dir = payload.get("output_dir")
    if not isinstance(output_dir, str) or not output_dir.strip():
        raise DocumentConversionError("output_dir is required for a context pack")
    redact = payload.get("redact", True)
    ocr = payload.get("ocr", False)
    if not isinstance(redact, bool) or not isinstance(ocr, bool):
        raise DocumentConversionError("redact and ocr must be boolean values")
    return {
        "workflow": "document.to_markdown.context_pack",
        "status": "ready_for_review",
        "execution": "approval_gated_local_write",
        "requires_human_review": True,
        "documents_requested": len(paths),
        "redaction_enabled": redact,
        "ocr_requested": ocr,
        "output_files": ["context.md", "context.manifest.json", "chunks/context-0001.md and more"],
        "privacy": {"paths_returned": False, "addresses_returned": False, "credentials_returned": False},
        "notice": "Review the local inputs and destination before approving the context pack.",
    }


def execute_context_pack(payload: Mapping[str, Any], *, approved: bool = False) -> dict[str, Any]:
    if not approved:
        raise PermissionError("context pack generation requires explicit human approval")
    plan = build_context_plan(payload)
    result = build_context_pack(
        payload["paths"],
        payload["output_dir"],
        ocr=bool(payload.get("ocr", False)),
        redact=bool(payload.get("redact", True)),
        max_chars=payload.get("max_chars", _DEFAULT_MAX_CHARS),
        chunk_chars=payload.get("chunk_chars", _DEFAULT_CHUNK_CHARS),
    )
    result["execution"] = "approved_local_context_pack"
    result["requires_human_review"] = plan["requires_human_review"]
    return result
