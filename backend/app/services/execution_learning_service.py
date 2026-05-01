"""Phase 3 learning loop for delegated execution outcomes."""

from __future__ import annotations

import re
from datetime import datetime, UTC
from statistics import median
from uuid import UUID

from loguru import logger
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.event_bus import event_bus
from app.core.event_types import PROFILE_COGNITIVE_UPDATED
from app.models.cognitive import BehaviorPattern
from app.models.execution_intent import ExecutionIntent, ExecutionIntentStatus, TrustLevel
from app.models.execution_record import ExecutionRecord
from app.models.task import Task
from app.orchestration.adaptive_replanner import AdaptiveReplanner
from app.services.cognitive_service import CognitiveService
from app.services.profile_write_service import ProfileWriteService
from app.services.signal_adaptation import recency_weight


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ExecutionLearningService:
    """Learn from delegated execution outcomes and feed Phase 3 loops."""

    TRUST_BUILDING_STREAK = 5
    AVERSION_WINDOW = 10
    AVERSION_THRESHOLD = 0.6
    DURATION_WINDOW = 5
    DURATION_RATIO_DELTA = 0.3
    ERROR_SUGGESTION_WINDOW = 30

    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis
        self.cognitive_service = CognitiveService(db)
        self.profile_write_service = ProfileWriteService(db, redis)

    async def get_category_trust_stats(self, *, user_id: UUID) -> dict[str, dict[str, float | int | str]]:
        stmt = (
            select(
                ExecutionIntent.target_env,
                ExecutionIntent.status,
                ExecutionIntent.trust_level,
                func.count(ExecutionIntent.id).label("cnt"),
            )
            .where(
                ExecutionIntent.user_id == user_id,
                ExecutionIntent.deleted_at.is_(None),
                ExecutionIntent.target_env.is_not(None),
            )
            .group_by(
                ExecutionIntent.target_env,
                ExecutionIntent.status,
                ExecutionIntent.trust_level,
            )
        )
        rows = (await self.db.execute(stmt)).all()
        stats: dict[str, dict[str, float | int | str]] = {}
        for row in rows:
            target_env = row.target_env.value if row.target_env else "general"
            bucket = stats.setdefault(
                target_env,
                {
                    "total": 0,
                    "succeeded": 0,
                    "trusted_runs": 0,
                    "success_rate": 0.0,
                    "current_trust": "raw",
                },
            )
            count = int(row.cnt or 0)
            bucket["total"] = int(bucket["total"]) + count
            if row.status == ExecutionIntentStatus.SUCCEEDED:
                bucket["succeeded"] = int(bucket["succeeded"]) + count
            if row.trust_level == TrustLevel.TRUSTED:
                bucket["trusted_runs"] = int(bucket["trusted_runs"]) + count

        for bucket in stats.values():
            total = int(bucket["total"])
            succeeded = int(bucket["succeeded"])
            success_rate = round(succeeded / total, 2) if total > 0 else 0.0
            bucket["success_rate"] = success_rate
            if (
                total >= settings.OPENCLAW_TRUST_AUTO_PROMOTE_MIN_HISTORY
                and success_rate >= settings.OPENCLAW_TRUST_AUTO_PROMOTE_SUCCESS_RATE
                and int(bucket["trusted_runs"]) >= max(2, total // 2)
            ):
                bucket["current_trust"] = "trusted"
            elif total >= 3 and success_rate >= 0.6:
                bucket["current_trust"] = "validated"
            else:
                bucket["current_trust"] = "raw"
        return stats

    async def estimate_duration(
        self,
        *,
        user_id: UUID,
        target_env: str | None,
        goal_keywords: list[str] | None = None,
    ) -> int | None:
        del goal_keywords
        if not target_env:
            return None

        stmt = (
            select(ExecutionRecord.duration_ms)
            .join(
                ExecutionIntent,
                ExecutionRecord.execution_intent_id == ExecutionIntent.id,
            )
            .where(
                ExecutionIntent.user_id == user_id,
                ExecutionIntent.deleted_at.is_(None),
                ExecutionIntent.target_env == target_env,
                ExecutionIntent.status.in_(
                    [
                        ExecutionIntentStatus.SUCCEEDED,
                        ExecutionIntentStatus.PARTIAL,
                    ]
                ),
                ExecutionRecord.deleted_at.is_(None),
                ExecutionRecord.duration_ms.is_not(None),
                ExecutionRecord.duration_ms > 0,
            )
            .order_by(desc(ExecutionRecord.created_at))
            .limit(20)
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        durations_ms = [int(item) for item in rows if item]
        if not durations_ms:
            return None
        return max(1, round(median(durations_ms) / 1000))

    async def get_error_suggestion(
        self,
        *,
        user_id: UUID,
        error_category: str | None,
        target_env: str | None,
    ) -> dict[str, object] | None:
        normalized_error = str(error_category or "").strip().lower()
        if not normalized_error:
            return None

        recent_stmt = (
            select(ExecutionIntent)
            .where(
                ExecutionIntent.user_id == user_id,
                ExecutionIntent.deleted_at.is_(None),
                ExecutionIntent.error_category.is_not(None),
                ExecutionIntent.target_env == target_env if target_env else True,
            )
            .order_by(desc(ExecutionIntent.completed_at), desc(ExecutionIntent.created_at))
            .limit(self.ERROR_SUGGESTION_WINDOW)
        )
        recent_intents = list((await self.db.execute(recent_stmt)).scalars().all())
        matched = [
            intent
            for intent in recent_intents
            if str(intent.error_category or "").strip().lower() == normalized_error
        ]

        retry_attempts = len(matched)
        retry_successes = sum(
            1
            for intent in matched
            if intent.status in {ExecutionIntentStatus.SUCCEEDED, ExecutionIntentStatus.PARTIAL}
        )
        retry_success_rate = (
            round(retry_successes / retry_attempts, 2)
            if retry_attempts > 0
            else self._default_retry_success_rate(normalized_error)
        )

        suggestion = self._default_error_suggestion(
            error_category=normalized_error,
            target_env=target_env,
            retry_success_rate=retry_success_rate,
        )
        if suggestion is None:
            return None
        suggestion["history_samples"] = retry_attempts
        return suggestion

    async def handle_trusted_execution(
        self,
        *,
        intent: ExecutionIntent,
        record: ExecutionRecord,
        parsed: dict,
    ) -> None:
        if intent.status != ExecutionIntentStatus.SUCCEEDED:
            return
        intent_user_id = intent.user_id
        intent_plan_id = intent.plan_id

        await self._create_execution_fragment(
            intent=intent,
            record=record,
            signal_key=f"execution_trusted:{intent.id}",
            content=(
                f"用户确认并采纳了 AI 执行结果，任务《{intent.goal}》委派成功。"
            ),
            error_tags=["execution.delegated_success"],
            severity=1,
        )

        streak = await self._trusted_success_streak(intent_user_id)
        if streak >= self.TRUST_BUILDING_STREAK:
            confidence = min(0.95, 0.6 + (streak - self.TRUST_BUILDING_STREAK + 1) * 0.05)
            trust_pattern_name = "Delegation Trust Building"
            await self._upsert_pattern(
                user_id=intent.user_id,
                pattern_name=trust_pattern_name,
                pattern_type="execution",
                description=f"User accepted delegated execution successfully {streak} times in a row.",
                solution_text="Delegate low-risk digital steps proactively when helpful.",
                evidence_id=str(record.id),
                confidence=confidence,
            )
            await self._trigger_replanner(
                user_id=intent_user_id,
                plan_id=intent_plan_id,
                pattern_name=trust_pattern_name,
            )

        await self._refresh_delegate_preference(intent.user_id)
        await self._adjust_safety_concern_count(intent.user_id, delta=-1)

        duration_multiplier = await self._duration_multiplier(intent_user_id)
        if duration_multiplier is not None:
            duration_pattern_name = "Execution Time Learning"
            await self._upsert_pattern(
                user_id=intent.user_id,
                pattern_name=duration_pattern_name,
                pattern_type="execution",
                description=(
                    f"AI delegated tasks usually take multiplier={duration_multiplier:.2f} "
                    f"of the estimated task duration."
                ),
                solution_text="Adjust future AI task estimates using the learned multiplier.",
                evidence_id=str(record.id),
                confidence=min(0.9, 0.6 + abs(duration_multiplier - 1.0) * 0.5),
            )
            await self.profile_write_service.update_inferred_preference(
                user_id=intent.user_id,
                updates={"ai_duration_multiplier": round(duration_multiplier, 2)},
                source="execution_learning",
            )
            await self._trigger_replanner(
                user_id=intent_user_id,
                plan_id=intent_plan_id,
                pattern_name=duration_pattern_name,
            )

    async def handle_handed_back(
        self,
        *,
        intent: ExecutionIntent,
        record: ExecutionRecord | None = None,
        reason: str | None = None,
    ) -> None:
        intent_user_id = intent.user_id
        intent_plan_id = intent.plan_id

        await self._create_execution_fragment(
            intent=intent,
            record=record,
            signal_key=f"execution_handed_back:{intent.id}",
            content=(
                f"用户取回了 AI 执行任务《{intent.goal}》"
                + (f"，原因：{reason}" if reason else "")
                + "。"
            ),
            error_tags=["execution.delegation_takeback"],
            severity=2,
        )

        summary = await self._delegation_aversion_summary(intent_user_id)
        if not summary:
            return

        takeback_rate, total = summary
        confidence = min(0.95, 0.55 + takeback_rate * 0.5)
        aversion_pattern_name = "Delegation Aversion"
        await self._upsert_pattern(
            user_id=intent.user_id,
            pattern_name=aversion_pattern_name,
            pattern_type="execution",
            description=(
                f"User took back or rejected delegated execution {int(round(takeback_rate * total))}/{total} times "
                f"recently (takeback_rate={takeback_rate:.2f})."
            ),
            solution_text="Reduce auto-delegation suggestions and keep human confirmation in the loop.",
            evidence_id=str(record.id if record else intent.id),
            confidence=confidence,
        )
        await self._refresh_delegate_preference(intent.user_id)
        await self.profile_write_service.update_inferred_preference(
            user_id=intent.user_id,
            updates={
                "ai_approval_preference": round(min(0.95, 0.5 + takeback_rate * 0.4), 2),
            },
            source="execution_learning",
        )
        await self._trigger_replanner(
            user_id=intent_user_id,
            plan_id=intent_plan_id,
            pattern_name=aversion_pattern_name,
        )

    async def handle_approval_speed_signal(
        self,
        *,
        intent: ExecutionIntent,
        record: ExecutionRecord,
        approved: bool,
    ) -> None:
        if not intent.dispatched_at or not intent.completed_at:
            return
        decision_latency = max(
            (intent.completed_at - intent.dispatched_at).total_seconds(),
            0,
        )
        if approved and decision_latency <= 15:
            await self.profile_write_service.update_inferred_preference(
                user_id=intent.user_id,
                updates={
                    f"execution.{intent.target_env.value if intent.target_env else 'general'}.detail_level": "concise",
                },
                source="execution_approval_speed",
            )
            await self._create_execution_fragment(
                intent=intent,
                record=record,
                signal_key=f"execution_approval_speed:{intent.id}",
                content=f"用户在 {int(decision_latency)} 秒内确认了 AI 执行结果，说明对该类委派有较高即时信任。",
                error_tags=["execution.approval_fast_confirm"],
                severity=1,
            )
        elif (not approved) or decision_latency >= 45:
            await self.profile_write_service.update_inferred_preference(
                user_id=intent.user_id,
                updates={
                    f"execution.{intent.target_env.value if intent.target_env else 'general'}.detail_level": "detailed",
                },
                source="execution_approval_speed",
            )

    async def handle_task_type_delegation_tendency(
        self,
        *,
        user_id: UUID,
        task_type: str,
    ) -> None:
        normalized = (task_type or "general").lower()
        stmt = (
            select(
                ExecutionIntent.trust_level,
                func.count(ExecutionIntent.id).label("cnt"),
            )
            .where(
                ExecutionIntent.user_id == user_id,
                ExecutionIntent.deleted_at.is_(None),
            )
            .group_by(ExecutionIntent.trust_level)
        )
        rows = (await self.db.execute(stmt)).all()
        total = sum(int(row.cnt or 0) for row in rows)
        if total == 0:
            return
        trusted = sum(int(row.cnt or 0) for row in rows if row.trust_level == TrustLevel.TRUSTED)
        delegate_preference = round(trusted / total, 2)
        await self.profile_write_service.update_inferred_preference(
            user_id=user_id,
            updates={f"execution.{normalized}.delegate_preference": delegate_preference},
            source="task_type_delegation_tendency",
        )
        if total >= 5 and delegate_preference < 0.3:
            await self._upsert_pattern(
                user_id=user_id,
                pattern_name="Execution Type Preference",
                pattern_type="execution",
                description=(
                    f"User shows low delegation trust for {normalized} tasks "
                    f"(trust_rate={delegate_preference:.2f}, sample_size={total})."
                ),
                solution_text="Prefer human-first or confirmation-heavy routing for this execution type.",
                evidence_id=f"{normalized}:{total}",
                confidence=0.75,
            )

    async def handle_quality_sensitivity(
        self,
        *,
        intent: ExecutionIntent,
        record: ExecutionRecord,
        approved: bool,
    ) -> None:
        if record.quality_score is None:
            return
        key = "execution.quality_acceptance_floor" if approved else "execution.quality_rejection_ceiling"
        await self.profile_write_service.update_inferred_preference(
            user_id=intent.user_id,
            updates={key: round(float(record.quality_score), 2)},
            source="execution_quality_sensitivity",
        )
        await self._upsert_pattern(
            user_id=intent.user_id,
            pattern_name="Execution Quality Sensitivity",
            pattern_type="execution",
            description=(
                f"User {'accepted' if approved else 'rejected'} quality score "
                f"{float(record.quality_score):.2f} for delegated execution."
            ),
            solution_text="Adapt result detail and auto-promotion thresholds to the user's quality tolerance.",
            evidence_id=str(record.id),
            confidence=0.72,
        )

    async def handle_rejection_sentiment(
        self,
        *,
        intent: ExecutionIntent,
        record: ExecutionRecord | None,
        reason: str | None,
    ) -> None:
        text = (reason or "").strip().lower()
        if not text:
            return
        severity = 1
        if any(token in text for token in ["安全", "risk", "unsafe", "危险"]):
            severity = 3
            await self._adjust_safety_concern_count(intent.user_id, delta=1)
        elif any(token in text for token in ["不准确", "不对", "错误", "失望"]):
            severity = 2
        await self._create_execution_fragment(
            intent=intent,
            record=record,
            signal_key=f"execution_rejection_sentiment:{intent.id}",
            content=f"用户退回了委派结果，原因倾向为：{reason}",
            error_tags=["execution.rejection_sentiment"],
            severity=severity,
        )

    async def _create_execution_fragment(
        self,
        *,
        intent: ExecutionIntent,
        record: ExecutionRecord | None,
        signal_key: str,
        content: str,
        error_tags: list[str],
        severity: int,
    ) -> None:
        try:
            await self.cognitive_service.create_fragment(
                user_id=intent.user_id,
                task_id=intent.task_id,
                content=content,
                source_type="behavior_auto",
                context_tags={
                    "execution_intent_id": str(intent.id),
                    "execution_record_id": str(record.id) if record else None,
                    "executor": intent.executor.value if intent.executor else None,
                    "execution_mode": intent.execution_mode.value if intent.execution_mode else None,
                    "signal_key": signal_key,
                },
                error_tags=error_tags,
                severity=severity,
                source_event_id=f"execution_learning:{signal_key}",
            )
        except Exception as exc:
            logger.warning("Execution learning fragment creation failed for %s: %s", intent.id, exc)

    async def _trusted_success_streak(self, user_id: UUID) -> int:
        result = await self.db.execute(
            select(ExecutionIntent)
            .where(ExecutionIntent.user_id == user_id, ExecutionIntent.deleted_at.is_(None))
            .order_by(desc(ExecutionIntent.completed_at), desc(ExecutionIntent.created_at))
            .limit(self.TRUST_BUILDING_STREAK + 5)
        )
        streak = 0
        for intent in result.scalars().all():
            if intent.status == ExecutionIntentStatus.SUCCEEDED and intent.trust_level == TrustLevel.TRUSTED:
                streak += 1
            else:
                break
        return streak

    async def _delegation_aversion_summary(self, user_id: UUID) -> tuple[float, int] | None:
        terminal = await self._recent_terminal_intents(user_id, limit=self.AVERSION_WINDOW)
        total = len(terminal)
        if total < 5:
            return None
        weighted_total = 0.0
        weighted_takebacks = 0.0
        now = _utcnow()
        for intent in terminal:
            observed_at = intent.completed_at or intent.created_at
            weight = recency_weight(observed_at, now=now, half_life_days=7.0, min_weight=0.25)
            weighted_total += weight
            if intent.status == ExecutionIntentStatus.HANDED_BACK or str(intent.error_category or "") == "user_rejected":
                weighted_takebacks += weight
        if weighted_total <= 0:
            return None
        rate = weighted_takebacks / weighted_total
        if rate < self.AVERSION_THRESHOLD:
            return None
        return rate, total

    async def _refresh_delegate_preference(self, user_id: UUID) -> None:
        terminal = await self._recent_terminal_intents(user_id, limit=self.AVERSION_WINDOW)
        if not terminal:
            return

        delegated_successes = 0.0
        weighted_total = 0.0
        now = _utcnow()
        for intent in terminal:
            observed_at = intent.completed_at or intent.created_at
            weight = recency_weight(observed_at, now=now, half_life_days=7.0, min_weight=0.25)
            weighted_total += weight
            if intent.status == ExecutionIntentStatus.SUCCEEDED and intent.trust_level == TrustLevel.TRUSTED:
                delegated_successes += weight
        if weighted_total <= 0:
            return
        preference = round(
            min(0.9, max(0.1, delegated_successes / weighted_total)),
            2,
        )
        await self.profile_write_service.update_inferred_preference(
            user_id=user_id,
            updates={"ai_delegate_preference": preference},
            source="execution_learning",
        )

    async def _adjust_safety_concern_count(self, user_id: UUID, *, delta: int) -> None:
        prefs = await self.profile_write_service.pref_service.get_preferences(user_id)
        current = prefs.inferred.get("execution.safety_concern_count", 0) if prefs.inferred else 0
        try:
            current_count = int(current)
        except (TypeError, ValueError):
            current_count = 0

        next_count = max(0, current_count + delta)
        if next_count == current_count:
            return
        if next_count == 0:
            await self.profile_write_service.remove_inferred_preference(
                user_id=user_id,
                pref_key="execution.safety_concern_count",
            )
            return

        await self.profile_write_service.update_inferred_preference(
            user_id=user_id,
            updates={"execution.safety_concern_count": next_count},
            source="execution_rejection_sentiment",
        )

    async def _recent_terminal_intents(self, user_id: UUID, *, limit: int) -> list[ExecutionIntent]:
        result = await self.db.execute(
            select(ExecutionIntent)
            .where(ExecutionIntent.user_id == user_id, ExecutionIntent.deleted_at.is_(None))
            .order_by(desc(ExecutionIntent.completed_at), desc(ExecutionIntent.created_at))
            .limit(limit)
        )
        intents = list(result.scalars().all())
        return [
            intent for intent in intents
            if intent.status in {
                ExecutionIntentStatus.SUCCEEDED,
                ExecutionIntentStatus.FAILED,
                ExecutionIntentStatus.HANDED_BACK,
                ExecutionIntentStatus.CANCELED,
                ExecutionIntentStatus.TIMED_OUT,
                ExecutionIntentStatus.PARTIAL,
            }
        ]

    async def _duration_multiplier(self, user_id: UUID) -> float | None:
        result = await self.db.execute(
            select(ExecutionRecord, ExecutionIntent, Task)
            .join(ExecutionIntent, ExecutionIntent.id == ExecutionRecord.execution_intent_id)
            .join(Task, Task.id == ExecutionIntent.task_id)
            .where(
                ExecutionRecord.user_id == user_id,
                ExecutionIntent.status == ExecutionIntentStatus.SUCCEEDED,
                ExecutionIntent.trust_level == TrustLevel.TRUSTED,
            )
            .order_by(desc(ExecutionRecord.execution_completed_at))
            .limit(self.DURATION_WINDOW)
        )

        ratios: list[float] = []
        for record, _intent, task in result.all():
            estimated_minutes = getattr(task, "estimated_minutes", None)
            if not estimated_minutes or not record.duration_ms:
                continue
            estimated_ms = max(int(estimated_minutes) * 60_000, 1)
            ratios.append(record.duration_ms / estimated_ms)

        if len(ratios) < 3:
            return None

        multiplier = round(float(median(ratios)), 2)
        if abs(multiplier - 1.0) < self.DURATION_RATIO_DELTA:
            return None
        return multiplier

    @staticmethod
    def _default_retry_success_rate(error_category: str) -> float:
        if error_category in {"timeout", "network_timeout"}:
            return 0.68
        if error_category in {"adapter_error", "gateway_unreachable", "connection_unavailable"}:
            return 0.31
        if error_category in {"security_policy", "blocked"}:
            return 0.0
        return 0.42

    @staticmethod
    def _default_error_suggestion(
        *,
        error_category: str,
        target_env: str | None,
        retry_success_rate: float,
    ) -> dict[str, object] | None:
        env_label = {
            "browser": "网页访问",
            "shell": "终端执行",
            "api": "接口调用",
            "document": "文档处理",
        }.get(str(target_env or "").lower(), "执行链路")

        if error_category in {"timeout", "network_timeout"}:
            return {
                "suggestion": f"{env_label}这次超时了，通常是网络波动或目标响应偏慢。",
                "retry_success_rate": retry_success_rate,
                "recommended_action": "retry",
            }
        if error_category in {"adapter_error", "gateway_unreachable", "connection_unavailable"}:
            return {
                "suggestion": "当前更像是 OpenClaw 连接或网关不可达，先恢复连接再执行会更稳。",
                "retry_success_rate": retry_success_rate,
                "recommended_action": "manual" if retry_success_rate < 0.35 else "retry",
            }
        if error_category in {"security_policy", "blocked"}:
            return {
                "suggestion": "这条指令触发了安全策略，建议改成更小范围、更可逆的操作再试。",
                "retry_success_rate": retry_success_rate,
                "recommended_action": "alternative",
            }
        if error_category in {"execution_failed", "unexpected_error"}:
            return {
                "suggestion": f"{env_label}执行过程中出现异常，建议先重试一次；如果连续失败，改走人工步骤更稳。",
                "retry_success_rate": retry_success_rate,
                "recommended_action": "retry" if retry_success_rate >= 0.45 else "manual",
            }
        return {
            "suggestion": "这次执行没有成功完成，我建议先检查环境状态，再决定是重试还是人工接管。",
            "retry_success_rate": retry_success_rate,
            "recommended_action": "retry" if retry_success_rate >= 0.5 else "manual",
        }

    async def _upsert_pattern(
        self,
        *,
        user_id: UUID,
        pattern_name: str,
        pattern_type: str,
        description: str,
        solution_text: str,
        evidence_id: str,
        confidence: float,
    ) -> BehaviorPattern:
        stmt = select(BehaviorPattern).where(
            BehaviorPattern.user_id == user_id,
            BehaviorPattern.pattern_name == pattern_name,
            BehaviorPattern.is_archived.is_(False),
        )
        result = await self.db.execute(stmt)
        pattern = result.scalar_one_or_none()
        is_new_pattern = pattern is None

        if pattern is None:
            pattern = BehaviorPattern(
                user_id=user_id,
                pattern_name=pattern_name,
                pattern_type=pattern_type,
                description=description,
                solution_text=solution_text,
                evidence_ids=[evidence_id],
                confidence_score=confidence,
                frequency=1,
                last_observed_at=_utcnow(),
            )
            self.db.add(pattern)
        else:
            pattern.pattern_type = pattern_type
            pattern.description = description
            pattern.solution_text = solution_text
            pattern.last_observed_at = _utcnow()
            pattern.frequency = int(pattern.frequency or 0) + 1
            pattern.confidence_score = round(0.3 * confidence + 0.7 * float(pattern.confidence_score or 0.0), 4)
            evidence_ids = list(pattern.evidence_ids or [])
            if evidence_id not in evidence_ids:
                evidence_ids.append(evidence_id)
                pattern.evidence_ids = evidence_ids[-10:]

        await self.db.commit()
        await self.db.refresh(pattern)

        await event_bus.publish(
            PROFILE_COGNITIVE_UPDATED,
            {
                "event_type": PROFILE_COGNITIVE_UPDATED,
                "user_id": str(user_id),
                "pattern_name": pattern_name,
                "pattern_type": pattern_type,
                "confidence_change": float(confidence),
                "is_new_pattern": is_new_pattern,
            },
        )
        if float(pattern.confidence_score or 0.0) >= 0.7:
            await event_bus.publish(
                "behavior.pattern.updated",
                {
                    "event_type": "behavior.pattern.updated",
                    "user_id": str(user_id),
                    "pattern_id": str(pattern.id),
                    "pattern_name": pattern_name,
                    "pattern_type": pattern_type,
                    "confidence_score": float(pattern.confidence_score or 0.0),
                    "source_fragment_id": evidence_id,
                },
            )
        return pattern

    async def _trigger_replanner(
        self,
        *,
        user_id: UUID,
        plan_id: UUID | None,
        pattern_name: str,
    ) -> None:
        plan_ids: list[UUID] = []
        if plan_id:
            plan_ids.append(plan_id)
        else:
            result = await self.db.execute(
                select(Task.plan_id)
                .where(Task.user_id == user_id, Task.deleted_at.is_(None), Task.plan_id.is_not(None))
                .order_by(desc(Task.updated_at))
                .limit(3)
            )
            plan_ids.extend([plan_id for plan_id in result.scalars().all() if plan_id])

        seen: set[UUID] = set()
        for plan_id in plan_ids:
            if plan_id in seen:
                continue
            seen.add(plan_id)
            try:
                replanner = AdaptiveReplanner(self.db, self.redis)
                await replanner.on_behavior_pattern_detected(
                    user_id=user_id,
                    plan_id=plan_id,
                    pattern_name=pattern_name,
                )
            except Exception as exc:
                logger.warning("Execution learning replanner trigger failed for plan %s: %s", plan_id, exc)


def extract_multiplier_from_description(description: str | None) -> float | None:
    if not description:
        return None
    match = re.search(r"multiplier=([0-9]+(?:\.[0-9]+)?)", description)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None
