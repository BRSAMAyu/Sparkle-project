"""V4-U10 · 资料→错题→练习→检验连续体验（learning-journey 契约层）。

定位（v4/04_tasks/cards/V4-U10.md，locks: ui-learning；规格：
``v4/02_design/SCREEN_FAMILIES.md`「星图 / 学习 / 错题 / 资料」段、
MASTER_DESIGN §5「人机合作不偷走学习」/ §6「示例→自己做→检查」）：

统一材料/错题/练习/检验为目标上下文入口。本模块是**消费侧契约层，不是第二
权威**——三个既有权威原样复用、逐条 import 期钉死：

1. **人机权限与答案红化** = V4-I07 ``app.core.hybrid_policy``：
   - 检验段推进只经 :func:`hybrid_policy.next_scaffold_step`（用户选择且证据
     支持；阶段永不回退；检验是链终点）；
   - 检验答案键剥除只经 :func:`hybrid_policy.redact_independent_check`
     （``INDEPENDENT_CHECK_ANSWER_KEYS`` 封闭集），本模块不复制键集；
   - 答案本体只在服务端（``tasks.guide_json`` 策略块 ``independent_check``
     子结构 = 判分权威），**任何**客户端载荷必须过 :func:`check_client_payload`
     泄漏探针。
2. **来源可见与版本** = SCREEN_FAMILIES「来源badge能跳原文片段」+ 卡验收
   「来源版本正确」：:class:`JourneySourceRef` 携带来源 id + 版本 + 片段锚；
   版本从真实行（stored_files/错误记录的 ``updated_at``）读取，重绑定必须
   过 :func:`ensure_source_version_current`（陈旧声明拒绝，不臆测刷新）。
3. **解析诚实** = SCREEN_FAMILIES「OCR不支持时提供手输入；不假装图片已识别」+
   卡验收「真实文件/图片失败无伪造解析」：:class:`MaterialParseOutcome`
   封闭状态词表，``failed/unsupported`` 状态下**构造期拒绝**携带任何解析文本
   （不伪造解析是构造不变量，不是渲染约定）。

四域封闭词表（冻结；扩展 = bump ``LEARNING_JOURNEY_SCHEMA_VERSION`` 并过
reviewer）：

- 旅程段 :data:`JOURNEY_SEGMENTS`：materials（资料）→ errors（错题）→
  practice（练习）→ independent_check（检验）；后两段与 I07 脚手架链
  ``attempt`` / ``independent_check`` 对齐（import 期断言），资料/错题是
  旅程入口段，不进入脚手架语义。
- 解析状态 :data:`PARSE_STATUSES`：``parsed`` / ``failed`` / ``unsupported``
  / ``manual``（手输替代）。
- 检验裁决 reason :data:`CHECK_VERDICT_REASONS`：``OK.check_graded_correct``
  / ``OK.check_graded_incorrect`` / ``HOLD.evidence_not_supported`` /
  ``HOLD.scaffold_not_at_check`` / ``HOLD.check_authority_missing`` /
  ``HOLD.check_ungradeable``。（v2 bump：一审 R1 N-5 词表收口——
  ``check_authority_missing`` 原为服务层词表外字面量、ungradeable 原误落
  ``OK.check_graded_incorrect``，一并归拢入封闭集。）

数据面 unknown 语义（I07/B05 同款纪律）：块缺失/脏值 → 解析降级 + 原因，
不臆测回填；判分只做确定性归一比对（strip/casefold/空白折叠），无模型调用
（模型命题生成属后续卡，本卡零 LLM）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.core.hybrid_policy import (
    INDEPENDENT_CHECK_FLAG_KEY,
    INDEPENDENT_CHECK_KIND,
    SCAFFOLD_STAGE_ATTEMPT,
    SCAFFOLD_STAGE_EXAMPLE,
    SCAFFOLD_STAGE_INDEPENDENT_CHECK,
    SCAFFOLD_STAGES,
    ScaffoldDecision,
    contains_independent_check_answer,
    next_scaffold_step,
    redact_independent_check,
)

#: v2（2026-09-28 一审 R1 N-5 词表收口：+``HOLD.check_authority_missing`` /
#: +``HOLD.check_ungradeable``；v1 首发未外发，bump 随本卡整改走冻结集更新流程）。
LEARNING_JOURNEY_SCHEMA_VERSION = "learning_journey.v2"

# ---------------------------------------------------------------------------
# 封闭词表（冻结；扩展 = bump 版本并过 reviewer）
# ---------------------------------------------------------------------------

#: 旅程段（SCREEN_FAMILIES「材料、错题与词汇沿目标打开」+ MASTER_DESIGN §6）。
JOURNEY_SEGMENTS: frozenset[str] = frozenset({"materials", "errors", "practice", "independent_check"})

SEGMENT_MATERIALS = "materials"
SEGMENT_ERRORS = "errors"
SEGMENT_PRACTICE = "practice"
SEGMENT_INDEPENDENT_CHECK = "independent_check"

#: 解析状态（SCREEN_FAMILIES「OCR不支持时提供手输入；不假装图片已识别」）。
PARSE_STATUSES: frozenset[str] = frozenset({"parsed", "pending", "failed", "unsupported", "manual"})

PARSE_PARSED = "parsed"
PARSE_PENDING = "pending"  # 在途（既非成功也非失败；不宣称已解析）
PARSE_FAILED = "failed"
PARSE_UNSUPPORTED = "unsupported"
PARSE_MANUAL = "manual"

#: 解析失败需手输替代的状态集（failed/unsupported 共享同一替代语义）。
PARSE_MANUAL_INPUT_REQUIRED: frozenset[str] = frozenset({PARSE_FAILED, PARSE_UNSUPPORTED})

#: 检验裁决 reason（封闭集；扩展 = bump 版本并过 reviewer）。
CHECK_VERDICT_REASONS: frozenset[str] = frozenset(
    {
        "OK.check_graded_correct",
        "OK.check_graded_incorrect",
        "HOLD.evidence_not_supported",
        "HOLD.scaffold_not_at_check",
        "HOLD.check_authority_missing",
        "HOLD.check_ungradeable",
    }
)

CHECK_REASON_CORRECT = "OK.check_graded_correct"
CHECK_REASON_INCORRECT = "OK.check_graded_incorrect"
CHECK_REASON_HOLD_EVIDENCE = "HOLD.evidence_not_supported"
CHECK_REASON_HOLD_NOT_AT_CHECK = "HOLD.scaffold_not_at_check"
CHECK_REASON_HOLD_AUTHORITY_MISSING = "HOLD.check_authority_missing"
CHECK_REASON_UNGRADEABLE = "HOLD.check_ungradeable"

_SCAFFOLD_TO_SEGMENT: dict[str, str] = {
    SCAFFOLD_STAGE_EXAMPLE: SEGMENT_PRACTICE,
    SCAFFOLD_STAGE_ATTEMPT: SEGMENT_PRACTICE,
    SCAFFOLD_STAGE_INDEPENDENT_CHECK: SEGMENT_INDEPENDENT_CHECK,
}

# 旅程段与 I07 脚手架链的对齐断言（不复制权威；漂移即 import 失败）。
assert SCAFFOLD_STAGE_INDEPENDENT_CHECK == SEGMENT_INDEPENDENT_CHECK
assert {SCAFFOLD_STAGE_EXAMPLE, SCAFFOLD_STAGE_ATTEMPT, SCAFFOLD_STAGE_INDEPENDENT_CHECK} <= SCAFFOLD_STAGES
assert INDEPENDENT_CHECK_KIND == SEGMENT_INDEPENDENT_CHECK
assert INDEPENDENT_CHECK_FLAG_KEY == SEGMENT_INDEPENDENT_CHECK

_WHITESPACE_RUN = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# 来源可见与版本（验收「来源版本正确」）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class JourneySourceRef:
    """材料/错题的来源引用（来源badge 面：id + 版本 + 片段锚）。

    版本语义：从真实行读取（stored_files/error_records 的 ``updated_at`` ISO
    串或内容版本戳），**装配时点读出，不在消费方臆测**；重绑定/续用必须过
    :func:`ensure_source_version_current`。``fragment_anchor`` 指向原文片段
    （SCREEN_FAMILIES「来源badge能跳原文片段」），缺省表示整篇。
    """

    source_id: str
    source_version: str
    fragment_anchor: str | None = None
    source_kind: str = "document"  # document | error_record | manual_text

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise ValueError("source_id must be a non-empty string")
        if not isinstance(self.source_version, str) or not self.source_version.strip():
            raise ValueError("source_version must be a non-empty string (来源版本不得伪造)")

    def to_dict(self) -> dict[str, str | None]:
        return {
            "source_id": self.source_id,
            "source_version": self.source_version,
            "fragment_anchor": self.fragment_anchor,
            "source_kind": self.source_kind,
        }


def ensure_source_version_current(*, current_version: str, claimed_version: str) -> str:
    """重绑定/续用前的版本新鲜门：声明版本 ≠ 当前版本 → 拒绝（不臆测刷新）。

    返回当前版本（调用方以此为准继续）；不匹配抛
    :class:`SourceVersionMismatchError`——「来源版本正确」的机制化：陈旧引用
    显式失败，让用户重取，而不是拿旧版本冒充。
    """
    if not isinstance(current_version, str) or not current_version.strip():
        raise ValueError("current_version must be a non-empty string")
    if not isinstance(claimed_version, str) or not claimed_version.strip():
        raise ValueError("claimed_version must be a non-empty string")
    if claimed_version != current_version:
        raise SourceVersionMismatchError(current_version, claimed_version)
    return current_version


class SourceVersionMismatchError(ValueError):
    """声明来源版本与当前版本不符（陈旧引用；显式失败，不静默续用）。"""

    def __init__(self, current_version: str, claimed_version: str) -> None:
        self.current_version = current_version
        self.claimed_version = claimed_version
        super().__init__(f"source version mismatch: current={current_version!r} claimed={claimed_version!r}")


# ---------------------------------------------------------------------------
# 解析诚实（验收「真实文件/图片失败无伪造解析」）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MaterialParseOutcome:
    """一次材料解析的诚实结果（构造期不变量，非渲染约定）。

    - ``parsed``：必须有非空 ``text``，``manual_input_required=False``；
    - ``failed`` / ``unsupported``：**构造期拒绝携带 text**（传 text 即
      ValueError——伪造解析在数据层就不可能存在），``manual_input_required=True``
      （SCREEN_FAMILIES「OCR不支持时提供手输入」）；
    - ``manual``：用户手输文本（非空），``manual_input_required=False``
      （替代已发生），``reason`` 记录替代原因（如 ocr_unavailable）。
    """

    status: str
    text: str | None = None
    reason: str | None = None
    manual_input_required: bool = False

    def __post_init__(self) -> None:
        if self.status not in PARSE_STATUSES:
            raise ValueError(f"parse status out of vocabulary: {self.status!r}")
        if self.status == PARSE_PARSED:
            if not isinstance(self.text, str) or not self.text.strip():
                raise ValueError("parsed outcome requires non-empty text")
            if self.manual_input_required:
                raise ValueError("parsed outcome cannot require manual input")
        elif self.status == PARSE_PENDING:
            # 在途：既非成功也非失败，不携带文本、不需要手输（等真实结果）。
            if self.text is not None:
                raise ValueError("pending outcome must not carry text")
            if self.manual_input_required:
                raise ValueError("pending outcome must not require manual input")
        elif self.status in (PARSE_FAILED, PARSE_UNSUPPORTED):
            # 验收红线：失败/不支持 → 无解析文本（伪造解析在构造期即拒绝）。
            if self.text is not None:
                raise ValueError(f"{self.status} outcome must not carry parsed text (no fake parse)")
            if not self.manual_input_required:
                raise ValueError(f"{self.status} outcome must set manual_input_required")
        elif self.status == PARSE_MANUAL:
            if not isinstance(self.text, str) or not self.text.strip():
                raise ValueError("manual outcome requires the user-typed text")
            if self.manual_input_required:
                raise ValueError("manual outcome already carries the user-typed text")

    @property
    def parsed_ok(self) -> bool:
        return self.status == PARSE_PARSED

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "text": self.text,
            "reason": self.reason,
            "manual_input_required": self.manual_input_required,
        }


# ---------------------------------------------------------------------------
# 旅程段映射与检验推进（消费 I07 脚手架权威）
# ---------------------------------------------------------------------------


def journey_segment_for_scaffold(stage: str) -> str:
    """I07 脚手架 stage → 旅程主操作段（example/attempt → practice；
    independent_check → independent_check）。脏值 → practice（保守：
    先练习，绝不把未到检验的用户推进检验空页）。"""
    return _SCAFFOLD_TO_SEGMENT.get(stage, SEGMENT_PRACTICE)


def request_independent_check(
    *,
    stage: str,
    hint_level: str,
    evidence_supported: bool,
) -> tuple[ScaffoldDecision, str | None]:
    """用户在旅程页点「检验」→ 是否放行进入检验段。

    消费 I07 :func:`hybrid_policy.next_scaffold_step`（用户选择=True 的单点
    转移）：证据支持 → 推进（返回新决策，``hold_reason=None``）；证据不支持
    → 原地（返回当前态决策 + ``hold_reason=HOLD.evidence_not_supported``）。
    已在检验段 → ``OK.independent_check_reached``（链终点，幂等放行）。
    """
    decision = next_scaffold_step(
        stage=stage,
        hint_level=hint_level,
        user_chose=True,
        evidence_supported=evidence_supported,
    )
    if decision.stage == SCAFFOLD_STAGE_INDEPENDENT_CHECK:
        return decision, None
    return decision, CHECK_REASON_HOLD_EVIDENCE


# ---------------------------------------------------------------------------
# 检验判分（验收「答案不泄漏到检验用户可读状态」）
# ---------------------------------------------------------------------------


def _normalize_answer(value: Any) -> str:
    """确定性答案归一：strip + casefold + 空白折叠（零模型、零概率面）。"""
    if not isinstance(value, str):
        return ""
    return _WHITESPACE_RUN.sub(" ", value).strip().casefold()


def _extract_expected_answers(independent_check: dict[str, Any]) -> list[str]:
    """从判分权威子结构读预期答案（服务端 guide_json 策略块内）。

    只认 ``answer`` 单键——它是 I07 冻结答案键集（``INDEPENDENT_CHECK_ANSWER_KEYS``）
    的成员，红化门覆盖；**不发明**等价答案新键（任何新答案键都必须先进 I07
    键集扩展 = contract-owner 变更，否则红化门不识别即成泄漏面）。
    缺失 → 判分权威不完整，返回空列表（调用方以 ungradeable 处理，不猜）。
    """
    raw_single = independent_check.get("answer")
    if isinstance(raw_single, str) and raw_single.strip():
        return [raw_single]
    return []


@dataclass(frozen=True)
class CheckGradingResult:
    """一次检验提交的判分结果（客户端可见面 = 零答案材料）。

    ``feedback`` 是**泛化**教学反馈（预设短语，按对/错取自封闭词表），不承载
    解析/答案/解析步骤——``explanation``/``solution`` 属答案键（I07 R2-1），
    揭示面归后续教学卡，本卡一律不出口。
    """

    graded: bool
    correct: bool | None
    reason: str
    feedback: str | None = None

    def to_client_payload(self) -> dict[str, Any]:
        """客户端载荷（泄漏探针在出口强制执行——答案材料出现在载荷即 raise）。"""
        payload: dict[str, Any] = {
            "schema_version": LEARNING_JOURNEY_SCHEMA_VERSION,
            "graded": self.graded,
            "correct": self.correct,
            "reason": self.reason,
        }
        if self.feedback is not None:
            payload["feedback"] = self.feedback
        assert_client_payload_clean(payload)
        return payload


_FEEDBACK_CORRECT = "检验通过：这一步由你独立完成。"
_FEEDBACK_INCORRECT = "这次未通过：回到练习段再试一次，检验会保留。"
_FEEDBACK_UNGRADEABLE = "这道检验缺少判分依据，暂不能判分；请先反馈给系统。"


def grade_independent_check(
    independent_check: dict[str, Any],
    submitted: Any,
) -> CheckGradingResult:
    """对一次检验提交做确定性判分（零模型）。

    - 判分权威 = 服务端策略块 ``independent_check`` 子结构的 ``answer``
      单键（I07 冻结答案键集成员，红化门覆盖；``accepted_answers`` 属 V3
      exam_sprint 域（``schemas/exam_sprint.py``），不在 I07 契约与本卡
      判分权威内——R1 F-4 勘误：本 docstring 原误称权威含该键）；
    - 归一比对（strip/casefold/空白折叠）；命中预期答案 → 正确；
    - 判分权威不完整（无 ``answer``）→ ``graded=False, correct=None`` +
      ``HOLD.check_ungradeable``（不猜不伪造判分）；
    - 返回结果**不携带**预期答案/解析/解释；``to_client_payload()`` 出口有
      泄漏探针（答案键或 independent_check 节点出现在载荷即 raise）。
    """
    if not isinstance(independent_check, dict):
        raise ValueError("independent_check authority must be a dict")
    expected = _extract_expected_answers(independent_check)
    if not expected:
        return CheckGradingResult(False, None, CHECK_REASON_UNGRADEABLE, _FEEDBACK_UNGRADEABLE)
    submitted_norm = _normalize_answer(submitted)
    correct = any(_normalize_answer(item) == submitted_norm for item in expected)
    return CheckGradingResult(
        graded=True,
        correct=correct,
        reason=CHECK_REASON_CORRECT if correct else CHECK_REASON_INCORRECT,
        feedback=_FEEDBACK_CORRECT if correct else _FEEDBACK_INCORRECT,
    )


def assert_client_payload_clean(payload: Any) -> None:
    """泄漏探针（出口强制）：载荷内不得有 independent_check 节点或其答案键。

    唯一实现 = I07 :func:`hybrid_policy.contains_independent_check_answer`
    （不造第二探针）；客户端载荷装配点的最后一道门。
    """
    if contains_independent_check_answer(payload):
        raise ValueError("check client payload leaks independent_check answer material")


def redact_for_client(payload: Any) -> tuple[Any, tuple[str, ...]]:
    """任意旅程载荷的客户端投影门（消费 I07 红化权威，透传剥除路径）。"""
    return redact_independent_check(payload)


__all__ = [
    "CHECK_REASON_CORRECT",
    "CHECK_REASON_HOLD_AUTHORITY_MISSING",
    "CHECK_REASON_HOLD_EVIDENCE",
    "CHECK_REASON_HOLD_NOT_AT_CHECK",
    "CHECK_REASON_INCORRECT",
    "CHECK_REASON_UNGRADEABLE",
    "CHECK_VERDICT_REASONS",
    "JOURNEY_SEGMENTS",
    "CheckGradingResult",
    "JourneySourceRef",
    "LEARNING_JOURNEY_SCHEMA_VERSION",
    "MaterialParseOutcome",
    "PARSE_FAILED",
    "PARSE_MANUAL",
    "PARSE_MANUAL_INPUT_REQUIRED",
    "PARSE_PARSED",
    "PARSE_PENDING",
    "PARSE_STATUSES",
    "PARSE_UNSUPPORTED",
    "SEGMENT_ERRORS",
    "SEGMENT_INDEPENDENT_CHECK",
    "SEGMENT_MATERIALS",
    "SEGMENT_PRACTICE",
    "SourceVersionMismatchError",
    "assert_client_payload_clean",
    "ensure_source_version_current",
    "grade_independent_check",
    "journey_segment_for_scaffold",
    "redact_for_client",
    "request_independent_check",
]
