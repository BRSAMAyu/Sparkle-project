"""AURORA-LABEL (PROD-LOG2 ②-7): gateway slug experiments must be UUID-backed.

The Go gateway's ABTestMiddleware maps lanes to slug experiment ids
(``planning-experiment`` / ``default-chat-experiment`` /
``recommendation-experiment``, see
``gateway/internal/middleware/ab_test_middleware.go:getDefaultExperimentID``).
The engine experiments API used to treat any non-UUID id as fallback-to-control
and silently skipped every metric — the whole A/B data plane for those lanes
was dead (production: "Experiment planning-experiment is not UUID-backed" x8 +
"Skipping metric for non-UUID experiment assignment" x8).

Contract under test:
- assign on a known gateway slug resolves/provisions a UUID-backed experiment
  and returns a real variant UUID (no ``fallback``);
- metrics posted with that variant UUID are actually recorded (no skip);
- provisioning is idempotent (one experiment per slug, deterministic
  assignment);
- an operator-created experiment named exactly like the slug is resolved
  instead of shadow-provisioned;
- unknown slugs keep the honest fallback + never create rows + are counted
  (``sparkle_ab_experiment_metric_skip_total``).
"""

from __future__ import annotations

from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY
from sqlalchemy import select

from app.api.deps import get_current_user, get_db
from app.api.v1.experiments import router as experiments_router
from app.core.cache import cache_service
from app.learning.ab_test_framework_enhanced import ABTestFrameworkEnhanced
from app.models.experiment import ABExperiment, ABExperimentMetric, ABExperimentVariant
from app.models.user import User

KNOWN_SLUG = "planning-experiment"


class _FakeProvisionLockRedis:
    """Minimal async redis stub supporting the SET NX EX provisioning lock."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def set(self, key: str, value: str, nx: bool = False, ex: int | None = None) -> bool:
        if nx and key in self.store:
            return False
        self.store[key] = value
        return True


@pytest.fixture
def slug_client(db_session, monkeypatch):
    app = FastAPI()
    app.include_router(experiments_router, prefix="/experiments")

    state = {"current_user": None}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    monkeypatch.setattr(cache_service, "redis", _FakeProvisionLockRedis())

    with TestClient(app) as client:
        yield client, state, db_session


async def _create_user(db_session, username: str) -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def _skip_counter(reason: str) -> float:
    value = REGISTRY.get_sample_value("sparkle_ab_experiment_metric_skip_total", {"reason": reason})
    return value or 0.0


@pytest.mark.asyncio
async def test_gateway_slug_assign_provisions_uuid_backed_experiment(slug_client) -> None:
    client, state, db_session = slug_client
    state["current_user"] = await _create_user(db_session, "slug_probe_user")

    response = client.post(f"/experiments/{KNOWN_SLUG}/assign")

    assert response.status_code == 200
    body = response.json()
    # Real UUID-backed variant, not the dead "control" string fallback.
    assert "fallback" not in body
    assert body["is_new_assignment"] is True
    variant_id = UUID(body["variant_id"])

    experiments = (
        (await db_session.execute(select(ABExperiment).where(ABExperiment.name == KNOWN_SLUG))).scalars().all()
    )
    assert len(experiments) == 1
    experiment = experiments[0]
    variants = (
        (
            await db_session.execute(
                select(ABExperimentVariant).where(ABExperimentVariant.experiment_id == experiment.id)
            )
        )
        .scalars()
        .all()
    )
    variant_ids = {str(v.id) for v in variants}
    assert str(variant_id) in variant_ids
    assert len(variants) == 2
    assert any(v.is_control for v in variants)


@pytest.mark.asyncio
async def test_gateway_slug_assign_is_idempotent(slug_client) -> None:
    client, state, db_session = slug_client
    state["current_user"] = await _create_user(db_session, "slug_probe_user2")

    first = client.post(f"/experiments/{KNOWN_SLUG}/assign").json()
    second = client.post(f"/experiments/{KNOWN_SLUG}/assign").json()

    assert first["variant_id"] == second["variant_id"]
    assert second["is_new_assignment"] is False
    experiments = (
        (await db_session.execute(select(ABExperiment).where(ABExperiment.name == KNOWN_SLUG))).scalars().all()
    )
    assert len(experiments) == 1


@pytest.mark.asyncio
async def test_gateway_slug_metric_is_actually_recorded(slug_client) -> None:
    client, state, db_session = slug_client
    user = await _create_user(db_session, "slug_probe_user3")
    state["current_user"] = user

    assign_body = client.post(f"/experiments/{KNOWN_SLUG}/assign").json()
    variant_id = assign_body["variant_id"]

    response = client.post(
        f"/experiments/{KNOWN_SLUG}/metrics",
        params={"variant_id": variant_id},
        json={
            "metric_name": "success",
            "metric_value": 1.0,
            "metric_type": "success",
            "context_data": {"path": "/api/v1/plans"},
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "recorded"}

    experiment = (await db_session.execute(select(ABExperiment).where(ABExperiment.name == KNOWN_SLUG))).scalars().one()
    metrics = (
        (await db_session.execute(select(ABExperimentMetric).where(ABExperimentMetric.experiment_id == experiment.id)))
        .scalars()
        .all()
    )
    assert len(metrics) == 1
    assert metrics[0].variant_id == UUID(variant_id)
    assert metrics[0].metric_name == "success"


@pytest.mark.asyncio
async def test_existing_named_experiment_is_resolved_not_shadow_provisioned(slug_client) -> None:
    client, state, db_session = slug_client
    user = await _create_user(db_session, "slug_probe_user4")
    state["current_user"] = user

    redis_stub = _FakeProvisionLockRedis()
    framework = ABTestFrameworkEnhanced(db_session, redis_stub)
    operator_experiment = await framework.create_experiment(
        name=KNOWN_SLUG,
        description="Operator-authored planning experiment",
        hypothesis="Personalized plan preview raises plan completion",
        variants=[
            {"name": "control", "is_control": True, "weight": 0.5},
            {"name": "treatment", "is_control": False, "weight": 0.5},
        ],
        metrics=["success"],
        created_by=str(user.id),
    )

    body = client.post(f"/experiments/{KNOWN_SLUG}/assign").json()

    assert "fallback" not in body
    operator_variants = (
        (
            await db_session.execute(
                select(ABExperimentVariant).where(ABExperimentVariant.experiment_id == operator_experiment.id)
            )
        )
        .scalars()
        .all()
    )
    operator_variant_ids = {str(v.id) for v in operator_variants}
    assert body["variant_id"] in operator_variant_ids

    experiments = (
        (await db_session.execute(select(ABExperiment).where(ABExperiment.name == KNOWN_SLUG))).scalars().all()
    )
    assert len(experiments) == 1
    assert experiments[0].id == operator_experiment.id


@pytest.mark.asyncio
async def test_unknown_slug_falls_back_counted_and_creates_no_rows(slug_client) -> None:
    client, state, db_session = slug_client
    user = await _create_user(db_session, "slug_probe_user5")
    state["current_user"] = user

    response = client.post("/experiments/rogue-lane/assign")

    assert response.status_code == 200
    body = response.json()
    assert body["fallback"] is True
    assert body["variant_id"] == "control"

    rogue = (await db_session.execute(select(ABExperiment).where(ABExperiment.name == "rogue-lane"))).scalars().all()
    assert rogue == []

    before = _skip_counter("non_uuid_assignment")
    metric_response = client.post(
        "/experiments/rogue-lane/metrics",
        params={"variant_id": "control"},
        json={"metric_name": "success", "metric_value": 0.0, "metric_type": "success"},
    )
    after = _skip_counter("non_uuid_assignment")

    assert metric_response.status_code == 200
    assert metric_response.json() == {"status": "skipped", "reason": "non_uuid_assignment"}
    # 上报失败可观测：静默跳过必须留下计数痕迹。
    assert after == pytest.approx(before + 1.0)
