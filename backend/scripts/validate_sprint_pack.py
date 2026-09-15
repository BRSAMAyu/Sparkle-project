#!/usr/bin/env python3
"""Validate a Sprint Pack JSON file against the SprintPackV1 schema."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import ValidationError


def _find_backend_root(start: Path) -> Path:
    for path in [start, *start.parents]:
        if (path / "app").is_dir() and (path / "pyproject.toml").exists():
            return path
    return Path(__file__).resolve().parents[1]


BACKEND_ROOT = _find_backend_root(Path(__file__).resolve())
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.sprint_packs.sprint_pack_schema import SprintPackV1  # noqa: E402


def _resolve_input_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if path.exists():
        return path

    backend_relative = BACKEND_ROOT / path
    if backend_relative.exists():
        return backend_relative

    parts = path.parts
    if parts and parts[0] == "backend":
        stripped = BACKEND_ROOT / Path(*parts[1:])
        if stripped.exists():
            return stripped

    return path


def _format_loc(loc: tuple[Any, ...]) -> str:
    rendered = ""
    for part in loc:
        if isinstance(part, int):
            rendered += f"[{part}]"
        else:
            rendered = f"{rendered}.{part}" if rendered else str(part)
    return rendered


def _node_id_for(data: Any, index: int) -> str:
    if isinstance(data, dict):
        nodes = data.get("knowledge_nodes")
        if isinstance(nodes, list) and 0 <= index < len(nodes):
            node = nodes[index]
            if isinstance(node, dict):
                node_id = node.get("node_id")
                if isinstance(node_id, str) and node_id:
                    return node_id
    return f"knowledge_nodes[{index}]"


def _format_validation_error(exc: ValidationError, data: Any) -> str:
    error = exc.errors()[0]
    loc = tuple(error.get("loc", ()))
    error_type = str(error.get("type", ""))
    message = str(error.get("msg", "validation error"))

    if error_type == "missing":
        field = str(loc[-1]) if loc else "unknown"
        if len(loc) >= 3 and loc[0] == "knowledge_nodes" and isinstance(loc[1], int):
            node_id = _node_id_for(data, loc[1])
            return f"field '{field}' missing in node {node_id}"
        if len(loc) == 1:
            return f"field '{field}' missing"
        return f"field '{field}' missing at {_format_loc(loc[:-1])}"

    location = _format_loc(loc) if loc else "input"
    return f"field '{location}' invalid: {message}"


def validate_file(path: Path) -> tuple[bool, str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return False, f"file not found: {path}"
    except json.JSONDecodeError as exc:
        return (
            False,
            f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}",
        )
    except OSError as exc:
        return False, f"cannot read file: {exc}"

    try:
        pack = SprintPackV1.model_validate(payload)
    except ValidationError as exc:
        return False, _format_validation_error(exc, payload)

    return (
        True,
        (
            f"{path.name} — {len(pack.knowledge_nodes)} nodes, "
            f"{len(pack.mistake_types)} mistakes, {len(pack.question_archetypes)} archetypes"
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a Sprint Pack JSON file.")
    parser.add_argument("pack_path", help="Path to the Sprint Pack JSON file.")
    args = parser.parse_args(argv)

    path = _resolve_input_path(args.pack_path)
    valid, detail = validate_file(path)
    if valid:
        print(f"✅ VALID: {detail}")
        return 0

    print(f"❌ INVALID: {detail}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
