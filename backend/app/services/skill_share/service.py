from __future__ import annotations

import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Awaitable, Callable
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.metrics import SPARKLE_SKILL_SHARE_PIPELINE_LATENCY_SECONDS
from app.models.aurora_stage21 import SharedSkill, SkillShareModerationQueue, UserSkill
from app.services.aurora_stage21_kill_switch_service import AuroraStage21KillSwitchService


PHONE_PATTERN = re.compile(r"\b(?:\+?\d[\d\- ]{6,}\d)\b")
EMAIL_PATTERN = re.compile(r"\b[\w.\-]+@[\w.\-]+\.\w+\b")
ADDRESS_PATTERN = re.compile(r"(路|街|大道|号|Street|Avenue|Road|Lane)")
HANDLE_PATTERN = re.compile(r"@\w+")


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class SkillShareService:
    PII_PROMPT_PATH = Path(__file__).resolve().parents[1] / "skill_pii_detector_prompt.v1.md"
    INJECTION_PROMPT_PATH = Path(__file__).resolve().parents[1] / "skill_injection_detector_prompt.v1.md"

    def __init__(
        self,
        db: AsyncSession,
        *,
        llm_json: Callable[[list[dict[str, str]], Any], Awaitable[Any | None]] | None = None,
    ) -> None:
        self.db = db
        self._llm_json = llm_json
        self.kill_switches = AuroraStage21KillSwitchService()

    async def submit_share_request(self, *, user_id: UUID, skill_id: UUID) -> dict[str, Any]:
        share_mode = await self.kill_switches.get_feature_mode("skill_share_enabled")
        if share_mode == "off":
            raise ValueError("Skill share disabled")
        skill = await self._load_user_skill(user_id=user_id, skill_id=skill_id)
        if skill is None:
            raise ValueError("Skill not found")
        await self._ensure_daily_limit(user_id)

        started = time.perf_counter()
        pii_reasons = await self.scan_for_pii(skill)
        injection_reasons = await self.detect_injection(skill)
        queue = await self.enqueue_for_moderation(
            user_id=user_id,
            skill=skill,
            pii_reasons=pii_reasons,
            injection_reasons=injection_reasons,
        )

        if pii_reasons or injection_reasons:
            queue.moderation_status = "rejected"
            queue.rejection_reason = "; ".join([*pii_reasons, *injection_reasons])[:512]
            queue.reviewed_at = _utcnow()
            queue.reviewer_label = "mock_approver"
            await self.db.commit()
            SPARKLE_SKILL_SHARE_PIPELINE_LATENCY_SECONDS.observe(time.perf_counter() - started)
            return {"status": "rejected", "queue_id": str(queue.id), "reasons": [*pii_reasons, *injection_reasons]}

        published = None
        if share_mode == "live" and settings.SPARKLE_SKILL_SHARE_MOCK_REVIEW_ENABLED:
            published = await self.review_and_publish(queue_id=queue.id, approved=True, reviewer_label="mock_approver")
        SPARKLE_SKILL_SHARE_PIPELINE_LATENCY_SECONDS.observe(time.perf_counter() - started)
        return {
            "status": "approved" if published is not None else "pending",
            "queue_id": str(queue.id),
            "shared_skill_id": str(published.id) if published is not None else None,
        }

    async def scan_for_pii(self, skill: UserSkill) -> list[str]:
        text = self._skill_text(skill)
        reasons: list[str] = []
        if PHONE_PATTERN.search(text):
            reasons.append("phone_detected")
        if EMAIL_PATTERN.search(text):
            reasons.append("email_detected")
        if ADDRESS_PATTERN.search(text):
            reasons.append("address_like_text_detected")
        if HANDLE_PATTERN.search(text):
            reasons.append("handle_detected")
        llm_reasons = await self._run_detector(
            prompt_path=self.PII_PROMPT_PATH,
            payload={"skill_text": text},
            positive_key="contains_pii",
        )
        reasons.extend(llm_reasons)
        return list(dict.fromkeys(reasons))

    async def detect_injection(self, skill: UserSkill) -> list[str]:
        return list(
            dict.fromkeys(
                await self._run_detector(
                    prompt_path=self.INJECTION_PROMPT_PATH,
                    payload={"skill_text": self._skill_text(skill)},
                    positive_key="contains_injection",
                )
            )
        )

    async def enqueue_for_moderation(
        self,
        *,
        user_id: UUID,
        skill: UserSkill,
        pii_reasons: list[str],
        injection_reasons: list[str],
    ) -> SkillShareModerationQueue:
        queue = SkillShareModerationQueue(
            owner_user_id=user_id,
            user_skill_id=skill.id,
            staged_name=skill.name,
            staged_pattern_template=skill.pattern_template,
            staged_activation_conditions=skill.activation_conditions or [],
            staged_examples=skill.examples or [],
            pii_scan_reasons=pii_reasons,
            injection_scan_reasons=injection_reasons,
            moderation_status="pending",
        )
        self.db.add(queue)
        await self.db.commit()
        await self.db.refresh(queue)
        return queue

    async def review_and_publish(
        self,
        *,
        queue_id: UUID,
        approved: bool,
        reviewer_label: str,
    ) -> SharedSkill | None:
        result = await self.db.execute(
            select(SkillShareModerationQueue).where(
                SkillShareModerationQueue.id == queue_id,
                SkillShareModerationQueue.deleted_at.is_(None),
            )
        )
        queue = result.scalar_one_or_none()
        if queue is None:
            raise ValueError("Moderation queue item not found")

        queue.reviewed_at = _utcnow()
        queue.reviewer_label = reviewer_label
        if not approved:
            queue.moderation_status = "rejected"
            await self.db.commit()
            return None

        shared = SharedSkill(
            share_slug=f"shared-skill-{str(queue.id)[:8]}",
            name=queue.staged_name,
            pattern_template=queue.staged_pattern_template,
            activation_conditions=queue.staged_activation_conditions or [],
            examples=queue.staged_examples or [],
            author_label="anonymous",
            published_at=_utcnow(),
            source_schema_version="skill.v1",
        )
        self.db.add(shared)
        await self.db.flush()

        user_skill = await self._load_user_skill(user_id=queue.owner_user_id, skill_id=queue.user_skill_id)
        if user_skill is not None:
            user_skill.privacy_level = "shared"
            user_skill.shared_catalog_id = shared.id
            user_skill.updated_at = _utcnow()

        queue.moderation_status = "approved"
        queue.published_shared_skill_id = shared.id
        await self.db.commit()
        await self.db.refresh(shared)
        return shared

    async def withdraw_share(self, *, user_id: UUID, skill_id: UUID) -> UserSkill:
        skill = await self._load_user_skill(user_id=user_id, skill_id=skill_id)
        if skill is None:
            raise ValueError("Skill not found")
        if skill.shared_catalog_id is not None:
            result = await self.db.execute(
                select(SharedSkill).where(
                    SharedSkill.id == skill.shared_catalog_id,
                    SharedSkill.deleted_at.is_(None),
                )
            )
            shared = result.scalar_one_or_none()
            if shared is not None:
                shared.deleted_at = _utcnow()
                shared.updated_at = _utcnow()
        skill.privacy_level = "private"
        skill.shared_catalog_id = None
        skill.updated_at = _utcnow()
        await self.db.commit()
        await self.db.refresh(skill)
        return skill

    async def list_shared_catalog(self, *, page: int = 1, page_size: int = 20) -> list[SharedSkill]:
        stmt = (
            select(SharedSkill)
            .where(SharedSkill.deleted_at.is_(None))
            .order_by(SharedSkill.published_at.desc(), SharedSkill.created_at.desc())
            .offset(max(page - 1, 0) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _ensure_daily_limit(self, user_id: UUID) -> None:
        now = _utcnow()
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self.db.execute(
            select(func.count(SkillShareModerationQueue.id)).where(
                SkillShareModerationQueue.owner_user_id == user_id,
                SkillShareModerationQueue.created_at >= day_start,
                SkillShareModerationQueue.deleted_at.is_(None),
            )
        )
        if int(result.scalar() or 0) >= 3:
            raise ValueError("Daily shared Skill limit reached")

    async def _run_detector(
        self,
        *,
        prompt_path: Path,
        payload: dict[str, Any],
        positive_key: str,
    ) -> list[str]:
        messages = [
            {"role": "system", "content": prompt_path.read_text(encoding="utf-8")},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
        if self._llm_json is not None:
            response = await self._llm_json(
                messages,
                model=settings.SPARKLE_SKILL_SHARE_REVIEW_MODEL,
                max_tokens=settings.SPARKLE_SKILL_SHARE_REVIEW_MAX_TOKENS,
                temperature=0.0,
            )
        else:
            from app.services.llm_service import llm_service

            response = await llm_service.chat_json(
                messages,
                model=settings.SPARKLE_SKILL_SHARE_REVIEW_MODEL,
                max_tokens=settings.SPARKLE_SKILL_SHARE_REVIEW_MAX_TOKENS,
                temperature=0.0,
            )
        if not isinstance(response, dict) or not response.get(positive_key):
            return []
        reasons = response.get("reasons") or []
        return [str(item).strip() for item in reasons if str(item).strip()]

    @staticmethod
    def _skill_text(skill: UserSkill) -> str:
        return "\n".join([skill.name, skill.pattern_template, *[str(item) for item in (skill.examples or [])]])

    async def _load_user_skill(self, *, user_id: UUID, skill_id: UUID) -> UserSkill | None:
        result = await self.db.execute(
            select(UserSkill).where(
                UserSkill.id == skill_id,
                UserSkill.user_id == user_id,
                UserSkill.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
