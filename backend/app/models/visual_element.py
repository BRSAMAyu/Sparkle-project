"""
Visual Element System Models
视觉元素系统数据模型 - 包含视觉元素定义、用户解锁记录、用户视觉配置
"""
import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel


class VisualElementType(enum.StrEnum):
    """视觉元素类型"""
    BACKGROUND = "background"  # 背景层
    PARTICLE = "particle"      # 粒子层
    EFFECT = "effect"          # 特效层
    BUNDLE = "bundle"          # 套装（包含多个元素）


class VisualElementRarity(enum.StrEnum):
    """视觉元素稀有度"""
    COMMON = "common"         # 普通 (灰/白)
    RARE = "rare"             # 稀有 (蓝)
    EPIC = "epic"             # 史诗 (紫)
    LEGENDARY = "legendary"   # 传说 (金/橙)


class VisualElementUnlockSource(enum.StrEnum):
    """解锁来源"""
    SYSTEM = "system"           # 系统默认
    ACHIEVEMENT = "achievement" # 成就解锁
    SHOP = "shop"               # 商城购买
    EVENT = "event"             # 活动奖励
    SEASON = "season"           # 季节限定


class VisualElement(BaseModel):
    """视觉元素定义表"""
    __tablename__ = "visual_elements"

    # 基础信息
    id = Column(String(50), primary_key=True)  # 如：bg_aurora_001
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    name_i18n = Column(JSONB, default=dict, nullable=True)
    description_i18n = Column(JSONB, default=dict, nullable=True)

    # 类型与稀有度
    element_type = Column(Enum(VisualElementType), nullable=False, index=True)
    rarity = Column(Enum(VisualElementRarity), default=VisualElementRarity.COMMON, nullable=False)

    # 解锁来源
    unlock_source = Column(Enum(VisualElementUnlockSource), default=VisualElementUnlockSource.SYSTEM)
    unlock_requirement = Column(JSONB, nullable=True)  # {"achievement_id": "streak_30"} 或 {"price_photons": 200}

    # 元素配置（根据 element_type 不同，配置内容不同）
    # background: {"gradient": {...}, "texture": "stars", "texture_opacity": 0.3}
    # particle: {"count": 50, "shape": "star", "colors": [...], "speed": 1.0}
    # effect: {"effect_type": "pulse_glow", "intensity": 0.8, "color": "#FF6B6B"}
    # bundle: {"background_id": "bg_aurora", "particle_id": "particle_star", "effect_id": "effect_glow"}
    config = Column(JSONB, nullable=False, default=dict)

    # 预览图
    preview_url = Column(String(500), nullable=True)
    icon_url = Column(String(500), nullable=True)

    # 状态
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)  # 是否为默认元素

    # 排序和分类
    sort_order = Column(Integer, default=0, nullable=False)
    category = Column(String(50), nullable=True)  # 如：nature, space, cyberpunk

    # 季节/时间限制
    season_start = Column(String(10), nullable=True)  # "03-01" 表示3月1日开始
    season_end = Column(String(10), nullable=True)    # "05-31" 表示5月31日结束

    def __repr__(self):
        return f"<VisualElement(id={self.id}, name={self.name}, type={self.element_type})>"

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


class UserVisualElement(BaseModel):
    """用户解锁的视觉元素记录"""
    __tablename__ = "user_visual_elements"

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    element_id = Column(String(50), ForeignKey("visual_elements.id", ondelete="CASCADE"), primary_key=True)

    # 解锁信息
    unlocked_at = Column(DateTime, nullable=False)
    unlock_source = Column(String(50), nullable=False)  # achievement, shop, event, system

    # 关联的成就/购买记录
    source_id = Column(String(100), nullable=True)  # achievement_id 或 purchase_id

    # 关系
    element = relationship("VisualElement")

    def __repr__(self):
        return f"<UserVisualElement(user_id={self.user_id}, element_id={self.element_id})>"


class UserVisualConfig(BaseModel):
    """用户当前视觉配置（装备状态）"""
    __tablename__ = "user_visual_configs"

    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

    # 装备的视觉元素
    equipped_background_id = Column(String(50), ForeignKey("visual_elements.id"), nullable=True)
    equipped_particle_id = Column(String(50), ForeignKey("visual_elements.id"), nullable=True)
    equipped_effect_id = Column(String(50), ForeignKey("visual_elements.id"), nullable=True)

    # 装备时间
    background_equipped_at = Column(DateTime, nullable=True)
    particle_equipped_at = Column(DateTime, nullable=True)
    effect_equipped_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<UserVisualConfig(user_id={self.user_id}, bg={self.equipped_background_id})>"


# 创建索引
Index("ix_visual_elements_type_rarity", VisualElement.element_type, VisualElement.rarity)
Index("ix_visual_elements_category", VisualElement.category)
Index("ix_visual_elements_active", VisualElement.is_active)
Index("ix_user_visual_elements_user_id", UserVisualElement.user_id)
Index("ix_user_visual_configs_user_id", UserVisualConfig.user_id)
