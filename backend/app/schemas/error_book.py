"""
错题档案相关的 Pydantic Schema
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ============================================
# 枚举定义
# ============================================


class SubjectEnum(str, Enum):
    """科目枚举"""

    MATH = "math"
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"
    BIOLOGY = "biology"
    ENGLISH = "english"
    CHINESE = "chinese"
    HISTORY = "history"
    GEOGRAPHY = "geography"
    POLITICS = "politics"
    COMPUTER = "computer"
    OTHER = "other"


class ErrorTypeEnum(str, Enum):
    """错因分类枚举"""

    CONCEPT_CONFUSION = "concept_confusion"
    CALCULATION_ERROR = "calculation_error"
    READING_CARELESS = "reading_careless"
    KNOWLEDGE_GAP = "knowledge_gap"
    METHOD_WRONG = "method_wrong"
    LOGIC_ERROR = "logic_error"
    MEMORY_LAPSE = "memory_lapse"
    TIME_PRESSURE = "time_pressure"
    OTHER = "other"


class ReviewPerformanceEnum(str, Enum):
    """复习表现枚举"""

    REMEMBERED = "remembered"
    FUZZY = "fuzzy"
    FORGOTTEN = "forgotten"


COGNITIVE_DIMENSIONS = {
    "memory",
    "understanding",
    "application",
    "analysis",
    "evaluation",
    "creation",
}

# ============================================
# 错题创建/更新 Schema
# ============================================


class ErrorRecordCreate(BaseModel):
    """创建错题的请求体"""

    question_text: str | None = Field(None, max_length=5000, description="题目内容")
    question_image_url: str | None = Field(None, max_length=500, description="题目图片URL")

    user_answer: str | None = Field(None, max_length=2000, description="你的错误答案")
    correct_answer: str | None = Field(None, max_length=2000, description="正确答案")

    subject: SubjectEnum = Field(..., description="科目")
    chapter: str | None = Field(None, max_length=100, description="章节（可选）")

    cognitive_tags: list[str] = Field(default_factory=list, description="认知维度标签")
    ai_analysis_summary: str | None = Field(None, description="AI 分析摘要")

    @field_validator("cognitive_tags")
    @classmethod
    def validate_cognitive_tags(cls, value: list[str]) -> list[str]:
        for tag in value:
            if tag not in COGNITIVE_DIMENSIONS:
                raise ValueError("Invalid cognitive dimension tag")
        return value

    @model_validator(mode="before")
    @classmethod
    def check_content_or_image(cls, data):
        if isinstance(data, dict):
            text = data.get("question_text")
            image = data.get("question_image_url")
            if not text and not image:
                raise ValueError("题目内容和图片不能同时为空")
        return data


class ErrorRecordUpdate(BaseModel):
    """更新错题的请求体"""

    question_text: str | None = Field(None, max_length=5000)
    user_answer: str | None = Field(None, max_length=2000)
    correct_answer: str | None = Field(None, max_length=2000)
    subject: SubjectEnum | None = None
    chapter: str | None = Field(None, max_length=100)
    question_image_url: str | None = Field(None, max_length=500)

    cognitive_tags: list[str] | None = None
    ai_analysis_summary: str | None = None

    @field_validator("cognitive_tags")
    @classmethod
    def validate_cognitive_tags(cls, value: list[str] | None) -> list[str] | None:
        if value:
            for tag in value:
                if tag not in COGNITIVE_DIMENSIONS:
                    raise ValueError("Invalid cognitive dimension tag")
        return value


# ============================================
# AI 分析结果 Schema
# ============================================


class ErrorAnalysisResult(BaseModel):
    """AI 分析结果"""

    error_type: ErrorTypeEnum = Field(..., description="错因分类")
    error_type_label: str = Field(..., description="错因分类的中文标签")
    root_cause: str = Field(..., description="错误根因分析")
    correct_approach: str = Field(..., description="正确的解题思路")
    similar_traps: list[str] = Field(default_factory=list, description="类似的易错点提醒")
    recommended_knowledge: list[str] = Field(default_factory=list, description="推荐复习的知识点")
    study_suggestion: str = Field(..., description="学习建议")
    ocr_text: str | None = Field(None, description="OCR识别的文本（如果是图片题）")

    @field_validator(
        "error_type_label", "root_cause", "correct_approach", "study_suggestion", "ocr_text", mode="before"
    )
    @classmethod
    def normalize_text_fields(cls, value):
        if value is None:
            return value
        if isinstance(value, list):
            return "\n".join(str(item) for item in value if item is not None)
        return str(value)

    @field_validator("similar_traps", "recommended_knowledge", mode="before")
    @classmethod
    def normalize_list_fields(cls, value):
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if item is not None]
        return [str(value)]


# ============================================
# 错题响应 Schema
# ============================================


class KnowledgeLinkBrief(BaseModel):
    """关联知识点的简要信息"""

    id: UUID
    name: str
    relevance: float = 1.0  # Default fallback
    is_primary: bool = False

    model_config = ConfigDict(from_attributes=True)


class ErrorRecordResponse(BaseModel):
    """错题详情响应"""

    id: UUID
    question_text: str | None
    question_image_url: str | None
    user_answer: str | None
    correct_answer: str | None
    subject_code: str
    chapter: str | None

    # 复习状态
    mastery_level: float
    review_count: int
    next_review_at: datetime | None
    last_reviewed_at: datetime | None

    # AI 分析 (从 JSONB 字段解析)
    latest_analysis: ErrorAnalysisResult | None = None

    cognitive_tags: list[str] = Field(default_factory=list)
    ai_analysis_summary: str | None = None

    # 关联信息 (Service 层需要手动填充)
    affected_node_id: UUID | None = None
    mastery_delta: float | None = None
    knowledge_links: list[KnowledgeLinkBrief] = Field(default_factory=list)
    suggested_concepts: list[str] = Field(default_factory=list)

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ErrorRecordListResponse(BaseModel):
    """错题列表响应"""

    items: list[ErrorRecordResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


# ============================================
# 复习相关 Schema
# ============================================


class ReviewAction(BaseModel):
    """提交复习记录 (Body)"""

    performance: ReviewPerformanceEnum
    time_spent_seconds: int | None = Field(None, ge=0, description="花费时间（秒）")


class ReviewStatsResponse(BaseModel):
    """复习统计响应"""

    total_errors: int
    mastered_count: int
    need_review_count: int
    review_streak_days: int
    subject_distribution: dict[str, int]


# ============================================
# 筛选查询 Schema
# ============================================


class ErrorQueryParams(BaseModel):
    """错题查询参数"""

    subject: SubjectEnum | None = None
    chapter: str | None = None
    node_id: str | None = None
    error_type: ErrorTypeEnum | None = None
    mastery_min: float | None = Field(None, ge=0, le=1)
    mastery_max: float | None = Field(None, ge=0, le=1)
    need_review: bool | None = None
    keyword: str | None = None
    cognitive_dimension: str | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

    @field_validator("cognitive_dimension")
    @classmethod
    def validate_cognitive_dimension(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if value not in COGNITIVE_DIMENSIONS:
            raise ValueError("Invalid cognitive dimension")
        return value
