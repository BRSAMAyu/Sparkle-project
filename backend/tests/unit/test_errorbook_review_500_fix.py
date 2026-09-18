"""Regression tests: POST /errors/{id}/review 基线双 500（round2 errorbook-review-500-fix）。

两条路径共用 ErrorBookService.submit_review，基线 main@efb1567a 实测复现：

1) 网关 gRPC 桥 500 MissingGreenlet（`greenlet_spawn has not been called`）：
   submit_review 在首次 refresh 之后还有第二次 commit（mastery sync 段）。
   无关联节点时 _attach_no_linked_node_hint 会改写 latest_analysis 并随该
   commit 落库，UPDATE 带服务端生成的 updated_at=now()，flush 后 ORM 实例的
   updated_at 属性被 SQLAlchemy 过期。返回的实例随后在无 greenlet 的同步上下文
   里被读取（gRPC _map_to_proto 的 error.updated_at / FastAPI 响应序列化），
   触发同步刷新 IO → MissingGreenlet → 网关映射 500。

2) 引擎直连 HTTP 500 response 校验失败：同一次提交把只有 linking_hint 的局部
   JSONB 写进 latest_analysis，违反 ErrorAnalysisResult 的必填字段
   （error_type / error_type_label / root_cause / correct_approach /
   study_suggestion），毒化的存量行让后续所有读取都 500。

修法：
  A. _attach_no_linked_node_hint 补齐 schema 必填字段再写（写入点修复）；
  B. submit_review 尾部 commit 后 refresh 返回的 ORM 实例（过期属性兜底）；
  C. ErrorAnalysisResult 对存量局部数据容错（读取面修复）。
"""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.schemas.error_book import ErrorAnalysisResult, ErrorTypeEnum
from app.services.error_book_mastery_sync_service import ErrorBookMasterySyncService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _MissingGreenletLike(Exception):
    """Stands in for sqlalchemy.exc.MissingGreenlet in unit tests."""


class _ExpiringAttrsError:
    """ORM stand-in mimicking post-commit expiry of server-generated columns.

    Every mocked ``db.commit()`` expires all attributes; a subsequent
    synchronous attribute read raises (exactly the async-SQLAlchemy behavior
    that surfaced as ``MissingGreenlet`` in the gRPC servicer). A mocked
    ``db.refresh()`` reloads them.
    """

    _LOADED = {
        "id": None,  # filled in __init__
        "mastery_level": 0.25,
        "easiness_factor": 2.5,
        "interval_days": 0.0,
        "review_count": 0,
        "next_review_at": None,
        "last_reviewed_at": None,
        "latest_analysis": None,
        "linked_knowledge_node_ids": [],
        "affected_node_id": None,
    }

    def __init__(self):
        store = dict(self._LOADED)
        store["id"] = uuid4()
        store["updated_at"] = datetime.now(UTC)
        object.__setattr__(self, "_store", store)
        object.__setattr__(self, "_expired", False)

    def _expire_all(self):
        object.__setattr__(self, "_expired", True)

    def _reload(self):
        object.__setattr__(self, "_expired", False)

    def __getattr__(self, name):
        # Only reached for names absent from instance __dict__.
        if name.startswith("_"):
            raise AttributeError(name)
        if object.__getattribute__(self, "_expired"):
            raise _MissingGreenletLike("greenlet_spawn has not been called; can't call await_only() here.")
        return object.__getattribute__(self, "_store")[name]

    def __setattr__(self, name, value):
        self._store[name] = value


def _make_review_service(expiring_error: _ExpiringAttrsError):
    """ErrorBookService wired to mocks that reproduce the expiry semantics."""
    from app.services.error_book_service import ErrorBookService

    db = MagicMock()
    db.commit = AsyncMock(side_effect=lambda: expiring_error._expire_all())
    db.refresh = AsyncMock(side_effect=lambda obj, **kw: obj._reload())
    db.rollback = AsyncMock()

    service = ErrorBookService.__new__(ErrorBookService)
    service.db = db
    service.review_scheduler = SimpleNamespace(
        calculate_next_review=MagicMock(return_value=(0.5, 2.5, 1.0, datetime.now(UTC)))
    )

    service.get_error = AsyncMock(return_value=expiring_error)
    service._store_practice_outcome_memory = AsyncMock()
    service._flush_pending_mastery_events = AsyncMock()
    return service, db


def _make_sync_service():
    """ErrorBookMasterySyncService with mocked DB/Redis/stats dependencies."""
    with patch("app.services.error_book_mastery_sync_service.GalaxyStatsService"):
        return ErrorBookMasterySyncService(MagicMock(), MagicMock())


# ---------------------------------------------------------------------------
# 500 #1: MissingGreenlet — submit_review must return an instance whose
# attributes survive synchronous reads after its final commit.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_review_returns_instance_without_expired_attributes():
    error = _ExpiringAttrsError()
    service, _db = _make_review_service(error)

    from app.schemas.error_book import ReviewAction, ReviewPerformanceEnum

    processor_cls = MagicMock(return_value=SimpleNamespace(process_error_created=AsyncMock()))
    mastery_sync_cls = MagicMock(return_value=SimpleNamespace(apply_review_feedback=AsyncMock(return_value=[])))
    with (
        patch(
            "app.services.error_book_signal_processor.ErrorBookSignalProcessor",
            processor_cls,
        ),
        patch(
            "app.services.error_book_mastery_sync_service.ErrorBookMasterySyncService",
            mastery_sync_cls,
        ),
    ):
        result = await service.submit_review(
            UUID(int=1), error.id, ReviewAction(performance=ReviewPerformanceEnum.FUZZY)
        )

    # gRPC _map_to_proto / FastAPI serialization read updated_at synchronously;
    # an expired attribute here is the baseline 500.
    assert result.updated_at is not None
    assert result.mastery_level is not None


def test_submit_review_refresh_contract_red_simulation():
    """Direct simulation: after the final commit the attribute must not be expired.

    Mirrors the production sequence (commit → expire → sync read) without
    dragging the whole service graph in.
    """
    error = _ExpiringAttrsError()
    error._expire_all()
    with pytest.raises(_MissingGreenletLike):
        _ = error.updated_at  # noqa: B018


# ---------------------------------------------------------------------------
# 500 #2: partial latest_analysis — write point must persist schema-complete
# data, and the response schema must tolerate poisoned legacy rows.
# ---------------------------------------------------------------------------


def test_no_linked_node_hint_persists_schema_complete_analysis():
    service = _make_sync_service()
    error = SimpleNamespace(id=uuid4(), latest_analysis=None)

    service._attach_no_linked_node_hint(error)

    analysis = error.latest_analysis
    assert analysis["linking_hint"]["code"] == "missing_knowledge_links"
    # Must round-trip through the response schema without ValidationError.
    parsed = ErrorAnalysisResult.model_validate(analysis)
    assert parsed.error_type == ErrorTypeEnum.OTHER


def test_no_linked_node_hint_preserves_existing_analysis_fields():
    service = _make_sync_service()
    error = SimpleNamespace(
        id=uuid4(),
        latest_analysis={
            "error_type": "knowledge_gap",
            "error_type_label": "知识缺口",
            "root_cause": "r",
            "correct_approach": "c",
            "study_suggestion": "s",
        },
    )

    service._attach_no_linked_node_hint(error)

    parsed = ErrorAnalysisResult.model_validate(error.latest_analysis)
    assert parsed.error_type == ErrorTypeEnum.KNOWLEDGE_GAP
    assert parsed.root_cause == "r"
    assert error.latest_analysis["linking_hint"] is not None


@pytest.mark.parametrize(
    "poisoned",
    [
        # 实测基线写进 DB 的毒化行（review 无关联节点时）：
        {
            "linking_hint": {
                "code": "missing_knowledge_links",
                "message": "暂时没有关联到知识节点。",
                "action": "add_subject_or_link_course",
            }
        },
        # LLM 返回未校验 JSON 时可能出现的残缺/非法枚举行：
        {"error_type": "not_a_real_type"},
        {"error_type": "knowledge_gap"},  # 缺其余必填
    ],
)
def test_error_analysis_result_tolerates_partial_legacy_rows(poisoned):
    parsed = ErrorAnalysisResult.model_validate(poisoned)

    assert isinstance(parsed.error_type, ErrorTypeEnum)
    assert parsed.error_type_label
    assert parsed.root_cause
    assert parsed.correct_approach
    assert parsed.study_suggestion
