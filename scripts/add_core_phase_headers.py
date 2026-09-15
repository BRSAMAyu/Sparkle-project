#!/usr/bin/env python3
from __future__ import annotations

import argparse
import collections
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIMIT = 50
PYTHON_HEADER = '''"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>
"""

'''
GO_HEADER = '''/*
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>
*/

'''


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add Core/Phase headers to the hottest backend files.")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    return parser.parse_args()


def _candidate_files() -> list[Path]:
    files: list[Path] = []
    for root, suffix in ((REPO_ROOT / "backend/app", ".py"), (REPO_ROOT / "backend/gateway", ".go")):
        for path in root.rglob(f"*{suffix}"):
            if any(part in {"__pycache__", "gen", "vendor"} for part in path.parts):
                continue
            head = "\n".join(path.read_text(encoding="utf-8").splitlines()[:5])
            if "Code generated" in head and "DO NOT EDIT" in head:
                continue
            files.append(path)
    return files


def _hot_files(limit: int) -> list[Path]:
    candidates = {path.relative_to(REPO_ROOT).as_posix(): path for path in _candidate_files()}
    result = subprocess.run(
        ["git", "log", "--format=", "--name-only", "--", "backend/app", "backend/gateway"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    counter: collections.Counter[str] = collections.Counter()
    for raw in result.stdout.splitlines():
        path = raw.strip()
        if path in candidates:
            counter[path] += 1
    ranked = sorted(candidates, key=lambda item: (-counter[item], item))
    return [candidates[item] for item in ranked[: max(1, limit)]]


def _has_header(text: str) -> bool:
    head = "\n".join(text.splitlines()[:20])
    return all(token in head for token in ("Core:", "Phase:", "Stage:"))


def _python_header_body() -> str:
    return "\n".join(
        (
            "Core: <cognitive|execution|bridge|infra>",
            "Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>",
            "Stage: <首次引入 Stage 号>",
        )
    )


def _render_python_docstring(body: str) -> str:
    normalized = body.strip("\n")
    return f'"""\n{normalized}\n"""\n\n'


def _extract_docstring(lines: list[str], start: int) -> tuple[int, int, str] | None:
    idx = start
    while idx < len(lines) and lines[idx].strip() == "":
        idx += 1
    if idx >= len(lines):
        return None

    stripped = lines[idx].lstrip()
    quote = None
    if stripped.startswith('"""'):
        quote = '"""'
    elif stripped.startswith("'''"):
        quote = "'''"
    if quote is None:
        return None

    start_col = lines[idx].find(quote)
    remainder = lines[idx][start_col + len(quote):]
    end_col = remainder.find(quote)
    if end_col != -1:
        return idx, idx + 1, remainder[:end_col]

    chunks = [remainder]
    cursor = idx + 1
    while cursor < len(lines):
        end_col = lines[cursor].find(quote)
        if end_col != -1:
            chunks.append(lines[cursor][:end_col])
            return idx, cursor + 1, "".join(chunks)
        chunks.append(lines[cursor])
        cursor += 1
    return None


def _insert_python_header(text: str) -> str:
    lines = text.splitlines(keepends=True)
    idx = 0
    if lines and lines[0].startswith("#!"):
        idx = 1
    if idx < len(lines) and lines[idx].startswith("# -*-"):
        idx += 1

    docstring = _extract_docstring(lines, idx)
    header_body = _python_header_body()
    if docstring is None:
        return "".join(lines[:idx]) + PYTHON_HEADER + "".join(lines[idx:])

    start, end, body = docstring
    has_header = all(token in body for token in ("Core:", "Phase:", "Stage:"))
    second_docstring = _extract_docstring(lines, end)
    if has_header and second_docstring is not None:
        next_start, next_end, next_body = second_docstring
        if not any(line.strip() for line in lines[end:next_start]):
            merged = body.rstrip() + "\n\n" + next_body.strip("\n")
            return "".join(lines[:start]) + _render_python_docstring(merged) + "".join(lines[next_end:])
    if has_header:
        return text

    merged = header_body + "\n\n" + body.strip("\n")
    return "".join(lines[:start]) + _render_python_docstring(merged) + "".join(lines[end:])


def _insert_go_header(text: str) -> str:
    if _has_header(text):
        return text
    return GO_HEADER + text


def main() -> int:
    args = parse_args()
    changed: list[str] = []
    for path in _hot_files(args.limit):
        original = path.read_text(encoding="utf-8")
        updated = _insert_python_header(original) if path.suffix == ".py" else _insert_go_header(original)
        if updated == original:
            continue
        path.write_text(updated, encoding="utf-8")
        changed.append(path.relative_to(REPO_ROOT).as_posix())

    print(f"added headers to {len(changed)} files")
    for item in changed:
        print(item)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
