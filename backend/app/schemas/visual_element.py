"""
Visual Element System Schemas
视觉元素系统数据传输对象
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.visual_element import (
    VisualElementRarity,
    VisualElementType,
    VisualElementUnlockSource,
)


class VisualElementBase(BaseModel):
    """视觉元素基础 Schema"""
    id: str = Field(..., description="元素ID")
    name: str = Field(..., description="元素名称")
    description: str | None = Field(None, description="元素描述")
    element_type: VisualElementType = Field(..., description="元素类型")
    rarity: VisualElementRarity = Field(..., description="稀有度")
    preview_url: str | None = Field(None, description="预览图URL")
    icon_url: str | None = Field(None, description="图标URL")
    category: str | None = Field(None, description="分类")
    config: dict[str, Any] = Field(default_factory=dict, description="元素配置")
    unlock_requirement: dict[str, Any] | None = Field(
        None,
        description="解锁条件",
    )


class VisualElementResponse(VisualElementBase):
    """视觉元素响应 Schema"""
    unlock_source: VisualElementUnlockSource = Field(..., description="解锁来源")
    is_default: bool = Field(..., description="是否默认元素")
    sort_order: int = Field(..., description="排序权重")

    # 用户相关状态
    is_unlocked: bool = Field(False, description="是否已解锁")
    unlocked_at: datetime | None = Field(None, description="解锁时间")
    is_equipped: bool = Field(False, description="是否已装备")

    model_config = {"from_attributes": True}


class VisualElementListResponse(BaseModel):
    """视觉元素列表响应"""
    items: list[VisualElementResponse] = Field(..., description="元素列表")
    total: int = Field(..., description="总数")


class UserVisualConfigResponse(BaseModel):
    """用户视觉配置响应"""
    equipped_background: VisualElementResponse | None = Field(None, description="装备的背景")
    equipped_particle: VisualElementResponse | None = Field(None, description="装备的粒子")
    equipped_effect: VisualElementResponse | None = Field(None, description="装备的特效")
    background_equipped_at: datetime | None = Field(None)
    particle_equipped_at: datetime | None = Field(None)
    effect_equipped_at: datetime | None = Field(None)


class EquipElementRequest(BaseModel):
    """装备元素请求"""
    element_id: str = Field(..., description="要装备的元素ID")


class EquipElementResponse(BaseModel):
    """装备元素响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="消息")
    config: UserVisualConfigResponse = Field(..., description="更新后的配置")


class UnlockElementRequest(BaseModel):
    """解锁元素请求（内部使用）"""
    element_id: str = Field(..., description="要解锁的元素ID")
    source: str = Field(..., description="解锁来源")
    source_id: str | None = Field(None, description="来源ID（成就ID/购买ID等）")


class UnlockElementResponse(BaseModel):
    """解锁元素响应"""
    success: bool = Field(..., description="是否成功")
    element: VisualElementResponse = Field(..., description="解锁的元素")
    message: str = Field(..., description="消息")


class VisualElementBundleConfig(BaseModel):
    """套装配置"""
    background_id: str | None = Field(None, description="背景ID")
    particle_id: str | None = Field(None, description="粒子ID")
    effect_id: str | None = Field(None, description="特效ID")
    discount_percent: int | None = Field(None, description="折扣百分比")


class VisualElementBundleResponse(VisualElementBase):
    """套装响应"""
    bundle_config: VisualElementBundleConfig = Field(..., description="套装配置")
    included_elements: list[VisualElementResponse] = Field(
        default_factory=list,
        description="包含的元素列表"
    )
