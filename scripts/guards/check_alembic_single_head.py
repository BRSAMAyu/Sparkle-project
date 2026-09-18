#!/usr/bin/env python3
"""守卫：alembic 迁移链必须恰好 1 个 head（G2/G8 双头事故防线，提交侧闸门）。

背景：2026-09 两个 agent 并行建迁移 parented 同一节点（0150e391736a），双头
潜伏数周无人发现。Makefile db-migrate 的 head 计数是部署侧闸；本守卫 +
backend/tests/test_migrations_single_head.py 是提交侧闸（rule_guard_manifest
登记名 DB-HEAD）。纯脚本目录解析，不需要数据库连接。

退出码：0 = 单头；1 = 双头/多头或链不可解析。
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_DIR = REPO_ROOT / "backend" / "alembic"


def main() -> int:
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
    except ModuleNotFoundError as exc:
        print(f"环境错误: alembic 未安装: {exc}", file=sys.stderr)
        return 2

    config = Config(str(ALEMBIC_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    script = ScriptDirectory.from_config(config)

    try:
        heads = sorted(script.get_heads())
    except Exception as exc:  # noqa: BLE001 — 链损坏（坏 down_revision 等）
        print(f"❌ alembic 链不可解析: {exc}")
        return 1

    if len(heads) == 1:
        print(f"✅ alembic 单头: {heads[0]}")
        return 0

    children: dict[str, list[str]] = {}
    for revision in script.walk_revisions("base", "heads"):
        down = revision.down_revision
        if down is None:
            continue
        downs = list(down) if isinstance(down, tuple) else [down]
        for d in downs:
            children.setdefault(d, []).append(revision.revision)
    branch_points = {p: k for p, k in children.items() if len(k) > 1}
    print(f"❌ alembic 双头/多头（{len(heads)} 个）: {heads}")
    print(f"   分叉点（单父多子）: {branch_points}")
    print("   修复：alembic merge -m 'merge heads' <headA> <headB>，或改挂 down_revision。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
