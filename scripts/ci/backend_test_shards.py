#!/usr/bin/env python3
"""Backend Tests 3-shard 静态清单工具（wt592，落地 wt577 提案）。

数据源与算法
------------
时长数据来自 GitHub Actions run **36253679384**（run #525，main@cfaefe63）的
Backend Tests job **108452479615**，由 ``scripts/devtools/ci_suite_profile.py``
从 job 完整日志解析并与 pytest 自报总时长 5043.68s 完全对平
（见 ``v3-output/WT577-PROFILE/report.md`` §0）。清单本身是静态落盘文件
（可复现、可 review diff），本脚本负责生成/校验/按片取出：

    # 重新生成清单（durations 数据 + 当前测试树 → LPT 装箱 + 有状态钉扎）
    python3 scripts/ci/backend_test_shards.py generate

    # CI 内按片取出文件清单（matrix.shard → pytest 参数文件）
    python3 scripts/ci/backend_test_shards.py emit --shard 2 --out .pytest-shard-files.txt

    # 校验：三片并集 == 当前 backend/tests 可收集测试集（零遗漏零重复）
    python3 scripts/ci/backend_test_shards.py verify

均衡与钉扎规则
--------------
* 切分单位 = 测试文件（``backend/pyproject.toml`` python_files =
  ``test_*.py`` + ``*_test.py``），文件不拆（module/session fixture 与 import
  副作用的天然边界，wt577 §5.0）。
* 装箱 = LPT 贪心（最慢文件进当前最空片）；原子按 ``(-secs, path)`` 稳定排序、
  片内清单按 path 升序输出（保持与原全量跑一致的相对顺序，wt577 §5.5 迹象 6
  的重排兜底），同分片时长并列时钉低编号片——同输入恒同输出。
* 有状态钉扎（同片约束优先于均衡，宁可某片 +10% 时长）见 ``PIN_GROUPS``，
  每组理由在清单头注释逐条展开。
* durations 数据没有的新文件（画像之后新增）：按中位文件时长/中位用例数计重
  参与 LPT，并在清单标注 ``[unprofiled]``；文件消失则从清单剔除。
* 因此：**新增/删除测试文件后必须重跑 generate 并 diff review 清单**；
  ``verify`` 在不一致时以非零退出（也适合挂成 CI 守卫）。

只依赖标准库；不连网、不改仓库文件（仅写出 --out / 清单参数指定的落点）。
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DURATIONS = Path(__file__).resolve().parent / "backend_test_durations.json"
DEFAULT_MANIFEST = Path(__file__).resolve().parent / "backend_tests_shards.txt"
TESTS_DIR = "backend/tests"
PYPROJECT = "backend/pyproject.toml"
N_SHARDS = 3

# ----------------------------------------------------------- 有状态钉扎组 ---
# wt577 §5.5「分片/并行化前必读」六条迹象的落地：同片约束优先于均衡。
# 组内文件必须整组落同片；注释理由随 generate 写进清单头。
PIN_GROUPS: list[dict] = [
    {
        "id": "pin-registry-state",
        "sign": "wt577 §5.5 迹象 2（进程级全局注册表）",
        "reason": (
            "circuit_breaker_registry / orchestrator._track_task 后台任务注册表是"
            "进程级全局态，这些文件在同一 pytest 进程内跨文件读写它（注册-清理、"
            "断言他人注册的 breaker）。整组钉同片 = 保证它们始终共享同一进程、"
            "保留与全量跑一致的共执行关系；拆散到多片会让「依赖他人注册态」的"
            "断言在空注册表上假红。"
        ),
        "files": [
            "backend/tests/workflow/test_orchestrator_resilience_workflow.py",
            "backend/tests/workflow/test_contract_fixture_replay.py",
            "backend/tests/unit/test_plan_review_service_breaker.py",
            "backend/tests/integration/test_phase5_orchestrator_north_star_acceptance.py",
            "backend/tests/integration/test_full_orchestration_flow.py",
            "backend/tests/orchestration/test_orchestrator_process_stream_integration.py",
            "backend/tests/orchestration/test_round1_p2_fixes.py",
        ],
    },
    {
        "id": "pin-noisy-heavy",
        "sign": "wt577 §5.5 迹象 1（workspace 树全局可变）+ 迹象 5（墙钟敏感断言）",
        "reason": (
            "tests/load/test_performance_load.py 是合成压测（1000 轮顺序请求后断言"
            "延迟分位数，对资源竞争敏感）；tests/unit/test_bi_hardcoded_secrets_guard.py"
            "在 backend/app/ 下写临时 .py 再 subprocess 扫全仓（workspace 树可变）。"
            "两者整组钉同片：全仓扫描与压测噪声只落在唯一一片（宁可该片 +10% 时长），"
            "其余两片对 timing/文件树保持干净；每片独占 VM，跨片无互扰。"
        ),
        "files": [
            "backend/tests/load/test_performance_load.py",
            "backend/tests/unit/test_bi_hardcoded_secrets_guard.py",
        ],
    },
]


def collected_test_files(repo_root: Path = REPO_ROOT) -> list[str]:
    """pytest 当前会收集的测试文件（backend/pyproject.toml python_files 口径）。"""
    tests_root = repo_root / TESTS_DIR
    out: list[str] = []
    for dirpath, _dirnames, filenames in os.walk(tests_root):
        for name in filenames:
            if name.endswith(".py") and (name.startswith("test_") or name.endswith("_test.py")):
                out.append(os.path.join(TESTS_DIR, os.path.relpath(os.path.join(dirpath, name), tests_root)))
    return sorted(out)


def load_durations(path: Path) -> tuple[dict, dict[str, dict]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["meta"], payload["files"]


# ---------------------------------------------------------------- 装箱 ---


def build_atoms(live: set[str], durations: dict[str, dict]) -> tuple[list[dict], list[str], dict]:
    """返回 (原子列表, 钉扎告警, 统计)。原子 = 钉扎组（整组）或单个文件。"""
    secs = {f: float(info["secs"]) for f, info in durations.items()}
    tests = {f: int(info["tests"]) for f, info in durations.items()}
    default_secs = float(statistics.median(secs.values())) if secs else 1.0
    default_tests = int(statistics.median(tests.values())) if tests else 1

    pinned: set[str] = set()
    warnings: list[str] = []
    atoms: list[dict] = []
    for group in PIN_GROUPS:
        members = [f for f in group["files"] if f in live]
        missing = [f for f in group["files"] if f not in live]
        if missing:
            warnings.append(f"钉扎组 {group['id']} 成员已从测试树消失（自动剔除）: {missing}")
        if not members:
            continue
        pinned.update(members)
        atoms.append(
            {
                "files": sorted(members),
                "secs": sum(secs.get(f, default_secs) for f in members),
                "tests": sum(tests.get(f, default_tests) for f in members),
                "pin": group,
            }
        )
    unprofiled: list[str] = []
    for f in sorted(live - pinned):
        if f in durations:
            atoms.append({"files": [f], "secs": secs[f], "tests": tests[f], "pin": None})
        else:
            unprofiled.append(f)
            atoms.append({"files": [f], "secs": default_secs, "tests": default_tests, "pin": None})
    stats = {"default_secs": default_secs, "default_tests": default_tests, "unprofiled": unprofiled}
    return atoms, warnings, stats


def lpt_pack(atoms: list[dict], n_shards: int) -> list[list[dict]]:
    """LPT 贪心装箱：原子按 (-secs, 首文件路径) 稳定排序，逐个放进当前
    (时长, 片号) 字典序最小的片。同输入恒同输出。"""
    ordered = sorted(atoms, key=lambda a: (-a["secs"], a["files"][0]))
    shards: list[list[dict]] = [[] for _ in range(n_shards)]
    loads = [0.0] * n_shards
    for atom in ordered:
        tgt = min(range(n_shards), key=lambda i: (loads[i], i))
        shards[tgt].append(atom)
        loads[tgt] += atom["secs"]
    return shards


# ------------------------------------------------------------- 清单渲染 ---


def _fmt_wall(secs: float) -> str:
    return f"{secs / 60:.1f}m" if secs >= 60 else f"{secs:.1f}s"


def estimate_walls(shards: list[list[dict]], meta: dict) -> list[float]:
    """wt577 模型：collection 按用例数比例（40% 固定 import 成本），收尾按
    时长比例摊；返回每片预估 pytest 墙钟（秒）。"""
    collection = float(meta.get("collection_secs", 76.1))
    tail = max(float(meta.get("tail_secs", 0.1)), 0.0)
    total_tests = sum(a["tests"] for s in shards for a in s) or 1
    total_secs = sum(a["secs"] for s in shards for a in s) or 1.0
    walls = []
    for s in shards:
        s_secs = sum(a["secs"] for a in s)
        s_tests = sum(a["tests"] for a in s)
        walls.append(s_secs + collection * (0.4 + 0.6 * (s_tests / total_tests)) + tail * (s_secs / total_secs))
    return walls


def render_manifest(shards: list[list[dict]], meta: dict, warnings: list[str], stats: dict) -> str:
    walls = estimate_walls(shards, meta)
    L: list[str] = []
    L.append("# " + "=" * 76)
    L.append("# Backend Tests 3-shard 静态文件清单（wt592 落地 wt577 提案）")
    L.append("#")
    L.append(
        "# 数据源: GitHub Actions run {run} (main@{sha}) Backend Tests job {job};".format(
            run=meta.get("source_run"), sha=meta.get("source_commit"), job=meta.get("source_job")
        )
    )
    L.append("#   逐文件时长由 scripts/devtools/ci_suite_profile.py 解析并与 pytest 自报")
    L.append(
        "#   总时长 {t}s 完全对平（v3-output/WT577-PROFILE/report.md §0）。".format(
            t=meta.get("pytest_reported_total_secs")
        )
    )
    L.append("# 生成器: python3 scripts/ci/backend_test_shards.py generate")
    L.append("#   （勿手改；重新生成后 diff review）")
    L.append("# 方法: 文件粒度 LPT 装箱；原子按 (-时长, 路径) 稳定排序、片内按路径升序，")
    L.append("#   同输入恒同输出；文件不拆（module/session fixture 边界，wt577 §5.0）。")
    L.append("# 有状态钉扎（同片约束优先于均衡，宁可某片 +10% 时长）:")
    for i, s in enumerate(shards, 1):
        for a in s:
            if a["pin"]:
                L.append(f"#   [{a['pin']['id']}] → shard {i} （{a['pin']['sign']}）")
    for group in PIN_GROUPS:
        L.append(f"#   - {group['id']}（{group['sign']}）:")
        L.append("#     " + group["reason"])
    L.append("#   - 迹象 3（module 级重型 fixture，如 q04_personal_redteam 六车道仿真）:")
    L.append("#     由「文件不拆」保证——文件整体落单一片，fixture 成本只计一次，")
    L.append("#     无需跨文件钉扎。")
    L.append("#   - 迹象 4（环境顺序契约: 先图谱后迁移）:")
    L.append("#     ci.yml 每片原样复制 AGE 容器 + init_age_extension + alembic upgrade head")
    L.append("#     （run 36178015150 教训）。")
    L.append("#   - 迹象 6（LPT 跨片重排兜底）:")
    L.append("#     稳定排序 + 片内路径升序保持相对顺序；建议保留夜间全量单进程跑法作")
    L.append("#     漂移网（另卡）。")
    L.append(
        "# 画像后新增文件（无时长数据，按中位文件时长/中位用例数计重参与装箱）:"
        f" {len(stats['unprofiled'])} 个（中位 {stats['default_secs']:.3f}s/{stats['default_tests']} 例）"
    )
    for f in stats["unprofiled"]:
        L.append(f"#   [unprofiled] {f}")
    for w in warnings:
        L.append(f"# 注意: {w}")
    L.append("# 维护: 新增/删除测试文件后 verify 会红 → 重跑 generate 并 diff review 本清单。")
    L.append("# " + "=" * 76)
    for i, s in enumerate(shards, 1):
        files = [f for a in sorted(s, key=lambda a: a["files"][0]) for f in a["files"]]
        secs = sum(a["secs"] for a in s)
        n_tests = sum(a["tests"] for a in s)
        L.append("")
        L.append(
            f"# === shard {i} of {len(shards)} === files={len(files)} tests≈{n_tests}"
            f" profiled_secs={secs:.1f} est_pytest_wall≈{_fmt_wall(walls[i - 1])}"
        )
        for f in files:
            L.append(f)
    return "\n".join(L) + "\n"


# --------------------------------------------------------------- 子命令 ---


def parse_manifest(path: Path) -> dict[int, list[str]]:
    shards: dict[int, list[str]] = {}
    current: int | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("# === shard ") and " of " in line:
            current = int(line.split()[3])
            shards.setdefault(current, [])
            continue
        if not line or line.startswith("#"):
            continue
        if current is None:
            raise SystemExit(f"{path}: shard 段之外出现文件行: {line}")
        shards[current].append(line)
    return shards


def cmd_generate(args: argparse.Namespace) -> int:
    meta, durations = load_durations(args.durations)
    live = set(collected_test_files())
    atoms, warnings, stats = build_atoms(live, durations)
    shards = lpt_pack(atoms, args.shards)
    text = render_manifest(shards, meta, warnings, stats)
    args.manifest.write_text(text, encoding="utf-8")
    walls = estimate_walls(shards, meta)
    for i, s in enumerate(shards, 1):
        print(
            f"shard {i}: files={sum(len(a['files']) for a in s)}"
            f" tests≈{sum(a['tests'] for a in s)}"
            f" profiled_secs={sum(a['secs'] for a in s):.1f}"
            f" est_pytest_wall≈{_fmt_wall(walls[i - 1])}"
        )
    print(f"[generate] 已写出 {args.manifest}")
    return 0


def cmd_emit(args: argparse.Namespace) -> int:
    shards = parse_manifest(args.manifest)
    if args.shard not in shards:
        raise SystemExit(f"清单中没有 shard {args.shard}: 现有 {sorted(shards)}")
    files = shards[args.shard]
    text = "\n".join(files)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"shard {args.shard}: {len(files)} files -> {args.out}", file=sys.stderr)
    else:
        print(text)
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    shards = parse_manifest(args.manifest)
    listed = [f for files in shards.values() for f in files]
    dupes = sorted({f for f in listed if listed.count(f) > 1})
    live = set(collected_test_files())
    listed_set = set(listed)
    stale = sorted(listed_set - live)
    missing = sorted(live - listed_set)
    rc = 0
    if dupes:
        print(f"[verify] 重复条目 {len(dupes)}:", file=sys.stderr)
        for f in dupes:
            print(f"  ! {f}", file=sys.stderr)
        rc = 1
    if stale:
        print(f"[verify] 清单中有但测试树已无 {len(stale)}:", file=sys.stderr)
        for f in stale:
            print(f"  - {f}", file=sys.stderr)
        rc = 1
    if missing:
        print(f"[verify] 测试树新增未入清单 {len(missing)}（重跑 generate）:", file=sys.stderr)
        for f in missing:
            print(f"  + {f}", file=sys.stderr)
        rc = 1
    if rc == 0:
        print(
            f"[verify] OK: {len(shards)} 片并集 == 当前 {TESTS_DIR} 可收集测试集" f"（{len(live)} 文件），零遗漏零重复"
        )
    return rc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="按 durations 数据 + 当前测试树重新生成清单")
    g.add_argument("--durations", type=Path, default=DEFAULT_DURATIONS)
    g.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    g.add_argument("--shards", type=int, default=N_SHARDS)
    g.set_defaults(func=cmd_generate)

    e = sub.add_parser("emit", help="输出指定片的文件清单（CI matrix 用）")
    e.add_argument("--shard", type=int, required=True)
    e.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    e.add_argument("--out", help="写到文件而非 stdout")
    e.set_defaults(func=cmd_emit)

    v = sub.add_parser("verify", help="三片并集 == 当前测试树，零遗漏零重复")
    v.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    v.set_defaults(func=cmd_verify)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
