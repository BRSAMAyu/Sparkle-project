from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from app.config import settings
from app.core.metrics import SPARKLE_SKILL_EXTRACT_DRAFT_ACCEPT_RATE
from app.services.llm_service import llm_service
from app.services.skill_schema import (
    SkillDraft,
    normalize_activation_conditions,
    normalize_examples,
    normalize_name,
    normalize_pattern_template,
)


class SkillExtractService:
    PROMPT_PATH = Path(__file__).with_name("skill_extract_prompt.v1.md")
    TRIGGER_KEYWORDS_PATH = Path(__file__).with_name("skill_extract_trigger_keywords.v1.json")
    _draft_total = 0
    _draft_accept_total = 0

    def __init__(
        self,
        *,
        llm_json: Callable[[list[dict[str, str]], Any], Awaitable[Any | None]] | None = None,
    ) -> None:
        self._llm_json = llm_json

    def matches_explicit_trigger(self, text: str) -> bool:
        payload = json.loads(self.TRIGGER_KEYWORDS_PATH.read_text(encoding="utf-8"))
        normalized = str(text or "").strip().lower()
        if not normalized:
            return False
        for pattern in payload.get("zh_patterns", []) + payload.get("en_patterns", []):
            if str(pattern).strip().lower() in normalized:
                return True
        return False

    async def generate_draft(
        self,
        *,
        trigger_type: str,
        consent_text: str,
        user_message: str,
        assistant_message: str,
        seconds_since_response: int | None = None,
        feedback_positive: bool = False,
        user_confirmed: bool = False,
    ) -> SkillDraft:
        if not settings.SPARKLE_SKILL_EXTRACT_ENABLED:
            raise ValueError("Skill extract disabled")
        if not self._trigger_is_allowed(
            trigger_type=trigger_type,
            consent_text=consent_text,
            seconds_since_response=seconds_since_response,
            feedback_positive=feedback_positive,
            user_confirmed=user_confirmed,
        ):
            raise ValueError("Skill extract trigger rejected")

        payload = await self._call_llm(
            consent_text=consent_text,
            user_message=user_message,
            assistant_message=assistant_message,
        )
        return self._parse_draft(payload)

    async def _call_llm(
        self,
        *,
        consent_text: str,
        user_message: str,
        assistant_message: str,
    ) -> Any | None:
        prompt = self.PROMPT_PATH.read_text(encoding="utf-8")
        messages = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "consent_text": consent_text,
                        "user_message": user_message,
                        "assistant_message": assistant_message,
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        if self._llm_json is not None:
            return await self._llm_json(
                messages,
                model=settings.SPARKLE_SKILL_EXTRACT_MODEL,
                max_tokens=settings.SPARKLE_SKILL_EXTRACT_MAX_TOKENS,
                temperature=0.0,
            )
        return await llm_service.chat_json(
            messages,
            model=settings.SPARKLE_SKILL_EXTRACT_MODEL,
            max_tokens=settings.SPARKLE_SKILL_EXTRACT_MAX_TOKENS,
            temperature=0.0,
        )

    def _parse_draft(self, payload: Any | None) -> SkillDraft:
        if not isinstance(payload, dict) or payload.get("rejected"):
            raise ValueError(str((payload or {}).get("rejection_reason") or "Skill draft rejected"))
        return SkillDraft(
            name=normalize_name(str(payload.get("name") or "")),
            pattern_template=normalize_pattern_template(str(payload.get("pattern_template") or "")),
            activation_conditions=normalize_activation_conditions(payload.get("activation_conditions")),
            examples=normalize_examples(payload.get("examples")),
        )

    def _trigger_is_allowed(
        self,
        *,
        trigger_type: str,
        consent_text: str,
        seconds_since_response: int | None,
        feedback_positive: bool,
        user_confirmed: bool,
    ) -> bool:
        if trigger_type == "explicit_phrase":
            effective = seconds_since_response if seconds_since_response is not None else 10_000
            return effective <= 60 and self.matches_explicit_trigger(consent_text)
        if trigger_type == "feedback_opt_in":
            return feedback_positive and user_confirmed
        return False

    def record_draft_outcome(self, *, accepted: bool) -> None:
        self.__class__._draft_total += 1
        if accepted:
            self.__class__._draft_accept_total += 1
        total = max(1, self.__class__._draft_total)
        SPARKLE_SKILL_EXTRACT_DRAFT_ACCEPT_RATE.set(self.__class__._draft_accept_total / total)
