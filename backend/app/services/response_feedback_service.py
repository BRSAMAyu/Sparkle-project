import time
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.metrics import RESPONSE_FEEDBACK_DEDUPE_TOTAL, RESPONSE_FEEDBACK_INGESTED
from app.learning.prompt_bandit import PromptBandit
from app.models.context_pack import ContextPackFeedback, ContextPackRun
from app.models.response_feedback import ResponseFeedback
from app.orchestration.expert_strategy import parse_selected_experts
from app.services.budget_tuning_service import BudgetTuningService
from app.services.content_quality_evaluator import ContentQualityEvaluator

MAX_REASONS = 3
MAX_FREE_TEXT_LEN = 120
EXPERT_AFFINITY_STEP_UP = 0.08
EXPERT_AFFINITY_STEP_DOWN = -0.08
EXPERT_AFFINITY_MIN = 0.1
EXPERT_AFFINITY_MAX = 0.95


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


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ResponseFeedbackService:
    def __init__(self, db: AsyncSession, redis_client=None):
        self.db = db
        self.redis = redis_client

    def _validate(self, feedback_type: int, reasons: list[str], free_text: str | None) -> None:
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
        reasons: list[str] | None = None,
        free_text: str | None = None,
        workflow_id: str | None = None,
        prompt_version: str | None = None,
        meta: dict[str, Any] | None = None,
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
            feedback_type="up" if feedback_type == ResponseFeedback.FEEDBACK_UP else "down"
        ).inc()

        await self._record_feedback_ts(user_id, workflow_id, prompt_version)
        await self._update_bandit(workflow_id, prompt_version, feedback_type)
        await self._handle_context_pack_feedback(
            user_uuid,
            feedback_type,
            reasons,
            meta or {},
        )
        await self._update_expert_affinity(
            user_id=user_uuid,
            feedback_type=feedback_type,
            meta=meta or {},
        )
        await self._emit_learning_feedback_event(
            user_id=user_id,
            trace_id=trace_id,
            workflow_id=workflow_id,
            feedback_type=feedback_type,
            reasons=reasons,
            meta=meta or {},
        )

        # Opportunistically evaluate and auto-seed high-quality responses.
        try:
            evaluator = ContentQualityEvaluator(self.db)
            evaluation = await evaluator.evaluate_response_quality(response_id)
            if evaluation.get("should_seed"):
                await evaluator.auto_seed_to_library(response_id)
        except Exception as exc:
            logger.warning(f"Auto-seed evaluation failed: {exc}")

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

    async def _emit_learning_feedback_event(
        self,
        *,
        user_id: str,
        trace_id: str,
        workflow_id: str | None,
        feedback_type: int,
        reasons: list[str],
        meta: dict[str, Any],
    ) -> None:
        if not getattr(settings, "ENABLE_LEARNING_CONTROL_PLANE", False):
            return
        try:
            from app.services.learning_event_service import LearningEventService

            policy_id = str(meta.get("policy_id", ""))
            strategy_pack = ""
            if policy_id.startswith("meta_policy_v1:"):
                # meta_policy_v1:<channel>:<strategy_pack>:<hash>
                parts = policy_id.split(":")
                if len(parts) >= 3:
                    strategy_pack = parts[2]
            elif ":" in policy_id:
                rest = policy_id.split(":", 1)[1]
                if ":candidate_" in rest:
                    strategy_pack = rest.split(":candidate_", 1)[0]
                elif ":" in rest:
                    strategy_pack = rest.split(":", 1)[0]
                else:
                    strategy_pack = rest
            event_data = {
                "feedback_type": "up" if feedback_type == ResponseFeedback.FEEDBACK_UP else "down",
                "reasons": list(reasons),
                "workflow_id": str(workflow_id or ""),
                "response_id": str(meta.get("response_id", "")),
                "policy_id": policy_id,
                "prompt_policy_id": str(meta.get("prompt_policy_id", "")),
                "toolchain_policy_id": str(meta.get("toolchain_policy_id", "")),
                "strategy_pack": strategy_pack,
                "selected_experts": parse_selected_experts(meta.get("selected_experts")),
                "cohort_id": str(meta.get("cohort_id", "")),
                "user_scope": str(meta.get("user_scope", "")),
                "complexity_tier": str(meta.get("complexity_tier", "")),
                "task_type": str(meta.get("task_type", "")),
                "meta_rule_ids": parse_selected_experts(meta.get("meta_rule_ids")),
                "motif_graph_id": str(meta.get("motif_graph_id", "")),
                "transfer_source": str(meta.get("transfer_source", "")),
                "rule_confidence": str(meta.get("rule_confidence", "")),
                "rule_block_reason": str(meta.get("rule_block_reason", "")),
                "rule_block_detail": meta.get("rule_block_detail"),
                "trace_id": trace_id,
            }
            service = LearningEventService(redis_client=self.redis)
            await service.emit(
                event_type="response_feedback",
                user_id=user_id,
                workflow_id=str(workflow_id or ""),
                trace_id=trace_id,
                response_id=str(meta.get("response_id", "")),
                policy_id=policy_id,
                strategy_pack=strategy_pack,
                cohort_id=str(meta.get("cohort_id", "")),
                user_scope=str(meta.get("user_scope", "")),
                complexity_tier=str(meta.get("complexity_tier", "")),
                task_type=str(meta.get("task_type", "")),
                data=event_data,
            )
        except Exception as exc:
            logger.warning("Failed to emit learning feedback event: {}", exc)

    async def _handle_context_pack_feedback(
        self,
        user_id: uuid.UUID,
        feedback_type: int,
        reasons: list[str],
        meta: dict[str, Any],
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
        meta: dict[str, Any],
    ) -> ContextPackRun | None:
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

        cutoff = _utcnow() - timedelta(minutes=settings.CONTEXT_PACK_FEEDBACK_WINDOW_MINUTES)
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
        workflow_id: str | None,
        prompt_version: str | None,
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
        workflow_id: str | None,
        prompt_version: str | None,
    ) -> None:
        if not self.redis:
            return
        if not workflow_id or not prompt_version:
            return
        key = f"bandit:last_feedback_ts:{user_id}:{workflow_id}:{prompt_version}"
        await self.redis.setex(key, settings.FEEDBACK_EFFECT_TTL_SECONDS, int(time.time()))

    async def _update_expert_affinity(
        self,
        *,
        user_id: uuid.UUID,
        feedback_type: int,
        meta: dict[str, Any],
    ) -> None:
        if not settings.ENABLE_EXPERT_AFFINITY_MEMORY:
            return

        selected_experts = parse_selected_experts(meta.get("selected_experts"))
        if not selected_experts:
            return

        from app.services.personalization.preference_service import PreferenceService

        pref_service = PreferenceService(self.db, self.redis)
        prefs = await pref_service.get_preferences(user_id)
        inferred = prefs.inferred.copy() if isinstance(prefs.inferred, dict) else {}

        affinity_map = inferred.get("expert_affinity")
        if not isinstance(affinity_map, dict):
            affinity_map = {}

        delta = EXPERT_AFFINITY_STEP_UP if feedback_type == ResponseFeedback.FEEDBACK_UP else EXPERT_AFFINITY_STEP_DOWN
        for expert_id in selected_experts:
            current = affinity_map.get(expert_id, 0.5)
            try:
                current_value = float(current)
            except (TypeError, ValueError):
                current_value = 0.5
            updated = max(EXPERT_AFFINITY_MIN, min(EXPERT_AFFINITY_MAX, current_value + delta))
            affinity_map[expert_id] = round(updated, 4)

        inferred["expert_affinity"] = affinity_map
        inferred["expert_affinity_last_updated"] = _utcnow().isoformat()
        await pref_service.update_inferred(user_id, inferred)

    async def get_summary(self, window: timedelta) -> dict[str, Any]:
        since = _utcnow() - window
        stmt = select(ResponseFeedback).where(
            ResponseFeedback.created_at >= since,
            ResponseFeedback.deleted_at.is_(None),
        )
        rows = (await self.db.execute(stmt)).scalars().all()

        total = len(rows)
        up_count = 0
        down_count = 0
        reasons_counter: Counter[str] = Counter()
        by_prompt: dict[str, dict[str, int]] = {}
        by_workflow: dict[str, dict[str, int]] = {}

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
    def _accumulate(target: dict[str, dict[str, int]], key: str | None, is_up: bool) -> None:
        bucket_key = key or "unknown"
        if bucket_key not in target:
            target[bucket_key] = {"up": 0, "down": 0}
        if is_up:
            target[bucket_key]["up"] += 1
        else:
            target[bucket_key]["down"] += 1

    @staticmethod
    def _finalize_groups(groups: dict[str, dict[str, int]]) -> dict[str, dict[str, float]]:
        finalized: dict[str, dict[str, float]] = {}
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
    def normalize_reasons(reasons: list[int]) -> list[str]:
        normalized = []
        for reason in reasons:
            normalized.append(FEEDBACK_REASON_MAP.get(int(reason), "unspecified"))
        return normalized
