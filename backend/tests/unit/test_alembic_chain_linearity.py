from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
VERSIONS_DIR = REPO_ROOT / "backend/alembic/versions"


def _read_revision_metadata() -> dict[str, tuple[str, ...]]:
    metadata: dict[str, tuple[str, ...]] = {}
    for path in VERSIONS_DIR.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        revision = None
        down_revision: tuple[str, ...] = ()
        for node in tree.body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = node.value
            for target in targets:
                if not isinstance(target, ast.Name):
                    continue
                if target.id == "revision" and isinstance(value, ast.Constant):
                    revision = str(value.value)
                if target.id == "down_revision":
                    if isinstance(value, ast.Constant) and value.value:
                        down_revision = (str(value.value),)
                    elif isinstance(value, ast.Tuple):
                        down_revision = tuple(
                            str(item.value)
                            for item in value.elts
                            if isinstance(item, ast.Constant) and item.value
                        )
        if revision is not None:
            metadata[revision] = down_revision
    return metadata


def _children_map(metadata: dict[str, tuple[str, ...]]) -> dict[str, set[str]]:
    children: dict[str, set[str]] = {revision: set() for revision in metadata}
    for revision, parents in metadata.items():
        for parent in parents:
            children.setdefault(parent, set()).add(revision)
    return children


def _ancestor_closure(metadata: dict[str, tuple[str, ...]], revision: str) -> set[str]:
    seen: set[str] = set()
    stack = [revision]
    while stack:
        current = stack.pop()
        for parent in metadata.get(current, ()):
            if parent in seen:
                continue
            seen.add(parent)
            stack.append(parent)
    return seen


def test_alembic_revision_graph_has_no_orphan_references() -> None:
    metadata = _read_revision_metadata()
    missing = sorted(
        {
            parent
            for parents in metadata.values()
            for parent in parents
            if parent not in metadata
        }
    )
    assert missing == []


def test_alembic_stage29_5_merge_is_the_single_head() -> None:
    metadata = _read_revision_metadata()
    children = _children_map(metadata)
    heads = sorted(revision for revision, dependents in children.items() if not dependents)
    assert len(heads) == 1
    head = heads[0]
    ancestors = _ancestor_closure(metadata, head)
    assert "s295a1b2c3d4" in ancestors or head == "s295a1b2c3d4"
    assert "stage38_06_add_vector_hnsw_indexes" in ancestors or head == "stage38_06_add_vector_hnsw_indexes"
    assert "s39b1c2d3e4" in ancestors or head == "s39b1c2d3e4"


def test_alembic_stage29_5_head_includes_stage19_and_stage22_backfills() -> None:
    metadata = _read_revision_metadata()
    ancestors = _ancestor_closure(metadata, "s295a1b2c3d4")
    assert "s19c1d2e3f4" in ancestors
    assert "s22c1d2e3f4" in ancestors
    assert "s29a1b2c3d4" in ancestors
