"""V4-U10 · 旅程装配服务层守卫（sqlite 隔离，不触 dev DB）。

覆盖验收项（卡 V4-U10，每条一正一反可失败）：
1. **不会从目标跳入无上下文的工具空页**：装配视图自带目标上下文 + 检验入口
   证据门（无复习证据 → HOLD + 脚手架不推进；有证据 → 放行出题面）；出题
   证据门同时覆盖 GET 读模型与判分面（未到检验段 → check 面不出、提交不判
   分——R1 F-1 收口）；
2. **答案不泄漏到检验用户可读状态**：判分响应零答案材料（答案留在服务端
   guide_json）；跨用户 404 不泄露存在性；
3. **真实文件/图片失败无伪造解析，来源版本正确**：materials 面的解析状态从
   stored_files 真实行映射（failed 无文本、图片→unsupported 手输替代、在途
   →pending），来源版本 = 行 updated_at 装配时点读出。
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from app.core.hybrid_policy import GOAL_PURPOSE_BLOCK_KEY, HYBRID_POLICY_VERSION
from app.core.learning_journey import LEARNING_JOURNEY_SCHEMA_VERSION, assert_client_payload_clean
from app.models.error_book import ErrorRecord
from app.models.file_storage import StoredFile
from app.models.task import Task, TaskStatus, TaskType
from app.models.task_document import TaskDocument
from app.models.user import User
from app.services.learning_journey_service import LearningJourneyService

pytestmark = pytest.mark.asyncio

_CHECK_QUESTION = "独立解释：为什么滑动摩擦力与接触面积无关？"
_CHECK_ANSWER = "压力决定摩擦力，而非面积"


def _guide_with_check(*, question: str = _CHECK_QUESTION, answer: str = _CHECK_ANSWER, stage: str = "attempt") -> dict:
    return {
        GOAL_PURPOSE_BLOCK_KEY: {
            "schema_version": HYBRID_POLICY_VERSION,
            "goal_purpose": "mastery",
            "human_required": True,
            "scaffold": {"stage": stage, "hint_level": "full"},
            "independent_check": {
                "kind": "independent_check",
                "question": question,
                "answer": answer,
                "explanation": "摩擦力公式 μN 不含面积项。",
            },
        }
    }


async def _make_user(db_session) -> User:
    user = User(
        username=f"u10{uuid4().hex[:8]}",
        email=f"u10{uuid4().hex[:8]}@t.co",
        hashed_password="x",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _make_task(db_session, user: User, *, guide_json: dict | None = None, node_id=None) -> Task:
    task = Task(
        user_id=user.id,
        title="力学单元巩固",
        type=TaskType.LEARNING,
        estimated_minutes=30,
        status=TaskStatus.IN_PROGRESS,
        guide_json=guide_json,
        knowledge_node_id=node_id,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


async def _attach_file(
    db_session,
    task: Task,
    *,
    status: str,
    mime: str = "application/pdf",
    error: str | None = None,
    updated_at: datetime | None = None,
) -> StoredFile:
    stored = StoredFile(
        user_id=task.user_id,
        file_name=f"material-{uuid4().hex[:6]}.bin",
        mime_type=mime,
        file_size=2048,
        bucket="test",
        object_key=f"u10-{uuid4()}",
        status=status,
        error_message=error,
    )
    db_session.add(stored)
    await db_session.flush()
    if updated_at is not None:
        stored.updated_at = updated_at
        db_session.add(stored)
        await db_session.flush()
    db_session.add(TaskDocument(task_id=task.id, file_id=stored.id, linked_by="user"))
    await db_session.commit()
    await db_session.refresh(stored)
    return stored


async def _add_error(db_session, task: Task, *, node_id, review_count: int = 0) -> ErrorRecord:
    error = ErrorRecord(
        user_id=task.user_id,
        subject_code="physics",
        chapter="摩擦力",
        question_text="斜面上的物体为什么匀速下滑？",
        correct_answer="重力分量与摩擦力平衡",
        linked_knowledge_node_ids=[str(node_id)],
        affected_node_id=node_id,
        mastery_level=0.3,
        review_count=review_count,
    )
    db_session.add(error)
    await db_session.commit()
    await db_session.refresh(error)
    return error


# ---------------------------------------------------------------------------
# 验收1：旅程装配自带目标上下文 + 检验证据门
# ---------------------------------------------------------------------------


async def test_build_journey_carries_goal_context_and_segments(db_session):
    user = await _make_user(db_session)
    task = await _make_task(db_session, user, guide_json=_guide_with_check())
    result = await LearningJourneyService(db_session).build_goal_journey(user_id=user.id, task_id=task.id)

    assert result.reason_code == "ok"
    view = result.view
    assert view is not None
    assert view["schema_version"] == LEARNING_JOURNEY_SCHEMA_VERSION
    assert view["goal"] == {"task_id": str(task.id), "title": "力学单元巩固"}
    assert view["scaffold"]["segment"] == "practice"  # attempt 段主操作是练习，不是检验空页
    assert view["practice"] == {"evidence_supported": False}


async def test_build_journey_cross_user_is_typed_404_not_leaked(db_session):
    owner = await _make_user(db_session)
    stranger = await _make_user(db_session)
    task = await _make_task(db_session, owner, guide_json=_guide_with_check())
    result = await LearningJourneyService(db_session).build_goal_journey(user_id=stranger.id, task_id=task.id)
    # 反（可失败面）：跨用户按 404 语义 reason，视图不出、不泄露存在性。
    assert result.view is None
    assert result.reason_code == "cross_object_access"


async def test_get_journey_check_face_gated_by_scaffold_position(db_session):
    # 反（可失败面，R1 F-1 读模型面）：stage=example + 判分权威齐备 → GET
    # 视图不出题面（题面预告只经 enter_check 证据门放行）。
    user = await _make_user(db_session)
    task = await _make_task(db_session, user, guide_json=_guide_with_check(stage="example"))
    result = await LearningJourneyService(db_session).build_goal_journey(user_id=user.id, task_id=task.id)
    assert result.view is not None
    assert result.view["check"] is None
    assert result.view["scaffold"]["stage"] == "example"
    # 权威在、只是未到检验段——不误报权威/题面缺失警示。
    assert "check_authority_missing" not in result.warnings
    assert "check_question_missing" not in result.warnings

    # 正：脚手架推进到检验段后（enter_check 同款权威位写回），GET 读模型照常带题面。
    reached = await _make_task(db_session, user, guide_json=_guide_with_check(stage="independent_check"))
    result_ok = await LearningJourneyService(db_session).build_goal_journey(user_id=user.id, task_id=reached.id)
    assert result_ok.view is not None
    assert result_ok.view["check"] == {"question": _CHECK_QUESTION}

    # 到段但题面缺失 → 诚实降级警示照常（check None + check_question_missing）。
    guide = _guide_with_check(stage="independent_check")
    del guide[GOAL_PURPOSE_BLOCK_KEY]["independent_check"]["question"]
    no_question = await _make_task(db_session, user, guide_json=guide)
    result_warn = await LearningJourneyService(db_session).build_goal_journey(user_id=user.id, task_id=no_question.id)
    assert result_warn.view is not None
    assert result_warn.view["check"] is None
    assert "check_question_missing" in result_warn.warnings


async def test_enter_check_without_evidence_holds_and_persists_nothing(db_session):
    user = await _make_user(db_session)
    node_id = uuid4()
    task = await _make_task(db_session, user, guide_json=_guide_with_check(), node_id=node_id)
    await _add_error(db_session, task, node_id=node_id, review_count=0)

    result, reason = await LearningJourneyService(db_session).enter_check(user_id=user.id, task_id=task.id)
    assert reason == "ok"
    assert result is not None
    assert result.view["check_available"] is False
    assert result.view["hold_reason"] == "HOLD.evidence_not_supported"
    assert result.scaffold_persisted is False
    await db_session.refresh(task)
    # 脚手架不推进（阶段不跳进检验空页）。
    assert task.guide_json[GOAL_PURPOSE_BLOCK_KEY]["scaffold"]["stage"] == "attempt"


async def test_enter_check_with_review_evidence_advances_and_serves_question(db_session):
    user = await _make_user(db_session)
    node_id = uuid4()
    task = await _make_task(db_session, user, guide_json=_guide_with_check(), node_id=node_id)
    await _add_error(db_session, task, node_id=node_id, review_count=2)

    result, _reason = await LearningJourneyService(db_session).enter_check(user_id=user.id, task_id=task.id)
    assert result is not None
    assert result.view["check_available"] is True
    assert result.view["question"] == _CHECK_QUESTION
    assert result.scaffold_persisted is True
    await db_session.refresh(task)
    assert task.guide_json[GOAL_PURPOSE_BLOCK_KEY]["scaffold"]["stage"] == "independent_check"
    # 写回的是 I07 权威位（guide_json 策略块），答案本体原地保留在服务端。
    assert task.guide_json[GOAL_PURPOSE_BLOCK_KEY]["independent_check"]["answer"] == _CHECK_ANSWER


# ---------------------------------------------------------------------------
# 验收2：判分响应零答案材料
# ---------------------------------------------------------------------------


async def test_submit_check_grades_without_leaking_answer(db_session):
    user = await _make_user(db_session)
    task = await _make_task(db_session, user, guide_json=_guide_with_check(stage="independent_check"))
    payload, reason = await LearningJourneyService(db_session).grade_check(
        user_id=user.id, task_id=task.id, submitted="接触面积越大摩擦力越大"
    )
    assert reason == "ok"
    assert payload is not None
    assert payload["graded"] is True and payload["correct"] is False
    # 反（可失败面）：响应全文不含答案/解析材料；出口探针强制。
    serialized = str(payload)
    assert _CHECK_ANSWER not in serialized
    assert "μN" not in serialized
    assert "answer" not in payload
    assert_client_payload_clean(payload)


async def test_submit_check_correct_and_without_authority_holds(db_session):
    user = await _make_user(db_session)
    task = await _make_task(db_session, user, guide_json=_guide_with_check(stage="independent_check"))
    payload, _ = await LearningJourneyService(db_session).grade_check(
        user_id=user.id, task_id=task.id, submitted=_CHECK_ANSWER
    )
    assert payload is not None and payload["correct"] is True

    legacy = await _make_task(db_session, user, guide_json=None)
    payload, _ = await LearningJourneyService(db_session).grade_check(
        user_id=user.id, task_id=legacy.id, submitted=_CHECK_ANSWER
    )
    # 反（可失败面）：legacy 目标回 example 保守态 → 判分面位置门（R1 F-1）
    # HOLD.scaffold_not_at_check，不猜不伪造判分。
    assert payload is not None and payload["graded"] is False
    assert payload["correct"] is None
    assert payload["reason"] == "HOLD.scaffold_not_at_check"


async def test_submit_check_before_check_stage_rejected_without_verdict(db_session):
    # 反（可失败面，R1 F-1 判分面）：从未 enter（stage=example）+ 判分权威齐备
    # → 提交不判分：无 correct 裁决（correct=true 不可能绕过证据门拿到）。
    user = await _make_user(db_session)
    task = await _make_task(db_session, user, guide_json=_guide_with_check(stage="example"))
    payload, reason = await LearningJourneyService(db_session).grade_check(
        user_id=user.id, task_id=task.id, submitted=_CHECK_ANSWER
    )
    assert reason == "ok"
    assert payload is not None
    assert payload["graded"] is False
    assert payload["correct"] is None
    assert payload["reason"] == "HOLD.scaffold_not_at_check"
    assert "answer" not in payload
    assert _CHECK_ANSWER not in str(payload)


async def test_submit_check_missing_authority_at_check_stage_uses_authority_reason(db_session):
    # 反（可失败面，R1 N-5b）：已到检验段但判分权威子结构缺失 → 词表内专属
    # HOLD.check_authority_missing（缺权威 ≠ 位置不对，不再借用位置 reason）。
    user = await _make_user(db_session)
    guide = _guide_with_check(stage="independent_check")
    del guide[GOAL_PURPOSE_BLOCK_KEY]["independent_check"]
    task = await _make_task(db_session, user, guide_json=guide)
    payload, _ = await LearningJourneyService(db_session).grade_check(
        user_id=user.id, task_id=task.id, submitted=_CHECK_ANSWER
    )
    assert payload is not None
    assert payload["graded"] is False
    assert payload["correct"] is None
    assert payload["reason"] == "HOLD.check_authority_missing"


# ---------------------------------------------------------------------------
# 验收3：材料解析诚实 + 来源版本
# ---------------------------------------------------------------------------


async def test_materials_reflect_real_parse_status_and_source_version(db_session):
    user = await _make_user(db_session)
    task = await _make_task(db_session, user)
    stamp = datetime(2026, 9, 28, 10, 0, 0)
    ok_file = await _attach_file(db_session, task, status="processed", updated_at=stamp)
    failed_file = await _attach_file(db_session, task, status="failed", error="ocr engine timeout")
    image_file = await _attach_file(db_session, task, status="uploaded", mime="image/jpeg")

    result = await LearningJourneyService(db_session).build_goal_journey(user_id=user.id, task_id=task.id)
    view = result.view
    assert view is not None
    parses = {item["file_name"]: item for item in view["materials"]}

    parsed = parses[ok_file.file_name]
    assert parsed["parse"] == {"status": "parsed", "reason": None, "manual_input_required": False}
    assert parsed["source"]["source_version"] == stamp.isoformat()  # 来源版本 = 行真实版本戳
    assert parsed["source"]["source_id"] == str(ok_file.id)

    failed = parses[failed_file.file_name]
    # 反（可失败面）：失败解析无文本 + 需手输替代（伪造解析在结构上不可能）。
    assert failed["parse"]["status"] == "failed"
    assert failed["parse"]["manual_input_required"] is True
    assert "text" not in failed["parse"]
    assert failed["parse"]["reason"] == "ocr engine timeout"

    image = parses[image_file.file_name]
    # 反（可失败面）：图片不假装已识别 → unsupported + 手输替代。
    assert image["parse"]["status"] == "unsupported"
    assert image["parse"]["reason"] == "ocr_unavailable_for_image"
    assert image["parse"]["manual_input_required"] is True


async def test_journey_without_policy_block_degrades_with_warning(db_session):
    user = await _make_user(db_session)
    task = await _make_task(db_session, user, guide_json=None)
    result = await LearningJourneyService(db_session).build_goal_journey(user_id=user.id, task_id=task.id)
    assert result.reason_code == "ok"
    assert result.view is not None
    # legacy 目标：回 example/full 保守态 + 显式警示（不臆测回填、不硬推检验）。
    assert result.view["scaffold"] == {"stage": "example", "hint_level": "full", "segment": "practice"}
    assert "policy_block_missing" in result.warnings
    assert result.view["check"] is None
