from __future__ import annotations

from typing import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.metrics import SPARKLE_SKILL_SELECTION_ACTIVATION_RATE
from app.models.aurora_stage21 import UserSkill
from app.services.conflict_resolver_service import ConflictResolverService
from app.services.skill_schema import (
    SkillActivationMatch,
    SkillSelectionContext,
    time_of_day_token,
    weekday_token,
)


class SkillSelectionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.conflict_resolver = ConflictResolverService(db)

    async def resolve_prompt_payload(
        self,
        *,
        user_id: UUID,
        selection_context: SkillSelectionContext,
    ) -> tuple[list[SkillActivationMatch], list[str]]:
        if not settings.SPARKLE_SKILL_STORE_ENABLED:
            return [], []

        result = await self.db.execute(
            select(UserSkill).where(
                UserSkill.user_id == user_id,
                UserSkill.active.is_(True),
                UserSkill.deleted_at.is_(None),
            )
        )

        matches: list[SkillActivationMatch] = []
        blocked_caveats: list[str] = []
        for skill in result.scalars().all():
            score, topic_keys = self._match_skill(skill=skill, selection_context=selection_context)
            if score < 0.6:
                continue
            if await self.conflict_resolver.has_unresolved_conflict(user_id=user_id, topic_keys=topic_keys):
                blocked_caveats.append(f"技能“{skill.name}”因存在未决事实分歧未激活。")
                continue
            matches.append(
                SkillActivationMatch(
                    skill_id=str(skill.id),
                    name=skill.name,
                    activation_match_score=score,
                )
            )

        matches.sort(key=lambda item: (-item.activation_match_score, item.name))
        selected = matches[:3]
        SPARKLE_SKILL_SELECTION_ACTIVATION_RATE.observe(float(len(selected)))
        return selected, blocked_caveats

    @staticmethod
    def render_prompt_context(
        *,
        skills: Iterable[dict[str, str]],
        blocked_caveats: list[str] | None = None,
    ) -> str:
        lines: list[str] = []
        skills = list(skills)
        if skills:
            lines.append("## Active Skills")
            lines.append("可以参考这些由用户确认过的处理方式：")
            for skill in skills:
                lines.append(f"- {skill['name']}: {skill['pattern_template']}")
        for caveat in blocked_caveats or []:
            lines.append(f"- Caveat: {caveat}")
        return "\n".join(lines).strip()

    def _match_skill(
        self,
        *,
        skill: UserSkill,
        selection_context: SkillSelectionContext,
    ) -> tuple[float, tuple[str, ...]]:
        conditions = skill.activation_conditions or []
        if not conditions:
            return 0.0, ()

        intent = selection_context.intent.lower()
        tool_category = selection_context.tool_category.lower()
        tod = time_of_day_token(selection_context.current_time)
        weekday = weekday_token(selection_context.current_time)

        total = 0
        matched = 0
        topic_keys: list[str] = []
        for condition in conditions:
            kind = str(condition.get("kind") or "").strip()
            values = [str(item or "").strip().lower() for item in (condition.get("value") or []) if str(item or "").strip()]
            if not values:
                continue
            total += 1
            is_match = False
            if kind == "intent_keywords":
                is_match = any(value in intent or intent in value for value in values)
            elif kind == "tool_category":
                is_match = any(value == tool_category for value in values)
            elif kind == "time_of_day":
                is_match = any(value == tod for value in values)
            elif kind == "weekday_set":
                is_match = any(value == weekday for value in values)
            if is_match:
                matched += 1
                topic_keys.extend(values)

        if total == 0:
            return 0.0, ()
        return round(matched / total, 4), tuple(dict.fromkeys(topic_keys))
