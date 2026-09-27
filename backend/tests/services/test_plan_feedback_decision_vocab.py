"""V3-FIX-355: PlanFeedback.decision 四套词汇归一回归测试。

历史缺陷（wt658 盘点亲证）：
- 声明 Literal["accept","reject","supplement"]（schemas.py）
- docstring 宣称 approve/reject/modify（plan_feedback_service）
- gRPC 实写 ReviewDecision 四值 approved/rejected/needs_modification/requires_confirmation
  （agent_grpc_service decision_map → update_feedback_decision / append_user_feedback）
- workflow 路由消费 modify/reject（agents/graph/workflow.py，独立 LangGraph 通道）

后果：get_pending_feedback 过滤 `in ["reject","supplement"]` 与实写值零交集——
用户拒绝写 "rejected" 永不进 pending；`== "reject"/"approve"` 升级与重置分支恒假死码。

裁决：以 ReviewDecision 四值为规范词表；写侧入口归一（别名收编），读侧别名归一
兼容存量 accept/supplement 行；proto wire 契约不动。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import Base
from app.models.plan_state import PlanState
from app.orchestration.plan_review_service import PlanReviewService, ReviewDecision
from app.orchestration.schemas import PlanFeedback, normalize_plan_feedback_decision
from app.services.plan_feedback_service import PlanFeedbackService
from app.services.plan_state_service import PlanStateService

CANONICAL_DECISIONS = (
    ReviewDecision.APPROVED.value,
    ReviewDecision.REJECTED.value,
    ReviewDecision.NEEDS_MODIFICATION.value,
    ReviewDecision.REQUIRES_CONFIRMATION.value,
)


@pytest.fixture
async def sqlite_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    tables = [Base.metadata.tables["plan_states"]]
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


async def _reload(session: AsyncSession, state: PlanState) -> PlanState:
    plan_id = state.plan_id
    session.expire_all()
    result = await session.execute(select(PlanState).where(PlanState.plan_id == plan_id))
    return result.scalar_one()


async def _seed_review_entry(
    sqlite_session: AsyncSession,
    user_id: UUID,
    plan_id: UUID,
    review_id: str,
    decision: str,
    priority: str = "normal",
) -> None:
    """按 append_review_feedback 的真实条目形态种一条 review 反馈。"""
    state_service = PlanStateService(sqlite_session, redis=None)
    await state_service.get_or_create_plan_state(user_id, plan_id)
    await state_service.append_feedback(
        user_id=user_id,
        plan_id=plan_id,
        feedback_type="review",
        content=f"Plan review completed: {decision}",
        applied_adjustment={
            "decision": decision,
            "priority": priority,
            "review_id": review_id,
        },
    )


# ===========================================================================
# 归一函数：四套词汇 → 规范词表（参数化钉死）
# ===========================================================================


class TestNormalizePlanFeedbackDecision:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            # 规范词表（ReviewDecision 四值）——幂等
            ("approved", "approved"),
            ("rejected", "rejected"),
            ("needs_modification", "needs_modification"),
            ("requires_confirmation", "requires_confirmation"),
            # 声明 Literal 词汇（schemas 旧词表，存量 feedback_log 行）
            ("accept", "approved"),
            ("supplement", "needs_modification"),
            # docstring 词汇（approve/reject/modify）
            ("approve", "approved"),
            ("reject", "rejected"),
            ("modify", "needs_modification"),
            # proto ACKNOWLEDGE 语义
            ("acknowledge", "requires_confirmation"),
            # 大小写与空白容错
            ("  Rejected  ", "rejected"),
            ("APPROVED", "approved"),
        ],
    )
    def test_maps_every_vocabulary_to_canonical(self, raw, expected):
        assert normalize_plan_feedback_decision(raw) == expected

    @pytest.mark.parametrize("canonical", CANONICAL_DECISIONS)
    def test_idempotent_on_canonical(self, canonical):
        assert normalize_plan_feedback_decision(canonical) == canonical

    def test_unknown_falls_back_to_requires_confirmation(self):
        # 与 plan_review_service._map_quality_gate_decision 的未知值惯例一致
        assert normalize_plan_feedback_decision("totally_unknown") == "requires_confirmation"

    def test_all_canonical_values_are_valid(self):
        for value in CANONICAL_DECISIONS:
            assert normalize_plan_feedback_decision(value) in CANONICAL_DECISIONS


# ===========================================================================
# get_pending_feedback：用户决策必须可见（修前红）
# ===========================================================================


class TestPendingFeedbackVisibility:
    @pytest.mark.asyncio
    async def test_rejected_user_decision_enters_pending(self, sqlite_session):
        """gRPC 实写 "rejected" 的用户决策必须进 pending（V3-FIX-355 主红测）。"""
        user_id, plan_id = uuid4(), uuid4()
        await _seed_review_entry(sqlite_session, user_id, plan_id, "rev-1", "pending")

        service = PlanFeedbackService(sqlite_session, redis=None)
        await service.update_feedback_decision(
            user_id=user_id, plan_id=plan_id, review_id="rev-1", user_decision="rejected"
        )

        pending = await service.get_pending_feedback(user_id, plan_id)
        assert len(pending) == 1, f"用户 rejected 决策丢失于 pending: {pending}"
        assert pending[0]["applied_adjustment"]["decision"] == "rejected"

    @pytest.mark.parametrize(
        ("decision", "should_be_pending"),
        [
            ("rejected", True),
            ("needs_modification", True),
            ("requires_confirmation", True),
            ("approved", False),
        ],
    )
    @pytest.mark.asyncio
    async def test_canonical_decisions_pending_membership(
        self, sqlite_session, decision, should_be_pending
    ):
        user_id, plan_id = uuid4(), uuid4()
        service = PlanFeedbackService(sqlite_session, redis=None)
        await service.append_user_feedback(
            user_id=user_id,
            plan_id=plan_id,
            content=f"decision: {decision}",
            decision=decision,
        )

        pending = await service.get_pending_feedback(user_id, plan_id)
        if should_be_pending:
            assert len(pending) == 1, f"{decision} 应为 pending，实际: {pending}"
        else:
            assert pending == [], f"{decision} 不应为 pending，实际: {pending}"

    @pytest.mark.parametrize(
        ("legacy_decision", "should_be_pending"),
        [
            ("accept", False),  # 存量：批准的审查反馈不进 pending（与修前一致）
            ("supplement", True),  # 存量：待补充的审查反馈进 pending（与修前一致）
        ],
    )
    @pytest.mark.asyncio
    async def test_legacy_rows_keep_pending_semantics(
        self, sqlite_session, legacy_decision, should_be_pending
    ):
        """存量兼容：JSONB 里已持久化的 accept/supplement 行语义不因归一翻转。"""
        user_id, plan_id = uuid4(), uuid4()
        await _seed_review_entry(sqlite_session, user_id, plan_id, "rev-old", legacy_decision)

        service = PlanFeedbackService(sqlite_session, redis=None)
        pending = await service.get_pending_feedback(user_id, plan_id)
        if should_be_pending:
            assert len(pending) == 1, f"存量 {legacy_decision} 行应仍为 pending"
        else:
            assert pending == [], f"存量 {legacy_decision} 行应仍不进 pending"


# ===========================================================================
# 升级/重置分支复活（修前恒假死码）
# ===========================================================================


class TestDecisionEscalationBranches:
    @pytest.mark.asyncio
    async def test_rejected_canonical_bumps_priority(self, sqlite_session):
        """update_feedback_decision("rejected") 必须升 high（修前 == "reject" 恒假）。"""
        user_id, plan_id = uuid4(), uuid4()
        await _seed_review_entry(sqlite_session, user_id, plan_id, "rev-1", "pending")

        service = PlanFeedbackService(sqlite_session, redis=None)
        result = await service.update_feedback_decision(
            user_id=user_id, plan_id=plan_id, review_id="rev-1", user_decision="rejected"
        )
        assert result is not None

        state = await PlanStateService(sqlite_session, redis=None).get_plan_state(
            user_id, plan_id, refresh=True
        )
        reloaded = await _reload(sqlite_session, state)
        entry = next(
            e for e in reloaded.feedback_log
            if e.get("applied_adjustment", {}).get("review_id") == "rev-1"
        )
        assert entry["applied_adjustment"]["decision"] == "rejected"
        assert entry["applied_adjustment"]["priority"] == "high", (
            f"rejected 决策必须升 high: {entry}"
        )
        assert entry["priority"] == "high"

    @pytest.mark.asyncio
    async def test_legacy_reject_alias_persists_canonical(self, sqlite_session):
        """输入别名 "reject"（旧 HITL 契约）归一为规范 "rejected" 持久化。"""
        user_id, plan_id = uuid4(), uuid4()
        await _seed_review_entry(sqlite_session, user_id, plan_id, "rev-1", "pending")

        service = PlanFeedbackService(sqlite_session, redis=None)
        await service.update_feedback_decision(
            user_id=user_id, plan_id=plan_id, review_id="rev-1", user_decision="reject"
        )

        state = await PlanStateService(sqlite_session, redis=None).get_plan_state(
            user_id, plan_id, refresh=True
        )
        reloaded = await _reload(sqlite_session, state)
        entry = reloaded.feedback_log[0]
        assert entry["applied_adjustment"]["decision"] == "rejected"
        assert entry["applied_adjustment"]["priority"] == "high"

    @pytest.mark.asyncio
    async def test_legacy_approve_alias_persists_canonical(self, sqlite_session):
        """输入别名 "approve" 归一为规范 "approved" 持久化。"""
        user_id, plan_id = uuid4(), uuid4()
        await _seed_review_entry(sqlite_session, user_id, plan_id, "rev-1", "pending")

        service = PlanFeedbackService(sqlite_session, redis=None)
        await service.update_feedback_decision(
            user_id=user_id, plan_id=plan_id, review_id="rev-1", user_decision="approve"
        )

        state = await PlanStateService(sqlite_session, redis=None).get_plan_state(
            user_id, plan_id, refresh=True
        )
        reloaded = await _reload(sqlite_session, state)
        entry = reloaded.feedback_log[0]
        assert entry["applied_adjustment"]["decision"] == "approved"


# ===========================================================================
# from_review_result / append_review_feedback 写侧归一
# ===========================================================================


class _FakeReviewResult:
    def __init__(self, decision: str):
        self.decision = decision
        self.plan_id = "plan-1"
        self.review_id = "rev-x"
        self.comments: list = []


class TestFromReviewResultCanonical:
    @pytest.mark.parametrize(
        ("review_decision", "expected"),
        [
            ("approved", "approved"),
            ("rejected", "rejected"),
            ("needs_modification", "needs_modification"),
            ("requires_confirmation", "requires_confirmation"),
            # skipped ≠ approved：沿用 _map_quality_gate_decision 未知值惯例
            ("skipped", "requires_confirmation"),
        ],
    )
    def test_from_review_result_emits_canonical(self, review_decision, expected):
        feedback = PlanFeedback.from_review_result(_FakeReviewResult(review_decision))
        assert feedback.decision == expected, (
            f"review {review_decision} 应产出规范值 {expected}"
        )
        assert feedback.decision in CANONICAL_DECISIONS


class TestAppendReviewFeedbackEscalation:
    @pytest.mark.asyncio
    async def test_user_rejected_decision_escalates(self, sqlite_session):
        """append_review_feedback(user_decision="rejected") 必须升 high + plan_disagree
        （修前 == "reject" 恒假死码）。"""
        user_id, plan_id = uuid4(), uuid4()
        service = PlanFeedbackService(sqlite_session, redis=None)
        review_result = _FakeReviewResult("requires_confirmation")

        from app.services.plan_outcome_service import PlanOutcomeService

        with patch.object(PlanOutcomeService, "record_outcome", new_callable=AsyncMock):
            await service.append_review_feedback(
                user_id=user_id,
                plan_id=plan_id,
                review_result=review_result,
                user_decision="rejected",
            )

        state = await PlanStateService(sqlite_session, redis=None).get_plan_state(
            user_id, plan_id, refresh=True
        )
        assert state and state.feedback_log, "feedback_log 未写入"
        entry = state.feedback_log[-1]
        assert entry["decision"] == "rejected"
        assert entry["priority"] == "high"
        assert entry["feedback_type"] == "plan_disagree"
        assert entry["source"] == "user"


# ===========================================================================
# handle_review_feedback 全链：拒绝计数与重置分支复活（plan_review_service）
# ===========================================================================


class TestHandleReviewFeedbackCanonicalChain:
    def _make_service(self, mock_redis) -> PlanReviewService:
        service = PlanReviewService()
        service.set_redis(mock_redis)
        return service

    def _mock_claim(self, plan_id: UUID):
        async def claim(action_id, user_id):
            return {
                "tool_name": "__plan_review__",
                "arguments": {"review_id": action_id},
                "preview_data": {"plan_id": str(plan_id), "decision": "requires_confirmation"},
            }

        return claim

    @pytest.mark.asyncio
    async def test_canonical_rejected_counts_toward_information_collection(self, sqlite_session):
        """gRPC 规范值 "rejected" 必须驱动拒绝计数（修前 == "reject" 恒假，
        Fix #3 信息收集链路对真实 gRPC 流量死码）。"""
        from app.core.pending_actions import pending_actions_store
        from app.services import plan_feedback_service as pfs_module

        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.set = AsyncMock(return_value=True)
        service = self._make_service(mock_redis)

        user_id, plan_id = uuid4(), uuid4()
        feedback_svc = PlanFeedbackService(sqlite_session, redis=None)

        def fake_get_svc(db, redis=None):
            return feedback_svc

        with (
            patch.object(pending_actions_store, "claim", side_effect=self._mock_claim(plan_id)),
            patch.object(pfs_module, "get_plan_feedback_service", fake_get_svc),
            patch.object(pfs_module.PlanOutcomeService, "record_outcome", new_callable=AsyncMock),
        ):
            result = await service.handle_review_feedback(
                review_id="rev-canon-1",
                user_decision="rejected",
                user_id=str(user_id),
                db_session=sqlite_session,
                user_comment="不要这个方向",
            )

        assert result["status"] == "success"
        assert mock_redis.incr.called, "规范值 rejected 必须触发拒绝计数（track_rejection_count）"

        # 持久化条目为规范值且进 pending
        state = await PlanStateService(sqlite_session, redis=None).get_plan_state(
            user_id, plan_id, refresh=True
        )
        assert state and state.feedback_log
        entry = state.feedback_log[-1]
        assert entry["applied_adjustment"]["decision"] == "rejected"
        pending = await feedback_svc.get_pending_feedback(user_id, plan_id)
        assert len(pending) == 1, f"rejected 全链写入后必须进 pending: {pending}"

    @pytest.mark.asyncio
    async def test_second_canonical_rejection_triggers_information_collection(
        self, sqlite_session
    ):
        from app.core.pending_actions import pending_actions_store
        from app.services import plan_feedback_service as pfs_module

        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=2)
        mock_redis.set = AsyncMock(return_value=True)
        service = self._make_service(mock_redis)

        user_id, plan_id = uuid4(), uuid4()

        with (
            patch.object(pending_actions_store, "claim", side_effect=self._mock_claim(plan_id)),
            patch.object(pfs_module, "get_plan_feedback_service", lambda db, redis=None: None),
        ):
            result = await service.handle_review_feedback(
                review_id="rev-canon-2",
                user_decision="rejected",
                user_id=str(user_id),
                db_session=None,
            )

        assert result["status"] == "information_collection_triggered", (
            f"第二次规范值 rejected 必须触发信息收集: {result}"
        )
        assert mock_redis.publish.called

    @pytest.mark.asyncio
    async def test_canonical_approved_resets_rejection_count(self):
        """gRPC 规范值 "approved" 必须重置拒绝计数（修前 == "approve" 恒假死码）。"""
        from app.core.pending_actions import pending_actions_store
        from app.services import plan_feedback_service as pfs_module

        mock_redis = AsyncMock()
        service = self._make_service(mock_redis)

        user_id, plan_id = uuid4(), uuid4()

        def fake_get_svc(db, redis=None):
            return None

        with (
            patch.object(pending_actions_store, "claim", side_effect=self._mock_claim(plan_id)),
            patch.object(pfs_module, "get_plan_feedback_service", fake_get_svc),
        ):
            result = await service.handle_review_feedback(
                review_id="rev-canon-3",
                user_decision="approved",
                user_id=str(user_id),
                db_session=None,
            )

        assert result["status"] == "success"
        assert mock_redis.delete.called, "规范值 approved 必须重置拒绝计数"


# ===========================================================================
# gRPC proto 枚举面与字符串面语义一致性（判别两路应同果）
# ===========================================================================


class TestProtoDecisionMapConsistency:
    def test_module_level_map_is_bijective_with_canonical(self):
        from app.gen.agent.v1 import agent_service_pb2
        from app.services.agent_grpc_service import PROTO_DECISION_TO_REVIEW_DECISION

        proto_decisions = {
            agent_service_pb2.APPROVE,
            agent_service_pb2.REJECT,
            agent_service_pb2.MODIFY,
            agent_service_pb2.ACKNOWLEDGE,
        }
        assert set(PROTO_DECISION_TO_REVIEW_DECISION) == proto_decisions

        mapped_values = [d.value for d in PROTO_DECISION_TO_REVIEW_DECISION.values()]
        assert sorted(mapped_values) == sorted(CANONICAL_DECISIONS)
        assert len(set(mapped_values)) == len(CANONICAL_DECISIONS), "映射必须单射"

    def test_mapped_values_survive_normalization_unchanged(self):
        """proto 枚举映射出的字符串面（进入 handle_review_feedback 的
        user_decision）与字符串判别路应同果：归一后不变。"""
        from app.services.agent_grpc_service import PROTO_DECISION_TO_REVIEW_DECISION

        for review_decision in PROTO_DECISION_TO_REVIEW_DECISION.values():
            assert normalize_plan_feedback_decision(review_decision.value) == review_decision.value
