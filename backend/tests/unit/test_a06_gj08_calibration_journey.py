"""A-06 v3 · GJ08 Calibration Receipt 旅程级验收（Correction → memory scope → next-session adaptation）。

卡面验收（headless 口径）：
1. **receipt 与真实 Context 一致**：经真实装配路径（``ResponseBuilderMixin``
   —— chat 回复回执的同一函数）产出的 receipt，其声称的每一条 memory ref
   必须真实存在于该用户的 Context 行（正测）；编造 ref（receipt 形状完好、
   id 不在该用户 Context）纠偏必败（负测，API 面 404）。
2. **四路纠偏反馈环**：not_relevant / wrong / change_scope / delete 从
   receipt 直接纠偏后在既有权威真源真实生效，且**下一轮召回/回执适配**
   （M 系召回真源 ``list_recent_episodic`` 排除态 + 重建回执不再错认）。
3. **按需展开（默认不打扰）**：回复未自然引用 → 无回执；全部高置信已确认
   → ambient 安静呈现（四动作仍在，不弱化纠偏面）；存在不确定引用 →
   surfaced（预算内）；被纠正降置信后 → 下一轮回执升格 surfaced——
   用户反馈可见地改变下一次呈现。
4. **零 CoT 泄露（硬红线负测）**：装配边界透传固定字段集，候选携带的
   reasoning 形态脏字段在传输编码（``json.dumps ensure_ascii=False``，与
   agent_grpc_service 同款）后的 receipt 载荷零出现。

诚实标注：本文件为旅程级验收锁。机制面（纯模块/服务委托）由
``test_a06_calibration_receipt.py`` / ``test_a06_receipt_respond.py`` /
``test_calibration_receipt.py`` 既有用例覆盖；base（d105aa57）上 journeys
的红绿结果如实记录于提交信息，不剪不饰。
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.api.v1.aurora_receipts import router as receipts_router
from app.models.memory import EpisodicMemory
from app.models.user import User
from app.orchestration.response_builder import ResponseBuilderMixin
from app.services.aurora_receipt_service import AuroraReceiptService
from app.services.memory_invalidation_pipeline import MemoryInvalidationPipeline
from app.services.memory_provenance_service import MemoryProvenanceNotFoundError
from app.services.memory_service import MemoryService
from tests.unit.test_a06_receipt_respond import (
    _OUTBOX_DDL,
    FakeRedis,
    _insert_episodic,
    _make_user,
)

# ---------------------------------------------------------------------------
# Hermetic 环境（与 test_a06_receipt_respond 同款口径：sqlite 内存 + FakeRedis）
# ---------------------------------------------------------------------------


@pytest.fixture(name="receipt_env")
async def gj08_receipt_env(db_session, monkeypatch):
    from unittest.mock import AsyncMock

    from app.config import settings

    monkeypatch.setattr(settings, "ENABLE_MEMORY_CORRECTION", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_RETRACTION", True, raising=False)
    monkeypatch.setattr("app.services.memory_service.SystemUpdateService.enqueue", AsyncMock())
    monkeypatch.setattr(
        "app.aurora.runtime_v1.self_model.SparkleSelfModelService.record_user_correction",
        AsyncMock(),
    )
    for ddl in _OUTBOX_DDL:
        await db_session.execute(text(ddl))
    await db_session.commit()
    fake = FakeRedis()
    monkeypatch.setattr(MemoryInvalidationPipeline, "_resolve_redis", lambda self: fake)
    yield fake


def _project_rows(rows: list[EpisodicMemory]) -> list[dict]:
    """把真实 DB 行投影成 context payload 的 episodic 候选（聚合器同款字段面）。

    只投影真实行字段——投影即「receipt 与真实 Context 一致」的锚点；测试里
    额外塞入的 reasoning 形态脏字段用于 CoT 边界负测（见独立用例）。
    """
    return [
        {
            "id": str(row.id),
            "summary": row.summary,
            "confidence": float(row.confidence or 0.0),
            "source_lane": row.source_lane,
            "source_type": row.source_type,
            "occurred_at": row.occurred_at.isoformat(),
        }
        for row in rows
    ]


def _build_receipt(rows: list[EpisodicMemory], *, reply: str, calibration_shown_today: int = 0):
    return ResponseBuilderMixin._build_memory_reference_receipt(
        full_response=reply,
        user_context_payload={"episodic_memories": _project_rows(rows)},
        context_data={},
        response_id="resp_gj08",
        calibration_shown_today=calibration_shown_today,
    )


async def _live_rows(db_session: AsyncSession, user: User) -> list[EpisodicMemory]:
    """下一轮召回的 M 系真源（与 context_builder 同一读取口径）。"""
    return await MemoryService(db_session, None).list_recent_episodic(user.id, limit=10)


# ---------------------------------------------------------------------------
# 1. receipt 与真实 Context 一致（正测 + 编造 ref 负测）
# ---------------------------------------------------------------------------


async def test_receipt_refs_resolve_to_real_user_context(db_session, receipt_env):
    """正测：经真实装配路径的 receipt，声称的 refs 全部真实存在于该用户 Context。"""
    user = await _make_user(db_session)
    row = await _insert_episodic(db_session, user, "用户偏好先看示例再动手写代码", confidence=0.9)

    receipt = _build_receipt(
        [row],
        reply="好的，你之前说过「用户偏好先看示例再动手写代码」，我们按这个来。",
    )

    assert receipt is not None
    user_row_ids = {
        str(memory_id)
        for (memory_id,) in (
            await db_session.execute(select(EpisodicMemory.id).where(EpisodicMemory.user_id == user.id))
        ).all()
    }
    claimed_ids = {str(ref["id"]) for ref in receipt["referenced_memories"]}
    assert claimed_ids, "receipt must claim at least one ref"
    assert claimed_ids <= user_row_ids, f"fabricated refs detected: {claimed_ids - user_row_ids}"
    # 回执与真实行的内容一致（不凭空改写）
    assert all("先看示例" in str(ref["content"]) for ref in receipt["referenced_memories"])


async def test_receipt_hidden_without_natural_reference(db_session, receipt_env):
    """按需展开·hidden：回复未自然引用记忆 → 无回执，绝不硬造。"""
    user = await _make_user(db_session)
    row = await _insert_episodic(db_session, user, "用户偏好先看示例再动手写代码", confidence=0.9)

    receipt = _build_receipt([row], reply="今天我们来学习操作系统的进程调度。")
    assert receipt is None, "reply that never references the memory must not produce a receipt"


async def test_receipt_default_quiet_when_all_confident(db_session, receipt_env):
    """按需展开·ambient：全部高置信已确认 → 安静呈现；四动作仍在（不弱化纠偏面）。"""
    user = await _make_user(db_session)
    row = await _insert_episodic(
        db_session, user, "用户偏好先看示例再动手写代码", confidence=0.9, lane="direct_capture"
    )

    receipt = _build_receipt([row], reply="按「用户偏好先看示例再动手写代码」来，先看示例。")
    assert receipt is not None
    assert receipt["surface"]["decision"] == "ambient"
    assert receipt["surface"]["presentation"] == "ambient"
    assert receipt["uncertainties"] == []
    for ref in receipt["referenced_memories"]:
        assert sorted(ref["actions"]) == ["change_scope", "delete", "not_relevant", "wrong"]


async def test_uncertain_reference_surfaces_calibration_within_budget(db_session, receipt_env):
    """按需展开·surfaced：不确定引用且预算内 → calibration 强调呈现。"""
    user = await _make_user(db_session)
    row = await _insert_episodic(
        db_session, user, "用户好像正在准备操作系统考试", confidence=0.55, lane="inferred_extraction"
    )

    receipt = _build_receipt([row], reply="用户好像正在准备操作系统考试，我们聚焦复习。")
    assert receipt is not None
    assert receipt["surface"]["decision"] == "surfaced"
    assert receipt["surface"]["presentation"] == "calibration"
    assert receipt["referenced_memories"][0]["uncertain"] is True
    assert any(u["kind"] == "unverified_inference" for u in receipt["uncertainties"])


# ---------------------------------------------------------------------------
# 2. GJ08 旅程链：从建议直接纠偏 → 真源生效 → 下一轮召回/回执适配
# ---------------------------------------------------------------------------


async def test_gj08_change_scope_adapts_next_session(db_session, receipt_env):
    user = await _make_user(db_session)
    row = await _insert_episodic(db_session, user, "用户偏好先看示例再动手写代码", confidence=0.9)
    reply = "按「用户偏好先看示例再动手写代码」来。"
    receipt = _build_receipt([row], reply=reply)
    assert receipt is not None and receipt["referenced_memories"][0]["id"] == str(row.id)

    result = await AuroraReceiptService(db_session, receipt_env).respond(
        user_id=user.id,
        memory_type="episodic",
        memory_id=row.id,
        action="change_scope",
        response_id="resp_gj08",
    )
    assert result["status"] == "ok" and result["paused"] is True

    # 下一轮：召回真源排除 + 重建回执不再声称该 ref
    rows = await _live_rows(db_session, user)
    assert str(row.id) not in {str(r.id) for r in rows}
    rebuilt = _build_receipt(rows, reply=reply)
    assert rebuilt is None, "paused memory must not be claimed by the next receipt"


async def test_gj08_delete_adapts_next_session(db_session, receipt_env):
    user = await _make_user(db_session)
    row = await _insert_episodic(db_session, user, "用户住在上海", confidence=0.9)
    reply = "你在上海，附近的自习室可以考虑。"
    receipt = _build_receipt([row], reply=reply)
    assert receipt is not None

    result = await AuroraReceiptService(db_session, receipt_env).respond(
        user_id=user.id,
        memory_type="episodic",
        memory_id=row.id,
        action="delete",
    )
    assert result["status"] == "ok" and result["revoked"] is True

    rows = await _live_rows(db_session, user)
    assert str(row.id) not in {str(r.id) for r in rows}
    assert _build_receipt(rows, reply=reply) is None


async def test_gj08_supersede_adapts_next_session(db_session, receipt_env):
    user = await _make_user(db_session)
    row = await _insert_episodic(db_session, user, "用户在准备期末考", confidence=0.9)
    receipt = _build_receipt([row], reply="用户在准备期末考，我们优先复习。")
    assert receipt is not None

    result = await AuroraReceiptService(db_session, receipt_env).respond(
        user_id=user.id,
        memory_type="episodic",
        memory_id=row.id,
        action="wrong",
        corrected_content="其实在准备考研复试",
        response_id="resp_gj08",
    )
    assert result["mode"] == "supersede"

    # 下一轮：旧内容不再被召回/认领；新内容可被引用
    rows = await _live_rows(db_session, user)
    summaries = " | ".join(r.summary for r in rows)
    assert "期末考" not in summaries and "考研复试" in summaries
    rebuilt = _build_receipt(rows, reply="用户在准备考研复试，我们优先复习。")
    assert rebuilt is not None
    blob = json.dumps(rebuilt, ensure_ascii=False)
    assert "期末考" not in blob, "superseded content must not be claimed by the next receipt"
    assert "考研复试" in blob
    assert all(ref["id"] != str(row.id) for ref in rebuilt["referenced_memories"])


@pytest.mark.parametrize("action", ["not_relevant", "wrong"])
async def test_gj08_denial_becomes_visible_calibration_next_session(db_session, receipt_env, action):
    """降噪类纠偏：记忆仍可召回但降置信 → 下一轮回执如实升格 uncertain/surfaced。

    0.65 - CONFIDENCE_DECREMENT(0.1) = 0.55 < UNCERTAIN_REFERENCE_CONFIDENCE(0.6)
    ——用户的「这条不对/无关」反馈在下一次呈现里可见（被纠正后能变）。
    """
    user = await _make_user(db_session)
    row = await _insert_episodic(db_session, user, "用户偏好先看示例再动手写代码", confidence=0.65)
    reply = "按「用户偏好先看示例再动手写代码」来。"
    before = _build_receipt([row], reply=reply)
    assert before is not None
    assert before["referenced_memories"][0]["uncertain"] is False
    assert before["surface"]["decision"] == "ambient"

    result = await AuroraReceiptService(db_session, receipt_env).respond(
        user_id=user.id,
        memory_type="episodic",
        memory_id=row.id,
        action=action,
    )
    assert result["status"] == "ok"

    await db_session.refresh(row)
    assert float(row.confidence or 0) == pytest.approx(0.55, abs=1e-6)

    rows = await _live_rows(db_session, user)
    rebuilt = _build_receipt(rows, reply=reply)
    assert rebuilt is not None
    assert rebuilt["referenced_memories"][0]["id"] == str(row.id)
    assert rebuilt["referenced_memories"][0]["uncertain"] is True
    assert rebuilt["surface"]["decision"] == "surfaced"


async def test_fabricated_ref_in_real_receipt_fails_all_actions(db_session, receipt_env):
    """负测：receipt 形状完好的编造 ref（id 不在该用户 Context）纠偏必败。

    真实 receipt 上只替换一条 ref 的 id 为随机 UUID——四动作一律
    ``MemoryProvenanceNotFoundError``（API 面 404，无存在性泄漏）；
    真实 ref 的纠偏不受影响。
    """
    user = await _make_user(db_session)
    row = await _insert_episodic(db_session, user, "用户偏好先看示例再动手写代码", confidence=0.9)
    receipt = _build_receipt([row], reply="按「用户偏好先看示例再动手写代码」来。")
    assert receipt is not None

    fabricated = dict(receipt["referenced_memories"][0])
    fabricated["id"] = str(uuid4())  # 编造：形状完好，但不在该用户 Context
    service = AuroraReceiptService(db_session, receipt_env)
    for action in ("not_relevant", "wrong", "change_scope", "delete"):
        with pytest.raises(MemoryProvenanceNotFoundError):
            await service.respond(
                user_id=user.id,
                memory_type="episodic",
                memory_id=UUID(fabricated["id"]),
                action=action,
            )

    # 真实 ref 仍可纠偏（回执其余部分不受编造 ref 污染）
    ok = await service.respond(
        user_id=user.id, memory_type="episodic", memory_id=row.id, action="not_relevant"
    )
    assert ok["status"] == "ok"


# ---------------------------------------------------------------------------
# 3. 零 CoT 泄露（硬红线负测）：装配边界 + 传输编码后的载荷
# ---------------------------------------------------------------------------


def test_receipt_transport_payload_contains_no_cot_boundary_leak():
    """候选携带 reasoning 形态脏字段 → 传输编码后的 receipt 零泄露。"""
    dirty_reasoning = "chain_of_thought: 先查 policy_why 再看 joint_why，R0. 分配不足所以选 S1.sufficient"
    dirty_item = {
        "id": "m_dirty",
        "summary": "用户偏好先看示例再动手写代码",
        "confidence": 0.9,
        "user_confirmed": True,
        "occurred_at": datetime.now(UTC).isoformat(),
        # 脏字段：决策环内部注释/推理流形态，结构上不允许进入 receipt
        "chain_of_thought": dirty_reasoning,
        "policy_why": "S1.sufficient",
        "joint_why": "R0.budget",
        "reasoning_trace": [{"step": 1, "thought": dirty_reasoning}],
        "internal_reason": "allocation_why:exhausted",
    }
    receipt = ResponseBuilderMixin._build_memory_reference_receipt(
        full_response="按「用户偏好先看示例再动手写代码」来。",
        user_context_payload={"episodic_memories": [dirty_item]},
        context_data={},
        response_id="resp_cot",
    )
    assert receipt is not None
    # 与 agent_grpc_service 相同的传输编码
    transported = json.dumps(receipt, ensure_ascii=False)
    for marker in (
        dirty_reasoning,
        "chain_of_thought",
        "policy_why",
        "joint_why",
        "reasoning_trace",
        "internal_reason",
        "allocation_why",
        "S1.sufficient",
        "R0.budget",
    ):
        assert marker not in transported, f"CoT/内部 reason 泄露进 receipt: {marker}"


def test_receipt_metadata_transport_roundtrip_keeps_actions_and_gate():
    """metadata JSON 往返（gRPC 传输面）后回执契约不变：四动作 + 呈现门 + refs。"""
    item = {
        "id": "m_roundtrip",
        "summary": "用户偏好先看示例再动手写代码",
        "confidence": 0.9,
        "user_confirmed": True,
        "occurred_at": datetime.now(UTC).isoformat(),
    }
    receipt = ResponseBuilderMixin._build_memory_reference_receipt(
        full_response="按「用户偏好先看示例再动手写代码」来。",
        user_context_payload={"episodic_memories": [item]},
        context_data={},
        response_id="resp_rt",
    )
    assert receipt is not None
    decoded = json.loads(json.dumps(receipt, ensure_ascii=False))
    assert decoded["schema_version"] == "aurora_calibration_receipt.v1"
    assert decoded["referenced_memories"][0]["id"] == "m_roundtrip"
    assert sorted(decoded["referenced_memories"][0]["actions"]) == [
        "change_scope",
        "delete",
        "not_relevant",
        "wrong",
    ]
    assert decoded["surface"]["decision"] == "ambient"


# ---------------------------------------------------------------------------
# 4. HTTP 入口面（GJ08「用户可从建议直接纠偏」的用户真实入口）
# ---------------------------------------------------------------------------


app = FastAPI()
app.include_router(receipts_router, prefix="/api/v1")


@pytest.fixture(name="client")
async def gj08_client_fixture(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)


def _auth_as(user: User):
    app.dependency_overrides[get_current_user] = lambda: user


async def test_http_respond_from_suggestion_receipt_takes_real_effect(db_session, receipt_env, client):
    user = await _make_user(db_session)
    row = await _insert_episodic(db_session, user, "用户偏好先看示例再动手写代码", confidence=0.9)
    _auth_as(user)

    response = await client.post(
        "/api/v1/aurora/receipts/respond",
        json={
            "memory_type": "episodic",
            "memory_id": str(row.id),
            "action": "not_relevant",
            "response_id": "resp_gj08",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ok"
    assert body["action"] == "not_relevant"
    assert body["authority"] == "memory.record_memory_reference_outcome(denied)"
    await db_session.refresh(row)
    assert float(row.confidence or 0) < 0.9


async def test_http_fabricated_ref_is_404_without_existence_leak(db_session, receipt_env, client):
    owner = await _make_user(db_session)
    attacker = await _make_user(db_session)
    row = await _insert_episodic(db_session, owner, "owner 的记忆", confidence=0.9)
    _auth_as(attacker)

    fabricated = await client.post(
        "/api/v1/aurora/receipts/respond",
        json={"memory_type": "episodic", "memory_id": str(uuid4()), "action": "delete"},
    )
    cross_user = await client.post(
        "/api/v1/aurora/receipts/respond",
        json={"memory_type": "episodic", "memory_id": str(row.id), "action": "delete"},
    )
    # 降噪路径（引用层）同样不放过越权 id
    cross_user_deny = await client.post(
        "/api/v1/aurora/receipts/respond",
        json={"memory_type": "episodic", "memory_id": str(row.id), "action": "not_relevant"},
    )
    assert fabricated.status_code == 404
    assert cross_user.status_code == 404
    assert cross_user_deny.status_code == 404
    # 无存在性泄漏：编造与越权同一 404 形态
    assert fabricated.json() == cross_user.json()
    refreshed = await db_session.get(EpisodicMemory, row.id)
    assert refreshed.revoked_at is None
    assert float(refreshed.confidence or 0) == pytest.approx(0.9, abs=1e-6), (
        "attacker must not be able to decay the owner's memory confidence"
    )


async def test_http_closed_vocabulary_rejections(db_session, receipt_env, client):
    user = await _make_user(db_session)
    row = await _insert_episodic(db_session, user, "正常记忆", confidence=0.9)
    _auth_as(user)

    bad_action = await client.post(
        "/api/v1/aurora/receipts/respond",
        json={"memory_type": "episodic", "memory_id": str(row.id), "action": "wipe_all"},
    )
    bad_kind = await client.post(
        "/api/v1/aurora/receipts/respond",
        json={"memory_type": "document", "memory_id": str(row.id), "action": "delete"},
    )
    bad_uuid = await client.post(
        "/api/v1/aurora/receipts/respond",
        json={"memory_type": "episodic", "memory_id": "not-a-uuid", "action": "delete"},
    )
    assert bad_action.status_code == 422
    assert bad_kind.status_code == 422
    assert bad_uuid.status_code == 422
    refreshed = await db_session.get(EpisodicMemory, row.id)
    assert refreshed.revoked_at is None


async def test_http_wrong_after_delete_conflicts_409(db_session, receipt_env, client):
    user = await _make_user(db_session)
    row = await _insert_episodic(db_session, user, "先删再改的记忆", confidence=0.9)
    _auth_as(user)
    deleted = await client.post(
        "/api/v1/aurora/receipts/respond",
        json={"memory_type": "episodic", "memory_id": str(row.id), "action": "delete"},
    )
    assert deleted.status_code == 200
    conflict = await client.post(
        "/api/v1/aurora/receipts/respond",
        json={
            "memory_type": "episodic",
            "memory_id": str(row.id),
            "action": "wrong",
            "corrected_content": "改写已删除记忆",
        },
    )
    assert conflict.status_code == 409


async def test_http_actions_vocabulary_self_described(db_session, receipt_env, client):
    user = await _make_user(db_session)
    _auth_as(user)
    response = await client.get("/api/v1/aurora/receipts/actions")
    assert response.status_code == 200
    body = response.json()
    assert sorted(body["actions"]) == ["change_scope", "delete", "not_relevant", "wrong"]
    assert sorted(body["memory_kinds"]) == ["episodic", "goal", "preference"]
    assert sorted(body["wrong_modes"]) == ["lower_confidence", "supersede"]
    assert body["schema_version"] == "aurora_calibration_receipt.v1"
