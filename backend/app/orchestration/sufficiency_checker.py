"""
信息充分性检查模块
Sufficiency Checker

检查LLM是否有足够信息执行用户请求，避免在没有必要信息时直接执行。
"""
from typing import Dict, Any, List, Optional, Literal
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class SufficiencyStatus(str, Enum):
    """信息充分性状态"""
    SUFFICIENT = "sufficient"           # 信息充足，可以直接执行
    NEED_CLARIFICATION = "need_clarification"  # 需要澄清信息
    NEED_CONFIRMATION = "need_confirmation"    # 需要用户确认


@dataclass
class SufficiencyCheckResult:
    """信息充分性检查结果"""
    status: SufficiencyStatus
    clarification_questions: List[str] = field(default_factory=list)
    confirmation_message: Optional[str] = None
    recommended_action: Literal["proceed", "ask", "confirm"] = "proceed"
    missing_fields: List[str] = field(default_factory=list)


class SufficiencyChecker:
    """
    检查LLM是否有足够信息执行操作

    设计原则:
    1. 意图驱动: 不同意图有不同的信息要求
    2. 渐进式: 优先使用上下文推断，必要时才追问
    3. 用户友好: 澄清问题清晰具体
    """

    # 各意图类型的信息要求
    INTENT_REQUIREMENTS = {
        "create_task": {
            "required": ["task_title"],  # 必需字段
            "clarify_if_missing": [  # 缺失时需要澄清
                "due_date",
                "task_type",
                "priority",
            ],
            "can_infer": [  # 可以从上下文推断
                "subject_id",
                "estimated_minutes",
            ],
        },
        "update_task": {
            "required": ["task_id"],
            "clarify_if_missing": ["new_status", "new_title"],
        },
        "create_plan": {
            "required": ["plan_title", "plan_type"],
            "clarify_if_missing": ["target_date", "subject_id"],
        },
        "generate_tasks": {
            "required": ["plan_id", "topic"],
            "clarify_if_missing": ["difficulty", "task_count"],
        },
        "knowledge_query": {
            "required": ["query"],
            "clarify_if_missing": ["subject_id"],
        },
        "start_focus": {
            "required": [],
            "clarify_if_missing": ["duration_minutes", "task_id"],
        },
        "time_planning": {
            "required": ["plan_type"],
            "clarify_if_missing": ["target_date", "daily_hours"],
        },
    }

    # 默认要求（未知意图类型）
    DEFAULT_REQUIREMENTS = {
        "required": [],
        "clarify_if_missing": [],
        "can_infer": [],
    }

    def __init__(self, strict_mode: bool = False):
        """
        Args:
            strict_mode: 严格模式，缺失任何可选字段也会询问
        """
        self.strict_mode = strict_mode

    async def check(
        self,
        intent: str,
        extracted_entities: Dict[str, Any],
        conversation_context: List[Dict[str, Any]],
    ) -> SufficiencyCheckResult:
        """
        检查是否有足够信息执行意图

        Args:
            intent: 意图类型 (create_task, create_plan, etc.)
            extracted_entities: 已提取的实体
            conversation_context: 对话历史上下文（用于推断）

        Returns:
            SufficiencyCheckResult: 检查结果
        """
        requirements = self.INTENT_REQUIREMENTS.get(
            intent,
            self.DEFAULT_REQUIREMENTS
        )

        required_fields = requirements.get("required", [])
        clarify_fields = requirements.get("clarify_if_missing", [])
        can_infer_fields = requirements.get("can_infer", [])

        result = SufficiencyCheckResult(status=SufficiencyStatus.SUFFICIENT)

        # 检查必需字段
        for field in required_fields:
            if not self._has_field_value(field, extracted_entities):
                result.status = SufficiencyStatus.NEED_CLARIFICATION
                result.recommended_action = "ask"
                result.missing_fields.append(field)
                question = self._generate_clarification_question(field, intent)
                if question:
                    result.clarification_questions.append(question)

        # 检查需要澄清的字段
        if result.status == SufficiencyStatus.SUFFICIENT:
            for field in clarify_fields:
                if not self._has_field_value(field, extracted_entities):
                    # 尝试从上下文推断
                    inferred_value = self._infer_from_context(
                        field, intent, conversation_context
                    )
                    if inferred_value is None and self.strict_mode:
                        result.status = SufficiencyStatus.NEED_CLARIFICATION
                        result.recommended_action = "ask"
                        question = self._generate_clarification_question(field, intent)
                        if question:
                            result.clarification_questions.append(question)

        # 检查是否需要确认（高风险操作）
        if result.status == SufficiencyStatus.SUFFICIENT:
            if self._requires_confirmation(intent, extracted_entities):
                result.status = SufficiencyStatus.NEED_CONFIRMATION
                result.recommended_action = "confirm"
                result.confirmation_message = self._generate_confirmation_message(
                    intent, extracted_entities
                )

        logger.debug(
            f"Sufficiency check: intent={intent}, status={result.status}, "
            f"missing_fields={result.missing_fields}"
        )

        return result

    def _has_field_value(self, field: str, entities: Dict[str, Any]) -> bool:
        """检查字段是否有有效值"""
        value = entities.get(field)
        if value is None:
            return False
        if isinstance(value, str) and not value.strip():
            return False
        if isinstance(value, list) and len(value) == 0:
            return False
        return True

    def _infer_from_context(
        self,
        field: str,
        intent: str,
        context: List[Dict[str, Any]],
    ) -> Optional[Any]:
        """从对话上下文推断字段值"""
        if not context:
            return None

        # 从最近的对话中查找
        for msg in reversed(context[-5:]):  # 只看最近5条
            content = msg.get("content", "")
            role = msg.get("role", "")

            # 优先从用户消息中提取
            if role == "user":
                # 简单推断规则
                if field == "subject_id":
                    # 从最近的对话中查找科目提及
                    # 这里可以调用NER或知识图谱服务
                    pass
                elif field == "estimated_minutes":
                    # 查找时长相关数字
                    import re
                    time_matches = re.findall(r"(\d+)\s*(分钟|小时|hour|min)", content)
                    if time_matches:
                        value, unit = time_matches[0]
                        if "小时" in unit or "hour" in unit:
                            return int(value) * 60
                        return int(value)

        return None

    def _requires_confirmation(
        self,
        intent: str,
        entities: Dict[str, Any],
    ) -> bool:
        """检查是否需要用户确认"""
        # 高风险操作需要确认
        CONFIRMATION_REQUIRED_INTENTS = {
            "delete_task",
            "delete_plan",
            "abandon_plan",
            "bulk_delete",
        }

        if intent in CONFIRMATION_REQUIRED_INTENTS:
            return True

        # 某些条件下的确认
        if intent == "create_task":
            # 如果设置高优先级，需要确认
            priority = entities.get("priority", 2)
            if priority >= 4:
                return True

        return False

    def _generate_clarification_question(
        self,
        field: str,
        intent: str,
    ) -> Optional[str]:
        """生成澄清问题"""
        QUESTIONS = {
            "task_title": "请问您想创建什么任务？",
            "task_id": "请问您想操作哪个任务？",
            "plan_id": "请问您想操作哪个计划？",
            "plan_title": "请问您的计划叫什么名字？",
            "plan_type": "请问这是冲刺计划还是长期成长计划？",
            "target_date": "请问您的目标日期是什么时候？",
            "due_date": "请问这个任务什么时候截止？",
            "task_type": "请问这是什么类型的任务？（学习/训练/错题订正/反思）",
            "priority": "请问任务的优先级是多少？（1-5，5最高）",
            "subject_id": "请问这是关于哪个科目的？",
            "topic": "请问您想学习什么主题？",
            "duration_minutes": "请问您想专注多长时间？",
            "difficulty": "请问难度如何？（简单/中等/困难）",
            "query": "请问您想查询什么？",
        }

        return QUESTIONS.get(field)

    def _generate_confirmation_message(
        self,
        intent: str,
        entities: Dict[str, Any],
    ) -> str:
        """生成确认消息"""
        if intent == "delete_task":
            title = entities.get("task_title", "此任务")
            return f"您确定要删除任务「{title}」吗？此操作不可撤销。"

        if intent == "delete_plan":
            title = entities.get("plan_title", "此计划")
            return f"您确定要删除计划「{title}」吗？所有相关任务也将被删除。"

        if intent == "abandon_plan":
            title = entities.get("plan_title", "此计划")
            return f"您确定要放弃计划「{title}」吗？"

        if intent == "create_task" and entities.get("priority", 0) >= 4:
            title = entities.get("task_title", "此任务")
            return f"您正在创建高优先级任务「{title}」，确认继续吗？"

        return "请确认是否继续此操作。"


# 全局实例
sufficiency_checker = SufficiencyChecker()
