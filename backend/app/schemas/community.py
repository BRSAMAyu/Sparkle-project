"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>

社群功能 Pydantic Schemas
Community Schemas - 好友、群组、消息、任务相关的请求/响应模型
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import BaseSchema

# ============ 枚举类型 ============

class FriendshipStatusEnum(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    BLOCKED = "blocked"


class GroupTypeEnum(StrEnum):
    SQUAD = "squad"
    SPRINT = "sprint"


class GroupRoleEnum(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class GroupFileTrustLevelEnum(StrEnum):
    OFFICIAL = "official"
    VERIFIED = "verified"
    MEMBER = "member"


class MessageTypeEnum(StrEnum):
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


class ReactionActionEnum(StrEnum):
    ADD = "add"
    REMOVE = "remove"


class UserStatusEnum(StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"
    INVISIBLE = "invisible"


# ============ 用户简要信息 ============

class UserBrief(BaseModel):
    """用户简要信息（用于社群场景）"""
    id: UUID = Field(description="用户ID")
    username: str = Field(description="用户名")
    nickname: str | None = Field(default=None, description="昵称")
    avatar_url: str | None = Field(default=None, description="头像URL")
    flame_level: int = Field(default=1, description="火苗等级")
    flame_brightness: float = Field(default=0.5, description="火苗亮度")
    status: UserStatusEnum = Field(default=UserStatusEnum.OFFLINE, description="在线状态")

    model_config = ConfigDict(from_attributes=True)


class UserStatusUpdate(BaseModel):
    """更新用户在线状态"""
    status: UserStatusEnum = Field(description="新状态")



# ============ 好友系统 Schemas ============

class FriendRequest(BaseModel):
    """发起好友请求"""
    target_user_id: UUID = Field(description="目标用户ID")
    message: str | None = Field(default=None, max_length=200, description="请求留言")


class FriendResponse(BaseModel):
    """好友请求响应"""
    friendship_id: UUID = Field(description="好友关系ID")
    accept: bool = Field(description="是否接受")


class AccountabilityFriendSummary(BaseModel):
    """好友列表中的责任伙伴摘要"""
    partnership_id: UUID = Field(description="伙伴关系ID")
    slot_type: str = Field(description="伙伴槽位类型")
    status: str = Field(description="伙伴关系状态")
    my_role: str | None = Field(default=None, description="我在伙伴关系中的角色")
    my_checked_in_today: bool | None = Field(default=None, description="我今天是否已打卡")
    partner_checked_in_today: bool | None = Field(default=None, description="对方今天是否已打卡")
    my_streak_days: int | None = Field(default=None, description="我的连续打卡天数")
    partner_streak_days: int | None = Field(default=None, description="对方连续打卡天数")
    last_checkin_at: datetime | None = Field(default=None, description="最近一次打卡时间")
    goal_preview: str | None = Field(default=None, description="伙伴目标摘要")


class FriendshipInfo(BaseSchema):
    """好友关系信息"""
    friend: UserBrief = Field(description="好友信息")
    status: FriendshipStatusEnum = Field(description="关系状态")
    match_reason: dict[str, Any] | None = Field(default=None, description="匹配原因")
    initiated_by_me: bool = Field(default=False, description="是否由我发起")
    accountability: AccountabilityFriendSummary | None = Field(default=None, description="责任伙伴摘要")


class FriendRecommendation(BaseModel):
    """好友推荐"""
    user: UserBrief = Field(description="推荐用户")
    match_score: float = Field(ge=0, le=1, description="匹配得分")
    match_reasons: list[str] = Field(description="匹配原因列表")
    strategy: str = Field(default="compatibility", description="匹配策略")
    target: str = Field(default="accountability", description="推荐目标")
    summary: str | None = Field(default=None, description="推荐摘要")
    relationship_status: str = Field(default="none", description="当前关系状态")
    is_existing_friend: bool = Field(default=False, description="是否已经是好友")
    can_invite_accountability: bool = Field(default=False, description="是否可直接邀请为责任伙伴")
    recommended_action: str = Field(default="send_friend_request", description="推荐动作")
    score_breakdown: dict[str, float] = Field(default_factory=dict, description="评分拆解")

    model_config = ConfigDict(from_attributes=True)


class FriendMatchStrategyEnum(StrEnum):
    """好友/责任伙伴匹配策略"""

    COMPATIBILITY = "compatibility"
    COMPLEMENTARY = "complementary"


class FriendRecommendationTargetEnum(StrEnum):
    """好友推荐目标"""

    FRIEND = "friend"
    ACCOUNTABILITY = "accountability"


class RecommendationItemTypeEnum(StrEnum):
    """推荐对象类型"""

    FRIEND = "friend"
    GROUP = "group"


class RecommendationFeedbackStageEnum(StrEnum):
    """推荐反馈阶段"""

    IMMEDIATE = "immediate"
    FOLLOW_UP = "follow_up"
    OUTCOME = "outcome"


class RecommendationFeedbackMixin(BaseModel):
    """推荐反馈通用问卷字段"""

    prompt_id: str | None = Field(default=None, max_length=128, description="待反馈提示ID")
    stage: RecommendationFeedbackStageEnum = Field(
        default=RecommendationFeedbackStageEnum.IMMEDIATE,
        description="反馈阶段",
    )
    questionnaire_version: int = Field(default=1, ge=1, description="问卷版本")
    overall_score: int | None = Field(default=None, ge=1, le=5, description="总体满意度")
    relevance_score: int | None = Field(default=None, ge=1, le=5, description="相关度评分")
    explanation_score: int | None = Field(default=None, ge=1, le=5, description="推荐理由解释性评分")
    actionability_score: int | None = Field(default=None, ge=1, le=5, description="推荐可行动性评分")
    similarity_score: int | None = Field(default=None, ge=1, le=5, description="相似度预期评分")
    complementary_score: int | None = Field(default=None, ge=1, le=5, description="互补性预期评分")
    comfort_score: int | None = Field(default=None, ge=1, le=5, description="信任/舒适度评分")
    interest_match_score: int | None = Field(default=None, ge=1, le=5, description="兴趣匹配评分")
    activity_score: int | None = Field(default=None, ge=1, le=5, description="活跃度评分")
    atmosphere_score: int | None = Field(default=None, ge=1, le=5, description="社群氛围评分")
    selected_issues: list[str] = Field(default_factory=list, description="用户勾选的问题点")
    selected_strengths: list[str] = Field(default_factory=list, description="用户勾选的优点")
    free_text: str | None = Field(default=None, max_length=1000, description="自然语言补充反馈")


class FriendRecommendationFeedbackRequest(RecommendationFeedbackMixin):
    """好友推荐反馈"""

    target_user_id: UUID = Field(description="被推荐用户ID")
    strategy: FriendMatchStrategyEnum = Field(description="匹配策略")
    target: FriendRecommendationTargetEnum = Field(description="推荐目标")
    action: Literal[
        "view",
        "dismiss",
        "friend_request",
        "accountability_invite",
    ] = Field(description="反馈动作")
    source: str = Field(default="friends_discover", max_length=64, description="来源位置")
    score: float | None = Field(default=None, ge=0, le=1, description="展示时的匹配分")


class RecommendationFeedbackPrompt(BaseModel):
    """待处理的推荐反馈提示"""

    prompt_id: str = Field(description="提示ID")
    item_type: RecommendationItemTypeEnum = Field(description="推荐对象类型")
    item_id: UUID = Field(description="对象ID")
    stage: RecommendationFeedbackStageEnum = Field(description="当前反馈阶段")
    trigger_action: str = Field(description="触发提示的行为")
    title: str = Field(description="提示标题")
    subtitle: str | None = Field(default=None, description="提示副标题")
    due_at: datetime = Field(description="建议反馈时间")
    strategy: str | None = Field(default=None, description="对应的推荐策略")
    target: str | None = Field(default=None, description="对应推荐目标")
    user: UserBrief | None = Field(default=None, description="好友候选快照")
    group: GroupListItem | None = Field(default=None, description="社群候选快照")
    reason_tags: list[str] = Field(default_factory=list, description="展示过的理由标签")


class RecommendationFeedbackInsight(BaseModel):
    """推荐反馈洞察摘要"""

    item_type: RecommendationItemTypeEnum = Field(description="推荐对象类型")
    recent_feedback_count: int = Field(default=0, description="近期反馈数")
    average_scores: dict[str, float] = Field(default_factory=dict, description="各维度平均分")
    top_positive_signals: list[str] = Field(default_factory=list, description="高频正向信号")
    top_negative_signals: list[str] = Field(default_factory=list, description="高频负向信号")
    user_tuning: dict[str, Any] = Field(default_factory=dict, description="用户个性化调优参数")
    global_adjustments: dict[str, float] = Field(default_factory=dict, description="全局算法调优参数")


# ============ 群组 Schemas ============

class GroupCreate(BaseModel):
    """创建群组"""
    name: str = Field(min_length=2, max_length=100, description="群组名称")
    description: str | None = Field(default=None, max_length=500, description="群组描述")
    type: GroupTypeEnum = Field(description="群组类型")
    focus_tags: list[str] = Field(default_factory=list, max_length=10, description="关注标签")

    # 冲刺群专用
    deadline: datetime | None = Field(default=None, description="冲刺截止日期")
    sprint_goal: str | None = Field(default=None, max_length=500, description="冲刺目标")

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
    name: str | None = Field(default=None, min_length=2, max_length=100, description="群组名称")
    description: str | None = Field(default=None, max_length=500, description="群组描述")
    focus_tags: list[str] | None = Field(default=None, max_length=10, description="关注标签")
    deadline: datetime | None = Field(default=None, description="冲刺截止日期")
    sprint_goal: str | None = Field(default=None, max_length=500, description="冲刺目标")
    is_public: bool | None = Field(default=None, description="是否公开")
    join_requires_approval: bool | None = Field(default=None, description="加入需要审批")


class GroupInfo(BaseSchema):
    """群组详细信息"""
    name: str = Field(description="群组名称")
    description: str | None = Field(description="群组描述")
    avatar_url: str | None = Field(description="群组头像")
    type: GroupTypeEnum = Field(description="群组类型")
    focus_tags: list[str] = Field(description="关注标签")

    # 冲刺群信息
    deadline: datetime | None = Field(description="冲刺截止日期")
    sprint_goal: str | None = Field(description="冲刺目标")
    days_remaining: int | None = Field(default=None, description="距离截止日期天数")

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
    my_role: GroupRoleEnum | None = Field(default=None, description="我的角色")

    # 群公告
    announcement: str | None = Field(default=None, description="群公告内容")


class GroupListItem(BaseModel):
    """群组列表项（简要信息）"""
    id: UUID = Field(description="群组ID")
    name: str = Field(description="群组名称")
    description: str | None = Field(default=None, description="群组简介")
    type: GroupTypeEnum = Field(description="群组类型")
    member_count: int = Field(description="成员数量")
    total_flame_power: int = Field(description="火苗总能量")
    today_checkin_count: int = Field(default=0, description="今日打卡数量")
    deadline: datetime | None = Field(description="冲刺截止日期")
    days_remaining: int | None = Field(description="剩余天数")
    focus_tags: list[str] = Field(description="关注标签")
    is_public: bool = Field(default=True, description="是否公开")
    join_requires_approval: bool = Field(default=False, description="加入是否需要审批")
    activity_score: float | None = Field(default=None, description="目录排序用活跃度得分")
    my_role: GroupRoleEnum | None = Field(default=None, description="我的角色")

    model_config = ConfigDict(from_attributes=True)


# ============ 群组推荐 ============


class GroupDirectorySortEnum(StrEnum):
    """群组目录排序方式"""

    HOT = "hot"
    LATEST = "latest"
    RANDOM = "random"

class GroupRecommendationReason(BaseModel):
    """推荐理由"""
    type: str = Field(description="理由类型")
    data: dict[str, Any] | None = Field(default=None, description="理由数据")


class GroupRecommendationItem(BaseModel):
    """群组推荐项"""
    group: GroupListItem = Field(description="群组信息")
    score: float = Field(ge=0, le=1, description="推荐分数")
    reasons: list[GroupRecommendationReason] = Field(
        default_factory=list, description="推荐理由",
    )
    requires_approval: bool = Field(default=False, description="是否需要审批")


class GroupRecommendationFeedbackRequest(RecommendationFeedbackMixin):
    """群组推荐反馈"""
    group_id: UUID = Field(description="群组ID")
    action: Literal["view", "dismiss", "join"] = Field(description="反馈动作")
    source: Literal["list", "discover"] = Field(description="来源位置")
    reason_types: list[str] | None = Field(default=None, description="展示的理由类型")


class GroupDirectoryResponse(BaseModel):
    """公开群组目录聚合响应"""

    sort_by: GroupDirectorySortEnum = Field(description="当前排序方式")
    keyword: str | None = Field(default=None, description="搜索关键词")
    applied_tags: list[str] = Field(default_factory=list, description="当前筛选标签")
    available_tags: list[str] = Field(default_factory=list, description="可浏览标签")
    total_count: int = Field(default=0, description="符合筛选条件的群组总数")
    recommendations: list[GroupRecommendationItem] = Field(
        default_factory=list,
        description="个性化推荐",
    )
    groups: list[GroupListItem] = Field(default_factory=list, description="公开群组目录结果")


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

    model_config = ConfigDict(from_attributes=True)


class MemberRoleUpdate(BaseModel):
    """更新成员角色"""
    user_id: UUID = Field(description="用户ID")
    new_role: GroupRoleEnum = Field(description="新角色")


# ============ 群消息 Schemas ============

class MessageSend(BaseModel):
    """发送消息"""
    message_type: MessageTypeEnum = Field(default=MessageTypeEnum.TEXT, description="消息类型")
    content: str | None = Field(default=None, max_length=2000, description="消息内容")
    content_data: dict[str, Any] | None = Field(default=None, description="结构化内容")
    reply_to_id: UUID | None = Field(default=None, description="回复的消息ID")
    thread_root_id: UUID | None = Field(default=None, description="线程根消息ID")
    mention_user_ids: list[UUID] | None = Field(default=None, description="提及用户ID列表")
    nonce: str | None = Field(default=None, description="客户端生成的随机串，用于ACK确认")

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
        if msg_type == MessageTypeEnum.FILE_SHARE and (not isinstance(v, dict) or not v.get('file_id')):
            raise ValueError('文件消息必须包含 file_id')
        return v


class MessageInfo(BaseSchema):
    """消息信息"""
    sender: UserBrief | None = Field(description="发送者（系统消息为空）")
    message_type: MessageTypeEnum = Field(description="消息类型")
    content: str | None = Field(description="消息内容")
    content_data: dict[str, Any] | None = Field(description="结构化内容")
    reply_to_id: UUID | None = Field(description="回复的消息ID")
    thread_root_id: UUID | None = Field(default=None, description="线程根消息ID")
    mention_user_ids: list[UUID] | None = Field(default=None, description="提及用户ID列表")
    reactions: dict[str, list[UUID]] | None = Field(default=None, description="表情反应")
    is_revoked: bool = Field(default=False, description="是否已撤回")
    revoked_at: datetime | None = Field(default=None, description="撤回时间")
    edited_at: datetime | None = Field(default=None, description="编辑时间")
    read_by: list[UUID] | None = Field(default=None, description="已读用户ID列表")
    read_by_users: list[UserBrief] | None = Field(default=None, description="已读用户信息")
    quoted_message: MessageInfo | None = Field(default=None, description="引用消息详情")


class MessageEdit(BaseModel):
    """编辑消息"""
    content: str | None = Field(default=None, max_length=2000, description="新内容")
    content_data: dict[str, Any] | None = Field(default=None, description="结构化内容")
    mention_user_ids: list[UUID] | None = Field(default=None, description="提及用户ID列表")


class MessageReactionUpdate(BaseModel):
    """更新消息表情反应"""
    emoji: str = Field(min_length=1, max_length=12, description="表情")
    action: ReactionActionEnum = Field(default=ReactionActionEnum.ADD, description="添加/移除")


class GroupMessageReadRequest(BaseModel):
    """批量标记群消息已读"""

    up_to_message_id: UUID = Field(description="已读到的消息ID（含）")


class GroupMessageReadResponse(BaseModel):
    """群消息已读结果"""

    updated_count: int = Field(description="新增已读回执数量")
    up_to_message_id: UUID = Field(description="已读到的消息ID")


# ============ 群文件 Schemas ============

class GroupFilePermissions(BaseModel):
    """群文件权限设置"""
    view_role: GroupRoleEnum = Field(default=GroupRoleEnum.MEMBER, description="可查看的最低角色")
    download_role: GroupRoleEnum = Field(default=GroupRoleEnum.MEMBER, description="可下载的最低角色")
    manage_role: GroupRoleEnum = Field(default=GroupRoleEnum.ADMIN, description="可管理的最低角色")


class GroupFileSortEnum(StrEnum):
    """群文件排序方式"""

    LATEST = "latest"
    DOWNLOADS = "downloads"
    NAME = "name"


class GroupFileCreateRequest(BaseModel):
    """创建群文件分享记录"""

    file_id: UUID = Field(description="文件ID")
    category: str | None = Field(default=None, max_length=64, description="分类")
    description: str | None = Field(default=None, max_length=500, description="分享描述")
    send_message: bool = Field(default=True, description="是否发送文件分享消息")


class GroupFileShareRequest(BaseModel):
    """分享文件到群组"""
    category: str | None = Field(default=None, max_length=64, description="分类")
    description: str | None = Field(default=None, max_length=500, description="分享描述")
    tags: list[str] | None = Field(default=None, description="标签")
    permissions: GroupFilePermissions | None = Field(default=None, description="权限设置")
    send_message: bool = Field(default=True, description="是否发送文件分享消息")


class UserFileShareRequest(BaseModel):
    """分享文件给单个用户"""

    file_id: UUID = Field(description="文件ID")


class FileCopyResponse(BaseModel):
    """文件复制结果"""

    file_id: UUID = Field(description="复制后的文件ID")
    status: str = Field(description="文件处理状态")
    job_id: str | None = Field(default=None, description="后台处理任务ID")
    already_in_library: bool = Field(default=False, description="是否已在我的资料库中")
    suggested_nodes_route: str | None = Field(default=None, description="推荐节点查询路由")


class GroupFilePermissionUpdate(BaseModel):
    """更新群文件权限"""
    permissions: GroupFilePermissions = Field(description="权限设置")


class GroupFileInfo(BaseSchema):
    """群文件信息"""
    group_id: UUID = Field(description="群组ID")
    file_id: UUID = Field(description="文件ID")
    shared_by: UserBrief | None = Field(description="分享者")
    category: str | None = Field(description="分类")
    description: str | None = Field(default=None, description="分享描述")
    uploader_name: str | None = Field(default=None, description="上传者名称")
    tags: list[str] = Field(default_factory=list, description="标签")
    trust_level: GroupFileTrustLevelEnum = Field(default=GroupFileTrustLevelEnum.MEMBER, description="信任等级")
    knowledge_base: bool = Field(default=False, description="是否属于群知识库")
    view_role: GroupRoleEnum = Field(description="查看权限")
    download_role: GroupRoleEnum = Field(description="下载权限")
    manage_role: GroupRoleEnum = Field(description="管理权限")
    file_name: str = Field(description="文件名")
    mime_type: str = Field(description="MIME类型")
    file_size: int = Field(description="文件大小")
    status: str = Field(description="处理状态")
    visibility: str = Field(description="可见性")
    download_count: int = Field(default=0, description="下载次数")
    citation_count: int = Field(default=0, description="被引用次数")
    rating_count: int = Field(default=0, description="评分次数")
    average_rating: float | None = Field(default=None, description="平均评分")
    quality_score: float = Field(default=0.0, description="综合质量分")
    retrieval_boost: float = Field(default=1.0, description="群组 RAG 检索加权系数")
    is_in_my_library: bool = Field(default=False, description="当前用户是否已收藏到个人资料库")
    can_download: bool = Field(description="当前用户是否可下载")
    can_manage: bool = Field(description="当前用户是否可管理")


class GroupFileCategoryStat(BaseModel):
    """群文件分类统计"""
    category: str | None = Field(description="分类")
    count: int = Field(description="数量")


class GroupKnowledgeBaseDocumentCreate(BaseModel):
    """将群文件加入官方知识库"""

    file_id: UUID = Field(description="文件ID")
    category: str | None = Field(default=None, max_length=64, description="知识库分类")
    tags: list[str] | None = Field(default=None, description="知识库标签")


class GroupKnowledgeBaseStats(BaseModel):
    """群知识库统计"""

    total_documents: int = Field(default=0, description="文档总数")
    official_count: int = Field(default=0, description="官方文档数")
    verified_count: int = Field(default=0, description="已验证文档数")
    member_count: int = Field(default=0, description="成员文档数")
    total_downloads: int = Field(default=0, description="总下载次数")
    total_citations: int = Field(default=0, description="总引用次数")
    average_rating: float | None = Field(default=None, description="知识库平均评分")


class GroupKnowledgeBaseResponse(BaseModel):
    """群知识库列表响应"""

    group_id: UUID = Field(description="群组ID")
    collaborative_galaxy_id: UUID | None = Field(default=None, description="群协作星图ID")
    documents: list[GroupFileInfo] = Field(default_factory=list, description="知识库文档")
    stats: GroupKnowledgeBaseStats = Field(default_factory=GroupKnowledgeBaseStats, description="知识库统计")


class GroupCollaborativeGalaxyNode(BaseModel):
    """群协作星图节点"""

    id: str = Field(description="节点ID")
    label: str = Field(description="节点名称")
    node_type: str = Field(description="节点类型")
    trust_level: GroupFileTrustLevelEnum = Field(default=GroupFileTrustLevelEnum.MEMBER, description="信任等级")
    knowledge_base: bool = Field(default=True, description="是否来自知识库")
    file_id: UUID | None = Field(default=None, description="关联文件ID")
    source_document_id: UUID | None = Field(default=None, description="来源知识库文档ID")
    category: str | None = Field(default=None, description="分类")
    tags: list[str] = Field(default_factory=list, description="标签")
    quality_score: float = Field(default=0.0, description="综合质量分")
    citation_count: int = Field(default=0, description="引用次数")
    download_count: int = Field(default=0, description="下载次数")
    average_rating: float | None = Field(default=None, description="平均评分")
    position_x: float | None = Field(default=None, description="星图X坐标")
    position_y: float | None = Field(default=None, description="星图Y坐标")


class GroupCollaborativeGalaxyRelation(BaseModel):
    """群协作星图关系"""

    source_id: str = Field(description="起点节点ID")
    target_id: str = Field(description="终点节点ID")
    relation_type: str = Field(description="关系类型")
    strength: float = Field(default=1.0, description="关系强度")


class GroupCollaborativeGalaxyStats(BaseModel):
    """群协作星图统计"""

    total_nodes: int = Field(default=0, description="节点总数")
    document_nodes: int = Field(default=0, description="文档节点数")
    concept_nodes: int = Field(default=0, description="知识点节点数")
    total_relations: int = Field(default=0, description="关系总数")


class GroupCollaborativeGalaxyResponse(BaseModel):
    """群协作星图响应"""

    galaxy_id: UUID | None = Field(default=None, description="协作星图ID")
    group_id: UUID = Field(description="群组ID")
    name: str = Field(description="星图名称")
    scope: str = Field(description="星图作用域")
    nodes: list[GroupCollaborativeGalaxyNode] = Field(default_factory=list, description="节点")
    relations: list[GroupCollaborativeGalaxyRelation] = Field(default_factory=list, description="关系")
    edges: list[GroupCollaborativeGalaxyRelation] | None = Field(default=None, description="兼容 edges 字段")
    stats: GroupCollaborativeGalaxyStats = Field(default_factory=GroupCollaborativeGalaxyStats, description="星图统计")


# ============ 群任务 Schemas ============

class GroupTaskCreate(BaseModel):
    """创建群任务"""
    title: str = Field(min_length=2, max_length=200, description="任务标题")
    description: str | None = Field(default=None, max_length=1000, description="任务描述")
    tags: list[str] = Field(default_factory=list, max_length=5, description="标签")
    estimated_minutes: int = Field(default=10, ge=1, le=480, description="预估时长（分钟）")
    difficulty: int = Field(default=1, ge=1, le=5, description="难度等级")
    due_date: datetime | None = Field(default=None, description="截止日期")


class GroupTaskInfo(BaseSchema):
    """群任务信息"""
    title: str = Field(description="任务标题")
    description: str | None = Field(description="任务描述")
    tags: list[str] = Field(description="标签")
    estimated_minutes: int = Field(description="预估时长")
    difficulty: int = Field(description="难度等级")
    total_claims: int = Field(description="认领次数")
    total_completions: int = Field(description="完成次数")
    completion_rate: float = Field(description="完成率")
    due_date: datetime | None = Field(description="截止日期")
    creator: UserBrief = Field(description="创建者")

    # 当前用户状态
    is_claimed_by_me: bool = Field(default=False, description="是否已认领")
    my_completion_status: bool | None = Field(default=None, description="我的完成状态")


# ============ 打卡 Schemas ============

class CheckinRequest(BaseModel):
    """打卡请求"""
    group_id: UUID = Field(description="群组ID")
    message: str | None = Field(default=None, max_length=200, description="打卡留言")
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
    flames: list[FlameStatus] = Field(description="所有成员的火苗")
    bonfire_level: int = Field(ge=1, le=5, description="火堆等级")


# ============ 共享资源 Schemas ============

class SharedResourceTypeEnum(StrEnum):
    PLAN = "plan"
    TASK = "task"
    KNOWLEDGE_NODE = "knowledge_node"
    SEED_LIBRARY = "seed_library"
    SEED_ITEM = "seed_item"
    COGNITIVE_FRAGMENT = "cognitive_fragment"
    CURIOSITY_CAPSULE = "curiosity_capsule"
    COGNITIVE_PRISM_PATTERN = "cognitive_prism_pattern"


class SharedResourceCreate(BaseModel):
    """创建共享资源请求"""
    resource_type: SharedResourceTypeEnum = Field(description="资源类型")
    resource_id: UUID = Field(description="资源ID")
    target_group_id: UUID | None = Field(default=None, description="分享给群组ID")
    target_user_id: UUID | None = Field(default=None, description="分享给好友ID")
    permission: str = Field(default="view", pattern="^(view|comment|edit|adopt|fork)$", description="权限")
    comment: str | None = Field(default=None, max_length=500, description="分享留言")


class SharedResourceInfo(BaseSchema):
    """共享资源信息"""
    resource_type: str = Field(description="资源类型") # Simplified for response
    # We return the embedded object if possible, or just IDs?
    # Ideally return a summary of the object.
    # For simplicity, we return generic info and client fetches details if needed,
    # OR we embed a brief summary.

    # IDs
    plan_id: UUID | None = None
    task_id: UUID | None = None
    knowledge_node_id: UUID | None = None
    seed_library_id: UUID | None = None
    seed_item_id: UUID | None = None
    cognitive_fragment_id: UUID | None = None
    curiosity_capsule_id: UUID | None = None
    behavior_pattern_id: UUID | None = None
    card_share_record_id: UUID | None = None

    # Metadata
    permission: str
    comment: str | None
    view_count: int
    save_count: int

    # FV-22: Quality scoring
    quality_score: float = 0.0
    quality_hidden: bool = False
    adoption_count: int = 0
    avg_rating: float | None = None

    sharer: UserBrief

    # Embedded Briefs (Optional)
    # Ideally we'd have a 'resource_title' or 'resource_summary' field computed
    resource_title: str | None = None
    resource_summary: str | None = None
    entity_card: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


# ============ COM-011: 同目标伙伴 ============

class SimilarGoalPursuer(BaseModel):
    """与当前用户追求相似目标的其他用户"""
    user_id: UUID = Field(description="用户ID")
    display_name: str = Field(description="显示名称")
    avatar_url: str | None = Field(default=None, description="头像URL")
    goal_title: str = Field(description="对方的目标标题")
    goal_type: str = Field(default="general", description="目标类型")
    goal_progress: float = Field(default=0.0, description="目标进度 0-1")
    similarity: float = Field(default=0.0, description="目标相似度 0-1")
    last_active: datetime | None = Field(default=None, description="最近活跃时间")
    mutual_friends_count: int = Field(default=0, description="共同好友数")

    model_config = ConfigDict(from_attributes=True)


# ============ 私聊消息 Schemas ============

class PrivateMessageSend(BaseModel):
    """发送私聊消息"""
    target_user_id: UUID = Field(description="接收用户ID")
    message_type: MessageTypeEnum = Field(default=MessageTypeEnum.TEXT, description="消息类型")
    content: str | None = Field(default=None, max_length=2000, description="消息内容")
    content_data: dict[str, Any] | None = Field(default=None, description="结构化内容")
    reply_to_id: UUID | None = Field(default=None, description="回复的消息ID")
    thread_root_id: UUID | None = Field(default=None, description="线程根消息ID")
    mention_user_ids: list[UUID] | None = Field(default=None, description="提及用户ID列表")
    nonce: str | None = Field(default=None, description="客户端生成的随机串，用于ACK确认")

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
        if msg_type == MessageTypeEnum.FILE_SHARE and (not isinstance(v, dict) or not v.get('file_id')):
            raise ValueError('文件消息必须包含 file_id')
        return v


class PrivateMessageInfo(BaseSchema):
    """私聊消息信息"""
    sender: UserBrief = Field(description="发送者")
    receiver: UserBrief = Field(description="接收者")
    message_type: MessageTypeEnum = Field(description="消息类型")
    content: str | None = Field(description="消息内容")
    content_data: dict[str, Any] | None = Field(description="结构化内容")
    reply_to_id: UUID | None = Field(description="回复的消息ID")
    thread_root_id: UUID | None = Field(default=None, description="线程根消息ID")
    mention_user_ids: list[UUID] | None = Field(default=None, description="提及用户ID列表")
    reactions: dict[str, list[UUID]] | None = Field(default=None, description="表情反应")
    is_revoked: bool = Field(default=False, description="是否已撤回")
    revoked_at: datetime | None = Field(default=None, description="撤回时间")
    edited_at: datetime | None = Field(default=None, description="编辑时间")
    is_read: bool = Field(description="是否已读")
    read_at: datetime | None = Field(description="阅读时间")
    quoted_message: PrivateMessageInfo | None = Field(default=None, description="引用消息详情")

# Handle recursive references
MessageInfo.model_rebuild()
PrivateMessageInfo.model_rebuild()


# ============ 加密相关 Schemas ============

class EncryptionKeyCreate(BaseModel):
    """创建加密密钥"""
    public_key: str = Field(description="Base64编码的公钥")
    key_type: str = Field(default="x25519", pattern="^(x25519|rsa)$", description="密钥类型")
    device_id: str | None = Field(default=None, max_length=100, description="设备ID")


class EncryptionKeyInfo(BaseSchema):
    """加密密钥信息"""
    public_key: str = Field(description="Base64编码的公钥")
    key_type: str = Field(description="密钥类型")
    device_id: str | None = Field(description="设备ID")
    is_active: bool = Field(description="是否激活")
    expires_at: datetime | None = Field(description="过期时间")


class EncryptedMessageSend(BaseModel):
    """发送加密消息"""
    encrypted_content: str = Field(description="加密后的内容")
    content_signature: str | None = Field(default=None, max_length=512, description="消息签名")
    encryption_version: int = Field(default=1, ge=1, le=10, description="加密版本")
    # 其他字段同普通消息
    message_type: MessageTypeEnum = Field(default=MessageTypeEnum.TEXT)
    content_data: dict[str, Any] | None = Field(default=None)
    reply_to_id: UUID | None = Field(default=None)
    nonce: str | None = Field(default=None)


# ============ 举报相关 Schemas ============

class ReportReasonEnum(StrEnum):
    SPAM = "spam"
    HARASSMENT = "harassment"
    VIOLENCE = "violence"
    HATE_SPEECH = "hate_speech"
    MISINFORMATION = "misinformation"
    INAPPROPRIATE = "inappropriate"
    OTHER = "other"


class ReportStatusEnum(StrEnum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    DISMISSED = "dismissed"
    ACTIONED = "actioned"


class ModerationActionEnum(StrEnum):
    WARN = "warn"
    MUTE = "mute"
    KICK = "kick"
    BAN = "ban"


class MessageReportCreate(BaseModel):
    """创建消息举报"""
    group_message_id: UUID | None = Field(default=None, description="群消息ID")
    private_message_id: UUID | None = Field(default=None, description="私聊消息ID")
    reason: ReportReasonEnum = Field(description="举报原因")
    description: str | None = Field(default=None, max_length=500, description="详细描述")


class MessageReportInfo(BaseSchema):
    """消息举报信息"""
    reporter: UserBrief = Field(description="举报人")
    reason: ReportReasonEnum = Field(description="举报原因")
    description: str | None = Field(description="详细描述")
    status: ReportStatusEnum = Field(description="状态")
    reviewed_by: UserBrief | None = Field(default=None, description="审核人")
    reviewed_at: datetime | None = Field(default=None, description="审核时间")
    action_taken: ModerationActionEnum | None = Field(default=None, description="处理动作")


class MessageReportReview(BaseModel):
    """审核消息举报"""
    status: ReportStatusEnum = Field(description="审核状态")
    action_taken: ModerationActionEnum | None = Field(default=None, description="处理动作")


# ============ 收藏相关 Schemas ============

class MessageFavoriteCreate(BaseModel):
    """创建消息收藏"""
    group_message_id: UUID | None = Field(default=None, description="群消息ID")
    private_message_id: UUID | None = Field(default=None, description="私聊消息ID")
    note: str | None = Field(default=None, max_length=500, description="个人备注")
    tags: list[str] | None = Field(default=None, max_length=10, description="自定义标签")


class MessageFavoriteInfo(BaseSchema):
    """消息收藏信息"""
    user_id: UUID = Field(description="收藏用户ID")
    group_message_id: UUID | None = Field(default=None)
    private_message_id: UUID | None = Field(default=None)
    note: str | None = Field(default=None)
    tags: list[str] | None = Field(default=None)
    # 可选：嵌入消息摘要
    message_preview: str | None = Field(default=None, description="消息预览")
    group_message: MessageInfo | None = Field(default=None, description="群消息详情")
    private_message: PrivateMessageInfo | None = Field(default=None, description="私聊消息详情")


# ============ 转发相关 Schemas ============

class MessageForwardRequest(BaseModel):
    """转发消息请求"""
    source_message_id: UUID = Field(description="源消息ID")
    source_type: str = Field(pattern="^(group|private)$", description="源消息类型")
    target_group_id: UUID | None = Field(default=None, description="目标群组ID")
    target_user_id: UUID | None = Field(default=None, description="目标用户ID")
    comment: str | None = Field(default=None, max_length=200, description="转发留言")


# ============ 广播相关 Schemas ============

class BroadcastMessageCreate(BaseModel):
    """创建跨群广播"""
    content: str = Field(min_length=1, max_length=2000, description="广播内容")
    content_data: dict[str, Any] | None = Field(default=None, description="结构化内容")
    target_group_ids: list[UUID] = Field(min_length=1, max_length=50, description="目标群组ID列表")


class BroadcastMessageInfo(BaseSchema):
    """广播消息信息"""
    sender: UserBrief = Field(description="发送者")
    content: str = Field(description="广播内容")
    content_data: dict[str, Any] | None = Field(description="结构化内容")
    target_group_ids: list[UUID] = Field(description="目标群组ID列表")
    delivered_count: int = Field(description="已送达数量")


# ============ 群管理相关 Schemas ============

class GroupAnnouncementUpdate(BaseModel):
    """更新群公告"""
    announcement: str | None = Field(default=None, max_length=2000, description="群公告内容")


class GroupModerationSettings(BaseModel):
    """群管理设置"""
    keyword_filters: list[str] | None = Field(default=None, max_length=100, description="敏感词列表")
    mute_all: bool | None = Field(default=None, description="全员禁言")
    slow_mode_seconds: int | None = Field(default=None, ge=0, le=3600, description="慢速模式秒数")


class MemberMuteRequest(BaseModel):
    """禁言成员请求"""
    user_id: UUID = Field(description="用户ID")
    duration_minutes: int = Field(ge=1, le=43200, description="禁言时长（分钟）")  # 最多30天
    reason: str | None = Field(default=None, max_length=200, description="禁言原因")


class MemberWarnRequest(BaseModel):
    """警告成员请求"""
    user_id: UUID = Field(description="用户ID")
    reason: str = Field(min_length=1, max_length=200, description="警告原因")


# ============ 离线队列相关 Schemas ============

class OfflineMessageStatusEnum(StrEnum):
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
    error_message: str | None = Field(default=None, description="错误信息")
    created_at: datetime = Field(description="创建时间")


class OfflineMessageRetryRequest(BaseModel):
    """重试离线消息请求"""
    message_ids: list[UUID] = Field(min_length=1, max_length=50, description="消息ID列表")


# ============ 搜索相关 Schemas ============

class MessageSearchRequest(BaseModel):
    """消息搜索请求"""
    keyword: str | None = Field(default=None, max_length=100, description="关键词")
    sender_id: UUID | None = Field(default=None, description="发送者ID")
    start_date: datetime | None = Field(default=None, description="开始时间")
    end_date: datetime | None = Field(default=None, description="结束时间")
    message_types: list[MessageTypeEnum] | None = Field(default=None, description="消息类型")
    topic: str | None = Field(default=None, max_length=100, description="话题")
    tags: list[str] | None = Field(default=None, max_length=10, description="标签")
    has_attachments: bool | None = Field(default=None, description="是否有附件")
    # 分页
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")


class MessageSearchResult(BaseModel):
    """消息搜索结果"""
    messages: list[MessageInfo] = Field(description="消息列表")
    total: int = Field(description="总数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页数量")
    has_more: bool = Field(description="是否有更多")


# ============ 拉黑相关 Schemas ============

class BlockUserRequest(BaseModel):
    """拉黑用户请求"""
    target_user_id: UUID = Field(description="要拉黑的用户ID")
    reason: str | None = Field(default=None, max_length=500, description="拉黑原因")


class BlockUserInfo(BaseSchema):
    """被拉黑用户信息"""
    blocked_user: UserBrief = Field(description="被拉黑的用户")
    reason: str | None = Field(default=None, description="拉黑原因")


class SearchVisibilityEnum(StrEnum):
    """搜索可见性设置"""
    EVERYONE = "everyone"
    FRIENDS = "friends"
    NOBODY = "nobody"


class UserPrivacySettings(BaseModel):
    """用户隐私设置"""
    searchable_by: SearchVisibilityEnum = Field(description="谁可以搜索到我")


# ============ 消息撤回配置 ============

# 从settings导入配置
def get_message_revoke_time_limit() -> int:
    """获取消息撤回时间限制（秒）"""
    from app.config import settings
    return getattr(settings, 'MESSAGE_REVOKE_TIME_LIMIT_SECONDS', 120)


# 保留常量作为默认值（向后兼容）
MESSAGE_REVOKE_TIME_LIMIT_SECONDS = 120  # 2分钟内可撤回

RecommendationFeedbackPrompt.model_rebuild()
