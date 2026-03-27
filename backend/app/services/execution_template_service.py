"""Execution template library for Phase 4 delegated workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models.execution_intent import ExecutionMode, ExecutionTargetEnv
from app.models.task import Task


@dataclass(frozen=True)
class ExecutionTemplateDefinition:
    template_id: str
    name: str
    description: str
    execution_mode: ExecutionMode
    target_env: ExecutionTargetEnv
    keywords: tuple[str, ...] = ()
    task_types: tuple[str, ...] = ()
    tag_hints: tuple[str, ...] = ()
    default_instructions: tuple[str, ...] = ()
    policy_patch: dict[str, Any] = field(default_factory=dict)
    success_criteria_patch: dict[str, Any] = field(default_factory=dict)
    result_contract_patch: dict[str, Any] = field(default_factory=dict)
    required_node_command: str | None = None


@dataclass(frozen=True)
class ExecutionTemplateMatch:
    definition: ExecutionTemplateDefinition
    match_score: float
    match_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.definition.template_id,
            "name": self.definition.name,
            "description": self.definition.description,
            "execution_mode": self.definition.execution_mode.value,
            "target_env": self.definition.target_env.value,
            "match_score": round(self.match_score, 4),
            "match_reasons": list(self.match_reasons),
            "required_node_command": self.definition.required_node_command,
        }


class ExecutionTemplateService:
    """Provide built-in execution templates and auto matching."""

    def __init__(self) -> None:
        self._templates = self._build_templates()

    def list_templates(
        self,
        *,
        task: Task,
        goal_override: str | None = None,
    ) -> list[ExecutionTemplateMatch]:
        text = " ".join(
            filter(
                None,
                [
                    (goal_override or task.title or "").strip(),
                    " ".join(task.tags or []),
                    str(task.type.value if task.type else ""),
                ],
            )
        ).lower()
        task_type = str(task.type.value if task.type else "").upper()
        tag_set = {str(tag).lower() for tag in (task.tags or [])}

        matches: list[ExecutionTemplateMatch] = []
        for template in self._templates:
            score = 0.0
            reasons: list[str] = []

            if task_type and task_type in template.task_types:
                score += 0.38
                reasons.append(f"task_type:{task_type.lower()}")

            keyword_hits = [keyword for keyword in template.keywords if keyword.lower() in text]
            if keyword_hits:
                score += min(0.42, 0.12 * len(keyword_hits))
                reasons.extend(f"keyword:{keyword}" for keyword in keyword_hits[:3])

            tag_hits = [tag for tag in template.tag_hints if tag.lower() in tag_set]
            if tag_hits:
                score += min(0.2, 0.08 * len(tag_hits))
                reasons.extend(f"tag:{tag}" for tag in tag_hits[:2])

            if score <= 0:
                continue

            matches.append(
                ExecutionTemplateMatch(
                    definition=template,
                    match_score=min(score, 0.98),
                    match_reasons=tuple(reasons),
                )
            )

        return sorted(matches, key=lambda item: item.match_score, reverse=True)

    def get_definition(self, template_id: str) -> ExecutionTemplateDefinition:
        for template in self._templates:
            if template.template_id == template_id:
                return template
        raise ValueError(f"Execution template not found: {template_id}")

    def auto_select(
        self,
        *,
        task: Task,
        goal_override: str | None = None,
        min_score: float = 0.72,
    ) -> ExecutionTemplateMatch | None:
        matches = self.list_templates(task=task, goal_override=goal_override)
        if not matches:
            return None
        best = matches[0]
        return best if best.match_score >= min_score else None

    def apply_template(
        self,
        *,
        task: Task,
        template_id: str,
        goal_override: str | None = None,
    ) -> dict[str, Any]:
        definition = self.get_definition(template_id)
        goal = (goal_override or task.title or "").strip()

        policy = dict(definition.policy_patch)
        if definition.execution_mode == ExecutionMode.HYBRID:
            policy.setdefault("approval_policy", "require_before_completion")
            policy.setdefault(
                "hybrid_plan",
                {
                    "stage": "prepare_then_confirm",
                    "steps": [
                        "prepare_artifacts",
                        "wait_for_user_review",
                        "commit_after_confirmation",
                    ],
                },
            )

        metadata = {
            "template_id": definition.template_id,
            "template_name": definition.name,
            "template_description": definition.description,
        }
        policy.setdefault("template_metadata", metadata)
        if definition.required_node_command:
            policy.setdefault("required_node_command", definition.required_node_command)

        return {
            "template_id": definition.template_id,
            "template_name": definition.name,
            "goal": goal,
            "execution_mode": definition.execution_mode,
            "target_env": definition.target_env,
            "instructions": list(definition.default_instructions),
            "policy": policy,
            "success_criteria": dict(definition.success_criteria_patch),
            "result_contract": dict(definition.result_contract_patch),
            "required_node_command": definition.required_node_command,
        }

    def _build_templates(self) -> list[ExecutionTemplateDefinition]:
        return [
            ExecutionTemplateDefinition(
                template_id="web_research_brief",
                name="网页调研简报",
                description="适合资料搜索、网页阅读和结构化总结。",
                execution_mode=ExecutionMode.AGENT,
                target_env=ExecutionTargetEnv.BROWSER,
                keywords=("搜索", "调研", "research", "网页", "网站", "资料", "浏览"),
                task_types=("OCR", "PLANNING"),
                tag_hints=("research", "browser", "summary"),
                default_instructions=(
                    "优先提取结论、证据来源和后续建议。",
                    "如果页面信息不足，明确标记缺口而不是猜测。",
                ),
                policy_patch={
                    "allowed_tools": ["browser", "read", "write_summary"],
                    "allow_exec": False,
                    "approval_policy": "deny",
                },
                success_criteria_patch={
                    "type": "structured_output",
                    "required_fields": ["summary", "key_findings", "sources"],
                },
                result_contract_patch={
                    "artifact_types": ["text", "screenshot"],
                    "parsed_output_schema": {
                        "type": "object",
                        "required": ["summary", "key_findings", "sources"],
                        "properties": {
                            "summary": {"type": "string"},
                            "key_findings": {"type": "array"},
                            "sources": {"type": "array"},
                        },
                    },
                },
            ),
            ExecutionTemplateDefinition(
                template_id="document_digest",
                name="文档摘要整理",
                description="适合 PDF、文档、笔记的提炼与行动项整理。",
                execution_mode=ExecutionMode.AGENT,
                target_env=ExecutionTargetEnv.DOCUMENT,
                keywords=("文档", "pdf", "摘要", "总结", "整理", "笔记"),
                task_types=("OCR", "PLANNING"),
                tag_hints=("document", "notes", "digest"),
                default_instructions=(
                    "输出简洁摘要，并列出可以直接执行的行动项。",
                    "若发现原文存在冲突信息，单独标记风险。",
                ),
                policy_patch={
                    "allowed_tools": ["read", "write_summary"],
                    "allow_exec": False,
                    "approval_policy": "deny",
                },
                success_criteria_patch={
                    "type": "structured_output",
                    "required_fields": ["summary", "highlights", "action_items"],
                },
                result_contract_patch={
                    "artifact_types": ["text"],
                    "parsed_output_schema": {
                        "type": "object",
                        "required": ["summary", "highlights", "action_items"],
                        "properties": {
                            "summary": {"type": "string"},
                            "highlights": {"type": "array"},
                            "action_items": {"type": "array"},
                        },
                    },
                },
            ),
            ExecutionTemplateDefinition(
                template_id="shell_diagnostics",
                name="终端诊断执行",
                description="适合低风险 shell 诊断、检查和只读命令执行。",
                execution_mode=ExecutionMode.AGENT,
                target_env=ExecutionTargetEnv.SHELL,
                keywords=("脚本", "命令", "终端", "诊断", "debug", "检查", "status"),
                task_types=("PLANNING", "SOCIAL"),
                tag_hints=("shell", "terminal", "ops"),
                default_instructions=(
                    "优先使用只读诊断命令，避免任何破坏性操作。",
                    "返回执行摘要、关键输出和下一步建议。",
                ),
                policy_patch={
                    "allowed_tools": ["exec", "read", "write_summary"],
                    "allow_exec": True,
                    "approval_policy": "require_for_side_effects",
                },
                success_criteria_patch={
                    "type": "structured_output",
                    "required_fields": ["summary", "key_output", "next_steps"],
                },
                result_contract_patch={
                    "artifact_types": ["text"],
                    "parsed_output_schema": {
                        "type": "object",
                        "required": ["summary", "key_output", "next_steps"],
                        "properties": {
                            "summary": {"type": "string"},
                            "key_output": {"type": "array"},
                            "next_steps": {"type": "array"},
                        },
                    },
                },
                required_node_command="system.run",
            ),
            ExecutionTemplateDefinition(
                template_id="browser_form_prepare",
                name="浏览器表单协作",
                description="AI 先准备信息和草稿，用户确认后再完成有副作用的浏览器步骤。",
                execution_mode=ExecutionMode.HYBRID,
                target_env=ExecutionTargetEnv.BROWSER,
                keywords=("表单", "提交", "申请", "填写", "预约", "创建", "publish"),
                task_types=("SOCIAL", "PLANNING"),
                tag_hints=("browser", "approval", "form"),
                default_instructions=(
                    "先收集和整理需要填写的字段，再等待用户确认。",
                    "任何提交、发送、保存动作都必须在确认后进行。",
                ),
                policy_patch={
                    "allowed_tools": ["browser", "read", "write_summary"],
                    "allow_exec": False,
                },
                success_criteria_patch={
                    "type": "structured_output",
                    "required_fields": ["draft", "fields_to_confirm", "final_action"],
                },
                result_contract_patch={
                    "artifact_types": ["text", "screenshot"],
                    "parsed_output_schema": {
                        "type": "object",
                        "required": ["draft", "fields_to_confirm", "final_action"],
                        "properties": {
                            "draft": {"type": "string"},
                            "fields_to_confirm": {"type": "array"},
                            "final_action": {"type": "string"},
                        },
                    },
                },
            ),
            ExecutionTemplateDefinition(
                template_id="cross_device_capture",
                name="跨设备节点协作",
                description="通过节点能力采集信息或在指定设备上执行动作。",
                execution_mode=ExecutionMode.HYBRID,
                target_env=ExecutionTargetEnv.DOCUMENT,
                keywords=("设备", "节点", "拍照", "截图", "mac", "ios", "android", "跨设备"),
                task_types=("OCR", "SOCIAL"),
                tag_hints=("node", "device", "capture"),
                default_instructions=(
                    "优先在目标节点上采集证据，再返回 Sparkle 等待用户确认下一步。",
                    "如果节点不可用，明确说明阻塞原因。",
                ),
                policy_patch={
                    "allowed_tools": ["read", "write_summary"],
                    "allow_exec": False,
                    "node_strategy": "prefer_connected",
                },
                success_criteria_patch={
                    "type": "structured_output",
                    "required_fields": ["summary", "artifacts", "recommended_next_step"],
                },
                result_contract_patch={
                    "artifact_types": ["text", "image", "screenshot"],
                    "parsed_output_schema": {
                        "type": "object",
                        "required": ["summary", "artifacts", "recommended_next_step"],
                        "properties": {
                            "summary": {"type": "string"},
                            "artifacts": {"type": "array"},
                            "recommended_next_step": {"type": "string"},
                        },
                    },
                },
                required_node_command="camera.capture",
            ),
        ]
