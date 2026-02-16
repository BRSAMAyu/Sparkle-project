"""
Seed Templates 2.0 API
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user
from app.config import settings
from app.db.session import get_db
from app.models.seed_template import SeedTemplate, SeedTemplatePack, SeedTemplateVersion
from app.models.user import User
from app.schemas.seed_template import (
    SeedTemplateForkRequest,
    SeedTemplateInstantiateRequest,
    SeedTemplateInstantiateResponse,
    SeedTemplatePackCreate,
    SeedTemplatePackInfo,
    SeedTemplatePublishRequest,
    SeedTemplateReviewDecisionRequest,
    SeedTemplateSignalRequest,
    SeedTemplateSubscriptionInfo,
    SeedTemplateSubscribeRequest,
    SeedTemplateListItem,
    SeedTemplateVersionCreate,
    SeedTemplateVersionInfo,
    TemplatePackScenarioEnum,
    TemplateVisibilityEnum,
)
from app.services.seed_template_service import SeedTemplateService

router = APIRouter()
service = SeedTemplateService()


def _ensure_feature_enabled(enabled: bool, detail: str = "Feature disabled") -> None:
    if not enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _pack_info(pack: SeedTemplatePack) -> SeedTemplatePackInfo:
    return SeedTemplatePackInfo.model_validate(pack)


def _version_info(version: SeedTemplateVersion) -> SeedTemplateVersionInfo:
    return SeedTemplateVersionInfo.model_validate(version)


@router.get("/seed-templates/packs", summary="List seed template packs")
async def list_seed_template_packs(
    scenario_type: TemplatePackScenarioEnum | None = Query(default=None),
    visibility: TemplateVisibilityEnum | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_feature_enabled(settings.ENABLE_SEED_TEMPLATE_PACKS_V1)
    packs = await service.list_packs(
        db,
        scenario_type=scenario_type.value if scenario_type else None,
        visibility=visibility.value if visibility else None,
        current_user_id=current_user.id,
        limit=limit,
    )
    return {"success": True, "message": "ok", "data": [_pack_info(pack) for pack in packs], "meta": {"count": len(packs)}}


@router.post("/seed-templates/packs", status_code=status.HTTP_201_CREATED, summary="Create seed template pack")
async def create_seed_template_pack(
    payload: SeedTemplatePackCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_feature_enabled(settings.ENABLE_SEED_TEMPLATE_PACKS_V1)
    pack = await service.create_pack(db, data=payload.model_dump(), owner_id=current_user.id)
    await db.commit()
    return {"success": True, "message": "created", "data": _pack_info(pack)}


@router.get("/seed-templates/packs/{pack_id}/templates", summary="List templates in pack")
async def list_seed_templates_by_pack(
    pack_id: UUID,
    include_official: bool = Query(default=True),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    _ensure_feature_enabled(settings.ENABLE_SEED_TEMPLATE_PACKS_V1)
    templates = await service.list_templates(
        db,
        pack_id=pack_id,
        include_official=include_official,
        limit=limit,
    )
    data = [SeedTemplateListItem.model_validate(item) for item in templates]
    return {"success": True, "message": "ok", "data": data, "meta": {"count": len(data)}}


@router.get("/seed-templates/{template_id}", summary="Get template")
async def get_seed_template(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_feature_enabled(settings.ENABLE_SEED_TEMPLATE_PACKS_V1)
    _ = current_user
    template = await service.get_template(db, template_id=template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    current_version = await service._get_current_or_latest_version(db, template.id)
    data = {
        "id": str(template.id),
        "pack_id": str(template.pack_id),
        "name": template.name,
        "template_role": template.template_role,
        "current_version_id": str(template.current_version_id) if template.current_version_id else None,
        "forked_from_template_id": str(template.forked_from_template_id) if template.forked_from_template_id else None,
        "forked_from_version_id": str(template.forked_from_version_id) if template.forked_from_version_id else None,
        "owner_id": str(template.owner_id) if template.owner_id else None,
        "is_official": bool(template.is_official),
        "is_featured": bool(template.is_featured),
        "created_at": template.created_at,
        "updated_at": template.updated_at,
        "current_version": _version_info(current_version) if current_version else None,
    }
    return {"success": True, "message": "ok", "data": data}


@router.get("/seed-templates/{template_id}/versions", summary="List template versions")
async def list_seed_template_versions(
    template_id: UUID,
    include_draft: bool = Query(default=True),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    _ensure_feature_enabled(settings.ENABLE_SEED_TEMPLATE_PACKS_V1)
    template = await service.get_template(db, template_id=template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    versions = await service.list_versions(
        db,
        template_id=template_id,
        include_draft=include_draft,
        limit=limit,
    )
    return {
        "success": True,
        "message": "ok",
        "data": [SeedTemplateVersionInfo.model_validate(item) for item in versions],
        "meta": {"count": len(versions)},
    }


@router.post("/seed-templates/{template_id}/fork", status_code=status.HTTP_201_CREATED, summary="Fork template")
async def fork_seed_template(
    template_id: UUID,
    payload: SeedTemplateForkRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_feature_enabled(settings.ENABLE_SEED_TEMPLATE_FORK_V1)
    template = await service.get_template(db, template_id=template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    forked = await service.fork_template(
        db,
        template=template,
        owner_id=current_user.id,
        target_pack_id=payload.target_pack_id,
        name=payload.name,
    )
    await db.commit()
    return {"success": True, "message": "forked", "data": {"template_id": str(forked.id)}}


@router.post("/seed-templates/{template_id}/versions", summary="Create or update version")
async def create_seed_template_version(
    template_id: UUID,
    payload: SeedTemplateVersionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_feature_enabled(settings.ENABLE_SEED_TEMPLATE_PACKS_V1)
    template = await service.get_template(db, template_id=template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    if template.owner_id and template.owner_id != current_user.id and not getattr(current_user, "is_superuser", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No permission")
    version = await service.create_or_update_version(
        db,
        template=template,
        created_by=current_user.id,
        body=payload.body,
        schema_json=payload.schema_json,
        variables_schema=payload.variables_schema,
        change_log=payload.change_log,
        overwrite_draft=payload.overwrite_draft,
    )
    await db.commit()
    return {"success": True, "message": "ok", "data": _version_info(version)}


@router.post("/seed-templates/{template_id}/publish", summary="Publish template version")
async def publish_seed_template(
    template_id: UUID,
    payload: SeedTemplatePublishRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_feature_enabled(settings.ENABLE_SEED_TEMPLATE_PACKS_V1)
    template = await service.get_template(db, template_id=template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    try:
        version = await service.publish_version(
            db,
            template=template,
            actor_id=current_user.id,
            version_id=payload.version_id,
            is_superuser=bool(getattr(current_user, "is_superuser", False)),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await db.commit()
    return {"success": True, "message": "published", "data": _version_info(version)}


@router.post("/seed-templates/{template_id}/signals", summary="Submit community signal")
async def submit_seed_template_signal(
    template_id: UUID,
    payload: SeedTemplateSignalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_feature_enabled(settings.ENABLE_SEED_TEMPLATE_COMMUNITY_SUPERVISION_V1)
    template = await service.get_template(db, template_id=template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    version = await service._resolve_publish_version(db, template.id, payload.version_id)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    signal, promotion = await service.add_signal(
        db,
        version=version,
        user_id=current_user.id,
        signal_type=payload.signal_type.value,
        score=payload.score,
        meta=payload.meta,
    )
    await db.commit()
    return {
        "success": True,
        "message": "recorded",
        "data": {
            "signal_id": str(signal.id),
            "promotion_state": promotion.promotion_state,
            "support": promotion.support,
            "adoption_rate": promotion.adoption_rate,
            "negative_feedback_rate": promotion.negative_feedback_rate,
            "report_rate": promotion.report_rate,
        },
    }


@router.post("/seed-templates/{template_id}/subscribe", summary="Subscribe template")
async def subscribe_seed_template(
    template_id: UUID,
    payload: SeedTemplateSubscribeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_feature_enabled(settings.ENABLE_SEED_TEMPLATE_PACKS_V1)
    sub = await service.subscribe(db, template_id=template_id, user_id=current_user.id, priority=payload.priority)
    await db.commit()
    return {"success": True, "message": "subscribed", "data": {"id": str(sub.id)}}


@router.delete("/seed-templates/{template_id}/subscribe", summary="Unsubscribe template")
async def unsubscribe_seed_template(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_feature_enabled(settings.ENABLE_SEED_TEMPLATE_PACKS_V1)
    success = await service.unsubscribe(db, template_id=template_id, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    await db.commit()
    return {"success": True, "message": "unsubscribed", "data": None}


@router.get("/seed-templates/subscriptions/me", summary="My template subscriptions")
async def get_my_seed_template_subscriptions(
    only_enabled: bool = Query(default=True),
    limit: int = Query(default=100, ge=1, le=300),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_feature_enabled(settings.ENABLE_SEED_TEMPLATE_PACKS_V1)
    subscriptions = await service.list_subscriptions(
        db,
        user_id=current_user.id,
        only_enabled=only_enabled,
        limit=limit,
    )
    data = [SeedTemplateSubscriptionInfo.model_validate(item) for item in subscriptions]
    return {"success": True, "message": "ok", "data": data, "meta": {"count": len(data)}}


@router.post("/seed-templates/{template_id}/instantiate", response_model=SeedTemplateInstantiateResponse, summary="Instantiate template")
async def instantiate_seed_template(
    template_id: UUID,
    payload: SeedTemplateInstantiateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ensure_feature_enabled(settings.ENABLE_SEED_TEMPLATE_PACKS_V1)
    _ = current_user
    template = await service.get_template(db, template_id=template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    version, rendered, unresolved, metadata = await service.instantiate(
        db,
        template=template,
        variables=payload.variables,
        version_id=payload.version_id,
        context=payload.template_instantiation_context,
    )
    return SeedTemplateInstantiateResponse(
        template_id=template.id,
        template_version_id=version.id,
        seed_template_pack=str(template.pack_id),
        seed_template_source=metadata.get("seed_template_source", "public"),
        rendered_body=rendered,
        unresolved_variables=unresolved,
        metadata=metadata,
    )


@router.get("/admin/seed-templates/review-queue", summary="Admin review queue")
async def admin_seed_template_review_queue(
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    _ensure_feature_enabled(settings.ENABLE_SEED_TEMPLATE_COMMUNITY_SUPERVISION_V1)
    _ = current_user
    queue = await service.get_review_queue(db)
    return {"success": True, "message": "ok", "data": [_version_info(item) for item in queue]}


@router.post("/admin/seed-templates/{version_id}/approve", summary="Admin approve version")
async def admin_seed_template_approve(
    version_id: UUID,
    payload: SeedTemplateReviewDecisionRequest,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    _ensure_feature_enabled(settings.ENABLE_SEED_TEMPLATE_COMMUNITY_SUPERVISION_V1)
    _ = current_user
    try:
        version = await service.admin_review(db, version_id=version_id, approve=True, note=payload.note)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await db.commit()
    return {"success": True, "message": "approved", "data": _version_info(version)}


@router.post("/admin/seed-templates/{version_id}/reject", summary="Admin reject version")
async def admin_seed_template_reject(
    version_id: UUID,
    payload: SeedTemplateReviewDecisionRequest,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    _ensure_feature_enabled(settings.ENABLE_SEED_TEMPLATE_COMMUNITY_SUPERVISION_V1)
    _ = current_user
    try:
        version = await service.admin_review(db, version_id=version_id, approve=False, note=payload.note)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await db.commit()
    return {"success": True, "message": "rejected", "data": _version_info(version)}


@router.get("/admin/seed-templates/promotion-dashboard", summary="Admin promotion dashboard")
async def admin_seed_template_dashboard(
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    _ensure_feature_enabled(settings.ENABLE_SEED_TEMPLATE_COMMUNITY_SUPERVISION_V1)
    _ = current_user
    dashboard = await service.promotion_dashboard(db)
    return {"success": True, "message": "ok", "data": dashboard}
