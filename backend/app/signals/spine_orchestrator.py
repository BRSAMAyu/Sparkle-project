"""
Core: execution
Phase: sense→clarify→plan→execute→reflect
Stage: Signal-to-Action Spine M1 — 全链路编排

Spine Orchestrator — 编排完整的 Signal→State→Decision→Directive→Audit→Receipt→Trace 链路。
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.signals.causal_trace_store import CausalTraceStore
from app.signals.core_session import CoreSession, CoreSessionManager
from app.signals.directive_applier import DirectiveApplier, DirectiveAuditor
from app.signals.policy_engine import PolicyEngine
from app.signals.task_timeout_detector import TaskTimeoutDetector
from app.signals.achievement_reinforcement import AchievementReinforcementConsumer
from app.signals.recall_opportunity import RecallOpportunityDetector
from app.signals.recall_notification import RecallMessage, RecallNotificationBuilder
from app.signals.signal_ranker import SignalRanker
from app.signals.state_register import StateRegister
from app.signals.exam_rescue_detector import ExamRescueDetector
from app.signals.stale_state_guard import StaleStateGuard
from app.signals.state_packet_builder import ActionableStatePacketBuilder
from app.signals.self_model import SparkleSelfModelService
from app.signals.community_signal import CommunitySignalDetector
from app.signals.community_loops import CommunityLoopManager
from app.signals.predicted_reply_options import SpineReplyOptionEngine
from app.signals.aurora_wake import AuroraWakeJudge
from app.signals.outcome_recorder import OutcomeRecorder
from app.signals.spine_metrics import SpineMetricsCollector
from app.signals.exam_sprint_policy import ExamSprintPolicyService
from app.signals.skill_lifecycle import SkillLifecycleManager
from app.signals.policy_analytics import PolicyAnalytics
from app.signals.policy_experiments import PolicyExperimentManager
from app.signals.learning_base import LearningBase
from app.signals.growth_chronicle import GrowthChronicleService
from app.signals.relationship_model import RelationshipModelService
from app.signals.skill_extraction import SkillExtractionService
from app.signals.goal_type_adapter import GoalTypeAdapter
from app.signals.material_signal import MaterialSignalDetector
from app.signals.timeline_card_renderer import TimelineCardRenderer
from app.signals.source_tray_integration import SourceEffectivenessTracker
from app.signals.goal_world_graph import GoalWorldGraphService
from app.signals.multi_goal_arbitration import MultiGoalArbitrator
from app.signals.types import (
    ActionableSignal,
    CausalTrace,
    CommunityDirective,
    DirectiveApplicationAudit,
    ModelWriteDirective,
    NotificationDirective,
    ExecutionDirective,
    PlanDirective,
    PolicyDecision,
    ResponseDirective,
    RetrievalDirective,
    SkillDirective,
    SkillEntry,
    UXDirective,
    UserVisibleReceipt,
    _uid,
)


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
        self.timeout_detector = TaskTimeoutDetector(redis_client)
        self.achievement_consumer = AchievementReinforcementConsumer()
        self.recall_detector = RecallOpportunityDetector()
        self.recall_notification_builder = RecallNotificationBuilder()
        self.exam_rescue = ExamRescueDetector()
        self.stale_guard = StaleStateGuard()
        self.state_packet_builder = ActionableStatePacketBuilder()
        self.self_model = SparkleSelfModelService(redis_client)
        self.community_detector = CommunitySignalDetector()
        self.community_loops = CommunityLoopManager()
        self.reply_engine = SpineReplyOptionEngine()
        self.wake_judge = AuroraWakeJudge()
        self.signal_ranker = SignalRanker()
        self.state_register = StateRegister(redis_client)
        self.outcome_recorder = OutcomeRecorder(redis_client)
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
        self.skill_extraction = SkillExtractionService()
        self.goal_type_adapter = GoalTypeAdapter()
        self.material_signal_detector = MaterialSignalDetector(redis_client)
        self.timeline_renderer = TimelineCardRenderer()
        self.source_effectiveness = SourceEffectivenessTracker(redis_client)
        self.goal_graph = GoalWorldGraphService(redis_client)
        self.goal_arbitrator = MultiGoalArbitrator(redis_client)

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

        Returns:
            CausalTrace if signal was generated and policy applied, None otherwise.
        """
        # Step 1: 创建 trace 骨架
        trace = await self.trace_store.create_trace()
        trace.raw_event_ids.append(task_id)
        await self.trace_store.link_to_user(user_id, trace.trace_id)
        await self.trace_store._save_trace(trace)

        # Step 2: 固定规则检测
        signal = await self.timeout_detector.on_task_completed(
            user_id=user_id,
            task_id=task_id,
            estimated_minutes=estimated_minutes,
            actual_minutes=actual_minutes,
            plan_id=plan_id,
        )

        if signal is None:
            # 无信号 — trace 记录了事件但无后续动作
            trace.outcome_to_measure = ["task_completed_normally"]
            await self.trace_store._save_trace(trace)
            return trace

        # Step 2b: 存储 signal 并链接到 trace
        await self.trace_store.store_signal(signal)
        await self.trace_store.append_signal(trace.trace_id, signal)
        trace.signal_ids.append(signal.signal_id)  # Keep local trace in sync
        await self.metrics.record_signal_generated()

        # Layer 4: Persist signal state to StateRegister
        await self.state_register.upsert_from_signal(user_id, signal)
        await self.metrics.record_signal_entered_state()

        # Step 3: PolicyEngine (with shadow learning from recent outcomes)
        consecutive = await self.timeout_detector._get_consecutive_timeouts(user_id)
        recent_effects = await self.outcome_recorder.get_recent_policy_effects(user_id, limit=10)
        result = await self.policy_engine.evaluate(
            signal,
            context={"consecutive": consecutive},
            recent_policy_effects=recent_effects,
        )
        await self.metrics.record_policy_evaluated(matched=result is not None)

        if result is None:
            trace.outcome_to_measure = ["signal_no_rule_match"]
            await self.trace_store._save_trace(trace)
            return trace

        decision, directive = result

        # Step 3b: 链接到 trace
        await self.trace_store.append_policy(trace.trace_id, decision)
        await self.trace_store.append_directive(trace.trace_id, directive)

        # Step 3c: Overlay ExamSprintPolicy constraints if user is in exam_rescue mode
        directive = await self._apply_exam_sprint_overlay(user_id, directive)

        # Step 4: 存储 active directive 供 task_generator 消费
        await self.trace_store.set_active_directive(user_id, directive)
        await self._link_directive_to_active_session(user_id, directive.directive_id)
        await self.metrics.record_directive_generated()

        # Step 4b: Build and store ResponseDirective
        response_dir = self.policy_engine.build_response_directive(decision, signal)
        if response_dir:
            await self._store_response_directive(user_id, response_dir)

        # Step 4c: Build and store NotificationDirective
        notif_dir = self.policy_engine.build_notification_directive(decision, signal)
        if notif_dir:
            await self._store_notification_directive(user_id, notif_dir)

        # Step 4c2: Build and store RetrievalDirective
        ret_dir = self.policy_engine.build_retrieval_directive(decision, signal)
        if ret_dir:
            await self._store_retrieval_directive(user_id, ret_dir)

        # Step 4d: Build and store PlanDirective
        plan_dir = self.policy_engine.build_plan_directive(decision, signal)
        if plan_dir:
            await self._store_plan_directive(user_id, plan_dir)
            trace.directive_ids.append(plan_dir.directive_id)

        # Step 4e: Build and store ModelWriteDirective
        mw_dir = self.policy_engine.build_model_write_directive(decision, signal)
        if mw_dir:
            await self._store_model_write_directive(user_id, mw_dir)
            trace.directive_ids.append(mw_dir.directive_id)
            await self._apply_model_writes(user_id, mw_dir)

        # Step 4f: Build and store UXDirective
        ux_dir = self.policy_engine.build_ux_directive(decision, signal)
        if ux_dir:
            await self._store_ux_directive(user_id, ux_dir)
            trace.directive_ids.append(ux_dir.directive_id)

        # Step 4g: Build and store CommunityDirective
        comm_dir = self.policy_engine.build_community_directive(decision, signal)
        if comm_dir:
            await self._store_community_directive(user_id, comm_dir)
            trace.directive_ids.append(comm_dir.directive_id)

        # Step 4h: Build and store SkillDirective
        skill_dir = self.policy_engine.build_skill_directive(decision, signal)
        if skill_dir:
            await self._store_skill_directive(user_id, skill_dir)
            trace.directive_ids.append(skill_dir.directive_id)

        # Step 5: 生成 Receipt（如果 visibility = "receipt"）
        if decision.visibility == "receipt":
            receipt = UserVisibleReceipt(
                receipt_id=_uid("rcpt"),
                receipt_type="strategy_adjustment",
                message=directive.user_visible_reason,
                actions=["confirm", "correct", "dismiss"],
                related_state_keys=[signal.state_key],
            )
            await self.trace_store.append_receipt(trace.trace_id, receipt)
            await self.metrics.record_receipt_shown()
            trace = await self.trace_store.get_trace(trace.trace_id) or trace
            # 将 receipt 挂到用户维度，方便前端拉取
            import json
            receipt_key = f"spine:receipt:{user_id}:latest"
            receipt_data = json.dumps(receipt.to_dict())
            await self.redis.set(receipt_key, receipt_data, ex=72 * 3600)
            # Store by receipt ID for timeline retrieval
            await self.redis.set(
                f"spine:receipt_by_id:{receipt.receipt_id}",
                receipt_data,
                ex=72 * 3600,
            )

        # Step 6: 设置 outcome_to_measure
        trace.outcome_to_measure = [
            "task_started",
            "task_completed",
            "actual_duration_min",
            "mini_quiz_accuracy",
            "user_feedback",
        ]
        await self.trace_store._save_trace(trace)

        logger.info(
            "Spine complete: trace={} signal={} policy={} directive={}",
            trace.trace_id, signal.signal_id,
            decision.policy_decision_id, directive.directive_id,
        )

        return trace

    async def get_active_directive(self, user_id: str) -> ExecutionDirective | None:
        """供 planning_workflow 调用——获取当前用户的活跃 directive。"""
        return await self.trace_store.get_active_directive(user_id)

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

        return await self._run_signal_pipeline(
            user_id=user_id,
            signal=signal,
            event_ids=[f"achievement_{achievement_id}"],
        )

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

        await self._store_notification_directive(user_id, notif_dir)
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
        except Exception:
            pass

        trace = await resilient_redis_call(
            "spine_pipeline", self.trace_store.create_trace(),
            fallback=None,
        )
        if trace is None:
            logger.warning("Spine pipeline skipped: trace creation failed for user={}", user_id)
            try:
                await self.redis.delete(lock_key)
            except Exception:
                pass
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

        result = await self.policy_engine.evaluate(
            signal,
            context={"source": "pipeline"},
            recent_policy_effects=recent_effects,
            strategy_beliefs=strategy_beliefs,
        )
        await self.metrics.record_policy_evaluated(matched=result is not None)
        if result is None:
            trace.outcome_to_measure = ["signal_no_rule_match"]
            await self.trace_store._save_trace(trace)
            try:
                await self.redis.delete(f"spine:pipeline_lock:{user_id}")
            except Exception:
                pass
            return trace

        decision, directive = result
        await self.trace_store.append_policy(trace.trace_id, decision)
        await self.trace_store.append_directive(trace.trace_id, directive)
        # Overlay ExamSprintPolicy constraints if user is in exam_rescue mode
        directive = await self._apply_exam_sprint_overlay(user_id, directive)
        await self.trace_store.set_active_directive(user_id, directive)
        await self._link_directive_to_active_session(user_id, directive.directive_id)
        trace.policy_decision_id = decision.policy_decision_id  # Keep local in sync
        trace.directive_ids.append(directive.directive_id)  # Keep local in sync
        await self.metrics.record_directive_generated()

        # Build and store ResponseDirective
        response_dir = self.policy_engine.build_response_directive(decision, signal)
        if response_dir:
            await self._store_response_directive(user_id, response_dir)

        # Build and store NotificationDirective
        notif_dir = self.policy_engine.build_notification_directive(decision, signal)
        if notif_dir:
            await self._store_notification_directive(user_id, notif_dir)

        # Build and store RetrievalDirective
        ret_dir = self.policy_engine.build_retrieval_directive(decision, signal)
        if ret_dir:
            await self._store_retrieval_directive(user_id, ret_dir)
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
                pass

        # Build and store PlanDirective
        plan_dir = self.policy_engine.build_plan_directive(decision, signal)
        if plan_dir:
            await self._store_plan_directive(user_id, plan_dir)
            trace.directive_ids.append(plan_dir.directive_id)

        # Build and store ModelWriteDirective
        mw_dir = self.policy_engine.build_model_write_directive(decision, signal)
        if mw_dir:
            await self._store_model_write_directive(user_id, mw_dir)
            trace.directive_ids.append(mw_dir.directive_id)
            await self._apply_model_writes(user_id, mw_dir)

        # Build and store UXDirective
        ux_dir = self.policy_engine.build_ux_directive(decision, signal)
        if ux_dir:
            await self._store_ux_directive(user_id, ux_dir)
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
            receipt = UserVisibleReceipt(
                receipt_id=_uid("rcpt"),
                receipt_type="strategy_adjustment",
                message=directive.user_visible_reason,
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
        except Exception:
            pass
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
            pass

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

    # ── Layer 3: Signal Ranking ────────────────────────────────────────

    def rank_signals(self, signals: list[ActionableSignal], *, max_signals: int = 5):
        """排序信号并解决冲突。返回 RankingResult。"""
        return self.signal_ranker.rank(signals, max_signals=max_signals)

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

    # ── Layer 6: ResponseDirective ─────────────────────────────────────

    async def _store_response_directive(self, user_id: str, rd: ResponseDirective) -> None:
        """存储 ResponseDirective 供 response layer 消费。"""
        import json
        key = f"spine:response_directive:{user_id}:latest"
        await self.redis.set(key, json.dumps(rd.to_dict()), ex=72 * 3600)
        await self.trace_store.store_directive_by_id(rd.directive_id, rd.to_dict())

    async def get_response_directive(self, user_id: str) -> ResponseDirective | None:
        """获取用户当前 ResponseDirective。Degraded: returns None on Redis failure."""
        try:
            import json
            raw = await self.redis.get(f"spine:response_directive:{user_id}:latest")
            if not raw:
                return None
            return ResponseDirective.from_dict(json.loads(raw))
        except Exception:
            logger.debug("get_response_directive degraded: Redis unavailable for user={}", user_id)
            return None

    async def _store_notification_directive(self, user_id: str, nd: NotificationDirective) -> None:
        """存储 NotificationDirective 供通知服务消费。"""
        import json
        key = f"spine:notification_directive:{user_id}:latest"
        await self.redis.set(key, json.dumps(nd.to_dict()), ex=72 * 3600)
        await self.trace_store.store_directive_by_id(nd.directive_id, nd.to_dict())

    async def get_notification_directive(self, user_id: str) -> NotificationDirective | None:
        """获取用户当前 NotificationDirective。Degraded: returns None on Redis failure."""
        try:
            import json
            raw = await self.redis.get(f"spine:notification_directive:{user_id}:latest")
            if not raw:
                return None
            return NotificationDirective.from_dict(json.loads(raw))
        except Exception:
            logger.debug("get_notification_directive degraded: Redis unavailable for user={}", user_id)
            return None

    async def _store_recall_message(self, user_id: str, message: RecallMessage) -> None:
        """存储用户可见 RecallMessage 供通知服务消费。"""
        import json
        key = f"spine:recall_notification:{user_id}:latest"
        await self.redis.set(key, json.dumps(message.to_dict()), ex=72 * 3600)

    async def get_recall_notification(self, user_id: str) -> RecallMessage | None:
        """获取用户当前 RecallMessage。Degraded: returns None on Redis failure."""
        try:
            import json
            raw = await self.redis.get(f"spine:recall_notification:{user_id}:latest")
            if not raw:
                return None
            return RecallMessage.from_dict(json.loads(raw))
        except Exception:
            logger.debug("get_recall_notification degraded: Redis unavailable for user={}", user_id)
            return None

    async def _store_retrieval_directive(self, user_id: str, rd: RetrievalDirective) -> None:
        import json
        key = f"spine:retrieval_directive:{user_id}:latest"
        await self.redis.set(key, json.dumps(rd.to_dict()), ex=72 * 3600)
        await self.trace_store.store_directive_by_id(rd.directive_id, rd.to_dict())

    async def get_retrieval_directive(self, user_id: str) -> RetrievalDirective | None:
        """获取用户当前 RetrievalDirective。Degraded: returns None on Redis failure."""
        try:
            import json
            raw = await self.redis.get(f"spine:retrieval_directive:{user_id}:latest")
            if not raw:
                return None
            return RetrievalDirective.from_dict(json.loads(raw))
        except Exception:
            logger.debug("get_retrieval_directive degraded: Redis unavailable for user={}", user_id)
            return None

    # ── Layer 6: PlanDirective ──────────────────────────────────────────

    async def _store_plan_directive(self, user_id: str, pd: PlanDirective) -> None:
        import json
        key = f"spine:plan_directive:{user_id}:latest"
        await self.redis.set(key, json.dumps(pd.to_dict()), ex=72 * 3600)
        await self.trace_store.store_directive_by_id(pd.directive_id, pd.to_dict())

    async def get_plan_directive(self, user_id: str) -> PlanDirective | None:
        """获取用户当前 PlanDirective。Degraded: returns None on Redis failure."""
        try:
            import json
            raw = await self.redis.get(f"spine:plan_directive:{user_id}:latest")
            if not raw:
                return None
            return PlanDirective.from_dict(json.loads(raw))
        except Exception:
            logger.debug("get_plan_directive degraded: Redis unavailable for user={}", user_id)
            return None

    # ── Layer 6: ModelWriteDirective ────────────────────────────────────

    async def _store_model_write_directive(self, user_id: str, mwd: ModelWriteDirective) -> None:
        import json
        key = f"spine:model_write_directive:{user_id}:latest"
        await self.redis.set(key, json.dumps(mwd.to_dict()), ex=72 * 3600)
        await self.trace_store.store_directive_by_id(mwd.directive_id, mwd.to_dict())

    async def get_model_write_directive(self, user_id: str) -> ModelWriteDirective | None:
        """获取用户当前 ModelWriteDirective。Degraded: returns None on Redis failure."""
        try:
            import json
            raw = await self.redis.get(f"spine:model_write_directive:{user_id}:latest")
            if not raw:
                return None
            return ModelWriteDirective.from_dict(json.loads(raw))
        except Exception:
            logger.debug("get_model_write_directive degraded: Redis unavailable for user={}", user_id)
            return None

    async def _apply_model_writes(self, user_id: str, mwd: ModelWriteDirective) -> None:
        """Apply model write claims to user state (confidence-gated, auto-apply only)."""
        import json
        for entry in mwd.writes:
            # Only auto-apply high-confidence claims that don't need user confirmation
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
                }),
                ex=self._ttl_to_seconds(entry.ttl),
            )

    @staticmethod
    def _ttl_to_seconds(ttl: str) -> int:
        """Parse TTL like '72h' to seconds."""
        if ttl.endswith("h"):
            return int(ttl[:-1]) * 3600
        if ttl.endswith("d"):
            return int(ttl[:-1]) * 86400
        return 72 * 3600  # default

    # ── Layer 6: UXDirective ────────────────────────────────────────────

    async def _store_ux_directive(self, user_id: str, uxd: UXDirective) -> None:
        import json
        key = f"spine:ux_directive:{user_id}:latest"
        await self.redis.set(key, json.dumps(uxd.to_dict()), ex=72 * 3600)
        await self.trace_store.store_directive_by_id(uxd.directive_id, uxd.to_dict())

    async def get_ux_directive(self, user_id: str) -> UXDirective | None:
        """获取用户当前 UXDirective。Degraded: returns None on Redis failure."""
        try:
            import json
            raw = await self.redis.get(f"spine:ux_directive:{user_id}:latest")
            if not raw:
                return None
            return UXDirective.from_dict(json.loads(raw))
        except Exception:
            logger.debug("get_ux_directive degraded: Redis unavailable for user={}", user_id)
            return None

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
        """Overlay ExamSprintPhase constraints onto an ExecutionDirective if in exam_rescue mode.

        Takes the stricter value for duration caps and adds phase-specific biases.
        No-ops if user is not in exam_rescue mode or deadline > 7 days.
        """
        goal_mode, days = await self._get_exam_sprint_context(user_id)
        if not ExamSprintPolicyService.should_activate(goal_mode=goal_mode, days_to_deadline=days):
            return directive

        assert days is not None  # guaranteed by should_activate
        esp = self.exam_sprint_policy.compute(days_to_deadline=days)
        phase = esp.phase

        hc = dict(directive.hard_constraints or {})
        # Duration cap: take the stricter (smaller) limit
        existing_max = hc.get("max_task_duration_min", 999)
        hc["max_task_duration_min"] = min(existing_max, phase.max_task_duration_min)
        # Chapter guard: once exam sprint says no new chapters, it cannot be relaxed
        if not phase.allow_new_chapters:
            hc["avoid_new_chapter"] = True
        if phase.prefer_high_yield_review:
            hc["prefer_high_yield"] = True
        hc["exam_sprint_task_type_bias"] = phase.task_type_bias
        hc["exam_sprint_difficulty_cap"] = phase.difficulty_cap
        hc["exam_sprint_retrieval_mode"] = phase.retrieval_mode
        hc["exam_sprint_phase_id"] = phase.phase_id
        directive.hard_constraints = hc

        # Append phase context to the user-visible reason
        prefix = f"[D-{days} · {phase.phase_id}]"
        existing = directive.user_visible_reason or ""
        if prefix not in existing:
            directive.user_visible_reason = f"{prefix} {existing}".strip()

        logger.info(
            "ExamSprintPolicy overlay applied: user={} days={} phase={} max_dur={}",
            user_id, days, phase.phase_id, hc["max_task_duration_min"],
        )
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
        import json
        key = f"spine:community_directive:{user_id}:latest"
        await self.redis.set(key, json.dumps(cd.to_dict()), ex=72 * 3600)
        await self.trace_store.store_directive_by_id(cd.directive_id, cd.to_dict())

    async def get_community_directive(self, user_id: str) -> CommunityDirective | None:
        """获取用户当前 CommunityDirective。Degraded: returns None on Redis failure."""
        try:
            import json
            raw = await self.redis.get(f"spine:community_directive:{user_id}:latest")
            if not raw:
                return None
            return CommunityDirective.from_dict(json.loads(raw))
        except Exception:
            logger.debug("get_community_directive degraded: Redis unavailable for user={}", user_id)
            return None

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
                    pass
        return None

    async def get_ux_risk_warning(self, user_id: str) -> dict[str, Any] | None:
        """Return a proactive risk warning payload for Flutter to render (divine moment #5 阻止低收益).

        Returns a dict with risk_level, reason, and suggested_action when the current
        UXDirective flags risk_detected — combining it with the active ExecutionDirective's
        user_visible_reason. Returns None if no risk is active.
        """
        import json

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
            return None

    # ── Layer 6: SkillDirective ──────────────────────────────────────────

    async def _store_skill_directive(self, user_id: str, sd: SkillDirective) -> None:
        import json
        key = f"spine:skill_directive:{user_id}:latest"
        await self.redis.set(key, json.dumps(sd.to_dict()), ex=72 * 3600)
        await self.trace_store.store_directive_by_id(sd.directive_id, sd.to_dict())

    async def get_skill_directive(self, user_id: str) -> SkillDirective | None:
        """获取用户当前 SkillDirective。Degraded: returns None on Redis failure."""
        try:
            import json
            raw = await self.redis.get(f"spine:skill_directive:{user_id}:latest")
            if not raw:
                return None
            return SkillDirective.from_dict(json.loads(raw))
        except Exception:
            logger.debug("get_skill_directive degraded: Redis unavailable for user={}", user_id)
            return None

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
            pass

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
            pass

        return record

    async def get_outcome_for_trace(self, trace_id: str):
        """获取 CausalTrace 对应的 OutcomeRecord。"""
        return await self.outcome_recorder.get_outcome_for_trace(trace_id)

    # ── Metrics ────────────────────────────────────────────────────────

    async def get_metrics_snapshot(self) -> dict[str, Any]:
        """获取 Decision Realization Score 指标快照。"""
        return await self.metrics.snapshot()

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
            pass

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
            pass

        # 2. relationship_model: update from interaction
        try:
            await self.relationship_model.update_from_interaction(
                user_id=user_id,
                interaction_type="system_proactive",
            )
        except Exception:
            pass

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
            pass

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
            pass

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
            pass

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
            pass

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
            pass

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
            return None

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
            return None

    async def build_recovery_card(
        self,
        *,
        user_id: str,
        elapsed_minutes: float,
        last_task_id: str | None = None,
        last_task_status: str | None = None,
    ) -> dict[str, Any] | None:
        """神性时刻4: 记得时间 — build recovery card for returning user."""
        import json
        try:
            recovery_card = {
                "type": "recovery_card",
                "user_id": user_id,
                "elapsed_minutes": elapsed_minutes,
                "last_task_id": last_task_id,
                "last_task_status": last_task_status,
                "options": [
                    {"label": "做完了，补记录", "value": "completed"},
                    {"label": "做了一半，卡住了", "value": "stuck"},
                    {"label": "没开始", "value": "not_started"},
                    {"label": "换个小任务", "value": "switch_task"},
                ],
            }

            if elapsed_minutes >= 120:
                recovery_card["urgency"] = "high"
                recovery_card["message"] = f"你离开了大约 {int(elapsed_minutes / 60)} 小时。"
            elif elapsed_minutes >= 60:
                recovery_card["urgency"] = "medium"
                recovery_card["message"] = f"你离开了大约 {int(elapsed_minutes)} 分钟。"
            else:
                recovery_card["urgency"] = "low"
                recovery_card["message"] = f"你离开了 {int(elapsed_minutes)} 分钟。"

            if last_task_id:
                recovery_card["message"] += f" 上一张任务卡预计完成，但还没收到反馈。"

            await self.redis.set(
                f"spine:card:recovery:{user_id}:latest",
                json.dumps(recovery_card),
                ex=24 * 3600,
            )

            return recovery_card
        except Exception:
            return None

    async def build_context_receipt(
        self,
        *,
        user_id: str,
        used_sources: list[str] | None = None,
        excluded_sources: list[str] | None = None,
        reason: str = "",
        retrieval_mode: str = "auto",
    ) -> dict[str, Any]:
        """神性时刻3: 知道不用资料 — build context receipt for current turn."""
        import json
        receipt = {
            "type": "context_receipt",
            "used": used_sources or [],
            "excluded": excluded_sources or [],
            "reason": reason,
            "retrieval_mode": retrieval_mode,
            "user_actions": [
                {"label": "按完整资料重讲", "value": "force_full_source"},
                {"label": "不要用这份资料", "value": "exclude_source"},
                {"label": "查看为什么", "value": "explain_decision"},
            ],
        }
        try:
            await self.redis.set(
                f"spine:card:context_receipt:{user_id}:latest",
                json.dumps(receipt),
                ex=2 * 3600,
            )
        except Exception:
            pass
        return receipt

    async def on_community_hint(
        self,
        *,
        user_id: str,
        knowledge_node: str,
        common_mistake: str,
        cohort_size: int,
    ) -> dict[str, Any] | None:
        """神性时刻6: 社群经验转策略 — cohort hint → directive bias."""
        import json
        try:
            hint = self.community_loops.build_cohort_mistake_hint({
                "knowledge_node_id": knowledge_node,
                "common_misconception": common_mistake,
                "cohort_size": cohort_size,
            })
            if hint is None:
                return None

            card = {
                "type": "community_hint",
                "knowledge_node": knowledge_node,
                "common_mistake": common_mistake,
                "cohort_size": cohort_size,
                "message": hint.get("hint_text", ""),
            }

            await self.redis.set(
                f"spine:card:community_hint:{user_id}:latest",
                json.dumps(card),
                ex=48 * 3600,
            )
            return card
        except Exception:
            return None

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

            # Timeline updates from recent traces
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
            pass

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
                pass

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
            pass

        return snapshot

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
            pass
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

    async def arbitrate_goals(self, user_id: str):
        """v2.5: Arbitrate between multiple active goals."""
        goals = await self.goal_arbitrator.get_active_goals(user_id)
        if not goals:
            return None
        return self.goal_arbitrator.arbitrate(goals)

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
