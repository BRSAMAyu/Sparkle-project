#!/usr/bin/env python3
"""舰队台账 union-merge 固化工具（V3-FIX-268；V3-FIX-278/282 防再发强化）。

针对 ``v3/06_agent_fleet/DYNAMIC_ISSUES.md`` 集成冲突的 union-merge：
按 V3-FIX-N 行 ID 做 ours/theirs 并集。固化前主会话使用临时件
``/tmp/union_merge.py``，其已知缺陷（本工具的根修对象）：

1. 吞行（≥4 次事故）：临时脚本给冲突块内非表格行按出现序编 ``_rawN``
   键，ours/theirs 两侧同序号键跨侧碰撞后"取长者"，另一侧整行
   （worker 新增的 246/247 等台账行、相邻段落）被静默丢弃。
2. 长度启发误判：同 ID 双版本"取长者"是纯长度比较；正确语义是取
   **状态更进化**者（OPEN < FIXED@/CLOSED@/WONTFIX）。
3. 撞号无辅助：并行 worker 各自登记新 FIX 号冲突（台账在册 17 次），
   集成侧只能手工重编号。

算法（分轨）：

- **表格行**（以 ``|`` 开头且含 ``V3-FIX-N`` ID）：按 ID 并集；同 ID
  双版本取状态更进化者（含 ``FIXED@``/``CLOSED@``/``WONTFIX`` 优先，
  同状态取长者；不做纯长度裁决）。
- **非表格行**（段落/标题/表头/分隔线等）：按出现序全保留——ours 段
  在前、theirs 独有行按原序追加；theirs 行与已保留行完全相同者去重
  （防 git 冲突块边界共享行双写），除此之外零丢失。

防再发强化（V3-FIX-278/282，事故形态：3896a1b5 吞 257 行、62f20b0b
并行回退 263 行、4 处历史粘连）：

- ``--check`` 扩展一：合并输出每行 V3-FIX 行做 **8 裸管形态校验**
  （``\\|`` 转义管不计；期望值 ``--expect-pipes`` 可配，默认 8=表头 7 列；
  多数行形态容差——与多数行一致的裸管数不 FAIL，``--strict-pipes`` 关闭
  容差），畸形行 FAIL 并列出行号。
- ``--check`` 扩展二：**行数对账**——输出行数 ≥ max(ours, theirs) 行数
  − 冲突块合法重叠数（跨侧同文去重、同 ID 折叠、侧内重号折叠的保守
  下界），低于下界即吞行报警（ID 差集法之外的整行级兜底）。
- 新增 ``--verify FILE``：对任一台账文件独立体检——零冲突标记残留 +
  8 裸管形态 + 行首锚定 ID 无重号 + 行尾状态枚举合法
  （OPEN/FIXED@/CLOSED@/WONTFIX 前缀；仅对形态合法行检查）。
- ``--verify`` deep 抽检三项（wt791；治 FIX-504/512/514 同族「台账行内容
  丢失/幻影号」病，默认开启、只报不改）：① FIXED@ 指针主干可达性——
  ``git merge-base --is-ancestor <sha> HEAD`` 不可达=指针腐烂（预 rebase
  SHA），git 调用失败/无 git 环境降级 warning 不 FAIL；② 行内 FIXED@ 与
  行首状态枚举一致性——状态格 OPEN 开头而行内含 FIXED@=混合体（53 行
  事故的机器口径误报源），状态格 FIXED@ 开头而全行零 sha 指针=收口无
  凭证；③ HEAD 前 200 条 commit message 的 V3-FIX-N 引用号存在性——
  台账全文查无=幻影号（历史 message 不可改写，恒 warning 不 FAIL）。
  ``--no-deep`` 跳过 git 依赖的 ①③（性能受限/无 git 环境）；②为纯
  文本面恒跑。``--deep-strict`` 把 ①② 升格 FAIL（③与环境降级恒
  warning）——台账卫生卡收口后的零红验收用。
- **转义管全链感知**：格切分统一按裸管口径（``\\|`` 是格内字面竖线、
  裸 ``|`` 才是列界）——status_cell 提取、重编号注记落位与形态计数
  同源，状态格含 ``\\|`` 注记（如 ``OPEN [wt474分诊:备忘型\\|…]``、
  ``str\\|None`` 类注记）不再被行尾碎片误报为状态非法。

用法::

    # 合并（结果到 stdout 或 -o 指定文件）
    python3 scripts/devtools/ledger_union_merge.py 冲突文件.md -o 合并.md
    git show :1:path | python3 scripts/devtools/ledger_union_merge.py > merged.md

    # 撞号重编号：theirs 侧 V3-FIX-265 整行改为 V3-FIX-267 并自动追加注记
    python3 scripts/devtools/ledger_union_merge.py f.md --renumber 265=267 --renumber 266=268

    # 合并后验证：零冲突标记残留 + 双侧 ID 全在场（吞行检测）
    #             + 8 裸管形态 + 行数对账
    python3 scripts/devtools/ledger_union_merge.py f.md --check

    # 独立体检任一台账文件（只读，不改文件）
    python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md

    # deep 抽检性能受限/无 git 环境降级（跳过 ①可达性 ③幻影号，②仍跑）
    python3 scripts/devtools/ledger_union_merge.py --verify 台账.md --no-deep

    # 卫生卡收口验收：deep 抽检 ①② 升格 FAIL（③幻影号恒 warning）
    python3 scripts/devtools/ledger_union_merge.py --verify 台账.md --deep-strict

退出码：0 成功/验证通过；1 --check/--verify 验证失败；2 输入/用法错误
（如未闭合冲突块、非法 --renumber）。
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field

# 表格行 ID：以 | 开头且含 V3-FIX-N
FIX_ID_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9-])V3-FIX-\d+(?!\d)")
# FIXED@ 指针：FIXED@<sha>（7-40 位十六进制；deep 抽检① 主干可达性用；
# 后随守卫防把超长散列/字串截半当指针）
FIXED_SHA_RE = re.compile(r"FIXED@([0-9a-f]{7,40})(?![0-9a-f])")
# deep 抽检③：commit message 幻影号扫描深度（HEAD 前 N 条）
PHANTOM_SCAN_LIMIT = 200
# 已收口状态标记：进化于 OPEN（台账实录形态：FIXED@sha / CLOSED@tag / WONTFIX，
# 含「OPEN 补记FIXED@...」扫陈补记形态）
RESOLVED_MARK_RE = re.compile(r"FIXED@|CLOSED@|WONTFIX")
# 行首锚定 ID（状态列/重号检测用）：行首 | V3-FIX-N |
ROW_ANCHOR_RE = re.compile(r"^\|\s*(V3-FIX-\d+)\s*\|")
# 裸管：非转义 |（\| 是格内字面竖线，不构成列边界）
BARE_PIPE_RE = re.compile(r"(?<!\\)\|")
# 表头 7 列 → 行须 8 裸管；行尾状态枚举合法前缀
DEFAULT_EXPECT_PIPES = 8
LEGAL_STATUS_PREFIXES = ("OPEN", "FIXED@", "CLOSED@", "WONTFIX")

START_RE = re.compile(r"^<{7}(?: .*)?$")
SEP_RE = re.compile(r"^={7}\s*$")
END_RE = re.compile(r"^>{7}(?: .*)?$")


@dataclass
class ConflictBlock:
    """一个 <<<<<<< / ======= / >>>>>>> 冲突块。"""

    start_line: str
    ours: list[str] = field(default_factory=list)
    theirs: list[str] = field(default_factory=list)
    end_line: str = ""


@dataclass
class ParsedText:
    segments: list  # ("text", [lines]) | ("conflict", ConflictBlock)
    blocks: list[ConflictBlock] = field(default_factory=list)


@dataclass
class MergeOutcome:
    text: str
    blocks: int = 0
    ours_ids: set = field(default_factory=set)
    theirs_ids: set = field(default_factory=set)
    applied_renumbers: list = field(default_factory=list)
    # 行数对账（V3-FIX-282）：ours/theirs 全文行数与冲突块合法重叠数
    ours_lines: int = 0
    theirs_lines: int = 0
    overlap_lines: int = 0
    # 分轨算法输出行数的精确期望（共享段 + 逐块出账），低于即吞行
    expected_lines: int = 0


def row_id(line: str) -> str | None:
    """表格行判定：以 ``|`` 开头且含 V3-FIX-N ID，返回 ID token，否则 None。"""
    if not line.startswith("|"):
        return None
    m = FIX_ID_TOKEN_RE.search(line)
    return m.group(0) if m else None


def parse_conflicts(text: str) -> ParsedText:
    """解析冲突标记。未闭合/嵌套块抛 ValueError。"""
    result = ParsedText(segments=[])
    lines = text.splitlines(keepends=True)
    buf: list[str] = []
    block: ConflictBlock | None = None
    in_theirs = False
    for lineno, line in enumerate(lines, 1):
        stripped = line.rstrip("\r\n")
        if block is None:
            if START_RE.match(stripped):
                if buf:
                    result.segments.append(("text", buf))
                    buf = []
                block = ConflictBlock(start_line=line)
                in_theirs = False
            else:
                buf.append(line)
        else:
            if SEP_RE.match(stripped) and not in_theirs:
                in_theirs = True
                continue
            if END_RE.match(stripped):
                block.end_line = line
                result.segments.append(("conflict", block))
                result.blocks.append(block)
                block = None
                in_theirs = False
                continue
            (block.theirs if in_theirs else block.ours).append(line)
    if block is not None:
        raise ValueError(f"未闭合冲突块（起始标记 {block.start_line.strip()!r}，EOF 前无 >>>>>>>）")
    if buf:
        result.segments.append(("text", buf))
    return result


def _is_more_evolved(a: str, b: str) -> bool:
    """b 是否比 a 状态更进化（OPEN < FIXED@/CLOSED@/WONTFIX）。"""
    return bool(RESOLVED_MARK_RE.search(b)) and not RESOLVED_MARK_RE.search(a)


def _pick(ours_line: str, theirs_line: str) -> str:
    """同 ID 双版本取状态更进化者；同状态取长者（信息超集），全同取 ours。

    不做纯长度裁决：长度只在状态同级时作平局裁断（临时件曾以纯长度
    误判 OPEN 长行压过 FIXED 短行）。
    """
    if _is_more_evolved(ours_line, theirs_line):
        return theirs_line
    if _is_more_evolved(theirs_line, ours_line):
        return ours_line
    if len(theirs_line.rstrip("\r\n")) > len(ours_line.rstrip("\r\n")):
        return theirs_line
    return ours_line


def apply_renumber(line: str, old: str, new: str) -> str:
    """theirs 侧撞号行整行重编号：首个 ID token 替换 + 注记后缀。

    只替换首个出现（ID 格本位）；行内描述引用的其他/自身 FIX ID 不动。
    注记落位仿台账实录形态（重编号注记置于第三个单元格开头；
    参见 V3-FIX-259/260/263/267 行），列数不足时回退到 ID 后或行尾。
    列界按裸管口径（``\\|`` 是格内字符），格含转义管时注记不错位进格中。
    """
    token_old, token_new = f"V3-FIX-{old}", f"V3-FIX-{new}"
    pat = re.compile(re.escape(token_old) + r"(?!\d)")
    new_line = pat.sub(token_new, line, count=1)
    note = f"（集成重编号：原登记 {token_old}，撞号顺延 {token_new}）"
    cells = split_bare_pipes(new_line)
    if len(cells) >= 5:
        cells[3] = note + cells[3]
        return "|".join(cells)
    if len(cells) >= 3:
        cells[1] = cells[1].rstrip() + " " + note + " "
        return "|".join(cells)
    body = new_line.rstrip("\r\n")
    tail = new_line[len(body) :]
    return f"{body} {note}{tail}"


def merge_block(block: ConflictBlock, renumber: dict[str, str] | None = None):
    """合并单个冲突块，返回 (merged_lines, ours_ids, theirs_ids, applied, overlap, expected)。

    ours_ids/theirs_ids 为合并后仍应存在于输出的双侧 ID 集（theirs 按
    重编号后计），供 --check 吞行检测。overlap 为该块合法重叠行数的
    保守上界（跨侧同文行去重 + 同 ID 跨侧折叠 + 侧内重号折叠）；
    expected 为本块输出行数的精确期望（分轨算法逐行出账）。二者供
    行数对账下界使用——只放宽不收紧，宁可漏报不误报。
    """
    renumber = renumber or {}
    applied: list[str] = []

    theirs_lines: list[str] = []
    for line in block.theirs:
        rid = row_id(line)
        if rid is not None:
            old = rid.removeprefix("V3-FIX-")
            if old in renumber:
                theirs_lines.append(apply_renumber(line, old, renumber[old]))
                applied.append(f"{old}={renumber[old]}")
                continue
        theirs_lines.append(line)

    # 双侧各自折叠：同 ID 多行取进化者，记录首现序
    def fold(lines):
        order, folded = [], {}
        for line in lines:
            rid = row_id(line)
            if rid is None:
                continue
            if rid in folded:
                folded[rid] = _pick(folded[rid], line)
            else:
                order.append(rid)
                folded[rid] = line
        return order, folded

    ours_order, ours_fold = fold(block.ours)
    theirs_order, theirs_fold = fold(theirs_lines)
    ours_ids = set(ours_order)
    theirs_ids = set(theirs_order)

    # 合法重叠（保守上界）：
    # ① 跨侧同文行（含非表格行与同 ID 同文表格行）去重 → 各折 1 行
    ours_content = Counter(line.rstrip("\r\n") for line in block.ours)
    theirs_content = Counter(line.rstrip("\r\n") for line in theirs_lines)
    overlap = sum((ours_content & theirs_content).values())
    # ② 同 ID 跨侧异文折叠（2 行取 1 胜者）→ 各折 1 行（同文已在 ① 计）
    overlap += sum(1 for rid in ours_ids & theirs_ids if ours_fold[rid] != theirs_fold[rid])
    # ③ 侧内重号折叠（同 ID 同侧多行只出胜者）→ 各重号行折 1
    for lines in (block.ours, theirs_lines):
        id_counts = Counter(rid for line in lines if (rid := row_id(line)) is not None)
        overlap += sum(count - 1 for count in id_counts.values() if count > 1)

    # 本块输出行数的精确期望：ours 非表格行全保留 + ours 表格行按
    # 去重 ID + theirs 独有非表格行 + theirs 独有 ID 行。合并输出少于
    # 此值即吞行（含 ID 仍在场但整行被粘连进邻行的形态——257 事故）。
    ours_nt_contents = {line.rstrip("\r\n") for line in block.ours if row_id(line) is None}
    theirs_nt_contents = {line.rstrip("\r\n") for line in theirs_lines if row_id(line) is None}
    ours_nt_count = sum(1 for line in block.ours if row_id(line) is None)
    expected = ours_nt_count + len(ours_ids) + len(theirs_nt_contents - ours_nt_contents) + len(theirs_ids - ours_ids)

    out: list[str] = []
    emitted_nt: set[str] = set()
    emitted_at: dict[str, int] = {}

    # ① ours 侧按原序：表格行（同 ID 只出折叠胜者一次）+ 非表格行全保留
    for line in block.ours:
        rid = row_id(line)
        if rid is None:
            out.append(line)
            emitted_nt.add(line.rstrip("\r\n"))
        else:
            if rid in emitted_at:
                continue
            emitted_at[rid] = len(out)
            out.append(ours_fold[rid])

    # ② theirs 侧按原序追加：已有 ID 与 ours 胜者做跨侧进化裁决（原地替换），
    #    新 ID 整行追加；非表格独有行追加（跨侧同文去重防边界行双写）
    for line in theirs_lines:
        rid = row_id(line)
        if rid is None:
            key = line.rstrip("\r\n")
            if key in emitted_nt:
                continue
            emitted_nt.add(key)
            out.append(line)
        else:
            if rid in emitted_at:
                idx = emitted_at[rid]
                out[idx] = _pick(out[idx], theirs_fold[rid])
            else:
                emitted_at[rid] = len(out)
                out.append(theirs_fold[rid])

    return out, ours_ids, theirs_ids, applied, overlap, expected


def merge_text(text: str, renumber: dict[str, str] | None = None) -> MergeOutcome:
    parsed = parse_conflicts(text)
    parts: list[str] = []
    outcome = MergeOutcome(text="", blocks=len(parsed.blocks))
    for kind, payload in parsed.segments:
        if kind == "text":
            parts.append("".join(payload))
            # 共享段两侧各计一次（对账公式用全文行数口径）
            shared = len(payload)
            outcome.ours_lines += shared
            outcome.theirs_lines += shared
            outcome.expected_lines += shared
        else:
            merged, ours_ids, theirs_ids, applied, overlap, expected = merge_block(payload, renumber)
            parts.append("".join(merged))
            outcome.ours_ids |= ours_ids
            outcome.theirs_ids |= theirs_ids
            outcome.applied_renumbers.extend(applied)
            outcome.ours_lines += len(payload.ours)
            outcome.theirs_lines += len(payload.theirs)
            outcome.overlap_lines += overlap
            outcome.expected_lines += expected
    outcome.text = "".join(parts)
    return outcome


def ids_in_text(text: str) -> set:
    return set(FIX_ID_TOKEN_RE.findall(text))


def verify_merge(merged_text: str, ours_ids: set, theirs_ids: set) -> list[str]:
    """合并后验证：零冲突标记残留 + 双侧所有 ID 在场（吞行检测）。"""
    problems: list[str] = []
    present = ids_in_text(merged_text)
    problems.extend(check_conflict_markers(merged_text))
    for rid in sorted(ours_ids - present, key=lambda t: int(t.rsplit("-", 1)[1])):
        problems.append(f"ours 侧 {rid} 未在合并输出中（疑似吞行）")
    for rid in sorted(theirs_ids - present, key=lambda t: int(t.rsplit("-", 1)[1])):
        problems.append(f"theirs 侧 {rid} 未在合并输出中（疑似吞行）")
    return problems


def check_conflict_markers(text: str) -> list[str]:
    """冲突标记残留检测（<<<<<<< / ======= / >>>>>>> 行首形态）。"""
    problems: list[str] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.rstrip("\r\n")
        if START_RE.match(stripped) or SEP_RE.match(stripped) or END_RE.match(stripped):
            problems.append(f"第 {lineno} 行冲突标记残留：{stripped!r}")
    return problems


def bare_pipe_count(line: str) -> int:
    """裸管数：非转义 | 计数（转义管为格内字面竖线，不构成列边界）。"""
    return len(BARE_PIPE_RE.findall(line))


def split_bare_pipes(line: str) -> list[str]:
    """按裸管切分单元格：裸 ``|`` 才是列界，``\\|`` 原样留在格内。

    与 bare_pipe_count 同一口径（形态计数/格提取/注记落位同源）；
    ``"|".join`` 回拼无损还原原行（转义管保留在段内不被消费）。
    """
    return BARE_PIPE_RE.split(line)


def check_row_shapes(
    text: str, expect_pipes: int = DEFAULT_EXPECT_PIPES, majority_tolerance: bool = True
) -> tuple[list[str], dict]:
    """每行 V3-FIX 行的 8 裸管形态校验（V3-FIX-278/282）。

    期望值 expect_pipes（默认 8=表头 7 列）；majority_tolerance 开启时
    与多数行裸管数一致的行不 FAIL（「真实列数与多数行一致」的容差，
    防历史同形存量被整体误报）——``--strict-pipes`` 可关闭。

    返回 (problems, stats)；stats 含 majority/expect/distribution/checked，
    problems 每项带行号与实际裸管数。
    """
    rows = [
        (lineno, line.rstrip("\r\n")) for lineno, line in enumerate(text.splitlines(), 1) if row_id(line) is not None
    ]
    distribution = Counter(bare_pipe_count(line) for _, line in rows)
    stats = {
        "majority": distribution.most_common(1)[0][0] if distribution else expect_pipes,
        "expect": expect_pipes,
        "distribution": dict(sorted(distribution.items())),
        "checked": len(rows),
    }
    allowed = {expect_pipes}
    if majority_tolerance:
        allowed.add(stats["majority"])
    problems: list[str] = []
    failed_lines: set[int] = set()
    for lineno, line in rows:
        count = bare_pipe_count(line)
        if count not in allowed:
            failed_lines.add(lineno)
            rid = row_id(line)
            problems.append(
                f"第 {lineno} 行 {rid} 裸管数 {count}（合法形态 {sorted(allowed)}，"
                f"多数行形态 {stats['majority']}）——列错位/粘连/幻影列"
            )
    stats["failed_lines"] = failed_lines
    return problems, stats


def check_duplicate_ids(text: str) -> list[str]:
    """行首锚定 ID 重号检测（V3-FIX-279 双行形态：陈旧行+权威行并存）。"""
    seen: dict[str, int] = {}
    problems: list[str] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        m = ROW_ANCHOR_RE.match(line)
        if m:
            rid = m.group(1)
            if rid in seen:
                problems.append(f"{rid} 行首锚定重号：第 {seen[rid]} 行与第 {lineno} 行并存")
            else:
                seen[rid] = lineno
    return problems


def status_cell(line: str) -> str:
    """行尾状态格：最后一个非空裸管格（容忍缺尾管形态）。

    裸管切分：``\\|`` 是格内字面竖线，状态格含转义注记（如
    ``OPEN [wt474分诊:备忘型\\|…]``）时整格保留——不按转义管误断、
    不把行尾碎片当状态格误报状态非法。
    """
    for seg in reversed(split_bare_pipes(line)):
        seg = seg.strip()
        if seg:
            return seg
    return ""


def check_status_enum(text: str, skip_lines: set[int] | None = None) -> list[str]:
    """行尾状态枚举前缀扫描（V3-FIX-282）。

    合法前缀：OPEN / FIXED@ / CLOSED@ / WONTFIX。skip_lines 中的行号
    （形态校验已 FAIL 的行）跳过，避免对粘连/错位行双重报警。
    """
    skip = skip_lines or set()
    problems: list[str] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if lineno in skip or row_id(line) is None:
            continue
        cell = status_cell(line)
        if cell and not cell.startswith(LEGAL_STATUS_PREFIXES):
            problems.append(
                f"第 {lineno} 行 {row_id(line)} 行尾状态格非法：{cell[:40]!r}"
                f"（合法前缀 {list(LEGAL_STATUS_PREFIXES)}）"
            )
    return problems


def resolve_git_dir(ledger_path: str | None) -> str | None:
    """deep 抽检的 git 上下文解析：ledger 所在仓优先，回退进程 cwd；均无则 None。

    返回 toplevel 目录（worktree 感知：HEAD=当前分支头）。两处都解析不
    出仓即判「无 git 环境」，调用方按护栏降级 warning。
    """
    candidates: list[str] = []
    if ledger_path:
        candidates.append(os.path.dirname(os.path.abspath(ledger_path)) or ".")
    candidates.append(os.getcwd())
    for directory in candidates:
        proc = subprocess.run(["git", "-C", directory, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    return None


def check_fixed_pointer_reachability(
    text: str, git_dir: str | None, skip_lines: set[int] | None = None
) -> tuple[list[str], list[str]]:
    """deep 抽检①：FIXED@ 指针主干可达性（FIX-504 病——预 rebase SHA 指针腐烂）。

    对每行（形态合法行）内全部 FIXED@<sha> 指针跑
    ``git merge-base --is-ancestor <sha> HEAD``：不可达（exit 1）即确证
    指针腐烂。返回 (rot_findings, env_warnings)：

    - rot_findings：确证不可达——指针腐烂证据，默认档出 warning、
      ``--deep-strict`` 升格 FAIL；
    - env_warnings：无 git 仓/无 HEAD/单次调用出错（exit ∉ {0,1}）——
      环境性降级，恒 warning 不 FAIL（性能/环境护栏），任何模式不升格。

    同 sha 去重缓存；调用成本 O(去重指针数) 次 git 子进程。
    """
    if git_dir is None:
        return [], ["git 环境不可用（ledger 所在目录与进程 cwd 均无 git 仓）——FIXED@ 可达性抽检降级跳过"]
    probe = subprocess.run(["git", "-C", git_dir, "rev-parse", "--verify", "HEAD"], capture_output=True, text=True)
    if probe.returncode != 0:
        return [], [f"git HEAD 不可用（{probe.stderr.strip()[:80]}）——FIXED@ 可达性抽检降级跳过"]
    skip = skip_lines or set()
    rot: list[str] = []
    env: list[str] = []
    cache: dict[str, bool | None] = {}  # sha → 可达 True / 确证不可达 False / 无法核验 None
    for lineno, line in enumerate(text.splitlines(), 1):
        if lineno in skip or row_id(line) is None:
            continue
        rid = row_id(line)
        for match in FIXED_SHA_RE.finditer(line):
            sha = match.group(1)
            if sha not in cache:
                proc = subprocess.run(
                    ["git", "-C", git_dir, "merge-base", "--is-ancestor", sha, "HEAD"],
                    capture_output=True,
                    text=True,
                )
                if proc.returncode == 0:
                    cache[sha] = True
                elif proc.returncode == 1:
                    cache[sha] = False
                else:
                    cache[sha] = None
                    env.append(
                        f"git merge-base 调用失败（exit {proc.returncode}：{proc.stderr.strip()[:60]}），"
                        f"{rid} 行 FIXED@{sha} 可达性无法核验——降级 warning 不 FAIL"
                    )
            if cache[sha] is False:
                rot.append(
                    f"第 {lineno} 行 {rid} FIXED@{sha} 主干不可达"
                    "（merge-base --is-ancestor HEAD 判否）——指针腐烂/预 rebase 提交（FIX-504 病）"
                )
    return rot, env


def check_status_pointer_consistency(text: str, skip_lines: set[int] | None = None) -> list[str]:
    """deep 抽检②：行内 FIXED@ 与行首状态枚举一致性（FIX-512 病混合体）。

    两个方向（纯文本面，无 git 依赖，``--no-deep`` 仍跑）：

    - 正向混合体：状态格以 OPEN 开头而行内含 FIXED@——OPEN/FIXED 双口径
      并存（53 行事故的机器误报源：统计按 OPEN 计、收口指针却在行内）；
    - 反向无凭证：状态格以 FIXED@ 开头而全行零 FIXED@<sha> 指针——收口
      无 commit 凭证（仅 worktree 名/文字桩位，审计断链）。
    """
    skip = skip_lines or set()
    problems: list[str] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if lineno in skip or row_id(line) is None:
            continue
        rid = row_id(line)
        cell = status_cell(line)
        if cell.startswith("OPEN") and "FIXED@" in line:
            problems.append(
                f"第 {lineno} 行 {rid} 状态格 OPEN 开头而行内含 FIXED@——OPEN/FIXED 混合体"
                "（FIX-512 病：统计按 OPEN 计而收口指针在行内，口径误报源）"
            )
        elif cell.startswith("FIXED@") and not FIXED_SHA_RE.search(line):
            problems.append(f"第 {lineno} 行 {rid} 状态格 FIXED@ 开头而全行零 FIXED@<sha> 指针——收口无凭证（审计断链）")
    return problems


def check_commit_message_phantoms(
    text: str, git_dir: str | None, scan_limit: int = PHANTOM_SCAN_LIMIT
) -> tuple[list[str], list[str]]:
    """deep 抽检③（可选低配）：commit message 引用号 vs 台账存在性（FIX-514 病幻影号）。

    扫 HEAD 前 scan_limit 条 commit message 里的 V3-FIX-N 引用：台账全文
    （行首锚定或任何位置提及）都查无的号=幻影号。恒 warning 不 FAIL
    （历史 message 不可改写，任何模式下不升格）；无 git 环境降级跳过。
    """
    if git_dir is None:
        return [], ["git 环境不可用——commit message 幻影号抽检降级跳过"]
    proc = subprocess.run(
        ["git", "-C", git_dir, "log", f"-n{scan_limit}", "--format=%x1e%H%x1f%B"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return [], [f"git log 调用失败（{proc.stderr.strip()[:60]}）——幻影号抽检降级跳过"]
    known = set(FIX_ID_TOKEN_RE.findall(text))
    refs: dict[str, list[str]] = {}
    scanned = 0
    for record in proc.stdout.split("\x1e"):
        record = record.lstrip("\n")
        if not record:
            continue
        sha, _, body = record.partition("\x1f")
        scanned += 1
        for token in FIX_ID_TOKEN_RE.findall(body):
            refs.setdefault(token, []).append(sha)
    phantoms = [
        f"commit message（HEAD 前 {scanned} 条）引用 {token}（如 {shas[0][:12]}）而台账全文无此号"
        "——幻影号（FIX-514 病）；历史 message 不可改写，仅登记不阻断"
        for token, shas in sorted(refs.items(), key=lambda kv: int(kv[0].rsplit("-", 1)[1]))
        if token not in known
    ]
    return phantoms, []


def verify_ledger_deep(
    text: str,
    ledger_path: str | None = None,
    skip_lines: set[int] | None = None,
    deep: bool = True,
    strict_deep: bool = False,
) -> tuple[list[str], list[str], dict]:
    """deep 抽检聚合（--verify 叠加三项，只报不改；FIX-504/512/514 同族病）。

    返回 (fail_problems, deep_warnings, stats)：

    - 默认档：三项发现全走 deep_warnings——现行台账历史残留不阻断，
      与既有四项结构检查的退出语义零耦合；
    - ``--deep-strict``：①指针腐烂与②状态混合体升格 fail_problems；
      ③幻影号（历史 message 改不了）与环境性降级（git 非本工具可控）
      恒 warning 不升格；
    - ``deep=False``（``--no-deep``）：跳过 git 依赖的 ①③，纯文本的
      ②仍跑。
    """
    hybrids = check_status_pointer_consistency(text, skip_lines=skip_lines)
    rot: list[str] = []
    phantoms: list[str] = []
    env: list[str] = []
    git_dir: str | None = None
    if deep:
        git_dir = resolve_git_dir(ledger_path)
        rot, rot_env = check_fixed_pointer_reachability(text, git_dir, skip_lines=skip_lines)
        phantoms, phantom_env = check_commit_message_phantoms(text, git_dir)
        env = rot_env + phantom_env
    deep_warnings = env + phantoms + rot + hybrids
    fail_problems: list[str] = []
    if strict_deep:
        fail_problems = rot + hybrids
        deep_warnings = env + phantoms
    stats = {
        "git_dir": git_dir,
        "deep_enabled": deep,
        "counts": {
            "rot": len(rot),
            "hybrid": len(hybrids),
            "phantom": len(phantoms),
            "env": len(env),
        },
        "escalated": len(fail_problems),
    }
    return fail_problems, deep_warnings, stats


def verify_ledger_file(
    text: str, expect_pipes: int = DEFAULT_EXPECT_PIPES, majority_tolerance: bool = True
) -> tuple[list[str], dict]:
    """独立体检任一台账文件（--verify 模式，V3-FIX-282）。

    四项：零冲突标记残留 + 8 裸管形态（多数容差）+ 行首锚定 ID 无重号
    + 行尾状态枚举合法。返回 (problems, stats)。
    """
    problems: list[str] = []
    problems.extend(check_conflict_markers(text))
    shape_problems, stats = check_row_shapes(text, expect_pipes, majority_tolerance)
    problems.extend(shape_problems)
    problems.extend(check_duplicate_ids(text))
    # 形态已 FAIL 的行不再做状态扫描（粘连/错位行尾格无意义）
    problems.extend(check_status_enum(text, skip_lines=stats["failed_lines"]))
    return problems, stats


def verify_line_accounting(outcome: MergeOutcome) -> list[str]:
    """行数对账（V3-FIX-282 吞行检测扩展）。

    双下界：
    - 精确期望：输出行数 ≥ 共享段 + 逐块出账（分轨算法的逐行期望，
      ID 仍在场但整行被粘连吞失的形态也必破此界——257 事故形态）；
    - 卡面公式：输出行数 ≥ max(ours, theirs) 行数 − 冲突块合法重叠数。
    """
    problems: list[str] = []
    output_lines = len(outcome.text.splitlines())
    if output_lines < outcome.expected_lines:
        problems.append(
            f"行数对账失败：输出 {output_lines} 行 < 精确期望 {outcome.expected_lines} 行"
            "——疑似整行吞失/粘连（含 ID 仍在场的粘连形态）"
        )
    bound = max(outcome.ours_lines, outcome.theirs_lines) - outcome.overlap_lines
    if output_lines < bound:
        problems.append(
            f"行数对账失败：输出 {output_lines} 行 < 下界 {bound}"
            f"（max(ours {outcome.ours_lines}, theirs {outcome.theirs_lines})"
            f" − 合法重叠 {outcome.overlap_lines}）——疑似整行吞失"
        )
    return problems


def parse_renumber(specs: list[str]) -> dict[str, str]:
    renumber: dict[str, str] = {}
    for spec in specs:
        if "=" not in spec:
            raise ValueError(f"--renumber 形如 OLD=NEW，收到 {spec!r}")
        old, new = (part.strip() for part in spec.split("=", 1))
        if not (old.isdigit() and new.isdigit()):
            raise ValueError(f"--renumber 编号须为纯数字，收到 {spec!r}")
        if old == new:
            raise ValueError(f"--renumber OLD=NEW 相同无意义：{spec!r}")
        if old in renumber and renumber[old] != new:
            raise ValueError(f"--renumber 对 {old} 重复指定且目标冲突：{spec!r}")
        renumber[old] = new
    return renumber


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="舰队台账 union-merge（V3-FIX-N 分轨并集，吞行根修+撞号辅助+8 管体检）",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help="含冲突标记的台账文件路径（缺省 stdin，可传 '-' 显式指 stdin；--verify 模式下不可用）",
    )
    parser.add_argument("-o", "--output", help="合并结果输出路径（缺省 stdout；--check 失败时不写）")
    parser.add_argument(
        "--renumber",
        action="append",
        default=[],
        metavar="OLD=NEW",
        help="撞号重编号：theirs 侧 V3-FIX-OLD 行改为 V3-FIX-NEW 并追加注记（可重复）",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="合并后验证（零冲突标记残留+双侧 ID 全在场+8 裸管形态+行数对账），失败 exit 1",
    )
    parser.add_argument(
        "--verify",
        metavar="FILE",
        default=None,
        help="独立体检模式：对台账 FILE 体检（零冲突标记+8 裸管形态+ID 无重号+状态枚举），只读",
    )
    parser.add_argument(
        "--expect-pipes",
        type=int,
        default=DEFAULT_EXPECT_PIPES,
        metavar="N",
        help=f"表格行期望裸管数（默认 {DEFAULT_EXPECT_PIPES}=表头 7 列）",
    )
    parser.add_argument(
        "--strict-pipes",
        action="store_true",
        help="关闭多数行形态容差：裸管数凡非期望值即 FAIL",
    )
    parser.add_argument(
        "--no-deep",
        action="store_true",
        help="--verify 附加项：跳过 git 依赖的 deep 抽检 ①FIXED@ 可达性与 ③幻影号（②状态一致性仍跑）",
    )
    parser.add_argument(
        "--deep-strict",
        action="store_true",
        help="--verify 附加项：deep 抽检 ①② 升格 FAIL（③幻影号与环境降级恒 warning）；卫生卡收口零红验收用",
    )
    args = parser.parse_args(argv)

    if args.verify is not None and args.input != "-":
        parser.error("--verify 与位置参数 input 互斥（体检文件由 --verify FILE 给出）")
    if (args.no_deep or args.deep_strict) and args.verify is None:
        parser.error("--no-deep/--deep-strict 仅在 --verify 模式适用")
    if args.no_deep and args.deep_strict:
        parser.error("--no-deep 与 --deep-strict 互斥")

    try:
        renumber = parse_renumber(args.renumber)
    except ValueError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    verify_path = args.verify
    if verify_path is not None:
        try:
            with open(verify_path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError as exc:
            print(f"错误：读取 {verify_path} 失败：{exc}", file=sys.stderr)
            return 2
        problems, stats = verify_ledger_file(
            text, expect_pipes=args.expect_pipes, majority_tolerance=not args.strict_pipes
        )
        deep_fail, deep_warnings, deep_stats = verify_ledger_deep(
            text,
            ledger_path=verify_path,
            skip_lines=stats["failed_lines"],
            deep=not args.no_deep,
            strict_deep=args.deep_strict,
        )
        problems.extend(deep_fail)
        print(
            f"verify：{stats['checked']} 行 V3-FIX 行，"
            f"裸管分布 {stats['distribution']}，多数形态 {stats['majority']}",
            file=sys.stderr,
        )
        git_label = (
            "跳过（--no-deep）" if not deep_stats["deep_enabled"] else (deep_stats["git_dir"] or "不可用（降级）")
        )
        counts = deep_stats["counts"]
        deep_mode = "关闭（--no-deep，仅②状态一致性）" if not deep_stats["deep_enabled"] else "开启"
        print(
            f"deep 抽检（{deep_mode}）：git 上下文 {git_label}，"
            f"rot {counts['rot']} / hybrid {counts['hybrid']} / phantom {counts['phantom']} / env {counts['env']}"
            f"{'，升格 FAIL ' + str(deep_stats['escalated']) + ' 项' if deep_stats['escalated'] else ''}",
            file=sys.stderr,
        )
        for warning in deep_warnings:
            print(f"WARN：{warning}", file=sys.stderr)
        if problems:
            for problem in problems:
                print(f"FAIL：{problem}", file=sys.stderr)
            if deep_warnings:
                print(f"（另有 deep 抽检 warning {len(deep_warnings)} 项，见 WARN 行）", file=sys.stderr)
            print(f"verify 失败：{len(problems)} 项", file=sys.stderr)
            return 1
        deep_note = (
            f"，deep 抽检 warning {len(deep_warnings)} 项（默认档不阻断）" if deep_warnings else "，deep 抽检零发现"
        )
        print(
            "verify 通过：零冲突标记残留，8 裸管形态合法（多数容差"
            f"{'开' if not args.strict_pipes else '关'}），ID 无重号，状态枚举合法"
            f"{deep_note}",
            file=sys.stderr,
        )
        return 0

    if args.input == "-":
        text = sys.stdin.read()
    else:
        try:
            with open(args.input, encoding="utf-8") as fh:
                text = fh.read()
        except OSError as exc:
            print(f"错误：读取 {args.input} 失败：{exc}", file=sys.stderr)
            return 2

    try:
        outcome = merge_text(text, renumber)
    except ValueError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    for spec in renumber:
        if spec not in {item.split("=", 1)[0] for item in outcome.applied_renumbers}:
            print(
                f"警告：--renumber {spec} 未命中任何 theirs 侧表格行（疑似笔误）",
                file=sys.stderr,
            )

    if args.check:
        problems = verify_merge(outcome.text, outcome.ours_ids, outcome.theirs_ids)
        problems.extend(verify_line_accounting(outcome))
        shape_problems, shape_stats = check_row_shapes(
            outcome.text,
            expect_pipes=args.expect_pipes,
            majority_tolerance=not args.strict_pipes,
        )
        problems.extend(shape_problems)
        print(
            f"check：{outcome.blocks} 个冲突块，"
            f"ours ID {len(outcome.ours_ids)} 个 / theirs ID {len(outcome.theirs_ids)} 个，"
            f"行数对账输出 {len(outcome.text.splitlines())} / 精确期望 "
            f"{outcome.expected_lines} / 卡面下界 "
            f"{max(outcome.ours_lines, outcome.theirs_lines) - outcome.overlap_lines}",
            file=sys.stderr,
        )
        if outcome.blocks == 0:
            print(
                "警告：输入零冲突块（可能已是合并后文件），吞行检测无从比对双侧",
                file=sys.stderr,
            )
        if problems:
            for problem in problems:
                print(f"FAIL：{problem}", file=sys.stderr)
            print(f"check 失败：{len(problems)} 项", file=sys.stderr)
            return 1
        print(
            "check 通过：零冲突标记残留，双侧 ID 全在场（无吞行），行数对账达标，"
            f"V3-FIX 行 {shape_stats['checked']} 行裸管形态合法（多数形态 "
            f"{shape_stats['majority']}）",
            file=sys.stderr,
        )
        if args.output:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(outcome.text)
        return 0

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(outcome.text)
    else:
        sys.stdout.write(outcome.text)
    print(f"已合并 {outcome.blocks} 个冲突块", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
