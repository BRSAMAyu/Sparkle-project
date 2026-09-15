"""Regression test for ISSUE-20260503-1300-B1: experience.py stub shadowed community_router.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute

_EXPERIENCE_DIR = Path(__file__).resolve().parents[2] / "app" / "api" / "v1" / "experience"


def _route_for_path(routes, path: str, method: str) -> APIRoute | None:
    for route in routes:
        if not isinstance(route, APIRoute):
            continue
        if route.path == path and method in (route.methods or set()):
            return route
    return None


def _load_router(filename: str):
    """Load an experience sub-router by filename."""
    router_file = _EXPERIENCE_DIR / filename
    spec = importlib.util.spec_from_file_location(
        f"app.api.v1.experience_closeout_{router_file.stem}", router_file
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {router_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    router = getattr(module, "router", None)
    if router is None:
        raise RuntimeError(f"No router attr in {filename}")
    return router


@pytest.mark.asyncio
async def test_community_accountability_registered_with_response_model():
    """
    After including experience.router (without the stub) and then
    community_router, the /experience/community-accountability route
    must use CommunityAccountabilityOut, not a plain dict.
    """
    from app.api.v1.experience import router as experience_router

    app = FastAPI()
    app.include_router(experience_router)

    # Simulate what _include_experience_routers does — include community_router
    community_router = _load_router("community_router.py")
    app.include_router(community_router)

    route = _route_for_path(app.routes, "/experience/community-accountability", "GET")
    assert route is not None, (
        "/experience/community-accountability route missing after including both routers."
    )
    assert route.response_model is not None, (
        "Route must have a response_model (CommunityAccountabilityOut), "
        "not a plain dict like the old stub."
    )
    keys = set(route.response_model.model_fields.keys())
    assert "my_commitments" in keys, f"Expected my_commitments, got {keys}"
    assert "partner_progress" in keys
    assert "shared_goals" in keys
    assert "squad_risks" in keys
    assert "helpable" in keys
    assert "commitments" not in keys, "Old stub field 'commitments' leaked"
    assert "partner_updates" not in keys, "Old stub field 'partner_updates' leaked"
    assert "suggested_actions" not in keys, "Old stub field 'suggested_actions' leaked"


@pytest.mark.asyncio
async def test_experience_router_no_longer_has_stub():
    """The experience.py router must not own /community-accountability anymore."""
    from app.api.v1.experience import router as experience_router

    paths = {r.path for r in experience_router.routes if isinstance(r, APIRoute)}
    assert "/community-accountability" not in paths, (
        "experience.py still has GET /community-accountability; remove the stub."
    )
