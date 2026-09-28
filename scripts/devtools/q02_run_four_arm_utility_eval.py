#!/usr/bin/env python3
"""V4-Q02 · 记忆效用四臂评测 runner（L1 可控服务模拟；零模型调用）。

协议权威：``v4/06_evaluation/EVALUATION_PROTOCOL.md`` §四臂效用实验 +
``v4/evidence/V4-B03/frozen_utility.json``（臂定义/冻结 utility/分母政策）。

四臂绑定（同当前约束、资料、工具；本层无模型故"模型/最大预算一致"以
零模型恒等成立；当前显式约束=Plan/Goal/当前任务四臂共享，非记忆剥夺——
PersonaWorld 对所有臂播种同一 goal/plan 结构）：

==========================  =============  =============================================
Q02 臂                      引擎臂         旗标（其余全部部署默认）
A ``v3_full``               full           默认（I02 gate off / I05 shadow / I04 off）
B ``no_optional_history``   no_memory      默认（可选历史缺席；mandatory 保留）
C ``v4_all_legal``          full           ``EXPERIENCE_STRATEGY_MODE=live``
D ``v4_utility_filtered``   full           C + ``ENABLE_MEMORY_UTILITY_GATE=True``
==========================  =============  =============================================

已知的面边界（如实申报，不事后粉饰）：I02 效用门的唯一集成面是
``context_pack.build``（chat 编排装配面），A-08 harness 决策回路不经过该面
（journey/chat 两面直接驱动既有服务）。因此 **L1 回路内 D 与 C 预期行为恒
等**——本 runner 实证该恒等（归一化逐记录比对）并显式披露；D 臂门的真实
差分证据在选择面（Surface-2，``--surface2``）：真实 ``ContextPackBuilder``
+ M-03 预筛 + 效用门，按 B03 配对集 CTX 族场景种子断言 oracle。

阶段（协议：先开发后 holdout，冻结点隔离）::

    --phase dev       30 开发 episode/臂（A-08 10 persona×2 = 20 + 种子扩展
                      5 persona×2 = 10；开发集可被实现者读——协议允许）
    --phase freeze    落冻结清单（臂定义/schema/判据/零模型声明）——冻结后
                      才允许生成 holdout
    --phase holdout   独立种子生成 30 profile×4 episode=120/臂 ×2 seed
                      （敏感性双检），全部四臂运行
    --phase analyze   冻结 utility + M08-M14 可映射面汇总；按 profile 簇
                      bootstrap 95% CI（配对差值 C−A/C−B/D−C/A−B）
    --phase surface2  选择面四方式对照（CTX-01..08 oracle：不合法引用=0；
                      必要记忆不可全部拒用；selected⊆input）
    --phase all       dev→freeze→holdout→analyze→surface2 顺序执行

用法（仓库根；backend venv 解释器）::

    SECRET_KEY=... backend/.venv/bin/python \
        scripts/devtools/q02_run_four_arm_utility_eval.py --phase all

exit 0 = 全部阶段完成且协议不变量绿；否则非零。产物落
``v4/evidence/V4-Q02/runs/``（gitignore；冻结区 v3-output 不触碰）。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

Q02_DIR = Path(__file__).resolve().parents[2] / "v4" / "evidence" / "V4-Q02"
REPO = Q02_DIR.parents[2]
BACKEND = REPO / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "app" / "gen"))

os.environ.setdefault("SECRET_KEY", "q02-eval-local-secret-key-0123456789ab")
os.environ.setdefault("EVENT_BUS_MAX_RETRIES", "0")
os.environ["PYTHONHASHSEED"] = "0"

RUNS = Q02_DIR / "runs"
ARMS: tuple[str, ...] = (
    "A_v3_full",
    "B_no_optional_history",
    "C_v4_all_legal",
    "D_v4_utility_filtered",
)
ENGINE_ARM = {
    "A_v3_full": "full",
    "B_no_optional_history": "no_memory",
    "C_v4_all_legal": "full",
    "D_v4_utility_filtered": "full",
}
FROZEN_WEIGHTS = (
    {  # v4/evidence/V4-B03/frozen_utility.json utility_frozen.weights（逐项；改动必红）
        "resolved_episode": 1.0,
        "unresolved_episode": -1.0,
        "wrong_followed_decision": -0.4,
        "question": -0.15,
        "control_intrusion": -0.6,
    }
)
HOLDOUT_SEED_MAIN = 20260928
HOLDOUT_SEED_SENSITIVITY = 20260929
DEV_EXT_SEED = 20260927
HOLDOUT_PROFILES = 30
HOLDOUT_EPISODES_PER_PROFILE = 4

# ---------------------------------------------------------------------------
# 种子人口生成（holdout 独立生成；生成规则先于运行提交，seed 显式）
# ---------------------------------------------------------------------------

_FRICTION_VOCAB = (
    "entry",
    "clarity",
    "knowledge",
    "skill",
    "difficulty",
    "time",
    "energy",
    "dependency",
    "choice",
    "feedback",
    "plan_drift",
    "goal_drift",
    "social",
    "tooling",
)
_TIER_VOCAB = ("weak", "strong")
_FAILURE_COUNT_RANGE = (0, 3)
_DAYS_STALLED_RANGE = (1, 6)


def generate_profiles(
    seed: int, *, n_profiles: int, episodes_per_profile: int, prefix: str
) -> list[dict]:
    """种子化 holdout profile 生成（确定性；规则先于数据提交）。

    profile 特质空间 = explicitness × correction_propensity × channel（3×2×2），
    簇 = (explicitness, correction_propensity) 六簇；摩擦类型/强度/失败数/
    停滞天数由 seed 决定。时间线 = episodes 与 control 会话交错（协议每
    episode 最多 3 会话预算 ≤ 协议上限 4 决策轮）。
    """
    rng = random.Random(seed)
    explicitness = ["vague", "mixed", "explicit"]
    corrections = ["none", "active"]
    channels = ["chat", "journey"]
    profiles: list[dict] = []
    for i in range(n_profiles):
        cluster = (explicitness[i % 3], corrections[(i // 3) % 2])
        channel = channels[(i // 6) % 2]
        events: list[dict] = []
        day = 0
        for e in range(episodes_per_profile):
            day += rng.randint(1, 4) if e else 0
            events.append(
                {
                    "kind": "episode",
                    "start_day": day,
                    "friction_type": rng.choice(_FRICTION_VOCAB),
                    "first_wordmark_tier": rng.choice(_TIER_VOCAB),
                    "failure_count": rng.randint(*_FAILURE_COUNT_RANGE),
                    "days_stalled": rng.randint(*_DAYS_STALLED_RANGE),
                    "note": f"{prefix} seeded",
                }
            )
            # 50% 概率在段后放一个对照会话（M14 侵入面），间隔 1-2 日。
            if rng.random() < 0.5:
                day += rng.randint(1, 2)
                events.append({"kind": "control", "day": day})
        profiles.append(
            {
                "profile_id": f"{prefix}_s{seed}_p{i:02d}",
                "cluster": "|".join(cluster),
                "explicitness": cluster[0],
                "correction_propensity": cluster[1],
                "channel": channel,
                "timeline": events,
            }
        )
    return profiles


def profiles_to_specs(profiles: list[dict]) -> list[Any]:
    """种子 profile → harness PersonaSpec（复用既有权威形态，零第二实现）。"""
    from tests.aurora_ablation.persona import ControlSession, Episode, PersonaSpec

    specs = []
    for p in profiles:
        timeline = []
        for ev in p["timeline"]:
            if ev["kind"] == "episode":
                timeline.append(
                    Episode(
                        "episode",
                        ev["start_day"],
                        ev["friction_type"],
                        ev["first_wordmark_tier"],
                        failure_count=ev["failure_count"],
                        days_stalled=ev["days_stalled"],
                        note=ev["note"],
                    )
                )
            else:
                timeline.append(ControlSession("control", ev["day"]))
        spec = PersonaSpec(
            persona_id=p["profile_id"],
            arc=p["cluster"].replace("|", "_"),
            explicitness=p["explicitness"],
            correction_propensity=p["correction_propensity"],
            channel=p["channel"],
            timeline=tuple(timeline),
        )
        from tests.aurora_ablation.persona import _validate_timeline

        _validate_timeline(spec)  # 构造期断言（真值可解析性/词表/日递增）——违反即红
        specs.append(spec)
    return specs


def dev_population() -> list[Any]:
    """开发集：A-08 冻结 10 persona（20 episode）+ 种子扩展 5 persona（10 episode）= 30/臂。"""
    from tests.aurora_ablation.persona import build_population

    base = build_population()
    ext_profiles = generate_profiles(
        DEV_EXT_SEED, n_profiles=5, episodes_per_profile=2, prefix="devext"
    )
    return base + profiles_to_specs(ext_profiles)


# ---------------------------------------------------------------------------
# 四臂运行（进程内旗标切换；每臂后恢复默认并断言）
# ---------------------------------------------------------------------------


def _set_flags(**flags: Any) -> dict[str, Any]:
    from app.config.settings import settings

    before: dict[str, Any] = {}
    for name, value in flags.items():
        before[name] = getattr(settings, name)
        setattr(settings, name, value)
    return before


def _restore_flags(before: dict[str, Any]) -> None:
    from app.config.settings import settings

    for name, value in before.items():
        setattr(settings, name, value)


def _default_flags_snapshot() -> dict[str, Any]:
    from app.config.settings import settings

    return {
        "ENABLE_MEMORY_UTILITY_GATE": settings.ENABLE_MEMORY_UTILITY_GATE,
        "EXPERIENCE_STRATEGY_MODE": settings.EXPERIENCE_STRATEGY_MODE,
        "NO_ACTION_CORRECTION_MODE": getattr(
            settings, "NO_ACTION_CORRECTION_MODE", "off"
        ),
    }


async def run_arm(arm: str, specs: list[Any], *, batch_size: int = 20) -> list[dict]:
    """一臂全人口运行（分批 checkpoint；协议：默认分批 20 episode 按原顺序）。"""
    from tests.aurora_ablation.engine import run_persona_arm

    flags: dict[str, Any] = {}
    if arm == "C_v4_all_legal":
        flags = _set_flags(EXPERIENCE_STRATEGY_MODE="live")
    elif arm == "D_v4_utility_filtered":
        flags = _set_flags(
            EXPERIENCE_STRATEGY_MODE="live", ENABLE_MEMORY_UTILITY_GATE=True
        )
    try:
        records: list[dict] = []
        for spec in specs:
            records.extend(await run_persona_arm(spec, arm=ENGINE_ARM[arm]))
            # 分批 checkpoint（每 ~20 episode 落盘，崩而不失）。
            if (
                sum(
                    1
                    for r in records
                    if r.get("kind") in ("episode_end", "episode_fail")
                )
                % batch_size
                == 0
            ):
                _dump_jsonl(RUNS / f"partial_{arm}.jsonl", records)
        return records
    finally:
        if flags:
            _restore_flags(flags)
            _assert_defaults()


def _assert_defaults() -> None:
    defaults = _default_flags_snapshot()
    assert defaults["ENABLE_MEMORY_UTILITY_GATE"] is False, "gate flag leaked"
    assert defaults["EXPERIENCE_STRATEGY_MODE"] == "shadow", "strategy mode leaked"


def _dump_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# 聚合：episode 级 schema 行 + 臂级 summary + 配对 bootstrap CI
# ---------------------------------------------------------------------------


def episode_rows(
    arm: str, records: list[dict], *, phase: str, seed: int | None
) -> list[dict]:
    """dev_holdout_template episode_record_schema 的必需字段逐项落行。"""
    ends = {r["episode_id"]: r for r in records if r.get("kind") == "episode_end"}
    fails = {r["episode_id"]: r for r in records if r.get("kind") == "episode_fail"}
    rows = []
    for episode_id, rec in {**ends, **fails}.items():
        resolved = episode_id in ends
        rows.append(
            {
                "episode_id": episode_id,
                "arm": arm,
                "pair_id": f"{phase}:{episode_id}",
                "profile_cluster": str(rec.get("persona", "")).rsplit("_p", 1)[0],
                "seed": seed,
                "spec_version": rec.get("spec_version"),
                "result_rules_version": rec.get("result_rules_version"),
                "started_at": None,
                "ended_at": None,
                "clock_kind": "controlled",
                "decision_rounds": (
                    int(rec.get("sessions_used") or 0) if resolved else None
                ),
                "resolved": resolved,
                "missing_or_unresolved": (not resolved) and "budget_exhausted",
                "utility_breakdown": {
                    "resolved_episode": (
                        FROZEN_WEIGHTS["resolved_episode"] if resolved else 0.0
                    ),
                    "unresolved_episode": (
                        0.0 if resolved else FROZEN_WEIGHTS["unresolved_episode"]
                    ),
                },
                "token_usage": {"model_calls": 0, "note": "L1 deterministic; zero LLM"},
                "denominator_notes": "unresolved 计入分母不排除（frozen_utility denominator_policy）",
            }
        )
    return rows


def _percentile_ci(values: list[float], *, rng_seed: int, n_boot: int = 10000) -> dict:
    """profile 簇 bootstrap 95% CI（配对差值；stdlib 确定性 RNG）。"""
    if not values:
        return {"mean": None, "ci95_low": None, "ci95_high": None, "n_profiles": 0}
    rng = random.Random(rng_seed)
    n = len(values)
    means = []
    for _ in range(n_boot):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    point = sum(values) / n
    return {
        "mean": round(point, 6),
        "ci95_low": round(means[int(0.025 * n_boot)], 6),
        "ci95_high": round(means[int(0.975 * n_boot)], 6),
        "n_profiles": n,
    }


def profile_metrics(
    arm: str, records: list[dict], persona_ids: list[str]
) -> dict[str, dict]:
    """按 profile 聚合：resolved/total、frozen utility、wrong/question/intrusion。"""
    out: dict[str, dict] = {}
    for pid in persona_ids:
        p_records = [r for r in records if r.get("persona") == pid]
        resolved = sum(1 for r in p_records if r.get("kind") == "episode_end")
        failed = sum(1 for r in p_records if r.get("kind") == "episode_fail")
        wrong = sum(
            1
            for r in p_records
            if r.get("kind") == "stuck"
            and r.get("match_class") == "wrong"
            and r.get("decision_used")
        )
        questions = sum(
            int(r.get("questions_this_session") or 0)
            for r in p_records
            if r.get("kind") == "stuck"
        )
        intrusions = sum(
            1
            for r in p_records
            if r.get("kind") == "control" and r.get("control_intrusion")
        )
        total = resolved + failed
        utility = (
            FROZEN_WEIGHTS["resolved_episode"] * resolved
            + FROZEN_WEIGHTS["unresolved_episode"] * failed
            + FROZEN_WEIGHTS["wrong_followed_decision"] * wrong
            + FROZEN_WEIGHTS["question"] * questions
            + FROZEN_WEIGHTS["control_intrusion"] * intrusions
        )
        out[pid] = {
            "resolved": resolved,
            "total": total,
            "resolve_rate": round(resolved / total, 6) if total else None,
            "utility": round(utility, 6),
            "followed_wrong": wrong,
            "questions": questions,
            "control_intrusions": intrusions,
        }
    return out


def paired_bootstrap(
    results: dict[str, dict[str, dict]], persona_ids: list[str], *, seed: int
) -> dict[str, dict]:
    """配对差值（逐 profile 相减再 bootstrap）：C−A / C−B / D−B / D−C / A−B。"""
    pairs = {
        "M11_shape_C_minus_A": ("C_v4_all_legal", "A_v3_full", "resolve_rate"),
        "M11_shape_D_minus_A": ("D_v4_utility_filtered", "A_v3_full", "resolve_rate"),
        "M12_shape_C_minus_B": (
            "C_v4_all_legal",
            "B_no_optional_history",
            "resolve_rate",
        ),
        "M12_shape_D_minus_B": (
            "D_v4_utility_filtered",
            "B_no_optional_history",
            "resolve_rate",
        ),
        "utility_C_minus_A": ("C_v4_all_legal", "A_v3_full", "utility"),
        "utility_D_minus_C": ("D_v4_utility_filtered", "C_v4_all_legal", "utility"),
        "utility_A_minus_B": ("A_v3_full", "B_no_optional_history", "utility"),
    }
    out: dict[str, dict] = {}
    for name, (x, y, metric) in pairs.items():
        deltas = []
        for pid in persona_ids:
            mx, my = results[x][pid][metric], results[y][pid][metric]
            if mx is not None and my is not None:
                deltas.append(mx - my)
        out[name] = _percentile_ci(deltas, rng_seed=seed + hash(name) % 1000)
    return out


def normalize_ids(obj: Any, key: str = "") -> Any:  # noqa: D401
    """id 形值归一（跨臂比对用；随机 UUID/内容盐派生 id 逐 run 不同）。"""
    import re

    if isinstance(obj, dict):
        return {k: normalize_ids(v, k) for k, v in obj.items()}
    if isinstance(obj, list):
        return [normalize_ids(v, key) for v in obj]
    if isinstance(obj, str) and key.endswith(("id", "ids", "_basis")):
        if re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}", obj) or re.match(
            r"^(polpatch|aurora|outc)_[0-9a-f]{32}$", obj
        ):
            return "<id>"
    return obj


def compare_arm_records(records_x: list[dict], records_y: list[dict]) -> dict:
    """跨臂决策行为比对（C vs D 恒等实证）：id 归一后逐记录一致？"""
    nx = [normalize_ids(r) for r in records_x]
    ny = [normalize_ids(r) for r in records_y]
    return {
        "record_counts": [len(records_x), len(records_y)],
        "identical_after_id_normalization": nx == ny,
    }


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--phase",
        choices=["dev", "freeze", "holdout", "analyze", "surface2", "all"],
        default="all",
    )
    ap.add_argument(
        "--surface2-only", action="store_true", help="只跑选择面（不跑 episode 回路）"
    )
    args = ap.parse_args()

    RUNS.mkdir(parents=True, exist_ok=True)
    started = datetime.now(UTC).isoformat()
    exit_code = 0

    if args.phase in ("dev", "all"):
        exit_code |= asyncio.run(phase_dev())
    if args.phase in ("freeze", "all"):
        phase_freeze()
    if args.phase in ("holdout", "all"):
        exit_code |= asyncio.run(phase_holdout())
    if args.phase in ("analyze", "all"):
        phase_analyze()
    if args.phase in ("surface2", "all") or args.surface2_only:
        exit_code |= asyncio.run(phase_surface2())

    meta = {
        "started_at": started,
        "ended_at": datetime.now(UTC).isoformat(),
        "exit_code": exit_code,
    }
    (RUNS / "runner_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n"
    )
    return exit_code


async def phase_dev() -> int:
    """开发阶段：30 episode/臂；找协议错误（不变量核查），不改阈值不选样本。"""
    from tests.aurora_ablation.metrics import summarize_arm

    specs = dev_population()
    n_episodes = sum(
        1 for s in specs for ev in s.timeline if getattr(ev, "kind", "") == "episode"
    )
    print(
        f"[q02] dev population: {len(specs)} profiles, {n_episodes} episodes/arm",
        file=sys.stderr,
    )
    results = {}
    for arm in ARMS:
        records = await run_arm(arm, specs)
        _dump_jsonl(RUNS / f"dev_{arm}.jsonl", records)
        results[arm] = records
        s = summarize_arm(records, arm=ENGINE_ARM[arm])
        print(
            f"[q02] dev {arm}: resolved={s['episodes_resolved']}/{s['episodes_total']} "
            f"utility={s['utility']} wrong={s['followed_wrong_decisions']}",
            file=sys.stderr,
        )
    # 协议不变量（开发集用途=找协议错误）：预算/解决判据/臂隔离
    issues = []
    for arm, records in results.items():
        for r in records:
            if r.get("kind") == "episode_end" and r.get(
                "resolving_match_class"
            ) not in ("primary", "secondary"):
                issues.append(f"{arm}:{r.get('episode_id')}: resolution without match")
            if r.get("kind") == "episode_fail" and int(r.get("attempts") or 0) > 3:
                issues.append(f"{arm}:{r.get('episode_id')}: budget exceeded")
    if arm_isolation_violated(results):
        issues.append(
            "arm isolation violated: D differs from C on L1 loop (undisclosed surface)"
        )
    (RUNS / "dev_invariants.json").write_text(
        json.dumps({"issues": issues, "ok": not issues}, ensure_ascii=False, indent=2)
        + "\n"
    )
    print(f"[q02] dev invariants: ok={not issues} issues={issues[:5]}", file=sys.stderr)
    return 0 if not issues else 1


def arm_isolation_violated(results: dict[str, list[dict]]) -> bool:
    """C/D 在 L1 回路面应恒等（I02 门不在该面）——恒等破坏=未声明的行为差。"""
    if "C_v4_all_legal" not in results or "D_v4_utility_filtered" not in results:
        return False
    return not compare_arm_records(
        results["C_v4_all_legal"], results["D_v4_utility_filtered"]
    )["identical_after_id_normalization"]


def phase_freeze() -> None:
    """冻结清单：臂定义/判据/schema/零模型声明——落盘后 holdout 才可生成。"""
    from tests.aurora_ablation.metrics import METRICS_RULES_VERSION
    from tests.aurora_ablation.persona import ABLATION_SPEC_VERSION

    manifest = {
        "frozen_by": "V4-Q02",
        "frozen_at_utc": datetime.now(UTC).isoformat(),
        "authority": [
            "v4/06_evaluation/EVALUATION_PROTOCOL.md §四臂效用实验",
            "v4/evidence/V4-B03/frozen_utility.json（utility_frozen.weights + denominator_policy）",
        ],
        "arms": {
            "A_v3_full": "冻结 V3 当前部署逻辑（A-08 full 臂；I02 gate off / I05 shadow / I04 off——部署默认）",
            "B_no_optional_history": "无可选历史（A-08 no_memory 臂；mandatory 当前约束各臂共享）",
            "C_v4_all_legal": "V4 语义控制+所有合法历史（full 臂 + EXPERIENCE_STRATEGY_MODE=live）",
            "D_v4_utility_filtered": "V4 语义控制+效用筛选历史（C + ENABLE_MEMORY_UTILITY_GATE=True）",
        },
        "shared_constraints": "同当前约束（goal/plan 全臂播种）、资料、工具；本层零模型故模型/最大预算恒等成立；token 差异单报（L1=0）",
        "utility_weights_frozen": FROZEN_WEIGHTS,
        "spec_version": ABLATION_SPEC_VERSION,
        "metrics_rules_version": METRICS_RULES_VERSION,
        "thresholds_frozen": "无评测阈值调参；效用门权重/TopK 保持 I02 冻结初值（本卡不改被评对象）",
        "model_frozen": "零 LLM（L1 可控服务模拟）；L2 真模型层另需预算授权（budget.example.json enabled=false）",
        "episode_shape": "每 episode 最多 3 会话（≤协议 4 决策轮）；EPISODE_SESSION_BUDGET=3",
        "holdout_plan": f"{HOLDOUT_PROFILES} profile × {HOLDOUT_EPISODES_PER_PROFILE} episode = "
        f"{HOLDOUT_PROFILES * HOLDOUT_EPISODES_PER_PROFILE}/臂；seed_main={HOLDOUT_SEED_MAIN} "
        f"seed_sensitivity={HOLDOUT_SEED_SENSITIVITY}；生成规则已随本 runner 提交（seed 显式）",
        "known_surface_boundary": "I02 门集成面=context_pack（不在 A-08 决策回路）→ L1 面内 D≡C 实证披露；"
        "D 差分证据在选择面 Surface-2（真实 ContextPackBuilder + M-03 预筛 + 效用门）",
    }
    (RUNS / "freeze_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    )
    print("[q02] freeze manifest written", file=sys.stderr)


async def phase_holdout() -> int:
    """holdout：两 seed 独立生成 × 四臂 × 120 episode/臂/seed。"""
    from tests.aurora_ablation.metrics import summarize_arm

    overall = 0
    for seed in (HOLDOUT_SEED_MAIN, HOLDOUT_SEED_SENSITIVITY):
        profiles = generate_profiles(
            seed,
            n_profiles=HOLDOUT_PROFILES,
            episodes_per_profile=HOLDOUT_EPISODES_PER_PROFILE,
            prefix="holdout",
        )
        specs = profiles_to_specs(profiles)
        (RUNS / f"holdout_profiles_s{seed}.json").write_text(
            json.dumps(profiles, ensure_ascii=False, indent=2) + "\n"
        )
        for arm in ARMS:
            records = await run_arm(arm, specs)
            _dump_jsonl(RUNS / f"holdout_s{seed}_{arm}.jsonl", records)
            rows = episode_rows(arm, records, phase="holdout", seed=seed)
            _dump_jsonl(RUNS / f"holdout_s{seed}_{arm}_episodes.jsonl", rows)
            s = summarize_arm(records, arm=ENGINE_ARM[arm])
            print(
                f"[q02] holdout s{seed} {arm}: resolved={s['episodes_resolved']}/{s['episodes_total']} "
                f"utility={s['utility']}",
                file=sys.stderr,
            )
    return overall


def phase_analyze() -> None:
    """汇总：臂级指标 + 按 profile 簇配对 bootstrap CI + 双 seed 敏感性。"""
    from tests.aurora_ablation.metrics import summarize_arm

    out: dict[str, Any] = {
        "task": "V4-Q02",
        "kind": "FOUR_ARM_L1_ANALYSIS_ZERO_MODEL",
        "utility_weights": FROZEN_WEIGHTS,
        "denominator_policy": "0 分母 N/A；未解决/缺失计入；不换样本（frozen_utility.json）",
        "seeds": {},
    }
    for seed in (None, HOLDOUT_SEED_MAIN, HOLDOUT_SEED_SENSITIVITY):
        tag = "dev" if seed is None else f"holdout_s{seed}"
        arms_records = {}
        for arm in ARMS:
            path = RUNS / f"{tag}_{arm}.jsonl"
            if path.exists():
                arms_records[arm] = [json.loads(l) for l in path.open() if l.strip()]
        if not arms_records:
            continue
        persona_ids = sorted(
            {str(r.get("persona")) for recs in arms_records.values() for r in recs}
        )
        profiles = {
            arm: profile_metrics(arm, recs, persona_ids)
            for arm, recs in arms_records.items()
        }
        summaries = {}
        for arm, recs in arms_records.items():
            s = summarize_arm(recs, arm=ENGINE_ARM[arm])
            summaries[arm] = {
                "episodes_resolved": s["episodes_resolved"],
                "episodes_total": s["episodes_total"],
                "stuck_accuracy": s["stuck_accuracy"],
                "utility": s["utility"],
                "followed_wrong_decisions": s["followed_wrong_decisions"],
                "questions_total": s["questions_total"],
                "control_intrusions": s["control_intrusions"],
                "patch_reordered_turns": (s.get("experience") or {}).get(
                    "patch_reordered_turns"
                ),
                "patch_ids_seen": (s.get("experience") or {}).get("patch_ids_seen"),
            }
        block: dict[str, Any] = {
            "arm_summaries": summaries,
            "n_profiles": len(persona_ids),
        }
        if seed is not None:
            block["paired_bootstrap_ci"] = paired_bootstrap(
                profiles, persona_ids, seed=seed
            )
            block["per_cluster"] = _per_cluster(profiles, seed)
        out["seeds"][tag] = block

    # C≡D 恒等实证（L1 面）判读注记落盘。
    for block in out["seeds"].values():
        if "paired_bootstrap_ci" in block:
            block["d_minus_c_identity_note"] = (
                "utility_D_minus_C CI 应为精确零（L1 回路面 D≡C，I02 门不在该面）；非零=未声明行为差"
            )
    (RUNS / "analysis.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    )
    print("[q02] analysis written", file=sys.stderr)


def _per_cluster(profiles: dict[str, dict[str, dict]], seed: int) -> dict[str, dict]:
    import json as _json
    from collections import defaultdict

    cluster_of: dict[str, str] = {}
    for s_seed in (HOLDOUT_SEED_MAIN, seed):
        path = RUNS / f"holdout_profiles_s{s_seed}.json"
        if path.exists():
            for p in _json.loads(path.read_text()):
                cluster_of[p["profile_id"]] = p["cluster"]
    clusters: dict[str, list[str]] = defaultdict(list)
    for pid, cluster in cluster_of.items():
        if pid in profiles.get("A_v3_full", {}):
            clusters[cluster].append(pid)
    out = {}
    for cluster, pids in sorted(clusters.items()):
        out[cluster] = {
            "n_profiles": len(pids),
            "resolve_rate": {
                arm: round(
                    sum(profiles[arm][p]["resolve_rate"] or 0 for p in pids)
                    / len(pids),
                    4,
                )
                for arm in ARMS
                if arm in profiles
            },
        }
    return out


async def phase_surface2() -> int:
    """选择面四方式对照（真实 ContextPackBuilder + M-03 预筛 + I02 效用门）。

    CTX 族 oracle（B03 配对集）：不合法引用=0；必要记忆不可全部拒用；
    selected⊆input（无复活）。方式：gate_off（A/C 选择语义=预筛后全量）/
    gate_on（D）/ no_history（B 对照：空 episodic 面）。零模型、确定性。
    """
    from tests.q02_surface2 import run_surface2

    return await run_surface2(RUNS)


if __name__ == "__main__":
    sys.exit(main())
