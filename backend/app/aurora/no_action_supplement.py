"""V4-I04 无动作仍可纠正与一次决策性澄清（FIX97 裁决落地；stuck-policy 域受限消费层）。

定位（v4/04_tasks/cards/V4-I04.md + v4/03_intelligence/AURORA_SEMANTIC_POLICY.md
「无动作也可纠正（FIX97拍板）」+「澄清的判据」）：A-03 摩擦引擎诚实化后
（B1 exact-tie 不猜 / B2 无证据 no_action / FIX-49 chat 门静默），「不是这个
原因」类纠正通道以**被提名的成因**为前提——无动作面上没有可纠正的对象，
纠正记忆回路被饿死（V3-FIX-97）。本模块是 stuck-policy 域的受限消费层：

1. **无动作自由补充（FIX97，验收①）**——``supplement_entry``：no_action /
   abstain / 无提案面上恒可用的单一自由输入出口（「还有什么情况需要我知道？」），
   至多附 2 个**不同操作后果**的例子（竞争带首要提名不同才给，绝不摆 15 种卡点）；
   ``apply_free_supplement``：把补充文本作为**用户主动证据**重放既有 A-03 引擎
   （单一权威，零第二诊断器）——no_action 是**可纠正状态**不是终审：补充证据
   足够即可翻转 act/ask；不足则如实保持 no_action（但带「已复核」注记，不固化
   为永久失败）。**用户主动补充不占系统追问预算**（AURORA_SEMANTIC_POLICY：
   「用户主动补充不算系统追问」）。合法经验 = 结构化补充经验记录（封闭词表 +
   既有 scheme 证据引用 + 会话作用域 + 可撤回标注），供下游记忆面按既有合法性
   门（I02 效用门同纪律）消费——本模块自身零写路径。

2. **临时约束不写永久偏好（验收②）**——``classify_supplement_constraint``：
   「今天只有15分钟」类时间预算识别为**会话作用域**约束记录
   （``permanent_preference_write=False``）；本模块对永久偏好面的写授权是
   **空集**（``SUPPLEMENT_WRITE_SURFACES == frozenset()``，结构保证：A-05
   patch / self-model 写路径属既有 owner，本层零调用、零新枚举）；
   ``difficulty_not_chased``：「不是不会/不是太难」类否定极性的能力族证据
   不得抬高难度族后验占比（复用引擎 FIX-110 否定感知面做守卫断言，不重实现
   词面判定）。

3. **一次决策性澄清（验收③）**——``clarification_exit_ramp``：自动澄清预算
   初值 **≤1 轮**（``V4_AUTO_CLARIFICATION_BUDGET``）；已答一轮后引擎仍想追问
   时**不 surfaced 第二问**，改出封闭出口斜坡：直接说情况（自由补充——用户
   主动，不占预算）/ 先给保守可试方案（引擎自身 B1 预算声明 best-guess，
   uncertain 如实标注——绝不由本层伪造第二诊断）/ 先暂停。
   ``SKIP_MARKERS`` / ``PAUSE_MARKERS``：用户可跳过/暂停的封闭词表——跳过 =
   保守可试方案或如实无行动，不锁住聊天；暂停 = 本域静默，可随时继续。
   ``correction_trace``：澄清/纠正后**行动改变依据可追踪**——内容寻址
   trace_id（D02 ``attr_`` / I03 ``sscmp_`` 同族）+ 前后出口 + 依据
   （答句分支 / reason 码 / 证据引用）+ 重开可见通道声明（随
   ``context_data["friction_decision"]`` checkpoint 持久，I03 N-3 同面）。

纪律（不造第二权威）：
- 诊断真源 = ``app.aurora.friction_diagnosis.diagnose_friction``（本模块零
  词牌、零问题库、零权重复制——所有语义判定都是引擎重放）；
- 干预名 = ``AURORA_INTERVENTION_TYPES`` 成员（import 期断言钉死）；
- 不确定类型 = ``AURORA_UNCERTAINTY_KINDS`` 既有成员；
- 零 IO、零模型调用、零用户文案（invitation 为 FIX97 裁决原文；例子只出
  封闭词表键，展示文案归客户端 l10n）；
- 行为开关 ``settings.NO_ACTION_CORRECTION_MODE`` ∈ {off, shadow, live}
  （默认 off = 零行为；shadow = 指标+结构化日志留痕、payload 零变化；
  live = 载荷出面——**本卡即 live 裁决语义的归属卡**，激活时有显式 WARN
  与 metric 标识，响应 I03 N-2「消费侧显式标识」）。未知值按 off 处理
  （fail-closed，不猜）。
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from loguru import logger

from app.aurora.friction_diagnosis import (
    DEFAULT_SESSION_QUESTION_LIMIT,
    FRICTION_DIAGNOSIS_VERSION,
    FRICTION_TYPES,
    FrictionDiagnosis,
    diagnose_friction,
)
from app.core.aurora_decision import AURORA_INTERVENTION_TYPES, AURORA_UNCERTAINTY_KINDS

NO_ACTION_SUPPLEMENT_VERSION = "no_action_supplement.v4.i04.v1"

# ---------------------------------------------------------------------------
# 封闭词表（冻结；扩展 = 词表变更过 reviewer）
# ---------------------------------------------------------------------------

#: FIX97 裁决的基本出口：单一自由输入（不依赖错误行动、不受每日解释气泡次数
#: 限制；AURORA_SEMANTIC_POLICY「无动作也可纠正」节原文）。
SUPPLEMENT_INVITATION = "还有什么情况需要我知道？"

#: 无动作/弃权出口（entry 可用面；act/ask 面各有既有纠正/回答通道，不重复给）。
_SUPPLEMENT_ENTRY_OUTCOMES: frozenset[str] = frozenset({"no_action", "abstain"})

#: 出口斜坡（AURORA_SEMANTIC_POLICY「澄清的判据」：仍不清楚时允许
#: 「直接说情况/先给保守可试方案/先暂停」——封闭三值）。
CLARIFICATION_EXIT_KINDS: frozenset[str] = frozenset({"tell_situation", "conservative_option", "pause"})

#: V4 自动澄清预算初值（policy：自动澄清 ≤1 轮；用户主动补充不算系统追问）。
V4_AUTO_CLARIFICATION_BUDGET = 1

#: 跳过词表（封闭；多字低碰撞——单关键词零判定的 I03 同款纪律。「跳过」在
#: 本域语义唯一：不回答当前问句、要一个可直接做的下一步或先放放）。
SKIP_MARKERS: tuple[str, ...] = (
    "跳过这个问题",
    "跳过",
    "不用问了",
    "别问了",
    "先不答",
    "不想回答",
    "skip this question",
    "skip",
)

#: 暂停词表（封闭；本域静默但输入与返回继续可用——FIX97「输入、返回和当前
#: 目标继续可用」同律）。
PAUSE_MARKERS: tuple[str, ...] = (
    "先暂停",
    "暂停一下",
    "先停一下",
    "停一下",
    "pause",
)

#: 临时约束种类（封闭词表；本卡只识别「今天口径」的时间预算——多天/每周
#: 口径属 A-05 契约 owner 的枚举迁移面，本层不猜）。
TEMPORARY_CONSTRAINT_KINDS: frozenset[str] = frozenset({"time_budget_today"})

#: 难度族（「不是不会」不追难度的守卫域：difficulty 直属 + skill/knowledge
#: 同属能力归因族——难度族占比 = 三者后验概率之和）。
DIFFICULTY_FAMILY: frozenset[str] = frozenset({"difficulty", "skill", "knowledge"})

#: 本模块对永久偏好面的写授权 = **空集**（结构保证：临时约束永不写永久偏好；
#: A-05 patch / self-model 写路径属既有 owner，本层零调用。测试冻结该常量）。
SUPPLEMENT_WRITE_SURFACES: frozenset[str] = frozenset()

#: 难度族占比守卫容差（浮点比较；纯否定证据下占比应严格不升）。
_DIFFICULTY_GUARD_EPSILON = 1e-9

# 「今天口径」时间预算（多 token 结构：今日词 + 上限词 + 数量 + 分钟单位，
# 拆任一算子即不命中——与 I03 结构模式同纪律；数量与单位之间允许空格；
# _UNIT 自身带 | 交替，引用处必须整组包裹——否则交替撕裂整条模式）。
_TODAY_SCOPE = r"(?:今天|今日|this morning|today)"
_LIMIT_WORD = r"(?:只有?|只剩?|最多|只能|至多|only)"
_QUANTITY = r"[0-9０-９一二两三四五六七八九十百半几]+"
_UNIT = r"(?:\s*分(?:钟)?\s*(?:左右|以内|之内)?|\s*min(?:ute)?s?\b)"

_TODAY_TIME_BUDGET_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        "today_budget_scope_limit_quantity_unit",
        _TODAY_SCOPE + r"[^。！？；;!?;]{0,8}" + _LIMIT_WORD + r"[^。！？；;!?;]{0,6}" + _QUANTITY + _UNIT,
    ),
    ("today_budget_limit_quantity_unit", _TODAY_SCOPE + _LIMIT_WORD + _QUANTITY + _UNIT),
    ("quantity_unit_today_scope", _LIMIT_WORD + _QUANTITY + _UNIT + r"[^。！？；;!?;]{0,6}" + _TODAY_SCOPE),
)


# ---------------------------------------------------------------------------
# 面一：无动作自由补充入口（FIX97，验收①）
# ---------------------------------------------------------------------------


def _diagnosis_payload(diagnosis: FrictionDiagnosis | Mapping[str, Any] | None) -> dict[str, Any]:
    """归一诊断载荷（对象 → to_dict；Mapping → 原样；None → 空表）。"""
    if diagnosis is None:
        return {}
    if isinstance(diagnosis, FrictionDiagnosis):
        return diagnosis.to_dict()
    return dict(diagnosis) if isinstance(diagnosis, Mapping) else {}


def supplement_entry(
    *,
    outcome: str | None,
    contender_primary_nominations: Mapping[str, str] | None = None,
    friction_type: str | None = None,
) -> dict[str, Any] | None:
    """无动作面的自由补充入口载荷（FIX97；纯函数）。

    - ``outcome is None``（连提案都没有）或 ∈ {no_action, abstain} → 入口可用；
    - act / ask 在场 → None（提案有自己的纠正通道、问句有自己的回答通道——
      不双轨出面）；
    - 例子（≤2）只给**不同操作后果**的候选：竞争带成员的首要提名互不相同
      且 ≥2 个才附（单一后果不是选择，不摆卡点清单）；目录外提名 fail-closed
      不给。
    - ``budget_impact="none"``：该入口是用户主动补充，不占系统追问预算。
    """
    if outcome is not None and outcome not in _SUPPLEMENT_ENTRY_OUTCOMES:
        return None
    examples: list[dict[str, str]] = []
    if contender_primary_nominations:
        seen_interventions: set[str] = set()
        ordered: list[dict[str, str]] = []
        for ftype in dict(contender_primary_nominations):
            intervention = str(contender_primary_nominations[ftype])
            if intervention in seen_interventions:
                continue  # 同一后果不重复出面
            if intervention not in AURORA_INTERVENTION_TYPES:
                continue  # 目录外 fail-closed（不猜）
            seen_interventions.add(intervention)
            ordered.append({"friction_type": str(ftype), "primary_intervention": intervention})
        if len(seen_interventions) >= 2:  # 单一后果不是「不同操作后果」的选择
            examples = ordered[:2]
    return {
        "schema_version": NO_ACTION_SUPPLEMENT_VERSION,
        "kind": "free_supplement_entry",
        "available": True,
        "invitation": SUPPLEMENT_INVITATION,
        "examples": examples,
        "budget_impact": "none",
        "surface_friction_type": friction_type,
    }


@dataclass(frozen=True)
class SupplementOutcome:
    """一次自由补充的完整结局（诊断重放 + 约束分类 + 守卫 + 经验记录 + 追踪）。"""

    diagnosis: FrictionDiagnosis
    constraint: dict[str, Any] | None
    trace: dict[str, Any]
    experience: dict[str, Any]
    guard_checks: dict[str, bool] = field(default_factory=dict)
    budget_impact: str = "none"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": NO_ACTION_SUPPLEMENT_VERSION,
            "diagnosis": self.diagnosis.to_dict(),
            "constraint": self.constraint,
            "trace": self.trace,
            "experience": self.experience,
            "guard_checks": dict(self.guard_checks),
            "budget_impact": self.budget_impact,
        }


def apply_free_supplement(
    supplement_text: str,
    *,
    prior: FrictionDiagnosis | Mapping[str, Any] | None = None,
    task_anchor: str | None = None,
    spine_state_keys: frozenset[str] | set[str] | list[str] | tuple[str, ...] = (),
    has_active_goal: bool | None = None,
    has_task_context: bool | None = None,
    days_since_progress: int | None = None,
    recent_failure_count: int | None = None,
    blocked_on_external: bool | None = None,
    materials_available_unused: bool | None = None,
    clarification_preference: str | None = None,
) -> SupplementOutcome:
    """用户主动补充 → 既有引擎重放（no_action 可纠正；不占系统追问预算）。

    - ``prior`` 可以是 None——**没有错误提案也能纠正**（FIX97 核心语义）；
    - 预算计数不递增（``questions_asked_*`` 恒按 prior 透传，缺省 0）；
    - 引擎对任何输入不 raise（韧性契约），本层同律：内部异常降级为 unknown
      no_action 诊断 + trace 如实标注（不伪装成功翻转）。
    """
    prior_payload = _diagnosis_payload(prior)
    prior_counters = (
        prior_payload.get("annotations", {}).get("input_snapshot", {})
        if isinstance(prior_payload.get("annotations"), Mapping)
        else {}
    )
    try:
        diagnosis = diagnose_friction(
            {
                "utterance": str(supplement_text or ""),
                "spine_state_keys": set(spine_state_keys or ()),
                "task_anchor": task_anchor,
                "has_active_goal": has_active_goal,
                "has_task_context": has_task_context,
                "days_since_progress": days_since_progress,
                "recent_failure_count": recent_failure_count,
                "blocked_on_external": blocked_on_external,
                "materials_available_unused": materials_available_unused,
                "clarification_preference": clarification_preference,
                "questions_asked_session": int(prior_counters.get("questions_asked_session") or 0),
                "questions_asked_day": int(prior_counters.get("questions_asked_day") or 0),
            }
        )
    except Exception as exc:  # noqa: BLE001 — 与引擎同款韧性契约（防御性；引擎自身不 raise）
        logger.warning("[NoActionSupplement] replay degraded: {!r}", exc)
        diagnosis = FrictionDiagnosis(
            outcome="no_action",
            friction_type="unknown",
            reasons=("E1.degraded_to_conservative",),
            uncertainty_kinds=("insufficient_context",),
            annotations={"degraded": True},
        )

    constraint = classify_supplement_constraint(supplement_text)
    guard_ok = difficulty_not_chased(
        prior_payload.get("posterior") or (),
        diagnosis.posterior,
        after_annotations=diagnosis.annotations,
    )
    trace = correction_trace(
        before_outcome=str(prior_payload.get("outcome")) if prior_payload.get("outcome") else None,
        after_outcome=diagnosis.outcome,
        basis={
            "channel": "free_supplement",
            "reason_codes": list(diagnosis.reasons),
            "evidence_refs": list(diagnosis.evidence_refs),
            "constraint_kind": (constraint or {}).get("kind"),
            "difficulty_guard_ok": guard_ok,
        },
    )
    experience = {
        "kind": "user_supplement_evidence",
        "scope": "session",
        "retractable": True,
        "permanent_preference_write": False,
        "evidence_refs": list(diagnosis.evidence_refs),
        "write_surfaces": sorted(SUPPLEMENT_WRITE_SURFACES),  # 恒空——写授权空集的结构声明
        "downstream_legality": "memory_gate",  # 下游入记忆必须过既有合法性门（I02 同纪律）
    }
    return SupplementOutcome(
        diagnosis=diagnosis,
        constraint=constraint,
        trace=trace,
        experience=experience,
        guard_checks={"difficulty_not_chased": guard_ok},
        budget_impact="none",
    )


# ---------------------------------------------------------------------------
# 面二：临时约束分类 + 难度族守卫（验收②）
# ---------------------------------------------------------------------------


def classify_supplement_constraint(text: str) -> dict[str, Any] | None:
    """「今天只有15分钟」类临时约束 → 会话作用域记录（纯函数）。

    判定是多 token 结构（今日词 + 上限词 + 数量 + 分钟单位）；拆任一算子即
    不命中（I03 结构模式同纪律）。**永不产生永久偏好写**：返回记录显式携带
    ``permanent_preference_write=False`` 与 ``expires_same_day=True``；非今日
    口径（每周/每次/永久表述）返回 None——那是 A-05 契约 owner 的枚举迁移面，
    本层不猜（fail-closed）。
    """
    body = str(text or "")
    if not body.strip():
        return None
    for pattern_id, pattern in _TODAY_TIME_BUDGET_PATTERNS:
        match = re.search(pattern, body, flags=re.IGNORECASE)
        if match:
            return {
                "schema_version": NO_ACTION_SUPPLEMENT_VERSION,
                "kind": "time_budget_today",
                "pattern_id": pattern_id,
                "matched_span": match.group(0),
                "scope": "this_session",
                "expires_same_day": True,
                "permanent_preference_write": False,
                "write_surfaces": sorted(SUPPLEMENT_WRITE_SURFACES),
            }
    return None


def _family_share(posterior: Any) -> float:
    """难度族（difficulty/skill/knowledge）后验占比。"""
    total = 0.0
    family = 0.0
    for item in posterior or ():
        try:
            ftype, prob = item[0], float(item[1])
        except (TypeError, ValueError, IndexError):
            continue
        total += max(prob, 0.0)
        if ftype in DIFFICULTY_FAMILY:
            family += max(prob, 0.0)
    return family / total if total > 0 else 0.0


def difficulty_not_chased(
    prior_posterior: Any,
    after_posterior: Any,
    *,
    after_annotations: Mapping[str, Any] | None = None,
) -> bool:
    """「不是不会」不追难度守卫（纯函数；消费层复核引擎 FIX-110 不变式）。

    判定域：补充文本的难度族 utterance 证据**全部为否定命中**时
    （``utterance_negated_matches`` 含难度族词牌且 ``utterance_matches`` 无
    难度族词牌），难度族后验占比相对先前不得上升——否定词牌零证据权重
    （「不是不会/不是太难」不得变成难度归因）。难度族正向词牌在场（用户
    真实自报难度）属合法归因，守卫不适用（True）；难度族否定证据不在场
    同样域外（True）。判定材料来自引擎注记，本层零词面复制——若未来改动
    让补充面绕过否定感知（否定词牌被计分），占比上升在此显式失败。
    """
    matched = ((after_annotations or {}).get("utterance_matches")) or []
    negated = ((after_annotations or {}).get("utterance_negated_matches")) or []

    def _is_family(item: Any) -> bool:
        return str(item).split(":", 1)[0] in DIFFICULTY_FAMILY

    matched_family = any(_is_family(item) for item in matched)
    negated_family = any(_is_family(item) for item in negated)
    if matched_family or not negated_family:
        return True
    prior_share = _family_share(prior_posterior)
    after_share = _family_share(after_posterior)
    ok = after_share <= prior_share + _DIFFICULTY_GUARD_EPSILON
    if not ok:
        logger.warning(
            "[NoActionSupplement] difficulty guard failed: prior_share={} after_share={} negated={}",
            round(prior_share, 6),
            round(after_share, 6),
            negated,
        )
    return ok


# ---------------------------------------------------------------------------
# 面三：一次决策性澄清 + 出口斜坡 + 纠正追踪（验收③）
# ---------------------------------------------------------------------------


def clarification_exit_ramp(
    *,
    conservative_option: Mapping[str, Any] | None = None,
    reason: str = "v4_clarification_budget_exhausted",
    prior_question_id: str | None = None,
) -> dict[str, Any]:
    """澄清预算尽后的封闭出口斜坡（绝不 surfaced 第二问）。

    - ``tell_situation``：直接说情况（自由补充入口——用户主动，不占预算）；
    - ``conservative_option``：先给保守可试方案（**只能来自引擎自身 B1 预算
      声明 best-guess 出口**——``source_reason`` 必须是引擎 reason 码；本层
      永不伪造第二诊断）；
    - ``pause``：先暂停（本域静默，输入与返回继续可用）。
    ``question`` 恒 None——斜坡出口结构上不携带追问。
    """
    option: dict[str, Any] | None = None
    if conservative_option is not None:
        intervention = str(conservative_option.get("intervention") or "")
        if intervention not in AURORA_INTERVENTION_TYPES:
            raise ValueError(f"conservative_option intervention {intervention!r} out of AURORA_INTERVENTION_TYPES")
        option = {
            "intervention": intervention,
            "uncertain": bool(conservative_option.get("uncertain", True)),
            "source_reason": str(conservative_option.get("source_reason") or ""),
            "delivery": "recommendation",  # J-05 同律：建议非执行
        }
        if not option["source_reason"]:
            raise ValueError("conservative_option must carry engine source_reason (no fabricated diagnosis)")
    return {
        "schema_version": NO_ACTION_SUPPLEMENT_VERSION,
        "kind": "clarification_exit_ramp",
        "kinds": sorted(CLARIFICATION_EXIT_KINDS),
        "question": None,
        "prior_question_id": prior_question_id,
        "conservative_option": option,
        "reason": reason,
        "supplement_invitation": SUPPLEMENT_INVITATION,
    }


def match_skip_marker(text: str) -> str | None:
    """封闭跳过词表命中（长词优先；无命中 None）。"""
    body = str(text or "").strip().lower()
    if not body:
        return None
    for marker in sorted(SKIP_MARKERS, key=len, reverse=True):
        if marker in body:
            return marker
    return None


def match_pause_marker(text: str) -> str | None:
    """封闭暂停词表命中（长词优先；无命中 None）。"""
    body = str(text or "").strip().lower()
    if not body:
        return None
    for marker in sorted(PAUSE_MARKERS, key=len, reverse=True):
        if marker in body:
            return marker
    return None


def correction_trace(
    *,
    before_outcome: str | None,
    after_outcome: str | None,
    basis: Mapping[str, Any],
    skipped: bool = False,
    paused: bool = False,
) -> dict[str, Any]:
    """纠正/澄清后的行动改变依据追踪（内容寻址；重开可见通道显式声明）。

    ``trace_id = nactrace_<sha256(version|before|after|basis)[:32]>``——同输入
    重放 id 恒定（D02 ``attr_`` / I03 ``sscmp_`` 同族，重放幂等不虚增）。
    ``user_can``：用户可跳过/暂停（验收③）；``reopen_visible_via``：本追踪随
    ``context_data["friction_decision"]`` checkpoint 持久（I03 N-3 同面），
    重开后可见。``permanent_preference_write`` 恒 False。
    """
    basis_payload = {str(k): basis[k] for k in sorted(basis, key=str)}
    digest = hashlib.sha256(
        "|".join(
            (
                NO_ACTION_SUPPLEMENT_VERSION,
                str(before_outcome),
                str(after_outcome),
                json.dumps(basis_payload, ensure_ascii=False, sort_keys=True, default=str),
            )
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": NO_ACTION_SUPPLEMENT_VERSION,
        "trace_id": f"nactrace_{digest[:32]}",
        "before_outcome": before_outcome,
        "after_outcome": after_outcome,
        "changed": before_outcome != after_outcome,
        "basis": basis_payload,
        "skipped": skipped,
        "paused": paused,
        "user_can": {"skip": True, "pause": True},
        "permanent_preference_write": False,
        "engine_version": FRICTION_DIAGNOSIS_VERSION,
        "reopen_visible_via": "context_data.friction_decision",
    }


def budget_declared_replay(
    input_snapshot: Mapping[str, Any],
    *,
    answer: tuple[str, str] | None = None,
    clarification_preference: str | None = None,
) -> FrictionDiagnosis:
    """以「会话问题预算已用完」声明重放引擎（J-05 同律：绝不由本层伪造诊断）。

    引擎自身的预算尽出口接管：有区分度 → B1 best-guess（act + uncertain 标注）；
    exact tie → B3 no_action；无证据 → B2 no_action。出口斜坡的保守可试方案
    只能取自这里。``answer``：已答分支 (question_id, branch_key)，跳过路径
    （无回答）传 None——只声明预算，不注入未发生的答案。
    """
    snapshot = dict(input_snapshot)
    snapshot["answered_branches"] = [list(pair) for pair in (snapshot.get("answered_branches") or [])]
    if answer is not None:
        snapshot["answered_branches"].append([answer[0], answer[1]])
    snapshot["questions_asked_session"] = DEFAULT_SESSION_QUESTION_LIMIT
    if clarification_preference is not None:
        snapshot["clarification_preference"] = clarification_preference
    return diagnose_friction(snapshot)


def conservative_option_from(diagnosis: FrictionDiagnosis) -> dict[str, Any] | None:
    """引擎预算尽出口 → 出口斜坡的保守可试方案（无提名 → None，不编造）。

    只有引擎自身 reason 码（B1 best-guess）背书的提名才可作保守方案；
    B2/B3 no_action 出口如实给 None（斜坡只剩直接说情况/先暂停）。
    """
    if not diagnosis.nominated_interventions:
        return None
    if "B1.budget_exhausted_best_guess" not in diagnosis.reasons:
        return None
    return {
        "intervention": diagnosis.nominated_interventions[0],
        "uncertain": True,
        "source_reason": "B1.budget_exhausted_best_guess",
    }


# ---------------------------------------------------------------------------
# import 期不变式（词表纪律；测试另有冻结断言）
# ---------------------------------------------------------------------------

assert set(DIFFICULTY_FAMILY) <= set(FRICTION_TYPES), "DIFFICULTY_FAMILY must be a subset of FRICTION_TYPES"
assert frozenset() == SUPPLEMENT_WRITE_SURFACES, "supplement layer must never gain permanent-preference write surfaces"
assert V4_AUTO_CLARIFICATION_BUDGET >= 1, "auto clarification budget must allow at least one decisive question"
for _kind in CLARIFICATION_EXIT_KINDS:
    assert isinstance(_kind, str) and _kind
for _uncertainty in ("insufficient_context",):
    assert _uncertainty in AURORA_UNCERTAINTY_KINDS, "uncertainty vocabulary must stay engine-aligned"

__all__ = [
    "CLARIFICATION_EXIT_KINDS",
    "DIFFICULTY_FAMILY",
    "DEFAULT_SESSION_QUESTION_LIMIT",
    "NO_ACTION_SUPPLEMENT_VERSION",
    "PAUSE_MARKERS",
    "SKIP_MARKERS",
    "SUPPLEMENT_INVITATION",
    "SUPPLEMENT_WRITE_SURFACES",
    "SupplementOutcome",
    "TEMPORARY_CONSTRAINT_KINDS",
    "V4_AUTO_CLARIFICATION_BUDGET",
    "apply_free_supplement",
    "budget_declared_replay",
    "classify_supplement_constraint",
    "clarification_exit_ramp",
    "conservative_option_from",
    "correction_trace",
    "difficulty_not_chased",
    "match_pause_marker",
    "match_skip_marker",
    "supplement_entry",
]
