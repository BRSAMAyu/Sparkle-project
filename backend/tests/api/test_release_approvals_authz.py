"""R2-08-01 回归证明：/release_approvals 全部端点必须要求 superuser。

鉴权闸门位于路由级依赖 `dependencies=[Depends(get_current_active_superuser)]`
（app/api/v1/release_approvals.py 的 APIRouter 构造参数），对路由内所有端点
（含 4 个只读 GET：列表 / dashboard-summary / admin-tab / 详情）统一生效。

本测试实证两条契约：
1. 普通（非 superuser）登录用户访问任意读端点 → 403（R2-08-01 声称的越权面不存在）；
2. superuser 通过闸门（列表/摘要/页签 200，详情未命中返回 404 而非 403）。
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.api.v1.release_approvals import router as release_approvals_router
from app.core.exceptions import SparkleException
from app.models.user import User

READ_PATHS = ["", "/", "/dashboard-summary", "/admin-tab"]


@pytest.fixture
def release_approvals_client(db_session: AsyncSession):
    app = FastAPI()
    app.include_router(release_approvals_router, prefix="/api/v1")

    @app.exception_handler(SparkleException)
    async def _sparkle_exception_handler(request: Request, exc: SparkleException) -> JSONResponse:
        # 与 app/main.py 的 sparkle_exception_handler 同语义（测试环境无 request_id）
        return JSONResponse(status_code=exc.status_code, content={"success": False, "message": exc.message})

    state = {"current_user": None}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    with TestClient(app) as client:
        yield client, state


async def _create_user(db: AsyncSession, username: str, *, is_superuser: bool = False) -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password="hashed",
        is_active=True,
        is_superuser=is_superuser,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.mark.asyncio
@pytest.mark.parametrize("path", READ_PATHS)
async def test_read_endpoints_reject_normal_user(db_session, release_approvals_client, path: str) -> None:
    """普通用户 JWT 访问 4 个只读端点必须 403（闸门在业务逻辑之前生效）。"""
    client, state = release_approvals_client
    normal_user = await _create_user(db_session, f"ra_normal_{abs(hash(path)) % 10000}")
    state["current_user"] = normal_user

    response = client.get(f"/api/v1/release_approvals{path}")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_detail_endpoint_rejects_normal_user(db_session, release_approvals_client) -> None:
    client, state = release_approvals_client
    normal_user = await _create_user(db_session, "ra_normal_detail")
    state["current_user"] = normal_user

    response = client.get(f"/api/v1/release_approvals/{uuid.uuid4()}")

    assert response.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("path", READ_PATHS)
async def test_read_endpoints_allow_superuser(db_session, release_approvals_client, path: str) -> None:
    client, state = release_approvals_client
    admin = await _create_user(db_session, f"ra_admin_{abs(hash(path)) % 10000}", is_superuser=True)
    state["current_user"] = admin

    response = client.get(f"/api/v1/release_approvals{path}")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_detail_endpoint_superuser_passes_gate(db_session, release_approvals_client) -> None:
    """superuser 通过闸门后进入业务逻辑：不存在的 id → 404（而非 403）。"""
    client, state = release_approvals_client
    admin = await _create_user(db_session, "ra_admin_detail", is_superuser=True)
    state["current_user"] = admin

    response = client.get(f"/api/v1/release_approvals/{uuid.uuid4()}")

    assert response.status_code == 404
