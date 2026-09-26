#!/usr/bin/env python3
"""ledger_union_merge.py 工具测试（V3-FIX-268；V3-FIX-278/282 防再发强化）。

覆盖面（对应卡片验收项）：
① 新增行存活——246/247 吞行事故复现；
② 同 ID 行状态进化取本（OPEN→FIXED，非纯长度）；
③ 非表格行零丢失；
④ --renumber 撞号重编号（含注记后缀与行内引用保护）；
⑤ --check 吞行/标记残留检测；
⑥ 257 吞行事故形态重建——ID 仍在场（粘连进邻行）时行数对账兜底报警；
⑦ 263 并行回退形态——回退长行胜出后 8 裸管形态校验点名；
⑧ 8 管畸形检出——多数行容差与 --expect-pipes/--strict-pipes 阈值；
⑨ --verify 独立体检——合成台账全绿 + 畸形四类点名 + 真台账只读自检；
⑩ 转义管感知（wt578）——\\| 是格内字符、裸 | 才是列界：状态格不误报、
ID 提取不受损、含转义管行 union-merge 正确合成、真措辞项仍被点名。

用构造的最小台账样本为主，真台账只读跑 verify（自适配 wt561 存量收口）。
运行：
    pytest scripts/devtools/test_ledger_union_merge.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

import ledger_union_merge as lum

SCRIPT = Path(__file__).resolve().parent / "ledger_union_merge.py"
REAL_LEDGER = Path(__file__).resolve().parents[2] / "v3/06_agent_fleet/DYNAMIC_ISSUES.md"

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


# ---------------------------------------------------------------------------
# ⑥ V3-FIX-278/282 强化面：257 吞行事故形态重建
# ---------------------------------------------------------------------------
def _accounting_like(outcome, text):
    """以 outcome 的对账口径构造新 MergeOutcome（用于事后篡改形态检测）。"""
    return lum.MergeOutcome(
        text=text,
        ours_lines=outcome.ours_lines,
        theirs_lines=outcome.theirs_lines,
        overlap_lines=outcome.overlap_lines,
        expected_lines=outcome.expected_lines,
    )


def test_incident_257_row_swallow_glued_into_neighbor():
    """257 事故形态重建（3896a1b5）：257 闭账行整行被粘连进相邻 258 行内。

    该形态下 V3-FIX-257 token 仍在全文（afbfdef2 关键词留在 258 行格内），
    ID 差集法不报警——正是行数对账（精确期望）兜底的对象。
    """
    row257 = row(257, "OPEN→FIXED@afbfdef2", desc="guest 转正种子清洗闭账（含裁决 A 记录）")
    row258 = row(258, "OPEN")
    theirs258 = row(258, "OPEN", desc="净版重建（集成侧）")
    text = HEADER + conflict(row257 + row258 + "### 集成批注\n", theirs258 + "### 集成批注\n")

    outcome = lum.merge_text(text)
    # 干净合并：全部检测绿
    assert lum.verify_merge(outcome.text, outcome.ours_ids, outcome.theirs_ids) == []
    assert lum.verify_line_accounting(outcome) == []
    assert "| V3-FIX-257 |" in outcome.text

    # 事故形态：257 行删除、其内容粘连进 258 行格内（ID token 仍在场）
    lines = outcome.text.splitlines(keepends=True)
    glued = []
    for line in lines:
        if "| V3-FIX-257 |" in line:
            continue  # 整行吞失
        if "| V3-FIX-258 |" in line:
            line = line.replace("集成侧）", f"集成侧；粘连体：{row257.strip()}）")
        glued.append(line)
    swallowed_text = "".join(glued)

    # ID 差集法沉默（token 仍在场）——事故当时无人发现的原因
    assert lum.verify_merge(swallowed_text, outcome.ours_ids, outcome.theirs_ids) == []
    # 行数对账点名
    problems = lum.verify_line_accounting(_accounting_like(outcome, swallowed_text))
    assert problems and "精确期望" in problems[0]

    # 对照：整行删除（token 一并消失）时 ID 差集与对账双报警
    dropped_text = outcome.text.replace(row257, "")
    assert any("V3-FIX-257" in p for p in lum.verify_merge(dropped_text, outcome.ours_ids, outcome.theirs_ids))
    assert lum.verify_line_accounting(_accounting_like(outcome, dropped_text))


# ---------------------------------------------------------------------------
# ⑦ 263 并行回退形态：回退长行胜出（同状态取长者）→ 8 管校验点名
# ---------------------------------------------------------------------------
def test_incident_263_parallel_rollback_shape_detected():
    """263 事故形态（62f20b0b）：R1 修复后的 8 管行被并行登记的 11 管长行
    逐字节回退。_pick 同状态取长者 → 坏形行胜出（机制如实复现），
    强化后的 8 裸管形态校验在合并输出上点名该行。
    """
    repaired = row(263, "FIXED@c9cf78f8", desc="无幻影列 8 管规范化重建")
    reverted = (
        "| V3-FIX-263 | P4 | mypy 批四烧减（回退形态） a| b 幻影列 c| d 再补"
        " e| f| g 三处（与当年 11 裸管坏形同构） | ev | T-mypy-batch4 | FIXED@c9cf78f8 |\n"
    )
    assert lum.bare_pipe_count(reverted.rstrip()) == 11
    assert len(reverted) > len(repaired)  # 回退行更长——当年胜出的原因
    # 足量 8 管行锚定多数形态
    text = HEADER + "".join(row(n) for n in (260, 261, 262)) + conflict(repaired, reverted)

    outcome = lum.merge_text(text)
    # 机制复现断言：同状态取长者 → 回退行胜出
    assert "回退形态" in outcome.text and "8 管规范化重建" not in outcome.text
    # 形态校验点名（多数形态 8，回退行 11 管 FAIL）
    problems, stats = lum.check_row_shapes(outcome.text)
    assert stats["majority"] == 8
    assert any("V3-FIX-263" in p and "11" in p for p in problems)


# ---------------------------------------------------------------------------
# ⑧ 8 管畸形检出：多数容差与阈值配置
# ---------------------------------------------------------------------------
def _pipe_row(num, pipes, status="OPEN"):
    """构造指定裸管数的表格行（7=缺尾管、9+=幻影列、8=规范）。"""
    base = f"| V3-FIX-{num} | P3 | journey-{num} | 描述 | 证据 | T-task | {status} |"
    assert pipes >= 7
    if pipes == 8:
        return base + "\n"
    if pipes == 7:
        return base[:-2].rstrip() + "\n"  # 只去尾管：…| OPEN
    phantoms = " | ".join(f"幻影{i}" for i in range(pipes - 8))
    return base.replace(f"| {status} |", f"| {phantoms} | {status} |")


def test_shape_check_majority_tolerance_and_expect_pipes():
    three7 = _pipe_row(301, 7) + _pipe_row(302, 7) + _pipe_row(303, 7)
    one8 = _pipe_row(304, 8)
    one9 = _pipe_row(305, 9)
    text = HEADER + three7 + one8 + one9

    # 默认（容差开）：合法形态 = {期望 8, 多数 7} → 9 管独 FAILED
    problems, stats = lum.check_row_shapes(text)
    assert stats["majority"] == 7 and stats["expect"] == 8
    assert [p for p in problems if "V3-FIX-301" in p or "V3-FIX-302" in p] == []
    assert any("V3-FIX-305" in p and "9" in p for p in problems)
    assert len(problems) == 1

    # --strict-pipes（容差关）：7 管三行也 FAIL
    problems_strict, _ = lum.check_row_shapes(text, majority_tolerance=False)
    assert len(problems_strict) == 4

    # --expect-pipes 7（期望改 7，容差开）：8 管与 9 管 FAIL
    problems_7, stats_7 = lum.check_row_shapes(text, expect_pipes=7)
    assert stats_7["expect"] == 7
    assert len(problems_7) == 2
    assert any("V3-FIX-304" in p for p in problems_7)


# ---------------------------------------------------------------------------
# ⑨ --verify 独立体检
# ---------------------------------------------------------------------------
def _clean_ledger():
    rows = "".join(
        [
            row(401, "OPEN"),
            row(402, "FIXED@abcd123"),
            row(403, "CLOSED@v1.2"),
            row(404, "WONTFIX（拍板不修）"),
        ]
    )
    return HEADER + rows + "\n收尾段落\n"


def test_verify_ledger_file_green_on_wellformed():
    problems, stats = lum.verify_ledger_file(_clean_ledger())
    assert problems == []
    assert stats["checked"] == 4 and stats["majority"] == 8


def test_verify_ledger_file_names_all_four_defect_classes():
    base = _clean_ledger()
    lines = base.splitlines(keepends=True)
    # ① 冲突标记残留
    with_marker = base + ">>>>>>> wt-x\n"
    problems, _ = lum.verify_ledger_file(with_marker)
    assert any("冲突标记残留" in p for p in problems)
    # ② 行首锚定 ID 重号（233 双行形态）
    dup = HEADER + row(233, "OPEN（陈旧行）") + row(233, "FIXED@5caa5355（权威行）")
    problems, _ = lum.verify_ledger_file(dup)
    assert any("V3-FIX-233" in p and "重号" in p for p in problems)
    # ③ 行尾状态枚举非法（形态合法行）：裸 FIXED 无 @sha、非法 DONE
    bad_status = HEADER + _pipe_row(501, 8, status="DONE（拍板）")
    problems, _ = lum.verify_ledger_file(bad_status)
    assert any("V3-FIX-501" in p and "状态格非法" in p for p in problems)
    bad_fixed = HEADER + _pipe_row(502, 8, status="FIXED")
    problems, _ = lum.verify_ledger_file(bad_fixed)
    assert any("V3-FIX-502" in p and "状态格非法" in p for p in problems)
    # ④ 粘连行（两行挤一行 15 管）：形态点名且不对该行重复报状态
    glued = lines[0] + lines[1].rstrip("\n") + " " + lines[2].lstrip("| ")  # 401 行 + 402 行粘连
    glued_ledger = glued + lines[3] + lines[4]
    problems, _ = lum.verify_ledger_file(glued_ledger)
    assert any("V3-FIX-401" in p and "裸管数" in p for p in problems)
    assert not any("状态格非法" in p for p in problems)  # 粘连行跳过状态扫描


def test_verify_real_ledger_readonly_and_reports_known_stock():
    """真台账只读体检：文件零改动；存量（279 行粘连/233 双行等）在案必被
    点名，存量收口（wt561 集成）后须全绿——自适配断言，不伪造通过。"""
    if not REAL_LEDGER.exists():
        pytest.skip("真台账不在本树")
    before = REAL_LEDGER.read_bytes()
    text = before.decode("utf-8")
    problems, stats = lum.verify_ledger_file(text)
    assert REAL_LEDGER.read_bytes() == before  # 只读实证
    assert stats["checked"] > 0

    legacy_glue = any("裸管数 15" in p or "裸管数 14" in p for p in problems)
    legacy_dup = any("V3-FIX-233" in p and "重号" in p for p in problems)
    if legacy_glue or legacy_dup:
        # 存量在案：粘连 4 处（201+179/214+179/239+221/220+231）与 233 双行
        # 必须被点名——若漏报即检测器失效
        assert legacy_dup, "233 双行在案但重号检测未命中"
        assert legacy_glue, "粘连行在案但形态检测未命中"
    else:
        # 存量已收口（wt561 集成后）：R2 标的（真粘连=一行双 ID、重号）须零发现；
        # 历史 6/7 管原生形态按 wt561 裁定容忍（其问题串通用后缀含"粘连"字样，
        # 不能按子串过滤——用结构判据：一行内出现 ≥2 个 V3-FIX-N 才是真粘连）。
        dup = [x for x in problems if "重号" in x]
        glue = [
            ln
            for ln in text.splitlines()
            if ln.startswith("| V3-FIX-")
            and len(re.findall(r"\| V3-FIX-\d+ \|", ln)) >= 2
        ]
        assert not dup, f"R2 收口后仍有重号：{dup[:3]}"
        assert not glue, f"R2 收口后仍有一行双 ID 粘连：{glue[:2]}"

    # wt578 转义管感知：状态格含 \| 且裸管口径下状态合法的行不得被点名
    # （回归守卫——若退回全管切分，行尾碎片会重新被误报为状态非法）
    for lineno, line in enumerate(text.splitlines(), 1):
        if lum.row_id(line) is None or "\\|" not in line:
            continue
        if lum.status_cell(line).startswith(lum.LEGAL_STATUS_PREFIXES):
            offenders = [p for p in problems if f"第 {lineno} 行" in p and "状态格非法" in p]
            assert not offenders, f"第 {lineno} 行转义管状态格被误报：{offenders}"


def test_cli_verify_mode(tmp_path):
    green = tmp_path / "green.md"
    green.write_text(_clean_ledger(), encoding="utf-8")
    proc = _run_cli(["--verify", str(green)], "")
    assert proc.returncode == 0, proc.stderr
    assert "verify 通过" in proc.stderr

    dirty = tmp_path / "dirty.md"
    dirty.write_text(HEADER + row(1, "DONE"), encoding="utf-8")
    proc = _run_cli(["--verify", str(dirty)], "")
    assert proc.returncode == 1
    assert "状态格非法" in proc.stderr

    # --verify 与位置输入互斥 → 用法错误
    proc = _run_cli(["--verify", str(green), str(dirty)], "")
    assert proc.returncode == 2


# ---------------------------------------------------------------------------
# ⑩ 转义管感知（wt578）：\| 是格内字符、裸 | 才是列界
# ---------------------------------------------------------------------------
def escaped_row(num, status="OPEN"):
    """台账实录形态的转义管行：状态格含 ``\\|`` 分诊注记 + 描述格含类型注记。"""
    return (
        f"| V3-FIX-{num} | P3 | journey-{num} | 描述含类型注记 str\\|None | ev-{num}"
        f" | T-task | {status} [wt474分诊:备忘型\\|抽查仍存活，随评测迭代] |\n"
    )


def test_status_cell_keeps_escaped_pipe_whole_not_misreported():
    """状态格含转义管（\\|）时不按转义管误断：整格提取、状态合法、不进 verify FAIL。"""
    line = escaped_row(310).rstrip("\n")
    cell = lum.status_cell(line)
    assert cell.startswith("OPEN [wt474分诊:备忘型\\|")
    assert "抽查仍存活" in cell
    # 与形态计数同口径：裸管 8（转义管不计），verify 全绿
    assert lum.bare_pipe_count(line) == 8
    problems, stats = lum.verify_ledger_file(HEADER + escaped_row(310))
    assert problems == []
    assert stats["checked"] == 1 and stats["majority"] == 8


def test_id_extraction_unbroken_by_in_cell_escaped_pipes():
    """格内转义管不破坏 ID 提取与重号检测（str\\|None 类注记行）。"""
    line = escaped_row(311).rstrip("\n")
    assert lum.row_id(line) == "V3-FIX-311"
    dup_text = HEADER + escaped_row(311) + escaped_row(311)
    problems = lum.check_duplicate_ids(dup_text)
    assert any("V3-FIX-311" in p and "重号" in p for p in problems)


def test_union_merge_escaped_pipe_rows_synthesized_correctly():
    """两侧均含转义管的冲突块：进化裁决、转义格原样存活、全链检测绿。"""
    ours = escaped_row(320, "OPEN")
    theirs = (
        "| V3-FIX-320 | P3 | journey-320 | 集成侧净版（str\\|None 注记改写） | ev-320"
        " | T-task | FIXED@beefcafe（分诊收口） |\n"
    )
    outcome = lum.merge_text(HEADER + conflict(ours, theirs))
    # 同 ID 进化裁决取 theirs FIXED，ours 转义长行让位（非纯长度）
    assert "FIXED@beefcafe（分诊收口）" in outcome.text
    assert "wt474分诊:备忘型" not in outcome.text
    assert "集成侧净版（str\\|None 注记改写）" in outcome.text
    assert lum.verify_merge(outcome.text, outcome.ours_ids, outcome.theirs_ids) == []
    assert lum.verify_line_accounting(outcome) == []
    shape_problems, _ = lum.check_row_shapes(outcome.text)
    assert shape_problems == []
    assert lum.check_status_enum(outcome.text) == []


def test_renumber_note_lands_in_third_column_despite_escaped_pipes():
    """撞号重编号注记落位按裸管列口径：格含转义管（\\|）时不错位进格中。"""
    theirs_row = (
        "| V3-FIX-265 | P3 | journey-265 | 描述含 str\\|None 注记的撞号行 | ev | T-worker | OPEN |\n"
    )
    ours_row = row(265, "OPEN", desc="集成侧先到先得行")
    outcome = lum.merge_text(HEADER + conflict(ours_row, theirs_row), renumber={"265": "267"})
    # 注记置于第三个实际列（Journey 格）开头（转义管不构成列界、不错位进格中）
    assert (
        "| V3-FIX-267 | P3 |（集成重编号：原登记 V3-FIX-265，撞号顺延 V3-FIX-267） journey-265"
        " | 描述含 str\\|None 注记的撞号行 |" in outcome.text
    )
    assert "str\\|None 注记的撞号行 | ev |" in outcome.text  # 描述格原样未被注记劈开
    # 重排后行仍 8 裸管、状态枚举合法
    shape_problems, _ = lum.check_row_shapes(outcome.text)
    assert shape_problems == []
    assert lum.check_status_enum(outcome.text) == []


def test_cli_verify_escaped_rows_pass_but_real_wording_still_fails(tmp_path):
    """--verify 对转义行不再 FAIL，对真措辞项（裸 FIXED 无 @sha）仍 FAIL。"""
    ledger = HEADER + escaped_row(330) + escaped_row(331, "WONTFIX") + row(332, "OPEN")

    green = tmp_path / "escaped.md"
    green.write_text(ledger, encoding="utf-8")
    proc = _run_cli(["--verify", str(green)], "")
    assert proc.returncode == 0, proc.stderr
    assert "verify 通过" in proc.stderr

    dirty = tmp_path / "real_wording.md"
    dirty.write_text(ledger + row(333, "FIXED"), encoding="utf-8")
    proc = _run_cli(["--verify", str(dirty)], "")
    assert proc.returncode == 1
    fail_lines = proc.stderr.splitlines()
    assert any("V3-FIX-333" in ln and "状态格非法" in ln for ln in fail_lines)
    # 转义行不被点名（升级不把误报换个地方留下）
    assert not any("V3-FIX-330" in ln or "V3-FIX-331" in ln for ln in fail_lines)
