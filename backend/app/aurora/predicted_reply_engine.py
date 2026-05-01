"""Aurora PredictedReplyOption Engine.

Generates semantically meaningful quick-reply options for the user during Aurora
modeling interactions. These are NOT static chips — each option is generated from
the live Aurora state and carries a model_write_effect that updates user/goal/
situation models when selected.

Design rules:
- Every option group MUST include one `freeform_correction` option ("都不对，我解释一下").
- Options are generated per band_status + active tension combination.
- Confidence scores come from the Aurora tension priority and facet readiness.
- Options are typed A/B/C/D per the product taxonomy.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Literal

ReplyType = Literal["fact_confirm", "assumption_check", "strategy_choice", "relational_signal", "freeform"]

_FREEFORM_LABEL = "都不对，我解释一下"
_FREEFORM_ID = "freeform_correction"


@dataclass
class ModelWriteEffect:
    """Describes which user/goal model fields get updated when this option is selected."""
    target: Literal["user_model", "goal_model", "situation_model", "self_model", "none"]
    field_key: str
    field_value: Any
    operation: Literal["set", "increment", "flag", "confirm", "invalidate"] = "set"
    requires_persistence: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "field_key": self.field_key,
            "field_value": self.field_value,
            "operation": self.operation,
            "requires_persistence": self.requires_persistence,
        }


@dataclass
class PredictedReplyOption:
    """A single predicted reply option with semantic meaning and model effects."""
    id: str
    label: str
    semantic_value: str
    reply_type: ReplyType
    confidence: float  # [0.0, 1.0]
    model_write_effect: ModelWriteEffect | None
    is_disconfirming: bool = False
    is_freeform: bool = False
    context_source: str = ""
    telemetry_id: str = ""

    def __post_init__(self) -> None:
        self.confidence = max(0.0, min(1.0, self.confidence))
        if not self.telemetry_id:
            raw = f"{self.id}:{self.semantic_value}:{self.context_source}"
            self.telemetry_id = hashlib.sha1(raw.encode()).hexdigest()[:12]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "semantic_value": self.semantic_value,
            "reply_type": self.reply_type,
            "confidence": round(self.confidence, 4),
            "model_write_effect": self.model_write_effect.to_dict() if self.model_write_effect else None,
            "is_disconfirming": self.is_disconfirming,
            "is_freeform": self.is_freeform,
            "context_source": self.context_source,
            "telemetry_id": self.telemetry_id,
        }


@dataclass
class PredictedReplyGroup:
    """A set of predicted options for a specific modeling question."""
    group_id: str
    question: str
    question_type: ReplyType
    options: list[PredictedReplyOption] = field(default_factory=list)
    context_note: str = ""

    def sorted_options(self) -> list[PredictedReplyOption]:
        """Returns options sorted by confidence descending, freeform always last."""
        primary = [o for o in self.options if not o.is_freeform]
        freeform = [o for o in self.options if o.is_freeform]
        return sorted(primary, key=lambda o: o.confidence, reverse=True) + freeform

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "question": self.question,
            "question_type": self.question_type,
            "context_note": self.context_note,
            "options": [o.to_dict() for o in self.sorted_options()],
        }


def _freeform_option(context_source: str = "") -> PredictedReplyOption:
    """Standard freeform correction option — mandatory in every group."""
    return PredictedReplyOption(
        id=_FREEFORM_ID,
        label=_FREEFORM_LABEL,
        semantic_value="freeform_correction",
        reply_type="freeform",
        confidence=0.0,
        model_write_effect=None,
        is_disconfirming=True,
        is_freeform=True,
        context_source=context_source,
    )


class PredictedReplyOptionEngine:
    """Generates PredictedReplyOption groups from Aurora control surface state.

    Inputs:
      - band_status: the current 6-state Aurora band
      - facets: list of facet dicts from AuroraControlSurfaceService.build_snapshot()
      - informational_tensions: list from AuroraState (if available)
      - energy_level: current L0-L3 level
      - wake_eligibility: dict from AuroraWakeEligibility
      - user_model_meta: optional dict with available_time, goal_type, task_density, etc.

    Output:
      List of PredictedReplyGroup (0-3 groups depending on state)
    """

    _MAX_GROUPS = 3

    def generate(
        self,
        *,
        band_status: str,
        facets: list[dict[str, Any]],
        informational_tensions: list[dict[str, Any]] | None = None,
        energy_level: str = "L1",
        wake_eligibility: dict[str, Any] | None = None,
        user_model_meta: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Return serialized PredictedReplyGroup list."""
        groups = self._generate_groups(
            band_status=band_status,
            facets=facets,
            tensions=informational_tensions or [],
            energy_level=energy_level,
            wake_eligibility=wake_eligibility or {},
            meta=user_model_meta or {},
        )
        return [g.to_dict() for g in groups[: self._MAX_GROUPS]]

    # ── Core dispatch ──────────────────────────────────────────────

    def _generate_groups(
        self,
        *,
        band_status: str,
        facets: list[dict[str, Any]],
        tensions: list[dict[str, Any]],
        energy_level: str,
        wake_eligibility: dict[str, Any],
        meta: dict[str, Any],
    ) -> list[PredictedReplyGroup]:
        handlers = {
            "needs_confirm": self._groups_for_needs_confirm,
            "risk_found": self._groups_for_risk_found,
            "calibration_available": self._groups_for_calibration_available,
            "cooling_down": self._groups_for_cooling_down,
            "calibrated": self._groups_for_calibrated,
            "sensing": self._groups_for_sensing,
        }
        handler = handlers.get(band_status, self._groups_for_sensing)
        return handler(facets=facets, tensions=tensions, wake_eligibility=wake_eligibility, meta=meta)

    # ── State handlers ─────────────────────────────────────────────

    def _groups_for_needs_confirm(
        self,
        *,
        facets: list[dict[str, Any]],
        tensions: list[dict[str, Any]],
        wake_eligibility: dict[str, Any],
        meta: dict[str, Any],
    ) -> list[PredictedReplyGroup]:
        groups: list[PredictedReplyGroup] = []

        # Primary: confirm the top tension or missing information
        top_tension = self._top_tension(tensions)
        if top_tension:
            groups.append(self._tension_confirm_group(top_tension, meta))

        # Secondary: time availability check (most common missing field)
        if not meta.get("available_time_confirmed"):
            groups.append(self._available_time_group(meta))

        # Tertiary: goal type check
        if not meta.get("goal_type_confirmed"):
            groups.append(self._goal_type_group(meta))

        return groups[:self._MAX_GROUPS]

    def _groups_for_risk_found(
        self,
        *,
        facets: list[dict[str, Any]],
        tensions: list[dict[str, Any]],
        wake_eligibility: dict[str, Any],
        meta: dict[str, Any],
    ) -> list[PredictedReplyGroup]:
        groups: list[PredictedReplyGroup] = []

        # Risk acknowledgment
        top_tension = self._top_tension(tensions)
        if top_tension:
            groups.append(self._risk_acknowledge_group(top_tension, meta))

        # Strategy response
        groups.append(self._strategy_response_group(meta))

        return groups[:self._MAX_GROUPS]

    def _groups_for_calibration_available(
        self,
        *,
        facets: list[dict[str, Any]],
        tensions: list[dict[str, Any]],
        wake_eligibility: dict[str, Any],
        meta: dict[str, Any],
    ) -> list[PredictedReplyGroup]:
        quota = wake_eligibility.get("user_quota_remaining", 0)
        context = f"calibration_available|quota={quota}"
        group = PredictedReplyGroup(
            group_id="calibration_intent",
            question="想进行 Aurora 深度校准吗？",
            question_type="assumption_check",
            context_note=f"今日还可进行 {quota} 次深度校准",
        )
        group.options = [
            PredictedReplyOption(
                id="wake_full_aurora",
                label="进入深度校准",
                semantic_value="wake_full_aurora",
                reply_type="assumption_check",
                confidence=0.55,
                model_write_effect=ModelWriteEffect(
                    target="user_model",
                    field_key="aurora_wake_intent",
                    field_value=True,
                    operation="flag",
                ),
                context_source=context,
            ),
            PredictedReplyOption(
                id="quick_check_only",
                label="只做快速检查",
                semantic_value="quick_calibration",
                reply_type="assumption_check",
                confidence=0.35,
                model_write_effect=ModelWriteEffect(
                    target="user_model",
                    field_key="aurora_wake_intent",
                    field_value="quick",
                    operation="set",
                ),
                context_source=context,
            ),
            PredictedReplyOption(
                id="not_now",
                label="现在不需要",
                semantic_value="calibration_dismissed",
                reply_type="assumption_check",
                confidence=0.1,
                model_write_effect=ModelWriteEffect(
                    target="user_model",
                    field_key="aurora_wake_intent",
                    field_value=False,
                    operation="flag",
                ),
                is_disconfirming=True,
                context_source=context,
            ),
            _freeform_option(context),
        ]
        return [group]

    def _groups_for_cooling_down(
        self,
        *,
        facets: list[dict[str, Any]],
        tensions: list[dict[str, Any]],
        wake_eligibility: dict[str, Any],
        meta: dict[str, Any],
    ) -> list[PredictedReplyGroup]:
        remaining = wake_eligibility.get("cooldown_remaining_min", 0)
        context = f"cooling_down|remaining={remaining}min"
        group = PredictedReplyGroup(
            group_id="post_calibration_follow_up",
            question="刚完成深度校准，有什么需要跟进吗？",
            question_type="fact_confirm",
            context_note="Aurora 校准结果已生效",
        )
        group.options = [
            PredictedReplyOption(
                id="view_calibration_result",
                label="查看刚才更新了什么",
                semantic_value="show_calibration_result",
                reply_type="fact_confirm",
                confidence=0.6,
                model_write_effect=None,
                context_source=context,
            ),
            PredictedReplyOption(
                id="quick_check_after_cooldown",
                label="快速检查当前任务",
                semantic_value="quick_task_check",
                reply_type="fact_confirm",
                confidence=0.3,
                model_write_effect=None,
                context_source=context,
            ),
            _freeform_option(context),
        ]
        return [group]

    def _groups_for_calibrated(
        self,
        *,
        facets: list[dict[str, Any]],
        tensions: list[dict[str, Any]],
        wake_eligibility: dict[str, Any],
        meta: dict[str, Any],
    ) -> list[PredictedReplyGroup]:
        groups: list[PredictedReplyGroup] = []
        # When calibrated, offer light feedback on current strategy
        groups.append(self._strategy_feedback_group(meta))
        return groups[:1]

    def _groups_for_sensing(
        self,
        *,
        facets: list[dict[str, Any]],
        tensions: list[dict[str, Any]],
        wake_eligibility: dict[str, Any],
        meta: dict[str, Any],
    ) -> list[PredictedReplyGroup]:
        # L0/L1 sensing — minimal, just orientation
        return []

    # ── Group builders ─────────────────────────────────────────────

    def _tension_confirm_group(
        self,
        tension: dict[str, Any],
        meta: dict[str, Any],
    ) -> PredictedReplyGroup:
        domain = tension.get("domain", "")
        description = tension.get("description", "需要确认一个判断")
        priority = float(tension.get("priority", 0.5))
        context = f"tension|domain={domain}"

        group = PredictedReplyGroup(
            group_id=f"tension_confirm_{domain}",
            question=description,
            question_type="assumption_check",
            context_note=f"Aurora 需要确认这个判断",
        )
        options = self._domain_options(domain, priority, context, meta)
        options.append(_freeform_option(context))
        group.options = options
        return group

    def _risk_acknowledge_group(
        self,
        tension: dict[str, Any],
        meta: dict[str, Any],
    ) -> PredictedReplyGroup:
        domain = tension.get("domain", "")
        context = f"risk|domain={domain}"
        group = PredictedReplyGroup(
            group_id=f"risk_ack_{domain}",
            question="Aurora 发现了一个策略风险，你怎么看？",
            question_type="assumption_check",
        )
        group.options = [
            PredictedReplyOption(
                id="risk_confirmed",
                label="是的，确实有问题",
                semantic_value="risk_confirmed",
                reply_type="assumption_check",
                confidence=0.45,
                model_write_effect=ModelWriteEffect(
                    target="situation_model",
                    field_key=f"risk_acknowledged_{domain}",
                    field_value=True,
                    operation="flag",
                ),
                context_source=context,
            ),
            PredictedReplyOption(
                id="risk_temporary",
                label="只是今天特殊情况",
                semantic_value="risk_temporary",
                reply_type="assumption_check",
                confidence=0.3,
                model_write_effect=ModelWriteEffect(
                    target="situation_model",
                    field_key=f"risk_temporary_{domain}",
                    field_value=True,
                    operation="flag",
                ),
                is_disconfirming=True,
                context_source=context,
            ),
            PredictedReplyOption(
                id="risk_different_cause",
                label="不是这个问题",
                semantic_value="risk_wrong_diagnosis",
                reply_type="assumption_check",
                confidence=0.2,
                model_write_effect=ModelWriteEffect(
                    target="situation_model",
                    field_key=f"risk_misdiagnosed_{domain}",
                    field_value=True,
                    operation="flag",
                ),
                is_disconfirming=True,
                context_source=context,
            ),
            _freeform_option(context),
        ]
        return group

    def _available_time_group(self, meta: dict[str, Any]) -> PredictedReplyGroup:
        context = "missing|available_time"
        group = PredictedReplyGroup(
            group_id="available_time_confirm",
            question="今晚你真实可用的时间更接近哪个？",
            question_type="fact_confirm",
        )
        group.options = [
            PredictedReplyOption(
                id="time_30min",
                label="30 分钟",
                semantic_value="available_time_30",
                reply_type="fact_confirm",
                confidence=0.25,
                model_write_effect=ModelWriteEffect(
                    target="user_model",
                    field_key="available_time_today_min",
                    field_value=30,
                    operation="set",
                ),
                context_source=context,
            ),
            PredictedReplyOption(
                id="time_45min",
                label="45 分钟",
                semantic_value="available_time_45",
                reply_type="fact_confirm",
                confidence=0.42,
                model_write_effect=ModelWriteEffect(
                    target="user_model",
                    field_key="available_time_today_min",
                    field_value=45,
                    operation="set",
                ),
                context_source=context,
            ),
            PredictedReplyOption(
                id="time_60min",
                label="60 分钟",
                semantic_value="available_time_60",
                reply_type="fact_confirm",
                confidence=0.33,
                model_write_effect=ModelWriteEffect(
                    target="user_model",
                    field_key="available_time_today_min",
                    field_value=60,
                    operation="set",
                ),
                context_source=context,
            ),
            PredictedReplyOption(
                id="time_90min",
                label="90 分钟",
                semantic_value="available_time_90",
                reply_type="fact_confirm",
                confidence=0.15,
                model_write_effect=ModelWriteEffect(
                    target="user_model",
                    field_key="available_time_today_min",
                    field_value=90,
                    operation="set",
                ),
                context_source=context,
            ),
            _freeform_option(context),
        ]
        return group

    def _goal_type_group(self, meta: dict[str, Any]) -> PredictedReplyGroup:
        context = "missing|goal_type"
        group = PredictedReplyGroup(
            group_id="goal_type_confirm",
            question="你的目标现在是先过线，还是冲高分？",
            question_type="assumption_check",
        )
        group.options = [
            PredictedReplyOption(
                id="goal_pass_first",
                label="先过线",
                semantic_value="goal_pass_threshold",
                reply_type="assumption_check",
                confidence=0.55,
                model_write_effect=ModelWriteEffect(
                    target="goal_model",
                    field_key="primary_goal_type",
                    field_value="pass_threshold",
                    operation="set",
                ),
                context_source=context,
            ),
            PredictedReplyOption(
                id="goal_high_score",
                label="冲高分",
                semantic_value="goal_maximize_score",
                reply_type="assumption_check",
                confidence=0.35,
                model_write_effect=ModelWriteEffect(
                    target="goal_model",
                    field_key="primary_goal_type",
                    field_value="maximize_score",
                    operation="set",
                ),
                context_source=context,
            ),
            PredictedReplyOption(
                id="goal_uncertain",
                label="我不确定",
                semantic_value="goal_uncertain",
                reply_type="assumption_check",
                confidence=0.1,
                model_write_effect=ModelWriteEffect(
                    target="goal_model",
                    field_key="primary_goal_type",
                    field_value="uncertain",
                    operation="set",
                ),
                is_disconfirming=True,
                context_source=context,
            ),
            _freeform_option(context),
        ]
        return group

    def _strategy_response_group(self, meta: dict[str, Any]) -> PredictedReplyGroup:
        context = "risk|strategy_response"
        group = PredictedReplyGroup(
            group_id="strategy_response",
            question="接下来怎么处理比较好？",
            question_type="strategy_choice",
        )
        group.options = [
            PredictedReplyOption(
                id="shrink_task",
                label="缩小今晚任务",
                semantic_value="reduce_task_scope",
                reply_type="strategy_choice",
                confidence=0.45,
                model_write_effect=ModelWriteEffect(
                    target="situation_model",
                    field_key="strategy_adjustment",
                    field_value="reduce_scope",
                    operation="set",
                ),
                context_source=context,
            ),
            PredictedReplyOption(
                id="change_approach",
                label="换一种讲法",
                semantic_value="change_explanation_style",
                reply_type="strategy_choice",
                confidence=0.3,
                model_write_effect=ModelWriteEffect(
                    target="situation_model",
                    field_key="strategy_adjustment",
                    field_value="change_approach",
                    operation="set",
                ),
                context_source=context,
            ),
            PredictedReplyOption(
                id="diagnose_first",
                label="先出题诊断",
                semantic_value="run_diagnostic",
                reply_type="strategy_choice",
                confidence=0.25,
                model_write_effect=ModelWriteEffect(
                    target="situation_model",
                    field_key="strategy_adjustment",
                    field_value="run_diagnostic",
                    operation="set",
                ),
                context_source=context,
            ),
            _freeform_option(context),
        ]
        return group

    def _strategy_feedback_group(self, meta: dict[str, Any]) -> PredictedReplyGroup:
        context = "calibrated|strategy_feedback"
        group = PredictedReplyGroup(
            group_id="strategy_feedback",
            question="当前策略感觉怎么样？",
            question_type="relational_signal",
        )
        group.options = [
            PredictedReplyOption(
                id="strategy_good",
                label="刚好",
                semantic_value="strategy_affirmed",
                reply_type="relational_signal",
                confidence=0.5,
                model_write_effect=ModelWriteEffect(
                    target="self_model",
                    field_key="strategy_user_rating",
                    field_value="affirmed",
                    operation="set",
                ),
                context_source=context,
            ),
            PredictedReplyOption(
                id="strategy_too_fast",
                label="节奏太快了",
                semantic_value="strategy_too_aggressive",
                reply_type="relational_signal",
                confidence=0.3,
                model_write_effect=ModelWriteEffect(
                    target="self_model",
                    field_key="strategy_user_rating",
                    field_value="too_aggressive",
                    operation="set",
                ),
                is_disconfirming=True,
                context_source=context,
            ),
            PredictedReplyOption(
                id="strategy_too_slow",
                label="可以再快一些",
                semantic_value="strategy_too_conservative",
                reply_type="relational_signal",
                confidence=0.2,
                model_write_effect=ModelWriteEffect(
                    target="self_model",
                    field_key="strategy_user_rating",
                    field_value="too_conservative",
                    operation="set",
                ),
                context_source=context,
            ),
            _freeform_option(context),
        ]
        return group

    # ── Domain-specific options ────────────────────────────────────

    def _domain_options(
        self,
        domain: str,
        priority: float,
        context: str,
        meta: dict[str, Any],
    ) -> list[PredictedReplyOption]:
        """Generate domain-aware confirm/disconfirm options for a tension."""
        if domain == "time":
            return self._time_domain_options(priority, context)
        if domain == "scope":
            return self._scope_domain_options(priority, context)
        if domain == "motivation":
            return self._motivation_domain_options(priority, context)
        if domain in ("goal", "baseline"):
            return self._goal_domain_options(domain, priority, context)
        return self._generic_tension_options(priority, context)

    def _time_domain_options(self, priority: float, context: str) -> list[PredictedReplyOption]:
        return [
            PredictedReplyOption(
                id="time_overrun_confirmed",
                label="确实超时了",
                semantic_value="time_overrun_confirmed",
                reply_type="assumption_check",
                confidence=priority * 0.8,
                model_write_effect=ModelWriteEffect(
                    target="user_model",
                    field_key="task_time_estimation_bias",
                    field_value="underestimates",
                    operation="set",
                ),
                context_source=context,
            ),
            PredictedReplyOption(
                id="time_overrun_not_task",
                label="是题太难，不是时间问题",
                semantic_value="difficulty_mismatch",
                reply_type="assumption_check",
                confidence=priority * 0.5,
                model_write_effect=ModelWriteEffect(
                    target="situation_model",
                    field_key="overrun_cause",
                    field_value="difficulty",
                    operation="set",
                ),
                is_disconfirming=True,
                context_source=context,
            ),
            PredictedReplyOption(
                id="time_overrun_today_only",
                label="只是今天偶尔这样",
                semantic_value="time_overrun_exceptional",
                reply_type="assumption_check",
                confidence=priority * 0.3,
                model_write_effect=ModelWriteEffect(
                    target="situation_model",
                    field_key="overrun_cause",
                    field_value="exceptional",
                    operation="set",
                ),
                is_disconfirming=True,
                context_source=context,
            ),
        ]

    def _scope_domain_options(self, priority: float, context: str) -> list[PredictedReplyOption]:
        return [
            PredictedReplyOption(
                id="scope_too_large",
                label="任务量确实太大",
                semantic_value="task_scope_too_large",
                reply_type="assumption_check",
                confidence=priority * 0.7,
                model_write_effect=ModelWriteEffect(
                    target="situation_model",
                    field_key="scope_adjustment_needed",
                    field_value=True,
                    operation="flag",
                ),
                context_source=context,
            ),
            PredictedReplyOption(
                id="scope_fine_motivation",
                label="任务不大，是状态不好",
                semantic_value="scope_ok_low_motivation",
                reply_type="assumption_check",
                confidence=priority * 0.4,
                model_write_effect=ModelWriteEffect(
                    target="user_model",
                    field_key="current_motivation_cause",
                    field_value="low_state",
                    operation="set",
                ),
                is_disconfirming=True,
                context_source=context,
            ),
        ]

    def _motivation_domain_options(self, priority: float, context: str) -> list[PredictedReplyOption]:
        return [
            PredictedReplyOption(
                id="motivation_avoidance",
                label="有点回避，不是不想学",
                semantic_value="avoidance_not_disengaged",
                reply_type="assumption_check",
                confidence=priority * 0.6,
                model_write_effect=ModelWriteEffect(
                    target="user_model",
                    field_key="motivation_pattern",
                    field_value="avoidance",
                    operation="set",
                ),
                context_source=context,
            ),
            PredictedReplyOption(
                id="motivation_genuinely_tired",
                label="确实很累",
                semantic_value="genuinely_fatigued",
                reply_type="assumption_check",
                confidence=priority * 0.5,
                model_write_effect=ModelWriteEffect(
                    target="user_model",
                    field_key="motivation_pattern",
                    field_value="fatigued",
                    operation="set",
                ),
                is_disconfirming=True,
                context_source=context,
            ),
        ]

    def _goal_domain_options(self, domain: str, priority: float, context: str) -> list[PredictedReplyOption]:
        return [
            PredictedReplyOption(
                id="goal_still_pass",
                label="目标还是先过",
                semantic_value="goal_unchanged_pass",
                reply_type="assumption_check",
                confidence=priority * 0.6,
                model_write_effect=ModelWriteEffect(
                    target="goal_model",
                    field_key="goal_still_valid",
                    field_value=True,
                    operation="confirm",
                ),
                context_source=context,
            ),
            PredictedReplyOption(
                id="goal_changed",
                label="目标变了，想说一下",
                semantic_value="goal_has_changed",
                reply_type="assumption_check",
                confidence=priority * 0.3,
                model_write_effect=ModelWriteEffect(
                    target="goal_model",
                    field_key="goal_still_valid",
                    field_value=False,
                    operation="invalidate",
                ),
                is_disconfirming=True,
                context_source=context,
            ),
        ]

    def _generic_tension_options(self, priority: float, context: str) -> list[PredictedReplyOption]:
        return [
            PredictedReplyOption(
                id="generic_confirm",
                label="这个判断对",
                semantic_value="judgment_confirmed",
                reply_type="assumption_check",
                confidence=priority * 0.6,
                model_write_effect=ModelWriteEffect(
                    target="user_model",
                    field_key="last_judgment_confirmed",
                    field_value=True,
                    operation="flag",
                ),
                context_source=context,
            ),
            PredictedReplyOption(
                id="generic_deny",
                label="这个判断不对",
                semantic_value="judgment_denied",
                reply_type="assumption_check",
                confidence=priority * 0.3,
                model_write_effect=ModelWriteEffect(
                    target="user_model",
                    field_key="last_judgment_confirmed",
                    field_value=False,
                    operation="flag",
                ),
                is_disconfirming=True,
                context_source=context,
            ),
        ]

    # ── Helpers ────────────────────────────────────────────────────

    def _top_tension(self, tensions: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not tensions:
            return None
        open_tensions = [t for t in tensions if t.get("status", "open") == "open"]
        if not open_tensions:
            return None
        return max(open_tensions, key=lambda t: float(t.get("priority", 0.0)))
