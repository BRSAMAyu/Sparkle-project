"""E-04 face adapters — 评测对象与生产代码的单一连接层。

每个 sub-suite adapter 做三件事（全部调用/镜像生产真源，不造第二套真值）：

1. ``rule_view(payload)``：调用**生产规则层**（decide_allocation /
   evaluate_intervention_policy / decide_joint / classify_by_rules）得到
   可行集、规则缺省、semantic_eligible——与 harness 的冻结期望比对（漂移绊线）。
2. ``build_prompt(case, rule_view)``：按生产 ``_semantic_refine`` 同款插值
   构造 prompt（同一 format 参数、同一截断、同一情境摘要函数）。
3. ``extract_choice(payload)``：按生产同款字段提取/归一（closed-set 引擎的
   strip().lower() / regex 归一），JSON 解析统一走生产
   ``LLMService._parse_json_payload``（静态方法直接复用）。

温度镜像生产：semantic-tier 通道经 ``chat_json`` 默认 temperature=0.3；
Stage19 extractor 显式 temperature=0.0。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.aurora.intervention_policy import (
    InterventionPolicyEngine,
    InterventionPolicyFactors,
    SEMANTIC_PROMPT as INTERVENTION_PROMPT,
    evaluate_intervention_policy,
)
from app.aurora.joint_decision import (
    JOINT_SEMANTIC_PROMPT,
    decide_joint,
    decide_joint_two_step,
)
from app.services.action_allocation_policy import (
    SEMANTIC_PROMPT as ALLOCATION_PROMPT,
    decide_allocation,
)
from app.services.llm_service import LLMService
from app.services.memory_storage_gate import (
    SEMANTIC_PROMPT as GATE_PROMPT,
    StorageGateCandidate,
    classify_by_rules,
)
from app.services.llm_extractor_service import LlmExtractorService

EXTRACTOR_PROMPT_PATH = LlmExtractorService.PROMPT_PATH


def parse_production_json(raw: str) -> Any | None:
    """生产 JSON 解析（LLMService._parse_json_payload 静态复用，含围栏/思维链剥离）。"""
    return LLMService._parse_json_payload(raw, response_kind="chat")


def live_prompts() -> dict[str, str]:
    """现役生产 prompt 文本（registry 校验 sha 用）。"""
    return {
        "aurora.intervention": INTERVENTION_PROMPT,
        "aurora.joint": JOINT_SEMANTIC_PROMPT,
        "action.allocation": ALLOCATION_PROMPT,
        "memory.gate": GATE_PROMPT,
        "memory.extract": EXTRACTOR_PROMPT_PATH.read_text(encoding="utf-8"),
    }


# --- RuleView -----------------------------------------------------------------


@dataclass
class RuleView:
    semantic_eligible: bool
    feasible: tuple[str, ...] | None  # closed-set 引擎：排序后可行项；extractor: None
    rule_default: str | None  # 规则层缺省选择/裁决
    scenario: str = ""  # joint 面：annotations.scenario_summary（生产随行数据）
    factor_flags: dict[str, Any] | None = None  # joint 面：intervention factors 原始投影
    decision_allocation_mode: str | None = None  # joint 面：决策实际携带的分配 mode

    def matches_expectation(self, expected: Any) -> tuple[bool, str]:
        if bool(expected.semantic_eligible) != self.semantic_eligible:
            return False, f"semantic_eligible drift: frozen={expected.semantic_eligible} live={self.semantic_eligible}"
        if expected.feasible is not None or self.feasible is not None:
            frozen = expected.feasible or ()
            live = self.feasible or ()
            if tuple(sorted(frozen)) != tuple(sorted(live)):
                return False, f"feasible drift: frozen={sorted(frozen)} live={sorted(live)}"
        if (expected.rule_default or None) != (self.rule_default or None):
            return False, f"rule_default drift: frozen={expected.rule_default!r} live={self.rule_default!r}"
        return True, "ok"


# --- sub-suite adapters ---------------------------------------------------------


class InterventionFace:
    """A-02 L2 提名（aurora.intervention）。"""

    sub_suite = "aurora.intervention"

    @staticmethod
    def rule_view(payload: dict[str, Any]) -> RuleView:
        factors = InterventionPolicyFactors.coerce(payload.get("factors"))
        decision = evaluate_intervention_policy(factors)
        return RuleView(
            semantic_eligible=bool(decision.semantic_eligible),
            feasible=tuple(sorted(decision.feasible_interventions)),
            rule_default=decision.selected,
        )

    @staticmethod
    def build_prompt(payload: dict[str, Any], view: RuleView) -> str:
        factors = InterventionPolicyFactors.coerce(payload.get("factors"))
        # 生产同款：feasible join + _context_summary（真实静态方法）
        return INTERVENTION_PROMPT.format(
            feasible=", ".join(view.feasible or ()),
            context_summary=InterventionPolicyEngine._context_summary(factors),
        )

    @staticmethod
    def extract_choice(parsed: Any) -> str | None:
        # 生产同款：_extract_field("intervention") + strip().lower()
        if isinstance(parsed, dict):
            value = parsed.get("intervention")
            if isinstance(value, str) and value.strip():
                return value.strip().lower()
        return None


class JointFace:
    """A-04 联合裁决（aurora.joint）——生产两步链（decide_joint_two_step）。"""

    @staticmethod
    def rule_view(payload: dict[str, Any]) -> RuleView:
        # 生产同款：spine 升格链走 decide_joint_two_step(factors, task_factors)
        joint = decide_joint_two_step(payload.get("intervention_factors"), payload.get("allocation"))
        names = tuple(dict.fromkeys(name for name, _ in joint.joint_feasible_pairs if name))
        allocation_mode = getattr(joint.allocation, "mode", None) if joint.allocation is not None else None
        return RuleView(
            semantic_eligible=bool(joint.semantic_eligible),
            feasible=names,
            rule_default=joint.selected,
            scenario=str(joint.annotations.get("scenario_summary") or ""),
            factor_flags=payload.get("intervention_factors") or {},
            decision_allocation_mode=allocation_mode,
        )

    @staticmethod
    def build_prompt(payload: dict[str, Any], view: RuleView) -> str:
        # 生产同款渲染：情境旗标（decision_mode 以决策携带的分配事实为准）+ 场景
        factors = InterventionPolicyFactors.coerce(view.factor_flags)
        decision_mode = view.decision_allocation_mode or factors.allocation_mode or "none"
        context_summary = "; ".join(
            (
                f"task_context={'yes' if factors.has_task_context else 'no'}",
                f"allocation_mode={decision_mode}",
                f"quiet_hours={'yes' if factors.quiet_hours else 'no'}",
                f"explicit_request={'yes' if factors.explicit_user_request else 'no'}",
            )
        )
        scenario = (view.scenario or "").strip() or "（无触发摘要）"
        return JOINT_SEMANTIC_PROMPT.format(
            feasible=", ".join(view.feasible or ()),
            context_summary=context_summary,
            scenario=scenario[:300],
        )

    @staticmethod
    def extract_choice(parsed: Any) -> str | None:
        if isinstance(parsed, dict):
            value = parsed.get("intervention")
            if isinstance(value, str) and value.strip():
                return value.strip().lower()
        return None


class AllocationFace:
    """X-02 执行分配（action.allocation）。"""

    sub_suite = "action.allocation"

    @staticmethod
    def rule_view(payload: dict[str, Any]) -> RuleView:
        decision = decide_allocation(payload.get("factors"))
        return RuleView(
            semantic_eligible=bool(decision.annotations.get("semantic_eligible")),
            feasible=tuple(sorted(decision.feasible_modes)),
            rule_default=decision.mode,
        )

    @staticmethod
    def build_prompt(payload: dict[str, Any], view: RuleView) -> str:
        # 生产同款 format 参数（含 task_summary[:300] 截断）
        from app.services.action_allocation_policy import AllocationFactors

        factors = AllocationFactors.coerce(payload.get("factors"))
        return ALLOCATION_PROMPT.format(
            task_type=factors.task_type or "unknown",
            task_summary=(factors.task_summary or "")[:300],
            ownership=factors.cognitive_ownership or "unknown",
            tool_advantage=factors.tool_advantage or "unknown",
            risk_class=factors.risk_class or "unknown",
            reversible=factors.reversible,
            time_pressure=factors.time_pressure or "unknown",
        )

    @staticmethod
    def extract_choice(parsed: Any) -> str | None:
        # 生产同款 _parse_mode：mode 字段 strip().lower() ∈ 词表
        if isinstance(parsed, dict):
            value = parsed.get("mode")
            if isinstance(value, str) and value.strip():
                mode = value.strip().lower()
                return mode if mode in {"human", "agent", "hybrid"} else mode
        return None


class GateFace:
    """M-02 记忆入库五分类（memory.gate）。"""

    sub_suite = "memory.gate"

    @staticmethod
    def _candidate(payload: dict[str, Any]) -> StorageGateCandidate:
        return StorageGateCandidate(
            user_id="eval-user",
            summary=str(payload.get("summary") or ""),
            subject_type=str(payload.get("subject_type") or "self"),
            source_type=str(payload.get("source_type") or "user_state"),
            source_lane=str(payload.get("source_lane") or "inferred_extraction"),
        )

    @classmethod
    def rule_view(cls, payload: dict[str, Any]) -> RuleView:
        decision = classify_by_rules(cls._candidate(payload))
        return RuleView(
            semantic_eligible=bool(decision.annotations.get("semantic_eligible")),
            feasible=("current_state", "event", "ignore", "store", "confirm"),  # 五类恒全集（无代码 closed-set）
            rule_default=decision.verdict,
        )

    @classmethod
    def build_prompt(cls, payload: dict[str, Any], view: RuleView) -> str:
        candidate = cls._candidate(payload)
        return GATE_PROMPT.format(
            subject_type=candidate.subject_type,
            source_type=candidate.source_type,
            source_lane=candidate.source_lane,
            summary=str(candidate.summary or "")[:400],
        )

    @staticmethod
    def extract_choice(parsed: Any) -> str | None:
        # 生产同款 _parse_verdict：正则从任意输出里捞五类之一
        import re as _re

        try:
            if isinstance(parsed, dict):
                raw = str(parsed.get("class") or "").strip().lower()
            else:
                raw = str(parsed or "").strip().lower()
            match = _re.search(r"(store|event|current_state|ignore|confirm)", raw)
            return match.group(1) if match else None
        except Exception:
            return None


class ExtractFace:
    """Stage19 LLM 抽取（memory.extract）。"""

    sub_suite = "memory.extract"

    @staticmethod
    def rule_view(payload: dict[str, Any]) -> RuleView:
        # extractor 无规则可行集；规则面（RuleYAdapter.validate）在 grading 里逐候选调用
        return RuleView(semantic_eligible=True, feasible=None, rule_default=None)

    @staticmethod
    def build_prompt(payload: dict[str, Any], view: RuleView) -> tuple[str, str]:
        """返回 (system_prompt, user_content)——生产同款 user JSON 载荷。"""
        system = EXTRACTOR_PROMPT_PATH.read_text(encoding="utf-8")
        user = {
            "user_message": payload.get("user_message", ""),
            "assistant_message": payload.get("assistant_message", ""),
            "now_utc": f"{payload['now_utc']}Z" if payload.get("now_utc") else None,
        }
        import json as _json

        return system, _json.dumps({k: v for k, v in user.items() if v is not None}, ensure_ascii=False)

    @staticmethod
    def extract_candidates(parsed: Any, *, evidence_token: str = "eval-token", occurred_at: datetime | None = None) -> list[Any]:
        """生产同款：payload['candidates'][:2] → LlmExtractorService._build_candidate
        → RuleYAdapter.validate（真实函数复用，零重写）。"""
        from app.services.rule_y_adapter import RuleYAdapter

        occurred = occurred_at or datetime(2026, 9, 20, 10, 0, 0)
        if not isinstance(parsed, dict):
            return []
        raw_candidates = parsed.get("candidates") or []
        if not isinstance(raw_candidates, list):
            return []
        service = LlmExtractorService.__new__(LlmExtractorService)  # 不跑 __init__（避开 kill-switch IO）
        accepted: list[Any] = []
        for raw in raw_candidates[:2]:
            if not isinstance(raw, dict):
                continue
            candidate = service._build_candidate(
                raw=raw, evidence_token=evidence_token, occurred_at=occurred
            )
            validated = RuleYAdapter.validate(candidate)
            if validated is not None:
                accepted.append(validated)
        return accepted


ADAPTERS: dict[str, Any] = {
    "aurora.intervention": InterventionFace,
    "aurora.joint": JointFace,
    "action.allocation": AllocationFace,
    "memory.gate": GateFace,
    "memory.extract": ExtractFace,
}

#: 每 sub_suite 的生产温度镜像（chat_json 缺省 0.3；extractor 显式 0.0）。
FACE_TEMPERATURES: dict[str, float] = {
    "aurora.intervention": 0.3,
    "aurora.joint": 0.3,
    "action.allocation": 0.3,
    "memory.gate": 0.3,
    "memory.extract": 0.0,
}
