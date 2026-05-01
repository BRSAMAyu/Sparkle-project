from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.services.simulation.scenario_templates import normalize_scenario_key
from app.services.simulation.seed_extractor import SeedExtractor
from app.services.simulation.simulation_engine import SimulationEngine

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
    anchor_material: str | None = Field(default=None, description="锚点材料：错题、课文、概念定义等")
    anchor_type: str | None = Field(
        default=None,
        description="锚点类型：error_record / concept / textbook_passage / case / historical_source",
    )
    anchor_id: str | None = Field(default=None, description="锚点材料的来源 ID")
    learning_objective: str | None = Field(default=None, description="用户希望通过模拟获得的具体目标")


class SimulationContinueRequest(BaseModel):
    user_response: str = Field(..., min_length=1, description="用户在互动节点给出的回应")
    planned_round_count: int | None = Field(
        default=None,
        ge=3,
        le=12,
        description="运行中更新后的目标轮数",
    )


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
    try:
        mastery_rows = await db.execute(
            select(KnowledgeNode.name, UserNodeStatus.mastery_score)
            .join(UserNodeStatus, UserNodeStatus.node_id == KnowledgeNode.id)
            .where(UserNodeStatus.user_id == UUID(user_id))
            .order_by(UserNodeStatus.mastery_score.asc())
            .limit(8)
        )
        mastery_gaps = [
            str(name).strip().casefold()
            for name, score in mastery_rows.all()
            if str(name).strip() and float(score or 0.0) < 60
        ]
        if mastery_gaps:
            seeds = sorted(
                seeds,
                key=lambda seed: (
                    0
                    if any(gap in seed.topic.casefold() for gap in mastery_gaps)
                    else 1,
                    -seed.relevance_score,
                ),
            )
    except Exception:
        pass
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
        anchor_material=request.anchor_material,
        anchor_type=request.anchor_type,
        anchor_id=request.anchor_id,
        learning_objective=request.learning_objective,
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
                anchor_material=request.anchor_material,
                anchor_type=request.anchor_type,
                anchor_id=request.anchor_id,
                learning_objective=request.learning_objective,
                user_id=UUID(user_id),
            ):
                yield f"event: {event_name}\n"
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            yield "event: done\n"
            yield "data: {\"status\":\"completed\"}\n\n"
        except Exception as exc:
            yield "event: error\n"
            yield f"data: {json.dumps({'message': '仿真过程出现错误，请稍后重试'}, ensure_ascii=False)}\n\n"
            logger.error(f"Simulation stream error: {exc}", exc_info=True)

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
            updated_planned_round_count=request.planned_round_count,
            user_id=UUID(user_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return session.to_dict()


# route-tier: authed
@router.get("/sessions/{session_id}")
async def get_learning_simulation_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    engine = SimulationEngine(db)
    try:
        session = await engine.get_session(
            session_id=session_id,
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
                updated_planned_round_count=request.planned_round_count,
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
            yield f"data: {json.dumps({'message': '仿真过程出现错误，请稍后重试'}, ensure_ascii=False)}\n\n"
            logger.error(f"Simulation continue stream error: {exc}", exc_info=True)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
