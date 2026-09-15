"""Translate Sparkle execution intents to OpenClaw request payloads."""

from __future__ import annotations

from typing import Any

from app.models.execution_intent import ExecutionIntent
from app.services.execution_risk_assessor import ExecutionRiskAssessor

_TOOL_STAGE_DESCRIPTIONS = {
    "browser_navigate": "openclaw.stage.navigating",
    "browser_click": "openclaw.stage.clicking",
    "browser_screenshot": "openclaw.stage.screenshotting",
    "browser_extract": "openclaw.stage.extracting",
    "browser_read": "openclaw.stage.reading_page",
    "browser_write": "openclaw.stage.writing",
    "shell_exec": "openclaw.stage.executing_command",
    "system.run": "openclaw.stage.executing_command",
    "file_read": "openclaw.stage.reading_file",
    "file_write": "openclaw.stage.saving_file",
    "file_delete": "openclaw.stage.deleting_file",
    "web_search": "openclaw.stage.searching",
    "web_fetch": "openclaw.stage.fetching",
    "code_execute": "openclaw.stage.running_code",
}

# Chinese fallback for backward compatibility when i18n keys are not resolved
_TOOL_STAGE_DESCRIPTIONS_ZH = {
    "browser_navigate": "正在访问目标网页",
    "browser_click": "正在点击页面元素",
    "browser_screenshot": "正在截取页面截图",
    "browser_extract": "正在提取页面内容",
    "browser_read": "正在读取页面内容",
    "browser_write": "正在填写页面内容",
    "shell_exec": "正在执行终端命令",
    "system.run": "正在执行终端命令",
    "file_read": "正在读取文件",
    "file_write": "正在保存文件",
    "file_delete": "正在删除文件",
    "web_search": "正在搜索信息",
    "web_fetch": "正在获取网页内容",
    "code_execute": "正在运行代码",
}


def summarize_tool_input(raw_input: Any, *, limit: int = 60) -> str:
    """Build a compact human-readable summary for tool inputs."""
    if isinstance(raw_input, str):
        normalized = " ".join(raw_input.split()).strip()
        return normalized[:limit].rstrip() + ("…" if len(normalized) > limit else "")
    if isinstance(raw_input, dict):
        for key in ("url", "path", "file", "cwd", "command", "query", "selector", "text"):
            value = raw_input.get(key)
            if isinstance(value, str) and value.strip():
                return summarize_tool_input(value, limit=limit)
        compact = " ".join(f"{key}={value}" for key, value in raw_input.items() if isinstance(value, (str, int, float, bool)))
        if compact:
            return summarize_tool_input(compact, limit=limit)
    if isinstance(raw_input, list):
        compact = ", ".join(
            summarize_tool_input(item, limit=max(12, limit // max(len(raw_input), 1)))
            for item in raw_input[:3]
        ).strip(", ")
        return summarize_tool_input(compact, limit=limit) if compact else ""
    return ""


def describe_tool_call(tool_name: str, input_summary: str | None = None, *, locale: str = "zh") -> str:
    """Translate raw tool calls into user-facing stage text.

    Returns i18n key for Flutter to resolve, with Chinese fallback for
    backward compatibility when locale='zh'.
    """
    normalized = str(tool_name or "").strip()
    i18n_key = _TOOL_STAGE_DESCRIPTIONS.get(normalized)
    if i18n_key and locale != "zh":
        return i18n_key
    base = _TOOL_STAGE_DESCRIPTIONS_ZH.get(normalized, f"正在执行操作：{normalized or 'unknown'}")
    summary = str(input_summary or "").strip()
    if summary:
        return f"{base}（{summary}）"
    return base


class IntentTranslator:
    """Translate ExecutionIntent to OpenClaw `/v1/responses` requests."""

    def __init__(self, risk_assessor: ExecutionRiskAssessor | None = None):
        self._risk_assessor = risk_assessor or ExecutionRiskAssessor()

    def build_session_key(self, intent: ExecutionIntent, *, agent_id: str = "") -> str:
        policy = intent.policy or {}
        override = str(policy.get("session_key") or policy.get("chat_session_key") or "").strip()
        if override:
            return override
        agent_suffix = agent_id or "main"
        return f"sparkle:{agent_suffix}:{intent.user_id}:{intent.task_id}"

    def translate(
        self,
        intent: ExecutionIntent,
        *,
        agent_id: str = "",
        model_override: str | None = None,
    ) -> dict[str, Any]:
        self._enforce_safety_guards(intent)
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
        self._enforce_safety_guards(intent)
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

    def _enforce_safety_guards(self, intent: ExecutionIntent) -> None:
        policy = intent.policy or {}
        cached_risk = policy.get("_risk_assessment")
        if isinstance(cached_risk, dict) and cached_risk.get("blocked"):
            raise IntentTranslationSafetyError(
                str(cached_risk.get("blocked_reason") or "该执行因安全策略被阻止")
            )

        assessment = self._risk_assessor.assess(
            intent_goal=intent.goal,
            instructions=list(intent.instructions or []),
            policy=policy,
            target_env=intent.target_env.value if intent.target_env else None,
        )
        if assessment.blocked:
            raise IntentTranslationSafetyError(
                assessment.blocked_reason or "该执行因安全策略被阻止"
            )

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

        approval_policy = policy.get("approval_policy")
        if approval_policy:
            lines.append(f"Approval policy: {approval_policy}")

        working_directory = str(policy.get("working_directory") or "").strip()
        if working_directory:
            lines.append(f"When executing shell commands, use working directory: {working_directory}")

        template_metadata = policy.get("template_metadata") or {}
        if template_metadata.get("template_name"):
            lines.append(f"Use template behavior: {template_metadata['template_name']}")
        if template_metadata.get("optimized_prompt"):
            lines.append(str(template_metadata["optimized_prompt"]))

        quality_strategy = policy.get("quality_strategy") or {}
        if quality_strategy.get("variant_name"):
            lines.append(f"Execution strategy variant: {quality_strategy['variant_name']}")
        for extra_instruction in quality_strategy.get("configuration", {}).get("instruction_suffixes", []):
            lines.append(str(extra_instruction))

        target_node_label = policy.get("target_node_label")
        target_node_command = policy.get("target_node_command")
        if target_node_label:
            node_line = f"Prefer node: {target_node_label}"
            if target_node_command:
                node_line += f" using command {target_node_command}"
            lines.append(node_line)

        hybrid_plan = policy.get("hybrid_plan") or {}
        if hybrid_plan:
            lines.append(f"Hybrid execution stage: {hybrid_plan.get('stage', 'unknown')}")

        lines.extend(
            [
                "DO NOT send messages, emails, or make purchases.",
                "DO NOT modify account settings or passwords.",
                "If you encounter a login prompt or CAPTCHA, STOP and report it.",
                "Return results in a structured format.",
            ]
        )
        return "\n".join(lines)


class IntentTranslationSafetyError(ValueError):
    """Raised when Sparkle blocks a payload during final translation."""
