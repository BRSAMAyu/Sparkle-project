#!/usr/bin/env python3
"""ledger_union_merge.py 工具测试（V3-FIX-268）。

覆盖面（对应卡片验收五项）：
① 新增行存活——246/247 吞行事故复现；
② 同 ID 行状态进化取本（OPEN→FIXED，非纯长度）；
③ 非表格行零丢失；
④ --renumber 撞号重编号（含注记后缀与行内引用保护）；
⑤ --check 吞行/标记残留检测。

用构造的最小台账样本，不依赖真实台账。运行：
    pytest scripts/devtools/test_ledger_union_merge.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import ledger_union_merge as lum

SCRIPT = Path(__file__).resolve().parent / "ledger_union_merge.py"

HEADER = "| ID | Severity | Journey | Reproduction | Evidence | Owner task | Status |\n|---|---|---|---|---|---|---|\n"


def row(num, status="OPEN", desc="描述", sev="P3", task="T-task"):
    return f"| V3-FIX-{num} | {sev} | journey-{num} | {desc} | evidence-{num} | {task} | {status} |\n"


def conflict(ours, theirs, label="wt-worker"):
    return f"<<<<<<< HEAD\n{ours}=======\n{theirs}>>>>>>> {label}\n"


# ① 吞行事故复现：worker 新增的 246/247 整行必须存活
# （临时件根因：非表格行按出现序编 _rawN 键，两侧同序号跨侧碰撞取长者）
def test_new_worker_rows_survive_incident_246_247():
    ours = row(251, "OPEN") + "### 集成批注：批三收尾\n"
    theirs = "### 批次注记：l10n 批二\n" + row(246) + row(247)
    text = HEADER + row(245, "FIXED@abc1234") + conflict(ours, theirs)

    outcome = lum.merge_text(text)

    assert "V3-FIX-245" in outcome.text
    assert "| V3-FIX-246 |" in outcome.text
    assert "| V3-FIX-247 |" in outcome.text
    assert "| V3-FIX-251 |" in outcome.text
    # 非表格行双侧都在（旧临时件会丢其一）
    assert "### 集成批注：批三收尾" in outcome.text
    assert "### 批次注记：l10n 批二" in outcome.text
    # 零标记残留
    assert lum.verify_merge(outcome.text, outcome.ours_ids, outcome.theirs_ids) == []


# ② 同 ID 双版本取状态更进化者；长度只作同级平局裁断
def test_same_id_open_to_fixed_evolution_not_pure_length():
    long_open = row(100, "OPEN", desc="超长描述" * 60)
    short_fixed = row(100, "FIXED@deadbee", desc="短收口")
    text = HEADER + conflict(long_open, short_fixed)
    outcome = lum.merge_text(text)
    assert "FIXED@deadbee" in outcome.text
    assert "超长描述" * 60 not in outcome.text

    # 反向：ours 已 FIXED、theirs 是更长的 OPEN 陈行 → 保留 ours
    text_rev = HEADER + conflict(short_fixed, long_open)
    outcome_rev = lum.merge_text(text_rev)
    assert "FIXED@deadbee" in outcome_rev.text
    assert "超长描述" * 60 not in outcome_rev.text


def test_same_id_equal_status_takes_longer_superset():
    ours = row(101, "OPEN", desc="基线")
    theirs = row(101, "OPEN", desc="基线+集成侧补记的验收证据")
    outcome = lum.merge_text(HEADER + conflict(ours, theirs))
    assert "集成侧补记的验收证据" in outcome.text


def test_open_supplement_fixed_beats_plain_open():
    # 台账实录形态「OPEN 补记FIXED@...」（wt474 扫陈补记）进化于纯 OPEN
    ours = row(102, "OPEN", desc="长基线" * 40)
    theirs = "| V3-FIX-102 | P3 | journey-102 | 短 | ev | T-task | OPEN 补记FIXED@cafe000（扫陈已在 main） |\n"
    outcome = lum.merge_text(HEADER + conflict(ours, theirs))
    assert "OPEN 补记FIXED@cafe000" in outcome.text
    assert "长基线" * 40 not in outcome.text


# ③ 非表格行零丢失（含跨侧同文去重不双写）
def test_non_table_lines_zero_loss():
    ours = "尾注 A：ours 独有段落\n公共脚注：两分支同文行\n"
    theirs = "尾注 B：theirs 独有段落\n公共脚注：两分支同文行\n"
    outcome = lum.merge_text(HEADER + conflict(ours, theirs))
    assert "尾注 A：ours 独有段落" in outcome.text
    assert "尾注 B：theirs 独有段落" in outcome.text
    assert outcome.text.count("公共脚注：两分支同文行") == 1


# ④ 撞号重编号：theirs 侧整行 ID 替换 + 自动注记；行内引用不受牵连
def test_renumber_theirs_row_with_annotation():
    theirs_row = (
        "| V3-FIX-265 | P3 |（编号自 264 起：基线 grep 验证 256-263 全占） "
        "同族扫描新登记，引用 V3-FIX-210 与自身 V3-FIX-265 语义 | ev | T-worker | OPEN |\n"
    )
    ours_row = row(265, "OPEN", desc="集成侧先到先得行") + row(264, "FIXED@abcd123")
    text = HEADER + conflict(ours_row, theirs_row)

    outcome = lum.merge_text(text, renumber={"265": "267"})

    # ours 先到先得行原样保留
    assert "| V3-FIX-265 | P3 | journey-265 | 集成侧先到先得行 |" in outcome.text
    # theirs 行整行换成 267 并带注记
    assert "| V3-FIX-267 | P3 |（集成重编号：原登记 V3-FIX-265，撞号顺延 V3-FIX-267）" in outcome.text
    # 行内既有引用不被牵连：他人引用保留、第二个（自引用）出现不替换
    assert "引用 V3-FIX-210" in outcome.text
    assert "与自身 V3-FIX-265 语义" in outcome.text
    assert outcome.applied_renumbers == ["265=267"]


def test_renumber_repeatable_and_check_consistent():
    theirs = row(265) + row(266)
    ours = row(265, "FIXED@aaa") + row(266, "FIXED@bbb")
    outcome = lum.merge_text(HEADER + conflict(ours, theirs), renumber={"265": "268", "266": "269"})
    assert "| V3-FIX-268 |" in outcome.text
    assert "| V3-FIX-269 |" in outcome.text
    assert "| V3-FIX-265 | P3 | journey-265 | 描述 | evidence-265 | T-task | FIXED@aaa |" in outcome.text
    # 重编号后双侧 ID 仍全部在场
    assert lum.verify_merge(outcome.text, outcome.ours_ids, outcome.theirs_ids) == []


def test_renumber_bad_spec_rejected():
    import pytest

    with pytest.raises(ValueError):
        lum.parse_renumber(["265267"])
    with pytest.raises(ValueError):
        lum.parse_renumber(["abc=267"])
    with pytest.raises(ValueError):
        lum.parse_renumber(["265=265"])


# ⑤ --check 吞行检测：丢行/残留标记都要红
def test_check_detects_swallowed_row():
    ours = row(251)
    theirs = row(246) + row(247)
    outcome = lum.merge_text(HEADER + conflict(ours, theirs))
    assert lum.verify_merge(outcome.text, outcome.ours_ids, outcome.theirs_ids) == []

    # 模拟吞行：theirs 的 247 行消失
    swallowed = outcome.text.replace(row(247), "")
    problems = lum.verify_merge(swallowed, outcome.ours_ids, outcome.theirs_ids)
    assert any("V3-FIX-247" in p and "theirs" in p for p in problems)

    # ours 侧丢行同样报红
    swallowed_ours = outcome.text.replace(row(251), "")
    problems_ours = lum.verify_merge(swallowed_ours, outcome.ours_ids, outcome.theirs_ids)
    assert any("V3-FIX-251" in p and "ours" in p for p in problems_ours)


def test_check_detects_marker_residue():
    text = HEADER + conflict(row(1), row(2))
    outcome = lum.merge_text(text)
    dirty = outcome.text + "<<<<<<< HEAD\n"
    problems = lum.verify_merge(dirty, outcome.ours_ids, outcome.theirs_ids)
    assert any("冲突标记残留" in p for p in problems)


def test_no_conflict_blocks_passthrough():
    text = HEADER + row(1, "FIXED@abc") + "\n尾段\n"
    outcome = lum.merge_text(text)
    assert outcome.text == text
    assert outcome.blocks == 0
    assert lum.verify_merge(outcome.text, set(), set()) == []


def test_unterminated_block_raises():
    import pytest

    with pytest.raises(ValueError, match="未闭合"):
        lum.parse_conflicts(HEADER + "<<<<<<< HEAD\n" + row(1))


# CLI 端到端：stdin 合并、--check 通过/失败退出码
def _run_cli(args, stdin_text):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=stdin_text,
        capture_output=True,
        text=True,
    )


def test_cli_merge_via_stdin():
    text = HEADER + conflict(row(1), row(2, "FIXED@abc"))
    proc = _run_cli([], text)
    assert proc.returncode == 0, proc.stderr
    assert "| V3-FIX-1 |" in proc.stdout
    assert "| V3-FIX-2 |" in proc.stdout
    assert "FIXED@abc" in proc.stdout
    assert "<<<<<<<" not in proc.stdout


def test_cli_check_pass_and_fail(tmp_path):
    good = HEADER + conflict(row(1), row(2))
    assert _run_cli(["--check"], good).returncode == 0

    # 失败路径：正文残留游离冲突标记（解析器视为内容、verify 判残留）→ check 红
    dirty = good + ">>>>>>> wt-worker-残留\n"
    proc = _run_cli(["--check"], dirty)
    assert proc.returncode == 1
    assert "冲突标记残留" in proc.stderr

    # 已合并文件（零冲突块）进 --check：无可比对侧，提示性警告但不误报
    merged = _run_cli([], good).stdout
    proc_merged = _run_cli(["--check"], merged)
    assert proc_merged.returncode == 0
    assert "0 个冲突块" in proc_merged.stderr


def test_cli_check_writes_output_on_pass(tmp_path):
    good = HEADER + conflict(row(1), row(2))
    out_path = tmp_path / "merged.md"
    proc = _run_cli(["--check", "-o", str(out_path)], good)
    assert proc.returncode == 0
    assert "| V3-FIX-2 |" in out_path.read_text(encoding="utf-8")
