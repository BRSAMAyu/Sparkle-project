"""V3-FIX-54 · 用户文档删除无 HTTP 出口 —— DELETE /api/v1/documents/{file_id} 红绿锁.

wt394 Q-02 GJ10（v3-output/WT394-Q02-GOLDEN/raw/GJ10_local.jsonl）：上传链
完整可用（POST /documents/upload → MinIO 预签名 PUT → confirm-upload →
status 走到 processed），但用户「删除已上传资料」在 /documents API 面
无出口——``DELETE /documents/{file_id}`` 404，``/documents/clean`` 是
ingestion 面独立子系统（400）。

修复口径（复用既有权威实现）：
- ``/api/v1/sources/{source_id}`` DELETE 已有完整删除语义
  （``SourceLifecycleService.delete``：软删 + chunks/群组链接软删 +
  lifecycle→REVOKED 召回排除 + 提交后检索失效 + MinIO 对象擦除）。
  本卡把该语义接到用户上传流所在的 /documents 面：DELETE 路由委托同一
  服务，不复制实现。
- 存储清理失败不阻塞删除语义：``erasure_receipt`` 落
  ``:object_delete_pending`` 收据（一致性边界已在服务层定义），HTTP 仍 200。

红测（base 上红）：
1. DELETE /api/v1/documents/{file_id} 200 + 软删 + 召回排除（base 404/405：红）。
2. 归属校验：非属主 404，文件不受影响（base 路由不存在：红）。
3. 存储擦除失败不阻塞删除（base 路由不存在：红）。
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.documents import router as documents_router
from app.db.session import get_db
from app.models.document_chunks import DocumentChunk
from app.models.file_storage import SourceLifecycleStatus, StoredFile
from app.models.user import User
from app.services import source_lifecycle as sl
from app.services.source_lifecycle import source_lifecycle_service

# --- 基建 ----------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _no_rag_redis(monkeypatch):
    """删除路径不触真实 Redis（与 tests/services/test_source_lifecycle.py 同款隔离）。"""
    from unittest.mock import AsyncMock

    monkeypatch.setattr(sl, "get_rag_redis", AsyncMock(return_value=None))


@pytest.fixture(name="documents_app")
async def documents_app_fixture(db_session, test_user: User):
    app = FastAPI()
    app.include_router(documents_router, prefix="/api/v1/documents")

    async def _override_db():
        yield db_session

    async def _override_user():
        return test_user

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    yield app
    app.dependency_overrides.clear()


async def _owned_source_with_chunk(db_session: AsyncSession, user_id) -> tuple[StoredFile, DocumentChunk]:
    stored_file = StoredFile(
        user_id=user_id,
        file_name="q02_gj10_allergy_note.txt",
        mime_type="text/plain",
        file_size=64,
        bucket="test",
        object_key=f"{user_id}/{uuid4()}/original.txt",
        status="processed",
        visibility="private",
        retention_policy="standard",
    )
    db_session.add(stored_file)
    await db_session.flush()
    chunk = DocumentChunk(
        file_id=stored_file.id,
        user_id=user_id,
        chunk_index=0,
        content="花生过敏注意事项：避免一切含花生制品。",
    )
    db_session.add(chunk)
    await db_session.flush()
    return stored_file, chunk


# --- 红测 1：删除出口 + 软删 + 召回排除 ------------------------------------------


@pytest.mark.asyncio
async def test_delete_document_soft_deletes_and_excludes_from_recall(
    documents_app: FastAPI, db_session: AsyncSession, test_user: User
) -> None:
    stored_file, chunk = await _owned_source_with_chunk(db_session, test_user.id)

    async with AsyncClient(
        transport=ASGITransport(app=documents_app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        resp = await client.delete(f"/api/v1/documents/{stored_file.id}")

    assert resp.status_code in (
        200,
        204,
    ), f"删除出口必须可达（base 404/405），实际 {resp.status_code}: {resp.text[:200]}"

    await db_session.refresh(stored_file)
    await db_session.refresh(chunk)
    assert stored_file.deleted_at is not None, "记录必须软删（不可物理消失）"
    assert stored_file.lifecycle_status == SourceLifecycleStatus.REVOKED.value, "lifecycle 必须 REVOKED（召回排除）"
    assert chunk.deleted_at is not None, "文档 chunks 必须软删（RAG 召回排除）"
    assert not source_lifecycle_service.should_include_in_retrieval(stored_file), "软删后不得参与召回"

    # 删除后再查状态 = 404（既有 is_deleted 过滤生效）
    async with AsyncClient(
        transport=ASGITransport(app=documents_app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        resp2 = await client.get(f"/api/v1/documents/{stored_file.id}/status")
    assert resp2.status_code == 404, f"已删文件 status 必须按不存在处理，实际 {resp2.status_code}"


# --- 红测 2：归属校验 ------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_document_is_owner_scoped(
    documents_app: FastAPI, db_session: AsyncSession, test_user: User
) -> None:
    stored_file, _chunk = await _owned_source_with_chunk(db_session, test_user.id)

    # 非属主身份（仅用 id 过滤，无需真实第二用户行）
    other = User(id=uuid4(), email=f"other-{uuid4().hex[:8]}@test.local", username="other")

    # 以非属主身份删除（覆盖依赖为 test_user → 换 app 覆盖 other）
    app = FastAPI()
    app.include_router(documents_router, prefix="/api/v1/documents")

    async def _override_db():
        yield db_session

    async def _override_other():
        return other

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_other

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        resp = await client.delete(f"/api/v1/documents/{stored_file.id}")

    assert resp.status_code == 404, f"非属主删除必须 404（不暴露存在性），实际 {resp.status_code}"
    await db_session.refresh(stored_file)
    assert stored_file.deleted_at is None, "非属主删除不得影响文件"


# --- 红测 3：存储擦除失败不阻塞删除语义 -------------------------------------------


@pytest.mark.asyncio
async def test_delete_document_survives_storage_erase_failure(
    documents_app: FastAPI,
    db_session: AsyncSession,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.document_upload_storage import document_upload_storage

    def _boom(**kwargs):
        raise RuntimeError("simulated minio outage")

    monkeypatch.setattr(document_upload_storage, "delete_object", _boom)

    stored_file, _chunk = await _owned_source_with_chunk(db_session, test_user.id)

    async with AsyncClient(
        transport=ASGITransport(app=documents_app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        resp = await client.delete(f"/api/v1/documents/{stored_file.id}")

    assert resp.status_code in (200, 204), f"存储清理失败不得阻塞删除语义，实际 {resp.status_code}"
    await db_session.refresh(stored_file)
    assert stored_file.deleted_at is not None, "存储失败时记录仍必须软删"
    assert stored_file.erasure_receipt and "object_delete_pending" in str(
        stored_file.erasure_receipt
    ), f"存储清理失败必须留 object_delete_pending 收据（一致性行为），实际: {stored_file.erasure_receipt!r}"
