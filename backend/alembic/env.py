"""
Alembic Environment Configuration
数据库迁移环境配置
"""
from logging.config import fileConfig
import asyncio

from sqlalchemy import pool, create_engine
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import settings and Base
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.config import settings
from app.db.session import Base

# Import all models to ensure they are registered with Base.metadata
from app.models import (
    # Core models
    User, PushPreference, Task, Plan, ChatMessage, ErrorRecord,
    Job, Subject, IdempotencyKey, Notification, PushHistory,
    # Galaxy models
    KnowledgeNode, UserNodeStatus, NodeRelation, StudyRecord, NodeExpansionQueue,
    # Community models
    Friendship, Group, GroupMember, GroupMessage, GroupTask,
    GroupTaskClaim, SharedResource, PrivateMessage,
    # Cognitive models
    CognitiveFragment, BehaviorPattern,
    # Analytics models
    UserDailyMetric,
    # Curiosity Capsule
    CuriosityCapsule,
    # Focus models
    FocusSession,
    # Vocabulary models
    WordBook, DictionaryEntry
)  # noqa: F401

# this is the Alembic Config object
config = context.config

# Override sqlalchemy.url from settings
# Convert asyncpg URL to psycopg2 for Alembic migrations
database_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
config.set_main_option("sqlalchemy.url", database_url)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model's MetaData object
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode with synchronous engine."""
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
