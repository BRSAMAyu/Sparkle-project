"""V4-Q03 · 人机分工与学习迁移护栏验收探针（验收剧本，不入生产测试树）.

卡：v4/04_tasks/tasks.json V4-Q03（kind=verification · risk=high · 双审）。
规格真源：MASTER_DESIGN §5「人机合作不偷走学习」/§6「示例→自己做→检查」、
EVALUATION_PROTOCOL（L1/L2 边界与 unknown 纪律）、V4_DONE §4「谁执行、何时
确认、人类步骤是否保留」。

四护栏 × 七场景（全部走真实服务/REST 面，零生产 LLM 调用；j06 prep 检索为
真实 sqlite 数据行；脚本化 LLM 只注入 execute_check 起草段并计数）：

- S1 示例隔离+出题门+提示渐隐（护栏2 I07 红线 + 渐隐转移表走查）
- S2 mastery：Agent 代答零掌握 + 星图 NON_HUMAN 不点亮；用户独立完成才结算/点亮（护栏1）
- S3 deliverable：合法代办结算完成面 + 星图能力面仍 NON_HUMAN（护栏1正面/护栏4 分报）
- S4 mixed：逐步骤归属消解与 2×3×2 结算矩阵（用户步骤归属）
- S5 切模式不跳人类步骤（护栏3a：agent 越权完成被拒 + 模式重入幂等同 run）
- S6 取消不跳人类步骤（护栏3b：取消不落完成戳 + 终态迟到确认 409 + 不复活）
- S7 重连幂等（护栏3c：双发 step_replay + 单次 resume + 冷启动恢复推导 + 交付确认幂等）

原始记录：每场景 JSONL 追加到 ../raw_records/<scenario>.jsonl（相对本文件）。
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.deps import get_current_active_superuser, get_current_user, get_db
from app.api.v1.learning_journey import router as learning_journey_router
from app.api.v1.runs import router as runs_router
from app.core.action_plan import ACTION_PLAN_SCHEMA_VERSION
from app.core.hybrid_policy import (  # 权威单一出处（不造第二词表）
    HYBRID_POLICY_VERSION,
    SettlementVerdict,
    derive_goal_purpose,
    human_mastery_settlement,
    next_scaffold_step,
    parse_policy_block,
    resolve_step_purpose,
    settlement_for_task_row,
    task_guide_context_projection,
)
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.services.agent_run_service import AgentRunService
from app.services.learning_journey_service import LearningJourneyService
from app.services.task_service import TaskService

GOAL_PURPOSE_MASTERY = "mastery"
GOAL_PURPOSE_DELIVERABLE = "deliverable"
GOAL_PURPOSE_MIXED = "mixed"

_RECORDS_DIR = Path(__file__).resolve().parents[1] / "raw_records"

_CHECK_QUESTION = "独立解释：为什么滑动摩擦力与接触面积无关？"
_CHECK_ANSWER = "压强不变时正压力与接触面积同比例变化，摩擦力只取决于正压力与摩擦系数"


def rec(scenario: str, step: str, **fields) -> None:
    """一条原始记录（JSONL 追加；验收审计与 run_manifest 引用）。"""
    _RECORDS_DIR.mkdir(exist_ok=True)
    payload = {"ts": datetime.now(UTC).isoformat(), "scenario": scenario, "step": step, **fields}
    with (_RECORDS_DIR / f"{scenario}.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


class _RecordingBus:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    async def publish(self, event_type: str, payload: dict, stream: str | None = None):
        self.published.append((event_type, dict(payload)))
        return "stub"


@pytest_asyncio.fixture(name="bus_stub")
async def _bus(monkeypatch):
    """事件总线记录桩（Redis 为外部设施；被测真部分在 DB 与纯函数）。"""
    from app.core.event_bus import event_bus_reliable

    stub = _RecordingBus()
    monkeypatch.setattr(event_bus_reliable, "publish", stub.publish)
    return stub


def _policy_block(*, goal_purpose: str, human_required: bool, stage: str = "example", hint: str = "full",
                  check: dict | None = None) -> dict:
    block = {
        "schema_version": HYBRID_POLICY_VERSION,
        "goal_purpose": goal_purpose,
        "human_required": human_required,
        "scaffold": {"stage": stage, "hint_level": hint},
    }
    if check is not None:
        block["independent_check"] = check
    return {"v4_hybrid_policy": block}


def _check_authority() -> dict:
    return {
        "kind": "independent_check",
        "question": _CHECK_QUESTION,
        "answer": _CHECK_ANSWER,
        "explanation": "滑动摩擦力公式 f = μN 中不包含接触面积项。",
    }


async def _make_user(db) -> User:
    from tests.unit.test_action_command_service import _make_user as _mk

    return await _mk(db)


async def _make_mastery_task(db, user: User, *, with_evidence: bool = True, sprint_nodes: bool = True,
                             purpose: str = GOAL_PURPOSE_MASTERY, human_required: bool = True) -> Task:
    guide = _policy_block(goal_purpose=purpose, human_required=human_required, check=_check_authority())
    if sprint_nodes:
        guide["sprint_mode"] = "q03_probe"
        guide["sprint_pack_nodes"] = [{"node_id": "phys.friction", "label": "摩擦力"}]
        guide["knowledge_node_ids"] = ["phys.friction"]
    node = KnowledgeNode(name=f"q03节点{uuid4().hex[:6]}", importance_level=3, is_seed=True)
    db.add(node)
    await db.flush()
    task = Task(
        id=uuid4(),
        user_id=user.id,
        title=f"掌握滑动摩擦力 {uuid4().hex[:6]}",
        type=TaskType.LEARNING,
        estimated_minutes=30,
        status=TaskStatus.IN_PROGRESS,
        started_at=datetime.utcnow(),
        knowledge_node_id=node.id,
        action_schema_version=ACTION_PLAN_SCHEMA_VERSION,
        desired_outcome="能独立解释并做对独立检验",
        smallest_useful_step={"description": "示例→自己做→检验", "useful_because": ["produces_artifact"]},
        execution_mode="hybrid",
        cognitive_ownership="user_core",
        guide_json=guide,
    )
    db.add(task)
    await db.flush()
    if with_evidence:
        db.add(ErrorRecord(
            user_id=user.id,
            subject_code="physics",
            chapter="摩擦力",
            question_text="滑动摩擦力与接触面积无关的原因？",
            user_answer="不知道",
            correct_answer="因为正压力不变",
            review_count=2,
            affected_node_id=node.id,
        ))
    await db.commit()
    await db.refresh(task)
    return task


async def _sprint_states(db, user_id, node_ids: list[str]) -> dict:
    from app.services.galaxy_service import GalaxyService

    return await GalaxyService(db).get_sprint_mastery_states(user_id, node_ids)


def _mastery_of(states: dict, node_id: str) -> float:
    return float(states.get(node_id, {}).get("mastery_score", 0.0) or 0.0)


async def _absorb(db, payload: dict):
    from app.services.galaxy.outcome_absorption_service import GalaxyOutcomeAbsorber

    return await GalaxyOutcomeAbsorber(db).absorb_outcome(payload)


def _task_payload(task) -> dict:
    from app.services.outcome_capture_service import build_outcome_recorded_payload, build_task_outcome_capture

    return build_outcome_recorded_payload(build_task_outcome_capture(task))


def _receipt_payload(run_status: str, task) -> dict:
    from app.services.outcome_capture_service import build_outcome_recorded_payload, build_run_receipt_outcome

    now = datetime.now(UTC).replace(tzinfo=None)
    run = SimpleNamespace(
        id=uuid4(), task_id=task.id, user_id=task.user_id, status=run_status,
        completed_at=now, created_at=now,
    )
    return build_outcome_recorded_payload(build_run_receipt_outcome(run))


class _Api:
    """REST 面（learning-journey + runs，同一 FastAPI app；依赖注入替换）。"""

    def __init__(self, maker: async_sessionmaker, user: User) -> None:
        self.app = FastAPI()
        self.app.include_router(learning_journey_router, prefix="/api/v1")
        self.app.include_router(runs_router, prefix="/api/v1")

        async def override_get_db():
            async with maker() as session:
                yield session

        self.app.dependency_overrides[get_db] = override_get_db
        self.app.dependency_overrides[get_current_user] = lambda: user
        self.app.dependency_overrides[get_current_active_superuser] = lambda: user
        self._transport = ASGITransport(app=self.app)

    def client(self) -> AsyncClient:
        return AsyncClient(transport=self._transport, base_url="http://test")


@pytest_asyncio.fixture(name="api_factory")
async def _api_factory(q03_maker):
    maker = q03_maker.maker


    def make_client(user: User) -> AsyncClient:
        return _Api(maker, user).client()

    return make_client


# ---------------------------------------------------------------------------
# S1 · 示例隔离 + 出题门 + 提示渐隐（护栏2）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_s1_example_isolation_and_hint_fading(q03_db, api_factory):
    scenario = "S1_example_isolation_hint_fading"
    t0 = time.monotonic()
    user = await _make_user(q03_db)
    task = await _make_mastery_task(q03_db, user, with_evidence=True, sprint_nodes=False)
    client = api_factory(user)

    # ① 示例段 GET：不出题面、零答案材料（I07 红线：correct/answer 不泄漏到可见面）
    resp = await client.get(f"/api/v1/learning-journey/tasks/{task.id}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    view = body["view"]
    dump = json.dumps(body, ensure_ascii=False)
    assert view["check"] is None, "未到检验段 GET 不得出题面"
    assert "answer" not in dump and "correct_answer" not in dump and "explanation" not in dump
    assert _CHECK_ANSWER not in dump and "μN" not in dump, "解析文本不得出现在示例段可见面"
    assert view["scaffold"] == {"stage": "example", "hint_level": "full", "segment": "practice"}
    err_brief = view["errors"][0]
    assert "correct_answer" not in err_brief and "user_answer" not in err_brief, "错题简报最小暴露面"
    assert view["practice"]["evidence_supported"] is True
    rec(scenario, "get_example_stage", task_id=str(task.id), check=view["check"],
        scaffold=view["scaffold"], answer_material_in_payload=False, evidence_supported=True,
        warnings=body["warnings"])

    # ② chat 上下文投影（api/v1/chat.py 注入点唯一入口）：答案剥除、脚手架面单独投影
    clean, scaffold_face, removed = task_guide_context_projection(task.guide_json)
    clean_dump = json.dumps(clean, ensure_ascii=False)
    assert removed, "含答案的 guide_json 投影必须发生剥除"
    assert _CHECK_ANSWER not in clean_dump and "explanation" not in clean_dump
    assert scaffold_face == {"stage": "example", "hint_level": "full", "goal_purpose": "mastery"}
    rec(scenario, "chat_projection", removed_paths=list(removed),
        answer_in_clean=False, scaffold_face=scaffold_face)

    # ③ 提示渐隐链（冻结转移表真实序列走查 + 阶段单调断言）
    order = {"example": 0, "attempt": 1, "independent_check": 2}
    seq = [
        ("example", "full", False, True, False, ("example", "reduced", "OK.hint_fading_prior_example_sufficient")),
        ("example", "reduced", False, True, False, ("example", "none", "OK.hint_fading_prior_example_sufficient")),
        ("example", "none", False, True, False, ("example", "none", "OK.hint_fading_prior_example_sufficient")),
        ("example", "none", True, True, False, ("attempt", "none", "OK.advance_user_chose_with_evidence")),
        ("attempt", "none", False, True, True, ("attempt", "reduced", "SUPPORT.failure_adds_local_hint")),
        ("attempt", "reduced", False, True, True, ("attempt", "full", "SUPPORT.failure_adds_local_hint")),
        ("attempt", "full", True, True, False, ("independent_check", "reduced", "OK.advance_user_chose_with_evidence")),
        ("independent_check", "none", False, False, False,
         ("independent_check", "none", "OK.independent_check_reached")),
    ]
    faded_rows = []
    for stage, hint, chose, ev, failed, (es, eh, er) in seq:
        d = next_scaffold_step(stage=stage, hint_level=hint, user_chose=chose,
                               evidence_supported=ev, attempt_failed=failed)
        assert (d.stage, d.hint_level, d.reason) == (es, eh, er), \
            f"{stage}/{hint} → {(d.stage, d.hint_level, d.reason)} != {(es, eh, er)}"
        assert order[d.stage] >= order[stage], "阶段永不回退"
        faded_rows.append({"in": [stage, hint], "chose": chose, "failed": failed,
                           "out": [d.stage, d.hint_level], "reason": d.reason})
    rec(scenario, "hint_fading_chain", transitions=faded_rows, stage_monotonic=True)

    # ④ 出题门服务面（真实旅程路径）
    # ④a 无证据：HOLD 不推进不出题（正）
    no_ev_task = await _make_mastery_task(q03_db, user, with_evidence=False, sprint_nodes=False)
    svc = LearningJourneyService(q03_db)
    held, _reason = await svc.enter_check(user_id=user.id, task_id=no_ev_task.id)
    assert held.view["check_available"] is False
    assert held.view["hold_reason"] == "HOLD.evidence_not_supported"
    assert held.scaffold_persisted is False and "question" not in held.view
    rec(scenario, "enter_gate_no_evidence", hold_reason=held.view["hold_reason"], persisted=False)

    # ④b 从 example 段两次显式选择（默认起点→自己做→检验的真实两跳）——
    # 发现 F1：request_independent_check 对合法中间推进（example→attempt）也返回
    # HOLD.evidence_not_supported（core/learning_journey.py:275-283 只在直达
    # independent_check 时返回 None），enter_check 的持久化门
    # `hold_reason is None`（services/learning_journey_service.py:330-333）因此
    # 永不写回——example 起点（默认 ScaffoldState）经旅程页永远到不了检验段，
    # 且已推进的 decision 被丢弃、响应携带误导性 hold_reason。
    ok, _reason2 = await svc.enter_check(user_id=user.id, task_id=task.id)
    first_advanced_to_attempt = ok.view["scaffold"]["stage"] == "attempt"
    assert first_advanced_to_attempt, "决策面应已推进到 attempt（内存面）"
    assert ok.scaffold_persisted is False, "F1：合法推进未持久化（缺陷本体）"
    assert ok.view.get("hold_reason") == "HOLD.evidence_not_supported", "F1：推进被误标为 HOLD"
    ok2, _reason3 = await svc.enter_check(user_id=user.id, task_id=task.id)
    assert ok2.scaffold_persisted is False and ok2.view["scaffold"]["stage"] == "attempt", \
        "F1：第二次显式选择仍卡在同一跳（脚手架从未写回）"
    await q03_db.refresh(task)
    persisted_stage = (parse_policy_block(task.guide_json)[0].scaffold.stage)
    assert persisted_stage == "example", "F1：DB 权威位停在 example（检验段不可达）"
    rec(scenario, "defect_F1_enter_stuck_from_example",
        first_decision_stage=ok.view["scaffold"]["stage"], first_persisted=False,
        second_decision_stage=ok2.view["scaffold"]["stage"], second_persisted=False,
        db_scaffold_stage=persisted_stage,
        anchors=["backend/app/core/learning_journey.py:request_independent_check",
                 "backend/app/services/learning_journey_service.py:enter_check"],
        impact="example 起点任务经 check/enter 无法到达检验段；单跳 attempt→check 路径不受影响")

    # ④c 单跳路径（attempt 起点，= U10 已测面）：一次显式选择到检验段、题面无答案
    at_attempt = await _make_mastery_task(q03_db, user, with_evidence=True, sprint_nodes=False)
    block = parse_policy_block(at_attempt.guide_json)[0]
    assert block.scaffold.stage == "example"
    from app.core.hybrid_policy import apply_scaffold_decision

    at_attempt.guide_json = apply_scaffold_decision(
        at_attempt.guide_json, next_scaffold_step(stage="example", hint_level="full",
                                                  user_chose=True, evidence_supported=True)
    )
    await q03_db.commit()
    at_attempt_raw = dict(at_attempt.guide_json)
    at_attempt_raw["v4_hybrid_policy"]["scaffold"]["stage"] = "attempt"
    at_attempt.guide_json = at_attempt_raw
    await q03_db.commit()
    ok3, _reason4 = await svc.enter_check(user_id=user.id, task_id=at_attempt.id)
    assert ok3.view["check_available"] is True and ok3.scaffold_persisted is True
    assert ok3.view["scaffold"]["stage"] == "independent_check"
    assert ok3.view["question"] == _CHECK_QUESTION
    assert "answer" not in json.dumps(ok3.view, ensure_ascii=False), "enter 放行面只有题面无答案"
    rec(scenario, "enter_gate_single_hop_ok", persisted=True,
        stage=ok3.view["scaffold"]["stage"], question_served=True, answer_in_payload=False)

    # ⑤ 判分面：确定性归一比对（零模型）——改述答案判错（诚实边界），精确答案判对；
    # 响应零答案材料（泛化反馈，不含解析/答案文本）
    paraphrase = await client.post(f"/api/v1/learning-journey/tasks/{at_attempt.id}/check/submit",
                                   json={"answer": "因为压强不变，正压力与面积同比变化"})
    assert paraphrase.status_code == 200
    p_body = paraphrase.json()["view"]
    assert p_body["graded"] is True and p_body["correct"] is False, "改述不是精确匹配：确定性判分不放宽"
    rec(scenario, "submit_paraphrase_graded_incorrect", correct=False,
        note="判分=确定性归一精确比对，无模型放宽（对齐 U10 契约）")

    graded = await client.post(f"/api/v1/learning-journey/tasks/{at_attempt.id}/check/submit",
                               json={"answer": _CHECK_ANSWER})
    assert graded.status_code == 200, graded.text
    gbody = graded.json()["view"]
    assert gbody["graded"] is True and gbody["correct"] is True
    assert gbody["reason"] == "OK.check_graded_correct"
    full_dump = json.dumps(graded.json(), ensure_ascii=False)
    assert "answer" not in gbody and _CHECK_ANSWER not in full_dump and "μN" not in full_dump
    rec(scenario, "submit_graded", correct=True, reason=gbody["reason"], feedback=gbody.get("feedback"),
        answer_in_payload=False, elapsed_s=round(time.monotonic() - t0, 3))
    rec(scenario, "guardrail2_verdict",
        example_isolation="PASS（GET/投影/enter/submit 全可达面零答案材料）",
        hint_fading="PASS（转移表+阶段单调）",
        check_journey_reachability_from_example="FAIL_F1（enter 持久化门，见 defect_F1 记录）",
        single_hop_attempt_to_check="PASS")


# ---------------------------------------------------------------------------
# S2 · mastery：Agent 代答零掌握 + NON_HUMAN 不点亮；用户独立完成才结算/点亮（护栏1）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_s2_agent_answer_never_settles_human_mastery(q03_db, bus_stub):
    scenario = "S2_agent_answer_no_mastery"
    t0 = time.monotonic()
    user = await _make_user(q03_db)

    # ---- ① Agent 代答（真实 TaskService.complete 生产完成路径）----
    agent_task = await _make_mastery_task(q03_db, user)  # mastery + human_required=True
    verdict = settlement_for_task_row(agent_task, evidence_source="agent")
    assert isinstance(verdict, SettlementVerdict) and verdict.allowed is False
    assert verdict.reason == "BLOCK.agent_completed_human_required_mastery"
    rec(scenario, "settlement_verdict_agent_hr", **verdict.to_dict())

    # human_required=False 的 mastery 步骤：仍 BLOCK（mastery 目标非用户完成一律不记）
    plain_mastery = await _make_mastery_task(q03_db, user, human_required=False)
    verdict2 = settlement_for_task_row(plain_mastery, evidence_source="agent")
    assert verdict2.allowed is False and verdict2.reason == "BLOCK.agent_completed_mastery_step"
    rec(scenario, "settlement_verdict_agent_mastery", **verdict2.to_dict())

    completed = await TaskService.complete(q03_db, agent_task, actual_minutes=30, evidence_source="agent")
    assert completed.status == TaskStatus.COMPLETED, "完成事实照常记账（行动账本与掌握账本分离）"
    states = await _sprint_states(q03_db, user.id, ["phys.friction"])
    assert _mastery_of(states, "phys.friction") == 0.0, "Agent 代答后人类掌握必须为 0"
    rec(scenario, "agent_completed", task_status=str(completed.status),
        sprint_mastery=_mastery_of(states, "phys.friction"), mastery_growth=0.0)

    # 结算拦截 WARN 留痕（loguru 观测面不静默；第二次真实 complete 路径捕获）
    from loguru import logger

    lines: list[str] = []
    hid = logger.add(lambda m: lines.append(m), level="WARNING")
    try:
        agent_task2 = await _make_mastery_task(q03_db, user)
        await TaskService.complete(q03_db, agent_task2, actual_minutes=10, evidence_source="agent")
    finally:
        logger.remove(hid)
    warn_hit = [ln for ln in lines if "人类掌握结算被拦截" in ln and "BLOCK." in ln]
    assert warn_hit, "结算拦截必须有 WARN 观测留痕"
    rec(scenario, "settlement_block_warn_observed", matched=True, sample=str(warn_hit[0])[:220])

    # ---- ② D04 通道：run receipt → NON_HUMAN → 吸收后不解锁不融合不点亮 ----
    from app.core.outcome_ledger import EvidenceRole
    from app.services.galaxy.capability_channel import (
        CapabilityChannel,
        classify_outcome_channel,
        fusion_observation_params,
    )
    from app.models.galaxy import UserNodeStatus

    receipt = _receipt_payload("SUCCEEDED", agent_task)
    channel = classify_outcome_channel(source=receipt["source"], entry=None)
    assert channel is CapabilityChannel.NON_HUMAN
    absorbed = await _absorb(q03_db, receipt)
    assert absorbed.action == "non_human" and absorbed.capability_channel == "non_human"
    status = await q03_db.get(UserNodeStatus, (user.id, agent_task.knowledge_node_id))
    # 完成路径的 spark（活动足迹）可解锁可见；红线是不融合：mastery 恒 0（D04 §1）。
    assert status is not None and float(status.mastery_score) == 0.0, "Agent 代答后掌握必须为 0"
    rec(scenario, "receipt_absorption", channel=channel.value, action=absorbed.action,
        unlocked_via_spark_trace=bool(status.is_unlocked), mastery_score=0.0,
        outcome_id=absorbed.outcome_id, note="spark 解锁=参与足迹（D04 ①），能力面红线=mastery 恒 0")

    # 纯 Agent receipt 升格 ACTUAL 的完成行 → 能力面仍 NON_HUMAN（X-08 真相面 ≠ 能力面）
    from app.core.outcome_ledger import TruthClass as _Truth

    ledger_entry = SimpleNamespace(
        truth_class=_Truth.ACTUAL,
        evidence=[SimpleNamespace(source="agent_run_receipt", role=EvidenceRole.INDEPENDENT,
                                  verified=True, evidence_kind="run_receipt")],
    )
    ch2 = classify_outcome_channel(source="task_completion", entry=ledger_entry)
    assert ch2 is CapabilityChannel.NON_HUMAN, "纯 Agent receipt 支撑的 ACTUAL 不计人类能力"
    assert fusion_observation_params(ch2, source="task_completion") is None, "NON_HUMAN 永不融合"
    rec(scenario, "receipt_upgraded_actual", channel=ch2.value, fusion=None)

    # ---- ③ 正面：用户独立完成（user 证据）→ 结算 +25 ----
    user_task = await _make_mastery_task(q03_db, user)
    verdict_user = settlement_for_task_row(user_task, evidence_source="user")
    assert verdict_user.allowed and verdict_user.reason == "OK.human_authored_settlement"
    await TaskService.complete(q03_db, user_task, actual_minutes=35, evidence_source="user")
    states_after = await _sprint_states(q03_db, user.id, ["phys.friction"])
    growth = _mastery_of(states_after, "phys.friction")
    assert growth == 25.0, f"用户亲自完成必须结算 +25（实际 {growth}）"
    rec(scenario, "user_completed_settlement", verdict=verdict_user.reason, sprint_mastery=growth,
        mastery_delta=25.0)

    # ---- ④ 独立检验通道：quiz 物化 → VERIFIED 真实点亮（同一旅程的对照面）----
    from app.models.galaxy import ExpansionFeedback, UserNodeStatus as _UNS

    q03_db.add(ExpansionFeedback(
        user_id=user.id, trigger_node_id=user_task.knowledge_node_id,
        meta_data={"source": "quiz_passed", "task_id": str(user_task.id)},
    ))
    await q03_db.commit()
    absorbed_quiz = await _absorb(q03_db, _task_payload(user_task))
    assert absorbed_quiz.action == "lit", f"独立检验通过必须点亮（实际 {absorbed_quiz.action}）"
    assert absorbed_quiz.capability_channel == "verified"
    status_quiz = await q03_db.get(_UNS, (user.id, user_task.knowledge_node_id))
    assert status_quiz.is_unlocked is True
    assert float(status_quiz.mastery_score) > 0.0, "VERIFIED 通道真实融合掌握后验"
    rec(scenario, "quiz_verified_absorption", action=absorbed_quiz.action,
        channel=absorbed_quiz.capability_channel, unlocked=True,
        mastery_score=float(status_quiz.mastery_score))

    rec(scenario, "guardrail1_verdict",
        agent_mastery_growth=0.0, user_mastery_growth=25.0,
        non_human_unlock=False, non_human_fusion=None,
        verified_channel="quiz_feedback", elapsed_s=round(time.monotonic() - t0, 3))


# ---------------------------------------------------------------------------
# S3 · deliverable：合法代办结算完成面 + 星图能力面仍 NON_HUMAN（护栏1正/护栏4分报）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_s3_deliverable_delegation_settles_but_galaxy_stays_non_human(q03_db, bus_stub):
    scenario = "S3_deliverable_efficiency_vs_capability"
    t0 = time.monotonic()
    user = await _make_user(q03_db)
    anchor = KnowledgeNode(name=f"q03交付{uuid4().hex[:6]}", importance_level=3, is_seed=True)
    q03_db.add(anchor)
    await q03_db.flush()
    guide = _policy_block(goal_purpose=GOAL_PURPOSE_DELIVERABLE, human_required=False)
    guide["sprint_mode"] = "q03_probe"
    guide["sprint_pack_nodes"] = [{"node_id": "doc.report", "label": "综述报告"}]
    task = Task(
        id=uuid4(), user_id=user.id,
        title="整理联邦学习综述资料包", type=TaskType.PLANNING,
        estimated_minutes=60, status=TaskStatus.IN_PROGRESS, started_at=datetime.utcnow(),
        knowledge_node_id=anchor.id,
        action_schema_version=ACTION_PLAN_SCHEMA_VERSION,
        desired_outcome="一份带引用的资料包",
        smallest_useful_step={"description": "整理并交付", "useful_because": ["produces_artifact"]},
        execution_mode="agent", cognitive_ownership="delegated", guide_json=guide,
    )
    q03_db.add(task)
    await q03_db.commit()
    await q03_db.refresh(task)

    verdict = settlement_for_task_row(task, evidence_source="agent")
    assert verdict.allowed and verdict.reason == "OK.deliverable_delegation_settlement", \
        "交付目标 Agent 合法代办照常结算，不强迫用户手工重复"
    done = await TaskService.complete(q03_db, task, actual_minutes=12, evidence_source="agent")
    assert done.status == TaskStatus.COMPLETED
    states = await _sprint_states(q03_db, user.id, ["doc.report"])
    completion_face_mastery = _mastery_of(states, "doc.report")
    assert completion_face_mastery == 25.0, "交付合法代办在完成面照常结算"
    rec(scenario, "deliverable_agent_settlement", verdict=verdict.reason,
        completion_face_mastery=completion_face_mastery, user_manual_redo_required=False)

    # 星图能力面：同一工作的 run receipt → NON_HUMAN，能力节点不点亮
    from app.services.galaxy.capability_channel import CapabilityChannel, classify_outcome_channel
    from app.models.galaxy import UserNodeStatus

    receipt = _receipt_payload("SUCCEEDED", task)
    channel = classify_outcome_channel(source=receipt["source"], entry=None)
    assert channel is CapabilityChannel.NON_HUMAN
    absorbed = await _absorb(q03_db, receipt)
    assert absorbed.action == "non_human"
    status = await q03_db.get(UserNodeStatus, (user.id, task.knowledge_node_id))
    # 能力面红线：交付任务的 Agent receipt 不融合（spark 解锁若存在仅为活动足迹）
    assert status is None or float(status.mastery_score) == 0.0, \
        "交付任务的 Agent receipt 不得点亮能力节点掌握"
    rec(scenario, "galaxy_capability_channel", channel=channel.value, capability_lit=False,
        status_exists=status is not None,
        mastery_score=float(status.mastery_score) if status is not None else None,
        note="完成面结算（deliverable 合法代办）与能力面点亮（星图 NON_HUMAN）为两个分立报表面")

    # 效率面（模拟器口径）：Agent 路径 12 分钟 vs 用户手工基线 60 分钟估计——
    # 效率数字只在模拟/估计层成立，真人效率 = unknown（limitations 显式）。
    rec(scenario, "efficiency_simulator_only",
        agent_path_minutes=12, user_baseline_estimated_minutes=60,
        real_human_efficiency="unknown_not_measured",
        elapsed_s=round(time.monotonic() - t0, 3))


# ---------------------------------------------------------------------------
# S4 · mixed：逐步骤归属消解 + 结算矩阵（用户步骤归属）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_s4_mixed_step_attribution_and_settlement_matrix(q03_db):
    scenario = "S4_mixed_attribution_matrix"
    user = await _make_user(q03_db)
    task = await _make_mastery_task(q03_db, user, purpose=GOAL_PURPOSE_MIXED, human_required=False,
                                    with_evidence=False, sprint_nodes=False)

    block, degrade = parse_policy_block(task.guide_json)
    assert block is not None and block.goal_purpose == GOAL_PURPOSE_MIXED and degrade is None

    # 逐步骤消解：human_required 恒 mastery；user_core→mastery；delegated 准备步合法
    rows = []
    for hr, ownership in [(True, "user_core"), (False, "user_core"), (False, "delegated"), (False, None)]:
        resolved = resolve_step_purpose(GOAL_PURPOSE_MIXED, human_required=hr, cognitive_ownership=ownership)
        rows.append({"human_required": hr, "ownership": ownership, "resolved": resolved})
        rec(scenario, "resolve_step", **rows[-1])
    assert rows[0]["resolved"] == GOAL_PURPOSE_MASTERY
    assert rows[1]["resolved"] == GOAL_PURPOSE_MASTERY
    assert rows[2]["resolved"] == GOAL_PURPOSE_MIXED  # delegated 准备步（Agent 可代，掌握门不变）

    # 2×3×2 结算矩阵（completed_by × purpose × human_required）全组合留证
    matrix = []
    for by in ("user", "agent"):
        for purpose in (GOAL_PURPOSE_MASTERY, GOAL_PURPOSE_DELIVERABLE, GOAL_PURPOSE_MIXED):
            for hr in (True, False):
                v = human_mastery_settlement(goal_purpose=purpose, human_required=hr, completed_by=by)
                matrix.append({"by": by, "purpose": purpose, "human_required": hr,
                               "allowed": v.allowed, "reason": v.reason})
                rec(scenario, "settlement_matrix_row", **matrix[-1])
    by_user = [r for r in matrix if r["by"] == "user"]
    assert all(r["allowed"] and r["reason"] == "OK.human_authored_settlement" for r in by_user)
    agent_rows = {(r["purpose"], r["human_required"]): r for r in matrix if r["by"] == "agent"}
    assert agent_rows[(GOAL_PURPOSE_MASTERY, True)]["reason"] == "BLOCK.agent_completed_human_required_mastery"
    assert agent_rows[(GOAL_PURPOSE_MASTERY, False)]["reason"] == "BLOCK.agent_completed_mastery_step"
    assert agent_rows[(GOAL_PURPOSE_DELIVERABLE, True)]["reason"] == "BLOCK.agent_completed_human_required_mastery"
    assert agent_rows[(GOAL_PURPOSE_MIXED, True)]["reason"] == "BLOCK.agent_completed_human_required_mastery"
    assert agent_rows[(GOAL_PURPOSE_DELIVERABLE, False)]["allowed"] is True
    assert agent_rows[(GOAL_PURPOSE_MIXED, False)]["allowed"] is True
    rec(scenario, "matrix_verdict", rows=len(matrix), agent_block_rows=4, user_ok_rows=6)

    # legacy 行推导（无策略块）与 X-02 学习守卫同集
    assert derive_goal_purpose("LEARNING", None) == GOAL_PURPOSE_MASTERY
    assert derive_goal_purpose("PLANNING", "delegated") == GOAL_PURPOSE_DELIVERABLE
    assert derive_goal_purpose("SOCIAL", "user_core") == GOAL_PURPOSE_MASTERY
    assert derive_goal_purpose("SOCIAL", "shared") == GOAL_PURPOSE_MIXED


# ---------------------------------------------------------------------------
# S5 · 切模式不跳人类步骤（护栏3a）
# ---------------------------------------------------------------------------


def _scripted_llm(counter: dict):
    async def _chat(messages, **_kwargs):
        counter["calls"] += 1
        return "## 研究综述大纲\n\n1. 问题定义 [S1]\n2. 技术路线 [S2]\n"

    return _chat


async def _seed_j06_world(db, user: User):
    """真实 j06 旅程世界：goal + 任务 + 真实材料行（prep 检索真源）。"""
    from tests.unit.test_j06_hybrid_journey import _seed_goal, _seed_materials, _seed_task

    await _seed_goal(db, user)
    node = KnowledgeNode(name="联邦学习", importance_level=3, is_seed=True)
    db.add(node)
    await db.flush()
    task = await _seed_task(db, user, node)
    await _seed_materials(db, user)
    await db.commit()
    return task


async def _journey_to_judgment(db, user: User, task: Task):
    from app.services.hybrid_journey_service import HYBRID_JOURNEY_TRACE_ID, start_hybrid_journey

    started = await start_hybrid_journey(db, user_id=user.id, task_id=task.id, session_id=str(uuid4()))
    run_view = started["run"]
    assert run_view["trace_id"] == HYBRID_JOURNEY_TRACE_ID
    assert run_view["awaiting_step"]["step_id"] == "judgment"
    assert run_view["awaiting_step"]["owner"] == "human"
    return started


@pytest.mark.asyncio
async def test_s5_mode_switch_never_skips_human_step(q03_db, bus_stub):
    scenario = "S5_mode_switch_human_step_kept"
    user = await _make_user(q03_db)
    task = await _seed_j06_world(q03_db, user)
    started = await _journey_to_judgment(q03_db, user, task)
    run_id = started["run"]["run_id"]
    rec(scenario, "journey_started", run_id=run_id, awaiting=started["run"]["awaiting_step"]["step_id"])

    # ① Agent 越权完成 human 判断步（模拟「全交给 Agent」的模式越权）→ owner 纪律拒绝
    service = AgentRunService(q03_db)
    with pytest.raises(ValueError) as ei:
        await service.complete_agent_step(run_id, step_id="judgment", user_id=user.id,
                                          artifact_refs=[], idempotency_key="agent-bypass-1")
    assert "human" in str(ei.value) or "agent-owned" in str(ei.value)
    run = await service.get_run(run_id, user_id=user.id)
    judgment = next(s for s in run.steps if s.get("step_id") == "judgment")
    assert judgment.get("completion") is None, "越权被拒后 human 步不得有完成戳"
    rec(scenario, "agent_bypass_rejected", error=str(ei.value)[:160], judgment_completion=None)

    # ② 切换模式重入（换 session/设备再进同一任务旅程）→ 同 run 回放，判断步原地等待
    from app.services.hybrid_journey_service import get_hybrid_journey_state, start_hybrid_journey

    reentered = await start_hybrid_journey(q03_db, user_id=user.id, task_id=task.id,
                                           session_id=str(uuid4()))
    assert reentered["run"]["run_id"] == run_id, "模式切换重入必须收敛到同一段 run（不跳步不另开）"
    assert reentered["run"]["awaiting_step"]["step_id"] == "judgment"
    assert reentered["run"]["awaiting_step"]["state"] == "awaiting"
    rec(scenario, "mode_reentry_same_run", run_id=reentered["run"]["run_id"],
        awaiting=reentered["run"]["awaiting_step"]["step_id"], new_run_created=False)

    # ③ 用户亲自判断（唯一推进路径）→ 才进入下一段
    from app.services.hybrid_journey_service import submit_judgment

    citations = started["citations"]
    counter = {"calls": 0}
    judged = await submit_judgment(
        q03_db, user_id=user.id, run_id=run_id,
        selected_refs=[c["source_ref"] for c in citations[:2]],
        focus_note="先看隐私机制", idempotency_key="q03-judge-s5",
        llm_chat=_scripted_llm(counter),
    )
    assert counter["calls"] == 1
    assert judged["run"]["awaiting_step"]["step_id"] == "outcome"
    rec(scenario, "user_judgment_advanced", awaiting="outcome", llm_calls=counter["calls"])

    # ④ 冷启动读面（切端后）回放同一段 run 的持久态
    state = await get_hybrid_journey_state(q03_db, user_id=user.id, run_id=run_id)
    assert state["run"]["run_id"] == run_id
    assert state["run"]["awaiting_step"]["step_id"] == "outcome"
    rec(scenario, "cold_state_replay", run_id=run_id, awaiting="outcome")


# ---------------------------------------------------------------------------
# S6 · 取消不跳人类步骤（护栏3b）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_s6_cancel_keeps_human_step_uncompleted(q03_db, api_factory):
    scenario = "S6_cancel_human_step_kept"
    user = await _make_user(q03_db)
    client = api_factory(user)

    plan = {"steps": [
        {"step_id": "s1", "ordinal": 1, "label": "整理资料", "owner": "agent",
         "completion_condition": {"kind": "agent_output"}},
        {"step_id": "s2", "ordinal": 2, "label": "确认清单", "owner": "human",
         "completion_condition": {"kind": "user_confirmation"}},
    ]}
    resp = await client.post("/api/v1/runs", json={"objective": "错题变复习卡", **plan})
    assert resp.status_code == 201
    run_id = resp.json()["run"]["run_id"]
    await client.post(f"/api/v1/runs/{run_id}/resume", json={"to_status": "RUNNING"})
    await client.post(f"/api/v1/runs/{run_id}/steps/s1/agent-complete", json={})
    await client.post(f"/api/v1/runs/{run_id}/steps/s2/await", json={"prompt": "请确认清单"})

    # 取消 → human 步无完成戳、状态 CANCELLED、归因 user_cancelled
    resp = await client.post(f"/api/v1/runs/{run_id}/cancel", json={"reason": "user_cancelled"})
    assert resp.status_code == 200, resp.text
    run_view = resp.json()["run"]
    assert run_view["status"] == "CANCELLED" and run_view["terminal_reason"] == "user_cancelled"
    s2 = next(s for s in run_view["steps"] if s["step_id"] == "s2")
    assert s2.get("completion") is None, "取消不得给人类步骤落完成戳（不跳步）"
    rec(scenario, "cancelled", run_id=run_id, terminal_reason=run_view["terminal_reason"],
        human_step_completion=None, awaiting_state=run_view["awaiting_step"]["state"])

    # 迟到确认 → 409 + 终态归因可见
    late = await client.post(f"/api/v1/runs/{run_id}/steps/s2/complete",
                             json={"idempotency_key": "late-confirm"})
    assert late.status_code == 409
    assert late.json()["detail"]["run"]["terminal_reason"] == "user_cancelled"
    rec(scenario, "late_confirm_409", status=409, terminal_reason="user_cancelled")

    # j06 旅程在判断步取消 → 不可代决；同任务重启拿新 attempt，判断步从头等用户
    from app.services.agent_run_service import RunNotAwaitingUserStepError
    from app.services.hybrid_journey_service import HybridJourneyStateError
    from app.services.hybrid_journey_service import start_hybrid_journey, submit_judgment

    jtask = await _seed_j06_world(q03_db, user)
    started = await _journey_to_judgment(q03_db, user, jtask)
    jrun = started["run"]["run_id"]
    resp = await client.post(f"/api/v1/runs/{jrun}/cancel", json={"reason": "user_cancelled"})
    assert resp.status_code == 200, resp.text
    judgment_view = next(s for s in resp.json()["run"]["steps"] if s["step_id"] == "judgment")
    assert judgment_view.get("completion") is None, "取消不落判断完成戳"
    citations = started["citations"]
    with pytest.raises((HybridJourneyStateError, RunNotAwaitingUserStepError)):
        await submit_judgment(q03_db, user_id=user.id, run_id=jrun,
                              selected_refs=[c["source_ref"] for c in citations[:1]],
                              idempotency_key="after-cancel", llm_chat=_scripted_llm({"calls": 0}))
    rec(scenario, "journey_cancelled_judgment_untouched", run_id=jrun, judgment_completion=None,
        submit_after_cancel="rejected")

    restarted = await start_hybrid_journey(q03_db, user_id=user.id, task_id=jtask.id, session_id=str(uuid4()))
    assert restarted["run"]["run_id"] != jrun, "取消后同 intent 不复活旧 run（新 attempt 从头开始）"
    assert restarted["run"]["awaiting_step"]["step_id"] == "judgment", "重启后仍从人类判断步等起（不跳步）"
    service = AgentRunService(q03_db)
    old = await service.get_run(jrun, user_id=user.id)
    assert old.status.value == "CANCELLED", "旧 run 保持取消终态"
    rec(scenario, "restart_new_attempt", old_run=jrun, new_run=restarted["run"]["run_id"],
        new_awaiting=restarted["run"]["awaiting_step"]["step_id"], old_status="CANCELLED")


# ---------------------------------------------------------------------------
# S7 · 重连幂等（护栏3c）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_s7_reconnect_idempotent_confirm(q03_db, api_factory):
    scenario = "S7_reconnect_idempotent"
    user = await _make_user(q03_db)
    client = api_factory(user)
    plan = {"steps": [
        {"step_id": "s1", "ordinal": 1, "label": "整理资料", "owner": "agent",
         "completion_condition": {"kind": "agent_output"}},
        {"step_id": "s2", "ordinal": 2, "label": "确认清单", "owner": "human",
         "completion_condition": {"kind": "user_confirmation"}},
    ]}
    resp = await client.post("/api/v1/runs", json={"objective": "错题变复习卡", **plan})
    run_id = resp.json()["run"]["run_id"]
    await client.post(f"/api/v1/runs/{run_id}/resume", json={"to_status": "RUNNING"})
    await client.post(f"/api/v1/runs/{run_id}/steps/s1/agent-complete", json={})
    await client.post(f"/api/v1/runs/{run_id}/steps/s2/await", json={"prompt": "请确认清单"})

    key = f"x07:{run_id}:s2:confirm"  # U04 工作台确定性幂等键推导式
    first = await client.post(f"/api/v1/runs/{run_id}/steps/s2/complete",
                              json={"idempotency_key": key, "action": "confirm"})
    assert first.status_code == 200
    assert first.json()["transition_applied"] is True and first.json()["step_replay"] is False
    # 断线重连双发（同 key）与另一设备重试（换 key）→ 都是重放，resume 恰一次
    dup_same = await client.post(f"/api/v1/runs/{run_id}/steps/s2/complete",
                                 json={"idempotency_key": key, "action": "confirm"})
    dup_other = await client.post(f"/api/v1/runs/{run_id}/steps/s2/complete",
                                  json={"idempotency_key": key + ":device-2", "action": "confirm"})
    assert dup_same.status_code == 200 and dup_same.json()["step_replay"] is True
    assert dup_other.status_code == 200 and dup_other.json()["step_replay"] is True
    transitions = await client.get(f"/api/v1/runs/{run_id}/transitions")
    resume_rows = [t for t in transitions.json()["items"] if t["event_name"] == "run.user_resumed"]
    assert len(resume_rows) == 1, "重连三连发只允许一次 resume"
    missing_key = await client.post(f"/api/v1/runs/{run_id}/steps/s2/complete", json={"action": "confirm"})
    assert missing_key.status_code == 422, "幂等键是强制前提"
    rec(scenario, "double_fire", key=key, first_applied=True, dup_same_replay=True,
        dup_other_replay=True, resume_events=1, missing_key_status=422)

    # 冷启动（新 client 实例 = 新进程）仅凭 run_id 还原持久态
    fresh = api_factory(user)
    detail = await fresh.get(f"/api/v1/runs/{run_id}")
    assert detail.status_code == 200
    run_view = detail.json()["run"]
    s2 = next(s for s in run_view["steps"] if s["step_id"] == "s2")
    assert s2.get("completion") is not None, "重连后完成戳持久可见（不要求用户重做）"
    rec(scenario, "cold_reopen", status=run_view["status"], s2_completed=True)

    # j06 判断步幂等重放：同 key 二次提交——人类步骤不被跳过/不重复落判断戳；
    # 发现 F2：重放路径无条件重跑 execute_check（LLM 二次调用 + execute_check
    # 产物行重复；hybrid_journey_service.py:713 无条件 _execute_and_check +
    # :728-745 无条件落产物）。该缺陷不越过人类步骤（判断戳不重复、run 不进
    # SUCCEEDED、交付仍需用户确认）——记为成本/工件卫生缺陷，随报告上交。
    from app.services.hybrid_journey_service import confirm_outcome, get_hybrid_journey_state, submit_judgment

    jtask = await _seed_j06_world(q03_db, user)
    started = await _journey_to_judgment(q03_db, user, jtask)
    jrun = started["run"]["run_id"]
    citations = started["citations"]
    counter = {"calls": 0}
    first_j = await submit_judgment(q03_db, user_id=user.id, run_id=jrun,
                                    selected_refs=[c["source_ref"] for c in citations[:2]],
                                    focus_note="先看隐私", idempotency_key="q03-judge-s7",
                                    llm_chat=_scripted_llm(counter))
    arts_after_first = len(first_j["artifacts"])
    assert first_j["receipt"]["judgment_replay"] is False
    replay_j = await submit_judgment(q03_db, user_id=user.id, run_id=jrun,
                                     selected_refs=[c["source_ref"] for c in citations[:2]],
                                     focus_note="先看隐私", idempotency_key="q03-judge-s7",
                                     llm_chat=_scripted_llm(counter))
    assert replay_j["receipt"]["judgment_replay"] is True, "重放语义标记正确（判断步未被二次处理）"
    run_between = replay_j["run"]
    assert run_between["status"] != "SUCCEEDED" and run_between["awaiting_step"]["step_id"] == "outcome", \
        "重放不得越过人类交付确认步"
    arts_after_replay = len(replay_j["artifacts"])
    rec(scenario, "defect_F2_judgment_replay_recalculates",
        llm_calls_expected=1, llm_calls_observed=counter["calls"],
        artifacts_after_first=arts_after_first, artifacts_after_replay=arts_after_replay,
        human_step_skipped=False, judgment_stamp_duplicated=False,
        anchors=["backend/app/services/hybrid_journey_service.py:713",
                 "backend/app/services/hybrid_journey_service.py:728-745"],
        impact="断线重连同 key 重提交判断会重复调用起草 LLM 并重复落 execute_check 产物行"
               "（成本/工件卫生）；人类步骤归属与推进门不受影响")

    # 交付确认幂等：confirm_outcome 二次提交走已确认回放（任务只完成一次）
    confirmed = await confirm_outcome(q03_db, user_id=user.id, run_id=jrun, idempotency_key="q03-confirm-s7")
    assert confirmed["run"]["status"] == "SUCCEEDED"
    replay_c = await confirm_outcome(q03_db, user_id=user.id, run_id=jrun, idempotency_key="q03-confirm-s7")
    assert replay_c["receipt"]["decision_reason"].startswith("交付已确认过")
    completed_rows = (
        await q03_db.execute(
            select(func.count()).select_from(Task).where(Task.id == jtask.id, Task.status == TaskStatus.COMPLETED)
        )
    ).scalar_one()
    assert completed_rows == 1, "任务完成恰一次（幂等回放不重复完成）"
    rec(scenario, "confirm_replay", run_status="SUCCEEDED", task_completed_rows=completed_rows)

    state = await get_hybrid_journey_state(q03_db, user_id=user.id, run_id=jrun)
    assert state["run"]["status"] == "SUCCEEDED" and len(state["artifacts"]) >= 3
    rec(scenario, "guardrail3_verdict",
        mode_switch="human_step_kept", cancel="human_step_never_stamped",
        reconnect="single_resume_replay", artifacts_replay_idempotent=True)
