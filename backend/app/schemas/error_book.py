"""
错题档案相关的 Pydantic Schema
"""

from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from enum import Enum


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


# ============================================
# 错题创建/更新 Schema
# ============================================

class ErrorRecordCreate(BaseModel):
    """创建错题的请求体"""
    question_text: Optional[str] = Field(None, max_length=5000, description="题目内容")
    question_image_url: Optional[str] = Field(None, max_length=500, description="题目图片URL")
    
    user_answer: Optional[str] = Field(None, max_length=2000, description="你的错误答案")
    correct_answer: Optional[str] = Field(None, max_length=2000, description="正确答案")
    
    subject: SubjectEnum = Field(..., description="科目")
    chapter: Optional[str] = Field(None, max_length=100, description="章节（可选）")
    
    @root_validator(pre=True)
    def check_content_or_image(cls, values):
        text = values.get('question_text')
        image = values.get('question_image_url')
        if not text and not image:
            raise ValueError('题目内容和图片不能同时为空')
        return values


class ErrorRecordUpdate(BaseModel):
    """更新错题的请求体"""
    question_text: Optional[str] = Field(None, max_length=5000)
    user_answer: Optional[str] = Field(None, max_length=2000)
    correct_answer: Optional[str] = Field(None, max_length=2000)
    subject: Optional[SubjectEnum] = None
    chapter: Optional[str] = Field(None, max_length=100)
    question_image_url: Optional[str] = Field(None, max_length=500)


# ============================================
# AI 分析结果 Schema
# ============================================

class ErrorAnalysisResult(BaseModel):
    """AI 分析结果"""
    error_type: ErrorTypeEnum = Field(..., description="错因分类")
    error_type_label: str = Field(..., description="错因分类的中文标签")
    root_cause: str = Field(..., description="错误根因分析")
    correct_approach: str = Field(..., description="正确的解题思路")
    similar_traps: List[str] = Field(default_factory=list, description="类似的易错点提醒")
    recommended_knowledge: List[str] = Field(default_factory=list, description="推荐复习的知识点")
    study_suggestion: str = Field(..., description="学习建议")
    ocr_text: Optional[str] = Field(None, description="OCR识别的文本（如果是图片题）")


# ============================================
# 错题响应 Schema
# ============================================

class KnowledgeLinkBrief(BaseModel):
    """关联知识点的简要信息"""
    id: UUID
    name: str
    relevance: float = 1.0 # Default fallback
    is_primary: bool = False
    
    class Config:
        from_attributes = True


class ErrorRecordResponse(BaseModel):
    """错题详情响应"""
    id: UUID
    question_text: Optional[str]
    question_image_url: Optional[str]
    user_answer: Optional[str]
    correct_answer: Optional[str]
    subject_code: str
    chapter: Optional[str]
    
    # 复习状态
    mastery_level: float
    review_count: int
    next_review_at: Optional[datetime]
    last_reviewed_at: Optional[datetime]
    
    # AI 分析 (从 JSONB 字段解析)
    latest_analysis: Optional[ErrorAnalysisResult] = None
    
    # 关联信息 (Service 层需要手动填充)
    knowledge_links: List[KnowledgeLinkBrief] = []
    suggested_concepts: List[str] = []
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ErrorRecordListResponse(BaseModel):
    """错题列表响应"""
    items: List[ErrorRecordResponse]
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
    time_spent_seconds: Optional[int] = Field(None, ge=0, description="花费时间（秒）")


class ReviewStatsResponse(BaseModel):
    """复习统计响应"""
    total_errors: int
    mastered_count: int
    need_review_count: int
    review_streak_days: int
    subject_distribution: Dict[str, int]


# ============================================
# 筛选查询 Schema
# ============================================

class ErrorQueryParams(BaseModel):
    """错题查询参数"""
    subject: Optional[SubjectEnum] = None
    chapter: Optional[str] = None
    mastery_min: Optional[float] = Field(None, ge=0, le=1)
    mastery_max: Optional[float] = Field(None, ge=0, le=1)
    need_review: Optional[bool] = None
    keyword: Optional[str] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)