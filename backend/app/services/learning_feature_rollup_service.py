from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger

from app.config import settings
from app.core.cache import cache_service
from app.services.learning_cohort_service import LearningCohortService
from app.services.learning_event_service import LearningEventService

_MEM_ROLLUPS: dict[str, dict[str, Any]] = {}


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _rollup_key(date_key: str, bucket: str) -> str:
    return f"learning:feature_rollup:{date_key}:{bucket}"


class LearningFeatureRollupService:
    """Aggregate learning events into long-lived, text-free feature buckets."""

    def __init__(self, redis_client=None):
        self.redis = redis_client or cache_service.redis
        self.events = LearningEventService(redis_client=self.redis)

    async def run_rollup_job(self, *, window_minutes: int = 30) -> dict[str, Any]:
        if not getattr(settings, "ENABLE_LEARNING_CONTROL_PLANE", False):
            return {"status": "disabled", "reason": "flag_off"}

        window = max(5, int(window_minutes))
        since = _utcnow() - timedelta(minutes=window)
        events = await self.events.list_events_since(since=since, limit=20000)
        aggregated = self._aggregate(events)
        await self._persist_aggregates(aggregated)
        return {
            "status": "ok",
            "window_minutes": window,
            "events": len(events),
            "buckets": len(aggregated),
        }

    async def list_rollups(self, *, days: int = 14) -> list[dict[str, Any]]:
        if self.redis is None:
            cutoff = (_utcnow() - timedelta(days=max(1, days))).date()
            output = []
            for payload in _MEM_ROLLUPS.values():
                date_key = payload.get("date", "")
                try:
                    event_date = datetime.fromisoformat(f"{date_key}T00:00:00").date()
                except ValueError:
                    continue
                if event_date >= cutoff:
                    output.append(payload)
            return output

        cutoff = (_utcnow() - timedelta(days=max(1, days))).date()
        output: list[dict[str, Any]] = []
        try:
            async for key in self.redis.scan_iter("learning:feature_rollup:*"):
                raw = await self.redis.get(key)
                if not raw:
                    continue
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                date_key = str(payload.get("date", ""))
                try:
                    event_date = datetime.fromisoformat(f"{date_key}T00:00:00").date()
                except ValueError:
                    continue
                if event_date < cutoff:
                    continue
                output.append(payload)
        except Exception as exc:
            logger.warning("Failed loading feature rollups: {}", exc)
        return output

    @staticmethod
    def _aggregate(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        buckets: dict[str, dict[str, Any]] = {}
        for event in events:
            data = event.get("data") if isinstance(event.get("data"), dict) else {}
            sample_validity = str(event.get("sample_validity") or data.get("sample_validity") or "valid")
            if sample_validity != "valid":
                continue
            policy_id = str(event.get("policy_id") or data.get("policy_id") or "unknown")
            strategy_pack = str(event.get("strategy_pack") or data.get("strategy_pack") or "default")
            complexity_tier = str(event.get("complexity_tier") or data.get("complexity_tier") or "unknown")
            task_type = str(event.get("task_type") or data.get("task_type") or "unknown")
            cohort_id = str(event.get("cohort_id") or data.get("cohort_id") or "")
            user_scope = str(event.get("user_scope") or data.get("user_scope") or "")
            if not user_scope:
                user_scope = LearningCohortService.user_scope_key(str(event.get("user_id", "")))
            timestamp = str(event.get("timestamp") or _utcnow().isoformat())
            date_key = timestamp.split("T", 1)[0]
            bucket_id = "|".join((policy_id, strategy_pack, cohort_id, user_scope, complexity_tier, task_type))
            key = f"{date_key}|{bucket_id}"

            if key not in buckets:
                buckets[key] = {
                    "date": date_key,
                    "bucket_id": bucket_id,
                    "policy_id": policy_id,
                    "strategy_pack": strategy_pack,
                    "cohort_id": cohort_id,
                    "user_scope": user_scope,
                    "complexity_tier": complexity_tier,
                    "task_type": task_type,
                    "counts": defaultdict(int),
                    "latency_ms_sum": 0.0,
                    "latency_ms_count": 0,
                }

            record = buckets[key]
            counts = record["counts"]
            event_type = str(event.get("event_type", ""))
            if event_type == "expert_selected":
                counts["expert_selected"] += 1
            elif event_type == "expert_invoked":
                counts["expert_invoked"] += 1
            elif event_type == "expert_fallback":
                counts["expert_fallback"] += 1
                reason = str(data.get("reason", "")).strip()
                if reason:
                    counts[f"failure_pattern::fallback::{reason}"] += 1
            elif event_type == "prompt_selected":
                counts["prompt_selected"] += 1
                prompt_version = str(data.get("prompt_version", "")).strip()
                if prompt_version:
                    counts[f"prompt_selected::{prompt_version}"] += 1
            elif event_type == "prompt_applied":
                counts["prompt_applied"] += 1
                prompt_version = str(data.get("prompt_version", "")).strip()
                if prompt_version:
                    counts[f"prompt_applied::{prompt_version}"] += 1
            elif event_type == "toolchain_selected":
                counts["toolchain_selected"] += 1
                toolchain_id = str(data.get("toolchain_id", "")).strip()
                if toolchain_id:
                    counts[f"toolchain_selected::{toolchain_id}"] += 1
            elif event_type == "toolchain_degraded":
                counts["toolchain_degraded"] += 1
                reason = str(data.get("reason", "")).strip()
                if reason:
                    counts[f"toolchain_degraded::{reason}"] += 1
                    counts[f"failure_pattern::toolchain::{reason}"] += 1
            elif event_type == "cold_start_bootstrap_applied":
                counts["cold_start_bootstrap_applied"] += 1
            elif event_type == "quality_gate_blocked":
                counts["quality_gate_blocked"] += 1
                reason = str(data.get("quality_gate_block_reason", "")).strip()
                if reason:
                    counts[f"failure_pattern::quality_gate::{reason}"] += 1
            elif event_type == "response_feedback":
                feedback_type = str(data.get("feedback_type", ""))
                if feedback_type == "up":
                    counts["feedback_up"] += 1
                elif feedback_type == "down":
                    counts["feedback_down"] += 1
            elif event_type == "plan_execution_outcome":
                counts["plan_execution_total"] += 1
                if bool(data.get("success", False)):
                    counts["plan_execution_success"] += 1
                else:
                    failed_types = data.get("failed_step_types")
                    if isinstance(failed_types, dict):
                        for failure_type, value in failed_types.items():
                            try:
                                fail_count = max(1, int(value))
                            except (TypeError, ValueError):
                                fail_count = 1
                            counts[f"failure_pattern::step::{str(failure_type)}"] += fail_count
            elif event_type == "plan_repair_triggered":
                counts["plan_repair_triggered"] += 1
                for action in data.get("repair_actions", []) if isinstance(data.get("repair_actions"), list) else []:
                    counts[f"plan_repair_action::{str(action)}"] += 1
            elif event_type == "plan_repair_succeeded":
                counts["plan_repair_succeeded"] += 1
            elif event_type == "checkpoint_due":
                counts["checkpoint_due"] += 1
            elif event_type == "checkpoint_done":
                counts["checkpoint_done"] += 1
            elif event_type == "checkpoint_skipped":
                counts["checkpoint_skipped"] += 1
            elif event_type == "route_decision":
                counts["route_decision"] += 1

            latency_ms = data.get("latency_ms")
            if isinstance(latency_ms, (int, float)) and latency_ms >= 0:
                record["latency_ms_sum"] += float(latency_ms)
                record["latency_ms_count"] += 1

        normalized: dict[str, dict[str, Any]] = {}
        for key, item in buckets.items():
            counts = dict(item["counts"])
            avg_latency_ms = (
                float(item["latency_ms_sum"]) / int(item["latency_ms_count"])
                if item["latency_ms_count"] > 0
                else 0.0
            )
            fallback_rate = _safe_rate(counts.get("expert_fallback", 0), counts.get("expert_selected", 0))
            feedback_up_rate = _safe_rate(
                counts.get("feedback_up", 0),
                counts.get("feedback_up", 0) + counts.get("feedback_down", 0),
            )
            quality_gate_pass_rate = _safe_rate(
                counts.get("plan_execution_success", 0),
                counts.get("plan_execution_total", 0) + counts.get("quality_gate_blocked", 0),
            )
            prompt_apply_rate = _safe_rate(
                counts.get("prompt_applied", 0),
                counts.get("prompt_selected", 0),
            )
            toolchain_degrade_rate = _safe_rate(
                counts.get("toolchain_degraded", 0),
                counts.get("toolchain_selected", 0),
            )
            repair_success_rate = _safe_rate(
                counts.get("plan_repair_succeeded", 0),
                counts.get("plan_repair_triggered", 0),
            )
            checkpoint_done_rate = _safe_rate(
                counts.get("checkpoint_done", 0),
                counts.get("checkpoint_done", 0) + counts.get("checkpoint_skipped", 0),
            )
            checkpoint_skip_rate = _safe_rate(
                counts.get("checkpoint_skipped", 0),
                counts.get("checkpoint_done", 0) + counts.get("checkpoint_skipped", 0),
            )
            failure_pattern_topn = _top_prefixed_counts(counts, prefix="failure_pattern::", limit=5)
            normalized_latency = min(max(avg_latency_ms / 4000.0, 0.0), 1.0)
            q_score = (
                0.4 * (1.0 - fallback_rate)
                + 0.3 * feedback_up_rate
                + 0.2 * quality_gate_pass_rate
                + 0.1 * (1.0 - normalized_latency)
            )
            normalized[key] = {
                "date": item["date"],
                "bucket_id": item["bucket_id"],
                "policy_id": item["policy_id"],
                "strategy_pack": item["strategy_pack"],
                "cohort_id": item["cohort_id"],
                "user_scope": item["user_scope"],
                "complexity_tier": item["complexity_tier"],
                "task_type": item["task_type"],
                "counts": counts,
                "avg_latency_ms": round(avg_latency_ms, 3),
                "fallback_rate": round(fallback_rate, 4),
                "feedback_up_rate": round(feedback_up_rate, 4),
                "quality_gate_pass_rate": round(quality_gate_pass_rate, 4),
                "prompt_apply_rate": round(prompt_apply_rate, 4),
                "toolchain_degrade_rate": round(toolchain_degrade_rate, 4),
                "repair_success_rate": round(repair_success_rate, 4),
                "checkpoint_done_rate": round(checkpoint_done_rate, 4),
                "checkpoint_skip_rate": round(checkpoint_skip_rate, 4),
                "failure_pattern_topn": failure_pattern_topn,
                "normalized_latency": round(normalized_latency, 4),
                "q_score": round(q_score, 4),
                "updated_at": _utcnow().isoformat(),
            }
        return normalized

    async def _persist_aggregates(self, aggregated: dict[str, dict[str, Any]]) -> None:
        if not aggregated:
            return

        ttl_days = int(getattr(settings, "LEARNING_FEATURE_TTL_DAYS", 180))
        ttl_seconds = max(3600, ttl_days * 24 * 3600)

        for key, payload in aggregated.items():
            date_key, bucket_id = key.split("|", 1)
            merged = payload
            redis_key = _rollup_key(date_key, bucket_id)
            if self.redis is None:
                existing = _MEM_ROLLUPS.get(redis_key)
                if existing:
                    merged = _merge_rollups(existing, payload)
                _MEM_ROLLUPS[redis_key] = merged
                continue

            try:
                raw_existing = await self.redis.get(redis_key)
                if raw_existing:
                    try:
                        existing = json.loads(raw_existing)
                        merged = _merge_rollups(existing, payload)
                    except json.JSONDecodeError:
                        merged = payload
                await self.redis.setex(redis_key, ttl_seconds, json.dumps(merged, ensure_ascii=False))
            except Exception as exc:
                logger.warning("Failed persisting learning rollup {}: {}", redis_key, exc)


def _merge_rollups(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged_counts: dict[str, int] = {}
    existing_counts = existing.get("counts") if isinstance(existing.get("counts"), dict) else {}
    incoming_counts = incoming.get("counts") if isinstance(incoming.get("counts"), dict) else {}
    for name in set(existing_counts) | set(incoming_counts):
        merged_counts[name] = int(existing_counts.get(name, 0)) + int(incoming_counts.get(name, 0))

    avg_latency_ms = _weighted_avg(
        existing_avg=float(existing.get("avg_latency_ms", 0.0)),
        existing_count=int(existing_counts.get("route_decision", 0)),
        incoming_avg=float(incoming.get("avg_latency_ms", 0.0)),
        incoming_count=int(incoming_counts.get("route_decision", 0)),
    )

    fallback_rate = _safe_rate(merged_counts.get("expert_fallback", 0), merged_counts.get("expert_selected", 0))
    feedback_up_rate = _safe_rate(
        merged_counts.get("feedback_up", 0),
        merged_counts.get("feedback_up", 0) + merged_counts.get("feedback_down", 0),
    )
    quality_gate_pass_rate = _safe_rate(
        merged_counts.get("plan_execution_success", 0),
        merged_counts.get("plan_execution_total", 0) + merged_counts.get("quality_gate_blocked", 0),
    )
    prompt_apply_rate = _safe_rate(
        merged_counts.get("prompt_applied", 0),
        merged_counts.get("prompt_selected", 0),
    )
    toolchain_degrade_rate = _safe_rate(
        merged_counts.get("toolchain_degraded", 0),
        merged_counts.get("toolchain_selected", 0),
    )
    repair_success_rate = _safe_rate(
        merged_counts.get("plan_repair_succeeded", 0),
        merged_counts.get("plan_repair_triggered", 0),
    )
    checkpoint_done_rate = _safe_rate(
        merged_counts.get("checkpoint_done", 0),
        merged_counts.get("checkpoint_done", 0) + merged_counts.get("checkpoint_skipped", 0),
    )
    checkpoint_skip_rate = _safe_rate(
        merged_counts.get("checkpoint_skipped", 0),
        merged_counts.get("checkpoint_done", 0) + merged_counts.get("checkpoint_skipped", 0),
    )
    failure_pattern_topn = _top_prefixed_counts(merged_counts, prefix="failure_pattern::", limit=5)
    normalized_latency = min(max(avg_latency_ms / 4000.0, 0.0), 1.0)
    q_score = (
        0.4 * (1.0 - fallback_rate)
        + 0.3 * feedback_up_rate
        + 0.2 * quality_gate_pass_rate
        + 0.1 * (1.0 - normalized_latency)
    )

    merged = dict(existing)
    merged.update(incoming)
    merged["counts"] = merged_counts
    merged["avg_latency_ms"] = round(avg_latency_ms, 3)
    merged["fallback_rate"] = round(fallback_rate, 4)
    merged["feedback_up_rate"] = round(feedback_up_rate, 4)
    merged["quality_gate_pass_rate"] = round(quality_gate_pass_rate, 4)
    merged["prompt_apply_rate"] = round(prompt_apply_rate, 4)
    merged["toolchain_degrade_rate"] = round(toolchain_degrade_rate, 4)
    merged["repair_success_rate"] = round(repair_success_rate, 4)
    merged["checkpoint_done_rate"] = round(checkpoint_done_rate, 4)
    merged["checkpoint_skip_rate"] = round(checkpoint_skip_rate, 4)
    merged["failure_pattern_topn"] = failure_pattern_topn
    merged["normalized_latency"] = round(normalized_latency, 4)
    merged["q_score"] = round(q_score, 4)
    merged["updated_at"] = _utcnow().isoformat()
    return merged


def _weighted_avg(*, existing_avg: float, existing_count: int, incoming_avg: float, incoming_count: int) -> float:
    total_count = max(0, existing_count) + max(0, incoming_count)
    if total_count <= 0:
        return 0.0
    return (
        existing_avg * max(0, existing_count) + incoming_avg * max(0, incoming_count)
    ) / total_count


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return max(0.0, min(float(numerator) / float(denominator), 1.0))


def _top_prefixed_counts(counts: dict[str, int], *, prefix: str, limit: int) -> list[dict[str, Any]]:
    pairs: list[tuple[str, int]] = []
    for key, value in counts.items():
        if not str(key).startswith(prefix):
            continue
        pairs.append((str(key)[len(prefix):], int(value)))
    pairs.sort(key=lambda item: item[1], reverse=True)
    out: list[dict[str, Any]] = []
    for name, value in pairs[: max(1, int(limit))]:
        out.append({"pattern": name, "count": int(value)})
    return out
