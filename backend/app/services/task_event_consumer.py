"""
Task 事件消费者 - 处理任务与计划相关事件，驱动认知闭环。
"""

import asyncio
import os
from uuid import UUID

from loguru import logger
from sqlalchemy import select

from app.core.cache import cache_service
from app.core.event_bus import EventBus
from app.db.session import AsyncSessionLocal
from app.models.goal import Goal
from app.models.task import Task
from app.orchestration.adaptive_replanner import AdaptiveReplanner
from app.services.behavior_signal_collector import BehaviorSignalCollector
from app.services.cognitive.auto_fragment_collector import AutoFragmentCollector
from app.services.community_signal_bridge import CommunitySignalBridge
from app.services.metacognition_service import MetacognitionService


class TaskEventConsumer:
    """消费任务 / 计划相关事件"""

    STREAM_NAME = "sparkle_events"
    GROUP_NAME = "task_event_consumer"

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._running = False
        self._subscribed = False
        self.consumer_name = f"task-{os.getpid()}"

    @staticmethod
    async def _safe_run(coro_fn, label: str, ctx_id) -> None:
        try:
            result = coro_fn()
            if asyncio.iscoroutine(result):
                await result
            elif asyncio.iscoroutinefunction(coro_fn):
                await coro_fn()
        except Exception as exc:
            logger.warning("%s failed for %s: %s", label, ctx_id, exc)

    async def start(self):
        """启动事件消费循环"""
        await self.event_bus.connect()
        if self._running:
            return
        self._running = True

        logger.info(f"TaskEventConsumer started, listening on {self.STREAM_NAME}")

        while self._running:
            try:
                if not self._subscribed:
                    await self.event_bus.subscribe(
                        stream=self.STREAM_NAME,
                        group_name=self.GROUP_NAME,
                        consumer_name=self.consumer_name,
                        callback=self.handle_event,
                    )
                    self._subscribed = True
                await asyncio.sleep(1)
            except Exception as e:
                self._subscribed = False
                logger.error(f"TaskEventConsumer error: {e}")
                await asyncio.sleep(1)

    async def handle_event(self, event: dict):
        """处理单个事件"""
        event_type = event.get("event_type")

        if event_type == "task.completed":
            await self._handle_task_completed(event)
        elif event_type == "task.abandoned":
            await self._handle_task_abandoned(event)
        elif event_type == "task.stuck":
            await self._handle_task_stuck(event)
        elif event_type == "task.feedback_submitted":
            await self._handle_task_feedback(event)
        elif event_type == "plan.replanned":
            await self._handle_plan_replanned(event)
        elif event_type == "reflection.completed":
            await self._handle_reflection_completed(event)
        elif event_type == "behavior.pattern.updated":
            await self._handle_behavior_pattern(event)
        elif event_type in {
            "focus.session.completed",
            "plan.created",
            "srl.phase.transition",
            "calendar.event.created",
            "calendar.event.updated",
            "calendar.event.deleted",
            "achievement.unlocked",
            "shop.purchase_completed",
            "notification.fatigue_detected",
        }:
            await self._handle_spine_bridge_event(event)

    async def _handle_task_completed(self, event: dict):
        """处理任务完成。"""
        try:
            user_id_raw = event.get("user_id")
            task_id_raw = event.get("task_id")
            if not user_id_raw or not task_id_raw:
                logger.warning(f"Task completed event missing user_id or task_id: {event}")
                return
            user_id = UUID(str(user_id_raw))
            task_id = UUID(str(task_id_raw))
            estimated = event.get("estimated_minutes", 0)
            actual = event.get("actual_minutes", 0)
            completion_rate = event.get("completion_rate")
            if completion_rate is None:
                completion_rate = actual / estimated if estimated > 0 else 1.0

            async def _signal_collection():
                async with AsyncSessionLocal() as db:
                    collector = BehaviorSignalCollector(db, cache_service.redis, self.event_bus)
                    await collector.handle_task_completed_event(event)
                    await db.commit()

            async def _metacognition_refresh():
                async with AsyncSessionLocal() as db:
                    await MetacognitionService(db, cache_service.redis, self.event_bus).refresh_snapshot(user_id)
                    await db.commit()

            async def _community_bridge():
                async with AsyncSessionLocal() as db:
                    bridge = CommunitySignalBridge(db, cache_service.redis)
                    await bridge.handle_group_task_completed(event)
                    await db.commit()

            async def _spine_pipeline():
                from app.signals.spine_orchestrator import get_spine_orchestrator

                spine = get_spine_orchestrator(cache_service.redis)
                async with AsyncSessionLocal() as db:
                    await spine.on_task_completed(
                        user_id=str(user_id),
                        task_id=str(task_id),
                        estimated_minutes=estimated,
                        actual_minutes=actual,
                        plan_id=event.get("plan_id"),
                    )
                    await db.commit()

            async def _auto_fragment():
                async with AsyncSessionLocal() as db:
                    auto_collector = AutoFragmentCollector(db)
                    await auto_collector.collect_from_task_completion(
                        user_id=user_id,
                        task_id=task_id,
                        estimated_minutes=estimated if estimated else None,
                        actual_minutes=actual if actual else None,
                        completion_rate=completion_rate,
                        difficulty=event.get("difficulty"),
                    )
                    await db.commit()

            async def _route_history_backfill():
                await self._record_route_history_task_outcome(
                    event,
                    user_id=user_id,
                    task_id=task_id,
                    completed=True,
                )

            async def _belief_outcome_shadow():
                await self._record_belief_task_outcome(
                    event,
                    user_id=user_id,
                    completed=True,
                )

            # Run independent signal processors in parallel
            await asyncio.gather(
                self._safe_run(_signal_collection, "BehaviorSignalCollector", task_id),
                self._safe_run(_metacognition_refresh, "MetacognitionService", user_id),
                self._safe_run(_community_bridge, "CommunitySignalBridge", task_id),
                self._safe_run(
                    lambda: self._record_task_outcome(
                        user_id=str(user_id),
                        task_id=str(task_id),
                        plan_id=event.get("plan_id"),
                        completed=True,
                        actual_minutes=actual,
                        estimated_minutes=estimated,
                        completion_rate=completion_rate,
                    ),
                    "OutcomeRecording",
                    task_id,
                ),
                self._safe_run(_spine_pipeline, "SpinePipeline", task_id),
                self._safe_run(_auto_fragment, "AutoFragment", task_id),
                self._safe_run(_route_history_backfill, "RouteHistoryTaskOutcome", task_id),
                self._safe_run(_belief_outcome_shadow, "BeliefTaskOutcomeShadow", task_id),
                return_exceptions=True,
            )

            # Adaptive replanner: independent session
            plan_id = event.get("plan_id")
            if not plan_id or plan_id == "None":
                try:
                    async with AsyncSessionLocal() as db:
                        result = await db.execute(
                            select(Task.plan_id).where(
                                Task.id == task_id,
                                Task.user_id == user_id,
                            )
                        )
                        plan_id = result.scalar_one_or_none()
                        await db.commit()
                except Exception as exc:
                    logger.warning("Failed to fetch plan_id for task %s: %s", task_id, exc)

            if plan_id:
                try:
                    async with AsyncSessionLocal() as db:
                        adaptive_replanner = AdaptiveReplanner(db, cache_service.redis)
                        await adaptive_replanner.on_task_completed(
                            user_id=user_id,
                            plan_id=UUID(str(plan_id)),
                            task_id=task_id,
                            completion_rate=completion_rate,
                        )
                        await db.commit()
                except Exception as exc:
                    logger.warning("AdaptiveReplanner failed for plan %s: %s", plan_id, exc)

            # Goal progress update: independent session
            try:
                plan_uuid = UUID(str(plan_id)) if plan_id else None
                if plan_uuid:
                    async with AsyncSessionLocal() as db:
                        from sqlalchemy import func as sa_func

                        result = await db.execute(
                            select(Goal).where(Goal.plan_id == plan_uuid, Goal.user_id == user_id)
                        )
                        goal = result.scalar_one_or_none()
                        if goal:
                            total = await db.scalar(
                                select(sa_func.count(Task.id)).where(
                                    Task.plan_id == plan_uuid,
                                    Task.user_id == user_id,
                                )
                            )
                            completed = await db.scalar(
                                select(sa_func.count(Task.id)).where(
                                    Task.plan_id == plan_uuid,
                                    Task.user_id == user_id,
                                    Task.status == "completed",
                                )
                            )
                            goal.progress = (completed / total) if total and total > 0 else 0.0
                            db.add(goal)
                            await db.commit()
                            logger.debug("Updated Goal %s progress to %.2f", goal.id, goal.progress)
            except Exception as goal_exc:
                logger.warning("Failed to update goal progress: %s", goal_exc)

        except Exception as e:
            logger.error(f"Failed to handle task.completed: {e}")
            raise

    async def _handle_task_abandoned(self, event: dict):
        """处理任务放弃。"""
        try:
            user_id = event.get("user_id")
            task_id = event.get("task_id")
            plan_id_raw = event.get("plan_id")
            async with AsyncSessionLocal() as db:
                collector = BehaviorSignalCollector(db, cache_service.redis, self.event_bus)
                await collector.handle_task_abandoned_event(event)

                # Update Goal.progress when a task is abandoned
                plan_uuid = None
                if plan_id_raw and str(plan_id_raw) != "None":
                    plan_uuid = UUID(str(plan_id_raw))
                elif task_id and user_id:
                    result = await db.execute(
                        select(Task.plan_id).where(
                            Task.id == UUID(str(task_id)),
                            Task.user_id == UUID(str(user_id)),
                        )
                    )
                    plan_id_fetched = result.scalar_one_or_none()
                    if plan_id_fetched:
                        plan_uuid = UUID(str(plan_id_fetched))

                if plan_uuid and user_id:
                    try:
                        from sqlalchemy import func as sa_func

                        result = await db.execute(
                            select(Goal).where(
                                Goal.plan_id == plan_uuid,
                                Goal.user_id == UUID(str(user_id)),
                            )
                        )
                        goal = result.scalar_one_or_none()
                        if goal:
                            total = await db.scalar(
                                select(sa_func.count(Task.id)).where(
                                    Task.plan_id == plan_uuid,
                                    Task.user_id == UUID(str(user_id)),
                                )
                            )
                            completed = await db.scalar(
                                select(sa_func.count(Task.id)).where(
                                    Task.plan_id == plan_uuid,
                                    Task.user_id == UUID(str(user_id)),
                                    Task.status == "completed",
                                )
                            )
                            goal.progress = (completed / total) if total and total > 0 else 0.0
                            db.add(goal)
                            await db.commit()
                            logger.debug(
                                "Updated Goal {} progress to {:.2f} after task abandoned",
                                goal.id,
                                goal.progress,
                            )
                    except Exception as goal_exc:
                        logger.warning("Failed to update goal progress on abandon: {}", goal_exc)

            # C-01-FIX: Record actual outcome (abandoned) for pending Spine directives
            if user_id:
                try:
                    await self._record_task_outcome(
                        user_id=str(user_id),
                        task_id=str(task_id) if task_id else None,
                        plan_id=event.get("plan_id"),
                        completed=False,
                        actual_minutes=event.get("actual_minutes", 0),
                        estimated_minutes=event.get("estimated_minutes", 0),
                        completion_rate=0.0,
                    )
                except Exception as outcome_exc:
                    logger.warning("Outcome recording failed for abandoned task {}: {}", task_id, outcome_exc)

            if user_id and task_id:
                try:
                    await self._record_route_history_task_outcome(
                        event,
                        user_id=UUID(str(user_id)),
                        task_id=UUID(str(task_id)),
                        completed=False,
                    )
                except Exception as route_history_exc:
                    logger.warning(
                        "Route history backfill failed for abandoned task {}: {}", task_id, route_history_exc
                    )
                try:
                    await self._record_belief_task_outcome(
                        event,
                        user_id=UUID(str(user_id)),
                        completed=False,
                    )
                except Exception as belief_exc:
                    logger.warning("Belief task outcome shadow failed for abandoned task {}: {}", task_id, belief_exc)

            if user_id:
                await self._handle_spine_bridge_event(event)
                await self._trigger_adaptive_plan_health_event(
                    event,
                    trigger="task_abandoned",
                    feedback_category="abandoned",
                    completion_rate=0.0,
                )

        except Exception as e:
            logger.error(f"Failed to handle task.abandoned: {e}")
            raise

    async def _handle_task_stuck(self, event: dict):
        """处理任务卡住 — H-01: 新增 Spine 信号。"""
        try:
            async with AsyncSessionLocal() as db:
                collector = BehaviorSignalCollector(db, cache_service.redis, self.event_bus)
                await collector.handle_task_stuck_event(event)
            await self._handle_spine_bridge_event(event)
            await self._trigger_adaptive_plan_health_event(
                event,
                trigger="task_stuck",
                feedback_category=event.get("category") or event.get("feedback_category") or "stuck",
            )
        except Exception as e:
            logger.error(f"Failed to handle task.stuck: {e}")
            raise

    async def _record_route_history_task_outcome(
        self,
        event: dict,
        *,
        user_id: UUID,
        task_id: UUID,
        completed: bool,
    ) -> None:
        from app.services.route_history_service import RouteHistoryService

        metadata = event.get("source_metadata") if isinstance(event.get("source_metadata"), dict) else {}
        route_history_decision_id = event.get("route_history_decision_id") or metadata.get("route_history_decision_id")
        routing_outcome_signal_id = event.get("routing_outcome_signal_id") or metadata.get("routing_outcome_signal_id")
        routing_trace_id = event.get("routing_trace_id") or metadata.get("routing_trace_id")
        plan_id = self._coerce_uuid(event.get("plan_id"))
        outcome_signal_id = (
            f"task.completed:{task_id}:{event.get('timestamp') or ''}"
            if completed
            else f"task.abandoned:{task_id}:{event.get('timestamp') or ''}"
        )

        async with AsyncSessionLocal() as db:
            service = RouteHistoryService(db)
            if completed:
                updated = await service.record_task_completion_for_event(
                    user_id=user_id,
                    task_id=task_id,
                    plan_id=plan_id,
                    route_history_decision_id=route_history_decision_id,
                    routing_outcome_signal_id=routing_outcome_signal_id,
                    routing_trace_id=routing_trace_id,
                    outcome_signal_id=outcome_signal_id,
                )
            else:
                updated = await service.record_task_abandonment_for_event(
                    user_id=user_id,
                    task_id=task_id,
                    plan_id=plan_id,
                    route_history_decision_id=route_history_decision_id,
                    routing_outcome_signal_id=routing_outcome_signal_id,
                    routing_trace_id=routing_trace_id,
                    outcome_signal_id=outcome_signal_id,
                )
            if updated is None:
                logger.debug("No route history decision matched task outcome: task={} completed={}", task_id, completed)

    async def _record_belief_task_outcome(
        self,
        event: dict,
        *,
        user_id: UUID,
        completed: bool,
    ) -> dict | None:
        from app.services.evidence import FusionEngine, RoutingRewardModel, build_task_outcome_evidence

        if not cache_service.redis:
            return None
        evidence_items = build_task_outcome_evidence(event, completed=completed)
        if not evidence_items:
            return None
        metadata = event.get("source_metadata") if isinstance(event.get("source_metadata"), dict) else {}
        actual_router_mode = event.get("actual_router_mode") or metadata.get("actual_router_mode")
        action_type = "task_completed" if completed else "task_abandoned"
        engine = FusionEngine(str(user_id))
        reward = RoutingRewardModel.from_task_outcome(event, completed=completed)
        match = {
            "routing_trace_id": event.get("routing_trace_id") or metadata.get("routing_trace_id"),
            "route_history_decision_id": event.get("route_history_decision_id")
            or metadata.get("route_history_decision_id"),
            "routing_outcome_signal_id": event.get("routing_outcome_signal_id")
            or metadata.get("routing_outcome_signal_id"),
            "task_id": event.get("task_id"),
            "plan_id": event.get("plan_id"),
        }
        bound_trace = await engine.bind_outcome_to_recent_trace(
            cache_service.redis,
            user_id=str(user_id),
            outcome=reward.outcome_label,
            reward=reward,
            match=match,
        )
        binding_diagnostics = None
        if bound_trace is None:
            binding_diagnostics = await engine.diagnose_outcome_binding(
                cache_service.redis,
                user_id=str(user_id),
                match=match,
            )
        belief_state = await engine.update_user_state(
            cache_service.redis,
            user_id=str(user_id),
            evidence_items=evidence_items,
        )
        if bound_trace is not None:
            return bound_trace
        trace = engine.generate_rl_trace(
            belief_state,
            action_taken={
                "source": "task_event_consumer",
                "action_type": action_type,
                "task_id": event.get("task_id"),
                "plan_id": event.get("plan_id"),
                "mode": actual_router_mode,
            },
            actual_router_mode=str(actual_router_mode) if actual_router_mode else None,
            router_snapshot={
                "source": "task_outcome_shadow",
                "event_type": event.get("event_type"),
                "task_id": event.get("task_id"),
                "plan_id": event.get("plan_id"),
                "actual_router_mode": actual_router_mode,
                "route_history_decision_id": event.get("route_history_decision_id")
                or metadata.get("route_history_decision_id"),
                "routing_trace_id": event.get("routing_trace_id") or metadata.get("routing_trace_id"),
            },
            outcome=reward.outcome_label,
            reward=reward,
            reward_proxy={
                "task_completed": completed,
                "completion_rate": event.get("completion_rate") if completed else 0.0,
            },
            cost_proxy={
                "abandoned": not completed,
                "time_spent": event.get("actual_minutes") or event.get("time_spent"),
                "estimated_minutes": event.get("estimated_minutes"),
            },
            evidence_metadata_summary=engine.summarize_evidence_metadata(evidence_items),
            training_eligible=False,
        )
        trace["outcome_binding_status"] = "unmatched_outcome_event_post_state_trace"
        trace["outcome_binding_diagnostics"] = binding_diagnostics or {}
        await engine.append_trace(cache_service.redis, user_id=str(user_id), trace=trace)
        return trace

    async def _record_belief_task_feedback(self, event: dict, *, user_id: UUID) -> dict | None:
        from app.services.evidence import FusionEngine, RoutingRewardModel, build_task_feedback_evidence

        if not cache_service.redis:
            return None
        evidence_items = build_task_feedback_evidence(event)
        if not evidence_items:
            return None
        metadata = event.get("source_metadata") if isinstance(event.get("source_metadata"), dict) else {}
        actual_router_mode = event.get("actual_router_mode") or metadata.get("actual_router_mode")
        engine = FusionEngine(str(user_id))
        reward = RoutingRewardModel.from_task_feedback(event)
        match = {
            "routing_trace_id": event.get("routing_trace_id") or metadata.get("routing_trace_id"),
            "route_history_decision_id": event.get("route_history_decision_id")
            or metadata.get("route_history_decision_id"),
            "routing_outcome_signal_id": event.get("routing_outcome_signal_id")
            or metadata.get("routing_outcome_signal_id"),
            "task_id": event.get("task_id"),
            "plan_id": event.get("plan_id"),
        }
        bound_trace = None
        if reward is not None:
            bound_trace = await engine.bind_outcome_to_recent_trace(
                cache_service.redis,
                user_id=str(user_id),
                outcome=reward.outcome_label,
                reward=reward,
                match=match,
            )
        binding_diagnostics = None
        if bound_trace is None:
            binding_diagnostics = await engine.diagnose_outcome_binding(
                cache_service.redis,
                user_id=str(user_id),
                match=match,
            )
        belief_state = await engine.update_user_state(
            cache_service.redis,
            user_id=str(user_id),
            evidence_items=evidence_items,
        )
        if bound_trace is not None:
            return bound_trace
        trace = engine.generate_rl_trace(
            belief_state,
            action_taken={
                "source": "task_event_consumer",
                "action_type": "task_feedback",
                "task_id": event.get("task_id"),
                "plan_id": event.get("plan_id"),
                "mode": actual_router_mode,
            },
            actual_router_mode=str(actual_router_mode) if actual_router_mode else None,
            router_snapshot={
                "source": "task_feedback_shadow",
                "event_type": event.get("event_type"),
                "feedback_category": event.get("category") or event.get("feedback_category"),
                "actual_router_mode": actual_router_mode,
            },
            outcome=reward.outcome_label if reward else "task_feedback",
            reward=reward,
            cost_proxy={"feedback_category": event.get("category") or event.get("feedback_category")},
            evidence_metadata_summary=engine.summarize_evidence_metadata(evidence_items),
            training_eligible=False,
        )
        trace["outcome_binding_status"] = "unmatched_feedback_event_post_state_trace"
        trace["outcome_binding_diagnostics"] = binding_diagnostics or {}
        await engine.append_trace(cache_service.redis, user_id=str(user_id), trace=trace)
        return trace

    @staticmethod
    def _coerce_uuid(value) -> UUID | None:
        raw = str(value or "").strip()
        if not raw or raw == "None":
            return None
        try:
            return UUID(raw)
        except (TypeError, ValueError, AttributeError):
            return None

    async def _handle_task_feedback(self, event: dict):
        try:
            async with AsyncSessionLocal() as db:
                collector = BehaviorSignalCollector(db, cache_service.redis, self.event_bus)
                await collector.handle_task_feedback_event(event)

                user_id_raw = event.get("user_id")
                task_id_raw = event.get("task_id")
                if not user_id_raw or not task_id_raw:
                    return

                user_id = UUID(str(user_id_raw))
                task_id = UUID(str(task_id_raw))
                plan_id = event.get("plan_id")
                if not plan_id or plan_id == "None":
                    result = await db.execute(
                        select(Task.plan_id).where(
                            Task.id == task_id,
                            Task.user_id == user_id,
                        )
                    )
                    plan_id = result.scalar_one_or_none()

                if not plan_id:
                    return

                adaptive_replanner = AdaptiveReplanner(db, cache_service.redis)
                await adaptive_replanner.on_task_feedback(
                    user_id=user_id,
                    plan_id=UUID(str(plan_id)),
                    task_id=task_id,
                    category=event.get("category") or event.get("feedback_category"),
                    difficulty_delta=event.get("difficulty_delta"),
                    feedback_text=event.get("feedback_text") or event.get("feedback"),
                )
                await self._record_belief_task_feedback(event, user_id=user_id)

                # Signal-to-Action Spine: quiz accuracy check on feedback
                try:
                    quiz_accuracy = event.get("quiz_accuracy")
                    if quiz_accuracy is not None:
                        from app.signals.spine_orchestrator import get_spine_orchestrator

                        spine = get_spine_orchestrator(cache_service.redis)
                        await spine.on_quiz_result(
                            user_id=str(user_id),
                            task_id=str(task_id),
                            quiz_accuracy=float(quiz_accuracy),
                            linked_node_ids=event.get("linked_node_ids"),
                        )
                except Exception as spine_exc:
                    logger.debug("Spine on_quiz_result skipped: {}", spine_exc)
        except Exception as e:
            logger.error(f"Failed to handle task.feedback_submitted: {e}")
            raise

    async def _handle_plan_replanned(self, event: dict):
        try:
            async with AsyncSessionLocal() as db:
                collector = BehaviorSignalCollector(db, cache_service.redis, self.event_bus)
                await collector.handle_plan_replanned_event(event)
        except Exception as e:
            logger.error(f"Failed to handle plan.replanned: {e}")
            raise

    async def _handle_behavior_pattern(self, event: dict):
        try:
            async with AsyncSessionLocal() as db:
                collector = BehaviorSignalCollector(db, cache_service.redis, self.event_bus)
                await collector.handle_behavior_pattern_event(event)
        except Exception as e:
            logger.error(f"Failed to handle behavior.pattern.updated: {e}")
            raise

    async def _handle_spine_bridge_event(self, event: dict) -> None:
        try:
            from app.services.spine_event_bridge import SpineEventBridge

            await SpineEventBridge(cache_service.redis).handle_event(event)
        except Exception as e:
            logger.warning("Spine event bridge failed for {}: {}", event.get("event_type"), e)
            raise

    async def _trigger_adaptive_plan_health_event(
        self,
        event: dict,
        *,
        trigger: str,
        feedback_category: str | None = None,
        completion_rate: float | None = None,
    ) -> None:
        """Route live negative execution signals into AdaptiveReplanner."""
        user_id_raw = event.get("user_id")
        if not user_id_raw:
            return

        task_id_raw = event.get("task_id")
        plan_id_raw = event.get("plan_id")
        try:
            user_id = UUID(str(user_id_raw))
            task_id = UUID(str(task_id_raw)) if task_id_raw else None
        except (TypeError, ValueError):
            logger.warning("Adaptive replanner skipped invalid event ids: {}", event)
            return

        async with AsyncSessionLocal() as db:
            plan_id = plan_id_raw
            if (not plan_id or plan_id == "None") and task_id:
                result = await db.execute(
                    select(Task.plan_id).where(
                        Task.id == task_id,
                        Task.user_id == user_id,
                    )
                )
                plan_id = result.scalar_one_or_none()

            if not plan_id or plan_id == "None":
                logger.debug("Adaptive replanner skipped {} because plan_id was missing", trigger)
                return

            try:
                replanner = AdaptiveReplanner(db, cache_service.redis)
                await replanner.evaluate_plan_health_now(
                    user_id=user_id,
                    plan_id=UUID(str(plan_id)),
                    trigger=trigger,
                    task_id=task_id,
                    completion_rate=completion_rate,
                    feedback_category=feedback_category,
                )
            except (TypeError, ValueError) as exc:
                logger.warning("Adaptive replanner skipped {} due to invalid plan id: {}", trigger, exc)
            except Exception as exc:
                logger.warning("Adaptive replanner failed for {}: {}", trigger, exc)

    async def _record_task_outcome(
        self,
        *,
        user_id: str,
        task_id: str | None,
        plan_id: str | None,
        completed: bool,
        actual_minutes: int | float,
        estimated_minutes: int | float,
        completion_rate: float,
    ) -> None:
        """Record actual outcome for the most recent pending Spine directive."""
        from app.signals.outcome_tracker import OutcomeTracker

        actual = {
            "task_id": task_id,
            "plan_id": plan_id,
            "completed": completed,
            "started": True,
            "actual_duration_min": actual_minutes,
            "estimated_duration_min": estimated_minutes,
            "completion_rate": completion_rate,
        }
        if not completed:
            actual["user_responded"] = False
            actual["behavior_changed"] = False

        tracker = OutcomeTracker(cache_service.redis)
        await tracker.record_actual_for_user(
            user_id=user_id,
            actual_outcome=actual,
            exclude_context={"task_id": task_id},
        )

    async def _handle_reflection_completed(self, event: dict) -> None:
        """Wire reflection → adapt: trigger plan re-evaluation after user reflects."""
        user_id = event.get("user_id")
        plan_id = event.get("plan_id")
        if not user_id or not plan_id or plan_id == "None":
            return
        try:
            async with AsyncSessionLocal() as db:
                replanner = AdaptiveReplanner(db, cache_service.redis)
                await replanner.evaluate_plan_health_now(
                    user_id=UUID(user_id),
                    plan_id=UUID(plan_id),
                    trigger="reflection_completed",
                )
                logger.info("Triggered adaptation after reflection: plan_id={}", plan_id)
        except Exception as exc:
            logger.warning("reflection→adapt failed for plan {}: {}", plan_id, exc)
            raise

    def stop(self):
        """停止消费者"""
        self._running = False
