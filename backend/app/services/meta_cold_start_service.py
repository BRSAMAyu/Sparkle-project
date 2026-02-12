from __future__ import annotations

from typing import Any

from app.config import settings


class MetaColdStartService:
    """Cold-start bootstrap heuristics for cohort/global first-turn optimization."""

    @staticmethod
    def is_cold_start(
        *,
        user_context: dict[str, Any] | None,
        conversation_context: dict[str, Any] | None,
    ) -> bool:
        if not bool(getattr(settings, "ENABLE_COLD_START_BOOTSTRAP", True)):
            return False

        ctx = user_context if isinstance(user_context, dict) else {}
        conv = conversation_context if isinstance(conversation_context, dict) else {}

        messages = conv.get("messages") if isinstance(conv.get("messages"), list) else []
        summary = str(conv.get("summary", "") or "").strip()
        if len(messages) > 2 or summary:
            return False

        analytics = ctx.get("analytics_summary") if isinstance(ctx.get("analytics_summary"), dict) else {}
        profile = ctx.get("profile") if isinstance(ctx.get("profile"), dict) else {}
        prefs = ctx.get("preferences") if isinstance(ctx.get("preferences"), dict) else {}
        inferred = ctx.get("inferred") if isinstance(ctx.get("inferred"), dict) else {}

        flame_level = analytics.get("flame_level", profile.get("flame_level"))
        try:
            flame_level_val = int(flame_level) if flame_level is not None else 0
        except (TypeError, ValueError):
            flame_level_val = 0

        has_affinity = False
        expert_affinity = inferred.get("expert_affinity")
        if isinstance(expert_affinity, dict):
            has_affinity = len(expert_affinity) > 0

        has_strong_pref = any(
            key in prefs for key in ("preferred_experts", "expert_preference", "depth_preference", "curiosity_preference")
        )

        return flame_level_val <= 1 and not has_affinity and not has_strong_pref

    @staticmethod
    def build_bootstrap_overrides(*, chat_mode: str) -> dict[str, Any]:
        _ = chat_mode
        return {
            "routing_pack_overrides": {
                "thresholds": {
                    # Cold-start phase prefers stable single/dual expert routing over aggressive fan-out.
                    "min_selected_score": float(getattr(settings, "COLD_START_MIN_SELECTED_SCORE_FLOOR", 0.36)),
                },
            },
            "toolchain_params": {
                "max_parallel_experts": int(getattr(settings, "COLD_START_MAX_PARALLEL_EXPERTS", 2)),
                "retry_limit": 1,
                "timeout_multiplier": 1.0,
            },
            "scope": "cohort_global_bootstrap",
        }

    @staticmethod
    async def mark_session_bootstrap_once(
        *,
        redis_client: Any,
        user_id: str,
        session_id: str,
    ) -> bool:
        if redis_client is None:
            return False
        marker_key = f"learning:cold_start:session_seen:{user_id}:{session_id}"
        ttl_hours = max(1, int(getattr(settings, "COLD_START_SESSION_TTL_HOURS", 24)))
        ttl_seconds = ttl_hours * 3600
        try:
            created = await redis_client.set(marker_key, "1", nx=True, ex=ttl_seconds)
            return bool(created)
        except Exception:
            return False
