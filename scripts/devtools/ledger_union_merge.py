#!/usr/bin/env python3
"""舰队台账 union-merge 固化工具（V3-FIX-268）。

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

用法::

    # 合并（结果到 stdout 或 -o 指定文件）
    python3 scripts/devtools/ledger_union_merge.py 冲突文件.md -o 合并.md
    git show :1:path | python3 scripts/devtools/ledger_union_merge.py > merged.md

    # 撞号重编号：theirs 侧 V3-FIX-265 整行改为 V3-FIX-267 并自动追加注记
    python3 scripts/devtools/ledger_union_merge.py f.md --renumber 265=267 --renumber 266=268

    # 合并后验证：零冲突标记残留 + ours/theirs 侧所有 ID 在输出中均存在（吞行检测）
    python3 scripts/devtools/ledger_union_merge.py f.md --check

退出码：0 成功/验证通过；1 --check 验证失败；2 输入/用法错误
（如未闭合冲突块、非法 --renumber）。
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field

# 表格行 ID：以 | 开头且含 V3-FIX-N
FIX_ID_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9-])V3-FIX-\d+(?!\d)")
# 已收口状态标记：进化于 OPEN（台账实录形态：FIXED@sha / CLOSED@tag / WONTFIX，
# 含「OPEN 补记FIXED@...」扫陈补记形态）
RESOLVED_MARK_RE = re.compile(r"FIXED@|CLOSED@|WONTFIX")

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
    """
    token_old, token_new = f"V3-FIX-{old}", f"V3-FIX-{new}"
    pat = re.compile(re.escape(token_old) + r"(?!\d)")
    new_line = pat.sub(token_new, line, count=1)
    note = f"（集成重编号：原登记 {token_old}，撞号顺延 {token_new}）"
    cells = new_line.split("|")
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
    """合并单个冲突块，返回 (merged_lines, ours_ids, theirs_ids, applied)。

    ours_ids/theirs_ids 为合并后仍应存在于输出的双侧 ID 集（theirs 按
    重编号后计），供 --check 吞行检测。
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

    return out, ours_ids, theirs_ids, applied


def merge_text(text: str, renumber: dict[str, str] | None = None) -> MergeOutcome:
    parsed = parse_conflicts(text)
    parts: list[str] = []
    outcome = MergeOutcome(text="", blocks=len(parsed.blocks))
    for kind, payload in parsed.segments:
        if kind == "text":
            parts.append("".join(payload))
        else:
            merged, ours_ids, theirs_ids, applied = merge_block(payload, renumber)
            parts.append("".join(merged))
            outcome.ours_ids |= ours_ids
            outcome.theirs_ids |= theirs_ids
            outcome.applied_renumbers.extend(applied)
    outcome.text = "".join(parts)
    return outcome


def ids_in_text(text: str) -> set:
    return set(FIX_ID_TOKEN_RE.findall(text))


def verify_merge(merged_text: str, ours_ids: set, theirs_ids: set) -> list[str]:
    """合并后验证：零冲突标记残留 + 双侧所有 ID 在场（吞行检测）。"""
    problems: list[str] = []
    present = ids_in_text(merged_text)
    for lineno, line in enumerate(merged_text.splitlines(), 1):
        stripped = line.rstrip("\r\n")
        if START_RE.match(stripped) or SEP_RE.match(stripped) or END_RE.match(stripped):
            problems.append(f"第 {lineno} 行冲突标记残留：{stripped!r}")
    for rid in sorted(ours_ids - present, key=lambda t: int(t.rsplit("-", 1)[1])):
        problems.append(f"ours 侧 {rid} 未在合并输出中（疑似吞行）")
    for rid in sorted(theirs_ids - present, key=lambda t: int(t.rsplit("-", 1)[1])):
        problems.append(f"theirs 侧 {rid} 未在合并输出中（疑似吞行）")
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
        description="舰队台账 union-merge（V3-FIX-N 分轨并集，吞行根修+撞号辅助）",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help="含冲突标记的台账文件路径（缺省 stdin，可传 '-' 显式指 stdin）",
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
        help="合并后验证（零冲突标记残留+双侧 ID 全在场），失败 exit 1",
    )
    args = parser.parse_args(argv)

    try:
        renumber = parse_renumber(args.renumber)
    except ValueError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2

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
        print(
            f"check：{outcome.blocks} 个冲突块，"
            f"ours ID {len(outcome.ours_ids)} 个 / theirs ID {len(outcome.theirs_ids)} 个",
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
        print("check 通过：零冲突标记残留，双侧 ID 全在场（无吞行）", file=sys.stderr)
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
