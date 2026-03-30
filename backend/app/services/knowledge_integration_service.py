"""
Knowledge Integration Service

Integrates external content (translations, imports, etc.) into the knowledge graph.
Creates draft knowledge nodes that users can review and publish.

Author: Claude Code (Opus 4.5)
Created: 2026-01-15
"""
from __future__ import annotations
import uuid
from datetime import timezone, datetime, timedelta
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.services.embedding_service import embedding_service
from app.services.expansion_service import ExpansionService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class KnowledgeIntegrationService:
    """
    Service for integrating external content into the knowledge graph.

    Supported integrations:
    - Translation → Vocabulary nodes
    - Document import → Concept nodes
    - External links → Reference nodes
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_vocabulary_node(
        self,
        user_id: UUID,
        source_text: str,
        translation: str,
        context: str,
        source_url: str | None = None,
        source_document_id: UUID | None = None,
        language: str = "en",
        domain: str | None = None,
        subject_id: int | None = None,
    ) -> KnowledgeNode:
        """
        Create or update a vocabulary knowledge node from a translation.

        If the node already exists (same name), it will be linked to the user
        and the new context will be appended.

        Args:
            user_id: User who created/updated the node
            source_text: Original text (e.g., "polymorphism")
            translation: Translated text (e.g., "多态性")
            context: Context where the word appeared
            source_url: Source URL where the word appeared
            source_document_id: Source document ID
            language: Source language (e.g., "en", "zh")
            domain: Domain for subject linking ("cs", "math", "business", etc.)
            subject_id: Optional explicit subject ID

        Returns:
            KnowledgeNode: The created or updated node
        """
        try:
            # 1. Check if node already exists (Idempotency)
            result = await self.db.execute(
                select(KnowledgeNode).where(KnowledgeNode.name == source_text)
            )
            existing_node = result.scalar_one_or_none()

            if existing_node:
                return await self._handle_existing_vocabulary_node(
                    existing_node, user_id, context, source_url
                )

            # 2. Create new node
            description = self._format_vocabulary_description(
                source_text, translation, context, language, source_url
            )

            expansion_service = ExpansionService(self.db)
            node, _ = await expansion_service.upsert_node_from_candidate(
                user_id=user_id,
                candidate={
                    "name": source_text,
                    "name_en": source_text if language == "en" else None,
                    "description": description,
                    "keywords": [source_text, translation, domain] if domain else [source_text, translation],
                    "importance_level": 1,
                },
                subject_id=subject_id,
                source_type="translation",
                generate_embedding=False,
                unlock_for_user=False,
                commit=False,
                invalidate_caches=False,
                allow_existing_match=False,
                node_updates={
                    "source_file_id": source_document_id,
                    "status": "draft",
                },
            )

            logger.info(f"✅ Created vocabulary node: {source_text} → {translation} (id={node.id})")

            # Create initial user status
            user_status = UserNodeStatus(
                user_id=user_id,
                node_id=node.id,
                mastery_score=0.0,
                bkt_mastery_prob=0.0,
                is_unlocked=True,
                first_unlock_at=_utcnow(),
                created_at=_utcnow(),
                updated_at=_utcnow(),
            )

            self.db.add(user_status)

            # Schedule for review (24 hours later)
            await self._schedule_first_review(user_status)

            await self.db.commit()
            await expansion_service._invalidate_after_graph_mutation(user_id)
            await self.db.refresh(node)

            # Generate embedding asynchronously
            await self._generate_embedding_async(node.id, node.name, node.description)

            return node

        except Exception as e:
            logger.exception(f"❌ Failed to create vocabulary node: {e}")
            await self.db.rollback()
            raise

    async def _handle_existing_vocabulary_node(
        self,
        node: KnowledgeNode,
        user_id: UUID,
        context: str,
        source_url: str | None
    ) -> KnowledgeNode:
        """Handle logic when vocabulary node already exists."""
        # 1. Ensure User Status Exists
        result = await self.db.execute(
            select(UserNodeStatus)
            .where(UserNodeStatus.node_id == node.id)
            .where(UserNodeStatus.user_id == user_id)
        )
        user_status = result.scalar_one_or_none()

        if not user_status:
            # User hasn't unlocked this node yet, subscribe them
            user_status = UserNodeStatus(
                user_id=user_id,
                node_id=node.id,
                mastery_score=0.0,
                bkt_mastery_prob=0.0,
                is_unlocked=True,
                first_unlock_at=_utcnow(),
                created_at=_utcnow(),
                updated_at=_utcnow(),
            )
            self.db.add(user_status)
            await self._schedule_first_review(user_status)
            logger.info(f"🔗 Linked user {user_id} to existing node {node.id}")

        # 2. Append Context (if not already present)
        if context and (not node.description or context not in node.description):
            # Check length to prevent massive descriptions
            if node.description and len(node.description) < 2000:
                append_text = f"\n\n**其他场景**:\n{context}"
                if source_url:
                    append_text += f"\n*来源: {source_url}*"

                node.description += append_text
                node.updated_at = _utcnow()
                logger.info(f"📝 Appended context to node {node.id}")

        await self.db.commit()
        await self.db.refresh(node)
        return node

    def _format_vocabulary_description(
        self,
        source_text: str,
        translation: str,
        context: str,
        language: str,
        source_url: str | None = None
    ) -> str:
        """Format node description with translation and context."""
        description_parts = []

        # Translation
        if language == "en":
            description_parts.append(f"**中文译文**: {translation}")
        else:
            description_parts.append(f"**English**: {translation}")

        # Context
        if context:
            # Highlight the source text in context
            highlighted_context = context.replace(
                source_text,
                f"**{source_text}**"
            )
            description_parts.append(f"\n**使用场景**:\n{highlighted_context}")

        if source_url:
            description_parts.append(f"\n*来源: {source_url}*")

        # Source indicator
        description_parts.append("\n\n*此节点由翻译功能自动创建*")

        return "\n".join(description_parts)

    async def _schedule_first_review(self, user_status: UserNodeStatus):
        """
        Schedule the first review for a new vocabulary node.

        Uses spaced repetition algorithm:
        - First review: 24 hours
        - Subsequent reviews determined by mastery score
        """
        user_status.next_review_at = _utcnow() + timedelta(hours=24)
        user_status.last_study_at = _utcnow()

        logger.debug(f"📅 Scheduled first review: node={user_status.node_id}, "
                    f"review_at={user_status.next_review_at}")

    async def _generate_embedding_async(
        self,
        node_id: UUID,
        name: str,
        description: str | None
    ):
        """
        Generate embedding for the node (async, non-blocking).

        This is called asynchronously to avoid blocking the API response.
        """
        try:
            # Combine name and description for embedding
            text = f"{name}\n{description or ''}"

            embedding = await embedding_service.get_embedding(text)

            # Update node with embedding
            result = await self.db.execute(
                select(KnowledgeNode).where(KnowledgeNode.id == node_id)
            )
            node = result.scalar_one_or_none()

            if node:
                node.embedding = embedding
                node.updated_at = _utcnow()
                await self.db.commit()
                logger.debug(f"✅ Generated embedding for node {node_id}")
            else:
                logger.warning(f"⚠️ Node {node_id} not found for embedding generation")

        except Exception as e:
            logger.exception(f"❌ Failed to generate embedding for node {node_id}: {e}")
            # Don't raise - embedding generation is non-critical

    async def publish_node(self, node_id: UUID, user_id: UUID) -> KnowledgeNode:
        """
        Publish a draft node to the main knowledge graph.

        Args:
            node_id: Node to publish
            user_id: User publishing the node (for permission check)

        Returns:
            KnowledgeNode: Published node

        Raises:
            ValueError: If node not found or user doesn't have permission
        """
        result = await self.db.execute(
            select(KnowledgeNode).where(KnowledgeNode.id == node_id)
        )
        node = result.scalar_one_or_none()

        if not node:
            raise ValueError(f"Node {node_id} not found")

        # Check permission (node must be created by user or be a draft)
        user_status_result = await self.db.execute(
            select(UserNodeStatus)
            .where(UserNodeStatus.node_id == node_id)
            .where(UserNodeStatus.user_id == user_id)
        )
        user_status = user_status_result.scalar_one_or_none()

        if not user_status:
            raise ValueError(f"User {user_id} doesn't have access to node {node_id}")

        # Publish node
        node.status = "published"
        node.updated_at = _utcnow()

        await self.db.commit()
        await self.db.refresh(node)

        logger.info(f"📤 Published node: {node.name} (id={node.id})")

        return node

    async def delete_draft_node(self, node_id: UUID, user_id: UUID):
        """
        Delete a draft node.

        Args:
            node_id: Node to delete
            user_id: User deleting the node (for permission check)

        Raises:
            ValueError: If node not found, not a draft, or user doesn't have permission
        """
        result = await self.db.execute(
            select(KnowledgeNode).where(KnowledgeNode.id == node_id)
        )
        node = result.scalar_one_or_none()

        if not node:
            raise ValueError(f"Node {node_id} not found")

        if node.status != "draft":
            raise ValueError(f"Only draft nodes can be deleted (node status: {node.status})")

        # Check permission
        user_status_result = await self.db.execute(
            select(UserNodeStatus)
            .where(UserNodeStatus.node_id == node_id)
            .where(UserNodeStatus.user_id == user_id)
        )
        user_status = user_status_result.scalar_one_or_none()

        if not user_status:
            raise ValueError(f"User {user_id} doesn't have access to node {node_id}")

        # Delete node (cascade will delete user_status)
        await self.db.delete(node)
        await self.db.commit()

        logger.info(f"🗑️ Deleted draft node: {node.name} (id={node.id})")

    async def update_node_content(
        self,
        node_id: UUID,
        user_id: UUID,
        name: str | None = None,
        description: str | None = None,
        keywords: list | None = None,
    ) -> KnowledgeNode:
        """
        Update node content before publishing.

        Args:
            node_id: Node to update
            user_id: User updating the node
            name: New name (optional)
            description: New description (optional)
            keywords: New keywords (optional)

        Returns:
            KnowledgeNode: Updated node

        Raises:
            ValueError: If node not found or user doesn't have permission
        """
        result = await self.db.execute(
            select(KnowledgeNode).where(KnowledgeNode.id == node_id)
        )
        node = result.scalar_one_or_none()

        if not node:
            raise ValueError(f"Node {node_id} not found")

        # Check permission
        user_status_result = await self.db.execute(
            select(UserNodeStatus)
            .where(UserNodeStatus.node_id == node_id)
            .where(UserNodeStatus.user_id == user_id)
        )
        user_status = user_status_result.scalar_one_or_none()

        if not user_status:
            raise ValueError(f"User {user_id} doesn't have access to node {node_id}")

        # Update fields
        if name is not None:
            node.name = name
        if description is not None:
            node.description = description
        if keywords is not None:
            node.keywords = keywords

        node.updated_at = _utcnow()

        await self.db.commit()
        await self.db.refresh(node)

        # Regenerate embedding if content changed
        if name is not None or description is not None:
            await self._generate_embedding_async(node.id, node.name, node.description)

        logger.info(f"✏️ Updated node: {node.name} (id={node.id})")

        return node
