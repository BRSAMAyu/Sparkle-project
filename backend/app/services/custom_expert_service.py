from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent_profiles import AgentRole, ModelTier, get_public_agent_catalog
from app.models.custom_expert import CustomExpertProfile, CustomExpertTeam

CUSTOM_EXPERT_PREFIX = "custom_expert:"


def make_custom_expert_id(expert_id: uuid.UUID | str) -> str:
    return f"{CUSTOM_EXPERT_PREFIX}{expert_id}"


def is_custom_expert_id(value: str | None) -> bool:
    return str(value or "").startswith(CUSTOM_EXPERT_PREFIX)


def parse_custom_expert_uuid(value: str | None) -> uuid.UUID | None:
    if not is_custom_expert_id(value):
        return None
    try:
        return uuid.UUID(str(value).split(CUSTOM_EXPERT_PREFIX, 1)[1].strip())
    except Exception:
        return None


class CustomExpertService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_custom_experts(self, user_id: str) -> list[CustomExpertProfile]:
        result = await self.db.execute(
            select(CustomExpertProfile)
            .where(
                CustomExpertProfile.user_id == uuid.UUID(str(user_id)),
                CustomExpertProfile.is_enabled.is_(True),
                CustomExpertProfile.deleted_at.is_(None),
            )
            .order_by(CustomExpertProfile.updated_at.desc())
        )
        return list(result.scalars().all())

    async def list_custom_teams(self, user_id: str) -> list[CustomExpertTeam]:
        result = await self.db.execute(
            select(CustomExpertTeam)
            .where(
                CustomExpertTeam.user_id == uuid.UUID(str(user_id)),
                CustomExpertTeam.is_enabled.is_(True),
                CustomExpertTeam.deleted_at.is_(None),
            )
            .order_by(CustomExpertTeam.updated_at.desc())
        )
        return list(result.scalars().all())

    async def create_custom_expert(
        self,
        *,
        user_id: str,
        name: str,
        system_prompt: str,
        description: str | None = None,
        base_expert_id: str | None = None,
        preferred_model_key: str | None = None,
        preferred_model_tier: str | None = None,
        reasoning_mode: str = "balanced",
        metadata_json: dict[str, Any] | None = None,
    ) -> CustomExpertProfile:
        profile = CustomExpertProfile(
            user_id=uuid.UUID(str(user_id)),
            name=name.strip(),
            description=(description or "").strip() or None,
            system_prompt=system_prompt.strip(),
            base_expert_id=(base_expert_id or "").strip() or None,
            preferred_model_key=(preferred_model_key or "").strip() or None,
            preferred_model_tier=(preferred_model_tier or "").strip() or None,
            reasoning_mode=(reasoning_mode or "balanced").strip() or "balanced",
            metadata_json=metadata_json or {},
        )
        self.db.add(profile)
        await self.db.flush()
        await self.db.refresh(profile)
        return profile

    async def update_custom_expert(
        self,
        *,
        user_id: str,
        expert_id: str,
        payload: dict[str, Any],
    ) -> CustomExpertProfile | None:
        profile = await self.get_custom_expert(user_id=user_id, expert_id=expert_id)
        if profile is None:
            return None
        for field_name in (
            "name",
            "description",
            "system_prompt",
            "base_expert_id",
            "preferred_model_key",
            "preferred_model_tier",
            "reasoning_mode",
            "is_enabled",
        ):
            if field_name in payload:
                setattr(profile, field_name, payload[field_name])
        if "metadata_json" in payload:
            profile.metadata_json = payload["metadata_json"] or {}
        await self.db.flush()
        await self.db.refresh(profile)
        return profile

    async def soft_delete_custom_expert(self, *, user_id: str, expert_id: str) -> bool:
        profile = await self.get_custom_expert(user_id=user_id, expert_id=expert_id)
        if profile is None:
            return False
        profile.soft_delete()
        await self.db.flush()
        return True

    async def create_custom_team(
        self,
        *,
        user_id: str,
        name: str,
        expert_ids: list[str],
        collaboration_mode: str = "auto",
        answer_expert_ids: list[str] | None = None,
        description: str | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> CustomExpertTeam:
        team = CustomExpertTeam(
            user_id=uuid.UUID(str(user_id)),
            name=name.strip(),
            description=(description or "").strip() or None,
            collaboration_mode=(collaboration_mode or "auto").strip() or "auto",
            expert_ids=expert_ids,
            answer_expert_ids=answer_expert_ids or [],
            metadata_json=metadata_json or {},
        )
        self.db.add(team)
        await self.db.flush()
        await self.db.refresh(team)
        return team

    async def update_custom_team(
        self,
        *,
        user_id: str,
        team_id: str,
        payload: dict[str, Any],
    ) -> CustomExpertTeam | None:
        team = await self.get_custom_team(user_id=user_id, team_id=team_id)
        if team is None:
            return None
        for field_name in (
            "name",
            "description",
            "collaboration_mode",
            "expert_ids",
            "answer_expert_ids",
            "is_enabled",
        ):
            if field_name in payload:
                setattr(team, field_name, payload[field_name])
        if "metadata_json" in payload:
            team.metadata_json = payload["metadata_json"] or {}
        await self.db.flush()
        await self.db.refresh(team)
        return team

    async def soft_delete_custom_team(self, *, user_id: str, team_id: str) -> bool:
        team = await self.get_custom_team(user_id=user_id, team_id=team_id)
        if team is None:
            return False
        team.soft_delete()
        await self.db.flush()
        return True

    async def get_custom_expert(self, *, user_id: str, expert_id: str) -> CustomExpertProfile | None:
        expert_uuid = parse_custom_expert_uuid(expert_id)
        if expert_uuid is None:
            try:
                expert_uuid = uuid.UUID(str(expert_id))
            except Exception:
                return None
        result = await self.db.execute(
            select(CustomExpertProfile).where(
                CustomExpertProfile.id == expert_uuid,
                CustomExpertProfile.user_id == uuid.UUID(str(user_id)),
                CustomExpertProfile.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_custom_team(self, *, user_id: str, team_id: str) -> CustomExpertTeam | None:
        try:
            team_uuid = uuid.UUID(str(team_id))
        except Exception:
            return None
        result = await self.db.execute(
            select(CustomExpertTeam).where(
                CustomExpertTeam.id == team_uuid,
                CustomExpertTeam.user_id == uuid.UUID(str(user_id)),
                CustomExpertTeam.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def load_runtime_profiles(
        self,
        *,
        user_id: str,
        expert_ids: list[str],
    ) -> dict[str, dict[str, Any]]:
        resolved: dict[str, dict[str, Any]] = {}
        for expert_id in expert_ids:
            profile = await self.get_custom_expert(user_id=user_id, expert_id=expert_id)
            if profile is None or not profile.is_enabled:
                continue
            resolved[make_custom_expert_id(profile.id)] = self.serialize_runtime_profile(profile)
        return resolved

    @staticmethod
    def serialize_runtime_profile(profile: CustomExpertProfile) -> dict[str, Any]:
        return {
            "id": make_custom_expert_id(profile.id),
            "db_id": str(profile.id),
            "display_name": profile.name,
            "description": profile.description or "",
            "system_prompt": profile.system_prompt,
            "base_expert_id": profile.base_expert_id,
            "preferred_model_key": profile.preferred_model_key,
            "preferred_model_tier": profile.preferred_model_tier,
            "reasoning_mode": profile.reasoning_mode,
            "metadata": profile.metadata_json or {},
            "source": "custom",
            "official": False,
            "entry_chat_mode": f"expert::{make_custom_expert_id(profile.id)}",
            "enabled": profile.is_enabled,
            "tags": list((profile.metadata_json or {}).get("tags") or []),
        }

    @staticmethod
    def serialize_team(team: CustomExpertTeam) -> dict[str, Any]:
        return {
            "id": str(team.id),
            "name": team.name,
            "description": team.description or "",
            "collaboration_mode": team.collaboration_mode,
            "expert_ids": list(team.expert_ids or []),
            "answer_expert_ids": list(team.answer_expert_ids or []),
            "enabled": team.is_enabled,
            "source": "custom",
        }

    async def build_catalog_payload(self, user_id: str) -> dict[str, Any]:
        experts = [self.serialize_runtime_profile(item) for item in await self.list_custom_experts(user_id)]
        teams = [self.serialize_team(item) for item in await self.list_custom_teams(user_id)]
        return {
            "experts": experts,
            "teams": teams,
        }

    @staticmethod
    def build_model_options() -> list[dict[str, str]]:
        from app.core.llm_router import llm_router

        options: list[dict[str, str]] = []
        for key, config in llm_router._available_models.items():
            if key == "default":
                continue
            options.append(
                {
                    "key": key,
                    "provider": config.provider.value,
                    "model_name": config.model_name,
                    "tier": config.tier.value,
                }
            )
        return options

    @staticmethod
    def official_expert_ids() -> list[str]:
        return [item["id"] for item in get_public_agent_catalog()]

    @staticmethod
    def valid_tier_values() -> list[str]:
        return [tier.value for tier in ModelTier]

    @staticmethod
    def valid_base_expert_ids() -> list[str]:
        return [role.value for role in AgentRole if role not in {AgentRole.ORCHESTRATOR, AgentRole.GENERATION, AgentRole.RETRIEVAL, AgentRole.REVIEWER}]
