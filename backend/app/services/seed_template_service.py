"""
Seed Template Service
"""
from __future__ import annotations

import string
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from loguru import logger
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.seed_template import (
    SeedTemplate,
    SeedTemplatePack,
    SeedTemplateRewardLedger,
    SeedTemplateSignal,
    SeedTemplateSubscription,
    SeedTemplateVersion,
    TemplatePackStatus,
    TemplatePromotionState,
    TemplateSignalType,
    TemplateVersionStatus,
    TemplateVisibility,
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class _SafeDict(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


@dataclass
class PromotionResult:
    promotion_state: str
    support: int
    adoption_rate: float
    negative_feedback_rate: float
    report_rate: float


class SeedTemplateService:
    """Seed template packs/templates/versions service."""

    AUTO_PROMOTION_MIN_SUPPORT = 20
    AUTO_PROMOTION_MIN_ADOPTION = 0.18
    AUTO_PROMOTION_MAX_NEGATIVE = 0.15
    AUTO_PROMOTION_MAX_REPORT = 0.05

    SIGNAL_POINTS = {
        TemplateSignalType.LIKE.value: 1,
        TemplateSignalType.SAVE.value: 2,
        TemplateSignalType.REUSE.value: 3,
        TemplateSignalType.ADOPT_SUCCESS.value: 5,
    }

    BLOCK_TERMS = ("违法", "仇恨", "极端主义", "诈骗", "色情")

    async def list_packs(
        self,
        db: AsyncSession,
        *,
        scenario_type: str | None = None,
        visibility: str | None = None,
        current_user_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> list[SeedTemplatePack]:
        conditions = [SeedTemplatePack.deleted_at.is_(None)]
        if scenario_type:
            conditions.append(SeedTemplatePack.scenario_type == scenario_type)
        if visibility:
            conditions.append(SeedTemplatePack.visibility == visibility)
        else:
            public_conditions = [
                SeedTemplatePack.visibility == TemplateVisibility.PUBLIC.value,
                SeedTemplatePack.visibility == TemplateVisibility.OFFICIAL.value,
            ]
            if current_user_id:
                public_conditions.append(
                    and_(
                        SeedTemplatePack.visibility == TemplateVisibility.PRIVATE.value,
                        SeedTemplatePack.owner_id == current_user_id,
                    )
                )
            conditions.append(or_(*public_conditions))
        result = await db.execute(
            select(SeedTemplatePack)
            .where(and_(*conditions))
            .order_by(desc(SeedTemplatePack.updated_at))
            .limit(max(1, min(limit, 100)))
        )
        return list(result.scalars().all())

    async def create_pack(self, db: AsyncSession, *, data: dict[str, Any], owner_id: uuid.UUID) -> SeedTemplatePack:
        pack = SeedTemplatePack(
            scenario_type=str(data["scenario_type"]),
            name=str(data["name"]),
            description=data.get("description"),
            owner_id=owner_id,
            visibility=str(data.get("visibility", TemplateVisibility.PRIVATE.value)),
            status=TemplatePackStatus.DRAFT.value,
            language=str(data.get("language", "zh")),
            tags=data.get("tags"),
            extra_metadata=data.get("extra_metadata"),
        )
        db.add(pack)
        await db.flush()
        await db.refresh(pack)
        return pack

    async def get_template(
        self,
        db: AsyncSession,
        *,
        template_id: uuid.UUID,
    ) -> SeedTemplate | None:
        result = await db.execute(
            select(SeedTemplate).where(
                and_(SeedTemplate.id == template_id, SeedTemplate.deleted_at.is_(None))
            )
        )
        template = result.scalar_one_or_none()
        return template

    async def list_templates(
        self,
        db: AsyncSession,
        *,
        pack_id: uuid.UUID | None = None,
        owner_id: uuid.UUID | None = None,
        include_official: bool = True,
        limit: int = 50,
    ) -> list[SeedTemplate]:
        conditions = [SeedTemplate.deleted_at.is_(None)]
        if pack_id:
            conditions.append(SeedTemplate.pack_id == pack_id)
        if owner_id:
            conditions.append(SeedTemplate.owner_id == owner_id)
        elif include_official:
            conditions.append(or_(SeedTemplate.is_official.is_(True), SeedTemplate.owner_id.is_not(None)))
        result = await db.execute(
            select(SeedTemplate)
            .where(and_(*conditions))
            .order_by(desc(SeedTemplate.updated_at))
            .limit(max(1, min(limit, 200)))
        )
        return list(result.scalars().all())

    async def list_versions(
        self,
        db: AsyncSession,
        *,
        template_id: uuid.UUID,
        include_draft: bool = True,
        limit: int = 50,
    ) -> list[SeedTemplateVersion]:
        conditions = [
            SeedTemplateVersion.template_id == template_id,
            SeedTemplateVersion.deleted_at.is_(None),
        ]
        if not include_draft:
            conditions.append(SeedTemplateVersion.status == TemplateVersionStatus.PUBLISHED.value)
        result = await db.execute(
            select(SeedTemplateVersion)
            .where(and_(*conditions))
            .order_by(desc(SeedTemplateVersion.version_no))
            .limit(max(1, min(limit, 200)))
        )
        return list(result.scalars().all())

    async def get_pack(self, db: AsyncSession, *, pack_id: uuid.UUID) -> SeedTemplatePack | None:
        result = await db.execute(
            select(SeedTemplatePack).where(
                and_(SeedTemplatePack.id == pack_id, SeedTemplatePack.deleted_at.is_(None))
            )
        )
        return result.scalar_one_or_none()

    async def fork_template(
        self,
        db: AsyncSession,
        *,
        template: SeedTemplate,
        owner_id: uuid.UUID,
        target_pack_id: uuid.UUID | None = None,
        name: str | None = None,
    ) -> SeedTemplate:
        source_version = await self._get_current_or_latest_version(db, template.id)
        if source_version is None:
            raise ValueError("template_has_no_versions")

        pack_id = target_pack_id or template.pack_id
        fork = SeedTemplate(
            pack_id=pack_id,
            name=name or f"{template.name} (Fork)",
            template_role=template.template_role,
            forked_from_template_id=template.id,
            forked_from_version_id=source_version.id,
            owner_id=owner_id,
            is_official=False,
        )
        db.add(fork)
        await db.flush()

        version = SeedTemplateVersion(
            template_id=fork.id,
            version_no=1,
            status=TemplateVersionStatus.DRAFT.value,
            body=source_version.body,
            schema_json=source_version.schema_json,
            variables_schema=source_version.variables_schema,
            change_log="forked_from_upstream",
            created_by=owner_id,
            moderation_status="pending",
            promotion_state=TemplatePromotionState.NONE.value,
        )
        db.add(version)
        await db.flush()

        fork.current_version_id = version.id
        await db.flush()
        await db.refresh(fork)
        return fork

    async def create_or_update_version(
        self,
        db: AsyncSession,
        *,
        template: SeedTemplate,
        created_by: uuid.UUID,
        body: str,
        schema_json: dict[str, Any] | None,
        variables_schema: dict[str, Any] | None,
        change_log: str | None,
        overwrite_draft: bool = True,
    ) -> SeedTemplateVersion:
        latest = await self._get_latest_version(db, template.id)
        if overwrite_draft and latest and latest.status == TemplateVersionStatus.DRAFT.value:
            latest.body = body
            latest.schema_json = schema_json
            latest.variables_schema = variables_schema
            latest.change_log = change_log
            latest.created_by = created_by
            latest.updated_at = _utcnow()
            await db.flush()
            await db.refresh(latest)
            return latest

        version_no = 1 if latest is None else int(latest.version_no) + 1
        version = SeedTemplateVersion(
            template_id=template.id,
            version_no=version_no,
            status=TemplateVersionStatus.DRAFT.value,
            body=body,
            schema_json=schema_json,
            variables_schema=variables_schema,
            change_log=change_log,
            created_by=created_by,
            moderation_status="pending",
            promotion_state=TemplatePromotionState.NONE.value,
        )
        db.add(version)
        await db.flush()
        await db.refresh(version)
        return version

    async def publish_version(
        self,
        db: AsyncSession,
        *,
        template: SeedTemplate,
        actor_id: uuid.UUID,
        version_id: uuid.UUID | None = None,
        is_superuser: bool = False,
    ) -> SeedTemplateVersion:
        version = await self._resolve_publish_version(db, template.id, version_id)
        if version is None:
            raise ValueError("version_not_found")
        if version.status != TemplateVersionStatus.DRAFT.value:
            raise ValueError("only_draft_can_publish")

        gate = self._quality_gate(version.body)
        moderation = self._moderation_gate(version.body)
        version.quality_gate_report = gate
        version.moderation_report = moderation

        if not gate["passed"]:
            raise ValueError("quality_gate_failed")
        if not moderation["passed"]:
            version.moderation_status = "blocked"
            version.promotion_state = TemplatePromotionState.BLOCKED.value
            raise ValueError("moderation_blocked")

        if template.is_official and not is_superuser:
            raise ValueError("official_template_requires_admin")

        version.status = TemplateVersionStatus.PUBLISHED.value
        version.published_at = _utcnow()
        version.moderation_status = "approved_auto" if not is_superuser else "approved"
        version.promotion_state = TemplatePromotionState.PUBLIC_CANDIDATE.value
        template.current_version_id = version.id
        template.updated_at = _utcnow()

        pack = await self.get_pack(db, pack_id=template.pack_id)
        if pack:
            pack.status = TemplatePackStatus.PUBLISHED.value
            pack.updated_at = _utcnow()

        await db.flush()
        await db.refresh(version)
        return version

    async def add_signal(
        self,
        db: AsyncSession,
        *,
        version: SeedTemplateVersion,
        user_id: uuid.UUID,
        signal_type: str,
        score: float,
        meta: dict[str, Any] | None,
    ) -> tuple[SeedTemplateSignal, PromotionResult]:
        signal = SeedTemplateSignal(
            template_version_id=version.id,
            user_id=user_id,
            signal_type=signal_type,
            score=max(0.0, float(score)),
            meta=meta,
        )
        db.add(signal)
        await db.flush()
        await self._record_reward_if_needed(
            db,
            user_id=user_id,
            template_id=version.template_id,
            signal_type=signal_type,
            signal_score=score,
        )
        promotion = await self._evaluate_promotion(db, version.id)
        version.promotion_state = promotion.promotion_state
        await db.flush()
        await db.refresh(signal)
        return signal, promotion

    async def subscribe(
        self,
        db: AsyncSession,
        *,
        template_id: uuid.UUID,
        user_id: uuid.UUID,
        priority: int = 0,
    ) -> SeedTemplateSubscription:
        existing = await db.execute(
            select(SeedTemplateSubscription).where(
                and_(
                    SeedTemplateSubscription.template_id == template_id,
                    SeedTemplateSubscription.user_id == user_id,
                    SeedTemplateSubscription.deleted_at.is_(None),
                )
            )
        )
        sub = existing.scalar_one_or_none()
        if sub:
            sub.is_enabled = True
            sub.priority = priority
            sub.updated_at = _utcnow()
            await db.flush()
            return sub
        sub = SeedTemplateSubscription(
            template_id=template_id,
            user_id=user_id,
            is_enabled=True,
            priority=priority,
        )
        db.add(sub)
        await db.flush()
        return sub

    async def list_subscriptions(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        only_enabled: bool = True,
        limit: int = 100,
    ) -> list[SeedTemplateSubscription]:
        conditions = [
            SeedTemplateSubscription.user_id == user_id,
            SeedTemplateSubscription.deleted_at.is_(None),
        ]
        if only_enabled:
            conditions.append(SeedTemplateSubscription.is_enabled.is_(True))
        result = await db.execute(
            select(SeedTemplateSubscription)
            .where(and_(*conditions))
            .order_by(desc(SeedTemplateSubscription.updated_at))
            .limit(max(1, min(limit, 300)))
        )
        return list(result.scalars().all())

    async def unsubscribe(self, db: AsyncSession, *, template_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        result = await db.execute(
            select(SeedTemplateSubscription).where(
                and_(
                    SeedTemplateSubscription.template_id == template_id,
                    SeedTemplateSubscription.user_id == user_id,
                    SeedTemplateSubscription.deleted_at.is_(None),
                )
            )
        )
        sub = result.scalar_one_or_none()
        if not sub:
            return False
        await sub.delete(db, soft=True)
        return True

    async def instantiate(
        self,
        db: AsyncSession,
        *,
        template: SeedTemplate,
        variables: dict[str, Any],
        version_id: uuid.UUID | None = None,
        context: dict[str, Any] | None = None,
    ) -> tuple[SeedTemplateVersion, str, list[str], dict[str, Any]]:
        version = await self._resolve_publish_version(db, template.id, version_id)
        if version is None:
            raise ValueError("version_not_found")
        merged_vars = dict(context or {})
        merged_vars.update(variables)
        rendered = version.body.format_map(_SafeDict(merged_vars))
        unresolved = sorted({field for _, field, _, _ in string.Formatter().parse(version.body) if field and field not in merged_vars})
        metadata = {
            "seed_template_id": str(template.id),
            "seed_template_version_id": str(version.id),
            "seed_template_source": "official" if template.is_official else ("fork" if template.forked_from_template_id else "public"),
            "seed_template_pack": str(template.pack_id),
            "template_instantiation_context": context or {},
        }
        return version, rendered, unresolved, metadata

    async def get_review_queue(self, db: AsyncSession, *, limit: int = 200) -> list[SeedTemplateVersion]:
        result = await db.execute(
            select(SeedTemplateVersion)
            .where(
                and_(
                    SeedTemplateVersion.deleted_at.is_(None),
                    SeedTemplateVersion.status == TemplateVersionStatus.PUBLISHED.value,
                    SeedTemplateVersion.promotion_state.in_(
                        [TemplatePromotionState.PUBLIC_CANDIDATE.value, TemplatePromotionState.BLOCKED.value]
                    ),
                )
            )
            .order_by(desc(SeedTemplateVersion.updated_at))
            .limit(max(1, min(limit, 500)))
        )
        return list(result.scalars().all())

    async def admin_review(self, db: AsyncSession, *, version_id: uuid.UUID, approve: bool, note: str | None = None) -> SeedTemplateVersion:
        result = await db.execute(
            select(SeedTemplateVersion).where(
                and_(
                    SeedTemplateVersion.id == version_id,
                    SeedTemplateVersion.deleted_at.is_(None),
                )
            )
        )
        version = result.scalar_one_or_none()
        if version is None:
            raise ValueError("version_not_found")
        version.moderation_status = "approved" if approve else "rejected"
        if approve and version.promotion_state == TemplatePromotionState.BLOCKED.value:
            version.promotion_state = TemplatePromotionState.PUBLIC_CANDIDATE.value
        if not approve:
            version.promotion_state = TemplatePromotionState.BLOCKED.value
            version.status = TemplateVersionStatus.REJECTED.value
        report = dict(version.moderation_report or {})
        if note:
            report["admin_note"] = note
        version.moderation_report = report
        await db.flush()
        await db.refresh(version)
        return version

    async def promotion_dashboard(self, db: AsyncSession) -> dict[str, Any]:
        total_versions = await db.execute(
            select(func.count()).select_from(SeedTemplateVersion).where(SeedTemplateVersion.deleted_at.is_(None))
        )
        by_state = await db.execute(
            select(SeedTemplateVersion.promotion_state, func.count())
            .where(SeedTemplateVersion.deleted_at.is_(None))
            .group_by(SeedTemplateVersion.promotion_state)
        )
        total_signals = await db.execute(
            select(func.count()).select_from(SeedTemplateSignal).where(SeedTemplateSignal.deleted_at.is_(None))
        )
        return {
            "total_versions": int(total_versions.scalar() or 0),
            "total_signals": int(total_signals.scalar() or 0),
            "promotion_state_breakdown": {str(row[0]): int(row[1]) for row in by_state.all()},
        }

    async def _record_reward_if_needed(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        template_id: uuid.UUID,
        signal_type: str,
        signal_score: float,
    ) -> None:
        points = self.SIGNAL_POINTS.get(signal_type, 0)
        if points <= 0:
            return
        points = int(points * max(1.0, float(signal_score)))
        ledger = SeedTemplateRewardLedger(
            user_id=user_id,
            template_id=template_id,
            event_type="template_signal_reward",
            points_delta=points,
            source_signal=signal_type,
            occurred_at=_utcnow(),
        )
        db.add(ledger)

    async def _evaluate_promotion(self, db: AsyncSession, version_id: uuid.UUID) -> PromotionResult:
        if not settings.ENABLE_SEED_TEMPLATE_AUTO_PROMOTION_V1:
            return PromotionResult(
                promotion_state=TemplatePromotionState.PUBLIC_CANDIDATE.value,
                support=0,
                adoption_rate=0.0,
                negative_feedback_rate=0.0,
                report_rate=0.0,
            )

        result = await db.execute(
            select(SeedTemplateSignal.signal_type, func.count())
            .where(
                and_(
                    SeedTemplateSignal.template_version_id == version_id,
                    SeedTemplateSignal.deleted_at.is_(None),
                )
            )
            .group_by(SeedTemplateSignal.signal_type)
        )
        counts = {str(row[0]): int(row[1]) for row in result.all()}
        support = sum(counts.values())
        if support <= 0:
            return PromotionResult(
                promotion_state=TemplatePromotionState.PUBLIC_CANDIDATE.value,
                support=0,
                adoption_rate=0.0,
                negative_feedback_rate=0.0,
                report_rate=0.0,
            )
        adoption = counts.get(TemplateSignalType.REUSE.value, 0) + counts.get(TemplateSignalType.ADOPT_SUCCESS.value, 0)
        negative = counts.get(TemplateSignalType.DOWNVOTE.value, 0)
        reports = counts.get(TemplateSignalType.REPORT.value, 0)
        adoption_rate = adoption / support
        negative_rate = negative / support
        report_rate = reports / support
        state = TemplatePromotionState.PUBLIC_CANDIDATE.value
        if report_rate >= self.AUTO_PROMOTION_MAX_REPORT:
            state = TemplatePromotionState.BLOCKED.value
        elif (
            support >= self.AUTO_PROMOTION_MIN_SUPPORT
            and adoption_rate >= self.AUTO_PROMOTION_MIN_ADOPTION
            and negative_rate <= self.AUTO_PROMOTION_MAX_NEGATIVE
            and report_rate <= self.AUTO_PROMOTION_MAX_REPORT
        ):
            state = TemplatePromotionState.PUBLIC_RECOMMENDED.value
        return PromotionResult(
            promotion_state=state,
            support=support,
            adoption_rate=round(adoption_rate, 4),
            negative_feedback_rate=round(negative_rate, 4),
            report_rate=round(report_rate, 4),
        )

    async def _get_latest_version(self, db: AsyncSession, template_id: uuid.UUID) -> SeedTemplateVersion | None:
        result = await db.execute(
            select(SeedTemplateVersion)
            .where(
                and_(
                    SeedTemplateVersion.template_id == template_id,
                    SeedTemplateVersion.deleted_at.is_(None),
                )
            )
            .order_by(desc(SeedTemplateVersion.version_no))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_current_or_latest_version(self, db: AsyncSession, template_id: uuid.UUID) -> SeedTemplateVersion | None:
        template = await self.get_template(db, template_id=template_id)
        if template is None:
            return None
        if template.current_version_id:
            result = await db.execute(
                select(SeedTemplateVersion).where(
                    and_(
                        SeedTemplateVersion.id == template.current_version_id,
                        SeedTemplateVersion.deleted_at.is_(None),
                    )
                )
            )
            version = result.scalar_one_or_none()
            if version is not None:
                return version
        return await self._get_latest_version(db, template_id)

    async def _resolve_publish_version(
        self,
        db: AsyncSession,
        template_id: uuid.UUID,
        version_id: uuid.UUID | None,
    ) -> SeedTemplateVersion | None:
        if version_id:
            result = await db.execute(
                select(SeedTemplateVersion).where(
                    and_(
                        SeedTemplateVersion.id == version_id,
                        SeedTemplateVersion.template_id == template_id,
                        SeedTemplateVersion.deleted_at.is_(None),
                    )
                )
            )
            return result.scalar_one_or_none()
        latest = await self._get_latest_version(db, template_id)
        return latest

    def _quality_gate(self, body: str) -> dict[str, Any]:
        required = ["goal", "constraints", "milestones", "acceptance_criteria", "risks"]
        lower_body = body.lower()
        covered = [item for item in required if item in lower_body]
        score = len(covered) / len(required)
        return {
            "score": round(score, 4),
            "required": required,
            "covered": covered,
            "missing": [item for item in required if item not in covered],
            "passed": score >= 0.6,
        }

    def _moderation_gate(self, body: str) -> dict[str, Any]:
        hits = [term for term in self.BLOCK_TERMS if term in body]
        passed = len(hits) == 0
        return {
            "passed": passed,
            "blocked_terms": hits,
        }
