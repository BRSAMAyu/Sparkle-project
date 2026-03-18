"""
Seed Library Service
种子内容库核心服务 - 管理库、内容项、订阅和查询
"""
from __future__ import annotations
import uuid
from datetime import timezone, datetime
from typing import Any

from loguru import logger
from sqlalchemy import and_, asc, desc, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.seed_content import (
    ItemType,
    LibraryCategory,
    LibraryVisibility,
    SeedItem,
    SeedLibrary,
    UserLibrarySubscription,
)
from app.schemas.seed_content import (
    ItemCreate,
    ItemListParams,
    ItemQueryRequest,
    ItemUpdate,
    LibraryCreate,
    LibraryListParams,
    LibraryUpdate,
    SubscriptionCreate,
    SubscriptionUpdate,
)
from app.services.embedding_service import embedding_service


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class SeedLibraryService:
    """种子内容库服务"""

    # ============ 辅助方法 ============

    def _build_embedding_text(
        self,
        title: str | None,
        content: str | None,
        content_data: dict[str, Any] | None = None,
        item_type: str | None = None,
    ) -> str | None:
        """
        构建用于生成 embedding 的文本

        Args:
            title: 标题
            content: 内容
            content_data: 结构化内容数据
            item_type: 内容类型 (example, exercise, knowledge, template, flashcard)

        Returns:
            合并后的文本，若无有效内容则返回 None
        """
        parts = []
        if title:
            parts.append(title.strip())
        if content:
            # 限制内容长度，避免过长文本
            content_text = content.strip()[:2000]
            parts.append(content_text)

        # 处理 content_data 中的结构化内容
        if content_data:
            if item_type == ItemType.EXAMPLE.value or item_type == "example":
                # Few-shot 示例：包含 input/output
                if content_data.get("input"):
                    parts.append(f"输入: {str(content_data['input'])[:500]}")
                if content_data.get("output"):
                    parts.append(f"输出: {str(content_data['output'])[:500]}")
                if content_data.get("explanation"):
                    parts.append(f"解释: {str(content_data['explanation'])[:300]}")
            elif item_type == ItemType.EXERCISE.value or item_type == "exercise":
                # 练习题：包含 question/answer/options
                if content_data.get("question"):
                    parts.append(f"问题: {str(content_data['question'])[:500]}")
                if content_data.get("answer"):
                    parts.append(f"答案: {str(content_data['answer'])[:300]}")
                if content_data.get("options"):
                    options_text = " ".join([str(opt) for opt in content_data["options"][:5]])
                    parts.append(f"选项: {options_text[:200]}")
            elif item_type == ItemType.FLASHCARD.value or item_type == "flashcard":
                # 抽认卡：包含 front/back
                if content_data.get("front"):
                    parts.append(f"正面: {str(content_data['front'])[:300]}")
                if content_data.get("back"):
                    parts.append(f"背面: {str(content_data['back'])[:300]}")
            elif item_type == ItemType.KNOWLEDGE.value or item_type == "knowledge":
                # 知识点：可能包含 definition/formula/examples
                if content_data.get("definition"):
                    parts.append(f"定义: {str(content_data['definition'])[:500]}")
                if content_data.get("formula"):
                    parts.append(f"公式: {str(content_data['formula'])[:200]}")
                if content_data.get("key_points"):
                    kp_text = " ".join([str(kp) for kp in content_data["key_points"][:5]])
                    parts.append(f"要点: {kp_text[:300]}")

        return " ".join(parts) if parts else None

    # ============ 库管理 ============

    async def create_library(
        self,
        db: AsyncSession,
        library_data: LibraryCreate,
        owner_id: uuid.UUID,
    ) -> SeedLibrary:
        """
        创建新库

        Args:
            db: 数据库会话
            library_data: 库创建数据
            owner_id: 创建者ID

        Returns:
            创建的库对象
        """
        library = SeedLibrary(
            name=library_data.name,
            description=library_data.description,
            category=library_data.category.value,
            visibility=library_data.visibility.value,
            owner_id=owner_id,
            language=library_data.language,
            tags=library_data.tags,
            extra_metadata=library_data.extra_metadata,
        )
        db.add(library)
        await db.flush()
        await db.refresh(library)
        logger.info(f"Created library: {library.id} by user {owner_id}")
        return library

    async def get_library(
        self,
        db: AsyncSession,
        library_id: uuid.UUID,
        include_items: bool = False,
    ) -> SeedLibrary | None:
        """
        获取库详情

        Args:
            db: 数据库会话
            library_id: 库ID
            include_items: 是否包含内容项

        Returns:
            库对象或 None
        """
        query = select(SeedLibrary).where(
            and_(
                SeedLibrary.id == library_id,
                SeedLibrary.deleted_at.is_(None)
            )
        )

        if include_items:
            query = query.options(selectinload(SeedLibrary.items))

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def list_libraries(
        self,
        db: AsyncSession,
        params: LibraryListParams,
        user_id: uuid.UUID | None = None,
    ) -> tuple[list[SeedLibrary], int]:
        """
        获取库列表

        Args:
            db: 数据库会话
            params: 查询参数
            user_id: 当前用户ID (用于权限检查)

        Returns:
            (库列表, 总数)
        """
        # 构建查询条件
        conditions = [SeedLibrary.deleted_at.is_(None)]

        # 分类筛选
        if params.category:
            conditions.append(SeedLibrary.category == params.category.value)

        # 可见性筛选
        if params.visibility:
            if params.visibility == LibraryVisibility.PRIVATE:
                # 私有库只显示自己的
                if user_id:
                    conditions.append(
                        and_(
                            SeedLibrary.visibility == LibraryVisibility.PRIVATE,
                            SeedLibrary.owner_id == user_id
                        )
                    )
                else:
                    # 未登录用户看不到私有库，返回空结果
                    conditions.append(text("FALSE"))
            else:
                conditions.append(SeedLibrary.visibility == params.visibility.value)
        else:
            # 默认显示公开库和官方库
            public_conditions = [
                SeedLibrary.visibility == LibraryVisibility.PUBLIC,
                SeedLibrary.visibility == LibraryVisibility.OFFICIAL,
            ]
            # 如果有用户，也显示自己的私有库
            if user_id:
                public_conditions.append(
                    and_(
                        SeedLibrary.visibility == LibraryVisibility.PRIVATE,
                        SeedLibrary.owner_id == user_id
                    )
                )
            conditions.append(or_(*public_conditions))

        # 语言筛选
        if params.language:
            conditions.append(SeedLibrary.language == params.language)

        # 官方库筛选
        if params.is_official is not None:
            conditions.append(SeedLibrary.is_official == params.is_official)

        # 精选筛选
        if params.is_featured is not None:
            conditions.append(SeedLibrary.is_featured == params.is_featured)

        # 创建者筛选
        if params.owner_id:
            conditions.append(SeedLibrary.owner_id == params.owner_id)

        # 标签筛选
        if params.tags:
            for tag in params.tags:
                conditions.append(SeedLibrary.tags.contains([tag]))

        # 搜索关键词
        if params.search:
            search_term = f"%{params.search}%"
            conditions.append(
                or_(
                    SeedLibrary.name.ilike(search_term),
                    SeedLibrary.description.ilike(search_term),
                )
            )

        # 构建查询
        query = select(SeedLibrary).where(and_(*conditions))

        # 排序
        sort_column = getattr(SeedLibrary, params.sort_by, SeedLibrary.created_at)
        query = query.order_by(desc(sort_column)) if params.sort_order == "desc" else query.order_by(asc(sort_column))

        # 分页
        total_query = select(func.count()).select_from(SeedLibrary).where(and_(*conditions))
        total_result = await db.execute(total_query)
        total = total_result.scalar() or 0

        offset = (params.page - 1) * params.page_size
        query = query.offset(offset).limit(params.page_size)

        result = await db.execute(query)
        libraries = list(result.scalars().all())

        return libraries, total

    async def update_library(
        self,
        db: AsyncSession,
        library_id: uuid.UUID,
        update_data: LibraryUpdate,
        user_id: uuid.UUID,
        is_superuser: bool = False,
    ) -> SeedLibrary | None:
        """
        更新库

        Args:
            db: 数据库会话
            library_id: 库ID
            update_data: 更新数据
            user_id: 操作用户ID
            is_superuser: 是否为管理员

        Returns:
            更新后的库对象或 None
        """
        library = await self.get_library(db, library_id)
        if not library:
            return None

        # 权限检查
        if library.owner_id != user_id and not is_superuser:
            raise PermissionError("No permission to update this library")

        # 更新字段
        if update_data.name is not None:
            library.name = update_data.name
        if update_data.description is not None:
            library.description = update_data.description
        if update_data.category is not None:
            library.category = update_data.category.value
        if update_data.visibility is not None and is_superuser:
            library.visibility = update_data.visibility.value
        if update_data.language is not None:
            library.language = update_data.language
        if update_data.tags is not None:
            library.tags = update_data.tags
        if update_data.extra_metadata is not None:
            library.extra_metadata = update_data.extra_metadata
        if update_data.quality_score is not None and is_superuser:
            library.quality_score = update_data.quality_score

        await db.flush()
        await db.refresh(library)
        logger.info(f"Updated library: {library_id}")
        return library

    async def delete_library(
        self,
        db: AsyncSession,
        library_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superuser: bool = False,
    ) -> bool:
        """
        删除库 (软删除)

        Args:
            db: 数据库会话
            library_id: 库ID
            user_id: 操作用户ID
            is_superuser: 是否为管理员

        Returns:
            是否删除成功
        """
        library = await self.get_library(db, library_id)
        if not library:
            return False

        # 权限检查
        if library.owner_id != user_id and not is_superuser:
            raise PermissionError("No permission to delete this library")

        await library.delete(db, soft=True)
        logger.info(f"Deleted library: {library_id}")
        return True

    async def promote_to_official(
        self,
        db: AsyncSession,
        library_id: uuid.UUID,
        quality_score: float | None = None,
        is_featured: bool = False,
    ) -> SeedLibrary | None:
        """
        将库提升为官方库 (管理员操作)

        Args:
            db: 数据库会话
            library_id: 库ID
            quality_score: 质量评分
            is_featured: 是否设为精选

        Returns:
            更新后的库对象或 None
        """
        library = await self.get_library(db, library_id)
        if not library:
            return None

        library.is_official = True
        library.visibility = LibraryVisibility.OFFICIAL
        if quality_score is not None:
            library.quality_score = quality_score
        library.is_featured = is_featured

        await db.flush()
        await db.refresh(library)
        logger.info(f"Promoted library to official: {library_id}")
        return library

    # ============ 内容项管理 ============

    async def add_item(
        self,
        db: AsyncSession,
        library_id: uuid.UUID,
        item_data: ItemCreate,
        user_id: uuid.UUID,
        is_superuser: bool = False,
    ) -> SeedItem | None:
        """
        添加内容项

        Args:
            db: 数据库会话
            library_id: 库ID
            item_data: 内容项数据
            user_id: 操作用户ID
            is_superuser: 是否为管理员

        Returns:
            创建的内容项或 None
        """
        library = await self.get_library(db, library_id)
        if not library:
            return None

        # 权限检查
        if library.owner_id != user_id and not is_superuser:
            raise PermissionError("No permission to add items to this library")

        item = SeedItem(
            library_id=library_id,
            item_type=item_data.item_type.value,
            title=item_data.title,
            content=item_data.content,
            content_data=item_data.content_data,
            subject=item_data.subject,
            difficulty_level=item_data.difficulty_level.value if item_data.difficulty_level else None,
            tags=item_data.tags,
            order_index=item_data.order_index,
        )

        # 生成 embedding 用于语义搜索
        embedding_text = self._build_embedding_text(
            title=item_data.title,
            content=item_data.content,
            content_data=item_data.content_data,
            item_type=item_data.item_type.value,
        )
        if embedding_text:
            try:
                item.embedding = await embedding_service.get_embedding(embedding_text, text_type="document")
            except Exception as e:
                logger.warning(f"Failed to generate embedding for seed item: {e}")

        db.add(item)
        await db.flush()
        await db.refresh(item)
        logger.info(f"Added item to library {library_id}: {item.id}")
        return item

    async def get_items(
        self,
        db: AsyncSession,
        params: ItemListParams,
    ) -> tuple[list[SeedItem], int]:
        """
        获取内容项列表

        Args:
            db: 数据库会话
            params: 查询参数

        Returns:
            (内容项列表, 总数)
        """
        conditions = [SeedItem.deleted_at.is_(None)]

        # 库筛选
        if params.library_id:
            conditions.append(SeedItem.library_id == params.library_id)

        # 类型筛选
        if params.item_type:
            conditions.append(SeedItem.item_type == params.item_type.value)

        # 学科筛选
        if params.subject:
            conditions.append(SeedItem.subject == params.subject)

        # 难度筛选
        if params.difficulty_level:
            conditions.append(SeedItem.difficulty_level == params.difficulty_level.value)

        # 标签筛选
        if params.tags:
            for tag in params.tags:
                conditions.append(SeedItem.tags.contains([tag]))

        # 启用状态筛选
        if params.is_active is not None:
            conditions.append(SeedItem.is_active == params.is_active)

        # 搜索关键词
        if params.search:
            search_term = f"%{params.search}%"
            conditions.append(
                or_(
                    SeedItem.title.ilike(search_term),
                    SeedItem.content.ilike(search_term),
                )
            )

        # 构建查询
        query = select(SeedItem).where(and_(*conditions))

        # 排序
        sort_column = getattr(SeedItem, params.sort_by, SeedItem.order_index)
        query = query.order_by(desc(sort_column)) if params.sort_order == "desc" else query.order_by(asc(sort_column))

        # 分页
        total_query = select(func.count()).select_from(SeedItem).where(and_(*conditions))
        total_result = await db.execute(total_query)
        total = total_result.scalar() or 0

        offset = (params.page - 1) * params.page_size
        query = query.offset(offset).limit(params.page_size)

        result = await db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_item(
        self,
        db: AsyncSession,
        item_id: uuid.UUID,
    ) -> SeedItem | None:
        """获取单个内容项"""
        result = await db.execute(
            select(SeedItem).where(
                and_(
                    SeedItem.id == item_id,
                    SeedItem.deleted_at.is_(None)
                )
            )
        )
        return result.scalar_one_or_none()

    async def update_item(
        self,
        db: AsyncSession,
        item_id: uuid.UUID,
        update_data: ItemUpdate,
        user_id: uuid.UUID,
        is_superuser: bool = False,
    ) -> SeedItem | None:
        """
        更新内容项

        Args:
            db: 数据库会话
            item_id: 内容项ID
            update_data: 更新数据
            user_id: 操作用户ID
            is_superuser: 是否为管理员

        Returns:
            更新后的内容项或 None
        """
        item = await self.get_item(db, item_id)
        if not item:
            return None

        # 检查权限
        library = await self.get_library(db, item.library_id)
        if library and library.owner_id != user_id and not is_superuser:
            raise PermissionError("No permission to update this item")

        # 跟踪内容是否变化（需要更新 embedding）
        content_changed = False

        # 更新字段
        if update_data.title is not None:
            if item.title != update_data.title:
                content_changed = True
            item.title = update_data.title
        if update_data.content is not None:
            if item.content != update_data.content:
                content_changed = True
            item.content = update_data.content
        if update_data.content_data is not None:
            # content_data 变化也需要更新 embedding（包含 input/output 等）
            if item.content_data != update_data.content_data:
                content_changed = True
            item.content_data = update_data.content_data
        if update_data.subject is not None:
            item.subject = update_data.subject
        if update_data.difficulty_level is not None:
            item.difficulty_level = update_data.difficulty_level.value
        if update_data.tags is not None:
            item.tags = update_data.tags
        if update_data.order_index is not None:
            item.order_index = update_data.order_index
        if update_data.is_active is not None:
            item.is_active = update_data.is_active

        # 内容变化时更新 embedding
        if content_changed:
            embedding_text = self._build_embedding_text(
                title=item.title,
                content=item.content,
                content_data=item.content_data,
                item_type=item.item_type,
            )
            if embedding_text:
                try:
                    item.embedding = await embedding_service.get_embedding(embedding_text, text_type="document")
                except Exception as e:
                    logger.warning(f"Failed to update embedding for seed item {item_id}: {e}")

        await db.flush()
        await db.refresh(item)
        logger.info(f"Updated item: {item_id}")
        return item

    async def delete_item(
        self,
        db: AsyncSession,
        item_id: uuid.UUID,
        user_id: uuid.UUID,
        is_superuser: bool = False,
    ) -> bool:
        """
        删除内容项 (软删除)

        Args:
            db: 数据库会话
            item_id: 内容项ID
            user_id: 操作用户ID
            is_superuser: 是否为管理员

        Returns:
            是否删除成功
        """
        item = await self.get_item(db, item_id)
        if not item:
            return False

        # 检查权限
        library = await self.get_library(db, item.library_id)
        if library and library.owner_id != user_id and not is_superuser:
            raise PermissionError("No permission to delete this item")

        await item.delete(db, soft=True)
        logger.info(f"Deleted item: {item_id}")
        return True

    # ============ 订阅管理 ============

    async def subscribe(
        self,
        db: AsyncSession,
        library_id: uuid.UUID,
        user_id: uuid.UUID,
        subscription_data: SubscriptionCreate,
    ) -> UserLibrarySubscription | None:
        """
        订阅库

        Args:
            db: 数据库会话
            library_id: 库ID
            user_id: 用户ID
            subscription_data: 订阅数据

        Returns:
            订阅对象或 None
        """
        library = await self.get_library(db, library_id)
        if not library:
            return None

        if not library.can_be_subscribed:
            raise ValueError("This library cannot be subscribed")

        # 检查是否已订阅
        existing = await db.execute(
            select(UserLibrarySubscription).where(
                and_(
                    UserLibrarySubscription.user_id == user_id,
                    UserLibrarySubscription.library_id == library_id,
                    UserLibrarySubscription.deleted_at.is_(None)
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Already subscribed to this library")

        subscription = UserLibrarySubscription(
            user_id=user_id,
            library_id=library_id,
            is_enabled=True,
            priority=subscription_data.priority,
            notes=subscription_data.notes,
            subscribed_at=_utcnow(),
        )
        db.add(subscription)
        await db.flush()
        await db.refresh(subscription)

        # 增加库的使用计数
        library.increment_usage()

        logger.info(f"User {user_id} subscribed to library {library_id}")
        return subscription

    async def unsubscribe(
        self,
        db: AsyncSession,
        library_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """
        取消订阅

        Args:
            db: 数据库会话
            library_id: 库ID
            user_id: 用户ID

        Returns:
            是否取消成功
        """
        subscription = await db.execute(
            select(UserLibrarySubscription).where(
                and_(
                    UserLibrarySubscription.user_id == user_id,
                    UserLibrarySubscription.library_id == library_id,
                    UserLibrarySubscription.deleted_at.is_(None)
                )
            )
        )
        sub = subscription.scalar_one_or_none()
        if not sub:
            return False

        await sub.delete(db, soft=True)
        logger.info(f"User {user_id} unsubscribed from library {library_id}")
        return True

    async def get_subscriptions(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        is_enabled: bool | None = None,
    ) -> list[UserLibrarySubscription]:
        """
        获取用户的订阅列表

        Args:
            db: 数据库会话
            user_id: 用户ID
            is_enabled: 是否仅返回启用的订阅

        Returns:
            订阅列表
        """
        conditions = [
            UserLibrarySubscription.user_id == user_id,
            UserLibrarySubscription.deleted_at.is_(None)
        ]

        if is_enabled is not None:
            conditions.append(UserLibrarySubscription.is_enabled == is_enabled)

        result = await db.execute(
            select(UserLibrarySubscription)
            .where(and_(*conditions))
            .options(selectinload(UserLibrarySubscription.library))
            .order_by(desc(UserLibrarySubscription.priority), desc(UserLibrarySubscription.subscribed_at))
        )
        return list(result.scalars().all())

    async def update_subscription(
        self,
        db: AsyncSession,
        library_id: uuid.UUID,
        user_id: uuid.UUID,
        update_data: SubscriptionUpdate,
    ) -> UserLibrarySubscription | None:
        """
        更新订阅

        Args:
            db: 数据库会话
            library_id: 库ID
            user_id: 用户ID
            update_data: 更新数据

        Returns:
            更新后的订阅或 None
        """
        result = await db.execute(
            select(UserLibrarySubscription).where(
                and_(
                    UserLibrarySubscription.user_id == user_id,
                    UserLibrarySubscription.library_id == library_id,
                    UserLibrarySubscription.deleted_at.is_(None)
                )
            )
        )
        subscription = result.scalar_one_or_none()
        if not subscription:
            return None

        if update_data.is_enabled is not None:
            subscription.is_enabled = update_data.is_enabled
        if update_data.priority is not None:
            subscription.priority = update_data.priority
        if update_data.notes is not None:
            subscription.notes = update_data.notes

        await db.flush()
        await db.refresh(subscription)
        logger.info(f"Updated subscription for user {user_id} to library {library_id}")
        return subscription

    # ============ 查询/检索 ============

    async def query_items(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        query_request: ItemQueryRequest,
    ) -> tuple[list[SeedItem], int]:
        """
        跨订阅库查询内容项 - 支持语义搜索和关键词搜索

        Args:
            db: 数据库会话
            user_id: 用户ID
            query_request: 查询请求

        Returns:
            (内容项列表, 总数)
        """
        # 确定查询的库范围
        lib_ids: list[uuid.UUID] | None = None
        if query_request.use_subscribed_only:
            subscribed_lib_ids = await db.execute(
                select(UserLibrarySubscription.library_id).where(
                    and_(
                        UserLibrarySubscription.user_id == user_id,
                        UserLibrarySubscription.is_enabled,
                        UserLibrarySubscription.deleted_at.is_(None)
                    )
                )
            )
            lib_ids = [row[0] for row in subscribed_lib_ids.all()]

            if query_request.include_official:
                official_libs = await db.execute(
                    select(SeedLibrary.id).where(
                        and_(
                            SeedLibrary.is_official,
                            SeedLibrary.deleted_at.is_(None)
                        )
                    )
                )
                lib_ids.extend([row[0] for row in official_libs.all()])

            if not lib_ids:
                return [], 0

        # 准备类型筛选
        item_types = [t.value for t in query_request.item_types] if query_request.item_types else None

        # 语义搜索 + 关键词搜索混合
        if query_request.use_semantic_search and query_request.query:
            return await self._hybrid_query_items(
                db=db,
                query=query_request.query,
                lib_ids=lib_ids,
                item_types=item_types,
                subjects=query_request.subjects,
                difficulty_levels=[d.value for d in query_request.difficulty_levels] if query_request.difficulty_levels else None,
                tags=query_request.tags,
                limit=query_request.limit,
            )

        # 仅关键词搜索（原有逻辑）
        return await self._keyword_query_items(
            db=db,
            query=query_request.query,
            lib_ids=lib_ids,
            item_types=item_types,
            subjects=query_request.subjects,
            difficulty_levels=[d.value for d in query_request.difficulty_levels] if query_request.difficulty_levels else None,
            tags=query_request.tags,
            limit=query_request.limit,
        )

    async def _keyword_query_items(
        self,
        db: AsyncSession,
        query: str | None,
        lib_ids: list[uuid.UUID] | None,
        item_types: list[str] | None,
        subjects: list[str] | None,
        difficulty_levels: list[str] | None,
        tags: list[str] | None,
        limit: int,
    ) -> tuple[list[SeedItem], int]:
        """关键词搜索内部实现"""
        conditions = [SeedItem.deleted_at.is_(None), SeedItem.is_active]

        if lib_ids:
            conditions.append(SeedItem.library_id.in_(lib_ids))

        if item_types:
            conditions.append(SeedItem.item_type.in_(item_types))

        if subjects:
            conditions.append(SeedItem.subject.in_(subjects))

        if difficulty_levels:
            conditions.append(SeedItem.difficulty_level.in_(difficulty_levels))

        if tags:
            for tag in tags:
                conditions.append(SeedItem.tags.contains([tag]))

        if query:
            search_term = f"%{query}%"
            conditions.append(
                or_(
                    SeedItem.title.ilike(search_term),
                    SeedItem.content.ilike(search_term),
                )
            )

        stmt = select(SeedItem).where(and_(*conditions))

        total_query = select(func.count()).select_from(SeedItem).where(and_(*conditions))
        total_result = await db.execute(total_query)
        total = total_result.scalar() or 0

        stmt = stmt.limit(limit).order_by(desc(SeedItem.created_at))

        result = await db.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def _hybrid_query_items(
        self,
        db: AsyncSession,
        query: str,
        lib_ids: list[uuid.UUID] | None,
        item_types: list[str] | None,
        subjects: list[str] | None,
        difficulty_levels: list[str] | None,
        tags: list[str] | None,
        limit: int,
        semantic_weight: float = 0.6,
        keyword_weight: float = 0.4,
    ) -> tuple[list[SeedItem], int]:
        """
        混合搜索：语义搜索 + 关键词搜索，使用 RRF 融合

        Args:
            semantic_weight: 语义搜索权重
            keyword_weight: 关键词搜索权重
        """
        import asyncio

        # 并行执行语义搜索和关键词搜索
        semantic_task = self.semantic_search_items(
            db=db,
            query=query,
            library_ids=lib_ids,
            item_types=item_types,
            limit=limit * 2,
            threshold=0.25,
        )

        keyword_task = self._keyword_query_items(
            db=db,
            query=query,
            lib_ids=lib_ids,
            item_types=item_types,
            subjects=subjects,
            difficulty_levels=difficulty_levels,
            tags=tags,
            limit=limit * 2,
        )

        semantic_results, (keyword_items, keyword_total) = await asyncio.gather(
            semantic_task,
            keyword_task,
        )

        # RRF (Reciprocal Rank Fusion) 融合
        k = 60  # RRF 常数
        item_scores: dict[uuid.UUID, float] = {}
        item_map: dict[uuid.UUID, SeedItem] = {}

        # 语义搜索结果评分
        for rank, (item, _sim_score) in enumerate(semantic_results):
            item_id = item.id
            item_map[item_id] = item
            rrf_score = semantic_weight * (1 / (k + rank + 1))
            item_scores[item_id] = item_scores.get(item_id, 0) + rrf_score

        # 关键词搜索结果评分
        for rank, item in enumerate(keyword_items):
            item_id = item.id
            if item_id not in item_map:
                item_map[item_id] = item
            rrf_score = keyword_weight * (1 / (k + rank + 1))
            item_scores[item_id] = item_scores.get(item_id, 0) + rrf_score

        # 按 RRF 分数排序
        sorted_ids = sorted(item_scores.keys(), key=lambda x: item_scores[x], reverse=True)
        merged_items = [item_map[item_id] for item_id in sorted_ids[:limit]]

        # 估算总数：使用关键词总数作为基准（因为语义搜索未返回总数）
        # 如果语义搜索返回的结果较少，说明语义匹配更精准，使用实际去重后的数量
        # 如果语义搜索满了，则使用关键词总数作为保守估计
        semantic_limit = limit * 2
        if len(semantic_results) < semantic_limit:
            # 语义搜索没满，说明匹配结果有限，使用去重后的实际数量
            total = len(item_map)
        else:
            # 语义搜索满了，使用关键词总数作为估计（可能偏高但保守）
            total = max(keyword_total, len(item_map))

        return merged_items, total

    async def get_few_shot_examples(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        subject: str | None = None,
        difficulty_level: str | None = None,
        task_type: str | None = None,
        count: int = 3,
    ) -> list[dict[str, Any]]:
        """
        获取 Few-shot 示例用于 LLM prompt 增强

        Args:
            db: 数据库会话
            user_id: 用户ID
            subject: 学科筛选
            difficulty_level: 难度筛选
            task_type: 任务类型筛选
            count: 需要的示例数量

        Returns:
            示例列表 [{"input": ..., "output": ..., "explanation": ...}, ...]
        """
        conditions = [
            SeedItem.deleted_at.is_(None),
            SeedItem.is_active,
            SeedItem.item_type == ItemType.EXAMPLE,
        ]

        # 从 few_shot 分类库获取
        few_shot_libs = await db.execute(
            select(SeedLibrary.id).where(
                and_(
                    SeedLibrary.category == LibraryCategory.FEW_SHOT,
                    SeedLibrary.deleted_at.is_(None),
                    or_(
                        SeedLibrary.is_official,
                        SeedLibrary.visibility == LibraryVisibility.PUBLIC,
                    )
                )
            )
        )
        lib_ids = [row[0] for row in few_shot_libs.all()]
        if lib_ids:
            conditions.append(SeedItem.library_id.in_(lib_ids))

        # 学科筛选
        if subject:
            conditions.append(SeedItem.subject == subject)

        # 难度筛选
        if difficulty_level:
            conditions.append(SeedItem.difficulty_level == difficulty_level)

        # 任务类型筛选 (通过标签)
        if task_type:
            conditions.append(SeedItem.tags.contains([task_type]))

        # 查询示例
        result = await db.execute(
            select(SeedItem)
            .where(and_(*conditions))
            .order_by(asc(SeedItem.order_index))
            .limit(count)
        )
        items = list(result.scalars().all())

        # 转换为 few-shot 格式
        examples = []
        for item in items:
            example = {
                "input": "",
                "output": "",
                "explanation": None,
                "subject": item.subject,
                "difficulty_level": item.difficulty_level,
            }

            # 从 content_data 中提取 input/output
            if item.content_data:
                example["input"] = item.content_data.get("input", item.content or "")
                example["output"] = item.content_data.get("output", "")
                example["explanation"] = item.content_data.get("explanation")
            else:
                example["output"] = item.content or ""

            examples.append(example)

        logger.info(f"Retrieved {len(examples)} few-shot examples for user {user_id}")
        return examples

    async def get_reply_template(
        self,
        db: AsyncSession,
        template_key: str,
        user_id: uuid.UUID,
        language: str = "zh",
    ) -> str | None:
        """
        获取回复模板

        Args:
            db: 数据库会话
            template_key: 模板标识 (通过标签查找)
            user_id: 用户ID
            language: 语言

        Returns:
            模板内容或 None
        """
        conditions = [
            SeedItem.deleted_at.is_(None),
            SeedItem.is_active,
            SeedItem.item_type == ItemType.TEMPLATE,
            SeedItem.tags.contains([template_key]),
        ]

        # 从 reply_template 分类库获取
        template_libs = await db.execute(
            select(SeedLibrary.id).where(
                and_(
                    SeedLibrary.category == LibraryCategory.REPLY_TEMPLATE,
                    SeedLibrary.language == language,
                    SeedLibrary.deleted_at.is_(None),
                    or_(
                        SeedLibrary.is_official,
                        SeedLibrary.visibility == LibraryVisibility.PUBLIC,
                    )
                )
            )
        )
        lib_ids = [row[0] for row in template_libs.all()]
        if lib_ids:
            conditions.append(SeedItem.library_id.in_(lib_ids))

        result = await db.execute(
            select(SeedItem).where(and_(*conditions)).order_by(desc(SeedItem.order_index))
        )
        item = result.scalar_one_or_none()

        if item:
            # 增加使用计数
            library = await self.get_library(db, item.library_id)
            if library:
                library.increment_usage()
            return item.content

        return None

    async def get_library_stats(
        self,
        db: AsyncSession,
        library_id: uuid.UUID,
    ) -> dict[str, Any]:
        """
        获取库统计信息

        Args:
            db: 数据库会话
            library_id: 库ID

        Returns:
            统计信息字典
        """
        stats_map = await self.batch_get_library_stats(db, [library_id])
        return stats_map.get(library_id, {"item_count": 0, "subscriber_count": 0})

    async def batch_get_library_stats(
        self,
        db: AsyncSession,
        library_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, dict[str, Any]]:
        """
        批量获取多个库的统计信息（避免 N+1 查询）

        Args:
            db: 数据库会话
            library_ids: 库ID列表

        Returns:
            {library_id: {"item_count": n, "subscriber_count": m}, ...}
        """
        if not library_ids:
            return {}

        # 批量查询内容项数量
        item_counts_stmt = (
            select(SeedItem.library_id, func.count())
            .where(
                and_(
                    SeedItem.library_id.in_(library_ids),
                    SeedItem.deleted_at.is_(None)
                )
            )
            .group_by(SeedItem.library_id)
        )
        item_counts_result = await db.execute(item_counts_stmt)
        item_counts = {row[0]: row[1] for row in item_counts_result.all()}

        # 批量查询订阅者数量
        subscriber_counts_stmt = (
            select(UserLibrarySubscription.library_id, func.count())
            .where(
                and_(
                    UserLibrarySubscription.library_id.in_(library_ids),
                    UserLibrarySubscription.deleted_at.is_(None)
                )
            )
            .group_by(UserLibrarySubscription.library_id)
        )
        subscriber_counts_result = await db.execute(subscriber_counts_stmt)
        subscriber_counts = {row[0]: row[1] for row in subscriber_counts_result.all()}

        # 构建结果映射
        stats_map: dict[uuid.UUID, dict[str, Any]] = {}
        for lib_id in library_ids:
            stats_map[lib_id] = {
                "item_count": item_counts.get(lib_id, 0),
                "subscriber_count": subscriber_counts.get(lib_id, 0),
            }

        return stats_map

    # ============ Embedding 管理 ============

    async def backfill_embeddings(
        self,
        db: AsyncSession,
        batch_size: int = 50,
        library_id: uuid.UUID | None = None,
    ) -> dict[str, int]:
        """
        批量为缺少 embedding 的 SeedItem 生成向量

        Args:
            db: 数据库会话
            batch_size: 每批处理数量
            library_id: 可选，限定特定库

        Returns:
            {"processed": n, "failed": m, "skipped": k}
        """
        conditions = [
            SeedItem.deleted_at.is_(None),
            SeedItem.embedding.is_(None),
        ]
        if library_id:
            conditions.append(SeedItem.library_id == library_id)

        # 查询所有缺少 embedding 的 items
        result = await db.execute(
            select(SeedItem)
            .where(and_(*conditions))
            .limit(batch_size)
        )
        items = list(result.scalars().all())

        processed = 0
        failed = 0
        skipped = 0

        for item in items:
            embedding_text = self._build_embedding_text(
                title=item.title,
                content=item.content,
                content_data=item.content_data,
                item_type=item.item_type,
            )
            if not embedding_text:
                skipped += 1
                continue

            try:
                item.embedding = await embedding_service.get_embedding(embedding_text, text_type="document")
                processed += 1
            except Exception as e:
                logger.warning(f"Failed to generate embedding for item {item.id}: {e}")
                failed += 1

        if processed > 0:
            await db.flush()  # 确保写入数据库
            await db.commit()

        logger.info(f"Backfill embeddings: processed={processed}, failed={failed}, skipped={skipped}")
        return {"processed": processed, "failed": failed, "skipped": skipped}

    async def semantic_search_items(
        self,
        db: AsyncSession,
        query: str,
        user_id: uuid.UUID | None = None,
        library_ids: list[uuid.UUID] | None = None,
        item_types: list[str] | None = None,
        limit: int = 10,
        threshold: float = 0.3,
    ) -> list[tuple["SeedItem", float]]:
        """
        语义搜索种子内容项

        Args:
            db: 数据库会话
            query: 查询文本
            user_id: 用户ID（可选，用于限定订阅库）
            library_ids: 限定库ID列表
            item_types: 限定内容类型
            limit: 返回数量限制
            threshold: 相似度阈值

        Returns:
            [(SeedItem, similarity_score), ...]
        """
        # 生成查询向量
        try:
            query_embedding = await embedding_service.get_embedding(query, text_type="query")
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            return []

        # 构建查询条件
        conditions = [
            SeedItem.deleted_at.is_(None),
            SeedItem.is_active,
            SeedItem.embedding.isnot(None),
        ]

        if library_ids:
            conditions.append(SeedItem.library_id.in_(library_ids))

        if item_types:
            conditions.append(SeedItem.item_type.in_(item_types))

        # 使用 pgvector 的 cosine 距离进行相似度搜索
        # 注意：pgvector 的 <=> 操作符返回距离，需要转换为相似度

        similarity_expr = (1 - SeedItem.embedding.cosine_distance(query_embedding)).label("similarity")

        query_stmt = (
            select(SeedItem, similarity_expr)
            .where(and_(*conditions))
            .order_by(similarity_expr.desc())
            .limit(limit * 2)  # 取更多结果以便后续过滤
        )

        result = await db.execute(query_stmt)
        rows = result.all()

        # 过滤低于阈值的结果
        filtered_results = [
            (item, float(score)) for item, score in rows if score >= threshold
        ]

        return filtered_results[:limit]
