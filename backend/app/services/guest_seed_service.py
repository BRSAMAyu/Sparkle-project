"""
Guest Seed Service
Automatically seeds demo data for new guest users so they experience
the full app with realistic pre-populated content.
"""
import uuid
from datetime import date, datetime, timedelta

from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.data.populate_achievements import sync_achievement_definitions
from app.models.accountability import (
    AccountabilityCheckin,
    AccountabilityPartnership,
    AccountabilityStatus,
)
from app.models.cognitive import AnalysisStatus
from app.models import (
    Achievement,
    AchievementRarity,
    AchievementType,
    BehaviorPattern,
    CapsuleFeedback,
    CapsuleFavorite,
    CapsuleGenerationJob,
    CognitiveFragment,
    CuriosityCapsule,
    DepthLevel,
    Friendship,
    FriendshipStatus,
    FocusSession,
    FocusStatus,
    FocusType,
    GalaxySkin,
    GenerationType,
    Group,
    GroupMember,
    GroupMessage,
    GroupMessageRead,
    GroupRole,
    GroupTask,
    GroupTaskClaim,
    GroupType,
    InterventionAuditLog,
    InterventionFeedback,
    InterventionRequest,
    KnowledgeNode,
    MessageRole,
    MessageType,
    Notification,
    NotificationInteraction,
    NotificationPreferences,
    Plan,
    PlanType,
    Post,
    PrivateMessage,
    SharedResource,
    Task,
    TaskStatus,
    TaskType,
    User,
    UserAchievement,
    UserGalaxySkin,
    UserInterventionSettings,
    UserNodeStatus,
    UserStreakStats,
    UserTitle,
    UserVisualConfig,
    UserVisualElement,
    ChatMessage,
    ChatSession,
)
from app.models.community import MessageFavorite
from app.models.galaxy import NodeRelation
from app.models.shop import PhotonTransactionHistory, PhotonTransactionType
from app.models.user import UserStatus


async def _ensure_achievements(session: AsyncSession):
    await sync_achievement_definitions(session)

    from app.services.accountability_achievement_service import (
        accountability_achievement_service,
    )

    await accountability_achievement_service.ensure_achievement_definitions(session)


async def _ensure_galaxy_skins(session: AsyncSession):
    now = datetime.utcnow()
    skins = [
        dict(
            id="skin_nebula",
            name="星云幻彩",
            description="轻量星云渐变皮肤",
            preview_url="/skins/nebula.png",
            unlock_type="achievement",
            unlock_requirement={"achievement_id": "streak_7"},
            rarity=AchievementRarity.RARE,
            sort_order=1,
        ),
        dict(
            id="skin_solar",
            name="日耀核心",
            description="高亮太阳核心皮肤",
            preview_url="/skins/solar.png",
            unlock_type="achievement",
            unlock_requirement={"achievement_id": "study_100hours"},
            rarity=AchievementRarity.EPIC,
            sort_order=2,
        ),
    ]
    for item in skins:
        existing = await session.execute(
            select(GalaxySkin).where(GalaxySkin.id == item["id"])
        )
        if existing.scalar_one_or_none():
            continue
        session.add(GalaxySkin(**item, created_at=now, updated_at=now))


def _avatar_seed(seed: str) -> str:
    return f"https://api.dicebear.com/9.x/avataaars/png?seed={seed}"


async def _ensure_demo_user(
    session: AsyncSession,
    *,
    username: str,
    email: str,
    nickname: str,
    flame_level: int,
    flame_brightness: float,
    depth_preference: float,
    curiosity_preference: float,
    status: UserStatus,
) -> User:
    result = await session.execute(select(User).where(User.username == username))
    friend = result.scalar_one_or_none()
    if not friend:
        friend = User(
            username=username,
            email=email,
            hashed_password=get_password_hash("DemoFriend123"),
            nickname=nickname,
            avatar_url=_avatar_seed(username),
            flame_level=flame_level,
            flame_brightness=flame_brightness,
            depth_preference=depth_preference,
            curiosity_preference=curiosity_preference,
            registration_source="seed",
            is_active=True,
            status=status,
        )
        session.add(friend)
        await session.flush()
    else:
        friend.nickname = nickname
        friend.avatar_url = friend.avatar_url or _avatar_seed(username)
        friend.flame_level = max(friend.flame_level or 1, flame_level)
        friend.flame_brightness = max(friend.flame_brightness or 0.5, flame_brightness)
        friend.depth_preference = depth_preference
        friend.curiosity_preference = curiosity_preference
        friend.status = status
    return friend


async def _ensure_friendship(
    session: AsyncSession,
    *,
    left_user_id,
    right_user_id,
    initiated_by,
    status: FriendshipStatus,
    match_reason: dict | None = None,
) -> Friendship:
    uid_small, uid_large = sorted([left_user_id, right_user_id])
    friendship = (
        await session.execute(
            select(Friendship).where(
                Friendship.user_id == uid_small,
                Friendship.friend_id == uid_large,
            )
        )
    ).scalar_one_or_none()
    if friendship:
        friendship.status = status
        friendship.initiated_by = initiated_by
        if match_reason:
            friendship.match_reason = match_reason
        return friendship

    friendship = Friendship(
        user_id=uid_small,
        friend_id=uid_large,
        status=status,
        initiated_by=initiated_by,
        match_reason=match_reason,
    )
    session.add(friendship)
    await session.flush()
    return friendship


async def _ensure_group(
    session: AsyncSession,
    *,
    name: str,
    defaults: dict,
) -> Group:
    group = (
        await session.execute(select(Group).where(Group.name == name))
    ).scalar_one_or_none()
    if not group:
        group = Group(name=name, **defaults)
        session.add(group)
        await session.flush()
        return group

    for key, value in defaults.items():
        setattr(group, key, value)
    return group


async def _ensure_group_member(
    session: AsyncSession,
    *,
    group_id,
    member_id,
    role: GroupRole,
    flame_contribution: int,
    tasks_completed: int,
    checkin_streak: int,
    last_checkin_date: datetime | None,
    joined_at: datetime,
) -> GroupMember:
    membership = (
        await session.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.user_id == member_id,
            )
        )
    ).scalar_one_or_none()
    if membership:
        membership.role = role
        membership.flame_contribution = flame_contribution
        membership.tasks_completed = tasks_completed
        membership.checkin_streak = checkin_streak
        membership.last_checkin_date = last_checkin_date
        membership.joined_at = membership.joined_at or joined_at
        membership.last_active_at = max(membership.last_active_at or joined_at, joined_at)
        return membership

    membership = GroupMember(
        group_id=group_id,
        user_id=member_id,
        role=role,
        flame_contribution=flame_contribution,
        tasks_completed=tasks_completed,
        checkin_streak=checkin_streak,
        last_checkin_date=last_checkin_date,
        joined_at=joined_at,
        last_active_at=joined_at,
    )
    session.add(membership)
    await session.flush()
    return membership


async def _ensure_plan(
    session: AsyncSession,
    *,
    owner_id,
    name: str,
    defaults: dict,
) -> Plan:
    plan = (
        await session.execute(
            select(Plan).where(Plan.user_id == owner_id, Plan.name == name)
        )
    ).scalar_one_or_none()
    if plan:
        for key, value in defaults.items():
            setattr(plan, key, value)
        return plan

    plan = Plan(user_id=owner_id, name=name, **defaults)
    session.add(plan)
    await session.flush()
    return plan


async def _ensure_task(
    session: AsyncSession,
    *,
    owner_id,
    title: str,
    defaults: dict,
) -> Task:
    task = (
        await session.execute(
            select(Task).where(Task.user_id == owner_id, Task.title == title)
        )
    ).scalar_one_or_none()
    if task:
        for key, value in defaults.items():
            setattr(task, key, value)
        return task

    task = Task(user_id=owner_id, title=title, **defaults)
    session.add(task)
    await session.flush()
    return task


async def _ensure_shared_resource(
    session: AsyncSession,
    *,
    shared_by,
    group_id=None,
    target_user_id=None,
    plan_id=None,
    task_id=None,
    comment: str | None = None,
    permission: str = "view",
) -> SharedResource:
    query = select(SharedResource).where(
        SharedResource.shared_by == shared_by,
        SharedResource.group_id == group_id,
        SharedResource.target_user_id == target_user_id,
        SharedResource.plan_id == plan_id,
        SharedResource.task_id == task_id,
    )
    shared = (await session.execute(query)).scalar_one_or_none()
    if shared:
        shared.comment = comment
        shared.permission = permission
        return shared

    shared = SharedResource(
        shared_by=shared_by,
        group_id=group_id,
        target_user_id=target_user_id,
        plan_id=plan_id,
        task_id=task_id,
        comment=comment,
        permission=permission,
    )
    session.add(shared)
    await session.flush()
    return shared


async def _ensure_group_message(
    session: AsyncSession,
    *,
    group_id,
    sender_id,
    message_type: MessageType,
    content: str | None,
    created_at: datetime,
    content_data: dict | None = None,
    reply_to_id=None,
    thread_root_id=None,
    reactions: dict | None = None,
    mention_user_ids: list | None = None,
    forwarded_from_id=None,
    edited_at: datetime | None = None,
) -> GroupMessage:
    query = select(GroupMessage).where(
        GroupMessage.group_id == group_id,
        GroupMessage.sender_id == sender_id,
        GroupMessage.message_type == message_type,
        GroupMessage.content == content,
    )
    message = (await session.execute(query)).scalar_one_or_none()
    if message:
        message.content_data = content_data
        message.reply_to_id = reply_to_id
        message.thread_root_id = thread_root_id
        message.reactions = reactions
        message.mention_user_ids = mention_user_ids
        message.forwarded_from_id = forwarded_from_id
        message.edited_at = edited_at
        return message

    message = GroupMessage(
        group_id=group_id,
        sender_id=sender_id,
        message_type=message_type,
        content=content,
        content_data=content_data,
        reply_to_id=reply_to_id,
        thread_root_id=thread_root_id,
        reactions=reactions,
        mention_user_ids=mention_user_ids,
        forwarded_from_id=forwarded_from_id,
        edited_at=edited_at,
        created_at=created_at,
        updated_at=created_at,
    )
    session.add(message)
    await session.flush()
    return message


async def _ensure_private_message(
    session: AsyncSession,
    *,
    sender_id,
    receiver_id,
    message_type: MessageType,
    content: str | None,
    created_at: datetime,
    content_data: dict | None = None,
    is_read: bool = True,
    read_at: datetime | None = None,
    reply_to_id=None,
    thread_root_id=None,
    reactions: dict | None = None,
    forwarded_from_id=None,
) -> PrivateMessage:
    query = select(PrivateMessage).where(
        PrivateMessage.sender_id == sender_id,
        PrivateMessage.receiver_id == receiver_id,
        PrivateMessage.message_type == message_type,
        PrivateMessage.content == content,
    )
    message = (await session.execute(query)).scalar_one_or_none()
    if message:
        message.content_data = content_data
        message.is_read = is_read
        message.read_at = read_at
        message.reply_to_id = reply_to_id
        message.thread_root_id = thread_root_id
        message.reactions = reactions
        message.forwarded_from_id = forwarded_from_id
        return message

    message = PrivateMessage(
        sender_id=sender_id,
        receiver_id=receiver_id,
        message_type=message_type,
        content=content,
        content_data=content_data,
        is_read=is_read,
        read_at=read_at,
        reply_to_id=reply_to_id,
        thread_root_id=thread_root_id,
        reactions=reactions,
        forwarded_from_id=forwarded_from_id,
        created_at=created_at,
        updated_at=created_at,
    )
    session.add(message)
    await session.flush()
    return message


async def _ensure_group_message_read(
    session: AsyncSession,
    *,
    message_id,
    user_id,
    read_at: datetime,
) -> None:
    read = (
        await session.execute(
            select(GroupMessageRead).where(
                GroupMessageRead.message_id == message_id,
                GroupMessageRead.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if read:
        read.read_at = read_at
        return

    session.add(
        GroupMessageRead(
            message_id=message_id,
            user_id=user_id,
            read_at=read_at,
            created_at=read_at,
            updated_at=read_at,
        )
    )


async def _ensure_group_task(
    session: AsyncSession,
    *,
    group_id,
    created_by,
    title: str,
    defaults: dict,
) -> GroupTask:
    task = (
        await session.execute(
            select(GroupTask).where(
                GroupTask.group_id == group_id,
                GroupTask.title == title,
            )
        )
    ).scalar_one_or_none()
    if task:
        for key, value in defaults.items():
            setattr(task, key, value)
        return task

    task = GroupTask(
        group_id=group_id,
        created_by=created_by,
        title=title,
        **defaults,
    )
    session.add(task)
    await session.flush()
    return task


async def _ensure_group_task_claim(
    session: AsyncSession,
    *,
    group_task_id,
    user_id,
    personal_task_id=None,
    is_completed: bool = False,
    completed_at: datetime | None = None,
    claimed_at: datetime,
) -> GroupTaskClaim:
    claim = (
        await session.execute(
            select(GroupTaskClaim).where(
                GroupTaskClaim.group_task_id == group_task_id,
                GroupTaskClaim.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if claim:
        claim.personal_task_id = personal_task_id
        claim.is_completed = is_completed
        claim.completed_at = completed_at
        return claim

    claim = GroupTaskClaim(
        group_task_id=group_task_id,
        user_id=user_id,
        personal_task_id=personal_task_id,
        is_completed=is_completed,
        completed_at=completed_at,
        claimed_at=claimed_at,
    )
    session.add(claim)
    await session.flush()
    return claim


async def _ensure_message_favorite(
    session: AsyncSession,
    *,
    user_id,
    group_message_id=None,
    private_message_id=None,
    note: str | None = None,
    tags: list[str] | None = None,
) -> MessageFavorite:
    favorite = (
        await session.execute(
            select(MessageFavorite).where(
                MessageFavorite.user_id == user_id,
                MessageFavorite.group_message_id == group_message_id,
                MessageFavorite.private_message_id == private_message_id,
            )
        )
    ).scalar_one_or_none()
    if favorite:
        favorite.note = note
        favorite.tags = tags
        return favorite

    favorite = MessageFavorite(
        user_id=user_id,
        group_message_id=group_message_id,
        private_message_id=private_message_id,
        note=note,
        tags=tags,
    )
    session.add(favorite)
    await session.flush()
    return favorite


async def _ensure_partnership(
    session: AsyncSession,
    *,
    initiator_id,
    partner_id,
    friendship_id,
    initiator_goal: str,
    partner_goal: str | None,
    check_in_days: int,
    status: AccountabilityStatus,
    started_at: datetime | None,
    ended_at: datetime | None = None,
) -> AccountabilityPartnership:
    partnership = (
        await session.execute(
            select(AccountabilityPartnership).where(
                AccountabilityPartnership.initiator_id == initiator_id,
                AccountabilityPartnership.partner_id == partner_id,
            )
        )
    ).scalar_one_or_none()
    if partnership:
        partnership.friendship_id = friendship_id
        partnership.initiator_goal = initiator_goal
        partnership.partner_goal = partner_goal
        partnership.check_in_days = check_in_days
        partnership.status = status
        partnership.started_at = started_at
        partnership.ended_at = ended_at
        return partnership

    partnership = AccountabilityPartnership(
        initiator_id=initiator_id,
        partner_id=partner_id,
        friendship_id=friendship_id,
        initiator_goal=initiator_goal,
        partner_goal=partner_goal,
        check_in_days=check_in_days,
        status=status,
        started_at=started_at,
        ended_at=ended_at,
        created_at=started_at or datetime.utcnow(),
        updated_at=started_at or datetime.utcnow(),
    )
    session.add(partnership)
    await session.flush()
    return partnership


async def _ensure_accountability_checkin(
    session: AsyncSession,
    *,
    partnership_id,
    user_id,
    content: str,
    mood: int,
    minutes: int,
    created_at: datetime,
    likes: int = 0,
    liked_by: list[str] | None = None,
    encouragements: list[dict] | None = None,
) -> AccountabilityCheckin:
    checkin = (
        await session.execute(
            select(AccountabilityCheckin).where(
                AccountabilityCheckin.partnership_id == partnership_id,
                AccountabilityCheckin.user_id == user_id,
                AccountabilityCheckin.content == content,
            )
        )
    ).scalar_one_or_none()
    if checkin:
        checkin.mood = mood
        checkin.minutes = minutes
        checkin.likes = likes
        checkin.liked_by = liked_by or []
        checkin.encouragements = encouragements or []
        return checkin

    checkin = AccountabilityCheckin(
        partnership_id=partnership_id,
        user_id=user_id,
        content=content,
        mood=mood,
        minutes=minutes,
        likes=likes,
        liked_by=liked_by or [],
        encouragements=encouragements or [],
        created_at=created_at,
        updated_at=created_at,
    )
    session.add(checkin)
    await session.flush()
    return checkin


async def _ensure_user_achievement(
    session: AsyncSession,
    *,
    user_id,
    achievement_id: str,
    progress: float,
    value: int,
    target: int,
    unlocked_at: datetime | None,
    is_pinned: bool = False,
) -> UserAchievement:
    achievement = (
        await session.execute(
            select(UserAchievement).where(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement_id,
            )
        )
    ).scalar_one_or_none()
    if achievement:
        achievement.progress = progress
        achievement.progress_value = value
        achievement.progress_target = target
        achievement.unlocked_at = unlocked_at
        achievement.is_pinned = is_pinned
        achievement.last_progress_update = datetime.utcnow()
        return achievement

    achievement = UserAchievement(
        user_id=user_id,
        achievement_id=achievement_id,
        progress=progress,
        progress_value=value,
        progress_target=target,
        unlocked_at=unlocked_at,
        is_pinned=is_pinned,
        last_progress_update=datetime.utcnow(),
    )
    session.add(achievement)
    await session.flush()
    return achievement


async def _ensure_user_streak_stats(
    session: AsyncSession,
    *,
    user_id,
    current_streak: int,
    max_streak: int,
    total_checkin_days: int,
    last_activity_date: datetime,
    longest_streak_start: datetime | None = None,
    longest_streak_end: datetime | None = None,
    freeze_charges: int = 0,
    max_freeze_charges: int = 3,
) -> UserStreakStats:
    stats = (
        await session.execute(
            select(UserStreakStats).where(UserStreakStats.user_id == user_id)
        )
    ).scalar_one_or_none()
    if stats:
        stats.current_streak = current_streak
        stats.max_streak = max_streak
        stats.longest_streak = max_streak
        stats.total_checkin_days = total_checkin_days
        stats.last_activity_date = last_activity_date
        stats.longest_streak_start = longest_streak_start
        stats.longest_streak_end = longest_streak_end
        stats.freeze_charges = freeze_charges
        stats.max_freeze_charges = max_freeze_charges
        return stats

    stats = UserStreakStats(
        user_id=user_id,
        current_streak=current_streak,
        max_streak=max_streak,
        longest_streak=max_streak,
        total_checkin_days=total_checkin_days,
        last_activity_date=last_activity_date,
        longest_streak_start=longest_streak_start,
        longest_streak_end=longest_streak_end,
        freeze_charges=freeze_charges,
        max_freeze_charges=max_freeze_charges,
    )
    session.add(stats)
    await session.flush()
    return stats


async def _ensure_user_node_status(
    session: AsyncSession,
    *,
    user_id,
    node_id,
    mastery_score: int,
    total_study_minutes: int,
    study_count: int,
    first_unlock_at: datetime,
    last_study_at: datetime,
) -> UserNodeStatus:
    status = (
        await session.execute(
            select(UserNodeStatus).where(
                UserNodeStatus.user_id == user_id,
                UserNodeStatus.node_id == node_id,
            )
        )
    ).scalar_one_or_none()
    if status:
        status.is_unlocked = True
        status.mastery_score = mastery_score
        status.total_study_minutes = total_study_minutes
        status.study_count = study_count
        status.first_unlock_at = first_unlock_at
        status.last_study_at = last_study_at
        return status

    status = UserNodeStatus(
        user_id=user_id,
        node_id=node_id,
        is_unlocked=True,
        mastery_score=mastery_score,
        total_study_minutes=total_study_minutes,
        study_count=study_count,
        first_unlock_at=first_unlock_at,
        last_study_at=last_study_at,
    )
    session.add(status)
    await session.flush()
    return status


async def _ensure_focus_session(
    session: AsyncSession,
    *,
    user_id,
    start_time: datetime,
    end_time: datetime,
    duration_minutes: int,
    focus_type: FocusType,
    status: FocusStatus,
    task_id=None,
    white_noise_type: int | None = None,
) -> FocusSession:
    focus_session = (
        await session.execute(
            select(FocusSession).where(
                FocusSession.user_id == user_id,
                FocusSession.start_time == start_time,
                FocusSession.end_time == end_time,
            )
        )
    ).scalar_one_or_none()
    if focus_session:
        focus_session.duration_minutes = duration_minutes
        focus_session.focus_type = focus_type
        focus_session.status = status
        focus_session.task_id = task_id
        focus_session.white_noise_type = white_noise_type
        return focus_session

    focus_session = FocusSession(
        user_id=user_id,
        task_id=task_id,
        start_time=start_time,
        end_time=end_time,
        duration_minutes=duration_minutes,
        focus_type=focus_type,
        status=status,
        white_noise_type=white_noise_type,
    )
    session.add(focus_session)
    await session.flush()
    return focus_session


async def _ensure_notification(
    session: AsyncSession,
    *,
    user_id,
    title: str,
    content: str,
    notification_type: str,
    created_at: datetime,
    is_read: bool,
    data: dict | None = None,
    read_at: datetime | None = None,
) -> Notification:
    notification = (
        await session.execute(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.title == title,
                Notification.content == content,
            )
        )
    ).scalar_one_or_none()
    if notification:
        notification.type = notification_type
        notification.data = data
        notification.is_read = is_read
        notification.read_at = read_at
        return notification

    notification = Notification(
        user_id=user_id,
        title=title,
        content=content,
        type=notification_type,
        data=data,
        is_read=is_read,
        read_at=read_at,
        created_at=created_at,
        updated_at=created_at,
    )
    session.add(notification)
    await session.flush()
    return notification


async def _ensure_notification_interaction(
    session: AsyncSession,
    *,
    user_id,
    notification_type: str,
    notification_id,
    action_type: str,
    action_time: datetime,
    time_to_action: int | None,
) -> NotificationInteraction:
    interaction = (
        await session.execute(
            select(NotificationInteraction).where(
                NotificationInteraction.user_id == user_id,
                NotificationInteraction.notification_type == notification_type,
                NotificationInteraction.notification_id == notification_id,
                NotificationInteraction.action_type == action_type,
            )
        )
    ).scalar_one_or_none()
    if interaction:
        interaction.action_time = action_time
        interaction.time_to_action = time_to_action
        return interaction

    interaction = NotificationInteraction(
        id=uuid.uuid4(),
        user_id=user_id,
        notification_type=notification_type,
        notification_id=notification_id,
        action_type=action_type,
        action_time=action_time,
        time_to_action=time_to_action,
        created_at=action_time,
    )
    session.add(interaction)
    await session.flush()
    return interaction


async def _ensure_notification_preferences(
    session: AsyncSession,
    *,
    user_id,
    enable_system: bool,
    enable_interventions: bool,
    notification_level: str,
    quiet_hours_enabled: bool,
    quiet_hours_start: str | None,
    quiet_hours_end: str | None,
    updated_at: datetime,
) -> NotificationPreferences:
    preferences = (
        await session.execute(
            select(NotificationPreferences).where(
                NotificationPreferences.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    if preferences:
        preferences.enable_system = enable_system
        preferences.enable_interventions = enable_interventions
        preferences.notification_level = notification_level
        preferences.quiet_hours_enabled = quiet_hours_enabled
        preferences.quiet_hours_start = quiet_hours_start
        preferences.quiet_hours_end = quiet_hours_end
        preferences.updated_at = updated_at
        return preferences

    preferences = NotificationPreferences(
        user_id=user_id,
        enable_system=enable_system,
        enable_interventions=enable_interventions,
        notification_level=notification_level,
        quiet_hours_enabled=quiet_hours_enabled,
        quiet_hours_start=quiet_hours_start,
        quiet_hours_end=quiet_hours_end,
        updated_at=updated_at,
    )
    session.add(preferences)
    await session.flush()
    return preferences


async def _ensure_cognitive_fragment(
    session: AsyncSession,
    *,
    user_id,
    source_type: str,
    resource_type: str,
    content: str,
    created_at: datetime,
    sentiment: str | None = None,
    severity: int = 1,
    tags: list[str] | None = None,
    error_tags: list[str] | None = None,
    context_tags: dict | None = None,
    task_id=None,
) -> CognitiveFragment:
    fragment = (
        await session.execute(
            select(CognitiveFragment).where(
                CognitiveFragment.user_id == user_id,
                CognitiveFragment.source_type == source_type,
                CognitiveFragment.content == content,
            )
        )
    ).scalar_one_or_none()
    if fragment:
        fragment.resource_type = resource_type
        fragment.sentiment = sentiment
        fragment.severity = severity
        fragment.tags = tags
        fragment.error_tags = error_tags
        fragment.context_tags = context_tags
        fragment.task_id = task_id
        fragment.analysis_status = AnalysisStatus.COMPLETED
        return fragment

    fragment = CognitiveFragment(
        user_id=user_id,
        task_id=task_id,
        analysis_status=AnalysisStatus.COMPLETED,
        source_type=source_type,
        resource_type=resource_type,
        content=content,
        sentiment=sentiment,
        tags=tags,
        error_tags=error_tags,
        context_tags=context_tags,
        severity=severity,
        created_at=created_at,
        updated_at=created_at,
    )
    session.add(fragment)
    await session.flush()
    return fragment


async def _ensure_behavior_pattern(
    session: AsyncSession,
    *,
    user_id,
    pattern_name: str,
    pattern_type: str,
    description: str,
    solution_text: str,
    evidence_ids: list[str] | None,
    confidence_score: float,
    frequency: int,
    is_archived: bool,
    last_observed_at: datetime | None,
    last_decay_at: datetime | None = None,
) -> BehaviorPattern:
    pattern = (
        await session.execute(
            select(BehaviorPattern).where(
                BehaviorPattern.user_id == user_id,
                BehaviorPattern.pattern_name == pattern_name,
                BehaviorPattern.is_archived == is_archived,
            )
        )
    ).scalar_one_or_none()
    if pattern:
        pattern.pattern_type = pattern_type
        pattern.description = description
        pattern.solution_text = solution_text
        pattern.evidence_ids = evidence_ids
        pattern.confidence_score = confidence_score
        pattern.frequency = frequency
        pattern.last_observed_at = last_observed_at
        pattern.last_decay_at = last_decay_at
        return pattern

    pattern = BehaviorPattern(
        user_id=user_id,
        pattern_name=pattern_name,
        pattern_type=pattern_type,
        description=description,
        solution_text=solution_text,
        evidence_ids=evidence_ids,
        confidence_score=confidence_score,
        frequency=frequency,
        is_archived=is_archived,
        last_observed_at=last_observed_at,
        last_decay_at=last_decay_at,
        created_at=last_observed_at or datetime.utcnow(),
        updated_at=last_observed_at or datetime.utcnow(),
    )
    session.add(pattern)
    await session.flush()
    return pattern


async def _ensure_intervention_request(
    session: AsyncSession,
    *,
    user_id,
    dedupe_key: str,
    topic: str,
    requested_level: str,
    final_level: str,
    status: str,
    reason: dict | None,
    content: dict | None,
    cooldown_policy: dict | None,
    delivery_method: str | None,
    template_id: str | None,
    template_variant_id: str | None,
    scaffolding_level: int | None,
    intent_type: str | None,
    schema_version: str,
    policy_version: str | None,
    model_version: str | None,
    expires_at: datetime | None,
    is_retractable: bool,
    created_at: datetime,
    supersedes_id=None,
) -> InterventionRequest:
    request = (
        await session.execute(
            select(InterventionRequest).where(
                InterventionRequest.user_id == user_id,
                InterventionRequest.dedupe_key == dedupe_key,
            )
        )
    ).scalar_one_or_none()
    if request:
        request.topic = topic
        request.requested_level = requested_level
        request.final_level = final_level
        request.status = status
        request.reason = reason
        request.content = content
        request.cooldown_policy = cooldown_policy
        request.delivery_method = delivery_method
        request.template_id = template_id
        request.template_variant_id = template_variant_id
        request.scaffolding_level = scaffolding_level
        request.intent_type = intent_type
        request.schema_version = schema_version
        request.policy_version = policy_version
        request.model_version = model_version
        request.expires_at = expires_at
        request.is_retractable = is_retractable
        request.supersedes_id = supersedes_id
        return request

    request = InterventionRequest(
        user_id=user_id,
        dedupe_key=dedupe_key,
        topic=topic,
        requested_level=requested_level,
        final_level=final_level,
        status=status,
        reason=reason,
        content=content,
        cooldown_policy=cooldown_policy,
        delivery_method=delivery_method,
        template_id=template_id,
        template_variant_id=template_variant_id,
        scaffolding_level=scaffolding_level,
        intent_type=intent_type,
        schema_version=schema_version,
        policy_version=policy_version,
        model_version=model_version,
        expires_at=expires_at,
        is_retractable=is_retractable,
        supersedes_id=supersedes_id,
        created_at=created_at,
        updated_at=created_at,
    )
    session.add(request)
    await session.flush()
    return request


async def _ensure_intervention_audit(
    session: AsyncSession,
    *,
    request_id,
    user_id,
    action: str,
    guardrail_result: dict | None,
    decision_trace: dict | None,
    evidence_refs: list[str] | None,
    requested_level: str,
    final_level: str,
    policy_version: str | None,
    model_version: str | None,
    schema_version: str | None,
    occurred_at: datetime,
) -> InterventionAuditLog:
    audit = (
        await session.execute(
            select(InterventionAuditLog).where(
                InterventionAuditLog.request_id == request_id,
                InterventionAuditLog.action == action,
            )
        )
    ).scalar_one_or_none()
    if audit:
        audit.guardrail_result = guardrail_result
        audit.decision_trace = decision_trace
        audit.evidence_refs = evidence_refs
        audit.requested_level = requested_level
        audit.final_level = final_level
        audit.policy_version = policy_version
        audit.model_version = model_version
        audit.schema_version = schema_version
        audit.occurred_at = occurred_at
        return audit

    audit = InterventionAuditLog(
        request_id=request_id,
        user_id=user_id,
        action=action,
        guardrail_result=guardrail_result,
        decision_trace=decision_trace,
        evidence_refs=evidence_refs,
        requested_level=requested_level,
        final_level=final_level,
        policy_version=policy_version,
        model_version=model_version,
        schema_version=schema_version,
        occurred_at=occurred_at,
        created_at=occurred_at,
        updated_at=occurred_at,
    )
    session.add(audit)
    await session.flush()
    return audit


async def _ensure_intervention_feedback(
    session: AsyncSession,
    *,
    request_id,
    user_id,
    feedback_type: str,
    extra_data: dict | None,
    idempotency_key: str,
    created_at: datetime,
) -> InterventionFeedback:
    feedback = (
        await session.execute(
            select(InterventionFeedback).where(
                InterventionFeedback.request_id == request_id,
                InterventionFeedback.user_id == user_id,
                InterventionFeedback.feedback_type == feedback_type,
                InterventionFeedback.idempotency_key == idempotency_key,
            )
        )
    ).scalar_one_or_none()
    if feedback:
        feedback.extra_data = extra_data
        return feedback

    feedback = InterventionFeedback(
        request_id=request_id,
        user_id=user_id,
        feedback_type=feedback_type,
        extra_data=extra_data,
        idempotency_key=idempotency_key,
        created_at=created_at,
        updated_at=created_at,
    )
    session.add(feedback)
    await session.flush()
    return feedback


async def _ensure_intervention_settings(
    session: AsyncSession,
    *,
    user_id,
    interrupt_threshold: float,
    daily_interrupt_budget: int,
    cooldown_minutes: int,
    quiet_hours: dict | None,
    topic_allowlist: list[str] | None,
    topic_blocklist: list[str] | None,
    do_not_disturb: bool,
) -> UserInterventionSettings:
    settings = (
        await session.execute(
            select(UserInterventionSettings).where(
                UserInterventionSettings.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    if settings:
        settings.interrupt_threshold = interrupt_threshold
        settings.daily_interrupt_budget = daily_interrupt_budget
        settings.cooldown_minutes = cooldown_minutes
        settings.quiet_hours = quiet_hours
        settings.topic_allowlist = topic_allowlist
        settings.topic_blocklist = topic_blocklist
        settings.do_not_disturb = do_not_disturb
        return settings

    settings = UserInterventionSettings(
        user_id=user_id,
        interrupt_threshold=interrupt_threshold,
        daily_interrupt_budget=daily_interrupt_budget,
        cooldown_minutes=cooldown_minutes,
        quiet_hours=quiet_hours,
        topic_allowlist=topic_allowlist,
        topic_blocklist=topic_blocklist,
        do_not_disturb=do_not_disturb,
    )
    session.add(settings)
    await session.flush()
    return settings


async def _ensure_user_visual_element(
    session: AsyncSession,
    *,
    user_id,
    element_id: str,
    unlocked_at: datetime,
    unlock_source: str,
    source_id: str | None = None,
) -> UserVisualElement:
    unlocked = (
        await session.execute(
            select(UserVisualElement).where(
                UserVisualElement.user_id == user_id,
                UserVisualElement.element_id == element_id,
            )
        )
    ).scalar_one_or_none()
    if unlocked:
        unlocked.unlocked_at = unlocked_at
        unlocked.unlock_source = unlock_source
        unlocked.source_id = source_id
        return unlocked

    unlocked = UserVisualElement(
        user_id=user_id,
        element_id=element_id,
        unlocked_at=unlocked_at,
        unlock_source=unlock_source,
        source_id=source_id,
        created_at=unlocked_at,
        updated_at=unlocked_at,
    )
    session.add(unlocked)
    await session.flush()
    return unlocked


async def _ensure_user_visual_config(
    session: AsyncSession,
    *,
    user_id,
    equipped_background_id: str | None,
    equipped_particle_id: str | None,
    equipped_effect_id: str | None,
    equipped_at: datetime,
) -> UserVisualConfig:
    config = (
        await session.execute(
            select(UserVisualConfig).where(UserVisualConfig.user_id == user_id)
        )
    ).scalar_one_or_none()
    if not config:
        config = UserVisualConfig(user_id=user_id, created_at=equipped_at, updated_at=equipped_at)
        session.add(config)
        await session.flush()

    config.equipped_background_id = equipped_background_id
    config.equipped_particle_id = equipped_particle_id
    config.equipped_effect_id = equipped_effect_id
    config.background_equipped_at = equipped_at if equipped_background_id else None
    config.particle_equipped_at = equipped_at if equipped_particle_id else None
    config.effect_equipped_at = equipped_at if equipped_effect_id else None
    config.updated_at = equipped_at
    return config


async def seed_guest_user_data(session: AsyncSession, user: User) -> None:
    """
    Seed demo data for a new guest user.
    Idempotent — safe to call multiple times (checks before inserting).
    """
    now = datetime.utcnow()

    # Update guest profile to look like an active learner
    user.nickname = f"访客体验{user.username[-4:]}"
    user.flame_level = 15
    user.flame_brightness = 0.85
    user.depth_preference = 0.7
    user.curiosity_preference = 0.8
    user.avatar_url = f"https://api.dicebear.com/9.x/avataaars/png?seed={user.username}"

    # 访客用户设置较高的初始积分（让访客能体验积分系统，但不能转账）
    user.photon_balance = 1000
    user.photon_updated_at = datetime.utcnow()
    photon_history_exists = await session.execute(
        select(PhotonTransactionHistory).where(
            PhotonTransactionHistory.user_id == user.id,
        )
    )
    if photon_history_exists.first() is None:
        session.add(
            PhotonTransactionHistory(
                id=uuid.uuid4(),
                user_id=user.id,
                transaction_type=PhotonTransactionType.GRANT_ACHIEVEMENT.value,
                amount=1000,
                balance_before=0,
                balance_after=1000,
                source="guest_seed:welcome_bonus",
                related_item_id="guest_welcome",
                extra_data={"reason": "guest_experience_seed"},
                created_at=now,
                updated_at=now,
            )
        )

    # Achievements
    await _ensure_achievements(session)
    await session.flush()

    def _make_user_achievement(achievement_id: str, progress: float, value: int, target: int, unlocked: bool):
        return UserAchievement(
            user_id=user.id,
            achievement_id=achievement_id,
            progress=progress,
            progress_value=value,
            progress_target=target,
            unlocked_at=now - timedelta(days=1) if unlocked else None,
            is_pinned=unlocked,
            last_progress_update=now,
        )

    for ua in [
        _make_user_achievement("streak_7", 1.0, 7, 7, True),
        _make_user_achievement("streak_30", 0.23, 7, 30, False),
        _make_user_achievement("nodes_100", 0.45, 45, 100, False),
        _make_user_achievement("study_100hours", 0.62, 62, 100, False),
        _make_user_achievement("sprint_first", 1.0, 1, 1, True),
        _make_user_achievement("night_owl", 1.0, 10, 10, True),
    ]:
        exists = await session.execute(
            select(UserAchievement).where(
                UserAchievement.user_id == user.id,
                UserAchievement.achievement_id == ua.achievement_id,
            )
        )
        if not exists.scalar_one_or_none():
            session.add(ua)

    # Streak stats
    streak_exists = await session.execute(
        select(UserStreakStats).where(UserStreakStats.user_id == user.id)
    )
    if not streak_exists.scalar_one_or_none():
        session.add(
            UserStreakStats(
                user_id=user.id,
                current_streak=7,
                max_streak=30,
                longest_streak=30,
                total_checkin_days=45,
                last_activity_date=now - timedelta(hours=2),
                longest_streak_start=now - timedelta(days=30),
                longest_streak_end=now - timedelta(days=1),
                freeze_charges=2,
                max_freeze_charges=3,
            )
        )

    # Knowledge Nodes (Galaxy) - Create a rich demo knowledge graph
    # Mirrors the 6-sector structure from DemoDataService (COSMOS/TECH/ART/CIVILIZATION/LIFE/WISDOM)
    import math

    # Define nodes: (name, description, importance, keywords, sector_label, unlocked, mastery, study_count)
    _DEMO_NODES = [
        # === COSMOS 星域 - 自然科学基础 ===
        ("高等数学", "微积分、极限、导数、积分等基础数学知识", 5, ["数学", "基础"], "COSMOS", True, 85, 12),
        ("线性代数", "矩阵、向量空间、线性变换", 4, ["数学", "线性代数"], "COSMOS", True, 70, 8),
        ("概率论与数理统计", "概率、随机变量、统计推断", 4, ["数学", "统计"], "COSMOS", True, 60, 6),
        ("离散数学", "集合论、图论、组合数学、数理逻辑", 4, ["数学", "离散"], "COSMOS", True, 55, 5),
        ("大学物理", "力学、电磁学、热学、光学基础", 4, ["物理", "基础"], "COSMOS", True, 65, 7),
        ("经典力学", "牛顿力学、动量、能量", 3, ["物理", "力学"], "COSMOS", True, 70, 5),
        ("电磁学基础", "电场、磁场、电磁感应", 3, ["物理", "电磁"], "COSMOS", True, 50, 4),
        ("普通化学", "化学反应、元素周期表、化学键", 3, ["化学", "基础"], "COSMOS", True, 45, 3),
        ("有机化学", "有机物结构、反应机理", 2, ["化学", "有机"], "COSMOS", False, 0, 0),
        # === TECH 星域 - 科技与工程 ===
        ("程序设计基础", "变量、控制流、函数、基本算法", 5, ["编程", "基础"], "TECH", True, 90, 15),
        ("Python编程", "Python语法、数据结构、面向对象", 4, ["Python", "编程"], "TECH", True, 80, 10),
        ("C/C++编程", "C语言基础、指针、C++面向对象", 4, ["C++", "编程"], "TECH", True, 75, 9),
        ("Java编程", "Java语法、OOP、集合框架", 4, ["Java", "编程"], "TECH", True, 70, 8),
        ("数据结构", "线性表、栈、队列、树、图", 5, ["数据结构", "算法"], "TECH", True, 85, 12),
        ("算法设计与分析", "排序、搜索、动态规划、贪心算法", 5, ["算法", "优化"], "TECH", True, 70, 8),
        ("计算机组成原理", "CPU、内存、I/O系统", 4, ["计算机系统", "硬件"], "TECH", True, 65, 7),
        ("操作系统", "进程、内存管理、文件系统", 5, ["操作系统", "OS"], "TECH", True, 60, 6),
        ("计算机网络", "TCP/IP、HTTP、网络协议", 4, ["网络", "协议"], "TECH", True, 55, 5),
        ("数据库系统", "SQL、关系模型、事务处理", 4, ["数据库", "SQL"], "TECH", True, 70, 8),
        ("Web前端开发", "HTML、CSS、JavaScript基础", 3, ["Web", "前端"], "TECH", True, 60, 6),
        ("Web后端开发", "RESTful API、服务器开发", 3, ["Web", "后端"], "TECH", True, 50, 4),
        ("人工智能基础", "机器学习、神经网络入门", 4, ["AI", "机器学习"], "TECH", True, 40, 3),
        ("机器学习", "监督学习、非监督学习、模型评估", 4, ["机器学习", "ML"], "TECH", False, 0, 0),
        # === ART 星域 - 艺术与人文 ===
        ("中国文学", "古代文学、现代文学、诗词赏析", 4, ["文学", "中国"], "ART", True, 75, 9),
        ("外国文学", "西方文学、世界文学经典", 3, ["文学", "外国"], "ART", True, 60, 6),
        ("写作技巧", "议论文、说明文、创意写作", 3, ["写作", "技巧"], "ART", True, 65, 7),
        ("美术基础", "素描、色彩、构图", 2, ["美术", "绘画"], "ART", True, 45, 4),
        ("音乐欣赏", "音乐史、乐理、作品欣赏", 2, ["音乐", "欣赏"], "ART", True, 50, 5),
        ("设计思维", "UI/UX设计、平面设计原理", 3, ["设计", "UI"], "ART", True, 55, 5),
        ("摄影基础", "构图、光影、后期处理", 2, ["摄影", "艺术"], "ART", True, 60, 6),
        ("影视制作", "视频拍摄、剪辑、叙事技巧", 2, ["影视", "制作"], "ART", False, 0, 0),
        # === CIVILIZATION 星域 - 社会与文明 ===
        ("中国近现代史", "辛亥革命、新中国成立、改革开放", 4, ["历史", "中国"], "CIVILIZATION", True, 80, 10),
        ("世界历史", "文艺复兴、工业革命、两次世界大战", 4, ["历史", "世界"], "CIVILIZATION", True, 70, 8),
        ("马克思主义基本原理", "唯物辩证法、政治经济学", 4, ["政治", "马克思主义"], "CIVILIZATION", True, 75, 9),
        ("经济学原理", "微观经济、宏观经济、市场机制", 4, ["经济", "市场"], "CIVILIZATION", True, 60, 6),
        ("管理学基础", "组织管理、领导力、战略规划", 3, ["管理", "组织"], "CIVILIZATION", True, 55, 5),
        ("法律基础", "宪法、民法、刑法基础知识", 3, ["法律", "权利"], "CIVILIZATION", True, 50, 4),
        ("社会学导论", "社会结构、群体行为、社会问题", 3, ["社会", "群体"], "CIVILIZATION", True, 45, 3),
        # === LIFE 星域 - 生命科学 ===
        ("普通生物学", "细胞、遗传、进化、生态", 4, ["生物", "基础"], "LIFE", True, 70, 8),
        ("人体生理学", "循环系统、消化系统、神经系统", 3, ["生理", "人体"], "LIFE", True, 60, 6),
        ("基因与遗传", "DNA、基因表达、遗传规律", 3, ["遗传", "基因"], "LIFE", True, 55, 5),
        ("健康与养生", "营养、运动、睡眠、疾病预防", 3, ["健康", "养生"], "LIFE", True, 75, 9),
        ("急救与安全", "CPR、止血、常见急症处理", 3, ["急救", "安全"], "LIFE", True, 65, 7),
        ("心理学导论", "认知、情绪、人格、行为", 4, ["心理", "认知"], "LIFE", True, 70, 8),
        ("发展心理学", "儿童、青少年、成人心理发展", 3, ["心理", "发展"], "LIFE", True, 50, 4),
        ("社会心理学", "态度、说服、群体影响", 3, ["心理", "社会"], "LIFE", True, 45, 3),
        # === WISDOM 星域 - 智慧与思考 ===
        ("哲学导论", "形而上学、认识论、伦理学", 4, ["哲学", "思考"], "WISDOM", True, 65, 7),
        ("中国哲学", "儒家、道家、佛家思想", 3, ["哲学", "中国"], "WISDOM", True, 60, 6),
        ("西方哲学", "古希腊哲学、近代哲学、现代哲学", 3, ["哲学", "西方"], "WISDOM", True, 55, 5),
        ("批判性思维", "逻辑推理、论证分析、谬误识别", 5, ["思维", "逻辑"], "WISDOM", True, 70, 8),
        ("创新思维", "发散思维、联想、头脑风暴", 4, ["思维", "创新"], "WISDOM", True, 60, 6),
        ("系统思维", "整体观、反馈循环、涌现特性", 4, ["思维", "系统"], "WISDOM", True, 50, 4),
        ("学习科学", "记忆原理、遗忘曲线、刻意练习", 5, ["学习", "方法"], "WISDOM", True, 80, 10),
        ("时间管理", "四象限法则、番茄钟、GTD", 4, ["效率", "时间"], "WISDOM", True, 75, 9),
    ]

    # Sector layout: each sector occupies a 60° arc, nodes spread within it
    _SECTOR_ANGLES = {
        "COSMOS": 0, "TECH": 60, "ART": 120,
        "CIVILIZATION": 180, "LIFE": 240, "WISDOM": 300,
    }
    _sector_counters: dict[str, int] = {}

    created_nodes: dict[str, KnowledgeNode] = {}  # name -> node (for relations)

    for node_tuple in _DEMO_NODES:
        name, desc, importance, keywords, sector, unlocked, mastery, study_count = node_tuple

        existing = (await session.execute(
            select(KnowledgeNode).where(KnowledgeNode.name == name)
        )).scalar_one_or_none()
        if existing:
            created_nodes[name] = existing
            continue

        # Calculate position within sector
        sector_idx = _sector_counters.get(sector, 0)
        _sector_counters[sector] = sector_idx + 1
        base_angle_deg = _SECTOR_ANGLES[sector]
        # Spread nodes within 50° range, offset from sector center
        angle_deg = base_angle_deg + 5 + (sector_idx * 5) % 50
        angle_rad = math.radians(angle_deg)
        # Vary radius by importance (more important = closer to center)
        radius = 150.0 + (5 - importance) * 40 + (sector_idx % 3) * 20

        node = KnowledgeNode(
            name=name,
            description=desc,
            importance_level=importance,
            is_seed=True,
            source_type="seed",
            keywords=keywords,
            position_x=radius * math.cos(angle_rad),
            position_y=radius * math.sin(angle_rad),
        )
        session.add(node)
        await session.flush()
        created_nodes[name] = node

    # Create relations between nodes (prerequisite/related edges)
    _RELATIONS = [
        ("高等数学", "线性代数", "prerequisite", 0.9),
        ("高等数学", "概率论与数理统计", "prerequisite", 0.8),
        ("高等数学", "离散数学", "related", 0.6),
        ("大学物理", "经典力学", "prerequisite", 0.9),
        ("大学物理", "电磁学基础", "prerequisite", 0.8),
        ("普通化学", "有机化学", "prerequisite", 0.7),
        ("程序设计基础", "Python编程", "prerequisite", 0.9),
        ("程序设计基础", "C/C++编程", "prerequisite", 0.9),
        ("程序设计基础", "Java编程", "prerequisite", 0.8),
        ("程序设计基础", "数据结构", "prerequisite", 0.9),
        ("数据结构", "算法设计与分析", "prerequisite", 0.9),
        ("计算机组成原理", "操作系统", "prerequisite", 0.8),
        ("操作系统", "计算机网络", "related", 0.6),
        ("数据库系统", "Web后端开发", "prerequisite", 0.7),
        ("Web前端开发", "设计思维", "related", 0.5),
        ("人工智能基础", "机器学习", "prerequisite", 0.9),
        ("概率论与数理统计", "机器学习", "prerequisite", 0.8),
        ("线性代数", "人工智能基础", "prerequisite", 0.7),
        ("心理学导论", "发展心理学", "prerequisite", 0.8),
        ("心理学导论", "社会心理学", "prerequisite", 0.8),
        ("普通生物学", "人体生理学", "prerequisite", 0.8),
        ("普通生物学", "基因与遗传", "prerequisite", 0.7),
        ("哲学导论", "中国哲学", "prerequisite", 0.7),
        ("哲学导论", "西方哲学", "prerequisite", 0.7),
        ("批判性思维", "学习科学", "related", 0.6),
        ("学习科学", "时间管理", "related", 0.7),
        # Cross-sector relations
        ("离散数学", "数据结构", "prerequisite", 0.8),
        ("离散数学", "算法设计与分析", "prerequisite", 0.7),
        ("心理学导论", "学习科学", "related", 0.7),
        ("批判性思维", "写作技巧", "application", 0.5),
        ("经济学原理", "管理学基础", "related", 0.6),
    ]

    for src_name, tgt_name, rel_type, strength in _RELATIONS:
        src = created_nodes.get(src_name)
        tgt = created_nodes.get(tgt_name)
        if not src or not tgt:
            continue
        rel_exists = (await session.execute(
            select(NodeRelation).where(
                NodeRelation.source_node_id == src.id,
                NodeRelation.target_node_id == tgt.id,
            )
        )).scalar_one_or_none()
        if not rel_exists:
            session.add(NodeRelation(
                source_node_id=src.id,
                target_node_id=tgt.id,
                relation_type=rel_type,
                strength=strength,
                created_by="seed",
            ))

    await session.flush()

    # Create UserNodeStatus for unlocked nodes
    for node_tuple in _DEMO_NODES:
        name, _, _, _, _, unlocked, mastery, study_count = node_tuple
        if not unlocked:
            continue
        node = created_nodes.get(name)
        if not node:
            continue
        status_exists = (await session.execute(
            select(UserNodeStatus).where(
                UserNodeStatus.user_id == user.id,
                UserNodeStatus.node_id == node.id,
            )
        )).scalar_one_or_none()
        if not status_exists:
            session.add(UserNodeStatus(
                user_id=user.id,
                node_id=node.id,
                is_unlocked=True,
                mastery_score=mastery,
                total_study_minutes=study_count * 15,
                study_count=study_count,
                first_unlock_at=now - timedelta(days=max(1, study_count)),
                last_study_at=now - timedelta(hours=study_count),
            ))

    # Galaxy skins
    await _ensure_galaxy_skins(session)
    await session.flush()

    skin = (await session.execute(select(GalaxySkin).where(GalaxySkin.id == "skin_nebula"))).scalar_one_or_none()
    if skin:
        skin_exists = await session.execute(
            select(UserGalaxySkin).where(
                UserGalaxySkin.user_id == user.id,
                UserGalaxySkin.skin_id == skin.id,
            )
        )
        if not skin_exists.scalar_one_or_none():
            session.add(
                UserGalaxySkin(
                    user_id=user.id,
                    skin_id=skin.id,
                    unlocked_at=now - timedelta(days=5),
                    unlock_source="achievement",
                    is_equipped=True,
                )
            )

    # Title
    title_exists = await session.execute(
        select(UserTitle).where(UserTitle.user_id == user.id, UserTitle.title_id == "title_sprinter")
    )
    if not title_exists.scalar_one_or_none():
        session.add(
            UserTitle(
                user_id=user.id,
                title_id="title_sprinter",
                title_name="冲刺高手",
                title_display="🏃 冲刺高手",
                source_achievement_id="sprint_first",
                is_equipped=True,
                unlocked_at=now - timedelta(days=2),
            )
        )

    # Plans
    sprint_plan = (await session.execute(
        select(Plan).where(Plan.user_id == user.id, Plan.name == "数据结构期中冲刺")
    )).scalar_one_or_none()
    if not sprint_plan:
        sprint_plan = Plan(
            user_id=user.id,
            name="数据结构期中冲刺",
            type=PlanType.SPRINT,
            description="集中攻克链表、栈、队列和二叉树，准备期中考试。",
            target_date=date.today() + timedelta(days=7),
            daily_available_minutes=120,
            total_estimated_hours=20,
            mastery_level=0.6,
            progress=0.7,
            is_active=True,
            is_primary=True,
        )
        session.add(sprint_plan)
        await session.flush()

    growth_plan = (await session.execute(
        select(Plan).where(Plan.user_id == user.id, Plan.name == "计算机科学基础巩固")
    )).scalar_one_or_none()
    if not growth_plan:
        growth_plan = Plan(
            user_id=user.id,
            name="计算机科学基础巩固",
            type=PlanType.GROWTH,
            description="系统性复习CS基础四大件，构建完整的知识体系。",
            target_date=date.today() + timedelta(days=90),
            daily_available_minutes=60,
            total_estimated_hours=100,
            mastery_level=0.3,
            progress=0.45,
            is_active=True,
        )
        session.add(growth_plan)
        await session.flush()

    # Tasks
    for task_data in [
        dict(
            title="数据结构 - 二叉树遍历算法",
            type=TaskType.LEARNING,
            tags=["CS", "Data Structures", "Tree"],
            estimated_minutes=90,
            difficulty=4,
            energy_cost=4,
            status=TaskStatus.IN_PROGRESS,
            priority=3,
            due_date=date.today(),
            started_at=now - timedelta(minutes=30),
            plan_id=sprint_plan.id,
        ),
        dict(
            title="操作系统 - 死锁处理机制",
            type=TaskType.LEARNING,
            tags=["OS", "Concurrency"],
            estimated_minutes=75,
            difficulty=4,
            energy_cost=3,
            status=TaskStatus.PENDING,
            priority=3,
            due_date=date.today(),
            plan_id=sprint_plan.id,
        ),
        dict(
            title="离散数学 - 图论着色问题",
            type=TaskType.LEARNING,
            tags=["Math", "Graph Theory"],
            estimated_minutes=120,
            difficulty=4,
            energy_cost=4,
            status=TaskStatus.PENDING,
            priority=3,
            due_date=date.today() + timedelta(days=2),
            plan_id=growth_plan.id,
        ),
        dict(
            title="计算机网络 - TCP协议分析",
            type=TaskType.LEARNING,
            tags=["Network", "Protocol"],
            estimated_minutes=90,
            difficulty=3,
            energy_cost=3,
            status=TaskStatus.PENDING,
            priority=2,
            due_date=date.today() + timedelta(days=3),
            plan_id=growth_plan.id,
        ),
    ]:
        exists = await session.execute(
            select(Task).where(Task.user_id == user.id, Task.title == task_data["title"])
        )
        if not exists.scalar_one_or_none():
            session.add(Task(user_id=user.id, **task_data))

    # Curiosity Capsules
    capsule_ids = []
    for capsule_data in [
        dict(
            title="为什么二叉树的遍历有三种方式？",
            content="二叉树的三种遍历方式（前序、中序、后序）源于访问节点的不同时机。前序先访问根，适合复制树结构；中序产生有序序列，适合BST；后序最后访问根，适合释放资源。",
            related_subject="数据结构",
            depth_level=DepthLevel.DEEP,
            generation_method="knowledge_gap_analysis",
            quality_score=0.92,
            feedback_count=0,
            share_count=0,
            is_read=False,
        ),
        dict(
            title="进程和线程的本质区别是什么？",
            content="进程=资源容器+执行轨迹；线程=共享资源+独立执行轨迹。进程是OS资源分配单位，线程是CPU调度单位。同一进程内线程共享内存空间，这是并发编程中数据竞争问题的根源。",
            related_subject="操作系统",
            depth_level=DepthLevel.DEEP,
            generation_method="concept_clarification",
            quality_score=0.88,
            feedback_count=1,
            share_count=2,
            is_read=True,
        ),
        dict(
            title="TCP为什么需要三次握手？",
            content="三次握手用于同步序列号并确认双方收发能力。一次握手无法确认服务器发送能力；两次握手会导致历史连接复用问题。三次是双方确认各自收发正常的最少次数。",
            related_subject="计算机网络",
            depth_level=DepthLevel.MEDIUM,
            generation_method="why_question",
            quality_score=0.85,
            feedback_count=0,
            share_count=1,
            is_read=True,
        ),
    ]:
        exists = await session.execute(
            select(CuriosityCapsule).where(
                CuriosityCapsule.user_id == user.id,
                CuriosityCapsule.title == capsule_data["title"],
            )
        )
        capsule = exists.scalar_one_or_none()
        if capsule:
            capsule_ids.append(capsule.id)
        else:
            capsule = CuriosityCapsule(user_id=user.id, **capsule_data)
            session.add(capsule)
            await session.flush()
            capsule_ids.append(capsule.id)

    if len(capsule_ids) >= 2:
        fav_exists = await session.execute(
            select(CapsuleFavorite).where(
                CapsuleFavorite.user_id == user.id,
                CapsuleFavorite.capsule_id == capsule_ids[1],
            )
        )
        if not fav_exists.scalar_one_or_none():
            session.add(CapsuleFavorite(user_id=user.id, capsule_id=capsule_ids[1]))

        feedback_exists = await session.execute(
            select(CapsuleFeedback).where(
                CapsuleFeedback.user_id == user.id,
                CapsuleFeedback.capsule_id == capsule_ids[1],
            )
        )
        if not feedback_exists.scalar_one_or_none():
            session.add(
                CapsuleFeedback(
                    user_id=user.id,
                    capsule_id=capsule_ids[1],
                    rating=5,
                    helpful=True,
                    category="just_right",
                    comment="内容很实用",
                )
            )

        job_exists = await session.execute(
            select(CapsuleGenerationJob).where(CapsuleGenerationJob.user_id == user.id)
        )
        if not job_exists.scalar_one_or_none():
            session.add(
                CapsuleGenerationJob(
                    user_id=user.id,
                    status="completed",
                    generation_type=GenerationType.DAILY.value,
                    depth_preference=0.7,
                    curiosity_preference=0.6,
                    requested_count=3,
                    actual_count=3,
                    capsule_ids=[str(item) for item in capsule_ids],
                    progress=1.0,
                    duration_ms=4200,
                    completed_at=now - timedelta(hours=2),
                )
            )

    user_primary_task = (
        await session.execute(
            select(Task).where(
                Task.user_id == user.id,
                Task.title == "数据结构 - 二叉树遍历算法",
            )
        )
    ).scalar_one()

    user_network_task = (
        await session.execute(
            select(Task).where(
                Task.user_id == user.id,
                Task.title == "计算机网络 - TCP协议分析",
            )
        )
    ).scalar_one()

    user_review_task = await _ensure_task(
        session,
        owner_id=user.id,
        title="操作系统 - 线程同步错题回顾",
        defaults=dict(
            type=TaskType.LEARNING,
            tags=["OS", "线程同步", "错题"],
            estimated_minutes=45,
            difficulty=3,
            energy_cost=3,
            status=TaskStatus.COMPLETED,
            priority=2,
            due_date=date.today() - timedelta(days=1),
            completed_at=now - timedelta(days=1, hours=2),
            actual_minutes=55,
            user_note="把锁、信号量、条件变量的易混点重新过了一遍。",
            plan_id=growth_plan.id,
        ),
    )
    user_english_task = await _ensure_task(
        session,
        owner_id=user.id,
        title="英语口语 - 晨读复述 15 分钟",
        defaults=dict(
            type=TaskType.LEARNING,
            tags=["English", "Speaking", "Checkin"],
            estimated_minutes=20,
            difficulty=2,
            energy_cost=2,
            status=TaskStatus.COMPLETED,
            priority=2,
            due_date=date.today(),
            completed_at=now - timedelta(hours=1, minutes=5),
            actual_minutes=30,
            user_note="把昨天群里提到的微反馈模板顺口复述了一遍。",
            plan_id=growth_plan.id,
        ),
    )

    default_visual_unlock_at = now - timedelta(days=30)
    for element_id in [
        "background_origin_chamber",
        "particle_origin_sparks",
        "effect_origin_aura",
    ]:
        await _ensure_user_visual_element(
            session,
            user_id=user.id,
            element_id=element_id,
            unlocked_at=default_visual_unlock_at,
            unlock_source="system",
        )
    await _ensure_user_visual_element(
        session,
        user_id=user.id,
        element_id="particle_streak_embers",
        unlocked_at=now - timedelta(days=7),
        unlock_source="achievement",
        source_id="streak_7",
    )
    await _ensure_user_visual_config(
        session,
        user_id=user.id,
        equipped_background_id="background_origin_chamber",
        equipped_particle_id="particle_streak_embers",
        equipped_effect_id="effect_origin_aura",
        equipped_at=now - timedelta(days=5),
    )

    focus_seed_rows = [
        (now - timedelta(days=9, hours=3), 50, FocusType.POMODORO, FocusStatus.COMPLETED, user_primary_task.id, 1),
        (now - timedelta(days=8, hours=8), 35, FocusType.STOPWATCH, FocusStatus.INTERRUPTED, None, 2),
        (now - timedelta(days=8, hours=2), 40, FocusType.POMODORO, FocusStatus.COMPLETED, user_review_task.id, 1),
        (now - timedelta(days=7, hours=5), 65, FocusType.STOPWATCH, FocusStatus.COMPLETED, user_network_task.id, 3),
        (now - timedelta(days=6, hours=1), 25, FocusType.POMODORO, FocusStatus.COMPLETED, user_primary_task.id, 1),
        (now - timedelta(days=5, hours=6), 30, FocusType.POMODORO, FocusStatus.COMPLETED, user_review_task.id, 2),
        (now - timedelta(days=4, hours=2), 55, FocusType.STOPWATCH, FocusStatus.COMPLETED, user_primary_task.id, 3),
        (now - timedelta(days=3, hours=7), 20, FocusType.POMODORO, FocusStatus.INTERRUPTED, user_network_task.id, None),
        (now - timedelta(days=3, hours=1), 45, FocusType.POMODORO, FocusStatus.COMPLETED, user_review_task.id, 1),
        (now - timedelta(days=2, hours=4), 60, FocusType.STOPWATCH, FocusStatus.COMPLETED, user_primary_task.id, 2),
        (now - timedelta(days=1, hours=2), 35, FocusType.POMODORO, FocusStatus.COMPLETED, user_english_task.id, 1),
        (now - timedelta(hours=6), 25, FocusType.POMODORO, FocusStatus.COMPLETED, user_primary_task.id, 1),
        (now - timedelta(hours=2, minutes=20), 30, FocusType.STOPWATCH, FocusStatus.COMPLETED, user_english_task.id, 2),
    ]
    for start_time, duration, focus_type, status, task_id, noise in focus_seed_rows:
        await _ensure_focus_session(
            session,
            user_id=user.id,
            start_time=start_time,
            end_time=start_time + timedelta(minutes=duration),
            duration_minutes=duration,
            focus_type=focus_type,
            status=status,
            task_id=task_id,
            white_noise_type=noise,
        )

    fragment_1 = await _ensure_cognitive_fragment(
        session,
        user_id=user.id,
        task_id=user_primary_task.id,
        source_type="behavior",
        resource_type="text",
        content="准备只测社群收藏，结果一会儿去翻任务卡，一会儿又切去看计划卡展示。",
        created_at=now - timedelta(days=4, hours=5),
        sentiment="neutral",
        severity=2,
        tags=["验收", "上下文切换"],
        error_tags=["execution.context_switch"],
        context_tags={"scene": "community_testing", "location": "dorm"},
    )
    fragment_2 = await _ensure_cognitive_fragment(
        session,
        user_id=user.id,
        task_id=user_review_task.id,
        source_type="capsule",
        resource_type="text",
        content="明明以为 20 分钟能复盘完线程同步，结果一展开就比预想复杂。",
        created_at=now - timedelta(days=3, hours=2),
        sentiment="anxious",
        severity=3,
        tags=["复盘", "计划评估"],
        error_tags=["planning.underestimate"],
        context_tags={"scene": "task_review", "energy": "medium"},
    )
    fragment_3 = await _ensure_cognitive_fragment(
        session,
        user_id=user.id,
        task_id=user_network_task.id,
        source_type="interceptor",
        resource_type="text",
        content="测试到一半想直接跳去改接口，说明我还是会在临近完成时提前收缩范围。",
        created_at=now - timedelta(days=2, hours=6),
        sentiment="neutral",
        severity=2,
        tags=["范围控制", "验收"],
        error_tags=["planning.scope_shrink"],
        context_tags={"scene": "api_validation", "device": "mobile"},
    )
    fragment_4 = await _ensure_cognitive_fragment(
        session,
        user_id=user.id,
        task_id=user_english_task.id,
        source_type="behavior",
        resource_type="text",
        content="晨读的时候把微反馈说短以后，反而更容易连续坚持。",
        created_at=now - timedelta(days=1, hours=3),
        sentiment="focused",
        severity=1,
        tags=["微反馈", "正向强化"],
        error_tags=[],
        context_tags={"scene": "morning_reading", "mood": "steady"},
    )
    fragment_5 = await _ensure_cognitive_fragment(
        session,
        user_id=user.id,
        task_id=user_primary_task.id,
        source_type="behavior",
        resource_type="text",
        content="今晚群里和私聊都走通之后，注意力明显比前几天更稳了。",
        created_at=now - timedelta(hours=4),
        sentiment="positive",
        severity=1,
        tags=["社群", "验收完成感"],
        error_tags=[],
        context_tags={"scene": "post_review", "mood": "relieved"},
    )

    await _ensure_behavior_pattern(
        session,
        user_id=user.id,
        pattern_name="计划谬误",
        pattern_type="cognitive",
        description="你在进入复盘或验收任务前，往往会低估梳理细节所需的时间，导致中途压缩范围。",
        solution_text="开始前先写出“最小可验收闭环”，把时间估计乘以 1.5，再决定是否继续扩展。",
        evidence_ids=[str(fragment_2.id), str(fragment_3.id)],
        confidence_score=0.84,
        frequency=4,
        is_archived=False,
        last_observed_at=now - timedelta(hours=12),
    )
    await _ensure_behavior_pattern(
        session,
        user_id=user.id,
        pattern_name="临时切任务",
        pattern_type="execution",
        description="过去一周你常常在快完成前切去修细节，导致主线进度被打断。",
        solution_text="先把当前页面的成功标准勾完，再去新页面找问题。",
        evidence_ids=[str(fragment_1.id)],
        confidence_score=0.67,
        frequency=3,
        is_archived=True,
        last_observed_at=now - timedelta(days=4),
        last_decay_at=now - timedelta(days=1),
    )

    # Community: seed a richer guest social graph, shared resources, task boards,
    # favorites, and accountability history so the simulator has realistic data.
    friend_specs = [
        dict(
            username="spark_friend_1",
            email="friend1@sparkle.demo",
            nickname="阿泽",
            flame_level=18,
            flame_brightness=0.83,
            depth_preference=0.72,
            curiosity_preference=0.58,
            status=UserStatus.ONLINE,
            match_reason={"courses": ["数据结构", "操作系统"], "scene": "晚间复盘搭子"},
        ),
        dict(
            username="spark_friend_2",
            email="friend2@sparkle.demo",
            nickname="小林",
            flame_level=14,
            flame_brightness=0.74,
            depth_preference=0.61,
            curiosity_preference=0.67,
            status=UserStatus.ONLINE,
            match_reason={"courses": ["离散数学", "算法"], "scene": "题目互改"},
        ),
        dict(
            username="spark_friend_3",
            email="friend3@sparkle.demo",
            nickname="Nora",
            flame_level=20,
            flame_brightness=0.86,
            depth_preference=0.69,
            curiosity_preference=0.79,
            status=UserStatus.ONLINE,
            match_reason={"courses": ["英语", "微反馈"], "scene": "责任伙伴候选"},
        ),
        dict(
            username="spark_friend_4",
            email="friend4@sparkle.demo",
            nickname="Mia",
            flame_level=11,
            flame_brightness=0.66,
            depth_preference=0.52,
            curiosity_preference=0.73,
            status=UserStatus.OFFLINE,
            match_reason={"courses": ["产品设计", "表达"], "scene": "分享任务卡"},
        ),
        dict(
            username="spark_friend_5",
            email="friend5@sparkle.demo",
            nickname="Ethan",
            flame_level=13,
            flame_brightness=0.69,
            depth_preference=0.58,
            curiosity_preference=0.57,
            status=UserStatus.ONLINE,
            match_reason={"courses": ["计算机网络", "系统"], "scene": "资料收藏党"},
        ),
        dict(
            username="spark_friend_6",
            email="friend6@sparkle.demo",
            nickname="苏苏",
            flame_level=9,
            flame_brightness=0.61,
            depth_preference=0.49,
            curiosity_preference=0.81,
            status=UserStatus.OFFLINE,
            match_reason={"courses": ["英语", "共学打卡"], "scene": "晨读搭子"},
        ),
    ]
    pending_specs = [
        dict(
            username="spark_friend_pending_1",
            email="pending1@sparkle.demo",
            nickname="Vega",
            flame_level=10,
            flame_brightness=0.63,
            depth_preference=0.57,
            curiosity_preference=0.62,
            status=UserStatus.ONLINE,
            note="最近在搜集能一起验收社群系统的人",
        ),
    ]

    friends: list[User] = []
    friend_by_name: dict[str, User] = {}
    friendship_by_name: dict[str, Friendship] = {}
    for spec in friend_specs:
        friend = await _ensure_demo_user(session, **{k: spec[k] for k in (
            "username",
            "email",
            "nickname",
            "flame_level",
            "flame_brightness",
            "depth_preference",
            "curiosity_preference",
            "status",
        )})
        friends.append(friend)
        friend_by_name[spec["nickname"]] = friend
        friendship_by_name[spec["nickname"]] = await _ensure_friendship(
            session,
            left_user_id=user.id,
            right_user_id=friend.id,
            initiated_by=user.id,
            status=FriendshipStatus.ACCEPTED,
            match_reason=spec["match_reason"],
        )

    for spec in pending_specs:
        pending_user = await _ensure_demo_user(session, **{k: spec[k] for k in (
            "username",
            "email",
            "nickname",
            "flame_level",
            "flame_brightness",
            "depth_preference",
            "curiosity_preference",
            "status",
        )})
        await _ensure_friendship(
            session,
            left_user_id=user.id,
            right_user_id=pending_user.id,
            initiated_by=pending_user.id,
            status=FriendshipStatus.PENDING,
            match_reason={"intro": spec["note"]},
        )

    aze = friend_by_name["阿泽"]
    xiaolin = friend_by_name["小林"]
    nora = friend_by_name["Nora"]
    mia = friend_by_name["Mia"]
    ethan = friend_by_name["Ethan"]
    susu = friend_by_name["苏苏"]

    friend_learning_profiles = [
        (
            aze,
            dict(
                streak=(8, 21, 38),
                achievements=[
                    ("streak_7", 1.0, 7, 7, now - timedelta(days=14)),
                    ("sprint_first", 1.0, 1, 1, now - timedelta(days=10)),
                ],
                nodes=[
                    ("程序设计基础", 82, 9),
                    ("数据结构", 88, 11),
                    ("算法设计与分析", 76, 7),
                    ("高等数学", 68, 6),
                ],
            ),
        ),
        (
            xiaolin,
            dict(
                streak=(6, 16, 29),
                achievements=[
                    ("streak_7", 1.0, 7, 7, now - timedelta(days=9)),
                    ("night_owl", 1.0, 10, 10, now - timedelta(days=7)),
                ],
                nodes=[
                    ("离散数学", 73, 8),
                    ("算法设计与分析", 79, 9),
                    ("数据结构", 71, 7),
                    ("概率论与数理统计", 58, 5),
                ],
            ),
        ),
        (
            nora,
            dict(
                streak=(11, 25, 52),
                achievements=[
                    ("streak_7", 1.0, 7, 7, now - timedelta(days=18)),
                    ("sprint_first", 1.0, 1, 1, now - timedelta(days=16)),
                ],
                nodes=[
                    ("写作技巧", 74, 7),
                    ("心理学导论", 66, 6),
                    ("学习科学", 72, 8),
                    ("时间管理", 70, 7),
                ],
            ),
        ),
        (
            ethan,
            dict(
                streak=(5, 13, 24),
                achievements=[
                    ("night_owl", 1.0, 10, 10, now - timedelta(days=8)),
                ],
                nodes=[
                    ("计算机网络", 69, 6),
                    ("数据库系统", 64, 6),
                    ("Web后端开发", 55, 4),
                ],
            ),
        ),
        (
            susu,
            dict(
                streak=(9, 15, 33),
                achievements=[
                    ("streak_7", 1.0, 7, 7, now - timedelta(days=12)),
                ],
                nodes=[
                    ("学习科学", 61, 5),
                    ("时间管理", 63, 6),
                    ("写作技巧", 54, 4),
                ],
            ),
        ),
    ]
    for friend, profile in friend_learning_profiles:
        current_streak, max_streak, total_days = profile["streak"]
        await _ensure_user_streak_stats(
            session,
            user_id=friend.id,
            current_streak=current_streak,
            max_streak=max_streak,
            total_checkin_days=total_days,
            last_activity_date=now - timedelta(hours=2),
            longest_streak_start=now - timedelta(days=max_streak + 4),
            longest_streak_end=now - timedelta(days=4),
            freeze_charges=1,
            max_freeze_charges=3,
        )
        for achievement_id, progress, value, target, unlocked_at in profile["achievements"]:
            await _ensure_user_achievement(
                session,
                user_id=friend.id,
                achievement_id=achievement_id,
                progress=progress,
                value=value,
                target=target,
                unlocked_at=unlocked_at,
                is_pinned=True,
            )
        for idx, (node_name, mastery, study_count) in enumerate(profile["nodes"]):
            node = created_nodes.get(node_name)
            if not node:
                continue
            await _ensure_user_node_status(
                session,
                user_id=friend.id,
                node_id=node.id,
                mastery_score=mastery,
                total_study_minutes=study_count * 18,
                study_count=study_count,
                first_unlock_at=now - timedelta(days=18 + idx),
                last_study_at=now - timedelta(hours=8 + idx),
            )

    aze_plan = await _ensure_plan(
        session,
        owner_id=aze.id,
        name="阿泽的树与图复盘计划",
        defaults=dict(
            type=PlanType.SPRINT,
            description="用 5 天完成树、图和堆的高频题回顾。",
            target_date=date.today() + timedelta(days=5),
            daily_available_minutes=80,
            total_estimated_hours=10,
            mastery_level=0.55,
            progress=0.64,
            is_active=True,
        ),
    )
    nora_plan = await _ensure_plan(
        session,
        owner_id=nora.id,
        name="Nora 的口语微反馈计划",
        defaults=dict(
            type=PlanType.GROWTH,
            description="晨读、复述、微反馈三段式练口语。",
            target_date=date.today() + timedelta(days=21),
            daily_available_minutes=45,
            total_estimated_hours=18,
            mastery_level=0.48,
            progress=0.58,
            is_active=True,
        ),
    )
    mia_task = await _ensure_task(
        session,
        owner_id=mia.id,
        title="把任务卡改成更易读的三段结构",
        defaults=dict(
            type=TaskType.LEARNING,
            tags=["Design", "Task Card"],
            estimated_minutes=35,
            difficulty=2,
            energy_cost=2,
            status=TaskStatus.COMPLETED,
            priority=2,
            due_date=date.today() - timedelta(days=1),
            completed_at=now - timedelta(hours=18),
        ),
    )
    susu_task = await _ensure_task(
        session,
        owner_id=susu.id,
        title="英语晨读 shadowing 20 分钟",
        defaults=dict(
            type=TaskType.LEARNING,
            tags=["English", "Speaking"],
            estimated_minutes=20,
            difficulty=2,
            energy_cost=2,
            status=TaskStatus.IN_PROGRESS,
            priority=2,
            due_date=date.today(),
            started_at=now - timedelta(minutes=40),
        ),
    )

    feed_posts = [
        (user, "连续一周打卡成功！今天的专注时间达到了 120 分钟。", "学习分享", 12, 3),
        (user, "刚把微反馈模式在社群里走了一轮，准备继续补收藏和转发链路。", "产品验收", 9, 4),
        (aze, "刚和搭子语音复盘完二叉树遍历，顺手把任务卡也贴进群里了。", "学习心得", 16, 5),
        (xiaolin, "整理了一套图论错题卡，欢迎来算法冲刺小队一起测。", "资源分享", 21, 7),
        (nora, "晨读营今天已经 11 人打卡，微反馈一句话版本挺好用。", "打卡", 13, 2),
        (mia, "把计划卡和任务卡都换成更适合手机阅读的结构啦。", "设计迭代", 8, 3),
        (ethan, "我把几条关键消息收藏了，回头可以顺着收藏页继续验收。", "使用技巧", 7, 1),
    ]
    for post_user, content, topic, likes, comments in feed_posts:
        post_exists = await session.execute(
            select(Post).where(Post.user_id == post_user.id, Post.content == content)
        )
        if not post_exists.scalar_one_or_none():
            session.add(
                Post(
                    user_id=post_user.id,
                    content=content,
                    image_urls=[f"https://picsum.photos/seed/{post_user.username}/600/400"],
                    topic=topic,
                    visibility="public",
                    like_count=likes,
                    comment_count=comments,
                    created_at=now - timedelta(hours=likes),
                    updated_at=now - timedelta(hours=max(likes - 1, 0)),
                )
            )

    algorithm_group = await _ensure_group(
        session,
        name="算法冲刺小队",
        defaults=dict(
            description="一起冲刺算法与数据结构的学习群",
            avatar_url="https://picsum.photos/seed/algosprint/200/200",
            type=GroupType.SPRINT,
            focus_tags=["数据结构", "算法", "期中复习"],
            deadline=now + timedelta(days=10),
            sprint_goal="完成算法专题复习并拿下期中考试",
            max_members=30,
            is_public=True,
            join_requires_approval=False,
            total_flame_power=980,
            today_checkin_count=8,
            total_tasks_completed=24,
            announcement="今晚 20:00 语音复盘 + 微反馈验收。",
        ),
    )
    study_group = await _ensure_group(
        session,
        name="期末自习室",
        defaults=dict(
            description="长期自习陪伴群，适合静默学习、资料收藏和复盘。",
            avatar_url="https://picsum.photos/seed/finalstudy/200/200",
            type=GroupType.SQUAD,
            focus_tags=["自习", "复盘", "资料整理"],
            deadline=None,
            sprint_goal=None,
            max_members=80,
            is_public=True,
            join_requires_approval=False,
            total_flame_power=1640,
            today_checkin_count=14,
            total_tasks_completed=66,
            announcement="收藏值得二次复习的消息，周日晚统一回顾。",
        ),
    )
    english_group = await _ensure_group(
        session,
        name="英语口语晨读营",
        defaults=dict(
            description="口语晨读、shadowing、微反馈快回路。",
            avatar_url="https://picsum.photos/seed/englishclub/200/200",
            type=GroupType.SPRINT,
            focus_tags=["英语", "口语", "晨读"],
            deadline=now + timedelta(days=14),
            sprint_goal="连续 14 天完成晨读与跟读打卡",
            max_members=40,
            is_public=True,
            join_requires_approval=False,
            total_flame_power=760,
            today_checkin_count=11,
            total_tasks_completed=31,
            announcement="今天重点测试任务卡分享和打卡互动。",
        ),
    )
    design_group = await _ensure_group(
        session,
        name="产品设计共学社",
        defaults=dict(
            description="讨论计划卡、任务卡、社群体验和表达设计。",
            avatar_url="https://picsum.photos/seed/designlab/200/200",
            type=GroupType.SQUAD,
            focus_tags=["产品", "设计", "验收"],
            deadline=None,
            sprint_goal=None,
            max_members=60,
            is_public=True,
            join_requires_approval=False,
            total_flame_power=540,
            today_checkin_count=5,
            total_tasks_completed=18,
            announcement="优先看移动端展示是否完整，再看数据结构是否一致。",
        ),
    )
    await _ensure_group(
        session,
        name="考研政治夜航团",
        defaults=dict(
            description="夜间陪伴复习群，适合政治和公共课冲刺。",
            avatar_url="https://picsum.photos/seed/politicsnight/200/200",
            type=GroupType.SPRINT,
            focus_tags=["考研", "政治"],
            deadline=now + timedelta(days=30),
            sprint_goal="完成冲刺背诵",
            max_members=120,
            is_public=True,
            join_requires_approval=False,
            total_flame_power=1320,
            today_checkin_count=27,
            total_tasks_completed=84,
            announcement="新成员可以直接浏览群任务。",
        ),
    )
    await _ensure_group(
        session,
        name="AIGC 创作实验室",
        defaults=dict(
            description="分享 Prompt、计划卡和创作复盘。",
            avatar_url="https://picsum.photos/seed/aigclab/200/200",
            type=GroupType.SQUAD,
            focus_tags=["AI", "创作", "Prompt"],
            deadline=None,
            sprint_goal=None,
            max_members=90,
            is_public=True,
            join_requires_approval=True,
            total_flame_power=1880,
            today_checkin_count=19,
            total_tasks_completed=59,
            announcement="入群前先完成作品集自评表。",
        ),
    )

    for member, role, flame, tasks_completed, streak, joined_delta in [
        (user, GroupRole.OWNER, 210, 9, 7, 28),
        (aze, GroupRole.ADMIN, 160, 8, 6, 27),
        (xiaolin, GroupRole.MEMBER, 120, 5, 4, 20),
        (nora, GroupRole.MEMBER, 96, 4, 5, 16),
    ]:
        await _ensure_group_member(
            session,
            group_id=algorithm_group.id,
            member_id=member.id,
            role=role,
            flame_contribution=flame,
            tasks_completed=tasks_completed,
            checkin_streak=streak,
            last_checkin_date=now - timedelta(hours=6),
            joined_at=now - timedelta(days=joined_delta),
        )
    for member, role, flame, tasks_completed, streak, joined_delta in [
        (user, GroupRole.ADMIN, 155, 6, 5, 34),
        (aze, GroupRole.MEMBER, 110, 4, 3, 30),
        (mia, GroupRole.MEMBER, 88, 2, 2, 18),
        (ethan, GroupRole.OWNER, 132, 6, 6, 40),
    ]:
        await _ensure_group_member(
            session,
            group_id=study_group.id,
            member_id=member.id,
            role=role,
            flame_contribution=flame,
            tasks_completed=tasks_completed,
            checkin_streak=streak,
            last_checkin_date=now - timedelta(hours=12),
            joined_at=now - timedelta(days=joined_delta),
        )
    for member, role, flame, tasks_completed, streak, joined_delta in [
        (user, GroupRole.MEMBER, 92, 3, 4, 12),
        (nora, GroupRole.OWNER, 168, 8, 11, 25),
        (susu, GroupRole.ADMIN, 121, 6, 9, 22),
        (mia, GroupRole.MEMBER, 80, 2, 3, 11),
    ]:
        await _ensure_group_member(
            session,
            group_id=english_group.id,
            member_id=member.id,
            role=role,
            flame_contribution=flame,
            tasks_completed=tasks_completed,
            checkin_streak=streak,
            last_checkin_date=now - timedelta(hours=3),
            joined_at=now - timedelta(days=joined_delta),
        )
    for member, role, flame, tasks_completed, streak, joined_delta in [
        (user, GroupRole.MEMBER, 74, 3, 2, 15),
        (mia, GroupRole.OWNER, 140, 7, 5, 31),
        (ethan, GroupRole.ADMIN, 108, 4, 3, 26),
        (susu, GroupRole.MEMBER, 66, 2, 2, 14),
    ]:
        await _ensure_group_member(
            session,
            group_id=design_group.id,
            member_id=member.id,
            role=role,
            flame_contribution=flame,
            tasks_completed=tasks_completed,
            checkin_streak=streak,
            last_checkin_date=now - timedelta(days=1),
            joined_at=now - timedelta(days=joined_delta),
        )

    shared_algo_task = await _ensure_shared_resource(
        session,
        shared_by=mia.id,
        group_id=algorithm_group.id,
        task_id=mia_task.id,
        comment="这张任务卡适合测试分享和采纳。",
    )
    shared_algo_plan = await _ensure_shared_resource(
        session,
        shared_by=aze.id,
        group_id=algorithm_group.id,
        plan_id=aze_plan.id,
        comment="计划卡里有每日节奏，可以直接验收。",
    )
    shared_private_plan = await _ensure_shared_resource(
        session,
        shared_by=nora.id,
        target_user_id=user.id,
        plan_id=nora_plan.id,
        comment="你可以拿这个计划卡测私聊分享。",
    )
    shared_private_task = await _ensure_shared_resource(
        session,
        shared_by=susu.id,
        target_user_id=user.id,
        task_id=susu_task.id,
        comment="这个晨读任务卡也能测采纳。",
    )

    algo_msg_1 = await _ensure_group_message(
        session,
        group_id=algorithm_group.id,
        sender_id=aze.id,
        message_type=MessageType.TEXT,
        content="今晚 20:00 一起复盘二叉树遍历？我想顺手把微反馈流程也走一遍。",
        created_at=now - timedelta(hours=5),
    )
    algo_msg_2 = await _ensure_group_message(
        session,
        group_id=algorithm_group.id,
        sender_id=user.id,
        message_type=MessageType.TEXT,
        content="可以，我正好要测社群里的任务卡、计划卡、收藏和转发。",
        created_at=now - timedelta(hours=4, minutes=46),
        reply_to_id=algo_msg_1.id,
        thread_root_id=algo_msg_1.id,
    )
    algo_msg_3 = await _ensure_group_message(
        session,
        group_id=algorithm_group.id,
        sender_id=mia.id,
        message_type=MessageType.TASK_SHARE,
        content="我先把任务卡发出来，你们直接在群里看展示效果。",
        created_at=now - timedelta(hours=4, minutes=28),
        content_data={
            "resource_type": "task",
            "resource_id": str(mia_task.id),
            "shared_resource_id": str(shared_algo_task.id),
            "resource_title": mia_task.title,
            "resource_summary": "一张适合验证任务卡标题、摘要、采纳按钮是否正常展示的示例。",
            "resource_meta": {
                "estimated_minutes": mia_task.estimated_minutes,
                "completed_at": mia_task.completed_at.isoformat() if mia_task.completed_at else None,
            },
            "comment": "这张任务卡适合测试分享和采纳。",
        },
    )
    algo_msg_4 = await _ensure_group_message(
        session,
        group_id=algorithm_group.id,
        sender_id=aze.id,
        message_type=MessageType.PLAN_SHARE,
        content="再补一张计划卡，方便你一起测。",
        created_at=now - timedelta(hours=4, minutes=10),
        content_data={
            "resource_type": "plan",
            "resource_id": str(aze_plan.id),
            "shared_resource_id": str(shared_algo_plan.id),
            "resource_title": aze_plan.name,
            "resource_summary": aze_plan.description,
            "resource_meta": {
                "progress": 0.64,
                "target_date": datetime.combine(aze_plan.target_date, datetime.min.time()).isoformat()
                if aze_plan.target_date
                else None,
            },
            "comment": "计划卡里有每日节奏，可以直接验收。",
        },
    )
    algo_msg_5 = await _ensure_group_message(
        session,
        group_id=algorithm_group.id,
        sender_id=nora.id,
        message_type=MessageType.CHECKIN,
        content="完成今日算法打卡，刚把 DFS/BFS 题单刷完。",
        created_at=now - timedelta(hours=3, minutes=52),
        content_data={"flame_power": 118, "today_duration": 95, "streak": 6},
    )
    algo_msg_6 = await _ensure_group_message(
        session,
        group_id=algorithm_group.id,
        sender_id=aze.id,
        message_type=MessageType.TEXT,
        content="刚刚和你语音把微反馈流程过了一遍，聊天、收藏、转发、任务卡入口都能找到了。",
        created_at=now - timedelta(hours=3, minutes=35),
        reactions={"🔥": [str(user.id), str(xiaolin.id)]},
    )
    algo_msg_7 = await _ensure_group_message(
        session,
        group_id=algorithm_group.id,
        sender_id=xiaolin.id,
        message_type=MessageType.TEXT,
        content="我把上一条先收藏了，等会你再试试从群里转发到私聊。",
        created_at=now - timedelta(hours=3, minutes=20),
        reply_to_id=algo_msg_6.id,
        thread_root_id=algo_msg_6.id,
    )

    study_msg_1 = await _ensure_group_message(
        session,
        group_id=study_group.id,
        sender_id=ethan.id,
        message_type=MessageType.TEXT,
        content="自习室今天先别刷太快，把值得回看的消息收藏起来，验收会更顺。",
        created_at=now - timedelta(days=1, hours=2),
    )
    study_msg_2 = await _ensure_group_message(
        session,
        group_id=study_group.id,
        sender_id=aze.id,
        message_type=MessageType.CAPSULE_SHARE,
        content="这条胶囊适合在收藏和二次分享链路里测试。",
        created_at=now - timedelta(days=1, hours=1, minutes=40),
        content_data={
            "resource_type": "curiosity_capsule",
            "resource_id": str(capsule_ids[1]),
            "resource_title": "进程和线程的本质区别是什么？",
            "resource_summary": "进程是资源容器，线程是执行轨迹，这条内容很适合收藏回看。",
            "resource_meta": {"related_subject": "操作系统"},
            "comment": "收藏后再打开看看预览是否完整。",
        },
    )
    study_msg_3 = await _ensure_group_message(
        session,
        group_id=study_group.id,
        sender_id=mia.id,
        message_type=MessageType.PRISM_SHARE,
        content="我把一个认知棱镜放进来了，想看下卡片样式会不会挤。",
        created_at=now - timedelta(days=1, hours=1, minutes=20),
        content_data={
            "resource_type": "cognitive_prism_pattern",
            "resource_title": "计划谬误",
            "resource_summary": "容易低估任务复杂度，导致计划卡看起来很乐观。",
            "resource_meta": {"severity": 3, "source": "self_review"},
            "comment": "这里也能顺手测一下富文本气泡。",
        },
    )

    english_msg_1 = await _ensure_group_message(
        session,
        group_id=english_group.id,
        sender_id=nora.id,
        message_type=MessageType.TEXT,
        content="晨读营今天重点看微反馈是不是足够轻，别把打卡流程做重了。",
        created_at=now - timedelta(hours=9),
    )
    english_msg_2 = await _ensure_group_message(
        session,
        group_id=english_group.id,
        sender_id=susu.id,
        message_type=MessageType.CHECKIN,
        content="shadowing 20 分钟完成，今天状态不错。",
        created_at=now - timedelta(hours=8, minutes=42),
        content_data={"flame_power": 96, "today_duration": 20, "streak": 9},
    )
    english_msg_3 = await _ensure_group_message(
        session,
        group_id=english_group.id,
        sender_id=nora.id,
        message_type=MessageType.PLAN_SHARE,
        content="我把口语计划卡贴这里，方便你测群分享。",
        created_at=now - timedelta(hours=8, minutes=30),
        content_data={
            "resource_type": "plan",
            "resource_id": str(nora_plan.id),
            "shared_resource_id": str(shared_private_plan.id),
            "resource_title": nora_plan.name,
            "resource_summary": nora_plan.description,
            "resource_meta": {
                "progress": 0.58,
                "target_date": datetime.combine(nora_plan.target_date, datetime.min.time()).isoformat()
                if nora_plan.target_date
                else None,
            },
            "comment": "群里和私聊里都可以对着这张卡验收。",
        },
    )

    design_msg_1 = await _ensure_group_message(
        session,
        group_id=design_group.id,
        sender_id=mia.id,
        message_type=MessageType.TEXT,
        content="我把计划卡和任务卡的文案层级重新排了下，移动端看起来会更稳。",
        created_at=now - timedelta(days=2, hours=4),
    )
    design_msg_2 = await _ensure_group_message(
        session,
        group_id=design_group.id,
        sender_id=ethan.id,
        message_type=MessageType.FRAGMENT_SHARE,
        content="这条认知碎片可以帮你测分享卡的轻量信息密度。",
        created_at=now - timedelta(days=2, hours=3, minutes=25),
        content_data={
            "resource_type": "cognitive_fragment",
            "resource_title": "验收时先看入口，再看状态一致性",
            "resource_summary": "别一上来就盯细节，先确认全链路能进、能看、能回。",
            "resource_meta": {"source_type": "review", "severity": 1},
            "comment": "这条更适合看信息卡折叠后的效果。",
        },
    )
    await _ensure_group_message(
        session,
        group_id=study_group.id,
        sender_id=user.id,
        message_type=MessageType.TEXT,
        content="我把算法群里那条“语音复盘 + 微反馈”说明转到自习室，顺手测一下群内转发展示。",
        created_at=now - timedelta(hours=2, minutes=45),
        forwarded_from_id=algo_msg_6.id,
    )

    for message, readers in [
        (algo_msg_6, [user.id, xiaolin.id, nora.id]),
        (algo_msg_7, [user.id, aze.id]),
        (english_msg_3, [user.id, susu.id]),
    ]:
        for idx, reader_id in enumerate(readers):
            await _ensure_group_message_read(
                session,
                message_id=message.id,
                user_id=reader_id,
                read_at=message.created_at + timedelta(minutes=idx + 1),
            )

    algo_task_1 = await _ensure_group_task(
        session,
        group_id=algorithm_group.id,
        created_by=aze.id,
        title="把二叉树前中后序都手写一遍",
        defaults=dict(
            description="用于检查群任务列表、认领按钮和完成状态展示。",
            tags=["二叉树", "高频题"],
            estimated_minutes=40,
            difficulty=3,
            total_claims=3,
            total_completions=1,
            due_date=now + timedelta(days=1),
        ),
    )
    algo_task_2 = await _ensure_group_task(
        session,
        group_id=algorithm_group.id,
        created_by=xiaolin.id,
        title="把最近 5 条错题做成分享任务卡",
        defaults=dict(
            description="验收任务卡分享后，顺手看群任务池刷新是否正常。",
            tags=["错题整理", "分享"],
            estimated_minutes=25,
            difficulty=2,
            total_claims=2,
            total_completions=0,
            due_date=now + timedelta(days=2),
        ),
    )
    english_task_1 = await _ensure_group_task(
        session,
        group_id=english_group.id,
        created_by=susu.id,
        title="shadowing 15 分钟并发一句微反馈",
        defaults=dict(
            description="用来验证打卡和任务卡之间的节奏衔接。",
            tags=["晨读", "微反馈"],
            estimated_minutes=15,
            difficulty=2,
            total_claims=4,
            total_completions=2,
            due_date=now + timedelta(days=1),
        ),
    )
    await _ensure_group_task_claim(
        session,
        group_task_id=algo_task_1.id,
        user_id=user.id,
        personal_task_id=user_primary_task.id,
        is_completed=False,
        claimed_at=now - timedelta(hours=4),
    )
    await _ensure_group_task_claim(
        session,
        group_task_id=algo_task_1.id,
        user_id=aze.id,
        is_completed=True,
        completed_at=now - timedelta(hours=2),
        claimed_at=now - timedelta(days=1),
    )
    await _ensure_group_task_claim(
        session,
        group_task_id=algo_task_2.id,
        user_id=xiaolin.id,
        is_completed=False,
        claimed_at=now - timedelta(hours=6),
    )
    await _ensure_group_task_claim(
        session,
        group_task_id=english_task_1.id,
        user_id=user.id,
        personal_task_id=user_network_task.id,
        is_completed=True,
        completed_at=now - timedelta(hours=7),
        claimed_at=now - timedelta(hours=10),
    )

    private_aze_1 = await _ensure_private_message(
        session,
        sender_id=aze.id,
        receiver_id=user.id,
        message_type=MessageType.TEXT,
        content="刚刚语音里那套微反馈流程我又顺了一遍，好友页、私聊页、群聊页都能进。",
        created_at=now - timedelta(hours=6, minutes=10),
        is_read=True,
        read_at=now - timedelta(hours=6),
    )
    await _ensure_private_message(
        session,
        sender_id=user.id,
        receiver_id=aze.id,
        message_type=MessageType.TEXT,
        content="太好了，我主要担心访客模式的数据太薄，今天终于能像真实用户一样验收了。",
        created_at=now - timedelta(hours=5, minutes=55),
        is_read=True,
        read_at=now - timedelta(hours=5, minutes=40),
        reply_to_id=private_aze_1.id,
        thread_root_id=private_aze_1.id,
    )
    private_aze_3 = await _ensure_private_message(
        session,
        sender_id=aze.id,
        receiver_id=user.id,
        message_type=MessageType.TEXT,
        content="我已经把那条关键消息收藏了，你待会可以直接去收藏页看预览和备注。",
        created_at=now - timedelta(hours=5, minutes=20),
        is_read=True,
        read_at=now - timedelta(hours=5, minutes=10),
        reactions={"✅": [str(user.id)]},
    )
    await _ensure_private_message(
        session,
        sender_id=nora.id,
        receiver_id=user.id,
        message_type=MessageType.PLAN_SHARE,
        content="这张口语计划卡也发你一份，私聊分享链路可以直接测。",
        created_at=now - timedelta(hours=4, minutes=45),
        content_data={
            "resource_type": "plan",
            "resource_id": str(nora_plan.id),
            "shared_resource_id": str(shared_private_plan.id),
            "resource_title": nora_plan.name,
            "resource_summary": nora_plan.description,
            "resource_meta": {
                "progress": 0.58,
                "target_date": datetime.combine(nora_plan.target_date, datetime.min.time()).isoformat()
                if nora_plan.target_date
                else None,
            },
            "comment": "你从这里点开会更快。",
        },
        is_read=False,
    )
    await _ensure_private_message(
        session,
        sender_id=susu.id,
        receiver_id=user.id,
        message_type=MessageType.TASK_SHARE,
        content="晨读任务卡给你，看看私聊里的分享卡会不会压行。",
        created_at=now - timedelta(hours=3, minutes=35),
        content_data={
            "resource_type": "task",
            "resource_id": str(susu_task.id),
            "shared_resource_id": str(shared_private_task.id),
            "resource_title": susu_task.title,
            "resource_summary": "轻量任务卡，适合看私聊里的折叠布局。",
            "resource_meta": {"estimated_minutes": susu_task.estimated_minutes},
            "comment": "也能顺手测采纳。",
        },
        is_read=False,
    )
    await _ensure_private_message(
        session,
        sender_id=ethan.id,
        receiver_id=user.id,
        message_type=MessageType.TEXT,
        content="我把群里那条'语音复盘 + 微反馈'消息加了标签，收藏页应该能看到了。",
        created_at=now - timedelta(days=1, hours=4),
        is_read=True,
        read_at=now - timedelta(days=1, hours=3, minutes=40),
    )
    await _ensure_private_message(
        session,
        sender_id=mia.id,
        receiver_id=user.id,
        message_type=MessageType.TEXT,
        content="任务卡标题、摘要、按钮层级我都压缩过，移动端展示应该更稳。",
        created_at=now - timedelta(days=2, hours=1),
        is_read=True,
        read_at=now - timedelta(days=2, minutes=40),
    )
    await _ensure_private_message(
        session,
        sender_id=user.id,
        receiver_id=aze.id,
        message_type=MessageType.TEXT,
        content="我把你刚才那条收藏说明也转存一下，测试私聊内转发预览。",
        created_at=now - timedelta(hours=2, minutes=5),
        is_read=True,
        read_at=now - timedelta(hours=1, minutes=58),
        forwarded_from_id=private_aze_3.id,
    )

    await _ensure_message_favorite(
        session,
        user_id=user.id,
        group_message_id=algo_msg_6.id,
        note="验收用：语音复盘 + 微反馈全链路说明",
        tags=["验收", "微反馈", "群聊"],
    )
    await _ensure_message_favorite(
        session,
        user_id=user.id,
        private_message_id=private_aze_3.id,
        note="收藏页要能看到备注和发送人",
        tags=["收藏", "私聊"],
    )

    active_partnership = await _ensure_partnership(
        session,
        initiator_id=user.id,
        partner_id=aze.id,
        friendship_id=friendship_by_name["阿泽"].id,
        initiator_goal="连续 14 天完成算法复盘并记录微反馈。",
        partner_goal="每天晚上一起复盘 20 分钟，互相提醒打卡。",
        check_in_days=1,
        status=AccountabilityStatus.ACTIVE,
        started_at=now - timedelta(days=12),
    )
    await _ensure_partnership(
        session,
        initiator_id=nora.id,
        partner_id=user.id,
        friendship_id=friendship_by_name["Nora"].id,
        initiator_goal="一起把英语晨读和口语微反馈坚持 10 天。",
        partner_goal=None,
        check_in_days=1,
        status=AccountabilityStatus.ENDED,
        started_at=now - timedelta(days=24),
        ended_at=now - timedelta(days=16),
    )

    accountability_timeline = [
        (
            user.id,
            "今天把群聊里的任务卡、计划卡、收藏入口都走通了。",
            4,
            75,
            now - timedelta(days=4, hours=2),
            1,
            [str(aze.id)],
            [{"id": str(uuid.uuid4()), "user_id": str(aze.id), "message": "这条写得很清楚，继续保持。", "created_at": (now - timedelta(days=4, hours=1, minutes=40)).isoformat()}],
        ),
        (
            aze.id,
            "晚上的语音复盘把微反馈入口重新确认了一遍。",
            5,
            40,
            now - timedelta(days=3, hours=20),
            1,
            [str(user.id)],
            [{"id": str(uuid.uuid4()), "user_id": str(user.id), "message": "收到，明天我再测一次收藏页。", "created_at": (now - timedelta(days=3, hours=19, minutes=45)).isoformat()}],
        ),
        (
            user.id,
            "今天重点测了私聊分享计划卡，卡片展示正常。",
            4,
            55,
            now - timedelta(days=2, hours=3),
            1,
            [str(aze.id)],
            [],
        ),
        (
            aze.id,
            "帮你把群任务认领按钮也点了一遍，没有卡死。",
            5,
            35,
            now - timedelta(days=1, hours=5),
            0,
            [],
            [{"id": str(uuid.uuid4()), "user_id": str(user.id), "message": "太关键了，这样我明天能继续验收任务池。", "created_at": (now - timedelta(days=1, hours=4, minutes=50)).isoformat()}],
        ),
    ]
    for actor_id, content, mood, minutes, created_at, likes, liked_by, encouragements in accountability_timeline:
        await _ensure_accountability_checkin(
            session,
            partnership_id=active_partnership.id,
            user_id=actor_id,
            content=content,
            mood=mood,
            minutes=minutes,
            created_at=created_at,
            likes=likes,
            liked_by=liked_by,
            encouragements=encouragements,
        )

    reminder_notification = await _ensure_notification(
        session,
        user_id=user.id,
        title="责任伙伴提醒",
        content="阿泽刚完成今晚复盘，等你补一句微反馈并打卡。",
        notification_type="reminder",
        created_at=now - timedelta(minutes=45),
        is_read=False,
        data={
            "partnership_id": str(active_partnership.id),
            "group_id": str(algorithm_group.id),
            "message_id": str(algo_msg_6.id),
        },
    )
    favorite_notification = await _ensure_notification(
        session,
        user_id=user.id,
        title="收藏夹已更新",
        content="你收藏的 2 条关键消息现在可以从收藏页继续回看和删除。",
        notification_type="system",
        created_at=now - timedelta(hours=3, minutes=15),
        is_read=True,
        read_at=now - timedelta(hours=2, minutes=58),
        data={
            "favorite_count": 2,
            "route": "/community/favorites",
            "latest_message_id": str(private_aze_3.id),
        },
    )
    task_notification = await _ensure_notification(
        session,
        user_id=user.id,
        title="群任务进度有更新",
        content="英语口语晨读营里你认领的任务已记录为完成，可继续验收群任务池刷新。",
        notification_type="task",
        created_at=now - timedelta(hours=6, minutes=20),
        is_read=True,
        read_at=now - timedelta(hours=6, minutes=2),
        data={
            "group_id": str(english_group.id),
            "group_task_id": str(english_task_1.id),
            "task_id": str(user_network_task.id),
        },
    )
    achievement_notification = await _ensure_notification(
        session,
        user_id=user.id,
        title="连胜火苗仍在延续",
        content="你已连续 7 天保持活跃，粒子装扮“连胜余烬”已可使用。",
        notification_type="achievement",
        created_at=now - timedelta(days=1, hours=1),
        is_read=True,
        read_at=now - timedelta(days=1, minutes=40),
        data={
            "achievement_id": "streak_7",
            "unlocked_element_id": "particle_streak_embers",
        },
    )
    await _ensure_notification_preferences(
        session,
        user_id=user.id,
        enable_system=True,
        enable_interventions=True,
        notification_level="focused",
        quiet_hours_enabled=True,
        quiet_hours_start="23:30",
        quiet_hours_end="07:30",
        updated_at=now - timedelta(hours=2),
    )
    for notification, action_type, action_time in [
        (favorite_notification, "viewed", now - timedelta(hours=2, minutes=58)),
        (favorite_notification, "clicked", now - timedelta(hours=2, minutes=54)),
        (task_notification, "viewed", now - timedelta(hours=6, minutes=2)),
        (achievement_notification, "viewed", now - timedelta(days=1, minutes=40)),
        (achievement_notification, "clicked", now - timedelta(days=1, minutes=35)),
    ]:
        await _ensure_notification_interaction(
            session,
            user_id=user.id,
            notification_type="system",
            notification_id=notification.id,
            action_type=action_type,
            action_time=action_time,
            time_to_action=max(int((action_time - notification.created_at).total_seconds()), 0),
        )

    await _ensure_intervention_settings(
        session,
        user_id=user.id,
        interrupt_threshold=0.62,
        daily_interrupt_budget=3,
        cooldown_minutes=90,
        quiet_hours={"start": "23:30", "end": "07:30"},
        topic_allowlist=["focus", "accountability", "review"],
        topic_blocklist=["marketing"],
        do_not_disturb=False,
    )
    pending_intervention = await _ensure_intervention_request(
        session,
        user_id=user.id,
        dedupe_key="guest-demo-focus-reset",
        topic="专注状态提醒",
        requested_level="card",
        final_level="card",
        status="pending",
        reason={
            "signal": "context_switch",
            "recent_focus_interruptions": 2,
            "scene": "community_acceptance",
        },
        content={
            "message": "你已经在 30 分钟内来回切了 3 个验收入口，先把当前闭环收口再扩展。",
            "suggested_action": "先完成收藏页验收",
        },
        cooldown_policy={"minutes": 90, "scope": "focus"},
        delivery_method="in_app",
        template_id="focus_reset_card",
        template_variant_id="guest_demo_v2",
        scaffolding_level=2,
        intent_type="focus_reset",
        schema_version="v1",
        policy_version="2026-03",
        model_version="demo-seed",
        expires_at=now + timedelta(hours=2),
        is_retractable=True,
        created_at=now - timedelta(minutes=30),
    )
    approved_intervention = await _ensure_intervention_request(
        session,
        user_id=user.id,
        dedupe_key="guest-demo-accountability-nudge",
        topic="责任伙伴助推",
        requested_level="modal",
        final_level="card",
        status="approved",
        reason={
            "signal": "checkin_gap",
            "hours_since_last_checkin": 22,
            "partnership_id": str(active_partnership.id),
        },
        content={
            "message": "距离你和阿泽的上一次互评已经接近一天，发一句微反馈就能保持节奏。",
            "cta": "去责任伙伴页",
        },
        cooldown_policy={"minutes": 180, "scope": "accountability"},
        delivery_method="in_app",
        template_id="accountability_prompt",
        template_variant_id="micro_feedback_short",
        scaffolding_level=1,
        intent_type="accountability_nudge",
        schema_version="v1",
        policy_version="2026-03",
        model_version="demo-seed",
        expires_at=now + timedelta(days=1),
        is_retractable=True,
        created_at=now - timedelta(hours=5, minutes=10),
    )
    await _ensure_intervention_audit(
        session,
        request_id=pending_intervention.id,
        user_id=user.id,
        action="created",
        guardrail_result={"allowed": True, "risk_level": "low"},
        decision_trace={"source": "guest_seed", "variant": "focus_reset_card"},
        evidence_refs=[str(fragment_1.id), str(fragment_3.id)],
        requested_level="card",
        final_level="card",
        policy_version="2026-03",
        model_version="demo-seed",
        schema_version="v1",
        occurred_at=now - timedelta(minutes=30),
    )
    await _ensure_intervention_audit(
        session,
        request_id=approved_intervention.id,
        user_id=user.id,
        action="approved",
        guardrail_result={"allowed": True, "risk_level": "low"},
        decision_trace={"source": "guest_seed", "variant": "micro_feedback_short"},
        evidence_refs=[str(fragment_4.id)],
        requested_level="modal",
        final_level="card",
        policy_version="2026-03",
        model_version="demo-seed",
        schema_version="v1",
        occurred_at=now - timedelta(hours=5, minutes=9),
    )
    await _ensure_intervention_feedback(
        session,
        request_id=approved_intervention.id,
        user_id=user.id,
        feedback_type="accepted",
        extra_data={"action": "opened_accountability_detail"},
        idempotency_key="guest-demo-accountability-accepted",
        created_at=now - timedelta(hours=4, minutes=48),
    )
    await _ensure_notification_interaction(
        session,
        user_id=user.id,
        notification_type="intervention",
        notification_id=approved_intervention.id,
        action_type="clicked",
        action_time=now - timedelta(hours=4, minutes=48),
        time_to_action=max(int((now - timedelta(hours=4, minutes=48) - approved_intervention.created_at).total_seconds()), 0),
    )

    await session.flush()

    # Chat session + history
    chat_session = (await session.execute(
        select(ChatSession).where(
            ChatSession.user_id == user.id,
            ChatSession.title == "关于数学复习的建议",
        )
    )).scalar_one_or_none()
    if not chat_session:
        chat_session = ChatSession(
            user_id=user.id,
            title="关于数学复习的建议",
            is_active=True,
            last_message_at=now - timedelta(hours=1),
        )
        session.add(chat_session)
        await session.flush()

    msg_count = await session.scalar(
        select(func.count(ChatMessage.id)).where(
            ChatMessage.user_id == user.id,
            ChatMessage.session_id == chat_session.id,
        )
    )
    if not msg_count:
        session.add_all([
            ChatMessage(
                user_id=user.id,
                session_id=chat_session.id,
                role=MessageRole.USER,
                content="我觉得最近学习效率有点低，总是忍不住想玩手机，怎么办？",
            ),
            ChatMessage(
                user_id=user.id,
                session_id=chat_session.id,
                role=MessageRole.ASSISTANT,
                content="理解你的感受。这种焦虑和自责其实是恶性循环的一部分。可以从一个小任务开始找回节奏，比如先把二叉树遍历的代码手写一遍，15分钟完成，给自己一个小成就感。",
            ),
            ChatMessage(
                user_id=user.id,
                session_id=chat_session.id,
                role=MessageRole.USER,
                content="确实，那我先复习一下链表吧，但是我有点忘了怎么实现了。",
            ),
        ])
        chat_session.last_message_at = now

    await session.flush()
    logger.info(f"Guest data seeded for user_id={user.id} username={user.username}")
