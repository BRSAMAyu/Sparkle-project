# Sparkle 社群功能完整实现指南

## 一、功能概述与设计理念

根据方案设计，社群功能包含三个核心模块：

| 模块 | 定位 | 特点 |
|------|------|------|
| **好友系统** | 基础社交层 | 基于共同课程/考试/作息匹配，分享任务卡与学习进展 |
| **学习小队** | 长期目标社群 | 面向持续性目标，如"每日算法一题小队" |
| **冲刺群** | 短期临时群组 | 有明确DDL，如"计组期末冲刺群"，带倒计时与群任务池 |

### 核心设计原则

1. **任务与知识为核心**：群内互动围绕学习任务，减少无意义灌水
2. **模板引导氛围**：通过结构化的互动模板保持社群质量
3. **火苗汇聚视觉**：个体火苗在社群中汇聚成"大火堆"，增强归属感

---

## 二、数据库设计

### 2.1 ER 关系图

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   users     │────<│  friendships     │>────│     users       │
└─────────────┘     └──────────────────┘     └─────────────────┘
       │
       │ 1:N
       ▼
┌─────────────────────┐
│   group_members     │
└─────────────────────┘
       │ N:1
       ▼
┌─────────────────────┐     ┌─────────────────────┐
│      groups         │────<│   group_tasks       │
└─────────────────────┘     └─────────────────────┘
       │
       │ 1:N
       ▼
┌─────────────────────┐
│   group_messages    │
└─────────────────────┘
```

### 2.2 数据表定义

在你的 `models/` 目录下创建以下文件：

#### 文件：`models/community.py`

```python
"""
社群功能数据模型

位置：后端项目的 models/community.py
作用：定义社群相关的所有数据库表结构
依赖：SQLAlchemy, 你现有的 User 模型
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, 
    ForeignKey, Enum, UniqueConstraint, Index, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from .base import Base  # 你现有的 Base 类


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


class GroupRole(str, enum.Enum):
    """群组角色"""
    OWNER = "owner"          # 群主
    ADMIN = "admin"          # 管理员
    MEMBER = "member"        # 普通成员


class MessageType(str, enum.Enum):
    """消息类型"""
    TEXT = "text"            # 普通文本
    TASK_SHARE = "task_share"        # 分享任务卡
    PROGRESS_UPDATE = "progress"      # 进度更新
    ACHIEVEMENT = "achievement"       # 成就达成
    CHECKIN = "checkin"              # 打卡
    SYSTEM = "system"                # 系统消息


# ============ 好友系统 ============

class Friendship(Base):
    """
    好友关系表
    
    设计说明：
    - 使用双向存储，A->B 和 B->A 是同一条记录
    - user_id < friend_id 保证唯一性
    - 通过 status 控制关系状态
    """
    __tablename__ = "friendships"
    
    id = Column(Integer, primary_key=True)
    
    # 用户ID（较小的一方）
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # 好友ID（较大的一方）
    friend_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # 关系状态
    status = Column(Enum(FriendshipStatus), default=FriendshipStatus.PENDING)
    
    # 谁发起的请求（用于pending状态时判断谁需要确认）
    initiated_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # 匹配原因（JSON格式，记录为什么推荐这个好友）
    # 例如: {"courses": ["计算机组成原理"], "exams": ["期末考试"]}
    match_reason = Column(JSON, nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 关系
    user = relationship("User", foreign_keys=[user_id])
    friend = relationship("User", foreign_keys=[friend_id])
    initiator = relationship("User", foreign_keys=[initiated_by])
    
    # 约束：确保 user_id < friend_id，避免重复记录
    __table_args__ = (
        UniqueConstraint('user_id', 'friend_id', name='unique_friendship'),
        Index('idx_friendship_user', 'user_id'),
        Index('idx_friendship_friend', 'friend_id'),
    )


# ============ 群组系统 ============

class Group(Base):
    """
    群组表（学习小队 & 冲刺群）
    
    设计说明：
    - type 区分长期小队和短期冲刺群
    - 冲刺群有 deadline，小队没有
    - focus_tags 记录群组关注的课程/知识点
    """
    __tablename__ = "groups"
    
    id = Column(Integer, primary_key=True)
    
    # 基本信息
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    
    # 群组类型
    type = Column(Enum(GroupType), nullable=False)
    
    # 关注标签（课程/考试/知识点）
    # 例如: ["计算机组成原理", "数据结构", "算法"]
    focus_tags = Column(JSON, default=list)
    
    # 冲刺群专用字段
    deadline = Column(DateTime, nullable=True)  # 冲刺截止日期
    sprint_goal = Column(Text, nullable=True)   # 冲刺目标描述
    
    # 群组设置
    max_members = Column(Integer, default=50)
    is_public = Column(Boolean, default=True)   # 是否公开（可搜索加入）
    join_requires_approval = Column(Boolean, default=False)
    
    # 群组统计（定期更新）
    total_flame_power = Column(Integer, default=0)  # 火苗总能量
    today_checkin_count = Column(Integer, default=0)
    total_tasks_completed = Column(Integer, default=0)
    
    # 时间戳
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 关系
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
    messages = relationship("GroupMessage", back_populates="group", cascade="all, delete-orphan")
    tasks = relationship("GroupTask", back_populates="group", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_group_type', 'type'),
        Index('idx_group_public', 'is_public'),
    )


class GroupMember(Base):
    """
    群组成员表
    
    设计说明：
    - 记录用户在群组中的角色和状态
    - flame_contribution 记录该成员对群组火堆的贡献
    """
    __tablename__ = "group_members"
    
    id = Column(Integer, primary_key=True)
    
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # 角色
    role = Column(Enum(GroupRole), default=GroupRole.MEMBER)
    
    # 成员状态
    is_muted = Column(Boolean, default=False)      # 是否被禁言
    notifications_enabled = Column(Boolean, default=True)
    
    # 贡献统计
    flame_contribution = Column(Integer, default=0)  # 火苗贡献值
    tasks_completed = Column(Integer, default=0)
    checkin_streak = Column(Integer, default=0)      # 连续打卡天数
    last_checkin_date = Column(DateTime, nullable=True)
    
    # 时间戳
    joined_at = Column(DateTime, default=func.now())
    last_active_at = Column(DateTime, default=func.now())
    
    # 关系
    group = relationship("Group", back_populates="members")
    user = relationship("User")
    
    __table_args__ = (
        UniqueConstraint('group_id', 'user_id', name='unique_group_member'),
        Index('idx_member_group', 'group_id'),
        Index('idx_member_user', 'user_id'),
    )


# ============ 群消息系统 ============

class GroupMessage(Base):
    """
    群消息表
    
    设计说明：
    - 支持多种消息类型（文本、任务分享、进度更新等）
    - content_data 用JSON存储结构化内容
    - 使用模板化消息引导健康互动氛围
    """
    __tablename__ = "group_messages"
    
    id = Column(Integer, primary_key=True)
    
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # 消息类型
    message_type = Column(Enum(MessageType), default=MessageType.TEXT)
    
    # 消息内容
    content = Column(Text, nullable=True)  # 纯文本内容
    
    # 结构化内容（根据message_type不同存储不同结构）
    # TASK_SHARE: {"task_id": 123, "task_title": "...", "progress": 0.5}
    # PROGRESS_UPDATE: {"task_id": 123, "old_progress": 0.3, "new_progress": 0.8}
    # ACHIEVEMENT: {"achievement_type": "streak_7", "description": "连续学习7天"}
    # CHECKIN: {"flame_power": 85, "today_duration": 120}
    content_data = Column(JSON, nullable=True)
    
    # 回复相关
    reply_to_id = Column(Integer, ForeignKey("group_messages.id"), nullable=True)
    
    # 时间戳
    created_at = Column(DateTime, default=func.now())
    
    # 关系
    group = relationship("Group", back_populates="messages")
    sender = relationship("User")
    reply_to = relationship("GroupMessage", remote_side=[id])
    
    __table_args__ = (
        Index('idx_message_group_time', 'group_id', 'created_at'),
    )


# ============ 群任务池 ============

class GroupTask(Base):
    """
    群组任务池（主要用于冲刺群）
    
    设计说明：
    - 群主/管理员可以创建群组共享任务
    - 成员认领任务后在个人任务系统中执行
    - 跟踪群组整体进度
    """
    __tablename__ = "group_tasks"
    
    id = Column(Integer, primary_key=True)
    
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # 任务信息
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # 关联的知识点/标签
    tags = Column(JSON, default=list)
    
    # 任务属性
    estimated_minutes = Column(Integer, default=10)
    difficulty = Column(Integer, default=1)  # 1-5
    
    # 完成统计
    total_claims = Column(Integer, default=0)      # 认领次数
    total_completions = Column(Integer, default=0)  # 完成次数
    
    # 时间戳
    created_at = Column(DateTime, default=func.now())
    due_date = Column(DateTime, nullable=True)
    
    # 关系
    group = relationship("Group", back_populates="tasks")
    creator = relationship("User")
    claims = relationship("GroupTaskClaim", back_populates="group_task", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_group_task_group', 'group_id'),
    )


class GroupTaskClaim(Base):
    """
    群任务认领记录
    
    设计说明：
    - 记录谁认领了群任务
    - 关联到用户的个人任务
    """
    __tablename__ = "group_task_claims"
    
    id = Column(Integer, primary_key=True)
    
    group_task_id = Column(Integer, ForeignKey("group_tasks.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # 关联的个人任务（用户认领后会创建个人任务副本）
    personal_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    
    # 状态
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    
    # 时间戳
    claimed_at = Column(DateTime, default=func.now())
    
    # 关系
    group_task = relationship("GroupTask", back_populates="claims")
    user = relationship("User")
    
    __table_args__ = (
        UniqueConstraint('group_task_id', 'user_id', name='unique_task_claim'),
    )
```

### 2.3 数据库迁移脚本

创建 Alembic 迁移文件：

```bash
# 在项目根目录执行
alembic revision -m "add_community_tables"
```

#### 文件：`alembic/versions/xxx_add_community_tables.py`

```python
"""add community tables

Revision ID: xxx
Revises: previous_revision
Create Date: 2024-xx-xx
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'xxx'
down_revision = 'previous_revision'
branch_labels = None
depends_on = None


def upgrade():
    # 创建枚举类型
    friendship_status = postgresql.ENUM('pending', 'accepted', 'blocked', name='friendshipstatus')
    group_type = postgresql.ENUM('squad', 'sprint', name='grouptype')
    group_role = postgresql.ENUM('owner', 'admin', 'member', name='grouprole')
    message_type = postgresql.ENUM('text', 'task_share', 'progress', 'achievement', 'checkin', 'system', name='messagetype')
    
    friendship_status.create(op.get_bind())
    group_type.create(op.get_bind())
    group_role.create(op.get_bind())
    message_type.create(op.get_bind())
    
    # 创建 friendships 表
    op.create_table(
        'friendships',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('friend_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('status', friendship_status, default='pending'),
        sa.Column('initiated_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('match_reason', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'friend_id', name='unique_friendship')
    )
    op.create_index('idx_friendship_user', 'friendships', ['user_id'])
    op.create_index('idx_friendship_friend', 'friendships', ['friend_id'])
    
    # 创建 groups 表
    op.create_table(
        'groups',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('type', group_type, nullable=False),
        sa.Column('focus_tags', postgresql.JSON(), default=[]),
        sa.Column('deadline', sa.DateTime(), nullable=True),
        sa.Column('sprint_goal', sa.Text(), nullable=True),
        sa.Column('max_members', sa.Integer(), default=50),
        sa.Column('is_public', sa.Boolean(), default=True),
        sa.Column('join_requires_approval', sa.Boolean(), default=False),
        sa.Column('total_flame_power', sa.Integer(), default=0),
        sa.Column('today_checkin_count', sa.Integer(), default=0),
        sa.Column('total_tasks_completed', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('idx_group_type', 'groups', ['type'])
    op.create_index('idx_group_public', 'groups', ['is_public'])
    
    # 创建 group_members 表
    op.create_table(
        'group_members',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('group_id', sa.Integer(), sa.ForeignKey('groups.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('role', group_role, default='member'),
        sa.Column('is_muted', sa.Boolean(), default=False),
        sa.Column('notifications_enabled', sa.Boolean(), default=True),
        sa.Column('flame_contribution', sa.Integer(), default=0),
        sa.Column('tasks_completed', sa.Integer(), default=0),
        sa.Column('checkin_streak', sa.Integer(), default=0),
        sa.Column('last_checkin_date', sa.DateTime(), nullable=True),
        sa.Column('joined_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('last_active_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('group_id', 'user_id', name='unique_group_member')
    )
    op.create_index('idx_member_group', 'group_members', ['group_id'])
    op.create_index('idx_member_user', 'group_members', ['user_id'])
    
    # 创建 group_messages 表
    op.create_table(
        'group_messages',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('group_id', sa.Integer(), sa.ForeignKey('groups.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sender_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('message_type', message_type, default='text'),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('content_data', postgresql.JSON(), nullable=True),
        sa.Column('reply_to_id', sa.Integer(), sa.ForeignKey('group_messages.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('idx_message_group_time', 'group_messages', ['group_id', 'created_at'])
    
    # 创建 group_tasks 表
    op.create_table(
        'group_tasks',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('group_id', sa.Integer(), sa.ForeignKey('groups.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.JSON(), default=[]),
        sa.Column('estimated_minutes', sa.Integer(), default=10),
        sa.Column('difficulty', sa.Integer(), default=1),
        sa.Column('total_claims', sa.Integer(), default=0),
        sa.Column('total_completions', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('due_date', sa.DateTime(), nullable=True),
    )
    op.create_index('idx_group_task_group', 'group_tasks', ['group_id'])
    
    # 创建 group_task_claims 表
    op.create_table(
        'group_task_claims',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('group_task_id', sa.Integer(), sa.ForeignKey('group_tasks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('personal_task_id', sa.Integer(), sa.ForeignKey('tasks.id'), nullable=True),
        sa.Column('is_completed', sa.Boolean(), default=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('claimed_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('group_task_id', 'user_id', name='unique_task_claim')
    )


def downgrade():
    op.drop_table('group_task_claims')
    op.drop_table('group_tasks')
    op.drop_table('group_messages')
    op.drop_table('group_members')
    op.drop_table('groups')
    op.drop_table('friendships')
    
    # 删除枚举类型
    op.execute('DROP TYPE IF EXISTS messagetype')
    op.execute('DROP TYPE IF EXISTS grouprole')
    op.execute('DROP TYPE IF EXISTS grouptype')
    op.execute('DROP TYPE IF EXISTS friendshipstatus')
```

---

## 三、Pydantic Schemas

#### 文件：`schemas/community.py`

```python
"""
社群功能 Pydantic Schemas

位置：后端项目的 schemas/community.py
作用：定义API请求/响应的数据结构，提供数据验证
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============ 枚举类型 ============

class FriendshipStatusEnum(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    BLOCKED = "blocked"


class GroupTypeEnum(str, Enum):
    SQUAD = "squad"
    SPRINT = "sprint"


class GroupRoleEnum(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class MessageTypeEnum(str, Enum):
    TEXT = "text"
    TASK_SHARE = "task_share"
    PROGRESS = "progress"
    ACHIEVEMENT = "achievement"
    CHECKIN = "checkin"
    SYSTEM = "system"


# ============ 用户简要信息 ============

class UserBrief(BaseModel):
    """用户简要信息（用于社群场景）"""
    id: int
    nickname: str
    avatar_url: Optional[str] = None
    flame_power: int = 0  # 当前火苗能量
    
    class Config:
        from_attributes = True


# ============ 好友系统 Schemas ============

class FriendRequest(BaseModel):
    """发起好友请求"""
    target_user_id: int
    message: Optional[str] = Field(None, max_length=200)


class FriendResponse(BaseModel):
    """好友请求响应"""
    friendship_id: int
    accept: bool


class FriendshipInfo(BaseModel):
    """好友关系信息"""
    id: int
    friend: UserBrief
    status: FriendshipStatusEnum
    match_reason: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class FriendRecommendation(BaseModel):
    """好友推荐"""
    user: UserBrief
    match_score: float = Field(ge=0, le=1)
    match_reasons: List[str]  # ["同修《计算机组成原理》", "都在准备期末考试"]


# ============ 群组 Schemas ============

class GroupCreate(BaseModel):
    """创建群组"""
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    type: GroupTypeEnum
    focus_tags: List[str] = Field(default_factory=list, max_items=10)
    
    # 冲刺群专用
    deadline: Optional[datetime] = None
    sprint_goal: Optional[str] = Field(None, max_length=500)
    
    # 设置
    max_members: int = Field(default=50, ge=2, le=200)
    is_public: bool = True
    join_requires_approval: bool = False
    
    @validator('deadline')
    def validate_deadline(cls, v, values):
        if values.get('type') == GroupTypeEnum.SPRINT and v is None:
            raise ValueError('冲刺群必须设置截止日期')
        if v and v < datetime.now():
            raise ValueError('截止日期不能是过去的时间')
        return v


class GroupUpdate(BaseModel):
    """更新群组信息"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    focus_tags: Optional[List[str]] = Field(None, max_items=10)
    deadline: Optional[datetime] = None
    sprint_goal: Optional[str] = Field(None, max_length=500)
    is_public: Optional[bool] = None
    join_requires_approval: Optional[bool] = None


class GroupInfo(BaseModel):
    """群组详细信息"""
    id: int
    name: str
    description: Optional[str]
    avatar_url: Optional[str]
    type: GroupTypeEnum
    focus_tags: List[str]
    
    # 冲刺群信息
    deadline: Optional[datetime]
    sprint_goal: Optional[str]
    days_remaining: Optional[int] = None  # 距离截止日期的天数
    
    # 统计
    member_count: int
    total_flame_power: int
    today_checkin_count: int
    total_tasks_completed: int
    
    # 设置
    is_public: bool
    join_requires_approval: bool
    
    # 当前用户在群组中的角色（如果是成员）
    my_role: Optional[GroupRoleEnum] = None
    
    created_at: datetime
    
    class Config:
        from_attributes = True


class GroupListItem(BaseModel):
    """群组列表项（简要信息）"""
    id: int
    name: str
    type: GroupTypeEnum
    member_count: int
    total_flame_power: int
    deadline: Optional[datetime]
    days_remaining: Optional[int]
    focus_tags: List[str]
    
    class Config:
        from_attributes = True


# ============ 群成员 Schemas ============

class GroupMemberInfo(BaseModel):
    """群成员信息"""
    user: UserBrief
    role: GroupRoleEnum
    flame_contribution: int
    tasks_completed: int
    checkin_streak: int
    joined_at: datetime
    last_active_at: datetime
    
    class Config:
        from_attributes = True


class MemberRoleUpdate(BaseModel):
    """更新成员角色"""
    user_id: int
    new_role: GroupRoleEnum


# ============ 群消息 Schemas ============

class MessageSend(BaseModel):
    """发送消息"""
    message_type: MessageTypeEnum = MessageTypeEnum.TEXT
    content: Optional[str] = Field(None, max_length=2000)
    content_data: Optional[Dict[str, Any]] = None
    reply_to_id: Optional[int] = None
    
    @validator('content')
    def validate_content(cls, v, values):
        msg_type = values.get('message_type')
        if msg_type == MessageTypeEnum.TEXT and not v:
            raise ValueError('文本消息必须有内容')
        return v


class MessageInfo(BaseModel):
    """消息信息"""
    id: int
    sender: UserBrief
    message_type: MessageTypeEnum
    content: Optional[str]
    content_data: Optional[Dict[str, Any]]
    reply_to_id: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============ 群任务 Schemas ============

class GroupTaskCreate(BaseModel):
    """创建群任务"""
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    tags: List[str] = Field(default_factory=list, max_items=5)
    estimated_minutes: int = Field(default=10, ge=1, le=480)
    difficulty: int = Field(default=1, ge=1, le=5)
    due_date: Optional[datetime] = None


class GroupTaskInfo(BaseModel):
    """群任务信息"""
    id: int
    title: str
    description: Optional[str]
    tags: List[str]
    estimated_minutes: int
    difficulty: int
    total_claims: int
    total_completions: int
    completion_rate: float  # 完成率
    due_date: Optional[datetime]
    created_at: datetime
    creator: UserBrief
    
    # 当前用户是否已认领
    is_claimed_by_me: bool = False
    my_completion_status: Optional[bool] = None
    
    class Config:
        from_attributes = True


# ============ 打卡 Schemas ============

class CheckinRequest(BaseModel):
    """打卡请求"""
    group_id: int
    message: Optional[str] = Field(None, max_length=200)
    today_duration_minutes: int = Field(ge=0)  # 今日学习时长


class CheckinResponse(BaseModel):
    """打卡响应"""
    success: bool
    new_streak: int
    flame_earned: int
    rank_in_group: int
    group_checkin_count: int


# ============ 火堆视觉 Schemas ============

class FlameStatus(BaseModel):
    """火苗状态（用于可视化）"""
    user_id: int
    flame_power: int  # 0-100
    flame_color: str  # 颜色代码
    flame_size: float  # 相对大小 0.5-2.0
    position_x: float  # 在火堆中的位置
    position_y: float


class GroupFlameStatus(BaseModel):
    """群组火堆状态"""
    group_id: int
    total_power: int
    flames: List[FlameStatus]
    bonfire_level: int  # 火堆等级 1-5
```

---

## 四、后端服务层

#### 文件：`services/community_service.py`

```python
"""
社群功能服务层

位置：后端项目的 services/community_service.py
作用：实现社群功能的核心业务逻辑
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload
from typing import List, Optional, Tuple
from datetime import datetime, timedelta

from models.community import (
    Friendship, FriendshipStatus, 
    Group, GroupType, GroupMember, GroupRole,
    GroupMessage, MessageType,
    GroupTask, GroupTaskClaim
)
from models.user import User
from schemas.community import (
    GroupCreate, GroupUpdate, GroupTaskCreate,
    MessageSend, CheckinRequest
)


class FriendshipService:
    """好友系统服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def send_friend_request(
        self, 
        user_id: int, 
        target_id: int,
        match_reason: Optional[dict] = None
    ) -> Friendship:
        """
        发送好友请求
        
        逻辑说明：
        1. 检查是否已存在关系
        2. 确保 user_id < friend_id 以保持唯一性
        3. 创建 pending 状态的好友关系
        """
        if user_id == target_id:
            raise ValueError("不能添加自己为好友")
        
        # 标准化顺序
        small_id, large_id = min(user_id, target_id), max(user_id, target_id)
        
        # 检查是否已存在
        existing = await self.db.execute(
            select(Friendship).where(
                Friendship.user_id == small_id,
                Friendship.friend_id == large_id
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("已存在好友关系或待处理请求")
        
        friendship = Friendship(
            user_id=small_id,
            friend_id=large_id,
            initiated_by=user_id,
            status=FriendshipStatus.PENDING,
            match_reason=match_reason
        )
        self.db.add(friendship)
        await self.db.commit()
        await self.db.refresh(friendship)
        return friendship
    
    async def respond_to_request(
        self, 
        user_id: int, 
        friendship_id: int, 
        accept: bool
    ) -> Friendship:
        """
        响应好友请求
        
        逻辑说明：
        1. 验证当前用户是被请求方
        2. 更新状态为 accepted 或删除记录
        """
        friendship = await self.db.get(Friendship, friendship_id)
        if not friendship:
            raise ValueError("好友请求不存在")
        
        # 确认当前用户是被请求方
        if friendship.initiated_by == user_id:
            raise ValueError("不能响应自己发起的请求")
        
        if user_id not in (friendship.user_id, friendship.friend_id):
            raise ValueError("无权操作此请求")
        
        if accept:
            friendship.status = FriendshipStatus.ACCEPTED
        else:
            await self.db.delete(friendship)
        
        await self.db.commit()
        return friendship
    
    async def get_friends(
        self, 
        user_id: int, 
        status: FriendshipStatus = FriendshipStatus.ACCEPTED
    ) -> List[Tuple[Friendship, User]]:
        """获取好友列表"""
        result = await self.db.execute(
            select(Friendship, User).join(
                User, or_(
                    and_(Friendship.user_id == user_id, User.id == Friendship.friend_id),
                    and_(Friendship.friend_id == user_id, User.id == Friendship.user_id)
                )
            ).where(
                or_(Friendship.user_id == user_id, Friendship.friend_id == user_id),
                Friendship.status == status
            )
        )
        return result.all()
    
    async def get_pending_requests(self, user_id: int) -> List[Friendship]:
        """获取待处理的好友请求（收到的）"""
        result = await self.db.execute(
            select(Friendship).where(
                or_(Friendship.user_id == user_id, Friendship.friend_id == user_id),
                Friendship.status == FriendshipStatus.PENDING,
                Friendship.initiated_by != user_id  # 不是自己发起的
            ).options(
                selectinload(Friendship.initiator)
            )
        )
        return result.scalars().all()
    
    async def recommend_friends(
        self, 
        user_id: int, 
        limit: int = 10
    ) -> List[dict]:
        """
        推荐好友
        
        推荐逻辑：
        1. 相同课程/考试的用户
        2. 相近的学习时间段
        3. 排除已是好友或已发送请求的用户
        """
        # 这里需要根据你的 User 模型和任务/课程数据实现
        # 示例实现：基于共同课程标签
        
        # 获取当前用户的课程标签
        user = await self.db.get(User, user_id)
        if not user or not hasattr(user, 'course_tags'):
            return []
        
        # 获取已有关系的用户ID
        existing = await self.db.execute(
            select(Friendship).where(
                or_(Friendship.user_id == user_id, Friendship.friend_id == user_id)
            )
        )
        existing_ids = set()
        for f in existing.scalars():
            existing_ids.add(f.user_id)
            existing_ids.add(f.friend_id)
        existing_ids.add(user_id)
        
        # 查找有共同课程的用户（简化版本）
        # 实际实现需要更复杂的匹配算法
        result = await self.db.execute(
            select(User).where(
                User.id.notin_(existing_ids)
            ).limit(limit)
        )
        
        recommendations = []
        for candidate in result.scalars():
            recommendations.append({
                'user': candidate,
                'match_score': 0.7,  # 简化示例
                'match_reasons': ["同在学习相关课程"]
            })
        
        return recommendations


class GroupService:
    """群组服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_group(self, creator_id: int, data: GroupCreate) -> Group:
        """
        创建群组
        
        逻辑说明：
        1. 创建群组记录
        2. 将创建者设为群主
        """
        group = Group(
            name=data.name,
            description=data.description,
            type=data.type,
            focus_tags=data.focus_tags,
            deadline=data.deadline,
            sprint_goal=data.sprint_goal,
            max_members=data.max_members,
            is_public=data.is_public,
            join_requires_approval=data.join_requires_approval
        )
        self.db.add(group)
        await self.db.flush()  # 获取 group.id
        
        # 添加创建者为群主
        owner = GroupMember(
            group_id=group.id,
            user_id=creator_id,
            role=GroupRole.OWNER
        )
        self.db.add(owner)
        
        await self.db.commit()
        await self.db.refresh(group)
        return group
    
    async def get_group(self, group_id: int, user_id: Optional[int] = None) -> Optional[dict]:
        """
        获取群组详情
        
        返回包含成员数量和当前用户角色的完整信息
        """
        result = await self.db.execute(
            select(Group).where(Group.id == group_id).options(
                selectinload(Group.members)
            )
        )
        group = result.scalar_one_or_none()
        if not group:
            return None
        
        # 计算成员数量
        member_count = len(group.members)
        
        # 获取当前用户角色
        my_role = None
        if user_id:
            for member in group.members:
                if member.user_id == user_id:
                    my_role = member.role
                    break
        
        # 计算剩余天数
        days_remaining = None
        if group.deadline:
            delta = group.deadline - datetime.now()
            days_remaining = max(0, delta.days)
        
        return {
            **group.__dict__,
            'member_count': member_count,
            'my_role': my_role,
            'days_remaining': days_remaining
        }
    
    async def join_group(self, group_id: int, user_id: int) -> GroupMember:
        """加入群组"""
        # 检查群组是否存在
        group = await self.db.get(Group, group_id)
        if not group:
            raise ValueError("群组不存在")
        
        # 检查是否已是成员
        existing = await self.db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("已是群组成员")
        
        # 检查成员上限
        member_count = await self.db.execute(
            select(func.count(GroupMember.id)).where(
                GroupMember.group_id == group_id
            )
        )
        if member_count.scalar() >= group.max_members:
            raise ValueError("群组已满")
        
        member = GroupMember(
            group_id=group_id,
            user_id=user_id,
            role=GroupRole.MEMBER
        )
        self.db.add(member)
        await self.db.commit()
        await self.db.refresh(member)
        return member
    
    async def leave_group(self, group_id: int, user_id: int) -> bool:
        """退出群组"""
        result = await self.db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise ValueError("不是群组成员")
        
        if member.role == GroupRole.OWNER:
            raise ValueError("群主不能直接退出，请先转让群主")
        
        await self.db.delete(member)
        await self.db.commit()
        return True
    
    async def get_my_groups(self, user_id: int) -> List[dict]:
        """获取用户加入的所有群组"""
        result = await self.db.execute(
            select(Group, GroupMember).join(
                GroupMember, GroupMember.group_id == Group.id
            ).where(
                GroupMember.user_id == user_id
            ).options(
                selectinload(Group.members)
            )
        )
        
        groups = []
        for group, membership in result.all():
            days_remaining = None
            if group.deadline:
                delta = group.deadline - datetime.now()
                days_remaining = max(0, delta.days)
            
            groups.append({
                'id': group.id,
                'name': group.name,
                'type': group.type,
                'member_count': len(group.members),
                'total_flame_power': group.total_flame_power,
                'deadline': group.deadline,
                'days_remaining': days_remaining,
                'focus_tags': group.focus_tags,
                'my_role': membership.role
            })
        
        return groups
    
    async def search_groups(
        self, 
        keyword: Optional[str] = None,
        group_type: Optional[GroupType] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[Group]:
        """搜索公开群组"""
        query = select(Group).where(Group.is_public == True)
        
        if keyword:
            query = query.where(
                or_(
                    Group.name.ilike(f"%{keyword}%"),
                    Group.description.ilike(f"%{keyword}%")
                )
            )
        
        if group_type:
            query = query.where(Group.type == group_type)
        
        # 标签过滤（简化版本，实际可能需要更复杂的JSON查询）
        if tags:
            for tag in tags:
                query = query.where(Group.focus_tags.contains([tag]))
        
        query = query.limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()


class GroupMessageService:
    """群消息服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def send_message(
        self, 
        group_id: int, 
        sender_id: int, 
        data: MessageSend
    ) -> GroupMessage:
        """发送消息"""
        # 验证是否是群成员
        membership = await self.db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == sender_id
            )
        )
        member = membership.scalar_one_or_none()
        if not member:
            raise ValueError("不是群组成员")
        if member.is_muted:
            raise ValueError("您已被禁言")
        
        message = GroupMessage(
            group_id=group_id,
            sender_id=sender_id,
            message_type=data.message_type,
            content=data.content,
            content_data=data.content_data,
            reply_to_id=data.reply_to_id
        )
        self.db.add(message)
        
        # 更新最后活跃时间
        member.last_active_at = datetime.now()
        
        await self.db.commit()
        await self.db.refresh(message)
        return message
    
    async def get_messages(
        self, 
        group_id: int, 
        before_id: Optional[int] = None,
        limit: int = 50
    ) -> List[GroupMessage]:
        """获取群消息（分页）"""
        query = select(GroupMessage).where(
            GroupMessage.group_id == group_id
        ).options(
            selectinload(GroupMessage.sender)
        ).order_by(desc(GroupMessage.created_at))
        
        if before_id:
            query = query.where(GroupMessage.id < before_id)
        
        query = query.limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def send_system_message(
        self, 
        group_id: int, 
        content: str,
        content_data: Optional[dict] = None
    ) -> GroupMessage:
        """发送系统消息"""
        message = GroupMessage(
            group_id=group_id,
            sender_id=None,  # 系统消息没有发送者，需要修改模型允许null
            message_type=MessageType.SYSTEM,
            content=content,
            content_data=content_data
        )
        self.db.add(message)
        await self.db.commit()
        return message


class CheckinService:
    """打卡服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def checkin(
        self, 
        user_id: int, 
        data: CheckinRequest
    ) -> dict:
        """
        群组打卡
        
        逻辑说明：
        1. 验证群成员身份
        2. 检查今日是否已打卡
        3. 更新打卡连续天数
        4. 计算火苗奖励
        5. 发送打卡消息到群组
        """
        # 获取成员信息
        result = await self.db.execute(
            select(GroupMember).where(
                GroupMember.group_id == data.group_id,
                GroupMember.user_id == user_id
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise ValueError("不是群组成员")
        
        # 检查今日是否已打卡
        today = datetime.now().date()
        if member.last_checkin_date and member.last_checkin_date.date() == today:
            raise ValueError("今日已打卡")
        
        # 计算连续打卡天数
        yesterday = today - timedelta(days=1)
        if member.last_checkin_date and member.last_checkin_date.date() == yesterday:
            member.checkin_streak += 1
        else:
            member.checkin_streak = 1
        
        member.last_checkin_date = datetime.now()
        
        # 计算火苗奖励
        base_flame = 10
        streak_bonus = min(member.checkin_streak * 2, 20)  # 最多+20
        duration_bonus = min(data.today_duration_minutes // 30 * 5, 30)  # 每30分钟+5，最多+30
        flame_earned = base_flame + streak_bonus + duration_bonus
        
        member.flame_contribution += flame_earned
        
        # 更新群组统计
        group = await self.db.get(Group, data.group_id)
        group.total_flame_power += flame_earned
        group.today_checkin_count += 1
        
        # 发送打卡消息
        message = GroupMessage(
            group_id=data.group_id,
            sender_id=user_id,
            message_type=MessageType.CHECKIN,
            content=data.message,
            content_data={
                'flame_power': flame_earned,
                'streak': member.checkin_streak,
                'today_duration': data.today_duration_minutes
            }
        )
        self.db.add(message)
        
        await self.db.commit()
        
        # 计算排名
        rank_result = await self.db.execute(
            select(func.count(GroupMember.id)).where(
                GroupMember.group_id == data.group_id,
                GroupMember.flame_contribution > member.flame_contribution
            )
        )
        rank = rank_result.scalar() + 1
        
        return {
            'success': True,
            'new_streak': member.checkin_streak,
            'flame_earned': flame_earned,
            'rank_in_group': rank,
            'group_checkin_count': group.today_checkin_count
        }


class GroupTaskService:
    """群任务服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_task(
        self, 
        group_id: int, 
        creator_id: int, 
        data: GroupTaskCreate
    ) -> GroupTask:
        """创建群任务"""
        # 验证权限（群主或管理员）
        membership = await self.db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == creator_id
            )
        )
        member = membership.scalar_one_or_none()
        if not member or member.role == GroupRole.MEMBER:
            raise ValueError("只有群主或管理员可以创建群任务")
        
        task = GroupTask(
            group_id=group_id,
            created_by=creator_id,
            title=data.title,
            description=data.description,
            tags=data.tags,
            estimated_minutes=data.estimated_minutes,
            difficulty=data.difficulty,
            due_date=data.due_date
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task
    
    async def claim_task(
        self, 
        task_id: int, 
        user_id: int,
        task_service  # 你现有的任务服务，用于创建个人任务
    ) -> GroupTaskClaim:
        """
        认领群任务
        
        逻辑说明：
        1. 检查是否已认领
        2. 在个人任务系统中创建对应任务
        3. 记录认领关系
        """
        # 获取群任务
        group_task = await self.db.get(GroupTask, task_id)
        if not group_task:
            raise ValueError("任务不存在")
        
        # 检查是否已认领
        existing = await self.db.execute(
            select(GroupTaskClaim).where(
                GroupTaskClaim.group_task_id == task_id,
                GroupTaskClaim.user_id == user_id
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("已认领此任务")
        
        # 在个人任务系统中创建任务（调用你现有的任务服务）
        personal_task = await task_service.create_task(
            user_id=user_id,
            title=group_task.title,
            description=group_task.description,
            estimated_minutes=group_task.estimated_minutes,
            tags=group_task.tags,
            source_type='group_task',
            source_id=task_id
        )
        
        # 记录认领
        claim = GroupTaskClaim(
            group_task_id=task_id,
            user_id=user_id,
            personal_task_id=personal_task.id
        )
        self.db.add(claim)
        
        # 更新认领计数
        group_task.total_claims += 1
        
        await self.db.commit()
        await self.db.refresh(claim)
        return claim
    
    async def complete_task(self, claim_id: int) -> GroupTaskClaim:
        """完成群任务（由个人任务完成时触发）"""
        claim = await self.db.get(GroupTaskClaim, claim_id)
        if not claim or claim.is_completed:
            return claim
        
        claim.is_completed = True
        claim.completed_at = datetime.now()
        
        # 更新群任务完成计数
        group_task = await self.db.get(GroupTask, claim.group_task_id)
        group_task.total_completions += 1
        
        # 更新成员完成任务数
        membership = await self.db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_task.group_id,
                GroupMember.user_id == claim.user_id
            )
        )
        member = membership.scalar_one_or_none()
        if member:
            member.tasks_completed += 1
        
        await self.db.commit()
        return claim
    
    async def get_group_tasks(
        self, 
        group_id: int, 
        user_id: Optional[int] = None
    ) -> List[dict]:
        """获取群任务列表"""
        result = await self.db.execute(
            select(GroupTask).where(
                GroupTask.group_id == group_id
            ).options(
                selectinload(GroupTask.creator),
                selectinload(GroupTask.claims)
            ).order_by(desc(GroupTask.created_at))
        )
        
        tasks = []
        for task in result.scalars():
            task_dict = {
                **task.__dict__,
                'completion_rate': (
                    task.total_completions / task.total_claims 
                    if task.total_claims > 0 else 0
                ),
                'is_claimed_by_me': False,
                'my_completion_status': None
            }
            
            if user_id:
                for claim in task.claims:
                    if claim.user_id == user_id:
                        task_dict['is_claimed_by_me'] = True
                        task_dict['my_completion_status'] = claim.is_completed
                        break
            
            tasks.append(task_dict)
        
        return tasks
```

---

## 五、API 路由

#### 文件：`routers/community.py`

```python
"""
社群功能 API 路由

位置：后端项目的 routers/community.py
作用：定义社群相关的 RESTful API 端点
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from database import get_db
from auth import get_current_user
from models.user import User
from models.community import GroupType
from schemas.community import (
    # 好友
    FriendRequest, FriendResponse, FriendshipInfo, FriendRecommendation,
    # 群组
    GroupCreate, GroupUpdate, GroupInfo, GroupListItem, GroupMemberInfo,
    MemberRoleUpdate,
    # 消息
    MessageSend, MessageInfo,
    # 任务
    GroupTaskCreate, GroupTaskInfo,
    # 打卡
    CheckinRequest, CheckinResponse,
    # 火堆
    GroupFlameStatus
)
from services.community_service import (
    FriendshipService, GroupService, GroupMessageService,
    CheckinService, GroupTaskService
)

router = APIRouter(prefix="/community", tags=["社群"])


# ============ 好友系统 ============

@router.post("/friends/request", summary="发送好友请求")
async def send_friend_request(
    data: FriendRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    发送好友请求
    
    - **target_user_id**: 目标用户ID
    - **message**: 可选的请求消息
    """
    service = FriendshipService(db)
    try:
        friendship = await service.send_friend_request(
            current_user.id, 
            data.target_user_id
        )
        return {"success": True, "friendship_id": friendship.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/friends/respond", summary="响应好友请求")
async def respond_to_friend_request(
    data: FriendResponse,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """接受或拒绝好友请求"""
    service = FriendshipService(db)
    try:
        await service.respond_to_request(
            current_user.id,
            data.friendship_id,
            data.accept
        )
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/friends", response_model=List[FriendshipInfo], summary="获取好友列表")
async def get_friends(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户的好友列表"""
    service = FriendshipService(db)
    friends = await service.get_friends(current_user.id)
    return [
        FriendshipInfo(
            id=f.id,
            friend=friend,
            status=f.status,
            match_reason=f.match_reason,
            created_at=f.created_at
        )
        for f, friend in friends
    ]


@router.get("/friends/pending", summary="获取待处理的好友请求")
async def get_pending_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取收到的待处理好友请求"""
    service = FriendshipService(db)
    requests = await service.get_pending_requests(current_user.id)
    return requests


@router.get("/friends/recommendations", response_model=List[FriendRecommendation], summary="获取好友推荐")
async def get_friend_recommendations(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """基于共同课程/考试获取好友推荐"""
    service = FriendshipService(db)
    recommendations = await service.recommend_friends(current_user.id, limit)
    return recommendations


# ============ 群组管理 ============

@router.post("/groups", response_model=GroupInfo, summary="创建群组")
async def create_group(
    data: GroupCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    创建学习小队或冲刺群
    
    - **type**: squad（学习小队）或 sprint（冲刺群）
    - **deadline**: 冲刺群必填，截止日期
    """
    service = GroupService(db)
    group = await service.create_group(current_user.id, data)
    return await service.get_group(group.id, current_user.id)


@router.get("/groups/{group_id}", response_model=GroupInfo, summary="获取群组详情")
async def get_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取群组详细信息"""
    service = GroupService(db)
    group = await service.get_group(group_id, current_user.id)
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    return group


@router.post("/groups/{group_id}/join", summary="加入群组")
async def join_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """加入群组"""
    service = GroupService(db)
    try:
        await service.join_group(group_id, current_user.id)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/groups/{group_id}/leave", summary="退出群组")
async def leave_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """退出群组"""
    service = GroupService(db)
    try:
        await service.leave_group(group_id, current_user.id)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/groups", response_model=List[GroupListItem], summary="获取我的群组")
async def get_my_groups(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户加入的所有群组"""
    service = GroupService(db)
    return await service.get_my_groups(current_user.id)


@router.get("/groups/search", response_model=List[GroupListItem], summary="搜索公开群组")
async def search_groups(
    keyword: Optional[str] = None,
    group_type: Optional[GroupType] = None,
    tags: Optional[List[str]] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """搜索公开群组"""
    service = GroupService(db)
    return await service.search_groups(keyword, group_type, tags, limit)


# ============ 群消息 ============

@router.post("/groups/{group_id}/messages", response_model=MessageInfo, summary="发送群消息")
async def send_message(
    group_id: int,
    data: MessageSend,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """发送群消息"""
    service = GroupMessageService(db)
    try:
        message = await service.send_message(group_id, current_user.id, data)
        return message
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/groups/{group_id}/messages", response_model=List[MessageInfo], summary="获取群消息")
async def get_messages(
    group_id: int,
    before_id: Optional[int] = None,
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取群消息（分页）"""
    service = GroupMessageService(db)
    return await service.get_messages(group_id, before_id, limit)


# ============ 打卡 ============

@router.post("/checkin", response_model=CheckinResponse, summary="群组打卡")
async def checkin(
    data: CheckinRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    在群组中打卡
    
    - **today_duration_minutes**: 今日学习时长（分钟）
    - **message**: 可选的打卡留言
    """
    service = CheckinService(db)
    try:
        result = await service.checkin(current_user.id, data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============ 群任务 ============

@router.post("/groups/{group_id}/tasks", response_model=GroupTaskInfo, summary="创建群任务")
async def create_group_task(
    group_id: int,
    data: GroupTaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建群任务（仅群主/管理员）"""
    service = GroupTaskService(db)
    try:
        task = await service.create_task(group_id, current_user.id, data)
        return task
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/groups/{group_id}/tasks", response_model=List[GroupTaskInfo], summary="获取群任务列表")
async def get_group_tasks(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取群组的任务列表"""
    service = GroupTaskService(db)
    return await service.get_group_tasks(group_id, current_user.id)


@router.post("/tasks/{task_id}/claim", summary="认领群任务")
async def claim_group_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """认领群任务，会在个人任务系统中创建对应任务"""
    service = GroupTaskService(db)
    # 注意：这里需要注入你现有的 TaskService
    # from services.task_service import TaskService
    # task_service = TaskService(db)
    try:
        claim = await service.claim_task(task_id, current_user.id, task_service=None)
        return {"success": True, "claim_id": claim.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============ 火堆状态 ============

@router.get("/groups/{group_id}/flame", response_model=GroupFlameStatus, summary="获取群组火堆状态")
async def get_group_flame_status(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取群组火堆可视化数据
    
    返回所有成员的火苗状态，用于渲染火堆动画
    """
    # 获取群组成员的火苗数据
    service = GroupService(db)
    group = await service.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    
    # 这里需要实现火苗位置计算逻辑
    # 简化示例
    flames = []
    # ... 计算每个成员的火苗状态
    
    bonfire_level = min(5, group['total_flame_power'] // 1000 + 1)
    
    return GroupFlameStatus(
        group_id=group_id,
        total_power=group['total_flame_power'],
        flames=flames,
        bonfire_level=bonfire_level
    )
```

---

## 六、LLM 工具集成

根据你的 Agent Workflow 系统，需要将社群功能暴露为 LLM 可调用的工具。

#### 文件：`tools/community_tools.py`

```python
"""
社群功能 LLM 工具

位置：后端项目的 tools/community_tools.py
作用：定义可被 LLM 调用的社群操作工具
"""

from typing import Optional, List
from pydantic import BaseModel, Field


# ============ 工具定义 ============

class CreateSprintGroupTool(BaseModel):
    """创建冲刺群工具"""
    
    class Input(BaseModel):
        name: str = Field(..., description="群组名称，如'计组期末冲刺群'")
        deadline: str = Field(..., description="截止日期，ISO格式，如'2024-01-15T00:00:00'")
        sprint_goal: str = Field(..., description="冲刺目标描述")
        focus_tags: List[str] = Field(default_factory=list, description="关注的课程/知识点标签")
    
    name = "create_sprint_group"
    description = "当用户提到考试、DDL或需要集中冲刺时，帮助创建一个冲刺群"
    
    @staticmethod
    async def execute(input_data: Input, user_id: int, db) -> dict:
        from services.community_service import GroupService
        from schemas.community import GroupCreate, GroupTypeEnum
        from datetime import datetime
        
        service = GroupService(db)
        data = GroupCreate(
            name=input_data.name,
            type=GroupTypeEnum.SPRINT,
            deadline=datetime.fromisoformat(input_data.deadline),
            sprint_goal=input_data.sprint_goal,
            focus_tags=input_data.focus_tags
        )
        group = await service.create_group(user_id, data)
        
        return {
            "success": True,
            "message": f"已创建冲刺群「{group.name}」，距离截止日期还有 X 天",
            "group_id": group.id
        }


class InviteToGroupTool(BaseModel):
    """邀请好友加入群组工具"""
    
    class Input(BaseModel):
        group_id: int = Field(..., description="群组ID")
        friend_ids: List[int] = Field(..., description="要邀请的好友ID列表")
    
    name = "invite_to_group"
    description = "邀请好友加入学习小队或冲刺群"


class ShareProgressTool(BaseModel):
    """分享学习进度工具"""
    
    class Input(BaseModel):
        group_id: int = Field(..., description="群组ID")
        task_id: int = Field(..., description="任务ID")
        message: Optional[str] = Field(None, description="附加消息")
    
    name = "share_progress"
    description = "在群组中分享任务完成进度"
    
    @staticmethod
    async def execute(input_data: Input, user_id: int, db) -> dict:
        from services.community_service import GroupMessageService
        from schemas.community import MessageSend, MessageTypeEnum
        
        service = GroupMessageService(db)
        
        # 获取任务进度信息
        # task = await get_task(input_data.task_id)
        
        data = MessageSend(
            message_type=MessageTypeEnum.PROGRESS,
            content=input_data.message,
            content_data={
                "task_id": input_data.task_id,
                # "task_title": task.title,
                # "progress": task.progress
            }
        )
        
        await service.send_message(input_data.group_id, user_id, data)
        
        return {
            "success": True,
            "message": "已在群组中分享你的学习进度"
        }


class GroupCheckinTool(BaseModel):
    """群组打卡工具"""
    
    class Input(BaseModel):
        group_id: int = Field(..., description="群组ID")
        message: Optional[str] = Field(None, description="打卡留言")
    
    name = "group_checkin"
    description = "在群组中打卡，分享今日学习状态"
    
    @staticmethod
    async def execute(input_data: Input, user_id: int, db) -> dict:
        from services.community_service import CheckinService
        from schemas.community import CheckinRequest
        
        # 获取今日学习时长
        # today_duration = await get_today_study_duration(user_id)
        today_duration = 60  # 示例
        
        service = CheckinService(db)
        data = CheckinRequest(
            group_id=input_data.group_id,
            message=input_data.message,
            today_duration_minutes=today_duration
        )
        
        result = await service.checkin(user_id, data)
        
        return {
            "success": True,
            "message": f"打卡成功！连续打卡 {result['new_streak']} 天，获得 {result['flame_earned']} 点火苗能量",
            "streak": result['new_streak'],
            "flame_earned": result['flame_earned'],
            "rank": result['rank_in_group']
        }


# ============ 工具注册表 ============

COMMUNITY_TOOLS = [
    CreateSprintGroupTool,
    InviteToGroupTool,
    ShareProgressTool,
    GroupCheckinTool,
]


def get_community_tools_schema():
    """获取社群工具的 OpenAI Function Calling 格式 schema"""
    tools = []
    for tool_class in COMMUNITY_TOOLS:
        tools.append({
            "type": "function",
            "function": {
                "name": tool_class.name,
                "description": tool_class.description,
                "parameters": tool_class.Input.model_json_schema()
            }
        })
    return tools
```

---

## 七、Flutter 前端实现

### 7.1 目录结构

```
lib/
├── features/
│   └── community/
│       ├── models/
│       │   ├── friendship.dart
│       │   ├── group.dart
│       │   ├── message.dart
│       │   └── group_task.dart
│       ├── providers/
│       │   ├── friends_provider.dart
│       │   ├── groups_provider.dart
│       │   └── chat_provider.dart
│       ├── services/
│       │   └── community_api.dart
│       ├── widgets/
│       │   ├── flame_avatar.dart
│       │   ├── bonfire_animation.dart
│       │   ├── message_bubble.dart
│       │   ├── checkin_card.dart
│       │   └── group_task_card.dart
│       └── screens/
│           ├── friends_screen.dart
│           ├── group_list_screen.dart
│           ├── group_detail_screen.dart
│           ├── group_chat_screen.dart
│           └── create_group_screen.dart
```

### 7.2 数据模型

#### 文件：`lib/features/community/models/group.dart`

```dart
/// 群组数据模型
/// 
/// 位置：Flutter 项目的 lib/features/community/models/group.dart
/// 作用：定义群组相关的数据结构

import 'package:freezed_annotation/freezed_annotation.dart';

part 'group.freezed.dart';
part 'group.g.dart';

/// 群组类型
enum GroupType {
  @JsonValue('squad')
  squad,  // 学习小队
  @JsonValue('sprint')
  sprint, // 冲刺群
}

/// 群组角色
enum GroupRole {
  @JsonValue('owner')
  owner,
  @JsonValue('admin')
  admin,
  @JsonValue('member')
  member,
}

/// 群组信息
@freezed
class GroupInfo with _$GroupInfo {
  const factory GroupInfo({
    required int id,
    required String name,
    String? description,
    String? avatarUrl,
    required GroupType type,
    required List<String> focusTags,
    DateTime? deadline,
    String? sprintGoal,
    int? daysRemaining,
    required int memberCount,
    required int totalFlamePower,
    required int todayCheckinCount,
    required int totalTasksCompleted,
    required bool isPublic,
    required bool joinRequiresApproval,
    GroupRole? myRole,
    required DateTime createdAt,
  }) = _GroupInfo;

  factory GroupInfo.fromJson(Map<String, dynamic> json) =>
      _$GroupInfoFromJson(json);
}

/// 群组列表项
@freezed
class GroupListItem with _$GroupListItem {
  const factory GroupListItem({
    required int id,
    required String name,
    required GroupType type,
    required int memberCount,
    required int totalFlamePower,
    DateTime? deadline,
    int? daysRemaining,
    required List<String> focusTags,
  }) = _GroupListItem;

  factory GroupListItem.fromJson(Map<String, dynamic> json) =>
      _$GroupListItemFromJson(json);
}

/// 群成员信息
@freezed
class GroupMemberInfo with _$GroupMemberInfo {
  const factory GroupMemberInfo({
    required UserBrief user,
    required GroupRole role,
    required int flameContribution,
    required int tasksCompleted,
    required int checkinStreak,
    required DateTime joinedAt,
    required DateTime lastActiveAt,
  }) = _GroupMemberInfo;

  factory GroupMemberInfo.fromJson(Map<String, dynamic> json) =>
      _$GroupMemberInfoFromJson(json);
}

/// 用户简要信息
@freezed
class UserBrief with _$UserBrief {
  const factory UserBrief({
    required int id,
    required String nickname,
    String? avatarUrl,
    @Default(0) int flamePower,
  }) = _UserBrief;

  factory UserBrief.fromJson(Map<String, dynamic> json) =>
      _$UserBriefFromJson(json);
}
```

### 7.3 API 服务

#### 文件：`lib/features/community/services/community_api.dart`

```dart
/// 社群 API 服务
/// 
/// 位置：Flutter 项目的 lib/features/community/services/community_api.dart
/// 作用：封装社群功能的 HTTP 请求

import 'package:dio/dio.dart';
import '../models/group.dart';
import '../models/message.dart';

class CommunityApi {
  final Dio _dio;
  
  CommunityApi(this._dio);
  
  // ============ 好友系统 ============
  
  /// 获取好友列表
  Future<List<FriendshipInfo>> getFriends() async {
    final response = await _dio.get('/community/friends');
    return (response.data as List)
        .map((e) => FriendshipInfo.fromJson(e))
        .toList();
  }
  
  /// 发送好友请求
  Future<void> sendFriendRequest(int targetUserId, {String? message}) async {
    await _dio.post('/community/friends/request', data: {
      'target_user_id': targetUserId,
      'message': message,
    });
  }
  
  /// 响应好友请求
  Future<void> respondToRequest(int friendshipId, bool accept) async {
    await _dio.post('/community/friends/respond', data: {
      'friendship_id': friendshipId,
      'accept': accept,
    });
  }
  
  /// 获取好友推荐
  Future<List<FriendRecommendation>> getFriendRecommendations({
    int limit = 10,
  }) async {
    final response = await _dio.get('/community/friends/recommendations', 
        queryParameters: {'limit': limit});
    return (response.data as List)
        .map((e) => FriendRecommendation.fromJson(e))
        .toList();
  }
  
  // ============ 群组管理 ============
  
  /// 创建群组
  Future<GroupInfo> createGroup({
    required String name,
    required GroupType type,
    String? description,
    List<String> focusTags = const [],
    DateTime? deadline,
    String? sprintGoal,
    int maxMembers = 50,
    bool isPublic = true,
  }) async {
    final response = await _dio.post('/community/groups', data: {
      'name': name,
      'type': type.name,
      'description': description,
      'focus_tags': focusTags,
      'deadline': deadline?.toIso8601String(),
      'sprint_goal': sprintGoal,
      'max_members': maxMembers,
      'is_public': isPublic,
    });
    return GroupInfo.fromJson(response.data);
  }
  
  /// 获取群组详情
  Future<GroupInfo> getGroup(int groupId) async {
    final response = await _dio.get('/community/groups/$groupId');
    return GroupInfo.fromJson(response.data);
  }
  
  /// 获取我的群组列表
  Future<List<GroupListItem>> getMyGroups() async {
    final response = await _dio.get('/community/groups');
    return (response.data as List)
        .map((e) => GroupListItem.fromJson(e))
        .toList();
  }
  
  /// 搜索公开群组
  Future<List<GroupListItem>> searchGroups({
    String? keyword,
    GroupType? type,
    List<String>? tags,
    int limit = 20,
  }) async {
    final response = await _dio.get('/community/groups/search', 
        queryParameters: {
          if (keyword != null) 'keyword': keyword,
          if (type != null) 'group_type': type.name,
          if (tags != null) 'tags': tags,
          'limit': limit,
        });
    return (response.data as List)
        .map((e) => GroupListItem.fromJson(e))
        .toList();
  }
  
  /// 加入群组
  Future<void> joinGroup(int groupId) async {
    await _dio.post('/community/groups/$groupId/join');
  }
  
  /// 退出群组
  Future<void> leaveGroup(int groupId) async {
    await _dio.post('/community/groups/$groupId/leave');
  }
  
  // ============ 群消息 ============
  
  /// 获取群消息
  Future<List<MessageInfo>> getMessages(
    int groupId, {
    int? beforeId,
    int limit = 50,
  }) async {
    final response = await _dio.get('/community/groups/$groupId/messages',
        queryParameters: {
          if (beforeId != null) 'before_id': beforeId,
          'limit': limit,
        });
    return (response.data as List)
        .map((e) => MessageInfo.fromJson(e))
        .toList();
  }
  
  /// 发送消息
  Future<MessageInfo> sendMessage(
    int groupId, {
    required MessageType type,
    String? content,
    Map<String, dynamic>? contentData,
    int? replyToId,
  }) async {
    final response = await _dio.post('/community/groups/$groupId/messages',
        data: {
          'message_type': type.name,
          'content': content,
          'content_data': contentData,
          'reply_to_id': replyToId,
        });
    return MessageInfo.fromJson(response.data);
  }
  
  // ============ 打卡 ============
  
  /// 群组打卡
  Future<CheckinResponse> checkin(
    int groupId, {
    required int todayDurationMinutes,
    String? message,
  }) async {
    final response = await _dio.post('/community/checkin', data: {
      'group_id': groupId,
      'today_duration_minutes': todayDurationMinutes,
      'message': message,
    });
    return CheckinResponse.fromJson(response.data);
  }
  
  // ============ 群任务 ============
  
  /// 获取群任务列表
  Future<List<GroupTaskInfo>> getGroupTasks(int groupId) async {
    final response = await _dio.get('/community/groups/$groupId/tasks');
    return (response.data as List)
        .map((e) => GroupTaskInfo.fromJson(e))
        .toList();
  }
  
  /// 认领群任务
  Future<void> claimTask(int taskId) async {
    await _dio.post('/community/tasks/$taskId/claim');
  }
  
  // ============ 火堆状态 ============
  
  /// 获取群组火堆状态
  Future<GroupFlameStatus> getFlameStatus(int groupId) async {
    final response = await _dio.get('/community/groups/$groupId/flame');
    return GroupFlameStatus.fromJson(response.data);
  }
}
```

### 7.4 状态管理 (Riverpod)

#### 文件：`lib/features/community/providers/groups_provider.dart`

```dart
/// 群组状态管理
/// 
/// 位置：Flutter 项目的 lib/features/community/providers/groups_provider.dart
/// 作用：管理群组相关的状态和业务逻辑

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/group.dart';
import '../services/community_api.dart';

/// 我的群组列表 Provider
final myGroupsProvider = AsyncNotifierProvider<MyGroupsNotifier, List<GroupListItem>>(() {
  return MyGroupsNotifier();
});

class MyGroupsNotifier extends AsyncNotifier<List<GroupListItem>> {
  @override
  Future<List<GroupListItem>> build() async {
    final api = ref.watch(communityApiProvider);
    return await api.getMyGroups();
  }
  
  /// 刷新群组列表
  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() async {
      final api = ref.read(communityApiProvider);
      return await api.getMyGroups();
    });
  }
  
  /// 创建群组
  Future<GroupInfo> createGroup({
    required String name,
    required GroupType type,
    String? description,
    List<String> focusTags = const [],
    DateTime? deadline,
    String? sprintGoal,
  }) async {
    final api = ref.read(communityApiProvider);
    final group = await api.createGroup(
      name: name,
      type: type,
      description: description,
      focusTags: focusTags,
      deadline: deadline,
      sprintGoal: sprintGoal,
    );
    
    // 刷新列表
    await refresh();
    
    return group;
  }
  
  /// 加入群组
  Future<void> joinGroup(int groupId) async {
    final api = ref.read(communityApiProvider);
    await api.joinGroup(groupId);
    await refresh();
  }
  
  /// 退出群组
  Future<void> leaveGroup(int groupId) async {
    final api = ref.read(communityApiProvider);
    await api.leaveGroup(groupId);
    await refresh();
  }
}

/// 群组详情 Provider (Family)
final groupDetailProvider = AsyncNotifierProvider.family<GroupDetailNotifier, GroupInfo, int>(() {
  return GroupDetailNotifier();
});

class GroupDetailNotifier extends FamilyAsyncNotifier<GroupInfo, int> {
  @override
  Future<GroupInfo> build(int groupId) async {
    final api = ref.watch(communityApiProvider);
    return await api.getGroup(groupId);
  }
  
  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() async {
      final api = ref.read(communityApiProvider);
      return await api.getGroup(arg);
    });
  }
}

/// 群组搜索 Provider
final groupSearchProvider = StateNotifierProvider<GroupSearchNotifier, AsyncValue<List<GroupListItem>>>((ref) {
  return GroupSearchNotifier(ref);
});

class GroupSearchNotifier extends StateNotifier<AsyncValue<List<GroupListItem>>> {
  final Ref _ref;
  
  GroupSearchNotifier(this._ref) : super(const AsyncValue.data([]));
  
  Future<void> search({
    String? keyword,
    GroupType? type,
    List<String>? tags,
  }) async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() async {
      final api = _ref.read(communityApiProvider);
      return await api.searchGroups(
        keyword: keyword,
        type: type,
        tags: tags,
      );
    });
  }
  
  void clear() {
    state = const AsyncValue.data([]);
  }
}
```

### 7.5 火堆动画组件

#### 文件：`lib/features/community/widgets/bonfire_animation.dart`

```dart
/// 火堆动画组件
/// 
/// 位置：Flutter 项目的 lib/features/community/widgets/bonfire_animation.dart
/// 作用：渲染群组火堆的可视化效果，展示成员的火苗汇聚

import 'dart:math';
import 'package:flutter/material.dart';

/// 单个火苗数据
class FlameData {
  final int userId;
  final double power;      // 0-100
  final Color color;
  final double size;       // 相对大小
  final Offset position;   // 在火堆中的位置
  
  FlameData({
    required this.userId,
    required this.power,
    required this.color,
    required this.size,
    required this.position,
  });
}

/// 火堆动画组件
class BonfireAnimation extends StatefulWidget {
  /// 火苗列表
  final List<FlameData> flames;
  
  /// 火堆等级 (1-5)，决定整体大小和效果
  final int bonfireLevel;
  
  /// 总能量值
  final int totalPower;
  
  const BonfireAnimation({
    super.key,
    required this.flames,
    required this.bonfireLevel,
    required this.totalPower,
  });
  
  @override
  State<BonfireAnimation> createState() => _BonfireAnimationState();
}

class _BonfireAnimationState extends State<BonfireAnimation>
    with TickerProviderStateMixin {
  late AnimationController _flickerController;
  late AnimationController _glowController;
  final Random _random = Random();
  
  @override
  void initState() {
    super.initState();
    
    // 火焰闪烁动画
    _flickerController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 150),
    )..repeat(reverse: true);
    
    // 光晕动画
    _glowController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat(reverse: true);
  }
  
  @override
  void dispose() {
    _flickerController.dispose();
    _glowController.dispose();
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: Listenable.merge([_flickerController, _glowController]),
      builder: (context, child) {
        return CustomPaint(
          painter: BonfirePainter(
            flames: widget.flames,
            bonfireLevel: widget.bonfireLevel,
            flickerValue: _flickerController.value,
            glowValue: _glowController.value,
            random: _random,
          ),
          size: Size.infinite,
        );
      },
    );
  }
}

/// 火堆绘制器
class BonfirePainter extends CustomPainter {
  final List<FlameData> flames;
  final int bonfireLevel;
  final double flickerValue;
  final double glowValue;
  final Random random;
  
  BonfirePainter({
    required this.flames,
    required this.bonfireLevel,
    required this.flickerValue,
    required this.glowValue,
    required this.random,
  });
  
  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height * 0.7);
    final baseRadius = size.width * 0.15 * (1 + bonfireLevel * 0.1);
    
    // 1. 绘制底部光晕
    _drawGlow(canvas, center, baseRadius);
    
    // 2. 绘制每个成员的火苗
    for (final flame in flames) {
      _drawFlame(canvas, center, flame, baseRadius);
    }
    
    // 3. 绘制火花粒子
    _drawSparks(canvas, center, baseRadius);
  }
  
  void _drawGlow(Canvas canvas, Offset center, double radius) {
    final glowRadius = radius * (2.5 + glowValue * 0.3);
    
    final gradient = RadialGradient(
      colors: [
        Colors.orange.withOpacity(0.3 + glowValue * 0.1),
        Colors.orange.withOpacity(0.1),
        Colors.transparent,
      ],
      stops: const [0.0, 0.5, 1.0],
    );
    
    final paint = Paint()
      ..shader = gradient.createShader(
        Rect.fromCircle(center: center, radius: glowRadius),
      );
    
    canvas.drawCircle(center, glowRadius, paint);
  }
  
  void _drawFlame(
    Canvas canvas, 
    Offset bonfireCenter, 
    FlameData flame,
    double baseRadius,
  ) {
    // 计算火苗位置（围绕火堆中心分布）
    final flameCenter = bonfireCenter + flame.position * baseRadius;
    
    // 火苗大小根据 power 和 size 计算
    final flameHeight = baseRadius * 0.4 * flame.size * (0.8 + flame.power / 100 * 0.4);
    final flameWidth = flameHeight * 0.4;
    
    // 添加闪烁效果
    final flickerOffset = (flickerValue - 0.5) * flameWidth * 0.1;
    
    // 绘制火苗形状（使用贝塞尔曲线）
    final path = Path();
    path.moveTo(flameCenter.dx, flameCenter.dy);
    path.quadraticBezierTo(
      flameCenter.dx - flameWidth / 2 + flickerOffset,
      flameCenter.dy - flameHeight / 2,
      flameCenter.dx,
      flameCenter.dy - flameHeight,
    );
    path.quadraticBezierTo(
      flameCenter.dx + flameWidth / 2 + flickerOffset,
      flameCenter.dy - flameHeight / 2,
      flameCenter.dx,
      flameCenter.dy,
    );
    
    // 渐变填充
    final gradient = LinearGradient(
      begin: Alignment.bottomCenter,
      end: Alignment.topCenter,
      colors: [
        flame.color,
        flame.color.withOpacity(0.8),
        Colors.yellow.withOpacity(0.6),
      ],
    );
    
    final paint = Paint()
      ..shader = gradient.createShader(
        Rect.fromCenter(
          center: flameCenter - Offset(0, flameHeight / 2),
          width: flameWidth,
          height: flameHeight,
        ),
      );
    
    canvas.drawPath(path, paint);
  }
  
  void _drawSparks(Canvas canvas, Offset center, double radius) {
    // 绘制随机火花粒子
    final sparkCount = bonfireLevel * 3;
    final sparkPaint = Paint()..color = Colors.yellow;
    
    for (var i = 0; i < sparkCount; i++) {
      final angle = random.nextDouble() * 2 * pi;
      final distance = radius * (0.3 + random.nextDouble() * 0.5);
      final sparkSize = 1.0 + random.nextDouble() * 2;
      
      final sparkPos = center + Offset(
        cos(angle) * distance,
        -radius * 0.5 - random.nextDouble() * radius * 0.8,
      );
      
      canvas.drawCircle(sparkPos, sparkSize, sparkPaint);
    }
  }
  
  @override
  bool shouldRepaint(covariant BonfirePainter oldDelegate) {
    return oldDelegate.flickerValue != flickerValue ||
           oldDelegate.glowValue != glowValue;
  }
}
```

### 7.6 群组聊天界面

#### 文件：`lib/features/community/screens/group_chat_screen.dart`

```dart
/// 群组聊天界面
/// 
/// 位置：Flutter 项目的 lib/features/community/screens/group_chat_screen.dart
/// 作用：展示群组消息和互动功能

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/group.dart';
import '../models/message.dart';
import '../providers/chat_provider.dart';
import '../widgets/message_bubble.dart';
import '../widgets/bonfire_animation.dart';
import '../widgets/checkin_card.dart';

class GroupChatScreen extends ConsumerStatefulWidget {
  final int groupId;
  
  const GroupChatScreen({super.key, required this.groupId});
  
  @override
  ConsumerState<GroupChatScreen> createState() => _GroupChatScreenState();
}

class _GroupChatScreenState extends ConsumerState<GroupChatScreen> {
  final _messageController = TextEditingController();
  final _scrollController = ScrollController();
  bool _showBonfire = false;
  
  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
  }
  
  void _onScroll() {
    // 滚动到顶部时加载更多消息
    if (_scrollController.position.pixels >= 
        _scrollController.position.maxScrollExtent - 100) {
      ref.read(chatProvider(widget.groupId).notifier).loadMore();
    }
  }
  
  @override
  Widget build(BuildContext context) {
    final groupAsync = ref.watch(groupDetailProvider(widget.groupId));
    final messagesAsync = ref.watch(chatProvider(widget.groupId));
    
    return Scaffold(
      body: groupAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('加载失败: $e')),
        data: (group) => Column(
          children: [
            // 顶部：群组信息 + 火堆
            _buildHeader(group),
            
            // 消息列表
            Expanded(
              child: messagesAsync.when(
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (e, _) => Center(child: Text('加载失败: $e')),
                data: (messages) => _buildMessageList(messages),
              ),
            ),
            
            // 底部输入区域
            _buildInputArea(group),
          ],
        ),
      ),
    );
  }
  
  Widget _buildHeader(GroupInfo group) {
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Colors.orange.shade800,
            Colors.orange.shade600,
          ],
        ),
      ),
      child: SafeArea(
        bottom: false,
        child: Column(
          children: [
            // 导航栏
            Row(
              children: [
                IconButton(
                  icon: const Icon(Icons.arrow_back, color: Colors.white),
                  onPressed: () => Navigator.pop(context),
                ),
                Expanded(
                  child: Column(
                    children: [
                      Text(
                        group.name,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Text(
                        '${group.memberCount}人 · 今日${group.todayCheckinCount}人打卡',
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.8),
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  icon: Icon(
                    _showBonfire ? Icons.chat : Icons.local_fire_department,
                    color: Colors.white,
                  ),
                  onPressed: () => setState(() => _showBonfire = !_showBonfire),
                ),
                IconButton(
                  icon: const Icon(Icons.more_vert, color: Colors.white),
                  onPressed: () => _showGroupMenu(group),
                ),
              ],
            ),
            
            // 冲刺群显示倒计时
            if (group.type == GroupType.sprint && group.daysRemaining != null)
              Container(
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.timer, color: Colors.white, size: 16),
                    const SizedBox(width: 4),
                    Text(
                      '距离目标还有 ${group.daysRemaining} 天',
                      style: const TextStyle(color: Colors.white),
                    ),
                  ],
                ),
              ),
            
            // 火堆动画（可切换显示）
            if (_showBonfire)
              SizedBox(
                height: 200,
                child: BonfireAnimation(
                  flames: [], // 从 flameStatusProvider 获取
                  bonfireLevel: (group.totalFlamePower / 1000).clamp(1, 5).toInt(),
                  totalPower: group.totalFlamePower,
                ),
              ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildMessageList(List<MessageInfo> messages) {
    return ListView.builder(
      controller: _scrollController,
      reverse: true,  // 最新消息在底部
      padding: const EdgeInsets.all(16),
      itemCount: messages.length,
      itemBuilder: (context, index) {
        final message = messages[index];
        return _buildMessageItem(message);
      },
    );
  }
  
  Widget _buildMessageItem(MessageInfo message) {
    // 根据消息类型渲染不同的组件
    switch (message.messageType) {
      case MessageType.text:
        return MessageBubble(message: message);
      
      case MessageType.checkin:
        return CheckinCard(message: message);
      
      case MessageType.taskShare:
        return TaskShareCard(message: message);
      
      case MessageType.progress:
        return ProgressUpdateCard(message: message);
      
      case MessageType.achievement:
        return AchievementCard(message: message);
      
      case MessageType.system:
        return SystemMessageCard(message: message);
    }
  }
  
  Widget _buildInputArea(GroupInfo group) {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 4,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: Row(
          children: [
            // 快捷操作按钮
            IconButton(
              icon: const Icon(Icons.add_circle_outline),
              onPressed: () => _showQuickActions(group),
            ),
            
            // 打卡按钮
            IconButton(
              icon: const Icon(Icons.local_fire_department, color: Colors.orange),
              onPressed: () => _showCheckinDialog(group),
            ),
            
            // 文本输入
            Expanded(
              child: TextField(
                controller: _messageController,
                decoration: const InputDecoration(
                  hintText: '说点什么...',
                  border: InputBorder.none,
                  contentPadding: EdgeInsets.symmetric(horizontal: 12),
                ),
                maxLines: null,
              ),
            ),
            
            // 发送按钮
            IconButton(
              icon: const Icon(Icons.send, color: Colors.blue),
              onPressed: _sendMessage,
            ),
          ],
        ),
      ),
    );
  }
  
  void _sendMessage() {
    final content = _messageController.text.trim();
    if (content.isEmpty) return;
    
    ref.read(chatProvider(widget.groupId).notifier).sendMessage(
      type: MessageType.text,
      content: content,
    );
    
    _messageController.clear();
  }
  
  void _showQuickActions(GroupInfo group) {
    showModalBottomSheet(
      context: context,
      builder: (context) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          ListTile(
            leading: const Icon(Icons.task_alt),
            title: const Text('分享任务进度'),
            onTap: () {
              Navigator.pop(context);
              // 显示任务选择
            },
          ),
          ListTile(
            leading: const Icon(Icons.emoji_events),
            title: const Text('分享成就'),
            onTap: () {
              Navigator.pop(context);
              // 显示成就选择
            },
          ),
          if (group.myRole != GroupRole.member)
            ListTile(
              leading: const Icon(Icons.assignment),
              title: const Text('创建群任务'),
              onTap: () {
                Navigator.pop(context);
                // 跳转到创建群任务页面
              },
            ),
        ],
      ),
    );
  }
  
  void _showCheckinDialog(GroupInfo group) {
    showDialog(
      context: context,
      builder: (context) => CheckinDialog(
        groupId: widget.groupId,
        onCheckin: (duration, message) async {
          await ref.read(chatProvider(widget.groupId).notifier).checkin(
            todayDurationMinutes: duration,
            message: message,
          );
        },
      ),
    );
  }
  
  void _showGroupMenu(GroupInfo group) {
    // 显示群设置菜单
  }
}
```

---

## 八、实现优先级与时间线

### MVP 阶段（1-2周）

| 优先级 | 功能 | 预估时间 |
|--------|------|----------|
| P0 | 数据库模型 + 迁移 | 1天 |
| P0 | 群组创建/加入/退出 API | 1天 |
| P0 | 基础群消息发送/接收 | 2天 |
| P0 | Flutter 群组列表 + 聊天界面 | 3天 |
| P1 | 打卡功能 | 1天 |
| P1 | 群任务基础功能 | 2天 |

### 增强阶段（2-3周）

| 优先级 | 功能 | 预估时间 |
|--------|------|----------|
| P1 | 好友系统完整实现 | 2天 |
| P1 | 好友推荐算法 | 2天 |
| P2 | 火堆动画组件 | 2天 |
| P2 | 消息模板（进度分享/成就） | 2天 |
| P2 | LLM 工具集成 | 2天 |

---

## 九、关键技术决策

### 9.1 消息系统设计

**为什么使用模板化消息而不是纯文本聊天？**

根据方案设计的理念"群内互动以任务与知识为核心，减少无意义灌水"，我们通过结构化的消息类型（打卡、任务分享、进度更新等）来引导健康的社群氛围。

### 9.2 火苗贡献计算

```python
# 火苗贡献公式
base_flame = 10                              # 基础值
streak_bonus = min(streak_days * 2, 20)      # 连续打卡奖励，最多+20
duration_bonus = min(minutes // 30 * 5, 30)  # 学习时长奖励，每30分钟+5，最多+30
total = base_flame + streak_bonus + duration_bonus
```

这个公式鼓励：
1. 每日打卡（基础贡献）
2. 坚持连续打卡（连续奖励）
3. 深度学习（时长奖励）

### 9.3 群组与个人任务的关联

群任务 → 认领 → 创建个人任务副本 → 完成 → 同步更新群任务统计

这种设计保持了：
- 个人任务系统的独立性
- 群组进度的可追踪性
- 数据的一致性

---

## 十、测试要点

### 10.1 单元测试

```python
# tests/test_community.py

import pytest
from services.community_service import FriendshipService, GroupService

@pytest.mark.asyncio
async def test_create_sprint_group(db_session):
    """测试创建冲刺群"""
    service = GroupService(db_session)
    group = await service.create_group(
        creator_id=1,
        data=GroupCreate(
            name="计组期末冲刺",
            type=GroupType.SPRINT,
            deadline=datetime.now() + timedelta(days=14),
            sprint_goal="考试90分以上"
        )
    )
    
    assert group.id is not None
    assert group.type == GroupType.SPRINT
    assert group.deadline is not None

@pytest.mark.asyncio
async def test_checkin_streak(db_session):
    """测试连续打卡计数"""
    service = CheckinService(db_session)
    
    # 第一次打卡
    result1 = await service.checkin(user_id=1, data=CheckinRequest(
        group_id=1, today_duration_minutes=60
    ))
    assert result1['new_streak'] == 1
    
    # 模拟第二天打卡
    # ...
```

### 10.2 集成测试

```python
@pytest.mark.asyncio
async def test_group_task_flow(db_session, client):
    """测试群任务完整流程：创建 → 认领 → 完成"""
    # 1. 创建群任务
    response = await client.post('/community/groups/1/tasks', json={
        'title': '复习第一章',
        'estimated_minutes': 30
    })
    task_id = response.json()['id']
    
    # 2. 认领任务
    response = await client.post(f'/community/tasks/{task_id}/claim')
    assert response.status_code == 200
    
    # 3. 完成个人任务后检查群任务统计
    # ...
```

---

这份指南涵盖了社群功能从数据库设计到前端实现的完整技术栈。每个部分都包含了详细的代码示例和设计说明，你可以根据实际进度逐步实现。

有任何具体问题，随时问我！