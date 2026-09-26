from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.config import settings
from app.models.memory import EpisodicMemory
from app.routing.aggregator_backed_social_context_provider import (
    AggregatorBackedSocialContextProvider,
    build_social_context_provider,
)
from app.routing.router_context_reader import RouterContextReader


def _scenario_payload(now: datetime, index: int) -> list[EpisodicMemory]:
    user_id = uuid4()
    records: list[EpisodicMemory] = []
    mention_count = (index % 3) + 1
    relationship_count = index % 4
    overdue_commitments = index % 2

    for offset in range(mention_count):
        records.append(
            EpisodicMemory(
                user_id=user_id,
                summary=f"你提到过一位学习相关人物 {index}-{offset}",
                source_type="chat",
                source_id=f"session_{index}",
                source_lane="inferred_extraction",
                subject_type="person_mention",
                occurred_at=now - timedelta(days=offset + 1),
                evidence_refs=[{"type": "chat_turn", "id": f"turn_m_{index}_{offset}"}],
            )
        )
    for offset in range(relationship_count):
        records.append(
            EpisodicMemory(
                user_id=user_id,
                summary=f"你提到过一段与他人的关系动态 {index}-{offset}",
                source_type="chat",
                source_id=f"session_{index}",
                source_lane="inferred_extraction",
                subject_type="relationship",
                occurred_at=now - timedelta(days=offset + 1),
                evidence_refs=[{"type": "chat_turn", "id": f"turn_r_{index}_{offset}"}],
            )
        )
    for offset in range(overdue_commitments):
        records.append(
            EpisodicMemory(
                user_id=user_id,
                summary=f"overdue commitment {index}-{offset}",
                source_type="chat",
                source_id=f"session_{index}",
                source_lane="inferred_extraction",
                subject_type="commitment",
                occurred_at=now - timedelta(days=offset + 2),
                due_at=now - timedelta(hours=offset + 2),
                evidence_refs=[{"type": "chat_turn", "id": f"turn_c_{index}_{offset}"}],
            )
        )
    return records


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario_index", list(range(20)))
async def test_aggregator_backed_social_context_provider_matches_direct_reader(
    db_session,
    scenario_index: int,
) -> None:
    now = datetime.utcnow()
    records = _scenario_payload(now, scenario_index)
    user_id = records[0].user_id
    db_session.add_all(records)
    await db_session.commit()

    direct = await RouterContextReader(db_session).fetch_social_snapshot(user_id)
    aggregated = await AggregatorBackedSocialContextProvider(db_session).fetch_social_snapshot(user_id)

    assert [item.summary for item in aggregated.recent_person_mentions] == [
        item.summary for item in direct.recent_person_mentions
    ]
    assert aggregated.pending_commitments_count == direct.pending_commitments_count
    assert aggregated.relationship_count == direct.relationship_count


# ---------------------------------------------------------------------------
# V3-FIX-186：provider 选型必须走 stage18 三态门统一判据
#
# build_social_context_provider 曾直读 legacy bool SPARKLE_AGGREGATOR_ENABLED，
# 不读 AURORA_STAGE18_AGGREGATOR_MODE——tri-state off 时仍选中
# AggregatorBackedSocialContextProvider（治理面与行为面双权威分叉）。
# 修法 = 选型判据改走 kill_switch.resolve_settings_mode（V3-FIX-21 唯一判据）。
# ---------------------------------------------------------------------------
_TRI_STATE_ALL_ON = [
    pytest.param("off", RouterContextReader, id="stage18_off_deselects_aggregator_even_with_legacy_bool_true"),
    pytest.param("shadow", AggregatorBackedSocialContextProvider, id="stage18_shadow_keeps_selection"),
    pytest.param("live", AggregatorBackedSocialContextProvider, id="stage18_live_keeps_selection"),
]


@pytest.mark.parametrize(("mode", "expected"), _TRI_STATE_ALL_ON)
def test_build_social_context_provider_follows_stage18_tri_state(
    db_session,
    monkeypatch,
    mode: str,
    expected: type,
) -> None:
    """tri-state 设置在场即为唯一判据：off 时 legacy bool 默认 True 不得劫持选型。"""
    monkeypatch.setattr(settings, "AURORA_STAGE18_AGGREGATOR_MODE", mode, raising=False)
    monkeypatch.setattr(settings, "SPARKLE_AGGREGATOR_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "SPARKLE_ROUTER_USE_AGGREGATOR_PROVIDER", True, raising=False)

    provider = build_social_context_provider(db_session)

    assert isinstance(provider, expected)


def test_build_social_context_provider_tri_state_cannot_be_hijacked_down_by_legacy_bool(
    db_session,
    monkeypatch,
) -> None:
    """对偶面：tri-state live 时 legacy bool False 不得把选型压回 reader。"""
    monkeypatch.setattr(settings, "AURORA_STAGE18_AGGREGATOR_MODE", "live", raising=False)
    monkeypatch.setattr(settings, "SPARKLE_AGGREGATOR_ENABLED", False, raising=False)
    monkeypatch.setattr(settings, "SPARKLE_ROUTER_USE_AGGREGATOR_PROVIDER", True, raising=False)

    assert isinstance(build_social_context_provider(db_session), AggregatorBackedSocialContextProvider)


def test_build_social_context_provider_legacy_bool_backfills_when_tri_state_absent(
    db_session,
    monkeypatch,
) -> None:
    """未声明 tri-state 设置时 legacy bool 仍按 V3-FIX-21 语义兜底。"""
    monkeypatch.delattr(settings, "AURORA_STAGE18_AGGREGATOR_MODE", raising=False)
    monkeypatch.setattr(settings, "SPARKLE_ROUTER_USE_AGGREGATOR_PROVIDER", True, raising=False)

    monkeypatch.setattr(settings, "SPARKLE_AGGREGATOR_ENABLED", True, raising=False)
    assert isinstance(build_social_context_provider(db_session), AggregatorBackedSocialContextProvider)

    monkeypatch.setattr(settings, "SPARKLE_AGGREGATOR_ENABLED", False, raising=False)
    assert isinstance(build_social_context_provider(db_session), RouterContextReader)


def test_build_social_context_provider_router_flag_still_gates_selection(
    db_session,
    monkeypatch,
) -> None:
    """路由级 opt-out（SPARKLE_ROUTER_USE_AGGREGATOR_PROVIDER=False）语义保留。"""
    monkeypatch.setattr(settings, "AURORA_STAGE18_AGGREGATOR_MODE", "live", raising=False)
    monkeypatch.setattr(settings, "SPARKLE_AGGREGATOR_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "SPARKLE_ROUTER_USE_AGGREGATOR_PROVIDER", False, raising=False)

    assert isinstance(build_social_context_provider(db_session), RouterContextReader)
