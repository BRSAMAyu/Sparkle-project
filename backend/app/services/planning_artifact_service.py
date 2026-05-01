"""
PlanningArtifactService — CRUD + governance for versioned planning artifacts.

Artifacts are the governance layer: GLOBAL_COMPASS, STRATEGY_MAP, DECISION_LOG,
RISK_REGISTER, etc. They are versioned, require approval before becoming
authoritative, and enforce anti-drift rules from Section 8.3.

Phase 3 of the Card Protocol.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import EventBus
from app.models.card_protocol import (
    ArtifactStatus,
    ArtifactType,
    PlanningArtifact,
)


class PlanningArtifactService:
    """Manages PlanningArtifact lifecycle with governance enforcement."""

    def __init__(self, db: AsyncSession, event_bus: EventBus | None = None):
        self.db = db
        self.event_bus = event_bus

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_artifact(
        self,
        *,
        plan_card_id: uuid.UUID,
        artifact_type: ArtifactType,
        payload: dict,
        created_by_agent: str = "system",
        based_on_versions: dict | None = None,
    ) -> PlanningArtifact:
        """Create a new DRAFT artifact, auto-incrementing version."""
        # Versioning must be monotonic across all artifact states, not just APPROVED.
        # Otherwise a lingering DRAFT / PROPOSED artifact can cause duplicate version
        # allocation the next time a new artifact is created.
        stmt = select(func.max(PlanningArtifact.version)).where(
            PlanningArtifact.plan_card_id == plan_card_id,
            PlanningArtifact.artifact_type == artifact_type,
            PlanningArtifact.not_deleted_filter(),
        )
        result = await self.db.execute(stmt)
        latest_version = result.scalar_one_or_none() or 0
        next_version = latest_version + 1

        artifact = PlanningArtifact(
            plan_card_id=plan_card_id,
            artifact_type=artifact_type,
            version=next_version,
            status=ArtifactStatus.DRAFT,
            payload=payload,
            based_on_versions=based_on_versions or {},
            created_by_agent=created_by_agent,
        )
        self.db.add(artifact)
        await self.db.flush()

        if self.event_bus:
            await self.event_bus.publish(
                "planning_artifact.created",
                {
                    "artifact_id": str(artifact.id),
                    "plan_card_id": str(plan_card_id),
                    "artifact_type": artifact_type.value,
                    "version": next_version,
                },
            )
        return artifact

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------

    async def propose_artifact(self, artifact_id: uuid.UUID) -> PlanningArtifact | None:
        """DRAFT → PROPOSED."""
        artifact = await self._get_artifact(artifact_id)
        if not artifact or artifact.status != ArtifactStatus.DRAFT:
            return None
        artifact.status = ArtifactStatus.PROPOSED
        await self.db.flush()
        return artifact

    async def approve_artifact(
        self,
        artifact_id: uuid.UUID,
        approved_by_user_id: uuid.UUID | None = None,
    ) -> PlanningArtifact | None:
        """PROPOSED → APPROVED. Auto-supersedes previous APPROVED of same type."""
        artifact = await self._get_artifact(artifact_id)
        if not artifact or artifact.status != ArtifactStatus.PROPOSED:
            return None

        # Auto-supersede previous APPROVED
        prev = await self.get_approved(artifact.plan_card_id, artifact.artifact_type)
        if prev and prev.id != artifact.id:
            prev.status = ArtifactStatus.SUPERSEDED
            prev.superseded_at = datetime.utcnow()

        artifact.status = ArtifactStatus.APPROVED
        artifact.approved_by_user_id = approved_by_user_id
        artifact.approved_at = datetime.utcnow()
        await self.db.flush()

        if self.event_bus:
            await self.event_bus.publish(
                "planning_artifact.approved",
                {
                    "artifact_id": str(artifact.id),
                    "plan_card_id": str(artifact.plan_card_id),
                    "artifact_type": artifact.artifact_type.value,
                    "version": artifact.version,
                },
            )
        logger.info(
            "PlanningArtifactService: approved {} v{} for plan {}",
            artifact.artifact_type.value,
            artifact.version,
            artifact.plan_card_id,
        )
        return artifact

    async def auto_approve_artifact(
        self,
        artifact_id: uuid.UUID,
    ) -> PlanningArtifact | None:
        """System auto-approval for deterministic artifacts (compass, strategy)."""
        return await self.approve_artifact(artifact_id, approved_by_user_id=None)

    async def reject_artifact(self, artifact_id: uuid.UUID) -> PlanningArtifact | None:
        """PROPOSED → REJECTED."""
        artifact = await self._get_artifact(artifact_id)
        if not artifact or artifact.status != ArtifactStatus.PROPOSED:
            return None
        artifact.status = ArtifactStatus.REJECTED
        await self.db.flush()
        return artifact

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_approved(
        self, plan_card_id: uuid.UUID, artifact_type: ArtifactType
    ) -> PlanningArtifact | None:
        """Get the current APPROVED artifact for a plan + type."""
        stmt = (
            select(PlanningArtifact)
            .where(
                PlanningArtifact.plan_card_id == plan_card_id,
                PlanningArtifact.artifact_type == artifact_type,
                PlanningArtifact.status == ArtifactStatus.APPROVED,
                PlanningArtifact.not_deleted_filter(),
            )
            .order_by(PlanningArtifact.version.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_artifact(self, artifact_id: uuid.UUID) -> PlanningArtifact | None:
        return await self._get_artifact(artifact_id)

    async def get_artifact_history(
        self, plan_card_id: uuid.UUID, artifact_type: ArtifactType
    ) -> list[PlanningArtifact]:
        """Get version chain for an artifact type."""
        stmt = (
            select(PlanningArtifact)
            .where(
                PlanningArtifact.plan_card_id == plan_card_id,
                PlanningArtifact.artifact_type == artifact_type,
                PlanningArtifact.not_deleted_filter(),
            )
            .order_by(PlanningArtifact.version.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_or_create_approved(
        self,
        *,
        plan_card_id: uuid.UUID,
        artifact_type: ArtifactType,
        default_payload: dict,
        created_by_agent: str = "system",
    ) -> PlanningArtifact:
        """Get existing APPROVED or create + auto-approve a default one."""
        existing = await self.get_approved(plan_card_id, artifact_type)
        if existing:
            return existing
        artifact = await self.create_artifact(
            plan_card_id=plan_card_id,
            artifact_type=artifact_type,
            payload=default_payload,
            created_by_agent=created_by_agent,
        )
        await self.propose_artifact(artifact.id)
        return (await self.auto_approve_artifact(artifact.id)) or artifact

    # ------------------------------------------------------------------
    # Anti-drift (Section 8.3)
    # ------------------------------------------------------------------

    async def validate_freshness(
        self,
        plan_card_id: uuid.UUID,
        based_on_versions: dict[str, int],
    ) -> bool:
        """Check whether claimed versions match current APPROVED versions.

        Returns True if fresh, False if stale (anti-drift rule 6).
        """
        if not based_on_versions:
            return True  # No claim = no drift check

        for type_str, claimed_version in based_on_versions.items():
            try:
                art_type = ArtifactType(type_str)
            except ValueError:
                continue
            current = await self.get_approved(plan_card_id, art_type)
            actual_version = current.version if current else 0
            if actual_version != claimed_version:
                logger.warning(
                    "Anti-drift: {} claimed v{} but current is v{} for plan {}",
                    type_str,
                    claimed_version,
                    actual_version,
                    plan_card_id,
                )
                return False
        return True

    # ------------------------------------------------------------------
    # Update payload
    # ------------------------------------------------------------------

    async def update_payload(
        self, artifact_id: uuid.UUID, payload_patch: dict
    ) -> PlanningArtifact | None:
        """Merge payload_patch into existing artifact payload."""
        artifact = await self._get_artifact(artifact_id)
        if not artifact:
            return None
        current = dict(artifact.payload or {})
        current.update(payload_patch)
        artifact.payload = current
        await self.db.flush()
        return artifact

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _get_artifact(self, artifact_id: uuid.UUID) -> PlanningArtifact | None:
        stmt = select(PlanningArtifact).where(
            PlanningArtifact.id == artifact_id,
            PlanningArtifact.not_deleted_filter(),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
