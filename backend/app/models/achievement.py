"""
Achievement System Models
成就系统数据模型 - 包含成就定义、用户成就记录、连胜统计、契约等
"""

from __future__ import annotations

import enum

from sqlalchemy import JSON, Boolean, Column, Date, DateTime, Enum, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


# Python 3.9 compatible StrEnum
class StrEnum(enum.StrEnum):
    """String enum for Python 3.9 compatibility"""

    def __new__(cls, value):
        obj = str.__new__(cls, value)
        obj._value_ = value
        return obj


class AchievementRarity(StrEnum):
    """成就稀有度"""

    COMMON = "common"  # 普通（银色）
    RARE = "rare"  # 稀有（金色）
    EPIC = "epic"  # 史诗（紫色）
    LEGENDARY = "legendary"  # 传说（彩虹）


class AchievementType(StrEnum):
    """成就类型"""

    MILESTONE = "milestone"  # 学习里程碑
    STREAK = "streak"  # 连续学习
    MASTERY = "mastery"  # 领域精通
    TASK_COMPLETE = "task_complete"  # 任务完成
    HIDDEN = "hidden"  # 隐藏成就
    SOCIAL = "social"  # 社交成就
    CONTRACT = "contract"  # 契约成就
    STUDY_TIME = "study_time"  # 学习时长
    NODE_EXPLORE = "node_explore"  # 知识点探索
    SPRINT = "sprint"  # 冲刺专属成就
    PLANNING = "planning"  # 计划创建/规划行为


class VisualEffectType(StrEnum):
    """视觉特效类型"""

    NONE = "none"
    BLACK_HOLE = "black_hole"  # 恒星坍缩成黑洞
    SUPERNOVA = "supernova"  # 超新星爆发
    GRAVITY_WAVE = "gravity_wave"  # 引力波
    NEBULA_TRANSFORM = "nebula_transform"  # 星云变色
    GALAXY_SKIN = "galaxy_skin"  # 星系皮肤
    DUAL_STAR_CONNECTION = "dual_star"  # 双星连接


class StreakDayStatus(StrEnum):
    """连胜日历状态"""

    ACTIVE = "active"
    WEAK = "weak"  # Activity day but below quality threshold
    FROZEN = "frozen"
    MISSED = "missed"


class ContractStatus(StrEnum):
    """契约状态"""

    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class Achievement(BaseModel):
    """成就定义表"""

    __tablename__ = "achievements"

    # 基础信息
    id = Column(String(50), primary_key=True)  # 字符串ID用于标识，如 "streak_7"
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    name_i18n = Column(JSON, default=dict, nullable=True)
    description_i18n = Column(JSON, default=dict, nullable=True)
    icon_url = Column(String(500))

    # 分类
    type = Column(Enum(AchievementType), nullable=False, index=True)
    rarity = Column(Enum(AchievementRarity), default=AchievementRarity.COMMON)

    # 触发条件
    trigger_code = Column(String(50), nullable=False, index=True)
    trigger_config = Column(JSON)  # 触发条件配置，如 {"days": 7, "count": 100}

    # 隐藏成就
    is_hidden = Column(Boolean, default=False)
    hint = Column(String(200))  # 隐藏成就的模糊提示

    # 前置成就
    prerequisites = Column(JSON)  # 前置成就ID列表，如 ["achievement_id_1", "achievement_id_2"]

    # 视觉效果配置（核心：与星图联动）
    visual_effect_type = Column(Enum(VisualEffectType), default=VisualEffectType.NONE)
    visual_config = Column(JSON)  # 详细视觉效果配置

    # 奖励配置
    reward_config = Column(JSON)  # 奖励配置列表

    # 统计
    total_unlocked = Column(Integer, default=0)  # 全局解锁人数
    first_unlocker_id = Column(GUID(), ForeignKey("users.id"), nullable=True)

    # 排序权重（用于成就地图排序）
    sort_order = Column(Integer, default=0)
    category = Column(String(50))  # 用于成就地图分组

    # 活动窗口（限时成就）
    active_from = Column(DateTime, nullable=True)
    active_to = Column(DateTime, nullable=True)
    is_limited = Column(Boolean, default=False)
    event_tag = Column(String(50), nullable=True)

    # 父成就（用于成就树/成就链）
    parent_id = Column(String(50), ForeignKey("achievements.id"), nullable=True)

    # 关系
    children = relationship("Achievement", backref="parent", remote_side="Achievement.id")

    def __repr__(self):
        return f"<Achievement(id={self.id}, name={self.name}, rarity={self.rarity})>"

    @staticmethod
    def _normalize_locale(locale: str | None) -> str | None:
        if not locale:
            return None
        primary = locale.split(",")[0].strip()
        if not primary:
            return None
        primary = primary.split(";")[0].strip()
        if not primary:
            return None
        return primary.split("-")[0].lower()

    def get_localized_name(self, locale: str | None) -> str:
        language = self._normalize_locale(locale)
        if language and isinstance(self.name_i18n, dict):
            value = self.name_i18n.get(language)
            if value:
                return value
        return self.name

    def get_localized_description(self, locale: str | None) -> str | None:
        language = self._normalize_locale(locale)
        if language and isinstance(self.description_i18n, dict):
            value = self.description_i18n.get(language)
            if value:
                return value
        return self.description


class UserAchievement(BaseModel):
    """用户成就记录表"""

    __tablename__ = "user_achievements"

    user_id = Column(GUID(), ForeignKey("users.id"), primary_key=True)
    achievement_id = Column(String(50), ForeignKey("achievements.id"), primary_key=True)

    # 进度（0.0 - 1.0）
    progress = Column(Float, default=0.0)
    progress_value = Column(Integer, default=0)  # 当前值（如：已学习50天）
    progress_target = Column(Integer, default=1)  # 目标值（如：100天）

    # 解锁状态
    unlocked_at = Column(DateTime, nullable=True, index=True)
    is_pinned = Column(Boolean, default=False)  # 用户是否置顶展示

    # 社交统计
    share_count = Column(Integer, default=0)
    is_first_unlocker = Column(Boolean, default=False)

    # 最后更新时间（用于进度变化追踪）
    last_progress_update = Column(DateTime, nullable=True)

    # 解锁时上下文快照：当前计划、任务、触发事件和故事描述
    context_snapshot = Column(JSONBCompat, nullable=True)

    # 关系
    achievement = relationship("Achievement")

    def __repr__(self):
        return (
            f"<UserAchievement(user_id={self.user_id}, achievement_id={self.achievement_id}, progress={self.progress})>"
        )


class UserStreakStats(BaseModel):
    """用户连胜统计表"""

    __tablename__ = "user_streak_stats"

    user_id = Column(GUID(), ForeignKey("users.id"), primary_key=True)

    # 连胜数据
    current_streak = Column(Integer, default=0)
    max_streak = Column(Integer, default=0)
    last_activity_date = Column(DateTime, nullable=True)

    # 连胜保护机制
    freeze_charges = Column(Integer, default=1)  # 默认送1个
    max_freeze_charges = Column(Integer, default=3)
    last_freeze_used_at = Column(DateTime, nullable=True)

    # 统计
    total_checkin_days = Column(Integer, default=0)
    longest_streak_start = Column(DateTime, nullable=True)
    longest_streak_end = Column(DateTime, nullable=True)

    # 最长连胜记录
    longest_streak = Column(Integer, default=0)

    def __repr__(self):
        return f"<UserStreakStats(user_id={self.user_id}, current_streak={self.current_streak})>"


class UserStreakDay(BaseModel):
    """用户连胜日历记录"""

    __tablename__ = "user_streak_days"

    user_id = Column(GUID(), ForeignKey("users.id"), primary_key=True)
    day = Column(Date, primary_key=True)

    status = Column(
        Enum(StreakDayStatus, values_callable=lambda enum_cls: [item.value for item in enum_cls]),
        nullable=False,
    )
    used_freeze = Column(Boolean, default=False)
    source_event = Column(String(50), nullable=True)

    __table_args__ = (Index("ix_user_streak_days_user_day", "user_id", "day", unique=True),)

    user = relationship("User")

    def __repr__(self):
        return f"<UserStreakDay(user_id={self.user_id}, day={self.day}, status={self.status})>"


class SparkContract(BaseModel):
    """星火契约（承诺机制）"""

    __tablename__ = "spark_contracts"

    user_id = Column(GUID(), ForeignKey("users.id"), primary_key=True)

    # 契约内容
    target_study_minutes = Column(Integer, default=60)  # 目标学习时长（分钟）
    target_days = Column(Integer, default=7)  # 目标连续天数
    photon_stake = Column(Integer, default=100)  # 投入的光子积分

    # 状态
    status = Column(Enum(ContractStatus), default=ContractStatus.ACTIVE)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)

    # 进度
    current_days = Column(Integer, default=0)
    current_minutes = Column(Integer, default=0)

    # 结算
    completed_at = Column(DateTime, nullable=True)
    reward_multiplier = Column(Float, default=2.0)  # 完成后的倍数奖励

    # 失败记录
    failed_at = Column(DateTime, nullable=True)
    failure_reason = Column(String(200), nullable=True)

    def __repr__(self):
        return f"<SparkContract(user_id={self.user_id}, status={self.status}, progress={self.current_days}/{self.target_days})>"


class GalaxySkin(BaseModel):
    """星系皮肤表"""

    __tablename__ = "galaxy_skins"

    id = Column(String(50), primary_key=True)
    name = Column(String(100))
    description = Column(String(500))
    preview_url = Column(String(500))

    # 解锁条件
    unlock_type = Column(String(50))  # achievement, level, purchase
    unlock_requirement = Column(JSON)  # {"achievement_id": "legend_master"}

    # 皮肤配置（核心：改变星系视觉）
    skin_config = Column(JSON)

    # 排序和稀有度
    rarity = Column(Enum(AchievementRarity), default=AchievementRarity.RARE)
    sort_order = Column(Integer, default=0)

    def __repr__(self):
        return f"<GalaxySkin(id={self.id}, name={self.name}, rarity={self.rarity})>"


class UserGalaxySkin(BaseModel):
    """用户星系皮肤记录"""

    __tablename__ = "user_galaxy_skins"

    user_id = Column(GUID(), ForeignKey("users.id"), primary_key=True)
    skin_id = Column(String(50), ForeignKey("galaxy_skins.id"), primary_key=True)

    # 解锁状态
    unlocked_at = Column(DateTime, nullable=False)
    unlock_source = Column(String(50))  # achievement, purchase, etc.

    # 使用状态
    is_equipped = Column(Boolean, default=False)

    # 关系
    skin = relationship("GalaxySkin")

    def __repr__(self):
        return f"<UserGalaxySkin(user_id={self.user_id}, skin_id={self.skin_id}, is_equipped={self.is_equipped})>"


class StudyBuddy(BaseModel):
    """学习搭子关系表"""

    __tablename__ = "study_buddies"

    user1_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    user2_id = Column(GUID(), ForeignKey("users.id"), nullable=False)

    # 关系状态
    status = Column(String(20), default="active")  # active, paused
    connection_strength = Column(Float, default=0.0)  # 连接强度 0-1

    # 共同成就
    mutual_study_days = Column(Integer, default=0)
    last_mutual_study_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<StudyBuddy(user1={self.user1_id}, user2={self.user2_id}, strength={self.connection_strength})>"


class UserTitle(BaseModel):
    """用户称号表"""

    __tablename__ = "user_titles"

    user_id = Column(GUID(), ForeignKey("users.id"), primary_key=True)
    title_id = Column(String(50), primary_key=True)

    # 称号信息
    title_name = Column(String(100))
    title_display = Column(String(100))

    # 来源成就
    source_achievement_id = Column(String(50), ForeignKey("achievements.id"))

    # 状态
    is_equipped = Column(Boolean, default=False)
    unlocked_at = Column(DateTime, nullable=False)

    def __repr__(self):
        return f"<UserTitle(user_id={self.user_id}, title={self.title_name}, is_equipped={self.is_equipped})>"


# 创建索引
Index("idx_user_achievements_user_unlocked", UserAchievement.user_id, UserAchievement.unlocked_at)
Index("idx_user_achievements_unlocked_at", UserAchievement.unlocked_at)
Index("idx_achievements_type_rarity", Achievement.type, Achievement.rarity)
Index("idx_achievements_category", Achievement.category)
Index("idx_user_streak_stats_last_activity", UserStreakStats.last_activity_date)
