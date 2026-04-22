from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.metrics import SPARKLE_SKILL_COUNT_PER_USER
from app.models.aurora_stage21 import SharedSkill, UserSkill
from app.services.aurora_stage21_kill_switch_service import AuroraStage21KillSwitchService
from app.services.skill_schema import (
    conditions_to_json,
    normalize_activation_conditions,
    normalize_examples,
    normalize_name,
    normalize_pattern_template,
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class SkillStoreService:
    USER_SKILL_LIMIT = 50

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.kill_switches = AuroraStage21KillSwitchService()

    async def list_user_skills(self, *, user_id: UUID, include_inactive: bool = True) -> list[UserSkill]:
        if not await self.kill_switches.is_enabled("skill_store_enabled"):
            return []
        stmt = select(UserSkill).where(
            UserSkill.user_id == user_id,
            UserSkill.deleted_at.is_(None),
        )
        if not include_inactive:
            stmt = stmt.where(UserSkill.active.is_(True))
        stmt = stmt.order_by(UserSkill.updated_at.desc(), UserSkill.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_user_skill(self, *, user_id: UUID, skill_id: UUID) -> UserSkill | None:
        if not await self.kill_switches.is_enabled("skill_store_enabled"):
            return None
        result = await self.db.execute(
            select(UserSkill).where(
                UserSkill.id == skill_id,
                UserSkill.user_id == user_id,
                UserSkill.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def create_skill(self, *, user_id: UUID, payload: dict[str, Any]) -> UserSkill:
        await self._ensure_store_enabled()
        await self._ensure_under_limit(user_id)

        skill = UserSkill(
            user_id=user_id,
            name=normalize_name(str(payload.get("name") or "")),
            pattern_template=normalize_pattern_template(str(payload.get("pattern_template") or "")),
            activation_conditions=conditions_to_json(normalize_activation_conditions(payload.get("activation_conditions"))),
            examples=list(normalize_examples(payload.get("examples"))),
            active=bool(payload.get("active", True)),
            forked_from_share_id=payload.get("forked_from_share_id"),
            shared_catalog_id=payload.get("shared_catalog_id"),
            forked_at=payload.get("forked_at"),
            privacy_level=str(payload.get("privacy_level") or "private"),
            schema_version="skill.v1",
        )
        self.db.add(skill)
        await self.db.commit()
        await self.db.refresh(skill)
        await self._observe_count(user_id)
        return skill

    async def update_skill(self, *, user_id: UUID, skill_id: UUID, payload: dict[str, Any]) -> UserSkill:
        await self._ensure_store_enabled()
        skill = await self.get_user_skill(user_id=user_id, skill_id=skill_id)
        if skill is None:
            raise ValueError("Skill not found")

        structural_change = False
        if "name" in payload:
            normalized = normalize_name(str(payload.get("name") or ""))
            structural_change = structural_change or normalized != skill.name
            skill.name = normalized
        if "pattern_template" in payload:
            normalized = normalize_pattern_template(str(payload.get("pattern_template") or ""))
            structural_change = structural_change or normalized != skill.pattern_template
            skill.pattern_template = normalized
        if "activation_conditions" in payload:
            normalized = conditions_to_json(normalize_activation_conditions(payload.get("activation_conditions")))
            structural_change = structural_change or normalized != (skill.activation_conditions or [])
            skill.activation_conditions = normalized
        if "examples" in payload:
            normalized = list(normalize_examples(payload.get("examples")))
            structural_change = structural_change or normalized != (skill.examples or [])
            skill.examples = normalized
        if "active" in payload:
            skill.active = bool(payload.get("active"))

        if structural_change:
            skill.usage_count = 0
            skill.last_activated_at = None
        skill.updated_at = _utcnow()
        await self.db.commit()
        await self.db.refresh(skill)
        await self._observe_count(user_id)
        return skill

    async def delete_skill(self, *, user_id: UUID, skill_id: UUID) -> None:
        await self._ensure_store_enabled()
        skill = await self.get_user_skill(user_id=user_id, skill_id=skill_id)
        if skill is None:
            return
        skill.deleted_at = _utcnow()
        skill.updated_at = _utcnow()
        await self.db.commit()
        await self._observe_count(user_id)

    async def set_active(self, *, user_id: UUID, skill_id: UUID, active: bool) -> UserSkill:
        return await self.update_skill(user_id=user_id, skill_id=skill_id, payload={"active": active})

    async def fork_shared_skill(self, *, user_id: UUID, shared_skill_id: UUID) -> UserSkill:
        await self._ensure_store_enabled()
        await self._ensure_under_limit(user_id)
        shared = await self._load_shared_skill(shared_skill_id)
        if shared is None:
            raise ValueError("Shared skill not found")
        return await self.create_skill(
            user_id=user_id,
            payload={
                "name": shared.name,
                "pattern_template": shared.pattern_template,
                "activation_conditions": shared.activation_conditions,
                "examples": shared.examples,
                "forked_from_share_id": shared.id,
                "privacy_level": "private",
                "active": True,
                "forked_at": _utcnow(),
            },
        )

    async def increment_usage(self, *, user_id: UUID, skill_ids: list[UUID], activated_at: datetime | None = None) -> None:
        if not await self.kill_switches.is_enabled("skill_store_enabled"):
            return
        if not skill_ids:
            return
        result = await self.db.execute(
            select(UserSkill).where(
                UserSkill.user_id == user_id,
                UserSkill.id.in_(skill_ids),
                UserSkill.deleted_at.is_(None),
            )
        )
        now = activated_at or _utcnow()
        for skill in result.scalars().all():
            skill.usage_count = int(skill.usage_count or 0) + 1
            skill.last_activated_at = now
            skill.updated_at = now
        await self.db.commit()
        await self._observe_count(user_id)

    async def _ensure_under_limit(self, user_id: UUID) -> None:
        result = await self.db.execute(
            select(func.count(UserSkill.id)).where(
                UserSkill.user_id == user_id,
                UserSkill.deleted_at.is_(None),
            )
        )
        count = int(result.scalar() or 0)
        if count >= self.USER_SKILL_LIMIT:
            raise ValueError("Skill limit reached; archive or delete an existing skill first")

    async def _load_shared_skill(self, shared_skill_id: UUID) -> SharedSkill | None:
        result = await self.db.execute(
            select(SharedSkill).where(
                SharedSkill.id == shared_skill_id,
                SharedSkill.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def _observe_count(self, user_id: UUID) -> None:
        result = await self.db.execute(
            select(func.count(UserSkill.id)).where(
                UserSkill.user_id == user_id,
                UserSkill.deleted_at.is_(None),
            )
        )
        SPARKLE_SKILL_COUNT_PER_USER.observe(float(result.scalar() or 0))

    async def _ensure_store_enabled(self) -> None:
        if not await self.kill_switches.is_enabled("skill_store_enabled"):
            raise ValueError("Skill store disabled")
