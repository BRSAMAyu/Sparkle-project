from __future__ import annotations

import pickle
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import networkx as nx
import pytest
import sqlalchemy as sa

from app.config import settings
from app.db.session import Base
from app.db.url import to_sync_database_url
from app.models import (
    ChatMessage,
    ChatSession,
    CognitiveFragment,
    KnowledgeNode,
    NodeRelation,
    Plan,
    Task,
    UserNodeStatus,
)
from app.services.graph_reasoning_service import GraphReasoningService

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _require_alembic():
    try:
        from alembic import command
        from alembic.config import Config
        from alembic.script import ScriptDirectory
    except ModuleNotFoundError as exc:
        pytest.skip(f"Alembic not installed in test environment: {exc}")
    return command, Config, ScriptDirectory


def _sync_database_url() -> str:
    database_url = getattr(settings, "DATABASE_URL", "") or ""
    if not database_url:
        pytest.skip("DATABASE_URL not configured for migration tests")
    if not database_url.startswith(("postgresql", "postgres")):
        pytest.skip(f"Migration tests require PostgreSQL, got {database_url!r}")
    return to_sync_database_url(database_url)


def _connect_sync_engine() -> sa.Engine:
    engine = sa.create_engine(_sync_database_url(), future=True)
    try:
        with engine.connect() as connection:
            connection.execute(sa.text("SELECT 1"))
    except Exception as exc:
        engine.dispose()
        pytest.skip(f"PostgreSQL unavailable for migration tests: {exc}")
    return engine


def _make_alembic_config():
    _, Config, _ = _require_alembic()
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("prepend_sys_path", str(BACKEND_ROOT))
    return config


def _upgrade_to_head() -> tuple[sa.Engine, str]:
    command, _, ScriptDirectory = _require_alembic()
    config = _make_alembic_config()
    engine = _connect_sync_engine()
    try:
        command.upgrade(config, "head")
    except Exception:
        engine.dispose()
        raise

    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()
    assert heads, "Alembic script directory returned no heads"
    return engine, heads[-1]


def test_alembic_head_matches_models():
    engine, _ = _upgrade_to_head()
    try:
        inspector = sa.inspect(engine)
        actual_tables = set(inspector.get_table_names())
        expected_tables = {
            table.name
            for table in Base.metadata.sorted_tables
            if not table.info.get("skip_autogen")
        }
        missing_tables = expected_tables - actual_tables
        assert not missing_tables, f"Missing tables after alembic upgrade head: {sorted(missing_tables)}"
    finally:
        engine.dispose()


def test_migration_idempotent_upgrade():
    command, _, _ = _require_alembic()
    config = _make_alembic_config()
    engine = _connect_sync_engine()
    try:
        command.upgrade(config, "head")
        command.upgrade(config, "head")
    finally:
        engine.dispose()


def test_no_pending_migration_conflicts():
    command, _, ScriptDirectory = _require_alembic()
    config = _make_alembic_config()
    engine = _connect_sync_engine()
    try:
        command.upgrade(config, "head")
        script = ScriptDirectory.from_config(config)
        heads = script.get_heads()
        assert len(heads) == 1, f"Expected a single Alembic head, found {heads}"

        with engine.connect() as connection:
            current_heads = {
                row[0]
                for row in connection.execute(sa.text("SELECT version_num FROM alembic_version"))
            }
        assert current_heads == set(heads), f"Database revision {current_heads} != Alembic head {set(heads)}"
    finally:
        engine.dispose()


def test_critical_tables_exist():
    engine, _ = _upgrade_to_head()
    try:
        inspector = sa.inspect(engine)
        tables = set(inspector.get_table_names())
        critical_tables = {
            ChatSession.__tablename__,
            ChatMessage.__tablename__,
            Plan.__tablename__,
            Task.__tablename__,
            KnowledgeNode.__tablename__,
            UserNodeStatus.__tablename__,
            CognitiveFragment.__tablename__,
        }
        missing = critical_tables - tables
        assert not missing, f"Critical tables missing after migrations: {sorted(missing)}"
    finally:
        engine.dispose()


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute.side_effect = []
    return db


@pytest.fixture
def mock_cache():
    cache = MagicMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    cache.delete = AsyncMock()
    cache.redis = MagicMock()
    cache.redis.get = AsyncMock(return_value=None)
    cache.redis.set = AsyncMock()
    cache.redis.delete = AsyncMock()
    return cache


@pytest.fixture
def graph_service(mock_db):
    return GraphReasoningService(mock_db)


@pytest.mark.asyncio
async def test_graph_caching_preserved(graph_service, mock_db, mock_cache):
    with patch("app.services.graph_reasoning_service.cache_service", mock_cache):
        id_a = uuid.uuid4()
        id_b = uuid.uuid4()

        nodes = [
            KnowledgeNode(id=id_a, name="Node A"),
            KnowledgeNode(id=id_b, name="Node B"),
        ]
        edges: list[NodeRelation] = []

        mock_db.execute.side_effect = [
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=nodes)))),
            MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=edges)))),
        ]

        await graph_service._load_graph()
        assert graph_service.G is not None
        assert graph_service.G.number_of_nodes() == 2
        mock_cache.redis.set.assert_called_once()

        graph_service.G = None

        mock_cache.get = AsyncMock(return_value={"cache": "hit"})
        cached_graph = nx.DiGraph()
        for node in nodes:
            cached_graph.add_node(node.id, name=node.name, description=node.description)
        mock_cache.redis.get = AsyncMock(return_value=pickle.dumps(cached_graph, protocol=5))

        await graph_service._load_graph()
        assert graph_service.G is not None
        assert graph_service.G.number_of_nodes() == 2


@pytest.mark.asyncio
async def test_graph_cache_invalidation_preserved(graph_service, mock_cache):
    with patch("app.services.graph_reasoning_service.cache_service", mock_cache):
        graph_service.G = nx.DiGraph()
        graph_service.G.add_node(uuid.uuid4(), name="Test")

        await graph_service.invalidate_cache()

        mock_cache.redis.delete.assert_called_once_with(graph_service.CACHE_KEY)
        assert graph_service.G is None


@pytest.mark.asyncio
async def test_graph_cycle_detection_preserved(graph_service, mock_db):
    id_a = uuid.uuid4()
    id_b = uuid.uuid4()
    user_id = uuid.uuid4()

    nodes = [
        KnowledgeNode(id=id_a, name="Node A"),
        KnowledgeNode(id=id_b, name="Node B"),
    ]
    edges = [
        NodeRelation(source_node_id=id_a, target_node_id=id_b, relation_type="PREREQUISITE"),
        NodeRelation(source_node_id=id_b, target_node_id=id_a, relation_type="PREREQUISITE"),
    ]

    mock_db.execute.side_effect = [
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=nodes)))),
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=edges)))),
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
    ]

    path = await graph_service.generate_learning_path(user_id, id_b)

    assert len(path) == 1
    assert path[0]["error"] == "cyclic_dependency"
    assert path[0]["error_code"] == "CYCLIC_DEPENDENCY"
    assert "message" in path[0]
    assert "details" in path[0]
    assert "cycle_count" in path[0]["details"]
