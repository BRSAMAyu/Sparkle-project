"""P-05 · persona 时间线规格与决策模型（seeded、显式声明、双组共享）.

persona 三条事件谱（对应卡面 stalled / deadline / completion）：

- **stalled**：经典 3 天+ 沉默后建议召回——计划窗口在时间线外（deadline=16），
  看建议能否把停滞目标拉回活跃。
- **deadline**：窗口在时间线内收口（deadline=9..11）——看建议能否在截止前
  恢复推进（deadline 达成），以及窗口过期后建议是否诚实地继续/继续打扰。
- **completion**：账本小、接受度高——中段即可全部完成目标；看目标达成后
  主动面是否还会继续打扰（负担反例候选谱）。

决策模型（对建议的 accept/dismiss/mute/silent）与内在行为（intrinsic 自发
重启日）都从 persona seed 确定性导出，**两组共用同一份 persona 规格**——
唯一组间差异是主动面开/关。
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field, replace
from typing import Any

__all__ = [
    "PersonaSpec",
    "build_population",
    "decide_disposition",
    "SUGGESTION_TYPE",
]

#: comeback 面的 suggestion 类型词表（P-03 反馈键；celery 任务内同值）
SUGGESTION_TYPE = "comeback_nudge"

ARCS: tuple[str, ...] = ("stalled", "deadline", "completion")

#: 各 arc 的（账本总量, 事前已完成数, 计划截止模拟日, 当日钟点 slot）
_ARC_SHAPE: dict[str, dict[str, Any]] = {
    # deadline=16：时间线（14 天）内不过期——纯停滞召回谱
    "stalled": {
        "total_tasks": 8,
        "pre_completed": 2,
        "deadline_day": 16,
        "deadline_jitter": 0,
    },
    # deadline=9..11：窗口在时间线内收口——截止达成 / 过期诚实谱
    "deadline": {
        "total_tasks": 6,
        "pre_completed": 2,
        "deadline_day": 10,
        "deadline_jitter": 1,
    },
    # deadline=16：高接受度小账本——中段完成目标后观察主动面是否继续打扰
    "completion": {
        "total_tasks": 4,
        "pre_completed": 1,
        "deadline_day": 16,
        "deadline_jitter": 0,
    },
}


@dataclass(frozen=True)
class PersonaSpec:
    """一个 persona 的全量时间线规格（raw 落盘，实验装置显式化）."""

    persona_id: str
    arc: str
    seed: int
    deadline_sim_day: int
    total_tasks: int
    pre_completed: int
    #: 开局沉默起点（负数模拟日）： activity 痕迹回溯到这一天 → 第 0 天时 days_away>=3
    initial_active_sim_day: int
    #: 对建议的初始接受倾向
    receptivity: float
    #: 被打扰到静音的倾向
    mute_propensity: float
    #: 连续未行动建议的疲劳步长（每次无行动建议叠加，行动后清零）
    fatigue_step: float
    #: 内在自发重启日（两组共享——与主动面无关的基线行为）
    intrinsic_restart_days: frozenset[int]
    #: 首次 accept 时是否走 P-04 授权仪式（master+类别 grant）
    auto_grant_on_first_accept: bool
    #: 累计无行动建议达到该数 → revoke 授权 + mute（负担反例谱）
    revoke_after_ignores: int | None
    #: 测试用脚本化决策覆盖：sim_day → disposition（缺省走 seeded 随机）
    decision_script: dict[int, str] = field(default_factory=dict)


def build_population(*, seed: int, per_arc: int, days: int) -> list[PersonaSpec]:
    """确定性 persona 总体：同 seed 同总体（两组各跑一份）。"""
    rng = random.Random(f"p05-population:{seed}")
    specs: list[PersonaSpec] = []
    for arc in ARCS:
        shape = _ARC_SHAPE[arc]
        for i in range(per_arc):
            persona_seed = rng.getrandbits(32)
            prng = random.Random(f"p05-persona:{seed}:{arc}:{i}:{persona_seed}")
            intrinsic: set[int] = set()
            for day in range(days):
                if prng.random() < prng.uniform(0.02, 0.10):
                    intrinsic.add(day)
            specs.append(
                PersonaSpec(
                    persona_id=f"{arc}_{i:02d}",
                    arc=arc,
                    seed=persona_seed,
                    deadline_sim_day=shape["deadline_day"]
                    + (
                        prng.randint(
                            -shape["deadline_jitter"], shape["deadline_jitter"]
                        )
                        if shape["deadline_jitter"]
                        else 0
                    ),
                    total_tasks=shape["total_tasks"],
                    pre_completed=shape["pre_completed"],
                    initial_active_sim_day=-4,
                    receptivity=round(prng.uniform(0.35, 0.85), 3),
                    mute_propensity=round(prng.uniform(0.0, 0.25), 3),
                    fatigue_step=0.12,
                    intrinsic_restart_days=frozenset(intrinsic),
                    # 一半 persona 走 P-04 授权仪式（stalled/deadline 谱）
                    auto_grant_on_first_accept=(
                        arc != "completion" and prng.random() < 0.5
                    ),
                    # 1/4 persona 走「被打扰到关停」反例谱（revoke+mute）
                    revoke_after_ignores=(
                        prng.choice([3, 4])
                        if arc != "completion" and prng.random() < 0.25
                        else None
                    ),
                )
            )
    return specs


def decide_disposition(
    spec: PersonaSpec,
    *,
    sim_day: int,
    slot: str,
    suggestion_seq: int,
    consecutive_non_accept: int,
) -> str:
    """对一条建议的 disposition 决策（seeded；accept/dismiss/mute/silent）.

    疲劳模型：连续无行动建议越多接受倾向越低（``receptivity - fatigue``，
    下限 0.05）；未接受时按 mute 倾向（疲劳加压）→ dismiss → silent 落桶。
    decision_script 优先（测试/反例谱脚本化）。
    """
    scripted = spec.decision_script.get(sim_day)
    if scripted is not None:
        return scripted
    prng = random.Random(f"p05-decision:{spec.seed}:{sim_day}:{slot}:{suggestion_seq}")
    fatigue = min(spec.fatigue_step * consecutive_non_accept, 0.6)
    p_accept = max(spec.receptivity - fatigue, 0.05)
    if prng.random() < p_accept:
        return "accept"
    if prng.random() < spec.mute_propensity + (0.1 if fatigue >= 0.3 else 0.0):
        return "mute"
    if prng.random() < 0.55:
        return "dismiss"
    return "silent"


def with_decision_script(spec: PersonaSpec, script: dict[int, str]) -> PersonaSpec:
    """测试辅助：给 persona 挂逐日脚本化决策（其余参数不变）."""
    return replace(spec, decision_script=dict(script))
