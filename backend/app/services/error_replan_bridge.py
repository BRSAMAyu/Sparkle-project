from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from loguru import logger
from sqlalchemy import desc, select

from app.core.metrics import (
    ERROR_REPLAN_BRIDGE_BLOCKED_BY_GATE_TOTAL,
    ERROR_REPLAN_BRIDGE_ERROR_TOTAL,
    ERROR_REPLAN_BRIDGE_EVALUATED_TOTAL,
    ERROR_REPLAN_BRIDGE_TRIGGERED_TOTAL,
)
from app.models.card_protocol import InterventionRecord
from app.models.error_book import ErrorRecord
from app.models.galaxy import UserNodeStatus
from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from app.models.task_resources import TaskKnowledgeLink
from app.models.user import User
from app.models.card_protocol import DeliveryChannel, DeliveryStrategy, InterventionTriggerType
from app.orchestration.adaptive_replanner import AdaptiveReplanner
from app.services.aurora_stage38_kill_switch_service import AuroraStage38KillSwitchService
from app.services.intervention_record_service import InterventionRecordService
from app.services.route_history_service import RouteHistoryService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class BridgeEvaluationError(RuntimeError):
    """Raised when Stage34 bridge evaluation cannot be computed safely."""


class PlanHealthError(RuntimeError):
    """Raised when AdaptiveReplanner evaluation fails for an eligible plan."""


@dataclass(frozen=True)
class ErrorPressureDecision:
    triggered: bool
    threshold: int
    recent_error_count: int


class ErrorReplanBridge:
    """Separates ErrorCreated -> immediate plan-health evaluation from mastery sync."""

    LOW_MASTERY_THRESHOLD = 50.0
    ERROR_PRESSURE_LOOKBACK_DAYS = 7
    ERROR_PRESSURE_TRIGGER_COUNT = 3
    COOLDOWN_HOURS = 24
    TRIGGERING_ERROR_TYPES = {
        "concept_confusion",
        "knowledge_gap",
        "procedural_error",
        "careless_mistake",
        "time_management",
        "strategy_mismatch",
    }

    def __init__(self, db, redis=None) -> None:
        self.db = db
        self.redis = redis

    async def on_error_created(
        self,
        *,
        user_id: UUID,
        error_id: UUID,
        linked_node_ids: list[UUID],
    ) -> dict[str, object]:
        mode = "shadow"
        try:
            mode = await AuroraStage38KillSwitchService().get_feature_mode("err_replan")
            ERROR_REPLAN_BRIDGE_EVALUATED_TOTAL.labels(mode=mode).inc()
            normalized_node_ids = [node_id for node_id in linked_node_ids if node_id]
            if not normalized_node_ids:
                return self._blocked(mode=mode, gate="no_linked_nodes")

            error = await self.db.get(ErrorRecord, error_id)
            if error is None or error.user_id != user_id:
                return self._blocked(mode=mode, gate="error_not_found")

            error_type = self._classify_trigger_type(error)
            if error_type is None:
                return self._blocked(
                    mode=mode,
                    gate="unsupported_error_type",
                    reason=f"unsupported_error_type:{self._extract_error_type(error)}",
                )

            plan_ids = await self._find_relevant_active_plan_ids(user_id=user_id, node_ids=normalized_node_ids)
            if not plan_ids:
                return self._blocked(mode=mode, gate="no_relevant_active_plan")

            eligible_plan_ids = await self._filter_plan_ids_by_cooldown(
                user_id=user_id,
                plan_ids=plan_ids,
                error_type=error_type,
            )
            if not eligible_plan_ids:
                return self._blocked(mode=mode, gate="trigger_cooldown_active")

            low_mastery_nodes = await self._find_low_mastery_nodes(user_id=user_id, node_ids=normalized_node_ids)
            if not low_mastery_nodes:
                return self._blocked(mode=mode, gate="mastery_not_low")

            try:
                is_new_user = await self._is_new_user(user_id)
                recent_error_count = await self._count_recent_triggering_errors(
                    user_id=user_id,
                    node_ids=low_mastery_nodes,
                    days=self.ERROR_PRESSURE_LOOKBACK_DAYS,
                )
            except Exception as exc:
                raise BridgeEvaluationError("stage34_bridge_evaluation_failed") from exc

            legacy_decision = ErrorPressureDecision(
                triggered=recent_error_count >= self.ERROR_PRESSURE_TRIGGER_COUNT,
                threshold=self.ERROR_PRESSURE_TRIGGER_COUNT,
                recent_error_count=recent_error_count,
            )
            stage34_threshold = 1 if is_new_user else self.ERROR_PRESSURE_TRIGGER_COUNT
            stage34_decision = ErrorPressureDecision(
                triggered=recent_error_count >= stage34_threshold,
                threshold=stage34_threshold,
                recent_error_count=recent_error_count,
            )

            if mode == "shadow":
                await self._record_shadow_decision(
                    user_id=user_id,
                    error_id=error_id,
                    error_type=error_type,
                    plan_ids=eligible_plan_ids,
                    is_new_user=is_new_user,
                    legacy_decision=legacy_decision,
                    stage34_decision=stage34_decision,
                )
                effective_decision = legacy_decision
            elif mode == "live":
                effective_decision = stage34_decision
            else:
                effective_decision = legacy_decision

            if not effective_decision.triggered:
                return self._blocked(
                    mode=mode,
                    gate="insufficient_error_pressure",
                    plan_ids=[],
                    recent_error_count=recent_error_count,
                    threshold_applied=effective_decision.threshold,
                    is_new_user=is_new_user,
                )

            replanner = AdaptiveReplanner(self.db, self.redis)
            triggered_plan_ids: list[str] = []
            for plan_id in sorted(eligible_plan_ids, key=str):
                try:
                    await replanner.evaluate_plan_health_now(
                        user_id=user_id,
                        plan_id=plan_id,
                        trigger="error_created_bridge",
                        feedback_category="concept_gap_repeated",
                    )
                except Exception as exc:
                    raise PlanHealthError(f"plan_health_eval_failed:{plan_id}") from exc
                triggered_plan_ids.append(str(plan_id))

            intervention_id = await self._create_error_intervention_record(
                user_id=user_id,
                low_mastery_nodes=low_mastery_nodes,
                recent_error_count=recent_error_count,
                plan_ids=triggered_plan_ids,
                error_type=error_type,
            )

            await self._notify_plan_adjusted(
                user_id=user_id,
                low_mastery_nodes=low_mastery_nodes,
                recent_error_count=recent_error_count,
                intervention_id=intervention_id,
            )

            logger.info(
                "ErrorReplanBridge: triggered immediate plan-health evaluation for user={} error={} plans={} count={} mode={} threshold={}",
                user_id,
                error_id,
                len(triggered_plan_ids),
                recent_error_count,
                mode,
                effective_decision.threshold,
            )
            ERROR_REPLAN_BRIDGE_TRIGGERED_TOTAL.labels(mode=mode).inc()
            return {
                "triggered": True,
                "reason": "error_pressure_bridge",
                "plan_ids": triggered_plan_ids,
                "recent_error_count": recent_error_count,
                "threshold_applied": effective_decision.threshold,
                "is_new_user": is_new_user,
                "mode": mode,
            }
        except BridgeEvaluationError as exc:
            ERROR_REPLAN_BRIDGE_ERROR_TOTAL.labels(category="BridgeEvaluationError", mode=mode).inc()
            logger.warning("ErrorReplanBridge evaluation failed for user {}: {}", user_id, exc)
            await self._notify_bridge_failure(user_id=user_id, category="BridgeEvaluationError", error=str(exc))
            return {"triggered": False, "reason": "bridge_evaluation_error", "plan_ids": []}
        except PlanHealthError as exc:
            ERROR_REPLAN_BRIDGE_ERROR_TOTAL.labels(category="PlanHealthError", mode=mode).inc()
            logger.warning("ErrorReplanBridge plan-health evaluation failed for user {}: {}", user_id, exc)
            await self._notify_bridge_failure(user_id=user_id, category="PlanHealthError", error=str(exc))
            return {"triggered": False, "reason": "plan_health_error", "plan_ids": []}
        except Exception as exc:
            ERROR_REPLAN_BRIDGE_ERROR_TOTAL.labels(category="UnknownError", mode=mode).inc()
            logger.exception("ErrorReplanBridge unknown failure for user {}", user_id)
            await self._notify_bridge_failure(user_id=user_id, category="UnknownError", error=str(exc))
            return {"triggered": False, "reason": "unknown_error", "plan_ids": []}

    async def _create_error_intervention_record(
        self,
        *,
        user_id: UUID,
        low_mastery_nodes: list[UUID],
        recent_error_count: int,
        plan_ids: list[str],
        error_type: str,
    ) -> str | None:
        try:
            node_name = await self._resolve_node_name(low_mastery_nodes)
            cohort_profile = await self._get_cohort_profile(user_id)
            record = await InterventionRecordService(self.db).create_record(
                user_id=user_id,
                trigger_type=InterventionTriggerType.CONCEPT_GAP,
                delivery_strategy=DeliveryStrategy.SUPPORTIVE,
                delivery_channel=DeliveryChannel.CHAT,
                trigger_source_ref="error_replan_bridge",
                diagnosis_payload={
                    "node_ids": [str(node_id) for node_id in low_mastery_nodes],
                    "node_name": node_name,
                    "recent_error_count": recent_error_count,
                    "plan_ids": plan_ids,
                    "error_type": error_type,
                    "cohort_profile": cohort_profile or {},
                    "trigger": "error_replan_bridge",
                },
                outcome_window_days=14,
            )
            await self.db.flush()
            return str(record.id)
        except Exception as exc:
            logger.warning("ErrorReplanBridge: failed to create intervention record: {}", exc)
            return None

    async def _notify_plan_adjusted(
        self,
        *,
        user_id: UUID,
        low_mastery_nodes: list[UUID],
        recent_error_count: int,
        intervention_id: str | None = None,
    ) -> None:
        """Emit a system update so the user sees the plan was adjusted due to errors."""
        try:
            from app.services.system_update_service import SystemUpdateService, build_system_update

            node_name = await self._resolve_node_name(low_mastery_nodes)

            description = (
                f"我注意到你在「{node_name}」上遇到了{recent_error_count}次相似的问题，"
                "已经调整了本周计划，把相关任务移到了更早的时间段。"
                if node_name
                else f"你最近在同一知识点上遇到了{recent_error_count}次问题，我已经微调了本周计划。"
            )

            await SystemUpdateService(self.redis).enqueue(
                user_id,
                build_system_update(
                    update_type="plan_adjusted_from_error",
                    category="evolution",
                    title="计划已根据你的错题调整",
                    description=description,
                    priority="normal",
                    metadata={
                        "evolution_kind": "adjustment",
                        "node_name": node_name,
                        "error_count": recent_error_count,
                        "trigger": "error_replan_bridge",
                        "intervention_id": intervention_id,
                    },
                ),
            )
        except Exception as exc:
            logger.warning("ErrorReplanBridge: failed to enqueue plan_adjusted system update: {}", exc)

    async def _notify_bridge_failure(
        self,
        *,
        user_id: UUID,
        category: str,
        error: str,
    ) -> None:
        try:
            from app.services.system_update_service import SystemUpdateService, build_system_update

            await SystemUpdateService(self.redis).enqueue(
                user_id,
                build_system_update(
                    update_type="error_bridge_failure",
                    category="system",
                    title="计划校准暂时未完成",
                    description="系统识别到了新的错题压力信号，但这次自动校准没有完整执行，稍后会继续重试。",
                    priority="medium",
                    metadata={
                        "trigger": "error_replan_bridge",
                        "error_category": category,
                        "error": error,
                    },
                ),
            )
        except Exception as exc:
            logger.warning("ErrorReplanBridge: failed to enqueue failure update: {}", exc)

    async def _record_shadow_decision(
        self,
        *,
        user_id: UUID,
        error_id: UUID,
        error_type: str,
        plan_ids: set[UUID],
        is_new_user: bool,
        legacy_decision: ErrorPressureDecision,
        stage34_decision: ErrorPressureDecision,
    ) -> None:
        await RouteHistoryService(self.db).record_decision(
            user_id=user_id,
            input_aggregator_snapshot_id="stage38:error_replan_bridge",
            decision_type="stage38_error_replan_bridge_shadow",
            decision_payload={
                "trigger": "error_created_bridge",
                "error_id": str(error_id),
                "error_type": error_type,
                "is_new_user": is_new_user,
                "legacy_threshold": legacy_decision.threshold,
                "legacy_triggered": legacy_decision.triggered,
                "stage34_threshold": stage34_decision.threshold,
                "stage34_triggered": stage34_decision.triggered,
                "recent_error_count": stage34_decision.recent_error_count,
                "plan_ids": [str(plan_id) for plan_id in sorted(plan_ids, key=str)],
            },
            source_state_v2={
                "stage": "38",
                "feature": "error_bridge_shadow",
                "mode": "shadow",
            },
        )

    @staticmethod
    def _blocked(
        *,
        mode: str,
        gate: str,
        reason: str | None = None,
        plan_ids: list[str] | None = None,
        **extra: object,
    ) -> dict[str, object]:
        ERROR_REPLAN_BRIDGE_BLOCKED_BY_GATE_TOTAL.labels(gate=gate, mode=mode).inc()
        payload: dict[str, object] = {
            "triggered": False,
            "reason": reason or gate,
            "plan_ids": list(plan_ids or []),
            "mode": mode,
        }
        payload.update(extra)
        return payload

    async def _is_new_user(self, user_id: UUID) -> bool:
        user = await self.db.get(User, user_id)
        if user is None or getattr(user, "created_at", None) is None:
            return False
        created_at = user.created_at
        if created_at.tzinfo is not None:
            created_at = created_at.replace(tzinfo=None)
        return (_utcnow() - created_at) < timedelta(days=7)

    async def _resolve_node_name(self, node_ids: list[UUID]) -> str:
        if not node_ids:
            return ""

        from app.models.galaxy import KnowledgeNode

        node_result = await self.db.execute(select(KnowledgeNode).where(KnowledgeNode.id == node_ids[0]))
        node = node_result.scalar_one_or_none()
        if node is None:
            return ""
        return str(node.name or "").strip()

    @staticmethod
    def _extract_error_type(error: ErrorRecord) -> str:
        analysis = error.latest_analysis if isinstance(error.latest_analysis, dict) else {}
        return str(analysis.get("error_type") or "other").strip().lower()

    def _classify_trigger_type(self, error: ErrorRecord) -> str | None:
        analysis = error.latest_analysis if isinstance(error.latest_analysis, dict) else {}
        return self._classify_trigger_type_from_analysis(analysis)

    def _classify_trigger_type_from_analysis(self, analysis: dict[str, object]) -> str | None:
        raw_error_type = str(analysis.get("error_type") or "other").strip().lower()
        if raw_error_type in {"concept_confusion", "knowledge_gap"}:
            return raw_error_type
        if raw_error_type in {"procedural_error", "method_wrong"}:
            return "procedural_error"
        if raw_error_type in {"careless_mistake", "reading_careless", "calculation_error"}:
            return "careless_mistake"

        root_cause = str(analysis.get("root_cause") or "").strip().lower()
        study_suggestions = str(analysis.get("study_suggestions") or "").strip().lower()
        if raw_error_type == "time_management" or any(
            token in f"{root_cause} {study_suggestions}" for token in ("time", "rush", "pace", "deadline")
        ):
            return "time_management"
        if raw_error_type in {"strategy_mismatch", "logic_error"} or any(
            token in f"{root_cause} {study_suggestions}" for token in ("strategy", "approach", "method selection")
        ):
            return "strategy_mismatch"
        return None

    async def _find_low_mastery_nodes(self, *, user_id: UUID, node_ids: list[UUID]) -> list[UUID]:
        result = await self.db.execute(
            select(UserNodeStatus.node_id)
            .where(UserNodeStatus.user_id == user_id)
            .where(UserNodeStatus.node_id.in_(node_ids))
            .where(UserNodeStatus.mastery_score < self.LOW_MASTERY_THRESHOLD)
        )
        return list(result.scalars().all())

    async def _find_relevant_active_plan_ids(self, *, user_id: UUID, node_ids: list[UUID]) -> set[UUID]:
        today = _utcnow().date()
        result = await self.db.execute(
            select(Task.plan_id)
            .join(Plan, Plan.id == Task.plan_id)
            .join(TaskKnowledgeLink, TaskKnowledgeLink.task_id == Task.id)
            .where(
                Task.user_id == user_id,
                Task.plan_id.is_not(None),
                Task.status.in_((TaskStatus.PENDING, TaskStatus.IN_PROGRESS)),
                Plan.user_id == user_id,
                Plan.is_active.is_(True),
                TaskKnowledgeLink.knowledge_node_id.in_(node_ids),
            )
            .where((Task.due_date.is_(None)) | (Task.due_date >= today))
        )
        return {plan_id for plan_id in result.scalars().all() if plan_id is not None}

    async def _count_recent_triggering_errors(
        self,
        *,
        user_id: UUID,
        node_ids: list[UUID],
        days: int,
    ) -> int:
        cutoff = _utcnow() - timedelta(days=days)
        result = await self.db.execute(
            select(
                ErrorRecord.id,
                ErrorRecord.created_at,
                ErrorRecord.latest_analysis,
                ErrorRecord.linked_knowledge_node_ids,
            )
            .where(ErrorRecord.user_id == user_id)
            .where(ErrorRecord.is_deleted.is_(False))
            .order_by(desc(ErrorRecord.created_at))
        )

        seen_error_ids: set[UUID] = set()
        for error_id, created_at, latest_analysis, linked_ids in result.all():
            normalized_created_at = created_at
            if normalized_created_at and normalized_created_at.tzinfo is not None:
                normalized_created_at = normalized_created_at.replace(tzinfo=None)
            if normalized_created_at and normalized_created_at < cutoff:
                continue

            analysis = latest_analysis if isinstance(latest_analysis, dict) else {}
            error_type = self._classify_trigger_type_from_analysis(analysis)
            if error_type not in self.TRIGGERING_ERROR_TYPES:
                continue

            linked = {str(value) for value in (linked_ids or []) if value is not None}
            if not linked.intersection({str(node_id) for node_id in node_ids}):
                continue
            seen_error_ids.add(error_id)
        return len(seen_error_ids)

    async def _filter_plan_ids_by_cooldown(
        self,
        *,
        user_id: UUID,
        plan_ids: set[UUID],
        error_type: str,
    ) -> set[UUID]:
        if not plan_ids:
            return set()
        cutoff = _utcnow() - timedelta(hours=self.COOLDOWN_HOURS)
        records = list(
            (
                await self.db.execute(
                    select(InterventionRecord).where(
                        InterventionRecord.user_id == user_id,
                        InterventionRecord.trigger_source_ref == "error_replan_bridge",
                        InterventionRecord.created_at >= cutoff,
                    )
                )
            )
            .scalars()
            .all()
        )
        cooled_plan_ids = set(plan_ids)
        for record in records:
            diagnosis = dict(record.diagnosis_payload or {})
            if str(diagnosis.get("error_type") or "").strip().lower() != error_type:
                continue
            recent_plan_ids = {
                UUID(plan_id) for plan_id in (diagnosis.get("plan_ids") or []) if isinstance(plan_id, str)
            }
            cooled_plan_ids -= recent_plan_ids
        return cooled_plan_ids

    async def _get_cohort_profile(self, user_id: UUID) -> dict[str, str] | None:
        try:
            from app.models.user_preferences import UserPreferencesCenter

            result = await self.db.execute(
                select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == user_id)
            )
            prefs = result.scalar_one_or_none()
            if prefs is None:
                return None
            explicit = dict(getattr(prefs, "explicit", None) or getattr(prefs, "explicit_preferences", None) or {})
            goal_mem = dict(prefs.goal_memory or {}) if hasattr(prefs, "goal_memory") else {}
            return {
                "goal_type": str(
                    goal_mem.get("learning_goal_type") or explicit.get("learning_goal_type") or ""
                ).strip(),
                "knowledge_level": str(explicit.get("knowledge_level") or "").strip(),
                "learning_style": str(explicit.get("learning_style") or "").strip(),
            }
        except Exception:
            return None
