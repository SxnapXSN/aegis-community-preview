"""Command-line entry point for the local-only Community Preview."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .task_contract import TaskEnvelope, TaskValidationError, build_execution_brief


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a local task envelope and print a conservative JSON brief."
    )
    parser.add_argument("--input", required=True, type=Path, help="Path to a JSON task file")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        task = TaskEnvelope.from_mapping(payload)
    except (OSError, json.JSONDecodeError, TaskValidationError) as error:
        raise SystemExit(f"Input error: {error}") from error

    print(json.dumps(build_execution_brief(task), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
