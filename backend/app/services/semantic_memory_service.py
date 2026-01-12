from __future__ import annotations

import hashlib
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.error_book import ErrorRecord
from app.models.semantic_memory import StrategyNode, SemanticLink


class SemanticMemoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert_strategy_from_error(self, error: ErrorRecord) -> Optional[StrategyNode]:
        if not error.latest_analysis:
            return None
        suggestion = error.latest_analysis.get("study_suggestion")
        if not suggestion:
            return None

        title = suggestion.strip().split("\n")[0][:80]
        content_hash = self._hash_content(str(error.user_id), suggestion)

        existing = await self._get_strategy_by_hash(error.user_id, content_hash)
        if existing:
            await self._ensure_links(error, existing)
            return existing

        strategy = StrategyNode(
            user_id=error.user_id,
            title=title,
            description=suggestion.strip(),
            subject_code=error.subject_code,
            tags=error.cognitive_tags,
            content_hash=content_hash,
            source_type="llm",
            evidence_refs=[
                {"type": "error", "id": str(error.id), "schema_version": "error.v1"}
            ],
        )
        self.db.add(strategy)
        await self.db.flush()

        await self._ensure_links(error, strategy)
        return strategy

    async def get_strategies_for_error(self, error_id: UUID, user_id: UUID) -> List[StrategyNode]:
        links = await self._get_links("error", str(error_id), "strategy")
        if not links:
            return []

        strategy_ids = [link.target_id for link in links]
        result = await self.db.execute(
            select(StrategyNode).where(
                StrategyNode.user_id == user_id,
                StrategyNode.id.in_(strategy_ids),
                StrategyNode.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    async def get_same_cause_errors(
        self,
        error_id: UUID,
        user_id: UUID,
        limit: int = 5,
    ) -> List[ErrorRecord]:
        error = await self._get_error(user_id, error_id)
        if not error or not error.latest_analysis:
            return []
        root_cause = error.latest_analysis.get("root_cause")
        if not root_cause:
            return []

        try:
            stmt = select(ErrorRecord).where(
                ErrorRecord.user_id == user_id,
                ErrorRecord.is_deleted == False,
                ErrorRecord.id != error_id,
                ErrorRecord.subject_code == error.subject_code,
                ErrorRecord.latest_analysis["root_cause"].astext == root_cause,
            ).limit(limit)
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except Exception:
            stmt = select(ErrorRecord).where(
                ErrorRecord.user_id == user_id,
                ErrorRecord.is_deleted == False,
                ErrorRecord.id != error_id,
                ErrorRecord.subject_code == error.subject_code,
            ).limit(50)
            result = await self.db.execute(stmt)
            candidates = list(result.scalars().all())
            matched = [
                item for item in candidates
                if (item.latest_analysis or {}).get("root_cause") == root_cause
            ]
            return matched[:limit]

    async def _get_error(self, user_id: UUID, error_id: UUID) -> Optional[ErrorRecord]:
        result = await self.db.execute(
            select(ErrorRecord).where(
                ErrorRecord.user_id == user_id,
                ErrorRecord.id == error_id,
                ErrorRecord.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def _get_strategy_by_hash(self, user_id: UUID, content_hash: str) -> Optional[StrategyNode]:
        result = await self.db.execute(
            select(StrategyNode).where(
                StrategyNode.user_id == user_id,
                StrategyNode.content_hash == content_hash,
                StrategyNode.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def _get_links(self, source_type: str, source_id: str, target_type: str) -> List[SemanticLink]:
        result = await self.db.execute(
            select(SemanticLink).where(
                SemanticLink.source_type == source_type,
                SemanticLink.source_id == source_id,
                SemanticLink.target_type == target_type,
                SemanticLink.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    async def _ensure_links(self, error: ErrorRecord, strategy: StrategyNode) -> None:
        await self._link(
            source_type="error",
            source_id=str(error.id),
            target_type="strategy",
            target_id=str(strategy.id),
            relation_type="suggested_strategy",
            evidence_refs=[{"type": "error", "id": str(error.id), "schema_version": "error.v1"}],
        )

        for node_id in error.linked_knowledge_node_ids or []:
            await self._link(
                source_type="concept",
                source_id=str(node_id),
                target_type="strategy",
                target_id=str(strategy.id),
                relation_type="supports",
                evidence_refs=[{"type": "error", "id": str(error.id), "schema_version": "error.v1"}],
            )

    async def _link(
        self,
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str,
        relation_type: str,
        evidence_refs: Optional[list] = None,
    ) -> None:
        result = await self.db.execute(
            select(SemanticLink).where(
                SemanticLink.source_type == source_type,
                SemanticLink.source_id == source_id,
                SemanticLink.target_type == target_type,
                SemanticLink.target_id == target_id,
                SemanticLink.relation_type == relation_type,
                SemanticLink.deleted_at.is_(None),
            )
        )
        if result.scalar_one_or_none():
            return

        link = SemanticLink(
            source_type=source_type,
            source_id=source_id,
            target_type=target_type,
            target_id=target_id,
            relation_type=relation_type,
            strength=0.7,
            created_by="llm",
            evidence_refs=evidence_refs or [],
        )
        self.db.add(link)

    def _hash_content(self, user_id: str, content: str) -> str:
        payload = f"{user_id}:{content}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
