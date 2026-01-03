"""
LLM 响应解析器
Parser - 解析 LLM 输出并处理容错 (v2.2 增强版)

v2.2 变更:
- 使用 llm.py 中的增强版 coerce 函数
- 增强意图检测，支持更多中文表达和否定词排除
"""
import json
import re
from typing import Any, Optional, List
from pydantic import BaseModel
from loguru import logger
import json_repair

from app.schemas.llm import (
    LLMResponse,
    CoercedInt,
    CoercedStrList,
)


# ==================== Schema 定义 ====================

class TaskActionParams(BaseModel):
    """任务创建参数 - 宽容模式 (v2.2)"""
    title: str
    type: str = "learning"
    estimated_minutes: CoercedInt = 15  # 自动转换 "15" -> 15, "十五" -> 15, "1小时" -> 60
    tags: CoercedStrList = []           # 自动转换 "tag" -> ["tag"]
    difficulty: CoercedInt = 3          # 自动转换
    guide_content: Optional[str] = None

    class Config:
        extra = "ignore"


class ChatAction(BaseModel):
    """对话 Action"""
    type: str
    params: dict = {}

    class Config:
        extra = "ignore"





# ==================== 解析器 ====================

class LLMResponseParser:
    """
    LLM 响应解析器 - v2.1 增强版
    
    改进：
    1. Pydantic 宽容模式，自动类型转换
    2. 显性降级状态，不再"假装成功"
    """
    
    def parse(self, raw_response: str) -> LLMResponse:
        """
        解析 LLM 响应，支持多级容错
        
        Level 1: 直接解析（使用宽容模式）
        Level 2: JSON 修复后解析
        Level 3: 正则提取后解析
        Level 4: 🆕 显性降级（告知用户操作可能未成功）
        """
        
        # Level 1: 直接解析
        try:
            return self._parse_json(raw_response)
        except Exception as e:
            logger.warning(f"Direct parse failed: {e}")
        
        # Level 2: JSON 修复
        try:
            fixed = json_repair.repair_json(raw_response)
            return self._parse_json(fixed)
        except Exception as e:
            logger.warning(f"JSON repair failed: {e}")
        
        # Level 3: 正则提取
        try:
            json_match = re.search(r'\{[\s\S]*\}', raw_response)
            if json_match:
                return self._parse_json(json_match.group())
        except Exception as e:
            logger.warning(f"Regex extract failed: {e}")
        
        # Level 4: 🆕 显性降级 - 必须让用户知道
        logger.error("All parse methods failed, returning degraded response")
        
        extracted_text = self._extract_text(raw_response)
        
        # 🆕 关键改进：检测是否有"假装成功"的风险
        degraded_reason = self._detect_action_intent(extracted_text)
        
        return LLMResponse(
            assistant_message=extracted_text,
            actions=[],
            parse_degraded=True,  # 🆕 显性标记
            degraded_reason=degraded_reason
        )
    
    def _parse_json(self, json_str: str) -> LLMResponse:
        """解析并验证 JSON"""
        data = json.loads(json_str)
        return LLMResponse.model_validate(data)
    
    def _extract_text(self, raw: str) -> str:
        """从原始响应中提取可读文本"""
        text = re.sub(r'```json[\s\S]*?```', '', raw)
        text = re.sub(r'\{[\s\S]*\}', '', text)
        return text.strip() or "抱歉，我遇到了一些问题，请重新描述您的需求。"
    
    def _detect_action_intent(self, text: str) -> Optional[str]:
        """
        增强版意图检测 (v2.2)

        检测文本中是否暗示了操作成功，同时处理否定句

        Returns:
            警告信息 (如果检测到假装成功的风险) 或 None
        """
        text_lower = text.lower()

        # 1. 否定词排除 - 如果句子是否定意图，不触发警告
        negation_prefixes = ["不要", "取消", "删除", "移除", "别", "不用", "不需要", "撤销"]
        for prefix in negation_prefixes:
            if prefix in text_lower:
                return None

        # 2. 定义意图映射
        intent_map = {
            "create_task": {
                "actions": [
                    "创建", "新建", "添加", "建立", "生成",
                    "安排", "记下", "记一下", "加个", "加一个",
                    "create", "add", "new", "make"
                ],
                "objects": [
                    "任务", "待办", "事项", "todo", "task",
                    "日程", "提醒", "计划", "复习", "学习"
                ],
                "message": "创建任务"
            },
            "create_plan": {
                "actions": [
                    "制定", "规划", "设定", "设置", "安排",
                    "plan", "schedule", "set"
                ],
                "objects": [
                    "计划", "方案", "日程", "安排", "目标",
                    "plan", "schedule", "goal"
                ],
                "message": "制定计划"
            },
            "exam_preparation": {
                "actions": [
                    "考试", "备考", "复习", "准备", "冲刺",
                    "exam", "prepare", "review"
                ],
                "objects": [
                    "考研", "期末", "测验", "quiz", "midterm", "final"
                ],
                "urgency_keywords": [
                    "明天", "后天", "下周", "即将", "马上",
                    "tomorrow", "soon"
                ],
                "message": "考试冲刺准备"
            },
            "fake_success": {
                "phrases": [
                    "已为您", "成功创建", "已经创建", "帮你创建了",
                    "已添加", "已安排", "创建完成", "添加完成",
                    "done", "finished", "created", "added",
                    "好的，我已", "我帮你", "已经帮你"
                ],
                "message": "执行操作"
            }
        }

        # 3. 检查显式的成功短语 (优先级最高)
        for phrase in intent_map["fake_success"]["phrases"]:
            if phrase in text_lower:
                return (
                    f"AI 反馈包含'{phrase}'，但未生成有效数据结构。"
                    f"请尝试更明确的指令（如：'创建一个背单词任务，预计15分钟'）。"
                )

        # 4. 交叉匹配动作和对象
        for intent_key in ["create_task", "create_plan"]:
            intent = intent_map[intent_key]
            has_action = any(a in text_lower for a in intent["actions"])
            has_object = any(o in text_lower for o in intent["objects"])

            if has_action and has_object:
                return (
                    f"AI 识别到{intent['message']}意图，但未能生成正确的 JSON 格式。"
                    f"请尝试更明确的指令（如：'创建一个背单词任务'）。"
                )

        exam_intent = intent_map["exam_preparation"]
        has_exam = any(a in text_lower for a in exam_intent["actions"]) or any(o in text_lower for o in exam_intent["objects"])
        has_urgency = any(k in text_lower for k in exam_intent["urgency_keywords"])
        if has_exam:
            urgency_hint = "（检测到紧急时间）" if has_urgency else ""
            return (
                f"AI 识别到{exam_intent['message']}{urgency_hint}意图，但未能生成正确的 JSON 格式。"
                f"请尝试更明确的指令（如：'帮我创建一个3天冲刺复习计划'）。"
            )

        return None
