"""A-08 · persona 时间线规格 + ground truth + 确定性世界/行动模型。

设计纪律（对照 P-05）：
- persona 谱、事件时间线、ground truth 摩擦类型全部 **seeded 显式声明**（本
  模块静态数据 + 常量），评估结论是该模型与真实 Aurora 服务行为的联合结果；
  效应方向可审计（判据全冻结），效应量级不可外推为真人 RCT（REPORT 声明）。
- 行动模型（intervention 是否解决卡点）是**规则判据**（冻结常量），不是
  随机数：主提名命中 → 当轮解决；次提名命中 → 下一轮（证据升级）解决；
  错位/无行动 → 重试（词牌升级 + 纠正），超出会话预算 → 未解决。
- persona 的「回答 truthful」：对引擎问题回答 ground truth 所在分支——
  确定性解析（分支支持集包含真值；真值不在任何分支时的情形在时间线设计上
  排除并由构造断言兜底）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.aurora.friction_diagnosis import (
    FRICTION_INTERVENTION_NOMINATIONS,
    FRICTION_QUESTION_BANK,
    FRICTION_TYPE_TO_LIFECYCLE_TAG,
)
from app.core.intervention_lifecycle import SPINE_STATE_KEY_TO_FRICTION as _SPINE_STATE_KEY_TO_FRICTION

__all__ = [
    "ARMS",
    "FIXED_TEMPLATE_INTERVENTION",
    "EPISODE_SESSION_BUDGET",
    "ABLATION_SPEC_VERSION",
    "Episode",
    "ControlSession",
    "PersonaSpec",
    "PERSONAS",
    "build_population",
    "primary_nomination",
    "match_class",
    "truthful_branch_key",
    "friction_spine_key",
]

ABLATION_SPEC_VERSION = "aurora_ablation_spec.v1"

#: 四臂（消融协议；同时间线同 seed 单因子差异）。
ARMS: tuple[str, ...] = ("full", "no_memory", "no_experience", "fixed_policy")

#: 固定模板基线对任何卡点会话的恒定回应（模板 bot 的「一个规则一个回应」）。
FIXED_TEMPLATE_INTERVENTION = "explain"

#: 每个卡点段（episode）的会话预算：预算内未收敛 → 未解决（stuck accuracy 失分）。
EPISODE_SESSION_BUDGET = 3


def primary_nomination(friction_type: str) -> str | None:
    """ground truth 摩擦类型的**主干预**（A-03 冻结提名表首项；单一真源）。"""
    noms = FRICTION_INTERVENTION_NOMINATIONS.get(friction_type) or ()
    return noms[0] if noms else None


def match_class(intervention: str | None, friction_type: str) -> str:
    """分派匹配规则分（allocation 判据；全评估统一口径）。

    - ``primary``：命中主提名（1.0）
    - ``secondary``：命中次提名（0.5）
    - ``wrong``：主次皆未命中 / 无行动（0.0）
    """
    noms = FRICTION_INTERVENTION_NOMINATIONS.get(friction_type) or ()
    if intervention is None or intervention in ("no_action", "abstain"):
        return "wrong"
    if not noms:
        return "wrong"
    if intervention == noms[0]:
        return "primary"
    if intervention in noms[1:]:
        return "secondary"
    return "wrong"


def truthful_branch_key(question_id: str, friction_type: str) -> str:
    """persona 对引擎问题的 truthful 回答（确定性）。

    - 真值恰落在一个分支 → 直答该分支（构造断言兜底多命中即红）；
    - 真值不在任何分支（IG 判据可能选到不覆盖真值的判别问——真实引擎行为）
      → persona 选「与自身处境最接近」的分支：同摩擦族（lifecycle tag）支持
      数最多者，并列按分支声明序——确定性、可解释，不静默乱答。
    """
    spec = next(q for q in FRICTION_QUESTION_BANK if q.question_id == question_id)
    hits = [b.key for b in spec.branches if friction_type in b.supports]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        raise AssertionError(
            f"ground truth {friction_type!r} landed in multiple branches of {question_id}: {hits}"
        )
    truth_tag = FRICTION_TYPE_TO_LIFECYCLE_TAG[friction_type]
    best: str | None = None
    best_shared = -1
    for branch in spec.branches:
        shared = sum(
            1
            for t in branch.supports
            if FRICTION_TYPE_TO_LIFECYCLE_TAG.get(t) == truth_tag
        )
        if shared > best_shared:
            best_shared = shared
            best = branch.key
    assert best is not None
    return best


# ---------------------------------------------------------------------------
# 时间线事件规格
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Episode:
    """一个卡点段：从 start_day 起每个卡点会话消耗预算，直到收敛或预算耗尽。

    - ``friction_type``：ground truth（V3 15 类摩擦分类学成员）；
    - ``first_wordmark_tier``：首轮表达强度（weak = 高歧义词牌 / strong = 无歧义）；
    - ``failure_count``：世界侧近 14 天失败痕迹数（0..3；no-memory 臂不落库）；
    - ``days_stalled``：会话时刻距上次推进的天数下界（当前任务 updated_at 回写；
      ≥5 时给 entry 弱证据——entry 类段依赖此面）；
    """

    kind: str  # "episode"
    start_day: int
    friction_type: str
    first_wordmark_tier: str  # "weak" | "strong"
    failure_count: int = 0
    days_stalled: int = 1
    note: str = ""

    @property
    def day(self) -> int:
        """时间线日（与 ControlSession.day 同名的统一访问面）。"""
        return self.start_day


@dataclass(frozen=True)
class ControlSession:
    """对照会话：persona 正常推进（无卡点），考察 Aurora 是否过度介入。"""

    kind: str  # "control"
    day: int
    utterance: str = "今天把这一章看完了，进度正常。"
    note: str = ""


@dataclass(frozen=True)
class PersonaSpec:
    """一个 persona：特质 + 按日时间线（episode/control 序列）。"""

    persona_id: str
    arc: str
    #: 表达含糊度：weak 首轮词牌 + 重试升级节奏（vague 两次一升，mixed 一次一升）
    explicitness: str  # "vague" | "mixed" | "explicit"
    #: 错位干预后是否走「不是这个原因」纠正（full/no_experience 臂落库生效）
    correction_propensity: str  # "none" | "active"
    #: 首选通道（真实用户差异：先在 chat 说，还是直接点「我卡住了」）。
    #: 决定行动模型的优先面——chat 面消费经验（spine+patch），旅程面消费
    #: 记忆（DB 事实+纠正）；两消融面分别在不同通道的用户群上咬合。
    channel: str = "chat"  # "chat" | "journey"
    timeline: tuple[Episode | ControlSession, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# 词牌选择（确定性；出自 A-03 冻结词表，按强度分层）
# ---------------------------------------------------------------------------

#: 各摩擦类型 × 强度 → 表达串（全部为 FRICTION_UTTERANCE_LEXICON 真实词牌；
#: weak = 高歧义/低权重（跨类型共用词牌），strong = 无歧义强词牌）。
_UTTERANCE_BY_TIER: dict[str, dict[str, str]] = {
    "entry": {"weak": "有点不知道从哪开始", "strong": "完全不知道怎么开始"},
    "clarity": {"weak": "这个要求有点模糊", "strong": "不清楚标准，不知道要交什么"},
    "knowledge": {"weak": "这里有点看不懂", "strong": "没学过这个，证明看不懂"},
    "skill": {"weak": "看懂了但不会", "strong": "概念都懂但不会做，一做题就不会"},
    "difficulty": {"weak": "做不下去", "strong": "太难了，超出我的水平"},
    "time": {"weak": "时间有点碎", "strong": "完全没时间，挤不出时间"},
    "energy": {"weak": "有点学不进去", "strong": "太累了，状态不好"},
    "dependency": {"weak": "这部分得等着", "strong": "在等导师回复，卡在等"},
    "choice": {"weak": "方向有点多", "strong": "选择太多，不知道先做哪个"},
    "feedback": {"weak": "心里没底", "strong": "不知道对不对，没人给反馈"},
    "plan_drift": {"weak": "计划有点乱", "strong": "计划赶不上变化，原计划不行了"},
    "goal_drift": {"weak": "有点坚持不下去", "strong": "目标变了，其实更想做别的"},
    "social": {"weak": "一个人学有点闷", "strong": "一个人学不下去，想找个搭子"},
    "tooling": {"weak": "工具一直不太顺", "strong": "环境报错，配置搞不定"},
}


#: 显性度 × 重试轮次（0 起）→ 表达强度阶梯。升级是 persona 行为模型的一部分
#: （诚实表达升级），非引擎侧机制。
_TIER_LADDER: dict[str, tuple[str, ...]] = {
    "vague": ("weak", "weak", "strong", "strong"),
    "mixed": ("weak", "strong", "strong", "strong"),
    "explicit": ("strong", "strong", "strong", "strong"),
}


def utterance_for(spec: PersonaSpec, episode: Episode, attempt: int) -> str:
    """第 attempt 次会话（0 起）的表达：强度随重试升级（证据升级语义）。

    - 声明 ``strong`` 首轮强度时恒 strong（显性 persona 不存在歧义阶段）；
    - 声明 ``weak`` 时按 persona 显性度阶梯升级（vague 两轮、mixed 一轮）。
    """
    if episode.first_wordmark_tier == "strong":
        return _UTTERANCE_BY_TIER[episode.friction_type]["strong"]
    ladder = _TIER_LADDER[spec.explicitness]
    tier = ladder[min(attempt, len(ladder) - 1)]
    return _UTTERANCE_BY_TIER[episode.friction_type][tier]


# ---------------------------------------------------------------------------
# 10 persona 谱（时间线设计判据见各 note；全部 14 天）
# ---------------------------------------------------------------------------


def _p(
    name: str,
    arc: str,
    explicitness: str,
    correction: str,
    *events: Episode | ControlSession,
    channel: str = "chat",
) -> PersonaSpec:
    return PersonaSpec(
        persona_id=name,
        arc=arc,
        explicitness=explicitness,
        correction_propensity=correction,
        channel=channel,
        timeline=tuple(events),
    )


PERSONAS: tuple[PersonaSpec, ...] = (
    # p01 经验强化谱：同类型（knowledge）两段——第一段建立 prefer explain 的
    # 同 scope 证据，第二段考察经验是否加速（更少问询/更早收敛）。
    _p(
        "p01_experience_reinforce",
        "knowledge_repeat",
        "mixed",
        "active",
        Episode("episode", 0, "knowledge", "weak", failure_count=1, days_stalled=2, note="knowledge 段1（weak 词牌）"),
        ControlSession("control", 2, note="段1后紧邻对照（spine 新鲜度探针）"),
        Episode("episode", 3, "knowledge", "weak", failure_count=1, days_stalled=2, note="knowledge 段2（经验强化对照）"),
        ControlSession("control", 5),
        ControlSession("control", 8),
    ),
    # p02 经验滞后谱：knowledge → skill（同 coarse tag knowledge_bottleneck）——
    # 考察 prefer-explain patch 对新类型（skill 主提名 practice）的滞后误排。
    _p(
        "p02_experience_hysteresis",
        "tag_switch",
        "mixed",
        "active",
        Episode("episode", 0, "knowledge", "strong", failure_count=2, days_stalled=1, note="knowledge 段（建立 patch）"),
        Episode("episode", 4, "skill", "weak", failure_count=1, days_stalled=1, note="skill 段（同 tag 换型——滞后探针）"),
        ControlSession("control", 7),
        ControlSession("control", 10),
        channel="journey",
    ),
    # p03 无歧义快收敛谱（explicit）：difficulty 强词牌直出——各臂应都好；
    # 差值出现在 fixed（固定 explain 对 difficulty = 次提名，次轮才收敛）。
    _p(
        "p03_explicit_difficulty",
        "explicit_fast",
        "explicit",
        "none",
        Episode("episode", 0, "difficulty", "strong", failure_count=3, days_stalled=1, note="difficulty 强词牌（失败痕迹 3）"),
        ControlSession("control", 2),
        Episode("episode", 5, "energy", "strong", failure_count=0, days_stalled=1, note="energy 段（chat 面结构性不可服务——旅程面考察）"),
        ControlSession("control", 8),
    ),
    # p04 含糊歧义词牌谱：difficulty 弱词牌「做不下去」跨 difficulty/energy——
    # 考察记忆事实（失败痕迹）是否破局；无记忆时问询/B1 上升。
    _p(
        "p04_ambiguous_weak",
        "weak_ambiguous",
        "vague",
        "active",
        Episode("episode", 0, "difficulty", "weak", failure_count=3, days_stalled=1, note="difficulty 弱词牌+失败痕迹（记忆破局探针）"),
        Episode("episode", 5, "energy", "weak", failure_count=0, days_stalled=6, note="energy 弱词牌+长停滞（entry 证据干扰探针）"),
        ControlSession("control", 9),
        ControlSession("control", 12),
        channel="journey",
    ),
    # p05 纠正依赖谱：goal_drift（弱词牌「坚持不下去」跨 goal_drift/energy）——
    # 错位后靠纠正反馈环垫后类型；no-memory 臂纠正不落库 → 重复错位。
    _p(
        "p05_correction_loop",
        "correction_recovery",
        "vague",
        "active",
        Episode("episode", 0, "goal_drift", "weak", failure_count=1, days_stalled=2, note="goal_drift 弱词牌（纠正垫后探针）"),
        ControlSession("control", 4),
        Episode("episode", 6, "clarity", "weak", failure_count=0, days_stalled=2, note="clarity 段（定向问）"),
        ControlSession("control", 10),
        channel="journey",
    ),
    # p06 结构性服务缺口谱：time/dependency——chat 面 A-02 守卫结构性排除
    # （schedule/remind 需 task_write/scheduler 能力）；旅程面可服务。
    _p(
        "p06_structural_gap",
        "chat_infeasible",
        "explicit",
        "none",
        Episode("episode", 0, "time", "strong", failure_count=0, days_stalled=3, note="time 段（chat 缺口探针）"),
        Episode("episode", 4, "dependency", "strong", failure_count=0, days_stalled=4, note="dependency 段（chat 缺口+无 spine 键）"),
        ControlSession("control", 8),
        ControlSession("control", 11),
        channel="journey",
    ),
    # p07 长程计划漂移谱：plan_drift（弱起）→ entry（长停滞）——跨 tag 两段，
    # 第二段 days_stalled=6 触发 entry 事实证据（记忆面价值）。
    _p(
        "p07_plan_drift_entry",
        "drift_then_entry",
        "mixed",
        "active",
        Episode("episode", 0, "plan_drift", "weak", failure_count=1, days_stalled=2, note="plan_drift 弱词牌"),
        Episode("episode", 5, "entry", "weak", failure_count=0, days_stalled=6, note="entry 段（停滞事实证据探针）"),
        ControlSession("control", 9),
        ControlSession("control", 12),
    ),
    # p08 反复隐性卡点谱：skill 两段 + 中途对照——考察弱词牌 skill 的问询
    # 成本与经验积累方向（practice 证据 vs knowledge 证据竞争同 tag）。
    _p(
        "p08_skill_repeat",
        "skill_repeat",
        "vague",
        "active",
        Episode("episode", 0, "skill", "weak", failure_count=2, days_stalled=1, note="skill 段1（弱词牌+失败痕迹）"),
        ControlSession("control", 3),
        Episode("episode", 5, "skill", "weak", failure_count=2, days_stalled=1, note="skill 段2（同型经验对照）"),
        ControlSession("control", 9),
        ControlSession("control", 12),
    ),
    # p09 快节奏混合谱：choice → feedback（不同 tag 连续两段，explicit）——
    # 高显性低歧义下四臂应接近；差值来自 fixed 与 chat 结构缺口。
    _p(
        "p09_choice_feedback",
        "mixed_explicit",
        "explicit",
        "none",
        Episode("episode", 0, "choice", "strong", failure_count=1, days_stalled=1, note="choice 段"),
        Episode("episode", 3, "feedback", "strong", failure_count=2, days_stalled=1, note="feedback 段"),
        ControlSession("control", 6),
        ControlSession("control", 9),
        ControlSession("control", 12),
    ),
    # p10 静默期后复发谱：goal_drift 段后 3 个对照日（spine/事实过期探针），
    # 再来一段 tooling（chat 面分配守卫结构性 no_action 探针）。
    _p(
        "p10_quiet_then_tooling",
        "stale_probe",
        "mixed",
        "active",
        Episode("episode", 0, "goal_drift", "strong", failure_count=1, days_stalled=1, note="goal_drift 段"),
        ControlSession("control", 2),
        ControlSession("control", 3),
        ControlSession("control", 4, note="连续对照（stale spine/事实过期探针）"),
        Episode("episode", 8, "tooling", "strong", failure_count=0, days_stalled=1, note="tooling 段（分配守卫缺口探针）"),
        ControlSession("control", 12),
        channel="journey",
    ),
)


def build_population() -> list[PersonaSpec]:
    """评估人口（10 persona；时间线设计静态冻结，seed 只影响非语义抖动）。"""
    return list(PERSONAS)


# ---------------------------------------------------------------------------
# 构造期断言（时间线自洽；违反即 import 期红——不静默带病评估）
# ---------------------------------------------------------------------------


def _validate_timeline(spec: PersonaSpec) -> None:
    day = -1
    for event in spec.timeline:
        assert event.day > day, f"{spec.persona_id}: timeline days must strictly increase"
        day = event.day
        if isinstance(event, Episode):
            noms = FRICTION_INTERVENTION_NOMINATIONS.get(event.friction_type)
            assert noms, f"{spec.persona_id}: unknown friction type {event.friction_type!r}"
            assert event.first_wordmark_tier in ("weak", "strong")
            assert 0 <= event.failure_count <= 3
            # truthful 回答可解析性（真值落在每个可能问题的恰一分支）
            for q in FRICTION_QUESTION_BANK:
                if event.friction_type in q.supported_types:
                    truthful_branch_key(q.question_id, event.friction_type)


for _spec in PERSONAS:
    _validate_timeline(_spec)


#: friction 类型 → spine 状态键（experience 面统一投影；逆向
#: ``SPINE_STATE_KEY_TO_FRICTION`` × ``FRICTION_TYPE_TO_LIFECYCLE_TAG``——
#: spine 写入 / 暴露切片 / chat 消费三面同 tag，import 期完整性断言兜底）。
_FRICTION_TO_SPINE_KEY: dict[str, str] = {}
for _ftype, _tag in FRICTION_TYPE_TO_LIFECYCLE_TAG.items():
    for _skey, _tag2 in _SPINE_STATE_KEY_TO_FRICTION.items():
        if _tag2 == _tag:
            _FRICTION_TO_SPINE_KEY[_ftype] = _skey
            break
assert set(_FRICTION_TO_SPINE_KEY) == set(FRICTION_TYPE_TO_LIFECYCLE_TAG) - {"unknown"}, (
    "friction→spine 投影必须全覆盖（unknown 除外）"
)


def friction_spine_key(friction_type: str) -> str:
    """ground truth 摩擦类型的 spine 状态键（spine 写入与暴露切片共用）。"""
    key = _FRICTION_TO_SPINE_KEY.get(friction_type)
    assert key is not None, f"no spine key for friction type {friction_type!r}"
    return key
