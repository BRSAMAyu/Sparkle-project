from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.services.theater.prediction_theater_service import PredictionTheaterService

router = APIRouter(prefix="/theater", tags=["theater"])


class TheaterGenerateRequest(BaseModel):
    topic: str = Field(..., min_length=1, description="学习目标或主题")
    target_node_id: UUID | None = Field(default=None, description="可选的目标节点 ID")
    horizon_days: int = Field(default=14, ge=7, le=30, description="推演周期天数")


class TheaterWhatIfRequest(BaseModel):
    prediction_id: str
    route_id: str
    skip_node_id: str | None = None
    skip_node_ids: list[str] = Field(default_factory=list)


class TheaterSnapshotRequest(BaseModel):
    prediction_id: str
    route_id: str
    note: str | None = Field(default=None, max_length=500)


class TheaterAdoptRequest(BaseModel):
    prediction_id: str
    route_id: str
    source_chat_session_id: str | None = None


class TheaterActualOutcomeRequest(BaseModel):
    actual_completion_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    actual_mastery: float | None = Field(default=None, ge=0.0, le=100.0)


class TheaterPromoteNodeRequest(BaseModel):
    theater_node_id: str = Field(..., min_length=1)


@router.post("/predictions/generate")
async def generate_theater_prediction(
    request: TheaterGenerateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    service = PredictionTheaterService(db)
    try:
        return await service.generate_prediction(
            user_id=UUID(user_id),
            topic=request.topic,
            target_node_id=request.target_node_id,
            horizon_days=request.horizon_days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/predictions/what-if")
async def generate_theater_what_if(
    request: TheaterWhatIfRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    service = PredictionTheaterService(db)
    return await service.simulate_what_if(
        user_id=UUID(user_id),
        prediction_id=request.prediction_id,
        route_id=request.route_id,
        skip_node_id=request.skip_node_id,
        skip_node_ids=request.skip_node_ids,
    )


@router.post("/snapshots")
async def save_theater_snapshot(
    request: TheaterSnapshotRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    service = PredictionTheaterService(db)
    return await service.save_snapshot(
        user_id=UUID(user_id),
        prediction_id=request.prediction_id,
        route_id=request.route_id,
        note=request.note,
    )


@router.post("/predictions/{prediction_id}/adopt")
async def adopt_theater_prediction(
    prediction_id: str,
    request: TheaterAdoptRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    service = PredictionTheaterService(db)
    return await service.adopt_prediction(
        user_id=UUID(user_id),
        prediction_id=prediction_id,
        route_id=request.route_id,
        source_chat_session_id=request.source_chat_session_id,
    )


@router.post("/predictions/{prediction_id}/actuals")
async def record_theater_actual_outcome(
    prediction_id: str,
    request: TheaterActualOutcomeRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    service = PredictionTheaterService(db)
    return await service.record_actual_outcome(
        user_id=UUID(user_id),
        prediction_id=prediction_id,
        actual_completion_rate=request.actual_completion_rate,
        actual_mastery=request.actual_mastery,
    )


@router.get("/predictions/{prediction_id}/accuracy")
async def get_theater_prediction_accuracy(
    prediction_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    del user_id
    service = PredictionTheaterService(db)
    return await service.get_accuracy_summary(prediction_id)


@router.post("/predictions/{prediction_id}/promote-node")
async def promote_theater_node(
    prediction_id: str,
    request: TheaterPromoteNodeRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    service = PredictionTheaterService(db)
    try:
        return await service.promote_node_to_galaxy(
            user_id=UUID(user_id),
            prediction_id=prediction_id,
            theater_node_id=request.theater_node_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
