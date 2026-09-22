"""D-REDEEM · 兑换码 schemas（user 核销 + admin 批量生成）。

红线：明文兑换码只在 admin 批量生成响应出现一次（``codes``），核销请求携带
明文但服务端只落哈希；日志面禁止打印任何含明文的结构。
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.entitlement import ENTITLEMENT_PRO
from app.services.redeem_service import normalize_redeem_code

#: 批量生成上限（admin 单批；参赛演示面，防误操作生成海量码）
MAX_BATCH_SIZE = 200
#: 单码核销上限（防呆：单码多人共享场景的演示上限）
MAX_USES_CAP = 500
#: 单码授权时长上限（天；演示期 pro/30d 量级，防呆不设业务上限之外的天文值）
MAX_DURATION_DAYS = 3650


class RedeemRequest(BaseModel):
    """用户核销请求。"""

    code: str = Field(..., min_length=4, max_length=64, description="兑换码明文（SPARK-XXXX-XXXX-XXXX）")

    @field_validator("code")
    @classmethod
    def _normalize(cls, value: str) -> str:
        normalized = normalize_redeem_code(value)
        if len(normalized) < 4:
            raise ValueError("兑换码格式无效")
        return normalized


class RedeemResponse(BaseModel):
    """核销结果：成功返回档位与新到期时间；失败返回业务 status（HTTP 200/4xx 由路由层映射）。"""

    status: str = Field(..., description="ok | invalid | expired | exhausted | error")
    tier: str | None = None
    entitlement_expires_at: datetime | None = None
    message: str | None = None


class RedeemBatchCreateRequest(BaseModel):
    """admin 批量生成请求。"""

    tier: str = Field(default=ENTITLEMENT_PRO, max_length=32)
    duration_days: int = Field(default=30, ge=1, le=MAX_DURATION_DAYS)
    count: int = Field(default=5, ge=1, le=MAX_BATCH_SIZE)
    max_uses: int = Field(default=1, ge=1, le=MAX_USES_CAP)
    batch_id: str | None = Field(default=None, max_length=64)
    expires_in_days: int | None = Field(default=None, ge=1, le=MAX_DURATION_DAYS, description="码本身的有效期（天），NULL=永不过期")

    @field_validator("tier")
    @classmethod
    def _tier_in_vocabulary(cls, value: str) -> str:
        from app.core.entitlement import normalize_entitlement

        normalized = normalize_entitlement(value)
        # 值域约束：可授出的档位必须能被判级识别为 pro（宁降不升：未知 tier
        # 授出去也只是 free，这里直接在生成面拒绝）。
        if normalized != "pro":
            raise ValueError("tier 仅支持 'pro'（参赛演示期封闭词表）")
        return normalized


class RedeemBatchCreateResponse(BaseModel):
    """admin 批量生成响应 —— ``codes`` 是明文唯一出口，不落库不进日志。"""

    model_config = ConfigDict(from_attributes=True)

    batch_id: str
    tier: str
    duration_days: int
    max_uses: int
    expires_at: datetime | None = None
    codes: list[str]


class RedeemBatchSummary(BaseModel):
    """admin 批次核销进度（不含任何明文/哈希）。"""

    model_config = ConfigDict(from_attributes=True)

    batch_id: str
    total: int
    used_count: int
    tier: str
    duration_days: int
    expires_at: datetime | None = None
    created_by: UUID | None = None
