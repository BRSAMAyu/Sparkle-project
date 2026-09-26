#!/usr/bin/env python3
"""CI 套件时长画像工具（wt577）。

解析 GitHub Actions 上以 ``pytest -v`` 运行的完整日志（job 终态后经
``gh api .../actions/jobs/<job_id>/logs`` 下载），从相邻结果行的 ISO 时间戳差
估算每个测试的耗时，聚合出 Top 慢测试 / Top 慢文件 / 目录占比，并按文件粒度
做 LPT 贪心分片模拟，输出可直接粘贴进报告的 Markdown 表格。

用法（最小）::

    gh api repos/<org>/<repo>/actions/jobs/<job_id>/logs > /tmp/job.log
    python3 scripts/devtools/ci_suite_profile.py /tmp/job.log --shards 2 3

    # 附加：导出逐测试耗时 JSON（供二次分析）
    python3 scripts/devtools/ci_suite_profile.py /tmp/job.log --json /tmp/per_test.json

支持的日志形态：
  * 裸 API 下载：``2026-09-26T17:41:42.8337683Z <nodeid> PASSED [  0%]``
  * ``gh run view --log``：``<Job>\t<Step>\t2026-09-26T17:41:42.8337683Z ...``
  * 可含 ``\\ufeff`` BOM 与 ``##[group]``/``##[error]`` 装饰行（自动剥离）。

耗时模型与边界（重要）：
  * pytest -v 在非 TTY 下逐测试完成时整行输出，相邻行时间差 ≈ 后一测试耗时；
    行间穿插的 warning 块会略微抬高下一测试的归属，属已知噪声（报告中已注明）。
  * 首个测试的耗时 = 首结果行 − "collected" 行（收集完成时刻）。
  * collection 与收尾（coverage.xml 写盘 + warnings 汇总）单列，不摊入测试；
    分片预估按文件数比例摊 collection、按时长比例摊收尾。
  * 结果行只认进度区（带 ``[ NN%]`` 后缀、且位于 "short test summary info"
    标记之前）；末尾 summary 区的 ``FAILED <nodeid> - ...`` 行不会重复计数。

只读分析工具：不连网、不改仓库任何文件（输出走 stdout / --json 落点）。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

# ---------------------------------------------------------------- 日志解析 ---

TS_RE = re.compile(r"(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z)\s?")
# 进度区结果行：<ts> <nodeid> <OUTCOME> [可有 (reason)] [ NN%]
# nodeid 的参数化括号内可含空格（如 test_x[hello world]），故 node 只要求含 "::"，
# 用行尾的 "<OUTCOME> ... [ NN%]" 锚定（该形态仅出现在进度区结果行）。
OUTCOME_RE = re.compile(
    r"^(?P<node>.+?::\S.*?)\s+"
    r"(?P<outcome>PASSED|FAILED|SKIPPED|ERROR|XFAIL|XPASS|RERUN\d*)"
    r"(?:\s*\([^)]*\))?\s*\[\s*\d+%\]\s*$"
)
MARK_SESSION = "test session starts"
MARK_COLLECTED = "collecting ... collected"
MARK_SHORT_SUMMARY = "short test summary info"
SUMMARY_TOTAL_RE = re.compile(r"in\s+(?P<secs>[\d.]+)s\s*\(")

# 逻辑测试根（nodeid 前缀）。分组/分片都相对它进行。
TESTS_ROOT = "backend/tests/"


def parse_ts(raw: str) -> datetime:
    """GitHub 日志时间戳（7 位小数秒）→ datetime（Python fromisoformat 只认 6 位）。"""
    frac = raw[raw.find(".") + 1 : -1] if "." in raw else ""
    frac6 = (frac + "000000")[:6]
    base = raw.split(".", 1)[0] if "." in raw else raw[:-1]
    return datetime.fromisoformat(f"{base}.{frac6}+00:00")


@dataclass
class Parsed:
    session_start: datetime | None = None
    collected_at: datetime | None = None
    short_summary_at: datetime | None = None
    reported_total_secs: float | None = None
    tests: list[tuple[str, str, float]] = field(default_factory=list)  # (nodeid, outcome, secs)


def parse_log(path: str) -> Parsed:
    p = Parsed()
    prev_ts: datetime | None = None
    in_short_summary = False
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        for raw_line in fh:
            line = raw_line.rstrip("\n")
            # gh run view --log 形态："<Job>\t<Step>\t<ts> msg"
            if "\t" in line:
                head, sep, tail = line.rpartition("\t")
                if sep and TS_RE.match(tail):
                    line = tail
            m = TS_RE.match(line)
            if not m:
                continue
            ts = parse_ts(m.group("ts"))
            body = line[m.end() :]
            if MARK_SESSION in body:
                p.session_start = ts
                prev_ts = ts
                continue
            if MARK_COLLECTED in body:
                p.collected_at = ts
                continue
            if MARK_SHORT_SUMMARY in body:
                p.short_summary_at = ts
                in_short_summary = True
                continue
            if in_short_summary:
                # 形如 "=== 13 failed, 12989 passed, ... in 5043.68s (1:24:03) ==="
                if p.reported_total_secs is None and "passed" in body:
                    if m2 := SUMMARY_TOTAL_RE.search(body):
                        p.reported_total_secs = float(m2.group("secs"))
                continue
            om = OUTCOME_RE.match(body)
            if om:
                if prev_ts is None:
                    continue  # 结果行出现在会话标记之前（异常日志），放弃
                dur = (ts - prev_ts).total_seconds()
                node = om.group("node")
                outcome = om.group("outcome")
                if not p.tests and p.collected_at is not None:
                    dur = (ts - p.collected_at).total_seconds()
                p.tests.append((node, outcome, max(dur, 0.0)))
                prev_ts = ts
    return p


# ------------------------------------------------------------------ 聚合 ---


def file_of(node: str) -> str:
    return node.split("::", 1)[0]


def group_of(path: str) -> str:
    """backend/tests/<group>/... → <group>；根级文件归 <tests-root>。"""
    rel = path[len(TESTS_ROOT) :] if path.startswith(TESTS_ROOT) else path
    head = rel.split("/", 1)[0]
    if "/" in rel and (rel != head):
        return head
    return "<tests-root>"


def aggregate(tests: list[tuple[str, str, float]]):
    by_file: dict[str, dict] = defaultdict(lambda: {"secs": 0.0, "count": 0, "fails": 0})
    by_group: dict[str, dict] = defaultdict(lambda: {"secs": 0.0, "count": 0, "fails": 0})
    for node, outcome, secs in tests:
        f = file_of(node)
        g = group_of(f)
        for bucket, key in ((by_file, f), (by_group, g)):
            bucket[key]["secs"] += secs
            bucket[key]["count"] += 1
            if outcome in ("FAILED", "ERROR"):
                bucket[key]["fails"] += 1
    return by_file, by_group


# ------------------------------------------------------------------ 分片 ---


def shard_plan(by_file: dict[str, dict], n_shards: int, collection_secs: float, tail_secs: float) -> list[dict]:
    """按文件粒度 LPT 贪心分片（文件是原子单位：同文件测试共享模块级 fixture，
    拆文件会破坏 import/session 级共享状态，故不拆）。"""
    files = sorted(by_file.items(), key=lambda kv: -kv[1]["secs"])
    total_files = sum(v["count"] for v in by_file.values())
    shards: list[dict] = [{"secs": 0.0, "tests": 0, "files": []} for _ in range(n_shards)]
    for name, info in files:  # LPT：最慢文件进当前最空片
        tgt = min(shards, key=lambda s: s["secs"])
        tgt["secs"] += info["secs"]
        tgt["tests"] += info["count"]
        tgt["files"].append((name, info["secs"]))
    total_test_secs = sum(s["secs"] for s in shards)
    out = []
    for s in shards:
        # 分片固定开销估算：collection 按用例数比例（设 40% 为固定 import 成本）、
        # 收尾按测试时长比例摊。全为估算，用于比较方案，不作精确承诺。
        coll = collection_secs * (0.4 + 0.6 * (s["tests"] / max(total_files, 1)))
        tail = tail_secs * (s["secs"] / max(total_test_secs, 1e-9))
        out.append(
            {
                "test_secs": s["secs"],
                "est_wall_secs": s["secs"] + coll + tail,
                "tests": s["tests"],
                "files": sorted(s["files"], key=lambda kv: -kv[1]),
            }
        )
    return out


# ------------------------------------------------------------------ 输出 ---


def fmt_secs(x: float) -> str:
    return f"{x:,.1f}s" if x < 600 else f"{x / 60:,.1f}m"


def render(p: Parsed, by_file, by_group, shards_by_n: dict[int, list[dict]], top_n: int) -> str:
    L: list[str] = []
    total_test = sum(s for _, _, s in p.tests)
    L.append(f"- 结果行：{len(p.tests)} 条；测试净时长合计 {fmt_secs(total_test)}")
    if p.reported_total_secs:
        overhead = p.reported_total_secs - total_test
        L.append(
            f"- pytest 自报总时长 {fmt_secs(p.reported_total_secs)}；"
            f"未归属（collection+收尾+行间输出）≈ {fmt_secs(max(overhead, 0))}"
        )
    L.append("")
    L.append(f"### Top {top_n} 最慢单测")
    L.append("")
    L.append("| # | 测试 | 结果 | 估算耗时 |")
    L.append("|---|---|---|---|")
    for i, (node, outcome, secs) in enumerate(sorted(p.tests, key=lambda t: -t[2])[:top_n], 1):
        L.append(f"| {i} | `{node}` | {outcome} | {secs:.1f}s |")
    L.append("")
    L.append("### Top 10 最慢文件")
    L.append("")
    L.append("| # | 文件 | 用例数 | 失败 | 估算总耗时 | 占全量 |")
    L.append("|---|---|---|---|---|---|")
    top_files = sorted(by_file.items(), key=lambda kv: -kv[1]["secs"])[:10]
    for i, (name, info) in enumerate(top_files, 1):
        share = info["secs"] / max(total_test, 1e-9) * 100
        L.append(
            f"| {i} | `{name}` | {info['count']} | {info['fails']} | " f"{fmt_secs(info['secs'])} | {share:.1f}% |"
        )
    L.append("")
    L.append("### 目录占比（backend/tests 一级目录）")
    L.append("")
    L.append("| 目录 | 用例数 | 失败 | 估算总耗时 | 占比 | 累计 |")
    L.append("|---|---|---|---|---|---|")
    groups = sorted(by_group.items(), key=lambda kv: -kv[1]["secs"])
    cum = 0.0
    for name, info in groups:
        cum += info["secs"]
        share = info["secs"] / max(total_test, 1e-9) * 100
        L.append(
            f"| `{TESTS_ROOT}{name}` | {info['count']} | {info['fails']} | "
            f"{fmt_secs(info['secs'])} | {share:.1f}% | {cum / max(total_test, 1e-9) * 100:.1f}% |"
        )
    for n, plan in shards_by_n.items():
        L.append("")
        L.append(f"### 分片模拟（{n} shards，文件原子 LPT）")
        L.append("")
        L.append("| shard | 用例数 | 测试净时长 | 预估墙钟（含分摊 collection/收尾） | 最慢文件 |")
        L.append("|---|---|---|---|---|")
        for i, s in enumerate(plan, 1):
            top3 = "、".join(f"`{f.split('/')[-1]}`" for f, _ in s["files"][:3])
            L.append(
                f"| {i} | {s['tests']} | {fmt_secs(s['test_secs'])} | " f"{fmt_secs(s['est_wall_secs'])} | {top3} |"
            )
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("logfile", help="GitHub Actions job 完整日志文件路径")
    ap.add_argument("--top", type=int, default=20, help="Top N 慢测试（默认 20）")
    ap.add_argument("--shards", type=int, nargs="*", default=[2, 3], help="分片模拟档位（默认 2 3）")
    ap.add_argument("--json", help="逐测试/逐文件/逐目录/分片结果导出 JSON 路径")
    args = ap.parse_args(argv)

    p = parse_log(args.logfile)
    if not p.tests:
        print("未解析到任何结果行：请确认日志是 job 终态后的完整下载且 pytest 以 -v 运行", file=sys.stderr)
        return 2
    by_file, by_group = aggregate(p.tests)
    total_test = sum(s for _, _, s in p.tests)
    collection = (p.collected_at - p.session_start).total_seconds() if p.collected_at and p.session_start else 0.0
    # 收尾时长（coverage.xml 写盘 + warnings 汇总）= short summary 时刻 − 最后结果行时刻；
    # 最后结果行时刻按 collected_at + 累计净时长还原（与逐行解析一致）。
    tail = 0.0
    if p.collected_at and p.short_summary_at:
        tail = (p.short_summary_at - (p.collected_at + timedelta(seconds=total_test))).total_seconds()
    shards_by_n = {n: shard_plan(by_file, n, collection, max(tail, 0)) for n in args.shards}

    print(render(p, by_file, by_group, shards_by_n, args.top))
    if args.json:
        payload = {
            "meta": {
                "session_start": p.session_start.isoformat() if p.session_start else None,
                "collected_at": p.collected_at.isoformat() if p.collected_at else None,
                "short_summary_at": p.short_summary_at.isoformat() if p.short_summary_at else None,
                "reported_total_secs": p.reported_total_secs,
                "collection_secs": collection,
                "tail_secs": tail,
                "total_test_secs": total_test,
            },
            "tests": [{"node": n, "outcome": o, "secs": round(s, 3)} for n, o, s in p.tests],
            "files": {k: v for k, v in by_file.items()},
            "groups": {k: v for k, v in by_group.items()},
            "shards": {str(n): pl for n, pl in shards_by_n.items()},
        }
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=1)
        print(f"\n[json] 已写出 {args.json}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
