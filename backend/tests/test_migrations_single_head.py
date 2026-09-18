"""Alembic 单头守卫（G2/G8 双头事故防线）。

背景：2026-09 集成期两个 agent 各自建迁移 parented 同一节点（0150e391736a），
alembic 双头潜伏数周无人发现，最终 G8 收敛时才显性化。本测试保证迁移链
任意时刻恰好一个 head；失败信息直接给出分叉点（单父多子节点），免去人工
排查。注意：历史上已合并的分叉点（分叉后接 merge 迁移）是合法 DAG 形态，
不构成失败——唯一的门是 heads 恰好为 1。

配套：scripts/devtools/orm_migration_audit.py（三方列集审计，含整链重放）；
Makefile db-migrate 里的 head 计数检查是部署侧第二道闸，本测试是提交侧闸门。
"""
from __future__ import annotations

from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_DIR = BACKEND_ROOT / "alembic"


def _script_directory():
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
    except ModuleNotFoundError as exc:  # pragma: no cover
        pytest.skip(f"Alembic not installed: {exc}")
    config = Config(str(ALEMBIC_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    return ScriptDirectory.from_config(config)


def _branch_points(script) -> dict[str, list[str]]:
    """返回所有单父多子的分叉点：{down_revision: [child, ...]}。"""
    children: dict[str, list[str]] = {}
    for revision in script.walk_revisions("base", "heads"):
        down = revision.down_revision
        if down is None:
            continue
        downs = list(down) if isinstance(down, tuple) else [down]
        for d in downs:
            children.setdefault(d, []).append(revision.revision)
    return {parent: kids for parent, kids in children.items() if len(kids) > 1}


def test_alembic_has_exactly_one_head() -> None:
    """迁移链必须恰好 1 个 head——双头即失败（G2/G8 事故回归防线）。"""
    script = _script_directory()
    heads = script.get_heads()
    assert len(heads) == 1, (
        f"alembic 双头/多头（{len(heads)} 个）: {sorted(heads)}。"
        f"分叉点（单父多子）: {_branch_points(script)}。"
        f"禁止并行挂链：新迁移的 down_revision 必须指向当前唯一 head。"
        f"修复方式：新增 merge 迁移（alembic merge -m ... <headA> <headB>）或"
        f"把其中一条链的 down_revision 改挂到另一条链的头。"
    )


def test_alembic_revisions_unique_and_resolvable() -> None:
    """revision id 无重复且整条链可从 base 走到 head（坏 down_revision 即失败）。"""
    script = _script_directory()
    revisions = [r.revision for r in script.walk_revisions()]
    assert len(revisions) == len(set(revisions)), "alembic revision id 重复"
    # get_heads() 成功本身就要求图可解析；这里显式走一遍以给出更直白的报错。
    assert script.get_heads(), "alembic 链为空/不可解析"
