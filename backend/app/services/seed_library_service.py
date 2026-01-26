"""
Seed Library Service
种子内容库核心服务 - 管理库、内容项、订阅和查询
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc, text
from sqlalchemy.orm import selectinload
from loguru import logger

from app.models.seed_content import (
    SeedLibrary,
    SeedItem,
    UserLibrarySubscription,
    LibraryCategory,
    LibraryVisibility,
    ItemType,
    DifficultyLevel,
)
from app.schemas.seed_content import (
    LibraryCreate,
    LibraryUpdate,
    ItemCreate,
    ItemUpdate,
    SubscriptionCreate,
    SubscriptionUpdate,
    ItemQueryRequest,
    LibraryListParams,
    ItemListParams,
)


class SeedLibraryService:
    """种子内容库服务"""

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
    ) -> Optional[SeedLibrary]:
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
        user_id: Optional[uuid.UUID] = None,
    ) -> Tuple[List[SeedLibrary], int]:
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
        if params.sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

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
    ) -> Optional[SeedLibrary]:
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
        quality_score: Optional[float] = None,
        is_featured: bool = False,
    ) -> Optional[SeedLibrary]:
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
    ) -> Optional[SeedItem]:
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
        db.add(item)
        await db.flush()
        await db.refresh(item)
        logger.info(f"Added item to library {library_id}: {item.id}")
        return item

    async def get_items(
        self,
        db: AsyncSession,
        params: ItemListParams,
    ) -> Tuple[List[SeedItem], int]:
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
        if params.sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

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
    ) -> Optional[SeedItem]:
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
    ) -> Optional[SeedItem]:
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

        # 更新字段
        if update_data.title is not None:
            item.title = update_data.title
        if update_data.content is not None:
            item.content = update_data.content
        if update_data.content_data is not None:
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
    ) -> Optional[UserLibrarySubscription]:
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
            subscribed_at=datetime.utcnow(),
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
        is_enabled: Optional[bool] = None,
    ) -> List[UserLibrarySubscription]:
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
    ) -> Optional[UserLibrarySubscription]:
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
    ) -> Tuple[List[SeedItem], int]:
        """
        跨订阅库查询内容项

        Args:
            db: 数据库会话
            user_id: 用户ID
            query_request: 查询请求

        Returns:
            (内容项列表, 总数)
        """
        conditions = [SeedItem.deleted_at.is_(None), SeedItem.is_active == True]

        # 确定查询的库范围
        if query_request.use_subscribed_only:
            # 仅从订阅的库查询
            subscribed_lib_ids = await db.execute(
                select(UserLibrarySubscription.library_id).where(
                    and_(
                        UserLibrarySubscription.user_id == user_id,
                        UserLibrarySubscription.is_enabled == True,
                        UserLibrarySubscription.deleted_at.is_(None)
                    )
                )
            )
            lib_ids = [row[0] for row in subscribed_lib_ids.all()]

            if query_request.include_official:
                # 也包含官方库
                official_libs = await db.execute(
                    select(SeedLibrary.id).where(
                        and_(
                            SeedLibrary.is_official == True,
                            SeedLibrary.deleted_at.is_(None)
                        )
                    )
                )
                lib_ids.extend([row[0] for row in official_libs.all()])

            if not lib_ids:
                return [], 0

            conditions.append(SeedItem.library_id.in_(lib_ids))

        # 类型筛选
        if query_request.item_types:
            conditions.append(
                SeedItem.item_type.in_([t.value for t in query_request.item_types])
            )

        # 学科筛选
        if query_request.subjects:
            conditions.append(SeedItem.subject.in_(query_request.subjects))

        # 难度筛选
        if query_request.difficulty_levels:
            conditions.append(
                SeedItem.difficulty_level.in_([d.value for d in query_request.difficulty_levels])
            )

        # 标签筛选
        if query_request.tags:
            for tag in query_request.tags:
                conditions.append(SeedItem.tags.contains([tag]))

        # 关键词搜索
        if query_request.query:
            search_term = f"%{query_request.query}%"
            conditions.append(
                or_(
                    SeedItem.title.ilike(search_term),
                    SeedItem.content.ilike(search_term),
                )
            )

        # 构建查询
        query = select(SeedItem).where(and_(*conditions))

        # 计算总数
        total_query = select(func.count()).select_from(SeedItem).where(and_(*conditions))
        total_result = await db.execute(total_query)
        total = total_result.scalar() or 0

        # 应用限制
        query = query.limit(query_request.limit)
        query = query.order_by(desc(SeedItem.created_at))

        result = await db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_few_shot_examples(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        subject: Optional[str] = None,
        difficulty_level: Optional[str] = None,
        task_type: Optional[str] = None,
        count: int = 3,
    ) -> List[Dict[str, Any]]:
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
            SeedItem.is_active == True,
            SeedItem.item_type == ItemType.EXAMPLE,
        ]

        # 从 few_shot 分类库获取
        few_shot_libs = await db.execute(
            select(SeedLibrary.id).where(
                and_(
                    SeedLibrary.category == LibraryCategory.FEW_SHOT,
                    SeedLibrary.deleted_at.is_(None),
                    or_(
                        SeedLibrary.is_official == True,
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
    ) -> Optional[str]:
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
            SeedItem.is_active == True,
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
                        SeedLibrary.is_official == True,
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
    ) -> Dict[str, Any]:
        """
        获取库统计信息

        Args:
            db: 数据库会话
            library_id: 库ID

        Returns:
            统计信息字典
        """
        # 内容项数量
        item_count_result = await db.execute(
            select(func.count()).select_from(SeedItem).where(
                and_(
                    SeedItem.library_id == library_id,
                    SeedItem.deleted_at.is_(None)
                )
            )
        )
        item_count = item_count_result.scalar() or 0

        # 订阅者数量
        subscriber_count_result = await db.execute(
            select(func.count()).select_from(UserLibrarySubscription).where(
                and_(
                    UserLibrarySubscription.library_id == library_id,
                    UserLibrarySubscription.deleted_at.is_(None)
                )
            )
        )
        subscriber_count = subscriber_count_result.scalar() or 0

        return {
            "item_count": item_count,
            "subscriber_count": subscriber_count,
        }
