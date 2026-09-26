"""
Base Model Classes
所有数据库模型的基类
"""
from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import datetime
from typing import Any, ClassVar, TypeVar

from sqlalchemy import DateTime, exc, select
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import CHAR, TypeDecorator

from app.core.time_utils import utcnow as _utcnow
from app.db.session import Base


class SafeReprMixin:
    """
    IO-free ``__repr__`` for ORM models（V3-FIX-298 族防御加固）.

    选型依据：SQLAlchemy 2.x 没有内置的 repr 生成控制——``MappedAsDataclass``
    生成的 dataclass repr 会经描述符读取全部映射属性（含 lazy 关系），恰恰是
    事故放大器而非防御。官方提供的"只读已加载值"机制是
    ``inspect(instance).dict``（InstanceState.dict）：它绕过
    InstrumentedAttribute 描述符直接读已加载值字典，因此本 mixin 的 repr

    - 永不触发 lazy load / 过期属性刷新（greenlet 上下文外 DB IO）；
    - 永不抛 MissingGreenlet / DetachedInstanceError；
    - 对 expired / detached / expunged 实例退化为 ``id=?``（值未加载），
      而不是毒化共享会话。

    子类可用 ``__repr_fields__`` 追加标量字段（沿用旧手写 repr 的信息价值）；
    仅渲染已加载值，未加载的渲染 ``?``。字段名与主键同名时跳过（主键已渲染）。
    """

    __repr_fields__: ClassVar[tuple[str, ...]] = ()

    def __repr__(self) -> str:
        cls_name = type(self).__name__
        try:
            state = sa_inspect(self)
            if state is None:  # pragma: no cover - 非映射对象防御
                return f"<{cls_name} (unmapped)>"
        except exc.NoInspectionAvailable:  # pragma: no cover - 非映射对象防御
            return f"<{cls_name} (unmapped)>"
        loaded: Mapping[str, Any] = state.dict

        parts: list[str] = []
        seen: set[str] = set()
        for column in state.mapper.primary_key:
            name = column.key
            seen.add(name)
            parts.append(f"{name}={loaded[name]}" if name in loaded else f"{name}=?")
        for name in self.__repr_fields__:
            if name in seen:
                continue
            seen.add(name)
            parts.append(f"{name}={loaded[name]}" if name in loaded else f"{name}=?")
        return f"<{cls_name}({', '.join(parts)})>"


class GUID(TypeDecorator):
    """
    Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36), storing as stringified hex values.
    兼容 SQLite 和 PostgreSQL 的 UUID 类型
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None or dialect.name == "postgresql":
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            else:
                return value


T = TypeVar("T", bound="BaseModel")


class SoftDeleteMixin:
    """
    软删除 Mixin
    提供 deleted_at 字段和软删除相关方法
    """

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None, index=True)

    @property
    def is_deleted(self) -> bool:
        """检查记录是否已被软删除"""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """标记记录为已删除"""
        self.deleted_at = _utcnow()

    def restore(self) -> None:
        """恢复已删除的记录"""
        self.deleted_at = None

    @classmethod
    def not_deleted_filter(cls):
        """返回未删除记录的过滤条件"""
        return cls.deleted_at.is_(None)

    @classmethod
    def deleted_filter(cls):
        """返回已删除记录的过滤条件"""
        return cls.deleted_at.isnot(None)


class BaseModel(SafeReprMixin, SoftDeleteMixin, Base):
    """
    Base model with common fields
    包含 id, created_at, updated_at, deleted_at 字段
    支持软删除
    """

    __abstract__ = True

    id: Mapped[Any] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    @classmethod
    async def get_by_id(
        cls: type[T],
        db: AsyncSession,
        id: uuid.UUID,
        include_deleted: bool = False,
    ) -> T | None:
        """
        根据 ID 获取记录

        Args:
            db: 数据库会话
            id: 记录 ID
            include_deleted: 是否包含已删除的记录

        Returns:
            找到的记录或 None
        """
        query = select(cls).where(cls.id == id)
        if not include_deleted:
            query = query.where(cls.not_deleted_filter())
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def get_all(
        cls: type[T],
        db: AsyncSession,
        include_deleted: bool = False,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[T]:
        """
        获取所有记录

        Args:
            db: 数据库会话
            include_deleted: 是否包含已删除的记录
            limit: 限制返回数量
            offset: 偏移量

        Returns:
            记录列表
        """
        query = select(cls)
        if not include_deleted:
            query = query.where(cls.not_deleted_filter())
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def save(self, db: AsyncSession) -> BaseModel:
        """保存当前记录到数据库"""
        db.add(self)
        await db.flush()
        await db.refresh(self)
        return self

    async def delete(self, db: AsyncSession, soft: bool = True) -> None:
        """
        删除记录

        Args:
            db: 数据库会话
            soft: 是否软删除（默认为 True）
        """
        if soft:
            self.soft_delete()
            await db.flush()
        else:
            await db.delete(self)
            await db.flush()


class HardDeleteBaseModel(SafeReprMixin, Base):
    """
    不支持软删除的基础模型
    用于不需要软删除功能的表（如 IdempotencyKey, Job 等临时数据）
    """

    __abstract__ = True

    id: Mapped[Any] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    @classmethod
    async def get_by_id(
        cls: type[T],
        db: AsyncSession,
        id: uuid.UUID,
    ) -> T | None:
        """根据 ID 获取记录"""
        query = select(cls).where(cls.id == id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def save(self, db: AsyncSession) -> HardDeleteBaseModel:
        """保存当前记录到数据库"""
        db.add(self)
        await db.flush()
        await db.refresh(self)
        return self

    async def delete(self, db: AsyncSession) -> None:
        """物理删除记录"""
        await db.delete(self)
        await db.flush()
