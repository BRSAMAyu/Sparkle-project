"""Phase 3 learning loop for delegated execution outcomes."""

from __future__ import annotations

import re
from datetime import timezone, datetime
from statistics import median
from uuid import UUID

from loguru import logger
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import event_bus
from app.core.event_types import PROFILE_COGNITIVE_UPDATED
from app.models.cognitive import BehaviorPattern
from app.models.execution_intent import ExecutionIntent, ExecutionIntentStatus, TrustLevel
from app.models.execution_record import ExecutionRecord
from app.models.task import Task
from app.orchestration.adaptive_replanner import AdaptiveReplanner
from app.services.cognitive_service import CognitiveService
from app.services.profile_write_service import ProfileWriteService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ExecutionLearningService:
    """Learn from delegated execution outcomes and feed Phase 3 loops."""

    TRUST_BUILDING_STREAK = 5
    AVERSION_WINDOW = 10
    AVERSION_THRESHOLD = 0.6
    DURATION_WINDOW = 5
    DURATION_RATIO_DELTA = 0.3

    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis
        self.cognitive_service = CognitiveService(db)
        self.profile_write_service = ProfileWriteService(db, redis)

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
            await self.profile_write_service.update_inferred_preference(
                user_id=intent.user_id,
                updates={
                    "ai_delegate_preference": round(min(0.9, 0.55 + streak * 0.05), 2),
                },
                source="execution_learning",
            )
            await self._trigger_replanner(
                user_id=intent_user_id,
                plan_id=intent_plan_id,
                pattern_name=trust_pattern_name,
            )

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
        await self.profile_write_service.update_inferred_preference(
            user_id=intent.user_id,
            updates={
                "ai_delegate_preference": round(max(0.1, 1.0 - takeback_rate), 2),
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
            await self.profile_write_service.update_inferred_preference(
                user_id=intent.user_id,
                updates={"execution.safety_concern_count": 1},
                source="execution_rejection_sentiment",
            )
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
        result = await self.db.execute(
            select(ExecutionIntent)
            .where(ExecutionIntent.user_id == user_id, ExecutionIntent.deleted_at.is_(None))
            .order_by(desc(ExecutionIntent.completed_at), desc(ExecutionIntent.created_at))
            .limit(self.AVERSION_WINDOW)
        )
        intents = list(result.scalars().all())
        terminal = [
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
        total = len(terminal)
        if total < 5:
            return None
        takebacks = sum(
            1
            for intent in terminal
            if intent.status == ExecutionIntentStatus.HANDED_BACK or str(intent.error_category or "") == "user_rejected"
        )
        rate = takebacks / max(total, 1)
        if rate < self.AVERSION_THRESHOLD:
            return None
        return rate, total

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
