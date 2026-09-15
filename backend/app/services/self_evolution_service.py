from __future__ import annotations

import asyncio
import importlib.util
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import mean
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.business_metrics import (
    ADAPTIVE_ROLLBACK_TOTAL,
    PERCEPTIBLE_INSIGHT_SENT_TOTAL,
    PERCEPTIBLE_INSIGHT_SKIPPED_TOTAL,
    snapshot_metric,
)
from app.core.i18n import I18n
from app.models.chat import ChatMessage, MessageRole
from app.models.cognitive import BehaviorPattern
from app.models.memory import MemoryPreference
from app.models.task import Task, TaskStatus
from app.services.system_update_service import SystemUpdateService, build_system_update


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _week_bucket(value: datetime | None = None) -> str:
    dt = value or _utcnow()
    iso_year, iso_week, _ = dt.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def _mean_std(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    avg = mean(values)
    if len(values) == 1:
        return avg, 0.0
    variance = sum((item - avg) ** 2 for item in values) / len(values)
    return avg, math.sqrt(max(variance, 0.0))


async def _redis_json_get(redis, key: str, default: Any) -> Any:
    if not redis:
        return default
    try:
        raw = await redis.get(key)
        if not raw:
            return default
        return json.loads(raw)
    except Exception as exc:
        logger.warning(f"Failed to read redis json key {key}: {exc}")
        return default


async def _redis_json_set(redis, key: str, value: Any, *, ttl_seconds: int | None = None) -> None:
    if not redis:
        return
    payload = json.dumps(value, ensure_ascii=False)
    try:
        if ttl_seconds:
            await redis.setex(key, ttl_seconds, payload)
        else:
            await redis.set(key, payload)
    except Exception as exc:
        logger.warning(f"Failed to persist redis json key {key}: {exc}")


@dataclass
class UnderstandingDepthSnapshot:
    level: str
    score: int
    dimensions: dict[str, Any]


class StrategyCalibrationService:
    TTL_SECONDS = int(timedelta(days=35).total_seconds())
    ALIGNMENT_SCORE_KEY_TTL = int(timedelta(days=30).total_seconds())

    def __init__(self, db: AsyncSession | None = None, redis=None):
        self.db = db
        self.redis = redis

    @staticmethod
    def _weekly_key(user_id: UUID | str, week_bucket: str) -> str:
        return f"strategy-calibration:{user_id}:{week_bucket}"

    @staticmethod
    def _alignment_user_key(user_id: UUID | str) -> str:
        return f"alignment-scores:{user_id}"

    @staticmethod
    def _alignment_global_key() -> str:
        return "alignment-scores:global"

    @staticmethod
    def _profile_hit_rate_user_key(user_id: UUID | str) -> str:
        return f"profile-hit-rate:{user_id}"

    @staticmethod
    def _profile_hit_rate_global_key() -> str:
        return "profile-hit-rate:global"

    async def record_mapping_alignment(
        self,
        *,
        user_id: UUID,
        mappings: list[dict[str, Any]],
        matched_rule_keys: list[str],
    ) -> None:
        if not self.redis or not mappings:
            return
        key = self._weekly_key(user_id, _week_bucket())
        payload = await _redis_json_get(self.redis, key, {})
        matched = set(matched_rule_keys)
        for mapping in mappings:
            rule_key = str(mapping.get("rule_key") or mapping.get("signal_key") or "").strip()
            if not rule_key:
                continue
            bucket = payload.setdefault(rule_key, {"hit": 0, "miss": 0})
            if rule_key in matched:
                bucket["hit"] = int(bucket.get("hit", 0)) + 1
            else:
                bucket["miss"] = int(bucket.get("miss", 0)) + 1
        await _redis_json_set(self.redis, key, payload, ttl_seconds=self.TTL_SECONDS)

    async def get_rule_calibration(self, *, user_id: UUID | str) -> dict[str, Any]:
        if not self.redis:
            return {"by_rule": {}, "weak_rules": []}
        weeks = [_week_bucket(_utcnow() - timedelta(days=offset * 7)) for offset in range(3)]
        by_rule: dict[str, dict[str, Any]] = {}
        for week in weeks:
            payload = await _redis_json_get(self.redis, self._weekly_key(user_id, week), {})
            for rule_key, stats in payload.items():
                if not isinstance(stats, dict):
                    continue
                entry = by_rule.setdefault(rule_key, {"weekly_hit_rates": []})
                hits = int(stats.get("hit", 0) or 0)
                misses = int(stats.get("miss", 0) or 0)
                total = hits + misses
                entry["weekly_hit_rates"].append(round(hits / total, 4) if total else 0.0)
        weak_rules: list[str] = []
        for rule_key, entry in by_rule.items():
            rates = list(entry.get("weekly_hit_rates") or [])
            is_weak = len(rates) == 3 and all(rate < 0.4 for rate in rates)
            entry["is_weak"] = is_weak
            entry["recent_hit_rate"] = round(rates[-1], 4) if rates else None
            if is_weak:
                weak_rules.append(rule_key)
        return {"by_rule": by_rule, "weak_rules": weak_rules}

    async def apply_rule_calibration(
        self,
        *,
        user_id: UUID | None,
        mappings: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        if not user_id or not mappings:
            return mappings, {"by_rule": {}, "weak_rules": []}
        calibration = await self.get_rule_calibration(user_id=user_id)
        weak_rules = set(calibration.get("weak_rules") or [])
        adjusted: list[dict[str, Any]] = []
        for mapping in mappings:
            rule_key = str(mapping.get("rule_key") or mapping.get("signal_key") or "").strip()
            updated = dict(mapping)
            if rule_key in weak_rules:
                updated["confidence_tier"] = "weak"
                updated["calibration_note"] = I18n.t("self_evolution.calibration_note_weak", locale="zh")
            adjusted.append(updated)
        return adjusted, calibration

    async def record_alignment_score(self, *, user_id: UUID, score: float | None) -> None:
        if not self.redis or score is None:
            return
        for key in (self._alignment_user_key(user_id), self._alignment_global_key()):
            items = await _redis_json_get(self.redis, key, [])
            if not isinstance(items, list):
                items = []
            items.append({"score": round(float(score), 4), "timestamp": _utcnow().isoformat()})
            await _redis_json_set(self.redis, key, items[-50:], ttl_seconds=self.ALIGNMENT_SCORE_KEY_TTL)

    async def record_profile_hit_rate(self, *, user_id: UUID, hit_rate: float | None) -> None:
        if not self.redis or hit_rate is None:
            return
        for key in (self._profile_hit_rate_user_key(user_id), self._profile_hit_rate_global_key()):
            items = await _redis_json_get(self.redis, key, [])
            if not isinstance(items, list):
                items = []
            items.append({"hit_rate": round(float(hit_rate), 4), "timestamp": _utcnow().isoformat()})
            await _redis_json_set(self.redis, key, items[-50:], ttl_seconds=self.ALIGNMENT_SCORE_KEY_TTL)

    async def latest_profile_hit_rate(self, *, user_id: UUID) -> float | None:
        items = await _redis_json_get(self.redis, self._profile_hit_rate_user_key(user_id), [])
        if not isinstance(items, list) or not items:
            return None
        try:
            return float(items[-1].get("hit_rate"))
        except Exception:
            return None

    async def recent_alignment_scores(self, *, user_id: UUID, limit: int = 3) -> list[float]:
        items = await _redis_json_get(self.redis, self._alignment_user_key(user_id), [])
        if not isinstance(items, list):
            return []
        scores: list[float] = []
        for item in items[-limit:]:
            try:
                scores.append(float(item.get("score")))
            except Exception:
                continue
        return scores

    async def global_latest(self, key: str) -> float | None:
        items = await _redis_json_get(self.redis, key, [])
        if not isinstance(items, list) or not items:
            return None
        try:
            field = "score" if "alignment" in key else "hit_rate"
            return float(items[-1].get(field))
        except Exception:
            return None


class UnderstandingDepthService:
    TTL_SECONDS = int(timedelta(days=365).total_seconds())
    LEVEL_ORDER = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4, "L5": 5}

    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis
        self.updates = SystemUpdateService(redis)
        self.calibration = StrategyCalibrationService(db, redis)

    @staticmethod
    def _current_level_key(user_id: UUID) -> str:
        return f"understanding-depth:current:{user_id}"

    @staticmethod
    def _notified_key(user_id: UUID, level: str) -> str:
        return f"understanding-depth:notified:{user_id}:{level}"

    @staticmethod
    def _natural_hint(level: str) -> str:
        hints = {
            "L1": I18n.t("self_evolution.understanding_depth_l1_unnoticed_hint", locale="zh"),
            "L2": I18n.t("self_evolution.understanding_depth_l2_unnoticed_hint", locale="zh"),
            "L3": I18n.t("self_evolution.understanding_depth_l3_unnoticed_hint", locale="zh"),
            "L4": I18n.t("self_evolution.understanding_depth_l4_unnoticed_hint", locale="zh"),
            "L5": I18n.t("self_evolution.understanding_depth_l5_unnoticed_hint", locale="zh"),
        }
        return hints.get(level, "")

    async def evaluate(self, *, user_id: UUID) -> UnderstandingDepthSnapshot:
        pref_count = await self.db.scalar(
            select(func.count(MemoryPreference.id)).where(
                MemoryPreference.user_id == user_id,
                MemoryPreference.deleted_at.is_(None),
                MemoryPreference.archived_at.is_(None),
                MemoryPreference.retracted_at.is_(None),
            )
        ) or 0
        pattern_count = await self.db.scalar(
            select(func.count(BehaviorPattern.id)).where(
                BehaviorPattern.user_id == user_id,
                BehaviorPattern.confidence_score >= 0.7,
                BehaviorPattern.is_archived.is_(False),
            )
        ) or 0
        alignment_scores = await self.calibration.recent_alignment_scores(user_id=user_id, limit=3)
        alignment_ready = len(alignment_scores) >= 3 and all(score >= 0.7 for score in alignment_scores[-3:])
        adoption_rate = await self._insight_adoption_rate(user_id=user_id)
        strategy_resonance_rate = await self._strategy_resonance_rate(user_id=user_id)

        level = "L0"
        score = 0
        if pref_count >= 3:
            level, score = "L1", 1
        if pattern_count >= 2:
            level, score = "L2", 2
        if alignment_ready:
            level, score = "L3", 3
        if adoption_rate is not None and adoption_rate >= 0.5:
            level, score = "L4", 4
        if strategy_resonance_rate is not None and strategy_resonance_rate >= 0.6:
            level, score = "L5", 5

        return UnderstandingDepthSnapshot(
            level=level,
            score=score,
            dimensions={
                "active_preferences": int(pref_count),
                "active_patterns": int(pattern_count),
                "recent_alignment_scores": alignment_scores,
                "insight_adoption_rate": adoption_rate,
                "strategy_resonance_rate": strategy_resonance_rate,
            },
        )

    async def maybe_enqueue_upgrade(self, *, user_id: UUID) -> dict[str, Any] | None:
        if not self.redis:
            return None
        snapshot = await self.evaluate(user_id=user_id)
        if snapshot.level == "L0":
            return None
        current = await _redis_json_get(self.redis, self._current_level_key(user_id), {})
        current_level = str(current.get("level") or "")
        current_score = self.LEVEL_ORDER.get(current_level, 0)
        next_score = self.LEVEL_ORDER.get(snapshot.level, 0)
        if current_level == snapshot.level:
            return None
        if next_score <= current_score:
            return None
        if await self.redis.exists(self._notified_key(user_id, snapshot.level)):
            return None

        descriptions = {
            "L1": I18n.t("self_evolution.upgrade_desc_l1", locale="zh"),
            "L2": I18n.t("self_evolution.upgrade_desc_l2", locale="zh"),
            "L3": I18n.t("self_evolution.upgrade_desc_l3", locale="zh"),
            "L4": I18n.t("self_evolution.upgrade_desc_l4", locale="zh"),
            "L5": I18n.t("self_evolution.upgrade_desc_l5", locale="zh"),
        }
        payload = build_system_update(
            update_type="understanding_depth_upgraded",
            category="evolution",
            title=I18n.t("self_evolution.upgrade_title", locale="zh"),
            description=descriptions.get(snapshot.level, I18n.t("self_evolution.upgrade_desc_fallback", locale="zh")),
            priority="low",
            metadata={
                "evolution_kind": "understanding_depth",
                "understanding_depth": {
                    "level": snapshot.level,
                    "score": snapshot.score,
                    "dimensions": snapshot.dimensions,
                },
                "natural_hint": self._natural_hint(snapshot.level),
            },
        )
        enqueued = await self.updates.enqueue(user_id, payload)
        if enqueued:
            await _redis_json_set(
                self.redis,
                self._current_level_key(user_id),
                {"level": snapshot.level, "updated_at": _utcnow().isoformat()},
                ttl_seconds=self.TTL_SECONDS,
            )
            await self.redis.setex(self._notified_key(user_id, snapshot.level), self.TTL_SECONDS, "1")
            return payload
        return None

    async def _strategy_resonance_rate(self, *, user_id: UUID) -> float | None:
        # 当前阶段先复用已校准的画像命中率作为“用户主动调整与系统建议方向一致率”的近似代理。
        # 后续如果存在更直接的主动调整追踪源，可替换这里的数据来源而不改等级定义。
        return await self.calibration.latest_profile_hit_rate(user_id=user_id)

    async def _insight_adoption_rate(self, *, user_id: UUID) -> float | None:
        if not self.redis:
            return None
        updates = await self.updates.list_updates(user_id, limit=80)
        insights = [
            update for update in updates
            if isinstance(update, dict)
            and isinstance(update.get("metadata"), dict)
            and update["metadata"].get("evolution_kind") == "proactive_insight"
        ]
        if not insights:
            return None
        adopted = 0
        for insight in insights[:10]:
            created_at = int(insight.get("created_at") or 0)
            if not created_at:
                continue
            created_dt = datetime.fromtimestamp(created_at, tz=UTC).replace(tzinfo=None)
            event_result = await self.db.execute(
                select(func.count(ChatMessage.id)).where(
                    ChatMessage.user_id == user_id,
                    ChatMessage.role == MessageRole.USER,
                    ChatMessage.created_at >= created_dt,
                    ChatMessage.created_at <= created_dt + timedelta(hours=24),
                )
            )
            task_result = await self.db.execute(
                select(func.count(Task.id)).where(
                    Task.user_id == user_id,
                    Task.status == TaskStatus.COMPLETED,
                    Task.completed_at.is_not(None),
                    Task.completed_at >= created_dt,
                    Task.completed_at <= created_dt + timedelta(hours=24),
                )
            )
            if int(event_result.scalar() or 0) > 0 or int(task_result.scalar() or 0) > 0:
                adopted += 1
        return round(adopted / max(min(len(insights), 10), 1), 4)


class MetricBaselineService:
    SNAPSHOT_KEY = "ai:metric-baseline:snapshots"
    BASELINE_KEY = "ai:metric-baseline:computed"
    TTL_SECONDS = int(timedelta(days=30).total_seconds())

    def __init__(self, redis=None):
        self.redis = redis
        self.calibration = StrategyCalibrationService(redis=redis)

    async def capture_snapshot(self) -> dict[str, Any]:
        if not self.redis:
            return {}
        sent_total = sum(snapshot_metric(PERCEPTIBLE_INSIGHT_SENT_TOTAL).values())
        skipped_total = sum(snapshot_metric(PERCEPTIBLE_INSIGHT_SKIPPED_TOTAL).values())
        snapshot = {
            "captured_at": _utcnow().isoformat(),
            "adaptive_rollback_total": sum(snapshot_metric(ADAPTIVE_ROLLBACK_TOTAL).values()),
            "perceptible_insight_skipped_ratio": round(skipped_total / max(sent_total + skipped_total, 1.0), 4),
            "alignment_score": await self.calibration.global_latest(self.calibration._alignment_global_key()),
            "profile_hit_rate": await self.calibration.global_latest(self.calibration._profile_hit_rate_global_key()),
        }
        history = await _redis_json_get(self.redis, self.SNAPSHOT_KEY, [])
        if not isinstance(history, list):
            history = []
        history.append(snapshot)
        history = history[-30:]
        await _redis_json_set(self.redis, self.SNAPSHOT_KEY, history, ttl_seconds=self.TTL_SECONDS)
        baseline = self._compute_baseline(history[-14:])
        await _redis_json_set(self.redis, self.BASELINE_KEY, baseline, ttl_seconds=self.TTL_SECONDS)
        return {"snapshot": snapshot, "baseline": baseline}

    async def get_status_payload(self) -> tuple[dict[str, Any], dict[str, Any]]:
        baseline = await _redis_json_get(self.redis, self.BASELINE_KEY, {})
        history = await _redis_json_get(self.redis, self.SNAPSHOT_KEY, [])
        if not baseline or not history:
            return {}, {}
        latest = history[-1] if isinstance(history, list) and history else {}
        anomalies: dict[str, Any] = {}
        for metric_name, stats in (baseline.get("metrics") or {}).items():
            if metric_name not in latest or latest.get(metric_name) is None:
                continue
            value = float(latest.get(metric_name) or 0.0)
            mean_value = float(stats.get("mean") or 0.0)
            std_value = float(stats.get("std") or 0.0)
            if std_value > 0 and abs(value - mean_value) > std_value * 2:
                anomalies[metric_name] = {
                    "value": round(value, 4),
                    "mean": round(mean_value, 4),
                    "std": round(std_value, 4),
                }
        return baseline, anomalies

    def _compute_baseline(self, history: list[dict[str, Any]]) -> dict[str, Any]:
        metrics: dict[str, dict[str, float]] = {}
        fields = (
            "adaptive_rollback_total",
            "perceptible_insight_skipped_ratio",
            "alignment_score",
            "profile_hit_rate",
        )
        for field in fields:
            values = [float(item.get(field)) for item in history if item.get(field) is not None]
            if not values:
                continue
            ordered = sorted(values)
            avg, std = _mean_std(values)
            metrics[field] = {
                "p50": round(ordered[len(ordered) // 2], 4),
                "p95": round(ordered[min(len(ordered) - 1, math.ceil(len(ordered) * 0.95) - 1)], 4),
                "mean": round(avg, 4),
                "std": round(std, 4),
            }
        return {
            "computed_at": _utcnow().isoformat(),
            "points": len(history),
            "metrics": metrics,
        }


class CohortPromotionService:
    HISTORY_KEY = "ai:perceptible:promotion-history"
    BASELINE_KEY = "ai:perceptible:baseline_strategy"
    TTL_SECONDS = int(timedelta(days=120).total_seconds())

    def __init__(self, redis=None):
        self.redis = redis

    async def evaluate_and_promote(self) -> dict[str, Any]:
        if self._is_off_week():
            return {
                "status": "skipped",
                "reason": "off_week",
                "evaluated_at": _utcnow().isoformat(),
            }
        result = await self._run_evaluator()
        if not self.redis:
            return result
        history = await _redis_json_get(self.redis, self.HISTORY_KEY, [])
        if not isinstance(history, list):
            history = []
        history.append(result)
        history = history[-10:]
        await _redis_json_set(self.redis, self.HISTORY_KEY, history, ttl_seconds=self.TTL_SECONDS)

        recommendation = (result.get("recommendation") or {})
        if recommendation.get("promotion_ready"):
            last_ready = [
                item for item in history[:-1]
                if isinstance(item, dict)
                and isinstance(item.get("recommendation"), dict)
                and item["recommendation"].get("promotion_ready")
            ]
            if last_ready:
                previous = last_ready[-1]["recommendation"]
                if (
                    previous.get("recommended_default") == recommendation.get("recommended_default")
                    and float(previous.get("margin") or 0.0) >= 0.05
                    and float(recommendation.get("margin") or 0.0) >= 0.05
                ):
                    await _redis_json_set(
                        self.redis,
                        self.BASELINE_KEY,
                        {
                            "baseline_strategy": recommendation.get("recommended_default"),
                            "promoted_at": _utcnow().isoformat(),
                            "source": "automatic_promotion",
                        },
                        ttl_seconds=self.TTL_SECONDS,
                    )
        return result

    @staticmethod
    def _is_off_week(now: datetime | None = None) -> bool:
        iso_week = (now or _utcnow()).isocalendar().week
        return iso_week % 2 == 1

    async def get_admin_payload(self) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        baseline = await _redis_json_get(self.redis, self.BASELINE_KEY, None)
        history = await _redis_json_get(self.redis, self.HISTORY_KEY, [])
        return baseline, history if isinstance(history, list) else []

    async def _run_evaluator(self) -> dict[str, Any]:
        script_path = Path(__file__).resolve().parents[3] / "scripts" / "evaluate_perceptible_cohorts.py"
        spec = importlib.util.spec_from_file_location("evaluate_perceptible_cohorts", script_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("Unable to load cohort evaluation script")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        evaluate = getattr(module, "evaluate", None)
        if evaluate is None:
            raise RuntimeError("Cohort evaluation script does not export evaluate")
        if asyncio.iscoroutinefunction(evaluate):
            return await evaluate(7)
        return evaluate(7)
