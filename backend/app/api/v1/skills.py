from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.aurora_stage21 import SharedSkill, UserSkill
from app.models.user import User
from app.services.skill_extract_service import SkillExtractService
from app.services.skill_schema import draft_to_payload
from app.services.skill_share import SkillShareService
from app.services.skill_store import SkillStoreService

router = APIRouter(prefix="/skills", tags=["skills"])


def _serialize_skill(skill: UserSkill) -> dict[str, object]:
    return {
        "id": str(skill.id),
        "name": skill.name,
        "pattern_template": skill.pattern_template,
        "activation_conditions": skill.activation_conditions or [],
        "examples": skill.examples or [],
        "privacy_level": skill.privacy_level,
        "usage_count": int(skill.usage_count or 0),
        "last_activated_at": skill.last_activated_at,
        "active": bool(skill.active),
        "forked_from_share_id": str(skill.forked_from_share_id) if skill.forked_from_share_id else None,
        "forked_at": skill.forked_at,
        "shared_catalog_id": str(skill.shared_catalog_id) if skill.shared_catalog_id else None,
        "schema_version": skill.schema_version,
        "created_at": skill.created_at,
        "updated_at": skill.updated_at,
    }


def _serialize_shared_skill(skill: SharedSkill) -> dict[str, object]:
    return {
        "id": str(skill.id),
        "share_slug": skill.share_slug,
        "name": skill.name,
        "pattern_template": skill.pattern_template,
        "activation_conditions": skill.activation_conditions or [],
        "examples": skill.examples or [],
        "author_label": skill.author_label,
        "published_at": skill.published_at,
    }


# route-tier: authed
@router.get("")
async def list_skills(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = await SkillStoreService(db).list_user_skills(user_id=current_user.id)
    return {"items": [_serialize_skill(item) for item in items]}


# route-tier: authed
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_skill(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        skill = await SkillStoreService(db).create_skill(user_id=current_user.id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return _serialize_skill(skill)


# route-tier: authed
@router.put("/{skill_id}")
async def update_skill(
    skill_id: UUID,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        skill = await SkillStoreService(db).update_skill(user_id=current_user.id, skill_id=skill_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _serialize_skill(skill)


# route-tier: authed
@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    skill_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await SkillStoreService(db).delete_skill(user_id=current_user.id, skill_id=skill_id)


# route-tier: authed
@router.post("/{skill_id}/toggle")
async def toggle_skill(
    skill_id: UUID,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        skill = await SkillStoreService(db).set_active(
            user_id=current_user.id,
            skill_id=skill_id,
            active=bool(payload.get("active", True)),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _serialize_skill(skill)


# route-tier: authed
@router.post("/drafts/extract")
async def extract_skill_draft(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del db, current_user
    service = SkillExtractService()
    try:
        draft = await service.generate_draft(
            trigger_type=str(payload.get("trigger_type") or ""),
            consent_text=str(payload.get("consent_text") or ""),
            user_message=str(payload.get("user_message") or ""),
            assistant_message=str(payload.get("assistant_message") or ""),
            seconds_since_response=payload.get("seconds_since_response"),
            feedback_positive=bool(payload.get("feedback_positive", False)),
            user_confirmed=bool(payload.get("user_confirmed", False)),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return {"draft": draft_to_payload(draft)}


# route-tier: authed
@router.post("/drafts/outcome")
async def record_skill_draft_outcome(payload: dict):
    SkillExtractService().record_draft_outcome(accepted=bool(payload.get("accepted", False)))
    return {"status": "ok"}


# route-tier: authed
@router.get("/shared")
async def list_shared_skills(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    items = await SkillShareService(db).list_shared_catalog(page=page, page_size=page_size)
    return {"items": [_serialize_shared_skill(item) for item in items]}


# route-tier: authed
@router.post("/{skill_id}/share")
async def share_skill(
    skill_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await SkillShareService(db).submit_share_request(user_id=current_user.id, skill_id=skill_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return result


# route-tier: authed
@router.post("/{skill_id}/unshare")
async def unshare_skill(
    skill_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        skill = await SkillShareService(db).withdraw_share(user_id=current_user.id, skill_id=skill_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _serialize_skill(skill)


# route-tier: authed
@router.post("/shared/{shared_skill_id}/fork", status_code=status.HTTP_201_CREATED)
async def fork_shared_skill(
    shared_skill_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        skill = await SkillStoreService(db).fork_shared_skill(user_id=current_user.id, shared_skill_id=shared_skill_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return _serialize_skill(skill)
