"""WT364 卡 R2-B：plan_context ↔ prompts ↔ context_pack 循环 import 冒烟测试。

环拓扑（台账 C-01，WT355-HUNT-R2 H3 独立复现）::

    app.core.plan_context
      → app.models（__init__ 第 111 行 community_privacy）
      → app.aurora.runtime_v1/__init__（186 checkpoint_runtime / 221 chat_adapter）
      → app.aurora.runtime_v1.chat_adapter:20
      → app.orchestration.prompts
      → prompts:44 `from app.core.plan_context import merge_plan_context`
      → partially initialized app.core.plan_context → ImportError

修复方式（本卡）：prompts.py 对 merge_plan_context 改为函数内延迟导入，
打断 prompts→plan_context 这一条模块级边；不改变任何函数行为/签名。

本测试必须用 subprocess 干净进程复现三入口——tests/conftest.py 顶层预载
app.models，测试进程内 import 会因加载顺序不同而假绿，进程内断言无效。

三入口在干净进程 import 成功即 C-01 的可证伪判据；若回归（任何一入口
exit≠0），对应用例失败并回传 stderr。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]

# 台账 C-01 三个独立复现入口（WT355-HUNT-R2 REPORT.md H3 节）
CYCLE_ENTRY_POINTS = [
    "app.core.plan_context",
    "app.orchestration.prompts",
    "app.core.context_pack",
]


@pytest.mark.parametrize("entry_point", CYCLE_ENTRY_POINTS)
def test_clean_process_import_succeeds(entry_point: str) -> None:
    """干净进程 `python -c "import <entry>"` 必须 exit 0（C-01 冒烟判据）。"""
    env = dict(os.environ)
    # worktree 无 .env 属正常；app.config 必填项给最小测试值即可
    env.setdefault("SECRET_KEY", "wt364-r2b-import-smoke-test-key")

    result = subprocess.run(
        [sys.executable, "-c", f"import {entry_point}"],
        cwd=BACKEND_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )

    assert result.returncode == 0, (
        f"干净进程 import {entry_point} 失败（exit={result.returncode}），"
        f"疑似循环 import 回归（C-01）:\n{result.stderr[-3000:]}"
    )
