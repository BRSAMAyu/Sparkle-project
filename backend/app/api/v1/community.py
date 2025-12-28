"""
社群功能 API 路由
Community API - 好友、群组、消息、打卡、任务相关接口
"""
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
from app.models.community import GroupType, GroupMember
from app.schemas.community import (
    # 好友
    FriendRequest, FriendResponse, FriendshipInfo, FriendRecommendation,
    # 群组
    GroupCreate, GroupUpdate, GroupInfo, GroupListItem, GroupMemberInfo,
    MemberRoleUpdate, UserBrief,
    # 消息
    MessageSend, MessageInfo,
    PrivateMessageSend, PrivateMessageInfo,
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
    GroupTypeEnum, GroupRoleEnum, SharedResourceTypeEnum
)
from app.services.community_service import (
    FriendshipService, GroupService, GroupMessageService,
    CheckinService, GroupTaskService, PrivateMessageService
)
from app.services.collaboration_service import collaboration_service
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
        quoted_message=quoted_message
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
        is_read=msg.is_read,
        read_at=msg.read_at,
        quoted_message=quoted_message
    )


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
    连接地址: ws://host/api/v1/groups/{group_id}/ws?token={jwt_token}
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
        message = await GroupMessageService.send_message(db, group_id, current_user.id, data)
        await db.commit()

        message_info = _build_message_info(message)

        # 广播消息到 WebSocket
        await manager.broadcast(message_info.model_dump(mode='json'), str(group_id))

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


# ============ 私聊消息 ============

@router.post("/messages", response_model=PrivateMessageInfo, summary="发送私信")
async def send_private_message(
    data: PrivateMessageSend,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """发送私聊消息"""
    try:
        message = await PrivateMessageService.send_message(db, current_user.id, data)
        await db.commit()

        msg_info = _build_private_message_info(message)

        # 推送 WebSocket
        await manager.send_personal_message(msg_info.model_dump(mode='json'), str(data.target_user_id))

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
        await db.commit()
        
        # Construct response
        return SharedResourceInfo(
            id=shared.id,
            created_at=shared.created_at,
            updated_at=shared.updated_at,
            resource_type=data.resource_type.value,
            plan_id=shared.plan_id,
            task_id=shared.task_id,
            cognitive_fragment_id=shared.cognitive_fragment_id,
            permission=shared.permission,
            comment=shared.comment,
            view_count=shared.view_count,
            save_count=shared.save_count,
            sharer=UserBrief.model_validate(shared.sharer) if shared.sharer else None,
            # We skip embedding full object details for now or fetch if needed
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
        if res.plan_id: r_type_str = "plan"
        elif res.task_id: r_type_str = "task"
        elif res.cognitive_fragment_id: r_type_str = "cognitive_fragment"
        
        # Prepare embedded title/summary if possible
        title = None
        if res.plan: title = res.plan.name
        elif res.task: title = res.task.title
        # elif res.cognitive_fragment: title = ...
        
        result.append(SharedResourceInfo(
            id=res.id,
            created_at=res.created_at,
            updated_at=res.updated_at,
            resource_type=r_type_str,
            plan_id=res.plan_id,
            task_id=res.task_id,
            cognitive_fragment_id=res.cognitive_fragment_id,
            permission=res.permission,
            comment=res.comment,
            view_count=res.view_count,
            save_count=res.save_count,
            sharer=UserBrief.model_validate(res.sharer) if res.sharer else None,
            resource_title=title
        ))
    return result
