"""User-scoped execution preference management for OpenClaw flows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone, datetime, timedelta
from typing import Any
from uuid import UUID

from app.services.execution_learning_service import ExecutionLearningService
from app.services.personalization.preference_service import PreferenceService

EXECUTION_PREFERENCES_KEY = "openclaw.execution.preferences"
_ALLOWED_MODES = {"cautious", "balanced", "autonomous", "custom"}
_ALLOWED_NOTIFICATION_LEVELS = {"all", "essential", "silent"}
_ALLOWED_RULES = {"auto", "confirm", "skip", "reject"}
_ALLOWED_NODE_AFFINITY_KEYS = {"browser", "shell", "api", "document", "general"}
_DEFAULT_CUSTOM_RULES = {
    "browser_read": "auto",
    "browser_write": "confirm",
    "file_read": "auto",
    "file_write": "confirm",
    "file_delete": "confirm",
    "shell_exec": "confirm",
    "shell_read": "auto",
    "install": "reject",
    "send": "confirm",
}
_DEFAULT_PREFERENCES = {
    "mode": "balanced",
    "custom_rules": _DEFAULT_CUSTOM_RULES,
    "node_affinity": {},
    "notification_level": "essential",
    "auto_extend_timeout": True,
    "trust_auto_upgrade": True,
    "execution_budget": {
        "daily_token_limit": None,
        "monthly_token_limit": None,
        "daily_used": 0,
        "monthly_used": 0,
    },
}
_DELEGATION_SUGGESTION_STATE_KEY = "openclaw.execution.delegation_suggestions"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass(frozen=True)
class ExecutionPreferenceRecommendation:
    recommended_mode: str
    reason: str
    target_env: str | None = None
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "recommended_mode": self.recommended_mode,
            "reason": self.reason,
            "target_env": self.target_env,
            "confidence": round(float(self.confidence or 0.0), 2),
        }


class ExecutionPreferenceService:
    """Read and persist execution preference payloads."""

    def __init__(self, db, redis=None):
        self._preference_service = PreferenceService(db, redis)
        self._learning_service = ExecutionLearningService(db=db, redis=redis)

    async def get_preferences(
        self,
        *,
        user_id: UUID,
        include_recommendations: bool = True,
    ) -> dict[str, Any]:
        prefs = await self._preference_service.get_preferences(user_id)
        explicit = dict(prefs.explicit or {})
        payload = explicit.get(EXECUTION_PREFERENCES_KEY)
        normalized = self._normalize_payload(payload if isinstance(payload, dict) else None)
        normalized["summary"] = self._build_summary(normalized)
        normalized["recommendations"] = (
            [item.to_dict() for item in await self._build_recommendations(user_id=user_id, current=normalized)]
            if include_recommendations
            else []
        )
        return normalized

    async def save_preferences(self, *, user_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_payload(payload)
        await self._persist_preferences(user_id=user_id, payload=normalized)
        normalized["summary"] = self._build_summary(normalized)
        normalized["recommendations"] = [
            item.to_dict()
            for item in await self._build_recommendations(user_id=user_id, current=normalized)
        ]
        return normalized

    async def check_budget_allowance(self, *, user_id: UUID) -> dict[str, Any]:
        prefs = await self.get_preferences(user_id=user_id, include_recommendations=False)
        budget = dict(prefs.get("execution_budget") or {})
        daily_limit = self._coerce_optional_int(budget.get("daily_token_limit"))
        monthly_limit = self._coerce_optional_int(budget.get("monthly_token_limit"))
        daily_used = max(0, int(budget.get("daily_used") or 0))
        monthly_used = max(0, int(budget.get("monthly_used") or 0))
        if daily_limit is not None and daily_used >= daily_limit:
            return {
                "allowed": False,
                "code": "daily_token_limit_exceeded",
                "message": f"今日执行预算已用完（{daily_used}/{daily_limit} tokens）。你可以明天继续，或去设置里调高预算上限。",
                "budget": budget,
            }
        if monthly_limit is not None and monthly_used >= monthly_limit:
            return {
                "allowed": False,
                "code": "monthly_token_limit_exceeded",
                "message": f"本月执行预算已达到上限（{monthly_used}/{monthly_limit} tokens）。你可以下月继续，或去设置里调高预算上限。",
                "budget": budget,
            }
        return {
            "allowed": True,
            "code": "ok",
            "message": "",
            "budget": budget,
        }

    async def record_token_usage(self, *, user_id: UUID, token_usage: Any) -> dict[str, Any]:
        prefs = await self.get_preferences(user_id=user_id, include_recommendations=False)
        normalized = self._normalize_payload(prefs)
        budget = dict(normalized.get("execution_budget") or {})
        total_tokens = self._extract_total_tokens(token_usage)
        budget["daily_used"] = max(0, int(budget.get("daily_used") or 0)) + total_tokens
        budget["monthly_used"] = max(0, int(budget.get("monthly_used") or 0)) + total_tokens
        normalized["execution_budget"] = self._normalize_budget_payload(budget)
        await self._persist_preferences(user_id=user_id, payload=normalized)
        normalized["summary"] = self._build_summary(normalized)
        normalized["recommendations"] = []
        return normalized

    async def _persist_preferences(self, *, user_id: UUID, payload: dict[str, Any]) -> None:
        await self._preference_service.update_explicit(
            user_id,
            {EXECUTION_PREFERENCES_KEY: payload},
        )

    async def get_delegation_suggestion_state(self, *, user_id: UUID) -> dict[str, Any]:
        prefs = await self._preference_service.get_preferences(user_id)
        explicit = dict(prefs.explicit or {})
        payload = explicit.get(_DELEGATION_SUGGESTION_STATE_KEY)
        return self._normalize_delegation_state(payload if isinstance(payload, dict) else None)

    async def record_delegation_suggestion_shown(
        self,
        *,
        user_id: UUID,
        session_id: str,
    ) -> dict[str, Any]:
        state = await self.get_delegation_suggestion_state(user_id=user_id)
        session_key = str(session_id or "").strip() or "global"
        session_counts = dict(state.get("session_counts") or {})
        session_counts[session_key] = int(session_counts.get(session_key, 0) or 0) + 1

        shown_timestamps = list(state.get("shown_timestamps") or [])
        shown_timestamps.append(_utcnow().isoformat())
        next_state = self._normalize_delegation_state(
            {
                **state,
                "session_counts": session_counts,
                "shown_timestamps": shown_timestamps,
            }
        )
        cooldown = self._compute_cooldown(next_state)
        if cooldown is not None:
            next_state["cooldown_until"] = cooldown.isoformat()
        await self._preference_service.update_explicit(
            user_id,
            {_DELEGATION_SUGGESTION_STATE_KEY: next_state},
        )
        return next_state

    async def record_delegation_suggestion_accepted(self, *, user_id: UUID) -> dict[str, Any]:
        state = await self.get_delegation_suggestion_state(user_id=user_id)
        accepted_timestamps = list(state.get("accepted_timestamps") or [])
        accepted_timestamps.append(_utcnow().isoformat())
        next_state = self._normalize_delegation_state(
            {
                **state,
                "accepted_timestamps": accepted_timestamps,
                "cooldown_until": None,
            }
        )
        await self._preference_service.update_explicit(
            user_id,
            {_DELEGATION_SUGGESTION_STATE_KEY: next_state},
        )
        return next_state

    async def should_suppress_delegation_suggestion(
        self,
        *,
        user_id: UUID,
        session_id: str,
    ) -> bool:
        state = await self.get_delegation_suggestion_state(user_id=user_id)
        now = _utcnow()
        cooldown_until = self._parse_datetime(state.get("cooldown_until"))
        if cooldown_until is not None and cooldown_until > now:
            return True
        session_counts = dict(state.get("session_counts") or {})
        session_key = str(session_id or "").strip() or "global"
        return int(session_counts.get(session_key, 0) or 0) >= 3

    def _normalize_payload(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        payload = payload or {}
        mode = str(payload.get("mode") or _DEFAULT_PREFERENCES["mode"]).strip().lower()
        if mode not in _ALLOWED_MODES:
            mode = _DEFAULT_PREFERENCES["mode"]

        custom_rules = dict(_DEFAULT_CUSTOM_RULES)
        raw_rules = payload.get("custom_rules")
        if isinstance(raw_rules, dict):
            for key, value in raw_rules.items():
                rule = str(value or "").strip().lower()
                if key in custom_rules and rule in _ALLOWED_RULES:
                    custom_rules[key] = rule

        notification_level = str(
            payload.get("notification_level") or _DEFAULT_PREFERENCES["notification_level"]
        ).strip().lower()
        if notification_level not in _ALLOWED_NOTIFICATION_LEVELS:
            notification_level = _DEFAULT_PREFERENCES["notification_level"]

        node_affinity: dict[str, str] = {}
        raw_affinity = payload.get("node_affinity")
        if isinstance(raw_affinity, dict):
            for key, value in raw_affinity.items():
                normalized_key = str(key or "").strip().lower()
                normalized_value = str(value or "").strip()
                if normalized_key in _ALLOWED_NODE_AFFINITY_KEYS and normalized_value:
                    node_affinity[normalized_key] = normalized_value

        return {
            "mode": mode,
            "custom_rules": custom_rules,
            "node_affinity": node_affinity,
            "notification_level": notification_level,
            "auto_extend_timeout": bool(
                payload.get("auto_extend_timeout", _DEFAULT_PREFERENCES["auto_extend_timeout"])
            ),
            "trust_auto_upgrade": bool(
                payload.get("trust_auto_upgrade", _DEFAULT_PREFERENCES["trust_auto_upgrade"])
            ),
            "execution_budget": self._normalize_budget_payload(payload.get("execution_budget")),
        }

    def _normalize_budget_payload(self, payload: Any) -> dict[str, Any]:
        payload = payload if isinstance(payload, dict) else {}
        today = _utcnow().date().isoformat()
        month_bucket = _utcnow().strftime("%Y-%m")
        reset_date = str(payload.get("reset_date") or today).strip() or today
        current_month = str(payload.get("month_bucket") or month_bucket).strip() or month_bucket
        daily_used = max(0, int(payload.get("daily_used") or 0))
        monthly_used = max(0, int(payload.get("monthly_used") or 0))
        if reset_date != today:
            daily_used = 0
            reset_date = today
        if current_month != month_bucket:
            monthly_used = 0
            current_month = month_bucket
        return {
            "daily_token_limit": self._coerce_optional_int(payload.get("daily_token_limit")),
            "monthly_token_limit": self._coerce_optional_int(payload.get("monthly_token_limit")),
            "daily_used": daily_used,
            "monthly_used": monthly_used,
            "reset_date": reset_date,
            "month_bucket": current_month,
        }

    def _normalize_delegation_state(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        payload = payload or {}
        session_counts = {
            str(key): int(value)
            for key, value in dict(payload.get("session_counts") or {}).items()
            if str(key).strip()
        }
        shown_timestamps = self._normalize_timestamp_list(payload.get("shown_timestamps"))
        accepted_timestamps = self._normalize_timestamp_list(payload.get("accepted_timestamps"))
        cooldown_until = self._parse_datetime(payload.get("cooldown_until"))
        now = _utcnow()
        if cooldown_until is not None and cooldown_until <= now:
            cooldown_until = None
        return {
            "session_counts": session_counts,
            "shown_timestamps": shown_timestamps,
            "accepted_timestamps": accepted_timestamps,
            "cooldown_until": cooldown_until.isoformat() if cooldown_until else None,
        }

    @staticmethod
    def _normalize_timestamp_list(raw: Any) -> list[str]:
        values: list[str] = []
        if not isinstance(raw, list):
            return values
        cutoff = _utcnow() - timedelta(days=7)
        for item in raw:
            parsed = ExecutionPreferenceService._parse_datetime(item)
            if parsed is None or parsed < cutoff:
                continue
            values.append(parsed.isoformat())
        return values[-10:]

    @staticmethod
    def _parse_datetime(raw: Any) -> datetime | None:
        text = str(raw or "").strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed

    def _compute_cooldown(self, state: dict[str, Any]) -> datetime | None:
        shown = len(list(state.get("shown_timestamps") or []))
        accepted = len(list(state.get("accepted_timestamps") or []))
        if shown - accepted < 3:
            return None
        return _utcnow() + timedelta(days=7)

    @staticmethod
    def _coerce_optional_int(value: Any) -> int | None:
        if value in {None, "", 0, "0"}:
            return None
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None

    @staticmethod
    def _extract_total_tokens(token_usage: Any) -> int:
        if not isinstance(token_usage, dict):
            return 0
        for key in (
            "total_tokens",
            "totalTokens",
            "total",
        ):
            value = token_usage.get(key)
            if isinstance(value, (int, float)) and value > 0:
                return int(value)
        subtotal = 0
        for key in (
            "input_tokens",
            "output_tokens",
            "prompt_tokens",
            "completion_tokens",
            "cached_tokens",
        ):
            value = token_usage.get(key)
            if isinstance(value, (int, float)) and value > 0:
                subtotal += int(value)
        return subtotal

    async def _build_recommendations(
        self,
        *,
        user_id: UUID,
        current: dict[str, Any],
    ) -> list[ExecutionPreferenceRecommendation]:
        stats = await self._learning_service.get_category_trust_stats(user_id=user_id)
        recommendations: list[ExecutionPreferenceRecommendation] = []

        browser = stats.get("browser")
        if (
            browser
            and browser["total"] >= 8
            and browser["success_rate"] >= 0.9
            and current["mode"] in {"cautious", "balanced"}
        ):
            recommendations.append(
                ExecutionPreferenceRecommendation(
                    recommended_mode="autonomous" if current["mode"] == "balanced" else "balanced",
                    target_env="browser",
                    confidence=min(0.95, browser["success_rate"]),
                    reason="你在浏览器类委派上已经连续表现稳定，可以减少重复确认。",
                )
            )

        shell = stats.get("shell")
        if shell and shell["total"] >= 3 and shell["success_rate"] < 0.6 and current["mode"] == "autonomous":
            recommendations.append(
                ExecutionPreferenceRecommendation(
                    recommended_mode="balanced",
                    target_env="shell",
                    confidence=0.78,
                    reason="终端类任务近期失败率偏高，建议暂时回到平衡模式。",
                )
            )

        return recommendations[:3]

    @staticmethod
    def _build_summary(payload: dict[str, Any]) -> str:
        mode = payload.get("mode")
        affinity_count = len(payload.get("node_affinity") or {})
        affinity_note = f" 已为 {affinity_count} 类任务指定设备亲和性。" if affinity_count > 0 else ""
        budget = dict(payload.get("execution_budget") or {})
        budget_note_parts = []
        if budget.get("daily_token_limit") is not None:
            budget_note_parts.append(
                f"今日预算 {budget.get('daily_used', 0)}/{budget.get('daily_token_limit')} tokens"
            )
        if budget.get("monthly_token_limit") is not None:
            budget_note_parts.append(
                f"本月预算 {budget.get('monthly_used', 0)}/{budget.get('monthly_token_limit')} tokens"
            )
        budget_note = f" {'，'.join(budget_note_parts)}。" if budget_note_parts else ""
        if mode == "cautious":
            return f"当前模式：谨慎。所有执行尽量先确认，再写回结果。{affinity_note}{budget_note}".strip()
        if mode == "autonomous":
            return f"当前模式：信任。低到中风险动作会尽量自动完成。{affinity_note}{budget_note}".strip()
        if mode == "custom":
            return f"当前模式：自定义。不同动作按你设定的规则执行。{affinity_note}{budget_note}".strip()
        return f"当前模式：平衡。读取类动作自动执行，写入和高风险动作保持确认。{affinity_note}{budget_note}".strip()
