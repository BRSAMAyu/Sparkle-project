"""
信息充分性检查模块
Sufficiency Checker

检查LLM是否有足够信息执行用户请求，避免在没有必要信息时直接执行。
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

from loguru import logger

from app.config import settings
from app.orchestration.clarification_voi_service import ClarificationVOIService
from app.orchestration.idea_crystallization_service import IdeaCrystallizationService
from app.orchestration.task_decomposition_contract import (
    build_task_decomposition_contract,
    generate_contract_clarification_questions,
)

class SufficiencyStatus(str, Enum):
    """信息充分性状态"""
    SUFFICIENT = "sufficient"           # 信息充足，可以直接执行
    NEED_CLARIFICATION = "need_clarification"  # 需要澄清信息
    NEED_CONFIRMATION = "need_confirmation"    # 需要用户确认


@dataclass
class SufficiencyCheckResult:
    """信息充分性检查结果"""
    status: SufficiencyStatus
    clarification_questions: list[str] = field(default_factory=list)
    confirmation_message: str | None = None
    clarification_text: str | None = None
    recommended_action: Literal["proceed", "ask", "confirm"] = "proceed"
    missing_fields: list[str] = field(default_factory=list)
    decomposition_contract: dict[str, Any] = field(default_factory=dict)
    decomposition_contract_score: float = 0.0
    decomposition_gaps: list[str] = field(default_factory=list)
    ambiguity_profile: dict[str, Any] = field(default_factory=dict)
    intent_hypotheses: list[dict[str, Any]] = field(default_factory=list)
    recommended_clarifications: list[dict[str, Any]] = field(default_factory=list)
    clarification_voi_score: float = 0.0


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
    LLM_ELIGIBLE_INTENTS = {"create_plan", "time_planning"}

    def __init__(self, strict_mode: bool = False):
        """
        Args:
            strict_mode: 严格模式，缺失任何可选字段也会询问
        """
        self.strict_mode = strict_mode

    async def check(
        self,
        intent: str,
        extracted_entities: dict[str, Any],
        conversation_context: list[dict[str, Any]],
        user_message: str | None = None,
        use_llm_fallback: bool = False,
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
        idea_crystallizer = IdeaCrystallizationService()
        voi_service = ClarificationVOIService()

        required_fields = requirements.get("required", [])
        clarify_fields = requirements.get("clarify_if_missing", [])
        requirements.get("can_infer", [])

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

        if (
            result.status == SufficiencyStatus.SUFFICIENT
            and use_llm_fallback
            and intent in self.LLM_ELIGIBLE_INTENTS
            and user_message
        ):
            llm_specific = await self._llm_refinement(intent=intent, user_message=user_message)
            if not llm_specific:
                result.status = SufficiencyStatus.NEED_CLARIFICATION
                result.recommended_action = "ask"
                result.clarification_text = await self._generate_clarification(intent, user_message)

        if settings.ENABLE_DECOMPOSITION_CONTRACT_V1 and user_message:
            contract = build_task_decomposition_contract(
                message=user_message,
                intent=intent,
                extracted_entities=extracted_entities,
                conversation_context=conversation_context,
            )
            result.decomposition_contract = contract.to_dict()
            result.decomposition_contract_score = contract.score
            result.decomposition_gaps = list(contract.gaps)

            decomposition_request = self._is_decomposition_request(intent=intent, user_message=user_message)
            if decomposition_request:
                crystallized = idea_crystallizer.crystallize(
                    message=user_message,
                    intent=intent,
                    extracted_entities=extracted_entities,
                    conversation_context=conversation_context,
                )
                result.decomposition_contract = crystallized.draft_goal_contract
                result.decomposition_contract_score = float(
                    crystallized.draft_goal_contract.get("score", result.decomposition_contract_score) or 0.0
                )
                result.decomposition_gaps = [
                    str(item)
                    for item in (crystallized.draft_goal_contract.get("gaps") or result.decomposition_gaps)
                    if str(item).strip()
                ]
                result.ambiguity_profile = crystallized.ambiguity_profile
                result.intent_hypotheses = crystallized.intent_hypotheses

                uncertainty_seed = max(0.0, min(1.0, 1.0 - result.decomposition_contract_score))
                voi_result = voi_service.rank(
                    contract=result.decomposition_contract,
                    ambiguity_profile=result.ambiguity_profile,
                    uncertainty_score=uncertainty_seed,
                    max_questions=3,
                )
                result.clarification_voi_score = voi_result.voi_score
                result.recommended_clarifications = voi_result.clarification_priority_points

            is_decomposition_request = decomposition_request
            required_contract_gaps = {
                "missing_goal",
                "missing_constraints",
                "missing_milestones",
                "missing_acceptance_criteria",
                "missing_risks",
            }
            has_blocking_contract_gap = bool(required_contract_gaps.intersection(contract.gaps))
            if result.status == SufficiencyStatus.SUFFICIENT and is_decomposition_request and has_blocking_contract_gap:
                result.status = SufficiencyStatus.NEED_CLARIFICATION
                result.recommended_action = "ask"
                result.clarification_questions.extend(
                    generate_contract_clarification_questions(contract.gaps)
                )
            elif result.status == SufficiencyStatus.SUFFICIENT and (contract.score < 0.28):
                result.status = SufficiencyStatus.NEED_CLARIFICATION
                result.recommended_action = "ask"
                result.clarification_questions.extend(
                    generate_contract_clarification_questions(contract.gaps)
                )

            if (
                result.status == SufficiencyStatus.SUFFICIENT
                and is_decomposition_request
                and result.clarification_voi_score >= 0.18
                and result.recommended_clarifications
            ):
                result.status = SufficiencyStatus.NEED_CLARIFICATION
                result.recommended_action = "ask"
                for item in result.recommended_clarifications:
                    question = str(item.get("question", "")).strip()
                    if question and question not in result.clarification_questions:
                        result.clarification_questions.append(question)

        logger.debug(
            f"Sufficiency check: intent={intent}, status={result.status}, "
            f"missing_fields={result.missing_fields}, "
            f"decomposition_score={result.decomposition_contract_score:.2f}"
        )

        return result

    @staticmethod
    def _is_decomposition_request(intent: str, user_message: str | None) -> bool:
        intent_value = (intent or "").strip().lower()
        if intent_value in {"create_plan", "time_planning", "plan", "sprint_plan", "task_decomposition", "study_plan"}:
            return True
        msg = (user_message or "").lower()
        keywords = (
            "任务拆解",
            "分解",
            "计划",
            "规划",
            "里程碑",
            "执行计划",
            "roadmap",
            "milestone",
            "step by step",
            "阶段计划",
        )
        return any(k in msg for k in keywords)

    def _has_field_value(self, field: str, entities: dict[str, Any]) -> bool:
        """检查字段是否有有效值"""
        value = entities.get(field)
        if value is None:
            return False
        if isinstance(value, str) and not value.strip():
            return False
        return not (isinstance(value, list) and len(value) == 0)

    def _infer_from_context(
        self,
        field: str,
        intent: str,
        context: list[dict[str, Any]],
    ) -> Any | None:
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
        entities: dict[str, Any],
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
    ) -> str | None:
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
        entities: dict[str, Any],
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

    async def _llm_refinement(self, intent: str, user_message: str) -> bool:
        from app.services.llm_service import llm_service

        prompt = f"""判断用户消息是否足够具体以执行意图。

意图: {intent}
用户消息: "{user_message}"

如果信息足够，返回 {{"specific": true}}
如果信息不足，需要补充澄清，返回 {{"specific": false}}
仅返回 JSON。"""
        try:
            result = await llm_service.chat_json(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            return bool(result.get("specific", False))
        except Exception as e:
            logger.warning(f"LLM refinement failed: {e}")
            return True

    async def _generate_clarification(self, intent: str, user_message: str) -> str:
        from app.services.llm_service import llm_service

        prompt = f"""你是学习助手。用户消息信息不足，请给出一句自然的追问。

意图: {intent}
用户消息: "{user_message}"

要求：
1. 一次只问 1-2 个关键问题
2. 语气自然简短
3. 直接输出追问文本"""
        try:
            text = await llm_service.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
            )
            return text.strip()
        except Exception as e:
            logger.warning(f"Clarification generation failed: {e}")
            return "为了更准确地帮你制定计划，请补充目标时间、考试节点和每天可投入时长。"


# 全局实例
sufficiency_checker = SufficiencyChecker()
