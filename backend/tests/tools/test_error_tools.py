from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.tools.error_tools import QueryErrorHistoryTool, RecordErrorTool
from app.tools.schemas import QueryErrorHistoryParams, RecordErrorParams


@pytest.mark.asyncio
async def test_record_error_tool_success(monkeypatch):
    class _Svc:
        def __init__(self, _db):
            pass

        async def create_error(self, user_id, data):
            return SimpleNamespace(id=uuid4())

    monkeypatch.setattr("app.tools.error_tools.ErrorBookService", _Svc)

    tool = RecordErrorTool()
    result = await tool.execute(
        params=RecordErrorParams(question="1+1= ?", wrong_answer="3", correct_answer="2", subject="math"),
        user_id=str(uuid4()),
        db_session=object(),
        tool_call_id="tc1",
    )

    assert result.success is True
    assert result.data and "error_id" in result.data


@pytest.mark.asyncio
async def test_query_error_history_tool_success(monkeypatch):
    class _Svc:
        def __init__(self, _db):
            pass

        async def list_errors(self, user_id, params):
            record = SimpleNamespace(
                id=uuid4(),
                subject_code="math",
                chapter="ch1",
                question_text="q",
                user_answer="a",
                correct_answer="b",
                latest_analysis={},
                mastery_level=0.3,
            )
            return [record], 1

    monkeypatch.setattr("app.tools.error_tools.ErrorBookService", _Svc)

    tool = QueryErrorHistoryTool()
    result = await tool.execute(
        params=QueryErrorHistoryParams(subject="math", limit=5),
        user_id=str(uuid4()),
        db_session=object(),
        tool_call_id="tc2",
    )

    assert result.success is True
    assert result.data and result.data["total"] == 1
    assert len(result.data["errors"]) == 1
