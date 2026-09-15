"""
Seed Content Models
种子内容库模型 - 支持 few-shot 示例、预设教学内容、通用回复模板
"""
from datetime import UTC, datetime
from enum import StrEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import deferred, relationship

from app.models.base import GUID, BaseModel, HardDeleteBaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")
VectorCompat = Vector(1024).with_variant(JSON(), "sqlite")


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class LibraryCategory(StrEnum):
    """库分类枚举"""
    FEW_SHOT = "few_shot"  # Few-shot 学习示例
    TEACHING_CONTENT = "teaching_content"  # 预设教学内容
    REPLY_TEMPLATE = "reply_template"  # 通用回复模板
    CUSTOM = "custom"  # 自定义分类


class LibraryVisibility(StrEnum):
    """库可见性枚举"""
    PRIVATE = "private"  # 私有库，仅创建者可见
    PUBLIC = "public"  # 公开库，所有用户可浏览和订阅
    OFFICIAL = "official"  # 官方库，系统推荐


class ItemType(StrEnum):
    """内容项类型枚举"""
    EXAMPLE = "example"  # 学习示例
    EXERCISE = "exercise"  # 练习题
    KNOWLEDGE = "knowledge"  # 知识点
    TEMPLATE = "template"  # 回复模板
    FLASHCARD = "flashcard"  # 抽认卡


class DifficultyLevel(StrEnum):
    """难度等级枚举"""
    BEGINNER = "beginner"  # 初级
    INTERMEDIATE = "intermediate"  # 中级
    ADVANCED = "advanced"  # 高级
    EXPERT = "expert"  # 专家级


class SeedLibrary(BaseModel):
    """
    种子内容库定义表
    管理各类种子内容的集合
    """
    __tablename__ = "seed_libraries"

    # 基本信息
    name = Column(String(200), nullable=False, index=True, doc="库名称")
    description = Column(Text, nullable=True, doc="库描述")

    # 分类与可见性
    category = Column(
        String(50),
        nullable=False,
        index=True,
        doc="库分类: few_shot, teaching_content, reply_template, custom"
    )
    visibility = Column(
        String(20),
        nullable=False,
        default="private",
        index=True,
        doc="可见性: private, public, official"
    )

    # 所有权
    owner_id = Column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="创建者ID，NULL表示官方库"
    )

    # 元数据
    language = Column(String(10), nullable=False, default="zh", doc="语言代码")
    tags = Column(JSONBCompat, nullable=True, doc="标签数组，用于分类和搜索")
    extra_metadata = Column(JSONBCompat, nullable=True, doc="额外的元数据信息")

    # 官方标记
    is_official = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        doc="是否为官方库"
    )
    is_featured = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        doc="是否为精选推荐"
    )

    # 统计信息
    usage_count = Column(
        Integer,
        nullable=False,
        default=0,
        doc="使用次数统计"
    )
    quality_score = Column(
        Float,
        nullable=True,
        doc="质量评分 (0-10)"
    )

    # 关系
    items = relationship(
        "SeedItem",
        back_populates="library",
        cascade="all, delete-orphan",
        order_by="SeedItem.order_index"
    )
    subscriptions = relationship(
        "UserLibrarySubscription",
        back_populates="library",
        cascade="all, delete-orphan"
    )
    ratings = relationship(
        "SeedLibraryRating",
        back_populates="library",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<SeedLibrary(id={self.id}, name={self.name}, category={self.category})>"

    @property
    def is_visible_to_public(self) -> bool:
        """检查库是否对公众可见"""
        return self.visibility in [LibraryVisibility.PUBLIC, LibraryVisibility.OFFICIAL]

    @property
    def can_be_subscribed(self) -> bool:
        """检查库是否可被订阅"""
        return self.visibility != LibraryVisibility.PRIVATE

    def increment_usage(self) -> None:
        """增加使用计数"""
        self.usage_count = (self.usage_count or 0) + 1


class SeedItem(BaseModel):
    """
    种子内容项表
    存储具体的学习示例、练习题、知识点等
    """
    __tablename__ = "seed_items"

    # 关联
    library_id = Column(
        GUID(),
        ForeignKey("seed_libraries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="所属库ID"
    )

    # 类型
    item_type = Column(
        String(50),
        nullable=False,
        index=True,
        doc="内容类型: example, exercise, knowledge, template, flashcard"
    )

    # 内容
    title = Column(String(300), nullable=True, doc="内容标题")
    content = Column(Text, nullable=True, doc="文本内容")

    # 结构化数据 (用于存储复杂内容)
    content_data = Column(
        JSONBCompat,
        nullable=True,
        doc="结构化内容数据，如题目选项、答案解析等"
    )

    # 分类属性
    subject = Column(
        String(100),
        nullable=True,
        index=True,
        doc="学科分类"
    )
    difficulty_level = Column(
        String(20),
        nullable=True,
        index=True,
        doc="难度等级: beginner, intermediate, advanced, expert"
    )
    tags = Column(JSONBCompat, nullable=True, doc="标签数组，用于分类和搜索")

    # 向量嵌入 (用于语义搜索)
    embedding = deferred(
        Column(
            VectorCompat,
            nullable=True,
            doc="内容向量嵌入，用于语义相似度搜索"
        )
    )

    # 排序与状态
    order_index = Column(
        Integer,
        nullable=False,
        default=0,
        doc="排序索引"
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        doc="是否启用"
    )

    # 关系
    library = relationship("SeedLibrary", back_populates="items")

    def __repr__(self):
        return f"<SeedItem(id={self.id}, title={self.title}, type={self.item_type})>"

    @property
    def is_few_shot_example(self) -> bool:
        """是否为 few-shot 示例"""
        return self.item_type == ItemType.EXAMPLE

    @property
    def is_teaching_content(self) -> bool:
        """是否为教学内容"""
        return self.item_type in [ItemType.EXERCISE, ItemType.KNOWLEDGE, ItemType.FLASHCARD]

    @property
    def is_template(self) -> bool:
        """是否为回复模板"""
        return self.item_type == ItemType.TEMPLATE


class UserLibrarySubscription(BaseModel):
    """
    用户库订阅表
    管理用户对内容库的订阅关系
    """
    __tablename__ = "user_library_subscriptions"

    # 关联
    user_id = Column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="用户ID"
    )
    library_id = Column(
        GUID(),
        ForeignKey("seed_libraries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="订阅的库ID"
    )

    # 订阅状态
    is_enabled = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        doc="是否启用订阅"
    )
    priority = Column(
        Integer,
        nullable=False,
        default=0,
        doc="优先级，数值越大优先级越高"
    )
    notes = Column(Text, nullable=True, doc="用户备注")

    # 时间戳
    subscribed_at = Column(
        DateTime,
        nullable=False,
        default=lambda: _utcnow(),
        doc="订阅时间"
    )
    last_used_at = Column(
        DateTime,
        nullable=True,
        doc="最后使用时间"
    )

    # 关系
    library = relationship("SeedLibrary", back_populates="subscriptions")

    def __repr__(self):
        return f"<UserLibrarySubscription(user_id={self.user_id}, library_id={self.library_id})>"

    def mark_used(self) -> None:
        """标记为已使用"""
        self.last_used_at = _utcnow()


class SeedLibraryRating(HardDeleteBaseModel):
    """
    用户对种子库的评分
    用于计算真实用户质量反馈，并与系统评分做融合
    """

    __tablename__ = "seed_library_ratings"
    __table_args__ = (
        UniqueConstraint("user_id", "library_id", name="uq_seed_library_ratings_user_library"),
    )

    user_id = Column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="评分用户ID",
    )
    library_id = Column(
        GUID(),
        ForeignKey("seed_libraries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="种子库ID",
    )
    score = Column(
        Float,
        nullable=False,
        doc="用户评分，0-10",
    )
    comment = Column(
        Text,
        nullable=True,
        doc="用户评价说明",
    )

    library = relationship("SeedLibrary", back_populates="ratings")

    def __repr__(self):
        return (
            f"<SeedLibraryRating(user_id={self.user_id}, "
            f"library_id={self.library_id}, score={self.score})>"
        )
