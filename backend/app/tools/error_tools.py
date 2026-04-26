from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.i18n import I18n
from app.schemas.error_book import ErrorQueryParams, ErrorRecordCreate, ErrorTypeEnum, SubjectEnum
from app.services.error_book_service import ErrorBookService
from app.tools.base import BaseTool, ToolCategory, ToolResult
from app.tools.schemas import QueryErrorHistoryParams, RecordErrorParams


def _safe_subject(subject: str | None) -> SubjectEnum:
    if not subject:
        return SubjectEnum.MATH
    try:
        return SubjectEnum(subject)
    except ValueError:
        return SubjectEnum.OTHER


def _safe_error_type(error_type: str | None) -> ErrorTypeEnum | None:
    if not error_type:
        return None
    try:
        return ErrorTypeEnum(error_type)
    except ValueError:
        return None


class RecordErrorTool(BaseTool):
    name = "record_error"
    description = "Record an error into user's error book for spaced repetition."
    category = ToolCategory.TASK
    parameters_schema = RecordErrorParams
    requires_confirmation = False

    async def execute(
        self,
        params: RecordErrorParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None,
    ) -> ToolResult:
        try:
            service = ErrorBookService(db_session)
            payload = ErrorRecordCreate(
                question_text=params.question,
                user_answer=params.wrong_answer,
                correct_answer=params.correct_answer,
                subject=_safe_subject(params.subject),
                chapter=params.chapter,
                ai_analysis_summary=params.root_cause,
            )
            record = await service.create_error(user_id=UUID(str(user_id)), data=payload)
            return ToolResult(
                success=True,
                tool_name=self.name,
                tool_call_id=tool_call_id,
                data={"error_id": str(record.id)},
                suggestion=I18n.t("error_tools.record_success_suggestion", locale="zh"),
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                tool_call_id=tool_call_id,
                error_message=str(e),
                suggestion=I18n.t("error_tools.record_fail_suggestion", locale="zh"),
            )


class QueryErrorHistoryTool(BaseTool):
    name = "query_error_history"
    description = "Query user's historical errors from error book."
    category = ToolCategory.QUERY
    parameters_schema = QueryErrorHistoryParams
    requires_confirmation = False

    async def execute(
        self,
        params: QueryErrorHistoryParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None,
    ) -> ToolResult:
        try:
            service = ErrorBookService(db_session)
            query = ErrorQueryParams(
                subject=_safe_subject(params.subject) if params.subject else None,
                error_type=_safe_error_type(params.error_type),
                page=1,
                page_size=params.limit,
            )
            records, total = await service.list_errors(UUID(str(user_id)), query)
            errors = [
                {
                    "id": str(r.id),
                    "subject_code": r.subject_code,
                    "chapter": r.chapter,
                    "question_text": r.question_text,
                    "user_answer": r.user_answer,
                    "correct_answer": r.correct_answer,
                    "latest_analysis": r.latest_analysis,
                    "mastery_level": r.mastery_level,
                }
                for r in records
            ]
            return ToolResult(
                success=True,
                tool_name=self.name,
                tool_call_id=tool_call_id,
                data={"total": total, "errors": errors},
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                tool_call_id=tool_call_id,
                error_message=str(e),
                suggestion=I18n.t("error_tools.query_fail_suggestion", locale="zh"),
            )

