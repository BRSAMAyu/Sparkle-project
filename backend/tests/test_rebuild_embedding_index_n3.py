"""FIX-16 ③（E-05 N3）rebuild 脚本 dry-run 无 key 行为测试。

缺陷（REVIEW_RECEIPT_2.md N3 + DYNAMIC_ISSUES V3-FIX-16 ③）：
dry-run 不调 embedding API，却在无 key 时 fail-close（exit 2）——无 key 环境
无法盘点 stale/untagged 行，漂移监控失去唯一的零副作用入口。

修复：无 key 时 dry-run 放行（WARNING + 仅盘点）；``--execute`` 仍 fail-closed
（真实重嵌绝不静默进行）。

脚本以 importlib 从 devtools 目录加载；DB 会话与 Redis 客户端全部替换，
不触 dev PG / dev Redis。
"""
from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path

import pytest

from app.services.embedding_service import embedding_service

_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "devtools" / "rebuild_embedding_index.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("rebuild_embedding_index_n3", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _FakeResult:
    """支持 dry-run 全部读取形态的空结果（.scalars().all() / .all()）。"""

    def scalars(self):
        return self

    def all(self):
        return []


class _FakeSession:
    def __init__(self) -> None:
        self.executed = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def execute(self, _stmt):
        self.executed += 1
        return _FakeResult()

    async def get(self, _model, _pk):
        return None

    async def commit(self):
        return None


class _FakeSessionLocal:
    def __call__(self):
        return _FakeSession()


@pytest.fixture()
def no_embedding_key(monkeypatch):
    monkeypatch.setattr(embedding_service, "dashscope_api_key", None)
    monkeypatch.setattr(embedding_service, "siliconflow_api_key", None)


@pytest.fixture()
def fake_infra(monkeypatch):
    """脚本 main() 内延迟导入的 DB 会话与 Redis 全部替换。"""
    import app.db.session as db_session_mod
    import app.services.rag_indexing_service as rag_mod

    fake_local = _FakeSessionLocal()
    monkeypatch.setattr(db_session_mod, "AsyncSessionLocal", fake_local)
    monkeypatch.setattr(rag_mod, "get_rag_redis", _async_none)
    return fake_local


async def _async_none():
    return None


def _run_script(*argv):
    module = _load_script()
    old_argv = sys.argv
    sys.argv = ["rebuild_embedding_index.py", *argv]
    try:
        return asyncio.run(module.main())
    finally:
        sys.argv = old_argv


@pytest.mark.usefixtures("no_embedding_key")
def test_dry_run_without_key_is_allowed_and_inventories(fake_infra, capsys) -> None:
    """无 key dry-run：退出码 0、WARNING 标注、仅盘点（N3 缺陷本体：旧版 exit 2）。"""
    rc = _run_script("--table", "document_chunks")
    out = capsys.readouterr().out

    assert rc == 0
    assert "WARNING: no embedding provider key configured" in out
    assert "dry-run inventory only" in out
    assert "stale row(s) [dry-run]" in out


@pytest.mark.usefixtures("no_embedding_key")
def test_execute_without_key_still_fail_closed(fake_infra, capsys) -> None:
    """无 key --execute：保持 fail-closed（exit 2），绝不静默重嵌。"""
    rc = _run_script("--table", "document_chunks", "--execute")
    out = capsys.readouterr().out

    assert rc == 2
    assert "FATAL: no embedding provider key configured" in out
    assert "--execute refused" in out


def test_dry_run_with_key_keeps_full_inventory_path(fake_infra, capsys, monkeypatch) -> None:
    """有 key dry-run 走原有路径（回归保护：不因 N3 分支改变有 key 行为）。"""
    monkeypatch.setattr(embedding_service, "dashscope_api_key", "test-key")
    rc = _run_script("--table", "document_chunks")
    out = capsys.readouterr().out

    assert rc == 0
    assert "WARNING: no embedding provider key" not in out
    assert "stale row(s) [dry-run]" in out
