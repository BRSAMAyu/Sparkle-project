"""V4-I06 · 来源验证集成测（E4 双重校验，不可悬空）。

覆盖（卡验收 + B05 反例 E4）：
1. selected ref join 真实存储：episodic/preference/goal 内存行 resolved；
2. 删除后旧 receipt 读时验证 → unresolved/deleted（「删除后旧receipt更新」读侧）；
3. 跨用户/不存在 → unresolved/unknown（统一，不区分泄漏，I3）；
4. scheme 集合外/畸形 ref → unresolved/unknown（fabricated_ref_scheme 反例）；
5. 回执落库 fail-closed：契约违例不落库；latest 读取 → 读侧版本门；
6. 读面（live）：receipt + source_verification + resolved_selected_count；
   off/shadow 读面不暴露。

红线：验证结果 metadata-only——不构造 quote/时间（「来源不可定位时明确unknown；
不编时间/quote」）。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context_selection_receipt import (
    ContextSelectionReceipt,
    ReceiptBudget,
    ReceiptCandidate,
    ReceiptInputVersions,
    ReceiptWhyNow,
    new_receipt_id,
)
from app.models.memory import EpisodicMemory, MemoryPreference
from app.models.user import User
from app.services.context_selection_receipt_service import (
    SOURCE_RESOLUTION_RESOLVED,
    SOURCE_RESOLUTION_UNRESOLVED,
    latest_receipt,
    record_receipt,
    verify_receipt_sources,
    verify_source_ref,
)
from app.services.memory_service import MemoryService


def _utcnow():
    return datetime.now(UTC).replace(tzinfo=None)


async def _create_user(db_session: AsyncSession, *, email_suffix: str = "") -> UUID:
    user_id = uuid4()
    db_session.add(
        User(
            id=user_id,
            username=f"user_{user_id.hex[:8]}",
            email=f"{user_id.hex[:8]}{email_suffix}@example.com",
            hashed_password="test",
        )
    )
    await db_session.commit()
    return user_id


def _receipt_for(refs: list[str], *, why_now: ReceiptWhyNow | None = None) -> ContextSelectionReceipt:
    return ContextSelectionReceipt(
        receipt_id=new_receipt_id(),
        selection_role="chat_context",
        input_versions=ReceiptInputVersions(memory_epoch=1, selector_version="context_pack.v4-i06.v1"),
        candidates=[ReceiptCandidate(ref=ref, status="selected", reason_code=None) for ref in refs],
        budget=ReceiptBudget(candidate_scan_limit=len(refs), selected_max=len(refs), clarifications_used=0),
        why_now=why_now,
    )


async def _seed_sources(db_session: AsyncSession, user_id: UUID) -> dict[str, str]:
    """真实存储行 → refs。"""
    memory_service = MemoryService(db_session)
    now = _utcnow()
    episodic = await memory_service.create_episodic_memory(
        user_id=user_id,
        summary="Episodic source row",
        source_type="analysis",
        source_id="src_v",
        occurred_at=now - timedelta(hours=1),
        importance_score=0.5,
        tags=["execution"],
        evidence_refs=[{"type": "event", "id": "evt"}],
    )
    pref = MemoryPreference(
        user_id=user_id,
        pref_key="depth_preference",
        pref_value={"value": "deep"},
        version=1,
        evidence_refs=[{"type": "event", "id": "evt"}],
    )
    db_session.add(pref)
    await db_session.commit()
    return {
        "episodic": f"memory://episodic/{episodic.id}",
        "preference": "memory://preference/depth_preference",
    }


@pytest.mark.asyncio
async def test_selected_refs_join_real_storage(db_session):
    """E4 双重校验绿色路径：selected ref 逐条 join 到真实行 → resolved。"""
    user_id = await _create_user(db_session)
    refs = await _seed_sources(db_session, user_id)
    receipt = _receipt_for([refs["episodic"], refs["preference"]])
    verification = await verify_receipt_sources(db_session, user_id, receipt)
    by_ref = {entry["ref"]: entry for entry in verification}
    assert by_ref[refs["episodic"]]["resolution"] == SOURCE_RESOLUTION_RESOLVED
    assert by_ref[refs["preference"]]["resolution"] == SOURCE_RESOLUTION_RESOLVED
    # metadata-only：验证结果不携带任何正文
    for entry in verification:
        blob = repr(entry)
        assert "Episodic source row" not in blob
        assert "deep" not in blob


@pytest.mark.asyncio
async def test_deleted_source_reads_unresolved_after_delete(db_session):
    """卡验收「删除后旧receipt更新」：回执行不改写；删除来源后，读时验证如实
    unresolved/deleted——用户看到的 scope 与后台一致。"""
    user_id = await _create_user(db_session)
    refs = await _seed_sources(db_session, user_id)
    receipt = _receipt_for([refs["episodic"]])
    assert (await verify_receipt_sources(db_session, user_id, receipt))[0]["resolution"] == SOURCE_RESOLUTION_RESOLVED

    row = (await db_session.execute(select(EpisodicMemory).where(EpisodicMemory.user_id == user_id))).scalar_one()
    row.deleted_at = _utcnow().replace(tzinfo=None)
    await db_session.commit()

    entry = (await verify_receipt_sources(db_session, user_id, receipt))[0]
    assert entry["resolution"] == SOURCE_RESOLUTION_UNRESOLVED
    assert entry["status_code"] == "deleted"


@pytest.mark.asyncio
async def test_cross_user_and_missing_refs_are_unknown(db_session):
    """I3：他人对象与不存在对象统一 unknown，不区分泄漏、不 500。"""
    owner = await _create_user(db_session, email_suffix=".owner")
    other = await _create_user(db_session, email_suffix=".other")
    refs = await _seed_sources(db_session, owner)
    cross_ref = refs["episodic"]  # other 验证 owner 的 ref
    receipt_other_view = await verify_source_ref(db_session, other, cross_ref)
    assert receipt_other_view["resolution"] == SOURCE_RESOLUTION_UNRESOLVED
    assert receipt_other_view["status_code"] == "unknown"

    missing = await verify_source_ref(db_session, owner, f"memory://episodic/{uuid4()}")
    assert missing["resolution"] == SOURCE_RESOLUTION_UNRESOLVED
    assert missing["status_code"] == "unknown"


@pytest.mark.asyncio
async def test_fabricated_or_malformed_refs_are_unknown(db_session):
    """B05 反例 fabricated_ref_scheme 的验证面：scheme 集合外/畸形 → unknown。"""
    user_id = await _create_user(db_session)
    for bad_ref in ("astro://invented-id", "no-scheme-shape", "memory://unknownkind/xyz", "plan://not-a-uuid"):
        entry = await verify_source_ref(db_session, user_id, bad_ref)
        assert entry["resolution"] == SOURCE_RESOLUTION_UNRESOLVED, bad_ref
        assert entry["status_code"] == "unknown"


@pytest.mark.asyncio
async def test_why_now_basis_refs_are_verified(db_session):
    """why_now.basis_refs（必须 ⊆ selected，契约 C1 投影）与 selected 同进验证面。"""
    user_id = await _create_user(db_session)
    refs = await _seed_sources(db_session, user_id)
    receipt = _receipt_for(
        [refs["episodic"], refs["preference"]],
        why_now=ReceiptWhyNow(
            statement="距检查点还剩2天",
            basis_refs=[refs["episodic"], refs["preference"]],
            expires_at=None,
            confidence_band="medium",
        ),
    )
    assert receipt.validate_contract() == []
    # 契约面：basis_ref 不在 selected 集 = 违约（伪依据防线）
    stray = _receipt_for(
        [refs["episodic"]],
        why_now=ReceiptWhyNow(statement="s", basis_refs=[refs["preference"]], confidence_band="low"),
    )
    assert any("not among selected" in v for v in stray.validate_contract())
    verified_refs = {entry["ref"] for entry in await verify_receipt_sources(db_session, user_id, receipt)}
    assert refs["preference"] in verified_refs  # basis_refs 逐条被验证


@pytest.mark.asyncio
async def test_record_fail_closed_on_contract_violation(db_session):
    """落库 fail-closed：契约违例回执不落库（第二真值污染防线）。"""
    user_id = await _create_user(db_session)
    bad = ContextSelectionReceipt(
        receipt_id=new_receipt_id(),
        selection_role="chat_context",
        input_versions=ReceiptInputVersions(memory_epoch=1, selector_version="context_pack.v4-i06.v1"),
        candidates=[
            ReceiptCandidate(ref="astro://invented", status="selected", reason_code=None),  # C1 违例
        ],
        budget=ReceiptBudget(candidate_scan_limit=1, selected_max=1, clarifications_used=0),
    )
    assert bad.validate_contract()
    persisted = await record_receipt(db_session, user_id=user_id, receipt=bad)
    assert persisted is None
    receipt, meta = await latest_receipt(db_session, user_id)
    assert receipt is None and meta is None


@pytest.mark.asyncio
async def test_latest_receipt_roundtrip(db_session):
    user_id = await _create_user(db_session)
    refs = await _seed_sources(db_session, user_id)
    receipt = _receipt_for([refs["episodic"]])
    persisted = await record_receipt(db_session, user_id=user_id, receipt=receipt)
    assert persisted == receipt.receipt_id

    loaded, meta = await latest_receipt(db_session, user_id)
    assert loaded is not None
    assert loaded.receipt_id == receipt.receipt_id
    assert loaded.selected_refs == [refs["episodic"]]
    assert meta is not None and "violations" in meta
    assert loaded.validate_contract() == []


@pytest.mark.asyncio
async def test_read_face_mode_gate(db_session, monkeypatch):
    """B05 §8：shadow 写先行、默认读关闭——off/shadow 读面不暴露；live 全量。"""
    from app.api.v1.experience_readouts import get_latest_context_receipt
    from app.config import settings
    from app.models.user import User as UserModel

    user_id = await _create_user(db_session)
    refs = await _seed_sources(db_session, user_id)
    receipt = _receipt_for([refs["episodic"]])
    await record_receipt(db_session, user_id=user_id, receipt=receipt)
    user = (await db_session.execute(select(UserModel).where(UserModel.id == user_id))).scalar_one()

    monkeypatch.setattr(settings, "CONTEXT_SELECTION_RECEIPT_MODE", "shadow", raising=False)
    payload = await get_latest_context_receipt(current_user=user, db=db_session)
    assert payload["receipt"] is None and payload["mode"] == "shadow"

    monkeypatch.setattr(settings, "CONTEXT_SELECTION_RECEIPT_MODE", "off", raising=False)
    payload = await get_latest_context_receipt(current_user=user, db=db_session)
    assert payload["receipt"] is None and payload["mode"] == "off"

    monkeypatch.setattr(settings, "CONTEXT_SELECTION_RECEIPT_MODE", "live", raising=False)
    payload = await get_latest_context_receipt(current_user=user, db=db_session)
    assert payload["receipt"] is not None
    assert payload["receipt"]["receipt_id"] == receipt.receipt_id
    assert payload["resolved_selected_count"] == 1
    assert payload["source_verification"][0]["resolution"] == SOURCE_RESOLUTION_RESOLVED
    # 不编时间/quote：读面 payload 无 quote/正文构造字段
    assert "quote" not in payload["source_verification"][0]
