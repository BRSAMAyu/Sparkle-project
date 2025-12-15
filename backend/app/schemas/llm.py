"""
LLM Schemas
用于 AI 交互的宽容模式数据结构 (v2.1)
"""
from typing import Any, Optional, List
from pydantic import BaseModel, BeforeValidator, field_validator, Field
from typing_extensions import Annotated

# ==================== 宽容类型转换器 ====================

def coerce_int(v: Any) -> int:
    """
    宽容的 int 转换
    
    处理 LLM 常见错误：
    - "15" -> 15
    - 15.0 -> 15
    - "十五" -> 保留原值会报错，由 Pydantic 处理
    """
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        v = v.strip()
        try:
            return int(v)
        except ValueError:
            # 尝试浮点数转换
            try:
                return int(float(v))
            except ValueError:
                pass
    if isinstance(v, float):
        return int(v)
    raise ValueError(f"Cannot coerce {v!r} to int")


def coerce_float(v: Any) -> float:
    """宽容的 float 转换"""
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip())
        except ValueError:
            pass
    raise ValueError(f"Cannot coerce {v!r} to float")


def coerce_bool(v: Any) -> bool:
    """
    宽容的 bool 转换
    
    处理：
    - "true", "True", "TRUE" -> True
    - "false", "False", "FALSE" -> False
    - 1, 0 -> True, False
    """
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        if v.lower() in ("true", "yes", "1"):
            return True
        if v.lower() in ("false", "no", "0"):
            return False
    if isinstance(v, int):
        return bool(v)
    raise ValueError(f"Cannot coerce {v!r} to bool")


def coerce_str_list(v: Any) -> List[str]:
    """
    宽容的字符串列表转换
    
    处理：
    - "tag1" -> ["tag1"]
    - ["tag1", "tag2"] -> ["tag1", "tag2"]
    - "tag1, tag2" -> ["tag1", "tag2"]  # 逗号分隔
    """
    if isinstance(v, list):
        return [str(item).strip() for item in v if item]
    if isinstance(v, str):
        if "," in v:
            return [s.strip() for s in v.split(",") if s.strip()]
        return [v.strip()] if v.strip() else []
    return []


# ==================== 宽容类型别名 ====================

CoercedInt = Annotated[int, BeforeValidator(coerce_int)]
CoercedFloat = Annotated[float, BeforeValidator(coerce_float)]
CoercedBool = Annotated[bool, BeforeValidator(coerce_bool)]
CoercedStrList = Annotated[List[str], BeforeValidator(coerce_str_list)]


# ==================== LLM Action Schemas ====================

class CreateTaskParams(BaseModel):
    """创建任务参数 - 宽容模式"""
    title: str
    type: str = "learning"
    estimated_minutes: CoercedInt = 15
    tags: CoercedStrList = []
    difficulty: CoercedInt = 3
    guide_content: Optional[str] = None
    
    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title cannot be empty")
        return v[:100]  # 截断过长标题
    
    @field_validator("difficulty")
    @classmethod
    def difficulty_in_range(cls, v: int) -> int:
        return max(1, min(5, v))  # 限制在 1-5
    
    @field_validator("estimated_minutes")
    @classmethod
    def minutes_in_range(cls, v: int) -> int:
        return max(2, min(120, v))  # 限制在 2-120 分钟
    
    class Config:
        extra = "ignore"  # 忽略额外字段


class CreatePlanParams(BaseModel):
    """创建计划参数 - 宽容模式"""
    name: str
    type: str = "sprint"
    target_date: Optional[str] = None
    subject: Optional[str] = None
    daily_available_minutes: CoercedInt = 60
    
    class Config:
        extra = "ignore"
