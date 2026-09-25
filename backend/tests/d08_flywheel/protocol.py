"""D-08 · 协议规格（冻结常量）+ 探针组成 + 记忆种子。

复用纪律：persona 谱、词牌阶梯、truthful 应答、匹配判据全部自
``tests.aurora_ablation.persona`` 导入（A-08 真源，零重建）；本模块只定义
D-08 的纵向协议面（探针日、双臂、记忆种子、反馈事件规则）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tests.aurora_ablation.persona import (
    PersonaSpec,
    utterance_for,
)

__all__ = [
    "D08_SPEC_VERSION",
    "FLYWHEEL_ARMS",
    "PROBE_DAYS",
    "EVENT_DAYS",
    "CONTROL_UTTERANCE",
    "MemorySeed",
    "MEMORY_PHRASE_BY_PERSONA",
    "memory_seeds_for",
    "STALE_KEY",
    "ProbeComposition",
    "probe_composition",
    "build_population",
    "truth_primary_intervention",
]

#: 协议版本（冻结；改动需 bump 并过 reviewer）。
D08_SPEC_VERSION = "d08_flywheel_spec.v1"

#: 双臂（paired design：同世界同探针，唯一差异 = 系统反馈事件是否发生）。
FLYWHEEL_ARMS: tuple[str, ...] = ("flywheel", "no_feedback")

#: 探针模拟日（Day0 基线 / Day3 中程 / Day7 终测；配对差 = Day7 vs Day0）。
PROBE_DAYS: tuple[int, ...] = (0, 3, 7)

#: 反馈事件日（探针之间的飞轮驱动日）。
EVENT_DAYS: tuple[int, ...] = (1, 4)

#: 对照会话日（正常推进话轮——over-personalization 探针）。
CONTROL_DAY: int = 5
CONTROL_UTTERANCE = "今天把这一章看完了，进度正常。"


# ---------------------------------------------------------------------------
# 记忆种子（persona 世界事实；经真实模型行落库，非语义 mock）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MemorySeed:
    """一条 persona 偏好记忆种子（世界数据）。

    值以该 persona 的卡点短语（``MEMORY_PHRASE_BY_PERSONA``）入词——真实
    记忆系统里用户的方法偏好本就以其自述措辞存在；这也是 M-05 memory-use
    selfcheck（词面相关性门）能放行的原因：与探针话轮零重叠的偏好会被
    ``selfcheck:irrelevant_to_query`` 结构性切掉（真实产品行为，勿绕）。
    """

    pref_key: str
    pref_value: str
    confidence: float
    evidence_score: float
    #: stale = 喜好已改变的记忆（PERSONALIZATION_EVAL 对抗面：观察与明确陈述
    #: 冲突）——persona 模型将对其 deny/retract；系统"变安静"链的被试。
    stale: bool
    created_days_ago: int


#: persona → 卡点短语（冻结；取自该 persona 探针词牌的特异子串，即 persona
#: 自述卡点的原话片段——记忆值与其共享词面）。
MEMORY_PHRASE_BY_PERSONA: dict[str, str] = {
    "p01_experience_reinforce": "看不懂",
    "p02_experience_hysteresis": "没学过",
    "p03_explicit_difficulty": "太难",
    "p04_ambiguous_weak": "做不下去",
    "p05_correction_loop": "坚持不下去",
    "p06_structural_gap": "没时间",
    "p07_plan_drift_entry": "计划",
    "p08_skill_repeat": "不会",
    "p09_choice_feedback": "选择太多",
    "p10_quiet_then_tooling": "目标变了",
}


def memory_seeds_for(persona_id: str) -> tuple[MemorySeed, ...]:
    """一个 persona 的三条记忆种子（两条稳定方法偏好 + 一条已废弃旧习惯）。

    stale 条 = PERSONALIZATION_EVAL 对抗面「喜好改变/观察与陈述冲突」：
    persona 早已不再「跳过」，但记忆系统仍持有该旧习惯——flywheel 臂的
    persona 将 deny（Day1）/ retract（Day4），考察记忆是否变安静。
    """
    phrase = MEMORY_PHRASE_BY_PERSONA[persona_id]
    pidx = persona_id.split("_")[0]
    return (
        MemorySeed(
            pref_key=f"old_coping_{pidx}",
            pref_value=f"以前{phrase}就先跳过这段",
            confidence=0.9,
            evidence_score=0.85,
            stale=True,
            created_days_ago=20,
        ),
        MemorySeed(
            pref_key=f"study_method_{pidx}",
            pref_value=f"{phrase}的时候先做例题再回读概念",
            confidence=0.8,
            evidence_score=0.7,
            stale=False,
            created_days_ago=10,
        ),
        MemorySeed(
            pref_key=f"review_habit_{pidx}",
            pref_value=f"{phrase}的时候记下来第二天重读一遍",
            confidence=0.75,
            evidence_score=0.65,
            stale=False,
            created_days_ago=9,
        ),
    )


#: 旧习惯（stale）记忆的 pref_key 前缀——链提取按 key 前缀识别。
STALE_KEY = "old_coping"


# ---------------------------------------------------------------------------
# 探针组成（逐 persona；来自该 persona 的 A-08 首 episode——零新建模）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProbeComposition:
    """一个 persona 的 D-08 探针组成（三探针同构）。"""

    persona_id: str
    friction_truth: str  # ground truth 摩擦类型（A-03 词表）
    days_stalled: int  # 探针任务停滞天数（S）
    failure_count: int  # 近 14 天失败痕迹数（F）
    utterance: str  # 探针词牌（A-08 词牌阶梯 attempt 0）
    truth_primary: str | None  # 真值主干预（A-03 冻结提名表首项）


def probe_composition(spec: PersonaSpec) -> ProbeComposition:
    """从 A-08 persona 规格导出 D-08 探针组成（纯函数；确定性）。"""
    from tests.aurora_ablation.persona import Episode

    first_episode = next(e for e in spec.timeline if isinstance(e, Episode))
    return ProbeComposition(
        persona_id=spec.persona_id,
        friction_truth=first_episode.friction_type,
        days_stalled=first_episode.days_stalled,
        failure_count=first_episode.failure_count,
        utterance=utterance_for(spec, first_episode, 0),
        truth_primary=truth_primary_intervention(first_episode.friction_type),
    )


def truth_primary_intervention(friction_type: str) -> str | None:
    """A-03 冻结提名表首项（patch prefer 方向的真源；复用 A-08 判据）。"""
    from tests.aurora_ablation.persona import primary_nomination

    return primary_nomination(friction_type)


def build_population() -> list[PersonaSpec]:
    """评估人口（A-08 的 10 persona 原样复用）。"""
    from tests.aurora_ablation.persona import build_population as _a08_population

    return _a08_population()


def persona_channel(spec: PersonaSpec) -> str:
    """persona 首选通道（A-08 特质原样复用；行动模型优先面）。"""
    return spec.channel


def persona_faces_snapshot_skeleton() -> dict[str, Any]:
    """五面快照骨架（键序冻结；引擎逐面填充）。"""
    return {
        "understanding": {},
        "memory": {},
        "intervention": {},
        "outcome": {},
        "personalization": {},
    }
