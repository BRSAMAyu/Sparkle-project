"""D-02 · Outcome Ledger 服务层守卫（sqlite 隔离，不触 dev DB）。

覆盖验收项：
- 五源 roundtrip + 每条 truth_class + source ref；
- 去重（同因合并）：task 完成与其 pipeline 回声 study_record 算 **一个** outcome
  的多源证据；standalone study_record 是独立 outcome；计数不重复；
- keyset 分页完整无重无漏 + 幂等（同游标重复查询同页同 id）；
  **跨流同刻 tie 回归**（R2 P1 返修）：页边界落在同刻处全量翻页每条恰一次；
- source / truth_class 过滤；truth_class=actual 不含自报完成；
- 用户隔离与 cohort 边界（exclude_seed_cohort，词表值冻结钉死）；
- 证据来源约束（R2 P2-1/P2-2 返修）：kind↔scheme 配对、文件生命周期、
  TaskDocument 任务关联性、focus 时间方向（P2-3）；
- 「完成 ≠ 点击」度量面（truth_coverage）。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.core.action_plan import ACTION_PLAN_SCHEMA_VERSION
from app.core.outcome_ledger import (
    FOCUS_COVERAGE_MIN_MINUTES,
    OutcomeSource,
    TruthClass,
    derive_outcome_id,
)
from app.models.file_storage import StoredFile
from app.models.focus import FocusSession, FocusStatus
from app.models.galaxy import ExpansionFeedback, StudyRecord
from app.models.intervention_adaptive import BehavioralOutcome
from app.models.task import Task, TaskStatus, TaskType
from app.models.task_document import TaskDocument
from app.models.user import User
from app.services.outcome_ledger_service import EXCLUDED_COHORT_REGISTRATION_SOURCES, OutcomeLedgerService

pytestmark = pytest.mark.asyncio

_BASE = datetime(2026, 9, 19, 10, 0, 0)


async def _make_user(db_session, *, registration_source: str = "email") -> User:
    user = User(
        username=f"u{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@t.co",
        hashed_password="x",
        registration_source=registration_source,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def _task(user_id, *, completed_at=None, actual_minutes=30, status=TaskStatus.COMPLETED, **extra) -> Task:
    return Task(
        user_id=user_id,
        title="任务",
        type=TaskType.LEARNING,
        estimated_minutes=30,
        status=status,
        completed_at=completed_at,
        actual_minutes=actual_minutes if status == TaskStatus.COMPLETED else None,
        **extra,
    )


def _focus(user_id, *, task_id=None, duration=25, at=None, status=FocusStatus.COMPLETED) -> FocusSession:
    end = at or _BASE
    return FocusSession(
        user_id=user_id,
        task_id=task_id,
        start_time=end - timedelta(minutes=duration),
        end_time=end,
        duration_minutes=duration,
        status=status,
    )


def _study(user_id, *, node_id=None, task_id=None, record_type="task_complete", minutes=20, at=None) -> StudyRecord:
    return StudyRecord(
        user_id=user_id,
        node_id=node_id or uuid4(),
        task_id=task_id,
        study_minutes=minutes,
        mastery_delta=4.0,
        record_type=record_type,
        created_at=at or _BASE,
    )


def _quiz(user_id, *, node_id=None, task_id=None, passed=True, at=None) -> ExpansionFeedback:
    return ExpansionFeedback(
        user_id=user_id,
        trigger_node_id=node_id or uuid4(),
        feedback_type="implicit",
        implicit_score=1.0 if passed else -0.5,
        meta_data={"source": "quiz_passed" if passed else "quiz_failed", "task_id": str(task_id) if task_id else None},
        created_at=at or _BASE,
    )


def _behavioral(user_id, *, success=True, at=None) -> BehavioralOutcome:
    return BehavioralOutcome(
        user_id=user_id,
        intervention_id=uuid4(),
        outcome_type="action_taken",
        time_to_outcome=3600,
        success=success,
        timestamp=at or _BASE,
    )


def _stored_file(
    user_id,
    *,
    status="uploaded",
    lifecycle_status="active",
    erased_at=None,
    deleted_at=None,
) -> tuple[StoredFile, object]:
    file_id = uuid4()
    return (
        StoredFile(
            id=file_id,
            user_id=user_id,
            file_name="notes.pdf",
            mime_type="application/pdf",
            file_size=1024,
            bucket="docs",
            object_key=f"obj-{file_id}",
            status=status,
            lifecycle_status=lifecycle_status,
            erased_at=erased_at,
            deleted_at=deleted_at,
        ),
        file_id,
    )


def _evidence_task(user_id, evidence, *, completed_at=_BASE, actual_minutes=30) -> Task:
    """带 completion_evidence 声明的 V3 任务（走 X-01 action_plan 门）。"""
    return _task(
        user_id,
        completed_at=completed_at,
        actual_minutes=actual_minutes,
        action_schema_version=ACTION_PLAN_SCHEMA_VERSION,
        desired_outcome="完成并留下证据",
        smallest_useful_step={"description": "产出", "useful_because": ["produces_artifact"]},
        completion_evidence=list(evidence),
        execution_mode="human",
        cognitive_ownership="user_core",
    )


async def _add_and_link(
    db_session,
    user_id,
    *,
    file_status="uploaded",
    lifecycle_status="active",
    erased_at=None,
    kind="artifact",
):
    """就绪文件 + 完成任务 + TaskDocument 显式挂载（合法验证证据的最小构造）。"""
    file_row, file_id = _stored_file(
        user_id, status=file_status, lifecycle_status=lifecycle_status, erased_at=erased_at
    )
    task = _evidence_task(user_id, [{"evidence_kind": kind, "ref": f"document://{file_id}", "description": None}])
    db_session.add_all([file_row, task])
    await db_session.flush()
    db_session.add(TaskDocument(task_id=task.id, file_id=file_id, linked_by="user"))
    await db_session.commit()
    return task, file_id


class TestFiveSourceRoundtrip:
    async def test_each_source_produces_one_outcome_with_expected_truth(self, db_session):
        user = await _make_user(db_session)
        db_session.add_all(
            [
                _task(user.id, completed_at=_BASE),
                _study(user.id, record_type="error_review", at=_BASE),
                _focus(user.id, at=_BASE),
                _quiz(user.id, at=_BASE),
                _behavioral(user.id, at=_BASE),
            ]
        )
        await db_session.commit()

        page = await OutcomeLedgerService(db_session).query(user_id=user.id, limit=50)
        by_source = {entry.source: entry for entry in page.items}
        assert set(by_source) == {
            OutcomeSource.TASK_COMPLETION,
            OutcomeSource.STUDY_RECORD,
            OutcomeSource.FOCUS_SESSION,
            OutcomeSource.QUIZ_FEEDBACK,
            OutcomeSource.BEHAVIORAL,
        }
        # 非 task 源 = 服务器记录的行为观察 → actual
        for source in (
            OutcomeSource.STUDY_RECORD,
            OutcomeSource.FOCUS_SESSION,
            OutcomeSource.QUIZ_FEEDBACK,
            OutcomeSource.BEHAVIORAL,
        ):
            assert by_source[source].truth_class is TruthClass.ACTUAL
        # 无独立证据的 task 完成 → self_reported（「完成 ≠ 点击」）
        assert by_source[OutcomeSource.TASK_COMPLETION].truth_class is TruthClass.SELF_REPORTED
        # 每条带 source ref + outcome_id 幂等形态
        expected_ref_prefixes = {
            OutcomeSource.TASK_COMPLETION: "task://",
            OutcomeSource.STUDY_RECORD: "study_record://",
            OutcomeSource.FOCUS_SESSION: "focus_session://",
            OutcomeSource.QUIZ_FEEDBACK: "quiz_feedback://",
            OutcomeSource.BEHAVIORAL: "behavioral://",
        }
        for source, entry in by_source.items():
            assert entry.source_ref.startswith(expected_ref_prefixes[source])
            assert entry.outcome_id == derive_outcome_id(source=source, source_id=entry.source_id)

    async def test_quiz_failed_is_negative_polarity_but_still_actual(self, db_session):
        user = await _make_user(db_session)
        db_session.add(_quiz(user.id, passed=False))
        await db_session.commit()

        page = await OutcomeLedgerService(db_session).query(user_id=user.id)
        assert page.items[0].polarity.value == "negative"
        assert page.items[0].truth_class is TruthClass.ACTUAL


class TestSameCauseDedup:
    """验收：「同 task 的 completion+study_record 算一个 outcome 的多源证据」。"""

    async def test_echo_study_record_merges_into_task_outcome(self, db_session):
        user = await _make_user(db_session)
        task = _task(user.id, completed_at=_BASE)
        db_session.add(task)
        await db_session.flush()
        db_session.add(_study(user.id, task_id=task.id, record_type="task_complete", at=_BASE))
        await db_session.commit()

        service = OutcomeLedgerService(db_session)
        page = await service.query(user_id=user.id, limit=50)
        assert len(page.items) == 1  # 不是两个 outcome
        entry = page.items[0]
        assert entry.source is OutcomeSource.TASK_COMPLETION
        echo_refs = [e for e in entry.evidence if e.source == "study_record"]
        assert len(echo_refs) == 1
        assert echo_refs[0].role.value == "pipeline_echo"

        counts = await service.count_by_source(user_id=user.id)
        assert counts[OutcomeSource.TASK_COMPLETION.value] == 1
        assert counts[OutcomeSource.STUDY_RECORD.value] == 0  # echo 不入独立流

    async def test_standalone_study_records_are_own_outcomes(self, db_session):
        user = await _make_user(db_session)
        task = _task(user.id, completed_at=_BASE)
        db_session.add(task)
        await db_session.flush()
        db_session.add_all(
            [
                _study(user.id, task_id=None, record_type="task_complete", at=_BASE),  # 无 task 可并
                _study(user.id, task_id=task.id, record_type="error_review", at=_BASE),  # 非 echo 类型
                _study(user.id, task_id=task.id, record_type="task_complete", at=_BASE),  # echo
            ]
        )
        await db_session.commit()

        service = OutcomeLedgerService(db_session)
        counts = await service.count_by_source(user_id=user.id)
        assert counts[OutcomeSource.STUDY_RECORD.value] == 2  # 前两条独立，第三条并入 task
        assert counts[OutcomeSource.TASK_COMPLETION.value] == 1

    async def test_interrupted_focus_is_not_an_outcome(self, db_session):
        user = await _make_user(db_session)
        db_session.add(_focus(user.id, status=FocusStatus.INTERRUPTED))
        await db_session.commit()

        counts = await OutcomeLedgerService(db_session).count_by_source(user_id=user.id)
        assert counts[OutcomeSource.FOCUS_SESSION.value] == 0

    async def test_deleted_rows_are_excluded(self, db_session):
        """五流删除口径对齐（R2 P2-6 返修）：软删除行不入账本流也不入计数。"""
        user = await _make_user(db_session)
        task = _task(user.id, completed_at=_BASE)
        task.deleted_at = _BASE
        db_session.add(task)
        db_session.add(_focus(user.id))
        focus_deleted = _focus(user.id, at=_BASE + timedelta(minutes=5))
        focus_deleted.deleted_at = _BASE
        db_session.add(focus_deleted)
        quiz_deleted = _quiz(user.id, at=_BASE + timedelta(minutes=6))
        quiz_deleted.deleted_at = _BASE
        behavioral_deleted = _behavioral(user.id, at=_BASE + timedelta(minutes=7))
        behavioral_deleted.deleted_at = _BASE
        db_session.add_all([quiz_deleted, behavioral_deleted])
        await db_session.commit()

        service = OutcomeLedgerService(db_session)
        counts = await service.count_by_source(user_id=user.id)
        assert counts[OutcomeSource.TASK_COMPLETION.value] == 0
        assert counts[OutcomeSource.FOCUS_SESSION.value] == 1
        assert counts[OutcomeSource.QUIZ_FEEDBACK.value] == 0  # P2-6：quiz 流同口径
        assert counts[OutcomeSource.BEHAVIORAL.value] == 0  # P2-6：behavioral 流同口径

        page = await service.query(user_id=user.id, limit=50)
        assert {entry.source for entry in page.items} == {OutcomeSource.FOCUS_SESSION}

    async def test_deleted_quiz_and_behavioral_rows_leave_the_stream(self, db_session):
        """P2-6 定向：quiz/behavioral 流的 not_deleted_filter（旧行软删后消失）。"""
        user = await _make_user(db_session)
        quiz_alive = _quiz(user.id, at=_BASE - timedelta(minutes=1))
        quiz_dead = _quiz(user.id, at=_BASE)
        quiz_dead.deleted_at = _BASE
        behavioral_alive = _behavioral(user.id, at=_BASE - timedelta(minutes=1))
        behavioral_dead = _behavioral(user.id, at=_BASE)
        behavioral_dead.deleted_at = _BASE
        db_session.add_all([quiz_alive, quiz_dead, behavioral_alive, behavioral_dead])
        await db_session.commit()

        service = OutcomeLedgerService(db_session)
        page = await service.query(user_id=user.id, limit=50)
        assert {entry.source for entry in page.items} == {OutcomeSource.QUIZ_FEEDBACK, OutcomeSource.BEHAVIORAL}
        assert len(page.items) == 2  # 各 1：软删行出流


class TestTruthUpgradePaths:
    async def test_focus_coverage_meeting_threshold_upgrades_task_to_actual(self, db_session):
        user = await _make_user(db_session)
        task = _task(user.id, completed_at=_BASE, actual_minutes=60)
        db_session.add(task)
        await db_session.flush()
        db_session.add(_focus(user.id, task_id=task.id, duration=30, at=_BASE - timedelta(minutes=1)))
        await db_session.commit()

        page = await OutcomeLedgerService(db_session).query(user_id=user.id)
        entry = page.items[0]
        assert entry.truth_class is TruthClass.ACTUAL
        assert any(e.source == "focus_session" and e.role.value == "independent" for e in entry.evidence)

    async def test_focus_below_threshold_keeps_self_reported(self, db_session):
        user = await _make_user(db_session)
        task = _task(user.id, completed_at=_BASE, actual_minutes=60)
        db_session.add(task)
        await db_session.flush()
        db_session.add(_focus(user.id, task_id=task.id, duration=5, at=_BASE - timedelta(minutes=1)))
        await db_session.commit()

        page = await OutcomeLedgerService(db_session).query(user_id=user.id)
        entry = [e for e in page.items if e.source is OutcomeSource.TASK_COMPLETION][0]
        assert entry.truth_class is TruthClass.SELF_REPORTED

    async def test_minimal_focus_absolute_floor(self, db_session):
        """actual_minutes 缺失时以绝对下限（10 分钟）为准——刚好达标升 actual。"""
        user = await _make_user(db_session)
        task = _task(user.id, completed_at=_BASE, actual_minutes=None)
        db_session.add(task)
        await db_session.flush()
        db_session.add(_focus(user.id, task_id=task.id, duration=FOCUS_COVERAGE_MIN_MINUTES))
        await db_session.commit()

        page = await OutcomeLedgerService(db_session).query(user_id=user.id)
        entry = [e for e in page.items if e.source is OutcomeSource.TASK_COMPLETION][0]
        assert entry.truth_class is TruthClass.ACTUAL

    async def test_materialized_quiz_upgrades_task_to_actual_with_correlation(self, db_session):
        user = await _make_user(db_session)
        task = _task(user.id, completed_at=_BASE, actual_minutes=30)
        db_session.add(task)
        await db_session.flush()
        db_session.add(_quiz(user.id, task_id=task.id, at=_BASE + timedelta(seconds=5)))
        await db_session.commit()

        page = await OutcomeLedgerService(db_session).query(user_id=user.id)
        entry = [e for e in page.items if e.source is OutcomeSource.TASK_COMPLETION][0]
        assert entry.truth_class is TruthClass.ACTUAL
        assert entry.correlation["task_id"] == str(task.id)

    async def test_v3_declared_unresolvable_ref_stays_self_reported(self, db_session):
        """V3 任务声明 artifact ref 但 ref 无法解析 → 不伪装 actual（验收守卫）。"""
        user = await _make_user(db_session)
        task = _task(
            user.id,
            completed_at=_BASE,
            actual_minutes=30,
            action_schema_version=ACTION_PLAN_SCHEMA_VERSION,
            desired_outcome="能独立复述概念",
            smallest_useful_step={"description": "写 3 条", "useful_because": ["builds_capability"]},
            completion_evidence=[{"evidence_kind": "artifact", "ref": f"document://{uuid4()}", "description": None}],
            execution_mode="human",
            cognitive_ownership="user_core",
        )
        db_session.add(task)
        await db_session.commit()

        page = await OutcomeLedgerService(db_session).query(user_id=user.id)
        entry = page.items[0]
        assert entry.truth_class is TruthClass.SELF_REPORTED
        assert any(e.source == "declared_ref" and not e.verified for e in entry.evidence)

    async def test_v3_declared_resolvable_document_ref_upgrades_to_actual(self, db_session):
        """合法验证证据的最小完整构造：本人文件 + 状态就绪 + 生命周期 active +
        TaskDocument 显式挂载到被完成任务 → actual（R2 返修后的三重门全开）。"""
        user = await _make_user(db_session)
        task, _file_id = await _add_and_link(db_session, user.id)

        page = await OutcomeLedgerService(db_session).query(user_id=user.id)
        entry = page.items[0]
        assert entry.truth_class is TruthClass.ACTUAL
        assert any(e.source == "declared_ref" and e.verified and e.role.value == "independent" for e in entry.evidence)

    async def test_file_kind_linked_document_also_upgrades(self, db_session):
        """file kind 与 artifact 同走 document:// 配对白名单。"""
        user = await _make_user(db_session)
        task, _file_id = await _add_and_link(db_session, user.id, kind="file")

        page = await OutcomeLedgerService(db_session).query(user_id=user.id)
        entry = [e for e in page.items if e.source is OutcomeSource.TASK_COMPLETION][0]
        assert entry.truth_class is TruthClass.ACTUAL

    async def test_cross_user_ref_cannot_upgrade(self, db_session):
        """他人文件 ref 不构成我的完成证据（隔离防注入升级）——即使对方文件
        状态就绪也无效（归属门先于一切）。"""
        other = await _make_user(db_session)
        me = await _make_user(db_session)
        other_file, other_file_id = _stored_file(other.id)
        task = _evidence_task(
            me.id, [{"evidence_kind": "artifact", "ref": f"document://{other_file_id}", "description": None}]
        )
        db_session.add_all([other_file, task])
        await db_session.commit()

        page = await OutcomeLedgerService(db_session).query(user_id=me.id)
        assert page.items[0].truth_class is TruthClass.SELF_REPORTED


class TestEvidenceSourceConstraints:
    """R2 P2-1/P2-2 返修：验证证据三重门 = kind↔scheme 配对 + 生命周期就绪 + 任务关联性。

    归属 ≠ 相关、声明不构成证明——「上传过任意文件的用户把之后所有完成都
    洗成 actual」与「code kind 借 document ref 升 actual」两条路径都必须关死。
    """

    async def test_code_kind_document_ref_never_upgrades(self, db_session):
        """code 在解析器支持前恒不单独升 actual——即使挂了合法就绪文件。"""
        user = await _make_user(db_session)
        task, _file_id = await _add_and_link(db_session, user.id, kind="code")

        page = await OutcomeLedgerService(db_session).query(user_id=user.id)
        entry = [e for e in page.items if e.source is OutcomeSource.TASK_COMPLETION][0]
        assert entry.truth_class is TruthClass.SELF_REPORTED
        declared = [e for e in entry.evidence if e.source == "declared_ref"]
        assert declared and not declared[0].verified

    async def test_quiz_result_kind_never_verifies_via_declaration(self, db_session):
        """quiz_result 只经 quiz_feedback 物化面验证，声明 ref 不算数。"""
        user = await _make_user(db_session)
        task, _file_id = await _add_and_link(db_session, user.id, kind="quiz_result")

        page = await OutcomeLedgerService(db_session).query(user_id=user.id)
        entry = [e for e in page.items if e.source is OutcomeSource.TASK_COMPLETION][0]
        assert entry.truth_class is TruthClass.SELF_REPORTED

    async def test_unlinked_own_document_is_not_valid_evidence(self, db_session):
        """与任务无关的自有旧文件不得作为有效证据（归属 ≠ 相关）：
        文件就绪、归属本人，但没有 TaskDocument 挂载到被完成的任务。"""
        user = await _make_user(db_session)
        file_row, file_id = _stored_file(user.id)
        # 旧文件：早于任务完成很久之前上传
        file_row.created_at = _BASE - timedelta(days=30)
        task = _evidence_task(
            user.id, [{"evidence_kind": "artifact", "ref": f"document://{file_id}", "description": None}]
        )
        db_session.add_all([file_row, task])
        await db_session.commit()

        page = await OutcomeLedgerService(db_session).query(user_id=user.id)
        entry = [e for e in page.items if e.source is OutcomeSource.TASK_COMPLETION][0]
        assert entry.truth_class is TruthClass.SELF_REPORTED

    async def test_other_own_task_ref_is_not_valid_evidence(self, db_session):
        """task:// 指向自己的另一个（已完成）任务不得作为完成证据：
        被指向行本身也只是用户主张，声明不构成证明。"""
        user = await _make_user(db_session)
        other_task = _task(user.id, completed_at=_BASE - timedelta(days=1))
        task = _evidence_task(
            user.id, [{"evidence_kind": "artifact", "ref": f"task://{other_task.id}", "description": None}]
        )
        db_session.add_all([other_task, task])
        await db_session.commit()

        page = await OutcomeLedgerService(db_session).query(user_id=user.id)
        entry = [e for e in page.items if e.source is OutcomeSource.TASK_COMPLETION][0]
        assert entry.truth_class is TruthClass.SELF_REPORTED

    @pytest.mark.parametrize("status", ["uploading", "queued", "processing", "failed"])
    async def test_non_ready_file_status_does_not_verify(self, db_session, status):
        """uploading（从未传完）等非就绪状态不算已验证证据（P2-2）。"""
        user = await _make_user(db_session)
        task, _file_id = await _add_and_link(db_session, user.id, file_status=status)

        page = await OutcomeLedgerService(db_session).query(user_id=user.id)
        entry = [e for e in page.items if e.source is OutcomeSource.TASK_COMPLETION][0]
        assert entry.truth_class is TruthClass.SELF_REPORTED

    @pytest.mark.parametrize("lifecycle", ["archived", "revoked", "orphaned"])
    async def test_non_active_lifecycle_does_not_verify(self, db_session, lifecycle):
        """archived/revoked/orphaned 生命周期的文件不构成有效证据（P2-2）。"""
        user = await _make_user(db_session)
        task, _file_id = await _add_and_link(db_session, user.id, lifecycle_status=lifecycle)

        page = await OutcomeLedgerService(db_session).query(user_id=user.id)
        entry = [e for e in page.items if e.source is OutcomeSource.TASK_COMPLETION][0]
        assert entry.truth_class is TruthClass.SELF_REPORTED

    async def test_erased_file_does_not_verify(self, db_session):
        """被抹除（erased_at 置位）的文件不构成有效证据（P2-2）。"""
        user = await _make_user(db_session)
        task, _file_id = await _add_and_link(db_session, user.id, erased_at=_BASE - timedelta(minutes=1))

        page = await OutcomeLedgerService(db_session).query(user_id=user.id)
        entry = [e for e in page.items if e.source is OutcomeSource.TASK_COMPLETION][0]
        assert entry.truth_class is TruthClass.SELF_REPORTED

    async def test_soft_deleted_link_does_not_verify(self, db_session):
        """TaskDocument 软删除后关联失效 → 证据降级（关联性以有效挂载为准）。"""
        user = await _make_user(db_session)
        file_row, file_id = _stored_file(user.id)
        task = _evidence_task(
            user.id, [{"evidence_kind": "artifact", "ref": f"document://{file_id}", "description": None}]
        )
        db_session.add_all([file_row, task])
        await db_session.flush()
        link = TaskDocument(task_id=task.id, file_id=file_id, linked_by="user")
        link.deleted_at = _BASE
        db_session.add(link)
        await db_session.commit()

        page = await OutcomeLedgerService(db_session).query(user_id=user.id)
        entry = [e for e in page.items if e.source is OutcomeSource.TASK_COMPLETION][0]
        assert entry.truth_class is TruthClass.SELF_REPORTED


class TestFocusTimeDirection:
    """R2 P2-3 返修：完成之后开始的 focus 会话不得追溯升级（truth 时间方向）。"""

    async def test_focus_started_after_completion_never_upgrades(self, db_session):
        user = await _make_user(db_session)
        task = _task(user.id, completed_at=_BASE, actual_minutes=30)
        db_session.add(task)
        await db_session.flush()
        # 完成后 2 小时才开始、40 分钟的会话：即使覆盖分钟达标也不算
        db_session.add(_focus(user.id, task_id=task.id, duration=40, at=_BASE + timedelta(hours=2, minutes=40)))
        await db_session.commit()

        page = await OutcomeLedgerService(db_session).query(user_id=user.id)
        entry = [e for e in page.items if e.source is OutcomeSource.TASK_COMPLETION][0]
        assert entry.truth_class is TruthClass.SELF_REPORTED
        assert not any(e.source == "focus_session" for e in entry.evidence)

    async def test_focus_overlapping_completion_still_counts(self, db_session):
        """开始于完成前、结束于完成后的会话与工作窗口重叠 → 仍计入。"""
        user = await _make_user(db_session)
        task = _task(user.id, completed_at=_BASE, actual_minutes=30)
        db_session.add(task)
        await db_session.flush()
        overlap = FocusSession(
            user_id=user.id,
            task_id=task.id,
            start_time=_BASE - timedelta(minutes=25),
            end_time=_BASE + timedelta(minutes=10),
            duration_minutes=35,
            status=FocusStatus.COMPLETED,
        )
        db_session.add(overlap)
        await db_session.commit()

        page = await OutcomeLedgerService(db_session).query(user_id=user.id)
        entry = [e for e in page.items if e.source is OutcomeSource.TASK_COMPLETION][0]
        assert entry.truth_class is TruthClass.ACTUAL

    async def test_focus_starting_exactly_at_completion_does_not_count(self, db_session):
        """边界：start_time == completed_at 不满足严格早于（start < completed_at）。"""
        user = await _make_user(db_session)
        task = _task(user.id, completed_at=_BASE, actual_minutes=30)
        db_session.add(task)
        await db_session.flush()
        db_session.add(
            FocusSession(
                user_id=user.id,
                task_id=task.id,
                start_time=_BASE,
                end_time=_BASE + timedelta(minutes=40),
                duration_minutes=40,
                status=FocusStatus.COMPLETED,
            )
        )
        await db_session.commit()

        page = await OutcomeLedgerService(db_session).query(user_id=user.id)
        entry = [e for e in page.items if e.source is OutcomeSource.TASK_COMPLETION][0]
        assert entry.truth_class is TruthClass.SELF_REPORTED


class TestPaginationAndIdempotency:
    async def test_keyset_walks_all_outcomes_no_dup_no_miss(self, db_session):
        user = await _make_user(db_session)
        rows = []
        for i in range(12):
            ts = _BASE - timedelta(minutes=i)
            task = _task(user.id, completed_at=ts)
            rows.append(task)
            rows.append(_focus(user.id, at=ts + timedelta(seconds=1)))
        db_session.add_all(rows)
        await db_session.commit()

        service = OutcomeLedgerService(db_session)
        seen: list[str] = []
        cursor = None
        pages = 0
        while True:
            page = await service.query(user_id=user.id, limit=5, cursor=cursor)
            seen.extend(entry.key for entry in page.items)
            pages += 1
            cursor = page.next_cursor
            if cursor is None:
                break
            assert pages < 20
        assert len(seen) == len(set(seen)) == 24
        counts = await service.count_by_source(user_id=user.id)
        assert counts[OutcomeSource.TASK_COMPLETION.value] == 12
        assert counts[OutcomeSource.FOCUS_SESSION.value] == 12

    async def test_single_stream_dominant_walk_reaches_the_end(self, db_session):
        """回归（live smoke 发现）：单流占优时 30 个 focus、limit=25 必须翻到 30。

        旧实现在 merged == limit 且流未取尽时误判流尽（next_cursor=None，
        live PG 上 68 条只翻到 50）。取 limit+1 作「未取尽」探针后修复。
        """
        user = await _make_user(db_session)
        db_session.add_all([_focus(user.id, at=_BASE - timedelta(minutes=i)) for i in range(30)])
        await db_session.commit()

        service = OutcomeLedgerService(db_session)
        seen: list[str] = []
        cursor = None
        while True:
            page = await service.query(user_id=user.id, limit=25, cursor=cursor)
            seen.extend(entry.key for entry in page.items)
            cursor = page.next_cursor
            if cursor is None:
                break
        assert len(seen) == len(set(seen)) == 30

    async def test_exactly_full_page_has_no_cursor_when_exhausted(self, db_session):
        """恰好 limit 条：满页但流尽 → next_cursor=None（不伪造下一页）。"""
        user = await _make_user(db_session)
        db_session.add_all([_focus(user.id, at=_BASE - timedelta(minutes=i)) for i in range(25)])
        await db_session.commit()

        page = await OutcomeLedgerService(db_session).query(user_id=user.id, limit=25)
        assert len(page.items) == 25
        assert page.next_cursor is None

    async def test_same_cursor_returns_identical_page(self, db_session):
        """幂等：重复聚合不重复计数——同输入重复查询返回同页同 id。"""
        user = await _make_user(db_session)
        db_session.add_all([_task(user.id, completed_at=_BASE), _focus(user.id, at=_BASE)])
        await db_session.commit()

        service = OutcomeLedgerService(db_session)
        page1 = await service.query(user_id=user.id, limit=1)
        page2 = await service.query(user_id=user.id, limit=1, cursor=page1.next_cursor)
        page2_again = await service.query(user_id=user.id, limit=1, cursor=page1.next_cursor)
        assert [(e.outcome_id, e.key) for e in page2.items] == [(e.outcome_id, e.key) for e in page2_again.items]
        assert page2.next_cursor == page2_again.next_cursor

    async def test_requery_first_page_is_stable(self, db_session):
        user = await _make_user(db_session)
        db_session.add_all([_task(user.id, completed_at=_BASE), _focus(user.id, at=_BASE)])
        await db_session.commit()

        service = OutcomeLedgerService(db_session)
        p1 = await service.query(user_id=user.id)
        p2 = await service.query(user_id=user.id)
        assert [e.outcome_id for e in p1.items] == [e.outcome_id for e in p2.items]

    async def test_truth_filter_pages_do_not_underfill_across_batches(self, db_session):
        """truth 过滤在流内按批推进：10 个 self_reported 之后 2 个 actual，
        limit=2 的 actual 查询仍能翻到深处的 actual（不因首批全滤而漏页）。"""
        user = await _make_user(db_session)
        rows = []
        for i in range(10):
            rows.append(_task(user.id, completed_at=_BASE - timedelta(minutes=i)))
        good_task = _task(user.id, completed_at=_BASE - timedelta(minutes=30), actual_minutes=60)
        rows.append(good_task)
        rows.append(_focus(user.id, task_id=None, duration=40, at=_BASE - timedelta(minutes=31)))
        db_session.add_all(rows)
        await db_session.flush()
        good_focus = _focus(user.id, task_id=good_task.id, duration=40, at=_BASE - timedelta(minutes=30))
        db_session.add(good_focus)
        await db_session.commit()

        service = OutcomeLedgerService(db_session)
        page = await service.query(user_id=user.id, truth_class=TruthClass.ACTUAL, source=OutcomeSource.TASK_COMPLETION)
        assert len(page.items) == 1
        assert page.items[0].source_id == str(good_task.id)

    # ------------------------------------------------------------------
    # R2 P1 返修回归：跨流同刻 tie 的 keyset 分页（旧实现剥前缀比较裸 UUID
    # → 页边界落在外流同刻条目上时高前缀流行重取 → 跨页重复交付）。
    # ------------------------------------------------------------------

    @staticmethod
    def _tie_dataset(user_id, *, at):
        """五流各一行、occurred_at **精确同刻**的数据集（返回 (行, 全局键谓词)）。"""
        node_id = uuid4()
        return {
            OutcomeSource.TASK_COMPLETION: _task(user_id, completed_at=at),
            OutcomeSource.STUDY_RECORD: _study(
                user_id, node_id=node_id, task_id=None, record_type="task_complete", at=at
            ),
            OutcomeSource.QUIZ_FEEDBACK: _quiz(user_id, node_id=node_id, at=at),
            OutcomeSource.FOCUS_SESSION: _focus(user_id, at=at),
            OutcomeSource.BEHAVIORAL: _behavioral(user_id, at=at),
        }

    async def test_cross_stream_same_timestamp_walk_delivers_each_row_exactly_once(self, db_session):
        """全五流两档时刻精确同刻（10 行、每时刻 5-way tie），limit=1 全量翻页：
        每条恰一次、无重无漏、全局序严格降序。limit=1 使页边界必然落在每个
        同刻条目上（含全部 4 个「外流锚点 × 高前缀流」重复触发组合）。"""
        user = await _make_user(db_session)
        t_hi, t_lo = _BASE, _BASE - timedelta(hours=1)
        rows = list(self._tie_dataset(user_id=user.id, at=t_hi).values()) + list(
            self._tie_dataset(user_id=user.id, at=t_lo).values()
        )
        db_session.add_all(rows)
        await db_session.commit()

        service = OutcomeLedgerService(db_session)
        seen: list = []
        cursor = None
        pages = 0
        while True:
            page = await service.query(user_id=user.id, limit=1, cursor=cursor)
            seen.extend(page.items)
            pages += 1
            cursor = page.next_cursor
            if cursor is None:
                break
            assert pages < 30

        keys = [entry.key for entry in seen]
        assert len(keys) == len(set(keys)) == 10  # 每条恰一次
        assert {entry.source for entry in seen} == set(OutcomeSource)  # 五流全在
        for source in OutcomeSource:
            assert sum(1 for e in seen if e.source is source) == 2
        # 全局序：(occurred_at, key) 严格降序（tie 处按 '<source>:<id>' 字典序）
        for prev, cur in zip(seen, seen[1:], strict=False):
            assert (prev.occurred_at, prev.key) > (cur.occurred_at, cur.key)

    @pytest.mark.parametrize(
        "anchor_source",
        [
            OutcomeSource.STUDY_RECORD,
            OutcomeSource.QUIZ_FEEDBACK,
            OutcomeSource.FOCUS_SESSION,
            OutcomeSource.BEHAVIORAL,
        ],
    )
    async def test_tie_page_boundary_does_not_redeliver_task_stream(self, db_session, anchor_source):
        """页边界锚点 = 词序更小前缀的同刻流（study/quiz/focus/behavioral）且
        同刻存在 task_completion 行：下页不得重取 task（R2 复现链的机制级钉死）。

        旧实现：task 流 keyset 用裸 id 与 '<anchor_source>:<id>' 比较 → 任何
        UUID 都小于该带前缀键 → 同刻 task 行重进 merged → 重复交付。
        """
        user = await _make_user(db_session)
        filler_source = (
            OutcomeSource.STUDY_RECORD if anchor_source is OutcomeSource.FOCUS_SESSION else OutcomeSource.FOCUS_SESSION
        )
        at = _BASE
        below = _BASE - timedelta(hours=1)
        rows_by_source = self._tie_dataset(user_id=user.id, at=at)
        kept = {
            OutcomeSource.TASK_COMPLETION: rows_by_source[OutcomeSource.TASK_COMPLETION],
            anchor_source: rows_by_source[anchor_source],
        }
        below_rows = self._tie_dataset(user_id=user.id, at=below)
        db_session.add_all([*kept.values(), below_rows[filler_source]])
        await db_session.commit()

        service = OutcomeLedgerService(db_session)
        page1 = await service.query(user_id=user.id, limit=2)
        # 同刻处 'task_completion:' 前缀词序最大 → 第一页 = [task@T, anchor@T]
        assert [e.source for e in page1.items] == [OutcomeSource.TASK_COMPLETION, anchor_source]
        assert page1.next_cursor is not None

        page2 = await service.query(user_id=user.id, limit=2, cursor=page1.next_cursor)
        # 关键断言：下页只有 T-1h 的 filler 行——task@T 不得重取
        assert [e.source for e in page2.items] == [filler_source]
        assert page2.items[0].occurred_at == below
        assert page2.next_cursor is None

    async def test_tie_walk_matches_single_shot_full_query(self, db_session):
        """翻页全量 == 一次性大页查询：同刻 tie 下两种读取路径条目一致（不重不漏
        的等价性交叉验证）。"""
        user = await _make_user(db_session)
        t_hi, t_lo = _BASE, _BASE - timedelta(hours=1)
        rows = list(self._tie_dataset(user_id=user.id, at=t_hi).values()) + list(
            self._tie_dataset(user_id=user.id, at=t_lo).values()
        )
        db_session.add_all(rows)
        await db_session.commit()

        service = OutcomeLedgerService(db_session)
        one_shot = await service.query(user_id=user.id, limit=50)
        walked: list = []
        cursor = None
        pages = 0
        while True:
            page = await service.query(user_id=user.id, limit=3, cursor=cursor)
            walked.extend(page.items)
            pages += 1
            cursor = page.next_cursor
            if cursor is None:
                break
            assert pages < 30  # 游标不收敛（同条目重复翻页）即失败，防止死循环掩盖根因
        assert [e.key for e in walked] == [e.key for e in one_shot.items]
        assert [e.outcome_id for e in walked] == [e.outcome_id for e in one_shot.items]


class TestFiltersAndIsolation:
    async def test_source_filter(self, db_session):
        user = await _make_user(db_session)
        db_session.add_all([_task(user.id, completed_at=_BASE), _focus(user.id, at=_BASE)])
        await db_session.commit()

        page = await OutcomeLedgerService(db_session).query(user_id=user.id, source=OutcomeSource.FOCUS_SESSION)
        assert [e.source for e in page.items] == [OutcomeSource.FOCUS_SESSION]

    async def test_truth_class_actual_excludes_self_reported_completions(self, db_session):
        user = await _make_user(db_session)
        db_session.add_all([_task(user.id, completed_at=_BASE), _focus(user.id, at=_BASE)])
        await db_session.commit()

        page = await OutcomeLedgerService(db_session).query(user_id=user.id, truth_class=TruthClass.ACTUAL)
        assert page.items
        assert all(e.truth_class is TruthClass.ACTUAL for e in page.items)
        assert OutcomeSource.TASK_COMPLETION not in {e.source for e in page.items}

    async def test_truth_class_non_actual_drops_server_sources(self, db_session):
        """self_reported 过滤 = 只剩自报完成（服务器记录源不产 self_reported）。"""
        user = await _make_user(db_session)
        db_session.add_all([_task(user.id, completed_at=_BASE), _focus(user.id, at=_BASE)])
        await db_session.commit()

        page = await OutcomeLedgerService(db_session).query(user_id=user.id, truth_class=TruthClass.SELF_REPORTED)
        assert {e.source for e in page.items} == {OutcomeSource.TASK_COMPLETION}

    async def test_user_isolation(self, db_session):
        user_a = await _make_user(db_session)
        user_b = await _make_user(db_session)
        db_session.add_all([_task(user_a.id, completed_at=_BASE), _focus(user_a.id, at=_BASE)])
        await db_session.commit()

        service = OutcomeLedgerService(db_session)
        page_b = await service.query(user_id=user_b.id, limit=50)
        assert page_b.items == ()
        counts_b = await service.count_by_source(user_id=user_b.id)
        assert set(counts_b.values()) == {0}
        coverage_b = await service.truth_coverage(user_id=user_b.id)
        assert coverage_b["total"] == 0
        assert coverage_b["actual_ratio"] is None

    async def test_exclude_seed_cohort_filters_guest_rows(self, db_session):
        guest = await _make_user(db_session, registration_source="guest")
        human = await _make_user(db_session)
        db_session.add_all([_focus(guest.id, at=_BASE), _focus(human.id, at=_BASE)])
        await db_session.commit()

        service = OutcomeLedgerService(db_session)
        guest_page = await service.query(user_id=guest.id, exclude_seed_cohort=True)
        assert guest_page.items == ()
        guest_page_own = await service.query(user_id=guest.id)  # 默认关闭：guest 查自己合法
        assert len(guest_page_own.items) == 1
        human_page = await service.query(user_id=human.id, exclude_seed_cohort=True)
        assert len(human_page.items) == 1

    async def test_excluded_cohort_vocabulary_frozen(self, db_session):
        """R2 返修（P2-5，变异 M6）：cohort 词表字面钉死 + 与 leaderboard 双向对照。

        与 leaderboard 的「一致」不能只是拷贝约定——两侧任一漂移本测试必红。
        """
        from app.services.leaderboard_service import LeaderboardService

        assert EXCLUDED_COHORT_REGISTRATION_SOURCES == ("guest", "seed")
        assert LeaderboardService.EXCLUDED_COHORT_REGISTRATION_SOURCES == ("guest", "seed")
        assert EXCLUDED_COHORT_REGISTRATION_SOURCES == LeaderboardService.EXCLUDED_COHORT_REGISTRATION_SOURCES

    async def test_quiz_stream_survives_dirty_meta(self, db_session):
        """R2 P3-1 返修：quiz meta 是非受信 JSON——脏 task_id/node_id 降级为空
        关联，不得让该用户整个 query() 崩溃。"""
        user = await _make_user(db_session)
        db_session.add(
            ExpansionFeedback(
                user_id=user.id,
                trigger_node_id=uuid4(),
                feedback_type="implicit",
                implicit_score=1.0,
                meta_data={"source": "quiz_passed", "task_id": "not-a-uuid", "node_id": "!!!garbage"},
                created_at=_BASE,
            )
        )
        await db_session.commit()

        page = await OutcomeLedgerService(db_session).query(user_id=user.id)
        assert len(page.items) == 1
        assert page.items[0].correlation == {"node_id": "", "task_id": ""}  # 降级不炸

    async def test_time_window(self, db_session):
        user = await _make_user(db_session)
        db_session.add_all(
            [
                _focus(user.id, at=_BASE - timedelta(hours=3)),
                _focus(user.id, at=_BASE),
            ]
        )
        await db_session.commit()

        service = OutcomeLedgerService(db_session)
        page = await service.query(user_id=user.id, since=_BASE - timedelta(hours=1), until=_BASE + timedelta(hours=1))
        assert len(page.items) == 1


class TestTruthCoverage:
    async def test_coverage_counts_the_click_vs_actual_gap(self, db_session):
        user = await _make_user(db_session)
        click_task = _task(user.id, completed_at=_BASE, actual_minutes=30)
        proven_task = _task(user.id, completed_at=_BASE - timedelta(hours=1), actual_minutes=60)
        db_session.add_all([click_task, proven_task])
        await db_session.flush()
        db_session.add(_focus(user.id, task_id=proven_task.id, duration=45, at=_BASE - timedelta(hours=1)))
        await db_session.commit()

        coverage = await OutcomeLedgerService(db_session).truth_coverage(user_id=user.id)
        assert coverage["total"] == 2
        assert coverage["actual"] == 1
        assert coverage["self_reported"] == 1
        assert coverage["unknown"] == 0
        assert coverage["actual_ratio"] == 0.5

    async def test_coverage_counts_broken_row_as_unknown(self, db_session):
        user = await _make_user(db_session)
        broken = _task(user.id, completed_at=None)  # status=COMPLETED 但无 completed_at
        db_session.add(broken)
        await db_session.commit()

        coverage = await OutcomeLedgerService(db_session).truth_coverage(user_id=user.id)
        assert coverage["unknown"] == 1
        assert coverage["actual_ratio"] == 0.0
