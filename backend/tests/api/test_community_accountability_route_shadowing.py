"""Regression test for ISSUE-20260503-1300-B1: experience.py stub shadowed community_router.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute


def _route_for_path(routes, path: str, method: str) -> APIRoute | None:
    for route in routes:
        if not isinstance(route, APIRoute):
            continue
        if route.path == path and method in (route.methods or set()):
            return route
    return None


def _load_experience_routers_into(app: FastAPI):
    """Replicate _include_experience_routers() but target a specific app."""
    experience_dir = Path(__file__).resolve().parents[3] / "app" / "api" / "v1" / "experience"
    existing = {_route_key(r) for r in app.routes}

    for router_file in sorted(experience_dir.glob("*_router.py")):
        module_name = f"app.api.v1.experience_closeout_{router_file.stem}"
        spec = importlib.util.spec_from_file_location(module_name, router_file)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        router = getattr(module, "router", None)
        if router is None:
            continue
        incoming = {_route_key(r) for r in router.routes}
        if existing.isdisjoint(incoming):
            app.include_router(router)
            existing |= incoming


def _route_key(route) -> tuple:
    path = getattr(route, "path", None) or ""
    methods = frozenset(getattr(route, "methods", None) or [])
    return path, methods


@pytest.mark.asyncio
async def test_community_accountability_route_uses_complete_impl():
    """
    Replicate the production registration order (experience.router first,
    then community_router via _include_experience_routers) and verify the
    final /community-accountability route uses CommunityAccountabilityOut.
    """
    from app.api.v1.experience import router as experience_router

    app = FastAPI()
    app.include_router(experience_router)
    _load_experience_routers_into(app)

    # Both routers use prefix="/experience", so the full path includes it.
    route = _route_for_path(app.routes, "/experience/community-accountability", "GET")

    assert route is not None, (
        "/experience/community-accountability route is missing from the app. "
        "community_router.py may have failed to register."
    )

    assert route.response_model is not None, (
        "/experience/community-accountability must have a response_model "
        "(CommunityAccountabilityOut). The old stub returns plain dict (no response_model)."
    )

    keys = set(route.response_model.model_fields.keys())
    assert "my_commitments" in keys, (
        f"Expected my_commitments in response model, got {keys}. "
        "The old stub may still be shadowing the full implementation."
    )
    assert "partner_progress" in keys
    assert "shared_goals" in keys
    assert "squad_risks" in keys
    assert "helpable" in keys
    # Old stub fields must NOT be present
    assert "commitments" not in keys, "Old stub field 'commitments' leaked through"
    assert "partner_updates" not in keys, "Old stub field 'partner_updates' leaked through"
    assert "suggested_actions" not in keys, "Old stub field 'suggested_actions' leaked through"


@pytest.mark.asyncio
async def test_community_accountability_no_longer_on_experience_router():
    """The experience.py router must no longer own /community-accountability."""
    from app.api.v1.experience import router as experience_router

    simple_routes = {
        r.path for r in experience_router.routes
        if isinstance(r, APIRoute)
    }
    assert "/community-accountability" not in simple_routes, (
        "experience.py still has GET /community-accountability; remove the stub "
        "so community_router.py can register its full implementation."
    )
