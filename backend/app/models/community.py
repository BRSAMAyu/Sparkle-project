"""
社群功能数据模型
Community Models - 好友系统、群组、消息、任务

包含:
- Friendship: 好友关系
- Group: 群组（学习小队/冲刺群）
- GroupMember: 群成员
- GroupMessage: 群消息
- GroupTask: 群任务
- GroupTaskClaim: 任务认领记录
"""
import enum
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    Column, String, Text, DateTime, Boolean, Integer, Float,
    ForeignKey, Enum, UniqueConstraint, Index, JSON
)
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, GUID


# ============ 枚举类型定义 ============

class FriendshipStatus(str, enum.Enum):
    """好友关系状态"""
    PENDING = "pending"      # 待确认
    ACCEPTED = "accepted"    # 已接受
    BLOCKED = "blocked"      # 已拉黑


class GroupType(str, enum.Enum):
    """群组类型"""
    SQUAD = "squad"          # 学习小队（长期）
    SPRINT = "sprint"        # 冲刺群（短期）
    OFFICIAL = "official"    # 官方课程/考试群


class GroupRole(str, enum.Enum):
    """群组角色"""
    OWNER = "owner"          # 群主
    ADMIN = "admin"          # 管理员
    MEMBER = "member"        # 普通成员


class MessageType(str, enum.Enum):
    """消息类型"""
    TEXT = "text"                    # 普通文本
    TASK_SHARE = "task_share"        # 分享任务卡
    PLAN_SHARE = "plan_share"        # 分享计划
    FRAGMENT_SHARE = "fragment_share" # 分享认知碎片
    CAPSULE_SHARE = "capsule_share"  # 分享好奇心胶囊
    PRISM_SHARE = "prism_share"      # 分享认知棱镜模式
    PROGRESS = "progress"            # 进度更新
    ACHIEVEMENT = "achievement"      # 成就达成
    CHECKIN = "checkin"              # 打卡
    SYSTEM = "system"                # 系统消息


class SharedResourceType(str, enum.Enum):
    """共享资源类型"""
    PLAN = "plan"
    TASK = "task"
    COGNITIVE_FRAGMENT = "cognitive_fragment"
    CURIOSITY_CAPSULE = "curiosity_capsule"
    COGNITIVE_PRISM_PATTERN = "cognitive_prism_pattern"


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
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    # 好友ID（较大的一方）
    friend_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    # 关系状态
    status = Column(Enum(FriendshipStatus), default=FriendshipStatus.PENDING, nullable=False)

    # 谁发起的请求（用于pending状态时判断谁需要确认）
    initiated_by = Column(GUID(), ForeignKey("users.id"), nullable=False)

    # 匹配原因（JSON格式，记录为什么推荐这个好友）
    # 例如: {"courses": ["计算机组成原理"], "exams": ["期末考试"]}
    match_reason = Column(JSON, nullable=True)

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
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # 群组类型
    type = Column(Enum(GroupType), nullable=False)

    # 关注标签（课程/考试/知识点）
    # 例如: ["计算机组成原理", "数据结构", "算法"]
    focus_tags = Column(JSON, default=list, nullable=False)

    # 冲刺群专用字段
    deadline = Column(DateTime, nullable=True)  # 冲刺截止日期
    sprint_goal = Column(Text, nullable=True)   # 冲刺目标描述

    # 群组设置
    max_members = Column(Integer, default=50, nullable=False)
    is_public = Column(Boolean, default=True, nullable=False)   # 是否公开（可搜索加入）
    join_requires_approval = Column(Boolean, default=False, nullable=False)

    # 群组统计（定期更新）
    total_flame_power = Column(Integer, default=0, nullable=False)  # 火苗总能量
    today_checkin_count = Column(Integer, default=0, nullable=False)
    total_tasks_completed = Column(Integer, default=0, nullable=False)

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

    group_id = Column(GUID(), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    # 角色
    role = Column(Enum(GroupRole), default=GroupRole.MEMBER, nullable=False)

    # 成员状态
    is_muted = Column(Boolean, default=False, nullable=False)      # 是否被禁言
    notifications_enabled = Column(Boolean, default=True, nullable=False)

    # 贡献统计
    flame_contribution = Column(Integer, default=0, nullable=False)  # 火苗贡献值
    tasks_completed = Column(Integer, default=0, nullable=False)
    checkin_streak = Column(Integer, default=0, nullable=False)      # 连续打卡天数
    last_checkin_date = Column(DateTime, nullable=True)

    # 时间戳
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_active_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    group = relationship("Group", back_populates="members")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint('group_id', 'user_id', name='uq_group_member'),
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

    group_id = Column(GUID(), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(GUID(), ForeignKey("users.id"), nullable=True)  # 系统消息可为空

    # 消息类型
    message_type = Column(Enum(MessageType), default=MessageType.TEXT, nullable=False)

    # 消息内容
    content = Column(Text, nullable=True)  # 纯文本内容

    # 结构化内容（根据message_type不同存储不同结构）
    # TASK_SHARE: {"task_id": "xxx", "task_title": "...", "progress": 0.5}
    # PROGRESS: {"task_id": "xxx", "old_progress": 0.3, "new_progress": 0.8}
    # ACHIEVEMENT: {"achievement_type": "streak_7", "description": "连续学习7天"}
    # CHECKIN: {"flame_power": 85, "today_duration": 120, "streak": 5}
    content_data = Column(JSON, nullable=True)

    # 回复相关
    reply_to_id = Column(GUID(), ForeignKey("group_messages.id"), nullable=True)
    thread_root_id = Column(GUID(), ForeignKey("group_messages.id"), nullable=True, index=True)

    # 状态与协作
    is_revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    edited_at = Column(DateTime, nullable=True)
    reactions = Column(JSON, nullable=True)  # {"like": ["user_id", ...]}
    mention_user_ids = Column(JSON, nullable=True)  # ["user_id", ...]

    # 关系
    group = relationship("Group", back_populates="messages")
    sender = relationship("User")
    reply_to = relationship("GroupMessage", remote_side="GroupMessage.id")
    thread_root = relationship("GroupMessage", remote_side="GroupMessage.id", foreign_keys=[thread_root_id])

    __table_args__ = (
        Index('idx_message_group_time', 'group_id', 'created_at'),
        Index('idx_message_group_thread', 'group_id', 'thread_root_id', 'created_at'),
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

    group_id = Column(GUID(), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by = Column(GUID(), ForeignKey("users.id"), nullable=False)

    # 任务信息
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # 关联的知识点/标签
    tags = Column(JSON, default=list, nullable=False)

    # 任务属性
    estimated_minutes = Column(Integer, default=10, nullable=False)
    difficulty = Column(Integer, default=1, nullable=False)  # 1-5

    # 完成统计
    total_claims = Column(Integer, default=0, nullable=False)      # 认领次数
    total_completions = Column(Integer, default=0, nullable=False)  # 完成次数

    # 截止日期
    due_date = Column(DateTime, nullable=True)

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

    group_task_id = Column(GUID(), ForeignKey("group_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    # 关联的个人任务（用户认领后会创建个人任务副本）
    personal_task_id = Column(GUID(), ForeignKey("tasks.id"), nullable=True)

    # 状态
    is_completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # 认领时间
    claimed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

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
    group_id = Column(GUID(), ForeignKey("groups.id", ondelete="CASCADE"), nullable=True, index=True)
    target_user_id = Column(GUID(), ForeignKey("users.id"), nullable=True, index=True)

    # 来源
    shared_by = Column(GUID(), ForeignKey("users.id"), nullable=False)

    # 资源引用 (多态关联)
    # 注意: 需要确保 plan/task/cognitive 模型已定义或使用字符串引用避免循环导入
    # 实际运行时 SQLAlchemy 会解析
    plan_id = Column(GUID(), ForeignKey("plans.id"), nullable=True)
    task_id = Column(GUID(), ForeignKey("tasks.id"), nullable=True)
    cognitive_fragment_id = Column(GUID(), ForeignKey("cognitive_fragments.id"), nullable=True)
    curiosity_capsule_id = Column(GUID(), ForeignKey("curiosity_capsules.id"), nullable=True)
    behavior_pattern_id = Column(GUID(), ForeignKey("behavior_patterns.id"), nullable=True)

    # 权限与元数据
    permission = Column(String(20), default="view", nullable=False)  # view, comment, edit
    comment = Column(Text, nullable=True)  # 分享留言

    # 计数
    view_count = Column(Integer, default=0)
    save_count = Column(Integer, default=0)  # 被转存/fork次数

    # 关系
    group = relationship("Group")
    sharer = relationship("User", foreign_keys=[shared_by])
    
    # 资源关系 (Lazy load to avoid circular import issues at module level if carefully handled, 
    # but strictly Plan/Task should be imported. For now we assume they are available in registry)
    plan = relationship("Plan", foreign_keys=[plan_id])
    task = relationship("Task", foreign_keys=[task_id])
    cognitive_fragment = relationship("CognitiveFragment", foreign_keys=[cognitive_fragment_id])
    curiosity_capsule = relationship("CuriosityCapsule", foreign_keys=[curiosity_capsule_id])
    behavior_pattern = relationship("BehaviorPattern", foreign_keys=[behavior_pattern_id])

    __table_args__ = (
        Index('idx_share_group', 'group_id'),
        Index('idx_share_target_user', 'target_user_id'),
        Index('idx_share_resource_plan', 'plan_id'),
        Index('idx_share_resource_capsule', 'curiosity_capsule_id'),
        Index('idx_share_resource_pattern', 'behavior_pattern_id'),
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

    sender_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    receiver_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)

    # 消息类型
    message_type = Column(Enum(MessageType), default=MessageType.TEXT, nullable=False)

    # 消息内容
    content = Column(Text, nullable=True)  # 纯文本内容

    # 结构化内容 (同 GroupMessage)
    content_data = Column(JSON, nullable=True)

    # 回复相关
    reply_to_id = Column(GUID(), ForeignKey("private_messages.id"), nullable=True)
    thread_root_id = Column(GUID(), ForeignKey("private_messages.id"), nullable=True, index=True)

    # 状态
    is_read = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime, nullable=True)
    is_revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    edited_at = Column(DateTime, nullable=True)
    reactions = Column(JSON, nullable=True)  # {"like": ["user_id", ...]}
    mention_user_ids = Column(JSON, nullable=True)  # ["user_id", ...]

    # 关系
    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])
    reply_to = relationship("PrivateMessage", remote_side="PrivateMessage.id")
    thread_root = relationship("PrivateMessage", remote_side="PrivateMessage.id", foreign_keys=[thread_root_id])

    __table_args__ = (
        Index('idx_private_message_conversation', 'sender_id', 'receiver_id', 'created_at'),
        Index('idx_private_message_receiver_unread', 'receiver_id', 'is_read'),
        Index('idx_private_message_thread', 'sender_id', 'receiver_id', 'thread_root_id', 'created_at'),
    )
