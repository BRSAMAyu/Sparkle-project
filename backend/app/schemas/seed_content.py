"""
Seed Content Schemas
种子内容库的 Pydantic Schema 定义
"""
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# 枚举类型定义 (与模型保持一致)
class LibraryCategoryEnum(str, Enum):
    FEW_SHOT = "few_shot"
    TEACHING_CONTENT = "teaching_content"
    REPLY_TEMPLATE = "reply_template"
    CUSTOM = "custom"


class LibraryVisibilityEnum(str, Enum):
    PRIVATE = "private"
    PUBLIC = "public"
    OFFICIAL = "official"


class ItemTypeEnum(str, Enum):
    EXAMPLE = "example"
    EXERCISE = "exercise"
    KNOWLEDGE = "knowledge"
    TEMPLATE = "template"
    FLASHCARD = "flashcard"


class DifficultyLevelEnum(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


# ============ 库相关 Schema ============

class LibraryBase(BaseModel):
    """库基础 Schema"""
    name: str = Field(..., min_length=1, max_length=200, description="库名称")
    description: str | None = Field(None, description="库描述")
    category: LibraryCategoryEnum = Field(..., description="库分类")
    language: str = Field(default="zh", min_length=2, max_length=10, description="语言代码")
    tags: list[str] | None = Field(default=None, description="标签列表")
    extra_metadata: dict[str, Any] | None = Field(default=None, description="额外元数据")


class LibraryCreate(LibraryBase):
    """创建库请求"""
    visibility: LibraryVisibilityEnum = Field(
        default=LibraryVisibilityEnum.PRIVATE,
        description="库可见性"
    )


class LibraryUpdate(BaseModel):
    """更新库请求"""
    name: str | None = Field(None, min_length=1, max_length=200, description="库名称")
    description: str | None = Field(None, description="库描述")
    category: LibraryCategoryEnum | None = Field(None, description="库分类")
    visibility: LibraryVisibilityEnum | None = Field(None, description="库可见性")
    language: str | None = Field(None, min_length=2, max_length=10, description="语言代码")
    tags: list[str] | None = Field(None, description="标签列表")
    extra_metadata: dict[str, Any] | None = Field(None, description="额外元数据")
    quality_score: float | None = Field(None, ge=0, le=10, description="质量评分 (0-10)")


class LibraryInfo(BaseModel):
    """库信息响应"""
    id: UUID = Field(..., description="库ID")
    name: str = Field(..., description="库名称")
    description: str | None = Field(None, description="库描述")
    category: LibraryCategoryEnum = Field(..., description="库分类")
    visibility: LibraryVisibilityEnum = Field(..., description="库可见性")
    owner_id: UUID | None = Field(None, description="创建者ID")
    language: str = Field(..., description="语言代码")
    tags: list[str] | None = Field(default_factory=list, description="标签列表")
    extra_metadata: dict[str, Any] | None = Field(None, description="额外元数据")
    is_official: bool = Field(default=False, description="是否为官方库")
    is_featured: bool = Field(default=False, description="是否为精选推荐")
    usage_count: int = Field(default=0, description="使用次数")
    quality_score: float | None = Field(None, description="质量评分")
    item_count: int = Field(default=0, description="内容项数量")
    subscriber_count: int = Field(default=0, description="订阅者数量")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class LibraryListParams(BaseModel):
    """库列表查询参数"""
    category: LibraryCategoryEnum | None = Field(None, description="按分类筛选")
    visibility: LibraryVisibilityEnum | None = Field(None, description="按可见性筛选")
    language: str | None = Field(None, description="按语言筛选")
    is_official: bool | None = Field(None, description="仅显示官方库")
    is_featured: bool | None = Field(None, description="仅显示精选库")
    owner_id: UUID | None = Field(None, description="按创建者筛选")
    search: str | None = Field(None, min_length=1, description="搜索关键词 (名称/描述)")
    tags: list[str] | None = Field(None, description="按标签筛选")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")
    sort_by: str = Field(default="created_at", description="排序字段")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$", description="排序方向")


# ============ 内容项相关 Schema ============

class ItemBase(BaseModel):
    """内容项基础 Schema"""
    title: str | None = Field(None, max_length=300, description="内容标题")
    content: str | None = Field(None, description="文本内容")
    content_data: dict[str, Any] | None = Field(None, description="结构化内容数据")
    subject: str | None = Field(None, max_length=100, description="学科分类")
    difficulty_level: DifficultyLevelEnum | None = Field(None, description="难度等级")
    tags: list[str] | None = Field(default=None, description="标签列表")
    order_index: int = Field(default=0, description="排序索引")


class ItemCreate(ItemBase):
    """创建内容项请求"""
    item_type: ItemTypeEnum = Field(..., description="内容类型")


class ItemUpdate(BaseModel):
    """更新内容项请求"""
    title: str | None = Field(None, max_length=300, description="内容标题")
    content: str | None = Field(None, description="文本内容")
    content_data: dict[str, Any] | None = Field(None, description="结构化内容数据")
    subject: str | None = Field(None, max_length=100, description="学科分类")
    difficulty_level: DifficultyLevelEnum | None = Field(None, description="难度等级")
    tags: list[str] | None = Field(None, description="标签列表")
    order_index: int | None = Field(None, description="排序索引")
    is_active: bool | None = Field(None, description="是否启用")


class ItemInfo(BaseModel):
    """内容项信息响应"""
    id: UUID = Field(..., description="内容项ID")
    library_id: UUID = Field(..., description="所属库ID")
    item_type: ItemTypeEnum = Field(..., description="内容类型")
    title: str | None = Field(None, description="内容标题")
    content: str | None = Field(None, description="文本内容")
    content_data: dict[str, Any] | None = Field(None, description="结构化内容数据")
    subject: str | None = Field(None, description="学科分类")
    difficulty_level: DifficultyLevelEnum | None = Field(None, description="难度等级")
    tags: list[str] | None = Field(default_factory=list, description="标签列表")
    order_index: int = Field(default=0, description="排序索引")
    is_active: bool = Field(default=True, description="是否启用")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class ItemListParams(BaseModel):
    """内容项列表查询参数"""
    library_id: UUID | None = Field(None, description="库ID")
    item_type: ItemTypeEnum | None = Field(None, description="按类型筛选")
    subject: str | None = Field(None, description="按学科筛选")
    difficulty_level: DifficultyLevelEnum | None = Field(None, description="按难度筛选")
    tags: list[str] | None = Field(None, description="按标签筛选")
    is_active: bool | None = Field(default=True, description="仅显示启用的项")
    search: str | None = Field(None, min_length=1, description="搜索关键词")
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")
    sort_by: str = Field(default="order_index", description="排序字段")
    sort_order: str = Field(default="asc", pattern="^(asc|desc)$", description="排序方向")


# ============ 订阅相关 Schema ============

class SubscriptionCreate(BaseModel):
    """创建订阅请求"""
    priority: int = Field(default=0, ge=0, le=100, description="优先级")
    notes: str | None = Field(None, description="备注")


class SubscriptionUpdate(BaseModel):
    """更新订阅请求"""
    is_enabled: bool | None = Field(None, description="是否启用")
    priority: int | None = Field(None, ge=0, le=100, description="优先级")
    notes: str | None = Field(None, description="备注")


class SubscriptionInfo(BaseModel):
    """订阅信息响应"""
    id: UUID = Field(..., description="订阅ID")
    user_id: UUID = Field(..., description="用户ID")
    library_id: UUID = Field(..., description="库ID")
    library_name: str = Field(..., description="库名称")
    is_enabled: bool = Field(default=True, description="是否启用")
    priority: int = Field(default=0, description="优先级")
    notes: str | None = Field(None, description="备注")
    subscribed_at: datetime = Field(..., description="订阅时间")
    last_used_at: datetime | None = Field(None, description="最后使用时间")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True


# ============ 查询相关 Schema ============

class ItemQueryRequest(BaseModel):
    """跨库内容查询请求"""
    query: str = Field(..., min_length=1, description="查询文本")
    categories: list[LibraryCategoryEnum] | None = Field(
        default=None,
        description="限制查询的库分类"
    )
    item_types: list[ItemTypeEnum] | None = Field(
        default=None,
        description="限制查询的内容类型"
    )
    subjects: list[str] | None = Field(default=None, description="限制查询的学科")
    difficulty_levels: list[DifficultyLevelEnum] | None = Field(
        default=None,
        description="限制查询的难度"
    )
    tags: list[str] | None = Field(None, description="限制查询的标签")
    use_subscribed_only: bool = Field(
        default=True,
        description="是否仅从订阅的库中查询"
    )
    include_official: bool = Field(
        default=True,
        description="是否包含官方库"
    )
    limit: int = Field(default=10, ge=1, le=50, description="返回数量限制")
    use_semantic_search: bool = Field(
        default=True,
        description="是否使用语义搜索"
    )


class ItemQueryResponse(BaseModel):
    """内容查询响应"""
    items: list[ItemInfo] = Field(default_factory=list, description="查询结果")
    total_count: int = Field(default=0, description="总结果数")
    query_used: str = Field(..., description="使用的查询文本")
    search_method: str = Field(default="keyword", description="搜索方法: keyword 或 semantic")


class FewShotExamplesRequest(BaseModel):
    """获取 Few-shot 示例请求"""
    subject: str | None = Field(None, description="学科筛选")
    difficulty_level: DifficultyLevelEnum | None = Field(None, description="难度筛选")
    count: int = Field(default=3, ge=1, le=10, description="需要的示例数量")
    task_type: str | None = Field(None, description="任务类型筛选")


class FewShotExample(BaseModel):
    """Few-shot 示例响应"""
    input: str = Field(..., description="示例输入")
    output: str = Field(..., description="示例输出")
    explanation: str | None = Field(None, description="解释说明")
    subject: str | None = Field(None, description="所属学科")
    difficulty_level: DifficultyLevelEnum | None = Field(None, description="难度等级")


# ============ 管理员相关 Schema ============

class PromoteToOfficialRequest(BaseModel):
    """提升为官方库请求"""
    quality_score: float | None = Field(None, ge=0, le=10, description="质量评分")
    is_featured: bool = Field(default=False, description="是否设为精选")


# ============ 通用响应 Schema ============

from app.schemas.common import PaginationMeta


class LibraryListResponse(BaseModel):
    """库列表响应"""
    success: bool = Field(default=True)
    message: str = Field(default="Success")
    data: list[LibraryInfo] = Field(default_factory=list)
    meta: PaginationMeta | None = Field(None)


class LibraryResponse(BaseModel):
    """单个库响应"""
    success: bool = Field(default=True)
    message: str = Field(default="Success")
    data: LibraryInfo | None = Field(None)


class ItemListResponse(BaseModel):
    """内容项列表响应"""
    success: bool = Field(default=True)
    message: str = Field(default="Success")
    data: list[ItemInfo] = Field(default_factory=list)
    meta: PaginationMeta | None = Field(None)


class ItemResponse(BaseModel):
    """单个内容项响应"""
    success: bool = Field(default=True)
    message: str = Field(default="Success")
    data: ItemInfo | None = Field(None)


class SubscriptionListResponse(BaseModel):
    """订阅列表响应"""
    success: bool = Field(default=True)
    message: str = Field(default="Success")
    data: list[SubscriptionInfo] = Field(default_factory=list)
    meta: PaginationMeta | None = Field(None)


class SubscriptionResponse(BaseModel):
    """单个订阅响应"""
    success: bool = Field(default=True)
    message: str = Field(default="Success")
    data: SubscriptionInfo | None = Field(None)
