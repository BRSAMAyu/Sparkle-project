"""
Alembic Environment Configuration
数据库迁移环境配置
"""
from logging.config import fileConfig
import os
import sys

from sqlalchemy import create_engine, pool
import sqlalchemy as sa

from alembic import context

# Ensure backend/ is on sys.path for CLI usage
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.config import settings
from app.db.session import Base
from app.db.url import to_sync_database_url

# Import all models to ensure they are registered with Base.metadata
from app.models import (
    # Core models
    User, PushPreference, Task, Plan, ChatMessage, ErrorRecord,
    Job, Subject, IdempotencyKey, Notification, PushHistory,
    # Galaxy models
    KnowledgeNode, UserNodeStatus, NodeRelation, StudyRecord, NodeExpansionQueue, ExpansionFeedback,
    # Community models
    Friendship, Group, GroupMember, GroupMessage, GroupTask,
    GroupTaskClaim, SharedResource, PrivateMessage, Post, PostLike,
    # Cognitive models
    CognitiveFragment, BehaviorPattern,
    # Analytics models
    UserDailyMetric,
    # Curiosity Capsule
    CuriosityCapsule,
    # Focus models
    FocusSession,
    # Vocabulary models
    WordBook, DictionaryEntry,
    # Intervention models
    InterventionRequest, InterventionAuditLog, InterventionFeedback, UserInterventionSettings,
    # Phase 1 models
    TrackingEvent, UserStateSnapshot,
    # Phase 2 models
    StrategyNode, SemanticLink,
    # Recommendation models
    UserSimilarity, ItemSimilarity, UserItemInteraction, UserLearningProfile, RecommendationCache, LeaderboardSnapshot,
    NightlyReview,
    # Seed Content Library
    SeedLibrary, SeedItem, UserLibrarySubscription,
)  # noqa: F401

# this is the Alembic Config object
config = context.config

# Override sqlalchemy.url from settings
database_url = to_sync_database_url(settings.DATABASE_URL)
# Fix for configparser interpolation error when using special characters like %
database_url = database_url.replace("%", "%%")
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


def _ensure_alembic_version_table(connection) -> None:
    inspector = sa.inspect(connection)
    if not inspector.has_table("alembic_version"):
        metadata = sa.MetaData()
        sa.Table(
            "alembic_version",
            metadata,
            sa.Column("version_num", sa.String(64), nullable=False),
            sa.PrimaryKeyConstraint("version_num", name="alembic_version_pkc"),
        )
        metadata.create_all(connection)
        return

    columns = inspector.get_columns("alembic_version")
    version_col = next((col for col in columns if col.get("name") == "version_num"), None)
    if not version_col:
        return

    length = getattr(version_col.get("type"), "length", None)
    if length is None or length >= 64:
        return

    if connection.dialect.name == "postgresql":
        connection.execute(
            sa.text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(64)")
        )


def run_migrations_online() -> None:
    """Run migrations in 'online' mode with synchronous engine."""
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        _ensure_alembic_version_table(connection)
        # _ensure_alembic_version_table() can open an implicit transaction via
        # inspector/create_all. Commit it before Alembic starts its own
        # migration transaction; otherwise SQLAlchemy will roll everything back
        # when the connection closes even though the migration log looks
        # successful.
        if connection.in_transaction():
            connection.commit()
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
