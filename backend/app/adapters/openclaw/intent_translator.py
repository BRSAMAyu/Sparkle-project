"""Translate Sparkle execution intents to OpenClaw request payloads."""

from __future__ import annotations

from typing import Any

from app.models.execution_intent import ExecutionIntent


class IntentTranslator:
    """Translate ExecutionIntent to OpenClaw `/v1/responses` requests."""

    def build_session_key(self, intent: ExecutionIntent, *, agent_id: str = "") -> str:
        agent_suffix = agent_id or "main"
        return f"sparkle:{agent_suffix}:{intent.user_id}:{intent.task_id}"

    def translate(
        self,
        intent: ExecutionIntent,
        *,
        agent_id: str = "",
        model_override: str | None = None,
    ) -> dict[str, Any]:
        model = model_override
        if not model:
            model = f"openclaw/{agent_id}" if agent_id else "openclaw"

        return {
            "model": model,
            "input": self._build_user_message(intent),
            "instructions": self._build_system_instructions(intent),
            "stream": False,
            "user": self.build_session_key(intent, agent_id=agent_id),
        }

    def translate_gateway_request(
        self,
        intent: ExecutionIntent,
        *,
        agent_id: str = "",
    ) -> dict[str, Any]:
        return {
            "agentId": agent_id or "main",
            "sessionKey": self.build_session_key(intent, agent_id=agent_id),
            "message": "\n\n".join(
                part
                for part in (
                    self._build_user_message(intent),
                    self._build_system_instructions(intent),
                )
                if part
            ),
            "idempotencyKey": intent.idempotency_key,
        }

    def _build_user_message(self, intent: ExecutionIntent) -> str:
        parts = [f"## Task Goal\n{intent.goal}"]

        if intent.instructions:
            constraint_lines = "\n".join(f"- {item}" for item in intent.instructions)
            parts.append(f"\n## Constraints\n{constraint_lines}")

        if intent.success_criteria:
            criteria_type = intent.success_criteria.get("type", "")
            required_fields = intent.success_criteria.get("required_fields", [])
            if required_fields:
                parts.append(
                    "\n## Expected Output\n" f"Type: {criteria_type}\n" f"Required fields: {', '.join(required_fields)}"
                )

        if intent.result_contract:
            artifact_types = intent.result_contract.get("artifact_types", [])
            if artifact_types:
                parts.append(f"\n## Output Format\nProvide results as: {', '.join(artifact_types)}")

        return "\n".join(parts)

    def _build_system_instructions(self, intent: ExecutionIntent) -> str:
        policy = intent.policy or {}
        lines = [
            "You are executing a delegated task from Sparkle AI Learning Assistant.",
            f"Task environment: {intent.target_env.value if intent.target_env else 'general'}",
            f"Time limit: {intent.timeout_seconds} seconds",
        ]

        allowed_domains = policy.get("allowed_domains", [])
        if allowed_domains:
            lines.append(f"ONLY access these domains: {', '.join(allowed_domains)}")

        allowed_tools = policy.get("allowed_tools", [])
        if allowed_tools:
            lines.append(f"ONLY use these tools: {', '.join(allowed_tools)}")

        if not policy.get("allow_exec", False):
            lines.append("DO NOT execute shell commands or scripts.")

        lines.extend(
            [
                "DO NOT send messages, emails, or make purchases.",
                "DO NOT modify account settings or passwords.",
                "If you encounter a login prompt or CAPTCHA, STOP and report it.",
                "Return results in a structured format.",
            ]
        )
        return "\n".join(lines)
