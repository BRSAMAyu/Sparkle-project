"""
Seed Libraries API Endpoints
种子内容库 API 接口
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import PaginationMeta
from app.schemas.seed_content import (
    BatchItemImportRequest,
    BatchItemImportResponse,
    FewShotExample,
    ItemCreate,
    ItemInfo,
    ItemListParams,
    ItemListResponse,
    ItemQueryRequest,
    ItemQueryResponse,
    ItemResponse,
    ItemUpdate,
    LibraryCreate,
    LibraryInfo,
    LibraryListParams,
    LibraryListResponse,
    LibraryResponse,
    LibraryUpdate,
    PromoteToOfficialRequest,
    RatingUpsertRequest,
    SubscriptionCreate,
    SubscriptionInfo,
    SubscriptionListResponse,
    SubscriptionResponse,
    SubscriptionUpdate,
)
from app.services.seed_library_service import SeedLibraryService

router = APIRouter()
service = SeedLibraryService()


async def _enrich_library_info(
    db: AsyncSession,
    library,
    *,
    user_id: UUID | None,
    stats: dict[str, int] | None = None,
    include_item_actions: bool = False,
) -> LibraryInfo:
    lib_info = LibraryInfo.model_validate(library)
    stats = stats or {"item_count": 0, "subscriber_count": 0}
    rating_summary = await service.get_rating_summary(db, library.id, user_id)
    lib_info.item_count = stats["item_count"]
    lib_info.subscriber_count = stats["subscriber_count"]
    lib_info.system_quality_score = library.quality_score
    lib_info.user_rating_avg = rating_summary["user_rating_avg"]
    lib_info.user_rating_count = rating_summary["user_rating_count"]
    lib_info.current_user_rating = rating_summary["current_user_rating"]
    lib_info.quality_score = service._blend_quality_score(
        library.quality_score,
        rating_summary["user_rating_avg"],
        rating_summary["user_rating_count"],
    )
    if include_item_actions:
        lib_info.adoption_next_actions = await service.get_library_adoption_actions(db, library)
    else:
        lib_info.adoption_next_actions = service.build_library_adoption_actions(library)
    return lib_info


async def _subscription_info(db: AsyncSession, subscription, library) -> SubscriptionInfo:
    actions = await service.get_library_adoption_actions(db, library) if library else []
    return SubscriptionInfo(
        id=subscription.id,
        adoption_id=subscription.id,
        user_id=subscription.user_id,
        library_id=subscription.library_id,
        library_name=library.name if library else "",
        is_enabled=subscription.is_enabled,
        priority=subscription.priority,
        notes=subscription.notes,
        adoption_next_actions=actions,
        community_share={
            "resource_type": "seed_library",
            "resource_id": str(subscription.library_id),
            "permission": "adopt",
            "privacy": "recipient_gets_private_copy",
        },
        subscribed_at=subscription.subscribed_at,
        last_used_at=subscription.last_used_at,
        created_at=subscription.created_at,
        updated_at=subscription.updated_at,
    )


# ============ 库管理接口 ============

@router.post(
    "/seed-libraries",
    response_model=LibraryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建种子内容库",
    description="创建新的种子内容库，用于存储 few-shot 示例、教学内容或回复模板"
)
async def create_library(
    library_data: LibraryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新库"""
    try:
        library = await service.create_library(db, library_data, current_user.id)
        await db.commit()
        return LibraryResponse(data=LibraryInfo.model_validate(library))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Operation failed") from e


@router.get(
    "/seed-libraries",
    response_model=LibraryListResponse,
    summary="获取种子内容库列表",
    description="浏览可用的种子内容库，支持分类、标签、可见性筛选"
)
async def list_libraries(
    category: str | None = Query(None, description="库分类"),
    visibility: str | None = Query(None, description="可见性"),
    language: str | None = Query(None, description="语言代码"),
    is_official: bool | None = Query(None, description="仅官方库"),
    is_featured: bool | None = Query(None, description="仅精选库"),
    owner_id: UUID | None = Query(None, description="创建者ID"),
    search: str | None = Query(None, description="搜索关键词"),
    tags: list[str] | None = Query(None, description="标签筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="排序方向"),
    current_user: User | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取库列表"""
    params = LibraryListParams(
        category=category,
        visibility=visibility,
        language=language,
        is_official=is_official,
        is_featured=is_featured,
        owner_id=owner_id,
        search=search,
        tags=tags,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    user_id = current_user.id if current_user else None
    libraries, total = await service.list_libraries(db, params, user_id)

    # 批量获取统计信息（避免 N+1 查询）
    lib_ids = [lib.id for lib in libraries]
    stats_map = await service.batch_get_library_stats(db, lib_ids)

    rating_map = await service.batch_get_rating_summaries(db, lib_ids, user_id)

    data = []
    for lib in libraries:
        stats = stats_map.get(lib.id, {"item_count": 0, "subscriber_count": 0})
        lib_info = LibraryInfo.model_validate(lib)
        lib_info.item_count = stats["item_count"]
        lib_info.subscriber_count = stats["subscriber_count"]
        rating_summary = rating_map.get(
            lib.id,
            {
                "user_rating_avg": None,
                "user_rating_count": 0,
                "current_user_rating": None,
            },
        )
        lib_info.system_quality_score = lib.quality_score
        lib_info.user_rating_avg = rating_summary["user_rating_avg"]
        lib_info.user_rating_count = rating_summary["user_rating_count"]
        lib_info.current_user_rating = rating_summary["current_user_rating"]
        lib_info.quality_score = service._blend_quality_score(
            lib.quality_score,
            rating_summary["user_rating_avg"],
            rating_summary["user_rating_count"],
        )
        lib_info.adoption_next_actions = service.build_library_adoption_actions(lib)
        data.append(lib_info)

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    meta = PaginationMeta(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )

    return LibraryListResponse(data=data, meta=meta)


@router.get(
    "/seed-libraries/{library_id}",
    response_model=LibraryResponse,
    summary="获取库详情",
    description="获取指定库的详细信息，包括内容项数量和订阅者数量"
)
async def get_library(
    library_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取库详情"""
    library = await service.get_library_for_user(db, library_id, current_user.id, include_items=False)
    if not library:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Library not found")

    stats = await service.get_library_stats(db, library_id)
    lib_info = await _enrich_library_info(
        db,
        library,
        user_id=current_user.id,
        stats=stats,
        include_item_actions=True,
    )
    return LibraryResponse(data=lib_info)


@router.put(
    "/seed-libraries/{library_id}",
    response_model=LibraryResponse,
    summary="更新库信息",
    description="更新库的名称、描述、标签等信息"
)
async def update_library(
    library_id: UUID,
    update_data: LibraryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新库信息"""
    try:
        is_superuser = getattr(current_user, "is_superuser", False)
        library = await service.update_library(
            db, library_id, update_data, current_user.id, is_superuser
        )
        if not library:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Library not found")

        await db.commit()
        stats = await service.get_library_stats(db, library_id)
        lib_info = await _enrich_library_info(db, library, user_id=current_user.id, stats=stats)
        return LibraryResponse(data=lib_info)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Operation failed") from e


@router.delete(
    "/seed-libraries/{library_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除库",
    description="软删除指定的库及其内容"
)
async def delete_library(
    library_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除库"""
    try:
        is_superuser = getattr(current_user, "is_superuser", False)
        success = await service.delete_library(db, library_id, current_user.id, is_superuser)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Library not found")
        await db.commit()
        return None
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


# ============ 内容项管理接口 ============

@router.post(
    "/seed-libraries/{library_id}/items",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="添加内容项",
    description="向指定库添加新的内容项"
)
async def add_item(
    library_id: UUID,
    item_data: ItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """添加内容项"""
    try:
        is_superuser = getattr(current_user, "is_superuser", False)
        item = await service.add_item(db, library_id, item_data, current_user.id, is_superuser)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Library not found")
        await db.commit()
        return ItemResponse(data=ItemInfo.model_validate(item))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Operation failed") from e


@router.post(
    "/seed-libraries/{library_id}/items/import",
    response_model=BatchItemImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="批量导入内容项",
    description="向指定种子库批量导入内容项，适用于用户上传和迁移场景"
)
async def import_items(
    library_id: UUID,
    import_data: BatchItemImportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        is_superuser = getattr(current_user, "is_superuser", False)
        created_items, errors = await service.batch_add_items(
            db,
            library_id,
            import_data.items,
            current_user.id,
            is_superuser,
        )
        await db.commit()
        return BatchItemImportResponse(
            data=[ItemInfo.model_validate(item) for item in created_items],
            imported_count=len(created_items),
            failed_count=len(errors),
            errors=errors,
            message="Import completed" if not errors else "Import completed with partial failures",
        )
    except PermissionError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Operation failed") from e


@router.get(
    "/seed-libraries/{library_id}/items",
    response_model=ItemListResponse,
    summary="获取库内容项",
    description="获取指定库的内容项列表"
)
async def get_items(
    library_id: UUID,
    item_type: str | None = Query(None, description="内容类型"),
    subject: str | None = Query(None, description="学科"),
    difficulty_level: str | None = Query(None, description="难度等级"),
    tags: list[str] | None = Query(None, description="标签筛选"),
    is_active: bool | None = Query(True, description="仅启用的项"),
    search: str | None = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    sort_by: str = Query("order_index", description="排序字段"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="排序方向"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取库内容项"""
    library = await service.get_library_for_user(db, library_id, current_user.id)
    if not library:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Library not found")

    params = ItemListParams(
        library_id=library_id,
        item_type=item_type,
        subject=subject,
        difficulty_level=difficulty_level,
        tags=tags,
        is_active=is_active,
        search=search,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    items, total = await service.get_items(db, params, user_id=current_user.id)

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    meta = PaginationMeta(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )

    data = []
    for item in items:
        item_info = ItemInfo.model_validate(item)
        item_info.adoption_next_actions = service.build_item_adoption_actions(item)
        data.append(item_info)
    return ItemListResponse(data=data, meta=meta)


@router.put(
    "/seed-libraries/items/{item_id}",
    response_model=ItemResponse,
    summary="更新内容项",
    description="更新指定的内容项"
)
async def update_item(
    item_id: UUID,
    update_data: ItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新内容项"""
    try:
        is_superuser = getattr(current_user, "is_superuser", False)
        item = await service.update_item(db, item_id, update_data, current_user.id, is_superuser)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        await db.commit()
        return ItemResponse(data=ItemInfo.model_validate(item))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Operation failed") from e


@router.put(
    "/seed-libraries/{library_id}/items/{item_id}",
    response_model=ItemResponse,
    summary="更新内容项（嵌套路径）",
    description="兼容移动端与 REST 风格的嵌套内容项更新路径"
)
async def update_item_nested(
    library_id: UUID,
    item_id: UUID,
    update_data: ItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    del library_id
    return await update_item(item_id, update_data, current_user, db)


@router.delete(
    "/seed-libraries/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除内容项",
    description="软删除指定的内容项"
)
async def delete_item(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除内容项"""
    try:
        is_superuser = getattr(current_user, "is_superuser", False)
        success = await service.delete_item(db, item_id, current_user.id, is_superuser)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        await db.commit()
        return None
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Operation failed") from e


@router.delete(
    "/seed-libraries/{library_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除内容项（嵌套路径）",
    description="兼容移动端与 REST 风格的嵌套内容项删除路径"
)
async def delete_item_nested(
    library_id: UUID,
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    del library_id
    return await delete_item(item_id, current_user, db)


# ============ 订阅管理接口 ============

@router.post(
    "/seed-libraries/subscribe/{library_id}",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="订阅库",
    description="订阅指定的内容库，使其内容可用于查询"
)
async def subscribe_library(
    library_id: UUID,
    subscription_data: SubscriptionCreate = SubscriptionCreate(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """订阅库"""
    try:
        subscription = await service.subscribe(db, library_id, current_user.id, subscription_data)
        if not subscription:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Library not found")
        await db.commit()

        library = await service.get_library(db, library_id)
        sub_info = await _subscription_info(db, subscription, library)
        return SubscriptionResponse(data=sub_info)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request parameters") from e


@router.delete(
    "/seed-libraries/subscribe/{library_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="取消订阅",
    description="取消订阅指定的内容库"
)
async def unsubscribe_library(
    library_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """取消订阅"""
    success = await service.unsubscribe(db, library_id, current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    await db.commit()
    return None


@router.put(
    "/seed-libraries/{library_id}/subscription",
    response_model=SubscriptionResponse,
    summary="更新种子库应用状态",
    description="启用/停用种子库并调整优先级，决定它在系统中的实际生效方式",
)
async def update_library_subscription(
    library_id: UUID,
    update_data: SubscriptionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    subscription = await service.update_subscription(
        db,
        library_id,
        current_user.id,
        update_data,
    )
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    await db.commit()
    library = await service.get_library(db, library_id)
    return SubscriptionResponse(data=await _subscription_info(db, subscription, library))


@router.post(
    "/seed-libraries/{library_id}/rating",
    response_model=LibraryResponse,
    summary="评分种子库",
    description="提交用户评分，并更新融合后的质量分展示",
)
async def rate_library(
    library_id: UUID,
    rating_data: RatingUpsertRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await service.rate_library(
        db,
        library_id=library_id,
        user_id=current_user.id,
        score=rating_data.score,
        comment=rating_data.comment,
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Library not found")
    await db.commit()
    library = await service.get_library_for_user(db, library_id, current_user.id)
    if not library:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Library not found")
    stats = await service.get_library_stats(db, library_id)
    lib_info = await _enrich_library_info(db, library, user_id=current_user.id, stats=stats)
    return LibraryResponse(data=lib_info)


@router.post(
    "/seed-libraries/{library_id}/subscribe",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="订阅库（兼容路径）",
)
async def subscribe_library_alias(
    library_id: UUID,
    subscription_data: SubscriptionCreate = SubscriptionCreate(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await subscribe_library(library_id, subscription_data, current_user, db)


@router.delete(
    "/seed-libraries/{library_id}/unsubscribe",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="取消订阅（兼容路径）",
)
async def unsubscribe_library_alias(
    library_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await unsubscribe_library(library_id, current_user, db)


@router.get(
    "/seed-libraries/my-subscriptions",
    response_model=SubscriptionListResponse,
    summary="我的订阅（兼容路径）",
)
async def get_my_subscriptions_alias(
    is_enabled: bool | None = Query(None, description="仅返回启用的订阅"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_my_subscriptions(is_enabled, current_user, db)


@router.get(
    "/seed-libraries/subscriptions/me",
    response_model=SubscriptionListResponse,
    summary="我的订阅",
    description="获取当前用户的所有订阅"
)
async def get_my_subscriptions(
    is_enabled: bool | None = Query(None, description="仅返回启用的订阅"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取我的订阅"""
    subscriptions = await service.get_subscriptions(db, current_user.id, is_enabled)

    data = []
    for sub in subscriptions:
        sub_info = await _subscription_info(db, sub, sub.library)
        data.append(sub_info)

    return SubscriptionListResponse(data=data)


# ============ 查询/检索接口 ============

@router.post(
    "/seed-libraries/query",
    response_model=ItemQueryResponse,
    summary="查询内容",
    description="跨订阅库查询内容，支持关键词搜索和语义搜索"
)
async def query_items(
    query_request: ItemQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询内容"""
    items, total = await service.query_items(db, current_user.id, query_request)

    data = [ItemInfo.model_validate(item) for item in items]
    return ItemQueryResponse(
        items=data,
        total_count=total,
        query_used=query_request.query,
        search_method="semantic" if query_request.use_semantic_search else "keyword"
    )


@router.get(
    "/seed-libraries/examples/few-shot",
    response_model=list[FewShotExample],
    summary="获取 Few-shot 示例",
    description="获取用于 LLM prompt 增强的 few-shot 学习示例"
)
async def get_few_shot_examples(
    subject: str | None = Query(None, description="学科筛选"),
    difficulty_level: str | None = Query(None, description="难度筛选"),
    task_type: str | None = Query(None, description="任务类型筛选"),
    count: int = Query(3, ge=1, le=10, description="需要的示例数量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取 Few-shot 示例"""
    examples = await service.get_few_shot_examples(
        db,
        current_user.id,
        subject=subject,
        difficulty_level=difficulty_level,
        task_type=task_type,
        count=count,
    )

    return [
        FewShotExample(
            input=ex.get("input", ""),
            output=ex.get("output", ""),
            explanation=ex.get("explanation"),
            subject=ex.get("subject"),
            difficulty_level=ex.get("difficulty_level"),
        )
        for ex in examples
    ]


@router.get(
    "/seed-libraries/query/few-shot",
    response_model=list[FewShotExample],
    summary="获取 Few-shot 示例（兼容路径）",
)
async def get_few_shot_examples_alias(
    subject: str | None = Query(None, description="学科筛选"),
    difficulty_level: str | None = Query(None, description="难度筛选"),
    task_type: str | None = Query(None, description="任务类型筛选"),
    count: int = Query(3, ge=1, le=10, description="需要的示例数量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_few_shot_examples(
        subject=subject,
        difficulty_level=difficulty_level,
        task_type=task_type,
        count=count,
        current_user=current_user,
        db=db,
    )


# ============ 管理员接口 ============

@router.put(
    "/seed-libraries/admin/{library_id}/promote",
    response_model=LibraryResponse,
    summary="提升为官方库",
    description="管理员操作：将用户创建的库提升为官方库"
)
async def promote_to_official(
    library_id: UUID,
    promote_data: PromoteToOfficialRequest,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    """提升为官方库"""
    library = await service.promote_to_official(
        db,
        library_id,
        quality_score=promote_data.quality_score,
        is_featured=promote_data.is_featured,
    )
    if not library:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Library not found")

    await db.commit()

    stats = await service.get_library_stats(db, library_id)
    lib_info = LibraryInfo.model_validate(library)
    lib_info.item_count = stats["item_count"]
    lib_info.subscriber_count = stats["subscriber_count"]

    return LibraryResponse(data=lib_info)
