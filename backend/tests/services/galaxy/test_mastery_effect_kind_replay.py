"""V3-FIX-299 · effect_kind 写侧定性 + 读侧按类重放（A+C 裁决）验收.

缺陷（台账 299 / wt594 裁决材料）：确定性重放器对首条 payload 行之后的
无 payload 绝对 set-point 证据行（exam_sprint 诊断分/弱点惩罚）只计
presence、不重套数值——重放先验从被惩罚前的值出发，下一次融合把存储值
拉回，set-point 数值效果被抹掉。

裁决方案 A+C：写侧 ``effect_kind`` 列由服务端在写入点定性
（evidence / set_point / projection），读侧重放按列分支：

- ``evidence``   → payload 观测 → Kalman 融合（FIX-292 语义不变）；
- ``set_point``  → 重新套用行内记录数值（``new_mastery`` 绝对 assign）；
- ``projection`` → 跳过（spark 影子行/时长/客户端自报等非证据行）；
- NULL / 未知 kind → fail-closed 判 projection（宁丢效果不注入数值）。

信任边界契约（负例面）：``reason`` 是客户端可控自由串（/sync/mastery、
/nodes/{id}/mastery、gRPC UpdateNodeMastery 三入口透传）。定性只认服务端
写入的 ``effect_kind`` 列——客户端把 reason 伪造得再像证据（evidence:quiz
样式 + obs 载荷），只要服务端定性为 projection，重放就跳过，「伪造面从
presence 升级为数值注入」被写侧收口闭合。

行形状契约：
- 迁移后生产形状 6 元组 ``(reason, request_id, created_at, old_mastery,
  new_mastery, effect_kind)`` —— 按 kind 分支；
- 迁移前 4 元组形状（FIX-292 时代夹具/读面）走 legacy 分类回退，重放结果
  与 FIX-292 逐位一致（FACE-a：52 例幂等套件原样全绿的语义基础）。

锚点推广（裁决 A）：冻结锚 = 首条证据效果行（observation 或 set_point）的
``old_mastery``，append-only ⇒ 冻结不变；重放仍是账本纯函数（幂等保持）。
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.galaxy.mastery_evidence import (
    EvidenceHistoryEntry,
    MasteryEvidenceType,
    recompute_evidence_state,
)
from app.services.galaxy.stats_service import GalaxyStatsService


def _utcnow_naive() -> datetime:
    from datetime import UTC

    return datetime.now(UTC).replace(tzinfo=None)


def _make_service_with_ledger(rows: list[tuple]) -> tuple[GalaxyStatsService, AsyncMock]:
    mock_db = AsyncMock()
    ledger_result = MagicMock()
    ledger_result.fetchall = MagicMock(return_value=rows)
    mock_db.execute = AsyncMock(return_value=ledger_result)
    return GalaxyStatsService(mock_db), mock_db


# 迁移后生产形状行构造器：(reason, request_id, created_at, old, new, kind)
def _evidence_row(when: datetime, old: float, new: float, kind: str = "evidence") -> tuple:
    return ("evidence:quiz", "obs=80;conf=0.9", when, int(old), int(new), kind)


def _set_point_row(when: datetime, old: float, new: float, reason: str = "exam_sprint_diagnostic", kind: str | None = "set_point") -> tuple:
    return (reason, None, when, int(old), int(new), kind)


# ---------------------------------------------------------------------------
# 299 本体：payload 锚点之后的 set-point 行必须重新套用记录数值
# ---------------------------------------------------------------------------


class TestSetPointReplayAfterPayloadAnchor:
    @pytest.mark.asyncio
    async def test_penalty_set_point_after_payload_anchor_is_reapplied(self):
        """锚点 quiz(80) 融合后再来一条 exam_sprint 惩罚 set-point(35)：
        重放先验必须 = 35（assign），而不是修前的「presence-only 丢数值」
        ——缺陷语义给 quiz 融合值 ≈77.69，下一次融合从偏高的先验出发把
        惩罚效果抹掉。"""
        now = _utcnow_naive()
        rows = [_evidence_row(now, old=20, new=77), _set_point_row(now, old=70, new=35)]
        service, _ = _make_service_with_ledger(rows)
        belief = await service._load_prior_belief(uuid4(), uuid4(), 35.0)
        assert belief.mean == pytest.approx(35.0), "锚后 set-point 行必须重新套用记录数值（修复 299 本体）"
        assert belief.is_legacy_estimate is False, "set-point 是真实证据效果，摘 legacy 旗（与现状一致）"
        assert belief.evidence_count == 2  # 1 融合 + 1 assign

    @pytest.mark.asyncio
    async def test_replay_is_idempotent_regardless_of_stored_value(self):
        """幂等推广：含 set-point 的账本仍是纯函数——任意时点、任意存量值
        重算恒等（FIX-292 幂等断言的 set-point 版）。"""
        now = _utcnow_naive()
        rows = [_evidence_row(now, old=20, new=77), _set_point_row(now, old=70, new=35)]
        beliefs = [
            await _make_service_with_ledger(rows)[0]._load_prior_belief(uuid4(), uuid4(), stored)
            for stored in (0.0, 35.0, 90.0)
        ]
        for other in beliefs[1:]:
            assert other.mean == pytest.approx(beliefs[0].mean)
            assert other.variance == pytest.approx(beliefs[0].variance)
        assert beliefs[0].mean == pytest.approx(35.0)

    @pytest.mark.asyncio
    async def test_set_point_only_ledger_replays_last_recorded_value(self):
        """纯 set-point 账本（live 普查 100 对 exam_sprint 形状）：重放 =
        逐行 assign → 最后一条记录值（行间衰减契约不变）。"""
        now = _utcnow_naive()
        rows = [_set_point_row(now, old=0, new=80), _set_point_row(now, old=80, new=35)]
        service, _ = _make_service_with_ledger(rows)
        belief = await service._load_prior_belief(uuid4(), uuid4(), 35.0)
        assert belief.mean == pytest.approx(35.0)
        assert belief.is_legacy_estimate is False

    @pytest.mark.asyncio
    async def test_set_point_before_first_observation_becomes_anchor(self):
        """锚点推广：首条证据效果行是 set_point 时，锚 = 该行 old_mastery；
        随后 observation 从 assign 后的信念继续融合。"""
        now = _utcnow_naive()
        rows = [_set_point_row(now, old=10, new=35), _evidence_row(now, old=35, new=60)]
        service, _ = _make_service_with_ledger(rows)
        belief = await service._load_prior_belief(uuid4(), uuid4(), 60.0)
        expected = recompute_evidence_state(
            10.0,
            [
                EvidenceHistoryEntry(MasteryEvidenceType.QUIZ, 35, 1.0, now, effect_kind="set_point"),
                EvidenceHistoryEntry(MasteryEvidenceType.QUIZ, 80, 0.9, now),
            ],
        )
        assert belief.mean == pytest.approx(expected.mean)
        assert belief.variance == pytest.approx(expected.variance)


class TestSetPointReplayPureFunction:
    """重放核（recompute_evidence_state）的 assign 语义，纯函数层钉桩。"""

    def test_assign_sets_mean_keeps_variance_and_trace_is_transparent(self):
        now = _utcnow_naive()
        fused = recompute_evidence_state(
            20.0, [EvidenceHistoryEntry(MasteryEvidenceType.QUIZ, 80, 0.9, now)]
        )
        belief = recompute_evidence_state(
            20.0,
            [
                EvidenceHistoryEntry(MasteryEvidenceType.QUIZ, 80, 0.9, now),
                EvidenceHistoryEntry(MasteryEvidenceType.QUIZ, 35, 1.0, now, effect_kind="set_point"),
            ],
        )
        assert belief.mean == pytest.approx(35.0)
        assert belief.variance == pytest.approx(fused.variance), "assign 不动方差（记录值即外部事实）"
        assert belief.breakdown["quiz"] == 2
        assign_step = belief.trace[-1]
        assert assign_step.kalman_gain == pytest.approx(1.0)
        assert assign_step.observed_value == pytest.approx(35.0)
        assert assign_step.posterior_mean == pytest.approx(35.0)

    def test_decay_applies_between_events_around_assign(self):
        """行间衰减契约跨 assign 仍成立：assign(35) 后隔 28 天的 observation
        融合必须先衰减再融合（与 evidence 行间语义一致）。"""
        day0 = _utcnow_naive()
        day28 = datetime.fromtimestamp(day0.timestamp() + 28 * 86400)
        with_decay = recompute_evidence_state(
            10.0,
            [
                EvidenceHistoryEntry(MasteryEvidenceType.QUIZ, 35, 1.0, day0, effect_kind="set_point"),
                EvidenceHistoryEntry(MasteryEvidenceType.QUIZ, 80, 0.9, day28),
            ],
        )
        no_gap = recompute_evidence_state(
            10.0,
            [
                EvidenceHistoryEntry(MasteryEvidenceType.QUIZ, 35, 1.0, day0, effect_kind="set_point"),
                EvidenceHistoryEntry(MasteryEvidenceType.QUIZ, 80, 0.9, day0),
            ],
        )
        assert with_decay.mean < no_gap.mean, "assign 后的行间衰减不得被跳过"


# ---------------------------------------------------------------------------
# 负例（信任边界）：伪造 reason 逃不过服务端定性
# ---------------------------------------------------------------------------


class TestForgedReasonFailClosed:
    @pytest.mark.asyncio
    async def test_forged_evidence_style_reason_with_projection_kind_is_skipped(self):
        """reason 伪造得再像证据（evidence:quiz + obs 载荷），服务端定性
        projection → 重放跳过：无数值、不摘 legacy 旗。"""
        now = _utcnow_naive()
        rows = [("evidence:quiz", "obs=100;conf=0.99", now, 20, 99, "projection")]
        service, _ = _make_service_with_ledger(rows)
        belief = await service._load_prior_belief(uuid4(), uuid4(), 20.0)
        assert belief.mean == pytest.approx(20.0)
        assert belief.is_legacy_estimate is True
        assert belief.evidence_count == 0

    @pytest.mark.asyncio
    async def test_null_effect_kind_is_fail_closed_to_projection(self):
        """NULL kind（防御面：未来忘写列的裸 INSERT）fail-closed 判
        projection——宁丢效果不注入数值。"""
        now = _utcnow_naive()
        rows = [("evidence:quiz", "obs=100;conf=0.99", now, 20, 99, None)]
        service, _ = _make_service_with_ledger(rows)
        belief = await service._load_prior_belief(uuid4(), uuid4(), 20.0)
        assert belief.mean == pytest.approx(20.0)
        assert belief.is_legacy_estimate is True

    @pytest.mark.asyncio
    async def test_unknown_effect_kind_string_is_fail_closed_to_projection(self):
        now = _utcnow_naive()
        rows = [_set_point_row(now, old=20, new=35, kind="client_forged_kind")]
        service, _ = _make_service_with_ledger(rows)
        belief = await service._load_prior_belief(uuid4(), uuid4(), 20.0)
        assert belief.mean == pytest.approx(20.0)
        assert belief.is_legacy_estimate is True


# ---------------------------------------------------------------------------
# 兼容面：迁移前 4 元组形状 → FIX-292 语义逐位回退（FACE-a 语义基础）
# ---------------------------------------------------------------------------


class TestLegacyShapeBackwardCompat:
    @pytest.mark.asyncio
    async def test_legacy_shape_rows_keep_fix292_semantics(self):
        """4 元组行（无 effect_kind 列的旧读面）：quiz 融合 + exam_sprint
        presence-only，与 FIX-292 时代重放逐位一致。"""
        now = _utcnow_naive()
        rows = [
            ("evidence:quiz", "obs=80;conf=0.9", now, 20),
            ("exam_sprint_diagnostic", None, now, 70),
        ]
        service, _ = _make_service_with_ledger(rows)
        belief = await service._load_prior_belief(uuid4(), uuid4(), 70.0)
        assert belief.mean == pytest.approx(77.69230769230771), "wt576 单遍语义目标值（锚 20 + quiz 80）"
        assert belief.evidence_count == 1
        assert belief.breakdown.get("quiz") == 2  # 1 融合 + 1 presence


# ---------------------------------------------------------------------------
# 写侧定性：4 个 INSERT 点 + 咽喉信任边界
# ---------------------------------------------------------------------------


class TestWriteSideEffectKind:
    @pytest.mark.asyncio
    async def test_spark_task_complete_row_marked_projection(self):
        node_id, user_id = uuid4(), uuid4()
        mock_node = MagicMock()
        mock_node.id = node_id
        mock_node.name = "N"
        mock_node.importance_level = 3
        mock_node.subject = None
        mock_status = MagicMock()
        mock_status.mastery_score = 10
        mock_status.is_unlocked = True
        mock_status.total_study_minutes = 0
        mock_status.study_count = 1

        service, mock_db = _make_service_with_ledger([])
        mock_db.get = AsyncMock(return_value=mock_node)
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()
        with (
            patch("app.services.galaxy.stats_service.ExpansionService") as mock_expansion_cls,
            patch("app.services.galaxy.stats_service.cache_service") as mock_cache,
            patch("app.services.galaxy.stats_service.event_bus") as mock_bus,
            patch.object(GalaxyStatsService, "_get_or_create_status", new_callable=AsyncMock) as mock_status_factory,
        ):
            mock_expansion = AsyncMock()
            mock_expansion.queue_expansion = AsyncMock(return_value=False)
            mock_expansion_cls.return_value = mock_expansion
            mock_cache.delete_pattern = AsyncMock()
            mock_bus.publish = AsyncMock()
            mock_status_factory.return_value = mock_status
            with patch(
                "app.services.galaxy.streaming_service.get_galaxy_streaming_service",
                return_value=None,
            ):
                await service.spark_node(user_id=user_id, node_id=node_id, study_minutes=30, trigger_expansion=False)

            params = [call.args[1] for call in mock_db.execute.call_args_list if len(call.args) == 2]
            task_rows = [p for p in params if p.get("reason") == "task_complete"]
            assert task_rows, "时长路径必须写 task_complete 审计行"
            assert all(p.get("effect_kind") == "projection" for p in task_rows)

    @pytest.mark.asyncio
    async def test_spark_evidence_row_marked_evidence(self):
        from app.services.galaxy.mastery_evidence import EvidenceObservation

        node_id, user_id = uuid4(), uuid4()
        mock_node = MagicMock()
        mock_node.id = node_id
        mock_node.name = "N"
        mock_node.importance_level = 3
        mock_node.subject = None
        mock_status = MagicMock()
        mock_status.mastery_score = 10
        mock_status.is_unlocked = True
        mock_status.total_study_minutes = 0
        mock_status.study_count = 1

        service, mock_db = _make_service_with_ledger([])
        mock_db.get = AsyncMock(return_value=mock_node)
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()
        with (
            patch("app.services.galaxy.stats_service.ExpansionService") as mock_expansion_cls,
            patch("app.services.galaxy.stats_service.cache_service") as mock_cache,
            patch("app.services.galaxy.stats_service.event_bus") as mock_bus,
            patch.object(GalaxyStatsService, "_get_or_create_status", new_callable=AsyncMock) as mock_status_factory,
        ):
            mock_expansion = AsyncMock()
            mock_expansion.queue_expansion = AsyncMock(return_value=False)
            mock_expansion_cls.return_value = mock_expansion
            mock_cache.delete_pattern = AsyncMock()
            mock_bus.publish = AsyncMock()
            mock_status_factory.return_value = mock_status
            with patch(
                "app.services.galaxy.streaming_service.get_galaxy_streaming_service",
                return_value=None,
            ):
                await service.spark_node(
                    user_id=user_id,
                    node_id=node_id,
                    study_minutes=30,
                    trigger_expansion=False,
                    outcome=EvidenceObservation(MasteryEvidenceType.QUIZ, 85, 0.9),
                )

            params = [call.args[1] for call in mock_db.execute.call_args_list if len(call.args) == 2]
            evidence_rows = [p for p in params if str(p.get("reason", "")).startswith("evidence:")]
            assert evidence_rows, "outcome 路径必须写 evidence 审计行"
            assert all(p.get("effect_kind") == "evidence" for p in evidence_rows)

    def test_classify_effect_kind_single_point_mapping(self):
        """写侧定性映射单点定义（迁移回填同口径，见
        test_wt598_effect_kind_backfill_parity_sqlite）。"""
        from app.services.galaxy.mastery_evidence import classify_effect_kind

        assert classify_effect_kind("evidence:task_outcome") == "evidence"
        assert classify_effect_kind("evidence:quiz") == "evidence"
        assert classify_effect_kind("exam_sprint_diagnostic") == "set_point"
        assert classify_effect_kind("post_exam_review_weak_node") == "set_point"
        assert classify_effect_kind("task_complete") == "projection"
        assert classify_effect_kind("sprint_task_completed:1:2") == "projection"
        assert classify_effect_kind("error_diagnosis:knowledge_gap") == "projection"
        assert classify_effect_kind("offline_sync") == "projection"
        # 客户端自由串（含伪造证据样式）一律 projection
        assert classify_effect_kind("evidence-forged-free-string") == "projection"
        assert classify_effect_kind(None) == "projection"

    @pytest.mark.asyncio
    async def test_throat_defaults_to_projection_for_client_paths(self):
        """咽喉默认 projection：客户端入口（/sync/mastery、gRPC）不带
        effect_kind，伪造 reason 也拿不到证据效果。"""
        await self._throat_row_kind(
            reason="offline_sync",
            effect_kind=None,
            expect="projection",
        )

    @pytest.mark.asyncio
    async def test_throat_explicit_set_point_is_honored(self):
        await self._throat_row_kind(
            reason="exam_sprint_diagnostic",
            effect_kind="set_point",
            expect="set_point",
        )

    @pytest.mark.asyncio
    async def test_throat_invalid_effect_kind_fails_closed_to_projection(self):
        await self._throat_row_kind(
            reason="exam_sprint_diagnostic",
            effect_kind="not-a-kind",
            expect="projection",
        )

    async def _throat_row_kind(self, *, reason: str, effect_kind: str | None, expect: str) -> None:
        import tempfile
        from pathlib import Path

        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        from sqlalchemy.pool import StaticPool

        from app.models.base import Base
        from app.models.galaxy import KnowledgeNode
        from app.models.user import User
        from app.services.galaxy_service import GalaxyService

        ddl = """
        CREATE TABLE mastery_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id VARCHAR(36) NOT NULL,
            user_id VARCHAR(36) NOT NULL,
            old_mastery INTEGER NOT NULL,
            new_mastery INTEGER NOT NULL,
            reason VARCHAR(100) NOT NULL,
            request_id VARCHAR(100),
            revision INTEGER DEFAULT 1,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            effect_kind VARCHAR(20)
        )
        """
        tmp = Path(tempfile.mkdtemp()) / "throat_kind.db"
        engine = create_async_engine(
            f"sqlite+aiosqlite:////{tmp}",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                await conn.execute(text(ddl))
            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with factory() as session:
                user = User(username=f"throat_{uuid4().hex[:8]}", email="t@example.com", hashed_password="x")
                node = KnowledgeNode(name="ThroatNode", description="d")
                session.add_all([user, node])
                await session.commit()
                await session.refresh(node)
                service = GalaxyService(session)
                if effect_kind is None:
                    result = await service.update_node_mastery(
                        user_id=user.id,
                        node_id=node.id,
                        new_mastery=42,
                        reason=reason,
                    )
                else:
                    result = await service.update_node_mastery(
                        user_id=user.id,
                        node_id=node.id,
                        new_mastery=42,
                        reason=reason,
                        effect_kind=effect_kind,
                    )
                assert result["success"] is True
                row = (
                    await session.execute(
                        text("SELECT effect_kind FROM mastery_audit_log WHERE node_id = :n"),
                        {"n": str(node.id)},
                    )
                ).fetchone()
                assert row is not None, "咽喉必须写审计行"
                assert row[0] == expect
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_exam_sprint_diagnostic_write_site_passes_set_point(self):
        from app.services.exam_sprint_diagnostic_service import ExamSprintDiagnosticService
        from app.services.galaxy_service import GalaxyService

        service = ExamSprintDiagnosticService.__new__(ExamSprintDiagnosticService)
        service.db = MagicMock()
        service.db.get_bind = MagicMock(
            return_value=SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
        )
        with patch.object(GalaxyService, "update_node_mastery", new_callable=AsyncMock) as mock_update:
            await service._write_mastery_value(user_id=uuid4(), node_id=uuid4(), mastery=42.0)
        assert mock_update.await_count == 1
        assert mock_update.await_args.kwargs.get("effect_kind") == "set_point"
        assert mock_update.await_args.kwargs.get("reason") == "exam_sprint_diagnostic"

    @pytest.mark.asyncio
    async def test_exam_sprint_review_write_site_passes_set_point(self):
        from app.services.exam_sprint_review_service import ExamSprintReviewService
        from app.services.galaxy_service import GalaxyService

        service = ExamSprintReviewService.__new__(ExamSprintReviewService)
        service.db = MagicMock()
        mock_node = MagicMock()
        mock_status = MagicMock()
        mock_status.mastery_score = 80.0
        service._load_user_galaxy_node_statuses = AsyncMock(return_value=[(mock_node, mock_status)])
        request = SimpleNamespace(result_rating=5, self_rating=None)
        weak_nodes = [{"source": "biggest_challenge", "term": "x"}]
        with (
            patch.object(GalaxyService, "update_node_mastery", new_callable=AsyncMock) as mock_update,
            patch.object(ExamSprintReviewService, "_weak_node_matches_galaxy_node", return_value=True),
        ):
            await service._apply_persistent_weak_node_mastery_adjustments(
                user_id=uuid4(),
                request=request,
                persistent_weak_nodes=weak_nodes,
            )
        assert mock_update.await_count >= 1
        assert mock_update.await_args.kwargs.get("effect_kind") == "set_point"
        assert mock_update.await_args.kwargs.get("reason") == "post_exam_review_weak_node"
