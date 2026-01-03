"""
Base Model Classes
所有数据库模型的基类
"""
import uuid
from datetime import datetime
from typing import Optional, TypeVar, Type

from sqlalchemy import Column, DateTime, String, select, and_
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declared_attr

from app.db.session import Base


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
        if value is None:
            return value
        elif dialect.name == "postgresql":
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

    deleted_at = Column(DateTime, nullable=True, default=None, index=True)

    @property
    def is_deleted(self) -> bool:
        """检查记录是否已被软删除"""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """标记记录为已删除"""
        self.deleted_at = datetime.utcnow()

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


class BaseModel(SoftDeleteMixin, Base):
    """
    Base model with common fields
    包含 id, created_at, updated_at, deleted_at 字段
    支持软删除
    """

    __abstract__ = True

    id = Column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id})>"

    @classmethod
    async def get_by_id(
        cls: Type[T],
        db: AsyncSession,
        id: uuid.UUID,
        include_deleted: bool = False,
    ) -> Optional[T]:
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
        cls: Type[T],
        db: AsyncSession,
        include_deleted: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
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

    async def save(self, db: AsyncSession) -> "BaseModel":
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


class HardDeleteBaseModel(Base):
    """
    不支持软删除的基础模型
    用于不需要软删除功能的表（如 IdempotencyKey, Job 等临时数据）
    """

    __abstract__ = True

    id = Column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id})>"

    @classmethod
    async def get_by_id(
        cls: Type[T],
        db: AsyncSession,
        id: uuid.UUID,
    ) -> Optional[T]:
        """根据 ID 获取记录"""
        query = select(cls).where(cls.id == id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def save(self, db: AsyncSession) -> "HardDeleteBaseModel":
        """保存当前记录到数据库"""
        db.add(self)
        await db.flush()
        await db.refresh(self)
        return self

    async def delete(self, db: AsyncSession) -> None:
        """物理删除记录"""
        await db.delete(self)
        await db.flush()
