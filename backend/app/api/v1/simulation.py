from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.services.simulation.simulation_engine import SimulationEngine
from app.services.simulation.scenario_templates import normalize_scenario_key
from app.services.simulation.seed_extractor import SeedExtractor

router = APIRouter(prefix="/simulation", tags=["simulation"])


class SimulationRunRequest(BaseModel):
    topic: str = Field(..., description="学习主题")
    scenario_key: str = Field(default="study_group", description="场景模板 key")
    planned_round_count: int | None = Field(
        default=None,
        ge=3,
        le=12,
        description="期望轮次，后端会按场景上限裁剪（当前最高支持 12 轮）",
    )
    participant_names: list[str] = Field(
        default_factory=list,
        description="用户显式指定的参与角色名",
    )
    facilitation_style: str = Field(
        default="balanced",
        description="讨论展开方式：balanced / debate / guided / practical",
    )


class SimulationContinueRequest(BaseModel):
    user_response: str = Field(..., min_length=1, description="用户在互动节点给出的回应")


class SimulationSeedResponse(BaseModel):
    topic: str
    context: str
    tension_point: str
    source_type: str
    source_ids: list[str]
    relevance_score: float
    suggested_scenario: str
    suggested_experts: list[str]


class RecommendedSeedsResponse(BaseModel):
    scenario_key: str | None
    seeds: list[SimulationSeedResponse]


@router.get("/recommended-seeds", response_model=RecommendedSeedsResponse)
async def get_recommended_learning_simulation_seeds(
    scenario_key: str | None = None,
    limit: int = 3,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        normalized_scenario_key = normalize_scenario_key(scenario_key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    extractor = SeedExtractor(db)
    seeds = await extractor.get_cached_or_generate(
        UUID(user_id),
        scenario_key=normalized_scenario_key,
        limit=max(1, min(limit, 6)),
    )
    return RecommendedSeedsResponse(
        scenario_key=normalized_scenario_key,
        seeds=[SimulationSeedResponse(**seed.to_dict()) for seed in seeds],
    )


@router.post("/run")
async def run_learning_simulation(
    request: SimulationRunRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        normalized_scenario_key = normalize_scenario_key(request.scenario_key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    engine = SimulationEngine(db)
    session = await engine.run(
        topic=request.topic,
        scenario_key=normalized_scenario_key,
        planned_round_count=request.planned_round_count,
        participant_names=request.participant_names,
        facilitation_style=request.facilitation_style,
        user_id=UUID(user_id),
    )
    return session.to_dict()


@router.post("/run/stream")
async def stream_learning_simulation(
    request: SimulationRunRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        normalized_scenario_key = normalize_scenario_key(request.scenario_key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    engine = SimulationEngine(db)

    async def event_generator():
        try:
            async for event_name, payload in engine.stream(
                topic=request.topic,
                scenario_key=normalized_scenario_key,
                planned_round_count=request.planned_round_count,
                participant_names=request.participant_names,
                facilitation_style=request.facilitation_style,
                user_id=UUID(user_id),
            ):
                yield f"event: {event_name}\n"
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            yield "event: done\n"
            yield "data: {\"status\":\"completed\"}\n\n"
        except Exception as exc:
            yield "event: error\n"
            yield f"data: {json.dumps({'message': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/sessions/{session_id}/continue")
async def continue_learning_simulation(
    session_id: str,
    request: SimulationContinueRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    engine = SimulationEngine(db)
    try:
        session = await engine.continue_run(
            session_id=session_id,
            user_response=request.user_response,
            user_id=UUID(user_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return session.to_dict()


@router.post("/sessions/{session_id}/continue/stream")
async def continue_learning_simulation_stream(
    session_id: str,
    request: SimulationContinueRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    engine = SimulationEngine(db)

    async def event_generator():
        try:
            async for event_name, payload in engine.continue_stream(
                session_id=session_id,
                user_response=request.user_response,
                user_id=UUID(user_id),
            ):
                yield f"event: {event_name}\n"
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            yield "event: done\n"
            yield "data: {\"status\":\"completed\"}\n\n"
        except ValueError as exc:
            yield "event: error\n"
            yield f"data: {json.dumps({'message': str(exc), 'status_code': 404}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            yield "event: error\n"
            yield f"data: {json.dumps({'message': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
