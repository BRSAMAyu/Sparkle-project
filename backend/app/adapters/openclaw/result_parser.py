"""Parse OpenClaw responses into Sparkle-standardized results."""

from __future__ import annotations

import json
from typing import Any

from loguru import logger


class ResultParser:
    """Parse OpenClaw `/v1/responses` output."""

    def parse(self, raw_response: dict[str, Any]) -> dict[str, Any]:
        try:
            status = raw_response.get("status", "unknown")
            output_items = raw_response.get("output", [])
            usage = raw_response.get("usage")
            requires_approval = self._requires_approval(raw_response)

            if isinstance(output_items, str):
                output_text = output_items.strip()
                return {
                    "success": status == "completed" and not requires_approval and bool(output_text),
                    "output": output_text,
                    "parsed_output": self._try_parse_structured(output_text),
                    "artifacts": [],
                    "tool_calls_count": 0,
                    "token_usage": usage,
                    "requires_approval": requires_approval,
                    "approval_requests": 1 if requires_approval else 0,
                    "error_message": None if output_text else f"status={status}, no_output=True",
                    "raw_status": status,
                }

            text_parts: list[str] = []
            tool_calls_count = 0
            artifacts: list[dict[str, Any]] = []

            for item in output_items:
                item_type = item.get("type", "")
                if item_type == "message":
                    for block in item.get("content", []):
                        block_type = block.get("type")
                        if block_type == "output_text":
                            text_parts.append(block.get("text", ""))
                        elif block_type in {"output_image", "file"}:
                            artifacts.append(block)
                elif item_type == "function_call":
                    tool_calls_count += 1
                elif item_type in {"file", "image"}:
                    artifacts.append(item)

            output_text = "\n".join(part for part in text_parts if part).strip()
            parsed_output = self._try_parse_structured(output_text)
            success = status == "completed" and not requires_approval and bool(output_text or parsed_output)

            return {
                "success": success,
                "output": output_text,
                "parsed_output": parsed_output,
                "artifacts": artifacts,
                "tool_calls_count": tool_calls_count,
                "token_usage": usage,
                "requires_approval": requires_approval,
                "approval_requests": 1 if requires_approval else 0,
                "error_message": None if success else f"status={status}, no_output={not bool(output_text)}",
                "raw_status": status,
            }
        except Exception as exc:
            logger.exception("Failed to parse OpenClaw response")
            return {
                "success": False,
                "output": "",
                "parsed_output": None,
                "artifacts": [],
                "tool_calls_count": 0,
                "token_usage": None,
                "requires_approval": False,
                "approval_requests": 0,
                "error_message": str(exc),
                "raw_status": "parse_error",
            }

    def _requires_approval(self, raw_response: dict[str, Any]) -> bool:
        status = str(raw_response.get("status", "")).strip().lower()
        if status in {"requires_action", "waiting_approval", "approval_required"}:
            return True

        if raw_response.get("approval_required") is True:
            return True

        required_action = raw_response.get("required_action")
        if isinstance(required_action, dict) and required_action:
            return True

        approval = raw_response.get("approval")
        return isinstance(approval, dict) and bool(approval)

    def _try_parse_structured(self, text: str) -> dict[str, Any] | None:
        if not text:
            return None

        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass

        if "```json" in text:
            try:
                start = text.index("```json") + 7
                end = text.index("```", start)
                parsed = json.loads(text[start:end].strip())
                if isinstance(parsed, dict):
                    return parsed
            except (ValueError, json.JSONDecodeError, TypeError):
                return None

        return None
