from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.models.user import User
from app.orchestration.clarification_voi_service import ClarificationVOIService
from app.orchestration.idea_crystallization_service import IdeaCrystallizationService

router = APIRouter(prefix="/brain", tags=["brain"])


class IdeaClarifyRequest(BaseModel):
    message: str = Field(min_length=1)
    intent: str | None = None
    extracted_entities: dict[str, Any] | None = None
    conversation_context: list[dict[str, Any]] | None = None
    uncertainty_score: float = 0.0


class IdeaCommitRequest(BaseModel):
    message: str = Field(min_length=1)
    intent: str | None = None
    extracted_entities: dict[str, Any] | None = None
    conversation_context: list[dict[str, Any]] | None = None
    contract_overrides: dict[str, Any] | None = None


@router.post("/idea/clarify")
async def clarify_idea(
    payload: IdeaClarifyRequest,
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    crystallizer = IdeaCrystallizationService()
    voi_service = ClarificationVOIService()

    result = crystallizer.crystallize(
        message=payload.message,
        intent=payload.intent,
        extracted_entities=payload.extracted_entities,
        conversation_context=payload.conversation_context,
    )
    voi = voi_service.rank(
        contract=result.draft_goal_contract,
        ambiguity_profile=result.ambiguity_profile,
        uncertainty_score=payload.uncertainty_score,
        max_questions=3,
    )
    return {
        "success": True,
        "message": "Idea clarification generated",
        "data": {
            "intent_hypotheses": result.intent_hypotheses,
            "ambiguity_profile": result.ambiguity_profile,
            "draft_goal_contract": result.draft_goal_contract,
            "recommended_clarifications": voi.clarification_priority_points,
            "voi_score": voi.voi_score,
        },
    }


@router.post("/idea/commit")
async def commit_idea(
    payload: IdeaCommitRequest,
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    crystallizer = IdeaCrystallizationService()
    result = crystallizer.crystallize(
        message=payload.message,
        intent=payload.intent,
        extracted_entities=payload.extracted_entities,
        conversation_context=payload.conversation_context,
    )

    contract = dict(result.draft_goal_contract)
    overrides = payload.contract_overrides if isinstance(payload.contract_overrides, dict) else {}
    for key, value in overrides.items():
        contract[key] = value

    plan_ir_preview = {
        "goal": contract.get("goal", ""),
        "milestones": contract.get("milestones", []),
        "acceptance_criteria": contract.get("acceptance_criteria", []),
        "risks": contract.get("risks", []),
        "assumptions": contract.get("assumptions", []),
        "tradeoffs": contract.get("tradeoffs", []),
    }
    return {
        "success": True,
        "message": "Idea committed to contract",
        "data": {
            "goal_contract": contract,
            "plan_ir_preview": plan_ir_preview,
            "ambiguity_profile": result.ambiguity_profile,
            "intent_hypotheses": result.intent_hypotheses,
        },
    }
