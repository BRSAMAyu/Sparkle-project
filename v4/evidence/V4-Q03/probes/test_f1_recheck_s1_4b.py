"""V4-Q03 · 一审 F1 整改复验探针（S1 场景④b 重跑；验收剧本证据面，不入生产测试树）.

终门条件（review_r1.md 条件 1）：F1 在 U10 责任面修复后复验 S1④b——
example 起点（默认 ScaffoldState）经 check/enter API 可达独立检验段，
``defect_F1_enter_stuck_from_example`` 检查项翻绿。

本探针复用验收剧本同一场景设定（``test_q03_acceptance._make_mastery_task``：
真实 ErrorRecord review_count=2 证据 + 服务端 guide_json 判分权威）与真实
REST 面，断言**修复后**行为并逐条记录到 ``../r1_fix_recheck/recheck_records``.
jsonl（独立整改记录文件，**不追加**验收原始 raw_records/）。验收剧本原文与
一审 receipt 不改动。

覆盖面（与 S1④b 同构 + 整改边界）：
1. 两跳全链：example 起点 → enter#1 合法中间推进（attempt，落库，不出题、
   无误报 HOLD）→ enter#2 放行出题（independent_check）→ DB 权威位写回断言；
2. 判分门不放宽：中间推进后提交仍 HOLD.scaffold_not_at_check；到段后精确
   答案判对、响应零答案材料（I07 红线不动）；
3. 反例保持：example + 无证据 → 仍 HOLD.evidence_not_supported、不推进；
4. 单跳回归护栏：attempt 起点（带外写）单跳 enter 即 check_available=True
   （整改不得破坏既有行为）。
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user
from app.api.v1.learning_journey import router as learning_journey_router
from app.core.hybrid_policy import (
    apply_scaffold_decision,
    next_scaffold_step,
    parse_policy_block,
)
from app.db.session import get_db
from test_q03_acceptance import (  # 验收剧本同一场景设定（不复制、不漂移）
    _CHECK_ANSWER,
    _CHECK_QUESTION,
    _make_mastery_task,
    _make_user,
)

pytestmark = pytest.mark.asyncio

_RECORDS_PATH = Path(__file__).resolve().parents[1] / "r1_fix_recheck" / "recheck_records.jsonl"


def rec(step: str, **fields) -> None:
    """一条整改复验记录（JSONL 追加；独立于验收 raw_records）。"""
    _RECORDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"ts": datetime.now(UTC).isoformat(), "scenario": "F1_RECHECK_S1_4b", "step": step, **fields}
    with _RECORDS_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


@pytest_asyncio.fixture(name="recheck_api")
async def _recheck_api(q03_db):
    app = FastAPI()
    app.include_router(learning_journey_router)

    async def _override_db():
        yield q03_db

    caller = SimpleNamespace(id=None)

    def _override_user():
        return caller

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    transport = ASGITransport(app=app)
    return caller, AsyncClient(transport=transport, base_url="http://test")


async def test_f1_recheck_s1_4b_example_start_reaches_independent_check(q03_db, recheck_api):
    caller, client = recheck_api
    # ---- 1) 两跳全链（S1④b 同一场景设定：example 默认起点 + review_count=2 证据）----
    user = await _make_user(q03_db)
    caller.id = user.id
    task = await _make_mastery_task(q03_db, user, with_evidence=True, sprint_nodes=False)
    block, _degrade = parse_policy_block(task.guide_json)
    assert block is not None and block.scaffold.stage == "example", "起点=example（默认态，S1④b 同构）"

    resp1 = await client.post(f"/learning-journey/tasks/{task.id}/check/enter")
    assert resp1.status_code == 200, resp1.text
    body1 = resp1.json()
    view1 = body1["view"]
    assert body1["scaffold_persisted"] is True, "F1 修复：合法中间推进落库（缺陷本体消除）"
    assert view1["check_available"] is False
    assert "hold_reason" not in view1, "推进合法不得误报 HOLD.evidence_not_supported"
    assert "question" not in view1, "中间步不出题（出题仍被 stage 门拦住）"
    assert view1["scaffold"]["stage"] == "attempt"
    assert view1["scaffold"]["reason"] == "OK.advance_user_chose_with_evidence"
    assert "answer" not in json.dumps(body1, ensure_ascii=False)
    rec("enter_hop1_intermediate_advance_persisted", scaffold_persisted=True,
        stage=view1["scaffold"]["stage"], reason=view1["scaffold"]["reason"],
        check_available=False, false_hold_gone=True, answer_material_in_payload=False)

    # 判分门不放宽：中间推进后（attempt）提交仍拒判分（I07 红线不动）。
    early = await client.post(f"/learning-journey/tasks/{task.id}/check/submit", json={"answer": _CHECK_ANSWER})
    assert early.status_code == 200
    early_view = early.json()["view"]
    assert early_view["graded"] is False and early_view["correct"] is None
    assert early_view["reason"] == "HOLD.scaffold_not_at_check"
    rec("submit_before_check_stage_still_rejected", reason=early_view["reason"], correct=None)

    resp2 = await client.post(f"/learning-journey/tasks/{task.id}/check/enter")
    assert resp2.status_code == 200, resp2.text
    body2 = resp2.json()
    view2 = body2["view"]
    assert body2["scaffold_persisted"] is True
    assert view2["check_available"] is True, "example 起点两跳可达检验段（④b 翻绿）"
    assert view2["question"] == _CHECK_QUESTION
    assert view2["scaffold"]["stage"] == "independent_check"
    assert "answer" not in json.dumps(body2, ensure_ascii=False), "enter 放行面只有题面无答案"
    await q03_db.refresh(task)
    db_stage = parse_policy_block(task.guide_json)[0].scaffold.stage
    assert db_stage == "independent_check", "DB 权威位写回（持久化链全通）"
    assert task.guide_json["v4_hybrid_policy"]["independent_check"]["answer"] == _CHECK_ANSWER
    rec("enter_hop2_check_available", scaffold_persisted=True, stage=view2["scaffold"]["stage"],
        check_available=True, question_served=True, db_scaffold_stage=db_stage,
        answer_in_payload=False)

    graded = await client.post(f"/learning-journey/tasks/{task.id}/check/submit", json={"answer": _CHECK_ANSWER})
    assert graded.status_code == 200
    gview = graded.json()["view"]
    assert gview["graded"] is True and gview["correct"] is True
    assert gview["reason"] == "OK.check_graded_correct"
    assert _CHECK_ANSWER not in json.dumps(graded.json(), ensure_ascii=False)
    rec("submit_graded_zero_answer_material", graded=True, correct=True, reason=gview["reason"])

    # ---- 2) 反例保持：example + 无证据 → 仍 HOLD、不推进 ----
    no_ev = await _make_mastery_task(q03_db, user, with_evidence=False, sprint_nodes=False)
    held = await client.post(f"/learning-journey/tasks/{no_ev.id}/check/enter")
    assert held.status_code == 200
    held_view = held.json()["view"]
    assert held.json()["scaffold_persisted"] is False
    assert held_view["check_available"] is False
    assert held_view["hold_reason"] == "HOLD.evidence_not_supported"
    assert "question" not in held_view
    await q03_db.refresh(no_ev)
    assert parse_policy_block(no_ev.guide_json)[0].scaffold.stage == "example"
    rec("counter_case_no_evidence_still_holds", hold_reason="HOLD.evidence_not_supported",
        persisted=False, db_scaffold_stage="example")

    # ---- 3) 单跳回归护栏：attempt 起点单跳即达（整改不破坏既有行为）----
    single = await _make_mastery_task(q03_db, user, with_evidence=True, sprint_nodes=False)
    single.guide_json = apply_scaffold_decision(
        single.guide_json,
        next_scaffold_step(stage="example", hint_level="full", user_chose=True, evidence_supported=True),
    )
    raw = dict(single.guide_json)
    raw["v4_hybrid_policy"]["scaffold"]["stage"] = "attempt"  # S1④c 同款带外写（等价 attempt 起点）
    single.guide_json = raw
    await q03_db.commit()
    hop = await client.post(f"/learning-journey/tasks/{single.id}/check/enter")
    assert hop.status_code == 200
    hop_view = hop.json()["view"]
    assert hop_view["check_available"] is True and hop.json()["scaffold_persisted"] is True
    assert hop_view["scaffold"]["stage"] == "independent_check"
    assert hop_view["question"] == _CHECK_QUESTION
    rec("single_hop_attempt_to_check_unchanged", check_available=True, persisted=True,
        stage=hop_view["scaffold"]["stage"])

    rec("recheck_verdict", s1_4b="PASS（example 起点两跳可达独立检验段，defect_F1 检查项翻绿）",
        single_hop="PASS（既有行为不变）", counter_case_no_evidence="PASS（HOLD 保持）",
        submit_gate="PASS（未到段拒判分/到段判分零答案材料）")
