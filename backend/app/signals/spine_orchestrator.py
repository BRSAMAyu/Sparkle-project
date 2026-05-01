"""
Core: execution
Phase: sense→clarify→plan→execute→reflect
Stage: Signal-to-Action Spine M1 — 全链路编排

Spine Orchestrator — 编排完整的 Signal→State→Decision→Directive→Audit→Receipt→Trace 链路。
"""

from __future__ import annotations

import json
from datetime import UTC
from typing import Any

from loguru import logger

from app.aurora.runtime_v1.aurora_spine_confluence import (
    AuroraInputAssembler,
    AuroraOutputArbitrator,
    AuroraSelfCorrector,
    AuroraSelfModelAccessor,
)
from app.aurora.runtime_v1.correction_feedback import CorrectionFeedbackProcessor
from app.aurora.runtime_v1.energy_controller import EnergyLevelDecider
from app.aurora.runtime_v1.l3_full_core import L3FullCoreEngine
from app.core.cost_controller import is_aurora_within_budget, record_aurora_cost
from app.core.error_taxonomy import ErrorCategory, ErrorSeverity, classify_error
from app.signals.achievement_reinforcement import AchievementReinforcementConsumer
from app.signals.aurora_core_session import AuroraCoreSessionService, PolicyChange, SessionClosure, StatePatch
from app.signals.aurora_wake import AuroraWakeJudge
from app.signals.causal_trace_store import CausalTraceStore
from app.signals.card_store import CardStore
from app.signals.directive_store import DirectiveStore
from app.signals.community_loops import CommunityLoopManager
from app.signals.community_signal import CommunitySignalDetector
from app.signals.core_session import CoreSession, CoreSessionManager
from app.signals.directive_applier import DirectiveApplier, DirectiveAuditor
from app.signals.directive_quota import DirectiveQuotaService
from app.signals.exam_rescue_detector import ExamRescueDetector
from app.signals.exam_sprint_policy import ExamSprintPolicyService
from app.signals.goal_type_adapter import GoalTypeAdapter
from app.signals.goal_world_graph import GoalWorldGraphService
from app.signals.growth_chronicle import GrowthChronicleService
from app.signals.intervention_episode import (
    ContextSignature,
    InterventionEpisode,
    InterventionEpisodeLedger,
)
from app.signals.learning_base import LearningBase
from app.signals.material_signal import MaterialSignalDetector
from app.signals.mistake_signal import MistakeSignalDetector
from app.signals.multi_goal_arbitration import MultiGoalArbitrator
from app.signals.outcome_recorder import OutcomeRecorder
from app.signals.outcome_tracker import OutcomeTracker
from app.signals.partner_commitment_loop import PartnerCommitmentLoop
from app.signals.policy_analytics import PolicyAnalytics
from app.signals.policy_engine import PolicyEngine
from app.signals.policy_experiments import PolicyExperimentManager
from app.signals.predicted_reply_options import SpineReplyOptionEngine
from app.signals.recall_notification import RecallMessage, RecallNotificationBuilder
from app.signals.recall_opportunity import RecallOpportunityDetector
from app.signals.relationship_model import RelationshipModelService
from app.signals.self_model import SparkleSelfModelService
from app.signals.signal_ranker import SignalRanker
from app.signals.skill_extraction import SkillExtractionService
from app.signals.skill_lifecycle import SkillLifecycleManager
from app.signals.source_tray_integration import SourceEffectivenessTracker
from app.signals.spine_metrics import SpineMetricsCollector
from app.signals.stale_state_guard import StaleStateGuard
from app.signals.state_packet_builder import ActionableStatePacketBuilder
from app.signals.state_register import StateRegister
from app.signals.task_timeout_detector import TaskTimeoutDetector
from app.signals.timeline_card_renderer import TimelineCardRenderer
from app.signals.types import (
    ActionableSignal,
    ActionableStatePacket,
    CausalTrace,
    CommunityDirective,
    DirectiveApplicationAudit,
    ExecutionDirective,
    ModelWriteDirective,
    NotificationDirective,
    PlanDirective,
    PolicyDecision,
    ResponseDirective,
    RetrievalDirective,
    SkillDirective,
    SkillEntry,
    UserVisibleReceipt,
    UXDirective,
    _uid,
)


def _utcnow_iso() -> str:
    from datetime import datetime
    return datetime.now(UTC).isoformat()


class SpineOrchestrator:
    """
    Signal-to-Action Spine 主编排器。

    职责：
    1. 消费 task.completed 事件
    2. 运行固定规则检测 → ActionableSignal
    3. 运行 PolicyEngine → PolicyDecision + ExecutionDirective
    4. 存储 directive 供 planning_workflow 消费
    5. 生成 UserVisibleReceipt
    6. 记录完整 CausalTrace
    """

    def __init__(self, redis_client: Any):
        self.redis = redis_client
        self.trace_store = CausalTraceStore(redis_client)
        self.directive_store = DirectiveStore(redis_client, self.trace_store)
        self.timeout_detector = TaskTimeoutDetector(redis_client)
        self.mistake_detector = MistakeSignalDetector(redis_client)
        self.achievement_consumer = AchievementReinforcementConsumer()
        self.recall_detector = RecallOpportunityDetector()
        self.recall_notification_builder = RecallNotificationBuilder()
        self.exam_rescue = ExamRescueDetector()
        self.stale_guard = StaleStateGuard()
        self.state_packet_builder = ActionableStatePacketBuilder()
        self.self_model = SparkleSelfModelService(redis_client)
        self.community_detector = CommunitySignalDetector()
        self.community_loops = CommunityLoopManager()
        self.card_store = CardStore(redis_client, self.community_loops)
        self.reply_engine = SpineReplyOptionEngine()
        self.wake_judge = AuroraWakeJudge()
        self.signal_ranker = SignalRanker()
        self.state_register = StateRegister(redis_client)
        self.outcome_recorder = OutcomeRecorder(redis_client)
        self.outcome_tracker = OutcomeTracker(redis_client)
        self.metrics = SpineMetricsCollector(redis_client)
        self.policy_engine = PolicyEngine(reply_engine=self.reply_engine)
        self.exam_sprint_policy = ExamSprintPolicyService()
        self.core_session_manager = CoreSessionManager(redis_client)
        self.skill_lifecycle_manager = SkillLifecycleManager(redis_client)
        # P0-2: Previously orphaned modules — now wired into the pipeline
        self.policy_analytics = PolicyAnalytics(redis_client)
        self.policy_experiments = PolicyExperimentManager(redis_client)
        self.learning_base = LearningBase()
        self.growth_chronicle = GrowthChronicleService(redis_client)
        self.relationship_model = RelationshipModelService(redis_client)
        self.partner_commitments = PartnerCommitmentLoop(redis_client)
        self.directive_quota = DirectiveQuotaService(redis_client)
        self.aurora_core = AuroraCoreSessionService(redis_client)
        self.l3_engine = L3FullCoreEngine(redis_client)
        self.energy_decider = EnergyLevelDecider()

        self.aurora_input_assembler = AuroraInputAssembler(redis_client)
        self.aurora_arbitrator = AuroraOutputArbitrator()
        self.aurora_self_corrector = AuroraSelfCorrector(redis_client)
        self.aurora_self_model_accessor = AuroraSelfModelAccessor(redis_client)
        self.correction_feedback = CorrectionFeedbackProcessor(redis_client)
        self.skill_extraction = SkillExtractionService()
        self.goal_type_adapter = GoalTypeAdapter()
        self.material_signal_detector = MaterialSignalDetector(redis_client)
        self.timeline_renderer = TimelineCardRenderer()
        self.source_effectiveness = SourceEffectivenessTracker(redis_client)
        self.goal_graph = GoalWorldGraphService(redis_client)
        self.goal_arbitrator = MultiGoalArbitrator(redis_client)

        # EA-1~EA-4: Governance modules — wired into production pipeline
        from app.core.research_isolation import ResearchIsolationGuard
        from app.signals.fabrication_guard import check_response_for_fabrication
        from app.signals.high_impact_confirmation import HighImpactConfirmationFramework
        from app.signals.safety_degradation import SafetyDegradationManager
        self._fabrication_scanner = check_response_for_fabrication
        self._safety_degradation = SafetyDegradationManager(redis_client)
        self._high_impact_confirmation = HighImpactConfirmationFramework()
        self._research_isolation = ResearchIsolationGuard()

    async def on_task_completed(
        self,
        *,
        user_id: str,
        task_id: str,
        estimated_minutes: int,
        actual_minutes: int,
        plan_id: str | None = None,
    ) -> CausalTrace | None:
        """
        完整链路：task.completed → (可能) signal → policy → directive → trace。

        Delegates to _run_signal_pipeline for lock management and pipeline execution.
        Only handles signal detection and task-completed-specific post-processing.

        Returns:
            CausalTrace if signal was generated and policy applied, None otherwise.
        """
        # Step 1: Signal detection (no lock needed — lock is in _run_signal_pipeline)
        signal = await self.timeout_detector.on_task_completed(
            user_id=user_id,
            task_id=task_id,
            estimated_minutes=estimated_minutes,
            actual_minutes=actual_minutes,
            plan_id=plan_id,
        )

        if signal is None:
            # No signal — record lightweight trace for the event
            trace = await self.trace_store.create_trace()
            trace.raw_event_ids.append(task_id)
            await self.trace_store.link_to_user(user_id, trace.trace_id)
            trace.outcome_to_measure = ["task_completed_normally"]
            await self.trace_store._save_trace(trace)
            try:
                await self.relationship_model.update_from_behavioral_signal(
                    user_id, "task_completed", {"task_id": task_id},
                )
            except Exception:
                logger.warning("on_task_completed: relationship_model failed", exc_info=True)
            return trace

        # Step 2: Delegate pipeline to _run_signal_pipeline (handles lock)
        trace = await self._run_signal_pipeline(
            user_id=user_id,
            signal=signal,
            event_ids=[task_id],
        )
        if trace is None:
            return None

        # Step 3: Task-completed-specific post-processing
        # Re-acquire lock to prevent concurrent on_task_completed from
        # running post-processing while this one is still modifying trace state.
        _post_lock_key = f"spine:task_completed_lock:{user_id}"
        try:
            await self.redis.set(_post_lock_key, "1", nx=True, ex=15)
        except Exception:
            pass

        # Step 3a: Record Aurora energy level decision in trace (T3.1.6)
        try:
            active_states_dicts = await self._get_active_states_dicts(user_id)
            from app.aurora.runtime_v1.state import AuroraEnergyStore
            energy_store = AuroraEnergyStore(self.redis)
            energy = await energy_store.load_energy(user_id)
            energy_decision = self.energy_decider.decide(
                user_id=user_id,
                energy=energy,
                active_states=active_states_dicts,
            )
            trace.aurora_energy_level = energy_decision.current_level
            trace.aurora_upgrade_reason = energy_decision.upgrade_reason
        except Exception:
            logger.warning("on_task_completed: energy decision failed for user={}", user_id, exc_info=True)

        # Step 3b: Register expected outcome for verification loop
        try:
            recent_effects = await self.outcome_recorder.get_recent_policy_effects(user_id, limit=10)
            primary_strategy = getattr(trace, 'primary_strategy', 'task_completed')
            expected_outcome_type = "task_started_and_completed" if primary_strategy != "timeout_warning" else "behavioral_change"
            await self.outcome_tracker.register_expected(
                user_id=user_id,
                directive_type=primary_strategy,
                trace=trace,
                expected_outcome=expected_outcome_type,
                verification_window_hours=48,
                context={
                    "signal_claim": signal.claim,
                    "signal_state_key": signal.state_key,
                    "plan_id": plan_id,
                    "task_id": task_id,
                },
            )
        except Exception:
            logger.warning("on_task_completed: outcome_tracker.register_expected failed", exc_info=True)

        # Step 3c: Check Aurora wake eligibility for high-risk signals
        try:
            recent_effects = await self.outcome_recorder.get_recent_policy_effects(user_id, limit=10)
            risk_level = getattr(trace, 'risk_level', None)
            if risk_level in ("critical", "high"):
                neg_outcomes = sum(
                    1 for pe in recent_effects
                    if getattr(pe, "attribution", "") == "insufficient"
                ) if recent_effects else 0
                wake_result = self.check_aurora_wake(
                    user_id=user_id,
                    quota_remaining=3,
                    cooldown_status="available",
                    consecutive_negative_outcomes=neg_outcomes,
                )
                if wake_result.can_wake:
                    import json
                    await self.redis.set(
                        f"spine:aurora_wake_pending:{user_id}",
                        json.dumps(wake_result.to_dict()),
                        ex=3600,
                    )
                    logger.info(
                        "Aurora wake recommended: user={} type={}",
                        user_id, wake_result.recommended_session_type,
                    )
        except Exception:
            logger.warning("on_task_completed: aurora wake check failed", exc_info=True)

        await self.trace_store._save_trace(trace)

        # Release task-completed lock
        try:
            await self.redis.delete(_post_lock_key)
        except Exception:
            pass

        return trace

    async def get_active_directive(self, user_id: str) -> ExecutionDirective | None:
        """供 planning_workflow 调用——获取当前用户的活跃 directive。"""
        return await self.trace_store.get_active_directive(user_id)

    async def get_status_band_summary(self, user_id: str) -> dict[str, Any]:
        """
        Demo Experience Point #10: Aurora 状态带 — 6-state band + Spine risk flags。

        读取 StateRegister 中活跃信号状态，生成结构化状态带摘要供 Flutter 展示。
        新增 T3.4.1: 统一返回 6-state 模型 (sensing/calibrated/risk_found/
        needs_confirm/calibration_available/cooling_down) + 纠正选项 + 冷却信息。

        Returns:
            {
              "strategy_risk": bool,     # knowledge_transfer:transfer_failure 活跃
              "material_aware": bool,    # source_material:material_received 活跃
              "execution_risk": bool,    # task_granularity_fit:too_large 活跃
              "stale_guard": bool,       # stale_state 活跃
              "has_active_directive": bool,
              "active_claims": list[str],
              "active_state_keys": list[str],
              "directive_summary": str | None,
              "band_severity": str,      # "none" | "info" | "warning" | "critical"
              # ── T3.4.1: 6-state band ──
              "band_status": str,        # sensing/calibrated/risk_found/needs_confirm/calibration_available/cooling_down
              "band_label": str,         # 中文标签
              "band_summary": str,       # 一段话描述当前状态
              "band_energy": str,        # L0/L1/L2/L3
              # ── T3.4.2: correction options ──
              "correction_options": list[dict],
              # ── T3.4.3: cooldown info ──
              "cooldown_remaining_seconds": int | None,
              "cooldown_can_override": bool,
            }
        """
        # Read all active signals from StateRegister
        active_entries = await self.state_register.get_active_states(user_id)

        strategy_risk = False
        material_aware = False
        execution_risk = False
        stale_guard = False
        active_claims: list[str] = []
        active_state_keys: list[str] = []

        for entry in active_entries:
            active_state_keys.append(entry.state_key)
            active_claims.append(entry.value)  # value = claim

            if entry.state_key == "knowledge_transfer" and entry.value == "transfer_failure":
                strategy_risk = True
            elif entry.state_key == "source_material" and entry.value in (
                "material_received", "material_underutilized"
            ):
                material_aware = True
            elif entry.state_key == "task_granularity_fit" and entry.value == "too_large":
                execution_risk = True
            elif entry.state_key == "stale_state":
                stale_guard = True

        # Read active directive
        directive = await self.get_active_directive(user_id)
        has_active_directive = directive is not None
        directive_summary: str | None = None
        if directive is not None:
            parts = []
            if directive.max_task_duration_min is not None:
                parts.append(f"max_duration={directive.max_task_duration_min}min")
            if directive.required_task_type is not None:
                parts.append(f"type={directive.required_task_type}")
            if directive.avoid_new_chapter:
                parts.append("avoid_new_chapter")
            directive_summary = ", ".join(parts) if parts else directive.user_visible_reason

        # Severity: none < info < warning < critical
        risk_flags = [strategy_risk, execution_risk, stale_guard]
        risk_count = sum(1 for f in risk_flags if f)
        if risk_count >= 2 or (strategy_risk and execution_risk):
            band_severity = "critical"
        elif risk_count == 1:
            band_severity = "warning"
        elif material_aware:
            band_severity = "info"
        else:
            band_severity = "none"

        # ── T3.4.1: 6-state band computation ──
        band_status, band_label, band_summary, band_energy, cooldown_remaining, cooldown_can_override = (
            await self._compute_6state_band(user_id, active_entries)
        )

        # ── T3.4.2: correction options ──
        correction_options = await self._build_correction_options(band_status, active_entries)

        return {
            "strategy_risk": strategy_risk,
            "material_aware": material_aware,
            "execution_risk": execution_risk,
            "stale_guard": stale_guard,
            "has_active_directive": has_active_directive,
            "active_claims": active_claims,
            "active_state_keys": active_state_keys,
            "directive_summary": directive_summary,
            "band_severity": band_severity,
            "band_status": band_status,
            "band_label": band_label,
            "band_summary": band_summary,
            "band_energy": band_energy,
            "correction_options": correction_options,
            "cooldown_remaining_seconds": cooldown_remaining,
            "cooldown_can_override": cooldown_can_override,
        }

    async def _compute_6state_band(
        self,
        user_id: str,
        active_entries: list[Any],
    ) -> tuple[str, str, str, str, int | None, bool]:
        """Compute the 6-state Aurora band from StateRegister + energy store.

        Uses lightweight StateRegister data to approximate parameters for
        AuroraControlSurfaceService._resolve_band_status().
        """
        try:
            from datetime import UTC, datetime

            from app.aurora.runtime_v1.state import AuroraEnergyState, AuroraEnergyStore
            from app.services.aurora_control_surface_service import AuroraControlSurfaceService

            energy_store = AuroraEnergyStore(self.redis, enabled=True)
            energy = await energy_store.load_energy(user_id)

            # Approximate parameters from active states
            high_conf = [e for e in active_entries if e.confidence >= 0.6]
            mid_conf = [e for e in active_entries if e.confidence >= 0.4]
            has_corrections = any(len(e.counter_evidence) > 0 for e in active_entries)

            aurora_active = len(active_entries) > 0
            ready_count = len(high_conf)
            total_count = max(4, len(active_entries))
            active_count = len(mid_conf)
            recalibrating = has_corrections

            # Compute 6-state band
            cs = AuroraControlSurfaceService(None, self.redis)
            band_status = cs._resolve_band_status(
                energy=energy,
                aurora_active=aurora_active,
                ready_count=ready_count,
                total_count=total_count,
                recalibrating=recalibrating,
                active_count=active_count,
            )

            # Labels and summaries
            labels: dict[str, str] = {
                "sensing": "轻量感知中",
                "calibrated": "已校准",
                "risk_found": "发现风险",
                "needs_confirm": "需要确认",
                "calibration_available": "深度校准可用",
                "cooling_down": "冷却中",
            }
            band_label = labels.get(band_status, labels["sensing"])
            band_summary = cs._band_status_summary(band_status, [])
            band_energy = energy.current_level if isinstance(energy, AuroraEnergyState) else "L0"

            # Cooldown info — override only allowed when quota remains (P2: prevent L3 cost bypass)
            cooldown_remaining: int | None = None
            cooldown_can_override = False
            if isinstance(energy, AuroraEnergyState) and energy.is_cooling_down:
                now = datetime.now(UTC).replace(tzinfo=None)
                if energy.cooldown_until:
                    remaining = (energy.cooldown_until - now).total_seconds()
                    cooldown_remaining = max(0, int(remaining))
                # Check L3 daily quota: override should not bypass cost limits.
                # L3 base quota is 3/day (from _COST_LIMITS). Sprint-mode quotas
                # are enforced at session start, not at UI-override time.
                cooldown_can_override = energy.l3_session_count_today < 3

            return band_status, band_label, band_summary, band_energy, cooldown_remaining, cooldown_can_override

        except Exception as _band_err:
            _ce = classify_error(_band_err, component="spine_6state_band", category=ErrorCategory.AURORA)
            logger.warning("SpineOrchestrator: _compute_6state_band failed for user={} [{}]", user_id, _ce.severity.value)
            return "sensing", "轻量感知中", "Aurora 正在轻量感知，参考当前上下文优化回复。", "L0", None, False

    async def _build_correction_options(
        self,
        band_status: str,
        active_entries: list[Any],
    ) -> list[dict[str, Any]]:
        """Build correction reply options for the current band status.

        Each option has: label, semantic_value, is_freeform, is_disconfirming.
        The final option is always the freeform "都不对，我解释一下" fallback.
        """
        options: list[dict[str, Any]] = []

        # Per-band disconfirming options
        band_options: dict[str, list[dict[str, Any]]] = {
            "risk_found": [
                {"label": "这个风险判断不对", "semantic_value": "risk_false_positive", "is_freeform": False, "is_disconfirming": True},
                {"label": "风险没那么严重", "semantic_value": "risk_overstated", "is_freeform": False, "is_disconfirming": True},
                {"label": "方向是对的，继续", "semantic_value": "risk_accepted", "is_freeform": False, "is_disconfirming": False},
            ],
            "needs_confirm": [
                {"label": "这个判断不对", "semantic_value": "judgment_incorrect", "is_freeform": False, "is_disconfirming": True},
                {"label": "对，就是这样", "semantic_value": "judgment_confirmed", "is_freeform": False, "is_disconfirming": False},
            ],
            "calibration_available": [
                {"label": "现在校准", "semantic_value": "calibrate_now", "is_freeform": False, "is_disconfirming": False},
                {"label": "暂时不需要", "semantic_value": "calibrate_later", "is_freeform": False, "is_disconfirming": False},
            ],
            "calibrated": [
                {"label": "策略没问题", "semantic_value": "strategy_confirmed", "is_freeform": False, "is_disconfirming": False},
                {"label": "需要调整方向", "semantic_value": "strategy_adjust_needed", "is_freeform": False, "is_disconfirming": True},
            ],
            "sensing": [
                {"label": "帮我深入分析", "semantic_value": "request_deep_analysis", "is_freeform": False, "is_disconfirming": False},
            ],
            "cooling_down": [
                {"label": "快速校准", "semantic_value": "quick_calibrate", "is_freeform": False, "is_disconfirming": False},
                {"label": "坚持冷却", "semantic_value": "accept_cooldown", "is_freeform": False, "is_disconfirming": False},
            ],
        }

        options = list(band_options.get(band_status, band_options["sensing"]))

        # Always include freeform fallback
        options.append({
            "label": "都不对，我解释一下",
            "semantic_value": "freeform_correction",
            "is_freeform": True,
            "is_disconfirming": True,
        })

        return options

    async def get_rendered_timeline(
        self,
        user_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Demo Experience Point #11: 混合时间轴记录完整 causal trace。

        Loads recent CausalTrace records and renders them into user-visible
        TimelineCard dicts that Flutter can render as a mixed causal timeline.

        Returns:
            List of rendered TimelineCard dicts (may include card, trace_id,
            signal, policy_decision, directives, receipt, outcome, event_summary).
        """
        import json

        from app.signals.types import ActionableSignal, PolicyDecision, UserVisibleReceipt

        traces = await self.trace_store.get_user_traces(user_id, limit=limit)
        cards: list[dict[str, Any]] = []

        for trace in traces:
            # Load signal
            signal_data = None
            if trace.signal_ids:
                raw = await self.redis.get(f"spine:signal:{trace.signal_ids[0]}")
                if raw:
                    try:
                        signal_data = ActionableSignal.from_dict(
                            json.loads(raw if isinstance(raw, str) else raw.decode())
                        ).to_dict()
                    except Exception:
                        logger.warning("get_rendered_timeline: operation failed", exc_info=True)

            # Load policy decision
            policy_data = None
            if trace.policy_decision_id:
                raw = await self.redis.get(f"spine:policy:{trace.policy_decision_id}")
                if raw:
                    try:
                        policy_data = PolicyDecision.from_dict(
                            json.loads(raw if isinstance(raw, str) else raw.decode())
                        ).to_dict()
                    except Exception:
                        logger.warning("get_rendered_timeline: operation failed", exc_info=True)

            # Load directives
            directives: list[dict[str, Any]] = []
            for did in trace.directive_ids:
                raw = await self.redis.get(f"spine:directive_by_id:{did}")
                if raw:
                    try:
                        directives.append(
                            json.loads(raw if isinstance(raw, str) else raw.decode())
                        )
                    except Exception:
                        logger.warning("get_rendered_timeline: operation failed", exc_info=True)

            # Load receipt
            receipt_data = None
            if trace.receipt_ids:
                raw = await self.redis.get(f"spine:receipt_by_id:{trace.receipt_ids[0]}")
                if not raw:
                    raw = await self.redis.get(f"spine:receipt:{user_id}:latest")
                if raw:
                    try:
                        receipt_data = UserVisibleReceipt.from_dict(
                            json.loads(raw if isinstance(raw, str) else raw.decode())
                        ).to_dict()
                    except Exception:
                        logger.warning("get_rendered_timeline: operation failed", exc_info=True)

            # Build human-readable event summary
            event_parts = []
            if signal_data:
                event_parts.append(f"信号: {signal_data.get('claim', '?')}")
            if policy_data:
                event_parts.append(f"策略: {policy_data.get('primary_strategy', '?')}")
            event_summary = " → ".join(event_parts) if event_parts else "系统事件"

            # Render TimelineCard
            card_data = None
            try:
                card = self.timeline_renderer.render_card(
                    trace_id=trace.trace_id,
                    signal_data=signal_data,
                    policy_data=policy_data,
                    directives=directives,
                    receipt_data=receipt_data,
                    outcome_data=None,
                    mode="compact",
                    timestamp=trace.created_at,
                )
                if card:
                    card_data = card.to_dict()
            except Exception:
                logger.warning("get_rendered_timeline: operation failed", exc_info=True)

            cards.append({
                "trace_id": trace.trace_id,
                "created_at": trace.created_at,
                "event_summary": event_summary,
                "signal": signal_data,
                "policy_decision": policy_data,
                "directives": directives,
                "receipt": receipt_data,
                "card": card_data,
            })

        return cards

    # ── P12: SourceTray User Override ──────────────────────────────────

    async def set_source_tray_selection(
        self,
        *,
        user_id: str,
        selections: list[dict[str, Any]],
        mode: str = "manual_only",
    ) -> dict[str, Any]:
        """
        Demo Experience Point #5: 用户能手动选择资料参与本轮。

        Persists the user's explicit source tray selections. These are consumed
        by the retrieval layer to control which materials enter context.

        Args:
            user_id: User identifier
            selections: List of {source_id, action, scope, user_initiated} dicts.
                        action ∈ {include, exclude, auto}
                        scope ∈ {this_turn, this_task, today, this_goal}
            mode: "manual_only" | "auto" | "no_materials"

        Iron Rule: This only writes to Redis (ephemeral session state).
        It does NOT write to any database or affect long-term user state.
        """
        import json

        from app.signals.types import SourceTraySelection, SourceTrayState

        parsed: list[SourceTraySelection] = []
        for sel in selections:
            try:
                parsed.append(SourceTraySelection(
                    source_id=str(sel.get("source_id", "")),
                    action=str(sel.get("action", "auto")),
                    scope=str(sel.get("scope", "this_task")),
                    user_initiated=bool(sel.get("user_initiated", True)),
                ))
            except Exception:
                logger.warning("set_source_tray_selection: failed", exc_info=True)
                continue

        state = SourceTrayState(mode=mode, selections=parsed)
        key = f"spine:source_tray:{user_id}"
        await self.redis.set(key, json.dumps(state.to_dict()), ex=24 * 3600)  # 24h TTL
        logger.info(
            "SourceTray: user={} mode={} selections={}",
            user_id, mode, len(parsed),
        )
        return state.to_dict()

    async def get_source_tray_state(self, user_id: str) -> dict[str, Any]:
        """
        Returns the current SourceTrayState for the user.

        If no selections have been made, returns the default auto-mode state.
        Flutter reads this to render the source tray UI and indicate user overrides.
        """
        import json

        from app.signals.types import SourceTrayState

        key = f"spine:source_tray:{user_id}"
        raw = await self.redis.get(key)
        if not raw:
            # Default: auto mode, no explicit selections
            return SourceTrayState(mode="auto", selections=[]).to_dict()
        try:
            return json.loads(raw if isinstance(raw, str) else raw.decode())
        except (json.JSONDecodeError, TypeError):
            return SourceTrayState(mode="auto", selections=[]).to_dict()

    async def apply_directive_to_task_spec(
        self,
        user_id: str,
        task_spec: dict[str, Any],
        soft_biases: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], DirectiveApplicationAudit | None]:
        """
        供 planning_workflow 调用——将 directive 约束应用到任务 spec，并审计。
        soft_biases 来自 PolicyDecision，用于难度微调。
        """
        directive = await self.get_active_directive(user_id)
        if not directive:
            # No directive — still apply soft difficulty if available
            if soft_biases:
                current_diff = task_spec.get("difficulty", 3)
                adjusted_diff, changed = DirectiveApplier.apply_soft_difficulty(
                    soft_biases=soft_biases,
                    current_difficulty=current_diff,
                )
                if changed:
                    task_spec["difficulty"] = adjusted_diff
            return task_spec, None

        modified_spec = DirectiveApplier.apply_to_task_spec(
            directive=directive,
            task_spec=task_spec,
        )

        # Apply soft difficulty from PolicyDecision.soft_biases
        if soft_biases:
            current_diff = modified_spec.get("difficulty", 3)
            adjusted_diff, _ = DirectiveApplier.apply_soft_difficulty(
                soft_biases=soft_biases,
                current_difficulty=current_diff,
            )
            modified_spec["difficulty"] = adjusted_diff

        audit = DirectiveAuditor.audit(
            directive=directive,
            generated_task=modified_spec,
        )

        # Metrics: track if directive was applied and changed output
        changed = modified_spec != task_spec
        await self.metrics.record_directive_applied(changed_output=changed)

        # 链接 audit 到最近的 trace
        traces = await self.trace_store.get_user_traces(user_id, limit=1)
        if traces:
            await self.trace_store.append_audit(traces[0].trace_id, audit)

        # 如果 directive 已消费（scope=today），清除
        if directive.scope == "today":
            await self.trace_store.clear_active_directive(user_id)
            logger.info("Directive {} consumed and cleared for user {}", directive.directive_id, user_id)

        return modified_spec, audit

    async def get_latest_receipt(self, user_id: str) -> UserVisibleReceipt | None:
        """供前端调用——获取最新的 Receipt。Degraded: returns None on Redis failure."""
        try:
            import json
            raw = await self.redis.get(f"spine:receipt:{user_id}:latest")
            if not raw:
                return None
            d = json.loads(raw)
            return UserVisibleReceipt(
                receipt_id=d["receipt_id"],
                receipt_type=d["receipt_type"],
                message=d["message"],
                actions=d["actions"],
                related_state_keys=d["related_state_keys"],
                created_at=d.get("created_at", ""),
            )
        except Exception:
            logger.debug("get_latest_receipt degraded: Redis unavailable for user={}", user_id)
            return None

    async def handle_user_receipt_action(
        self,
        user_id: str,
        receipt_id: str,
        action: str,
    ) -> None:
        """
        用户对 Receipt 的反馈。
        - confirm: 确认接受策略调整
        - correct: 用户纠正（收回判断）
        - dismiss: 忽略
        """
        import json
        if action == "correct":
            # 用户纠正 → 清除 directive，记录到 self_model
            await self.trace_store.clear_active_directive(user_id)
            logger.info("User corrected receipt {} — directive cleared", receipt_id)
            await self.metrics.record_retraction()
            await self.metrics.record_outcome_recorded(effective=False)

            # 记录纠正到 self_model
            try:
                from app.aurora.runtime_v1.self_model import SparkleSelfModelService
                from app.core.cache import cache_service
                await SparkleSelfModelService(cache_service.redis).record_user_correction(
                    user_id=user_id,
                    signal_id=f"receipt_correct:{receipt_id}",
                    reason="user_corrected_strategy_adjustment",
                    source="spine_receipt",
                )
            except Exception as exc:
                logger.warning("Failed to record user correction to self_model: {}", exc)

            # Divine moment 2: 承认误判 — chronicle + relationship update
            try:
                await self.on_user_correction(
                    user_id=user_id,
                    correction_type="receipt_correction",
                    original_claim="strategy_adjustment",
                    corrected_understanding="user_disagreed_with_adjustment",
                    trace_id=receipt_id,
                )
            except Exception as exc:
                logger.debug("on_user_correction skipped: {}", exc)
        elif action == "confirm":
            await self.metrics.record_outcome_recorded(effective=True)
        elif action == "dismiss":
            await self.metrics.record_outcome_recorded(effective=False)

        # 清除 receipt
        await self.redis.delete(f"spine:receipt:{user_id}:latest")
        # 记录用户动作
        await self.redis.set(
            f"spine:receipt_action:{receipt_id}",
            json.dumps({"action": action, "user_id": user_id}),
            ex=72 * 3600,
        )

    # ── P1 Integration: Achievement Reinforcement ─────────────────────

    async def on_achievement_event(
        self,
        *,
        user_id: str,
        achievement_type: str,
        achievement_id: str,
        recent_unlocks: int = 0,
        active_streaks: int = 0,
        in_progress_count: int = 0,
    ) -> CausalTrace | None:
        """成就事件 → AchievementReinforcementConsumer → PolicyEngine → trace。"""
        signal = self.achievement_consumer.process_achievement_event(
            user_id=user_id,
            event_type="achievement.unlocked",
            recent_unlocks=recent_unlocks,
            active_streaks=active_streaks,
            in_progress_count=in_progress_count,
        )
        if signal is None:
            return None

        trace = await self._run_signal_pipeline(
            user_id=user_id,
            signal=signal,
            event_ids=[f"achievement_{achievement_id}"],
        )

        # Goal checkpoint snapshot: achievement unlock is a milestone worth persisting
        try:
            await self.save_spine_snapshot(
                user_id=user_id, snapshot_type="goal_checkpoint",
            )
        except Exception:
            logger.warning("on_achievement_event: save_spine_snapshot failed", exc_info=True)

        # STAB-004: Wire ReturnCaseFile from GrowthChronicle into return flow
        await self._save_return_case_file(user_id)

        return trace

    # ── P8: Mistake Event Integration ──────────────────────────────────

    async def on_mistake_event(
        self,
        *,
        user_id: str,
        error_id: str,
        linked_node_ids: list[str],
        error_type: str | None = None,
    ) -> CausalTrace | None:
        """
        错题创建事件 → MistakeSignalDetector → transfer_failure signal → pipeline。

        Called from galaxy_event_consumer._handle_error_created() when an error.created
        event arrives. If the same knowledge node has 3+ consecutive errors, generates
        a transfer_failure ActionableSignal that constrains the next task card.

        Iron Rule: This is a read-only Spine call. Galaxy mastery updates happen
        separately in ErrorBookMasterySyncService — no double-write here.
        """
        signals = await self.mistake_detector.on_error_created(
            user_id=user_id,
            error_id=error_id,
            linked_node_ids=linked_node_ids,
            error_type=error_type,
        )
        if not signals:
            return None

        # Run each triggering signal through the full pipeline.
        # Multiple nodes triggering simultaneously is rare; first trace wins.
        trace = None
        for signal in signals:
            t = await self._run_signal_pipeline(
                user_id=user_id,
                signal=signal,
                event_ids=[f"error_{error_id}"],
            )
            if t is not None and trace is None:
                trace = t
        return trace

    async def on_quiz_result(
        self,
        *,
        user_id: str,
        task_id: str,
        quiz_accuracy: float,
        linked_node_ids: list[str] | None = None,
        node_id: str | None = None,
    ) -> CausalTrace | None:
        """
        小测结果事件 → 低正确率 → transfer_failure signal → pipeline。

        Threshold: quiz_accuracy < 0.5 → generate signal (知识迁移失败).
        High accuracy (>= 0.7) → no signal (不干预).
        Mid accuracy (0.5-0.69) → no signal (观察, 不立即干预).
        """
        _LOW_ACCURACY_THRESHOLD = 0.5
        if quiz_accuracy >= _LOW_ACCURACY_THRESHOLD:
            return None

        effective_node = node_id or (linked_node_ids[0] if linked_node_ids else "unknown")
        signal = ActionableSignal(
            signal_id=_uid("sig"),
            source_event_ids=[task_id],
            source_system="quiz_result",
            state_key="knowledge_transfer",
            claim="transfer_failure",
            confidence=min(0.4 + (1.0 - quiz_accuracy) * 0.5, 0.85),
            scope="current_sprint",
            ttl_hours=48,
            evidence_summary=(
                f"小测正确率 {quiz_accuracy:.0%}，低于 50% 阈值。"
                f"节点 {effective_node} 当前掌握度不足，判断为知识迁移未完成。"
            ),
            possible_effects=[
                "avoid_new_chapter",
                "require_worked_example",
                "reduce_task_difficulty",
            ],
            priority="high",
        )

        return await self._run_signal_pipeline(
            user_id=user_id,
            signal=signal,
            event_ids=[f"quiz_{task_id}"],
        )

    # ── P9: File Upload → Galaxy Node Mapping ──────────────────────────

    async def on_file_uploaded(
        self,
        *,
        user_id: str,
        file_id: str,
        filename: str,
        parsed_summary: str = "",
        goal_id: str | None = None,
        mime_type: str = "application/octet-stream",
    ) -> CausalTrace | None:
        """
        文件上传事件 → 知识星图节点语义映射 → source_material signal → pipeline。

        Iron Rule: 本方法不写 UserNodeStatus，不修改 mastery_score。
        GalaxyService 仅做只读语义检索（semantic_search_nodes）。
        映射结果存入 Redis 供 Flutter 星图节点高亮消费。

        Demo Experience Point #2: 上传资料后，知识星图节点被点亮。
        """
        import json
        from datetime import datetime

        # Step 1: 语义检索匹配知识节点（只读，不修改任何 mastery）
        matched_nodes: list[dict[str, Any]] = []
        if parsed_summary.strip():
            try:
                from app.db.session import AsyncSessionLocal
                from app.services.galaxy_service import GalaxyService
                async with AsyncSessionLocal() as db:
                    galaxy = GalaxyService(db)
                    nodes = await galaxy.semantic_search_nodes(
                        parsed_summary,
                        limit=5,
                        threshold=0.15,
                    )
                    for n in nodes:
                        matched_nodes.append({
                            "node_id": str(n.id),
                            "node_name": getattr(n, "name", str(n.id)),
                        })
            except Exception as galaxy_err:
                logger.debug("P9 Galaxy node mapping skipped: {}", galaxy_err)

        # Step 2: 存储映射结果到 Redis（7天 TTL，供 Flutter 读取高亮节点）
        node_ids = [m["node_id"] for m in matched_nodes]
        mapping_key = f"spine:file_nodes:{user_id}:{file_id}"
        await self.redis.set(
            mapping_key,
            json.dumps({
                "file_id": file_id,
                "filename": filename,
                "goal_id": goal_id,
                "mime_type": mime_type,
                "mapped_nodes": matched_nodes,
                "mapped_at": datetime.now(UTC).isoformat(),
            }),
            ex=7 * 24 * 3600,
        )

        # Step 3: 注册到 MaterialSignalDetector（供后续利用率监测使用）
        await self.material_signal_detector.register_uploaded_file(
            user_id=user_id,
            file_id=file_id,
            filename=filename,
            node_ids=node_ids,
        )

        # Step 4: 生成 source_material:material_received signal
        confidence = 0.75 if matched_nodes else 0.45
        node_names = [m["node_name"] for m in matched_nodes[:3]]
        signal = ActionableSignal(
            signal_id=_uid("sig"),
            source_event_ids=[file_id],
            source_system="file_integration",
            state_key="source_material",
            claim="material_received",
            confidence=confidence,
            scope="current_sprint",
            ttl_hours=168,  # 7 days
            evidence_summary=(
                f"用户上传了课件「{filename}」。"
                + (
                    f"语义检索匹配到 {len(matched_nodes)} 个知识节点：{', '.join(node_names)}。"
                    if matched_nodes
                    else "暂未匹配到相关知识节点，待索引建立后重新匹配。"
                )
            ),
            possible_effects=[
                "highlight_galaxy_nodes",
                "prefer_targeted_source_rag",
                "suggest_material_review",
            ],
            priority="medium",
        )

        return await self._run_signal_pipeline(
            user_id=user_id,
            signal=signal,
            event_ids=[f"file_{file_id}"],
        )

    async def get_file_node_mapping(
        self,
        *,
        user_id: str,
        file_id: str,
    ) -> dict[str, Any] | None:
        """
        读取文件-知识节点映射（供 Flutter 星图高亮消费）。

        Returns:
            dict with keys: file_id, filename, goal_id, mapped_nodes, mapped_at
            None if no mapping found.
        """
        import json
        mapping_key = f"spine:file_nodes:{user_id}:{file_id}"
        raw = await self.redis.get(mapping_key)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None

    # ── P1 Integration: Recall Opportunity ─────────────────────────────

    async def on_recall_check(
        self,
        *,
        user_id: str,
        trigger_type: str,
        **kwargs,
    ) -> CausalTrace | None:
        """检查召回机会 → RecallOpportunityDetector → PolicyEngine → trace。"""
        trigger = None

        if trigger_type == "undigested_material":
            trigger = self.recall_detector.check_undigested_material(
                user_id=user_id, **kwargs,
            )
        elif trigger_type == "task_not_started":
            trigger = self.recall_detector.check_task_not_started(
                user_id=user_id, **kwargs,
            )
        elif trigger_type == "task_missed":
            trigger = self.recall_detector.check_task_missed(
                user_id=user_id, **kwargs,
            )
        elif trigger_type == "pre_exam_silence":
            trigger = self.recall_detector.check_pre_exam_silence(
                user_id=user_id, **kwargs,
            )

        if trigger is None:
            return None

        signal = self.recall_detector.to_actionable_signal(trigger)
        return await self._run_signal_pipeline(
            user_id=user_id,
            signal=signal,
            event_ids=[f"recall_{trigger_type}"],
        )

    async def build_recall_notification(
        self,
        user_id: str,
        trigger_type: str,
        context: dict[str, Any],
    ) -> RecallMessage | None:
        """Build and store a user-facing recall notification if policy allows it."""
        normalized_trigger = {
            "first_task_not_started": "task_not_started",
        }.get(trigger_type, trigger_type)

        in_cooldown = await self.recall_notification_builder.check_cooldown_async(
            user_id,
            normalized_trigger,
            self.redis,
        )
        if in_cooldown:
            return None

        signal = ActionableSignal(
            signal_id=_uid("sig"),
            source_event_ids=[f"recall_{normalized_trigger}"],
            source_system="recall_notification",
            state_key="recall_needed",
            claim=normalized_trigger,
            confidence=0.80,
            scope="current_sprint",
            ttl_hours=6,
            evidence_summary=context.get("evidence_summary", f"recall notification: {normalized_trigger}"),
            possible_effects=["send_recall_message"],
            priority=context.get("priority", "medium"),
        )
        result = await self.policy_engine.evaluate(signal, context={"source": "recall_notification"})
        if result is None:
            return None

        decision, _ = result
        notif_dir = self.policy_engine.build_notification_directive(decision, signal)
        if notif_dir is None or not notif_dir.allowed:
            return None

        message_context = {
            **context,
            "cooldown_until": self.recall_notification_builder.get_cooldown_until(normalized_trigger),
            "frequency_tag": notif_dir.max_frequency,
        }
        message = self.recall_notification_builder.build_message(
            trigger_type=normalized_trigger,
            message_strategy=notif_dir.message_strategy,
            context=message_context,
        )
        if message is None:
            return None

        await self.directive_store.store_notification(user_id, notif_dir)
        await self._store_recall_message(user_id, message)
        await self.recall_notification_builder.record_sent_async(user_id, normalized_trigger, self.redis)
        return message

    # ── Generic signal pipeline (shared by all P1 sources) ─────────────

    async def _run_signal_pipeline(
        self,
        *,
        user_id: str,
        signal: ActionableSignal,
        event_ids: list[str] | None = None,
    ) -> CausalTrace | None:
        """通用 Signal → PolicyEngine → Directive → Trace 链路。Wrapped with circuit breaker + concurrency guard."""
        import json

        from app.signals.redis_resilience import resilient_redis_call

        # Concurrency guard: skip if a pipeline is already running for this user
        lock_key = f"spine:pipeline_lock:{user_id}"
        try:
            locked = await self.redis.set(lock_key, "1", nx=True, ex=30)
            if not locked:
                logger.debug("Pipeline skipped: concurrent run for user={}", user_id)
                return None
        except Exception as _lock_err:
            _ce = classify_error(_lock_err, component="spine_pipeline_lock", category=ErrorCategory.REDIS)
            logger.warning("Pipeline lock failed: {} [{}]", _lock_err, _ce.severity.value)
            if _ce.severity == ErrorSeverity.CRITICAL:
                logger.error("Critical Redis failure in pipeline lock for user={}", user_id)

        # STAB-006: Auto-increment 24h interaction counter for FatigueGuard
        try:
            _ik = f"spine:interaction_count:{user_id}:24h"
            _ic = await self.redis.incr(_ik)
            if _ic == 1:
                await self.redis.expire(_ik, 24 * 3600)
        except Exception as _count_err:
            _ce = classify_error(_count_err, component="spine_interaction_counter", category=ErrorCategory.REDIS, severity=ErrorSeverity.WARNING)
            logger.warning("Interaction counter failed: {} [{}]", _count_err, _ce.severity.value)

        trace = await resilient_redis_call(
            "spine_pipeline", self.trace_store.create_trace(),
            fallback=None,
        )
        if trace is None:
            logger.warning("Spine pipeline skipped: trace creation failed for user={}", user_id)
            try:
                await self.redis.delete(lock_key)
            except Exception as _del_err:
                classify_error(_del_err, component="spine_pipeline_lock", category=ErrorCategory.REDIS)
            return None

        if event_ids:
            trace.raw_event_ids.extend(event_ids)
        await resilient_redis_call(
            "spine_pipeline",
            self.trace_store.link_to_user(user_id, trace.trace_id),
        )

        await resilient_redis_call(
            "spine_pipeline", self.trace_store.store_signal(signal),
        )
        await resilient_redis_call(
            "spine_pipeline",
            self.trace_store.append_signal(trace.trace_id, signal),
        )
        trace.signal_ids.append(signal.signal_id)
        await resilient_redis_call(
            "spine_pipeline", self.metrics.record_signal_generated(),
        )

        # Layer 4: Persist signal state to StateRegister
        await resilient_redis_call(
            "state_register",
            self.state_register.upsert_from_signal(user_id, signal),
        )
        await resilient_redis_call(
            "spine_pipeline", self.metrics.record_signal_entered_state(),
        )

        # L2 Mid Aurora: Check for escalation patterns and trigger interventions
        l2_escalation = await resilient_redis_call(
            "spine_pipeline",
            self._check_l2_escalation(user_id),
            fallback=None,
        )

        # Fetch recent policy effects for shadow learning
        recent_effects = await resilient_redis_call(
            "spine_pipeline",
            self.outcome_recorder.get_recent_policy_effects(user_id, limit=10),
            fallback=[],
        )

        # v2.4: Fetch strategy beliefs from LearningBase
        strategy_beliefs = await resilient_redis_call(
            "spine_pipeline",
            self._load_strategy_beliefs(user_id),
            fallback=[],
        )
        aurora_decisions = await resilient_redis_call(
            "spine_pipeline",
            self.consume_aurora_decisions(user_id=user_id, limit=3),
            fallback=[],
        )

        pipeline_context = {
            "source": "pipeline",
            "aurora_decisions": aurora_decisions,
        }
        if l2_escalation:
            pipeline_context["l2_escalation"] = l2_escalation
            trace.raw_event_ids.append(f"l2:{l2_escalation['pattern_name']}")

        # EA-2: Safety degradation gate — check level before policy evaluation
        safety_level = await resilient_redis_call(
            "spine_pipeline",
            self._safety_degradation.get_current_level(user_id),
            fallback=None,
        )
        if safety_level is not None and safety_level.value != "normal":
            restricted = self._safety_degradation.get_restricted_capabilities(safety_level)
            pipeline_context["safety_restricted_capabilities"] = restricted
            logger.debug("Safety degradation active for user={}: level={}, restricted={}", user_id, safety_level.value, restricted)

        result = await self.policy_engine.evaluate(
            signal,
            context=pipeline_context,
            recent_policy_effects=recent_effects,
            strategy_beliefs=strategy_beliefs,
        )
        await self.metrics.record_policy_evaluated(matched=result is not None)
        if result is None:
            trace.outcome_to_measure = ["signal_no_rule_match"]
            await self.trace_store._save_trace(trace)
            try:
                await self.redis.delete(f"spine:pipeline_lock:{user_id}")
            except Exception as _unlock_err:
                classify_error(_unlock_err, component="spine_pipeline_lock", category=ErrorCategory.REDIS)
            return trace

        decision, directive = result

        # GOV-016: Force receipt visibility for high-impact low-confidence signals
        # (handled after policy evaluation)

        # EA-3: High-impact confirmation gate
        if self._high_impact_confirmation.is_high_impact(
            directive_type=directive.directive_type if hasattr(directive, "directive_type") else "response",
            risk_level=decision.risk_level if hasattr(decision, "risk_level") else "low",
            user_correction_count=0,
            claim_confidence=signal.confidence if hasattr(signal, "confidence") else 0.8,
        ):
            confirm_req = self._high_impact_confirmation.build_confirmation_request(
                user_id=user_id,
                directive=directive.to_dict() if hasattr(directive, "to_dict") else {"directive_id": "unknown"},
                reason=f"High-impact directive (risk={decision.risk_level if hasattr(decision, 'risk_level') else 'unknown'})",
            )
            trace.raw_event_ids.append(f"confirm:{confirm_req.request_id}")
            pipeline_context["requires_confirmation"] = confirm_req.request_id

        await self.trace_store.append_policy(trace.trace_id, decision)
        await self.trace_store.append_directive(trace.trace_id, directive)
        await self.metrics.record_directive_generated()
        trace.policy_decision_id = decision.policy_decision_id  # Keep local in sync
        trace.directive_ids.append(directive.directive_id)  # Keep local in sync

        # Overlay ExamSprintPolicy constraints if user is in exam_rescue mode
        directive = await self._apply_exam_sprint_overlay(user_id, directive)
        await self.trace_store.set_active_directive(user_id, directive)
        await self._link_directive_to_active_session(user_id, directive.directive_id)

        # T5.1.2: Generate research-grade InterventionEpisode
        episode = await self._generate_episode(
            user_id=user_id, signal=signal, decision=decision,
            directive=directive, trace=trace,
        )
        if episode is not None:
            await self._store_episode(user_id, episode)

        # Build and store ResponseDirective (L1: state-aware)
        active_states = await self._get_active_states_dicts(user_id)
        response_dir = self.policy_engine.build_response_directive(
            decision, signal, active_states=active_states,
        )
        if response_dir:
            await self.directive_store.store_response(user_id, response_dir)
            # EA-1: Fabrication guard — scan response text for unverifiable claims
            try:
                response_text = response_dir.message if hasattr(response_dir, "message") else ""
                flagged = self._fabrication_scanner(response_text)
                if flagged:
                    logger.warning("FabricationGuard: flagged {} pattern(s) in response for user={}", len(flagged), user_id)
                    trace.raw_event_ids.append(f"fabrication:{len(flagged)}")
            except Exception:
                logger.debug("Fabrication scan failed for user={}", user_id, exc_info=True)

        # Build and store NotificationDirective
        notif_dir = self.policy_engine.build_notification_directive(decision, signal)
        if notif_dir:
            await self.directive_store.store_notification(user_id, notif_dir)

        # Build and store RetrievalDirective
        ret_dir = self.policy_engine.build_retrieval_directive(decision, signal)
        if ret_dir:
            await self.directive_store.store_retrieval(user_id, ret_dir)
            # Divine moment 3: 知道不用资料 — build context receipt
            try:
                await self.build_context_receipt(
                    user_id=user_id,
                    used_sources=list(ret_dir.must_load or []),
                    excluded_sources=list(ret_dir.do_not_load or []),
                    reason=signal.evidence_summary or "",
                    retrieval_mode=ret_dir.retrieval_mode,
                )
            except Exception:
                logger.warning("build_context_receipt failed for user=%s", user_id, exc_info=True)

        # Build and store PlanDirective
        plan_dir = self.policy_engine.build_plan_directive(decision, signal)
        if plan_dir:
            await self.directive_store.store_plan(user_id, plan_dir)
            trace.directive_ids.append(plan_dir.directive_id)

        # Build and store ModelWriteDirective
        mw_dir = self.policy_engine.build_model_write_directive(decision, signal)
        if mw_dir:
            await self.directive_store.store_model_write(user_id, mw_dir)
            trace.directive_ids.append(mw_dir.directive_id)
            # Auto-apply model writes (confidence-gated, no user_confirmation needed)
            await self._apply_model_writes(user_id, mw_dir)

        # Build and store UXDirective
        ux_dir = self.policy_engine.build_ux_directive(decision, signal)
        if ux_dir:
            await self.directive_store.store_ux(user_id, ux_dir)
            trace.directive_ids.append(ux_dir.directive_id)

        # Build and store CommunityDirective
        comm_dir = self.policy_engine.build_community_directive(decision, signal)
        if comm_dir:
            await self._store_community_directive(user_id, comm_dir)
            trace.directive_ids.append(comm_dir.directive_id)

        # Build and store SkillDirective
        skill_dir = self.policy_engine.build_skill_directive(decision, signal)
        if skill_dir:
            await self._store_skill_directive(user_id, skill_dir)
            trace.directive_ids.append(skill_dir.directive_id)

        if decision.visibility == "receipt":
            # EA-4: Research isolation — filter PII from receipt if research context
            receipt_message = directive.user_visible_reason
            try:
                research_ctx_key = f"spine:research_context:{user_id}"
                raw_ctx = await self.redis.get(research_ctx_key)
                if raw_ctx:
                    import json as _json
                    ctx_data = _json.loads(raw_ctx)
                    if ctx_data.get("is_research"):
                        rctx = self._research_isolation.create_research_context(
                            study_id=ctx_data.get("study_id", "unknown"),
                        )
                        filtered = self._research_isolation.filter_pii_fields(
                            {"message": receipt_message}, rctx,
                        )
                        receipt_message = filtered.get("message", receipt_message)
            except Exception:
                logger.debug("Research isolation filter failed for user={}", user_id, exc_info=True)

            receipt = UserVisibleReceipt(
                receipt_id=_uid("rcpt"),
                receipt_type="strategy_adjustment",
                message=receipt_message,
                actions=["confirm", "correct", "dismiss"],
                related_state_keys=[signal.state_key],
            )
            await self.trace_store.append_receipt(trace.trace_id, receipt)
            await self.metrics.record_receipt_shown()
            trace.receipt_ids.append(receipt.receipt_id)  # Keep local in sync
            await self.redis.set(
                f"spine:receipt:{user_id}:latest",
                json.dumps(receipt.to_dict()),
                ex=72 * 3600,
            )
            await self.redis.set(
                f"spine:receipt_by_id:{receipt.receipt_id}",
                json.dumps(receipt.to_dict()),
                ex=72 * 3600,
            )

        trace.outcome_to_measure = [
            "user_response",
            "behavioral_change",
        ]

        # Quality guard: validate signal→directive chain before finalizing trace
        await self._run_live_quality_guard(trace)

        await self.trace_store._save_trace(trace)

        # P0-2: Post-policy enrichment from previously orphaned modules
        await self._enrich_pipeline_post_policy(
            user_id=user_id,
            signal=signal,
            decision=decision,
            directive=directive,
        )

        logger.info(
            "Spine P1 pipeline: trace={} signal={} policy={}",
            trace.trace_id, signal.signal_id,
            decision.policy_decision_id,
        )

        # Release pipeline lock
        try:
            await self.redis.delete(f"spine:pipeline_lock:{user_id}")
        except Exception as _final_unlock:
            classify_error(_final_unlock, component="spine_pipeline_lock", category=ErrorCategory.REDIS)
        return trace

    # ── P0-1 Integration: FirstMinuteSnapshot / ExamRescue ─────────────

    async def on_first_message(
        self,
        *,
        user_id: str,
        message: str,
    ) -> CausalTrace | None:
        """首条消息 → ExamRescueDetector → PolicyEngine → trace。"""
        snapshot = self.exam_rescue.analyze_first_message(message)
        if snapshot is None:
            return None

        # Persist deadline context so ExamSprintPolicy can activate on every turn
        if snapshot.deadline_days is not None and snapshot.detected_mode == "exam_rescue":
            await self.redis.set(
                f"spine:exam_sprint:{user_id}:deadline_days",
                str(snapshot.deadline_days),
                ex=7 * 24 * 3600,
            )
            await self.redis.set(
                f"spine:exam_sprint:{user_id}:goal_mode",
                snapshot.detected_mode,
                ex=7 * 24 * 3600,
            )
            logger.info(
                "ExamSprintContext stored: user={} deadline_days={} mode={}",
                user_id, snapshot.deadline_days, snapshot.detected_mode,
            )

        signal = self.exam_rescue.to_actionable_signal(snapshot, user_id=user_id)
        if signal is None:
            return None

        return await self._run_signal_pipeline(
            user_id=user_id,
            signal=signal,
            event_ids=["first_message_exam_rescue"],
        )

    # ── P0-2 Integration: StaleStateGuard ──────────────────────────────

    async def on_user_return(
        self,
        *,
        user_id: str,
        time_context: dict,
    ) -> CausalTrace | None:
        """用户返回 → StaleStateGuard 检测 → trace + recovery card + snapshot recovery。"""
        from app.signals.stale_state_guard import TimeContext
        tc = TimeContext(**time_context)
        packet = self.stale_guard.check(tc)
        if packet is None:
            return None

        trace = await self.trace_store.create_trace()
        trace.raw_event_ids.append("user_return_stale")
        await self.trace_store.link_to_user(user_id, trace.trace_id)
        trace.outcome_to_measure = ["user_responded_to_stale_check"]
        await self.trace_store._save_trace(trace)

        logger.info("Spine stale: user={} elapsed={}min", user_id, tc.elapsed_since_last_interaction_min)

        # P2: Build recovery card for returning user (divine moment 4)
        try:
            await self.build_recovery_card(
                user_id=user_id,
                elapsed_minutes=tc.elapsed_since_last_interaction_min,
            )
        except Exception as exc:
            logger.debug("build_recovery_card skipped: {}", exc)

        # P2: Try to recover state from snapshot if states are empty (TTL expired)
        try:
            states = await self.state_register.get_active_states(user_id)
            if not states:
                recovered = await self.recover_from_snapshot(user_id=user_id)
                if recovered:
                    logger.info("Spine state recovered from snapshot for user={}", user_id)
        except Exception as exc:
            logger.debug("recover_from_snapshot skipped: {}", exc)

        # STAB-004: Wire ReturnCaseFile from GrowthChronicle into return flow
        await self._save_return_case_file(user_id)

        # Refresh snapshot on return (pre_ttl_expiry — extends the 90d window)
        try:
            snap_ttl = await self.redis.ttl(f"spine:snapshot:{user_id}:latest")
            if snap_ttl is not None and snap_ttl < 7 * 24 * 3600:  # < 7 days left
                await self.save_spine_snapshot(user_id=user_id, snapshot_type="pre_ttl_expiry")
                logger.info("Spine snapshot refreshed for user={} (was TTL={}s)", user_id, snap_ttl)
        except Exception:
            logger.warning("on_user_return: redis failed", exc_info=True)

        return trace

    # ── P0-3 Integration: ActionableStatePacket ────────────────────────

    async def build_state_packet(
        self,
        *,
        user_id: str,
        active_signals: list[ActionableSignal] | None = None,
        goal_frame: dict | None = None,
    ) -> ActionableStatePacket:
        """构建当前用户的 ActionableStatePacket 供下游消费。"""
        directive = await self.get_active_directive(user_id)
        signals = active_signals or []

        # Layer 3: rank signals before building state packet
        if signals:
            ranking = self.signal_ranker.rank(signals)
            signals = [rs.signal for rs in ranking.ranked]

        return self.state_packet_builder.build(
            user_id=user_id,
            active_signals=signals,
            active_directive=directive,
            goal_frame=goal_frame,
        )

    # ── P1-3 Integration: PredictedReplyOptions ────────────────────────

    def generate_reply_options(self, signal: ActionableSignal):
        """为确认问题生成预测回答选项。"""
        return self.reply_engine.generate_options(signal)

    def process_reply_selection(self, question, selected_option_id: str, freeform_text: str | None = None) -> dict:
        """处理用户选择的回答选项，返回状态补丁。"""
        return self.reply_engine.process_user_selection(question, selected_option_id, freeform_text)

    # ── P1-5 Integration: SelfModel ─────────────────────────────────────

    async def record_strategy_outcome(
        self,
        *,
        user_id: str,
        directive_id: str,
        claim_id: str,
        expected_outcome: str,
        actual_outcome: dict,
    ):
        """记录策略执行结果到自我模型。"""
        return await self.self_model.record_outcome(
            user_id=user_id,
            directive_id=directive_id,
            claim_id=claim_id,
            expected_outcome=expected_outcome,
            actual_outcome=actual_outcome,
        )

    # ── P1-6 Integration: CommunitySignal ───────────────────────────────

    async def on_community_cohort_data(
        self,
        *,
        user_id: str,
        knowledge_node_id: str,
        subject: str,
        mistake_type: str,
        cohort_size: int,
        error_count: int,
        common_misconception: str,
    ) -> CausalTrace | None:
        """社群错因数据 → CommunitySignalDetector → PolicyEngine → trace。"""
        pattern = self.community_detector.detect_cohort_mistake(
            knowledge_node_id=knowledge_node_id,
            subject=subject,
            mistake_type=mistake_type,
            cohort_size=cohort_size,
            error_count=error_count,
            common_misconception=common_misconception,
        )
        if pattern is None:
            return None

        hint = self.community_loops.build_cohort_mistake_hint(pattern.to_dict())
        if hint is None:
            return None
        await self._store_community_loop_artifact(user_id, "cohort_mistake_hint", hint)

        # Divine moment 6: 社群经验转策略
        try:
            await self.on_community_hint(
                user_id=user_id,
                knowledge_node=knowledge_node_id,
                common_mistake=common_misconception,
                cohort_size=cohort_size,
            )
        except Exception:
            logger.warning("on_community_cohort_data: on_community_hint failed", exc_info=True)

        signal = self.community_detector.to_actionable_signal(pattern)
        return await self._run_signal_pipeline(
            user_id=user_id,
            signal=signal,
            event_ids=["community_cohort_mistake"],
        )

    async def on_community_resource_data(
        self,
        *,
        user_id: str,
        resource_id: str,
        resource_title: str,
        subject: str,
        peer_count: int,
        relevance_score: float,
        peer_ratings: list[float] | None = None,
        completion_rate: float | None = None,
    ) -> CausalTrace | None:
        """社群资料推荐 → CommunitySignalDetector → PolicyEngine → trace。"""
        quality = self.community_loops.score_resource_quality({
            "resource_id": resource_id,
            "peer_ratings": peer_ratings or [relevance_score],
            "usage_count": peer_count,
            "completion_rate": completion_rate if completion_rate is not None else relevance_score,
            "relevance_score": relevance_score,
        })
        if quality["quality_score"] is None or quality["recommendation_level"] == "low":
            return None
        await self._store_community_loop_artifact(user_id, "resource_quality", quality)

        rec = self.community_detector.detect_shared_resource(
            resource_id=resource_id,
            resource_title=resource_title,
            subject=subject,
            recommendation_reason=(
                "highly_rated_by_cohort"
                if quality["recommendation_level"] == "high"
                else "frequently_used"
            ),
            peer_count=peer_count,
            relevance_score=float(quality["quality_score"]),
        )
        if rec is None:
            return None

        signal = self.community_detector.to_actionable_signal(rec)
        return await self._run_signal_pipeline(
            user_id=user_id,
            signal=signal,
            event_ids=["community_shared_resource"],
        )

    async def on_partner_observation(
        self,
        *,
        user_id: str,
        partner_id: str,
        observation_type: str,
        observation_text: str,
        target_area: str,
    ) -> CausalTrace | None:
        """Partner observation → CommunityLoopManager → ActionableSignal → trace."""
        adjustment = self.community_loops.apply_partner_feedback({
            "partner_id": partner_id,
            "observation_type": observation_type,
            "observation_text": observation_text,
            "target_area": target_area,
        })
        if adjustment is None:
            return None

        await self._store_community_loop_artifact(user_id, "partner_feedback", adjustment)
        scope = str(adjustment["scope"])
        signal = ActionableSignal(
            signal_id=_uid("sig"),
            source_event_ids=["community_partner_observation"],
            source_system="community_loops",
            state_key=str(adjustment["state_key"]),
            claim=str(adjustment["claim"]),
            confidence=0.75,
            scope=scope,
            ttl_hours=48 if scope in ("next_48h", "current_sprint") else 12,
            evidence_summary=str(adjustment["evidence_summary"]),
            possible_effects=["strategy_micro_adjustment", "plan_patch"],
            priority="medium",
        )
        return await self._run_signal_pipeline(
            user_id=user_id,
            signal=signal,
            event_ids=["community_partner_observation"],
        )

    # ── P3-6 Integration: ExternalIntegrationGateway ────────────────────

    async def on_external_event(
        self,
        *,
        user_id: str,
        source: str,
        source_detail: str,
        raw_payload: dict[str, Any],
        goal_id: str | None = None,
        integration_id: str = "",
    ) -> CausalTrace | None:
        """External event entry gate — all external data enters Spine as ExternalRawEvent.

        Dispatches to ExternalIntegrationGateway which translates to ActionableSignal.
        Iron Rule: external signals cannot bypass the Spine.
        Supports sources: 'calendar', 'file', 'email', 'github', 'tool'.
        """
        try:
            import uuid

            from app.signals.external_integration import ExternalIntegrationGateway, ExternalRawEvent
            raw_event = ExternalRawEvent(
                event_id=f"ext_{uuid.uuid4().hex[:12]}",
                source=source,
                source_detail=source_detail,
                goal_id=goal_id,
                raw_payload=raw_payload,
                user_visible=True,
                revocable=True,
                integration_id=integration_id,
            )
            gateway = ExternalIntegrationGateway()
            signal = gateway.dispatch(raw_event)
            if signal is None:
                return None

            return await self._run_signal_pipeline(
                user_id=user_id,
                signal=signal,
                event_ids=[raw_event.event_id],
            )
        except Exception:
            logger.debug("on_external_event degraded: source={}, user={}", source, user_id)
            return None

    # ── P1-2 Integration: AuroraWake ────────────────────────────────────

    def check_aurora_wake(
        self,
        *,
        user_id: str,
        quota_remaining: int,
        cooldown_status: str,
        cooldown_minutes_left: int = 0,
        consecutive_negative_outcomes: int = 0,
        user_requested_deep_review: bool = False,
        momentum_stalled: bool = False,
    ):
        """判断是否可以唤醒完整 Aurora Session。"""
        return self.wake_judge.judge(
            user_id=user_id,
            quota_remaining=quota_remaining,
            cooldown_status=cooldown_status,
            cooldown_minutes_left=cooldown_minutes_left,
            consecutive_negative_outcomes=consecutive_negative_outcomes,
            user_requested_deep_review=user_requested_deep_review,
            momentum_stalled=momentum_stalled,
        )

    # ── Layer 3: Signal Ranking ────────────────────────────────────────

    def rank_signals(self, signals: list[ActionableSignal], *, max_signals: int = 5):
        """排序信号并解决冲突。返回 RankingResult。"""
        return self.signal_ranker.rank(signals, max_signals=max_signals)

    # ── P1-3 Integration: CoreSession lifecycle ────────────────────────

    async def create_core_session(self, user_id: str, goal_id: str | None = None) -> CoreSession:
        """Create an active CoreSession for a user's current goal loop."""
        return await self.core_session_manager.create_session(user_id=user_id, goal_id=goal_id)

    async def get_active_core_session(self, user_id: str) -> CoreSession | None:
        """Return the user's active CoreSession, if one exists."""
        return await self.core_session_manager.get_active_session(user_id)

    async def advance_session_phase(self, session_id: str, phase: str) -> CoreSession:
        """Advance a CoreSession to the next lifecycle phase."""
        return await self.core_session_manager.advance_phase(session_id=session_id, to_phase=phase)

    async def _link_directive_to_active_session(self, user_id: str, directive_id: str) -> None:
        """Attach the newest directive to the user's active CoreSession when present."""
        session = await self.core_session_manager.get_active_session(user_id)
        if session is None:
            return
        await self.core_session_manager.link_directive(session.session_id, directive_id)

    # ── Layer 4: State Register ────────────────────────────────────────

    async def get_active_states(self, user_id: str) -> list:
        """获取用户当前所有活跃状态。返回 list[StateEntry]。"""
        return await self.state_register.get_active_states(user_id)

    async def add_counter_evidence(self, user_id: str, state_key: str, evidence: str) -> bool:
        """为某状态添加反证。"""
        return await self.state_register.add_counter_evidence(user_id, state_key, evidence)

    async def remove_state(self, user_id: str, state_key: str) -> None:
        """移除某状态。"""
        await self.state_register.remove_state(user_id, state_key)

    async def _get_active_states_dicts(self, user_id: str) -> list[dict[str, Any]]:
        """Get active StateRegister entries as dicts for L1 tone modulation."""
        try:
            entries = await self.state_register.get_active_states(user_id)
            return [
                {"state_key": e.state_key, "value": e.value, "confidence": e.confidence, "scope": e.scope}
                for e in entries
            ]
        except Exception:
            return []

    # ── T5.1.2: Research-Grade InterventionEpisode Generation ──────────

    async def _generate_episode(
        self,
        *,
        user_id: str,
        signal: ActionableSignal,
        decision: PolicyDecision,
        directive,
        trace: CausalTrace,
    ) -> InterventionEpisode | None:
        """Build a research-grade InterventionEpisode from the current pipeline state.

        Maps StateRegister entries → ContextSignature (9 dimensions),
        extracts candidate policies from the decision, and creates
        an episode with propensity scoring metadata.
        """
        try:
            # Build ContextSignature from StateRegister + signal
            states = await self.state_register.get_active_states(user_id)
            state_map = {s.state_key: s.value for s in states}

            goal_mode = state_map.get("goal_mode", "standard")
            deadline_pressure = "low"
            if "deadline_pressure" in state_map:
                deadline_pressure = state_map["deadline_pressure"]
            elif decision.risk_level in ("critical", "high"):
                deadline_pressure = "high"

            deadline_phase = ""
            raw_days = await self.redis.get(f"spine:exam_sprint:{user_id}:deadline_days")
            if raw_days:
                try:
                    days = int(raw_days if isinstance(raw_days, str) else raw_days.decode())
                    deadline_phase = f"D-{days}"
                except (ValueError, AttributeError):
                    pass

            cognitive_load = state_map.get("cognitive_load", "")
            affective_pressure = state_map.get("affective_pressure", "")

            ctx = ContextSignature(
                goal_mode=goal_mode,
                deadline_phase=deadline_phase,
                deadline_pressure=deadline_pressure,
                knowledge_bottleneck=signal.state_key if signal.state_key.startswith("knowledge_transfer") else state_map.get("knowledge_bottleneck", ""),
                failure_type=signal.claim,
                cognitive_load=cognitive_load if cognitive_load in ("low", "medium", "high") else ("medium" if signal.priority == "high" else "low"),
                affective_pressure=affective_pressure if affective_pressure in ("calm", "tense", "anxious", "fatigued") else "",
                source_availability=state_map.get("source_material", ""),
                user_id=user_id,
                goal_id=state_map.get("goal_id", ""),
            )

            # Candidate policies: primary + secondary + common alternatives
            candidates = [decision.primary_strategy]
            if decision.secondary_strategy:
                candidates.append(decision.secondary_strategy)
            # Add generic alternatives for propensity scoring
            for alt in ("reduce_pace", "reinforce_without_overpressure", "simplify_task"):
                if alt not in candidates:
                    candidates.append(alt)

            # Selection probability: uniform over candidates if no experiment running
            sel_prob = 1.0 / len(candidates) if len(candidates) > 1 else 1.0

            # Determine domain from goal mode
            domain = "exam_sprint" if goal_mode == "exam_rescue" else goal_mode or "standard"

            episode = InterventionEpisodeLedger.create_episode(
                user_id=user_id,
                goal_id=ctx.goal_id,
                domain=domain,
                context_signature=ctx,
                candidate_policies=candidates,
                selected_policy=decision.primary_strategy,
                selection_reason=decision.reasoning_summary[:200] if decision.reasoning_summary else signal.evidence_summary[:200],
                selection_mode="rule_based",
                selection_confidence=signal.confidence,
                selection_probability=sel_prob,
                risk_level=decision.risk_level,
                directive_ids=[directive.directive_id],
            )

            # T5.1.3: Validate integrity and apply evidence quality
            episode.evidence_quality = InterventionEpisodeLedger.validate_integrity(episode)

            return episode
        except Exception:
            logger.warning("_generate_episode failed for user={}", user_id, exc_info=True)
            return None

    async def _store_episode(self, user_id: str, episode: InterventionEpisode) -> None:
        """Persist InterventionEpisode to Redis for research-grade evaluation."""
        try:
            import json
            key = f"spine:episode:{user_id}:{episode.episode_id}"
            await self.redis.set(key, json.dumps(episode.to_dict()), ex=90 * 24 * 3600)
            # Also append to user's episode index (most recent 100)
            await self.redis.rpush(
                f"spine:episodes:{user_id}",
                episode.episode_id,
            )
            await self.redis.ltrim(f"spine:episodes:{user_id}", -100, -1)
            await self.redis.expire(f"spine:episodes:{user_id}", 90 * 24 * 3600)
        except Exception:
            logger.warning("_store_episode failed for user={}", user_id, exc_info=True)

    # ── L2 Mid Aurora: Escalation Detection ─────────────────────────────

    async def _check_l2_escalation(self, user_id: str) -> dict[str, Any] | None:
        """Check StateRegister for L2 escalation patterns.

        Returns escalation result if a pattern matched, None otherwise.
        """
        try:
            from app.aurora.runtime_v1.l2_intervention import L2InterventionEngine

            active_states = await self._get_active_states_dicts(user_id)
            if not active_states:
                return None

            engine = L2InterventionEngine(self.redis)
            return await engine.check_escalation(user_id, active_states)
        except Exception as exc:
            logger.warning("L2 escalation check failed for user={}: {}", user_id, exc)
            return None

    # ── Layer 6: Directive persistence (delegated to DirectiveStore) ────

    async def _store_response_directive(self, user_id: str, rd: ResponseDirective) -> None:
        await self.directive_store.store_response(user_id, rd)

    async def get_response_directive(self, user_id: str) -> ResponseDirective | None:
        return await self.directive_store.get_response(user_id)

    async def _store_notification_directive(self, user_id: str, nd: NotificationDirective) -> None:
        await self.directive_store.store_notification(user_id, nd)

    async def get_notification_directive(self, user_id: str) -> NotificationDirective | None:
        return await self.directive_store.get_notification(user_id)

    async def _store_recall_message(self, user_id: str, message: RecallMessage) -> None:
        import json
        key = f"spine:recall_notification:{user_id}:latest"
        await self.redis.set(key, json.dumps(message.to_dict()), ex=72 * 3600)

    async def get_recall_notification(self, user_id: str) -> RecallMessage | None:
        try:
            import json
            raw = await self.redis.get(f"spine:recall_notification:{user_id}:latest")
            if not raw:
                return None
            return RecallMessage.from_dict(json.loads(raw))
        except Exception:
            logger.debug("get_recall_notification degraded: Redis unavailable for user={}", user_id)
            return None

    async def _enrich_retrieval_with_source_tray(self, user_id: str, rd: RetrievalDirective) -> None:
        from app.signals.source_tray_integration import build_source_receipt, compute_retrieval_plan
        from app.signals.types import SourceTrayState

        try:
            import json
            raw = await self.redis.get(f"spine:source_tray:{user_id}")
            if not raw:
                return
            tray = SourceTrayState.from_dict(json.loads(raw if isinstance(raw, str) else raw.decode()))
        except Exception:
            logger.warning("_enrich_retrieval_with_source_tray: failed", exc_info=True)
            return

        from app.signals.source_tray_integration import SourceEffectivenessTracker
        blocked: set[str] = set()
        try:
            tracker = SourceEffectivenessTracker(self.redis)
            blocked = set(await tracker.get_blocked_sources(user_id))
        except Exception:
            logger.warning("_enrich_retrieval_with_source_tray: redis_op failed", exc_info=True)

        plan = await compute_retrieval_plan(
            retrieval_directive=rd, source_tray=tray, blocked_source_ids=blocked or None,
        )
        if plan["must_load"]:
            rd.must_load = list({s["source_id"] for s in plan["must_load"]} | set(rd.must_load or []))
        if plan["do_not_load"]:
            rd.do_not_load = list({s["source_id"] for s in plan["do_not_load"]} | set(rd.do_not_load or []))

        loaded_ids = [s["source_id"] for s in plan["must_load"]]
        receipt = build_source_receipt(rd, tray, loaded_ids)
        import json
        await self.redis.set(
            f"spine:source_receipt:{user_id}:latest",
            json.dumps(receipt),
            ex=72 * 3600,
        )

    async def _store_retrieval_directive(self, user_id: str, rd: RetrievalDirective) -> None:
        await self.directive_store.store_retrieval(user_id, rd)

    async def get_retrieval_directive(self, user_id: str) -> RetrievalDirective | None:
        return await self.directive_store.get_retrieval(user_id)

    async def get_source_receipt(self, user_id: str) -> dict[str, Any] | None:
        try:
            import json
            raw = await self.redis.get(f"spine:source_receipt:{user_id}:latest")
            if not raw:
                return None
            return json.loads(raw if isinstance(raw, str) else raw.decode())
        except Exception:
            logger.warning("get_source_receipt: failed", exc_info=True)
            return None

    async def set_source_tray(self, user_id: str, tray_state: dict[str, Any]) -> None:
        import json
        await self.redis.set(
            f"spine:source_tray:{user_id}",
            json.dumps(tray_state),
            ex=7 * 24 * 3600,
        )

    async def _store_plan_directive(self, user_id: str, pd: PlanDirective) -> None:
        await self.directive_store.store_plan(user_id, pd)

    async def get_plan_directive(self, user_id: str) -> PlanDirective | None:
        return await self.directive_store.get_plan(user_id)

    async def _store_model_write_directive(self, user_id: str, mwd: ModelWriteDirective) -> None:
        await self.directive_store.store_model_write(user_id, mwd)

    async def get_model_write_directive(self, user_id: str) -> ModelWriteDirective | None:
        return await self.directive_store.get_model_write(user_id)

    async def get_model_claims(
        self, user_id: str, target_model: str | None = None, scope: str | None = None,
    ) -> list[dict[str, Any]]:
        return await self.directive_store.get_model_claims(user_id, target_model, scope)

    _SHORT_SCOPES = frozenset({"turn", "session", "task", "day"})

    async def _apply_model_writes(self, user_id: str, mwd: ModelWriteDirective) -> None:
        import json
        for entry in mwd.writes:
            if entry.needs_user_confirmation or entry.confidence < 0.7:
                continue
            key = f"spine:model_claim:{user_id}:{entry.target_model}:{entry.scope}"
            await self.redis.set(
                key,
                json.dumps({
                    "claim": entry.claim,
                    "confidence": entry.confidence,
                    "source": "spine_auto",
                    "directive_id": mwd.directive_id,
                    "scope": entry.scope,
                }),
                ex=self._ttl_to_seconds(entry.ttl),
            )

    @staticmethod
    def _ttl_to_seconds(ttl: str) -> int:
        if ttl.endswith("h"):
            return int(ttl[:-1]) * 3600
        if ttl.endswith("d"):
            return int(ttl[:-1]) * 86400
        return 72 * 3600

    async def _store_ux_directive(self, user_id: str, uxd: UXDirective) -> None:
        await self.directive_store.store_ux(user_id, uxd)

    async def get_ux_directive(self, user_id: str) -> UXDirective | None:
        return await self.directive_store.get_ux(user_id)

    # ── P0-6: ExamSprintPolicy ──────────────────────────────────────────

    def get_exam_sprint_policy(
        self,
        *,
        days_to_deadline: int,
        goal_mode: str = "exam_rescue",
    ):
        """Compute phase-appropriate constraints for exam sprint."""
        if not ExamSprintPolicyService.should_activate(
            goal_mode=goal_mode, days_to_deadline=days_to_deadline,
        ):
            return None
        return self.exam_sprint_policy.compute(days_to_deadline=days_to_deadline)

    async def _get_exam_sprint_context(self, user_id: str) -> tuple[str, int | None]:
        """Return (goal_mode, days_to_deadline) from stored exam sprint context."""
        raw_mode = await self.redis.get(f"spine:exam_sprint:{user_id}:goal_mode")
        raw_days = await self.redis.get(f"spine:exam_sprint:{user_id}:deadline_days")
        if not raw_mode or not raw_days:
            return "standard", None
        goal_mode = raw_mode.decode() if isinstance(raw_mode, bytes) else raw_mode
        try:
            days = int(raw_days.decode() if isinstance(raw_days, bytes) else raw_days)
        except (ValueError, AttributeError):
            return goal_mode, None
        return goal_mode, days

    async def _apply_exam_sprint_overlay(
        self,
        user_id: str,
        directive: ExecutionDirective,
    ) -> ExecutionDirective:
        """Overlay ExamSprintPhase or GoalTypeAdapter constraints onto an ExecutionDirective.

        Exam sprint mode uses phase-specific constraints.
        Non-exam goals use GoalTypeAdapter for task type bias and retrieval mode.
        """
        goal_mode, days = await self._get_exam_sprint_context(user_id)
        if ExamSprintPolicyService.should_activate(goal_mode=goal_mode, days_to_deadline=days):
            assert days is not None  # guaranteed by should_activate
            esp = self.exam_sprint_policy.compute(days_to_deadline=days)
            phase = esp.phase

            hc = dict(directive.hard_constraints or {})
            existing_max = hc.get("max_task_duration_min", 999)
            hc["max_task_duration_min"] = min(existing_max, phase.max_task_duration_min)
            if not phase.allow_new_chapters:
                hc["avoid_new_chapter"] = True
            if phase.prefer_high_yield_review:
                hc["prefer_high_yield"] = True
            hc["exam_sprint_task_type_bias"] = phase.task_type_bias
            hc["exam_sprint_difficulty_cap"] = phase.difficulty_cap
            hc["exam_sprint_retrieval_mode"] = phase.retrieval_mode
            hc["exam_sprint_phase_id"] = phase.phase_id
            directive.hard_constraints = hc

            prefix = f"[D-{days} · {phase.phase_id}]"
            existing = directive.user_visible_reason or ""
            if prefix not in existing:
                directive.user_visible_reason = f"{prefix} {existing}".strip()

            logger.info(
                "ExamSprintPolicy overlay applied: user={} days={} phase={} max_dur={}",
                user_id, days, phase.phase_id, hc["max_task_duration_min"],
            )
            return directive

        # Non-exam goal: apply GoalTypeAdapter for task type bias
        try:
            goal_type_raw = await self.redis.get(f"spine:goal_type:{user_id}")
            if goal_type_raw:
                import json
                goal_data = json.loads(goal_type_raw if isinstance(goal_type_raw, str) else goal_type_raw.decode())
                goal_type = goal_data.get("goal_type", "general")
                if goal_type != "exam":
                    mapping = self.goal_type_adapter.adapt_mastery_mapping(
                        mastery=0.3,  # default; actual mastery comes from Galaxy
                        goal_type=goal_type,
                    )
                    hc = dict(directive.hard_constraints or {})
                    hc["goal_type_task_bias"] = mapping.get("task_type", "")
                    hc["goal_type_difficulty"] = mapping.get("difficulty", 3)
                    hc["goal_type_focus"] = mapping.get("focus", "")
                    hc["goal_type_label"] = mapping.get("node_label", "")
                    hc["goal_type_retrieval_mode"] = (
                        "task_bound_graph_rag" if mapping.get("mastery_trackable") else "targeted_source_rag"
                    )
                    directive.hard_constraints = hc
                    logger.info(
                        "GoalTypeAdapter overlay: user={} goal_type={} task_bias={}",
                        user_id, goal_type, mapping.get("task_type"),
                    )
        except Exception:
            logger.warning("_apply_exam_sprint_overlay: operation failed", exc_info=True)

        return directive

    async def update_exam_sprint_deadline(self, user_id: str, days_to_deadline: int) -> None:
        """Update the stored deadline days (e.g., called each new day or goal update)."""
        await self.redis.set(
            f"spine:exam_sprint:{user_id}:deadline_days",
            str(days_to_deadline),
            ex=7 * 24 * 3600,
        )
        logger.info("ExamSprint deadline updated: user={} days={}", user_id, days_to_deadline)

    # ── Layer 6: CommunityDirective ──────────────────────────────────────

    async def _store_community_loop_artifact(self, user_id: str, artifact_type: str, artifact: dict[str, Any]) -> None:
        """Store latest privacy-safe community loop output for downstream consumers."""
        import json
        key = f"spine:community_loop:{user_id}:{artifact_type}:latest"
        await self.redis.set(key, json.dumps(artifact), ex=72 * 3600)

    async def _store_community_directive(self, user_id: str, cd: CommunityDirective) -> None:
        await self.directive_store.store(user_id, "community", cd)
        await self.directive_store.publish_event("spine:community_directive_channel", {
            "user_id": user_id, "directive_id": cd.directive_id,
            "community_action": cd.action if hasattr(cd, "action") else None,
        })

    async def get_community_directive(self, user_id: str) -> CommunityDirective | None:
        return await self.directive_store.retrieve(user_id, "community", CommunityDirective)

    async def get_latest_community_hint(self, user_id: str) -> dict[str, Any] | None:
        """Return the latest privacy-safe community hint for Flutter to render.

        Checks cohort_mistake first, then partner_feedback.
        Returns None if no hint or the directive has cohort_hint_shown=False.
        """
        import json
        directive = await self.get_community_directive(user_id)
        if directive and not directive.cohort_hint_shown:
            return None

        for artifact_type in ("cohort_mistake", "partner_feedback"):
            raw = await self.redis.get(f"spine:community_loop:{user_id}:{artifact_type}:latest")
            if raw:
                try:
                    return json.loads(raw)
                except Exception:
                    logger.warning("get_latest_community_hint: operation failed", exc_info=True)
        return None

    async def get_ux_risk_warning(self, user_id: str) -> dict[str, Any] | None:
        """Return a proactive risk warning payload for Flutter to render (divine moment #5 阻止低收益).

        Returns a dict with risk_level, reason, and suggested_action when the current
        UXDirective flags risk_detected — combining it with the active ExecutionDirective's
        user_visible_reason. Returns None if no risk is active.
        """

        _CLAIM_TO_LABEL: dict[str, str] = {
            "recent_task_too_large": "任务拆解风险",
            "transfer_failure": "知识迁移受阻",
            "momentum_stalled": "学习势头放缓",
            "task_missed": "任务遗漏",
            "pre_exam_silence": "考前节奏异常",
        }
        _RISK_REASONS: dict[str, str] = {
            "recent_task_too_large": "当前任务颗粒度过大，建议先拆解再行动",
            "transfer_failure": "检测到知识迁移困难，换一种切入角度可能更有效",
            "momentum_stalled": "最近几天完成率下降，可能需要调整策略",
            "task_missed": "有已安排的任务未完成，建议先回顾再推进",
            "pre_exam_silence": "考前静默期——减少新内容，专注复盘",
        }

        try:
            ux_dir = await self.get_ux_directive(user_id)
            if not ux_dir or ux_dir.status_band_state != "risk_detected":
                return None

            active_dir = await self.get_active_directive(user_id)
            user_visible_reason = (
                active_dir.user_visible_reason if active_dir else ""
            )

            # Resolve the signal claim from the active directive's policy_decision_id to get human label
            claim_label = "策略风险"
            risk_reason = user_visible_reason
            if active_dir:
                # Try to match known claim labels from primary_strategy
                for claim, label in _CLAIM_TO_LABEL.items():
                    if claim in (active_dir.primary_strategy or ""):
                        claim_label = label
                        if not risk_reason:
                            risk_reason = _RISK_REASONS.get(claim, "")
                        break

            if not risk_reason:
                risk_reason = "Aurora 检测到当前路径存在效率风险"

            return {
                "risk_level": "medium",
                "label": claim_label,
                "reason": risk_reason,
                "suggested_action": "帮我调整策略",
                "predicted_reply_options": ux_dir.predicted_reply_options or [],
                "status_band_state": ux_dir.status_band_state,
                "directive_id": ux_dir.directive_id,
            }
        except Exception:
            logger.warning("get_ux_risk_warning: failed", exc_info=True)
            return None

    # ── Layer 6: SkillDirective ──────────────────────────────────────────

    async def _store_skill_directive(self, user_id: str, sd: SkillDirective) -> None:
        await self.directive_store.store(user_id, "skill", sd)
        await self.directive_store.publish_event("spine:skill_directive_channel", {
            "user_id": user_id, "directive_id": sd.directive_id,
            "skill_action": sd.action if hasattr(sd, "action") else None,
        })

    async def get_skill_directive(self, user_id: str) -> SkillDirective | None:
        return await self.directive_store.retrieve(user_id, "skill", SkillDirective)

    async def get_applicable_skills(self, user_id: str, context: dict[str, Any]) -> list[SkillEntry]:
        """Return skills that can safely be injected for the current context."""
        skills = await self.skill_lifecycle_manager.get_user_skills(user_id)
        return self.skill_lifecycle_manager.find_applicable_skills(skills, context)

    async def inject_skill_to_task(
        self,
        user_id: str,
        task_spec: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply the strongest applicable worked-example-repair skill to a task."""
        applicable = await self.get_applicable_skills(user_id, context)
        if not applicable:
            return dict(task_spec)

        skill = applicable[0]
        patch = self.skill_lifecycle_manager.build_worked_example_repair(skill, context)
        modified = dict(task_spec)
        modified["task_type"] = patch["task_type_override"]
        modified["strategy_summary"] = patch["strategy_summary"]
        modified["applies_to_nodes"] = patch["applies_to_nodes"]
        modified["_skill_injection"] = {
            "skill_id": skill.skill_id,
            "source_policy_key": skill.source_policy_key,
            "evidence": patch["evidence"],
        }
        return modified

    async def recommend_skill(self, user_id: str) -> dict[str, Any] | None:
        """Return the highest-confidence user-confirmable skill recommendation."""
        skills = await self.skill_lifecycle_manager.get_user_skills(user_id)
        candidates = sorted(
            skills,
            key=lambda skill: (
                -skill.effective_count,
                skill.sample_size,
                skill.skill_id,
            ),
        )
        for skill in candidates:
            recommendation = self.skill_lifecycle_manager.build_recommendation(skill)
            if recommendation is not None:
                return recommendation
        return None

    # ── Layer 8: Outcome Recording ────────────────────────────────────

    async def record_outcome(
        self,
        *,
        trace: CausalTrace,
        intervention: str,
        reason: str,
        expected_outcome: str,
        actual_outcome: dict[str, Any],
        user_id: str = "",
    ):
        """记录干预结果并执行因果归因。"""
        record = await self.outcome_recorder.record_outcome(
            trace=trace,
            intervention=intervention,
            reason=reason,
            expected_outcome=expected_outcome,
            actual_outcome=actual_outcome,
        )
        await self.metrics.record_outcome_recorded(effective=record.attribution == "effective")

        # V-9: Auto strategy learning — update belief from outcome
        if user_id and record.intervention:
            try:
                beliefs = await self._load_strategy_beliefs(user_id)
                outcome_label = "success" if record.attribution == "effective" else "failure"
                matched = [b for b in beliefs if b.strategy_key == record.intervention]
                if matched:
                    updated = self.learning_base.update_belief(
                        matched[0], outcome_label,
                    )
                    beliefs = [updated if b.strategy_key == record.intervention else b for b in beliefs]
                else:
                    from app.signals.learning_base import StrategyBelief
                    new_belief = StrategyBelief(
                        strategy_key=record.intervention,
                        alpha=2.0 if outcome_label == "success" else 1.0,
                        beta=1.0 if outcome_label == "success" else 2.0,
                        evidence_count=1,
                    )
                    beliefs.append(new_belief)
                await self._persist_strategy_beliefs(user_id, beliefs)
            except Exception:
                logger.debug("Auto strategy learning failed for user={}", user_id, exc_info=True)

        # v2.4: Record experiment trial with real outcome
        try:
            if user_id:
                experiments = await self.policy_experiments.get_user_experiments(user_id)
                for exp in experiments:
                    if exp.status == "running":
                        shadow_hyp = self.policy_experiments.evaluate_shadow_outcome(
                            primary_outcome=record.attribution,
                            primary_strategy=exp.primary_strategy,
                            context=actual_outcome,
                        )
                        await self.policy_experiments.record_trial(
                            exp.experiment_id,
                            primary_outcome=record.attribution,
                            shadow_hypothesis=shadow_hyp,
                        )
                        break  # Only record for the most relevant running experiment
        except Exception:
            logger.warning("record_outcome: operation failed", exc_info=True)

        # v2.4: Record source effectiveness if sources were involved
        try:
            source_ids = actual_outcome.get("source_ids", [])
            if user_id and source_ids:
                for sid in source_ids:
                    await self.source_effectiveness.record_source_outcome(
                        user_id=user_id,
                        source_id=sid,
                        outcome=record.attribution,
                    )
        except Exception:
            logger.warning("record_outcome: cache_op failed", exc_info=True)

        # v2.5: Skill extraction from effective strategies
        try:
            if user_id and record.attribution == "effective":
                policy_effects = await self.outcome_recorder.get_recent_policy_effects(
                    user_id, limit=20,
                )
                new_skills = self.skill_extraction.scan_for_extractions(
                    policy_effects,
                    user_id=user_id,
                    context={"goal_mode": actual_outcome.get("goal_mode", "")},
                )
                for skill in new_skills:
                    await self.skill_lifecycle_manager.store_skill(
                        user_id=user_id, skill=skill,
                    )
                    logger.info("Skill extracted and registered: {} from policy={}", skill.skill_id, skill.source_policy_key)
        except Exception:
            logger.warning("record_outcome: operation failed", exc_info=True)

        # v2.5: Consume Aurora decisions for outcome attribution
        try:
            if user_id:
                await self._consume_aurora_decisions_for_attribution(user_id, record)
        except Exception:
            logger.warning("record_outcome: _consume_aurora_decisions_for_attribution failed", exc_info=True)

        # v2.5: Counterfactual shadow evaluation (research-grade)
        try:
            if user_id and record.attribution in ("effective", "insufficient"):
                await self._run_counterfactual_shadow(user_id, record, actual_outcome)
        except Exception:
            logger.warning("record_outcome: _run_counterfactual_shadow failed", exc_info=True)

        return record

    async def get_outcome_for_trace(self, trace_id: str):
        """获取 CausalTrace 对应的 OutcomeRecord。"""
        return await self.outcome_recorder.get_outcome_for_trace(trace_id)

    # ── Metrics ────────────────────────────────────────────────────────

    async def get_metrics_snapshot(self) -> dict[str, Any]:
        """获取 Decision Realization Score 指标快照。"""
        return await self.metrics.snapshot()

    # ── Quality Guard: live pipeline validation ────────────────────────

    async def _run_live_quality_guard(self, trace: CausalTrace) -> None:
        """Run SpineQualityGuard checks on the live pipeline trace.

        Logs warnings but does NOT block the pipeline — quality issues
        are recorded for observability, not used as gates.
        """
        try:
            from app.signals.spine_quality_guard import SpineQualityGuard

            trace_dict = trace.to_dict()
            sig_check = SpineQualityGuard.check_signal_actionability([trace_dict])
            dir_check = SpineQualityGuard.check_directive_compliance([trace_dict])

            if not sig_check.get("passed", True):
                logger.warning(
                    "QualityGuard: signal actionability issue — trace={} issues={}",
                    trace.trace_id, sig_check.get("issues", []),
                )
                await self.metrics.record_spine_degradation("quality_guard_signal")

            if not dir_check.get("passed", True):
                logger.warning(
                    "QualityGuard: directive compliance issue — trace={} issues={}",
                    trace.trace_id, dir_check.get("issues", []),
                )
                await self.metrics.record_spine_degradation("quality_guard_directive")
        except Exception:
            logger.debug("Quality guard skipped for trace={}", trace.trace_id, exc_info=True)

    # ── P0-2: Post-policy enrichment from previously orphaned modules ──

    async def _enrich_pipeline_post_policy(
        self,
        *,
        user_id: str,
        signal: ActionableSignal,
        decision: PolicyDecision,
        directive,
    ) -> None:
        """Wire orphaned modules into the pipeline as capability hooks."""
        import json

        # 1. policy_experiments: shadow A/B evaluation
        try:
            strategy_key = getattr(directive, "strategy_key", None) or decision.primary_strategy
            active_exp = await self.policy_experiments.get_active_experiment_for_strategy(
                user_id, strategy_key,
            )
            if not active_exp:
                await self.policy_experiments.create_experiment(
                    user_id=user_id,
                    signal_state_key=signal.state_key,
                    signal_claim=signal.claim,
                    primary_strategy=strategy_key,
                )
        except Exception:
            logger.warning("_enrich_pipeline_post_policy: policy_experiments failed", exc_info=True)

        # 1b. policy_experiments: check for promotion suggestions
        try:
            experiments = await self.policy_experiments.get_user_experiments(user_id)
            promotions = self.policy_experiments.suggest_promotions(experiments)
            if promotions:
                await self.redis.set(
                    f"spine:experiment:promotions:{user_id}",
                    json.dumps(promotions),
                    ex=24 * 3600,
                )
        except Exception:
            logger.warning("_enrich_pipeline_post_policy: policy_experiments failed", exc_info=True)

        # 2. relationship_model: update from interaction
        try:
            await self.relationship_model.update_from_interaction(
                user_id=user_id,
                interaction_type="system_proactive",
            )
        except Exception:
            logger.warning("_enrich_pipeline_post_policy: relationship_model failed", exc_info=True)

        # 3. growth_chronicle: record if this is a significant event
        try:
            if signal.priority == "high" and signal.confidence >= 0.7:
                entry = self.growth_chronicle.build_milestone_from_outcome({
                    "attribution": "effective",
                    "attribution_confidence": signal.confidence,
                    "intervention": f"检测到 {signal.state_key}",
                    "user_id": user_id,
                    "actual_outcome": {"type": "signal_detected"},
                })
                if entry:
                    await self.growth_chronicle.add_entry(user_id=user_id, entry=entry)
        except Exception:
            logger.warning("_enrich_pipeline_post_policy: growth_chronicle failed", exc_info=True)

        # 4. policy_analytics: record for analytics (async)
        try:
            recent_effects = await self.outcome_recorder.get_recent_policy_effects(user_id, limit=20)
            if recent_effects:
                degrading = self.policy_analytics.detect_degrading_strategies(recent_effects)
                if degrading:
                    await self.redis.set(
                        f"spine:analytics:degrading:{user_id}",
                        json.dumps(degrading),
                        ex=24 * 3600,
                    )
        except Exception:
            logger.warning("_enrich_pipeline_post_policy: outcome_recorder failed", exc_info=True)

        # 5. learning_base: update + persist strategy beliefs
        try:
            beliefs = await self._load_strategy_beliefs(user_id)
            recent_effects = await self.outcome_recorder.get_recent_policy_effects(user_id, limit=10)
            if recent_effects:
                from app.signals.learning_base import StrategyBelief
                belief_map = {b.strategy_key: b for b in beliefs}
                for effect in recent_effects:
                    strategy = getattr(effect, "strategy_key", None) or effect.get("strategy_key")
                    outcome = getattr(effect, "attribution", None) or effect.get("attribution")
                    if strategy and outcome:
                        if strategy not in belief_map:
                            belief_map[strategy] = StrategyBelief(strategy_key=strategy)
                        self.learning_base.update_belief(belief_map[strategy], outcome)
                beliefs = list(belief_map.values())
                await self._persist_strategy_beliefs(user_id, beliefs)
        except Exception:
            logger.warning("_enrich_pipeline_post_policy: operation failed", exc_info=True)

        # 6. fatigue check: detect if user is overworked
        try:
            interaction_count_raw = await self.redis.get(f"spine:interaction_count:{user_id}:24h")
            interaction_count = int(interaction_count_raw) if interaction_count_raw else 0
            fatigue = await self.check_fatigue(
                user_id=user_id,
                interactions_last_24h=interaction_count,
            )
            if fatigue["fatigue_level"] in ("high", "critical"):
                await self.redis.set(
                    f"spine:fatigue:{user_id}:latest",
                    json.dumps(fatigue),
                    ex=6 * 3600,
                )
        except Exception:
            logger.warning("_enrich_pipeline_post_policy: redis failed", exc_info=True)

        # 7. crisis mode check for exam users
        try:
            goal_mode_raw = await self.redis.get(f"spine:exam_sprint:{user_id}:goal_mode")
            deadline_raw = await self.redis.get(f"spine:exam_sprint:{user_id}:deadline_days")
            if goal_mode_raw and deadline_raw:
                crisis = await self.detect_crisis_mode(
                    user_id=user_id,
                    days_to_deadline=int(deadline_raw),
                    baseline_mastery=0,  # unknown → triggers conservative
                )
                if crisis:
                    await self.redis.set(
                        f"spine:crisis:{user_id}:latest",
                        json.dumps(crisis),
                        ex=12 * 3600,
                    )
        except Exception:
            logger.warning("_enrich_pipeline_post_policy: operation failed", exc_info=True)

        # 8. P4 counterfactual evaluation: store policy decision for later analysis
        try:
            from datetime import datetime as _dt
            decision_record = {
                "strategy": decision.primary_strategy,
                "signal_claim": signal.claim,
                "signal_confidence": signal.confidence,
                "risk_level": decision.risk_level,
                "timestamp": _dt.now(UTC).isoformat(),
            }
            await self.redis.rpush(
                f"spine:policy_decisions:{user_id}",
                json.dumps(decision_record),
            )
            await self.redis.ltrim(f"spine:policy_decisions:{user_id}", -100, -1)
            await self.redis.expire(f"spine:policy_decisions:{user_id}", 90 * 24 * 3600)
        except Exception:
            logger.warning("_enrich_pipeline_post_policy: operation failed", exc_info=True)

        # 9. P4 quality guard: signal quality + directive compliance checks
        try:
            from app.signals.spine_quality_guard import SpineQualityGuard
            traces = await self.trace_store.get_user_traces(user_id, limit=20)
            if traces:
                trace_dicts = []
                for t in traces:
                    td = t.to_dict() if hasattr(t, "to_dict") else {}
                    td["had_policy_decision"] = bool(getattr(t, "policy_decision_id", ""))
                    td["had_directive"] = bool(getattr(t, "directive_ids", []))
                    trace_dicts.append(td)
                sig_check = SpineQualityGuard.check_signal_actionability(trace_dicts)
                dir_check = SpineQualityGuard.check_directive_compliance(trace_dicts)
                violations = []
                for chk in (sig_check, dir_check):
                    if not chk.passed:
                        violations.append(chk.to_dict() if hasattr(chk, "to_dict") else {"name": chk.check_name, "score": chk.score})
                if violations:
                    await self.redis.set(
                        f"spine:quality_violations:{user_id}:latest",
                        json.dumps({"violations": violations}),
                        ex=24 * 3600,
                    )
        except Exception:
            logger.warning("_enrich_pipeline_post_policy: operation failed", exc_info=True)

        # 10. P4 research mode: gap detection for continuous improvement
        try:
            from app.signals.research_mode import GapDetector
            quality_health = "healthy"
            quality_score = 1.0
            systemic_issues: list[str] = []
            raw_violations = await self.redis.get(f"spine:quality_violations:{user_id}:latest")
            if raw_violations:
                viol_data = json.loads(raw_violations if isinstance(raw_violations, str) else raw_violations.decode())
                quality_health = "at_risk"
                quality_score = 0.5
                systemic_issues = [v.get("name", "unknown") for v in viol_data.get("violations", [])]
            proposals = GapDetector.from_quality_report(
                quality_health=quality_health,
                quality_score=quality_score,
                systemic_issues=systemic_issues,
            )
            if proposals:
                await self.redis.set(
                    f"spine:research_gaps:{user_id}:latest",
                    json.dumps([p.to_dict() if hasattr(p, "to_dict") else p for p in proposals[:5]]),
                    ex=24 * 3600,
                )
        except Exception:
            logger.warning("_enrich_pipeline_post_policy: operation failed", exc_info=True)

        # 11. P4 safe experiment: bandit suggestion for strategy selection
        try:
            from app.signals.intervention_episode import ContextSignature
            from app.signals.safe_experiment_platform import SafeBanditController
            ctx_sig = ContextSignature(
                goal_mode="standard",
                failure_type=signal.claim,
                cognitive_load="medium" if signal.priority == "high" else "low",
                user_id=user_id,
            )
            candidate_strategies = [decision.primary_strategy, "reduce_pace", "reinforce_without_overpressure"]
            bandit = SafeBanditController()
            result = bandit.select_action(
                candidate_actions=candidate_strategies,
                context=ctx_sig,
                risk_level=decision.risk_level or "low",
            )
            if result and result.get("selected_action") != decision.primary_strategy:
                await self.redis.set(
                    f"spine:bandit_suggestion:{user_id}:latest",
                    json.dumps({
                        "suggested_strategy": result["selected_action"],
                        "reason": result.get("reason", ""),
                    }),
                    ex=24 * 3600,
                )
        except Exception:
            logger.warning("_enrich_pipeline_post_policy: operation failed", exc_info=True)


    # ── Aurora → Spine Return Path ────────────────────────────────────

    async def consume_aurora_decisions(
        self,
        *,
        user_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Consume recent Aurora decisions written by feed_aurora_decision().

        These are Aurora's surface-level action choices that should inform
        Spine's outcome attribution and strategy learning.
        """
        import json
        decisions: list[dict[str, Any]] = []
        try:
            key = f"spine:aurora_decisions:{user_id}"
            raw_list = await self.redis.lrange(key, -limit, -1)
            for raw in raw_list:
                raw_str = raw if isinstance(raw, str) else raw.decode()
                decisions.append(json.loads(raw_str))
        except Exception:
            logger.warning("consume_aurora_decisions: redis failed", exc_info=True)
        return decisions

    async def _consume_aurora_decisions_for_attribution(
        self,
        user_id: str,
        outcome_record: Any,
    ) -> None:
        """Link Aurora decisions with Spine outcomes for cross-system attribution."""
        import json
        try:
            decisions = await self.consume_aurora_decisions(user_id=user_id, limit=5)
            if not decisions:
                return
            # Store the latest Aurora decision alongside the outcome for traceability
            latest = decisions[-1] if decisions else {}
            attribution_link = {
                "spine_attribution": getattr(outcome_record, "attribution", "unknown"),
                "aurora_action": latest.get("action"),
                "aurora_surface": latest.get("surface"),
                "linked_at": _utcnow_iso(),
            }
            await self.redis.set(
                f"spine:aurora_outcome_link:{user_id}:latest",
                json.dumps(attribution_link),
                ex=7 * 24 * 3600,
            )
            # Feed into learning base: if Aurora's action aligns with effective outcome,
            # boost strategy confidence
            if getattr(outcome_record, "attribution", "") == "effective" and latest.get("action"):
                beliefs = await self._load_strategy_beliefs(user_id)
                belief_map = {b.strategy_key: b for b in beliefs}
                aurora_key = f"aurora_{latest['action']}"
                from app.signals.learning_base import StrategyBelief
                if aurora_key not in belief_map:
                    belief_map[aurora_key] = StrategyBelief(strategy_key=aurora_key)
                self.learning_base.update_belief(belief_map[aurora_key], "effective")
                await self._persist_strategy_beliefs(user_id, list(belief_map.values()))
        except Exception:
            logger.warning("_consume_aurora_decisions_for_attribution: operation failed", exc_info=True)

    async def _run_counterfactual_shadow(
        self,
        user_id: str,
        outcome_record: Any,
        actual_outcome: dict[str, Any],
    ) -> None:
        """Run counterfactual evaluation in shadow mode for research-grade analysis.

        Compares the actual strategy against alternatives, storing results for
        later policy improvement without affecting live decisions.
        """
        import json
        try:
            from app.signals.counterfactual_evaluation import MatchedContextEvaluator
            from app.signals.intervention_episode import ContextSignature
            evaluator = MatchedContextEvaluator()
            # Build a synthetic episode from the outcome
            actual_strategy = getattr(outcome_record, "intervention", "unknown")
            ctx = ContextSignature(
                goal_mode=actual_outcome.get("goal_mode", "standard"),
                failure_type=actual_outcome.get("failure_type", ""),
                cognitive_load="medium",
            )
            # Compare against common alternatives
            alternatives = ["reduce_pace", "simplify_task", "worked_example_first"]
            results: list[dict[str, Any]] = []
            for alt in alternatives:
                estimate = evaluator.evaluate(
                    actual_policy=actual_strategy,
                    alternative_policy=alt,
                    episodes=[],  # Shadow mode — no real episodes yet
                    target_context=ctx,
                )
                results.append({
                    "alternative": alt,
                    "estimate": estimate.to_dict() if hasattr(estimate, "to_dict") else str(estimate),
                })
            if results:
                await self.redis.rpush(
                    f"spine:counterfactual_shadow:{user_id}",
                    json.dumps({"strategies_compared": results, "timestamp": _utcnow_iso()}),
                )
                await self.redis.ltrim(f"spine:counterfactual_shadow:{user_id}", -50, -1)
                await self.redis.expire(f"spine:counterfactual_shadow:{user_id}", 90 * 24 * 3600)
        except Exception:
            logger.warning("_run_counterfactual_shadow: operation failed", exc_info=True)

    # ── P1: Divine Moment Enrichers ──────────────────────────────────

    async def on_achievement_unlocked(
        self,
        *,
        user_id: str,
        achievement_type: str,
        streak_count: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """神性时刻1: 看见坚持 — achievement → growth chronicle + strategy bias."""
        try:
            # Record to growth chronicle
            if streak_count >= 3:
                entry = self.growth_chronicle.build_milestone_from_outcome({
                    "attribution": "effective",
                    "attribution_confidence": 0.8,
                    "intervention": f"连续 {streak_count} 天完成任务",
                    "user_id": user_id,
                    "actual_outcome": {
                        "type": achievement_type,
                        "strategy": "consistency_streak",
                        "count": streak_count,
                    },
                })
                if entry:
                    await self.growth_chronicle.add_entry(user_id=user_id, entry=entry)

            # Generate timeline card
            card = self.timeline_renderer.render_card(
                trace_id=_uid("tc"),
                signal_data={
                    "state_key": "achievement_streak",
                    "claim": f"连续 {streak_count} 天完成任务",
                },
                policy_data={"primary_strategy": "reinforce_without_overpressure"},
                mode="compact",
            )
            card_dict = card.to_dict() if card and hasattr(card, "to_dict") else None
            if card_dict:
                import json
                await self.redis.set(
                    f"spine:card:growth:{user_id}:latest",
                    json.dumps(card_dict),
                    ex=7 * 24 * 3600,
                )

            return {"achievement_recorded": True, "streak_count": streak_count}
        except Exception:
            logger.warning("on_achievement_unlocked: failed", exc_info=True)
            return None

    async def on_streak_update(
        self,
        *,
        user_id: str,
        streak_length: int,
        broken: bool = False,
    ) -> None:
        """Update relationship model from streak events."""
        try:
            if broken:
                await self.relationship_model.update_from_behavioral_signal(
                    user_id, "streak_broken", {"streak_length": streak_length},
                )
            else:
                await self.relationship_model.update_from_behavioral_signal(
                    user_id, "streak_maintained", {"streak_length": streak_length},
                )
        except Exception:
            logger.warning("on_streak_update: relationship_model failed", exc_info=True)

    async def on_user_correction(
        self,
        *,
        user_id: str,
        correction_type: str,
        original_claim: str,
        corrected_understanding: str,
        trace_id: str | None = None,
    ) -> dict[str, Any] | None:
        """神性时刻2: 承认误判 — user correction → state patch + strategy bias."""
        import json
        try:
            # Update relationship model
            await self.relationship_model.update_from_interaction(
                user_id=user_id,
                interaction_type="corrected",
            )

            # Record to growth chronicle as turning point
            entry = self.growth_chronicle.build_turning_point_from_correction({
                "topic": original_claim,
                "lesson": corrected_understanding,
                "user_id": user_id,
                "trace_id": trace_id,
            })
            if entry:
                await self.growth_chronicle.add_entry(user_id=user_id, entry=entry)

            # Record to self-model so strategy learning incorporates corrections
            await self.self_model.record_user_correction(
                user_id=user_id,
                signal_id=trace_id or "",
                reason=f"{original_claim} → {corrected_understanding}",
                source="user_receipt_correction",
            )


            # T3.3.3: Feed correction back through Aurora feedback processor
            try:
                await self.correction_feedback.process(
                    user_id=user_id,
                    semantic_value=correction_type or "user_correction",
                    is_disconfirming=True,
                    freeform_text=f"{original_claim} → {corrected_understanding}",
                    telemetry_id=trace_id or "",
                )
            except Exception:
                pass

            # Store correction event for Aurora
            correction_event = {
                "type": "user_correction",
                "original_claim": original_claim,
                "corrected_understanding": corrected_understanding,
                "correction_type": correction_type,
                "trace_id": trace_id,
            }
            await self.redis.set(
                f"spine:correction:{user_id}:latest",
                json.dumps(correction_event),
                ex=72 * 3600,
            )

            return correction_event
        except Exception:
            logger.warning("on_user_correction: failed", exc_info=True)
            return None

    async def on_partner_checkin(
        self,
        *,
        user_id: str,
        partner_id: str,
        checkin_type: str,
    ) -> dict[str, Any] | None:
        """Process a partner accountability check-in event."""
        try:
            result = await self.community_loops.record_partner_checkin(
                self.redis,
                user_id=user_id,
                partner_id=partner_id,
                checkin_type=checkin_type,
            )
            signal_data = result.get("signal")
            if signal_data:
                signal = ActionableSignal(
                    signal_id=_uid("sig"),
                    source_event_ids=[partner_id],
                    source_system="community_loops",
                    state_key=signal_data["state_key"],
                    claim=signal_data["claim"],
                    confidence=signal_data["confidence"],
                    scope=signal_data["scope"],
                    ttl_hours=signal_data["ttl_hours"],
                    evidence_summary=signal_data["evidence_summary"],
                    possible_effects=["adjust_strategy_for_partner_engagement"],
                    priority=signal_data["priority"],
                )
                await self.state_register.upsert_from_signal(user_id, signal)
            return result
        except Exception:
            logger.warning("on_partner_checkin: failed", exc_info=True)
            return None

    async def start_aurora_core_session(
        self,
        *,
        user_id: str,
        goal_summary: str,
        current_plan_summary: str,
        wake_reason: str,
        session_type: str = "strategy_recalibration",
        wake_reasons: list[str] | None = None,
        quota_remaining: int = 3,
        cooldown_status: str = "available",
    ) -> dict[str, Any] | None:
        """Start an L3 Aurora Core Session. Per D6: backend builds case file + agenda."""
        try:
            if not await is_aurora_within_budget(tier="l3_full_core"):
                logger.warning("Aurora L3 budget exhausted, user={}", user_id)
                return None

            # Validate entry via L3 engine
            validation = self.l3_engine.validate_entry(
                wake_reasons=wake_reasons or [wake_reason],
                can_wake=True,
                quota_remaining=quota_remaining,
                cooldown_status=cooldown_status,
            )
            if not validation["allowed"]:
                logger.info(
                    "start_aurora_core_session: denied user={} reason={}",
                    user_id, validation["reason"],
                )
                return None

            states = await self.state_register.get_active_states(user_id)
            state_dicts = [s.to_dict() for s in states]

            recent_effects = await self.outcome_recorder.get_recent_policy_effects(user_id, limit=5)

            resolved_type = validation.get("session_type", session_type)

            case_file = self.aurora_core.build_case_file(
                user_id,
                goal_summary=goal_summary,
                current_plan_summary=current_plan_summary,
                wake_reason=wake_reason,
                active_states=state_dicts,
                recent_outcomes=recent_effects,
            )

            agenda = self.aurora_core.build_agenda_from_case_file(case_file, resolved_type)

            session = await self.aurora_core.create_session(user_id, case_file, agenda)

            try:
                await record_aurora_cost(tier="l3_full_core")
            except Exception:
                pass

            return session
        except Exception:
            logger.warning("start_aurora_core_session: failed", exc_info=True)
            return None

    async def process_aurora_reply(
        self,
        session_id: str,
        item_index: int,
        reply: str,
    ) -> dict[str, Any] | None:
        """Process a user reply to an Aurora agenda item via L3 engine."""
        return await self.l3_engine.execute_agenda_step(session_id, item_index, reply)

    async def pause_aurora_session(
        self,
        session_id: str,
        reason: str = "user_request",
    ) -> dict[str, Any] | None:
        """Pause an active Aurora session."""
        return await self.aurora_core.pause_session(session_id, reason)

    async def resume_aurora_session(self, session_id: str) -> dict[str, Any] | None:
        """Resume a paused Aurora session."""
        return await self.aurora_core.resume_session(session_id)

    async def check_aurora_session_health(self, session_id: str) -> dict[str, Any]:
        """Check health of an Aurora session (idle timeout, max turns, etc.)."""
        return await self.l3_engine.check_session_health(session_id)

    async def close_aurora_session(
        self,
        session_id: str,
        *,
        state_patches: list[dict[str, Any]] | None = None,
        policy_changes: list[dict[str, Any]] | None = None,
        user_summary: str = "",
    ) -> dict[str, Any] | None:
        """Close an Aurora session and apply closure through Spine."""
        patches = [StatePatch(**p) for p in (state_patches or [])]
        changes = [PolicyChange(**c) for c in (policy_changes or [])]

        closure = SessionClosure(
            session_id=session_id,
            state_patches=patches,
            policy_changes=changes,
            directives_to_regenerate=["ExecutionDirective", "ResponseDirective"],
            user_visible_summary=user_summary,
        )

        session = await self.aurora_core.close_session(session_id, closure)
        if not session or "error" in session:
            return session

        # Apply state patches through Spine (proper audit trail)
        user_id = session.get("user_id", "")
        for patch in patches:
            signal = ActionableSignal(
                signal_id=_uid("sig"),
                source_event_ids=[session_id],
                source_system="aurora_core_session",
                state_key=patch.state_key,
                claim=patch.new_value,
                confidence=patch.confidence,
                scope="current_sprint",
                ttl_hours=168,
                evidence_summary=f"Aurora校准: {patch.reason}",
                possible_effects=["strategy_update"],
                priority="high",
            )
            await self.state_register.upsert_from_signal(user_id, signal)

        # P2-C: Regenerate directives for affected states
        regenerated: list[dict[str, Any]] = []
        if user_id and patches:
            active_states = await self.state_register.get_active_states(user_id)
            state_map = {s.state_key: s for s in active_states}
            for patch in patches:
                state_key = patch.state_key
                state_entry = state_map.get(state_key)
                if not state_entry:
                    continue
                # Build a synthetic signal from the patched state for policy evaluation
                synthetic_signal = ActionableSignal(
                    signal_id=_uid("regen"),
                    source_event_ids=[session_id],
                    source_system="aurora_regen",
                    state_key=state_entry.state_key,
                    claim=state_entry.value,
                    confidence=state_entry.confidence,
                    scope=state_entry.scope,
                    ttl_hours=state_entry.ttl_hours,
                    evidence_summary=f"Aurora校准后重新评估: {patch.reason}",
                    possible_effects=["directive_update"],
                    priority="high",
                )
                result = await self.policy_engine.evaluate(synthetic_signal)
                if result:
                    decision, _directive = result
                    regenerated.append({
                        "state_key": state_key,
                        "strategy": decision.primary_strategy,
                    })
                    logger.info(
                        "AuroraRegen: state={} → strategy={}",
                        state_key, decision.primary_strategy,
                    )

        session["regenerated_directives"] = regenerated
        return session

    async def build_recovery_card(
        self,
        *,
        user_id: str,
        elapsed_minutes: float,
        last_task_id: str | None = None,
        last_task_status: str | None = None,
    ) -> dict[str, Any] | None:
        return await self.card_store.build_recovery_card(
            user_id=user_id,
            elapsed_minutes=elapsed_minutes,
            last_task_id=last_task_id,
            last_task_status=last_task_status,
        )

    async def build_context_receipt(
        self,
        *,
        user_id: str,
        used_sources: list[str] | None = None,
        excluded_sources: list[str] | None = None,
        reason: str = "",
        retrieval_mode: str = "auto",
    ) -> dict[str, Any]:
        return await self.card_store.build_context_receipt(
            user_id=user_id,
            used_sources=used_sources,
            excluded_sources=excluded_sources,
            reason=reason,
            retrieval_mode=retrieval_mode,
        )

    async def on_community_hint(
        self,
        *,
        user_id: str,
        knowledge_node: str,
        common_mistake: str,
        cohort_size: int,
    ) -> dict[str, Any] | None:
        return await self.card_store.build_community_hint(
            user_id=user_id,
            knowledge_node=knowledge_node,
            common_mistake=common_mistake,
            cohort_size=cohort_size,
        )

    # ── P2: ExperienceEnvelope Builder ────────────────────────────────

    async def build_experience_envelope(
        self,
        *,
        user_id: str,
        primary_message: str = "",
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """Build unified ExperienceEnvelope for the current turn."""
        import json
        envelope: dict[str, Any] = {
            "turn_id": _uid("turn"),
            "primary_message": {"text": primary_message},
            "status_band": None,
            "receipts": [],
            "context_receipt": None,
            "cards": [],
            "predicted_reply_options": [],
            "timeline_updates": [],
            "task_card_updates": [],
            "debug_trace_id": trace_id,
        }

        try:
            # Status band from active directive
            directive_raw = await self.redis.get(f"spine:directive:active:{user_id}")
            if directive_raw:
                d = json.loads(directive_raw if isinstance(directive_raw, str) else directive_raw.decode())
                envelope["status_band"] = {
                    "state": d.get("strategy_key", "active"),
                    "label": d.get("user_visible_reason", ""),
                    "expandable": True,
                }

            # Latest receipt
            receipt_raw = await self.redis.get(f"spine:receipt:{user_id}:latest")
            if receipt_raw:
                receipt = json.loads(receipt_raw if isinstance(receipt_raw, str) else receipt_raw.decode())
                envelope["receipts"].append(receipt)

            # Context receipt
            ctx_raw = await self.redis.get(f"spine:card:context_receipt:{user_id}:latest")
            if ctx_raw:
                envelope["context_receipt"] = json.loads(ctx_raw if isinstance(ctx_raw, str) else ctx_raw.decode())

            # Recovery card
            recovery_raw = await self.redis.get(f"spine:card:recovery:{user_id}:latest")
            if recovery_raw:
                envelope["cards"].append(json.loads(recovery_raw if isinstance(recovery_raw, str) else recovery_raw.decode()))

            # Growth card
            growth_raw = await self.redis.get(f"spine:card:growth:{user_id}:latest")
            if growth_raw:
                envelope["cards"].append(json.loads(growth_raw if isinstance(growth_raw, str) else growth_raw.decode()))

            # Community hint card
            comm_raw = await self.redis.get(f"spine:card:community_hint:{user_id}:latest")
            if comm_raw:
                envelope["cards"].append(json.loads(comm_raw if isinstance(comm_raw, str) else comm_raw.decode()))

            # Timeline updates: rendered TimelineCards from recent CausalTraces
            # P11 Demo Experience Point #11: 混合时间轴记录完整 causal trace
            try:
                rendered_cards = await self.get_rendered_timeline(user_id, limit=3)
                envelope["timeline_updates"] = rendered_cards
            except Exception:
                logger.warning("build_experience_envelope: failed", exc_info=True)
                # Fallback: bare trace IDs (previous behavior)
                recent_trace_ids = await self.redis.lrange(f"spine:user_traces:{user_id}", 0, 2)
                for tid in recent_trace_ids:
                    tid_str = tid if isinstance(tid, str) else tid.decode()
                    envelope["timeline_updates"].append({"trace_id": tid_str})

            # Predicted reply options from active receipt
            if envelope["receipts"]:
                latest_receipt = envelope["receipts"][0]
                actions = latest_receipt.get("actions", [])
                envelope["predicted_reply_options"] = [
                    {"label": a, "value": a} for a in actions
                ]

        except Exception:
            logger.warning("build_experience_envelope: operation failed", exc_info=True)

        return envelope

    # ── P3: Fatigue Guard ────────────────────────────────────────────

    async def check_fatigue(
        self,
        *,
        user_id: str,
        interactions_last_24h: int = 0,
        consecutive_hours: float = 0.0,
        accuracy_trend: list[float] | None = None,
        is_late_night: bool = False,
    ) -> dict[str, Any]:
        """Detect user fatigue from interaction patterns."""
        level = "low"
        evidence: list[str] = []

        if interactions_last_24h > 30:
            level = "high"
            evidence.append(f"24小时内交互 {interactions_last_24h} 次")
        elif interactions_last_24h > 15:
            level = "medium"
            evidence.append(f"24小时内交互 {interactions_last_24h} 次")

        if consecutive_hours > 4:
            level = "critical" if level == "high" else "high"
            evidence.append(f"连续在线 {consecutive_hours:.1f} 小时")

        if accuracy_trend and len(accuracy_trend) >= 3:
            recent = accuracy_trend[-3:]
            if all(recent[i] < recent[i - 1] for i in range(1, len(recent))):
                if level == "low":
                    level = "medium"
                evidence.append("最近 3 次正确率持续下降")

        if is_late_night:
            if level == "low":
                level = "medium"
            evidence.append("深夜使用")

        policy_map = {
            "low": "normal",
            "medium": "reduce_pace",
            "high": "low_load_review",
            "critical": "forced_break_suggestion",
        }

        constraints = {}
        if level in ("high", "critical"):
            constraints["avoid_new_chapter"] = True
            constraints["max_task_duration_min"] = 15 if level == "critical" else 25
        if level == "critical":
            constraints["suggest_break"] = True

        return {
            "fatigue_level": level,
            "evidence": evidence,
            "recommended_policy": policy_map[level],
            "hard_constraints": constraints,
        }

    # ── P3: Crisis Mode (zero-base + short deadline) ──────────────────

    async def detect_crisis_mode(
        self,
        *,
        user_id: str,
        days_to_deadline: int,
        baseline_mastery: float,
        goal_type: str = "exam",
    ) -> dict[str, Any] | None:
        """Detect if user is in crisis mode: zero-base + very short deadline."""
        if goal_type != "exam" or days_to_deadline > 5:
            return None
        if baseline_mastery >= 30:
            return None

        return {
            "mode": "exam_crisis_zero_base",
            "days_to_deadline": days_to_deadline,
            "baseline_mastery": baseline_mastery,
            "strategy_principles": [
                "不追求体系完整",
                "只追求最低可得分路径",
                "必须显式放弃部分内容",
                "每次任务 15-25 分钟",
                "每个任务只解决一个题型",
                "强制不平均复习",
            ],
            "task_constraints": {
                "max_task_duration_min": 25,
                "min_task_duration_min": 15,
                "avoid_new_chapter": days_to_deadline <= 2,
                "focus_high_yield_only": True,
            },
        }

    # ── P2: Cognitive Load & Affective Pressure Detectors ────────────────

    async def detect_cognitive_load(
        self,
        *,
        user_id: str,
        recent_tasks_count: int = 0,
        new_topics_count: int = 0,
        avg_accuracy: float | None = None,
        session_duration_min: float = 0.0,
    ) -> ActionableSignal | None:
        """Detect high cognitive load from task density + accuracy patterns."""
        triggers = []
        if new_topics_count >= 3 and recent_tasks_count >= 4:
            triggers.append("many_new_topics_in_short_time")
        if avg_accuracy is not None and avg_accuracy < 0.5 and recent_tasks_count >= 3:
            triggers.append("low_accuracy_with_many_tasks")
        if session_duration_min > 90:
            triggers.append("extended_session")

        if not triggers:
            return None

        return ActionableSignal(
            signal_id=_uid("sig"),
            source_event_ids=[f"cognitive_load_{user_id}"],
            source_system="spine_orchestrator",
            state_key="cognitive_load",
            claim="high_load_detected",
            confidence=min(0.9, 0.5 + 0.15 * len(triggers)),
            scope="session",
            ttl_hours=6,
            evidence_summary=f"认知负荷触发: {', '.join(triggers)}",
            possible_effects=["reduce_explanation_length", "prefer_review", "simplify_context"],
            priority="medium",
        )

    async def detect_affective_pressure(
        self,
        *,
        user_id: str,
        consecutive_abandons: int = 0,
        error_density: float = 0.0,
        is_late_night: bool = False,
        days_to_deadline: int | None = None,
        streak_broken: bool = False,
    ) -> ActionableSignal | None:
        """Detect emotional/affective pressure from behavioral signals."""
        triggers = []
        claim = "stress_detected"

        if consecutive_abandons >= 2:
            triggers.append("consecutive_abandonment")
        if error_density > 0.6:
            triggers.append("high_error_density")
        if is_late_night:
            triggers.append("late_night_study")
        if streak_broken:
            triggers.append("streak_broken")

        if not triggers:
            return None

        if consecutive_abandons >= 3 or (days_to_deadline is not None and days_to_deadline <= 2 and len(triggers) >= 2):
            claim = "burnout_risk"

        return ActionableSignal(
            signal_id=_uid("sig"),
            source_event_ids=[f"affective_{user_id}"],
            source_system="spine_orchestrator",
            state_key="affective_pressure",
            claim=claim,
            confidence=min(0.9, 0.5 + 0.12 * len(triggers)),
            scope="session",
            ttl_hours=12,
            evidence_summary=f"情绪压力触发: {', '.join(triggers)}",
            possible_effects=["reduce_pressure", "suggest_break", "easy_win_task"],
            priority="high" if claim == "burnout_risk" else "medium",
        )

    # ── P2: State Snapshot & Recovery ────────────────────────────────

    async def save_spine_snapshot(
        self,
        *,
        user_id: str,
        goal_id: str | None = None,
        snapshot_type: str = "daily",
    ) -> dict[str, Any]:
        """Save a snapshot of Spine state for recovery after TTL expiry."""
        import json
        snapshot = {
            "snapshot_id": _uid("snap"),
            "user_id": user_id,
            "goal_id": goal_id,
            "snapshot_type": snapshot_type,
            "state_summary": {
                "top_states": [],
                "relationship_summary": None,
                "growth_summary": None,
                "policy_effect_summary": None,
                "recent_skills": [],
            },
        }

        try:
            # Collect state summary
            states = await self.state_register.get_active_states(user_id)
            snapshot["state_summary"]["top_states"] = [
                s.to_dict() if hasattr(s, "to_dict") else s for s in states[:10]
            ]

            # Relationship summary
            rel = await self.relationship_model.get_or_create(user_id)
            if hasattr(rel, "to_dict"):
                snapshot["state_summary"]["relationship_summary"] = rel.to_dict()
            elif isinstance(rel, dict):
                snapshot["state_summary"]["relationship_summary"] = rel

            # Growth chronicle summary
            try:
                weekly = await self.growth_chronicle.generate_weekly_summary(user_id)
                if weekly:
                    snapshot["state_summary"]["growth_summary"] = weekly
            except Exception:
                logger.warning("save_spine_snapshot: growth_chronicle failed", exc_info=True)

            # Recent policy effects
            effects = await self.outcome_recorder.get_recent_policy_effects(user_id, limit=10)
            if effects:
                snapshot["state_summary"]["policy_effect_summary"] = [
                    e.to_dict() if hasattr(e, "to_dict") else e for e in effects[:5]
                ]

            # Recent skills
            skills = await self.skill_lifecycle_manager.get_user_skills(user_id)
            if skills:
                snapshot["state_summary"]["recent_skills"] = [
                    s.to_dict() if hasattr(s, "to_dict") else s for s in skills[:5]
                ]

            # Save to Redis with 90-day TTL
            await self.redis.set(
                f"spine:snapshot:{user_id}:latest",
                json.dumps(snapshot),
                ex=90 * 24 * 3600,
            )

        except Exception:
            logger.warning("save_spine_snapshot: operation failed", exc_info=True)

        return snapshot

    async def _save_return_case_file(self, user_id: str) -> None:
        """Build and cache the ReturnCaseFile from GrowthChronicle (STAB-004)."""
        try:
            return_case = await self.growth_chronicle.build_return_case_file(user_id)
            if return_case and return_case.get("confirmed_insights"):
                await self.redis.set(
                    f"spine:return_case_file:{user_id}:latest",
                    json.dumps(return_case),
                    ex=7 * 24 * 3600,
                )
        except Exception as exc:
            logger.debug("build_return_case_file skipped: {}", exc)

    async def recover_from_snapshot(
        self,
        *,
        user_id: str,
    ) -> dict[str, Any] | None:
        """Recover Spine state from latest snapshot after TTL expiry."""
        import json
        try:
            raw = await self.redis.get(f"spine:snapshot:{user_id}:latest")
            if not raw:
                return None
            snapshot = json.loads(raw if isinstance(raw, str) else raw.decode())

            # Rebuild state from snapshot
            states = snapshot.get("state_summary", {}).get("top_states", [])
            for state_data in states:
                state_key = state_data.get("state_key")
                if state_key:
                    from app.signals.types import StateEntry
                    entry = StateEntry(
                        state_key=state_key,
                        value=state_data.get("value", ""),
                        confidence=state_data.get("confidence", 0.5) * 0.8,
                        scope=state_data.get("scope", "current_sprint"),
                        ttl_hours=72,
                    )
                    await self.state_register._save_state(user_id, entry)

            return snapshot
        except Exception:
            logger.warning("recover_from_snapshot: failed", exc_info=True)
            return None

    # ── P2: Multi-Goal Namespace ─────────────────────────────────────

    @staticmethod
    def goal_scoped_key(user_id: str, state_key: str, goal_id: str | None = None) -> str:
        """Generate goal-scoped state key to prevent cross-goal pollution."""
        if goal_id:
            return f"goal:{goal_id}:{state_key}"
        return state_key

    async def get_goal_scoped_states(
        self,
        user_id: str,
        goal_id: str | None = None,
    ) -> list:
        """Get states filtered by goal scope."""
        all_states = await self.state_register.get_active_states(user_id)
        if not goal_id:
            return all_states
        prefix = f"goal:{goal_id}:"
        return [
            s for s in all_states
            if hasattr(s, "state_key") and (
                s.state_key.startswith(prefix) or
                not s.state_key.startswith("goal:")
            )
        ]

    # ── P2: Rolling Metrics ──────────────────────────────────────────

    async def get_rolling_metrics(self, user_id: str) -> dict[str, Any]:
        """Get rolling-window metrics instead of raw counters."""
        import json
        try:
            raw = await self.redis.get(f"spine:metrics:rolling:{user_id}")
            if raw:
                return json.loads(raw if isinstance(raw, str) else raw.decode())
        except Exception:
            logger.warning("get_rolling_metrics: redis failed", exc_info=True)
        return await self.metrics.snapshot()

    # ── v2.4: Learning Layer ────────────────────────────────────────────

    async def _load_strategy_beliefs(self, user_id: str) -> list[Any]:
        """Load persisted strategy beliefs from Redis."""
        import json

        from app.signals.learning_base import StrategyBelief

        key = f"spine:beliefs:{user_id}"
        raw = await self.redis.get(key)
        if not raw:
            return []
        data = json.loads(raw if isinstance(raw, str) else raw.decode())
        return [StrategyBelief.from_dict(b) for b in data]

    async def _persist_strategy_beliefs(self, user_id: str, beliefs: list[Any]) -> None:
        """Persist strategy beliefs to Redis."""
        import json

        key = f"spine:beliefs:{user_id}"
        await self.redis.set(
            key,
            json.dumps([b.to_dict() for b in beliefs]),
            ex=90 * 24 * 3600,  # 90 days
        )

    async def run_auto_deprecation(self, user_id: str) -> list[str]:
        """v2.4: Run auto-deprecation check for stale skills."""
        try:
            deprecated = await self.skill_lifecycle_manager.auto_deprecate_check(user_id)
            if deprecated:
                logger.info("SkillAutoDeprecation: user={} deprecated={}", user_id, deprecated)
            return deprecated
        except Exception:
            logger.warning("run_auto_deprecation: failed", exc_info=True)
            return []

    async def record_source_outcome(
        self,
        *,
        user_id: str,
        source_id: str,
        outcome: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """v2.4: Record source effectiveness after an outcome."""
        try:
            return await self.source_effectiveness.record_source_outcome(
                user_id=user_id,
                source_id=source_id,
                outcome=outcome,
                context=context,
            )
        except Exception:
            logger.warning("record_source_outcome: failed", exc_info=True)
            return None

    # ── v2.5: General Goal OS ───────────────────────────────────────────

    async def get_goal_graph(self, user_id: str, goal_id: str):
        """v2.5: Get goal world graph."""
        return await self.goal_graph.get_graph(user_id, goal_id)

    async def get_goal_focus_suggestions(
        self, user_id: str, goal_id: str, limit: int = 3,
    ) -> list[dict[str, Any]]:
        """v2.5: Get focus suggestions from goal graph."""
        graph = await self.goal_graph.get_graph(user_id, goal_id)
        if not graph:
            return []
        return self.goal_graph.suggest_focus_nodes(graph, limit=limit)

    async def get_goal_deferred_nodes(
        self, user_id: str, goal_id: str, focus_ids: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        """GOAL-006: Get deferred nodes with why_deferred explanations."""
        graph = await self.goal_graph.get_graph(user_id, goal_id)
        if not graph:
            return []
        if focus_ids is None:
            suggestions = self.goal_graph.suggest_focus_nodes(graph)
            focus_ids = {s["node_id"] for s in suggestions}
        return self.goal_graph.get_deferred_nodes(graph, focus_ids=focus_ids)

    async def arbitrate_goals(self, user_id: str):
        """v2.5: Arbitrate between multiple active goals.

        P3-3 ruling: 取舍写入 CausalTrace.
        """
        goals = await self.goal_arbitrator.get_active_goals(user_id)
        if not goals:
            return None
        result = self.goal_arbitrator.arbitrate(goals)
        if result and result.conflicts:
            trace = CausalTrace(
                trace_id=_uid("ct"),
                raw_event_ids=[g.goal_id for g in goals],
                signal_ids=["multi_goal_arbitration"],
                state_keys_changed=[f"goal_priority.{result.primary_goal_id}"],
            )
            await self.trace_store._save_trace(trace)
            await self.trace_store.link_to_user(user_id, trace.trace_id)
            await self.trace_store._save_trace(trace)
            await self.trace_store.link_to_user(user_id, trace.trace_id)
        return result

    async def get_goal_arbitration_summary(self, user_id: str) -> dict | None:
        """Return a card-ready summary when the user has multiple active goals with tension.

        Only surfaces when ≥2 goals exist AND either conflicts detected or ≥3 goals.
        """
        try:
            goals = await self.goal_arbitrator.get_active_goals(user_id)
            if len(goals) < 2:
                return None
            result = self.goal_arbitrator.arbitrate(goals)
            if not result:
                return None
            # Only show when there is genuine multi-goal tension
            if not result.conflicts and len(goals) < 3:
                return None
            title_map = {g.goal_id: g.title for g in goals}
            top_goals = sorted(
                result.priority_scores.items(), key=lambda x: x[1], reverse=True
            )[:3]
            return {
                "primary_goal_id": result.primary_goal_id,
                "primary_goal_title": title_map.get(result.primary_goal_id, ""),
                "reason": result.reason,
                "goals": [
                    {
                        "goal_id": gid,
                        "title": title_map.get(gid, gid),
                        "time_fraction": result.suggested_time_split.get(gid, 0.0),
                        "score": round(score, 3),
                    }
                    for gid, score in top_goals
                ],
                "conflicts": result.conflicts,
            }
        except Exception:
            logger.warning("get_goal_arbitration_summary: failed", exc_info=True)
            return None

    async def register_goal(
        self, user_id: str, goal_id: str, goal_type: str, title: str,
        deadline_days: int | None = None, mastery: float = 0.0,
    ) -> None:
        """v2.5: Register a new active goal."""
        from app.signals.multi_goal_arbitration import ActiveGoal
        goal = ActiveGoal(
            goal_id=goal_id,
            goal_type=goal_type,
            title=title,
            deadline_days=deadline_days,
            mastery=mastery,
        )
        await self.goal_arbitrator.register_goal(user_id, goal)

    # ── GOAL-009: Goal Drift Detection ────────────────────────────────

    async def detect_goal_drift(
        self,
        *,
        user_id: str,
        goal_id: str,
        current_goal_mode: str,
        recent_behavior: dict[str, Any],
    ) -> ActionableSignal | None:
        drift_signals: list[str] = []

        if recent_behavior.get("studying_out_of_scope"):
            drift_signals.append("studying_out_of_scope")
        if recent_behavior.get("goal_task_skip_rate", 0) > 0.6:
            drift_signals.append("high_skip_rate")
        if recent_behavior.get("mentions_different_priority"):
            drift_signals.append("different_priority_mentioned")
        if recent_behavior.get("goal_inactive_days", 0) >= 5 and recent_behavior.get("other_goal_active"):
            drift_signals.append("goal_abandoned_while_active_elsewhere")

        if not drift_signals:
            return None

        evidence_summary = ", ".join(drift_signals)
        confidence = min(0.5 + 0.1 * len(drift_signals), 0.95)

        return ActionableSignal(
            signal_id=_uid("sig"),
            source_event_ids=[],
            source_system="goal_drift_detector",
            state_key="goal_drift_suspected",
            claim="goal_drift_detected",
            confidence=confidence,
            scope=f"goal:{goal_id}",
            ttl_hours=48,
            evidence_summary=evidence_summary,
            possible_effects=["request_goal_confirmation", "suggest_goal_realignment"],
            priority="high",
        )

    # ── GoalTypeAdapter overlay for non-exam goals ────────────────────

    async def _apply_goal_type_overlay(
        self, user_id: str, directive: ExecutionDirective,
    ) -> ExecutionDirective:
        raw = await self.redis.get(f"spine:goal_type:{user_id}")
        if raw:
            goal_info = json.loads(raw if isinstance(raw, str) else raw.decode())
            goal_type = goal_info.get("goal_type", "exam")
            if goal_type != "exam":
                mapping = self.goal_type_adapter.adapt_mastery_mapping(0.5, goal_type)
                directive.hard_constraints["goal_type_task_bias"] = mapping.get("task_type", "")
                directive.hard_constraints["goal_type_label"] = mapping.get("node_label", "")
        return directive
