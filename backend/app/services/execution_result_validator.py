"""Lightweight execution result validator and presenter helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ResultQualityWarning:
    code: str
    severity: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


class ExecutionResultValidator:
    """Rule-based helpers for execution result warnings, replay, and comparisons."""

    def validate(
        self,
        *,
        parsed: dict[str, Any],
        result_contract: dict[str, Any] | None = None,
    ) -> list[dict[str, str]]:
        result_contract = result_contract or {}
        warnings: list[ResultQualityWarning] = []

        output = str(parsed.get("output") or "").strip()
        parsed_output = parsed.get("parsed_output")
        artifacts = list(parsed.get("artifacts") or [])
        required_fields = list(result_contract.get("required_fields") or [])
        artifact_types = list(result_contract.get("artifact_types") or [])

        if not output and not isinstance(parsed_output, dict):
            warnings.append(
                ResultQualityWarning(
                    code="empty_result",
                    severity="high",
                    message="执行结果为空，缺少可展示的正文或结构化输出。",
                ),
            )

        if isinstance(parsed_output, dict) and required_fields:
            missing = [field for field in required_fields if parsed_output.get(field) in (None, "", [], {})]
            if missing:
                warnings.append(
                    ResultQualityWarning(
                        code="missing_required_fields",
                        severity="high",
                        message=f"结构化结果缺少关键字段：{', '.join(missing)}。",
                    ),
                )

        if artifact_types and not artifacts:
            warnings.append(
                ResultQualityWarning(
                    code="missing_artifacts",
                    severity="medium",
                    message="该模板预期返回附件，但本次结果没有产生任何附件。",
                ),
            )

        if parsed.get("success") and output and len(output) < 48 and not isinstance(parsed_output, dict):
            warnings.append(
                ResultQualityWarning(
                    code="thin_output",
                    severity="medium",
                    message="结果过短，建议人工快速复核后再采纳。",
                ),
            )

        if parsed.get("error_message"):
            warnings.append(
                ResultQualityWarning(
                    code="execution_error",
                    severity="high",
                    message=str(parsed.get("error_message")),
                ),
            )

        return [warning.to_dict() for warning in warnings]

    def build_replay_steps_from_raw_response(self, raw_response: dict[str, Any] | None) -> list[dict[str, Any]]:
        if not isinstance(raw_response, dict):
            return []

        steps: list[dict[str, Any]] = []
        output_items = raw_response.get("output")
        if not isinstance(output_items, list):
            return steps

        for index, item in enumerate(output_items, start=1):
            item_type = str(item.get("type") or "message")
            if item_type == "function_call":
                arguments = item.get("arguments")
                steps.append(
                    {
                        "index": index,
                        "kind": "tool_call",
                        "label": str(item.get("name") or item.get("call_id") or f"tool_{index}"),
                        "status": "completed",
                        "preview": self._truncate(self._stringify(arguments)),
                    },
                )
                continue

            if item_type == "message":
                content_blocks = item.get("content")
                if isinstance(content_blocks, list):
                    for block in content_blocks:
                        block_type = str(block.get("type") or "output_text")
                        if block_type == "output_text":
                            steps.append(
                                {
                                    "index": len(steps) + 1,
                                    "kind": "message",
                                    "label": "生成结果",
                                    "status": "completed",
                                    "preview": self._truncate(str(block.get("text") or "")),
                                },
                            )
                        elif block_type in {"output_image", "file"}:
                            steps.append(
                                {
                                    "index": len(steps) + 1,
                                    "kind": "artifact",
                                    "label": str(block.get("name") or block.get("file_id") or "附件"),
                                    "status": "completed",
                                    "preview": self._truncate(self._stringify(block)),
                                },
                            )
                continue

            if item_type in {"file", "image"}:
                steps.append(
                    {
                        "index": index,
                        "kind": "artifact",
                        "label": str(item.get("name") or item.get("id") or "附件"),
                        "status": "completed",
                        "preview": self._truncate(self._stringify(item)),
                    },
                )

        return steps

    def build_replay_steps_from_plan_result(self, plan_result: Any | None) -> list[dict[str, Any]]:
        step_results = getattr(plan_result, "step_results", None)
        if not isinstance(step_results, list):
            return []

        replay_steps: list[dict[str, Any]] = []
        for index, step in enumerate(step_results, start=1):
            tool_result = getattr(step, "tool_result", None)
            success = bool(getattr(tool_result, "success", False))
            preview = self._compact_output_data(getattr(step, "output_data", None))
            if not preview:
                preview = str(getattr(tool_result, "error_message", "") or "")
            replay_steps.append(
                {
                    "index": index,
                    "kind": "tool_call",
                    "label": str(getattr(step, "tool_name", "") or f"step_{index}"),
                    "status": "completed" if success else "failed",
                    "duration_ms": int(getattr(step, "duration_ms", 0) or 0),
                    "preview": self._truncate(preview),
                },
            )
        return replay_steps

    def extract_preview(self, parsed: dict[str, Any]) -> dict[str, Any] | None:
        parsed_output = parsed.get("parsed_output")
        if isinstance(parsed_output, dict) and parsed_output:
            return parsed_output

        output = str(parsed.get("output") or "").strip()
        if output:
            return {"text": output}
        return None

    def extract_plan_result_preview(self, plan_result: Any | None) -> dict[str, Any] | None:
        step_results = getattr(plan_result, "step_results", None)
        if not isinstance(step_results, list):
            return None

        for step in reversed(step_results):
            output_data = getattr(step, "output_data", None)
            if isinstance(output_data, dict) and output_data:
                return output_data
            tool_result = getattr(step, "tool_result", None)
            data = getattr(tool_result, "data", None)
            if isinstance(data, dict) and data:
                return data

        for step in reversed(step_results):
            tool_result = getattr(step, "tool_result", None)
            text = str(getattr(tool_result, "error_message", "") or "").strip()
            if text:
                return {"text": text}
        return None

    def build_comparison_summary(
        self,
        *,
        current_record: Any,
        previous_record: Any | None,
    ) -> dict[str, Any] | None:
        if previous_record is None:
            return None

        current_quality = float(getattr(current_record, "quality_score", 0.0) or 0.0)
        previous_quality = float(getattr(previous_record, "quality_score", 0.0) or 0.0)
        quality_delta = round(current_quality - previous_quality, 2)
        current_tools = int(getattr(current_record, "tool_calls_count", 0) or 0)
        previous_tools = int(getattr(previous_record, "tool_calls_count", 0) or 0)
        tool_delta = current_tools - previous_tools

        if quality_delta > 0.05:
            headline = "这次结果比上次更稳"
            summary = f"质量分提升了 {quality_delta:.2f}，可直接复核关键结论。"
        elif quality_delta < -0.05:
            headline = "这次结果比上次更需要复核"
            summary = f"质量分下降了 {abs(quality_delta):.2f}，建议重点检查关键输出。"
        elif tool_delta < 0:
            headline = "这次执行更精简"
            summary = f"相比上次少用了 {abs(tool_delta)} 次工具调用，执行链路更短。"
        elif tool_delta > 0:
            headline = "这次执行更深入"
            summary = f"相比上次多了 {tool_delta} 次工具调用，覆盖面更广。"
        else:
            headline = "这次结果与上次接近"
            summary = "质量和执行复杂度基本持平，可以按相同标准快速审阅。"

        return {
            "headline": headline,
            "summary": summary,
            "quality_delta": quality_delta,
            "tool_delta": tool_delta,
        }

    def build_validation_summary(self, validation_result: Any) -> dict[str, Any]:
        step_validations = list(getattr(validation_result, "step_validations", []) or [])
        passed = sum(1 for step in step_validations if getattr(step, "passed", False))
        total = len(step_validations)
        quality_score = float(getattr(validation_result, "quality_score", 0.0) or 0.0)
        issues = [str(item) for item in (getattr(validation_result, "issues", []) or []) if str(item).strip()]
        warnings: list[dict[str, str]] = []
        if getattr(validation_result, "validation_status", "") != "passed":
            warnings.append(
                ResultQualityWarning(
                    code="validation_partial",
                    severity="medium" if passed else "high",
                    message=f"执行验证通过 {passed}/{total} 个步骤。",
                ).to_dict(),
            )
        warnings.extend(
            ResultQualityWarning(
                code=f"issue_{index}",
                severity="medium",
                message=item,
            ).to_dict()
            for index, item in enumerate(issues[:3], start=1)
        )
        comparison_summary = (
            "执行结果与成功标准基本对齐。"
            if getattr(validation_result, "validation_status", "") == "passed"
            else f"执行结果与成功标准存在偏差，当前通过 {passed}/{total} 个步骤。"
        )
        return {
            "quality_warnings": warnings,
            "validation_issues": issues[:5],
            "comparison_summary": comparison_summary,
            "validation_passed": passed,
            "validation_total": total,
            "quality_score": quality_score,
        }

    def _compact_output_data(self, value: Any) -> str:
        if isinstance(value, dict):
            preview_items = []
            for key, item in list(value.items())[:3]:
                preview_items.append(f"{key}: {self._stringify(item)}")
            return ", ".join(preview_items)
        return self._stringify(value)

    def _stringify(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, list):
            return ", ".join(self._stringify(item) for item in value[:3])
        if isinstance(value, dict):
            return ", ".join(f"{key}={self._stringify(item)}" for key, item in list(value.items())[:3])
        return str(value)

    def _truncate(self, value: str, limit: int = 160) -> str:
        text = value.strip()
        if len(text) <= limit:
            return text
        return f"{text[: limit - 1].rstrip()}…"
