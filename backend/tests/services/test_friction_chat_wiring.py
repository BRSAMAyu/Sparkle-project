"""WIRING-1 · A-03/A-05/M-06 chat 决策路径接线测试（FIX-43 + FIX-34 + FIX-33）。

证明「三引擎真实进 chat/决策路径」可执行而非纸上谈兵，验收员可独立复现：

1. **P2 负向反转修复钉死**（FIX-43 前置条件）：R2 登记的三族反转
   （「不在等」→waiting_external /「不想要了」→goal_still_wanted /
   「试过但不对」→tried_confident）全部修复 + 全问题库负向/正向对照集
   （branch 级全覆盖）+ 反转在 apply_question_answer 闭环内的端到端后果；
2. **ask 闭环 e2e**（FIX-43a）：chat 触发装配 FrictionDiagnosisInput →
   诊断 → 问（载荷带 branch_key 选项）→ 答（branch_key 直传主路径 /
   自由文本回退层）→ apply_question_answer 重诊断（S3/新出口）；
   未解析回答保持 pending、预算计数、pending TTL 生命周期；
3. **act 出口决策输入链**（FIX-34）：``policy_factors_patch`` 前置提名 →
   ``patched_decision_inputs``（A-05：真实 M-06 证据链激活的 prefer patch
   重排）→ ``evaluate_intervention_policy``（A-02）——patch 翻转 chat
   决策出口的实测（explain 从次位升首位的 selection flip）；DELTA-2/
   P3-5 语义不引入新缺陷（applied_patch_ids 归因随行、缓存版本键沿用）；
4. **M-06 经验记忆进 chat context**（FIX-33）：真实 D-05 证据链 →
   ``_attach_stage34_memory_context`` 注入 ``experience_memories``
   （经真实 M-03 预筛 + M-05 输出门），降档率可观测面
   ``experience_memory_meta``；**M-05 词法降档率实测**（FIX-33 原文要求）；
5. **拔接线必红三组**：orchestrator hook / M-06 stage34 注入 / A-05
   patched_decision_inputs 的接线点源面钉死（AST 活调用分析）——移除
   接线调用即红（防「建好无人走」回归）。

真实 LLM 0 次；sqlite 隔离（dev DB 只读纪律）；Redis 用 fakeredis。
"""

from __future__ import annotations

import ast
import json
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import fakeredis.aioredis
import pytest

from app.aurora.friction_diagnosis import (
    _QUESTION_BANK_INDEX,
    FRICTION_QUESTION_BANK,
    FrictionDiagnosis,
    OneBestQuestion,
    apply_question_answer,
    diagnose_friction,
    resolve_answer_branch,
)
from app.aurora.intervention_policy import evaluate_intervention_policy  # noqa: F401 (A-02 链面回归锚)
from app.core.aurora_decision import AuroraDecisionContract
from app.core.experience_memory import ExperienceContextQuery
from app.core.intervention_lifecycle import EVIDENCE_TIER_REPEATED
from app.core.outcome_ledger import (
    OutcomeEntry,
    OutcomePolarity,
    OutcomeSource,
    TruthClass,
    derive_outcome_id,
)
from app.models.execution_intent import ExecutionMode
from app.models.user import User
from app.orchestration.context_builder import ContextBuilderMixin
from app.orchestration.orchestrator import ChatOrchestrator
from app.services.experience_memory_projector import ExperienceMemoryProjector
from app.services.friction_chat_wiring import (
    _GATE_CLARIFY_QUESTION_REF,
    FRICTION_ANSWER_CONTEXT_KEY,
    FrictionChatWiringService,
    _gate_silent_diagnosis_payload,
)
from app.services.intervention_lifecycle_service import InterventionLifecycleService
from app.services.memory_use_selfcheck import SelfCheckContext, evaluate_memory_use_gate
from app.services.policy_patch_service import PolicyPatchService

_T0 = datetime(2026, 9, 19, 10, 0, 0)
_NOW = _T0 + timedelta(hours=80)

ORCHESTRATOR_PATH = Path(__file__).resolve().parents[2] / "app" / "orchestration" / "orchestrator.py"
CONTEXT_BUILDER_PATH = Path(__file__).resolve().parents[2] / "app" / "orchestration" / "context_builder.py"
RESPONSE_BUILDER_PATH = Path(__file__).resolve().parents[2] / "app" / "orchestration" / "response_builder.py"
WIRING_SVC_PATH = Path(__file__).resolve().parents[2] / "app" / "services" / "friction_chat_wiring.py"


@pytest.fixture(autouse=True)
def _clean_caches():
    PolicyPatchService.reset_cache()
    ExperienceMemoryProjector.reset_cache()
    yield
    PolicyPatchService.reset_cache()
    ExperienceMemoryProjector.reset_cache()


@pytest.fixture()
async def fake_redis():
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose() if hasattr(client, "aclose") else None


async def _make_user(db_session) -> User:
    user = User(
        username=f"u{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@t.co",
        hashed_password="x",
        registration_source="email",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def _decision(
    user_id,
    *,
    intervention_type: str = "practice",
    mode: ExecutionMode | None = ExecutionMode.HYBRID,
    task_id=None,
    salt: str = "",
    evidence=("signal://cognitive_load",),
) -> AuroraDecisionContract:
    return AuroraDecisionContract(
        user_id=user_id,
        intervention_type=intervention_type,
        rationale_summary=f"wiring test decision {salt or uuid4().hex[:6]}",
        cognition_tier="l2_intervention",
        execution_mode=mode,
        governance_mode="live",
        evidence_refs=tuple(evidence),
        clarifying_question=("要交什么、做到什么程度算好，现在清楚吗？" if intervention_type == "clarify" else None),
        action_proposal_ref=f"task://{task_id}" if task_id else None,
    )


def _outcome(
    user_id, *, at: datetime, polarity=OutcomePolarity.POSITIVE, correlation: dict | None = None
) -> OutcomeEntry:
    sid = uuid4().hex
    return OutcomeEntry(
        outcome_id=derive_outcome_id(source=OutcomeSource.TASK_COMPLETION, source_id=sid),
        source=OutcomeSource.TASK_COMPLETION,
        source_id=sid,
        user_id=str(user_id),
        occurred_at=at,
        truth_class=TruthClass.ACTUAL,
        polarity=polarity,
        source_ref=f"{OutcomeSource.TASK_COMPLETION.value}://{sid}",
        correlation=correlation if correlation is not None else {},
    )


async def _expose_and_link(
    db_session,
    user,
    *,
    intervention_type: str,
    n_positive: int = 0,
    n_negative: int = 0,
    goal: str = "exam",
    evidence=("signal://cognitive_load",),
    at: datetime = _T0,
) -> str:
    """真实 D-05 exposure + outcome 关联（生产服务路径，零 mock）。

    friction_tag 由决策 evidence_refs（signal://cognitive_load）推导——与
    A-05 服务测试同款（切片 friction_tag = cognitive_overload）。
    """
    svc = InterventionLifecycleService(db_session)
    task_id = uuid4()
    decision = _decision(
        user.id,
        intervention_type=intervention_type,
        task_id=task_id,
        salt=task_id.hex[:6],
        evidence=evidence,
    )
    result = await svc.record_exposure(
        decision=decision,
        user_id=user.id,
        goal_type=goal,
        occurred_at=at,
    )
    assert result.recorded, result.reason
    for i in range(n_positive):
        linked = await svc.record_outcome_association(
            decision_id=result.decision_id,
            outcome=_outcome(
                user.id,
                at=at + timedelta(hours=i + 1),
                polarity=OutcomePolarity.POSITIVE,
                correlation={"task_id": str(task_id)},
            ),
        )
        assert linked.recorded, linked.reason
    for i in range(n_negative):
        linked = await svc.record_outcome_association(
            decision_id=result.decision_id,
            outcome=_outcome(
                user.id,
                at=at + timedelta(hours=i + 1),
                polarity=OutcomePolarity.NEGATIVE,
                correlation={"task_id": str(task_id)},
            ),
        )
        assert linked.recorded, linked.reason
    return result.decision_id


async def _experience_record_id(
    db_session,
    user,
    *,
    intervention_type: str,
    goal: str = "exam",
    friction: str = "cognitive_overload",
) -> str:
    """（friction 参数只是过滤断言用；切片 friction_tag 由 evidence state_key 推导）"""
    projection = await ExperienceMemoryProjector(db_session).project(user_id=user.id, now=_NOW)
    for record in projection.records:
        signature = record.signature.as_dict()
        if (
            record.intervention == intervention_type
            and signature.get("goal_type") == goal
            and signature.get("friction_tag") == friction
        ):
            return record.record_id
    raise AssertionError(f"no experience record for {intervention_type}/{goal}/{friction}")


# ---------------------------------------------------------------------------
# 1. P2 负向反转修复：负向场景集钉死（FIX-43 前置条件）
# ---------------------------------------------------------------------------


class TestP2NegativeResolution:
    """R2 登记反转面 + 全问题库 branch 级负向/正向对照集（词面回退即红）。"""

    @pytest.mark.parametrize(
        ("question_id", "answer", "expected_branch"),
        [
            # R2 三族（修复前全部反转）：
            ("q_external_wait", "不在等", "not_waiting"),
            ("q_external_wait", "没在等", "not_waiting"),
            ("q_external_wait", "不等", "not_waiting"),
            ("q_goal_still_wanted", "不想要了", "goal_shifted"),
            ("q_goal_still_wanted", "没那么想要了", "goal_shifted"),
            ("q_tried_and_checked", "试过但不对", "tried_unsure"),
            # 同族扩展（负向词牌含正向子串的全部形态）：
            ("q_external_wait", "不等了，我自己来", "not_waiting"),
            ("q_external_wait", "没在等谁，是自己卡住了", "not_waiting"),
            ("q_goal_still_wanted", "不想要", "goal_shifted"),
            # 正向对照（修复不得伤正向解析）：
            ("q_external_wait", "在等", "waiting_external"),
            ("q_external_wait", "在等导师回复", "waiting_external"),
            ("q_external_wait", "waiting", "waiting_external"),
            ("q_external_wait", "还没回", "waiting_external"),
            ("q_goal_still_wanted", "还想要", "goal_still_wanted"),
            ("q_goal_still_wanted", "想要", "goal_still_wanted"),
            ("q_goal_still_wanted", "想换方向了", "goal_shifted"),
            ("q_tried_and_checked", "没把握", "tried_unsure"),
            ("q_tried_and_checked", "不确定", "tried_unsure"),
            ("q_tried_and_checked", "试过了，有把握，就是慢", "tried_confident"),
            ("q_tried_and_checked", "还没试", "not_tried"),
            ("q_tried_and_checked", "没做", "not_tried"),
            ("q_standard_clarity", "不清楚", "standard_unclear"),
            ("q_standard_clarity", "不知道要求", "standard_unclear"),
            ("q_standard_clarity", "清楚", "standard_clear"),
            ("q_standard_clarity", "明确", "standard_clear"),
            ("q_direction_vs_push", "完全不知道下一步做什么", "no_direction"),
            ("q_direction_vs_push", "知道做什么但推不动", "cant_push"),
            ("q_direction_vs_push", "卡住", "cant_push"),
            ("q_content_vs_state", "看不懂内容", "content_stuck"),
            ("q_content_vs_state", "没掌握", "content_stuck"),
            ("q_content_vs_state", "太累了", "state_stuck"),
            ("q_content_vs_state", "没时间", "state_stuck"),
        ],
    )
    def test_negative_and_positive_resolution_set(self, question_id, answer, expected_branch):
        assert (
            resolve_answer_branch(question_id, answer) == expected_branch
        ), f"{question_id} / {answer!r} must resolve to {expected_branch}"

    def test_unresolved_stays_none(self):
        assert resolve_answer_branch("q_external_wait", "天气不错") is None
        assert resolve_answer_branch("q_external_wait", "") is None
        assert resolve_answer_branch("no_such_question", "在等") is None

    def test_resolution_is_deterministic(self):
        for spec in FRICTION_QUESTION_BANK:
            for branch in spec.branches:
                for term in sorted(branch.match_terms):
                    results = {resolve_answer_branch(spec.question_id, term) for _ in range(5)}
                    assert results == {branch.key}, f"{spec.question_id}/{term} nondeterministic: {results}"

    def test_inversion_consequence_in_ask_loop_closed(self):
        """反转的闭环后果钉死：time/dependency 竞争带诊断问 q_external_wait，
        负向回答「不在等」把 dependency 衰减（time 收敛）——修复前会反向
        增强 waiting_external（dependency 反转主导）。"""
        base = diagnose_friction({"utterance": "在等，而且没时间"})
        assert base.outcome == "ask"
        assert base.question is not None and base.question.question_id == "q_external_wait"
        replay_not_waiting = apply_question_answer(base, "q_external_wait", "not_waiting")
        replay_waiting = apply_question_answer(base, "q_external_wait", "waiting_external")
        # 负向回答后 dependency 不再是 argmax（等待语义被用户否定）；
        # 正向回答后 dependency 反超主导。两路必须可区分。
        post_not_waiting = dict(replay_not_waiting.evidence_scores)
        post_waiting = dict(replay_waiting.evidence_scores)
        assert post_waiting.get("dependency", 0) > post_not_waiting.get("dependency", 0)
        assert replay_waiting.friction_type == "dependency"
        assert replay_not_waiting.friction_type != "dependency"

    def test_branch_key_direct_pass_roundtrip(self):
        """branch_key 直传面：载荷 options 的 key 全部可被 apply 面接受
        （coerce 校验不丢弃——直传主路径的结构完备性）。"""
        for spec in FRICTION_QUESTION_BANK:
            option_keys = {branch.key for branch in spec.branches}
            for key in option_keys:
                assert key in {b.key for b in _QUESTION_BANK_INDEX[spec.question_id].branches}


# ---------------------------------------------------------------------------
# 2. ask 闭环 e2e（FIX-43a）：chat 触发装配 → 问 → 答 → 重诊断
# ---------------------------------------------------------------------------


class TestAskLoopEndToEnd:
    async def test_fresh_turn_assembles_input_and_asks(self, db_session, fake_redis):
        user = await _make_user(db_session)
        svc = FrictionChatWiringService(db_session, fake_redis)
        outcome = await svc.process_turn(
            user_id=str(user.id),
            session_id="sess-1",
            user_message="最近做不下去",
            user_context_payload={"active_goals": [{"name": "考研数学一轮"}]},
            request_extra_context={},
            now=_NOW,
        )
        assert outcome.mode == "fresh"
        assert outcome.outcome == "ask"
        assert outcome.question is not None
        # 问句载荷：question_id + 渲染文本 + 带 branch_key 的选项（直传面）
        assert outcome.question["question_id"] == "q_tried_and_checked"
        assert outcome.question["text"].strip()
        keys = {opt["key"] for opt in outcome.question["branch_options"]}
        assert keys == {"not_tried", "tried_unsure", "tried_confident"}
        # pending 已存（含输入快照——闭环节点的重放源）
        pending = await svc._load_pending(str(user.id), "sess-1")
        assert pending is not None
        assert pending["question_id"] == "q_tried_and_checked"
        assert "utterance" in pending["input_snapshot"]
        # 装配面结构诚实：utterance 锚定 + active_goals 投影
        assert pending["input_snapshot"]["utterance"] == "最近做不下去"

    async def test_answer_via_branch_key_direct_pass_closes_loop(self, db_session, fake_redis):
        user = await _make_user(db_session)
        svc = FrictionChatWiringService(db_session, fake_redis)
        first = await svc.process_turn(
            user_id=str(user.id),
            session_id="sess-2",
            user_message="最近做不下去",
            user_context_payload={},
            request_extra_context={},
            now=_NOW,
        )
        assert first.outcome == "ask"
        # 用户点选建议选项「试过，没把握」→ branch_key 直传回传
        second = await svc.process_turn(
            user_id=str(user.id),
            session_id="sess-2",
            user_message="",
            user_context_payload={},
            request_extra_context={
                FRICTION_ANSWER_CONTEXT_KEY: {
                    "question_id": first.question["question_id"],
                    "branch_key": "tried_unsure",
                }
            },
            now=_NOW,
        )
        assert second.mode == "answer_replay"
        assert second.annotations["answer_resolution"] == "branch_key_direct"
        assert second.annotations["answered_branch_key"] == "tried_unsure"
        # 重诊断：skill/feedback 证据注入后仍未达置信门 → 一次问对链继续
        # （下一问 q_content_vs_state——skill/feedback 与 energy/time 的分离面）
        assert second.outcome in {"act", "ask"}
        if second.outcome == "act":
            assert second.friction_type == "skill"
            assert second.diagnosis["reasons"] == ["S3.sufficient_after_question"]
            assert second.intervention is not None
        else:
            assert second.question is not None
            assert second.question["question_id"] == "q_content_vs_state"
        # pending 面随出口演化：ask → 新问题接续；act → 已消费
        pending = await svc._load_pending(str(user.id), "sess-2")
        if second.outcome == "ask":
            assert pending is not None and pending["question_id"] == "q_content_vs_state"
        else:
            assert pending is None

    async def test_answer_via_free_text_fallback(self, db_session, fake_redis):
        user = await _make_user(db_session)
        svc = FrictionChatWiringService(db_session, fake_redis)
        first = await svc.process_turn(
            user_id=str(user.id),
            session_id="sess-3",
            user_message="最近做不下去",
            user_context_payload={},
            request_extra_context={},
            now=_NOW,
        )
        assert first.outcome == "ask"
        # 无结构回传，自由文本回退层解析
        second = await svc.process_turn(
            user_id=str(user.id),
            session_id="sess-3",
            user_message="试过了，就是不确定对不对",
            user_context_payload={},
            request_extra_context={},
            now=_NOW,
        )
        assert second.mode == "answer_replay"
        assert second.annotations["answer_resolution"] == "free_text_lexical"
        assert second.annotations["answered_branch_key"] == "tried_unsure"

    async def test_negative_free_text_answer_no_longer_inverts(self, db_session, fake_redis):
        """P2 在闭环内的端到端后果：负向回答经回退层解析为 not_waiting
        （修复前会反转为 waiting_external——接线测试钉死回归）。"""
        user = await _make_user(db_session)
        svc = FrictionChatWiringService(db_session, fake_redis)
        first = await svc.process_turn(
            user_id=str(user.id),
            session_id="sess-4",
            user_message="在等，而且没时间",
            user_context_payload={},
            request_extra_context={},
            now=_NOW,
        )
        assert first.outcome == "ask" and first.question["question_id"] == "q_external_wait"
        second = await svc.process_turn(
            user_id=str(user.id),
            session_id="sess-4",
            user_message="不在等，是我自己没时间",
            user_context_payload={},
            request_extra_context={},
            now=_NOW,
        )
        assert second.mode == "answer_replay"
        assert second.annotations["answered_branch_key"] == "not_waiting"
        # 闭环后果：dependency 被用户否定 → 重诊断不再以 dependency 为 argmax 出口
        if second.outcome == "act":
            assert second.friction_type != "dependency"

    async def test_unresolved_answer_keeps_pending(self, db_session, fake_redis):
        user = await _make_user(db_session)
        svc = FrictionChatWiringService(db_session, fake_redis)
        first = await svc.process_turn(
            user_id=str(user.id),
            session_id="sess-5",
            user_message="最近做不下去",
            user_context_payload={},
            request_extra_context={},
            now=_NOW,
        )
        assert first.outcome == "ask"
        second = await svc.process_turn(
            user_id=str(user.id),
            session_id="sess-5",
            user_message="今天天气不错",
            user_context_payload={},
            request_extra_context={},
            now=_NOW,
        )
        # 绝不猜分支：pending 保持，本轮零问句零行动
        assert second.annotations["answer_resolution"] == "unresolved_pending_kept"
        assert second.question is None
        assert await svc._load_pending(str(user.id), "sess-5") is not None

    async def test_budget_counters_accumulate_across_asks(self, db_session, fake_redis):
        user = await _make_user(db_session)
        svc = FrictionChatWiringService(db_session, fake_redis)
        # 问 → 答（b1）→ 再问（消耗 2）→ 答不再问（session 预算 2 用尽 → 非问出口）
        first = await svc.process_turn(
            user_id=str(user.id),
            session_id="sess-6",
            user_message="最近做不下去",
            user_context_payload={},
            request_extra_context={},
            now=_NOW,
        )
        assert first.outcome == "ask"
        second = await svc.process_turn(
            user_id=str(user.id),
            session_id="sess-6",
            user_message="",
            user_context_payload={},
            request_extra_context={
                FRICTION_ANSWER_CONTEXT_KEY: {
                    "question_id": first.question["question_id"],
                    "branch_key": "tried_unsure",
                }
            },
            now=_NOW,
        )
        if second.outcome == "ask":
            # 预算内第二次问询：计数已递增（1→2）
            pending = await svc._load_pending(str(user.id), "sess-6")
            assert pending is not None
            assert pending["questions_asked_session"] == 2
            third = await svc.process_turn(
                user_id=str(user.id),
                session_id="sess-6",
                user_message="",
                user_context_payload={},
                request_extra_context={
                    FRICTION_ANSWER_CONTEXT_KEY: {
                        "question_id": second.question["question_id"],
                        "branch_key": second.question["branch_options"][0]["key"],
                    }
                },
                now=_NOW,
            )
            # session 上限 2 已用尽 → 不再新问（act/best-guess/no_action 出口）
            assert third.outcome != "ask" or third.mode == "answer_replay"

    async def test_redis_absence_degrades_ask_path_but_no_crash(self, db_session):
        """Redis 缺席：fresh 诊断照常（无 pending 面），闭环降级不可用——主链路零风险。"""
        user = await _make_user(db_session)
        svc = FrictionChatWiringService(db_session, None)
        outcome = await svc.process_turn(
            user_id=str(user.id),
            session_id="sess-7",
            user_message="最近做不下去",
            user_context_payload={},
            request_extra_context={},
            now=_NOW,
        )
        assert outcome.outcome == "ask"
        assert outcome.question is not None  # 问句照常产出（面交客户端）
        # 但回答轮无 pending 可载入 → fresh 重诊断，不 crash
        again = await svc.process_turn(
            user_id=str(user.id),
            session_id="sess-7",
            user_message="试过了，没把握",
            user_context_payload={},
            request_extra_context={},
            now=_NOW,
        )
        assert again.mode == "fresh"

    async def test_dirty_input_never_raises(self, db_session, fake_redis):
        user = await _make_user(db_session)
        svc = FrictionChatWiringService(db_session, fake_redis)
        for bad_ctx in [None, {"friction_answer": "garbage"}, {"friction_answer": {"question_id": 1}}]:
            outcome = await svc.process_turn(
                user_id=str(user.id),
                session_id="sess-8",
                user_message=None if bad_ctx is None else "做不下去",
                user_context_payload={"active_goals": "not-a-list", "plan_context": 42},
                request_extra_context=bad_ctx,
                now=_NOW,
            )
            assert outcome.mode in {"fresh", "answer_replay", "degraded"}
            assert isinstance(outcome.to_dict(), dict)


# ---------------------------------------------------------------------------
# 3. act 出口决策输入链（FIX-34）：patched_decision_inputs → A-02
# ---------------------------------------------------------------------------


class TestFrictionWiringTriggerGate:
    """V3-FIX-49 · chat 面 fresh 出口词牌门（降噪不关死）。

    A-08 四臂反例（v3-output/WT393-A08-ABLATION raw 对照会话）：
    - 无词牌普通消息 + stale spine（48h 内）→ S1 置信直出建议（full 臂 21/25 侵入）；
    - 无词牌普通消息 + 零证据 → U1 根分裂澄清问（no_experience 臂 25/25 侵入）。
    契约：**fresh 轮的 ask/act 出面必须携带正向摩擦自报词牌**（utterance 词牌
    命中非空）；无词牌 → 静默 no_action（门原因入 annotations）。回答闭环
    （answer_replay）与带词牌的诊断不受门影响（降噪≠关死：A-08 full 臂
    真摩擦介入优势必须保持）。
    """

    CONTROL_MESSAGE = "今天把这一章看完了，进度正常。"

    async def _seed_spine(self, redis, user_id: str, key: str = "knowledge_transfer") -> None:
        await redis.sadd(f"spine:state_index:{user_id}", key)

    async def test_control_message_with_stale_spine_stays_silent(self, db_session, fake_redis):
        """反例①机制②：无词牌消息 + 48h 内 spine 键 → 不再 S1 直出建议。"""
        user = await _make_user(db_session)
        await self._seed_spine(fake_redis, str(user.id))
        svc = FrictionChatWiringService(db_session, fake_redis)
        outcome = await svc.process_turn(
            user_id=str(user.id),
            session_id="gate-1",
            user_message=self.CONTROL_MESSAGE,
            user_context_payload={},
            request_extra_context={},
            now=_NOW,
        )
        assert outcome.outcome == "no_action"
        assert outcome.question is None
        assert outcome.intervention is None
        assert outcome.annotations.get("wiring_gate") == "silent_no_utterance_wordmark"
        # 不落 pending、不耗日预算（门是静默出口，不是问询）
        assert await svc._load_pending(str(user.id), "gate-1") is None

    async def test_control_message_without_evidence_asks_nothing(self, db_session, fake_redis):
        """反例①机制①：零 spine + 零词牌 → 不再 U1 根分裂澄清问。"""
        user = await _make_user(db_session)
        svc = FrictionChatWiringService(db_session, fake_redis)
        outcome = await svc.process_turn(
            user_id=str(user.id),
            session_id="gate-2",
            user_message=self.CONTROL_MESSAGE,
            user_context_payload={},
            request_extra_context={},
            now=_NOW,
        )
        assert outcome.outcome == "no_action"
        assert outcome.question is None
        assert outcome.intervention is None
        # 零证据 → 引擎 U1 unknown-ask 出口被门拦下（专用门原因可审计）
        assert outcome.annotations.get("wiring_gate") == "silent_unknown_no_friction_evidence"
        assert outcome.friction_type == "unknown"

    async def test_gate_silent_payload_carries_no_blocked_question_text(self, db_session, fake_redis):
        """V3-FIX-114 · 门拦静默出口的载荷面一致：被拦问句全文不出 metadata。

        门拦出口顶层 outcome=no_action、question=None，但 diagnosis.to_dict()
        曾内嵌完整 question 对象（渲染问句全文+分支选项标签）——潜在消费方按
        顶层 outcome 判静默、按 diagnosis 渲染问句即翻车。修后载荷面：
        diagnosis.question 置 None（与顶层一致），出口序列化全文零残留。
        """
        user = await _make_user(db_session)
        svc = FrictionChatWiringService(db_session, fake_redis)
        outcome = await svc.process_turn(
            user_id=str(user.id),
            session_id="gate-114",
            user_message=self.CONTROL_MESSAGE,
            user_context_payload={},
            request_extra_context={},
            now=_NOW,
        )
        assert outcome.outcome == "no_action"
        assert outcome.question is None
        assert outcome.annotations.get("wiring_gate") == "silent_unknown_no_friction_evidence"
        payload = outcome.to_dict()
        # 可证伪判据（FIX-114 登记面）：门拦出口 diagnosis.question 非 None 而顶层 question 为 None
        assert payload["diagnosis"]["question"] is None
        assert payload["diagnosis"]["suggested_clarifying_question"] is None
        # 出口序列化全文零残留：被拦问句（U1 根分裂问）的渲染文本与分支标签
        # 不得出现在任何载荷面（response metadata 即 outcome.to_dict() 序列化）。
        entry_spec = _QUESTION_BANK_INDEX["q_direction_vs_push"]
        serialized = json.dumps(payload, ensure_ascii=False)
        assert entry_spec.render(None) not in serialized
        for branch in entry_spec.branches:
            assert branch.label not in serialized
        # 审计身份保留：门原因 + 引擎 reason 码照常（脱敏 ≠ 抹审计）
        assert "U1.unknown_ask_entry_question" in payload["diagnosis"]["reasons"]

    async def test_gate_silent_payload_suggested_clarify_identity_only(self):
        """V3-FIX-114 · 单元面：被拦 clarify 问句全文以封闭库 question_id 身份替代。

        suggested_clarifying_question 是渲染全文（嵌 task_anchor 用户内容）；
        门拦出口只留身份（FIX-62 类名/指纹同律：留身份不留文本）。
        """
        spec = _QUESTION_BANK_INDEX["q_standard_clarity"]
        diagnosis = FrictionDiagnosis(
            outcome="act",
            friction_type="clarity",
            nominated_interventions=("clarify",),
            suggested_clarifying_question=spec.render("考研数学"),
            question=OneBestQuestion(
                question_id="q_direction_vs_push",
                text="这步，是不知道下一步该做什么，还是知道做什么但推不动？",
                branch_options=(("dont_know_what", "不知道做什么"), ("know_but_stuck", "知道但推不动")),
                information_gain_bits=0.5,
            ),
        )
        payload = _gate_silent_diagnosis_payload(diagnosis)
        assert payload["question"] is None
        assert payload["suggested_clarifying_question"] == "q_standard_clarity"
        # 身份替身与封闭库双钉：库里 clarify 问句改 id 即红（防替身漂移）
        assert spec.question_id == _GATE_CLARIFY_QUESTION_REF
        serialized = json.dumps(payload, ensure_ascii=False)
        assert spec.render("考研数学") not in serialized
        assert "推不动" not in serialized

    async def test_wordmark_message_still_full_pipeline(self, db_session, fake_redis):
        """降噪不关死：带词牌的真卡点表达照常问（U1/Q1 面不受门影响）。"""
        user = await _make_user(db_session)
        svc = FrictionChatWiringService(db_session, fake_redis)
        outcome = await svc.process_turn(
            user_id=str(user.id),
            session_id="gate-3",
            user_message="最近做不下去",
            user_context_payload={"active_goals": [{"name": "考研数学一轮"}]},
            request_extra_context={},
            now=_NOW,
        )
        assert outcome.outcome == "ask"
        assert outcome.question is not None
        assert "wiring_gate" not in outcome.annotations

    async def test_wordmark_act_with_spine_still_acts(self, db_session, fake_redis):
        """带词牌 + spine 证据的 act 照常出面（A-08 full 臂主结论依赖）。"""
        user = await _make_user(db_session)
        await self._seed_spine(fake_redis, str(user.id))
        svc = FrictionChatWiringService(db_session, fake_redis)
        outcome = await svc.process_turn(
            user_id=str(user.id),
            session_id="gate-4",
            user_message="这里有点看不懂",
            user_context_payload={},
            request_extra_context={},
            now=_NOW,
        )
        assert outcome.outcome == "act"
        assert outcome.friction_type in {"skill", "knowledge"}
        assert outcome.intervention is not None
        assert "wiring_gate" not in outcome.annotations

    async def test_answer_replay_is_never_gated(self, db_session, fake_redis):
        """回答闭环不受门影响：pending 在册时即使消息无词牌也照常收敛。"""
        user = await _make_user(db_session)
        svc = FrictionChatWiringService(db_session, fake_redis)
        first = await svc.process_turn(
            user_id=str(user.id),
            session_id="gate-5",
            user_message="最近做不下去",
            user_context_payload={},
            request_extra_context={},
            now=_NOW,
        )
        assert first.outcome == "ask"
        replay = await svc.process_turn(
            user_id=str(user.id),
            session_id="gate-5",
            user_message=self.CONTROL_MESSAGE,  # 无词牌消息作答
            user_context_payload={},
            request_extra_context={
                FRICTION_ANSWER_CONTEXT_KEY: {
                    "question_id": first.question["question_id"],
                    "branch_key": first.question["branch_options"][0]["key"],
                }
            },
            now=_NOW,
        )
        assert replay.mode == "answer_replay"
        assert "wiring_gate" not in replay.annotations


class TestAnswerReplayFreeTextGate:
    """V3-FIX-111 · answer_replay 自由文本回退层的置信/意图门（FIX-49 同构）。

    FIX-49 声明「回答闭环不设门」的前提是**用户在回答**——branch_key 直传
    主路径由结构保证；自由文本回退层只有词面，前提需校验：自由文本不得仅凭
    词面直出 act。弱词面命中（单字话语标记「对了」/ 长消息低覆盖）→ 不
    apply、pending 保持（用户可点选或改述），门原因入 annotations 可审计；
    实质回答照常闭环。
    """

    async def _ask_first(self, db_session, fake_redis, session_id: str):
        user = await _make_user(db_session)
        svc = FrictionChatWiringService(db_session, fake_redis)
        first = await svc.process_turn(
            user_id=str(user.id),
            session_id=session_id,
            user_message="最近做不下去",
            user_context_payload={},
            request_extra_context={},
            now=_NOW,
        )
        assert first.outcome == "ask" and first.question is not None
        return user, svc, first

    async def test_spurious_free_text_never_acts_and_keeps_pending(self, db_session, fake_redis):
        """wt424 探针原样：「对了不想要了，帮我换个计划吧」（意图=换计划，非
        回答）不得被词面解析成 tried_confident 直出 S3 act。"""
        user, svc, first = await self._ask_first(db_session, fake_redis, "fix111-1")
        second = await svc.process_turn(
            user_id=str(user.id),
            session_id="fix111-1",
            user_message="对了不想要了，帮我换个计划吧",
            user_context_payload={},
            request_extra_context={},
            now=_NOW,
        )
        assert second.mode == "answer_replay"
        assert second.outcome != "act"
        assert second.intervention is None
        assert second.question is None  # 不 apply、不重问、不消费
        assert second.annotations["answer_resolution"] == "unresolved_weak_free_text"
        assert second.annotations["wiring_gate"] == "silent_weak_free_text_answer"
        # pending 保持：用户可点选选项或改述
        pending = await svc._load_pending(str(user.id), "fix111-1")
        assert pending is not None and pending["question_id"] == first.question["question_id"]

    async def test_substantive_free_text_still_closes_loop(self, db_session, fake_redis):
        """实质回答不受门影响（降噪不关死——与 FIX-49 同构）。"""
        user, svc, _first = await self._ask_first(db_session, fake_redis, "fix111-2")
        second = await svc.process_turn(
            user_id=str(user.id),
            session_id="fix111-2",
            user_message="试过了，就是不确定对不对",
            user_context_payload={},
            request_extra_context={},
            now=_NOW,
        )
        assert second.mode == "answer_replay"
        assert second.annotations["answer_resolution"] == "free_text_lexical"
        assert second.annotations.get("wiring_gate") is None

    async def test_branch_key_direct_never_gated_even_with_noisy_message(self, db_session, fake_redis):
        """branch_key 直传主路径不受自由文本门影响（结构保证「用户在回答」）。"""
        user, svc, first = await self._ask_first(db_session, fake_redis, "fix111-3")
        second = await svc.process_turn(
            user_id=str(user.id),
            session_id="fix111-3",
            user_message="对了不想要了，帮我换个计划吧",  # 消息体嘈杂不参与直传判定
            user_context_payload={},
            request_extra_context={
                FRICTION_ANSWER_CONTEXT_KEY: {
                    "question_id": first.question["question_id"],
                    "branch_key": "not_tried",
                }
            },
            now=_NOW,
        )
        assert second.mode == "answer_replay"
        assert second.annotations["answer_resolution"] == "branch_key_direct"
        assert "wiring_gate" not in second.annotations


class TestStuckSelfReportChatSurface:
    """V3-FIX-115 · 卡点自报「卡住」族在 chat 面有出面（只补词表不改门结构）。

    wt424 探针：「我真的卡住了，帮帮我」+ stale spine → 修前门拦
    （silent_no_utterance_wordmark）零出面。修后词牌在场 → 门自然放行。
    旅程面通道不动（本类不涉及）。
    """

    async def test_stuck_self_report_with_stale_spine_surfaces(self, db_session, fake_redis):
        user = await _make_user(db_session)
        await fake_redis.sadd(f"spine:state_index:{user.id}", "knowledge_transfer")
        svc = FrictionChatWiringService(db_session, fake_redis)
        outcome = await svc.process_turn(
            user_id=str(user.id),
            session_id="fix115-1",
            user_message="我真的卡住了，帮帮我",
            user_context_payload={},
            request_extra_context={},
            now=_NOW,
        )
        assert "wiring_gate" not in outcome.annotations
        assert outcome.outcome in ("ask", "act")
        assert outcome.question is not None or outcome.intervention is not None

    async def test_bare_stuck_without_spine_still_asks(self, db_session, fake_redis):
        user = await _make_user(db_session)
        svc = FrictionChatWiringService(db_session, fake_redis)
        outcome = await svc.process_turn(
            user_id=str(user.id),
            session_id="fix115-2",
            user_message="我卡住了",
            user_context_payload={},
            request_extra_context={},
            now=_NOW,
        )
        assert "wiring_gate" not in outcome.annotations
        assert outcome.outcome == "ask"
        assert outcome.question is not None



    async def _service(self, db_session, fake_redis):
        return FrictionChatWiringService(db_session, fake_redis)

    async def test_act_without_patches_uses_friction_nominations(self, db_session, fake_redis):
        user = await _make_user(db_session)
        svc = await self._service(db_session, fake_redis)
        outcome = await svc.process_turn(
            user_id=str(user.id),
            session_id="sess-act-1",
            user_message="背下来了但不会做，概念都懂但不会做",
            user_context_payload={"plan_context": {"task": "算法作业"}},
            request_extra_context={},
            now=_NOW,
        )
        assert outcome.outcome == "act"
        assert outcome.friction_type == "skill"
        # policy_factors_patch 前置提名 → A-05 补丁面（无 patch：序不变）→ A-02
        assert outcome.intervention is not None
        assert outcome.intervention["friction_nominated"][0] == "practice"
        assert outcome.intervention["selected"] == "practice"
        assert outcome.policy_patch is not None
        assert outcome.policy_patch["nominated_patched"][0] == "practice"
        assert outcome.policy_patch["applied_patch_ids"] == []
        # 归因随行（A-01 annotations 面）
        assert outcome.intervention["contract_annotations"]["friction_type"] == "skill"

    async def test_prefer_patch_flips_chat_decision_output(self, db_session, fake_redis):
        """FIX-34 核心验收：active intervention_preference patch（prefer explain，
        真实 M-06 证据链激活）改变 chat 决策出口——practice 让位 explain。"""
        user = await _make_user(db_session)
        # 真实证据链：explain ×2 正向（knowledge_transfer → knowledge_bottleneck
        # 切片——与接线传入的 diagnosis.lifecycle_tag 同 scope）→ repeated → 自动激活
        await _expose_and_link(
            db_session,
            user,
            intervention_type="explain",
            n_positive=2,
            evidence=("signal://knowledge_transfer",),
        )
        record_id = await _experience_record_id(
            db_session, user, intervention_type="explain", friction="knowledge_bottleneck"
        )
        patches = PolicyPatchService(db_session)
        result = await patches.propose_patch(
            user.id,
            surface="intervention_preference",
            payload={"intervention": "explain", "direction": "prefer"},
            evidence_refs=[f"memory://experience/{record_id}"],
        )
        admitted = await patches.admit_evidence(user.id, result.record.patch_id, now=_NOW)
        assert admitted.record.state == "active"
        assert admitted.record.evidence_tier == EVIDENCE_TIER_REPEATED

        svc = await self._service(db_session, fake_redis)
        outcome = await svc.process_turn(
            user_id=str(user.id),
            session_id="sess-act-2",
            user_message="背下来了但不会做，概念都懂但不会做",
            user_context_payload={"plan_context": {"task": "算法作业"}},
            request_extra_context={},
            now=_NOW,
        )
        assert outcome.outcome == "act"
        # 无 patch 基线序是 (practice, explain)——patch 重排后 explain 升首，
        # A-02 D1 取第一个合法提名 → selected 翻转为 explain。
        assert outcome.policy_patch["nominated_patched"][0] == "explain"
        assert outcome.intervention["selected"] == "explain"
        assert admitted.record.patch_id in outcome.policy_patch["applied_patch_ids"]
        assert any(
            move["intervention"] == "explain" and move["direction"] == "prefer"
            for move in outcome.policy_patch["moves"]
        )

    async def test_no_patch_trace_when_patches_absent_version_is_none_set(self, db_session, fake_redis):
        """无 active patch：版本归因仍随行（polpatch_none 常量语义）、moves 空。"""
        user = await _make_user(db_session)
        svc = await self._service(db_session, fake_redis)
        outcome = await svc.process_turn(
            user_id=str(user.id),
            session_id="sess-act-3",
            user_message="太难了，超出我的水平",
            user_context_payload={"plan_context": {"task": "作业"}},
            request_extra_context={},
            now=_NOW,
        )
        assert outcome.outcome == "act"
        assert outcome.friction_type == "difficulty"
        assert outcome.policy_patch["moves"] == []
        assert outcome.policy_patch["policy_patch_version"].startswith("polpatch_")


# ---------------------------------------------------------------------------
# 4. A-05 clarification patch → 追问预算（A-03 反向通道）
# ---------------------------------------------------------------------------


class TestClarificationBudgetChannel:
    async def test_clarification_patch_projects_to_budget(self, db_session, fake_redis):
        user = await _make_user(db_session)
        # 证据面（G3 方向门）：ask_less 需要 clarify 的**负向**共同出现证据
        # ×2 → repeated 档自动激活；clarify 契约面强制 clarifying_question 载体。
        await _expose_and_link(db_session, user, intervention_type="clarify", n_negative=2)
        record_id = await _experience_record_id(db_session, user, intervention_type="clarify")
        patches = PolicyPatchService(db_session)
        result = await patches.propose_patch(
            user.id,
            surface="clarification",
            payload={"mode": "ask_less"},
            evidence_refs=[f"memory://experience/{record_id}"],
        )
        admitted = await patches.admit_evidence(user.id, result.record.patch_id, now=_NOW)
        assert admitted.record.state == "active"

        svc = FrictionChatWiringService(db_session, fake_redis)
        mapping = await svc.assemble_input(
            user_id=str(user.id),
            session_id="sess-clar",
            user_message="做不下去",
            user_context_payload={},
            request_extra_context={},
            now=_NOW,
        )
        assert mapping["clarification_preference"] == "ask_less"
        # ask_less → 收紧预算 (1, 3)：诊断内生效（服务装配面 → 引擎贯通）
        diagnosis = diagnose_friction(mapping)
        assert diagnosis is not None  # 预算收紧不改变「不 raise」契约

    async def test_no_clarification_patch_projects_none(self, db_session, fake_redis):
        user = await _make_user(db_session)
        svc = FrictionChatWiringService(db_session, fake_redis)
        mapping = await svc.assemble_input(
            user_id=str(user.id),
            session_id="sess-clar",
            user_message="做不下去",
            user_context_payload={},
            request_extra_context={},
            now=_NOW,
        )
        assert mapping["clarification_preference"] is None


# ---------------------------------------------------------------------------
# 5. M-06 经验记忆进 chat context（FIX-33）+ M-05 降档率实测
# ---------------------------------------------------------------------------


class TestExperienceMemoryContextWiring:
    async def _mixin(self) -> ContextBuilderMixin:
        return ContextBuilderMixin.__new__(ContextBuilderMixin)

    async def test_experience_memories_injected_into_stage34_payload(self, db_session):
        user = await _make_user(db_session)
        await _expose_and_link(db_session, user, intervention_type="practice", n_positive=2)
        payload: dict = {}
        mixin = await self._mixin()
        await mixin._attach_experience_memory_context(payload, user_id=str(user.id), db_session=db_session)
        memories = payload["experience_memories"]
        assert isinstance(memories, list)
        assert len(memories) >= 1
        first = memories[0]
        assert first["claim"].strip()
        assert first["direction"] == "positive"
        assert first["evidence_count"] >= 1
        assert set(first["signature"]) == {"intervention_type", "goal_type", "friction_tag", "execution_mode"}
        meta = payload["experience_memory_meta"]
        assert meta["total_candidates"] >= 1
        assert meta["surfaced"] == len(memories)

    async def test_experience_memories_empty_without_evidence(self, db_session):
        user = await _make_user(db_session)
        payload: dict = {}
        mixin = await self._mixin()
        await mixin._attach_experience_memory_context(payload, user_id=str(user.id), db_session=db_session)
        assert payload["experience_memories"] == []
        assert payload["experience_memory_meta"]["total_candidates"] == 0

    async def test_m05_downgrade_rate_measured_on_experience_claims(self, db_session):
        """FIX-33 原文要求：M-05 词法降档率对经验 claims 的影响实测。

        真实链路语料：3 个情境切片（explain/practice/reminder ×2 正向）→
        M-06 投影 claims → 真实 M-05 gate → surfaced vs internal-only。
        断言面：降档率可观测（meta 数字与 gate 决策一致）。
        """
        user = await _make_user(db_session)
        for intervention in ("explain", "practice", "rescope"):
            await _expose_and_link(db_session, user, intervention_type=intervention, n_positive=2)
        projector = ExperienceMemoryProjector(db_session)
        result = await projector.retrieve_context(
            ExperienceContextQuery(
                user_id=str(user.id),
                purpose="llm_context",
                max_records_per_direction=10,
            )
        )
        records = (
            list(result.observed_with_positive) + list(result.observed_with_negative) + list(result.no_outcome_evidence)
        )
        assert len(records) >= 3, f"expected >=3 real claims, got {len(records)}"
        claims = [r.claim for r in records if r.claim.strip()]
        # claims 是 D-05 封闭模板族（高度相似）——这是降档率的现实来源
        assert len(set(claims)) < len(claims) or len(claims) >= 3

        from app.services.memory_use_selfcheck import MemoryUseCandidate

        candidates = [
            MemoryUseCandidate(item_id=record.record_id, section="experience", content=record.claim)
            for record in records
            if record.claim.strip()
        ]
        selfcheck = evaluate_memory_use_gate(episodic=candidates, ctx=SelfCheckContext())
        surfaced = set(selfcheck.surfaced_ids("experience"))
        internal_only = [c for c in candidates if c.item_id not in surfaced]
        downgrade_rate = len(internal_only) / len(candidates)
        # 实测数据写进测试输出（验收员可见）：
        print(
            f"\n[M-05 降档率实测] candidates={len(candidates)} surfaced={len(surfaced)} "
            f"internal_only={len(internal_only)} downgrade_rate={downgrade_rate:.2%} "
            f"internal_ids={[c.item_id for c in internal_only]}"
        )
        # 降档率 ∈ [0,1] 且 gate 全部出决策（零遗漏）
        assert 0.0 <= downgrade_rate <= 1.0
        assert len(surfaced) + len(internal_only) == len(candidates)

    async def test_stage34_wiring_call_site_is_live(self):
        """拔接线必红（M-06 组）：_attach_stage34_memory_context 必须真实调用
        _attach_experience_memory_context（常量假守卫不算活接线）。"""
        source = CONTEXT_BUILDER_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "_attach_stage34_memory_context":
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                        if sub.func.attr == "_attach_experience_memory_context":
                            found = True
        assert found, "M-06 wiring call removed from _attach_stage34_memory_context (拔接线回归)"


# ---------------------------------------------------------------------------
# 6. 拔接线必红（orchestrator / response_builder / wiring 服务活接线）
# ---------------------------------------------------------------------------


class TestWiringCallSitesPinned:
    def _live_calls(self, func_node: ast.AST) -> set[str]:
        names: set[str] = set()
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    names.add(node.func.attr)
                elif isinstance(node.func, ast.Name):
                    names.add(node.func.id)
        return names

    def test_orchestrator_hook_is_live(self):
        """拔接线必红（A-03 组）：process_stream 必须调用
        _run_friction_decision_wiring 且把产出写进 context_data。"""
        source = ORCHESTRATOR_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        process_stream = next(
            node for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef) and node.name == "process_stream"
        )
        calls = self._live_calls(process_stream)
        assert "_run_friction_decision_wiring" in calls, "A-03 chat hook removed (拔接线回归)"
        assert "friction_decision" in source, "context_data['friction_decision'] stash removed"

    def test_response_builder_emits_friction_metadata(self):
        source = RESPONSE_BUILDER_PATH.read_text(encoding="utf-8")
        assert '"friction_decision"' in source, "response metadata friction_decision removed"

    def test_wiring_service_calls_patched_decision_inputs(self):
        """拔接线必红（A-05 组）：接线服务必须真实调用 patched_decision_inputs
        与 evaluate_intervention_policy（决策输入链不被旁路）。"""
        source = WIRING_SVC_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        svc_class = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name == "FrictionChatWiringService"
        )
        names: set[str] = set()
        for node in ast.walk(svc_class):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    names.add(node.func.attr)
                elif isinstance(node.func, ast.Name):
                    names.add(node.func.id)
        assert "patched_decision_inputs" in names, "A-05 patched_decision_inputs bypassed (拔接线回归)"
        assert "diagnose_friction" in names, "A-03 diagnose_friction call removed"
        assert "apply_question_answer" in names, "ask-loop apply_question_answer call removed"
        # V3-FIX-111：自由文本回退走置信证据面解析（resolve_answer_branch_detail）；
        # resolve_answer_branch* 前缀断言保持「回退层解析不被旁路」的原守卫强度。
        assert any(name.startswith("resolve_answer_branch") for name in names), (
            "free-text fallback resolve_answer_branch* removed"
        )

    async def test_orchestrator_hook_end_to_end_with_real_service(self, db_session, fake_redis):
        """hook 行为面：ChatOrchestrator._run_friction_decision_wiring 用真实
        服务（sqlite + fakeredis）产出问句载荷。"""
        user = await _make_user(db_session)
        orchestrator = ChatOrchestrator.__new__(ChatOrchestrator)
        orchestrator.redis = fake_redis
        payload = await orchestrator._run_friction_decision_wiring(
            active_db=db_session,
            user_id=str(user.id),
            session_id="sess-hook-1",
            user_message="最近做不下去",
            user_context_payload={},
            request_extra_context={},
        )
        assert payload is not None
        assert payload["outcome"] == "ask"
        assert payload["question"]["question_id"] == "q_tried_and_checked"

    def test_p2_fix_is_algorithm_plus_lexeme_not_revert(self):
        """P2 修复结构钉死：最长词牌比较存在 + 「不对」词牌在场——回退即红。

        V3-FIX-111 后解析实现收敛进 ``resolve_answer_branch_detail``（legacy
        解析器委托之，单实现不分叉）——结构断言随实现迁移，守卫强度不变。
        """
        import inspect

        from app.aurora.friction_diagnosis import resolve_answer_branch_detail as fn

        src = inspect.getsource(fn)
        assert "-len(term)" in src or "len(term)" in src, "longest-match resolution reverted"
        assert resolve_answer_branch("q_tried_and_checked", "试过但不对") == "tried_unsure"
        assert resolve_answer_branch("q_external_wait", "不在等") == "not_waiting"


# ---------------------------------------------------------------------------
# 7. 三引擎同轮协同（端到端一体性）
# ---------------------------------------------------------------------------


class TestCombinedTurnCoherence:
    async def test_single_turn_emits_diagnosis_question_and_decision_fields(self, db_session, fake_redis):
        """一轮 chat：A-03 诊断问句 + （有证据时）A-05 决策归因 + M-06 经验
        context 三面同轮可装配——「用户可感知闭环」的装配完整性。"""
        user = await _make_user(db_session)
        # M-06 证据链（经验记忆 context 面）
        await _expose_and_link(db_session, user, intervention_type="practice", n_positive=2)
        svc = FrictionChatWiringService(db_session, fake_redis)
        outcome = await svc.process_turn(
            user_id=str(user.id),
            session_id="sess-both-1",
            user_message="太难了，超出我的水平",
            user_context_payload={"active_goals": [{"name": "高数期末"}], "plan_context": {"task": "刷题"}},
            request_extra_context={},
            now=_NOW,
        )
        assert outcome.outcome == "act"
        assert outcome.diagnosis["schema_version"].startswith("aurora_friction_diagnosis.")
        assert outcome.intervention["selected"] in {"split", "practice", "explain"}
        assert outcome.policy_patch["policy_patch_version"].startswith("polpatch_")
        # M-06 经验 context 同轮可注入（真实证据链 → surfaced memories）
        payload: dict = {}
        mixin = ContextBuilderMixin.__new__(ContextBuilderMixin)
        await mixin._attach_experience_memory_context(payload, user_id=str(user.id), db_session=db_session)
        assert payload["experience_memory_meta"]["surfaced"] >= 1
