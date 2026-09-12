"""Public MD contract and approval-gated local adapter runner."""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .public_text import redact_public_text


MD_PROTOCOL_VERSION = "1.0"
_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
_OUTPUT_SUFFIXES = {"glb", "obj"}
_MAX_INPUT_BYTES = 20 * 1024 * 1024
_MAX_OUTPUT_BYTES = 512 * 1024 * 1024
_DEFAULT_TIMEOUT_SECONDS = 900


@dataclass(frozen=True)
class _Backend:
    source: str
    command: tuple[str, ...]
    cwd: Path | None = None


def _strip_matching_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _parse_command(value: str) -> tuple[str, ...] | None:
    """Parse a configured command without invoking a shell."""

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, list) and all(isinstance(item, str) and item for item in parsed):
        return tuple(parsed)

    try:
        tokens = shlex.split(value, posix=False)
    except ValueError:
        return None
    tokens = tuple(_strip_matching_quotes(token) for token in tokens)
    return tokens or None


def _adapter_command(root: Path, script: Path) -> tuple[str, ...]:
    """Prefer the provider's own virtual environment when it has one."""

    python_candidates = (
        root / ".venv" / "Scripts" / "python.exe",
        root / ".venv" / "bin" / "python",
    )
    python = next((candidate for candidate in python_candidates if candidate.is_file()), None)
    return (str(python or sys.executable), str(script))


def _candidate_roots() -> list[Path]:
    roots: list[Path] = []
    root_value = os.environ.get("AEGIS_MD_ROOT", "").strip()
    if root_value:
        roots.append(Path(root_value).expanduser())

    if os.environ.get("AEGIS_MD_AUTO_DISCOVER", "1").strip().lower() not in {
        "0",
        "false",
        "no",
    }:
        try:
            roots.append(Path(__file__).resolve().parents[3] / "MD")
        except (IndexError, OSError):
            pass
    return roots


def _resolve_backend() -> _Backend | None:
    command_value = os.environ.get("AEGIS_MD_COMMAND", "").strip()
    if command_value:
        command = _parse_command(command_value)
        if command is None:
            return None
        cwd_value = os.environ.get("AEGIS_MD_CWD", "").strip()
        cwd = Path(cwd_value).expanduser() if cwd_value else None
        return _Backend("configured_adapter", command, cwd)

    for root in _candidate_roots():
        try:
            root = root.resolve()
            if root.is_file() and root.suffix.lower() == ".py":
                return _Backend("local_md_backend", _adapter_command(root.parent, root), root.parent)

            for candidate_root in (root, root / "Hunyuan3D-2"):
                if not candidate_root.is_dir():
                    continue
                for filename in ("aegis_md_adapter.py", "Aegis-MD-Adapter.py"):
                    script = candidate_root / filename
                    if script.is_file():
                        return _Backend(
                            "local_md_backend",
                            _adapter_command(candidate_root, script),
                            candidate_root,
                        )
        except OSError:
            continue
    return None


def _configured_backend() -> tuple[str, bool]:
    """Discover a protocol adapter without returning its command or path."""

    backend = _resolve_backend()
    if backend is None:
        return "not_configured", False
    return backend.source, True


def md_status() -> dict[str, Any]:
    source, ready = _configured_backend()
    return {
        "id": "md.image_to_3d",
        "name": "MD image-to-3D",
        "protocol": f"md-adapter/{MD_PROTOCOL_VERSION}",
        "tier": "community_high",
        "status": "ready" if ready else "optional",
        "source": source,
        "network_required": False,
        "inputs": ["image"],
        "outputs": ["3d_model"],
        "quality_band": "high_public",
        "execution": "approval_gated_local_run",
        "limits": [
            "Runs through a user-provided local protocol adapter.",
            "Model weights and upstream licenses remain outside this package.",
            "Private Stable models and optimizers are not included.",
        ],
    }


def build_md_plan(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate an MD request and return a non-executing, privacy-safe plan."""

    if not isinstance(payload, Mapping):
        raise ValueError("md task must be a JSON object")

    input_kind = payload.get("input_kind", "image")
    if input_kind != "image":
        raise ValueError("Community MD currently accepts input_kind=image")

    output_format = payload.get("output_format", "glb")
    if output_format not in _OUTPUT_SUFFIXES:
        raise ValueError("output_format must be glb or obj")

    quality = payload.get("quality", "high")
    if quality not in {"balanced", "high"}:
        raise ValueError("quality must be balanced or high")

    texture = payload.get("texture", False)
    if not isinstance(texture, bool):
        raise ValueError("texture must be a boolean")

    status = md_status()
    if status["status"] == "ready":
        plan_status = "ready_for_review"
        notice = "MD adapter detected; review the request before local generation."
    else:
        plan_status = "optional_backend_not_configured"
        notice = "Install or configure a local MD adapter before generation."

    return {
        "workflow": "md.image_to_3d",
        "status": plan_status,
        "input_kind": input_kind,
        "output_format": output_format,
        "quality": quality,
        "texture": texture,
        "requires_human_review": True,
        "execution": "plan_only",
        "notice": redact_public_text(notice),
        "privacy": {
            "paths_returned": False,
            "addresses_returned": False,
            "credentials_returned": False,
        },
    }


def _validate_image(path_value: Any) -> Path:
    if not isinstance(path_value, str) or not path_value.strip():
        raise ValueError("md-run requires image_path")
    path = Path(path_value).expanduser()
    try:
        if not path.is_file() or path.suffix.lower() not in _IMAGE_SUFFIXES:
            raise ValueError("image_path must point to a supported local image")
        if path.stat().st_size > _MAX_INPUT_BYTES:
            raise ValueError("image_path exceeds the Community input limit")
    except OSError as error:
        raise ValueError("image_path is not readable") from error
    return path.resolve()


def _timeout_seconds() -> int:
    value = os.environ.get("AEGIS_MD_TIMEOUT_SECONDS", str(_DEFAULT_TIMEOUT_SECONDS)).strip()
    try:
        timeout = int(value)
    except ValueError:
        return _DEFAULT_TIMEOUT_SECONDS
    return max(30, min(timeout, 3600))


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
    except ValueError:
        return False
    return True


def _artifact_is_readable(path: Path, output_format: str) -> bool:
    if output_format == "glb":
        with path.open("rb") as stream:
            header = stream.read(12)
        if len(header) != 12 or header[:4] != b"glTF":
            return False
        version = int.from_bytes(header[4:8], "little")
        declared_length = int.from_bytes(header[8:12], "little")
        return version == 2 and declared_length >= 12 and declared_length <= path.stat().st_size

    try:
        text = path.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeError):
        return False
    lines = text.splitlines()
    return any(line.startswith("v ") for line in lines) and any(line.startswith("f ") for line in lines)


def _artifact_summary(path: Path, output_format: str) -> dict[str, Any]:
    try:
        size = path.stat().st_size
        if size <= 0 or size > _MAX_OUTPUT_BYTES:
            raise ValueError("MD adapter returned an invalid artifact size")
        if not _artifact_is_readable(path, output_format):
            raise ValueError("MD adapter returned an unreadable artifact")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise ValueError("MD artifact could not be read back") from error
    return {
        "name": f"model.{output_format}",
        "format": output_format,
        "bytes": size,
        "sha256": digest.hexdigest(),
        "read_back": True,
    }


def _validate_destination(path_value: Any, output_format: str, overwrite: Any) -> Path | None:
    if path_value is None:
        return None
    if not isinstance(path_value, str) or not path_value.strip():
        raise ValueError("output_path must be a local file")
    if not isinstance(overwrite, bool):
        raise ValueError("overwrite must be a boolean")
    destination = Path(path_value).expanduser()
    if destination.suffix.lower().lstrip(".") != output_format:
        raise ValueError(f"output_path must use the .{output_format} extension")
    try:
        if destination.exists() and not destination.is_file():
            raise ValueError("output_path must be a file")
        if destination.exists() and not overwrite:
            raise ValueError("output_path already exists; set overwrite=true to replace it")
        destination.parent.mkdir(parents=True, exist_ok=True)
        return destination.resolve()
    except OSError as error:
        raise ValueError("output_path is not writable") from error


def execute_md(payload: Mapping[str, Any], *, approved: bool = False) -> dict[str, Any]:
    """Run one explicitly approved local adapter request and read its artifact back."""

    if not approved:
        raise PermissionError("MD generation requires explicit human approval")
    if not isinstance(payload, Mapping):
        raise ValueError("md task must be a JSON object")

    plan = build_md_plan(payload)
    image_path = _validate_image(payload.get("image_path"))
    backend = _resolve_backend()
    if backend is None:
        raise RuntimeError("No usable local MD adapter is configured")

    output_format = plan["output_format"]
    quality = plan["quality"]
    texture = plan["texture"]
    seed = payload.get("seed", 1234)
    if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed <= 2**31 - 1:
        raise ValueError("seed must be an integer from 0 to 2147483647")
    destination = _validate_destination(
        payload.get("output_path"),
        output_format,
        payload.get("overwrite", False),
    )

    with tempfile.TemporaryDirectory(prefix="aegis-community-md-") as temp_dir:
        output_dir = Path(temp_dir).resolve()
        request = {
            "protocol": f"md-adapter/{MD_PROTOCOL_VERSION}",
            "operation": "image_to_3d",
            "input_path": str(image_path),
            "output_dir": str(output_dir),
            "output_format": output_format,
            "quality": quality,
            "texture": texture,
            "seed": seed,
        }
        try:
            completed = subprocess.run(
                list(backend.command),
                cwd=str(backend.cwd) if backend.cwd else None,
                input=json.dumps(request),
                capture_output=True,
                text=True,
                timeout=_timeout_seconds(),
                check=False,
                shell=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise RuntimeError("MD adapter did not complete") from error

        if completed.returncode != 0:
            raise RuntimeError("MD adapter returned an error")
        try:
            response = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise RuntimeError("MD adapter returned an invalid response") from error
        if not isinstance(response, Mapping) or response.get("status") != "completed":
            raise RuntimeError("MD adapter did not complete the request")

        artifact_value = response.get("artifact_path")
        if not isinstance(artifact_value, str) or not artifact_value:
            raise RuntimeError("MD adapter did not return an artifact")
        artifact_path = Path(artifact_value).expanduser()
        try:
            artifact_path = artifact_path.resolve()
        except OSError as error:
            raise RuntimeError("MD adapter returned an invalid artifact") from error
        if not _is_within(artifact_path, output_dir):
            raise RuntimeError("MD adapter artifact was outside its temporary output area")
        if artifact_path.suffix.lower().lstrip(".") != output_format:
            raise RuntimeError("MD adapter returned the wrong artifact format")
        artifact = _artifact_summary(artifact_path, output_format)
        if destination is not None:
            try:
                shutil.copyfile(artifact_path, destination)
                saved_artifact = _artifact_summary(destination, output_format)
            except OSError as error:
                raise RuntimeError("MD artifact could not be saved") from error
            if saved_artifact["sha256"] != artifact["sha256"]:
                raise RuntimeError("MD artifact failed final verification")
            artifact["saved"] = True
        else:
            artifact["saved"] = False

    return {
        "workflow": "md.image_to_3d",
        "status": "completed",
        "output_format": output_format,
        "quality": quality,
        "texture": texture,
        "execution": "approved_local_adapter",
        "artifact": artifact,
        "privacy": {
            "paths_returned": False,
            "addresses_returned": False,
            "credentials_returned": False,
        },
    }
