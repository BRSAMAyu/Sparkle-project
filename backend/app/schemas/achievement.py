"""Achievement Schemas - Achievement system request/response models"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.achievement import AchievementRarity, AchievementType, ContractStatus, VisualEffectType
from app.schemas.common import BaseSchema

# ========== Achievement Schemas ==========


class AchievementBase(BaseSchema):
    """Achievement basic information"""

    id: str = Field(description="Achievement ID")
    name: str = Field(description="Achievement name")
    description: str | None = Field(default=None, description="Achievement description")
    icon_url: str | None = Field(default=None, description="Icon URL")
    type: AchievementType = Field(description="Achievement type")
    rarity: AchievementRarity = Field(description="Achievement rarity")
    category: str | None = Field(default=None, description="Category for grouping")
    is_hidden: bool = Field(default=False, description="Is hidden achievement")
    hint: str | None = Field(default=None, description="Hint for hidden achievement")
    sort_order: int = Field(default=0, description="Display order")
    parent_id: str | None = Field(default=None, description="Parent achievement ID")
    active_from: datetime | None = Field(default=None, description="Active start time (UTC)")
    active_to: datetime | None = Field(default=None, description="Active end time (UTC)")
    is_limited: bool = Field(default=False, description="Is limited-time achievement")
    event_tag: str | None = Field(default=None, description="Event tag for limited-time achievements")


class AchievementDetail(AchievementBase):
    """Achievement detailed information"""

    trigger_code: str = Field(description="Trigger code")
    trigger_config: dict[str, Any] | None = Field(default=None, description="Trigger config")
    prerequisites: list[str] | None = Field(default=None, description="Prerequisite achievement IDs")
    visual_effect_type: VisualEffectType = Field(description="Visual effect type")
    visual_config: dict[str, Any] | None = Field(default=None, description="Visual config")
    reward_config: list[dict[str, Any]] | None = Field(default=None, description="Reward config")
    total_unlocked: int = Field(default=0, description="Total unlocked count")


class UserAchievementBase(BaseModel):
    """User achievement basic information"""

    achievement_id: str = Field(description="Achievement ID")
    progress: float = Field(default=0.0, description="Progress 0.0-1.0")
    progress_value: int = Field(default=0, description="Current value")
    progress_target: int = Field(default=1, description="Target value")
    is_pinned: bool = Field(default=False, description="Is pinned")


class UserAchievementDetail(UserAchievementBase):
    """User achievement detailed information"""

    user_id: UUID = Field(description="User ID")
    unlocked_at: datetime | None = Field(default=None, description="Unlocked time")
    share_count: int = Field(default=0, description="Share count")
    is_first_unlocker: bool = Field(default=False, description="Is first unlocker")
    last_progress_update: datetime | None = Field(default=None, description="Last progress update")
    context_snapshot: dict[str, Any] | None = Field(default=None, description="Context captured when unlocked")
    context_story: str | None = Field(default=None, description="Personalized unlock context story")


class UserAchievementProgressPayload(UserAchievementBase):
    """User achievement progress payload for nested achievement responses"""

    unlocked_at: datetime | None = Field(default=None, description="Unlocked time")
    share_count: int = Field(default=0, description="Share count")
    is_first_unlocker: bool = Field(default=False, description="Is first unlocker")
    last_progress_update: datetime | None = Field(default=None, description="Last progress update")
    context_snapshot: dict[str, Any] | None = Field(default=None, description="Context captured when unlocked")
    context_story: str | None = Field(default=None, description="Personalized unlock context story")


class AchievementWithProgress(BaseModel):
    """Achievement with user progress"""

    achievement: AchievementDetail = Field(description="Achievement info")
    user_progress: UserAchievementProgressPayload | None = Field(default=None, description="User progress")
    is_unlocked: bool = Field(default=False, description="Is unlocked")
    progress_percentage: int = Field(default=0, description="Progress percentage")


class AchievementListResponse(BaseModel):
    """Achievement list response"""

    data: list[AchievementWithProgress] = Field(default_factory=list, description="Achievement list")
    meta: dict[str, Any] = Field(default_factory=dict, description="Metadata like categories, stats")


class CloseToUnlockAchievementListResponse(BaseModel):
    """Close-to-unlock achievement list response"""

    data: list[AchievementWithProgress] = Field(default_factory=list, description="Achievement list")
    count: int = Field(default=0, description="Achievement count")


class AchievementDetailResponse(BaseModel):
    """Achievement detail response"""

    data: AchievementDetail = Field(description="Achievement detail")
    is_unlocked: bool = Field(default=False, description="Whether the user has unlocked the achievement")
    user_progress: UserAchievementProgressPayload | None = Field(default=None, description="User progress")
    context_snapshot: dict[str, Any] | None = Field(default=None, description="Context captured when unlocked")
    context_story: str | None = Field(default=None, description="Personalized unlock context story")


class AchievementMapNode(BaseModel):
    """Achievement map node for visualization"""

    id: str = Field(description="Achievement ID")
    name: str = Field(description="Achievement name")
    rarity: AchievementRarity = Field(description="Achievement rarity")
    category: str = Field(description="Category")
    lane: str = Field(default="prestige_lane", description="Prestige lane identifier")
    lane_label: str = Field(default="声望进阶线", description="Prestige lane label")
    position: dict[str, float] = Field(description="Position {x, y}")
    is_unlocked: bool = Field(default=False, description="Is unlocked")
    is_hidden: bool = Field(default=False, description="Is hidden")
    prerequisites: list[str] = Field(default_factory=list, description="Prerequisites")
    parent_id: str | None = Field(default=None, description="Parent achievement ID")
    display_state: str = Field(
        default="blocked", description="unlocked | ready_to_pursue | close_to_unlock | blocked | hidden_unrevealed"
    )
    is_recommended_target: bool = Field(default=False, description="Is the current best next target")
    reward_preview: list[str] = Field(default_factory=list, description="Reward summary for the node")
    progress_percentage: int = Field(default=0, description="User progress percentage")
    progress_value: int = Field(default=0, description="User progress current value")
    progress_target: int = Field(default=1, description="User progress target value")
    unlock_hint: str | None = Field(default=None, description="What the user still needs to do")


class AchievementMapResponse(BaseModel):
    """Achievement map response"""

    nodes: list[AchievementMapNode] = Field(default_factory=list, description="Map nodes")
    connections: list[dict[str, Any]] = Field(default_factory=list, description="Connections")
    categories: list[dict[str, Any]] = Field(default_factory=list, description="Categories")


# ========== Streak Schemas ==========


class StreakStatsResponse(BaseModel):
    """User streak statistics"""

    current_streak: int = Field(default=0, description="Current streak days")
    max_streak: int = Field(default=0, description="Maximum streak")
    longest_streak: int = Field(default=0, description="Longest streak record")
    last_activity_date: datetime | None = Field(default=None, description="Last activity date")
    freeze_charges: int = Field(default=0, description="Available freeze charges")
    max_freeze_charges: int = Field(default=3, description="Maximum freeze charges")
    total_checkin_days: int = Field(default=0, description="Total check-in days")
    longest_streak_start: datetime | None = Field(default=None, description="Longest streak start")
    longest_streak_end: datetime | None = Field(default=None, description="Longest streak end")


class StreakDayRecord(BaseModel):
    """Single streak day record"""

    day: date = Field(description="Calendar day")
    status: str = Field(description="active | frozen | missed")
    used_freeze: bool = Field(default=False, description="Whether freeze was used")
    source_event: str | None = Field(default=None, description="Source event type")


class StreakHistoryResponse(BaseModel):
    """Streak history response for calendar view"""

    days: list[StreakDayRecord] = Field(default_factory=list, description="Streak day records")


# ========== Contract Schemas ==========


class ContractCreateRequest(BaseModel):
    """Create contract request"""

    target_study_minutes: int = Field(ge=10, le=480, description="Target study minutes per day")
    target_days: int = Field(ge=1, le=100, description="Target consecutive days")
    photon_stake: int = Field(ge=10, description="Photons to stake")


class ContractResponse(BaseModel):
    """Contract response"""

    user_id: UUID = Field(description="User ID")
    target_study_minutes: int = Field(description="Target study minutes per day")
    target_days: int = Field(description="Target consecutive days")
    photon_stake: int = Field(description="Staked photons")
    status: ContractStatus = Field(description="Contract status")
    start_date: datetime = Field(description="Start date")
    end_date: datetime = Field(description="End date")
    current_days: int = Field(default=0, description="Current completed days")
    current_minutes: int = Field(default=0, description="Current study minutes")
    completed_at: datetime | None = Field(default=None, description="Completed time")
    reward_multiplier: float = Field(default=2.0, description="Reward multiplier")
    failed_at: datetime | None = Field(default=None, description="Failed time")
    failure_reason: str | None = Field(default=None, description="Failure reason")


class ContractCheckResponse(BaseModel):
    """Contract check response"""

    has_active_contract: bool = Field(default=False, description="Has active contract")
    contract: ContractResponse | None = Field(default=None, description="Contract detail")
    progress_today: int = Field(default=0, description="Today's study minutes")
    remaining_days: int = Field(default=0, description="Remaining days")


# ========== Galaxy Skin Schemas ==========


class GalaxySkinBase(BaseModel):
    """Galaxy skin basic information"""

    id: str = Field(description="Skin ID")
    name: str = Field(description="Skin name")
    description: str | None = Field(default=None, description="Description")
    preview_url: str | None = Field(default=None, description="Preview image URL")
    rarity: AchievementRarity = Field(description="Skin rarity")
    sort_order: int = Field(default=0, description="Display order")


class GalaxySkinDetail(GalaxySkinBase):
    """Galaxy skin detailed information"""

    unlock_type: str = Field(description="Unlock type")
    unlock_requirement: dict[str, Any] = Field(description="Unlock requirement")
    skin_config: dict[str, Any] = Field(description="Skin configuration")
    is_unlocked: bool = Field(default=False, description="Is unlocked by user")
    is_equipped: bool = Field(default=False, description="Is currently equipped")


class GalaxySkinListResponse(BaseModel):
    """Galaxy skin list response"""

    data: list[GalaxySkinDetail] = Field(default_factory=list, description="Skins list")
    equipped_skin_id: str | None = Field(default=None, description="Currently equipped skin")


# ========== Title Schemas ==========


class UserTitleResponse(BaseModel):
    """User title response"""

    title_id: str = Field(description="Title ID")
    title_name: str = Field(description="Title name")
    title_display: str = Field(description="Display text")
    source_achievement_id: str | None = Field(default=None, description="Source achievement")
    is_equipped: bool = Field(default=False, description="Is equipped")
    unlocked_at: datetime = Field(description="Unlocked time")


class TitleListResponse(BaseModel):
    """User title list response"""

    data: list[UserTitleResponse] = Field(default_factory=list, description="Titles list")
    equipped_title: str | None = Field(default=None, description="Currently equipped title")


# ========== Event Schemas ==========


class AchievementEventType(StrEnum):
    """Achievement event types"""

    TASK_COMPLETED = "task_completed"
    DAILY_CHECKIN = "daily_checkin"
    NODE_UNLOCKED = "node_unlocked"
    NODE_MASTERED = "node_mastered"
    STUDY_MINUTES_ACCUMULATED = "study_minutes_accumulated"
    NIGHT_STUDY = "night_study"
    EARLY_BIRD = "early_bird"
    WEEKEND_WARRIOR = "weekend_warrior"
    STREAK_MILESTONE = "streak_milestone"
    CONTRACT_COMPLETED = "contract_completed"
    CONTRACT_FAILED = "contract_failed"
    HIDDEN_TRIGGER = "hidden_trigger"


class AchievementUnlockEvent(BaseModel):
    """Achievement unlock event"""

    achievement_id: str = Field(description="Achievement ID")
    name: str = Field(description="Achievement name")
    rarity: AchievementRarity = Field(description="Achievement rarity")
    visual_effect: dict[str, Any] | None = Field(default=None, description="Visual effect config")
    rewards: list[dict[str, Any]] | None = Field(default=None, description="Rewards")
    unlocked_at: datetime = Field(default_factory=datetime.utcnow, description="Unlock time")
    context_snapshot: dict[str, Any] | None = Field(default=None, description="Context captured when unlocked")
    context_story: str | None = Field(default=None, description="Personalized unlock context story")


class AchievementEventRequest(BaseModel):
    """Achievement event request (internal use)"""

    event_type: AchievementEventType = Field(description="Event type")
    event_data: dict[str, Any] | None = Field(default=None, description="Event data")


class AchievementEventProcessResponse(BaseModel):
    """Internal achievement event processing response"""

    success: bool = Field(default=True, description="Request success")
    unlocked_count: int = Field(default=0, description="Number of achievements unlocked by this event")
    unlocked: list[dict[str, Any]] = Field(default_factory=list, description="Unlocked achievement payloads")


# ========== Share Schemas ==========


class ShareCardPrivacySettings(BaseModel):
    """Privacy settings for achievement share cards"""

    display_name: str | None = Field(
        default=None,
        description="Custom display name. None means use default nickname.",
    )
    show_avatar: bool = Field(default=False, description="Show user avatar on card")
    show_unlock_date: bool = Field(default=True, description="Show unlock date on card")
    show_progress_stats: bool = Field(
        default=True,
        description="Show progress statistics on card",
    )
    show_first_unlocker_badge: bool = Field(
        default=True,
        description="Show first unlocker badge if applicable",
    )

    def get_effective_display_name(self, default_name: str) -> str:
        """Get effective display name, using default if custom name not set."""
        return self.display_name if self.display_name else default_name

    def settings_hash(self) -> str:
        """Generate a hash of settings for cache key."""
        import hashlib

        data = f"{self.display_name}|{self.show_avatar}|{self.show_unlock_date}|{self.show_progress_stats}|{self.show_first_unlocker_badge}"
        return hashlib.md5(data.encode()).hexdigest()[:8]


class ShareTemplateInfo(BaseModel):
    """Share card template information"""

    id: str = Field(description="Template ID")
    name: str = Field(description="Template display name")
    description: str | None = Field(default=None, description="Template description")
    preview_url: str | None = Field(default=None, description="Template preview image URL")


class AchievementShareRequest(BaseModel):
    """Request body for generating achievement share card"""

    template_id: str = Field(default="cosmic", description="Template ID (cosmic, minimal, neon, elegant)")
    privacy: ShareCardPrivacySettings = Field(
        default_factory=ShareCardPrivacySettings,
        description="Privacy settings for the share card",
    )


class AchievementShareResponse(BaseModel):
    """Achievement share response"""

    card_url: str = Field(description="Share card image URL")
    mime_type: str = Field(default="image/png", description="Share card MIME type")
    width: int = Field(description="Share card width in pixels")
    height: int = Field(description="Share card height in pixels")
    generated_at: datetime = Field(description="Share card generation time")
    template_id: str = Field(default="cosmic", description="Template used for generation")
    privacy_settings: ShareCardPrivacySettings = Field(
        default_factory=ShareCardPrivacySettings,
        description="Privacy settings applied to card",
    )
    achievement: AchievementDetail = Field(description="Achievement info")


class ShareTemplateListResponse(BaseModel):
    """Response for listing available share card templates"""

    templates: list[ShareTemplateInfo] = Field(
        default_factory=list,
        description="Available templates",
    )


class AchievementPinResponse(BaseModel):
    """Pin achievement response"""

    success: bool = Field(default=True, description="Request success")
    pinned: bool = Field(default=False, description="Whether the achievement is pinned")


# ========== Stats Schemas ==========


class AchievementStatsResponse(BaseModel):
    """User achievement statistics"""

    total_achievements: int = Field(description="Total achievements")
    unlocked_count: int = Field(description="Unlocked count")
    unlocked_percentage: float = Field(description="Unlocked percentage")
    common_count: int = Field(description="Common achievements unlocked")
    rare_count: int = Field(description="Rare achievements unlocked")
    epic_count: int = Field(description="Epic achievements unlocked")
    legendary_count: int = Field(description="Legendary achievements unlocked")
    hidden_found: int = Field(description="Hidden achievements found")
    current_streak: int = Field(description="Current streak")
    total_photons: int = Field(description="Total photons from achievements")
