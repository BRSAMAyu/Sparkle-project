"""卡 A（T-release-flag-authority）：release flag 单一权威 + 契约端点（wt483 PLAN §2.1/§2.8/§4-卡A）。

验收形制（改造吸收 cosmos T36 test_t36_release_flags.py，按主线单一权威重写）：
- RELEASE_ENABLE_* 五旗定义在 Settings 单一权威，默认全 False（安全默认）；
- release_flags.py 是薄视图（禁第二个 BaseSettings——V3-FIX-21 同族禁令）；
- GET /api/v1/release-flags 单一响应形（小写 snake_case，键集=移动端解码面，PLAN §2.8.1）；
- require_release_flag 工厂：旗 False→403 FEATURE_DISABLED / True→放行（测试内翻转，不改默认）；
- 卡 A 红线守卫（已阶段化演进，V3-FIX-05）：release-flag 依赖只允许出现在已
  裁决组（现 = /shop、/inventory，wt483 PLAN §2.2 卡 C shop 提前量），其他组
  消费即红；卡 A 落地时原形为全禁零消费。
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient

from app.api.v1.router import api_router
from app.config import settings
from app.config.release_flags import (
    RELEASE_FLAG_FIELDS,
    release_flags,
    release_flags_response,
    require_release_flag,
)

# PLAN §2.8.1：单一响应形键集（去 RELEASE_ENABLE_ 前缀、小写 snake_case）＝移动端 provider 解码面
EXPECTED_CONTRACT_KEYS = frozenset(
    {"shop", "photon_transfer", "public_leaderboards", "public_community", "visual_elements"}
)


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")
    with TestClient(app) as test_client:
        yield test_client


class TestReleaseFlagSingleAuthority:
    """PLAN §2.1/§3：旗权威唯一在 Settings 单例，release_flags.py 只是薄视图。"""

    def test_five_release_flags_declared_in_settings_default_false(self):
        """五旗必须在 Settings 权威上可见且默认 False（安全默认）。"""
        assert set(RELEASE_FLAG_FIELDS) == {
            "RELEASE_ENABLE_SHOP",
            "RELEASE_ENABLE_PHOTON_TRANSFER",
            "RELEASE_ENABLE_PUBLIC_LEADERBOARDS",
            "RELEASE_ENABLE_PUBLIC_COMMUNITY",
            "RELEASE_ENABLE_VISUAL_ELEMENTS",
        }
        for name in RELEASE_FLAG_FIELDS:
            assert getattr(settings, name) is False, f"{name} must default to False (safe default)"

    def test_release_flags_view_reads_settings_singleton(self):
        """薄视图 release_flags() 读 settings 单例，默认全 False。"""
        view = release_flags()
        assert set(view.keys()) == set(RELEASE_FLAG_FIELDS)
        assert all(value is False for value in view.values())

    def test_release_flags_response_shape_is_lowercase_snake(self):
        """契约响应构造：去 RELEASE_ENABLE_ 前缀的小写 snake_case 单一形。"""
        response = release_flags_response()
        assert set(response.keys()) == EXPECTED_CONTRACT_KEYS
        assert all(value is False for value in response.values())

    def test_no_second_basesettings_in_release_flags_module(self):
        """V3-FIX-21 同族禁令：薄视图模块不得再实例化/继承 BaseSettings（AST 守卫）。"""
        module_path = Path(__file__).resolve().parents[2] / "app" / "config" / "release_flags.py"
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                base_names = {getattr(base, "id", getattr(base, "attr", "")) for base in node.bases}
                assert "BaseSettings" not in base_names, (
                    f"release_flags.py must not declare a second BaseSettings ({node.name}) — "
                    "single authority lives in app/config/settings.py (PLAN §2.1)"
                )


class TestRequireReleaseFlagDependency:
    """PLAN §2.1.2：T36 的 403 FEATURE_DISABLED 语义原样保留（当前无路由消费=零行为）。"""

    def test_disabled_flag_raises_403_feature_disabled(self):
        dependency = require_release_flag("RELEASE_ENABLE_SHOP")
        with pytest.raises(HTTPException) as exc_info:
            dependency()
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert exc_info.value.detail == "FEATURE_DISABLED"

    def test_custom_status_code_404_form(self):
        """保留 T36 的自定义状态码形制（404 隐藏面语义备用）。"""
        dependency = require_release_flag("RELEASE_ENABLE_SHOP", status_code=status.HTTP_404_NOT_FOUND)
        with pytest.raises(HTTPException) as exc_info:
            dependency()
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "FEATURE_DISABLED"

    def test_unknown_flag_fails_closed(self):
        """未知旗名 fail-closed（403），与安全默认同向。"""
        dependency = require_release_flag("RELEASE_ENABLE_NON_EXISTENT")
        with pytest.raises(HTTPException) as exc_info:
            dependency()
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    def test_enabled_flag_passes(self, monkeypatch: pytest.MonkeyPatch):
        """旗开时放行——测试内翻转 settings 单例属性，不改默认值。"""
        monkeypatch.setattr(settings, "RELEASE_ENABLE_SHOP", True)
        dependency = require_release_flag("RELEASE_ENABLE_SHOP")
        dependency()  # 不抛即放行

    def test_monkeypatch_does_not_leak_across_dependencies(self, monkeypatch: pytest.MonkeyPatch):
        """翻转只影响被翻的旗，其余旗仍走默认 False。"""
        monkeypatch.setattr(settings, "RELEASE_ENABLE_PUBLIC_COMMUNITY", True)
        assert settings.RELEASE_ENABLE_SHOP is False
        with pytest.raises(HTTPException):
            require_release_flag("RELEASE_ENABLE_SHOP")()


class TestReleaseFlagsContractEndpoint:
    """PLAN §2.8：GET /api/v1/release-flags 契约端点（移动端将来经网关读取）。"""

    def test_endpoint_returns_single_shape_all_false(self, client: TestClient):
        response = client.get("/api/v1/release-flags")
        assert response.status_code == 200
        data = response.json()
        assert set(data.keys()) == EXPECTED_CONTRACT_KEYS
        assert all(value is False for value in data.values())

    def test_endpoint_reflects_flag_toggle(self, client: TestClient, monkeypatch: pytest.MonkeyPatch):
        """端点读单一权威实时值（测试内翻转，不改默认）。"""
        monkeypatch.setattr(settings, "RELEASE_ENABLE_SHOP", True)
        monkeypatch.setattr(settings, "RELEASE_ENABLE_PUBLIC_COMMUNITY", True)
        response = client.get("/api/v1/release-flags")
        assert response.status_code == 200
        data = response.json()
        assert data["shop"] is True
        assert data["public_community"] is True
        assert data["photon_transfer"] is False
        assert data["public_leaderboards"] is False
        assert data["visual_elements"] is False

    def test_api_root_index_lists_release_flags(self, client: TestClient):
        """PLAN §2.8.3：api_root prefixes 列表补 /release-flags 行。"""
        response = client.get("/api/v1/")
        assert response.status_code == 200
        assert "/release-flags" in response.json()["endpoints"]

    def test_openapi_contains_release_flags_get_operation(self):
        """新端点入 OpenAPI 契约面（快照重冻结的前提形制）。"""
        app = FastAPI()
        app.include_router(api_router, prefix="/api/v1")
        schema = app.openapi()
        operation = schema["paths"]["/api/v1/release-flags"]["get"]
        assert "200" in operation["responses"]


class TestCardAZeroBehaviorRedLine:
    """release-flag 消费面守卫（卡 A 红线的阶段化演进）。

    卡 A 落地时是零行为红线（无任何路由消费）；V3-FIX-05（wt483 PLAN §2.2
    卡 C shop 提前量）起 /shop、/inventory 两组合法消费 RELEASE_ENABLE_SHOP。
    本守卫钉住：消费面只能停在已裁决的组上，任何其他组偷挂 release-flag
    依赖即红（挂旗必须走卡片裁决，不允许顺手扩散）。
    """

    # 已裁决的 release-flag 消费组（api_router 相对前缀 → 消费卡片）
    ALLOWED_FLAG_CONSUMING_PREFIXES = frozenset({"/shop", "/inventory"})

    def test_release_flag_dependency_only_on_adjudicated_groups(self):
        scanned = 0
        consuming = set()
        for route in api_router.routes:
            route_dependencies = getattr(route, "dependencies", [])
            for dependency in route_dependencies:
                qualname = getattr(getattr(dependency, "dependency", None), "__qualname__", "")
                if "require_release_flag" in qualname:
                    consuming.add(getattr(route, "path", "?"))
                scanned += 1
        assert scanned > 0, "scan must be non-vacuous: api_router routes carry (auth) dependencies"
        unexpected = {
            path
            for path in consuming
            if not any(path == p or path.startswith(f"{p}/") for p in self.ALLOWED_FLAG_CONSUMING_PREFIXES)
        }
        assert not unexpected, (
            f"routes outside adjudicated groups consume release-flag dependencies: {sorted(unexpected)} — "
            "mounting a flag requires a card adjudication (wt483 PLAN), not a drive-by"
        )
        # 本卡裁决面非空：shop/inventory 两组在场（否则守卫退化为空许可）
        assert consuming, "shop/inventory must consume require_release_flag (V3-FIX-05 gate)"

    def test_release_flags_module_exposes_no_router(self):
        """薄视图不自带 APIRouter——端点注册唯一入口在 api/v1/router.py。"""
        import app.config.release_flags as release_flags_module

        assert not hasattr(
            release_flags_module, "router"
        ), "release_flags.py must stay a thin view module (no APIRouter of its own)"
