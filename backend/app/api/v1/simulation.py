from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.services.simulation.simulation_engine import SimulationEngine
from app.services.simulation.seed_extractor import SeedExtractor

router = APIRouter(prefix="/simulation", tags=["simulation"])


class SimulationRunRequest(BaseModel):
    topic: str = Field(..., description="学习主题")
    scenario_key: str = Field(default="study_group", description="场景模板 key")


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
    extractor = SeedExtractor(db)
    seeds = await extractor.get_cached_or_generate(
        UUID(user_id),
        scenario_key=scenario_key,
        limit=max(1, min(limit, 6)),
    )
    return RecommendedSeedsResponse(
        scenario_key=scenario_key,
        seeds=[SimulationSeedResponse(**seed.to_dict()) for seed in seeds],
    )


@router.post("/run")
async def run_learning_simulation(
    request: SimulationRunRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    engine = SimulationEngine(db)
    session = await engine.run(topic=request.topic, scenario_key=request.scenario_key, user_id=UUID(user_id))
    return session.to_dict()


@router.post("/run/stream")
async def stream_learning_simulation(
    request: SimulationRunRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    engine = SimulationEngine(db)

    async def event_generator():
        try:
            async for event_name, payload in engine.stream(
                topic=request.topic,
                scenario_key=request.scenario_key,
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
