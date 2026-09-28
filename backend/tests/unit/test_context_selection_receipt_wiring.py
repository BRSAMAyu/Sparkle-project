"""V4-I06 · 回执装配纯函数 + ContextPackBuilder.build 接线测试。

覆盖（卡要点）：
1. 装配归因判定序：prefilter 拒用 / surfaced / M-05 selfcheck / 冲突 suppressed /
   deny-quiet / budget 兜底（unattributed 缺口不悬空）；
2. I02 接口点：效用门 metadata 开 → utility_gate_rejected 覆盖 + 门选 中转
   selected；门关（metadata 缺席）→ 回执照常产生、原因码=prefilter 既有语义；
3. build 接线：mode=shadow → pack.context_selection_receipt 在场且契约合法 +
   落库（幂等）；mode=off → None（V3 路径零变化）；
4. 红线：回执不进 prompt 面（to_prompt_context 不含 note/候选明细）。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.context_budget import ContextBudgetScheduler
from app.core.context_pack import ContextPackBuilder
from app.core.context_selection_receipt import (
    CONTEXT_SELECTION_RECEIPT_SCHEMA_VERSION,
    REJECTION_REASON_CODES,
)
from app.models.context_selection_receipt import ContextSelectionReceiptRow
from app.models.memory import EpisodicMemory
from app.models.user import User
from app.orchestration.context_receipt_assembly import assemble_pack_receipt
from app.services.context_selection_receipt_service import record_receipt
from app.services.memory_retrieval_prefilter import (
    PrefilterResult,
    Rejection,
)
from app.services.memory_service import MemoryService


def _utcnow():
    return datetime.now(UTC).replace(tzinfo=None)


async def _create_user(db_session: AsyncSession) -> UUID:
    user_id = uuid4()
    db_session.add(
        User(
            id=user_id,
            username=f"user_{user_id.hex[:8]}",
            email=f"{user_id.hex[:8]}@example.com",
            hashed_password="test",
        )
    )
    await db_session.commit()
    return user_id


class _Record:
    """duck-typed episodic 记录（scope_of_record 经 M-01 投影读取列）。"""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


# ---------------------------------------------------------------------------
# 1. 装配纯函数：归因判定序
# ---------------------------------------------------------------------------


def test_assemble_prefilter_rejection_mapping():
    result = PrefilterResult(
        allowed=[],
        rejections=[Rejection(record_id="m1", dimension="ttl", reason="ttl:expired", detail="")],
        input_count=1,
        dimension_counts={"ttl": 1},
        reason_counts={"ttl:expired": 1},
    )
    receipt = assemble_pack_receipt(
        user_id=uuid4(),
        prefilter_results={"episodic": result},
        input_records={"episodic": [_Record(id="m1")]},
        surfaced_episodic_ids=[],
    )
    assert receipt.schema_version == CONTEXT_SELECTION_RECEIPT_SCHEMA_VERSION
    assert receipt.selection_role == "chat_context"
    assert receipt.receipt_id.startswith("csr_")
    assert len(receipt.candidates) == 1
    assert receipt.candidates[0].ref == "memory://episodic/m1"
    assert receipt.candidates[0].status == "rejected"
    assert receipt.candidates[0].reason_code == "expired"
    assert receipt.budget.candidate_scan_limit == 1
    assert receipt.budget.selected_max == 0
    assert receipt.input_versions.selector_version  # 必选版本位
    assert receipt.input_versions.goal_version is None  # 未读权威 → null 不冒充
    assert receipt.why_now is None
    assert receipt.validate_contract() == []


def test_assemble_attribution_precedence_surfaced_selfcheck_conflict_deny_budget():
    records = [_Record(id=f"m{i}", pref_key=None) for i in range(6)]
    allowed_result = PrefilterResult(
        allowed=list(records), rejections=[], input_count=6, dimension_counts={}, reason_counts={}
    )
    receipt = assemble_pack_receipt(
        user_id=uuid4(),
        prefilter_results={"episodic": allowed_result},
        input_records={"episodic": records},
        surfaced_episodic_ids=["m0"],  # selected
        ranked_episodic_ids=["m0", "m1", "m2", "m3", "m4"],
        selfcheck_internal=[{"id": "m1", "section": "episodic", "reason": "selfcheck:duplicate_in_pack"}],
        conflicts=[
            {"type": "episodic", "key": "k", "reason": "near_duplicate", "winners": ["m0"], "suppressed": ["m2"]}
        ],
    )
    by_ref = {c.ref: c for c in receipt.candidates}
    assert by_ref["memory://episodic/m0"].status == "selected"
    assert by_ref["memory://episodic/m0"].reason_code is None
    assert by_ref["memory://episodic/m1"].reason_code == "duplicate"
    assert by_ref["memory://episodic/m2"].reason_code == "conflicts_confirmed_preference"
    # m3/m4：在 ranked 面但被预算裁掉 → budget_exhausted（排名/预算截断面）
    assert by_ref["memory://episodic/m3"].reason_code == "budget_exhausted"
    assert by_ref["memory://episodic/m4"].reason_code == "budget_exhausted"
    # m5：过预筛但未进 ranked/surfaced 且无 attributable 面 → budget 兜底 + 缺口标记
    assert by_ref["memory://episodic/m5"].reason_code == "budget_exhausted"
    assert by_ref["memory://episodic/m5"].note == "unattributed_downstream"
    assert receipt.validate_contract() == []


def test_assemble_deny_quiet_maps_permission_denied():
    records = [_Record(id="p1", pref_key="depth_preference")]
    result = PrefilterResult(allowed=list(records), rejections=[], input_count=1, dimension_counts={}, reason_counts={})
    receipt = assemble_pack_receipt(
        user_id=uuid4(),
        prefilter_results={"preferences": result},
        input_records={"preferences": records},
        surfaced_pref_keys=[],
        ranked_pref_keys=["depth_preference"],
        deny_quieted_keys=["depth_preference"],
    )
    assert receipt.candidates[0].ref == "memory://preference/depth_preference"
    assert receipt.candidates[0].reason_code == "permission_denied"
    assert receipt.validate_contract() == []


# ---------------------------------------------------------------------------
# 2. I02 接口点：效用门开/关
# ---------------------------------------------------------------------------


def test_gate_on_metadata_overrides_candidates():
    records = [_Record(id="m1"), _Record(id="m2")]
    result = PrefilterResult(allowed=list(records), rejections=[], input_count=2, dimension_counts={}, reason_counts={})
    gate_payload = {
        "version": "memory-v4.i02.v1",
        "decisions": [
            {"item_id": "m1", "selected": False, "score": -1.0, "reasons": ["outcome:unresolved_episode"]},
            {"item_id": "m2", "selected": True, "score": 1.3, "reasons": ["outcome:resolved_episode"]},
        ],
        "required_memory_detected": False,
        "passed": True,
    }
    receipt = assemble_pack_receipt(
        user_id=uuid4(),
        prefilter_results={"episodic": result},
        input_records={"episodic": records},
        surfaced_episodic_ids=["m1"],  # 预筛后 surfaced，但效用门拒用
        gate_payload=gate_payload,
    )
    by_ref = {c.ref: c for c in receipt.candidates}
    # 门拒覆盖 surfaced → utility_gate_rejected + 门 reasons 进 note（debug-only）
    assert by_ref["memory://episodic/m1"].status == "rejected"
    assert by_ref["memory://episodic/m1"].reason_code == "utility_gate_rejected"
    assert (
        by_ref["memory://episodic/m1"].note is not None
        and "outcome:unresolved_episode" in by_ref["memory://episodic/m1"].note
    )
    # 门选中 → selected
    assert by_ref["memory://episodic/m2"].status == "selected"
    assert by_ref["memory://episodic/m2"].reason_code is None
    assert receipt.validate_contract() == []


def test_gate_off_receipt_still_produced_with_prefilter_semantics():
    """卡要点 3：门关（metadata 缺席/形状不符）→ 回执照常产生，原因码=prefilter 面。"""
    records = [_Record(id="m1")]
    result = PrefilterResult(
        allowed=[],
        rejections=[Rejection(record_id="m1", dimension="scope", reason="scope:mismatch", detail="")],
        input_count=1,
        dimension_counts={"scope": 1},
        reason_counts={"scope:mismatch": 1},
    )
    for gate in (None, {}, {"decisions": "not-a-list"}):
        receipt = assemble_pack_receipt(
            user_id=uuid4(),
            prefilter_results={"episodic": result},
            input_records={"episodic": records},
            gate_payload=gate,
        )
        assert receipt.candidates[0].reason_code == "out_of_scope_memory"
        assert receipt.validate_contract() == []


def test_gate_never_creates_dangling_ref_for_unknown_id():
    """门只裁决 M-03 allowed 面；未知 id 不构造悬空候选（I3）。"""
    records = [_Record(id="m1")]
    result = PrefilterResult(allowed=list(records), rejections=[], input_count=1, dimension_counts={}, reason_counts={})
    gate_payload = {"decisions": [{"item_id": "ghost", "selected": True, "score": 1.0, "reasons": []}]}
    receipt = assemble_pack_receipt(
        user_id=uuid4(),
        prefilter_results={"episodic": result},
        input_records={"episodic": records},
        gate_payload=gate_payload,
    )
    assert [c.ref for c in receipt.candidates] == ["memory://episodic/m1"]


# ---------------------------------------------------------------------------
# 3. build 接线（sqlite）
# ---------------------------------------------------------------------------


async def _seed_memory_user(db_session: AsyncSession) -> UUID:
    user_id = await _create_user(db_session)
    memory_service = MemoryService(db_session)
    await memory_service.upsert_preference(
        user_id=user_id,
        pref_key="depth_preference",
        pref_value={"value": "x" * 60},
        evidence_refs=[{"type": "event", "id": "evt_1"}],
    )
    now = _utcnow()
    await memory_service.create_episodic_memory(
        user_id=user_id,
        summary="Memory surfaced " + ("z" * 60),
        source_type="analysis",
        source_id="src_1",
        occurred_at=now - timedelta(hours=1),
        importance_score=0.6,
        tags=["execution"],
        evidence_refs=[{"type": "event", "id": "evt_2"}],
    )
    await memory_service.create_episodic_memory(
        user_id=user_id,
        summary="Memory trimmed by budget " + ("y" * 400),
        source_type="analysis",
        source_id="src_2",
        occurred_at=now - timedelta(hours=2),
        importance_score=0.5,
        tags=["execution"],
        evidence_refs=[{"type": "event", "id": "evt_3"}],
    )
    return user_id


@pytest.mark.asyncio
async def test_build_produces_and_persists_receipt_in_shadow_mode(db_session, monkeypatch):
    monkeypatch.setattr(settings, "CONTEXT_SELECTION_RECEIPT_MODE", "shadow", raising=False)
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_RANKING", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_CONFLICT_RESOLUTION", False, raising=False)
    user_id = await _seed_memory_user(db_session)

    scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 40, "goals": 40, "episodic": 60}})
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(user_id, intent="chat")

    assert pack.context_selection_receipt is not None
    receipt = pack.context_selection_receipt
    assert receipt.validate_contract() == []
    assert receipt.selection_role == "chat_context"
    statuses = {c.status for c in receipt.candidates}
    assert "selected" in statuses  # 记忆面有合法候选进面
    # 落库：shadow 写先行
    rows = (
        (
            await db_session.execute(
                select(ContextSelectionReceiptRow).where(ContextSelectionReceiptRow.user_id == user_id)
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].receipt_id == receipt.receipt_id
    # 幂等：同 receipt_id 重放不重复计数
    persisted = await record_receipt(db_session, user_id=user_id, receipt=receipt)
    assert persisted == receipt.receipt_id
    rows = (
        (
            await db_session.execute(
                select(ContextSelectionReceiptRow).where(ContextSelectionReceiptRow.user_id == user_id)
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_build_mode_off_produces_no_receipt(db_session, monkeypatch):
    monkeypatch.setattr(settings, "CONTEXT_SELECTION_RECEIPT_MODE", "off", raising=False)
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_RANKING", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_CONFLICT_RESOLUTION", False, raising=False)
    user_id = await _seed_memory_user(db_session)

    scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 200, "goals": 200, "episodic": 200}})
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(user_id, intent="chat")

    assert pack.context_selection_receipt is None
    rows = (
        (
            await db_session.execute(
                select(ContextSelectionReceiptRow).where(ContextSelectionReceiptRow.user_id == user_id)
            )
        )
        .scalars()
        .all()
    )
    assert rows == []


@pytest.mark.asyncio
async def test_receipt_never_leaks_into_prompt_face(db_session, monkeypatch):
    """红线：note 是 debug-only——to_prompt_context 输出不含回执候选明细/note。"""
    monkeypatch.setattr(settings, "CONTEXT_SELECTION_RECEIPT_MODE", "live", raising=False)
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_RANKING", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_CONFLICT_RESOLUTION", False, raising=False)
    user_id = await _seed_memory_user(db_session)

    scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 40, "goals": 40, "episodic": 60}})
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(user_id, intent="chat")
    assert pack.context_selection_receipt is not None

    prompt = pack.to_prompt_context()
    blob = repr(prompt)
    for candidate in pack.context_selection_receipt.candidates:
        assert candidate.ref not in blob  # 候选 ref 面不进 prompt
        assert not (candidate.note and candidate.note in blob)  # note 不进 prompt


@pytest.mark.asyncio
async def test_prefiltered_row_is_rejected_in_build_receipt(db_session, monkeypatch):
    """集成：SQL 拉取面放行、M-03 硬砍的候选（到期未解决的 due_at+7d 承诺）
    进回执 rejected/expired；活性记忆照常 selected（候选集=被扫描全集）。"""
    monkeypatch.setattr(settings, "CONTEXT_SELECTION_RECEIPT_MODE", "shadow", raising=False)
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_RANKING", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_CONFLICT_RESOLUTION", False, raising=False)
    user_id = await _seed_memory_user(db_session)
    # 到期承诺（due_at+7d 硬 TTL 已过、未解决）：list_recent_episodic 的 SQL 不
    # 过滤该形态，M-03 预筛 ttl/status 维度拒用（M-03 集成测试同款构造）。
    expired_row = EpisodicMemory(
        user_id=user_id,
        summary="Expired commitment should be cut by prefilter",
        source_type="analysis",
        source_id="src_expired",
        occurred_at=_utcnow() - timedelta(days=30),
        due_at=_utcnow() - timedelta(days=20),
        resolved_at=None,
        decay_policy="due_at+7d",
        importance_score=0.9,
        tags=["execution"],
    )
    db_session.add(expired_row)
    await db_session.commit()

    scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 200, "goals": 200, "episodic": 400}})
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(user_id, intent="chat")
    receipt = pack.context_selection_receipt
    assert receipt is not None
    by_ref = {c.ref: c for c in receipt.candidates}
    expired_ref = f"memory://episodic/{expired_row.id}"
    # 该行候选在册（被扫描面全覆盖）且被 M-03 拒用（ttl/status 过期家族）
    assert expired_ref in by_ref
    assert by_ref[expired_ref].status == "rejected"
    assert by_ref[expired_ref].reason_code == "expired"
    assert by_ref[expired_ref].reason_code in REJECTION_REASON_CODES
    assert any(c.status == "selected" for c in receipt.candidates)  # 活性记忆照常进面
    assert receipt.validate_contract() == []
