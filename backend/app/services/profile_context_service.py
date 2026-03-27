from __future__ import annotations

import json
from datetime import timezone, datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import nullslast

from app.core.cache import cache_service
from app.core.profile_context import (
    ActivePattern,
    CognitiveSummary,
    KnowledgeSummary,
    MasteryChange,
    ProfileContext,
    WeakSpot,
)
from app.models.cognitive import BehaviorPattern
from app.models.galaxy import KnowledgeNode, StudyRecord, UserNodeStatus
from app.models.subject import Subject
from app.services.insight_copy import canonical_pattern_key, present_pattern_name
from app.services.personalization.preference_service import PreferenceService
from app.services.report.report_tools import LearningReportTools


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ProfileContextService:
    CACHE_TTL_SECONDS = 300
    WEAK_SPOT_LIMIT = 5
    CHANGE_LIMIT = 5
    PATTERN_LIMIT = 5
    SUBJECT_LIMIT = 5

    PATTERN_POLICY_MAP: dict[str, list[str]] = {
        "planning_optimism": [
            "task.time_estimate.add_buffer_30pct",
            "plan.milestone.add_checkpoint",
        ],
        "night_time_energy_mismatch": [
            "push.timing.earlier_reminder",
        ],
        "perfectionism_avoidance": [
            "task.difficulty.start_easy",
            "llm.feedback.emphasize_progress",
        ],
        "perfectionism_paralysis": [
            "task.difficulty.start_easy",
            "llm.feedback.emphasize_progress",
        ],
        "cognitive_blindspot": [
            "task.content.scaffold_prerequisites",
            "llm.explanation.add_foundation",
        ],
        "focus_decay": [
            "push.timing.earlier_reminder",
            "llm.feedback.emphasize_progress",
        ],
        "doubt_driven_revision": [
            "task.difficulty.start_easy",
            "llm.feedback.emphasize_progress",
        ],
    }

    RISK_SIGNAL_MAP: dict[str, list[str]] = {
        "planning_optimism": ["risk.planning_overrun"],
        "night_time_energy_mismatch": ["risk.focus_fatigue"],
        "perfectionism_avoidance": ["risk.execution_delay", "risk.overcorrection"],
        "perfectionism_paralysis": ["risk.execution_delay", "risk.overcorrection"],
        "cognitive_blindspot": ["risk.knowledge_gap"],
        "focus_decay": ["risk.focus_fatigue"],
        "doubt_driven_revision": ["risk.overcorrection"],
    }

    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis or cache_service.redis
        self.pref_service = PreferenceService(db, self.redis)
        self.report_tools = LearningReportTools(db)

    async def get_profile_context(self, user_id: UUID) -> ProfileContext:
        cache_key = f"user:profile_context:{user_id}"
        if self.redis:
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    data = json.loads(cached)
                    return ProfileContext(**data)
            except Exception as exc:
                logger.warning(f"ProfileContext cache read failed: {exc}")

        preferences = await self._get_preferences(user_id)
        knowledge_summary = await self._get_knowledge_summary(user_id)
        cognitive_summary = await self._get_cognitive_summary(user_id)

        context = ProfileContext(
            preferences=preferences.get("explicit") or {},
            preference_version=preferences.get("version") or 0,
            knowledge_summary=knowledge_summary,
            cognitive_summary=cognitive_summary,
        )

        if self.redis:
            try:
                await self.redis.setex(cache_key, self.CACHE_TTL_SECONDS, context.model_dump_json())
            except Exception as exc:
                logger.warning(f"ProfileContext cache write failed: {exc}")

        return context

    async def _get_preferences(self, user_id: UUID) -> dict[str, Any]:
        prefs = await self.pref_service.get_preferences(user_id)
        return {
            "explicit": prefs.explicit if prefs else {},
            "version": prefs.version if prefs else 0,
        }

    async def _get_knowledge_summary(self, user_id: UUID) -> KnowledgeSummary:
        overall_mastery = 0.0
        weak_spots: list[WeakSpot] = []
        recent_changes: list[MasteryChange] = []
        active_subjects: list[str] = []

        try:
            avg_stmt = select(func.avg(UserNodeStatus.mastery_score)).where(
                UserNodeStatus.user_id == user_id
            )
            avg_result = await self.db.execute(avg_stmt)
            overall_mastery = float(avg_result.scalar() or 0.0)
        except Exception as exc:
            logger.warning(f"Failed to compute overall mastery: {exc}")

        try:
            weak_stmt = (
                select(UserNodeStatus, KnowledgeNode.name)
                .join(KnowledgeNode, KnowledgeNode.id == UserNodeStatus.node_id)
                .where(UserNodeStatus.user_id == user_id)
                .where(UserNodeStatus.is_unlocked.is_(True))
                .order_by(UserNodeStatus.mastery_score.asc(), nullslast(UserNodeStatus.last_study_at.desc()))
                .limit(self.WEAK_SPOT_LIMIT)
            )
            weak_result = await self.db.execute(weak_stmt)
            for status, node_name in weak_result.all():
                weak_spots.append(
                    WeakSpot(
                        node_id=str(status.node_id),
                        node_name=node_name,
                        mastery=float(status.mastery_score or 0.0),
                        last_attempt_at=status.last_study_at,
                    )
                )
        except Exception as exc:
            logger.warning(f"Failed to load weak spots: {exc}")

        try:
            since = _utcnow() - timedelta(days=7)
            change_stmt = (
                select(StudyRecord, KnowledgeNode.name)
                .join(KnowledgeNode, KnowledgeNode.id == StudyRecord.node_id)
                .where(StudyRecord.user_id == user_id)
                .where(StudyRecord.created_at >= since)
                .order_by(StudyRecord.created_at.desc())
                .limit(self.CHANGE_LIMIT)
            )
            change_result = await self.db.execute(change_stmt)
            for record, node_name in change_result.all():
                old_mastery = float(record.initial_mastery or 0.0)
                delta = float(record.mastery_delta or 0.0)
                recent_changes.append(
                    MasteryChange(
                        node_id=str(record.node_id),
                        node_name=node_name,
                        old_mastery=old_mastery,
                        new_mastery=old_mastery + delta,
                        changed_at=record.created_at,
                    )
                )
        except Exception as exc:
            logger.warning(f"Failed to load mastery changes: {exc}")

        try:
            since = _utcnow() - timedelta(days=30)
            subject_stmt = (
                select(Subject.name, func.count(StudyRecord.id))
                .join(KnowledgeNode, KnowledgeNode.id == StudyRecord.node_id)
                .join(Subject, Subject.id == KnowledgeNode.subject_id)
                .where(StudyRecord.user_id == user_id)
                .where(StudyRecord.created_at >= since)
                .group_by(Subject.name)
                .order_by(desc(func.count(StudyRecord.id)))
                .limit(self.SUBJECT_LIMIT)
            )
            subject_result = await self.db.execute(subject_stmt)
            active_subjects = [row[0] for row in subject_result.all() if row[0]]
        except Exception as exc:
            logger.warning(f"Failed to load active subjects: {exc}")

        if overall_mastery <= 0.0 or not weak_spots or not active_subjects:
            fallback_mastery = await self.report_tools.query_mastery_scores(
                user_id,
                limit=self.WEAK_SPOT_LIMIT,
            )
            if fallback_mastery:
                if overall_mastery <= 0.0:
                    overall_mastery = sum(
                        float(item.get("mastery_score") or 0.0) for item in fallback_mastery
                    ) / max(len(fallback_mastery), 1)
                if not weak_spots:
                    weak_spots = [
                        WeakSpot(
                            node_id=f"derived:{index}",
                            node_name=str(item.get("node_name") or ""),
                            mastery=float(item.get("mastery_score") or 0.0),
                            last_attempt_at=None,
                        )
                        for index, item in enumerate(fallback_mastery)
                        if str(item.get("node_name") or "").strip()
                    ]
                if not active_subjects:
                    active_subjects = [
                        str(item.get("node_name") or "")
                        for item in fallback_mastery[: self.SUBJECT_LIMIT]
                        if str(item.get("node_name") or "").strip()
                    ]

        if not recent_changes:
            fallback_timeline = await self.report_tools.query_study_timeline(
                user_id,
                limit=self.CHANGE_LIMIT,
            )
            recent_changes = []
            for index, item in enumerate(fallback_timeline):
                node_name = str(item.get("node_name") or "").strip()
                if not node_name:
                    continue
                delta = float(item.get("mastery_delta") or 0.0)
                created_at_raw = item.get("created_at")
                changed_at = _utcnow()
                if isinstance(created_at_raw, str) and created_at_raw.strip():
                    try:
                        changed_at = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00")).replace(
                            tzinfo=None
                        )
                    except ValueError:
                        changed_at = _utcnow()
                recent_changes.append(
                    MasteryChange(
                        node_id=f"derived:{index}",
                        node_name=node_name,
                        old_mastery=max(0.0, 42.0 - delta),
                        new_mastery=max(0.0, 42.0),
                        changed_at=changed_at,
                    )
                )

        return KnowledgeSummary(
            overall_mastery=overall_mastery,
            weak_spots=weak_spots,
            recent_mastery_changes=recent_changes,
            active_learning_subjects=active_subjects,
        )

    async def _get_cognitive_summary(self, user_id: UUID) -> CognitiveSummary:
        active_patterns: list[ActivePattern] = []
        risk_signals: list[str] = []
        dominant_pattern_type: str | None = None

        try:
            stmt = (
                select(BehaviorPattern)
                .where(BehaviorPattern.user_id == user_id)
                .where(BehaviorPattern.is_archived.is_(False))
                .where(BehaviorPattern.confidence_score >= 0.5)
                .order_by(desc(BehaviorPattern.confidence_score))
                .limit(self.PATTERN_LIMIT)
            )
            result = await self.db.execute(stmt)
            patterns = result.scalars().all()
        except Exception as exc:
            logger.warning(f"Failed to load behavior patterns: {exc}")
            patterns = []

        type_scores: dict[str, float] = {}
        for pattern in patterns:
            name = str(pattern.pattern_name or "").strip()
            normalized = self._normalize_pattern_name(name)
            signals = list(self.PATTERN_POLICY_MAP.get(normalized, []))
            active_patterns.append(
                ActivePattern(
                    pattern_name=present_pattern_name(name or normalized),
                    pattern_type=str(pattern.pattern_type or "execution"),
                    confidence=float(pattern.confidence_score or 0.0),
                    policy_signals=signals,
                )
            )

            confidence_val = float(pattern.confidence_score or 0.0)
            if confidence_val >= 0.6:
                risk_signals.extend(self.RISK_SIGNAL_MAP.get(normalized, []))

            pattern_type = str(pattern.pattern_type or "")
            if pattern_type:
                type_scores[pattern_type] = type_scores.get(pattern_type, 0.0) + confidence_val

        if type_scores:
            dominant_pattern_type = max(type_scores, key=type_scores.get)

        risk_signals = list(dict.fromkeys(risk_signals))

        return CognitiveSummary(
            active_patterns=active_patterns,
            dominant_pattern_type=dominant_pattern_type,
            risk_signals=risk_signals,
        )

    @staticmethod
    def _normalize_pattern_name(name: str) -> str:
        return canonical_pattern_key(name)
