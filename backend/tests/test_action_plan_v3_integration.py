"""X-01 · ActionPlan V3 契约的 service 接线 + 结构化守卫（sqlite 隔离）。

验收对应：
- Human/Agent/Hybrid 三模式各构造一条**经 TaskService.create 落库**的合法记录；
- 旧 task 不破：无 action_plan 的 TaskCreate 全新列 NULL；
- 关键字段必须是结构化列，不是 prompt 文本（守卫测试直接检查 ORM 表结构）。
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import JSON, Text

from app.core.action_plan import (
    ACTION_PLAN_SCHEMA_VERSION,
    ACTION_SOURCE_REF_SCHEMES,
    CognitiveOwnership,
    EvidenceKind,
    RiskClass,
    UsefulStepReason,
)
from app.models.execution_intent import ExecutionMode
from app.models.task import Task
from app.schemas.task import ActionPlanIn, CompletionEvidenceIn, SmallestUsefulStepIn, TaskCreate, TaskDetail, TaskUpdate
from app.services.task_service import TaskService


def _action_plan_in(mode: str) -> ActionPlanIn:
    return ActionPlanIn(
        desired_outcome="能独立讲清楚贝叶斯更新的适用条件",
        smallest_useful_step=SmallestUsefulStepIn(
            description="用自己的话写 3 条适用条件并各配 1 个反例",
            useful_because=["builds_capability", "reduces_uncertainty"],
        ),
        completion_evidence=[
            CompletionEvidenceIn(evidence_kind="artifact", ref="document://doc-1"),
            CompletionEvidenceIn(evidence_kind="user_confirmation"),
        ],
        execution_mode=mode,
        cognitive_ownership="user_core",
        source_refs=[f"goal://{uuid4()}", "memory://episodic/00000000-0000-0000-0000-000000000001"],
        risk_class="low",
        reversible=True,
    )


@pytest.fixture
def v3_task_deps(monkeypatch):
    """复用生产测试的 mock 依赖（personalization 引擎不可用 → 默认值路径）。"""

    def _no_engine(db, redis):
        raise Exception("no engine")

    monkeypatch.setattr("app.services.task_service.get_personalization_engine", _no_engine)
    monkeypatch.setattr("app.services.task_service._sync_task_card_projection", _async_noop())
    monkeypatch.setattr(
        "app.services.task_service.task_document_service",
        type("S", (), {"auto_link_from_task_context": _async_noop()})(),
    )
    monkeypatch.setattr("app.services.task_service.cache_service", type("C", (), {"redis": None})())
    monkeypatch.setattr("app.services.task_service.event_bus_reliable", type("E", (), {"publish": _async_noop()})())
    monkeypatch.setattr("app.services.task_service.publish_srl_event", _async_noop())


def _async_noop():
    async def _noop(*args, **kwargs):
        return None

    return _noop


async def _make_user(db_session):
    from app.models.user import User

    user = User(username=f"u{uuid4().hex[:8]}", email=f"{uuid4().hex[:8]}@t.co", hashed_password="x", photon_balance=0)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestThreeModesThroughService:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("mode", ["human", "agent", "hybrid"])
    async def test_create_with_action_plan_persists_structured_columns(self, db_session, v3_task_deps, mode):
        user = await _make_user(db_session)
        payload = TaskCreate(
            title=f"V3 任务-{mode}",
            type="LEARNING",
            estimated_minutes=25,
            difficulty=2,
            action_plan=_action_plan_in(mode),
        )
        task = await TaskService.create(db_session, payload, user.id)

        assert task.action_schema_version == ACTION_PLAN_SCHEMA_VERSION
        assert task.desired_outcome == "能独立讲清楚贝叶斯更新的适用条件"
        assert task.execution_mode == mode  # 复用既有镜像列，无第二列
        assert task.cognitive_ownership == "user_core"
        assert task.risk_class == "low"
        assert task.reversible is True
        assert task.smallest_useful_step["useful_because"] == ["builds_capability", "reduces_uncertainty"]
        assert task.completion_evidence[0]["evidence_kind"] == "artifact"
        assert task.completion_evidence[0]["ref"] == "document://doc-1"
        assert task.source_refs[0].startswith("goal://")

        # TaskDetail 序列化面：V3 块可读回，DTO 不丢字段
        detail = TaskDetail.model_validate(task)
        assert detail.action_plan is not None
        assert detail.action_plan.execution_mode == mode
        assert detail.action_plan.completion_evidence[0].evidence_kind == "artifact"

    @pytest.mark.asyncio
    async def test_legacy_create_without_action_plan_is_fully_compatible(self, db_session, v3_task_deps):
        user = await _make_user(db_session)
        payload = TaskCreate(title="旧式任务", type="LEARNING", estimated_minutes=25, difficulty=1)
        task = await TaskService.create(db_session, payload, user.id)

        assert task.action_schema_version is None
        assert task.desired_outcome is None
        assert task.smallest_useful_step is None
        assert task.completion_evidence is None
        assert task.cognitive_ownership is None
        assert task.source_refs is None
        assert task.risk_class is None
        assert task.reversible is None
        detail = TaskDetail.model_validate(task)
        assert detail.action_plan is None

    @pytest.mark.asyncio
    async def test_update_applies_and_clears_action_plan(self, db_session, v3_task_deps):
        user = await _make_user(db_session)
        task = await TaskService.create(
            db_session,
            TaskCreate(title="更新目标", type="TRAINING", estimated_minutes=20, difficulty=2),
            user.id,
        )

        updated = await TaskService.update(db_session, task, TaskUpdate(action_plan=_action_plan_in("hybrid")))
        assert updated.execution_mode == "hybrid"
        assert updated.cognitive_ownership == "user_core"
        assert updated.action_schema_version == ACTION_PLAN_SCHEMA_VERSION

        # 显式置 None（fields_set）→ 清除 V3 语义回到 legacy 形态
        clear = TaskUpdate(action_plan=None)
        assert "action_plan" in clear.model_fields_set
        cleared = await TaskService.update(db_session, updated, clear)
        assert cleared.action_schema_version is None
        assert cleared.completion_evidence is None


class TestDtoValidation:
    def test_uppercase_mode_normalized_to_execution_intent_vocab(self):
        plan = _action_plan_in("HUMAN")
        assert plan.execution_mode == "human"

    def test_invalid_source_ref_scheme_rejected_at_parse_time(self):
        with pytest.raises(ValueError):
            ActionPlanIn(
                desired_outcome="x",
                smallest_useful_step=SmallestUsefulStepIn(description="y", useful_because=["advances_goal"]),
                completion_evidence=[CompletionEvidenceIn(evidence_kind="file")],
                execution_mode="agent",
                cognitive_ownership="delegated",
                source_refs=["ftp://evil"],
            )

    def test_unstructured_evidence_rejected_at_parse_time(self):
        with pytest.raises(ValueError):
            CompletionEvidenceIn(description="用户说做完了")  # type: ignore[call-arg]

    def test_empty_useful_because_rejected(self):
        with pytest.raises(ValueError):
            SmallestUsefulStepIn(description="打开 IDE", useful_because=[])


class TestStructuredColumnsGuard:
    """非自然语言保证：关键字段必须是结构化列/字段，不是 prompt 文本。"""

    def test_key_fields_are_real_columns_on_tasks_table(self):
        table = Task.__table__
        for name in (
            "desired_outcome",
            "smallest_useful_step",
            "completion_evidence",
            "cognitive_ownership",
            "source_refs",
            "risk_class",
            "reversible",
            "action_schema_version",
        ):
            assert name in table.columns, f"{name} 必须是 tasks 表的真实列"

    def test_typed_payloads_are_structured_not_free_text(self):
        """completion_evidence / smallest_useful_step / source_refs 必须是 JSON 结构列，
        不是 Text 自由文本一列了事。"""
        table = Task.__table__
        for name in ("smallest_useful_step", "completion_evidence", "source_refs"):
            col = table.columns[name]
            assert isinstance(col.type, JSON), f"{name} 必须是 JSON 结构列，实际 {col.type}"
            assert not isinstance(col.type, Text)

    def test_execution_mode_single_source_no_duplicate_column(self):
        """execution_mode 复用既有 String(20) 镜像列：表上不得出现第二个执行模式列。"""
        mode_like = [c.name for c in Task.__table__.columns if "execution" in c.name]
        assert mode_like == ["execution_mode"]

    def test_closed_vocabularies_are_enums_not_free_strings(self):
        import enum

        for vocab in (CognitiveOwnership, RiskClass, EvidenceKind, UsefulStepReason):
            assert issubclass(vocab, enum.StrEnum)
        assert isinstance(ACTION_SOURCE_REF_SCHEMES, frozenset) and ACTION_SOURCE_REF_SCHEMES

    def test_all_new_columns_nullable_for_legacy_compat(self):
        for name in (
            "desired_outcome",
            "smallest_useful_step",
            "completion_evidence",
            "cognitive_ownership",
            "source_refs",
            "risk_class",
            "reversible",
            "action_schema_version",
        ):
            assert Task.__table__.columns[name].nullable, f"{name} 必须 nullable（旧记录全兼容）"


class TestJsonbSqliteCompat:
    def test_v3_json_columns_use_jsonb_compat_variant(self):
        """JSONBCompat（JSONB + sqlite JSON variant）保证 sqlite 测试与 PG 生产一致可跑。"""
        from sqlalchemy.dialects import postgresql, sqlite

        col = Task.__table__.columns["completion_evidence"]
        compiled_pg = str(col.type.compile(dialect=postgresql.dialect()))
        compiled_lite = str(col.type.compile(dialect=sqlite.dialect()))
        assert "JSONB" in compiled_pg.upper()
        assert "JSON" in compiled_lite.upper()


class TestDirtyRowTolerance:
    """X-01 返修 F1/F2（REVIEW_RECEIPT_2）：REST 读路径对词表外/未来枚举值零容错，
    单行脏数据曾使 GET /tasks、/today、/recommended、/tasks/{id} 全部 500。
    修复后：REST 投影与类型化路径走**同一个门**（版本 + 全词表 + 归一），
    脏/未来行降级为 action_plan=None 并打 WARN 日志（可观测降级，非静默）。"""

    def _v3_task(self, **overrides) -> Task:
        """构造带 V3 块的 Task 实例（不经 DB，直接喂序列化路径）。"""
        base = dict(
            id=uuid4(),
            user_id=uuid4(),
            created_at=datetime.now(UTC).replace(tzinfo=None),
            updated_at=datetime.now(UTC).replace(tzinfo=None),
            title="脏数据行",
            type="LEARNING",
            status="PENDING",
            tags=[],
            estimated_minutes=25,
            difficulty=1,
            energy_cost=1,
            priority=0,
            order_index=0,
            subtasks_total=0,
            subtasks_completed=0,
            action_schema_version="action_plan.v1",
            desired_outcome="能讲清贝叶斯更新适用条件",
            smallest_useful_step={"description": "写 3 条适用条件", "useful_because": ["builds_capability"]},
            completion_evidence=[{"evidence_kind": "artifact", "ref": "document://doc-1"}],
            execution_mode="human",
            cognitive_ownership="user_core",
            source_refs=["goal://00000000-0000-0000-0000-000000000001"],
            risk_class="low",
            reversible=True,
        )
        base.update(overrides)
        return Task(**base)

    def test_valid_row_still_serializes_fully(self):
        detail = TaskDetail.model_validate(self._v3_task())
        assert detail.action_plan is not None
        assert detail.action_plan.execution_mode == "human"

    @pytest.mark.parametrize(
        "dirty_overrides",
        [
            # F1 探针实证的四类脏形态（未来词表值 / 词表外镜像列值 / 半写行 / 未来版本行）
            {"smallest_useful_step": {"description": "x", "useful_because": ["builds_habit_v2"]}},
            {"completion_evidence": [{"evidence_kind": "streak_data_v2"}]},
            {"execution_mode": "manual"},
            {"desired_outcome": None},
            {"action_schema_version": "action_plan.v0"},  # F2：版本门分歧——REST 曾无版本门
            {"cognitive_ownership": "bogus_ownership"},
            {"source_refs": ["ftp://dirty"]},
        ],
    )
    def test_dirty_rows_dont_500_and_degrade_to_none(self, dirty_overrides):
        task = self._v3_task(**dirty_overrides)
        detail = TaskDetail.model_validate(task)  # 修复前：pydantic ValidationError → 端点 500
        assert detail.action_plan is None

    def test_dirty_row_in_a_list_does_not_break_other_rows(self):
        from app.core.action_plan import action_plan_from_task

        tasks = [self._v3_task(), self._v3_task(execution_mode="agent", desired_outcome=None)]
        details = [TaskDetail.model_validate(task) for task in tasks]  # 单行脏 → 列表端点整体不 500
        assert details[0].action_plan is not None
        assert details[1].action_plan is None
        # 类型化路径与 REST 路径同一行同答案（F2 统一）
        assert action_plan_from_task(tasks[0]) is not None
        assert action_plan_from_task(tasks[1]) is None

    def test_degradation_is_observable_via_warn_log(self):
        """F2 可观测性：非 NULL schema_version 但门失败 → WARN（带 task 标识与原因），非静默。"""
        from loguru import logger as loguru_logger

        events: list[str] = []
        sink_id = loguru_logger.add(lambda message: events.append(str(message)), level="WARNING")
        try:
            task = self._v3_task(execution_mode="manual")
            assert TaskDetail.model_validate(task).action_plan is None
        finally:
            loguru_logger.remove(sink_id)
        assert any("ActionPlan V3" in event for event in events), "降级必须留下 WARN 痕迹"

