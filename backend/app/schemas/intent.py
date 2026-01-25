"""
多意图识别 Schema
Multi-Intent Recognition Schemas

用于识别和拆分用户输入中的多个意图
"""
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class IntentType(str, Enum):
    """意图类型枚举"""
    TASK_MANAGEMENT = "task_management"      # 任务管理
    KNOWLEDGE_QUERY = "knowledge_query"      # 知识查询
    TIME_PLANNING = "time_planning"          # 时间规划
    SOCIAL = "social"                        # 社交互动
    LEARNING = "learning"                    # 学习内容
    REFLECTION = "reflection"                # 复习反思
    TOOL_CALL = "tool_call"                  # 工具调用
    UNKNOWN = "unknown"                      # 未知意图


class SubIntent(BaseModel):
    """子意图"""
    type: IntentType = Field(description="意图类型")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度 0-1")
    content: str = Field(description="意图内容")
    entities: Dict[str, Any] = Field(default_factory=dict, description="提取的实体")
    agent_role: Optional[str] = Field(default=None, description="推荐的Agent角色")


class IntentDependency(BaseModel):
    """意图依赖关系"""
    depends_on: int = Field(description="依赖的意图索引")
    reason: str = Field(description="依赖原因")


class MultiIntentResult(BaseModel):
    """多意图识别结果"""
    is_multi_intent: bool = Field(description="是否为多意图")
    intents: List[SubIntent] = Field(description="识别出的意图列表")
    execution_order: List[int] = Field(description="执行顺序（索引列表）")
    dependencies: List[List[int]] = Field(default_factory=list, description="依赖关系 [[0,1], [2]]")
    should_parallel: List[bool] = Field(default_factory=list, description="是否可并行执行")
    estimated_total_time: Optional[int] = Field(default=None, description="预计总时间（秒）")


class IntentParseRequest(BaseModel):
    """意图解析请求"""
    message: str = Field(description="用户输入的消息")
    context: Optional[Dict[str, Any]] = Field(default=None, description="上下文信息")
    user_id: Optional[UUID] = Field(default=None, description="用户ID")


class IntentExecuteRequest(BaseModel):
    """意图执行请求"""
    parse_result: MultiIntentResult = Field(description="解析结果")
    confirmed: bool = Field(default=True, description="用户是否确认执行")
    user_id: UUID = Field(description="用户ID")


class IntentExecuteResponse(BaseModel):
    """意图执行响应"""
    success: bool = Field(description="是否成功")
    results: List[Dict[str, Any]] = Field(description="各意图执行结果")
    errors: List[str] = Field(default_factory=list, description="错误信息")
    total_time: float = Field(description="总执行时间（秒）")


class IntentAnalysisPreview(BaseModel):
    """意图分析预览"""
    original_message: str = Field(description="原始消息")
    detected_intents: List[SubIntent] = Field(description="检测到的意图")
    execution_plan: str = Field(description="执行计划描述")
    estimated_time: Optional[int] = Field(default=None, description="预计时间（秒）")
    suggested_agent_roles: List[str] = Field(default_factory=list, description="建议的Agent角色")
