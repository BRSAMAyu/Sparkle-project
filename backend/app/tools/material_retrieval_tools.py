from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.file_storage import StoredFile
from app.services.galaxy.retrieval_service import KnowledgeRetrievalService
from app.services.group_file_service import GroupFileService
from app.services.knowledge_service import KnowledgeService
from app.tools.base import BaseTool, ToolCategory, ToolResult, get_tool_runtime_context


class RetrieveUserMaterialParams(BaseModel):
    query: str = Field(..., min_length=3, max_length=400, description="What to retrieve from the user's materials")
    file_ids: list[str] | None = Field(
        default=None,
        description="Optional file IDs to scope retrieval. If omitted, Sparkle uses the current request files or the user's recent files.",
    )
    limit: int = Field(default=4, ge=1, le=6)
    threshold: float = Field(default=0.4, ge=0.0, le=1.0)
    use_hypothetical_answer: bool = Field(default=True, description="Whether to reuse HyDE query expansion before retrieval")
    include_group_documents: bool | None = Field(
        default=None,
        description="When true, also search materials shared from groups the user can access.",
    )
    group_ids: list[str] | None = Field(
        default=None,
        description="Optional group IDs to constrain shared-material retrieval.",
    )


def _coerce_uuid_list(values: list[str] | None) -> list[UUID]:
    result: list[UUID] = []
    for raw in values or []:
        try:
            result.append(UUID(str(raw)))
        except (TypeError, ValueError):
            continue
    return result


def _snippet(text: str, *, limit: int = 420) -> str:
    normalized = " ".join(str(text or "").split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: max(0, limit - 1)].rstrip()}…"


async def _resolve_scoped_files(
    db_session: Any,
    *,
    user_id: UUID,
    requested_file_ids: list[str] | None,
    include_group_documents: bool,
    group_ids: list[str] | None,
) -> list[StoredFile]:
    runtime_context = get_tool_runtime_context(db_session)
    candidate_ids = _coerce_uuid_list(requested_file_ids)
    if not candidate_ids:
        candidate_ids = _coerce_uuid_list(runtime_context.get("file_ids"))
    effective_include_group_documents = (
        include_group_documents
        or bool(runtime_context.get("include_group_documents"))
        or bool(runtime_context.get("group_id"))
    )
    effective_group_ids = group_ids or runtime_context.get("group_ids")
    return await GroupFileService.list_accessible_files(
        db_session,
        user_id=user_id,
        requested_file_ids=candidate_ids or None,
        include_group_documents=effective_include_group_documents,
        group_ids=effective_group_ids,
        limit=None if candidate_ids else 25,
    )


class RetrieveUserMaterialTool(BaseTool):
    name = "retrieve_user_material"
    description = "Retrieve relevant passages from the current user's uploaded materials."
    category = ToolCategory.GROWTH
    parameters_schema = RetrieveUserMaterialParams

    async def execute(
        self,
        params: RetrieveUserMaterialParams,
        user_id: str,
        db_session: Any,
        tool_call_id: str | None = None,
    ) -> ToolResult:
        user_uuid = UUID(user_id)
        runtime_context = get_tool_runtime_context(db_session)
        include_group_documents = (
            params.include_group_documents
            if params.include_group_documents is not None
            else bool(runtime_context.get("include_group_documents") or runtime_context.get("group_id"))
        )
        effective_group_ids = params.group_ids or runtime_context.get("group_ids")
        scoped_files = await _resolve_scoped_files(
            db_session,
            user_id=user_uuid,
            requested_file_ids=params.file_ids,
            include_group_documents=include_group_documents,
            group_ids=effective_group_ids,
        )

        if not scoped_files:
            return ToolResult(
                success=True,
                tool_name=self.name,
                tool_call_id=tool_call_id,
                data={
                    "query": params.query,
                    "scoped_file_count": 0,
                    "results": [],
                },
            )

        vector_query = params.query
        if params.use_hypothetical_answer:
            try:
                vector_query = await KnowledgeService(db_session).generate_hypothetical_answer(params.query)
            except Exception:
                vector_query = params.query

        retrieval = KnowledgeRetrievalService(db_session)
        results = await retrieval.document_vector_search(
            user_id=user_uuid,
            query=params.query,
            file_ids=[file.id for file in scoped_files],
            vector_query=vector_query,
            limit=params.limit,
            threshold=params.threshold,
            include_group_documents=include_group_documents,
            group_ids=effective_group_ids,
        )

        payload = {
            "query": params.query,
            "vector_query": vector_query,
            "scoped_file_count": len(scoped_files),
            "scoped_files": [
                {
                    "file_id": str(file.id),
                    "file_name": file.file_name,
                    "mime_type": file.mime_type,
                    "status": file.status,
                }
                for file in scoped_files[:10]
            ],
            "include_group_documents": include_group_documents,
            "group_ids": list(effective_group_ids or []),
            "results": [
                {
                    "chunk_id": str(item.chunk.id),
                    "file_id": str(item.chunk.file_id),
                    "file_name": item.file_name,
                    "chunk_index": item.chunk.chunk_index,
                    "section_title": item.chunk.section_title,
                    "page_numbers": list(item.chunk.page_numbers or []),
                    "score": round(float(item.score), 4),
                    "snippet": _snippet(item.chunk.content),
                }
                for item in results
            ],
        }

        return ToolResult(success=True, tool_name=self.name, tool_call_id=tool_call_id, data=payload)
