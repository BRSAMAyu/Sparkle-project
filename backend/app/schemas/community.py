"""
社群功能 Pydantic Schemas
Community Schemas - 好友、群组、消息、任务相关的请求/响应模型
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import BaseSchema


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
    PLAN_SHARE = "plan_share"
    FRAGMENT_SHARE = "fragment_share"
    CAPSULE_SHARE = "capsule_share"
    PRISM_SHARE = "prism_share"
    FILE_SHARE = "file_share"
    PROGRESS = "progress"
    ACHIEVEMENT = "achievement"
    CHECKIN = "checkin"
    SYSTEM = "system"


class ReactionActionEnum(str, Enum):
    ADD = "add"
    REMOVE = "remove"


class UserStatusEnum(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    INVISIBLE = "invisible"


# ============ 用户简要信息 ============

class UserBrief(BaseModel):
    """用户简要信息（用于社群场景）"""
    id: UUID = Field(description="用户ID")
    username: str = Field(description="用户名")
    nickname: Optional[str] = Field(default=None, description="昵称")
    avatar_url: Optional[str] = Field(default=None, description="头像URL")
    flame_level: int = Field(default=1, description="火苗等级")
    flame_brightness: float = Field(default=0.5, description="火苗亮度")
    status: UserStatusEnum = Field(default=UserStatusEnum.OFFLINE, description="在线状态")

    class Config:
        from_attributes = True


class UserStatusUpdate(BaseModel):
    """更新用户在线状态"""
    status: UserStatusEnum = Field(description="新状态")



# ============ 好友系统 Schemas ============

class FriendRequest(BaseModel):
    """发起好友请求"""
    target_user_id: UUID = Field(description="目标用户ID")
    message: Optional[str] = Field(default=None, max_length=200, description="请求留言")


class FriendResponse(BaseModel):
    """好友请求响应"""
    friendship_id: UUID = Field(description="好友关系ID")
    accept: bool = Field(description="是否接受")


class FriendshipInfo(BaseSchema):
    """好友关系信息"""
    friend: UserBrief = Field(description="好友信息")
    status: FriendshipStatusEnum = Field(description="关系状态")
    match_reason: Optional[Dict[str, Any]] = Field(default=None, description="匹配原因")
    initiated_by_me: bool = Field(default=False, description="是否由我发起")


class FriendRecommendation(BaseModel):
    """好友推荐"""
    user: UserBrief = Field(description="推荐用户")
    match_score: float = Field(ge=0, le=1, description="匹配得分")
    match_reasons: List[str] = Field(description="匹配原因列表")

    class Config:
        from_attributes = True


# ============ 群组 Schemas ============

class GroupCreate(BaseModel):
    """创建群组"""
    name: str = Field(min_length=2, max_length=100, description="群组名称")
    description: Optional[str] = Field(default=None, max_length=500, description="群组描述")
    type: GroupTypeEnum = Field(description="群组类型")
    focus_tags: List[str] = Field(default_factory=list, max_length=10, description="关注标签")

    # 冲刺群专用
    deadline: Optional[datetime] = Field(default=None, description="冲刺截止日期")
    sprint_goal: Optional[str] = Field(default=None, max_length=500, description="冲刺目标")

    # 设置
    max_members: int = Field(default=50, ge=2, le=200, description="最大成员数")
    is_public: bool = Field(default=True, description="是否公开")
    join_requires_approval: bool = Field(default=False, description="加入需要审批")

    @field_validator('deadline')
    @classmethod
    def validate_deadline(cls, v, info):
        if info.data.get('type') == GroupTypeEnum.SPRINT and v is None:
            raise ValueError('冲刺群必须设置截止日期')
        if v and v < datetime.now():
            raise ValueError('截止日期不能是过去的时间')
        return v


class GroupUpdate(BaseModel):
    """更新群组信息"""
    name: Optional[str] = Field(default=None, min_length=2, max_length=100, description="群组名称")
    description: Optional[str] = Field(default=None, max_length=500, description="群组描述")
    focus_tags: Optional[List[str]] = Field(default=None, max_length=10, description="关注标签")
    deadline: Optional[datetime] = Field(default=None, description="冲刺截止日期")
    sprint_goal: Optional[str] = Field(default=None, max_length=500, description="冲刺目标")
    is_public: Optional[bool] = Field(default=None, description="是否公开")
    join_requires_approval: Optional[bool] = Field(default=None, description="加入需要审批")


class GroupInfo(BaseSchema):
    """群组详细信息"""
    name: str = Field(description="群组名称")
    description: Optional[str] = Field(description="群组描述")
    avatar_url: Optional[str] = Field(description="群组头像")
    type: GroupTypeEnum = Field(description="群组类型")
    focus_tags: List[str] = Field(description="关注标签")

    # 冲刺群信息
    deadline: Optional[datetime] = Field(description="冲刺截止日期")
    sprint_goal: Optional[str] = Field(description="冲刺目标")
    days_remaining: Optional[int] = Field(default=None, description="距离截止日期天数")

    # 统计
    member_count: int = Field(description="成员数量")
    total_flame_power: int = Field(description="火苗总能量")
    today_checkin_count: int = Field(description="今日打卡数")
    total_tasks_completed: int = Field(description="完成任务总数")

    # 设置
    max_members: int = Field(description="最大成员数")
    is_public: bool = Field(description="是否公开")
    join_requires_approval: bool = Field(description="加入需要审批")

    # 当前用户在群组中的角色（如果是成员）
    my_role: Optional[GroupRoleEnum] = Field(default=None, description="我的角色")


class GroupListItem(BaseModel):
    """群组列表项（简要信息）"""
    id: UUID = Field(description="群组ID")
    name: str = Field(description="群组名称")
    type: GroupTypeEnum = Field(description="群组类型")
    member_count: int = Field(description="成员数量")
    total_flame_power: int = Field(description="火苗总能量")
    deadline: Optional[datetime] = Field(description="冲刺截止日期")
    days_remaining: Optional[int] = Field(description="剩余天数")
    focus_tags: List[str] = Field(description="关注标签")
    my_role: Optional[GroupRoleEnum] = Field(default=None, description="我的角色")

    class Config:
        from_attributes = True


# ============ 群成员 Schemas ============

class GroupMemberInfo(BaseModel):
    """群成员信息"""
    user: UserBrief = Field(description="用户信息")
    role: GroupRoleEnum = Field(description="角色")
    flame_contribution: int = Field(description="火苗贡献值")
    tasks_completed: int = Field(description="完成任务数")
    checkin_streak: int = Field(description="连续打卡天数")
    joined_at: datetime = Field(description="加入时间")
    last_active_at: datetime = Field(description="最后活跃时间")

    class Config:
        from_attributes = True


class MemberRoleUpdate(BaseModel):
    """更新成员角色"""
    user_id: UUID = Field(description="用户ID")
    new_role: GroupRoleEnum = Field(description="新角色")


# ============ 群消息 Schemas ============

class MessageSend(BaseModel):
    """发送消息"""
    message_type: MessageTypeEnum = Field(default=MessageTypeEnum.TEXT, description="消息类型")
    content: Optional[str] = Field(default=None, max_length=2000, description="消息内容")
    content_data: Optional[Dict[str, Any]] = Field(default=None, description="结构化内容")
    reply_to_id: Optional[UUID] = Field(default=None, description="回复的消息ID")
    thread_root_id: Optional[UUID] = Field(default=None, description="线程根消息ID")
    mention_user_ids: Optional[List[UUID]] = Field(default=None, description="提及用户ID列表")
    nonce: Optional[str] = Field(default=None, description="客户端生成的随机串，用于ACK确认")

    @field_validator('content')
    @classmethod
    def validate_content(cls, v, info):
        msg_type = info.data.get('message_type')
        if msg_type == MessageTypeEnum.TEXT and not v:
            raise ValueError('文本消息必须有内容')
        return v

    @field_validator('content_data')
    @classmethod
    def validate_content_data(cls, v, info):
        msg_type = info.data.get('message_type')
        if msg_type == MessageTypeEnum.FILE_SHARE:
            if not isinstance(v, dict) or not v.get('file_id'):
                raise ValueError('文件消息必须包含 file_id')
        return v


class MessageInfo(BaseSchema):
    """消息信息"""
    sender: Optional[UserBrief] = Field(description="发送者（系统消息为空）")
    message_type: MessageTypeEnum = Field(description="消息类型")
    content: Optional[str] = Field(description="消息内容")
    content_data: Optional[Dict[str, Any]] = Field(description="结构化内容")
    reply_to_id: Optional[UUID] = Field(description="回复的消息ID")
    thread_root_id: Optional[UUID] = Field(default=None, description="线程根消息ID")
    mention_user_ids: Optional[List[UUID]] = Field(default=None, description="提及用户ID列表")
    reactions: Optional[Dict[str, List[UUID]]] = Field(default=None, description="表情反应")
    is_revoked: bool = Field(default=False, description="是否已撤回")
    revoked_at: Optional[datetime] = Field(default=None, description="撤回时间")
    edited_at: Optional[datetime] = Field(default=None, description="编辑时间")
    quoted_message: Optional['MessageInfo'] = Field(default=None, description="引用消息详情")


class MessageEdit(BaseModel):
    """编辑消息"""
    content: Optional[str] = Field(default=None, max_length=2000, description="新内容")
    content_data: Optional[Dict[str, Any]] = Field(default=None, description="结构化内容")
    mention_user_ids: Optional[List[UUID]] = Field(default=None, description="提及用户ID列表")


class MessageReactionUpdate(BaseModel):
    """更新消息表情反应"""
    emoji: str = Field(min_length=1, max_length=12, description="表情")
    action: ReactionActionEnum = Field(default=ReactionActionEnum.ADD, description="添加/移除")


# ============ 群文件 Schemas ============

class GroupFilePermissions(BaseModel):
    """群文件权限设置"""
    view_role: GroupRoleEnum = Field(default=GroupRoleEnum.MEMBER, description="可查看的最低角色")
    download_role: GroupRoleEnum = Field(default=GroupRoleEnum.MEMBER, description="可下载的最低角色")
    manage_role: GroupRoleEnum = Field(default=GroupRoleEnum.ADMIN, description="可管理的最低角色")


class GroupFileShareRequest(BaseModel):
    """分享文件到群组"""
    category: Optional[str] = Field(default=None, max_length=64, description="分类")
    tags: Optional[List[str]] = Field(default=None, description="标签")
    permissions: Optional[GroupFilePermissions] = Field(default=None, description="权限设置")
    send_message: bool = Field(default=True, description="是否发送文件分享消息")


class GroupFilePermissionUpdate(BaseModel):
    """更新群文件权限"""
    permissions: GroupFilePermissions = Field(description="权限设置")


class GroupFileInfo(BaseSchema):
    """群文件信息"""
    group_id: UUID = Field(description="群组ID")
    file_id: UUID = Field(description="文件ID")
    shared_by: Optional[UserBrief] = Field(description="分享者")
    category: Optional[str] = Field(description="分类")
    tags: List[str] = Field(default_factory=list, description="标签")
    view_role: GroupRoleEnum = Field(description="查看权限")
    download_role: GroupRoleEnum = Field(description="下载权限")
    manage_role: GroupRoleEnum = Field(description="管理权限")
    file_name: str = Field(description="文件名")
    mime_type: str = Field(description="MIME类型")
    file_size: int = Field(description="文件大小")
    status: str = Field(description="处理状态")
    visibility: str = Field(description="可见性")
    can_download: bool = Field(description="当前用户是否可下载")
    can_manage: bool = Field(description="当前用户是否可管理")


class GroupFileCategoryStat(BaseModel):
    """群文件分类统计"""
    category: Optional[str] = Field(description="分类")
    count: int = Field(description="数量")


# ============ 群任务 Schemas ============

class GroupTaskCreate(BaseModel):
    """创建群任务"""
    title: str = Field(min_length=2, max_length=200, description="任务标题")
    description: Optional[str] = Field(default=None, max_length=1000, description="任务描述")
    tags: List[str] = Field(default_factory=list, max_length=5, description="标签")
    estimated_minutes: int = Field(default=10, ge=1, le=480, description="预估时长（分钟）")
    difficulty: int = Field(default=1, ge=1, le=5, description="难度等级")
    due_date: Optional[datetime] = Field(default=None, description="截止日期")


class GroupTaskInfo(BaseSchema):
    """群任务信息"""
    title: str = Field(description="任务标题")
    description: Optional[str] = Field(description="任务描述")
    tags: List[str] = Field(description="标签")
    estimated_minutes: int = Field(description="预估时长")
    difficulty: int = Field(description="难度等级")
    total_claims: int = Field(description="认领次数")
    total_completions: int = Field(description="完成次数")
    completion_rate: float = Field(description="完成率")
    due_date: Optional[datetime] = Field(description="截止日期")
    creator: UserBrief = Field(description="创建者")

    # 当前用户状态
    is_claimed_by_me: bool = Field(default=False, description="是否已认领")
    my_completion_status: Optional[bool] = Field(default=None, description="我的完成状态")


# ============ 打卡 Schemas ============

class CheckinRequest(BaseModel):
    """打卡请求"""
    group_id: UUID = Field(description="群组ID")
    message: Optional[str] = Field(default=None, max_length=200, description="打卡留言")
    today_duration_minutes: int = Field(ge=0, description="今日学习时长（分钟）")


class CheckinResponse(BaseModel):
    """打卡响应"""
    success: bool = Field(description="是否成功")
    new_streak: int = Field(description="新的连续天数")
    flame_earned: int = Field(description="获得的火苗值")
    rank_in_group: int = Field(description="在群组中的排名")
    group_checkin_count: int = Field(description="群组今日打卡数")


# ============ 火堆视觉 Schemas ============

class FlameStatus(BaseModel):
    """火苗状态（用于可视化）"""
    user_id: UUID = Field(description="用户ID")
    flame_power: int = Field(description="火苗能量 0-100")
    flame_color: str = Field(description="火苗颜色代码")
    flame_size: float = Field(description="相对大小 0.5-2.0")
    position_x: float = Field(description="在火堆中的X位置")
    position_y: float = Field(description="在火堆中的Y位置")


class GroupFlameStatus(BaseModel):
    """群组火堆状态"""
    group_id: UUID = Field(description="群组ID")
    total_power: int = Field(description="总能量")
    flames: List[FlameStatus] = Field(description="所有成员的火苗")
    bonfire_level: int = Field(ge=1, le=5, description="火堆等级")


# ============ 共享资源 Schemas ============

class SharedResourceTypeEnum(str, Enum):
    PLAN = "plan"
    TASK = "task"
    COGNITIVE_FRAGMENT = "cognitive_fragment"
    CURIOSITY_CAPSULE = "curiosity_capsule"
    COGNITIVE_PRISM_PATTERN = "cognitive_prism_pattern"


class SharedResourceCreate(BaseModel):
    """创建共享资源请求"""
    resource_type: SharedResourceTypeEnum = Field(description="资源类型")
    resource_id: UUID = Field(description="资源ID")
    target_group_id: Optional[UUID] = Field(default=None, description="分享给群组ID")
    target_user_id: Optional[UUID] = Field(default=None, description="分享给好友ID")
    permission: str = Field(default="view", pattern="^(view|comment|edit)$", description="权限")
    comment: Optional[str] = Field(default=None, max_length=500, description="分享留言")


class SharedResourceInfo(BaseSchema):
    """共享资源信息"""
    resource_type: str = Field(description="资源类型") # Simplified for response
    # We return the embedded object if possible, or just IDs?
    # Ideally return a summary of the object.
    # For simplicity, we return generic info and client fetches details if needed, 
    # OR we embed a brief summary.
    
    # IDs
    plan_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    cognitive_fragment_id: Optional[UUID] = None
    curiosity_capsule_id: Optional[UUID] = None
    behavior_pattern_id: Optional[UUID] = None
    
    # Metadata
    permission: str
    comment: Optional[str]
    view_count: int
    save_count: int
    
    sharer: UserBrief
    
    # Embedded Briefs (Optional)
    # Ideally we'd have a 'resource_title' or 'resource_summary' field computed
    resource_title: Optional[str] = None
    resource_summary: Optional[str] = None

    class Config:
        from_attributes = True


# ============ 私聊消息 Schemas ============

class PrivateMessageSend(BaseModel):
    """发送私聊消息"""
    target_user_id: UUID = Field(description="接收用户ID")
    message_type: MessageTypeEnum = Field(default=MessageTypeEnum.TEXT, description="消息类型")
    content: Optional[str] = Field(default=None, max_length=2000, description="消息内容")
    content_data: Optional[Dict[str, Any]] = Field(default=None, description="结构化内容")
    reply_to_id: Optional[UUID] = Field(default=None, description="回复的消息ID")
    thread_root_id: Optional[UUID] = Field(default=None, description="线程根消息ID")
    mention_user_ids: Optional[List[UUID]] = Field(default=None, description="提及用户ID列表")
    nonce: Optional[str] = Field(default=None, description="客户端生成的随机串，用于ACK确认")

    @field_validator('content')
    @classmethod
    def validate_content(cls, v, info):
        msg_type = info.data.get('message_type')
        if msg_type == MessageTypeEnum.TEXT and not v:
            raise ValueError('文本消息必须有内容')
        return v

    @field_validator('content_data')
    @classmethod
    def validate_content_data(cls, v, info):
        msg_type = info.data.get('message_type')
        if msg_type == MessageTypeEnum.FILE_SHARE:
            if not isinstance(v, dict) or not v.get('file_id'):
                raise ValueError('文件消息必须包含 file_id')
        return v


class PrivateMessageInfo(BaseSchema):
    """私聊消息信息"""
    sender: UserBrief = Field(description="发送者")
    receiver: UserBrief = Field(description="接收者")
    message_type: MessageTypeEnum = Field(description="消息类型")
    content: Optional[str] = Field(description="消息内容")
    content_data: Optional[Dict[str, Any]] = Field(description="结构化内容")
    reply_to_id: Optional[UUID] = Field(description="回复的消息ID")
    thread_root_id: Optional[UUID] = Field(default=None, description="线程根消息ID")
    mention_user_ids: Optional[List[UUID]] = Field(default=None, description="提及用户ID列表")
    reactions: Optional[Dict[str, List[UUID]]] = Field(default=None, description="表情反应")
    is_revoked: bool = Field(default=False, description="是否已撤回")
    revoked_at: Optional[datetime] = Field(default=None, description="撤回时间")
    edited_at: Optional[datetime] = Field(default=None, description="编辑时间")
    is_read: bool = Field(description="是否已读")
    read_at: Optional[datetime] = Field(description="阅读时间")
    quoted_message: Optional['PrivateMessageInfo'] = Field(default=None, description="引用消息详情")

# Handle recursive references
MessageInfo.model_rebuild()
PrivateMessageInfo.model_rebuild()


# ============ 加密相关 Schemas ============

class EncryptionKeyCreate(BaseModel):
    """创建加密密钥"""
    public_key: str = Field(description="Base64编码的公钥")
    key_type: str = Field(default="x25519", pattern="^(x25519|rsa)$", description="密钥类型")
    device_id: Optional[str] = Field(default=None, max_length=100, description="设备ID")


class EncryptionKeyInfo(BaseSchema):
    """加密密钥信息"""
    public_key: str = Field(description="Base64编码的公钥")
    key_type: str = Field(description="密钥类型")
    device_id: Optional[str] = Field(description="设备ID")
    is_active: bool = Field(description="是否激活")
    expires_at: Optional[datetime] = Field(description="过期时间")


class EncryptedMessageSend(BaseModel):
    """发送加密消息"""
    encrypted_content: str = Field(description="加密后的内容")
    content_signature: Optional[str] = Field(default=None, max_length=512, description="消息签名")
    encryption_version: int = Field(default=1, ge=1, le=10, description="加密版本")
    # 其他字段同普通消息
    message_type: MessageTypeEnum = Field(default=MessageTypeEnum.TEXT)
    content_data: Optional[Dict[str, Any]] = Field(default=None)
    reply_to_id: Optional[UUID] = Field(default=None)
    nonce: Optional[str] = Field(default=None)


# ============ 举报相关 Schemas ============

class ReportReasonEnum(str, Enum):
    SPAM = "spam"
    HARASSMENT = "harassment"
    VIOLENCE = "violence"
    MISINFORMATION = "misinformation"
    INAPPROPRIATE = "inappropriate"
    OTHER = "other"


class ReportStatusEnum(str, Enum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    DISMISSED = "dismissed"
    ACTIONED = "actioned"


class ModerationActionEnum(str, Enum):
    WARN = "warn"
    MUTE = "mute"
    KICK = "kick"
    BAN = "ban"


class MessageReportCreate(BaseModel):
    """创建消息举报"""
    group_message_id: Optional[UUID] = Field(default=None, description="群消息ID")
    private_message_id: Optional[UUID] = Field(default=None, description="私聊消息ID")
    reason: ReportReasonEnum = Field(description="举报原因")
    description: Optional[str] = Field(default=None, max_length=500, description="详细描述")


class MessageReportInfo(BaseSchema):
    """消息举报信息"""
    reporter: UserBrief = Field(description="举报人")
    reason: ReportReasonEnum = Field(description="举报原因")
    description: Optional[str] = Field(description="详细描述")
    status: ReportStatusEnum = Field(description="状态")
    reviewed_by: Optional[UserBrief] = Field(default=None, description="审核人")
    reviewed_at: Optional[datetime] = Field(default=None, description="审核时间")
    action_taken: Optional[ModerationActionEnum] = Field(default=None, description="处理动作")


class MessageReportReview(BaseModel):
    """审核消息举报"""
    status: ReportStatusEnum = Field(description="审核状态")
    action_taken: Optional[ModerationActionEnum] = Field(default=None, description="处理动作")


# ============ 收藏相关 Schemas ============

class MessageFavoriteCreate(BaseModel):
    """创建消息收藏"""
    group_message_id: Optional[UUID] = Field(default=None, description="群消息ID")
    private_message_id: Optional[UUID] = Field(default=None, description="私聊消息ID")
    note: Optional[str] = Field(default=None, max_length=500, description="个人备注")
    tags: Optional[List[str]] = Field(default=None, max_length=10, description="自定义标签")


class MessageFavoriteInfo(BaseSchema):
    """消息收藏信息"""
    group_message_id: Optional[UUID] = Field(default=None)
    private_message_id: Optional[UUID] = Field(default=None)
    note: Optional[str] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)
    # 可选：嵌入消息摘要
    message_preview: Optional[str] = Field(default=None, description="消息预览")


# ============ 转发相关 Schemas ============

class MessageForwardRequest(BaseModel):
    """转发消息请求"""
    source_message_id: UUID = Field(description="源消息ID")
    source_type: str = Field(pattern="^(group|private)$", description="源消息类型")
    target_group_id: Optional[UUID] = Field(default=None, description="目标群组ID")
    target_user_id: Optional[UUID] = Field(default=None, description="目标用户ID")
    comment: Optional[str] = Field(default=None, max_length=200, description="转发留言")


# ============ 广播相关 Schemas ============

class BroadcastMessageCreate(BaseModel):
    """创建跨群广播"""
    content: str = Field(min_length=1, max_length=2000, description="广播内容")
    content_data: Optional[Dict[str, Any]] = Field(default=None, description="结构化内容")
    target_group_ids: List[UUID] = Field(min_length=1, max_length=50, description="目标群组ID列表")


class BroadcastMessageInfo(BaseSchema):
    """广播消息信息"""
    sender: UserBrief = Field(description="发送者")
    content: str = Field(description="广播内容")
    content_data: Optional[Dict[str, Any]] = Field(description="结构化内容")
    target_group_ids: List[UUID] = Field(description="目标群组ID列表")
    delivered_count: int = Field(description="已送达数量")


# ============ 群管理相关 Schemas ============

class GroupAnnouncementUpdate(BaseModel):
    """更新群公告"""
    announcement: Optional[str] = Field(default=None, max_length=2000, description="群公告内容")


class GroupModerationSettings(BaseModel):
    """群管理设置"""
    keyword_filters: Optional[List[str]] = Field(default=None, max_length=100, description="敏感词列表")
    mute_all: Optional[bool] = Field(default=None, description="全员禁言")
    slow_mode_seconds: Optional[int] = Field(default=None, ge=0, le=3600, description="慢速模式秒数")


class MemberMuteRequest(BaseModel):
    """禁言成员请求"""
    user_id: UUID = Field(description="用户ID")
    duration_minutes: int = Field(ge=1, le=43200, description="禁言时长（分钟）")  # 最多30天
    reason: Optional[str] = Field(default=None, max_length=200, description="禁言原因")


class MemberWarnRequest(BaseModel):
    """警告成员请求"""
    user_id: UUID = Field(description="用户ID")
    reason: str = Field(min_length=1, max_length=200, description="警告原因")


# ============ 离线队列相关 Schemas ============

class OfflineMessageStatusEnum(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    EXPIRED = "expired"


class OfflineMessageInfo(BaseSchema):
    """离线消息信息"""
    client_nonce: str = Field(description="客户端唯一标识")
    message_type: str = Field(description="消息类型")
    target_id: UUID = Field(description="目标ID")
    status: OfflineMessageStatusEnum = Field(description="状态")
    retry_count: int = Field(description="重试次数")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    created_at: datetime = Field(description="创建时间")


class OfflineMessageRetryRequest(BaseModel):
    """重试离线消息请求"""
    message_ids: List[UUID] = Field(min_length=1, max_length=50, description="消息ID列表")


# ============ 搜索相关 Schemas ============

class MessageSearchRequest(BaseModel):
    """消息搜索请求"""
    keyword: Optional[str] = Field(default=None, max_length=100, description="关键词")
    sender_id: Optional[UUID] = Field(default=None, description="发送者ID")
    start_date: Optional[datetime] = Field(default=None, description="开始时间")
    end_date: Optional[datetime] = Field(default=None, description="结束时间")
    message_types: Optional[List[MessageTypeEnum]] = Field(default=None, description="消息类型")
    topic: Optional[str] = Field(default=None, max_length=100, description="话题")
    tags: Optional[List[str]] = Field(default=None, max_length=10, description="标签")
    has_attachments: Optional[bool] = Field(default=None, description="是否有附件")
    # 分页
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


class MessageSearchResult(BaseModel):
    """消息搜索结果"""
    messages: List[MessageInfo] = Field(description="消息列表")
    total: int = Field(description="总数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页数量")
    has_more: bool = Field(description="是否有更多")
