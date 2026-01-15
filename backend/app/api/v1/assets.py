"""
Learning Assets API (学习资产API)

Provides endpoints for managing learning assets:
- Create assets from selections
- Activate assets (INBOX -> ACTIVE)
- List and filter assets
- Record suggestion feedback
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from loguru import logger

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.learning_assets import (
    AssetStatus,
    AssetKind,
    UserSuggestionResponse,
)
from app.services.learning_asset_service import learning_asset_service


router = APIRouter(prefix="/assets", tags=["assets"])


# ============ Schemas ============

class CreateAssetRequest(BaseModel):
    """Request to create a new learning asset"""
    selected_text: str = Field(..., description="Text that was selected", max_length=1000)
    translation: Optional[str] = Field(None, description="Translated text")
    definition: Optional[str] = Field(None, description="Definition or meaning")
    example: Optional[str] = Field(None, description="Example sentence")
    source_file_id: Optional[str] = Field(None, description="Source document UUID")
    context_before: Optional[str] = Field(None, description="Text before selection", max_length=500)
    context_after: Optional[str] = Field(None, description="Text after selection", max_length=500)
    page_no: Optional[int] = Field(None, description="Page number")
    language_code: str = Field(default="en", description="Source language code")
    asset_kind: str = Field(default="WORD", description="Asset type: WORD, SENTENCE, CONCEPT")
    activate_immediately: bool = Field(default=False, description="Skip inbox, activate directly")


class AssetResponse(BaseModel):
    """Response for a single asset"""
    id: str
    status: str
    asset_kind: str
    headword: str
    definition: Optional[str]
    translation: Optional[str]
    example: Optional[str]
    language_code: str
    lookup_count: int
    review_count: int
    review_success_rate: float
    inbox_expires_at: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class AssetListResponse(BaseModel):
    """Response for asset listing"""
    assets: List[AssetResponse]
    total: int
    limit: int
    offset: int


class SuggestionFeedbackRequest(BaseModel):
    """Request to record feedback on a suggestion"""
    suggestion_log_id: str = Field(..., description="Suggestion log UUID")
    response: str = Field(..., description="Response: ACCEPT, DISMISS, IGNORE")
    asset_id: Optional[str] = Field(None, description="Created asset ID if accepted")


# ============ Endpoints ============

@router.post("", response_model=AssetResponse, summary="创建学习资产")
async def create_asset(
    request: CreateAssetRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new learning asset from a text selection.

    This is called when user explicitly saves a word/phrase to their collection.
    """
    try:
        # Parse source_file_id if provided
        source_file_uuid = None
        if request.source_file_id:
            try:
                source_file_uuid = UUID(request.source_file_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid source_file_id format")

        # Parse asset_kind
        try:
            kind = AssetKind(request.asset_kind.upper())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid asset_kind. Must be one of: {[k.value for k in AssetKind]}"
            )

        # Determine initial status
        initial_status = AssetStatus.ACTIVE if request.activate_immediately else AssetStatus.INBOX

        # Create asset
        asset = await learning_asset_service.create_asset_from_selection(
            db=db,
            user_id=current_user.id,
            selected_text=request.selected_text,
            translation=request.translation,
            definition=request.definition,
            example=request.example,
            source_file_id=source_file_uuid,
            context_before=request.context_before,
            context_after=request.context_after,
            page_no=request.page_no,
            language_code=request.language_code,
            asset_kind=kind,
            initial_status=initial_status,
        )

        await db.commit()

        logger.info(f"Created asset {asset.id} for user {current_user.id}")

        return _asset_to_response(asset)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create asset: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create asset: {str(e)}")


@router.post("/{asset_id}/activate", response_model=AssetResponse, summary="激活资产")
async def activate_asset(
    asset_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Activate an asset (move from INBOX to ACTIVE).

    This makes the asset eligible for review scheduling.
    """
    try:
        asset_uuid = UUID(asset_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid asset_id format")

    asset = await learning_asset_service.get_asset_by_id(db, asset_uuid, current_user.id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    if asset.status != AssetStatus.INBOX.value:
        raise HTTPException(
            status_code=400,
            detail=f"Can only activate INBOX assets. Current status: {asset.status}"
        )

    asset = await learning_asset_service.activate_asset(db, asset)
    await db.commit()

    logger.info(f"Activated asset {asset_id} for user {current_user.id}")

    return _asset_to_response(asset)


@router.post("/{asset_id}/archive", response_model=AssetResponse, summary="归档资产")
async def archive_asset(
    asset_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Archive an asset.

    Archived assets are hidden from default views but can be restored.
    """
    try:
        asset_uuid = UUID(asset_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid asset_id format")

    asset = await learning_asset_service.get_asset_by_id(db, asset_uuid, current_user.id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    if asset.status == AssetStatus.ARCHIVED.value:
        raise HTTPException(status_code=400, detail="Asset is already archived")

    asset = await learning_asset_service.archive_asset(db, asset, reason="user_archive")
    await db.commit()

    logger.info(f"Archived asset {asset_id} for user {current_user.id}")

    return _asset_to_response(asset)


@router.get("", response_model=AssetListResponse, summary="获取资产列表")
async def list_assets(
    status: Optional[str] = Query(None, description="Filter by status: INBOX, ACTIVE, ARCHIVED"),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List user's learning assets with optional status filter.
    """
    # Parse status filter
    status_filter = None
    if status:
        try:
            status_filter = AssetStatus(status.upper())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {[s.value for s in AssetStatus]}"
            )

    assets = await learning_asset_service.get_user_assets(
        db=db,
        user_id=current_user.id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )

    return AssetListResponse(
        assets=[_asset_to_response(a) for a in assets],
        total=len(assets),  # TODO: Add actual count query for pagination
        limit=limit,
        offset=offset,
    )


@router.get("/{asset_id}", response_model=AssetResponse, summary="获取单个资产")
async def get_asset(
    asset_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single asset by ID.
    """
    try:
        asset_uuid = UUID(asset_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid asset_id format")

    asset = await learning_asset_service.get_asset_by_id(db, asset_uuid, current_user.id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    return _asset_to_response(asset)


@router.delete("/{asset_id}", summary="删除资产")
async def delete_asset(
    asset_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Soft delete an asset.
    """
    try:
        asset_uuid = UUID(asset_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid asset_id format")

    asset = await learning_asset_service.get_asset_by_id(db, asset_uuid, current_user.id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset.soft_delete()
    await db.commit()

    logger.info(f"Deleted asset {asset_id} for user {current_user.id}")

    return {"success": True, "message": "Asset deleted"}


@router.post("/suggestions/feedback", summary="记录建议反馈")
async def record_suggestion_feedback(
    request: SuggestionFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Record user feedback on an asset suggestion.

    If dismissed, sets a cooldown to avoid re-suggesting.
    """
    try:
        suggestion_log_uuid = UUID(request.suggestion_log_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid suggestion_log_id format")

    try:
        response = UserSuggestionResponse(request.response.upper())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid response. Must be one of: {[r.value for r in UserSuggestionResponse]}"
        )

    asset_uuid = None
    if request.asset_id:
        try:
            asset_uuid = UUID(request.asset_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid asset_id format")

    try:
        await learning_asset_service.record_suggestion_feedback(
            db=db,
            user_id=current_user.id,
            suggestion_log_id=suggestion_log_uuid,
            response=response,
            asset_id=asset_uuid,
        )
        await db.commit()

        return {"success": True, "message": f"Feedback recorded: {response.value}"}

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to record feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to record feedback: {str(e)}")


# ============ Helpers ============

def _asset_to_response(asset) -> AssetResponse:
    """Convert LearningAsset model to response schema"""
    return AssetResponse(
        id=str(asset.id),
        status=asset.status,
        asset_kind=asset.asset_kind,
        headword=asset.headword,
        definition=asset.definition,
        translation=asset.translation,
        example=asset.example,
        language_code=asset.language_code,
        lookup_count=asset.lookup_count,
        review_count=asset.review_count,
        review_success_rate=asset.review_success_rate,
        inbox_expires_at=asset.inbox_expires_at.isoformat() if asset.inbox_expires_at else None,
        created_at=asset.created_at.isoformat(),
        updated_at=asset.updated_at.isoformat(),
    )
