"""
社群功能数据模型
Community Models - 好友系统、群组、消息、任务、加密、风控

包含:
- Friendship: 好友关系
- Group: 群组（学习小队/冲刺群）
- GroupMember: 群成员
- GroupMessage: 群消息
- GroupTask: 群任务
- GroupTaskClaim: 任务认领记录
- UserEncryptionKey: 用户加密密钥
- MessageReport: 消息举报
- MessageFavorite: 消息收藏
- BroadcastMessage: 跨群广播
- OfflineMessageQueue: 离线消息队列
"""
import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.datetime_utils import _utcnow
from app.models.base import GUID, BaseModel

# ============ 枚举类型定义 ============

class FriendshipStatus(enum.StrEnum):
    """好友关系状态"""
    PENDING = "pending"      # 待确认
    ACCEPTED = "accepted"    # 已接受
    BLOCKED = "blocked"      # 已拉黑


class GroupType(enum.StrEnum):
    """群组类型"""
    SQUAD = "squad"          # 学习小队（长期）
    SPRINT = "sprint"        # 冲刺群（短期）
    OFFICIAL = "official"    # 官方课程/考试群


class GroupRole(enum.StrEnum):
    """群组角色"""
    OWNER = "owner"          # 群主
    ADMIN = "admin"          # 管理员
    MEMBER = "member"        # 普通成员


class MessageType(enum.StrEnum):
    """消息类型"""
    TEXT = "text"                    # 普通文本
    TASK_SHARE = "task_share"        # 分享任务卡
    PLAN_SHARE = "plan_share"        # 分享计划
    FRAGMENT_SHARE = "fragment_share" # 分享认知碎片
    CAPSULE_SHARE = "capsule_share"  # 分享好奇心胶囊
    PRISM_SHARE = "prism_share"      # 分享认知棱镜模式
    FILE_SHARE = "file_share"        # 分享文件
    PROGRESS = "progress"            # 进度更新
    ACHIEVEMENT = "achievement"      # 成就达成
    CHECKIN = "checkin"              # 打卡
    SYSTEM = "system"                # 系统消息
    BROADCAST = "broadcast"          # 跨群广播


class SharedResourceType(enum.StrEnum):
    """共享资源类型"""
    PLAN = "plan"
    TASK = "task"
    KNOWLEDGE_NODE = "knowledge_node"
    SEED_LIBRARY = "seed_library"
    SEED_ITEM = "seed_item"
    COGNITIVE_FRAGMENT = "cognitive_fragment"
    CURIOSITY_CAPSULE = "curiosity_capsule"
    COGNITIVE_PRISM_PATTERN = "cognitive_prism_pattern"


class ReportReason(enum.StrEnum):
    """举报原因"""
    SPAM = "spam"                    # 垃圾信息
    HARASSMENT = "harassment"        # 骚扰
    VIOLENCE = "violence"            # 暴力内容
    HATE_SPEECH = "hate_speech"      # 仇恨言论
    MISINFORMATION = "misinformation"  # 虚假信息
    INAPPROPRIATE = "inappropriate"  # 不当内容
    OTHER = "other"                  # 其他


class ReportStatus(enum.StrEnum):
    """举报状态"""
    PENDING = "pending"              # 待处理
    REVIEWED = "reviewed"            # 已审核
    DISMISSED = "dismissed"          # 已驳回
    ACTIONED = "actioned"            # 已处理


class ModerationAction(enum.StrEnum):
    """风控处置动作"""
    WARN = "warn"                    # 警告
    MUTE = "mute"                    # 禁言
    KICK = "kick"                    # 踢出
    BAN = "ban"                      # 封禁


class OfflineMessageStatus(enum.StrEnum):
    """离线消息状态"""
    PENDING = "pending"              # 待发送
    SENT = "sent"                    # 已发送
    FAILED = "failed"                # 发送失败
    EXPIRED = "expired"              # 已过期


# ============ 好友系统 ============

class Friendship(BaseModel):
    """
    好友关系表

    设计说明：
    - 使用双向存储，A->B 和 B->A 是同一条记录
    - user_id 和 friend_id 按字符串排序存储，保证唯一性
    - 通过 status 控制关系状态
    """
    __tablename__ = "friendships"

    # 用户ID（较小的一方）
    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    # 好友ID（较大的一方）
    friend_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    # 关系状态
    status: Mapped[FriendshipStatus] = mapped_column(Enum(FriendshipStatus), default=FriendshipStatus.PENDING, nullable=False)

    # 谁发起的请求（用于pending状态时判断谁需要确认）
    initiated_by: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)

    # 匹配原因（JSON格式，记录为什么推荐这个好友）
    # 例如: {"courses": ["计算机组成原理"], "exams": ["期末考试"]}
    match_reason: Mapped[Any] = mapped_column(JSON, nullable=True)

    # 关系
    user = relationship("User", foreign_keys=[user_id])
    friend = relationship("User", foreign_keys=[friend_id])
    initiator = relationship("User", foreign_keys=[initiated_by])

    # 约束：确保不重复
    __table_args__ = (
        UniqueConstraint('user_id', 'friend_id', name='uq_friendship'),
        Index('idx_friendship_user', 'user_id'),
        Index('idx_friendship_friend', 'friend_id'),
        Index('idx_friendship_status', 'status'),
    )


# ============ 群组系统 ============

class Group(BaseModel):
    """
    群组表（学习小队 & 冲刺群）

    设计说明：
    - type 区分长期小队和短期冲刺群
    - 冲刺群有 deadline，小队没有
    - focus_tags 记录群组关注的课程/知识点
    """
    __tablename__ = "groups"

    # 基本信息
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str] = mapped_column(String(500), nullable=True)

    # 群组类型
    type: Mapped[GroupType] = mapped_column(Enum(GroupType), nullable=False)

    # 关注标签（课程/考试/知识点）
    # 例如: ["计算机组成原理", "数据结构", "算法"]
    focus_tags: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)

    # 冲刺群专用字段
    deadline: Mapped[datetime] = mapped_column(DateTime, nullable=True)  # 冲刺截止日期
    sprint_goal: Mapped[str] = mapped_column(Text, nullable=True)   # 冲刺目标描述

    # 群组设置
    max_members: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)   # 是否公开（可搜索加入）
    join_requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 群组统计（定期更新）
    total_flame_power: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 火苗总能量
    today_checkin_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tasks_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 群管理与风控
    announcement: Mapped[str | None] = mapped_column(Text, nullable=True)  # 群公告
    announcement_updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    keyword_filters: Mapped[Any] = mapped_column(JSON, nullable=True)  # 敏感词过滤列表
    mute_all: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # 全员禁言
    slow_mode_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 慢速模式（秒）

    # 关系
    members = relationship(
        "GroupMember",
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    messages = relationship(
        "GroupMessage",
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    tasks = relationship(
        "GroupTask",
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    files = relationship(
        "GroupFile",
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    __table_args__ = (
        Index('idx_group_type', 'type'),
        Index('idx_group_public', 'is_public'),
    )


class GroupMember(BaseModel):
    """
    群组成员表

    设计说明：
    - 记录用户在群组中的角色和状态
    - flame_contribution 记录该成员对群组火堆的贡献
    """
    __tablename__ = "group_members"

    group_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    # 角色
    role: Mapped[GroupRole] = mapped_column(Enum(GroupRole), default=GroupRole.MEMBER, nullable=False)

    # 成员状态
    is_muted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)      # 是否被禁言
    mute_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # 禁言截止时间
    warn_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 警告次数
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # 贡献统计
    flame_contribution: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 火苗贡献值
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    checkin_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)      # 连续打卡天数
    last_checkin_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 时间戳
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    last_active_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    # 关系
    group = relationship("Group", back_populates="members")
    user = relationship("User")

    __table_args__ = (
        # SQUAD-REJOIN：原全列唯一约束 uq_group_member(group_id, user_id) 与软删
        # 语义相克——leave/kick 软删行依然占键，重加入 INSERT 撞键被误报
        # 「已是群组成员」，退出即永久无法回归。改为活跃行部分唯一索引：
        # 同组同用户至多一行 deleted_at IS NULL 的活跃成员，软删历史行让出键位
        # 供 join_group 复活原行。谓词与全仓 not_deleted_filter() 读口径严格
        # 同域。PG/SQLite 双 where（INTAKE-IDX 先例）；存量由迁移
        # sqrejoin_20260923 收敛（全列约束下不可能有重复对，防御性预检）。
        Index(
            'uq_group_member_active',
            'group_id',
            'user_id',
            unique=True,
            postgresql_where=text('deleted_at IS NULL'),
            sqlite_where=text('deleted_at IS NULL'),
        ),
        Index('idx_member_group', 'group_id'),
        Index('idx_member_user', 'user_id'),
    )


# ============ 群消息系统 ============

class GroupMessage(BaseModel):
    """
    群消息表

    设计说明：
    - 支持多种消息类型（文本、任务分享、进度更新等）
    - content_data 用JSON存储结构化内容
    - 使用模板化消息引导健康互动氛围
    """
    __tablename__ = "group_messages"

    group_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)  # 系统消息可为空

    # 消息类型
    message_type: Mapped[MessageType] = mapped_column(Enum(MessageType), default=MessageType.TEXT, nullable=False)

    # 消息内容
    content: Mapped[str | None] = mapped_column(Text, nullable=True)  # 纯文本内容

    # 结构化内容（根据message_type不同存储不同结构）
    # TASK_SHARE: {"task_id": "xxx", "task_title": "...", "progress": 0.5}
    # PROGRESS: {"task_id": "xxx", "old_progress": 0.3, "new_progress": 0.8}
    # ACHIEVEMENT: {"achievement_type": "streak_7", "description": "连续学习7天"}
    # CHECKIN: {"flame_power": 85, "today_duration": 120, "streak": 5}
    content_data: Mapped[Any] = mapped_column(JSON, nullable=True)

    # 回复相关
    reply_to_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("group_messages.id"), nullable=True)
    thread_root_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("group_messages.id"), nullable=True, index=True)

    # 状态与协作
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reactions: Mapped[Any] = mapped_column(JSON, nullable=True)  # {"like": ["user_id", ...]}
    mention_user_ids: Mapped[Any] = mapped_column(JSON, nullable=True)  # ["user_id", ...]

    # 端到端加密
    encrypted_content: Mapped[str] = mapped_column(Text, nullable=True)  # 加密后的内容
    content_signature: Mapped[str] = mapped_column(String(512), nullable=True)  # 消息签名
    encryption_version: Mapped[int] = mapped_column(Integer, nullable=True)  # 加密版本

    # 话题与标签
    topic: Mapped[str] = mapped_column(String(100), nullable=True)  # 话题
    tags: Mapped[Any] = mapped_column(JSON, nullable=True)  # 标签列表

    # 转发
    forwarded_from_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("group_messages.id"), nullable=True)
    forward_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 关系
    group = relationship("Group", back_populates="messages")
    sender = relationship("User")
    reply_to = relationship("GroupMessage", remote_side="GroupMessage.id", foreign_keys=[reply_to_id])
    thread_root = relationship("GroupMessage", remote_side="GroupMessage.id", foreign_keys=[thread_root_id])
    forwarded_from = relationship("GroupMessage", remote_side="GroupMessage.id", foreign_keys=[forwarded_from_id])
    read_receipts = relationship(
        "GroupMessageRead",
        back_populates="message",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index('idx_message_group_time', 'group_id', 'created_at'),
        Index('idx_message_group_thread', 'group_id', 'thread_root_id', 'created_at'),
    )


class GroupMessageRead(BaseModel):
    """群消息已读回执"""

    __tablename__ = "group_message_reads"

    message_id: Mapped[Any] = mapped_column(
        GUID(),
        ForeignKey("group_messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[Any] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    read_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    message = relationship("GroupMessage", back_populates="read_receipts")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint("message_id", "user_id", name="uq_group_message_read"),
        Index("idx_group_message_read_message", "message_id", "read_at"),
        Index("idx_group_message_read_user", "user_id", "read_at"),
    )


# ============ 群任务池 ============

class GroupTask(BaseModel):
    """
    群组任务池（主要用于冲刺群）

    设计说明：
    - 群主/管理员可以创建群组共享任务
    - 成员认领任务后在个人任务系统中执行
    - 跟踪群组整体进度
    """
    __tablename__ = "group_tasks"

    group_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)

    # 任务信息
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # 关联的知识点/标签
    tags: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)

    # 任务属性
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1-5

    # 完成统计
    total_claims: Mapped[int] = mapped_column(Integer, default=0, nullable=False)      # 认领次数
    total_completions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 完成次数

    # 截止日期
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 关系
    group = relationship("Group", back_populates="tasks")
    creator = relationship("User")
    claims = relationship(
        "GroupTaskClaim",
        back_populates="group_task",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    __table_args__ = (
        Index('idx_group_task_group', 'group_id'),
    )


class GroupTaskClaim(BaseModel):
    """
    群任务认领记录

    设计说明：
    - 记录谁认领了群任务
    - 关联到用户的个人任务
    """
    __tablename__ = "group_task_claims"

    group_task_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("group_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    # 关联的个人任务（用户认领后会创建个人任务副本）
    personal_task_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("tasks.id"), nullable=True)

    # 状态
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 认领时间
    claimed_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    # 关系
    group_task = relationship("GroupTask", back_populates="claims")
    user = relationship("User")
    personal_task = relationship("Task")

    __table_args__ = (
        UniqueConstraint('group_task_id', 'user_id', name='uq_task_claim'),
        Index('idx_claim_task', 'group_task_id'),
        Index('idx_claim_user', 'user_id'),
    )


# ============ 通用共享资源 ============

class SharedResource(BaseModel):
    """
    通用共享资源表
    用于将 Plan, CognitiveFragment, Task 等分享给群组或好友
    """
    __tablename__ = "shared_resources"

    # 目标 (分享给谁)
    group_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("groups.id", ondelete="CASCADE"), nullable=True, index=True)
    target_user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True, index=True)

    # 来源
    shared_by: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)

    # 资源引用 (多态关联)
    # 注意: 需要确保 plan/task/cognitive 模型已定义或使用字符串引用避免循环导入
    # 实际运行时 SQLAlchemy 会解析
    plan_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("plans.id"), nullable=True)
    task_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("tasks.id"), nullable=True)
    knowledge_node_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("knowledge_nodes.id"), nullable=True)
    seed_library_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("seed_libraries.id"), nullable=True)
    seed_item_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("seed_items.id"), nullable=True)
    cognitive_fragment_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("cognitive_fragments.id"), nullable=True)
    curiosity_capsule_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("curiosity_capsules.id"), nullable=True)
    behavior_pattern_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("behavior_patterns.id"), nullable=True)
    card_share_record_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("card_share_records.id", ondelete="SET NULL"), nullable=True, index=True)

    # 权限与元数据
    permission: Mapped[str] = mapped_column(String(20), default="view", nullable=False)  # view, comment, edit
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)  # 分享留言

    # 计数
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=True)
    save_count: Mapped[int] = mapped_column(Integer, default=0, nullable=True)  # 被转存/fork次数
    adoption_count: Mapped[int] = mapped_column(Integer, default=0, nullable=True)
    negative_feedback_count: Mapped[int] = mapped_column(Integer, default=0, nullable=True)

    # 质量评分 (FV-22)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=True)
    quality_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)  # auto-hide when score < 0.3

    # 关系
    group = relationship("Group")
    sharer = relationship("User", foreign_keys=[shared_by])

    # 资源关系 (Lazy load to avoid circular import issues at module level if carefully handled,
    # but strictly Plan/Task should be imported. For now we assume they are available in registry)
    plan = relationship("Plan", foreign_keys=[plan_id])
    task = relationship("Task", foreign_keys=[task_id])
    knowledge_node = relationship("KnowledgeNode", foreign_keys=[knowledge_node_id])
    seed_library = relationship("SeedLibrary", foreign_keys=[seed_library_id])
    seed_item = relationship("SeedItem", foreign_keys=[seed_item_id])
    cognitive_fragment = relationship("CognitiveFragment", foreign_keys=[cognitive_fragment_id])
    curiosity_capsule = relationship("CuriosityCapsule", foreign_keys=[curiosity_capsule_id])
    behavior_pattern = relationship("BehaviorPattern", foreign_keys=[behavior_pattern_id])
    card_share_record = relationship("CardShareRecord", foreign_keys=[card_share_record_id])

    __table_args__ = (
        Index('idx_share_group', 'group_id'),
        Index('idx_share_target_user', 'target_user_id'),
        Index('idx_share_resource_plan', 'plan_id'),
        Index('idx_share_resource_knowledge_node', 'knowledge_node_id'),
        Index('idx_share_resource_seed_library', 'seed_library_id'),
        Index('idx_share_resource_seed_item', 'seed_item_id'),
        Index('idx_share_resource_capsule', 'curiosity_capsule_id'),
        Index('idx_share_resource_pattern', 'behavior_pattern_id'),
        Index('idx_share_card_share_record', 'card_share_record_id'),
    )


class SharedResourceFeedback(BaseModel):
    """
    共享资源同伴反馈表（S-04）

    设计说明：
    - 记录同伴对一次共享 artifact（task/plan/knowledge_node…）的反馈/ack。
    - 反馈**不自动**成为 mastery/证据：只有资源主人显式「采纳为成果证据」
      （adopted_at 落值 + Goal.metadata_payload['community_evidence'] 回执 +
      services/evidence 信念证据）才进入个人成长系统。
    - 撤回传播：共享被撤回（SharedResource 软删）时，活跃反馈行打 retracted_at，
      已采纳的 Goal 回执由撤回服务同步标 retracted（派生引用更新）。
    - 一人一资源一条反馈（唯一约束），重复反馈=更新 verdict/comment。
    """
    __tablename__ = "shared_resource_feedbacks"

    shared_resource_id: Mapped[Any] = mapped_column(
        GUID(), ForeignKey("shared_resources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    feedback_by: Mapped[Any] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    verdict: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="helpful | insightful | applied（封闭词表，schemas.FeedbackVerdict）",
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 采纳为 outcome evidence 的回执（仅资源主人可采纳；一条反馈至多采纳一次）
    adopted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    adopted_into_goal_id: Mapped[Any] = mapped_column(
        GUID(), ForeignKey("goals.id", ondelete="SET NULL"), nullable=True
    )

    # 撤回传播（共享撤回时由服务层落值；行保留供审计）
    retracted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    feedback_by_user = relationship("User", foreign_keys=[feedback_by], viewonly=True)

    __table_args__ = (
        UniqueConstraint("shared_resource_id", "feedback_by", name="uq_sr_feedback_resource_user"),
        Index("idx_sr_feedback_resource_active", "shared_resource_id", "retracted_at"),
    )


class CommunityOutcomeEvidence(BaseModel):
    """
    结构化社群 outcome 证据表（S-04）

    定位（与既有真源的关系，不重建）：
    - 学习飞轮数据面的**结构化**证据行：资源主人把一条同伴反馈**显式采纳**
      为 Goal outcome evidence 时落一行。Goal.metadata_payload['community_evidence']
      轨迹回执（S-03）与 services/evidence 信念面（best-effort）保持不变——
      本表是它们旁边可查询、全真实外键的结构化面，不是第三真源。
    - 反馈**永不**自动成为证据：本表唯一写入路径是采纳（adopted 状态），
      撤回传播把行置 retracted（保留审计，不物理抹除）。
    - mastery/progress 与本表零耦合（卡魂：采纳是显式动作，不自动成长）。

    字段口径：
    - feedback_id 全表唯一（一条反馈至多一条证据行——采纳幂等锚点）；
    - peer_alias 只存采纳时刻的展示别名（不存 giver id——giver 身份留在
      反馈行，证据行是 goal 主人的个人轨迹数据）；
    - status：adopted | retracted（撤回传播由服务层落值）。
    """
    __tablename__ = "community_outcome_evidence"

    goal_id: Mapped[Any] = mapped_column(
        GUID(), ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    feedback_id: Mapped[Any] = mapped_column(
        GUID(), ForeignKey("shared_resource_feedbacks.id", ondelete="CASCADE"), nullable=False
    )
    shared_resource_id: Mapped[Any] = mapped_column(
        GUID(), ForeignKey("shared_resources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    owner_id: Mapped[Any] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    verdict: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="采纳时刻的反馈词表值：helpful | insightful | applied（schemas.FeedbackVerdict）",
    )
    peer_alias: Mapped[str | None] = mapped_column(String(100), nullable=True)

    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="adopted",
        comment="adopted | retracted（撤回传播置 retracted，行保留审计）",
    )
    adopted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    retracted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("feedback_id", name="uq_coe_feedback_once"),
        Index("idx_coe_goal_status", "goal_id", "status"),
        Index("idx_coe_owner_status", "owner_id", "status"),
    )


# ============ 私聊消息系统 ============

class PrivateMessage(BaseModel):
    """
    私聊消息表

    设计说明：
    - 类似于GroupMessage，但用于好友间一对一聊天
    - receiver_id 指向接收消息的用户
    """
    __tablename__ = "private_messages"

    sender_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    receiver_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    # 消息类型
    message_type: Mapped[MessageType] = mapped_column(Enum(MessageType), default=MessageType.TEXT, nullable=False)

    # 消息内容
    content: Mapped[str | None] = mapped_column(Text, nullable=True)  # 纯文本内容

    # 结构化内容 (同 GroupMessage)
    content_data: Mapped[Any] = mapped_column(JSON, nullable=True)

    # 回复相关
    reply_to_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("private_messages.id"), nullable=True)
    thread_root_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("private_messages.id"), nullable=True, index=True)

    # 状态
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reactions: Mapped[Any] = mapped_column(JSON, nullable=True)  # {"like": ["user_id", ...]}
    mention_user_ids: Mapped[Any] = mapped_column(JSON, nullable=True)  # ["user_id", ...]

    # 端到端加密
    encrypted_content: Mapped[str] = mapped_column(Text, nullable=True)  # 加密后的内容
    content_signature: Mapped[str] = mapped_column(String(512), nullable=True)  # 消息签名
    encryption_version: Mapped[int] = mapped_column(Integer, nullable=True)  # 加密版本

    # 话题与标签
    topic: Mapped[str] = mapped_column(String(100), nullable=True)  # 话题
    tags: Mapped[Any] = mapped_column(JSON, nullable=True)  # 标签列表

    # 转发
    forwarded_from_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("private_messages.id"), nullable=True)
    forward_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 关系
    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])
    reply_to = relationship("PrivateMessage", remote_side="PrivateMessage.id", foreign_keys=[reply_to_id])
    thread_root = relationship("PrivateMessage", remote_side="PrivateMessage.id", foreign_keys=[thread_root_id])
    forwarded_from = relationship("PrivateMessage", remote_side="PrivateMessage.id", foreign_keys=[forwarded_from_id])

    __table_args__ = (
        Index('idx_private_message_conversation', 'sender_id', 'receiver_id', 'created_at'),
        Index('idx_private_message_receiver_unread', 'receiver_id', 'is_read'),
        Index('idx_private_message_thread', 'sender_id', 'receiver_id', 'thread_root_id', 'created_at'),
    )


# ============ 加密密钥系统 ============

class UserEncryptionKey(BaseModel):
    """
    用户加密密钥表

    设计说明：
    - 存储用户的公钥，用于端到端加密
    - 支持多设备，每个设备可以有独立的密钥对
    - 私钥由客户端本地保存，服务器只存储公钥
    """
    __tablename__ = "user_encryption_keys"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    public_key: Mapped[str] = mapped_column(Text, nullable=False)  # Base64 编码的公钥
    key_type: Mapped[str] = mapped_column(String(50), default="x25519", nullable=False)  # x25519, rsa, etc.
    device_id: Mapped[str] = mapped_column(String(100), nullable=True)  # 可选的设备绑定
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 关系
    user = relationship("User")

    __table_args__ = (
        Index('idx_user_encryption_keys_user', 'user_id', 'is_active'),
    )


# ============ 消息举报系统 ============

class MessageReport(BaseModel):
    """
    消息举报表

    设计说明：
    - 支持举报群消息和私聊消息
    - 记录举报原因、状态和处理结果
    """
    __tablename__ = "message_reports"

    reporter_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    group_message_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("group_messages.id", ondelete="SET NULL"), nullable=True)
    private_message_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("private_messages.id", ondelete="SET NULL"), nullable=True)

    reason: Mapped[ReportReason] = mapped_column(Enum(ReportReason), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus), default=ReportStatus.PENDING, nullable=False)

    reviewed_by: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    action_taken: Mapped[ModerationAction | None] = mapped_column(Enum(ModerationAction), nullable=True)

    # 关系
    reporter = relationship("User", foreign_keys=[reporter_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    group_message = relationship("GroupMessage")
    private_message = relationship("PrivateMessage")

    __table_args__ = (
        Index('idx_message_reports_status', 'status'),
        Index('idx_message_reports_group_msg', 'group_message_id'),
    )


# ============ 消息收藏系统 ============

class MessageFavorite(BaseModel):
    """
    消息收藏表

    设计说明：
    - 用户可以收藏群消息或私聊消息
    - 支持添加个人备注和标签
    """
    __tablename__ = "message_favorites"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    group_message_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("group_messages.id", ondelete="CASCADE"), nullable=True)
    private_message_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("private_messages.id", ondelete="CASCADE"), nullable=True)

    note: Mapped[str | None] = mapped_column(Text, nullable=True)  # 用户的个人备注
    tags: Mapped[Any] = mapped_column(JSON, nullable=True)  # 用户自定义标签

    # 关系
    user = relationship("User")
    group_message = relationship("GroupMessage")
    private_message = relationship("PrivateMessage")

    __table_args__ = (
        Index('idx_message_favorites_user', 'user_id'),
    )


# ============ 跨群广播系统 ============

class BroadcastMessage(BaseModel):
    """
    跨群广播消息表

    设计说明：
    - 允许管理员向多个群组同时发送消息
    - 记录发送状态和送达统计
    """
    __tablename__ = "broadcast_messages"

    sender_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_data: Mapped[Any] = mapped_column(JSON, nullable=True)
    target_group_ids: Mapped[Any] = mapped_column(JSON, nullable=False)  # 目标群组ID列表
    delivered_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 关系
    sender = relationship("User")


# ============ 离线消息队列 ============

class OfflineMessageQueue(BaseModel):
    """
    离线消息队列表

    设计说明：
    - 存储用户离线时发送的消息
    - 支持去重（通过 client_nonce）
    - 支持重试和过期机制
    """
    __tablename__ = "offline_message_queue"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    client_nonce: Mapped[str] = mapped_column(String(100), nullable=False)  # 客户端生成的唯一标识，用于去重
    message_type: Mapped[str] = mapped_column(String(50), nullable=False)  # group, private
    target_id: Mapped[Any] = mapped_column(GUID(), nullable=False)  # group_id 或 receiver_id
    payload: Mapped[Any] = mapped_column(JSON, nullable=False)

    status: Mapped[OfflineMessageStatus] = mapped_column(Enum(OfflineMessageStatus), default=OfflineMessageStatus.PENDING, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_retry_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # 关系
    user = relationship("User")

    __table_args__ = (
        Index('idx_offline_queue_user_status', 'user_id', 'status'),
        UniqueConstraint('user_id', 'client_nonce', name='uq_offline_queue_nonce'),
    )


# ============ 动态广场系统 (Post) ============

class Post(BaseModel):
    """
    社区动态表
    """
    __tablename__ = "posts"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=True)
    image_urls: Mapped[Any] = mapped_column(JSON, nullable=True)  # List[str]
    topic: Mapped[str] = mapped_column(String(100), nullable=True)

    # 可见性控制
    visibility: Mapped[str] = mapped_column(String(20), default="public", nullable=False) # public, friends, private

    # 统计
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=True)
    comment_count: Mapped[int] = mapped_column(Integer, default=0, nullable=True)

    # 关系
    user = relationship("User")
    likes = relationship("PostLike", back_populates="post", cascade="all, delete-orphan")


class PostLike(BaseModel):
    """
    动态点赞表
    """
    __tablename__ = "post_likes"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    post_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("posts.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    # 关系
    user = relationship("User")
    post = relationship("Post", back_populates="likes")

    __table_args__ = (
        UniqueConstraint('user_id', 'post_id', name='uq_post_like'),
        Index('idx_post_like_user', 'user_id'),
        Index('idx_post_like_post', 'post_id'),
    )


class PostComment(BaseModel):
    """动态评论表 — flat (no nesting) for MVP."""

    __tablename__ = "post_comments"

    user_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    post_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("posts.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    user = relationship("User")
    post = relationship("Post")

    __table_args__ = (
        Index("idx_post_comment_post", "post_id"),
        Index("idx_post_comment_user", "user_id"),
    )


# ============ 用户拉黑系统 ============

class UserBlock(BaseModel):
    """
    用户拉黑表

    设计说明：
    - 记录用户拉黑关系
    - 拉黑后自动解除好友关系
    - 拉黑后无法发送消息、好友请求
    - 支持软删除（解除拉黑）
    """
    __tablename__ = "user_blocks"

    blocker_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    blocked_id: Mapped[Any] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 拉黑原因
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 关系
    blocker = relationship("User", foreign_keys=[blocker_id])
    blocked = relationship("User", foreign_keys=[blocked_id])

    __table_args__ = (
        UniqueConstraint('blocker_id', 'blocked_id', name='uq_user_blocks'),
        Index('idx_user_blocks_blocker', 'blocker_id', 'deleted_at'),
        Index('idx_user_blocks_blocked', 'blocked_id', 'deleted_at'),
    )
