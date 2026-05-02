from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user, get_db
from app.core.metrics import (
    MARKETPLACE_ADOPTIONS_TOTAL,
    MARKETPLACE_AUTO_DEPRECATIONS_TOTAL,
    MARKETPLACE_PRIVACY_REJECTIONS_TOTAL,
)
from app.models.marketplace import MarketplacePack, PackAdoptionHistory
from app.models.user import User
from app.signals.marketplace import (
    DomainPack,
    MarketplacePersistenceService,
    SkillCard,
    compute_marketplace_quality_score,
    scan_marketplace_asset_privacy,
)

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


class AdoptRequest(BaseModel):
    confirm: bool = Field(False, description="Must be true for explicit adoption.")
    context_signature: dict[str, Any] = Field(default_factory=dict)
    trace_id: str | None = None


class RevokeRequest(BaseModel):
    reason: str = ""


class ImpactRequest(BaseModel):
    trace_id: str = Field(..., min_length=1)
    impact_type: str = Field(..., pattern="^(task|plan|source|goal_graph|recall|skill)$")
    impact_summary: str = ""
    target_id: str | None = None
    before_snapshot: dict[str, Any] = Field(default_factory=dict)
    after_snapshot: dict[str, Any] = Field(default_factory=dict)
    outcome: str = Field("pending", pattern="^(pending|success|effective|negative|failure|harmful|revoked)$")
    metadata: dict[str, Any] = Field(default_factory=dict)


class SkillCardRequest(BaseModel):
    skill_id: str | None = None
    name: str
    description: str = ""
    goal_type: str = ""
    domain: str = ""
    version: int = 1
    trigger_condition: str = ""
    action_template: str = ""
    expected_outcome: str = ""
    prerequisites: list[str] = Field(default_factory=list)
    contraindications: list[str] = Field(default_factory=list)
    evidence_grade: int = 2
    evidence_summary: str = ""
    episode_count: int = 0
    success_rate: float = 0.0
    context_signatures: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "active"


class PackRequest(BaseModel):
    pack_id: str | None = None
    name: str
    description: str = ""
    domain: str = ""
    version: int = 1
    source: str = "system"
    status: str = "active"
    node_schema: dict[str, Any] = Field(default_factory=dict)
    task_templates: list[dict[str, Any]] = Field(default_factory=list)
    risk_rules: list[dict[str, Any]] = Field(default_factory=list)
    skill_ids: list[str] = Field(default_factory=list)
    quality_evidence: dict[str, Any] = Field(default_factory=dict)


def _raise_marketplace_error(exc: ValueError) -> None:
    message = str(exc)
    if message.startswith("pii_detected"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc
    if message in {"explicit_confirmation_required", "iron_law_violations"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc
    if message.endswith("_not_found") or message == "asset_not_available":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc


@router.get("/skills")
async def list_skills(
    domain: str | None = Query(default=None),
    goal_type: str | None = Query(default=None),
    include_deprecated: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    service = MarketplacePersistenceService(db)
    skills = await service.list_skills(domain=domain, goal_type=goal_type, include_deprecated=include_deprecated)
    return {"items": [service.serialize_skill(skill) for skill in skills]}


@router.get("/skills/{skill_id}")
async def get_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    service = MarketplacePersistenceService(db)
    skill = await service.get_skill(skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="skill_not_found")
    return service.serialize_skill(skill)


@router.get("/skills/{skill_id}/preview")
async def preview_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    service = MarketplacePersistenceService(db)
    skill = await service.get_skill(skill_id)
    if skill is None or skill.status != "active":
        raise HTTPException(status_code=404, detail="skill_not_available")
    return service.preview_asset(skill)


@router.post("/skills/{skill_id}/adopt", status_code=status.HTTP_201_CREATED)
async def adopt_skill(
    skill_id: str,
    payload: AdoptRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = MarketplacePersistenceService(db)
    try:
        adoption = await service.adopt_asset(
            user_id=current_user.id,
            asset_id=skill_id,
            asset_type="skill",
            confirm=payload.confirm,
            context_signature=payload.context_signature,
            trace_id=payload.trace_id,
        )
    except ValueError as exc:
        _raise_marketplace_error(exc)
    MARKETPLACE_ADOPTIONS_TOTAL.labels(asset_type="skill", status="active").inc()
    return service.serialize_adoption(adoption)


@router.get("/packs")
async def list_packs(
    domain: str | None = Query(default=None),
    include_deprecated: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    service = MarketplacePersistenceService(db)
    packs = await service.list_packs(domain=domain, include_deprecated=include_deprecated)
    return {"items": [service.serialize_pack(pack) for pack in packs]}


@router.get("/packs/{pack_id}")
async def get_pack(
    pack_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    service = MarketplacePersistenceService(db)
    pack = await service.get_pack(pack_id)
    if pack is None:
        raise HTTPException(status_code=404, detail="pack_not_found")
    return service.serialize_pack(pack)


@router.get("/packs/{pack_id}/preview")
async def preview_pack(
    pack_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    del current_user
    service = MarketplacePersistenceService(db)
    pack = await service.get_pack(pack_id)
    if pack is None or pack.status != "active":
        raise HTTPException(status_code=404, detail="pack_not_available")
    return service.preview_asset(pack)


@router.post("/packs/{pack_id}/adopt", status_code=status.HTTP_201_CREATED)
async def adopt_pack(
    pack_id: str,
    payload: AdoptRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = MarketplacePersistenceService(db)
    try:
        adoption = await service.adopt_asset(
            user_id=current_user.id,
            asset_id=pack_id,
            asset_type="pack",
            confirm=payload.confirm,
            context_signature=payload.context_signature,
            trace_id=payload.trace_id,
        )
    except ValueError as exc:
        _raise_marketplace_error(exc)
    MARKETPLACE_ADOPTIONS_TOTAL.labels(asset_type="pack", status="active").inc()
    return service.serialize_adoption(adoption)


@router.post("/adoptions/{adoption_id}/revoke")
async def revoke_adoption(
    adoption_id: UUID,
    payload: RevokeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = MarketplacePersistenceService(db)
    try:
        adoption = await service.revoke_adoption(user_id=current_user.id, adoption_id=adoption_id, reason=payload.reason)
    except ValueError as exc:
        _raise_marketplace_error(exc)
    MARKETPLACE_ADOPTIONS_TOTAL.labels(asset_type=adoption.asset_type, status="revoked").inc()
    return service.serialize_adoption(adoption)


@router.get("/adoptions/{adoption_id}/impact")
async def list_adoption_impact(
    adoption_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = MarketplacePersistenceService(db)
    result = await db.execute(
        select(PackAdoptionHistory).where(
            PackAdoptionHistory.adoption_id == adoption_id,
            PackAdoptionHistory.user_id == current_user.id,
            PackAdoptionHistory.deleted_at.is_(None),
        )
    )
    return {"items": [service.serialize_history(item) for item in result.scalars().all()]}


@router.post("/adoptions/{adoption_id}/impact", status_code=status.HTTP_201_CREATED)
async def record_adoption_impact(
    adoption_id: UUID,
    payload: ImpactRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = MarketplacePersistenceService(db)
    try:
        history = await service.record_impact(
            user_id=current_user.id,
            adoption_id=adoption_id,
            trace_id=payload.trace_id,
            impact_type=payload.impact_type,
            impact_summary=payload.impact_summary,
            target_id=payload.target_id,
            before_snapshot=payload.before_snapshot,
            after_snapshot=payload.after_snapshot,
            outcome=payload.outcome,
            metadata=payload.metadata,
        )
    except ValueError as exc:
        _raise_marketplace_error(exc)
    if payload.outcome in {"negative", "failure", "harmful"}:
        MARKETPLACE_AUTO_DEPRECATIONS_TOTAL.labels(asset_type=history.asset_type, reason="negative_feedback_observed").inc()
    return service.serialize_history(history)


@router.post("/admin/skills", status_code=status.HTTP_201_CREATED)
async def admin_register_skill(
    payload: SkillCardRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_active_superuser),
):
    service = MarketplacePersistenceService(db)
    card = SkillCard(
        card_id=payload.skill_id or "",
        name=payload.name,
        description=payload.description,
        goal_type=payload.goal_type,
        domain=payload.domain,
        author_id=str(admin.id),
        version=payload.version,
        trigger_condition=payload.trigger_condition,
        action_template=payload.action_template,
        expected_outcome=payload.expected_outcome,
        prerequisites=payload.prerequisites,
        evidence_grade=payload.evidence_grade,
        evidence_summary=payload.evidence_summary,
        episode_count=payload.episode_count,
        success_rate=payload.success_rate,
        context_signatures=payload.context_signatures,
        status=payload.status,
    )
    try:
        skill = await service.register_skill_card(
            card,
            source_skill_id=payload.skill_id,
            contraindications=payload.contraindications,
            governance={"registered_by": "admin", "admin_id": str(admin.id)},
        )
    except ValueError as exc:
        if str(exc).startswith("pii_detected"):
            MARKETPLACE_PRIVACY_REJECTIONS_TOTAL.labels(asset_type="skill").inc()
        _raise_marketplace_error(exc)
    return service.serialize_skill(skill)


@router.post("/admin/packs", status_code=status.HTTP_201_CREATED)
async def admin_register_pack(
    payload: PackRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_active_superuser),
):
    service = MarketplacePersistenceService(db)
    pack_asset = DomainPack(
        pack_id=payload.pack_id or "",
        name=payload.name,
        description=payload.description,
        domain=payload.domain,
        version=payload.version,
        source=payload.source,
        status=payload.status,
        node_schema=payload.node_schema,
        task_templates=payload.task_templates,
        risk_rules=payload.risk_rules,
        skill_ids=payload.skill_ids,
        quality_evidence=payload.quality_evidence,
        governance={"registered_by": "admin", "admin_id": str(admin.id)},
    )
    privacy_report = scan_marketplace_asset_privacy(pack_asset)
    if not privacy_report["passed"]:
        MARKETPLACE_PRIVACY_REJECTIONS_TOTAL.labels(asset_type="pack").inc()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"pii_detected:{','.join(privacy_report['categories'])}",
        )
    existing = await service.get_pack(pack_asset.pack_id)
    quality_score = compute_marketplace_quality_score(
        success_rate=float(payload.quality_evidence.get("success_rate", 0.0) or 0.0),
        evidence_grade=int(payload.quality_evidence.get("evidence_grade", 0) or 0),
        negative_feedback_rate=0.0,
        applicability_score=0.35 + min(len(payload.task_templates), 5) * 0.1,
    )
    if existing:
        existing.previous_versions = [*(existing.previous_versions or []), service.serialize_pack(existing)]
        existing.name = payload.name
        existing.description = payload.description
        existing.domain = payload.domain
        existing.version = payload.version
        existing.source = payload.source
        existing.status = payload.status
        existing.node_schema = payload.node_schema
        existing.task_templates = payload.task_templates
        existing.risk_rules = payload.risk_rules
        existing.skill_ids = payload.skill_ids
        existing.quality_evidence = payload.quality_evidence
        existing.quality_score = quality_score
        existing.privacy_report = privacy_report
        existing.governance = pack_asset.governance
        await db.flush()
        return service.serialize_pack(existing)

    pack = MarketplacePack(
        pack_id=pack_asset.pack_id,
        name=payload.name,
        description=payload.description,
        domain=payload.domain,
        version=payload.version,
        source=payload.source,
        status=payload.status,
        node_schema=payload.node_schema,
        task_templates=payload.task_templates,
        risk_rules=payload.risk_rules,
        skill_ids=payload.skill_ids,
        quality_evidence=payload.quality_evidence,
        quality_score=quality_score,
        privacy_report=privacy_report,
        governance=pack_asset.governance,
    )
    db.add(pack)
    await db.flush()
    return service.serialize_pack(pack)


@router.post("/admin/skills/{skill_id}/rollback")
async def admin_rollback_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_active_superuser),
):
    del admin
    service = MarketplacePersistenceService(db)
    try:
        skill = await service.rollback_skill(skill_id)
    except ValueError as exc:
        _raise_marketplace_error(exc)
    return service.serialize_skill(skill)


@router.post("/admin/packs/{pack_id}/rollback")
async def admin_rollback_pack(
    pack_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_active_superuser),
):
    del admin
    service = MarketplacePersistenceService(db)
    try:
        pack = await service.rollback_pack(pack_id)
    except ValueError as exc:
        _raise_marketplace_error(exc)
    return service.serialize_pack(pack)
