from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, get_args
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
from app.core.user_insight_state import BigFiveTraits
from app.models.cognitive import BehaviorPattern
from app.models.galaxy import KnowledgeNode, StudyRecord, UserNodeStatus
from app.models.subject import Subject
from app.schemas.error_book import ErrorQueryParams
from app.services.aurora_stage34_kill_switch_service import AuroraStage34KillSwitchService
from app.services.error_book_service import ErrorBookService
from app.services.idiographic_association_service import IdiographicAssociationService
from app.services.insight_copy import canonical_pattern_key, present_pattern_name
from app.services.metacognition_service import MetacognitionService
from app.services.personalization.preference_service import PreferenceService
from app.services.report.report_tools import LearningReportTools
from app.services.user_insight_compiler import UserInsightCompiler
from app.state_aggregator.schema import UserStateFieldName
from app.state_aggregator.service import StateAggregatorService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ProfileContextService:
    CACHE_TTL_SECONDS = 120  # 2 min to reduce stale knowledge mastery
    INLINE_SNAPSHOT_CACHE_TTL_SECONDS = 120
    WEAK_SPOT_LIMIT = 5
    CHANGE_LIMIT = 5
    PATTERN_LIMIT = 5
    SUBJECT_LIMIT = 5
    USER_STATE_V1_FIELDS = tuple(get_args(UserStateFieldName))

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
        "delegation_aversion": [
            "execution.delegate.require_confirmation",
            "task.execution.recommend_human_first",
        ],
        "delegation_trust_building": [
            "execution.delegate.suggest_when_safe",
        ],
        "execution_time_learning": [
            "task.execution.adjust_ai_duration",
        ],
        "execution_type_preference": [
            "execution.delegate.per_type_routing",
            "task.execution.type_aware_suggestion",
        ],
        "execution_quality_sensitivity": [
            "execution.result.detail_level_adjust",
            "execution.trust.quality_threshold_adjust",
        ],
        "execution_safety_concern": [
            "execution.delegate.require_manual_review",
            "execution.route.prefer_hybrid",
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
        "delegation_aversion": ["risk.delegation_takeback"],
    }

    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis or cache_service.redis
        self.pref_service = PreferenceService(db, self.redis)
        self.error_book_service = ErrorBookService(db)
        self.report_tools = LearningReportTools(db)

    async def get_profile_context(
        self,
        user_id: UUID,
        *,
        include_metacognition_prompt_extensions: bool = False,
    ) -> ProfileContext:
        cache_key = f"user:profile_context:{user_id}"
        if self.redis:
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    data = json.loads(cached)
                    context = ProfileContext(**data)
                    current_version = await self.pref_service.get_preference_version(
                        user_id
                    )
                    if (
                        context.preference_version == current_version
                        and context.user_insight_state is not None
                    ):
                        await self._attach_live_extensions(
                            user_id,
                            context,
                            include_metacognition_prompt_extensions=include_metacognition_prompt_extensions,
                        )
                        return context
                    logger.info(
                        "ProfileContext cache stale for %s: cached_version=%s current_version=%s has_insight=%s",
                        user_id,
                        context.preference_version,
                        current_version,
                        bool(context.user_insight_state),
                    )
            except Exception as exc:
                logger.warning(f"ProfileContext cache read failed: {exc}")

        preferences = await self._get_preferences(user_id)
        knowledge_summary = await self._get_knowledge_summary(user_id)
        cognitive_summary = await self._get_cognitive_summary(user_id)
        error_payload = await self._get_error_summary(user_id)

        context = ProfileContext(
            preferences=preferences.get("explicit") or {},
            preference_version=preferences.get("version") or 0,
            knowledge_summary=knowledge_summary,
            cognitive_summary=cognitive_summary,
            error_summary=error_payload.get("summary") or {},
            recent_errors=error_payload.get("recent") or [],
            traits_prior=BigFiveTraits.model_validate(
                preferences.get("traits_prior") or {}
            ),
            trait_observation_state=preferences.get("trait_observation_state") or {},
            traits_coldstart_completed_at=preferences.get(
                "traits_coldstart_completed_at"
            ),
        )
        contract = await UserInsightCompiler(self.db).compile(
            user_id=user_id,
            profile_context=context,
        )
        context.user_projection_contract = contract
        context.user_insight_state = contract.canonical_state

        if self.redis:
            try:
                await self.redis.setex(
                    cache_key, self.CACHE_TTL_SECONDS, context.model_dump_json()
                )
            except Exception as exc:
                logger.warning(f"ProfileContext cache write failed: {exc}")

        # Write inline snapshot cache as a side-effect of compilation
        if context.user_insight_state is not None:
            stage34_modes = await AuroraStage34KillSwitchService().summary()
            await self._write_inline_snapshot_cache(
                user_id,
                context.user_insight_state.to_inline_snapshot(
                    capsule_mode=stage34_modes.get("capsule_mode", "shadow")
                ),
            )

        await self._attach_live_extensions(
            user_id,
            context,
            include_metacognition_prompt_extensions=include_metacognition_prompt_extensions,
        )
        return context

    async def _attach_live_extensions(
        self,
        user_id: UUID,
        context: ProfileContext,
        *,
        include_metacognition_prompt_extensions: bool,
    ) -> None:
        await self._populate_user_state_v1_payload(user_id, context)
        await self._attach_srl_phase_summary(user_id, context)
        await self._attach_metacognition_profile(user_id, context)
        await self._attach_metacognition_dashboard(user_id, context)
        await self._attach_metacognition_process_scaffolding(
            user_id, context, include_prompt_extensions=include_metacognition_prompt_extensions
        )
        await self._attach_idiographic_summary(user_id, context)

    async def _attach_srl_phase_summary(
        self, user_id: UUID, context: ProfileContext
    ) -> None:
        if context.user_insight_state is None:
            return
        try:
            aggregator_state = await StateAggregatorService(self.db).get_user_state(
                user_id,
                required_fields=("srl_phase",),
            )
            if aggregator_state.srl_phase is None:
                return
            context.user_insight_state.srl_phase = {
                "current_phase": aggregator_state.srl_phase.value.current_phase,
                "phase_started_at": (
                    aggregator_state.srl_phase.value.phase_started_at.isoformat()
                    if aggregator_state.srl_phase.value.phase_started_at
                    else None
                ),
                "confidence": aggregator_state.srl_phase.value.confidence,
                "source": aggregator_state.srl_phase.value.source,
                "freshness_seconds": aggregator_state.srl_phase.freshness_seconds,
            }
        except Exception as exc:
            logger.warning(f"Failed to attach SRL phase summary: {exc}")

    async def _attach_metacognition_profile(
        self,
        user_id: UUID,
        context: ProfileContext,
    ) -> None:
        try:
            service = MetacognitionService(self.db, redis=self.redis)
            context.metacognition_profile = await service.get_snapshot(user_id)
        except Exception as exc:
            logger.warning(f"Failed to attach metacognition profile: {exc}")

    # rule-as: ignore stage35_dashboard_existing_path
    async def _attach_metacognition_dashboard(
        self,
        user_id: UUID,
        context: ProfileContext,
    ) -> None:
        try:
            service = MetacognitionService(self.db, redis=self.redis)
            context.metacognition_dashboard = await service.build_dashboard_payload(
                user_id
            )
        except Exception as exc:
            logger.warning(f"Failed to attach metacognition dashboard: {exc}")

    # rule-as: ignore existing_prompt_and_stage30_path
    async def _attach_metacognition_process_scaffolding(
        self,
        user_id: UUID,
        context: ProfileContext,
        *,
        include_prompt_extensions: bool,
    ) -> None:
        try:
            service = MetacognitionService(self.db, redis=self.redis)
            context.metacognition_process_scaffolding = (
                await service.build_prompt_process_scaffolding(user_id, consume=True)
                if include_prompt_extensions
                else None
            )
        except Exception as exc:
            logger.warning(f"Failed to attach metacognition process scaffolding: {exc}")

    # rule-as: ignore existing_prompt_and_stage31_path
    async def _attach_idiographic_summary(
        self,
        user_id: UUID,
        context: ProfileContext,
    ) -> None:
        try:
            service = IdiographicAssociationService(
                self.db, redis=self.redis
            )
            summary = await service.build_aggregator_summary(user_id)
            context.idiographic_summary = (
                self._serialize_idiographic_summary(
                    summary,
                    mode=await service.kill_switch.get_mode(),
                )
                if summary is not None
                else None
            )
        except Exception as exc:
            logger.warning(f"Failed to attach idiographic summary: {exc}")

    async def _populate_user_state_v1_payload(
        self,
        user_id: UUID,
        context: ProfileContext,
    ) -> None:
        try:
            user_state = await StateAggregatorService(self.db).get_user_state(
                user_id,
                required_fields=self.USER_STATE_V1_FIELDS,
                now=_utcnow(),
            )
            payload = {
                "schema_version": user_state.schema_version,
            }
            for field_name in self.USER_STATE_V1_FIELDS:
                envelope = getattr(user_state, field_name, None)
                if envelope is None:
                    continue
                payload[field_name] = self._serialize_user_state_value(envelope)
            context.user_state_v1 = payload
        except Exception as exc:
            logger.warning(f"Failed to populate user_state_v1 payload: {exc}")

    @classmethod
    def _serialize_user_state_value(cls, value: Any) -> Any:
        if is_dataclass(value):
            return {
                field.name: cls._serialize_user_state_value(getattr(value, field.name))
                for field in fields(value)
            }
        if isinstance(value, datetime):
            return value.isoformat()
        if hasattr(value, "isoformat") and not isinstance(value, str):
            with_json = getattr(value, "isoformat", None)
            if callable(with_json):
                return value.isoformat()
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, dict):
            return {
                str(key): cls._serialize_user_state_value(item)
                for key, item in value.items()
                if item is not None
            }
        if isinstance(value, (list, tuple)):
            return [cls._serialize_user_state_value(item) for item in value]
        return value

    @staticmethod
    def _serialize_idiographic_summary(summary: Any, *, mode: str) -> dict[str, Any]:
        return {
            "top_associations": [
                {
                    "dim_pair": item.dim_pair,
                    "dim_a": item.dim_a,
                    "dim_b": item.dim_b,
                    "correlation": item.correlation,
                    "q_value": item.q_value,
                    "confidence": item.confidence,
                    "direction": item.direction,
                    "strength_label": item.strength_label,
                    "rendered_text": item.rendered_text,
                    "displayed": item.displayed,
                    "density_insufficient": item.density_insufficient,
                    "sample_days": item.sample_days,
                }
                for item in summary.top_associations
            ],
            "change_points_30d": [
                {
                    "dim": item.dim,
                    "change_date": item.change_date.isoformat(),
                    "confidence": item.confidence,
                    "rendered_text": item.rendered_text,
                }
                for item in summary.change_points_30d
            ],
            "sample_days": summary.sample_days,
            "confidence": summary.confidence,
            "disclaimer_text": summary.disclaimer_text,
            "mode": mode,
        }

    async def get_inline_snapshot(self, user_id: UUID) -> dict[str, Any] | None:
        """Retrieve the cached inline snapshot for a user, if available.

        This is a cache-only read path.  It does NOT trigger recompilation.
        Returns ``None`` on cache miss or parse failure.

        The cache is populated as a side effect of ``get_profile_context()``
        (via the ``user_insight_state.to_inline_snapshot()`` call) or can be
        populated by a future nearline hot-reload worker.
        """
        if not self.redis:
            return None
        cache_key = f"user:inline_snapshot:{user_id}"
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                import json as _json

                return _json.loads(cached)
        except Exception as exc:
            logger.warning(f"Inline snapshot cache read failed: {exc}")
        return None

    async def _write_inline_snapshot_cache(
        self, user_id: UUID, snapshot: dict[str, Any]
    ) -> None:
        """Write the inline snapshot to Redis. Called internally after compilation."""
        if not self.redis:
            return
        cache_key = f"user:inline_snapshot:{user_id}"
        try:
            import json as _json

            await self.redis.setex(
                cache_key, self.INLINE_SNAPSHOT_CACHE_TTL_SECONDS, _json.dumps(snapshot)
            )
        except Exception as exc:
            logger.warning(f"Inline snapshot cache write failed: {exc}")

    async def _get_preferences(self, user_id: UUID) -> dict[str, Any]:
        prefs = await self.pref_service.get_preferences(user_id)
        explicit = dict(prefs.explicit or {}) if prefs else {}
        inferred = dict(prefs.inferred or {}) if prefs else {}
        merged = dict(inferred)
        merged.update(explicit)
        return {
            "explicit": merged,
            "inferred": inferred,
            "version": prefs.version if prefs else 0,
            "traits_prior": dict(prefs.traits_prior or {}) if prefs else {},
            "trait_observation_state": (
                dict(prefs.trait_observation_state or {}) if prefs else {}
            ),
            "traits_coldstart_completed_at": (
                prefs.traits_coldstart_completed_at if prefs else None
            ),
        }

    async def _get_error_summary(self, user_id: UUID) -> dict[str, Any]:
        try:
            stats = await self.error_book_service.get_review_stats(user_id)
        except Exception as exc:
            logger.warning(f"Failed to load error stats: {exc}")
            stats = {}

        try:
            errors, _ = await self.error_book_service.list_errors(
                user_id,
                ErrorQueryParams(page=1, page_size=5, need_review=False),
            )
        except Exception as exc:
            logger.warning(f"Failed to load recent errors: {exc}")
            errors = []

        recent_errors: list[dict[str, Any]] = []
        for error in errors or []:
            recent_errors.append(
                {
                    "id": str(error.id),
                    "question_preview": (
                        error.question_text[:50]
                        if error.question_text
                        else "Image Question"
                    ),
                    "subject": error.subject_code,
                    "error_type": (
                        error.latest_analysis.get("error_type_label")
                        if error.latest_analysis
                        else "Unknown"
                    ),
                    "mastery": error.mastery_level,
                    "review_count": error.review_count,
                    "last_reviewed_at": (
                        error.last_reviewed_at.isoformat()
                        if error.last_reviewed_at
                        else None
                    ),
                }
            )
        return {"summary": stats or {}, "recent": recent_errors}

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
                .order_by(
                    UserNodeStatus.mastery_score.asc(),
                    nullslast(UserNodeStatus.last_study_at.desc()),
                )
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
                        float(item.get("mastery_score") or 0.0)
                        for item in fallback_mastery
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
                delta_raw = item.get("mastery_delta")
                delta = (
                    float(delta_raw)
                    if isinstance(delta_raw, (int, float))
                    else None
                )
                created_at_raw = item.get("created_at")
                changed_at = _utcnow()
                if isinstance(created_at_raw, str) and created_at_raw.strip():
                    try:
                        changed_at = datetime.fromisoformat(
                            created_at_raw.replace("Z", "+00:00")
                        ).replace(tzinfo=None)
                    except ValueError:
                        changed_at = _utcnow()
                recent_changes.append(
                    MasteryChange(
                        node_id=f"derived:{index}",
                        node_name=node_name,
                        old_mastery=0.0 if delta is not None else None,
                        new_mastery=max(0.0, delta) if delta is not None else None,
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
                type_scores[pattern_type] = (
                    type_scores.get(pattern_type, 0.0) + confidence_val
                )

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
