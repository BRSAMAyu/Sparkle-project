from __future__ import annotations

from typing import Any


class IntentRouter:
    def get_intent(self, payload: dict[str, Any]) -> str:
        if not payload:
            return "chat"
        explicit = payload.get("intent")
        if explicit:
            return str(explicit)
        extra_context = payload.get("extra_context") or payload.get("context") or {}
        if isinstance(extra_context, dict) and extra_context.get("intent"):
            return str(extra_context["intent"])
        return "chat"
