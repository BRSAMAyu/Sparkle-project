from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from collections.abc import Awaitable, Callable
from uuid import UUID

from app.config import settings
from app.core.cache import cache_service
from app.services.aurora_stage19_kill_switch_service import AuroraStage19KillSwitchService
from app.services.llm_service import llm_service
from app.services.memory_inferred_write_lane import InferredEpisodicCandidate
from app.services.rule_y_adapter import RuleYAdapter


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class LlmExtractorService:
    PROMPT_PATH = Path(__file__).with_name("llm_extractor_prompt.v1.md")
    DRY_RUN_PREFIX = "stage19:llm_extract:dry_run:"
    SESSION_BUDGET_PREFIX = "stage19:llm_extract:budget:"
    _local_session_budget: dict[str, int] = {}

    def __init__(
        self,
        *,
        llm_json: Callable[[list[dict[str, str]], Any], Awaitable[Any | None]] | None = None,
        now_fn=_utcnow,
    ) -> None:
        self._llm_json = llm_json
        self._now_fn = now_fn
        self.kill_switches = AuroraStage19KillSwitchService()

    async def dry_run_extract(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        user_message: str,
        assistant_message: str,
        evidence_token: str,
    ) -> list[InferredEpisodicCandidate]:
        extractor_mode = await self.kill_switches.get_feature_mode("llm_extractor_enabled")
        if not settings.SPARKLE_LLM_EXTRACTOR_DRY_RUN_ENABLED and extractor_mode == "off":
            return []

        if not await self._consume_session_budget(session_id=session_id):
            return []

        payload = await self._call_llm(
            user_message=user_message,
            assistant_message=assistant_message,
        )
        candidates = self._parse_candidates(
            payload=payload,
            evidence_token=evidence_token,
            occurred_at=self._now_fn(),
        )
        await self._record_dry_run(user_id=user_id, session_id=session_id, candidates=candidates)
        return candidates

    async def _call_llm(self, *, user_message: str, assistant_message: str) -> Any | None:
        prompt = self.PROMPT_PATH.read_text(encoding="utf-8")
        messages = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {
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
                model=settings.SPARKLE_LLM_EXTRACTOR_MODEL,
                max_tokens=settings.SPARKLE_LLM_EXTRACTOR_MAX_TOKENS_PER_CALL,
                temperature=0.0,
            )
        return await llm_service.chat_json(
            messages,
            model=settings.SPARKLE_LLM_EXTRACTOR_MODEL,
            max_tokens=settings.SPARKLE_LLM_EXTRACTOR_MAX_TOKENS_PER_CALL,
            temperature=0.0,
        )

    def _parse_candidates(
        self,
        *,
        payload: Any | None,
        evidence_token: str,
        occurred_at: datetime,
    ) -> list[InferredEpisodicCandidate]:
        raw_candidates = []
        if isinstance(payload, dict):
            raw_candidates = payload.get("candidates") or []
        if not isinstance(raw_candidates, list):
            return []

        accepted: list[InferredEpisodicCandidate] = []
        for raw in raw_candidates[:2]:
            if not isinstance(raw, dict):
                continue
            candidate = self._build_candidate(
                raw=raw,
                evidence_token=evidence_token,
                occurred_at=occurred_at,
            )
            validated = RuleYAdapter.validate(candidate)
            if validated is not None:
                accepted.append(validated)
        return accepted

    def _build_candidate(
        self,
        *,
        raw: dict[str, Any],
        evidence_token: str,
        occurred_at: datetime,
    ) -> InferredEpisodicCandidate | None:
        candidate_text = str(raw.get("candidate_text") or "").strip()
        subject_type = str(raw.get("subject_type") or "").strip()
        semantic_key = str(raw.get("semantic_key") or "").strip()
        decay_policy = str(raw.get("decay_policy") or "30d").strip()
        if not candidate_text or not subject_type or not semantic_key:
            return None
        due_at_raw = raw.get("due_at")
        occurred_at_raw = raw.get("occurred_at")
        try:
            occurred = datetime.fromisoformat(str(occurred_at_raw)) if occurred_at_raw else occurred_at
        except ValueError:
            occurred = occurred_at
        due_at = None
        if due_at_raw:
            try:
                due_at = datetime.fromisoformat(str(due_at_raw))
            except ValueError:
                due_at = None

        return InferredEpisodicCandidate(
            candidate_text=candidate_text,
            subject_type=subject_type,
            confidence=float(raw.get("confidence") or 0.0),
            evidence_token=evidence_token,
            decay_policy=decay_policy,
            source_lane="llm_extractor",
            semantic_key=semantic_key,
            evidence_refs=[
                {
                    "type": "chat_turn",
                    "id": evidence_token,
                    "schema_version": "stage19.rule_y.v1",
                }
            ],
            occurred_at=occurred,
            due_at=due_at,
            mentioned_entity_hash=raw.get("mentioned_entity_hash"),
            mentioned_entity_owner_user_id=None,
        )

    async def _consume_session_budget(self, *, session_id: UUID) -> bool:
        amount = settings.SPARKLE_LLM_EXTRACTOR_MAX_TOKENS_PER_CALL
        key = f"{self.SESSION_BUDGET_PREFIX}{session_id}"
        current = await self._get_budget(key)
        if current + amount > settings.SPARKLE_LLM_EXTRACTOR_MAX_TOKENS_PER_SESSION:
            return False
        await self._set_budget(key, current + amount)
        return True

    async def _get_budget(self, key: str) -> int:
        redis_client = cache_service.redis
        if redis_client is None:
            return self._local_session_budget.get(key, 0)
        raw = await redis_client.get(key)
        return int(raw or 0)

    async def _set_budget(self, key: str, value: int) -> None:
        redis_client = cache_service.redis
        if redis_client is None:
            self._local_session_budget[key] = value
            return
        await redis_client.set(key, str(value), ex=86400)

    async def _record_dry_run(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        candidates: list[InferredEpisodicCandidate],
    ) -> None:
        redis_client = cache_service.redis
        payload = json.dumps(
            {
                "user_id": str(user_id),
                "session_id": str(session_id),
                "candidates": [candidate.candidate_text for candidate in candidates],
            },
            ensure_ascii=True,
        )
        if redis_client is None:
            self._local_session_budget[f"{self.DRY_RUN_PREFIX}{session_id}"] = len(payload)
            return
        await redis_client.set(f"{self.DRY_RUN_PREFIX}{session_id}", payload, ex=86400)
