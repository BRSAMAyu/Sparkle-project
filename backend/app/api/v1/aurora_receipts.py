"""A-06 · Aurora Receipts API —— Why-this 回执四动作端点（/aurora/receipts）。

GJ08（Correction → memory scope → next-session adaptation）的入口面：用户从
「为什么提这条」回执直接纠偏（not_relevant / wrong / change_scope / delete），
动作经 ``AuroraReceiptService`` 委托既有权威真源生效（服务层 docstring）。

分层边界：handler 只做协议适配 + 异常映射；鉴权走既有 get_current_user 依赖
（本引擎不做鉴权语义，只消费身份）；真实写路径/幂等/隔离守卫全在服务层与
被委托的权威服务内。
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.aurora.calibration_receipt import (
    CALIBRATION_RECEIPT_ACTIONS,
    CALIBRATION_RECEIPT_VERSION,
)
from app.models.user import User
from app.services.aurora_receipt_service import SUPPORTED_MEMORY_KINDS, AuroraReceiptService
from app.services.memory_provenance_service import (
    MemoryProvenanceConflictError,
    MemoryProvenanceNotFoundError,
)

router = APIRouter(prefix="/aurora/receipts", tags=["aurora"])


class ReceiptRespondRequest(BaseModel):
    """回执纠偏请求（四动作；wrong 可选携带更正文本——携带即走 supersede）。"""

    memory_type: str = Field(..., description="episodic | preference | goal")
    memory_id: str = Field(..., min_length=1)
    action: str = Field(..., description="not_relevant | wrong | change_scope | delete")
    corrected_content: str | None = Field(None, max_length=2000)
    reason: str | None = Field(None, max_length=1000)
    response_id: str | None = Field(None, max_length=200)

    @model_validator(mode="after")
    def _closed_vocab(self) -> "ReceiptRespondRequest":
        if str(self.memory_type or "").strip().lower() not in SUPPORTED_MEMORY_KINDS:
            raise ValueError(f"memory_type must be one of {sorted(SUPPORTED_MEMORY_KINDS)}")
        if str(self.action or "").strip().lower() not in CALIBRATION_RECEIPT_ACTIONS:
            raise ValueError(f"action must be one of {sorted(CALIBRATION_RECEIPT_ACTIONS)}")
        return self


class ReceiptRespondResponse(BaseModel):
    status: str
    action: str
    authority: str = ""
    detail: dict[str, object] = Field(default_factory=dict)


# route-tier: authed
@router.post("/respond", response_model=ReceiptRespondResponse)
async def respond_to_receipt(
    payload: ReceiptRespondRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReceiptRespondResponse:
    try:
        memory_id = UUID(payload.memory_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="memory_id must be a UUID"
        ) from exc
    service = AuroraReceiptService(db)
    try:
        result = await service.respond(
            user_id=current_user.id,
            memory_type=payload.memory_type,
            memory_id=memory_id,
            action=payload.action,
            corrected_content=payload.corrected_content,
            reason=payload.reason,
            response_id=payload.response_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except MemoryProvenanceNotFoundError as exc:
        # 跨用户与缺失一律 404（无存在性泄漏——M-08 同款法则）。
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory item not found") from exc
    except MemoryProvenanceConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    detail: dict[str, object] = {key: value for key, value in result.items() if key not in {"status", "action", "authority"}}
    return ReceiptRespondResponse(
        status=str(result.get("status") or "ok"),
        action=str(result.get("action") or payload.action),
        authority=str(result.get("authority") or ""),
        detail=detail,
    )


# route-tier: authed
@router.get("/actions")
async def list_receipt_actions(current_user: User = Depends(get_current_user)) -> dict[str, object]:
    """回执动作词表面（封闭集合的自描述出口；移动端无需硬编码枚举）。"""
    return {
        "schema_version": CALIBRATION_RECEIPT_VERSION,
        "actions": sorted(CALIBRATION_RECEIPT_ACTIONS),
        "memory_kinds": sorted(SUPPORTED_MEMORY_KINDS),
        "wrong_modes": ["supersede", "lower_confidence"],
    }
