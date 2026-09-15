from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.response_feedback import ResponseFeedback
from app.models.user_settings import UserSettings

DEFAULT_SETTINGS: dict[str, Any] = {
    "transparency_level": 0,
    "system_update_level": 1,
    "ai_reasoning_mode": "balanced",
    "current_goal_id": None,
    "task_reminders_enabled": True,
    "task_reminder_times": [1440, 60, 15],  # 1 day, 1 hour, 15 minutes
    "community_intelligence_enabled": True,
}


class UserSettingsService:
    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis

    async def get_or_create(self, user_id: UUID) -> UserSettings:
        record = await self._get_settings(user_id)
        if record:
            return record
        record = UserSettings(user_id=user_id, **DEFAULT_SETTINGS)
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def update_settings(
        self,
        user_id: UUID,
        updates: dict[str, Any],
    ) -> UserSettings:
        record = await self.get_or_create(user_id)
        for key, value in updates.items():
            if value is None and key != "current_goal_id":
                continue
            if hasattr(record, key):
                setattr(record, key, value)
        await self.db.commit()
        await self.db.refresh(record)

        # 清除相关缓存
        await self._invalidate_cache(user_id)

        return record

    async def get_ai_usage_summary(self, user_id: UUID) -> dict[str, Any]:
        redis_client = await self._ensure_redis()
        current_mode = "balanced"
        try:
            current_mode = (await self.get_or_create(user_id)).ai_reasoning_mode or "balanced"
        except Exception:
            current_mode = "balanced"

        mode_limits = {
            "fast": int(getattr(settings, "AI_MODE_FAST_DAILY_REQUEST_LIMIT", 120)),
            "balanced": int(getattr(settings, "AI_MODE_BALANCED_DAILY_REQUEST_LIMIT", 60)),
            "deep": int(getattr(settings, "AI_MODE_DEEP_DAILY_REQUEST_LIMIT", 24)),
        }

        items: list[dict[str, Any]] = []
        if redis_client is not None:
            from app.orchestration.token_tracker import get_token_tracker

            tracker = get_token_tracker(redis_client)
            items = await tracker.get_ai_usage_summary(str(user_id), mode_limits=mode_limits)
        else:
            items = [
                {
                    "mode": mode,
                    "label": {"fast": "敏捷", "balanced": "均衡", "deep": "深思"}[mode],
                    "requests_used": 0,
                    "requests_limit": limit,
                    "requests_remaining": limit,
                    "total_tokens": 0,
                    "total_cost_usd": 0.0,
                    "total_duration_ms": 0,
                    "avg_total_duration_ms": 0.0,
                    "avg_first_token_ms": 0.0,
                    "avg_stream_duration_ms": 0.0,
                }
                for mode, limit in mode_limits.items()
            ]

        from datetime import datetime

        return {
            "current_mode": current_mode,
            "items": items,
            "generated_at": datetime.utcnow(),
        }

    async def get_ai_usage_export(self, user_id: UUID, *, days: int = 7) -> dict[str, Any]:
        redis_client = await self._ensure_redis()
        summary = await self.get_ai_usage_summary(user_id)
        chat_mode_timing: list[dict[str, Any]] = []
        if redis_client is not None:
            from app.orchestration.token_tracker import get_token_tracker

            tracker = get_token_tracker(redis_client)
            chat_mode_timing = await tracker.get_chat_mode_timing_summary(days=days)
        return {
            "current_mode": summary["current_mode"],
            "window_days": days,
            "items": summary["items"],
            "chat_mode_timing": chat_mode_timing,
            "generated_at": summary["generated_at"],
        }

    async def get_ai_ops_dashboard(self, user_id: UUID, *, days: int = 7) -> dict[str, Any]:
        redis_client = await self._ensure_redis()
        items: list[dict[str, Any]] = []
        if redis_client is not None:
            from app.orchestration.token_tracker import get_token_tracker

            tracker = get_token_tracker(redis_client)
            items = await tracker.get_ai_ops_summary(str(user_id), days=days)

        since = datetime.utcnow() - timedelta(days=days)
        feedback_rows = (
            await self.db.execute(
                select(ResponseFeedback).where(
                    ResponseFeedback.user_id == user_id,
                    ResponseFeedback.deleted_at.is_(None),
                    ResponseFeedback.created_at >= since,
                )
            )
        ).scalars().all()

        feedback_by_mode: dict[str, dict[str, int]] = {}
        for row in feedback_rows:
            meta = row.meta if isinstance(row.meta, dict) else {}
            chat_mode = str(meta.get("chat_mode") or "standard").strip() or "standard"
            bucket = feedback_by_mode.setdefault(chat_mode, {"positive": 0, "negative": 0})
            if row.feedback_type == ResponseFeedback.FEEDBACK_UP:
                bucket["positive"] += 1
            elif row.feedback_type == ResponseFeedback.FEEDBACK_DOWN:
                bucket["negative"] += 1

        enriched_items: list[dict[str, Any]] = []
        for item in items:
            chat_mode = str(item.get("chat_mode") or "standard")
            feedback_bucket = feedback_by_mode.get(chat_mode, {"positive": 0, "negative": 0})
            positive = int(feedback_bucket["positive"])
            negative = int(feedback_bucket["negative"])
            feedback_total = positive + negative
            requests_total = int(item.get("requests_total") or 0)
            enriched_items.append(
                {
                    **item,
                    "positive_feedback_count": positive,
                    "negative_feedback_count": negative,
                    "positive_feedback_rate_percent": round((positive / feedback_total) * 100, 2)
                    if feedback_total > 0
                    else 0.0,
                    "feedback_coverage_percent": min(
                        100.0,
                        round((feedback_total / requests_total) * 100, 2)
                        if requests_total > 0
                        else 0.0,
                    ),
                    "avg_prompt_utilization_percent": float(item.get("avg_prompt_utilization_percent") or 0.0),
                    "avg_inference_utilization_percent": float(
                        item.get("avg_inference_utilization_percent") or 0.0
                    ),
                    "prompt_utilization_known_count": int(item.get("prompt_utilization_known_count") or 0),
                    "prompt_utilization_unknown_count": int(
                        item.get("prompt_utilization_unknown_count") or 0
                    ),
                    "prompt_utilization_not_applicable_count": int(
                        item.get("prompt_utilization_not_applicable_count") or 0
                    ),
                    "inference_utilization_known_count": int(
                        item.get("inference_utilization_known_count") or 0
                    ),
                    "inference_utilization_unknown_count": int(
                        item.get("inference_utilization_unknown_count") or 0
                    ),
                    "inference_utilization_not_applicable_count": int(
                        item.get("inference_utilization_not_applicable_count") or 0
                    ),
                }
            )

        return {
            "window_days": days,
            "items": enriched_items,
            "generated_at": datetime.utcnow(),
        }

    async def get_ai_ops_export(self, user_id: UUID, *, days: int = 14) -> dict[str, Any]:
        redis_client = await self._ensure_redis()
        dashboard = await self.get_ai_ops_dashboard(user_id, days=days)
        trend_rows: list[dict[str, Any]] = []
        if redis_client is not None:
            from app.orchestration.token_tracker import get_token_tracker

            tracker = get_token_tracker(redis_client)
            trend_rows = await tracker.get_ai_ops_trend_summary(str(user_id), days=days)

        totals = {
            "requests_total": 0,
            "requests_success": 0,
            "requests_failed": 0,
            "fallback_rate_numerator": 0.0,
            "total_cost_usd": 0.0,
            "weighted_total_duration_ms": 0.0,
            "weighted_first_token_ms": 0.0,
            "weighted_stream_duration_ms": 0.0,
            "task_count": 0,
            "plan_count": 0,
            "execution_count": 0,
            "task_request_estimate": 0.0,
            "plan_request_estimate": 0.0,
            "execution_request_estimate": 0.0,
            "prompt_utilization_known_count": 0,
            "prompt_utilization_unknown_count": 0,
            "prompt_utilization_not_applicable_count": 0,
            "prompt_utilization_ratio_weighted_sum": 0.0,
            "inference_utilization_known_count": 0,
            "inference_utilization_unknown_count": 0,
            "inference_utilization_not_applicable_count": 0,
            "inference_utilization_ratio_weighted_sum": 0.0,
        }

        for item in dashboard["items"]:
            requests_total = int(item.get("requests_total") or 0)
            totals["requests_total"] += requests_total
            totals["requests_success"] += int(item.get("requests_success") or 0)
            totals["requests_failed"] += int(item.get("requests_failed") or 0)
            totals["fallback_rate_numerator"] += (
                float(item.get("fallback_rate_percent") or 0.0) * requests_total / 100.0
            )
            totals["total_cost_usd"] += float(item.get("total_cost_usd") or 0.0)
            totals["weighted_total_duration_ms"] += (
                float(item.get("avg_total_duration_ms") or 0.0) * requests_total
            )
            totals["weighted_first_token_ms"] += (
                float(item.get("avg_first_token_ms") or 0.0) * requests_total
            )
            totals["weighted_stream_duration_ms"] += (
                float(item.get("avg_stream_duration_ms") or 0.0) * requests_total
            )
            totals["task_count"] += int(item.get("task_count") or 0)
            totals["plan_count"] += int(item.get("plan_count") or 0)
            totals["execution_count"] += int(item.get("execution_count") or 0)
            totals["task_request_estimate"] += (
                float(item.get("task_conversion_rate_percent") or 0.0) * requests_total / 100.0
            )
            totals["plan_request_estimate"] += (
                float(item.get("plan_conversion_rate_percent") or 0.0) * requests_total / 100.0
            )
            totals["execution_request_estimate"] += (
                float(item.get("execution_conversion_rate_percent") or 0.0) * requests_total / 100.0
            )
            prompt_known = int(item.get("prompt_utilization_known_count") or 0)
            prompt_unknown = int(item.get("prompt_utilization_unknown_count") or 0)
            prompt_not_applicable = int(item.get("prompt_utilization_not_applicable_count") or 0)
            inference_known = int(item.get("inference_utilization_known_count") or 0)
            inference_unknown = int(item.get("inference_utilization_unknown_count") or 0)
            inference_not_applicable = int(item.get("inference_utilization_not_applicable_count") or 0)
            totals["prompt_utilization_known_count"] += prompt_known
            totals["prompt_utilization_unknown_count"] += prompt_unknown
            totals["prompt_utilization_not_applicable_count"] += prompt_not_applicable
            totals["inference_utilization_known_count"] += inference_known
            totals["inference_utilization_unknown_count"] += inference_unknown
            totals["inference_utilization_not_applicable_count"] += inference_not_applicable
            if prompt_known > 0:
                totals["prompt_utilization_ratio_weighted_sum"] += float(
                    item.get("avg_prompt_utilization_percent") or 0.0
                ) * prompt_known
            if inference_known > 0:
                totals["inference_utilization_ratio_weighted_sum"] += float(
                    item.get("avg_inference_utilization_percent") or 0.0
                ) * inference_known

        requests_total = int(totals["requests_total"])
        requests_success = int(totals["requests_success"])
        trend_by_mode: dict[str, list[dict[str, Any]]] = {}
        for row in trend_rows:
            chat_mode = str(row.get("chat_mode") or "standard")
            trend_by_mode.setdefault(chat_mode, []).append(
                {
                    "date": row.get("date"),
                    "requests_total": int(row.get("requests_total") or 0),
                    "success_rate_percent": float(row.get("success_rate_percent") or 0.0),
                    "fallback_rate_percent": float(row.get("fallback_rate_percent") or 0.0),
                    "total_cost_usd": float(row.get("total_cost_usd") or 0.0),
                    "avg_total_duration_ms": float(row.get("avg_total_duration_ms") or 0.0),
                    "avg_first_token_ms": float(row.get("avg_first_token_ms") or 0.0),
                    "avg_stream_duration_ms": float(row.get("avg_stream_duration_ms") or 0.0),
                    "execution_conversion_rate_percent": float(
                        row.get("execution_conversion_rate_percent") or 0.0
                    ),
                }
            )

        for points in trend_by_mode.values():
            points.sort(key=lambda item: item["date"])

        return {
            "window_days": days,
            "overview": {
                "requests_total": requests_total,
                "requests_success": requests_success,
                "requests_failed": int(totals["requests_failed"]),
                "success_rate_percent": round((requests_success / requests_total) * 100, 2)
                if requests_total > 0
                else 0.0,
                "fallback_rate_percent": round(
                    (float(totals["fallback_rate_numerator"]) / requests_total) * 100,
                    2,
                )
                if requests_total > 0
                else 0.0,
                "total_cost_usd": round(float(totals["total_cost_usd"]), 6),
                "avg_total_duration_ms": round(
                    float(totals["weighted_total_duration_ms"]) / requests_total,
                    2,
                )
                if requests_total > 0
                else 0.0,
                "avg_first_token_ms": round(
                    float(totals["weighted_first_token_ms"]) / requests_total,
                    2,
                )
                if requests_total > 0
                else 0.0,
                "avg_stream_duration_ms": round(
                    float(totals["weighted_stream_duration_ms"]) / requests_total,
                    2,
                )
                if requests_total > 0
                else 0.0,
                "task_count": int(totals["task_count"]),
                "plan_count": int(totals["plan_count"]),
                "execution_count": int(totals["execution_count"]),
                "task_conversion_rate_percent": round(
                    (float(totals["task_request_estimate"]) / requests_total) * 100,
                    2,
                )
                if requests_total > 0
                else 0.0,
                "plan_conversion_rate_percent": round(
                    (float(totals["plan_request_estimate"]) / requests_total) * 100,
                    2,
                )
                if requests_total > 0
                else 0.0,
                "execution_conversion_rate_percent": round(
                    (float(totals["execution_request_estimate"]) / requests_total) * 100,
                    2,
                )
                if requests_total > 0
                else 0.0,
                "avg_prompt_utilization_percent": round(
                    float(totals["prompt_utilization_ratio_weighted_sum"])
                    / max(int(totals["prompt_utilization_known_count"]), 1),
                    2,
                )
                if int(totals["prompt_utilization_known_count"]) > 0
                else 0.0,
                "avg_inference_utilization_percent": round(
                    float(totals["inference_utilization_ratio_weighted_sum"])
                    / max(int(totals["inference_utilization_known_count"]), 1),
                    2,
                )
                if int(totals["inference_utilization_known_count"]) > 0
                else 0.0,
                "prompt_utilization_known_count": int(totals["prompt_utilization_known_count"]),
                "prompt_utilization_unknown_count": int(totals["prompt_utilization_unknown_count"]),
                "prompt_utilization_not_applicable_count": int(
                    totals["prompt_utilization_not_applicable_count"]
                ),
                "inference_utilization_known_count": int(totals["inference_utilization_known_count"]),
                "inference_utilization_unknown_count": int(
                    totals["inference_utilization_unknown_count"]
                ),
                "inference_utilization_not_applicable_count": int(
                    totals["inference_utilization_not_applicable_count"]
                ),
            },
            "items": dashboard["items"],
            "trend_series": [
                {
                    "chat_mode": chat_mode,
                    "points": points,
                }
                for chat_mode, points in sorted(trend_by_mode.items())
            ],
            "generated_at": dashboard["generated_at"],
        }

    async def _invalidate_cache(self, user_id: UUID) -> None:
        """清除与用户设置相关的缓存"""
        if not self.redis:
            try:
                from app.core.cache import cache_service

                if cache_service.redis:
                    self.redis = cache_service.redis
            except Exception:
                pass

        if self.redis:
            try:
                # 清除日程相关缓存
                await self.redis.delete(f"schedule:active_hours:{user_id}")
                # 清除个性化配置缓存
                await self.redis.delete(f"personalization:{user_id}")
                logger.debug(f"Invalidated cache for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to invalidate cache for user {user_id}: {e}")

    async def _ensure_redis(self):
        if self.redis:
            return self.redis
        try:
            from app.core.cache import cache_service

            self.redis = cache_service.redis
        except Exception:
            self.redis = None
        return self.redis

    async def _get_settings(self, user_id: UUID) -> UserSettings | None:
        result = await self.db.execute(
            select(UserSettings).where(
                UserSettings.user_id == user_id,
                UserSettings.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
