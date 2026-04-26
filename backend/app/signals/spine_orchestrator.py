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
from app.signals.directive_applier import DirectiveApplier, DirectiveAuditor
from app.signals.policy_engine import PolicyEngine
from app.signals.task_timeout_detector import TaskTimeoutDetector
from app.signals.achievement_reinforcement import AchievementReinforcementConsumer
from app.signals.recall_opportunity import RecallOpportunityDetector
from app.signals.signal_ranker import SignalRanker
from app.signals.state_register import StateRegister
from app.signals.exam_rescue_detector import ExamRescueDetector
from app.signals.stale_state_guard import StaleStateGuard
from app.signals.state_packet_builder import ActionableStatePacketBuilder
from app.signals.self_model import SparkleSelfModelService
from app.signals.community_signal import CommunitySignalDetector
from app.signals.predicted_reply_options import SpineReplyOptionEngine
from app.signals.aurora_wake import AuroraWakeJudge
from app.signals.types import (
    ActionableSignal,
    CausalTrace,
    DirectiveApplicationAudit,
    ExecutionDirective,
    PolicyDecision,
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
        self.policy_engine = PolicyEngine()
        self.achievement_consumer = AchievementReinforcementConsumer()
        self.recall_detector = RecallOpportunityDetector()
        self.exam_rescue = ExamRescueDetector()
        self.stale_guard = StaleStateGuard()
        self.state_packet_builder = ActionableStatePacketBuilder()
        self.self_model = SparkleSelfModelService(redis_client)
        self.community_detector = CommunitySignalDetector()
        self.reply_engine = SpineReplyOptionEngine()
        self.wake_judge = AuroraWakeJudge()
        self.signal_ranker = SignalRanker()
        self.state_register = StateRegister(redis_client)

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

        # Layer 4: Persist signal state to StateRegister
        await self.state_register.upsert_from_signal(user_id, signal)

        # Step 3: PolicyEngine
        consecutive = await self.timeout_detector._get_consecutive_timeouts(user_id)
        result = await self.policy_engine.evaluate(signal, context={"consecutive": consecutive})

        if result is None:
            trace.outcome_to_measure = ["signal_no_rule_match"]
            await self.trace_store._save_trace(trace)
            return trace

        decision, directive = result

        # Step 3b: 链接到 trace
        await self.trace_store.append_policy(trace.trace_id, decision)
        await self.trace_store.append_directive(trace.trace_id, directive)

        # Step 4: 存储 active directive 供 task_generator 消费
        await self.trace_store.set_active_directive(user_id, directive)

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
            trace = await self.trace_store.get_trace(trace.trace_id) or trace
            # 将 receipt 挂到用户维度，方便前端拉取
            import json
            receipt_key = f"spine:receipt:{user_id}:latest"
            await self.redis.set(
                receipt_key,
                json.dumps(receipt.to_dict()),
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
    ) -> tuple[dict[str, Any], DirectiveApplicationAudit | None]:
        """
        供 planning_workflow 调用——将 directive 约束应用到任务 spec，并审计。
        """
        directive = await self.get_active_directive(user_id)
        if not directive:
            return task_spec, None

        modified_spec = DirectiveApplier.apply_to_task_spec(
            directive=directive,
            task_spec=task_spec,
        )
        audit = DirectiveAuditor.audit(
            directive=directive,
            generated_task=modified_spec,
        )

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
        """供前端调用——获取最新的 Receipt。"""
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

    # ── Generic signal pipeline (shared by all P1 sources) ─────────────

    async def _run_signal_pipeline(
        self,
        *,
        user_id: str,
        signal: ActionableSignal,
        event_ids: list[str] | None = None,
    ) -> CausalTrace | None:
        """通用 Signal → PolicyEngine → Directive → Trace 链路。"""
        import json

        trace = await self.trace_store.create_trace()
        if event_ids:
            trace.raw_event_ids.extend(event_ids)
        await self.trace_store.link_to_user(user_id, trace.trace_id)

        await self.trace_store.store_signal(signal)
        await self.trace_store.append_signal(trace.trace_id, signal)

        # Layer 4: Persist signal state to StateRegister
        await self.state_register.upsert_from_signal(user_id, signal)

        result = await self.policy_engine.evaluate(signal)
        if result is None:
            trace.outcome_to_measure = ["signal_no_rule_match"]
            await self.trace_store._save_trace(trace)
            return trace

        decision, directive = result
        await self.trace_store.append_policy(trace.trace_id, decision)
        await self.trace_store.append_directive(trace.trace_id, directive)

        if decision.visibility == "receipt":
            receipt = UserVisibleReceipt(
                receipt_id=_uid("rcpt"),
                receipt_type="strategy_adjustment",
                message=directive.user_visible_reason,
                actions=["confirm", "correct", "dismiss"],
                related_state_keys=[signal.state_key],
            )
            await self.trace_store.append_receipt(trace.trace_id, receipt)
            await self.redis.set(
                f"spine:receipt:{user_id}:latest",
                json.dumps(receipt.to_dict()),
                ex=72 * 3600,
            )

        trace.outcome_to_measure = [
            "user_response",
            "behavioral_change",
        ]
        await self.trace_store._save_trace(trace)

        logger.info(
            "Spine P1 pipeline: trace={} signal={} policy={}",
            trace.trace_id, signal.signal_id,
            decision.policy_decision_id,
        )
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
        """用户返回 → StaleStateGuard 检测 → trace。"""
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
    ) -> CausalTrace | None:
        """社群资料推荐 → CommunitySignalDetector → PolicyEngine → trace。"""
        rec = self.community_detector.detect_shared_resource(
            resource_id=resource_id,
            resource_title=resource_title,
            subject=subject,
            recommendation_reason="highly_rated_by_cohort",
            peer_count=peer_count,
            relevance_score=relevance_score,
        )
        if rec is None:
            return None

        signal = self.community_detector.to_actionable_signal(rec)
        return await self._run_signal_pipeline(
            user_id=user_id,
            signal=signal,
            event_ids=["community_shared_resource"],
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
