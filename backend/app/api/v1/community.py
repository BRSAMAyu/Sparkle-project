"""
社群功能 API 路由
Community API - 好友、群组、消息、打卡、任务相关接口
"""
import json
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID

from app.db.session import get_db
from app.core.security import decode_token
from app.api.deps import get_current_user
from app.core.websocket import manager
from app.core.rate_limiting import limiter
from app.models.user import User, UserStatus
from app.models.community import GroupType, GroupMember, GroupRole
from app.models.group_files import GroupFile
from app.models.plan import Plan
from app.models.task import Task
from app.models.cognitive import CognitiveFragment, BehaviorPattern
from app.models.curiosity_capsule import CuriosityCapsule
from app.schemas.community import (
    # 好友
    FriendRequest, FriendResponse, FriendshipInfo, FriendRecommendation,
    # 群组
    GroupCreate, GroupUpdate, GroupInfo, GroupListItem, GroupMemberInfo,
    MemberRoleUpdate, UserBrief,
    # 消息
    MessageSend, MessageInfo, MessageEdit, MessageReactionUpdate,
    PrivateMessageSend, PrivateMessageInfo,
    # 群文件
    GroupFileShareRequest, GroupFilePermissionUpdate, GroupFileInfo, GroupFileCategoryStat, GroupFilePermissions,
    # 任务
    GroupTaskCreate, GroupTaskInfo,
    # 状态
    UserStatusUpdate,
    # 其他
    CheckinRequest, CheckinResponse,
    # 打卡
    CheckinRequest, CheckinResponse,
    # 火堆
    GroupFlameStatus, FlameStatus,
    # 共享资源
    SharedResourceCreate, SharedResourceInfo,
    # 枚举
    GroupTypeEnum, GroupRoleEnum, SharedResourceTypeEnum, MessageTypeEnum, ReactionActionEnum,
    # 加密相关
    EncryptionKeyCreate, EncryptionKeyInfo, EncryptedMessageSend,
    # 举报相关
    MessageReportCreate, MessageReportInfo, MessageReportReview, ReportStatusEnum,
    # 收藏相关
    MessageFavoriteCreate, MessageFavoriteInfo,
    # 转发相关
    MessageForwardRequest,
    # 广播相关
    BroadcastMessageCreate, BroadcastMessageInfo,
    # 群管理相关
    GroupAnnouncementUpdate, GroupModerationSettings, MemberMuteRequest, MemberWarnRequest,
    # 离线队列相关
    OfflineMessageInfo, OfflineMessageRetryRequest, OfflineMessageStatusEnum,
    # 搜索相关
    MessageSearchRequest, MessageSearchResult
)
from app.services.community_service import (
    FriendshipService, GroupService, GroupMessageService,
    CheckinService, GroupTaskService, PrivateMessageService
)
from app.services.group_file_service import GroupFileService
from app.services.collaboration_service import collaboration_service
from app.services.community_advanced_service import (
    EncryptionService, ModerationService, ReportService, FavoriteService,
    ForwardService, BroadcastService, MessageSearchService, OfflineQueueService
)
from app.models.community import SharedResourceType, GroupMessage, PrivateMessage
from app.db.session import AsyncSessionLocal

router = APIRouter()

def _build_message_info(msg: GroupMessage) -> MessageInfo:
    sender = None
    if msg.sender:
        sender = UserBrief(
            id=msg.sender.id,
            username=msg.sender.username,
            nickname=msg.sender.nickname,
            avatar_url=msg.sender.avatar_url,
            flame_level=msg.sender.flame_level,
            flame_brightness=msg.sender.flame_brightness
        )
    
    quoted_message = None
    if msg.reply_to:
        # Simplified quote (1 level recursion)
        quoted_sender = None
        if msg.reply_to.sender:
             quoted_sender = UserBrief(
                id=msg.reply_to.sender.id,
                username=msg.reply_to.sender.username,
                nickname=msg.reply_to.sender.nickname,
                avatar_url=msg.reply_to.sender.avatar_url,
                flame_level=msg.reply_to.sender.flame_level,
                flame_brightness=msg.reply_to.sender.flame_brightness
            )
        quoted_message = MessageInfo(
            id=msg.reply_to.id,
            created_at=msg.reply_to.created_at,
            updated_at=msg.reply_to.updated_at,
            sender=quoted_sender,
            message_type=msg.reply_to.message_type,
            content=msg.reply_to.content,
            content_data=msg.reply_to.content_data,
            reply_to_id=msg.reply_to.reply_to_id,
            thread_root_id=msg.reply_to.thread_root_id,
            mention_user_ids=msg.reply_to.mention_user_ids,
            reactions=msg.reply_to.reactions,
            is_revoked=msg.reply_to.is_revoked,
            revoked_at=msg.reply_to.revoked_at,
            edited_at=msg.reply_to.edited_at,
            quoted_message=None # Stop recursion
        )

    return MessageInfo(
        id=msg.id,
        created_at=msg.created_at,
        updated_at=msg.updated_at,
        sender=sender,
        message_type=msg.message_type,
        content=msg.content,
        content_data=msg.content_data,
        reply_to_id=msg.reply_to_id,
        thread_root_id=msg.thread_root_id,
        mention_user_ids=msg.mention_user_ids,
        reactions=msg.reactions,
        is_revoked=msg.is_revoked,
        revoked_at=msg.revoked_at,
        edited_at=msg.edited_at,
        quoted_message=quoted_message
    )


def _build_group_file_info(group_file: GroupFile, member_role) -> GroupFileInfo:
    shared_by = None
    if group_file.shared_by:
        shared_by = UserBrief(
            id=group_file.shared_by.id,
            username=group_file.shared_by.username,
            nickname=group_file.shared_by.nickname,
            avatar_url=group_file.shared_by.avatar_url,
            flame_level=group_file.shared_by.flame_level,
            flame_brightness=group_file.shared_by.flame_brightness
        )

    stored_file = group_file.file
    return GroupFileInfo(
        id=group_file.id,
        created_at=group_file.created_at,
        updated_at=group_file.updated_at,
        group_id=group_file.group_id,
        file_id=group_file.file_id,
        shared_by=shared_by,
        category=group_file.category,
        tags=group_file.tags or [],
        view_role=group_file.view_role,
        download_role=group_file.download_role,
        manage_role=group_file.manage_role,
        file_name=stored_file.file_name,
        mime_type=stored_file.mime_type,
        file_size=stored_file.file_size,
        status=stored_file.status,
        visibility=stored_file.visibility,
        can_download=GroupFileService.can_download(member_role, group_file.download_role),
        can_manage=GroupFileService.can_manage(member_role, group_file.manage_role),
    )

def _build_private_message_info(msg: PrivateMessage) -> PrivateMessageInfo:
    sender = UserBrief.model_validate(msg.sender)
    receiver = UserBrief.model_validate(msg.receiver)
    
    quoted_message = None
    if msg.reply_to:
        # Simplified quote (1 level recursion)
        q_sender = UserBrief.model_validate(msg.reply_to.sender)
        q_receiver = UserBrief.model_validate(msg.reply_to.receiver)
        
        quoted_message = PrivateMessageInfo(
            id=msg.reply_to.id,
            created_at=msg.reply_to.created_at,
            updated_at=msg.reply_to.updated_at,
            sender=q_sender,
            receiver=q_receiver,
            message_type=msg.reply_to.message_type,
            content=msg.reply_to.content,
            content_data=msg.reply_to.content_data,
            reply_to_id=msg.reply_to.reply_to_id,
            thread_root_id=msg.reply_to.thread_root_id,
            mention_user_ids=msg.reply_to.mention_user_ids,
            reactions=msg.reply_to.reactions,
            is_revoked=msg.reply_to.is_revoked,
            revoked_at=msg.reply_to.revoked_at,
            edited_at=msg.reply_to.edited_at,
            is_read=msg.reply_to.is_read,
            read_at=msg.reply_to.read_at,
            quoted_message=None
        )

    return PrivateMessageInfo(
        id=msg.id,
        created_at=msg.created_at,
        updated_at=msg.updated_at,
        sender=sender,
        receiver=receiver,
        message_type=msg.message_type,
        content=msg.content,
        content_data=msg.content_data,
        reply_to_id=msg.reply_to_id,
        thread_root_id=msg.thread_root_id,
        mention_user_ids=msg.mention_user_ids,
        reactions=msg.reactions,
        is_revoked=msg.is_revoked,
        revoked_at=msg.revoked_at,
        edited_at=msg.edited_at,
        is_read=msg.is_read,
        read_at=msg.read_at,
        quoted_message=quoted_message
    )

def _is_self_only_visibility(content_data: Optional[dict], user_id: UUID) -> bool:
    if not content_data:
        return False
    if content_data.get("visibility") != "self":
        return False
    visible_to = content_data.get("visible_to")
    if visible_to is None:
        return False
    if isinstance(visible_to, list):
        return str(user_id) in [str(item) for item in visible_to]
    return str(visible_to) == str(user_id)

def _normalize_self_visibility(content_data: Optional[dict], user_id: UUID) -> Optional[dict]:
    if not content_data:
        return content_data
    if content_data.get("visibility") != "self":
        return content_data
    if content_data.get("visible_to") is not None:
        return content_data
    updated = dict(content_data)
    updated["visible_to"] = str(user_id)
    return updated

def _truncate_text(text: Optional[str], limit: int = 160) -> Optional[str]:
    if not text:
        return None
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: max(0, limit - 3)].rstrip()}..."

def _compact_dict(data: dict) -> dict:
    return {k: v for k, v in data.items() if v is not None}

def _build_share_meta(resource_type: SharedResourceType, resource: object) -> dict:
    if resource_type == SharedResourceType.PLAN:
        plan = resource
        return _compact_dict({
            "plan_type": plan.type.value if plan.type else None,
            "subject": plan.subject,
            "progress": plan.progress,
            "target_date": plan.target_date.isoformat() if plan.target_date else None,
            "total_estimated_hours": plan.total_estimated_hours,
        })
    if resource_type == SharedResourceType.TASK:
        task = resource
        return _compact_dict({
            "task_type": task.type.value if task.type else None,
            "status": task.status.value if task.status else None,
            "estimated_minutes": task.estimated_minutes,
            "difficulty": task.difficulty,
            "tags": task.tags or [],
            "due_date": task.due_date.isoformat() if task.due_date else None,
        })
    if resource_type == SharedResourceType.CURIOSITY_CAPSULE:
        capsule = resource
        return _compact_dict({
            "related_subject": capsule.related_subject,
            "related_task_id": str(capsule.related_task_id) if capsule.related_task_id else None,
        })
    if resource_type == SharedResourceType.COGNITIVE_PRISM_PATTERN:
        pattern = resource
        return _compact_dict({
            "pattern_type": pattern.pattern_type,
            "confidence_score": pattern.confidence_score,
            "frequency": pattern.frequency,
            "is_archived": pattern.is_archived,
        })
    fragment = resource
    return _compact_dict({
        "source_type": fragment.source_type,
        "severity": fragment.severity,
        "tags": fragment.tags,
        "error_tags": fragment.error_tags,
        "context_tags": fragment.context_tags,
    })

def _build_share_brief(resource_type: SharedResourceType, resource: object) -> dict:
    if resource_type == SharedResourceType.PLAN:
        plan = resource
        title = plan.name
        summary = plan.description or plan.subject
    elif resource_type == SharedResourceType.TASK:
        task = resource
        title = task.title
        summary = task.user_note or task.guide_content
    elif resource_type == SharedResourceType.CURIOSITY_CAPSULE:
        capsule = resource
        title = capsule.title
        summary = capsule.content
    elif resource_type == SharedResourceType.COGNITIVE_PRISM_PATTERN:
        pattern = resource
        title = pattern.pattern_name
        summary = pattern.description or pattern.solution_text
    else:
        fragment = resource
        title = _truncate_text(fragment.content, 48) or "Cognitive Fragment"
        summary = fragment.content

    return {
        "title": title,
        "summary": _truncate_text(summary, 160),
        "meta": _build_share_meta(resource_type, resource)
    }

def _share_message_type(resource_type: SharedResourceType) -> MessageTypeEnum:
    if resource_type == SharedResourceType.PLAN:
        return MessageTypeEnum.PLAN_SHARE
    if resource_type == SharedResourceType.TASK:
        return MessageTypeEnum.TASK_SHARE
    if resource_type == SharedResourceType.CURIOSITY_CAPSULE:
        return MessageTypeEnum.CAPSULE_SHARE
    if resource_type == SharedResourceType.COGNITIVE_PRISM_PATTERN:
        return MessageTypeEnum.PRISM_SHARE
    return MessageTypeEnum.FRAGMENT_SHARE

async def _get_share_resource(
    db: AsyncSession,
    resource_type: SharedResourceType,
    resource_id: UUID,
    owner_id: UUID
):
    if resource_type == SharedResourceType.PLAN:
        plan = await db.get(Plan, resource_id)
        if not plan:
            raise HTTPException(status_code=404, detail="计划不存在")
        if plan.user_id != owner_id:
            raise HTTPException(status_code=403, detail="无权限分享该计划")
        return plan
    if resource_type == SharedResourceType.TASK:
        task = await db.get(Task, resource_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        if task.user_id != owner_id:
            raise HTTPException(status_code=403, detail="无权限分享该任务")
        return task
    if resource_type == SharedResourceType.CURIOSITY_CAPSULE:
        capsule = await db.get(CuriosityCapsule, resource_id)
        if not capsule:
            raise HTTPException(status_code=404, detail="好奇心胶囊不存在")
        if capsule.user_id != owner_id:
            raise HTTPException(status_code=403, detail="无权限分享该好奇心胶囊")
        return capsule
    if resource_type == SharedResourceType.COGNITIVE_PRISM_PATTERN:
        pattern = await db.get(BehaviorPattern, resource_id)
        if not pattern:
            raise HTTPException(status_code=404, detail="认知棱镜不存在")
        if pattern.user_id != owner_id:
            raise HTTPException(status_code=403, detail="无权限分享该认知棱镜")
        return pattern
    fragment = await db.get(CognitiveFragment, resource_id)
    if not fragment:
        raise HTTPException(status_code=404, detail="认知碎片不存在")
    if fragment.user_id != owner_id:
        raise HTTPException(status_code=403, detail="无权限分享该认知碎片")
    return fragment


# ============ 好友系统 ============

@router.post("/friends/request", summary="发送好友请求")
@limiter.limit("5/minute")
async def send_friend_request(
    request: Request,
    data: FriendRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    发送好友请求

    - **target_user_id**: 目标用户ID
    - **message**: 可选的请求消息
    """
    try:
        friendship = await FriendshipService.send_friend_request(
            db, current_user.id, data.target_user_id
        )
        await db.commit()
        return {"success": True, "friendship_id": str(friendship.id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/friends/respond", summary="响应好友请求")
async def respond_to_friend_request(
    data: FriendResponse,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """接受或拒绝好友请求"""
    try:
        await FriendshipService.respond_to_request(
            db, current_user.id, data.friendship_id, data.accept
        )
        await db.commit()
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/friends", response_model=List[FriendshipInfo], summary="获取好友列表")
async def get_friends(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户的好友列表"""
    friends = await FriendshipService.get_friends(db, current_user.id, limit=limit, offset=offset)
    result = []
    for friendship, friend in friends:
        result.append(FriendshipInfo(
            id=friendship.id,
            created_at=friendship.created_at,
            updated_at=friendship.updated_at,
            friend=UserBrief(
                id=friend.id,
                username=friend.username,
                nickname=friend.nickname,
                avatar_url=friend.avatar_url,
                flame_level=friend.flame_level,
                flame_brightness=friend.flame_brightness
            ),
            status=friendship.status,
            match_reason=friendship.match_reason,
            initiated_by_me=friendship.initiated_by == current_user.id
        ))
    return result


@router.get("/friends/pending", summary="获取待处理的好友请求")
async def get_pending_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取收到的待处理好友请求"""
    requests = await FriendshipService.get_pending_requests(db, current_user.id)
    return requests


@router.get("/users/search", response_model=List[UserBrief], summary="搜索用户")
@limiter.limit("20/minute")
async def search_users(
    request: Request,
    keyword: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    搜索用户（用于添加好友）
    
    支持按用户名或昵称搜索
    """
    from sqlalchemy import select, or_
    
    # Simple search implementation
    stmt = select(User).where(
        or_(
            User.username.ilike(f"%{keyword}%"),
            User.nickname.ilike(f"%{keyword}%")
        )
    ).where(
        User.id != current_user.id,
        User.is_active == True
    ).limit(limit)
    
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    return [
        UserBrief(
            id=user.id,
            username=user.username,
            nickname=user.nickname,
            avatar_url=user.avatar_url,
            flame_level=user.flame_level,
            flame_brightness=user.flame_brightness
        ) for user in users
    ]


# ============ WebSocket ============

@router.websocket("/groups/{group_id}/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    group_id: UUID,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    群组实时通讯 WebSocket 接口
    连接地址: ws://host/api/v1/community/groups/{group_id}/ws?token={jwt_token}
    """
    try:
        # 验证 Token
        payload = decode_token(token, expected_type="access")
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4003)
            return

        membership_result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == UUID(user_id),
                GroupMember.not_deleted_filter()
            )
        )
        if not membership_result.scalar_one_or_none():
            await websocket.close(code=4003)
            return
            
        # 建立连接
        await manager.connect(websocket, str(group_id), user_id)
        
        try:
            while True:
                # 保持连接活跃，接收客户端消息（如果有）
                # 目前主要用于服务器推送，客户端发送走 HTTP POST
                raw_data = await websocket.receive_text()
                try:
                    data = json.loads(raw_data)
                    if isinstance(data, dict) and data.get("type") == "typing":
                        # Add user_id to identify sender and broadcast
                        data["user_id"] = user_id
                        await manager.broadcast(data, str(group_id))
                except:
                    # Non-json or other messages, ignore
                    pass
        except WebSocketDisconnect:
            manager.disconnect(websocket, str(group_id), user_id)
            
    except Exception as e:
        print(f"WebSocket Error: {e}")
        # 尝试关闭连接
        try:
            await websocket.close()
        except:
            pass


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
    group = await GroupService.create_group(db, current_user.id, data)
    await db.commit()
    group_info = await GroupService.get_group(db, group.id, current_user.id)
    return group_info


@router.get("/groups/{group_id}", response_model=GroupInfo, summary="获取群组详情")
async def get_group(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取群组详细信息"""
    group = await GroupService.get_group(db, group_id, current_user.id)
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    return group


@router.post("/groups/{group_id}/join", summary="加入群组")
async def join_group(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """加入群组"""
    try:
        await GroupService.join_group(db, group_id, current_user.id)
        await db.commit()
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/groups/{group_id}/leave", summary="退出群组")
async def leave_group(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """退出群组"""
    try:
        await GroupService.leave_group(db, group_id, current_user.id)
        await db.commit()
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/groups/{group_id}", summary="解散群组")
async def dissolve_group(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """解散群组（仅限群主）"""
    try:
        await GroupService.dissolve_group(db, group_id, current_user.id)
        await db.commit()
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/groups/{group_id}/transfer", summary="转让群主")
async def transfer_group_owner(
    group_id: UUID,
    new_owner_id: UUID = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """转让群主身份"""
    try:
        await GroupService.transfer_owner(db, group_id, current_user.id, new_owner_id)
        await db.commit()
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/groups", response_model=List[GroupListItem], summary="获取我的群组")
async def get_my_groups(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户加入的所有群组"""
    return await GroupService.get_my_groups(db, current_user.id)


@router.get("/groups/search", response_model=List[GroupListItem], summary="搜索公开群组")
async def search_groups(
    keyword: Optional[str] = None,
    group_type: Optional[GroupTypeEnum] = None,
    tags: Optional[List[str]] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """搜索公开群组"""
    # Convert enum to model enum if provided
    model_type = GroupType(group_type.value) if group_type else None
    groups = await GroupService.search_groups(db, keyword, model_type, tags, limit)

    result = []
    for group_dict in groups:
        days_remaining = None
        deadline = group_dict.get('deadline')
        if deadline:
            from datetime import datetime
            delta = deadline - datetime.utcnow()
            days_remaining = max(0, delta.days)

        result.append(GroupListItem(
            id=group_dict['id'],
            name=group_dict['name'],
            type=GroupTypeEnum(group_dict['type'].value),
            member_count=group_dict['member_count'], 
            total_flame_power=group_dict['total_flame_power'],
            deadline=deadline,
            days_remaining=days_remaining,
            focus_tags=group_dict.get('focus_tags', [])
        ))
    return result


# ============ 群消息 ============

@router.post("/groups/{group_id}/messages", response_model=MessageInfo, summary="发送群消息")
async def send_message(
    group_id: UUID,
    data: MessageSend,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """发送群消息"""
    try:
        data.content_data = _normalize_self_visibility(data.content_data, current_user.id)
        message = await GroupMessageService.send_message(db, group_id, current_user.id, data)
        await db.commit()

        message_info = _build_message_info(message)

        is_self_only = _is_self_only_visibility(data.content_data, current_user.id)

        # 广播消息到 WebSocket
        if not is_self_only:
            await manager.broadcast(message_info.model_dump(mode='json'), str(group_id))

        # 提及通知
        if message.mention_user_ids and not is_self_only:
            for mentioned_id in message.mention_user_ids:
                if str(mentioned_id) == str(current_user.id):
                    continue
                await manager.send_personal_message({
                    "type": "mention",
                    "group_id": str(group_id),
                    "message": message_info.model_dump(mode='json')
                }, str(mentioned_id))

        # 回传 ACK 给发送者
        if data.nonce:
            await manager.send_personal_message({
                "type": "ack",
                "nonce": data.nonce,
                "message_id": str(message.id),
                "timestamp": message.created_at.isoformat()
            }, str(current_user.id))

        return message_info
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/groups/{group_id}/messages", response_model=List[MessageInfo], summary="获取群消息")
async def get_messages(
    group_id: UUID,
    before_id: Optional[UUID] = None,
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取群消息（分页）"""
    try:
        messages = await GroupMessageService.get_messages(db, group_id, current_user.id, before_id, limit)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

    result = []
    for msg in messages:
        result.append(_build_message_info(msg))
    return result


# ============ 群文件 ============

@router.post("/groups/{group_id}/files/{file_id}/share", response_model=GroupFileInfo, summary="分享文件到群组")
async def share_group_file(
    group_id: UUID,
    file_id: UUID,
    data: GroupFileShareRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        permissions = data.permissions or GroupFilePermissions()
        group_file, stored_file = await GroupFileService.share_file(
            db,
            group_id=group_id,
            user_id=current_user.id,
            file_id=file_id,
            category=data.category,
            tags=data.tags,
            view_role=GroupRole(permissions.view_role.value),
            download_role=GroupRole(permissions.download_role.value),
            manage_role=GroupRole(permissions.manage_role.value),
        )

        if data.send_message:
            message_payload = MessageSend(
                message_type=MessageTypeEnum.FILE_SHARE,
                content=stored_file.file_name,
                content_data={
                    "file_id": str(stored_file.id),
                    "file_name": stored_file.file_name,
                    "mime_type": stored_file.mime_type,
                    "file_size": stored_file.file_size,
                    "status": stored_file.status,
                },
            )
            message = await GroupMessageService.send_message(
                db,
                group_id,
                current_user.id,
                message_payload,
            )
            message_info = _build_message_info(message)
            await manager.broadcast(message_info.model_dump(mode="json"), str(group_id))

        await db.commit()
        member = await GroupFileService._require_member(db, group_id, current_user.id)
        return _build_group_file_info(group_file, member.role)
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/groups/{group_id}/files", response_model=List[GroupFileInfo], summary="获取群文件列表")
async def list_group_files(
    group_id: UUID,
    category: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        group_files, member_role = await GroupFileService.list_files(
            db,
            group_id=group_id,
            user_id=current_user.id,
            category=category,
            limit=limit,
            offset=offset,
        )
        return [_build_group_file_info(item, member_role) for item in group_files]
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.put("/groups/{group_id}/files/{file_id}/permissions", response_model=GroupFileInfo, summary="更新群文件权限")
async def update_group_file_permissions(
    group_id: UUID,
    file_id: UUID,
    data: GroupFilePermissionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        permissions = data.permissions
        group_file = await GroupFileService.update_permissions(
            db,
            group_id=group_id,
            user_id=current_user.id,
            file_id=file_id,
            view_role=GroupRole(permissions.view_role.value),
            download_role=GroupRole(permissions.download_role.value),
            manage_role=GroupRole(permissions.manage_role.value),
        )
        await db.commit()
        member = await GroupFileService._require_member(db, group_id, current_user.id)
        return _build_group_file_info(group_file, member.role)
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/groups/{group_id}/files/categories", response_model=List[GroupFileCategoryStat], summary="获取群文件分类统计")
async def get_group_file_categories(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        rows = await GroupFileService.category_stats(db, group_id, current_user.id)
        return [GroupFileCategoryStat(category=category, count=count) for category, count in rows]
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.patch("/groups/{group_id}/messages/{message_id}", response_model=MessageInfo, summary="编辑群消息")
async def edit_group_message(
    group_id: UUID,
    message_id: UUID,
    data: MessageEdit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """编辑群消息"""
    try:
        message = await GroupMessageService.edit_message(db, group_id, message_id, current_user.id, data)
        await db.commit()
        message_info = _build_message_info(message)
        if not _is_self_only_visibility(message.content_data, current_user.id):
            await manager.broadcast({
                "type": "message_edit",
                "message": message_info.model_dump(mode='json')
            }, str(group_id))
        return message_info
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/groups/{group_id}/messages/{message_id}/revoke", response_model=MessageInfo, summary="撤回群消息")
async def revoke_group_message(
    group_id: UUID,
    message_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """撤回群消息"""
    try:
        existing = await db.get(GroupMessage, message_id)
        is_self_only = False
        if existing and existing.group_id == group_id:
            is_self_only = _is_self_only_visibility(existing.content_data, current_user.id)
        message = await GroupMessageService.revoke_message(db, group_id, message_id, current_user.id)
        await db.commit()
        message_info = _build_message_info(message)
        if not is_self_only:
            await manager.broadcast({
                "type": "message_revoke",
                "message_id": str(message.id)
            }, str(group_id))
        return message_info
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/groups/{group_id}/messages/{message_id}/reactions", response_model=MessageInfo, summary="更新群消息表情")
async def update_group_message_reaction(
    group_id: UUID,
    message_id: UUID,
    data: MessageReactionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新群消息表情反应"""
    try:
        message = await GroupMessageService.update_reaction(
            db,
            group_id,
            message_id,
            current_user.id,
            data.emoji,
            data.action == ReactionActionEnum.ADD
        )
        await db.commit()
        if not _is_self_only_visibility(message.content_data, current_user.id):
            await manager.broadcast({
                "type": "reaction_update",
                "message_id": str(message.id),
                "reactions": message.reactions or {}
            }, str(group_id))
        return _build_message_info(message)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/groups/{group_id}/threads/{thread_root_id}", response_model=List[MessageInfo], summary="获取群消息线程")
async def get_group_thread_messages(
    group_id: UUID,
    thread_root_id: UUID,
    limit: int = Query(default=100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取群消息线程"""
    try:
        messages = await GroupMessageService.get_thread_messages(db, group_id, current_user.id, thread_root_id, limit)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return [_build_message_info(msg) for msg in messages]


@router.get("/groups/{group_id}/messages/search", response_model=List[MessageInfo], summary="搜索群消息")
async def search_group_messages(
    group_id: UUID,
    keyword: str = Query(min_length=1, max_length=120),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """搜索群消息"""
    try:
        messages = await GroupMessageService.search_messages(db, group_id, current_user.id, keyword, limit)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return [_build_message_info(msg) for msg in messages]


# ============ 私聊消息 ============

@router.post("/messages", response_model=PrivateMessageInfo, summary="发送私信")
async def send_private_message(
    data: PrivateMessageSend,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """发送私聊消息"""
    try:
        data.content_data = _normalize_self_visibility(data.content_data, current_user.id)
        message = await PrivateMessageService.send_message(db, current_user.id, data)
        await db.commit()

        msg_info = _build_private_message_info(message)

        is_self_only = _is_self_only_visibility(data.content_data, current_user.id)

        # 推送 WebSocket
        if not is_self_only:
            await manager.send_personal_message(msg_info.model_dump(mode='json'), str(data.target_user_id))
        await manager.send_personal_message(msg_info.model_dump(mode='json'), str(current_user.id))

        # 回传 ACK 给发送者
        if data.nonce:
            await manager.send_personal_message({
                "type": "ack",
                "nonce": data.nonce,
                "message_id": str(message.id),
                "timestamp": message.created_at.isoformat()
            }, str(current_user.id))

        return msg_info
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/friends/{friend_id}/messages", response_model=List[PrivateMessageInfo], summary="获取私信记录")
async def get_private_messages(
    friend_id: UUID,
    before_id: Optional[UUID] = None,
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取与某位好友的私信记录"""
    # 标记已读
    await PrivateMessageService.mark_as_read(db, current_user.id, friend_id)
    await db.commit()

    messages = await PrivateMessageService.get_messages(db, current_user.id, friend_id, before_id, limit)

    result = []
    for msg in messages:
        result.append(_build_private_message_info(msg))
    return result


@router.patch("/messages/{message_id}", response_model=PrivateMessageInfo, summary="编辑私信")
async def edit_private_message(
    message_id: UUID,
    data: MessageEdit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """编辑私聊消息"""
    try:
        message = await PrivateMessageService.edit_message(db, message_id, current_user.id, data)
        await db.commit()
        msg_info = _build_private_message_info(message)
        await manager.send_personal_message({
            "type": "message_edit",
            "message": msg_info.model_dump(mode='json')
        }, str(message.sender_id))
        if not _is_self_only_visibility(message.content_data, current_user.id):
            await manager.send_personal_message({
                "type": "message_edit",
                "message": msg_info.model_dump(mode='json')
            }, str(message.receiver_id))
        return msg_info
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/messages/{message_id}/revoke", response_model=PrivateMessageInfo, summary="撤回私信")
async def revoke_private_message(
    message_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """撤回私聊消息"""
    try:
        existing = await db.get(PrivateMessage, message_id)
        is_self_only = False
        if existing and existing.sender_id == current_user.id:
            is_self_only = _is_self_only_visibility(existing.content_data, current_user.id)
        message = await PrivateMessageService.revoke_message(db, message_id, current_user.id)
        await db.commit()
        await manager.send_personal_message({
            "type": "message_revoke",
            "message_id": str(message.id)
        }, str(message.sender_id))
        if not is_self_only:
            await manager.send_personal_message({
                "type": "message_revoke",
                "message_id": str(message.id)
            }, str(message.receiver_id))
        return _build_private_message_info(message)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/messages/{message_id}/reactions", response_model=PrivateMessageInfo, summary="更新私信表情")
async def update_private_message_reaction(
    message_id: UUID,
    data: MessageReactionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新私聊消息表情反应"""
    try:
        message = await PrivateMessageService.update_reaction(
            db,
            message_id,
            current_user.id,
            data.emoji,
            data.action == ReactionActionEnum.ADD
        )
        await db.commit()
        await manager.send_personal_message({
            "type": "reaction_update",
            "message_id": str(message.id),
            "reactions": message.reactions or {}
        }, str(message.sender_id))
        if not _is_self_only_visibility(message.content_data, current_user.id):
            await manager.send_personal_message({
                "type": "reaction_update",
                "message_id": str(message.id),
                "reactions": message.reactions or {}
            }, str(message.receiver_id))
        return _build_private_message_info(message)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/friends/{friend_id}/messages/search", response_model=List[PrivateMessageInfo], summary="搜索私信")
async def search_private_messages(
    friend_id: UUID,
    keyword: str = Query(min_length=1, max_length=120),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """搜索私聊消息"""
    messages = await PrivateMessageService.search_messages(db, current_user.id, friend_id, keyword, limit)
    return [_build_private_message_info(msg) for msg in messages]


async def _update_user_status(user_id: str, status: UserStatus):
    """更新用户状态并通知好友"""
    async with AsyncSessionLocal() as db:
        user = await db.get(User, user_id)
        if not user:
            return

        # Invisible 逻辑: 如果当前是隐身，上线/下线操作不改变DB状态（保持隐身）
        # 且不广播任何通知。
        if user.status == UserStatus.INVISIBLE:
            return 

        user.status = status
        db.add(user)
        await db.commit()

        # 广播 (分布式优化版：PUBLISH ONCE)
        broadcast_status = status.value
        await manager.notify_status_change(str(user.id), broadcast_status)


@router.put("/status", summary="更新在线状态")
async def update_status(
    data: UserStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """手动更新在线状态"""
    # 重新加载以确保 attached
    user = await db.get(User, current_user.id)
    user.status = UserStatus(data.status.value)
    db.add(user)
    await db.commit()
    
    # 通知
    broadcast_status = data.status.value
    if data.status == UserStatus.INVISIBLE:
        broadcast_status = UserStatus.OFFLINE.value
        
    await manager.notify_status_change(str(user.id), broadcast_status)
    
    return {"success": True, "status": data.status}


@router.websocket("/ws/connect")
async def user_websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...)
):
    """
    用户个人 WebSocket 连接
    用于接收私信通知、系统通知等
    连接地址: ws://host/api/v1/community/ws/connect?token={jwt_token}
    """
    user_id = None
    try:
        payload = decode_token(token, expected_type="access")
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4003)
            return
            
        # 获取好友列表以便优化 Presence 通知
        async with AsyncSessionLocal() as db:
            friends = await FriendshipService.get_friends(db, UUID(user_id))
            friend_ids = [str(f_user.id) for _, f_user in friends]

        await manager.connect_user(websocket, user_id, friend_ids=friend_ids)
        
        # 上线通知
        await _update_user_status(user_id, UserStatus.ONLINE)
        
        try:
            while True:
                # 保持连接，接收客户端消息
                data = await websocket.receive_text()
                # 可以在这里处理心跳
        except WebSocketDisconnect:
            manager.disconnect_user(user_id)
            # 下线通知
            await _update_user_status(user_id, UserStatus.OFFLINE)
            
    except Exception as e:
        print(f"User WebSocket Error: {e}")
        try:
            if user_id:
                manager.disconnect_user(user_id)
            await websocket.close()
        except:
            pass


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
    try:
        result = await CheckinService.checkin(db, current_user.id, data)
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============ 群任务 ============

@router.post("/groups/{group_id}/tasks", response_model=GroupTaskInfo, summary="创建群任务")
async def create_group_task(
    group_id: UUID,
    data: GroupTaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建群任务（仅群主/管理员）"""
    try:
        task = await GroupTaskService.create_task(db, group_id, current_user.id, data)
        await db.commit()

        return GroupTaskInfo(
            id=task.id,
            created_at=task.created_at,
            updated_at=task.updated_at,
            title=task.title,
            description=task.description,
            tags=task.tags or [],
            estimated_minutes=task.estimated_minutes,
            difficulty=task.difficulty,
            total_claims=task.total_claims,
            total_completions=task.total_completions,
            completion_rate=0.0,
            due_date=task.due_date,
            creator=UserBrief(
                id=current_user.id,
                username=current_user.username,
                nickname=current_user.nickname,
                avatar_url=current_user.avatar_url,
                flame_level=current_user.flame_level,
                flame_brightness=current_user.flame_brightness
            ),
            is_claimed_by_me=False,
            my_completion_status=None
        )
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/groups/{group_id}/tasks", response_model=List[GroupTaskInfo], summary="获取群任务列表")
async def get_group_tasks(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取群组的任务列表"""
    tasks = await GroupTaskService.get_group_tasks(db, group_id, current_user.id)

    result = []
    for task_dict in tasks:
        creator = task_dict.get('creator')
        creator_brief = UserBrief(
            id=creator.id,
            username=creator.username,
            nickname=creator.nickname,
            avatar_url=creator.avatar_url,
            flame_level=creator.flame_level,
            flame_brightness=creator.flame_brightness
        ) if creator else None

        result.append(GroupTaskInfo(
            id=task_dict['id'],
            created_at=task_dict['created_at'],
            updated_at=task_dict['updated_at'],
            title=task_dict['title'],
            description=task_dict['description'],
            tags=task_dict['tags'],
            estimated_minutes=task_dict['estimated_minutes'],
            difficulty=task_dict['difficulty'],
            total_claims=task_dict['total_claims'],
            total_completions=task_dict['total_completions'],
            completion_rate=task_dict['completion_rate'],
            due_date=task_dict['due_date'],
            creator=creator_brief,
            is_claimed_by_me=task_dict['is_claimed_by_me'],
            my_completion_status=task_dict['my_completion_status']
        ))
    return result


@router.post("/tasks/{task_id}/claim", summary="认领群任务")
async def claim_group_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """认领群任务，会在个人任务系统中创建对应任务"""
    try:
        claim = await GroupTaskService.claim_task(db, task_id, current_user.id)
        await db.commit()
        return {"success": True, "claim_id": str(claim.id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============ 火堆状态 ============

@router.get("/groups/{group_id}/flame", response_model=GroupFlameStatus, summary="获取群组火堆状态")
async def get_group_flame_status(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取群组火堆可视化数据

    返回所有成员的火苗状态，用于渲染火堆动画
    """
    from sqlalchemy import select
    from app.models.community import GroupMember
    import math

    group = await GroupService.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")

    # 获取群组成员的火苗数据
    result = await db.execute(
        select(GroupMember, User).join(
            User, GroupMember.user_id == User.id
        ).where(
            GroupMember.group_id == group_id,
            GroupMember.not_deleted_filter()
        ).order_by(GroupMember.flame_contribution.desc())
    )

    flames = []
    members = list(result.all())
    total_members = len(members)

    for idx, (member, user) in enumerate(members):
        # 计算火苗位置（围绕中心分布）
        angle = (2 * math.pi * idx) / max(total_members, 1)
        radius = 0.3 + (0.2 * (idx / max(total_members, 1)))  # 内外圈分布

        # 计算火苗属性
        power = min(100, max(0, member.flame_contribution))
        size = 0.5 + (power / 100) * 1.5  # 0.5 - 2.0

        # 根据等级决定颜色
        if user.flame_level >= 8:
            color = "#FFD700"  # 金色
        elif user.flame_level >= 5:
            color = "#FF6B35"  # 橙红
        else:
            color = "#FF9500"  # 橙色

        flames.append(FlameStatus(
            user_id=user.id,
            flame_power=power,
            flame_color=color,
            flame_size=size,
            position_x=math.cos(angle) * radius,
            position_y=math.sin(angle) * radius
        ))

    bonfire_level = min(5, (group['total_flame_power'] // 1000) + 1)

    return GroupFlameStatus(
        group_id=group_id,
        total_power=group['total_flame_power'],
        flames=flames,
        bonfire_level=bonfire_level
    )


# ============ 资源共享 ============

@router.post("/share", response_model=SharedResourceInfo, summary="分享资源")
async def share_resource(
    data: SharedResourceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    分享任务、计划或认知碎片给群组或好友
    """
    try:
        # Convert enum schema to model enum
        resource_type = SharedResourceType(data.resource_type.value)

        resource = await _get_share_resource(db, resource_type, data.resource_id, current_user.id)
        brief = _build_share_brief(resource_type, resource)

        shared = await collaboration_service.share_resource(
            db,
            current_user.id,
            resource_type,
            data.resource_id,
            target_group_id=data.target_group_id,
            target_user_id=data.target_user_id,
            permission=data.permission,
            comment=data.comment
        )

        share_payload = _compact_dict({
            "resource_type": resource_type.value,
            "resource_id": str(data.resource_id),
            "shared_resource_id": str(shared.id),
            "resource_title": brief["title"],
            "resource_summary": brief["summary"],
            "resource_meta": brief["meta"],
            "permission": shared.permission,
            "comment": data.comment
        })

        message_type = _share_message_type(resource_type)
        message_content = data.comment

        message_info = None
        if data.target_group_id:
            message = await GroupMessageService.send_message(
                db,
                data.target_group_id,
                current_user.id,
                MessageSend(
                    message_type=message_type,
                    content=message_content,
                    content_data=share_payload
                )
            )
            message_info = _build_message_info(message)
        elif data.target_user_id:
            message = await PrivateMessageService.send_message(
                db,
                current_user.id,
                PrivateMessageSend(
                    target_user_id=data.target_user_id,
                    message_type=message_type,
                    content=message_content,
                    content_data=share_payload
                )
            )
            message_info = _build_private_message_info(message)

        await db.commit()

        if message_info:
            if data.target_group_id:
                await manager.broadcast(message_info.model_dump(mode='json'), str(data.target_group_id))
            elif data.target_user_id:
                await manager.send_personal_message(message_info.model_dump(mode='json'), str(data.target_user_id))
                await manager.send_personal_message(message_info.model_dump(mode='json'), str(current_user.id))

        # Construct response
        return SharedResourceInfo(
            id=shared.id,
            created_at=shared.created_at,
            updated_at=shared.updated_at,
            resource_type=data.resource_type.value,
            plan_id=shared.plan_id,
            task_id=shared.task_id,
            cognitive_fragment_id=shared.cognitive_fragment_id,
            curiosity_capsule_id=shared.curiosity_capsule_id,
            behavior_pattern_id=shared.behavior_pattern_id,
            permission=shared.permission,
            comment=shared.comment,
            view_count=shared.view_count,
            save_count=shared.save_count,
            sharer=UserBrief.model_validate(current_user),
            resource_title=brief["title"],
            resource_summary=brief["summary"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/groups/{group_id}/resources", response_model=List[SharedResourceInfo], summary="获取群组共享资源")
async def get_group_resources(
    group_id: UUID,
    resource_type: Optional[SharedResourceTypeEnum] = None,
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取分享到群组的资源列表
    """
    # Check if user is member
    await GroupService.get_group(db, group_id, current_user.id) # Will raise/return None if not accessible? 
    # Actually get_group returns None if not found or not member? 
    # Current implementation of get_group checks permission implicitly or explicitly?
    # Let's rely on service check or do manual check if strictly needed.
    # GroupService.get_group returns group info if user is member (based on internal logic usually).
    
    rtype = SharedResourceType(resource_type.value) if resource_type else None
    
    resources = await collaboration_service.get_group_resources(
        db, group_id, rtype, limit
    )
    
    result = []
    for res in resources:
        # Determine strict type string
        r_type_str = "unknown"
        resource_title = None
        resource_summary = None
        if res.plan_id and res.plan:
            r_type_str = "plan"
            brief = _build_share_brief(SharedResourceType.PLAN, res.plan)
            resource_title = brief["title"]
            resource_summary = brief["summary"]
        elif res.task_id and res.task:
            r_type_str = "task"
            brief = _build_share_brief(SharedResourceType.TASK, res.task)
            resource_title = brief["title"]
            resource_summary = brief["summary"]
        elif res.cognitive_fragment_id and res.cognitive_fragment:
            r_type_str = "cognitive_fragment"
            brief = _build_share_brief(SharedResourceType.COGNITIVE_FRAGMENT, res.cognitive_fragment)
            resource_title = brief["title"]
            resource_summary = brief["summary"]
        elif res.curiosity_capsule_id and res.curiosity_capsule:
            r_type_str = "curiosity_capsule"
            brief = _build_share_brief(SharedResourceType.CURIOSITY_CAPSULE, res.curiosity_capsule)
            resource_title = brief["title"]
            resource_summary = brief["summary"]
        elif res.behavior_pattern_id and res.behavior_pattern:
            r_type_str = "cognitive_prism_pattern"
            brief = _build_share_brief(SharedResourceType.COGNITIVE_PRISM_PATTERN, res.behavior_pattern)
            resource_title = brief["title"]
            resource_summary = brief["summary"]
        
        result.append(SharedResourceInfo(
            id=res.id,
            created_at=res.created_at,
            updated_at=res.updated_at,
            resource_type=r_type_str,
            plan_id=res.plan_id,
            task_id=res.task_id,
            cognitive_fragment_id=res.cognitive_fragment_id,
            curiosity_capsule_id=res.curiosity_capsule_id,
            behavior_pattern_id=res.behavior_pattern_id,
            permission=res.permission,
            comment=res.comment,
            view_count=res.view_count,
            save_count=res.save_count,
            sharer=UserBrief.model_validate(res.sharer) if res.sharer else None,
            resource_title=resource_title,
            resource_summary=resource_summary
        ))
    return result


# ============ 端到端加密 ============

@router.post("/encryption/keys", response_model=EncryptionKeyInfo, summary="注册加密公钥")
async def register_encryption_key(
    data: EncryptionKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    注册用户的公钥用于端到端加密

    - **public_key**: Base64编码的公钥
    - **key_type**: 密钥类型 (x25519, rsa)
    - **device_id**: 可选的设备标识
    """
    key = await EncryptionService.register_public_key(db, current_user.id, data)
    await db.commit()
    return EncryptionKeyInfo(
        id=key.id,
        created_at=key.created_at,
        updated_at=key.updated_at,
        public_key=key.public_key,
        key_type=key.key_type,
        device_id=key.device_id,
        is_active=key.is_active,
        expires_at=key.expires_at
    )


@router.get("/encryption/keys/{user_id}", response_model=List[EncryptionKeyInfo], summary="获取用户公钥")
async def get_user_encryption_keys(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取指定用户的活跃公钥列表"""
    keys = await EncryptionService.get_user_public_keys(db, user_id)
    return [
        EncryptionKeyInfo(
            id=key.id,
            created_at=key.created_at,
            updated_at=key.updated_at,
            public_key=key.public_key,
            key_type=key.key_type,
            device_id=key.device_id,
            is_active=key.is_active,
            expires_at=key.expires_at
        ) for key in keys
    ]


@router.delete("/encryption/keys/{key_id}", summary="撤销加密密钥")
async def revoke_encryption_key(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """撤销指定的加密密钥"""
    success = await EncryptionService.revoke_key(db, current_user.id, key_id)
    if not success:
        raise HTTPException(status_code=404, detail="密钥不存在或无权操作")
    await db.commit()
    return {"success": True}


# ============ 群管理与风控 ============

@router.put("/groups/{group_id}/announcement", summary="更新群公告")
async def update_group_announcement(
    group_id: UUID,
    data: GroupAnnouncementUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新群公告（仅群主/管理员）"""
    try:
        group = await ModerationService.update_announcement(db, group_id, current_user.id, data)
        await db.commit()

        # 广播公告更新
        await manager.broadcast({
            "type": "announcement_update",
            "group_id": str(group_id),
            "announcement": group.announcement,
            "updated_at": group.announcement_updated_at.isoformat() if group.announcement_updated_at else None
        }, str(group_id))

        return {"success": True, "announcement": group.announcement}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.put("/groups/{group_id}/moderation", summary="更新群管理设置")
async def update_group_moderation_settings(
    group_id: UUID,
    data: GroupModerationSettings,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新群管理设置（仅群主/管理员）"""
    try:
        group = await ModerationService.update_moderation_settings(db, group_id, current_user.id, data)
        await db.commit()
        return {
            "success": True,
            "mute_all": group.mute_all,
            "slow_mode_seconds": group.slow_mode_seconds,
            "keyword_filters_count": len(group.keyword_filters or [])
        }
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/groups/{group_id}/members/{user_id}/mute", summary="禁言成员")
async def mute_group_member(
    group_id: UUID,
    user_id: UUID,
    data: MemberMuteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """禁言群成员（仅群主/管理员）"""
    try:
        # 覆盖 data 中的 user_id
        data.user_id = user_id
        member = await ModerationService.mute_member(db, group_id, current_user.id, data)
        await db.commit()

        # 通知被禁言用户
        await manager.send_personal_message({
            "type": "muted",
            "group_id": str(group_id),
            "mute_until": member.mute_until.isoformat() if member.mute_until else None,
            "reason": data.reason
        }, str(user_id))

        return {"success": True, "mute_until": member.mute_until}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/groups/{group_id}/members/{user_id}/mute", summary="解除禁言")
async def unmute_group_member(
    group_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """解除成员禁言（仅群主/管理员）"""
    try:
        await ModerationService.unmute_member(db, group_id, current_user.id, user_id)
        await db.commit()

        # 通知用户
        await manager.send_personal_message({
            "type": "unmuted",
            "group_id": str(group_id)
        }, str(user_id))

        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/groups/{group_id}/members/{user_id}/warn", summary="警告成员")
async def warn_group_member(
    group_id: UUID,
    user_id: UUID,
    data: MemberWarnRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """警告群成员（仅群主/管理员）"""
    try:
        data.user_id = user_id
        member = await ModerationService.warn_member(db, group_id, current_user.id, data)
        await db.commit()

        # 通知被警告用户
        await manager.send_personal_message({
            "type": "warned",
            "group_id": str(group_id),
            "reason": data.reason,
            "warn_count": member.warn_count
        }, str(user_id))

        return {"success": True, "warn_count": member.warn_count}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ============ 消息举报 ============

@router.post("/reports", response_model=MessageReportInfo, summary="举报消息")
@limiter.limit("10/minute")
async def report_message(
    request: Request,
    data: MessageReportCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """举报违规消息"""
    try:
        report = await ReportService.create_report(db, current_user.id, data)
        await db.commit()

        return MessageReportInfo(
            id=report.id,
            created_at=report.created_at,
            updated_at=report.updated_at,
            reporter=UserBrief.model_validate(current_user),
            reason=report.reason,
            description=report.description,
            status=report.status,
            reviewed_by=None,
            reviewed_at=None,
            action_taken=None
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/groups/{group_id}/reports", response_model=List[MessageReportInfo], summary="获取群组待处理举报")
async def get_group_pending_reports(
    group_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取群组中待处理的举报（仅群主/管理员）"""
    # 验证管理员权限
    result = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.id,
            GroupMember.role.in_(['owner', 'admin']),
            GroupMember.not_deleted_filter()
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="无权访问")

    reports = await ReportService.get_pending_reports(db, group_id, limit)
    return [
        MessageReportInfo(
            id=r.id,
            created_at=r.created_at,
            updated_at=r.updated_at,
            reporter=UserBrief.model_validate(r.reporter) if r.reporter else None,
            reason=r.reason,
            description=r.description,
            status=r.status,
            reviewed_by=None,
            reviewed_at=r.reviewed_at,
            action_taken=r.action_taken
        ) for r in reports
    ]


@router.put("/reports/{report_id}", response_model=MessageReportInfo, summary="审核举报")
async def review_message_report(
    report_id: UUID,
    data: MessageReportReview,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """审核消息举报（仅管理员）"""
    try:
        report = await ReportService.review_report(db, current_user.id, report_id, data)
        await db.commit()

        return MessageReportInfo(
            id=report.id,
            created_at=report.created_at,
            updated_at=report.updated_at,
            reporter=UserBrief.model_validate(report.reporter) if report.reporter else None,
            reason=report.reason,
            description=report.description,
            status=report.status,
            reviewed_by=UserBrief.model_validate(current_user),
            reviewed_at=report.reviewed_at,
            action_taken=report.action_taken
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============ 消息收藏 ============

@router.post("/favorites", response_model=MessageFavoriteInfo, summary="收藏消息")
async def add_message_favorite(
    data: MessageFavoriteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """收藏消息"""
    try:
        favorite = await FavoriteService.add_favorite(db, current_user.id, data)
        await db.commit()

        # 获取消息预览
        preview = None
        if favorite.group_message_id:
            msg = await db.get(GroupMessage, favorite.group_message_id)
            if msg:
                preview = msg.content[:100] if msg.content else None
        elif favorite.private_message_id:
            msg = await db.get(PrivateMessage, favorite.private_message_id)
            if msg:
                preview = msg.content[:100] if msg.content else None

        return MessageFavoriteInfo(
            id=favorite.id,
            created_at=favorite.created_at,
            updated_at=favorite.updated_at,
            group_message_id=favorite.group_message_id,
            private_message_id=favorite.private_message_id,
            note=favorite.note,
            tags=favorite.tags,
            message_preview=preview
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/favorites", response_model=List[MessageFavoriteInfo], summary="获取收藏列表")
async def get_message_favorites(
    tags: Optional[List[str]] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取我的消息收藏列表"""
    favorites = await FavoriteService.get_favorites(db, current_user.id, tags, limit, offset)

    result = []
    for fav in favorites:
        preview = None
        if fav.group_message and fav.group_message.content:
            preview = fav.group_message.content[:100]
        elif fav.private_message and fav.private_message.content:
            preview = fav.private_message.content[:100]

        result.append(MessageFavoriteInfo(
            id=fav.id,
            created_at=fav.created_at,
            updated_at=fav.updated_at,
            group_message_id=fav.group_message_id,
            private_message_id=fav.private_message_id,
            note=fav.note,
            tags=fav.tags,
            message_preview=preview
        ))
    return result


@router.delete("/favorites/{favorite_id}", summary="取消收藏")
async def remove_message_favorite(
    favorite_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """取消消息收藏"""
    success = await FavoriteService.remove_favorite(db, current_user.id, favorite_id)
    if not success:
        raise HTTPException(status_code=404, detail="收藏不存在")
    await db.commit()
    return {"success": True}


# ============ 消息转发 ============

@router.post("/forward", summary="转发消息")
async def forward_message(
    data: MessageForwardRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """转发消息到群组或用户"""
    try:
        forwarded = await ForwardService.forward_message(db, current_user.id, data)
        await db.commit()

        # 构建消息信息并广播
        if data.target_group_id:
            msg_info = _build_message_info(forwarded)
            await manager.broadcast(msg_info.model_dump(mode='json'), str(data.target_group_id))
        elif data.target_user_id:
            msg_info = _build_private_message_info(forwarded)
            await manager.send_personal_message(msg_info.model_dump(mode='json'), str(data.target_user_id))
            await manager.send_personal_message(msg_info.model_dump(mode='json'), str(current_user.id))

        return {"success": True, "message_id": str(forwarded.id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============ 跨群广播 ============

@router.post("/broadcast", response_model=BroadcastMessageInfo, summary="跨群广播")
async def create_broadcast_message(
    data: BroadcastMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """发送跨群广播消息（需要在所有目标群组中是管理员）"""
    try:
        broadcast = await BroadcastService.create_broadcast(db, current_user.id, data)
        await db.commit()

        # 广播到所有目标群组
        for group_id in data.target_group_ids:
            await manager.broadcast({
                "type": "broadcast",
                "broadcast_id": str(broadcast.id),
                "sender_id": str(current_user.id),
                "content": broadcast.content,
                "content_data": broadcast.content_data
            }, str(group_id))

        return BroadcastMessageInfo(
            id=broadcast.id,
            created_at=broadcast.created_at,
            updated_at=broadcast.updated_at,
            sender=UserBrief.model_validate(current_user),
            content=broadcast.content,
            content_data=broadcast.content_data,
            target_group_ids=data.target_group_ids,
            delivered_count=broadcast.delivered_count
        )
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ============ 高级搜索 ============

@router.post("/groups/{group_id}/messages/search/advanced", response_model=MessageSearchResult, summary="高级搜索群消息")
async def advanced_search_group_messages(
    group_id: UUID,
    data: MessageSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    高级消息搜索

    支持多条件组合搜索:
    - 关键词全文搜索
    - 发送者过滤
    - 时间范围
    - 消息类型
    - 话题/标签
    """
    try:
        result = await MessageSearchService.search_group_messages(db, group_id, current_user.id, data)

        messages = [_build_message_info(msg) for msg in result["messages"]]

        return MessageSearchResult(
            messages=messages,
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
            has_more=result["has_more"]
        )
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/groups/{group_id}/topics", summary="获取群组话题列表")
async def get_group_topics(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取群组中使用的话题列表及消息数量"""
    # 验证成员身份
    result = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.id,
            GroupMember.not_deleted_filter()
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="不是群组成员")

    topics = await MessageSearchService.get_topics(db, group_id)
    return {"topics": topics}


# ============ 离线队列 ============

@router.get("/offline/pending", response_model=List[OfflineMessageInfo], summary="获取待发送的离线消息")
async def get_pending_offline_messages(
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户待发送的离线消息"""
    messages = await OfflineQueueService.get_pending_messages(db, current_user.id, limit)
    return [
        OfflineMessageInfo(
            id=msg.id,
            created_at=msg.created_at,
            updated_at=msg.updated_at,
            client_nonce=msg.client_nonce,
            message_type=msg.message_type,
            target_id=msg.target_id,
            status=msg.status,
            retry_count=msg.retry_count,
            error_message=msg.error_message
        ) for msg in messages
    ]


@router.get("/offline/failed", response_model=List[OfflineMessageInfo], summary="获取发送失败的离线消息")
async def get_failed_offline_messages(
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取发送失败的离线消息（用于批量重试UI）"""
    messages = await OfflineQueueService.get_failed_messages(db, current_user.id, limit)
    return [
        OfflineMessageInfo(
            id=msg.id,
            created_at=msg.created_at,
            updated_at=msg.updated_at,
            client_nonce=msg.client_nonce,
            message_type=msg.message_type,
            target_id=msg.target_id,
            status=msg.status,
            retry_count=msg.retry_count,
            error_message=msg.error_message
        ) for msg in messages
    ]


@router.post("/offline/retry", summary="批量重试失败消息")
async def retry_offline_messages(
    data: OfflineMessageRetryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """批量重试失败的离线消息"""
    messages = await OfflineQueueService.retry_messages(db, current_user.id, data)
    await db.commit()
    return {
        "success": True,
        "retried_count": len(messages),
        "message_ids": [str(m.id) for m in messages]
    }
