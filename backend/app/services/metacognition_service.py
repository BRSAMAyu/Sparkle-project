from __future__ import annotations

import json
import statistics
import time
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.cache import cache_service
from app.core.metrics import (
    METACOG_BIAS_UPDATED_TOTAL,
    METACOG_PROCESS_SCAFFOLD_TOTAL,
    METACOG_SAMPLE_BELOW_THRESHOLD_TOTAL,
)
from app.models.chat import ChatMessage, MessageRole
from app.models.memory import MemoryCorrection
from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from app.models.theater_prediction import TheaterPrediction
from app.models.user_preferences import UserPreferencesCenter
from app.services.aurora_stage30_metacognition_kill_switch_service import (
    AuroraStage30MetacognitionKillSwitchService,
)
from app.services.metacognition_guard import record_metric, scan_many
from app.services.metacognition_registry import (
    CONFIDENCE_PROXY_REGISTRY,
    ensure_registered_proxies,
    get_confidence_proxy,
    list_templates,
    render_template,
)
from app.state_aggregator.schema import (
    MetacognitionDimensionSummaryValue,
    MetacognitionProfileSummaryValue,
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class MetacognitionService:
    CACHE_PREFIX = "metacognition:snapshot:"
    COOLDOWN_PREFIX = "metacognition:process_scaffold:"
    CACHE_TTL_SECONDS = int(settings.AURORA_METACOG_CACHE_TTL_SECONDS)
    DIMENSIONS = ("completion_bias", "mastery_bias", "time_estimation_bias")
    DASHBOARD_ORDER = ("time_estimation_bias", "completion_bias", "mastery_bias")
    _fallback_cache: dict[str, tuple[dict[str, Any], datetime]] = {}
    _local_cooldowns: dict[str, datetime] = {}

    def __init__(self, db: AsyncSession, redis=None, event_bus=None) -> None:
        self.db = db
        self.redis = redis or cache_service.redis
        self.event_bus = event_bus
        self.kill_switch = AuroraStage30MetacognitionKillSwitchService()

    async def get_snapshot(
        self,
        user_id: UUID,
        *,
        force_refresh: bool = False,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        reference_time = now or _utcnow()
        if not force_refresh:
            cached = await self._read_cache(user_id, reference_time)
            if cached is not None:
                return cached
        return await self.refresh_snapshot(user_id, now=reference_time)

    async def refresh_snapshot(
        self,
        user_id: UUID,
        *,
        now: datetime | None = None,
        publish_event: bool = True,
    ) -> dict[str, Any]:
        started_at = time.perf_counter()
        reference_time = now or _utcnow()
        mode = await self.kill_switch.get_mode()
        if mode == "off":
            snapshot = self._empty_snapshot(user_id, reference_time, mode=mode)
            await self._write_cache(user_id, snapshot)
            return snapshot

        dims = await self._build_dimension_profiles(user_id, reference_time)
        proxies = await self._build_proxy_snapshot(user_id, reference_time)
        snapshot = {
            "user_id": str(user_id),
            "mode": mode,
            "generated_at": reference_time.isoformat(),
            "dimensions": dims,
            "proxy_snapshot": proxies,
        }
        await self._write_cache(user_id, snapshot)
        METACOG_BIAS_UPDATED_TOTAL.labels(result="refreshed").inc()

        if publish_event and self.event_bus is not None:
            await self.event_bus.publish(
                "metacog.updated",
                {
                    "user_id": str(user_id),
                    "generated_at": snapshot["generated_at"],
                    "dimension_count": len(dims),
                },
            )

        elapsed_ms = (time.perf_counter() - started_at) * 1000.0
        if elapsed_ms > float(settings.AURORA_METACOG_P95_MS_BUDGET):
            logger.warning(
                "Metacognition snapshot exceeded budget user_id={} elapsed_ms={:.2f}",
                user_id,
                elapsed_ms,
            )
        return snapshot

    async def build_aggregator_summary(
        self, user_id: UUID
    ) -> MetacognitionProfileSummaryValue:
        snapshot = await self.get_snapshot(user_id)
        if snapshot.get("mode") == "off":
            return MetacognitionProfileSummaryValue(items=())

        items = []
        for dim in snapshot.get("dimensions", []):
            if int(dim.get("sample_size") or 0) < int(
                settings.AURORA_METACOG_MIN_SAMPLE_SIZE
            ):
                continue
            items.append(
                MetacognitionDimensionSummaryValue(
                    dim=str(dim.get("dim") or ""),
                    sample_size=int(dim.get("sample_size") or 0),
                    bias_mean=round(float(dim.get("bias_mean") or 0.0), 4),
                    trend=str(dim.get("trend") or "stable"),
                )
            )
        return MetacognitionProfileSummaryValue(items=tuple(items))

    async def build_daily_accuracy_series(
        self,
        user_id: UUID,
        *,
        now: datetime | None = None,
        days: int = 45,
    ) -> dict[date, float]:
        reference_time = now or _utcnow()
        earliest_day = reference_time.date() - timedelta(days=max(1, int(days or 45)) - 1)
        rows = (
            await self._collect_completion_bias_rows(user_id)
            + await self._collect_mastery_bias_rows(user_id)
            + await self._collect_time_estimation_bias_rows(user_id)
        )
        grouped: dict[datetime.date, list[float]] = {}
        for row in rows:
            recorded_at = row.get("recorded_at") or reference_time
            recorded_day = recorded_at.date()
            if recorded_day < earliest_day or recorded_day > reference_time.date():
                continue
            accuracy = 1.0 - min(1.0, abs(float(row.get("bias") or 0.0)))
            grouped.setdefault(recorded_day, []).append(round(accuracy, 4))
        return {
            day: round(statistics.mean(values), 4)
            for day, values in grouped.items()
            if values
        }

    async def build_dashboard_payload(self, user_id: UUID) -> dict[str, Any]:
        snapshot = await self.get_snapshot(user_id)
        panel_hidden = await self._load_panel_hidden(user_id)
        dashboard_mode = await self.kill_switch.get_feature_mode("dashboard")
        if snapshot.get("mode") == "off" or dashboard_mode != "live":
            return {
                "available": False,
                "hidden": panel_hidden,
                "cards": [],
                "generated_at": snapshot.get("generated_at"),
            }

        cards: list[dict[str, Any]] = []
        dimension_map = {
            item["dim"]: item
            for item in snapshot.get("dimensions", [])
            if isinstance(item, dict)
        }
        for dim in self.DASHBOARD_ORDER:
            item = dimension_map.get(dim)
            if not item:
                continue
            card = await self._build_dashboard_card(item)
            if card is None:
                return {
                    "available": False,
                    "hidden": panel_hidden,
                    "cards": [],
                    "generated_at": snapshot.get("generated_at"),
                }
            cards.append(card)
        return {
            "available": True,
            "hidden": panel_hidden,
            "cards": cards,
            "generated_at": snapshot.get("generated_at"),
        }

    async def build_prompt_process_scaffolding(
        self,
        user_id: UUID,
        *,
        consume: bool = True,
    ) -> dict[str, Any] | None:
        process_mode = await self.kill_switch.get_feature_mode("process_scaffolding")
        if process_mode != "live":
            return None

        snapshot = await self.get_snapshot(user_id)
        candidate = await self._select_process_candidate(snapshot)
        if candidate is None:
            METACOG_PROCESS_SCAFFOLD_TOTAL.labels(
                status="skipped", reason="below_sample_size"
            ).inc()
            return None

        if consume and await self._is_in_cooldown(user_id, str(candidate["dim"])):
            METACOG_PROCESS_SCAFFOLD_TOTAL.labels(
                status="skipped", reason="cooldown"
            ).inc()
            return None

        if consume:
            await self._mark_cooldown(user_id, str(candidate["dim"]))
        if self.event_bus is not None and consume:
            await self.event_bus.publish(
                "process_scaffold.triggered",
                {
                    "user_id": str(user_id),
                    "dim": candidate["dim"],
                    "template_id": candidate["template_id"],
                },
            )
        METACOG_PROCESS_SCAFFOLD_TOTAL.labels(
            status="triggered", reason="eligible"
        ).inc()
        return candidate

    async def get_proxy_snapshot(
        self,
        user_id: UUID,
        *,
        proxy_ids: list[str] | tuple[str, ...] | None = None,
    ) -> dict[str, dict[str, Any]]:
        requested = ensure_registered_proxies(
            proxy_ids or tuple(CONFIDENCE_PROXY_REGISTRY)
        )
        snapshot = await self.get_snapshot(user_id)
        proxy_snapshot = snapshot.get("proxy_snapshot", {})
        return {
            proxy_id: dict(proxy_snapshot.get(proxy_id) or {}) for proxy_id in requested
        }

    async def _build_dimension_profiles(
        self, user_id: UUID, now: datetime
    ) -> list[dict[str, Any]]:
        raw_rows = {
            "completion_bias": await self._collect_completion_bias_rows(user_id),
            "mastery_bias": await self._collect_mastery_bias_rows(user_id),
            "time_estimation_bias": await self._collect_time_estimation_bias_rows(
                user_id
            ),
        }
        profiles: list[dict[str, Any]] = []
        for dim, rows in raw_rows.items():
            profile = self._aggregate_dimension_rows(dim, rows, now)
            if profile["sample_size"] < int(settings.AURORA_METACOG_MIN_SAMPLE_SIZE):
                METACOG_SAMPLE_BELOW_THRESHOLD_TOTAL.labels(dim=dim).inc()
            profiles.append(profile)
        return profiles

    async def _build_proxy_snapshot(
        self, user_id: UUID, now: datetime
    ) -> dict[str, dict[str, Any]]:
        proxy_snapshot: dict[str, dict[str, Any]] = {}
        for proxy_id, definition in CONFIDENCE_PROXY_REGISTRY.items():
            if not self._proxy_enabled(definition.settings_attr):
                continue
            builder = getattr(self, f"_build_proxy_{proxy_id}")
            proxy_snapshot[proxy_id] = await builder(user_id, now)
        return proxy_snapshot

    async def _collect_completion_bias_rows(
        self, user_id: UUID
    ) -> list[dict[str, Any]]:
        stmt = (
            select(
                TheaterPrediction.generated_at,
                TheaterPrediction.selected_prediction,
                TheaterPrediction.accuracy_summary,
            )
            .where(
                TheaterPrediction.user_id == user_id,
                TheaterPrediction.deleted_at.is_(None),
                TheaterPrediction.accuracy_summary.is_not(None),
            )
            .order_by(TheaterPrediction.generated_at.asc())
            .limit(60)
        )
        result = await self.db.execute(stmt)
        rows = []
        for generated_at, selected_prediction, accuracy_summary in result.all():
            if not isinstance(selected_prediction, dict) or not isinstance(
                accuracy_summary, dict
            ):
                continue
            predicted = float(
                accuracy_summary.get("predicted_completion_rate")
                or selected_prediction.get("estimated_completion_rate")
                or 0.0
            )
            actual = float(accuracy_summary.get("actual_completion_rate") or 0.0)
            rows.append(
                {
                    "bias": actual - predicted,
                    "display_bias": (actual - predicted) * 100.0,
                    "predicted": predicted * 100.0,
                    "actual": actual * 100.0,
                    "recorded_at": generated_at or _utcnow(),
                }
            )
        return rows

    async def _collect_mastery_bias_rows(self, user_id: UUID) -> list[dict[str, Any]]:
        stmt = (
            select(
                TheaterPrediction.generated_at,
                TheaterPrediction.selected_prediction,
                TheaterPrediction.accuracy_summary,
            )
            .where(
                TheaterPrediction.user_id == user_id,
                TheaterPrediction.deleted_at.is_(None),
                TheaterPrediction.accuracy_summary.is_not(None),
            )
            .order_by(TheaterPrediction.generated_at.asc())
            .limit(60)
        )
        result = await self.db.execute(stmt)
        rows = []
        for generated_at, selected_prediction, accuracy_summary in result.all():
            if not isinstance(selected_prediction, dict) or not isinstance(
                accuracy_summary, dict
            ):
                continue
            predicted = float(
                accuracy_summary.get("predicted_mastery")
                or selected_prediction.get("estimated_mastery")
                or 0.0
            )
            actual = float(accuracy_summary.get("actual_mastery") or 0.0)
            rows.append(
                {
                    "bias": (actual - predicted) / 100.0,
                    "display_bias": actual - predicted,
                    "predicted": predicted,
                    "actual": actual,
                    "recorded_at": generated_at or _utcnow(),
                }
            )
        return rows

    async def _collect_time_estimation_bias_rows(
        self, user_id: UUID
    ) -> list[dict[str, Any]]:
        stmt = (
            select(
                Task.completed_at,
                Task.estimated_minutes,
                Task.actual_minutes,
            )
            .where(
                Task.user_id == user_id,
                Task.deleted_at.is_(None),
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at.is_not(None),
                Task.estimated_minutes.is_not(None),
                Task.actual_minutes.is_not(None),
                Task.estimated_minutes > 0,
                Task.actual_minutes > 0,
            )
            .order_by(Task.completed_at.asc())
            .limit(60)
        )
        result = await self.db.execute(stmt)
        rows = []
        for completed_at, estimated_minutes, actual_minutes in result.all():
            estimated = float(estimated_minutes or 0.0)
            actual = float(actual_minutes or 0.0)
            if estimated <= 0 or actual <= 0:
                continue
            rows.append(
                {
                    "bias": (actual - estimated) / estimated,
                    "display_bias": (actual - estimated) / 60.0,
                    "predicted": estimated / 60.0,
                    "actual": actual / 60.0,
                    "recorded_at": completed_at or _utcnow(),
                }
            )
        return rows

    def _aggregate_dimension_rows(
        self,
        dim: str,
        rows: list[dict[str, Any]],
        now: datetime,
    ) -> dict[str, Any]:
        values = [float(item.get("bias") or 0.0) for item in rows]
        display_values = [float(item.get("display_bias") or 0.0) for item in rows]
        predicted_values = [float(item.get("predicted") or 0.0) for item in rows]
        actual_values = [float(item.get("actual") or 0.0) for item in rows]
        timestamps = [item.get("recorded_at") or now for item in rows]
        sample_size = len(values)
        trend_slope = self._trend_slope(values)
        trend = self._trend_label(trend_slope)
        return {
            "dim": dim,
            "sample_size": sample_size,
            "bias_mean": round(statistics.mean(values), 4) if values else 0.0,
            "bias_stddev": (
                round(statistics.pstdev(values), 4) if len(values) > 1 else 0.0
            ),
            "trend_slope": round(trend_slope, 4),
            "trend": trend,
            "last_updated": (
                max(timestamps).isoformat() if timestamps else now.isoformat()
            ),
            "display_mean": (
                round(statistics.mean(display_values), 2) if display_values else 0.0
            ),
            "mean_predicted": (
                round(statistics.mean(predicted_values), 2) if predicted_values else 0.0
            ),
            "mean_actual": (
                round(statistics.mean(actual_values), 2) if actual_values else 0.0
            ),
        }

    async def _build_proxy_revision_frequency(
        self, user_id: UUID, now: datetime
    ) -> dict[str, Any]:
        threshold = timedelta(minutes=10)
        stmt = (
            select(Task.completed_at, Task.updated_at)
            .where(
                Task.user_id == user_id,
                Task.deleted_at.is_(None),
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at.is_not(None),
            )
            .order_by(Task.completed_at.desc())
            .limit(60)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        revised = sum(
            1
            for completed_at, updated_at in rows
            if completed_at and updated_at and updated_at - completed_at > threshold
        )
        sample_size = len(rows)
        return {
            "proxy_id": "revision_frequency",
            "value": round((revised / sample_size), 4) if sample_size else 0.0,
            "sample_size": sample_size,
            "last_updated": now.isoformat(),
        }

    async def _build_proxy_self_correction_rate(
        self, user_id: UUID, now: datetime
    ) -> dict[str, Any]:
        since = now - timedelta(days=90)
        correction_count = int(
            (
                await self.db.execute(
                    select(func.count(MemoryCorrection.id)).where(
                        MemoryCorrection.user_id == user_id,
                        MemoryCorrection.deleted_at.is_(None),
                        MemoryCorrection.created_at >= since,
                    )
                )
            ).scalar_one()
            or 0
        )
        message_count = int(
            (
                await self.db.execute(
                    select(func.count(ChatMessage.id)).where(
                        ChatMessage.user_id == user_id,
                        ChatMessage.deleted_at.is_(None),
                        ChatMessage.role == MessageRole.USER,
                        ChatMessage.created_at >= since,
                    )
                )
            ).scalar_one()
            or 0
        )
        return {
            "proxy_id": "self_correction_rate",
            "value": (
                round((correction_count / message_count), 4) if message_count else 0.0
            ),
            "sample_size": message_count,
            "last_updated": now.isoformat(),
        }

    async def _build_proxy_question_to_statement_ratio(
        self, user_id: UUID, now: datetime
    ) -> dict[str, Any]:
        stmt = (
            select(ChatMessage.content)
            .where(
                ChatMessage.user_id == user_id,
                ChatMessage.deleted_at.is_(None),
                ChatMessage.role == MessageRole.USER,
            )
            .order_by(ChatMessage.created_at.desc())
            .limit(120)
        )
        result = await self.db.execute(stmt)
        contents = [
            str(content or "").strip()
            for (content,) in result.all()
            if str(content or "").strip()
        ]
        question_count = sum(
            1 for content in contents if "?" in content or "？" in content
        )
        total = len(contents)
        return {
            "proxy_id": "question_to_statement_ratio",
            "value": round((question_count / total), 4) if total else 0.0,
            "sample_size": total,
            "last_updated": now.isoformat(),
        }

    async def _build_proxy_time_to_first_action(
        self, user_id: UUID, now: datetime
    ) -> dict[str, Any]:
        earliest_action = func.min(
            func.coalesce(Task.started_at, Task.confirmed_at, Task.completed_at)
        )
        stmt = (
            select(
                Plan.created_at,
                earliest_action,
            )
            .outerjoin(Task, and_(Task.plan_id == Plan.id, Task.deleted_at.is_(None)))
            .where(
                Plan.user_id == user_id,
                Plan.deleted_at.is_(None),
            )
            .group_by(Plan.id, Plan.created_at)
            .order_by(Plan.created_at.desc())
            .limit(30)
        )
        result = await self.db.execute(stmt)
        deltas = []
        for created_at, first_action_at in result.all():
            if (
                created_at is None
                or first_action_at is None
                or first_action_at < created_at
            ):
                continue
            deltas.append((first_action_at - created_at).total_seconds() / 3600.0)
        return {
            "proxy_id": "time_to_first_action",
            "value": round(statistics.mean(deltas), 4) if deltas else 0.0,
            "sample_size": len(deltas),
            "last_updated": now.isoformat(),
        }

    async def _build_proxy_completion_vs_estimate_delta_sign(
        self, user_id: UUID, now: datetime
    ) -> dict[str, Any]:
        stmt = (
            select(Task.estimated_minutes, Task.actual_minutes)
            .where(
                Task.user_id == user_id,
                Task.deleted_at.is_(None),
                Task.status == TaskStatus.COMPLETED,
                Task.estimated_minutes.is_not(None),
                Task.actual_minutes.is_not(None),
                Task.estimated_minutes > 0,
                Task.actual_minutes > 0,
            )
            .order_by(Task.completed_at.desc())
            .limit(60)
        )
        result = await self.db.execute(stmt)
        signs = []
        for estimated_minutes, actual_minutes in result.all():
            estimated = float(estimated_minutes or 0.0)
            actual = float(actual_minutes or 0.0)
            if actual > estimated:
                signs.append(1.0)
            elif actual < estimated:
                signs.append(-1.0)
            else:
                signs.append(0.0)
        return {
            "proxy_id": "completion_vs_estimate_delta_sign",
            "value": round(statistics.mean(signs), 4) if signs else 0.0,
            "sample_size": len(signs),
            "last_updated": now.isoformat(),
        }

    async def _build_dashboard_card(
        self, item: dict[str, Any]
    ) -> dict[str, Any] | None:
        dim = str(item.get("dim") or "")
        sample_size = int(item.get("sample_size") or 0)
        threshold = int(settings.AURORA_METACOG_MIN_SAMPLE_SIZE)
        if sample_size < threshold:
            body = render_template("mc_dashboard_insufficient")
            return {
                "dim": dim,
                "title": self._dashboard_title(dim),
                "status": "insufficient",
                "template_id": "mc_dashboard_insufficient",
                "body": body,
                "trend_text": "",
                "sample_size": sample_size,
            }

        direction = self._dashboard_direction(dim, float(item.get("bias_mean") or 0.0))
        body_template = next(
            template
            for template in list_templates(
                kind="dashboard_body", dim=dim, direction=direction
            )
            if template.dim == dim
        )
        body = render_template(
            body_template.template_id,
            sample_size=sample_size,
            display_value=self._format_display_value(
                dim, float(item.get("display_mean") or 0.0)
            ),
        )
        trend = str(item.get("trend") or "stable")
        trend_template = next(
            template
            for template in list_templates(kind="dashboard_trend", direction=trend)
        )
        trend_text = render_template(trend_template.template_id)
        if not await self._enforce_language_contract(
            [body, trend_text], source="dashboard"
        ):
            return None
        return {
            "dim": dim,
            "title": self._dashboard_title(dim),
            "status": "ready",
            "template_id": body_template.template_id,
            "body": body,
            "trend_text": trend_text,
            "sample_size": sample_size,
        }

    async def _select_process_candidate(
        self, snapshot: dict[str, Any]
    ) -> dict[str, Any] | None:
        threshold = float(settings.AURORA_METACOG_PROCESS_TRIGGER_ABS_BIAS)
        eligible = [
            item
            for item in snapshot.get("dimensions", [])
            if int(item.get("sample_size") or 0)
            >= int(settings.AURORA_METACOG_MIN_SAMPLE_SIZE)
            and abs(float(item.get("bias_mean") or 0.0)) >= threshold
        ]
        if not eligible:
            return None

        dominant = max(
            eligible, key=lambda item: abs(float(item.get("bias_mean") or 0.0))
        )
        dim = str(dominant.get("dim") or "")
        direction = self._support_direction(
            dim, float(dominant.get("bias_mean") or 0.0)
        )
        if dominant["sample_size"] >= 40:
            repeat_template_id = "mc_process_cross_dim_repeat"
            text = render_template(
                repeat_template_id,
                repeat_count=max(3, min(int(dominant["sample_size"] // 10), 6)),
            )
            if not await self._enforce_language_contract(
                [text], source="process_scaffolding"
            ):
                return None
            return {
                "dim": dim,
                "template_id": repeat_template_id,
                "body": text,
                "sample_size": dominant["sample_size"],
                "bias_mean": dominant["bias_mean"],
            }

        candidates = [
            item
            for item in list_templates(
                kind="process_scaffolding", dim=dim, direction=direction
            )
            if item.dim == dim
        ]
        template = candidates[0]
        text = render_template(
            template.template_id,
            predicted_value=self._format_display_value(
                dim, float(dominant.get("mean_predicted") or 0.0)
            ),
            actual_value=self._format_display_value(
                dim, float(dominant.get("mean_actual") or 0.0)
            ),
            repeat_count=max(3, min(int(dominant["sample_size"] // 10), 6)),
        )
        if not await self._enforce_language_contract(
            [text], source="process_scaffolding"
        ):
            return None
        return {
            "dim": dim,
            "template_id": template.template_id,
            "body": text,
            "sample_size": dominant["sample_size"],
            "bias_mean": dominant["bias_mean"],
        }

    def _dashboard_title(self, dim: str) -> str:
        return {
            "time_estimation_bias": "时间预估",
            "completion_bias": "完成预估",
            "mastery_bias": "掌握度预估",
        }.get(dim, dim)

    def _dashboard_direction(self, dim: str, bias_mean: float) -> str:
        if dim == "time_estimation_bias":
            return "more_support" if bias_mean >= 0 else "less_support"
        return "more_support" if bias_mean < 0 else "less_support"

    def _support_direction(self, dim: str, bias_mean: float) -> str:
        return self._dashboard_direction(dim, bias_mean)

    def _format_display_value(self, dim: str, value: float) -> str:
        magnitude = abs(float(value or 0.0))
        if dim == "time_estimation_bias":
            return f"{magnitude:.1f}"
        return f"{magnitude:.1f}"

    def _trend_slope(self, values: list[float]) -> float:
        if len(values) < 3:
            return 0.0
        xs = list(range(len(values)))
        ys = [abs(value) for value in values]
        x_mean = statistics.mean(xs)
        y_mean = statistics.mean(ys)
        denominator = sum((x - x_mean) ** 2 for x in xs)
        if denominator == 0:
            return 0.0
        numerator = sum(
            (x - x_mean) * (y - y_mean) for x, y in zip(xs, ys, strict=False)
        )
        return numerator / denominator

    @staticmethod
    def _trend_label(slope: float) -> str:
        if slope <= -0.015:
            return "improving"
        if slope >= 0.015:
            return "worsening"
        return "stable"

    async def _load_panel_hidden(self, user_id: UUID) -> bool:
        result = await self.db.execute(
            select(UserPreferencesCenter.explicit).where(
                UserPreferencesCenter.user_id == user_id
            )
        )
        explicit = result.scalar_one_or_none()
        return bool((explicit or {}).get("metacognition_dashboard_hidden"))

    def _proxy_enabled(self, settings_attr: str) -> bool:
        return str(getattr(settings, settings_attr, "off")).strip().lower() != "off"

    async def _read_cache(self, user_id: UUID, now: datetime) -> dict[str, Any] | None:
        cache_key = f"{self.CACHE_PREFIX}{user_id}"
        if self.redis is not None:
            raw = await self.redis.get(cache_key)
            if raw:
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                try:
                    return json.loads(raw)
                except Exception:
                    logger.warning(
                        "Invalid metacognition cache payload for {}", user_id
                    )
        cached = self._fallback_cache.get(cache_key)
        if cached is None:
            return None
        payload, expires_at = cached
        if expires_at <= now:
            self._fallback_cache.pop(cache_key, None)
            return None
        return payload

    async def _write_cache(self, user_id: UUID, payload: dict[str, Any]) -> None:
        cache_key = f"{self.CACHE_PREFIX}{user_id}"
        if self.redis is not None:
            await self.redis.setex(
                cache_key, self.CACHE_TTL_SECONDS, json.dumps(payload)
            )
            return
        self._fallback_cache[cache_key] = (
            payload,
            _utcnow() + timedelta(seconds=self.CACHE_TTL_SECONDS),
        )

    async def _is_in_cooldown(self, user_id: UUID, dim: str) -> bool:
        key = f"{self.COOLDOWN_PREFIX}{user_id}:{dim}"
        if self.redis is not None:
            return bool(await self.redis.get(key))
        expires_at = self._local_cooldowns.get(key)
        return bool(expires_at and expires_at > _utcnow())

    async def _mark_cooldown(self, user_id: UUID, dim: str) -> None:
        key = f"{self.COOLDOWN_PREFIX}{user_id}:{dim}"
        ttl_seconds = int(
            timedelta(
                hours=settings.AURORA_METACOG_PROCESS_COOLDOWN_HOURS
            ).total_seconds()
        )
        if self.redis is not None:
            await self.redis.setex(key, ttl_seconds, "1")
            return
        self._local_cooldowns[key] = _utcnow() + timedelta(seconds=ttl_seconds)

    async def _enforce_language_contract(
        self, texts: list[str], *, source: str
    ) -> bool:
        violations = scan_many(tuple(texts), source=source)
        if not violations:
            return True
        record_metric(violations, source=source)
        logger.warning(
            "Metacognition language contract violation source={} matches={}",
            source,
            violations,
        )
        await self.kill_switch.auto_disable_on_diagnostic_hit(len(violations))
        return False

    def _empty_snapshot(
        self, user_id: UUID, now: datetime, *, mode: str
    ) -> dict[str, Any]:
        return {
            "user_id": str(user_id),
            "mode": mode,
            "generated_at": now.isoformat(),
            "dimensions": [],
            "proxy_snapshot": {},
        }
