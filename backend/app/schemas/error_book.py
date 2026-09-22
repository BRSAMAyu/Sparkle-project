"""
错题档案相关的 Pydantic Schema
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ============================================
# 枚举定义
# ============================================


class SubjectEnum(StrEnum):
    """科目枚举（K12 + 大学常用科目，BP-6 扩展）

    大学新增值与 sprint pack 体系对齐：discrete_math → discrete_mathematics、
    data_structures → data_structures_algorithms、computer_networks/operating_systems
    同名 pack；calculus/linear_algebra/probability_statistics 归 mathematics pack。
    """

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
    # --- 大学常用科目（BP-6：错题本科目枚举无大学科目） ---
    DISCRETE_MATH = "discrete_math"  # 离散数学
    LINEAR_ALGEBRA = "linear_algebra"  # 线性代数
    PROBABILITY_STATISTICS = "probability_statistics"  # 概率论与数理统计
    CALCULUS = "calculus"  # 高等数学（微积分）
    DATA_STRUCTURES = "data_structures"  # 数据结构
    ALGORITHMS = "algorithms"  # 算法
    COMPUTER_NETWORKS = "computer_networks"  # 计算机网络
    OPERATING_SYSTEMS = "operating_systems"  # 操作系统
    DATABASE_SYSTEMS = "database_systems"  # 数据库系统
    OTHER = "other"


# 科目 → sprint pack key 映射（知识归位词典用；无对应 pack 的科目不出现）
SUBJECT_TO_SPRINT_PACK: dict[SubjectEnum, str] = {
    SubjectEnum.DISCRETE_MATH: "discrete_mathematics",
    SubjectEnum.DATA_STRUCTURES: "data_structures_algorithms",
    SubjectEnum.ALGORITHMS: "data_structures_algorithms",
    SubjectEnum.COMPUTER_NETWORKS: "computer_networks",
    SubjectEnum.OPERATING_SYSTEMS: "operating_systems",
    SubjectEnum.CALCULUS: "mathematics",
    SubjectEnum.LINEAR_ALGEBRA: "mathematics",
    SubjectEnum.PROBABILITY_STATISTICS: "mathematics",
    SubjectEnum.MATH: "mathematics",
}

# 归一化别名表：中文/缩写/英文变体 → SubjectEnum（校验放宽的统一入口）。
# 命中即归位；未命中的非空输入由调用方决定兜底语义（创建路径落 OTHER，不再 400）。
_SUBJECT_ALIASES: dict[str, SubjectEnum] = {
    # K12 / 既有
    "数学": SubjectEnum.MATH,
    "高数": SubjectEnum.CALCULUS,
    "高等数学": SubjectEnum.CALCULUS,
    "微积分": SubjectEnum.CALCULUS,
    "calculus": SubjectEnum.CALCULUS,
    "物理": SubjectEnum.PHYSICS,
    "化学": SubjectEnum.CHEMISTRY,
    "生物": SubjectEnum.BIOLOGY,
    "英语": SubjectEnum.ENGLISH,
    "语文": SubjectEnum.CHINESE,
    "历史": SubjectEnum.HISTORY,
    "地理": SubjectEnum.GEOGRAPHY,
    "政治": SubjectEnum.POLITICS,
    "计算机": SubjectEnum.COMPUTER,
    # 大学新增
    "离散数学": SubjectEnum.DISCRETE_MATH,
    "离散": SubjectEnum.DISCRETE_MATH,
    "discrete_math": SubjectEnum.DISCRETE_MATH,
    "discrete_mathematics": SubjectEnum.DISCRETE_MATH,
    "discrete math": SubjectEnum.DISCRETE_MATH,
    "discrete mathematics": SubjectEnum.DISCRETE_MATH,
    "线代": SubjectEnum.LINEAR_ALGEBRA,
    "线性代数": SubjectEnum.LINEAR_ALGEBRA,
    "linear_algebra": SubjectEnum.LINEAR_ALGEBRA,
    "linear algebra": SubjectEnum.LINEAR_ALGEBRA,
    "概率论": SubjectEnum.PROBABILITY_STATISTICS,
    "概率统计": SubjectEnum.PROBABILITY_STATISTICS,
    "概率论与数理统计": SubjectEnum.PROBABILITY_STATISTICS,
    "probability": SubjectEnum.PROBABILITY_STATISTICS,
    "probability_statistics": SubjectEnum.PROBABILITY_STATISTICS,
    "probability and statistics": SubjectEnum.PROBABILITY_STATISTICS,
    "数据结构": SubjectEnum.DATA_STRUCTURES,
    "数据结构与算法": SubjectEnum.DATA_STRUCTURES,
    "数据结构和算法": SubjectEnum.DATA_STRUCTURES,
    "data_structures": SubjectEnum.DATA_STRUCTURES,
    "data_structures_algorithms": SubjectEnum.DATA_STRUCTURES,
    "data structures": SubjectEnum.DATA_STRUCTURES,
    "算法": SubjectEnum.ALGORITHMS,
    "算法设计": SubjectEnum.ALGORITHMS,
    "algorithms": SubjectEnum.ALGORITHMS,
    "algorithm": SubjectEnum.ALGORITHMS,
    "计算机网络": SubjectEnum.COMPUTER_NETWORKS,
    "计网": SubjectEnum.COMPUTER_NETWORKS,
    "computer_networks": SubjectEnum.COMPUTER_NETWORKS,
    "computer networks": SubjectEnum.COMPUTER_NETWORKS,
    "操作系统": SubjectEnum.OPERATING_SYSTEMS,
    "操系": SubjectEnum.OPERATING_SYSTEMS,
    "操作系统原理": SubjectEnum.OPERATING_SYSTEMS,
    "operating_systems": SubjectEnum.OPERATING_SYSTEMS,
    "operating system": SubjectEnum.OPERATING_SYSTEMS,
    "数据库": SubjectEnum.DATABASE_SYSTEMS,
    "数据库系统": SubjectEnum.DATABASE_SYSTEMS,
    "数据库原理": SubjectEnum.DATABASE_SYSTEMS,
    "database": SubjectEnum.DATABASE_SYSTEMS,
    "database_systems": SubjectEnum.DATABASE_SYSTEMS,
}

# 紧凑形式索引（去空格/横线/下划线）："Discrete Mathematics" → discrete_math
_COMPACT_SUBJECT_ALIASES: dict[str, SubjectEnum] = {
    re.sub(r"[\s\-_]+", "", key): value for key, value in _SUBJECT_ALIASES.items()
}


def normalize_subject(raw: str | None) -> SubjectEnum | None:
    """把自由文本科目归一化到 SubjectEnum。

    规则（按确定性递减）：
    1. 空值 → None（由调用方决定默认语义）；
    2. 枚举 value 精确命中（含大小写，StrEnum 值比较）；
    3. 别名表精确命中（中文/缩写/英文变体）；
    4. 去空白/横线/下划线后的紧凑别名命中（"Discrete Mathematics" /
       "discrete-mathematics" 等）；
    5. 未识别 → None（调用方兜底；创建路径落 OTHER，不再抛 400）。
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None

    lowered = text.lower()
    try:
        return SubjectEnum(lowered)
    except ValueError:
        pass

    if text in _SUBJECT_ALIASES:
        return _SUBJECT_ALIASES[text]
    compact = re.sub(r"[\s\-_]+", "", lowered)
    if compact in _SUBJECT_ALIASES:
        return _SUBJECT_ALIASES[compact]
    return _COMPACT_SUBJECT_ALIASES.get(compact)


class ErrorTypeEnum(StrEnum):
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


class ReviewPerformanceEnum(StrEnum):
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


class ErrorLinkingHint(BaseModel):
    """错题无法关联知识点时的引导信息"""

    code: str
    message: str
    action: str | None = None


# 局部/历史脏数据的兜底标签（latest_analysis JSONB 曾被写入只有 linking_hint
# 或缺必填字段的行，见 round2/errorbook-review-500-fix.md）。
_ERROR_TYPE_LABEL_FALLBACKS: dict[str, str] = {
    ErrorTypeEnum.CONCEPT_CONFUSION.value: "概念混淆",
    ErrorTypeEnum.CALCULATION_ERROR.value: "计算错误",
    ErrorTypeEnum.READING_CARELESS.value: "粗心大意",
    ErrorTypeEnum.KNOWLEDGE_GAP.value: "知识缺口",
    ErrorTypeEnum.METHOD_WRONG.value: "方法错误",
    ErrorTypeEnum.LOGIC_ERROR.value: "逻辑错误",
    ErrorTypeEnum.MEMORY_LAPSE.value: "记忆偏差",
    ErrorTypeEnum.TIME_PRESSURE.value: "时间压力",
    ErrorTypeEnum.OTHER.value: "其他",
}
_ANALYSIS_TEXT_DEFAULTS: dict[str, str] = {
    "root_cause": "暂无错因分析",
    "correct_approach": "暂无解题思路",
    "study_suggestion": "暂无学习建议",
}


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
    linking_hint: ErrorLinkingHint | None = Field(None, description="无法关联知识节点时给前端的引导")

    @model_validator(mode="before")
    @classmethod
    def tolerate_partial_legacy_analysis(cls, data: Any) -> Any:
        """容错存量局部 latest_analysis：补齐必填字段而非让响应 500。

        写入侧已修复为落库前补齐（ErrorBookMasterySyncService）并校验 LLM JSON
        （ErrorBookService），这里兜住修复前已经写进 DB 的毒化行以及任何漏网
        的局部 dict。
        """
        if not isinstance(data, dict):
            return data
        normalized = dict(data)

        raw_error_type = normalized.get("error_type")
        try:
            error_type = ErrorTypeEnum(str(raw_error_type))
        except (TypeError, ValueError):
            error_type = ErrorTypeEnum.OTHER
        normalized["error_type"] = error_type.value

        if not str(normalized.get("error_type_label") or "").strip():
            normalized["error_type_label"] = _ERROR_TYPE_LABEL_FALLBACKS[error_type.value]

        for key, default in _ANALYSIS_TEXT_DEFAULTS.items():
            if normalized.get(key) is None or str(normalized.get(key)).strip() == "":
                normalized[key] = default

        return normalized

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


class ErrorReviewCardAction(BaseModel):
    """Action exposed by a clustered error-review card."""

    type: str = Field(description="Client action type, for example start_review or create_task")
    label: str
    route: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class ErrorClusterReviewCard(BaseModel):
    """A strategy card built from a cluster of related mistakes."""

    cluster_id: str
    title: str
    reason: str
    priority_score: float = Field(ge=0.0)
    error_count: int = Field(ge=0)
    due_count: int = Field(ge=0)
    average_mastery: float = Field(ge=0.0, le=1.0)
    subject_code: str | None = None
    chapter: str | None = None
    error_type: str | None = None
    root_cause: str | None = None
    affected_node_id: UUID | None = None
    affected_node_name: str | None = None
    representative_error_id: UUID
    error_ids: list[UUID] = Field(default_factory=list)
    review_steps: list[str] = Field(default_factory=list)
    task_card: dict[str, Any] = Field(default_factory=dict)
    actions: list[ErrorReviewCardAction] = Field(default_factory=list)


class ErrorReviewCardsResponse(BaseModel):
    """Clustered error-review cards for the reviews module."""

    cards: list[ErrorClusterReviewCard] = Field(default_factory=list)
    generated_at: datetime
    source_error_count: int = Field(ge=0)


class RemediablePattern(BaseModel):
    """A repeated error pattern that is strong enough to become a repair task."""

    id: str
    knowledge_node_id: UUID | None = None
    knowledge_node_name: str | None = None
    error_type: str
    error_type_label: str
    subject_code: str | None = None
    chapter: str | None = None
    error_count: int = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    average_mastery: float = Field(ge=0.0, le=1.0)
    suggested_duration_minutes: int = Field(ge=1)
    root_cause_summary: str | None = None
    representative_error_id: UUID
    error_ids: list[UUID] = Field(default_factory=list)
    last_seen_at: datetime


class StructuredRemediationStep(BaseModel):
    """ExecutablePlan-compatible remediation step."""

    order: int = Field(ge=1)
    title: str
    instruction: str
    duration_minutes: int = Field(ge=1)
    checkpoint: str


class TaskTemplate(BaseModel):
    """Preview payload for turning an error pattern into a task."""

    pattern_id: str
    title: str
    objective: str
    estimated_minutes: int = Field(ge=1)
    difficulty: int = Field(ge=1, le=5)
    knowledge_node_id: UUID | None = None
    error_type: str
    success_criteria: list[str] = Field(default_factory=list)
    minimum_output: str
    structured_steps: list[StructuredRemediationStep] = Field(default_factory=list)
    guide_json: dict[str, Any] = Field(default_factory=dict)
    task_payload: dict[str, Any] = Field(default_factory=dict)


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
