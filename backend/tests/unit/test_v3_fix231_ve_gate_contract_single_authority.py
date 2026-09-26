"""V3-FIX-231（T-ve-gate-contract-single-authority）红绿锁.

wt511 审查轮8 探针实录红×2（真实 api_router+TestClient）：visual-elements
发布闸旗与 /release-flags 契约旗双权威脑裂——

- ``settings.RELEASE_ENABLE_VISUAL_ELEMENTS``（settings.py 五旗权威，wt483 卡 A，
  /release-flags 契约键 ``visual_elements`` 唯一来源）；
- ``settings.ENABLE_VISUAL_ELEMENTS``（wt489 FIX-182 独立开关，router 组注册级
  闸唯一读取）。

两旗互不联动（wt511 探针两态实录）：
1. 契约 True+闸 False → /release-flags 声称开启而 /visual-elements/config
   403 FEATURE_DISABLED（rollout 翻五旗面不生效，契约谎报）；
2. 闸 True+契约 False → 端点越闸撞鉴权（LABS 面静默暴露）而契约仍报 false。

修法（行内二选一取①）：闸改读五旗权威 ``require_release_flag(
"RELEASE_ENABLE_VISUAL_ELEMENTS")``（与 shop/inventory 同形），删独立旗——
契约零漂移（/release-flags 键集与值源不动），单一权威纪律归位
（release_flags.py 模块自述：禁止双权威脑裂）。

回归锁（wt511 探针两态收编转正，修后两态均不可构造）：
- 不变量 A：契约 visual_elements==True ⟹ 端点不得被闸关死（403
  FEATURE_DISABLED 即谎报）——base 上红（只翻契约旗，闸仍读独立旗=False）；
- 不变量 B：契约 visual_elements==False ⟹ 端点必须被闸关死（不得越闸）——
  base/修后恒绿（fail-closed 守卫）；反向脑裂的根因（第二个可独立翻转的
  闸旗在场）由单一权威锁钉死——base 上红（独立旗仍在场）。
"""

from __future__ import annotations

import inspect

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router import api_router
from app.config import settings
from app.db.session import get_db

PROBE_PATH = "/api/v1/visual-elements/config"


@pytest.fixture
def gate_app(db_session: AsyncSession) -> FastAPI:
    """真实 api_router 全量挂载（等价 main.py 的 /api/v1 形态）+ db 覆盖。"""

    async def _override_get_db():
        yield db_session

    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = _override_get_db
    return app


def _contract_visual_elements(client: TestClient) -> bool:
    response = client.get("/api/v1/release-flags")
    assert response.status_code == 200
    return response.json()["visual_elements"]


@pytest.mark.asyncio
async def test_contract_on_gate_must_not_403_lie(gate_app, monkeypatch):
    """不变量 A（wt511 探针态 1 收编）：契约旗 True ⟹ 端点不得 403 FEATURE_DISABLED。

    base 红：闸读独立旗（False）——契约声称开启、端点全关（403 谎报）。
    修后：闸与契约同源（RELEASE 权威），契约 True ⟹ 闸放行（无鉴权深链
    撞端点鉴权 401，而非闸的 403）。
    """
    monkeypatch.setattr(settings, "RELEASE_ENABLE_VISUAL_ELEMENTS", True)

    with TestClient(gate_app, raise_server_exceptions=False) as client:
        assert _contract_visual_elements(client) is True, "契约旗已翻 True"
        response = client.get(PROBE_PATH)

        assert response.status_code == 401, (
            "契约 visual_elements=True 时端点不得被闸关死——无鉴权深链应越过闸"
            f"撞鉴权（401），实际: {response.status_code} {response.text}"
        )
        assert (
            response.json().get("detail") != "FEATURE_DISABLED"
        ), "403 FEATURE_DISABLED=闸谎报（契约声称开启而端点全关，wt511 探针态 1）"


@pytest.mark.asyncio
async def test_contract_off_gate_must_403_no_bypass(gate_app, monkeypatch):
    """不变量 B（wt511 探针态 2 反向守卫）：契约旗 False ⟹ 端点必须 403 关死。

    fail-closed 守卫：契约声称关闭时端点不得越闸暴露（base/修后恒绿——
    默认态安全，防止修法反向放宽）。
    """
    monkeypatch.setattr(settings, "RELEASE_ENABLE_VISUAL_ELEMENTS", False)

    with TestClient(gate_app, raise_server_exceptions=False) as client:
        assert _contract_visual_elements(client) is False, "契约旗 False"
        response = client.get(PROBE_PATH)

        assert (
            response.status_code == 403
        ), f"契约 visual_elements=False 时端点必须被闸关死，实际: {response.status_code}"
        assert response.json()["detail"] == "FEATURE_DISABLED"


def test_single_authority_no_independent_gate_flag():
    """单一权威锁（wt511 探针态 2 根因收编）：独立闸旗不得再在场。

    base 红：settings.ENABLE_VISUAL_ELEMENTS（wt489 FIX-182 独立开关）与
    RELEASE_ENABLE_VISUAL_ELEMENTS 并存=双权威脑裂土壤。修后：闸唯一权威
    =RELEASE 权威（/release-flags 契约同源），router 源面零残留引用。
    """
    assert not hasattr(settings, "ENABLE_VISUAL_ELEMENTS"), (
        "visual-elements 闸唯一权威=RELEASE_ENABLE_VISUAL_ELEMENTS（V3-FIX-231）——"
        "独立开关 ENABLE_VISUAL_ELEMENTS 必须删除，双旗并存即脑裂复发土壤"
    )

    from app.api.v1 import router as router_module

    source = inspect.getsource(router_module)
    assert "ENABLE_VISUAL_ELEMENTS" not in source.replace(
        "RELEASE_ENABLE_VISUAL_ELEMENTS", ""
    ), "api/v1/router.py 不得再读独立闸旗（闸唯一权威=五旗 RELEASE 权威）"
