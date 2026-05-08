"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>

社群功能 API 路由
Community API - 好友、群组、消息、打卡、任务相关接口
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
from copy import deepcopy
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from loguru import logger
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user
from app.api.v1.accountability import (
    _build_leaderboard_summary,
    _build_partnership_achievements_payload,
    _build_partnership_out,
    _build_partnership_stats_payload,
    _build_recent_shares_payload,
    _build_relationship_summary,
    _get_last_checkin_at,
    _slot_type_value,
)
from app.config import settings
from app.core.cache import cache_service
from app.core.metrics import (
    observe_product_loop_items,
    observe_product_loop_latency,
    record_product_loop_event,
)
from app.core.rate_limiting import limiter
from app.core.security import decode_token
from app.core.websocket import manager
from app.db.session import AsyncSessionLocal, get_db
from app.models.accountability import (
    AccountabilityPartnership,
    AccountabilitySlotType,
    AccountabilityStatus,
)
from app.models.card_protocol import ImportMode, SharePermission, ShareScope
from app.models.cognitive import BehaviorPattern, CognitiveFragment
from app.models.community import (
    Friendship,
    FriendshipStatus,
    GroupMember,
    GroupMessage,
    GroupRole,
    GroupType,
    Post,
    PostComment,
    PostLike,
    PrivateMessage,
    SharedResource,
    SharedResourceType,
    UserBlock,
)
from app.models.curiosity_capsule import CuriosityCapsule
from app.models.file_storage import StoredFile
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.group_files import GroupFile
from app.models.plan import Plan
from app.models.seed_content import SeedItem, SeedLibrary
from app.models.task import Task
from app.models.user import User, UserStatus
from app.schemas.community import (
    AccountabilityFriendSummary,
    BlockUserInfo,
    # 拉黑相关
    BlockUserRequest,
    # 广播相关
    BroadcastMessageCreate,
    BroadcastMessageInfo,
    # 其他
    CheckinRequest,
    CheckinResponse,
    EncryptionKeyCreate,
    EncryptionKeyInfo,
    # 群文件
    FileCopyResponse,
    FlameStatus,
    FriendMatchStrategyEnum,
    FriendRecommendation,
    FriendRecommendationFeedbackRequest,
    FriendRecommendationTargetEnum,
    # 好友
    FriendRequest,
    FriendResponse,
    FriendshipInfo,
    # 群管理相关
    GroupAnnouncementUpdate,
    GroupCollaborativeGalaxyResponse,
    # 群组
    GroupCreate,
    GroupDirectoryResponse,
    GroupDirectorySortEnum,
    GroupFileCategoryStat,
    GroupFileCreateRequest,
    GroupFileInfo,
    GroupFilePermissions,
    GroupFilePermissionUpdate,
    GroupFileShareRequest,
    GroupFileSortEnum,
    # 火堆
    GroupFlameStatus,
    GroupInfo,
    GroupKnowledgeBaseDocumentCreate,
    GroupKnowledgeBaseResponse,
    GroupListItem,
    GroupMemberInfo,
    GroupMessageReadRequest,
    GroupMessageReadResponse,
    GroupModerationSettings,
    GroupRecommendationFeedbackRequest,
    GroupRecommendationItem,
    GroupTaskCreate,
    GroupTaskInfo,
    # 枚举
    GroupTypeEnum,
    MemberMuteRequest,
    MemberWarnRequest,
    MessageEdit,
    # 收藏相关
    MessageFavoriteCreate,
    MessageFavoriteInfo,
    # 转发相关
    MessageForwardRequest,
    MessageInfo,
    MessageReactionUpdate,
    # 举报相关
    MessageReportCreate,
    MessageReportInfo,
    MessageReportReview,
    # 搜索相关
    MessageSearchRequest,
    MessageSearchResult,
    # 消息
    MessageSend,
    MessageTypeEnum,
    # 离线队列相关
    OfflineMessageInfo,
    OfflineMessageRetryRequest,
    PrivateMessageInfo,
    PrivateMessageSend,
    ReactionActionEnum,
    RecommendationFeedbackInsight,
    RecommendationFeedbackPrompt,
    RecommendationItemTypeEnum,
    # 隐私设置
    SearchVisibilityEnum,
    SharedResourceCreate,
    SharedResourceInfo,
    SharedResourceTypeEnum,
    SimilarGoalPursuer,
    UserBrief,
    UserFileShareRequest,
    UserPrivacySettings,
    # 状态
    UserStatusUpdate,
)
from app.schemas.plan import PlanCreate
from app.schemas.task import TaskCreate
from app.services.card_protocol.share_service import ShareService
from app.services.collaboration_service import collaboration_service
from app.services.community_advanced_service import (
    BroadcastService,
    EncryptionService,
    FavoriteService,
    ForwardService,
    MessageSearchService,
    ModerationService,
    OfflineQueueService,
    ReportService,
)
from app.services.community_service import (
    CheckinService,
    FriendshipService,
    GroupKnowledgeService,
    GroupMessageService,
    GroupService,
    GroupTaskService,
    PrivateMessageService,
    UserBlockService,
    UserSearchService,
    _is_visible_to,
    find_users_with_similar_goals,
)
from app.services.community_signal_bridge import CommunitySignalBridge
from app.services.friend_match_service import FriendMatchService
from app.services.group_file_service import GroupFileService
from app.services.group_recommendation_service import GroupRecommendationService
from app.services.plan_service import PlanService
from app.services.recommendation_feedback_service import RecommendationFeedbackService
from app.services.seed_library_service import SeedLibraryService
from app.services.streak_signal_processor import StreakSignalProcessor
from app.services.task_service import TaskService
from app.tools.entity_cards import (
    build_entity_action,
    build_entity_card,
    build_knowledge_entity_card,
    build_plan_entity_card,
    build_shared_resource_entity_card,
    build_task_entity_card,
)

router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _post_to_response(post: Post, current_user_id=None, liked_post_ids=None) -> dict:
    """Convert Post ORM object to Flutter-compatible response dict."""
    user_data = {
        "id": str(post.user.id) if post.user else str(post.user_id),
        "username": post.user.username if post.user else "unknown",
        "avatar_url": post.user.avatar_url if post.user else None,
    }
    if liked_post_ids is not None:
        is_liked = str(post.id) in liked_post_ids
    elif current_user_id is not None:
        is_liked = any(str(like.user_id) == str(current_user_id) for like in (post.likes or []))
    else:
        is_liked = False
    return {
        "id": str(post.id),
        "user_id": str(post.user_id),
        "content": post.content or "",
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "user": user_data,
        "image_urls": post.image_urls or [],
        "topic": post.topic,
        "like_count": post.like_count or 0,
        "is_liked": is_liked,
    }


def _shared_resource_payload_is_active(resource: SharedResource) -> bool:
    """Return False when the shared legacy object was soft-deleted."""
    payloads = (
        resource.plan,
        resource.task,
        resource.knowledge_node,
        resource.seed_library,
        resource.seed_item,
        resource.cognitive_fragment,
        resource.curiosity_capsule,
        resource.behavior_pattern,
    )
    for payload in payloads:
        if payload is not None:
            return not getattr(payload, "is_deleted", False)
    return resource.card_share_record_id is not None


def _shared_resource_avg_rating(resource: SharedResource) -> float | None:
    """Use persisted quality as the current rating proxy until explicit ratings exist."""
    if resource.quality_score is None:
        return None
    return round(max(0.0, min(float(resource.quality_score), 1.0)) * 5.0, 1)


# route-tier: authed
@router.get("/feed", summary="获取社区动态流")
async def get_feed(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
    scope: str | None = Query(default=None, description="筛选范围: squad, goal_mates, following"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取社区动态列表，按创建时间倒序。支持 scope 筛选。"""
    from sqlalchemy.orm import selectinload

    start_time = time.perf_counter()
    metric_surface = scope or "global"
    offset = (page - 1) * limit
    stmt = select(Post).options(selectinload(Post.user))

    # ── soft-delete guard ──
    stmt = stmt.where(Post.not_deleted_filter())

    accepted_friend_ids = (
        select(Friendship.friend_id)
        .where(
            Friendship.user_id == current_user.id,
            Friendship.status == FriendshipStatus.ACCEPTED,
            Friendship.not_deleted_filter(),
        )
        .correlate(None)
    )
    accepted_friend_ids_alt = (
        select(Friendship.user_id)
        .where(
            Friendship.friend_id == current_user.id,
            Friendship.status == FriendshipStatus.ACCEPTED,
            Friendship.not_deleted_filter(),
        )
        .correlate(None)
    )
    friend_visible_posts = or_(
        Post.visibility == "public",
        and_(
            Post.visibility == "friends",
            or_(
                Post.user_id == current_user.id,
                Post.user_id.in_(accepted_friend_ids),
                Post.user_id.in_(accepted_friend_ids_alt),
            ),
        ),
    )

    if scope == "squad":
        squad_member_subq = (
            select(GroupMember.group_id)
            .where(GroupMember.user_id == current_user.id, GroupMember.not_deleted_filter())
            .correlate(None)
        )
        squad_user_subq = (
            select(GroupMember.user_id)
            .where(GroupMember.group_id.in_(squad_member_subq), GroupMember.not_deleted_filter())
            .correlate(None)
        )
        stmt = stmt.where(Post.user_id.in_(squad_user_subq))
        stmt = stmt.where(friend_visible_posts)
    elif scope == "goal_mates":
        partner_ids_initiated = (
            select(AccountabilityPartnership.partner_id)
            .where(
                AccountabilityPartnership.initiator_id == current_user.id,
                AccountabilityPartnership.status == AccountabilityStatus.ACTIVE,
                AccountabilityPartnership.not_deleted_filter(),
            )
            .correlate(None)
        )
        partner_ids_accepted = (
            select(AccountabilityPartnership.initiator_id)
            .where(
                AccountabilityPartnership.partner_id == current_user.id,
                AccountabilityPartnership.status == AccountabilityStatus.ACTIVE,
                AccountabilityPartnership.not_deleted_filter(),
            )
            .correlate(None)
        )
        stmt = stmt.where(Post.user_id.in_(partner_ids_initiated) | Post.user_id.in_(partner_ids_accepted))
        stmt = stmt.where(friend_visible_posts)
    elif scope == "following":
        stmt = stmt.where(Post.user_id.in_(accepted_friend_ids) | Post.user_id.in_(accepted_friend_ids_alt))
        stmt = stmt.where(friend_visible_posts)
    elif scope is not None:
        record_product_loop_event("community_feed", metric_surface, "invalid_scope", "bad_scope")
        observe_product_loop_latency(
            "community_feed", metric_surface, "invalid_scope", time.perf_counter() - start_time
        )
        raise HTTPException(status_code=400, detail=f"Unknown scope: {scope}")
    else:
        stmt = stmt.where(Post.visibility == "public")

    # ── block guard: exclude authors with an active block relationship ──
    blocked_uids = (
        select(UserBlock.blocked_id.label("uid"))
        .where(UserBlock.blocker_id == current_user.id, UserBlock.not_deleted_filter())
        .union(
            select(UserBlock.blocker_id.label("uid")).where(
                UserBlock.blocked_id == current_user.id, UserBlock.not_deleted_filter()
            )
        )
        .subquery()
    )
    stmt = stmt.where(~Post.user_id.in_(select(blocked_uids.c.uid)))

    stmt = stmt.order_by(Post.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    posts = result.scalars().all()
    post_count = len(posts)
    record_product_loop_event(
        "community_feed",
        metric_surface,
        "loaded",
        "empty" if post_count == 0 else "has_posts",
    )
    observe_product_loop_items("community_feed", metric_surface, post_count)
    observe_product_loop_latency("community_feed", metric_surface, "loaded", time.perf_counter() - start_time)

    liked_post_ids = set()
    if posts and current_user:
        post_ids = [p.id for p in posts]
        likes_result = await db.execute(
            select(PostLike.post_id).where(
                PostLike.user_id == current_user.id,
                PostLike.post_id.in_(post_ids),
            )
        )
        liked_post_ids = {str(pid) for pid in likes_result.scalars().all()}

    return [_post_to_response(p, liked_post_ids=liked_post_ids) for p in posts]


# route-tier: authed
@router.post("/posts", summary="发布社区动态", status_code=201)
@limiter.limit("5/minute")
async def create_post(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建社区动态帖子"""
    body = await request.json()
    post = Post(
        user_id=current_user.id,
        content=body.get("content", ""),
        topic=body.get("topic"),
        image_urls=body.get("image_urls", []),
        visibility="public",
        like_count=0,
        comment_count=0,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post, attribute_names=["user"])
    return _post_to_response(post, current_user_id=str(current_user.id))


# route-tier: authed
@router.post("/posts/{post_id}/like", summary="点赞/取消点赞")
async def toggle_like_post(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle like on a post. Returns updated like_count."""
    post = (await db.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="动态不存在")

    existing = (
        await db.execute(
            select(PostLike).where(
                PostLike.user_id == current_user.id,
                PostLike.post_id == post_id,
            )
        )
    ).scalar_one_or_none()

    if existing:
        await db.delete(existing)
        post.like_count = max(0, (post.like_count or 1) - 1)
        liked = False
    else:
        db.add(PostLike(user_id=current_user.id, post_id=post_id))
        post.like_count = (post.like_count or 0) + 1
        liked = True

    await db.commit()

    # Notify post author when someone likes their post (not self-like)
    if liked and str(post.user_id) != str(current_user.id):
        try:
            from app.services.notification_push_service import NotificationPushService

            push_svc = NotificationPushService(db)
            await push_svc.create_and_push(
                user_id=post.user_id,
                title="Someone liked your post",
                content=f"{current_user.username} liked your post",
                notification_type="social",
                data={"post_id": str(post_id), "liker_id": str(current_user.id)},
            )
        except Exception:
            logger.debug("Failed to push like notification for post={}", post_id, exc_info=True)

    return {"liked": liked, "like_count": post.like_count}


# ============ 评论系统 ============

@router.get("/posts/{post_id}/comments", summary="获取评论列表")
async def list_post_comments(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get comments for a post, newest first."""
    comments = (
        await db.execute(
            select(PostComment)
            .where(PostComment.post_id == post_id)
            .order_by(desc(PostComment.created_at))
        )
    ).scalars().all()
    return [
        {
            "id": str(c.id),
            "post_id": str(c.post_id),
            "user_id": str(c.user_id),
            "content": c.content,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in comments
    ]


@router.post("/posts/{post_id}/comments", summary="发表评论", status_code=201)
async def create_post_comment(
    post_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a comment to a post."""
    post = (
        await db.execute(select(Post).where(Post.id == post_id))
    ).scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    body = await request.json()
    content = (body.get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=422, detail="Content required")

    comment = PostComment(
        user_id=current_user.id,
        post_id=post_id,
        content=content,
    )
    db.add(comment)
    post.comment_count = (post.comment_count or 0) + 1
    await db.commit()
    await db.refresh(comment)

    # Notify post author when someone comments (not self-comment)
    if str(post.user_id) != str(current_user.id):
        try:
            from app.services.notification_push_service import NotificationPushService

            push_svc = NotificationPushService(db)
            preview = content[:80] + ("..." if len(content) > 80 else "")
            await push_svc.create_and_push(
                user_id=post.user_id,
                title="New comment on your post",
                content=f"{current_user.username}: {preview}",
                notification_type="social",
                data={"post_id": str(post_id), "comment_id": str(comment.id)},
            )
        except Exception:
            logger.debug(
                "Failed to push comment notification for post={}", post_id, exc_info=True
            )

    return {
        "id": str(comment.id),
        "post_id": str(comment.post_id),
        "user_id": str(comment.user_id),
        "content": comment.content,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
    }


# route-tier: authed
@router.delete("/posts/{post_id}", summary="删除动态")
async def delete_post(
    post_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a post. Only the post owner can delete it."""
    post = (
        await db.execute(
            select(Post).where(
                Post.id == post_id,
                Post.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if str(post.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not your post")

    post.soft_delete()
    await db.commit()
    return {"deleted": True}


@router.delete("/posts/{post_id}/comments/{comment_id}", summary="删除评论")
async def delete_post_comment(
    post_id: UUID,
    comment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete own comment."""
    comment = (
        await db.execute(
            select(PostComment).where(
                PostComment.id == comment_id,
                PostComment.post_id == post_id,
            )
        )
    ).scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if str(comment.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not your comment")

    post = (
        await db.execute(select(Post).where(Post.id == post_id))
    ).scalar_one_or_none()
    if post:
        post.comment_count = max(0, (post.comment_count or 1) - 1)

    await db.delete(comment)
    await db.commit()
    return {"deleted": True}


def _build_message_info(msg: GroupMessage) -> MessageInfo:
    sender = None
    if msg.sender:
        sender = UserBrief(
            id=msg.sender.id,
            username=msg.sender.username,
            nickname=msg.sender.nickname,
            avatar_url=msg.sender.avatar_url,
            flame_level=msg.sender.flame_level,
            flame_brightness=msg.sender.flame_brightness,
        )

    read_receipts = sorted(
        getattr(msg, "read_receipts", []) or [],
        key=lambda receipt: receipt.read_at,
    )
    read_by = [receipt.user_id for receipt in read_receipts]
    read_by_users = [
        UserBrief(
            id=receipt.user.id,
            username=receipt.user.username,
            nickname=receipt.user.nickname,
            avatar_url=receipt.user.avatar_url,
            flame_level=receipt.user.flame_level,
            flame_brightness=receipt.user.flame_brightness,
        )
        for receipt in read_receipts
        if receipt.user is not None
    ]

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
                flame_brightness=msg.reply_to.sender.flame_brightness,
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
            read_by=None,
            read_by_users=None,
            quoted_message=None,  # Stop recursion
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
        read_by=read_by or None,
        read_by_users=read_by_users or None,
        quoted_message=quoted_message,
    )


def _build_group_file_info(
    group_file: GroupFile,
    member_role,
    *,
    is_in_my_library: bool = False,
) -> GroupFileInfo:
    shared_by = None
    uploader_name = None
    if group_file.shared_by:
        uploader_name = group_file.shared_by.nickname or group_file.shared_by.full_name or group_file.shared_by.username
        shared_by = UserBrief(
            id=group_file.shared_by.id,
            username=group_file.shared_by.username,
            nickname=group_file.shared_by.nickname,
            avatar_url=group_file.shared_by.avatar_url,
            flame_level=group_file.shared_by.flame_level,
            flame_brightness=group_file.shared_by.flame_brightness,
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
        description=group_file.description,
        uploader_name=uploader_name,
        tags=group_file.tags or [],
        trust_level=group_file.trust_level.value,
        knowledge_base=group_file.is_knowledge_base,
        view_role=group_file.view_role,
        download_role=group_file.download_role,
        manage_role=group_file.manage_role,
        file_name=stored_file.file_name,
        mime_type=stored_file.mime_type,
        file_size=stored_file.file_size,
        status=stored_file.status,
        visibility=stored_file.visibility,
        download_count=group_file.download_count,
        citation_count=group_file.citation_count,
        rating_count=group_file.rating_count,
        average_rating=GroupFileService.average_rating(group_file),
        quality_score=GroupFileService.quality_score(group_file),
        retrieval_boost=GroupFileService.retrieval_boost(group_file),
        is_in_my_library=is_in_my_library,
        can_download=GroupFileService.can_download(member_role, group_file.download_role),
        can_manage=GroupFileService.can_manage(member_role, group_file.manage_role),
    )


def _build_file_copy_response(
    *,
    file_id: UUID,
    status: str,
    job_id: str | None,
    already_in_library: bool,
) -> FileCopyResponse:
    return FileCopyResponse(
        file_id=file_id,
        status=status,
        job_id=job_id,
        already_in_library=already_in_library,
        suggested_nodes_route=f"/api/v1/galaxy/documents/{file_id}/suggested-nodes",
    )


def _build_group_member_info(member: GroupMember) -> GroupMemberInfo:
    return GroupMemberInfo(
        user=UserBrief.model_validate(member.user),
        role=member.role,
        flame_contribution=member.flame_contribution,
        tasks_completed=member.tasks_completed,
        checkin_streak=member.checkin_streak,
        joined_at=member.joined_at,
        last_active_at=member.last_active_at,
    )


def _build_friendship_info(
    friendship,
    friend: User,
    current_user_id: UUID,
    accountability: AccountabilityFriendSummary | None = None,
) -> FriendshipInfo:
    return FriendshipInfo(
        id=friendship.id,
        created_at=friendship.created_at,
        updated_at=friendship.updated_at,
        friend=UserBrief(
            id=friend.id,
            username=friend.username,
            nickname=friend.nickname,
            avatar_url=friend.avatar_url,
            flame_level=friend.flame_level,
            flame_brightness=friend.flame_brightness,
            status=friend.status,
        ),
        status=friendship.status,
        match_reason=friendship.match_reason,
        initiated_by_me=friendship.initiated_by == current_user_id,
        accountability=accountability,
    )


async def _build_accountability_summary_for_friend(
    db: AsyncSession,
    partnership: AccountabilityPartnership,
    current_user: User,
) -> AccountabilityFriendSummary:
    stats = None
    if partnership.status == AccountabilityStatus.ACTIVE:
        stats = await _build_partnership_stats_payload(db, partnership, current_user)
    last_checkin_at = await _get_last_checkin_at(db, partnership.id)
    my_role = "initiator" if str(partnership.initiator_id) == str(current_user.id) else "partner"
    goal_preview = partnership.partner_goal if my_role == "initiator" else partnership.initiator_goal
    return AccountabilityFriendSummary(
        partnership_id=partnership.id,
        slot_type=_slot_type_value(partnership.slot_type),
        status=partnership.status.value if hasattr(partnership.status, "value") else str(partnership.status),
        my_role=my_role,
        my_checked_in_today=stats.my_checked_in_today if stats else None,
        partner_checked_in_today=stats.partner_checked_in_today if stats else None,
        my_streak_days=stats.my_streak_days if stats else None,
        partner_streak_days=stats.partner_streak_days if stats else None,
        last_checkin_at=last_checkin_at,
        goal_preview=goal_preview,
    )


def _friendship_sort_key(friendship_info: FriendshipInfo) -> tuple[int, float]:
    summary = friendship_info.accountability
    if summary is None:
        return (2, -friendship_info.updated_at.timestamp())
    if summary.status == AccountabilityStatus.ACTIVE.value:
        return (0, -friendship_info.updated_at.timestamp())
    if summary.status == AccountabilityStatus.PENDING.value:
        return (1, -friendship_info.updated_at.timestamp())
    return (2, -friendship_info.updated_at.timestamp())


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
            quoted_message=None,
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
        quoted_message=quoted_message,
    )


def _is_self_only_visibility(content_data: dict | None, user_id: UUID) -> bool:
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


def _normalize_self_visibility(content_data: dict | None, user_id: UUID) -> dict | None:
    if not content_data:
        return content_data
    if content_data.get("visibility") != "self":
        return content_data
    if content_data.get("visible_to") is not None:
        return content_data
    updated = dict(content_data)
    updated["visible_to"] = str(user_id)
    return updated


def _truncate_text(text: str | None, limit: int = 160) -> str | None:
    if not text:
        return None
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: max(0, limit - 3)].rstrip()}..."


def _compact_dict(data: dict) -> dict:
    return {k: v for k, v in data.items() if v is not None}


def _share_owner_payload(user: User | None) -> dict | None:
    if user is None:
        return None
    return _compact_dict(
        {
            "user_id": str(user.id),
            "display_name": user.nickname or user.full_name or user.username,
            "avatar_url": user.avatar_url,
        }
    )


def _build_share_meta(resource_type: SharedResourceType, resource: object) -> dict:
    if resource_type == SharedResourceType.PLAN:
        plan = resource
        return _compact_dict(
            {
                "plan_type": plan.type.value if plan.type else None,
                "subject": plan.subject,
                "progress": plan.progress,
                "target_date": plan.target_date.isoformat() if plan.target_date else None,
                "total_estimated_hours": plan.total_estimated_hours,
            }
        )
    if resource_type == SharedResourceType.TASK:
        task = resource
        return _compact_dict(
            {
                "task_type": task.type.value if task.type else None,
                "status": task.status.value if task.status else None,
                "estimated_minutes": task.estimated_minutes,
                "difficulty": task.difficulty,
                "tags": task.tags or [],
                "due_date": task.due_date.isoformat() if task.due_date else None,
            }
        )
    if resource_type == SharedResourceType.KNOWLEDGE_NODE:
        node = resource
        return _compact_dict(
            {
                "importance_level": node.importance_level,
                "keywords": node.keywords or [],
                "source_type": node.source_type,
            }
        )
    if resource_type == SharedResourceType.SEED_LIBRARY:
        library = resource
        return _compact_dict(
            {
                "category": library.category,
                "visibility": library.visibility,
                "language": library.language,
                "tags": library.tags or [],
                "is_official": library.is_official,
            }
        )
    if resource_type == SharedResourceType.SEED_ITEM:
        item = resource
        return _compact_dict(
            {
                "item_type": item.item_type,
                "subject": item.subject,
                "difficulty_level": item.difficulty_level,
                "tags": item.tags or [],
                "library_id": str(item.library_id),
            }
        )
    if resource_type == SharedResourceType.CURIOSITY_CAPSULE:
        capsule = resource
        return _compact_dict(
            {
                "related_subject": capsule.related_subject,
                "related_task_id": str(capsule.related_task_id) if capsule.related_task_id else None,
            }
        )
    if resource_type == SharedResourceType.COGNITIVE_PRISM_PATTERN:
        pattern = resource
        return _compact_dict(
            {
                "pattern_type": pattern.pattern_type,
                "confidence_score": pattern.confidence_score,
                "frequency": pattern.frequency,
                "is_archived": pattern.is_archived,
            }
        )
    fragment = resource
    return _compact_dict(
        {
            "source_type": fragment.source_type,
            "severity": fragment.severity,
            "tags": fragment.tags,
            "error_tags": fragment.error_tags,
            "context_tags": fragment.context_tags,
        }
    )


def _build_share_brief(resource_type: SharedResourceType, resource: object) -> dict:
    if resource_type == SharedResourceType.PLAN:
        plan = resource
        title = plan.name
        summary = plan.description or plan.subject
    elif resource_type == SharedResourceType.TASK:
        task = resource
        title = task.title
        summary = task.user_note or task.guide_content
    elif resource_type == SharedResourceType.KNOWLEDGE_NODE:
        node = resource
        title = node.name
        summary = node.description
    elif resource_type == SharedResourceType.SEED_LIBRARY:
        library = resource
        title = library.name
        summary = library.description or f"{library.category} library"
    elif resource_type == SharedResourceType.SEED_ITEM:
        item = resource
        title = item.title or "Seed Item"
        summary = item.content
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

    return {"title": title, "summary": _truncate_text(summary, 160), "meta": _build_share_meta(resource_type, resource)}


def _share_message_type(resource_type: SharedResourceType) -> MessageTypeEnum:
    if resource_type == SharedResourceType.PLAN:
        return MessageTypeEnum.PLAN_SHARE
    if resource_type == SharedResourceType.TASK:
        return MessageTypeEnum.TASK_SHARE
    if resource_type == SharedResourceType.KNOWLEDGE_NODE:
        return MessageTypeEnum.CAPSULE_SHARE
    if resource_type == SharedResourceType.SEED_LIBRARY:
        return MessageTypeEnum.CAPSULE_SHARE
    if resource_type == SharedResourceType.SEED_ITEM:
        return MessageTypeEnum.CAPSULE_SHARE
    if resource_type == SharedResourceType.CURIOSITY_CAPSULE:
        return MessageTypeEnum.CAPSULE_SHARE
    if resource_type == SharedResourceType.COGNITIVE_PRISM_PATTERN:
        return MessageTypeEnum.PRISM_SHARE
    return MessageTypeEnum.FRAGMENT_SHARE


def _legacy_permission_to_share_permission(permission: str | None) -> SharePermission:
    normalized = (permission or "view").strip().lower()
    if normalized == "fork":
        return SharePermission.FORK
    if normalized in {"edit", "adopt"}:
        return SharePermission.ADOPT
    if normalized == "comment":
        return SharePermission.COMMENT
    return SharePermission.VIEW


async def _get_share_resource(db: AsyncSession, resource_type: SharedResourceType, resource_id: UUID, owner_id: UUID):
    seed_service = SeedLibraryService()
    if resource_type == SharedResourceType.PLAN:
        plan = await db.get(Plan, resource_id)
        if not plan:
            raise HTTPException(status_code=404, detail="没有找到这个学习计划")
        if plan.user_id != owner_id:
            raise HTTPException(status_code=403, detail="您没有权限分享这个计划")
        return plan
    if resource_type == SharedResourceType.TASK:
        task = await db.get(Task, resource_id)
        if not task:
            raise HTTPException(status_code=404, detail="没有找到这个任务")
        if task.user_id != owner_id:
            raise HTTPException(status_code=403, detail="您没有权限分享这个任务")
        return task
    if resource_type == SharedResourceType.KNOWLEDGE_NODE:
        node = await db.get(KnowledgeNode, resource_id)
        if not node:
            raise HTTPException(status_code=404, detail="没有找到这个知识节点")
        return node
    if resource_type == SharedResourceType.SEED_LIBRARY:
        library = await seed_service.get_library(db, resource_id)
        if not library:
            raise HTTPException(status_code=404, detail="没有找到这个种子库")
        if not await seed_service.can_access_library(db, library, owner_id):
            raise HTTPException(status_code=403, detail="您没有权限分享这个种子库")
        return library
    if resource_type == SharedResourceType.SEED_ITEM:
        item = await seed_service.get_item_for_user(db, resource_id, owner_id)
        if not item:
            raise HTTPException(status_code=404, detail="没有找到这个种子内容")
        return item
    if resource_type == SharedResourceType.CURIOSITY_CAPSULE:
        capsule = await db.get(CuriosityCapsule, resource_id)
        if not capsule:
            raise HTTPException(status_code=404, detail="没有找到这个知识胶囊")
        if capsule.user_id != owner_id:
            raise HTTPException(status_code=403, detail="您没有权限分享这个知识胶囊")
        return capsule
    if resource_type == SharedResourceType.COGNITIVE_PRISM_PATTERN:
        pattern = await db.get(BehaviorPattern, resource_id)
        if not pattern:
            raise HTTPException(status_code=404, detail="没有找到这个认知棱镜")
        if pattern.user_id != owner_id:
            raise HTTPException(status_code=403, detail="您没有权限分享这个认知棱镜")
        return pattern
    fragment = await db.get(CognitiveFragment, resource_id)
    if not fragment:
        raise HTTPException(status_code=404, detail="没有找到这个认知碎片")
    if fragment.user_id != owner_id:
        raise HTTPException(status_code=403, detail="您没有权限分享这个认知碎片")
    return fragment


# ============ 好友系统 ============


# route-tier: authed
@router.post("/friends/request", summary="发送好友请求")
@limiter.limit("5/minute")
async def send_friend_request(
    request: Request,
    data: FriendRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    发送好友请求

    - **target_user_id**: 目标用户ID
    - **message**: 可选的请求消息

    注意：如果被对方拉黑，将无法发送好友请求
    """
    # 检查是否被对方拉黑
    if await UserBlockService.is_blocked(db, current_user.id, data.target_user_id):
        raise HTTPException(status_code=403, detail="由于对方的隐私设置，无法发送请求")

    try:
        friendship = await FriendshipService.send_friend_request(db, current_user.id, data.target_user_id)
        await db.commit()

        if friendship.status == FriendshipStatus.PENDING and str(friendship.initiated_by) == str(current_user.id):
            from app.services.notification_push_service import NotificationPushService

            sender_name = current_user.nickname or current_user.full_name or current_user.username or "新朋友"
            try:
                push_svc = NotificationPushService(db)
                await push_svc.create_and_push(
                    user_id=data.target_user_id,
                    title="新的好友请求",
                    content=f"{sender_name} 向你发来了好友请求",
                    notification_type="friend_request",
                    data={
                        "friendship_id": str(friendship.id),
                        "from_user_id": str(current_user.id),
                        "message": data.message,
                    },
                )
            except Exception as exc:
                logger.warning(f"Failed to send friend request notification for friendship {friendship.id}: {exc}")

        return {"success": True, "friendship_id": str(friendship.id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# route-tier: authed
@router.post("/friends/respond", summary="响应好友请求")
async def respond_to_friend_request(
    data: FriendResponse, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """接受或拒绝好友请求"""
    try:
        friendship = await FriendshipService.respond_to_request(db, current_user.id, data.friendship_id, data.accept)
        await db.commit()

        # Notify the original requester of the response
        if friendship and data.accept:
            try:
                from app.services.notification_push_service import NotificationPushService
                push_svc = NotificationPushService(db)
                responder_name = current_user.nickname or current_user.full_name or current_user.username or "用户"
                await push_svc.create_and_push(
                    user_id=friendship.initiated_by,
                    title="好友请求已接受",
                    content=f"{responder_name} 已接受你的好友请求",
                    notification_type="friend_request_accepted",
                    data={"friendship_id": str(data.friendship_id)},
                )
            except Exception as exc:
                logger.warning(f"Failed to send friend acceptance notification: {exc}")

        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# route-tier: authed
@router.delete("/friends/{friendship_id}", summary="删除好友")
async def delete_friend(
    friendship_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    删除好友关系

    - 双方都会解除好友关系
    - 不会拉黑对方
    """
    try:
        await FriendshipService.delete_friendship(db, current_user.id, friendship_id)
        await db.commit()
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# route-tier: authed
@router.get("/friends", response_model=list[FriendshipInfo], summary="获取好友列表")
async def get_friends(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的好友列表"""
    friends = await FriendshipService.get_friends(db, current_user.id, limit=limit, offset=offset)
    friend_ids = [friend.id for _, friend in friends]
    accountability_map: dict[str, AccountabilityFriendSummary] = {}
    if friend_ids:
        partnership_result = await db.execute(
            select(AccountabilityPartnership).where(
                and_(
                    AccountabilityPartnership.slot_type == AccountabilitySlotType.CORE,
                    AccountabilityPartnership.status.in_(
                        [
                            AccountabilityStatus.ACTIVE,
                            AccountabilityStatus.PENDING,
                        ]
                    ),
                    or_(
                        and_(
                            AccountabilityPartnership.initiator_id == current_user.id,
                            AccountabilityPartnership.partner_id.in_(friend_ids),
                        ),
                        and_(
                            AccountabilityPartnership.partner_id == current_user.id,
                            AccountabilityPartnership.initiator_id.in_(friend_ids),
                        ),
                    ),
                )
            )
        )
        for partnership in partnership_result.scalars().all():
            friend_id = (
                str(partnership.partner_id)
                if str(partnership.initiator_id) == str(current_user.id)
                else str(partnership.initiator_id)
            )
            accountability_map[friend_id] = await _build_accountability_summary_for_friend(
                db,
                partnership,
                current_user,
            )

    payload = [
        _build_friendship_info(
            friendship,
            friend,
            current_user.id,
            accountability=accountability_map.get(str(friend.id)),
        )
        for friendship, friend in friends
    ]
    payload.sort(key=_friendship_sort_key)
    return payload


# route-tier: authed
@router.get("/friends/pending", response_model=list[FriendshipInfo], summary="获取待处理的好友请求")
async def get_pending_requests(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """获取收到的待处理好友请求"""
    requests = await FriendshipService.get_pending_requests(db, current_user.id)
    return [
        _build_friendship_info(friendship, friendship.initiator, current_user.id)
        for friendship in requests
        if friendship.initiator is not None
    ]


# route-tier: authed
@router.get("/friends/{friend_id}/profile", summary="获取好友详情资料")
async def get_friend_profile(
    friend_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取好友公开资料及责任伙伴摘要。"""
    friendship_result = await db.execute(
        select(Friendship).where(
            and_(
                Friendship.status == FriendshipStatus.ACCEPTED,
                Friendship.not_deleted_filter(),
                or_(
                    and_(
                        Friendship.user_id == current_user.id,
                        Friendship.friend_id == friend_id,
                    ),
                    and_(
                        Friendship.user_id == friend_id,
                        Friendship.friend_id == current_user.id,
                    ),
                ),
            )
        )
    )
    friendship = friendship_result.scalar_one_or_none()
    if not friendship:
        raise HTTPException(status_code=404, detail="Friendship not found")

    friend = await db.get(User, friend_id)
    if friend is None:
        raise HTTPException(status_code=404, detail="Friend not found")

    partnership_result = await db.execute(
        select(AccountabilityPartnership)
        .where(
            and_(
                AccountabilityPartnership.slot_type == AccountabilitySlotType.CORE,
                or_(
                    and_(
                        AccountabilityPartnership.initiator_id == current_user.id,
                        AccountabilityPartnership.partner_id == friend_id,
                    ),
                    and_(
                        AccountabilityPartnership.initiator_id == friend_id,
                        AccountabilityPartnership.partner_id == current_user.id,
                    ),
                ),
            )
        )
        .order_by(AccountabilityPartnership.updated_at.desc())
    )
    partnership = partnership_result.scalars().first()
    relationship_summary = None
    accountability = None
    achievements_summary = {"my_total_unlocked": 0, "partner_total_unlocked": 0}
    leaderboard_summary = await _build_leaderboard_summary(
        db,
        current_user_id=current_user.id,
        partner_id=friend_id,
    )
    recent_shares = await _build_recent_shares_payload(
        db,
        current_user_id=current_user.id,
        partner_id=friend_id,
    )
    if partnership is not None:
        relationship_summary = await _build_relationship_summary(db, partnership, current_user)
        accountability = await _build_partnership_out(db, partnership, current_user)
        achievements_payload = await _build_partnership_achievements_payload(db, partnership, current_user)
        achievements_summary = {
            "my_total_unlocked": achievements_payload["my_total_unlocked"],
            "partner_total_unlocked": achievements_payload["partner_total_unlocked"],
            "partner_achievements": achievements_payload["partner_achievements"],
        }

    return {
        "user": {
            "id": str(friend.id),
            "username": friend.username,
            "nickname": friend.nickname,
            "avatar_url": friend.avatar_url,
            "flame_level": friend.flame_level,
            "flame_brightness": friend.flame_brightness,
            "status": friend.status.value if friend.status else "offline",
        },
        "friendship": {
            "id": str(friendship.id),
            "status": friendship.status.value if hasattr(friendship.status, "value") else str(friendship.status),
            "initiated_by_me": str(friendship.initiated_by) == str(current_user.id),
            "created_at": friendship.created_at.isoformat() if friendship.created_at else None,
        },
        "accountability": accountability.model_dump(mode="json") if accountability else None,
        "relationship_summary": relationship_summary,
        "achievements_summary": achievements_summary,
        "leaderboard_summary": leaderboard_summary,
        "recent_shares": recent_shares,
        "quick_actions": {
            "can_invite_accountability": partnership is None or partnership.status == AccountabilityStatus.ENDED,
            "can_open_dashboard": partnership is not None and partnership.status == AccountabilityStatus.ACTIVE,
            "can_chat": True,
            "can_share": True,
        },
    }


# route-tier: authed
@router.get("/users/search", response_model=list[UserBrief], summary="搜索用户")
@limiter.limit("20/minute")
async def search_users(
    request: Request,
    keyword: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=20),  # 降低默认搜索结果数量
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    搜索用户（用于添加好友）

    支持按用户名或昵称搜索

    隐私保护：
    - 不可搜索的用户不会出现在结果中
    - 已拉黑当前用户的用户不会出现在结果中
    """
    # 使用带隐私过滤的搜索服务
    users = await UserSearchService.search_users(db=db, query=keyword, current_user_id=current_user.id, limit=limit)

    return [
        UserBrief(
            id=user.id,
            username=user.username,
            nickname=user.nickname,
            avatar_url=user.avatar_url,
            flame_level=user.flame_level,
            flame_brightness=user.flame_brightness,
            status=user.status,
        )
        for user in users
    ]


# ============ 用户拉黑 API ============


# route-tier: authed
@router.post("/users/block", summary="拉黑用户")
@limiter.limit("10/hour")
async def block_user(
    request: Request,
    data: BlockUserRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    拉黑用户

    - 拉黑后自动解除好友关系
    - 拉黑后对方无法发送消息或好友请求
    """
    await UserBlockService.block_user(
        db=db, blocker_id=current_user.id, blocked_id=data.target_user_id, reason=data.reason
    )
    await db.commit()

    return {"success": True, "message": "已拉黑该用户"}


# route-tier: authed
@router.delete("/users/block/{user_id}", summary="解除拉黑")
@limiter.limit("20/hour")
async def unblock_user(
    request: Request, user_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """解除拉黑用户"""
    await UserBlockService.unblock_user(db=db, blocker_id=current_user.id, blocked_id=user_id)
    await db.commit()

    return {"success": True, "message": "已解除拉黑"}


# route-tier: authed
@router.get("/users/blocked", response_model=list[BlockUserInfo], summary="获取拉黑列表")
async def get_blocked_users(
    request: Request,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户拉黑的用户列表"""
    blocks = await UserBlockService.get_blocked_users(db=db, blocker_id=current_user.id, limit=limit, offset=offset)

    return [
        BlockUserInfo(
            id=block.id,
            created_at=block.created_at,
            updated_at=block.updated_at,
            blocked_user=UserBrief(
                id=block.blocked.id,
                username=block.blocked.username,
                nickname=block.blocked.nickname,
                avatar_url=block.blocked.avatar_url,
                flame_level=block.blocked.flame_level,
                flame_brightness=block.blocked.flame_brightness,
                status=block.blocked.status,
            ),
            reason=block.reason,
        )
        for block in blocks
    ]


# route-tier: authed
@router.put("/users/privacy", summary="更新用户隐私设置")
async def update_privacy_settings(
    request: Request,
    data: UserPrivacySettings,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    更新用户隐私设置

    - everyone: 所有人可搜索
    - friends: 仅好友可搜索
    - nobody: 不可被搜索
    """
    await UserSearchService.update_searchability(db=db, user_id=current_user.id, searchable_by=data.searchable_by.value)
    await db.commit()

    return {"success": True, "searchable_by": data.searchable_by.value}


# route-tier: authed
@router.get("/users/privacy", response_model=UserPrivacySettings, summary="获取用户隐私设置")
async def get_privacy_settings(
    request: Request, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """获取当前用户的隐私设置"""
    searchable_by = await UserSearchService.get_user_searchability(db=db, user_id=current_user.id)

    return UserPrivacySettings(searchable_by=SearchVisibilityEnum(searchable_by))


# route-tier: authed
@router.get("/friends/recommendations", response_model=list[FriendRecommendation], summary="获取好友推荐")
@limiter.limit("10/minute")
async def get_friend_recommendations(
    request: Request,
    limit: int = Query(default=10, ge=1, le=50),
    strategy: FriendMatchStrategyEnum = Query(default=FriendMatchStrategyEnum.COMPATIBILITY),
    target: FriendRecommendationTargetEnum = Query(default=FriendRecommendationTargetEnum.ACCOUNTABILITY),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """基于用户画像、学习轨迹和责任伙伴可用性推荐潜在好友/责任伙伴。"""
    recommendations = await FriendMatchService.get_recommendations(
        db,
        current_user,
        limit=limit,
        strategy=strategy,
        target=target,
    )
    await db.commit()
    return recommendations


# route-tier: authed
@router.post("/friends/recommendations/feedback", summary="提交好友推荐反馈")
async def submit_friend_recommendation_feedback(
    data: FriendRecommendationFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await RecommendationFeedbackService.record_friend_feedback(db, current_user.id, data)
    await db.commit()
    return {"success": True}


# route-tier: authed
@router.get(
    "/recommendations/feedback/prompts",
    response_model=list[RecommendationFeedbackPrompt],
    summary="获取待处理推荐反馈提示",
)
async def get_recommendation_feedback_prompts(
    item_type: RecommendationItemTypeEnum | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prompts = await RecommendationFeedbackService.get_pending_prompts(
        db,
        current_user.id,
        item_type=item_type,
        limit=limit,
    )
    await db.commit()
    return prompts


# route-tier: authed
@router.get(
    "/recommendations/feedback/insights",
    response_model=list[RecommendationFeedbackInsight],
    summary="获取推荐反馈洞察",
)
async def get_recommendation_feedback_insights(
    item_type: RecommendationItemTypeEnum | None = Query(default=None),
    days: int = Query(default=30, ge=7, le=180),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    insights = await RecommendationFeedbackService.get_feedback_insights(
        db,
        current_user.id,
        item_type=item_type,
        days=days,
    )
    await db.commit()
    return insights


# ============ WebSocket ============


@router.websocket("/groups/{group_id}/ws")
async def websocket_endpoint(
    websocket: WebSocket, group_id: UUID, token: str | None = Query(None), db: AsyncSession = Depends(get_db)
):
    """
    群组实时通讯 WebSocket 接口
    连接地址: ws://host/api/v1/community/groups/{group_id}/ws?token={jwt_token}
    """
    try:
        auth_token = token if settings.WS_ALLOW_QUERY_TOKEN else None
        auth_token = auth_token or _extract_ws_token(websocket)
        if not auth_token:
            await websocket.close(code=4003)
            return

        # 验证 Token
        payload = await decode_token(auth_token, expected_type="access")
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4003)
            return

        membership_result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id, GroupMember.user_id == UUID(user_id), GroupMember.not_deleted_filter()
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
                except (json.JSONDecodeError, TypeError):
                    # Non-json or other messages, ignore
                    pass
        except WebSocketDisconnect:
            manager.disconnect(websocket, str(group_id), user_id)

    except Exception as e:
        print(f"WebSocket Error: {e}")
        # 尝试关闭连接
        with contextlib.suppress(BaseException):
            await websocket.close()


def _extract_ws_token(websocket: WebSocket) -> str | None:
    auth_header = websocket.headers.get("authorization")
    if auth_header:
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()

    protocol = websocket.headers.get("sec-websocket-protocol")
    if protocol:
        for part in protocol.split(","):
            candidate = part.strip()
            lower = candidate.lower()
            if lower.startswith("bearer "):
                return candidate[7:].strip()
            if lower.startswith("token="):
                return candidate[6:].strip()
            if lower.startswith("token:"):
                return candidate[6:].strip()

    if settings.WS_ALLOW_QUERY_TOKEN:
        return websocket.query_params.get("token")
    return None


# ============ 群组管理 ============


# route-tier: authed
@router.post("/groups", response_model=GroupInfo, summary="创建群组")
async def create_group(
    data: GroupCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
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


# route-tier: authed
@router.get("/groups/search", response_model=list[GroupListItem], summary="搜索公开群组")
async def search_groups(
    keyword: str | None = None,
    group_type: GroupTypeEnum | None = None,
    tags: list[str] | None = Query(default=None),
    sort_by: GroupDirectorySortEnum = Query(default=GroupDirectorySortEnum.LATEST),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """搜索公开群组"""
    model_type = GroupType(group_type.value) if group_type else None
    groups = await GroupService.search_groups(
        db,
        keyword,
        model_type,
        tags,
        limit,
        offset=offset,
        sort_by=sort_by.value,
        user_id=current_user.id,
    )

    result = []
    for group_dict in groups:
        days_remaining = None
        deadline = group_dict.get("deadline")
        if deadline:
            delta = deadline - _utcnow()
            days_remaining = max(0, delta.days)

        result.append(
            GroupListItem(
                id=group_dict["id"],
                name=group_dict["name"],
                description=group_dict.get("description"),
                type=GroupTypeEnum(group_dict["type"].value),
                member_count=group_dict["member_count"],
                total_flame_power=group_dict["total_flame_power"],
                today_checkin_count=group_dict.get("today_checkin_count", 0),
                deadline=deadline,
                days_remaining=days_remaining,
                focus_tags=group_dict.get("focus_tags", []),
                sprint_goal=group_dict.get("sprint_goal"),
                is_public=group_dict.get("is_public", True),
                join_requires_approval=group_dict.get("join_requires_approval", False),
                activity_score=group_dict.get("activity_score"),
                my_role=group_dict.get("my_role"),
            )
        )
    return result


# route-tier: authed
@router.get("/groups/directory", response_model=GroupDirectoryResponse, summary="公开群组目录")
async def get_group_directory(
    keyword: str | None = None,
    group_type: GroupTypeEnum | None = None,
    tags: list[str] | None = Query(default=None),
    sort_by: GroupDirectorySortEnum = Query(default=GroupDirectorySortEnum.HOT),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """公开群组目录，整合推荐、标签和公开浏览。"""
    model_type = GroupType(group_type.value) if group_type else None
    groups = await GroupService.search_groups(
        db,
        keyword,
        model_type,
        tags,
        limit,
        offset=offset,
        sort_by=sort_by.value,
        user_id=current_user.id,
    )
    total_count = await GroupService.count_public_groups(
        db,
        keyword=keyword,
        group_type=model_type,
        tags=tags,
    )
    available_tags = await GroupService.get_public_group_tags(db)
    recommendations: list[GroupRecommendationItem] = []
    if offset == 0 and not keyword and not tags and group_type is None:
        recommendations = await GroupRecommendationService.get_recommendations(
            db,
            current_user.id,
            limit=6,
            cursor=0,
        )

    items: list[GroupListItem] = []
    for group_dict in groups:
        days_remaining = None
        deadline = group_dict.get("deadline")
        if deadline:
            delta = deadline - _utcnow()
            days_remaining = max(0, delta.days)
        items.append(
            GroupListItem(
                id=group_dict["id"],
                name=group_dict["name"],
                description=group_dict.get("description"),
                type=GroupTypeEnum(group_dict["type"].value),
                member_count=group_dict["member_count"],
                total_flame_power=group_dict["total_flame_power"],
                today_checkin_count=group_dict.get("today_checkin_count", 0),
                deadline=deadline,
                days_remaining=days_remaining,
                focus_tags=group_dict.get("focus_tags", []),
                sprint_goal=group_dict.get("sprint_goal"),
                is_public=group_dict.get("is_public", True),
                join_requires_approval=group_dict.get("join_requires_approval", False),
                activity_score=group_dict.get("activity_score"),
                my_role=group_dict.get("my_role"),
            )
        )

    await db.commit()
    return GroupDirectoryResponse(
        sort_by=sort_by,
        keyword=keyword,
        applied_tags=tags or [],
        available_tags=available_tags,
        total_count=total_count,
        recommendations=recommendations,
        groups=items,
    )


# route-tier: authed
@router.get("/groups/recommendations", response_model=list[GroupRecommendationItem], summary="群组推荐")
async def get_group_recommendations(
    limit: int = Query(default=20, ge=1, le=50),
    cursor: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取群组推荐列表"""
    recommendations = await GroupRecommendationService.get_recommendations(
        db,
        current_user.id,
        limit=limit,
        cursor=cursor,
    )
    await db.commit()
    return recommendations


# route-tier: authed
@router.post("/groups/recommendations/feedback", summary="群组推荐反馈")
async def group_recommendations_feedback(
    data: GroupRecommendationFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """记录群组推荐反馈"""
    await RecommendationFeedbackService.record_group_feedback(db, current_user.id, data)
    await db.commit()
    return {"success": True}


# route-tier: authed
@router.get("/groups/{group_id}", response_model=GroupInfo, summary="获取群组详情")
async def get_group(group_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """获取群组详细信息"""
    group = await GroupService.get_group(db, group_id, current_user.id)
    if not group:
        raise HTTPException(status_code=404, detail="没有找到这个群组")
    return group


# route-tier: authed
@router.post("/groups/{group_id}/join", summary="加入群组")
async def join_group(
    group_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """加入群组"""
    try:
        await GroupService.join_group(db, group_id, current_user.id)
        await db.commit()

        # Broadcast member joined event
        await manager.broadcast(
            {
                "type": "member_joined",
                "group_id": str(group_id),
                "user": UserBrief.model_validate(current_user).model_dump(mode="json"),
                "timestamp": datetime.now(UTC).isoformat(),
            },
            str(group_id),
        )

        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# route-tier: authed
@router.post("/groups/{group_id}/leave", summary="退出群组")
async def leave_group(
    group_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """退出群组"""
    try:
        await GroupService.leave_group(db, group_id, current_user.id)
        await db.commit()

        # Broadcast member left event
        await manager.broadcast(
            {
                "type": "member_left",
                "group_id": str(group_id),
                "user_id": str(current_user.id),
                "timestamp": datetime.now(UTC).isoformat(),
            },
            str(group_id),
        )

        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# route-tier: authed
@router.delete("/groups/{group_id}", summary="解散群组")
async def dissolve_group(
    group_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """解散群组（仅限群主）"""
    try:
        await GroupService.dissolve_group(db, group_id, current_user.id)
        await db.commit()
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


# route-tier: authed
@router.post("/groups/{group_id}/transfer", summary="转让群主")
async def transfer_group_owner(
    group_id: UUID,
    new_owner_id: UUID = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """转让群主身份"""
    try:
        await GroupService.transfer_owner(db, group_id, current_user.id, new_owner_id)
        await db.commit()

        # Broadcast owner transfer event
        await manager.broadcast(
            {
                "type": "owner_transferred",
                "group_id": str(group_id),
                "old_owner_id": str(current_user.id),
                "new_owner_id": str(new_owner_id),
                "timestamp": datetime.now(UTC).isoformat(),
            },
            str(group_id),
        )

        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# route-tier: authed
@router.get("/groups/{group_id}/members", response_model=list[GroupMemberInfo], summary="获取群成员列表")
async def get_group_members(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取群成员列表。"""
    try:
        members = await GroupService.get_group_members(db, group_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    return [_build_group_member_info(member) for member in members]


# route-tier: authed
@router.post("/groups/{group_id}/members/{user_id}/kick", summary="移出群成员")
async def kick_group_member(
    group_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """移出群成员。"""
    try:
        await GroupService.kick_member(db, group_id, current_user.id, user_id)
        await db.commit()
        await manager.broadcast(
            {
                "type": "member_kicked",
                "group_id": str(group_id),
                "user_id": str(user_id),
                "operator_id": str(current_user.id),
                "timestamp": datetime.now(UTC).isoformat(),
            },
            str(group_id),
        )
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


# route-tier: authed
@router.post("/groups/{group_id}/members/{user_id}/promote", summary="提升成员为管理员")
async def promote_group_member(
    group_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """提升成员为管理员。"""
    try:
        member = await GroupService.promote_member(db, group_id, current_user.id, user_id)
        await db.commit()
        await manager.broadcast(
            {
                "type": "member_role_updated",
                "group_id": str(group_id),
                "user_id": str(user_id),
                "role": member.role.value,
                "operator_id": str(current_user.id),
                "timestamp": datetime.now(UTC).isoformat(),
            },
            str(group_id),
        )
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


# route-tier: authed
@router.post("/groups/{group_id}/members/{user_id}/demote", summary="降级管理员为普通成员")
async def demote_group_member(
    group_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """降级管理员为普通成员。"""
    try:
        member = await GroupService.demote_member(db, group_id, current_user.id, user_id)
        await db.commit()
        await manager.broadcast(
            {
                "type": "member_role_updated",
                "group_id": str(group_id),
                "user_id": str(user_id),
                "role": member.role.value,
                "operator_id": str(current_user.id),
                "timestamp": datetime.now(UTC).isoformat(),
            },
            str(group_id),
        )
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


# route-tier: authed
@router.post("/groups/{group_id}/members/{user_id}/transfer-ownership", summary="转让群主")
async def transfer_group_owner_by_path(
    group_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """按移动端使用的路径转让群主身份。"""
    return await transfer_group_owner(group_id, user_id, current_user, db)


# route-tier: authed
@router.get("/groups", response_model=list[GroupListItem], summary="获取我的群组")
async def get_my_groups(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """获取当前用户加入的所有群组"""
    return await GroupService.get_my_groups(db, current_user.id)


# ============ 群消息 ============


# route-tier: authed
@router.post("/groups/{group_id}/messages", response_model=MessageInfo, summary="发送群消息")
@limiter.limit("30/minute")
async def send_message(
    request: Request,
    group_id: UUID,
    data: MessageSend,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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
            await manager.broadcast(message_info.model_dump(mode="json"), str(group_id))

        # 提及通知
        if message.mention_user_ids and not is_self_only:
            for mentioned_id in message.mention_user_ids:
                if str(mentioned_id) == str(current_user.id):
                    continue
                await manager.send_personal_message(
                    {"type": "mention", "group_id": str(group_id), "message": message_info.model_dump(mode="json")},
                    str(mentioned_id),
                )

        # 回传 ACK 给发送者
        if data.nonce:
            await manager.send_personal_message(
                {
                    "type": "ack",
                    "nonce": data.nonce,
                    "message_id": str(message.id),
                    "timestamp": message.created_at.isoformat(),
                },
                str(current_user.id),
            )

        return message_info
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# route-tier: authed
@router.get("/groups/{group_id}/messages", response_model=list[MessageInfo], summary="获取群消息")
async def get_messages(
    group_id: UUID,
    before_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取群消息（分页）"""
    try:
        messages = await GroupMessageService.get_messages(db, group_id, current_user.id, before_id, limit)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e

    result = []
    for msg in messages:
        result.append(_build_message_info(msg))
    return result


# route-tier: authed
@router.post(
    "/groups/{group_id}/messages/read",
    response_model=GroupMessageReadResponse,
    summary="标记群消息已读",
)
async def mark_group_messages_read(
    group_id: UUID,
    data: GroupMessageReadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """对当前用户可见且不晚于目标消息的群消息做幂等已读标记。"""
    try:
        updated_count, target_message = await GroupMessageService.mark_as_read(
            db,
            group_id=group_id,
            user_id=current_user.id,
            up_to_message_id=data.up_to_message_id,
        )
        await db.commit()
        await manager.broadcast(
            {
                "type": "read_receipt",
                "group_id": str(group_id),
                "up_to_message_id": str(target_message.id),
                "reader_id": str(current_user.id),
                "reader": UserBrief.model_validate(current_user).model_dump(mode="json"),
                "read_at": _utcnow().isoformat(),
                "updated_count": updated_count,
            },
            str(group_id),
        )
        return GroupMessageReadResponse(
            updated_count=updated_count,
            up_to_message_id=target_message.id,
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


# ============ 群文件 ============


# route-tier: authed
@router.post("/groups/{group_id}/files", response_model=GroupFileInfo, summary="分享文件到群组")
async def create_group_file_share(
    group_id: UUID,
    data: GroupFileCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        group_file, stored_file, _job_id = await GroupFileService.share_file(
            db,
            group_id=group_id,
            user_id=current_user.id,
            file_id=data.file_id,
            category=data.category,
            description=data.description,
            tags=None,
            view_role=GroupRole.MEMBER,
            download_role=GroupRole.MEMBER,
            manage_role=GroupRole.ADMIN,
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
                    "category": data.category,
                    "description": data.description,
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
        detailed_group_file = await GroupFileService._get_group_file(db, group_id=group_id, file_id=data.file_id)
        return _build_group_file_info(detailed_group_file, member.role, is_in_my_library=True)
    except PermissionError as e:
        await db.rollback()
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


# route-tier: authed
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
        group_file, stored_file, _job_id = await GroupFileService.share_file(
            db,
            group_id=group_id,
            user_id=current_user.id,
            file_id=file_id,
            category=data.category,
            description=data.description,
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
        detailed_group_file = await GroupFileService._get_group_file(db, group_id=group_id, file_id=file_id)
        return _build_group_file_info(detailed_group_file, member.role, is_in_my_library=True)
    except PermissionError as e:
        await db.rollback()
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


# route-tier: authed
@router.get("/groups/{group_id}/files", response_model=list[GroupFileInfo], summary="获取群文件列表")
async def list_group_files(
    group_id: UUID,
    category: str | None = Query(default=None),
    search_query: str | None = Query(default=None),
    sort_by: GroupFileSortEnum = Query(default=GroupFileSortEnum.LATEST),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        group_files, member_role = await GroupFileService.list_files(
            db,
            group_id=group_id,
            user_id=current_user.id,
            category=category,
            search_query=search_query,
            sort_by=sort_by.value,
            page=page,
            page_size=page_size,
        )
        return [
            _build_group_file_info(item.group_file, member_role, is_in_my_library=item.is_in_my_library)
            for item in group_files
        ]
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


# route-tier: authed
@router.post(
    "/groups/{group_id}/files/{file_id}/copy-to-library",
    response_model=FileCopyResponse,
    summary="复制群文件到个人资料库",
)
async def copy_group_file_to_library(
    group_id: UUID,
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await GroupFileService.copy_to_library(
            db,
            group_id=group_id,
            file_id=file_id,
            user_id=current_user.id,
        )
        await db.commit()

        if result.notify_owner_id:
            from app.services.notification_push_service import NotificationPushService

            push_svc = NotificationPushService(db)
            copier_name = current_user.nickname or current_user.full_name or current_user.username or "群成员"
            await push_svc.create_and_push(
                user_id=result.notify_owner_id,
                title="你的文档被保存了",
                content=f"{copier_name} 已将你的文档复制到个人资料库",
                notification_type="document_copied",
                data={
                    "source": "group_file",
                    "group_id": str(group_id),
                    "source_file_id": str(file_id),
                    "copied_file_id": str(result.stored_file.id),
                    "copied_by_user_id": str(current_user.id),
                },
            )

        return _build_file_copy_response(
            file_id=result.stored_file.id,
            status=result.stored_file.status,
            job_id=result.job_id,
            already_in_library=result.already_exists,
        )
    except PermissionError as e:
        await db.rollback()
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


# route-tier: authed
@router.post(
    "/users/{user_id}/share-file",
    response_model=FileCopyResponse,
    summary="直接分享文件给单个用户",
)
async def share_file_to_user(
    user_id: UUID,
    data: UserFileShareRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        if user_id == current_user.id:
            raise HTTPException(status_code=400, detail="不能分享给自己")

        owner_file = await GroupFileService._get_owned_file(db, user_id=current_user.id, file_id=data.file_id)
        if owner_file.visibility == "friends":
            are_friends = await FriendshipService.are_friends(db, current_user.id, user_id)
            if not are_friends:
                raise HTTPException(status_code=403, detail="好友可见文件只能分享给好友")

        result = await GroupFileService.share_file_to_user(
            db,
            owner_id=current_user.id,
            target_user_id=user_id,
            file_id=data.file_id,
        )

        message = await PrivateMessageService.send_message(
            db,
            current_user.id,
            PrivateMessageSend(
                target_user_id=user_id,
                message_type=MessageTypeEnum.FILE_SHARE,
                content=owner_file.file_name,
                content_data={
                    "file_id": str(owner_file.id),
                    "shared_copy_file_id": str(result.stored_file.id),
                    "file_name": owner_file.file_name,
                    "mime_type": owner_file.mime_type,
                    "file_size": owner_file.file_size,
                    "status": result.stored_file.status,
                },
            ),
        )

        await db.commit()
        message_info = _build_private_message_info(message)
        await manager.send_personal_message(message_info.model_dump(mode="json"), str(user_id))
        await manager.send_personal_message(message_info.model_dump(mode="json"), str(current_user.id))

        return _build_file_copy_response(
            file_id=result.stored_file.id,
            status=result.stored_file.status,
            job_id=result.job_id,
            already_in_library=result.already_exists,
        )
    except HTTPException:
        await db.rollback()
        raise
    except PermissionError as e:
        await db.rollback()
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


# route-tier: authed
@router.post(
    "/groups/{group_id}/knowledge-base/documents",
    response_model=GroupFileInfo,
    summary="添加群组官方知识库文档",
)
async def add_group_knowledge_base_document(
    group_id: UUID,
    data: GroupKnowledgeBaseDocumentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        group_file, _galaxy = await GroupKnowledgeService.designate_official_document(
            db,
            group_id=group_id,
            user_id=current_user.id,
            file_id=data.file_id,
            category=data.category,
            tags=data.tags,
        )
        await db.commit()
        member = await GroupService._require_active_member(db, group_id, current_user.id)
        return _build_group_file_info(group_file, member.role)
    except ValueError as e:
        await db.rollback()
        detail = str(e)
        status_code = 403 if "权限" in detail or "成员" in detail else 400
        raise HTTPException(status_code=status_code, detail=detail) from e


# route-tier: authed
@router.get(
    "/groups/{group_id}/knowledge-base",
    response_model=GroupKnowledgeBaseResponse,
    summary="获取群组知识库",
)
async def get_group_knowledge_base(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        documents, stats, galaxy = await GroupKnowledgeService.get_knowledge_base(db, group_id, current_user.id)
        member = await GroupService._require_active_member(db, group_id, current_user.id)
        return GroupKnowledgeBaseResponse(
            group_id=group_id,
            collaborative_galaxy_id=galaxy.id if galaxy else None,
            documents=[_build_group_file_info(item, member.role) for item in documents],
            stats=stats,
        )
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


# route-tier: authed
@router.get(
    "/groups/{group_id}/galaxy",
    response_model=GroupCollaborativeGalaxyResponse,
    summary="获取群组协作星图",
)
async def get_group_collaborative_galaxy(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await GroupKnowledgeService.get_group_galaxy(db, group_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


# route-tier: authed
@router.put("/groups/{group_id}/files/{file_id}/permissions", response_model=GroupFileInfo, summary="更新群文件权限")
async def update_group_file_permissions(
    group_id: UUID,
    file_id: UUID,
    data: GroupFilePermissionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        member = await GroupFileService._require_member(db, group_id, current_user.id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e

    if member.role not in (GroupRole.ADMIN, GroupRole.OWNER):
        raise HTTPException(status_code=403, detail="无权限修改群文件权限")

    try:
        permissions = data.permissions
        await GroupFileService.update_permissions(
            db,
            group_id=group_id,
            user_id=current_user.id,
            file_id=file_id,
            view_role=GroupRole(permissions.view_role.value),
            download_role=GroupRole(permissions.download_role.value),
            manage_role=GroupRole(permissions.manage_role.value),
        )
        await db.commit()
        detailed_group_file = await GroupFileService._get_group_file(db, group_id=group_id, file_id=file_id)
        return _build_group_file_info(detailed_group_file, member.role)
    except PermissionError as e:
        await db.rollback()
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e


# route-tier: authed
@router.get(
    "/groups/{group_id}/files/categories", response_model=list[GroupFileCategoryStat], summary="获取群文件分类统计"
)
async def get_group_file_categories(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        rows = await GroupFileService.category_stats(db, group_id, current_user.id)
        return [GroupFileCategoryStat(category=category, count=count) for category, count in rows]
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


# route-tier: authed
@router.patch("/groups/{group_id}/messages/{message_id}", response_model=MessageInfo, summary="编辑群消息")
async def edit_group_message(
    group_id: UUID,
    message_id: UUID,
    data: MessageEdit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """编辑群消息"""
    try:
        message = await GroupMessageService.edit_message(db, group_id, message_id, current_user.id, data)
        await db.commit()
        message_info = _build_message_info(message)
        if not _is_self_only_visibility(message.content_data, current_user.id):
            await manager.broadcast(
                {"type": "message_edit", "message": message_info.model_dump(mode="json")}, str(group_id)
            )
        return message_info
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# route-tier: authed
@router.post("/groups/{group_id}/messages/{message_id}/revoke", response_model=MessageInfo, summary="撤回群消息")
async def revoke_group_message(
    group_id: UUID, message_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
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
            await manager.broadcast({"type": "message_revoke", "message_id": str(message.id)}, str(group_id))
        return message_info
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# route-tier: authed
@router.post("/groups/{group_id}/messages/{message_id}/reactions", response_model=MessageInfo, summary="更新群消息表情")
async def update_group_message_reaction(
    group_id: UUID,
    message_id: UUID,
    data: MessageReactionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新群消息表情反应"""
    try:
        message = await GroupMessageService.update_reaction(
            db, group_id, message_id, current_user.id, data.emoji, data.action == ReactionActionEnum.ADD
        )
        await db.commit()
        if not _is_self_only_visibility(message.content_data, current_user.id):
            await manager.broadcast(
                {"type": "reaction_update", "message_id": str(message.id), "reactions": message.reactions or {}},
                str(group_id),
            )
        return _build_message_info(message)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# route-tier: authed
@router.get("/groups/{group_id}/threads/{thread_root_id}", response_model=list[MessageInfo], summary="获取群消息线程")
async def get_group_thread_messages(
    group_id: UUID,
    thread_root_id: UUID,
    limit: int = Query(default=100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取群消息线程"""
    try:
        messages = await GroupMessageService.get_thread_messages(db, group_id, current_user.id, thread_root_id, limit)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    return [_build_message_info(msg) for msg in messages]


# route-tier: authed
@router.get("/groups/{group_id}/messages/search", response_model=list[MessageInfo], summary="搜索群消息")
async def search_group_messages(
    group_id: UUID,
    keyword: str = Query(min_length=1, max_length=120),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """搜索群消息"""
    try:
        messages = await GroupMessageService.search_messages(db, group_id, current_user.id, keyword, limit)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    return [_build_message_info(msg) for msg in messages]


# ============ 私聊消息 ============


# route-tier: authed
@router.post("/messages", response_model=PrivateMessageInfo, summary="发送私信")
@limiter.limit("30/minute")
async def send_private_message(
    request: Request,
    data: PrivateMessageSend,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    发送私聊消息

    注意：如果被对方拉黑，将无法发送消息
    """
    # 检查是否被对方拉黑
    if await UserBlockService.is_blocked(db, current_user.id, data.target_user_id):
        raise HTTPException(status_code=403, detail="由于对方的隐私设置，无法发送消息")

    try:
        data.content_data = _normalize_self_visibility(data.content_data, current_user.id)
        message = await PrivateMessageService.send_message(db, current_user.id, data)
        await db.commit()

        msg_info = _build_private_message_info(message)

        is_self_only = _is_self_only_visibility(data.content_data, current_user.id)

        # 推送 WebSocket
        if not is_self_only:
            await manager.send_personal_message(msg_info.model_dump(mode="json"), str(data.target_user_id))
        await manager.send_personal_message(msg_info.model_dump(mode="json"), str(current_user.id))

        # 回传 ACK 给发送者
        if data.nonce:
            await manager.send_personal_message(
                {
                    "type": "ack",
                    "nonce": data.nonce,
                    "message_id": str(message.id),
                    "timestamp": message.created_at.isoformat(),
                },
                str(current_user.id),
            )

        return msg_info
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# route-tier: authed
@router.get("/friends/{friend_id}/messages", response_model=list[PrivateMessageInfo], summary="获取私信记录")
async def get_private_messages(
    friend_id: UUID,
    before_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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


# route-tier: authed
@router.patch("/messages/{message_id}", response_model=PrivateMessageInfo, summary="编辑私信")
async def edit_private_message(
    message_id: UUID,
    data: MessageEdit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """编辑私聊消息"""
    try:
        message = await PrivateMessageService.edit_message(db, message_id, current_user.id, data)
        await db.commit()
        msg_info = _build_private_message_info(message)
        await manager.send_personal_message(
            {"type": "message_edit", "message": msg_info.model_dump(mode="json")}, str(message.sender_id)
        )
        if not _is_self_only_visibility(message.content_data, current_user.id):
            await manager.send_personal_message(
                {"type": "message_edit", "message": msg_info.model_dump(mode="json")}, str(message.receiver_id)
            )
        return msg_info
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# route-tier: authed
@router.post("/messages/{message_id}/revoke", response_model=PrivateMessageInfo, summary="撤回私信")
async def revoke_private_message(
    message_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """撤回私聊消息"""
    try:
        existing = await db.get(PrivateMessage, message_id)
        is_self_only = False
        if existing and existing.sender_id == current_user.id:
            is_self_only = _is_self_only_visibility(existing.content_data, current_user.id)
        message = await PrivateMessageService.revoke_message(db, message_id, current_user.id)
        await db.commit()
        await manager.send_personal_message(
            {"type": "message_revoke", "message_id": str(message.id)}, str(message.sender_id)
        )
        if not is_self_only:
            await manager.send_personal_message(
                {"type": "message_revoke", "message_id": str(message.id)}, str(message.receiver_id)
            )
        return _build_private_message_info(message)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# route-tier: authed
@router.post("/messages/{message_id}/reactions", response_model=PrivateMessageInfo, summary="更新私信表情")
async def update_private_message_reaction(
    message_id: UUID,
    data: MessageReactionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新私聊消息表情反应"""
    try:
        message = await PrivateMessageService.update_reaction(
            db, message_id, current_user.id, data.emoji, data.action == ReactionActionEnum.ADD
        )
        await db.commit()
        await manager.send_personal_message(
            {"type": "reaction_update", "message_id": str(message.id), "reactions": message.reactions or {}},
            str(message.sender_id),
        )
        if not _is_self_only_visibility(message.content_data, current_user.id):
            await manager.send_personal_message(
                {"type": "reaction_update", "message_id": str(message.id), "reactions": message.reactions or {}},
                str(message.receiver_id),
            )
        return _build_private_message_info(message)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# route-tier: authed
@router.get("/friends/{friend_id}/messages/search", response_model=list[PrivateMessageInfo], summary="搜索私信")
async def search_private_messages(
    friend_id: UUID,
    keyword: str = Query(min_length=1, max_length=120),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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


# route-tier: authed
@router.put("/status", summary="更新在线状态")
async def update_status(
    data: UserStatusUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
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
async def user_websocket_endpoint(websocket: WebSocket, token: str | None = Query(None)):
    """
    用户个人 WebSocket 连接
    用于接收私信通知、系统通知等
    连接地址: ws://host/api/v1/community/ws/connect?token={jwt_token}
    """
    user_id = None
    try:
        auth_token = token if settings.WS_ALLOW_QUERY_TOKEN else None
        auth_token = auth_token or _extract_ws_token(websocket)
        if not auth_token:
            await websocket.close(code=4003)
            return

        payload = await decode_token(auth_token, expected_type="access")
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
                await websocket.receive_text()
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
        except RuntimeError:
            pass


# ============ 打卡 ============


# route-tier: authed
@router.post("/checkin", response_model=CheckinResponse, summary="群组打卡")
async def checkin(
    data: CheckinRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    在群组中打卡

    - **today_duration_minutes**: 今日学习时长（分钟）
    - **message**: 可选的打卡留言
    """
    try:
        result = await CheckinService.checkin(db, current_user.id, data)
        await db.commit()
        asyncio.create_task(_refresh_streak_signals(current_user.id))

        # Broadcast member checkin event
        await manager.broadcast(
            {
                "type": "member_checkin",
                "group_id": str(data.group_id),
                "user": UserBrief.model_validate(current_user).model_dump(mode="json"),
                "duration": data.today_duration_minutes,
                "timestamp": datetime.now(UTC).isoformat(),
            },
            str(data.group_id),
        )

        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


async def _refresh_streak_signals(user_id: UUID) -> None:
    try:
        async with AsyncSessionLocal() as session:
            processor = StreakSignalProcessor(session, cache_service.redis)
            await processor.process_checkin(user_id)
    except Exception as exc:
        logger.warning(f"Failed to refresh streak signals for {user_id}: {exc}")


# ============ 群任务 ============


# route-tier: authed
@router.post("/groups/{group_id}/tasks", response_model=GroupTaskInfo, summary="创建群任务")
async def create_group_task(
    group_id: UUID,
    data: GroupTaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建群任务（仅群主/管理员）"""
    try:
        task = await GroupTaskService.create_task(db, group_id, current_user.id, data)
        await db.commit()

        # Broadcast task created event
        await manager.broadcast(
            {
                "type": "task_created",
                "group_id": str(group_id),
                "task": {
                    "id": str(task.id),
                    "title": task.title,
                    "description": task.description,
                    "creator": UserBrief.model_validate(current_user).model_dump(mode="json"),
                },
                "timestamp": datetime.now(UTC).isoformat(),
            },
            str(group_id),
        )

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
                flame_brightness=current_user.flame_brightness,
            ),
            is_claimed_by_me=False,
            my_completion_status=None,
        )
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


# route-tier: authed
@router.get("/groups/{group_id}/tasks", response_model=list[GroupTaskInfo], summary="获取群任务列表")
async def get_group_tasks(
    group_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """获取群组的任务列表"""
    tasks = await GroupTaskService.get_group_tasks(db, group_id, current_user.id)

    result = []
    for task_dict in tasks:
        creator = task_dict.get("creator")
        creator_brief = (
            UserBrief(
                id=creator.id,
                username=creator.username,
                nickname=creator.nickname,
                avatar_url=creator.avatar_url,
                flame_level=creator.flame_level,
                flame_brightness=creator.flame_brightness,
            )
            if creator
            else None
        )

        result.append(
            GroupTaskInfo(
                id=task_dict["id"],
                created_at=task_dict["created_at"],
                updated_at=task_dict["updated_at"],
                title=task_dict["title"],
                description=task_dict["description"],
                tags=task_dict["tags"],
                estimated_minutes=task_dict["estimated_minutes"],
                difficulty=task_dict["difficulty"],
                total_claims=task_dict["total_claims"],
                total_completions=task_dict["total_completions"],
                completion_rate=task_dict["completion_rate"],
                due_date=task_dict["due_date"],
                creator=creator_brief,
                is_claimed_by_me=task_dict["is_claimed_by_me"],
                my_completion_status=task_dict["my_completion_status"],
            )
        )
    return result


# route-tier: authed
@router.post("/tasks/{task_id}/claim", summary="认领群任务")
async def claim_group_task(
    task_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """认领群任务，会在个人任务系统中创建对应任务"""
    try:
        claim = await GroupTaskService.claim_task(db, task_id, current_user.id)
        await db.commit()
        return {"success": True, "claim_id": str(claim.id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ============ 火堆状态 ============


# route-tier: authed
@router.get("/groups/{group_id}/flame", response_model=GroupFlameStatus, summary="获取群组火堆状态")
async def get_group_flame_status(
    group_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    获取群组火堆可视化数据

    返回所有成员的火苗状态，用于渲染火堆动画
    """
    import math

    from sqlalchemy import select

    from app.models.community import GroupMember

    group = await GroupService.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="没有找到这个群组")

    # 获取群组成员的火苗数据
    result = await db.execute(
        select(GroupMember, User)
        .join(User, GroupMember.user_id == User.id)
        .where(GroupMember.group_id == group_id, GroupMember.not_deleted_filter())
        .order_by(GroupMember.flame_contribution.desc())
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

        flames.append(
            FlameStatus(
                user_id=user.id,
                flame_power=power,
                flame_color=color,
                flame_size=size,
                position_x=math.cos(angle) * radius,
                position_y=math.sin(angle) * radius,
            )
        )

    bonfire_level = min(5, (group["total_flame_power"] // 1000) + 1)

    return GroupFlameStatus(
        group_id=group_id, total_power=group["total_flame_power"], flames=flames, bonfire_level=bonfire_level
    )


# ============ 资源共享 ============


# route-tier: authed
@router.post("/share", response_model=SharedResourceInfo, summary="分享资源")
async def share_resource(
    data: SharedResourceCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    分享任务、计划或认知碎片给群组或好友
    """
    try:
        # Convert enum schema to model enum
        resource_type = SharedResourceType(data.resource_type.value)

        resource = await _get_share_resource(db, resource_type, data.resource_id, current_user.id)
        brief = _build_share_brief(resource_type, resource)
        card_share = None
        if resource_type in {SharedResourceType.PLAN, SharedResourceType.TASK}:
            try:
                share_service = ShareService(db)
                shareable_card = await share_service.resolve_card_from_legacy_resource(
                    resource_type=resource_type.value,
                    resource_id=data.resource_id,
                    owner_id=current_user.id,
                )
                if shareable_card is not None:
                    card_share = await share_service.share_card(
                        card_id=shareable_card.id,
                        user_id=current_user.id,
                        scope=ShareScope.GROUP if data.target_group_id else ShareScope.USER,
                        target_id=data.target_group_id or data.target_user_id,
                        permission=_legacy_permission_to_share_permission(data.permission),
                        message=data.comment,
                        include_children=resource_type == SharedResourceType.PLAN,
                        max_depth=4 if resource_type == SharedResourceType.PLAN else 2,
                        metadata={
                            "origin": "community.share",
                            "legacy_resource_type": resource_type.value,
                            "legacy_resource_id": str(data.resource_id),
                        },
                    )
            except Exception as exc:
                logger.warning(
                    "Card share bridge failed for {} {}: {}",
                    resource_type.value,
                    data.resource_id,
                    exc,
                )

        shared = await collaboration_service.share_resource(
            db,
            current_user.id,
            resource_type,
            data.resource_id,
            target_group_id=data.target_group_id,
            target_user_id=data.target_user_id,
            permission=data.permission,
            comment=data.comment,
        )
        if card_share is not None:
            shared.card_share_record_id = card_share.id
            db.add(shared)

        owner_payload = _share_owner_payload(current_user)
        visibility = "group" if data.target_group_id else "direct"
        adoption_action = _compact_dict(
            {
                "id": "adopt_shared_resource",
                "type": "adopt_resource",
                "label": "采纳到我的空间",
                "route": f"/community/shared-resources/{shared.id}/adopt",
                "payload": {
                    "shared_resource_id": str(shared.id),
                    "resource_type": resource_type.value,
                    "resource_id": str(data.resource_id),
                },
            }
        )
        source_receipt = _compact_dict(
            {
                "channel": "community_share",
                "shared_resource_id": str(shared.id),
                "shared_by_user_id": str(current_user.id),
                "card_share_record_id": str(card_share.id) if card_share else None,
            }
        )

        share_payload = _compact_dict(
            {
                "resource_type": resource_type.value,
                "resource_id": str(data.resource_id),
                "shared_resource_id": str(shared.id),
                "card_share_record_id": str(card_share.id) if card_share else None,
                "resource_title": brief["title"],
                "resource_summary": brief["summary"],
                "resource_meta": brief["meta"],
                "permission": shared.permission,
                "comment": data.comment,
                "owner": owner_payload,
                "visibility": visibility,
                "preview": {"title": brief["title"], "summary": brief["summary"], "meta": brief["meta"]},
                "source_receipt": source_receipt,
                "adoption_action": adoption_action,
                "availability": "available",
            }
        )

        message_type = _share_message_type(resource_type)
        message_content = data.comment

        message_info = None
        if data.target_group_id:
            message = await GroupMessageService.send_message(
                db,
                data.target_group_id,
                current_user.id,
                MessageSend(message_type=message_type, content=message_content, content_data=share_payload),
            )
            message_info = _build_message_info(message)
            await CommunitySignalBridge(db).handle_resource_shared(
                user_id=current_user.id,
                resource_type=resource_type.value,
                resource_id=data.resource_id,
                target_group_id=data.target_group_id,
                share_id=shared.id,
            )
        elif data.target_user_id:
            message = await PrivateMessageService.send_message(
                db,
                current_user.id,
                PrivateMessageSend(
                    target_user_id=data.target_user_id,
                    message_type=message_type,
                    content=message_content,
                    content_data=share_payload,
                ),
            )
            message_info = _build_private_message_info(message)

        await db.commit()

        if message_info:
            if data.target_group_id:
                await manager.broadcast(message_info.model_dump(mode="json"), str(data.target_group_id))
            elif data.target_user_id:
                await manager.send_personal_message(message_info.model_dump(mode="json"), str(data.target_user_id))
                await manager.send_personal_message(message_info.model_dump(mode="json"), str(current_user.id))

        # Construct response
        return SharedResourceInfo(
            id=shared.id,
            created_at=shared.created_at,
            updated_at=shared.updated_at,
            resource_type=data.resource_type.value,
            plan_id=shared.plan_id,
            task_id=shared.task_id,
            knowledge_node_id=shared.knowledge_node_id,
            seed_library_id=shared.seed_library_id,
            seed_item_id=shared.seed_item_id,
            cognitive_fragment_id=shared.cognitive_fragment_id,
            curiosity_capsule_id=shared.curiosity_capsule_id,
            behavior_pattern_id=shared.behavior_pattern_id,
            card_share_record_id=shared.card_share_record_id,
            permission=shared.permission,
            comment=shared.comment,
            view_count=shared.view_count,
            save_count=shared.save_count,
            quality_score=shared.quality_score or 0.0,
            quality_hidden=shared.quality_hidden or False,
            adoption_count=shared.adoption_count or 0,
            avg_rating=_shared_resource_avg_rating(shared),
            sharer=UserBrief.model_validate(current_user),
            resource_title=brief["title"],
            resource_summary=brief["summary"],
            entity_card=build_shared_resource_entity_card(
                shared_resource_id=str(shared.id),
                resource_type=data.resource_type.value,
                resource_id=str(data.resource_id),
                title=brief["title"],
                summary=brief["summary"],
                permission=shared.permission,
                comment=shared.comment,
                meta=brief["meta"],
                target_group_id=str(data.target_group_id) if data.target_group_id else None,
                target_user_id=str(data.target_user_id) if data.target_user_id else None,
                owner=owner_payload,
                visibility=visibility,
                availability="available",
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# route-tier: authed
@router.get("/groups/{group_id}/resources", response_model=list[SharedResourceInfo], summary="获取群组共享资源")
async def get_group_resources(
    group_id: UUID,
    resource_type: SharedResourceTypeEnum | None = None,
    sort: str = Query(default="recent", description="排序方式: recent | quality"),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    获取分享到群组的资源列表
    """
    try:
        await GroupService._require_active_member(db, group_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="不是群组成员") from exc

    rtype = SharedResourceType(resource_type.value) if resource_type else None

    resources = await collaboration_service.get_group_resources(
        db, group_id, rtype, limit=limit * 2 if sort == "quality" else limit, viewer_id=current_user.id
    )

    if sort == "quality":
        resources = sorted(resources, key=lambda r: r.quality_score or 0.0, reverse=True)

    result = []
    for res in resources:
        if not _shared_resource_payload_is_active(res):
            continue
        if res.quality_hidden and sort != "quality":
            continue

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
        elif res.knowledge_node_id and res.knowledge_node:
            r_type_str = "knowledge_node"
            brief = _build_share_brief(SharedResourceType.KNOWLEDGE_NODE, res.knowledge_node)
            resource_title = brief["title"]
            resource_summary = brief["summary"]
        elif res.seed_library_id and res.seed_library:
            r_type_str = "seed_library"
            brief = _build_share_brief(SharedResourceType.SEED_LIBRARY, res.seed_library)
            resource_title = brief["title"]
            resource_summary = brief["summary"]
        elif res.seed_item_id and res.seed_item:
            r_type_str = "seed_item"
            brief = _build_share_brief(SharedResourceType.SEED_ITEM, res.seed_item)
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

        result.append(
            SharedResourceInfo(
                id=res.id,
                created_at=res.created_at,
                updated_at=res.updated_at,
                resource_type=r_type_str,
                plan_id=res.plan_id,
                task_id=res.task_id,
                knowledge_node_id=res.knowledge_node_id,
                seed_library_id=res.seed_library_id,
                seed_item_id=res.seed_item_id,
                cognitive_fragment_id=res.cognitive_fragment_id,
                curiosity_capsule_id=res.curiosity_capsule_id,
                behavior_pattern_id=res.behavior_pattern_id,
                card_share_record_id=res.card_share_record_id,
                permission=res.permission,
                comment=res.comment,
                view_count=res.view_count,
                save_count=res.save_count,
                sharer=UserBrief.model_validate(res.sharer) if res.sharer else None,
                resource_title=resource_title,
                resource_summary=resource_summary,
                quality_score=res.quality_score or 0.0,
                quality_hidden=res.quality_hidden or False,
                adoption_count=res.adoption_count or 0,
                avg_rating=_shared_resource_avg_rating(res),
                entity_card=build_shared_resource_entity_card(
                    shared_resource_id=str(res.id),
                    resource_type=r_type_str,
                    resource_id=(
                        str(
                            res.plan_id
                            or res.task_id
                            or res.knowledge_node_id
                            or res.seed_library_id
                            or res.seed_item_id
                            or res.cognitive_fragment_id
                            or res.curiosity_capsule_id
                            or res.behavior_pattern_id
                        )
                        if (
                            res.plan_id
                            or res.task_id
                            or res.knowledge_node_id
                            or res.seed_library_id
                            or res.seed_item_id
                            or res.cognitive_fragment_id
                            or res.curiosity_capsule_id
                            or res.behavior_pattern_id
                        )
                        else None
                    ),
                    title=resource_title or "共享资源",
                    summary=resource_summary,
                    permission=res.permission,
                    comment=res.comment,
                    owner=_share_owner_payload(res.sharer),
                    visibility="group",
                    availability="available",
                ),
            )
        )
    return result


def _build_adopted_entity_card(
    *,
    resource_type: str,
    resource_id: UUID,
    title: str,
    summary: str | None = None,
) -> dict:
    resource_id_str = str(resource_id)
    if resource_type == "knowledge_node":
        return build_knowledge_entity_card(
            {
                "id": resource_id_str,
                "name": title,
                "description": summary,
            },
            tool_name="adopt_shared_resource",
            source_channel="community_share",
        )

    return build_entity_card(
        entity_type=resource_type,
        entity_id=resource_id_str,
        title=title,
        summary=summary,
        status="saved",
        execution_state="active",
        source={"channel": "community_share", "tool_name": "adopt_shared_resource"},
        primary_action=build_entity_action(
            action_id=f"open_{resource_type}",
            action_type="open_detail",
            label="查看详情",
        ),
        secondary_actions=[
            build_entity_action(
                action_id=f"share_{resource_type}",
                action_type="share_resource",
                label="再次分享",
                payload={"resource_type": resource_type, "resource_id": resource_id_str},
            )
        ],
    )


async def _clone_seed_library_with_items(
    db: AsyncSession,
    *,
    original: SeedLibrary,
    current_user: User,
) -> SeedLibrary:
    cloned_library = SeedLibrary(
        name=original.name,
        description=original.description,
        category=original.category,
        visibility="private",
        owner_id=current_user.id,
        language=original.language,
        tags=deepcopy(original.tags) if original.tags else [],
        extra_metadata=_compact_dict(
            {
                **(deepcopy(original.extra_metadata) if isinstance(original.extra_metadata, dict) else {}),
                "adopted_from_library_id": str(original.id),
                "adopted_from_user_id": str(original.owner_id) if original.owner_id else None,
            }
        ),
        is_official=False,
        is_featured=False,
        usage_count=0,
        quality_score=original.quality_score,
    )
    db.add(cloned_library)
    await db.flush()

    items_result = await db.execute(
        select(SeedItem)
        .where(
            SeedItem.library_id == original.id,
            SeedItem.not_deleted_filter(),
        )
        .order_by(SeedItem.order_index.asc(), SeedItem.created_at.asc())
    )
    for item in items_result.scalars().all():
        db.add(
            SeedItem(
                library_id=cloned_library.id,
                item_type=item.item_type,
                title=item.title,
                content=item.content,
                content_data=deepcopy(item.content_data) if item.content_data else None,
                subject=item.subject,
                difficulty_level=item.difficulty_level,
                tags=deepcopy(item.tags) if item.tags else [],
                order_index=item.order_index,
                is_active=item.is_active,
            )
        )

    await db.flush()
    return cloned_library


# route-tier: authed
@router.post(
    "/shared-resources/{shared_resource_id}/adopt",
    summary="采纳共享资源为个人任务/计划",
)
async def adopt_shared_resource(
    shared_resource_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    shared_result = await db.execute(
        select(SharedResource)
        .where(
            SharedResource.id == shared_resource_id,
            SharedResource.not_deleted_filter(),
        )
        .with_for_update()
    )
    shared = shared_result.scalar_one_or_none()
    if not shared:
        raise HTTPException(status_code=404, detail="共享资源不存在")

    if shared.target_user_id is not None and str(shared.target_user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="无权采纳该共享资源")

    if shared.group_id is not None:
        membership_result = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == shared.group_id,
                GroupMember.user_id == current_user.id,
                GroupMember.not_deleted_filter(),
            )
        )
        if not membership_result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="无权采纳该共享资源")

    if shared.target_user_id is None and shared.group_id is None and str(shared.shared_by) != str(current_user.id):
        raise HTTPException(status_code=403, detail="无权采纳该共享资源")

    if str(shared.shared_by) != str(current_user.id):
        if await UserBlockService.has_block_relationship(db, current_user.id, shared.shared_by):
            raise HTTPException(status_code=403, detail="无权采纳该共享资源")

    if shared.card_share_record_id:
        try:
            share_service = ShareService(db)
            import_mode = ImportMode.FORK if (shared.permission or "").strip().lower() == "fork" else ImportMode.ADOPT
            result = await share_service.adopt_shared_card(
                share_record_id=shared.card_share_record_id,
                user_id=current_user.id,
                import_mode=import_mode,
            )
            shared.save_count = (shared.save_count or 0) + 1
            db.add(shared)
            await db.commit()

            if result.imported_root_plan_id:
                imported_plan = await db.get(Plan, result.imported_root_plan_id)
                entity_card = build_plan_entity_card(
                    {
                        "id": str(imported_plan.id),
                        "name": imported_plan.name,
                        "description": imported_plan.description,
                        "type": imported_plan.type.value if imported_plan.type else None,
                        "subject": imported_plan.subject,
                        "source": imported_plan.source,
                        "is_active": imported_plan.is_active,
                    },
                    tool_name="adopt_shared_resource",
                    source_channel="community_share",
                )
                return {
                    "success": True,
                    "resource_type": "plan",
                    "new_resource_id": str(imported_plan.id),
                    "card_root_id": str(result.root_card.id),
                    "entity_card": entity_card,
                }

            if result.imported_root_task_id:
                imported_task = await db.get(Task, result.imported_root_task_id)
                entity_card = build_task_entity_card(
                    {
                        "id": str(imported_task.id),
                        "title": imported_task.title,
                        "type": imported_task.type.value if imported_task.type else None,
                        "status": imported_task.status.value if imported_task.status else "pending",
                        "estimated_minutes": imported_task.estimated_minutes,
                    },
                    tool_name="adopt_shared_resource",
                    source_channel="community_share",
                )
                return {
                    "success": True,
                    "resource_type": "task",
                    "new_resource_id": str(imported_task.id),
                    "card_root_id": str(result.root_card.id),
                    "entity_card": entity_card,
                }

            card_title = (
                result.root_card.metadata_.get("name")
                or result.root_card.metadata_.get("title")
                or result.root_card.card_type.value.title()
            )
            card_summary = result.root_card.metadata_.get("description") or result.root_card.metadata_.get("objective")
            entity_card = _build_adopted_entity_card(
                resource_type=result.root_card.card_type.value.lower(),
                resource_id=result.root_card.id,
                title=card_title,
                summary=card_summary,
            )
            return {
                "success": True,
                "resource_type": result.root_card.card_type.value.lower(),
                "new_resource_id": str(result.root_card.id),
                "card_root_id": str(result.root_card.id),
                "entity_card": entity_card,
            }
        except ValueError as exc:
            await db.rollback()
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    new_id: UUID | None = None
    resource_type = ""
    resource_title = ""
    resource_summary = None
    adoption_next_actions: list[dict] = []

    if shared.task_id:
        original = await db.get(Task, shared.task_id)
        if not original:
            raise HTTPException(status_code=404, detail="原始任务不存在")
        task_in = TaskCreate(
            title=original.title,
            type=original.type,
            tags=original.tags or [],
            estimated_minutes=original.estimated_minutes,
            difficulty=original.difficulty,
            energy_cost=original.energy_cost,
            guide_content=original.guide_content,
            priority=original.priority,
        )
        new_task = await TaskService.create(db, task_in, current_user.id)
        new_id = new_task.id
        resource_type = "task"
        resource_title = new_task.title
        resource_summary = new_task.guide_content
    elif shared.plan_id:
        original = await db.get(Plan, shared.plan_id)
        if not original:
            raise HTTPException(status_code=404, detail="原始计划不存在")
        plan_in = PlanCreate(
            name=original.name,
            type=original.type,
            description=original.description,
            subject=original.subject,
            target_date=original.target_date,
            daily_available_minutes=original.daily_available_minutes,
            total_estimated_hours=original.total_estimated_hours,
            priority=original.priority,
        )
        new_plan = await PlanService.create(db, plan_in, current_user.id)
        new_plan.source = "adopted"
        new_plan.source_metadata = {
            "original_id": str(original.id),
            "shared_by": str(shared.shared_by),
            "shared_resource_id": str(shared_resource_id),
        }
        db.add(new_plan)
        new_id = new_plan.id
        resource_type = "plan"
        resource_title = new_plan.name
        resource_summary = new_plan.description
    elif shared.knowledge_node_id:
        original = await db.get(KnowledgeNode, shared.knowledge_node_id)
        if not original:
            raise HTTPException(status_code=404, detail="原始知识节点不存在")
        new_node = KnowledgeNode(
            subject_id=original.subject_id,
            parent_id=None,
            name=original.name,
            name_en=original.name_en,
            description=original.description,
            keywords=deepcopy(original.keywords) if original.keywords else [],
            importance_level=original.importance_level,
            is_seed=False,
            source_type="user_created",
            source_task_id=None,
            source_file_id=None,
            chunk_refs=None,
            status=original.status or "published",
            sector_weights=deepcopy(original.sector_weights) if original.sector_weights else {},
            dominant_sector_code=original.dominant_sector_code or "VOID",
            sector_classification_status=original.sector_classification_status or "pending",
            sector_classification_model="community_adopt",
            sector_classified_at=_utcnow(),
            global_spark_count=0,
        )
        db.add(new_node)
        await db.flush()
        db.add(
            UserNodeStatus(
                user_id=current_user.id,
                node_id=new_node.id,
                mastery_score=0,
                bkt_mastery_prob=0.0,
                total_minutes=0,
                total_study_minutes=0,
                study_count=0,
                is_unlocked=True,
                is_collapsed=False,
                is_favorite=False,
            )
        )
        new_id = new_node.id
        resource_type = "knowledge_node"
        resource_title = new_node.name
        resource_summary = new_node.description
    elif shared.cognitive_fragment_id:
        original = await db.get(CognitiveFragment, shared.cognitive_fragment_id)
        if not original:
            raise HTTPException(status_code=404, detail="原始认知碎片不存在")
        new_fragment = CognitiveFragment(
            user_id=current_user.id,
            task_id=None,
            analysis_status=original.analysis_status,
            error_message=None,
            source_type=original.source_type,
            resource_type=original.resource_type,
            resource_url=original.resource_url,
            content=original.content,
            sentiment=original.sentiment,
            persona_version=original.persona_version,
            source_event_id=None,
            sensitive_tags_encrypted=original.sensitive_tags_encrypted,
            sensitive_tags_version=original.sensitive_tags_version,
            sensitive_tags_key_id=original.sensitive_tags_key_id,
            tags=deepcopy(original.tags) if original.tags else [],
            error_tags=deepcopy(original.error_tags) if original.error_tags else [],
            context_tags=deepcopy(original.context_tags) if original.context_tags else {},
            severity=original.severity,
        )
        db.add(new_fragment)
        await db.flush()
        new_id = new_fragment.id
        resource_type = "cognitive_fragment"
        resource_title = new_fragment.content[:40] or "认知碎片"
        resource_summary = new_fragment.content
    elif shared.curiosity_capsule_id:
        original = await db.get(CuriosityCapsule, shared.curiosity_capsule_id)
        if not original:
            raise HTTPException(status_code=404, detail="原始好奇心胶囊不存在")
        new_capsule = CuriosityCapsule(
            user_id=current_user.id,
            title=original.title,
            content=original.content,
            related_subject=original.related_subject,
            related_task_id=None,
            is_read=False,
            depth_level=original.depth_level,
            generation_method=original.generation_method,
            source_context=deepcopy(original.source_context) if original.source_context else None,
            personalization_context=(
                deepcopy(original.personalization_context) if original.personalization_context else None
            ),
            quality_score=original.quality_score,
            feedback_count=0,
            share_count=0,
        )
        db.add(new_capsule)
        await db.flush()
        new_id = new_capsule.id
        resource_type = "curiosity_capsule"
        resource_title = new_capsule.title
        resource_summary = new_capsule.content
    elif shared.seed_library_id:
        original = await db.get(SeedLibrary, shared.seed_library_id)
        if not original:
            raise HTTPException(status_code=404, detail="原始种子库不存在")
        new_library = await _clone_seed_library_with_items(db, original=original, current_user=current_user)
        new_id = new_library.id
        resource_type = "seed_library"
        resource_title = new_library.name
        resource_summary = new_library.description
        adoption_next_actions = await SeedLibraryService().get_library_adoption_actions(db, new_library)
    elif shared.seed_item_id:
        original = await db.get(SeedItem, shared.seed_item_id)
        if not original:
            raise HTTPException(status_code=404, detail="原始种子内容不存在")
        library = SeedLibrary(
            name=original.title or "采纳内容",
            description="从社群共享中采纳的单条种子内容",
            category="custom",
            visibility="private",
            owner_id=current_user.id,
            language="zh",
            tags=deepcopy(original.tags) if original.tags else [],
            extra_metadata={"adopted_from_item_id": str(original.id)},
            is_official=False,
            is_featured=False,
            usage_count=0,
        )
        db.add(library)
        await db.flush()
        new_item = SeedItem(
            library_id=library.id,
            item_type=original.item_type,
            title=original.title,
            content=original.content,
            content_data=deepcopy(original.content_data) if original.content_data else None,
            subject=original.subject,
            difficulty_level=original.difficulty_level,
            tags=deepcopy(original.tags) if original.tags else [],
            order_index=0,
            is_active=original.is_active,
        )
        db.add(new_item)
        await db.flush()
        new_id = new_item.id
        resource_type = "seed_item"
        resource_title = new_item.title or "种子内容"
        resource_summary = new_item.content
        adoption_next_actions = SeedLibraryService().build_item_adoption_actions(new_item)
    elif shared.behavior_pattern_id:
        original = await db.get(BehaviorPattern, shared.behavior_pattern_id)
        if not original:
            raise HTTPException(status_code=404, detail="原始认知棱镜不存在")
        new_pattern = BehaviorPattern(
            user_id=current_user.id,
            pattern_name=original.pattern_name,
            pattern_type=original.pattern_type,
            description=original.description,
            solution_text=original.solution_text,
            evidence_ids=[],
            confidence_score=original.confidence_score,
            frequency=original.frequency,
            is_archived=False,
            last_observed_at=None,
            last_decay_at=None,
        )
        db.add(new_pattern)
        await db.flush()
        new_id = new_pattern.id
        resource_type = "cognitive_prism_pattern"
        resource_title = new_pattern.pattern_name
        resource_summary = new_pattern.description
    else:
        raise HTTPException(status_code=400, detail="不支持采纳此类型资源")

    shared.save_count = (shared.save_count or 0) + 1
    db.add(shared)
    await db.commit()

    if resource_type == "task":
        entity_card = build_task_entity_card(
            {
                "id": str(new_id),
                "title": new_task.title,
                "type": new_task.type.value if new_task.type else None,
                "status": new_task.status.value if new_task.status else "pending",
                "estimated_minutes": new_task.estimated_minutes,
            },
            tool_name="adopt_shared_resource",
            source_channel="community_share",
        )
    elif resource_type == "plan":
        entity_card = build_plan_entity_card(
            {
                "id": str(new_id),
                "name": new_plan.name,
                "description": new_plan.description,
                "type": new_plan.type.value if new_plan.type else None,
                "subject": new_plan.subject,
                "source": new_plan.source,
                "is_active": True,
            },
            tool_name="adopt_shared_resource",
            source_channel="community_share",
        )
    else:
        entity_card = _build_adopted_entity_card(
            resource_type=resource_type,
            resource_id=new_id,
            title=resource_title or "已采纳资源",
            summary=resource_summary,
        )

    return {
        "success": True,
        "resource_type": resource_type,
        "new_resource_id": str(new_id),
        "entity_card": entity_card,
        "adoption_next_actions": adoption_next_actions,
    }


# ============ 端到端加密 ============


# route-tier: authed
@router.post("/encryption/keys", response_model=EncryptionKeyInfo, summary="注册加密公钥")
async def register_encryption_key(
    data: EncryptionKeyCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
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
        expires_at=key.expires_at,
    )


# route-tier: authed
@router.get("/encryption/keys/{user_id}", response_model=list[EncryptionKeyInfo], summary="获取用户公钥")
async def get_user_encryption_keys(
    user_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
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
            expires_at=key.expires_at,
        )
        for key in keys
    ]


# route-tier: authed
@router.delete("/encryption/keys/{key_id}", summary="撤销加密密钥")
async def revoke_encryption_key(
    key_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """撤销指定的加密密钥"""
    success = await EncryptionService.revoke_key(db, current_user.id, key_id)
    if not success:
        raise HTTPException(status_code=404, detail="没有找到这个密钥或无权操作")
    await db.commit()
    return {"success": True}


# ============ 群管理与风控 ============


# route-tier: authed
@router.put("/groups/{group_id}/announcement", summary="更新群公告")
async def update_group_announcement(
    group_id: UUID,
    data: GroupAnnouncementUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新群公告（仅群主/管理员）"""
    try:
        group = await ModerationService.update_announcement(db, group_id, current_user.id, data)
        await db.commit()

        # 广播公告更新
        await manager.broadcast(
            {
                "type": "announcement_update",
                "group_id": str(group_id),
                "announcement": group.announcement,
                "updated_at": group.announcement_updated_at.isoformat() if group.announcement_updated_at else None,
            },
            str(group_id),
        )

        return {"success": True, "announcement": group.announcement}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


# route-tier: authed
@router.put("/groups/{group_id}/moderation", summary="更新群管理设置")
async def update_group_moderation_settings(
    group_id: UUID,
    data: GroupModerationSettings,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新群管理设置（仅群主/管理员）"""
    try:
        group = await ModerationService.update_moderation_settings(db, group_id, current_user.id, data)
        await db.commit()

        # Broadcast settings updated event
        await manager.broadcast(
            {
                "type": "group_settings_updated",
                "group_id": str(group_id),
                "settings": data.model_dump(mode="json"),
                "timestamp": datetime.now(UTC).isoformat(),
            },
            str(group_id),
        )

        return {
            "success": True,
            "mute_all": group.mute_all,
            "slow_mode_seconds": group.slow_mode_seconds,
            "keyword_filters_count": len(group.keyword_filters or []),
        }
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


# route-tier: authed
@router.post("/groups/{group_id}/members/{user_id}/mute", summary="禁言成员")
async def mute_group_member(
    group_id: UUID,
    user_id: UUID,
    data: MemberMuteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """禁言群成员（仅群主/管理员）"""
    try:
        # 覆盖 data 中的 user_id
        data.user_id = user_id
        member = await ModerationService.mute_member(db, group_id, current_user.id, data)
        await db.commit()

        # 通知被禁言用户
        await manager.send_personal_message(
            {
                "type": "muted",
                "group_id": str(group_id),
                "mute_until": member.mute_until.isoformat() if member.mute_until else None,
                "reason": data.reason,
            },
            str(user_id),
        )

        return {"success": True, "mute_until": member.mute_until}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


# route-tier: authed
@router.delete("/groups/{group_id}/members/{user_id}/mute", summary="解除禁言")
async def unmute_group_member(
    group_id: UUID, user_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """解除成员禁言（仅群主/管理员）"""
    try:
        await ModerationService.unmute_member(db, group_id, current_user.id, user_id)
        await db.commit()

        # 通知用户
        await manager.send_personal_message({"type": "unmuted", "group_id": str(group_id)}, str(user_id))

        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


# route-tier: authed
@router.post("/groups/{group_id}/members/{user_id}/warn", summary="警告成员")
async def warn_group_member(
    group_id: UUID,
    user_id: UUID,
    data: MemberWarnRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """警告群成员（仅群主/管理员）"""
    try:
        data.user_id = user_id
        member = await ModerationService.warn_member(db, group_id, current_user.id, data)
        await db.commit()

        # 通知被警告用户
        await manager.send_personal_message(
            {"type": "warned", "group_id": str(group_id), "reason": data.reason, "warn_count": member.warn_count},
            str(user_id),
        )

        return {"success": True, "warn_count": member.warn_count}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


# ============ 消息举报 ============


# route-tier: authed
@router.post("/reports", response_model=MessageReportInfo, summary="举报消息")
@limiter.limit("10/minute")
async def report_message(
    request: Request,
    data: MessageReportCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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
            action_taken=None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# route-tier: authed
@router.get("/groups/{group_id}/reports", response_model=list[MessageReportInfo], summary="获取群组待处理举报")
async def get_group_pending_reports(
    group_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取群组中待处理的举报（仅群主/管理员）"""
    # 验证管理员权限
    result = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == current_user.id,
            GroupMember.role.in_(["owner", "admin"]),
            GroupMember.not_deleted_filter(),
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="您没有权限访问")

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
            action_taken=r.action_taken,
        )
        for r in reports
    ]


# route-tier: authed
@router.put("/reports/{report_id}", response_model=MessageReportInfo, summary="审核举报")
async def review_message_report(
    report_id: UUID,
    data: MessageReportReview,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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
            action_taken=report.action_taken,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ============ 消息收藏 ============


# route-tier: authed
@router.post("/favorites", response_model=MessageFavoriteInfo, summary="收藏消息")
async def add_message_favorite(
    data: MessageFavoriteCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """收藏消息"""
    try:
        favorite = await FavoriteService.add_favorite(db, current_user.id, data)
        await db.commit()
        favorite = await FavoriteService.get_favorite(db, current_user.id, favorite.id)
        if favorite is None:
            raise HTTPException(status_code=404, detail="收藏不存在")

        # 获取消息预览
        preview = None
        msg = favorite.group_message
        private_msg = favorite.private_message
        if msg and msg.content:
            preview = msg.content[:100]
        elif private_msg and private_msg.content:
            preview = private_msg.content[:100]

        return MessageFavoriteInfo(
            id=favorite.id,
            created_at=favorite.created_at,
            updated_at=favorite.updated_at,
            user_id=favorite.user_id,
            group_message_id=favorite.group_message_id,
            private_message_id=favorite.private_message_id,
            note=favorite.note,
            tags=favorite.tags,
            message_preview=preview,
            group_message=_build_message_info(msg) if msg else None,
            private_message=_build_private_message_info(private_msg) if private_msg else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# route-tier: authed
@router.get("/favorites", response_model=list[MessageFavoriteInfo], summary="获取收藏列表")
async def get_message_favorites(
    tags: list[str] | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取我的消息收藏列表"""
    favorites = await FavoriteService.get_favorites(db, current_user.id, tags, limit, offset)

    result = []
    for fav in favorites:
        if fav.group_message and not _is_visible_to(
            getattr(fav.group_message, "content_data", None),
            current_user.id,
        ):
            continue
        preview = None
        if fav.group_message and fav.group_message.content:
            preview = fav.group_message.content[:100]
        elif fav.private_message and fav.private_message.content:
            preview = fav.private_message.content[:100]

        result.append(
            MessageFavoriteInfo(
                id=fav.id,
                created_at=fav.created_at,
                updated_at=fav.updated_at,
                user_id=fav.user_id,
                group_message_id=fav.group_message_id,
                private_message_id=fav.private_message_id,
                note=fav.note,
                tags=fav.tags,
                message_preview=preview,
                group_message=_build_message_info(fav.group_message) if fav.group_message else None,
                private_message=_build_private_message_info(fav.private_message) if fav.private_message else None,
            )
        )
    return result


# route-tier: authed
@router.delete("/favorites/{favorite_id}", summary="取消收藏")
async def remove_message_favorite(
    favorite_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """取消消息收藏"""
    success = await FavoriteService.remove_favorite(db, current_user.id, favorite_id)
    if not success:
        raise HTTPException(status_code=404, detail="收藏不存在")
    await db.commit()
    return {"success": True}


# ============ 消息转发 ============


# route-tier: authed
@router.post("/forward", summary="转发消息")
async def forward_message(
    data: MessageForwardRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """转发消息到群组或用户"""
    try:
        forwarded = await ForwardService.forward_message(db, current_user.id, data)
        await db.commit()

        # 构建消息信息并广播
        if data.target_group_id:
            msg_info = _build_message_info(forwarded)
            await manager.broadcast(msg_info.model_dump(mode="json"), str(data.target_group_id))
        elif data.target_user_id:
            msg_info = _build_private_message_info(forwarded)
            await manager.send_personal_message(msg_info.model_dump(mode="json"), str(data.target_user_id))
            await manager.send_personal_message(msg_info.model_dump(mode="json"), str(current_user.id))

        return {"success": True, "message_id": str(forwarded.id)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ============ 跨群广播 ============


# route-tier: authed
@router.post("/broadcast", response_model=BroadcastMessageInfo, summary="跨群广播")
async def create_broadcast_message(
    data: BroadcastMessageCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """发送跨群广播消息（需要在所有目标群组中是管理员）"""
    try:
        broadcast = await BroadcastService.create_broadcast(db, current_user.id, data)
        await db.commit()

        # 广播到所有目标群组
        for group_id in data.target_group_ids:
            await manager.broadcast(
                {
                    "type": "broadcast",
                    "broadcast_id": str(broadcast.id),
                    "sender_id": str(current_user.id),
                    "content": broadcast.content,
                    "content_data": broadcast.content_data,
                },
                str(group_id),
            )

        return BroadcastMessageInfo(
            id=broadcast.id,
            created_at=broadcast.created_at,
            updated_at=broadcast.updated_at,
            sender=UserBrief.model_validate(current_user),
            content=broadcast.content,
            content_data=broadcast.content_data,
            target_group_ids=data.target_group_ids,
            delivered_count=broadcast.delivered_count,
        )
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


# ============ 高级搜索 ============


# route-tier: authed
@router.post(
    "/groups/{group_id}/messages/search/advanced", response_model=MessageSearchResult, summary="高级搜索群消息"
)
async def advanced_search_group_messages(
    group_id: UUID,
    data: MessageSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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

        visible_messages = [
            msg for msg in result["messages"] if _is_visible_to(getattr(msg, "content_data", None), current_user.id)
        ]
        messages = [_build_message_info(msg) for msg in visible_messages]

        return MessageSearchResult(
            messages=messages,
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
            has_more=result["has_more"],
        )
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


# route-tier: authed
@router.get("/groups/{group_id}/topics", summary="获取群组话题列表")
async def get_group_topics(
    group_id: UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """获取群组中使用的话题列表及消息数量"""
    # 验证成员身份
    result = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id, GroupMember.user_id == current_user.id, GroupMember.not_deleted_filter()
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="不是群组成员")

    topics = await MessageSearchService.get_topics(db, group_id)
    return {"topics": topics}


# ============ 离线队列 ============


# route-tier: authed
@router.get("/offline/pending", response_model=list[OfflineMessageInfo], summary="获取待发送的离线消息")
async def get_pending_offline_messages(
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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
            error_message=msg.error_message,
        )
        for msg in messages
    ]


# route-tier: authed
@router.get("/offline/failed", response_model=list[OfflineMessageInfo], summary="获取发送失败的离线消息")
async def get_failed_offline_messages(
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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
            error_message=msg.error_message,
        )
        for msg in messages
    ]


# route-tier: authed
@router.post("/offline/retry", summary="批量重试失败消息")
async def retry_offline_messages(
    data: OfflineMessageRetryRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """批量重试失败的离线消息"""
    messages = await OfflineQueueService.retry_messages(db, current_user.id, data)
    await db.commit()
    return {"success": True, "retried_count": len(messages), "message_ids": [str(m.id) for m in messages]}


# route-tier: authed
@router.get("/recommended-resources", summary="Get recommended shared resources from user's groups")
async def get_recommended_resources(
    limit: int = Query(default=5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Recommend high-quality community resources the user hasn't adopted yet."""
    from app.models.community import GroupMembership

    user_groups = await db.execute(
        select(GroupMembership.group_id).where(
            GroupMembership.user_id == current_user.id,
            GroupMembership.deleted_at.is_(None),
        )
    )
    group_ids = [row[0] for row in user_groups]
    if not group_ids:
        return {"recommendations": []}

    high_quality = await db.execute(
        select(GroupFile)
        .where(
            GroupFile.group_id.in_(group_ids),
            GroupFile.deleted_at.is_(None),
            GroupFile.trust_level.in_(["verified", "high"]),
        )
        .order_by(GroupFile.created_at.desc())
        .limit(limit)
    )

    recommendations = []
    for gf in high_quality.scalars():
        file_record = await db.get(StoredFile, gf.file_id)
        if not file_record or file_record.is_deleted:
            continue
        recommendations.append(
            {
                "file_id": str(gf.file_id),
                "filename": file_record.file_name,
                "group_id": str(gf.group_id),
                "shared_by": str(gf.shared_by_id),
                "trust_level": str(gf.trust_level),
                "recommendation_reason": "High quality community resource from your study group",
            }
        )

    return {"recommendations": recommendations, "count": len(recommendations)}


# ============ FV-22: Resource Quality Ranking ============


# route-tier: authed
@router.get("/resources", summary="Get community resources ranked by quality")
async def get_community_resources_ranked(
    sort: str = Query(default="quality", description="排序方式: quality | recent"),
    resource_type: SharedResourceTypeEnum | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve community-shared resources ranked by quality score.
    Low-quality resources (score < 0.3) are hidden by default unless sort=quality.
    """
    from app.models.community import GroupMembership
    from app.services.community_service import CommunityResourceScorer

    user_groups = await db.execute(
        select(GroupMembership.group_id).where(
            GroupMembership.user_id == current_user.id,
            GroupMembership.deleted_at.is_(None),
        )
    )
    group_ids = [row[0] for row in user_groups]
    if not group_ids:
        return {"resources": [], "total": 0, "offset": offset, "limit": limit}

    stmt = select(SharedResource).where(
        SharedResource.group_id.in_(group_ids),
        SharedResource.deleted_at.is_(None),
    )

    # Auto-hide low quality unless explicitly sorting by quality
    if sort != "quality":
        stmt = stmt.where(
            or_(
                SharedResource.quality_hidden.is_(False),
                SharedResource.quality_hidden.is_(None),
            )
        )

    if resource_type:
        rtype = SharedResourceType(resource_type.value)
        if rtype == SharedResourceType.PLAN:
            stmt = stmt.where(SharedResource.plan_id.isnot(None))
        elif rtype == SharedResourceType.TASK:
            stmt = stmt.where(SharedResource.task_id.isnot(None))
        elif rtype == SharedResourceType.KNOWLEDGE_NODE:
            stmt = stmt.where(SharedResource.knowledge_node_id.isnot(None))

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # Apply sorting
    if sort == "quality":
        stmt = stmt.order_by(SharedResource.quality_score.desc().nulls_last(), SharedResource.created_at.desc())
    else:
        stmt = stmt.order_by(SharedResource.created_at.desc())

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    resources = result.scalars().all()

    items = []
    for res in resources:
        items.append(
            {
                "id": str(res.id),
                "group_id": str(res.group_id) if res.group_id else None,
                "shared_by": str(res.shared_by),
                "quality_score": res.quality_score or 0.0,
                "quality_hidden": res.quality_hidden or False,
                "adoption_count": res.adoption_count or 0,
                "avg_rating": _shared_resource_avg_rating(res),
                "view_count": res.view_count or 0,
                "save_count": res.save_count or 0,
                "created_at": res.created_at.isoformat() if res.created_at else None,
                "resource_type": "plan" if res.plan_id else "task" if res.task_id else "knowledge_node" if res.knowledge_node_id else "other",
            }
        )

    return {"resources": items, "total": total, "offset": offset, "limit": limit}


# route-tier: authed
@router.post("/shared-resources/{resource_id}/flag-misleading", summary="标记资源为误导")
async def flag_resource_misleading(
    resource_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Flag a shared resource as misleading.
    Immediately applies a quality penalty and may auto-hide the resource.
    """
    from app.services.community_service import CommunityResourceScorer

    new_score = await CommunityResourceScorer.flag_misleading(db, resource_id, current_user.id)
    if new_score is None:
        raise HTTPException(status_code=404, detail="共享资源不存在")

    await db.commit()

    from app.core.metrics import COMMUNITY_RESOURCE_MISLEADING_FLAGS_TOTAL
    COMMUNITY_RESOURCE_MISLEADING_FLAGS_TOTAL.labels(resource_id=str(resource_id)).inc()

    return {"success": True, "quality_score": new_score, "resource_id": str(resource_id)}


# ============ COM-011: 同目标伙伴 ============

# route-tier: authed
@router.get(
    "/goals/{goal_id}/similar-pursuers",
    response_model=list[SimilarGoalPursuer],
    summary="Find users pursuing similar goals",
)
async def get_similar_goal_pursuers(
    goal_id: UUID,
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """COM-011: Find other users who are pursuing goals similar to the specified goal."""
    results = await find_users_with_similar_goals(
        user_id=current_user.id,
        goal_id=goal_id,
        db=db,
        limit=limit,
    )
    return [SimilarGoalPursuer(**r) for r in results]


# ============ 管理员社区审核 ============


# route-tier: authed
@router.get("/admin/reports", summary="获取所有待处理举报（管理员）")
async def get_all_pending_reports_admin(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_active_superuser),
):
    """管理员查看所有群组的待处理举报。"""
    from app.models.community import CommunityMessageReport

    result = await db.execute(
        select(CommunityMessageReport)
        .where(CommunityMessageReport.status == "pending")
        .order_by(CommunityMessageReport.created_at.desc())
        .limit(limit)
    )
    reports = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            "reporter_id": str(r.reporter_id) if r.reporter_id else None,
            "group_id": str(r.group_id) if r.group_id else None,
            "message_id": str(r.message_id) if r.message_id else None,
            "reason": r.reason,
            "description": r.description,
            "status": r.status,
            "reviewed_by": str(r.reviewed_by) if r.reviewed_by else None,
            "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
            "action_taken": r.action_taken,
        }
        for r in reports
    ]


# route-tier: authed
@router.put("/admin/reports/{report_id}/resolve", summary="管理员处理举报")
async def admin_resolve_report(
    report_id: UUID,
    data: MessageReportReview,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_active_superuser),
):
    """管理员审核并处理举报（超级管理员可处理任何举报）。"""
    try:
        report = await ReportService.review_report(db, _admin.id, report_id, data)
        await db.commit()
        return {
            "id": str(report.id),
            "status": report.status,
            "action_taken": report.action_taken,
            "reviewed_by": str(_admin.id),
            "reviewed_at": report.reviewed_at.isoformat() if report.reviewed_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
