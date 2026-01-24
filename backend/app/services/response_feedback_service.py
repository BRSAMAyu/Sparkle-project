import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
import time
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import RESPONSE_FEEDBACK_DEDUPE_TOTAL, RESPONSE_FEEDBACK_INGESTED
from app.learning.prompt_bandit import PromptBandit
from app.models.response_feedback import ResponseFeedback
from app.models.context_pack import ContextPackRun, ContextPackFeedback
from app.services.budget_tuning_service import BudgetTuningService
from app.config import settings


MAX_REASONS = 3
MAX_FREE_TEXT_LEN = 120


FEEDBACK_REASON_MAP = {
    0: "unspecified",
    1: "inaccurate",
    2: "incomplete",
    3: "verbose",
    4: "formatting",
    5: "misaligned",
    6: "too_hard",
    7: "too_simple",
}


@dataclass
class FeedbackResult:
    success: bool
    already_recorded: bool
    response_id: str


class ResponseFeedbackService:
    def __init__(self, db: AsyncSession, redis_client=None):
        self.db = db
        self.redis = redis_client

    def _validate(self, feedback_type: int, reasons: List[str], free_text: Optional[str]) -> None:
        if feedback_type not in (ResponseFeedback.FEEDBACK_UP, ResponseFeedback.FEEDBACK_DOWN):
            raise ValueError("invalid feedback_type")
        if reasons and len(reasons) > MAX_REASONS:
            raise ValueError("too many reasons")
        if free_text and len(free_text) > MAX_FREE_TEXT_LEN:
            raise ValueError("free_text too long")

    async def submit_feedback(
        self,
        *,
        user_id: str,
        response_id: str,
        trace_id: str,
        feedback_type: int,
        reasons: Optional[List[str]] = None,
        free_text: Optional[str] = None,
        workflow_id: Optional[str] = None,
        prompt_version: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> FeedbackResult:
        reasons = reasons or []
        self._validate(feedback_type, reasons, free_text)

        try:
            user_uuid = uuid.UUID(user_id)
            response_uuid = uuid.UUID(response_id)
        except ValueError as exc:
            raise ValueError("invalid uuid") from exc

        feedback = ResponseFeedback(
            user_id=user_uuid,
            response_id=response_uuid,
            trace_id=trace_id,
            workflow_id=workflow_id,
            prompt_version=prompt_version,
            feedback_type=feedback_type,
            reasons=reasons,
            free_text=free_text,
            meta=meta or None,
        )
        self.db.add(feedback)

        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            RESPONSE_FEEDBACK_DEDUPE_TOTAL.inc()
            return FeedbackResult(
                success=True,
                already_recorded=True,
                response_id=response_id,
            )

        RESPONSE_FEEDBACK_INGESTED.labels(
            type="up" if feedback_type == ResponseFeedback.FEEDBACK_UP else "down"
        ).inc()

        await self._record_feedback_ts(user_id, workflow_id, prompt_version)
        await self._update_bandit(workflow_id, prompt_version, feedback_type)
        await self._handle_context_pack_feedback(
            user_uuid,
            feedback_type,
            reasons,
            meta or {},
        )

        logger.info(
            "Response feedback stored trace_id=%s response_id=%s workflow_id=%s prompt_version=%s",
            trace_id,
            response_id,
            workflow_id,
            prompt_version,
        )
        return FeedbackResult(
            success=True,
            already_recorded=False,
            response_id=response_id,
        )

    async def _handle_context_pack_feedback(
        self,
        user_id: uuid.UUID,
        feedback_type: int,
        reasons: List[str],
        meta: Dict[str, Any],
    ) -> None:
        if not settings.ENABLE_BUDGET_TUNING:
            return

        pack_run = await self._resolve_pack_run(user_id, meta)
        if pack_run is None:
            return

        score = 1.0 if feedback_type == ResponseFeedback.FEEDBACK_UP else -1.0
        feedback = ContextPackFeedback(
            pack_run_id=pack_run.id,
            feedback_type="up" if score > 0 else "down",
            reasons=reasons or None,
            score=score,
        )
        self.db.add(feedback)
        await self.db.commit()

        tuning = BudgetTuningService(self.db)
        await tuning.apply_feedback(pack_run.intent, reasons, score)

        # 推断用户偏好
        try:
            from app.services.personalization.preference_inference_service import PreferenceInferenceService
            inference_service = PreferenceInferenceService(self.db, self.redis)
            normalized_reasons = self.normalize_reasons([int(r) for r in reasons] if reasons else [])

            result = await inference_service.process_feedback(
                user_id=user_id,
                feedback_type=feedback_type,
                reasons=normalized_reasons,
                metadata=meta
            )

            if result.get("changes"):
                logger.info(f"Preference inference applied: {result['changes']}")
        except Exception as e:
            logger.warning(f"Failed to apply preference inference: {e}")

    async def _resolve_pack_run(
        self,
        user_id: uuid.UUID,
        meta: Dict[str, Any],
    ) -> Optional[ContextPackRun]:
        pack_id = meta.get("pack_id") or meta.get("context_pack_id")
        if pack_id:
            try:
                pack_uuid = uuid.UUID(str(pack_id))
            except ValueError:
                pack_uuid = None
            if pack_uuid:
                result = await self.db.execute(
                    select(ContextPackRun).where(
                        ContextPackRun.id == pack_uuid,
                        ContextPackRun.user_id == user_id,
                        ContextPackRun.deleted_at.is_(None),
                    )
                )
                pack_run = result.scalar_one_or_none()
                if pack_run is not None:
                    return pack_run

        cutoff = datetime.utcnow() - timedelta(minutes=settings.CONTEXT_PACK_FEEDBACK_WINDOW_MINUTES)
        result = await self.db.execute(
            select(ContextPackRun)
            .where(
                ContextPackRun.user_id == user_id,
                ContextPackRun.created_at >= cutoff,
                ContextPackRun.deleted_at.is_(None),
            )
            .order_by(ContextPackRun.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _update_bandit(
        self,
        workflow_id: Optional[str],
        prompt_version: Optional[str],
        feedback_type: int,
    ) -> None:
        if not workflow_id or not prompt_version:
            return
        reward = 1 if feedback_type == ResponseFeedback.FEEDBACK_UP else 0
        bandit = PromptBandit(redis_client=self.redis)
        await bandit.update(workflow_id, prompt_version, reward)

    async def _record_feedback_ts(
        self,
        user_id: str,
        workflow_id: Optional[str],
        prompt_version: Optional[str],
    ) -> None:
        if not self.redis:
            return
        if not workflow_id or not prompt_version:
            return
        key = f"bandit:last_feedback_ts:{user_id}:{workflow_id}:{prompt_version}"
        await self.redis.setex(key, settings.FEEDBACK_EFFECT_TTL_SECONDS, int(time.time()))

    async def get_summary(self, window: timedelta) -> Dict[str, Any]:
        since = datetime.utcnow() - window
        stmt = select(ResponseFeedback).where(
            ResponseFeedback.created_at >= since,
            ResponseFeedback.deleted_at.is_(None),
        )
        rows = (await self.db.execute(stmt)).scalars().all()

        total = len(rows)
        up_count = 0
        down_count = 0
        reasons_counter: Counter[str] = Counter()
        by_prompt: Dict[str, Dict[str, int]] = {}
        by_workflow: Dict[str, Dict[str, int]] = {}

        for row in rows:
            if row.feedback_type == ResponseFeedback.FEEDBACK_UP:
                up_count += 1
                self._accumulate(by_prompt, row.prompt_version, True)
                self._accumulate(by_workflow, row.workflow_id, True)
            else:
                down_count += 1
                self._accumulate(by_prompt, row.prompt_version, False)
                self._accumulate(by_workflow, row.workflow_id, False)

            if row.reasons:
                for reason in row.reasons:
                    reasons_counter[str(reason)] += 1

        return {
            "feedback_count": total,
            "up_count": up_count,
            "down_count": down_count,
            "down_rate": (down_count / total) if total else 0.0,
            "top_reasons": dict(reasons_counter.most_common(5)),
            "by_prompt_version": self._finalize_groups(by_prompt),
            "by_workflow_id": self._finalize_groups(by_workflow),
        }

    @staticmethod
    def _accumulate(target: Dict[str, Dict[str, int]], key: Optional[str], is_up: bool) -> None:
        bucket_key = key or "unknown"
        if bucket_key not in target:
            target[bucket_key] = {"up": 0, "down": 0}
        if is_up:
            target[bucket_key]["up"] += 1
        else:
            target[bucket_key]["down"] += 1

    @staticmethod
    def _finalize_groups(groups: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, float]]:
        finalized: Dict[str, Dict[str, float]] = {}
        for key, counts in groups.items():
            up = counts.get("up", 0)
            down = counts.get("down", 0)
            total = up + down
            finalized[key] = {
                "up": up,
                "down": down,
                "down_rate": (down / total) if total else 0.0,
            }
        return finalized

    @staticmethod
    def normalize_reasons(reasons: List[int]) -> List[str]:
        normalized = []
        for reason in reasons:
            normalized.append(FEEDBACK_REASON_MAP.get(int(reason), "unspecified"))
        return normalized
