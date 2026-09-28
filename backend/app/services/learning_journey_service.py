"""V4-U10 · 资料→错题→练习→检验旅程装配服务（learning-journey 只读 + 单点写）。

规格：``v4/04_tasks/cards/V4-U10.md``（locks: ui-learning）+
``v4/02_design/SCREEN_FAMILIES.md`「星图 / 学习 / 错题 / 资料」。

数据源只接既有权威，不造第二真值表：

- 目标行 = ``tasks``（I07 策略块 ``guide_json["v4_hybrid_policy"]`` = 脚手架/
  检验判分权威；解析降级语义归 :func:`hybrid_policy.parse_policy_block`）；
- 资料 = ``task_documents → stored_files``（解析状态权威 = ``stored_files.status``
  + ``error_message``，经 :func:`documents._document_stage` 同集映射到本卡封闭
  词表——只消费同一行，不复制状态机）；
- 错题 = ``error_records``（归属用户自有材料；旅程简报**不携带**
  ``correct_answer``/``user_answer``/``latest_analysis``——最小暴露面）；
- 练习证据 = 关联错题的既有 SM-2 复习计数（``review_count > 0``）——检验推进
  的 ``evidence_supported`` 单一事实，其余证据面（尝试质量）归后续卡。

写路径只有一个：用户显式选择「检验」且证据支持时，经
:func:`hybrid_policy.next_scaffold_step` 推进脚手架并写回
``guide_json["v4_hybrid_policy"]["scaffold"]``（I07 权威位的版本化子键，零迁移）。
判分零写（检验是链终点，通过/失败归既有判分与 SM-2 面）。

跨用户语义沿用 house 先例（episode_resume_service/runs.py）：对象不存在/已删/
跨用户一律 404 语义 reason（``object_not_found``/``cross_object_access``），
不泄露存在性。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.hybrid_policy import (
    SCAFFOLD_STAGE_INDEPENDENT_CHECK,
    ScaffoldState,
    apply_scaffold_decision,
    parse_policy_block,
)
from app.core.learning_journey import (
    LEARNING_JOURNEY_SCHEMA_VERSION,
    PARSE_FAILED,
    PARSE_PARSED,
    PARSE_PENDING,
    PARSE_UNSUPPORTED,
    JourneySourceRef,
    assert_client_payload_clean,
    grade_independent_check,
    journey_segment_for_scaffold,
    redact_for_client,
    request_independent_check,
)
from app.models.error_book import ErrorRecord
from app.models.file_storage import StoredFile
from app.models.task import Task
from app.models.task_document import TaskDocument

#: 装配降级/警示 reason（封闭集；进 payload ``warnings``，不静默）。
JOURNEY_WARNINGS: frozenset[str] = frozenset(
    {
        "policy_block_degraded",
        "policy_block_missing",
        "errors_unlinked_no_node",
        "check_authority_missing",
        "check_question_missing",
    }
)

#: ``stored_files.status`` → 本卡解析状态词表的对齐断言集（真实状态面采样）。
_STORED_STATUS_PARSED = frozenset({"processed", "done"})
_STORED_STATUS_PENDING = frozenset({"uploading", "uploaded", "queued", "processing"})


def _stored_file_parse_face(status: str | None, mime_type: str | None, error_message: str | None) -> dict[str, Any]:
    """stored_files 真实行 → 旅程简报的解析状态面（**无 text 键**——文件级状态
    面不含正文；伪造解析在本面结构上不可能）。内容面（含 text 的解析结果与手输
    替代）归 :class:`learning_journey.MaterialParseOutcome` 与移动端手输流。

    - processed/done → parsed；
    - failed → failed（reason=error_message 截断）；
    - 图片 mime → unsupported 优先（OCR 不可用面，手输替代，不假装图片已识别）；
    - uploading/uploaded/queued/processing → pending（在途）；
    - 其余/未知 → unsupported（保守：不宣称已解析）。
    """
    normalized = (status or "").strip().lower()
    mime = (mime_type or "").strip().lower()
    is_image = mime.startswith("image/")
    if normalized in _STORED_STATUS_PARSED:
        return {"status": PARSE_PARSED, "reason": None, "manual_input_required": False}
    if normalized == "failed":
        reason = (error_message or "document_parse_failed")[:200]
        return {"status": PARSE_FAILED, "reason": reason, "manual_input_required": True}
    if normalized in _STORED_STATUS_PENDING:
        # 图片在途/未完成 OCR 的按不支持处理（不假装图片已识别）。
        if is_image:
            return {"status": PARSE_UNSUPPORTED, "reason": "ocr_unavailable_for_image", "manual_input_required": True}
        return {"status": PARSE_PENDING, "reason": "document_processing", "manual_input_required": False}
    return {
        "status": PARSE_UNSUPPORTED,
        "reason": f"unrecognized_status:{normalized or 'none'}",
        "manual_input_required": True,
    }


@dataclass(frozen=True)
class JourneyBuildResult:
    """一次旅程装配结果（``view=None`` + reason = 类型化降级，视图不出）。"""

    view: dict[str, Any] | None
    reason_code: str = "ok"
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CheckEnterResult:
    """一次「检验」入口结果（放行带题面 / 或类型化暂缓 reason）。"""

    view: dict[str, Any]
    scaffold_persisted: bool


class LearningJourneyService:
    """目标上下文旅程装配（读模型 + 单点脚手架推进写）。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── 权威行 ────────────────────────────────────────────────────────

    async def _load_task(self, *, user_id: UUID | str, task_id: UUID | str) -> tuple[Task | None, str]:
        task = (
            await self.db.execute(select(Task).where(Task.id == task_id, Task.deleted_at.is_(None)))
        ).scalar_one_or_none()
        if task is None:
            return None, "object_not_found"
        if str(task.user_id) != str(user_id):
            logger.warning(
                "LearningJourney 跨对象访问拒绝 (task_id={}, caller={}, owner={})",
                task_id,
                user_id,
                task.user_id,
            )
            return None, "cross_object_access"
        return task, "ok"

    def _resolve_scaffold(self, task: Task) -> tuple[ScaffoldState, str | None, dict[str, Any] | None]:
        """I07 策略块 → (脚手架当前态, 警示 reason, 检验判分权威子结构)。

        降级不臆测：缺块/脏块回 example/full + 警示；判分权威缺省 None。
        """
        block, degrade = parse_policy_block(task.guide_json)
        if block is not None:
            return block.scaffold, None, block.independent_check
        if degrade is None:
            return ScaffoldState(), "policy_block_missing", None
        return ScaffoldState(), "policy_block_degraded", None

    # ── 旅程装配（读模型） ────────────────────────────────────────────

    async def build_goal_journey(self, *, user_id: UUID | str, task_id: UUID | str) -> JourneyBuildResult:
        task, reason = await self._load_task(user_id=user_id, task_id=task_id)
        if task is None:
            return JourneyBuildResult(view=None, reason_code=reason)

        warnings: list[str] = []
        scaffold, warn, check_authority = self._resolve_scaffold(task)
        if warn is not None:
            warnings.append(warn)

        materials = await self._load_materials(task)
        if task.knowledge_node_id is None:
            warnings.append("errors_unlinked_no_node")
        errors, evidence_supported = await self._load_linked_errors(task)

        check_view: dict[str, Any] | None = None
        if check_authority is None:
            warnings.append("check_authority_missing")
        else:
            question = check_authority.get("question")
            if not isinstance(question, str) or not question.strip():
                warnings.append("check_question_missing")
            else:
                check_view = {"question": question}

        view: dict[str, Any] = {
            "schema_version": LEARNING_JOURNEY_SCHEMA_VERSION,
            "goal": {"task_id": str(task.id), "title": task.title},
            "scaffold": {
                "stage": scaffold.stage,
                "hint_level": scaffold.hint_level,
                "segment": journey_segment_for_scaffold(scaffold.stage),
            },
            "materials": materials,
            "errors": errors,
            "practice": {"evidence_supported": evidence_supported},
            "check": check_view,
        }
        clean, removed = redact_for_client(view)
        if removed:
            logger.warning("LearningJourney 载荷红化触发 paths={}", removed)
        assert_client_payload_clean(clean)
        return JourneyBuildResult(view=clean, reason_code="ok", warnings=tuple(warnings))

    async def _load_materials(self, task: Task) -> list[dict[str, Any]]:
        rows = (
            await self.db.execute(
                select(TaskDocument, StoredFile)
                .join(StoredFile, StoredFile.id == TaskDocument.file_id)
                .where(
                    TaskDocument.task_id == task.id,
                    StoredFile.not_deleted_filter(),
                    StoredFile.lifecycle_status == "active",
                )
                .order_by(TaskDocument.created_at.asc())
            )
        ).all()
        materials: list[dict[str, Any]] = []
        for _link, file_row in rows:
            parse_face = _stored_file_parse_face(file_row.status, file_row.mime_type, file_row.error_message)
            source = JourneySourceRef(
                source_id=str(file_row.id),
                source_version=_row_version(file_row.updated_at),
                source_kind="document",
            )
            materials.append(
                {
                    "file_name": file_row.file_name,
                    "mime_type": file_row.mime_type,
                    "source": source.to_dict(),
                    "parse": parse_face,
                }
            )
        return materials

    async def _load_linked_errors(self, task: Task) -> tuple[list[dict[str, Any]], bool]:
        """目标关联错题（经既有知识节点链路；无节点 → 空 + 不硬凑）。

        简报最小暴露面：id/subject/chapter/question_text/mastery/review 计数；
        **不携带** ``correct_answer``/``user_answer``/``latest_analysis``。
        """
        if task.knowledge_node_id is None:
            return [], False
        node_id = task.knowledge_node_id
        rows = (
            (
                await self.db.execute(
                    select(ErrorRecord)
                    .where(
                        ErrorRecord.user_id == task.user_id,
                        ErrorRecord.is_deleted.is_(False),  # ErrorRecord 用真实布尔列（非软删 mixin）
                    )
                    .order_by(ErrorRecord.updated_at.desc())
                    .limit(200)
                )
            )
            .scalars()
            .all()
        )
        linked = [
            row
            for row in rows
            if (row.affected_node_id == node_id) or (node_id in (row.linked_knowledge_node_ids or []))
        ]
        evidence_supported = any((row.review_count or 0) > 0 for row in linked)
        briefs: list[dict[str, Any]] = []
        for row in linked[:20]:
            source = JourneySourceRef(
                source_id=str(row.id),
                source_version=_row_version(row.updated_at),
                source_kind="error_record",
            )
            briefs.append(
                {
                    "id": str(row.id),
                    "subject_code": row.subject_code,
                    "chapter": row.chapter,
                    "question_text": (row.question_text or "")[:280],
                    "mastery_level": row.mastery_level,
                    "review_count": int(row.review_count or 0),
                    "source": source.to_dict(),
                }
            )
        return briefs, evidence_supported

    # ── 检验入口（唯一写路径：脚手架推进） ────────────────────────────

    async def enter_check(self, *, user_id: UUID | str, task_id: UUID | str) -> tuple[CheckEnterResult | None, str]:
        task, reason = await self._load_task(user_id=user_id, task_id=task_id)
        if task is None:
            return None, reason
        scaffold, _warn, check_authority = self._resolve_scaffold(task)
        if check_authority is None:
            return (
                CheckEnterResult(
                    view={
                        "schema_version": LEARNING_JOURNEY_SCHEMA_VERSION,
                        "check_available": False,
                        "hold_reason": "HOLD.check_authority_missing",
                    },
                    scaffold_persisted=False,
                ),
                "ok",
            )

        _errors, evidence_supported = await self._load_linked_errors(task)
        decision, hold_reason = request_independent_check(
            stage=scaffold.stage,
            hint_level=scaffold.hint_level,
            evidence_supported=evidence_supported,
        )

        persisted = False
        if hold_reason is None and decision.stage != scaffold.stage:
            task.guide_json = apply_scaffold_decision(task.guide_json or {}, decision)
            await self.db.commit()
            persisted = True

        question = check_authority.get("question")
        check_available = (
            hold_reason is None
            and decision.stage == SCAFFOLD_STAGE_INDEPENDENT_CHECK
            and isinstance(question, str)
            and bool(question.strip())
        )
        view: dict[str, Any] = {
            "schema_version": LEARNING_JOURNEY_SCHEMA_VERSION,
            "check_available": check_available,
            "scaffold": {"stage": decision.stage, "hint_level": decision.hint_level, "reason": decision.reason},
        }
        if check_available:
            view["question"] = question
        if hold_reason is not None:
            view["hold_reason"] = hold_reason
        assert_client_payload_clean(view)
        return CheckEnterResult(view=view, scaffold_persisted=persisted), "ok"

    # ── 检验判分（零写；客户端载荷零答案材料） ────────────────────────

    async def grade_check(
        self, *, user_id: UUID | str, task_id: UUID | str, submitted: Any
    ) -> tuple[dict[str, Any] | None, str]:
        task, reason = await self._load_task(user_id=user_id, task_id=task_id)
        if task is None:
            return None, reason
        _scaffold, _warn, check_authority = self._resolve_scaffold(task)
        if check_authority is None:
            payload = {
                "schema_version": LEARNING_JOURNEY_SCHEMA_VERSION,
                "graded": False,
                "correct": None,
                "reason": "HOLD.scaffold_not_at_check",
            }
            assert_client_payload_clean(payload)
            return payload, "ok"
        result = grade_independent_check(check_authority, submitted)
        return result.to_client_payload(), "ok"


def _row_version(updated_at: datetime | None) -> str:
    """真实行的版本戳（updated_at ISO 串；装配时点读出，不臆测）。"""
    if updated_at is None:
        return "v0"
    return updated_at.isoformat()


__all__ = [
    "CheckEnterResult",
    "JOURNEY_WARNINGS",
    "JourneyBuildResult",
    "LearningJourneyService",
]
