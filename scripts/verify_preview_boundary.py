"""Fail when a Community Preview contains private or secret material."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable


IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "build",
    "dist",
}
ALLOWED_TOP_LEVEL_DIRECTORIES = {
    ".github",
    "aegis_community",
    "docs",
    "examples",
    "scripts",
    "tests",
}
ALLOWED_TOP_LEVEL_FILES = {
    ".gitattributes",
    ".gitignore",
    "COMMUNITY_SCOPE.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "NOTICE",
    "README.md",
    "SECURITY.md",
    "pyproject.toml",
}
FORBIDDEN_PATH_PARTS = {
    ".aegis",
    ".aegis_runtime",
    "storage",
    "snapshots",
    "telemetry",
    "agent_hub",
    "providers",
    "backoffice",
}
FORBIDDEN_SUFFIXES = {".key", ".pem", ".p12", ".pfx"}
SECRET_PATTERN = re.compile(
    r"(?i)(?:api[_-]?key|secret|access[_-]?token)\s*[:=]\s*[\"'][^\"'\s]{8,}"
)
WINDOWS_PATH_PATTERN = re.compile(
    r"(?i)(?:[a-z]:[\\/](?![\\/])|\\\\[^\\/\s]+[\\/]+)[^\s<>\"']*"
)
UNIX_PATH_PATTERN = re.compile(
    r"(?i)(?<![\w])/(?:home|users|mnt|tmp|var|opt|workspace)/[^\s<>\"']*"
)
IPV4_PATTERN = re.compile(
    r"(?<![\w.])(?:25[0-5]|2[0-4]\d|1?\d?\d)"
    r"(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}(?::\d{1,5})?(?![\w.])"
)
LOOPBACK_HOST_PATTERN = re.compile(
    r"(?i)(?<![\w.-])localhost(?::\d{1,5})?(?![\w.-])"
)
TEXT_SUFFIXES = {
    ".bat",
    ".cmd",
    ".json",
    ".md",
    ".py",
    ".ps1",
    ".txt",
    ".toml",
    ".yml",
    ".yaml",
}
CONTENT_DISCLOSURE_EXEMPTIONS = {
    "aegis_community/public_text.py",
    "scripts/verify_preview_boundary.py",
}


def _files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if any(
            part in IGNORED_DIRECTORIES or part.endswith(".egg-info")
            for part in path.parts
        ):
            continue
        if path.is_file():
            yield path


def find_violations(root: Path) -> list[str]:
    violations: list[str] = []
    for path in _files(root):
        relative = path.relative_to(root)
        parts = {part.lower() for part in relative.parts}
        name = path.name.lower()
        top_level = relative.parts[0]

        if (
            len(relative.parts) == 1 and top_level not in ALLOWED_TOP_LEVEL_FILES
        ) or (
            len(relative.parts) > 1
            and top_level not in ALLOWED_TOP_LEVEL_DIRECTORIES
        ):
            violations.append(f"path is outside the public allow-list: {relative}")

        if parts & FORBIDDEN_PATH_PARTS:
            violations.append(f"forbidden private path: {relative}")
        if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
            violations.append(f"environment file: {relative}")
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            violations.append(f"credential file suffix: {relative}")

        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            violations.append(f"non-text file requires review: {relative}")
            continue
        if SECRET_PATTERN.search(content):
            violations.append(f"possible embedded credential: {relative}")
        if relative.as_posix() not in CONTENT_DISCLOSURE_EXEMPTIONS:
            if WINDOWS_PATH_PATTERN.search(content) or UNIX_PATH_PATTERN.search(content):
                violations.append(f"machine path in public text: {relative}")
            if IPV4_PATTERN.search(content):
                violations.append(f"IP address in public text: {relative}")
            if LOOPBACK_HOST_PATTERN.search(content):
                violations.append(f"local host in public text: {relative}")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", default=".", type=Path)
    args = parser.parse_args()
    root = args.directory.resolve()
    if not root.is_dir():
        parser.error("the selected directory is not available")

    violations = find_violations(root)
    if violations:
        print("Preview boundary check failed:")
        for violation in violations:
            print(f"- {violation}")
        return 1

    print("Preview boundary check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
