"""Bounded folder scanning for explicit local document conversion runs."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .document_md import SUPPORTED_EXTENSIONS, convert_documents


_SKIP_DIRECTORIES = {".git", ".venv", "__pycache__", "node_modules", "build", "dist"}


def _within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
    except ValueError:
        return False
    return True


def discover_documents(
    folder: str | Path,
    *,
    recursive: bool = True,
    output_dir: str | Path | None = None,
) -> list[Path]:
    """Discover supported files without following an output directory loop."""

    root = Path(folder).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("watch folder must be a directory")
    output = Path(output_dir).expanduser().resolve() if output_dir is not None else None
    candidates = root.rglob("*") if recursive else root.glob("*")
    found: list[Path] = []
    for path in candidates:
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        if any(part.lower() in _SKIP_DIRECTORIES for part in path.parts):
            continue
        if output is not None and _within(path, output):
            continue
        found.append(path)
    return sorted(found, key=lambda item: str(item).lower())


def watch_once(
    folder: str | Path,
    output_dir: str | Path,
    *,
    recursive: bool = True,
    ocr: bool = False,
    redact: bool = True,
) -> dict[str, Any]:
    paths = discover_documents(folder, recursive=recursive, output_dir=output_dir)
    result = convert_documents(paths, output_dir, ocr=ocr, redact=redact)
    result["watch"] = {"mode": "once", "discovered": len(paths), "recursive": recursive}
    return result


def watch_folder(
    folder: str | Path,
    output_dir: str | Path,
    *,
    interval_seconds: float = 5.0,
    iterations: int = 1,
    recursive: bool = True,
    ocr: bool = False,
    redact: bool = True,
) -> dict[str, Any]:
    """Poll a folder a bounded number of times; no unbounded daemon is created."""

    iterations = max(1, min(int(iterations), 60))
    interval_seconds = max(0.1, min(float(interval_seconds), 300.0))
    cycles: list[dict[str, Any]] = []
    for index in range(iterations):
        cycles.append(
            watch_once(
                folder,
                output_dir,
                recursive=recursive,
                ocr=ocr,
                redact=redact,
            )
        )
        if index + 1 < iterations:
            time.sleep(interval_seconds)
    return {
        "workflow": "document.to_markdown.watch",
        "status": "completed" if all(item.get("status") != "failed" for item in cycles) else "partial",
        "iterations": iterations,
        "interval_seconds": interval_seconds,
        "cycles": cycles,
        "privacy": {"paths_returned": False, "addresses_returned": False, "credentials_returned": False},
    }

