"""
LLM 响应解析器
Parser - 解析 LLM 输出并处理容错 (v2.1 增强版)
"""
import json
import re
from typing import Any, Optional, List
from pydantic import BaseModel, BeforeValidator
from typing_extensions import Annotated
from loguru import logger
import json_repair

from app.schemas.llm import LLMResponse


# ==================== 🆕 宽容类型转换器 ====================

def coerce_int(v: Any) -> int:
    """将字符串数字转为 int"""
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        try:
            return int(v)
        except ValueError:
            pass
        # 尝试提取数字
        match = re.search(r'\d+', v)
        if match:
            return int(match.group())
    if isinstance(v, float):
        return int(v)
    raise ValueError(f"Cannot convert {v} to int")


def coerce_str_list(v: Any) -> List[str]:
    """将单个字符串转为列表"""
    if isinstance(v, list):
        return [str(item) for item in v]
    if isinstance(v, str):
        return [v]
    return []


# 宽容类型定义
CoercedInt = Annotated[int, BeforeValidator(coerce_int)]
CoercedStrList = Annotated[List[str], BeforeValidator(coerce_str_list)]


# ==================== Schema 定义 ====================

class TaskActionParams(BaseModel):
    """任务创建参数 - 宽容模式"""
    title: str
    type: str = "learning"
    estimated_minutes: CoercedInt = 15  # 🆕 自动转换 "15" -> 15
    tags: CoercedStrList = []           # 🆕 自动转换 "tag" -> ["tag"]
    difficulty: CoercedInt = 3          # 🆕 自动转换
    guide_content: Optional[str] = None
    
    class Config:
        # 忽略额外字段，不报错
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
        🆕 检测文本中是否暗示了操作成功
        
        如果检测到，返回警告信息
        """
        # 检测关键词
        success_indicators = [
            ("创建", "任务"),
            ("添加", "计划"),
            ("已为您", ""),
            ("帮你", "创建"),
            ("completed", ""),
        ]
        
        text_lower = text.lower()
        for indicator1, indicator2 in success_indicators:
            if indicator1 in text_lower:
                if not indicator2 or indicator2 in text_lower:
                    return f"AI 可能尝试执行了操作，但数据格式有误。如需{indicator1}，请手动操作或重新描述需求。"
        
        return None
