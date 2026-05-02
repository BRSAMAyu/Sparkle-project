from __future__ import annotations

from types import SimpleNamespace

import pytest
from starlette.requests import Request

from app.api.v1.research_consent import ConsentRevokeRequest, get_research_consent, revoke_research_consent
from app.models.research_consent import ResearchConsentRecord
from app.signals.research_mode import ConsentTracker


@pytest.mark.asyncio
async def test_consent_persists_across_tracker_instances(db_session):
    tracker = ConsentTracker()
    await tracker.grant_consent_async(
        user_id="u_persist",
        consent_type="research_analytics",
        reason="onboarding opt-in",
        initiator="user",
        ip_address="203.0.113.7",
        db=db_session,
    )

    restarted_tracker = ConsentTracker()

    assert await restarted_tracker.has_consent_async("u_persist", "research_analytics", db=db_session) is True
    records = await restarted_tracker.get_user_consents_async("u_persist", db=db_session)
    assert records[0]["reason"] == "onboarding opt-in"
    assert records[0]["initiator"] == "user"
    assert records[0]["ip_hash"] != "203.0.113.7"
    assert len(records[0]["ip_hash"]) == 64


@pytest.mark.asyncio
async def test_revoke_is_immediate_even_with_stale_list_cache(db_session):
    tracker_a = ConsentTracker()
    tracker_b = ConsentTracker()

    await tracker_a.grant_consent_async(user_id="u_revoke", consent_type="anonymized_export", db=db_session)
    cached_records = await tracker_a.get_user_consents_async("u_revoke", db=db_session)
    assert cached_records[0]["granted"] is True

    revoked = await tracker_b.revoke_consent_async(
        user_id="u_revoke",
        consent_type="anonymized_export",
        reason="settings toggle off",
        initiator="user",
        db=db_session,
    )

    assert revoked is not None
    assert await tracker_a.has_consent_async("u_revoke", "anonymized_export", db=db_session) is False
    records = await tracker_a.get_user_consents_async("u_revoke", db=db_session)
    assert records[0]["granted"] is False
    assert records[0]["reason"] == "settings toggle off"


@pytest.mark.asyncio
async def test_concurrent_grant_is_idempotent_for_active_protocol(db_session):
    tracker = ConsentTracker()

    first = await tracker.grant_consent_async(user_id="u_concurrent", consent_type="cohort_comparison", db=db_session)
    second = await tracker.grant_consent_async(
        user_id="u_concurrent",
        consent_type="cohort_comparison",
        reason="second click",
        db=db_session,
    )

    assert first.consent_id == second.consent_id
    records = await tracker.get_user_consents_async("u_concurrent", db=db_session)
    assert len(records) == 1
    assert records[0]["reason"] == "second click"


@pytest.mark.asyncio
async def test_research_consent_api_get_and_revoke(db_session):
    user = SimpleNamespace(id="api_user_1")
    tracker = ConsentTracker()
    await tracker.grant_consent_async(user_id="api_user_1", consent_type="research_analytics", db=db_session)

    overview = await get_research_consent(include_revoked=True, db=db_session, current_user=user)
    assert overview.required_status["research_analytics"] is True
    assert overview.can_include_in_research is False
    assert overview.records[0].protocol_id == "research_analytics"

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/research/consent/revoke",
            "headers": [(b"x-forwarded-for", b"198.51.100.42")],
            "client": ("127.0.0.1", 12345),
        }
    )
    revoked = await revoke_research_consent(
        payload=ConsentRevokeRequest(protocol_id="research_analytics", reason="api revoke"),
        request=request,
        db=db_session,
        current_user=user,
    )

    assert revoked.granted is False
    assert revoked.reason == "api revoke"
    assert await tracker.has_consent_async("api_user_1", "research_analytics", db=db_session) is False


def test_research_consent_model_has_expected_table_name():
    assert ResearchConsentRecord.__tablename__ == "research_consent_records"
