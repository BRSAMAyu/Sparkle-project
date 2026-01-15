"""
Learning Asset Service (学习资产服务)

Manages the lifecycle of learning assets (words, sentences, concepts).
Handles:
- Asset creation from translation lookups
- Suggestion generation with cooldown
- Event outbox integration for audit trail
- Inbox expiry and status transitions
"""
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from uuid import UUID

from sqlalchemy import select, and_, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.learning_assets import (
    LearningAsset,
    AssetSuggestionLog,
    AssetStatus,
    AssetKind,
    SuggestionDecision,
    UserSuggestionResponse,
)
from app.core.fingerprint import (
    generate_fingerprints,
    normalize_with_hint,
    NORM_VERSION,
    DEFAULT_MATCH_PROFILE,
)
from app.core.fuzzy_match import find_provenance, build_provenance_json
from app.core.cache import cache_service


# === Configuration ===
INBOX_EXPIRY_DAYS = 7
SUGGESTION_COOLDOWN_MINUTES = 30
DISMISS_COOLDOWN_DAYS = 7
REPEAT_LOOKUP_THRESHOLD = 2  # Suggest after N lookups in session
SESSION_TTL_HOURS = 2


class LearningAssetService:
    """Service for managing learning assets and suggestions"""

    # === Redis Key Patterns ===
    @staticmethod
    def _session_lookup_key(session_id: str, selection_fp: str) -> str:
        """Key for tracking lookups in a session"""
        return f"sess:{session_id}:lookup:{selection_fp}"

    @staticmethod
    def _user_cooldown_key(user_id: UUID, policy_id: str) -> str:
        """Key for user-level cooldown"""
        return f"user:{user_id}:suggestion_cooldown:{policy_id}"

    # === Asset Creation ===

    async def create_asset_from_selection(
        self,
        db: AsyncSession,
        user_id: UUID,
        selected_text: str,
        translation: Optional[str] = None,
        definition: Optional[str] = None,
        example: Optional[str] = None,
        source_file_id: Optional[UUID] = None,
        context_before: Optional[str] = None,
        context_after: Optional[str] = None,
        page_no: Optional[int] = None,
        language_code: str = "en",
        asset_kind: AssetKind = AssetKind.WORD,
        initial_status: AssetStatus = AssetStatus.INBOX,
    ) -> LearningAsset:
        """
        Create a learning asset from a text selection.

        This is the primary entry point for explicit user collection.

        Args:
            db: Database session
            user_id: User UUID
            selected_text: The text user selected
            translation: Translated text (optional)
            definition: Definition or meaning (optional)
            example: Example sentence (optional)
            source_file_id: Source document UUID (optional)
            context_before: Text before selection (optional)
            context_after: Text after selection (optional)
            page_no: Page number (optional)
            language_code: Source language code
            asset_kind: Type of asset (WORD/SENTENCE/CONCEPT)
            initial_status: Starting status (default: INBOX)

        Returns:
            Created LearningAsset instance
        """
        # 1. Normalize and generate fingerprints
        norm_result = normalize_with_hint(selected_text)
        fp_result = generate_fingerprints(
            selected_text=selected_text,
            doc_id=source_file_id,
            context_before=context_before,
            context_after=context_after,
            page_no=page_no,
        )

        # 2. Build immutable snapshot
        snapshot = {
            "selected_text": selected_text,
            "context_before": context_before[:500] if context_before else None,
            "context_after": context_after[:500] if context_after else None,
            "page_no": page_no,
            "source_file_id": str(source_file_id) if source_file_id else None,
            "language_code": language_code,
            "ambiguity_hint": norm_result.ambiguity_hint,
            "norm_version": NORM_VERSION,
            "match_profile": DEFAULT_MATCH_PROFILE,
            "created_at": datetime.utcnow().isoformat(),
        }

        # 3. Try to find provenance if source_file_id provided
        provenance = {}
        if source_file_id:
            try:
                match_result = await find_provenance(
                    db=db,
                    selected_text=selected_text,
                    file_id=source_file_id,
                    page_no=page_no,
                    user_id=user_id,
                )
                provenance = build_provenance_json(match_result)
            except Exception as e:
                logger.warning(f"Provenance matching failed: {e}")
                provenance = {
                    "match_strength": "ORPHAN",
                    "reason": f"match_error: {str(e)}"
                }

        # 4. Set inbox expiry if starting in INBOX
        inbox_expires_at = None
        if initial_status == AssetStatus.INBOX:
            inbox_expires_at = datetime.utcnow() + timedelta(days=INBOX_EXPIRY_DAYS)

        # 5. Create asset
        asset = LearningAsset(
            user_id=user_id,
            source_file_id=source_file_id,
            status=initial_status.value,
            asset_kind=asset_kind.value,
            headword=selected_text[:255],  # Truncate to fit column
            definition=definition,
            translation=translation,
            example=example,
            language_code=language_code,
            inbox_expires_at=inbox_expires_at,
            snapshot_json=snapshot,
            snapshot_schema_version=1,
            provenance_json=provenance,
            provenance_updated_at=datetime.utcnow() if provenance else None,
            selection_fp=fp_result.selection_fp,
            anchor_fp=fp_result.anchor_fp,
            doc_fp=fp_result.doc_fp,
            norm_version=fp_result.norm_version,
            match_profile=fp_result.match_profile,
        )

        db.add(asset)
        await db.flush()
        await db.refresh(asset)

        # 6. Write event to outbox
        await self._write_event_outbox(
            db=db,
            aggregate_type="learning_asset",
            aggregate_id=asset.id,
            event_type="asset_created",
            payload={
                "user_id": str(user_id),
                "asset_kind": asset_kind.value,
                "status": initial_status.value,
                "headword": asset.headword[:50],
                "has_provenance": bool(provenance.get("chunk_id")),
            }
        )

        logger.info(
            f"Created learning asset {asset.id} for user {user_id}: "
            f"kind={asset_kind.value}, status={initial_status.value}"
        )

        return asset

    async def check_existing_asset(
        self,
        db: AsyncSession,
        user_id: UUID,
        selection_fp: str,
    ) -> Optional[LearningAsset]:
        """
        Check if user already has an asset with this fingerprint.

        Args:
            db: Database session
            user_id: User UUID
            selection_fp: Selection fingerprint

        Returns:
            Existing asset or None
        """
        query = select(LearningAsset).where(
            and_(
                LearningAsset.user_id == user_id,
                LearningAsset.selection_fp == selection_fp,
                LearningAsset.deleted_at.is_(None),
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    # === Status Transitions ===

    async def activate_asset(self, db: AsyncSession, asset: LearningAsset) -> LearningAsset:
        """
        Move asset from INBOX to ACTIVE status.

        Args:
            db: Database session
            asset: Asset to activate

        Returns:
            Updated asset
        """
        if asset.status != AssetStatus.INBOX.value:
            raise ValueError(f"Can only activate INBOX assets, got {asset.status}")

        old_status = asset.status
        asset.activate()

        await self._write_event_outbox(
            db=db,
            aggregate_type="learning_asset",
            aggregate_id=asset.id,
            event_type="asset_status_changed",
            payload={
                "old_status": old_status,
                "new_status": asset.status,
                "triggered_by": "user_activate",
            }
        )

        await db.flush()
        return asset

    async def archive_asset(
        self,
        db: AsyncSession,
        asset: LearningAsset,
        reason: str = "user_archive"
    ) -> LearningAsset:
        """
        Archive an asset.

        Args:
            db: Database session
            asset: Asset to archive
            reason: Reason for archival

        Returns:
            Updated asset
        """
        old_status = asset.status
        asset.archive()

        await self._write_event_outbox(
            db=db,
            aggregate_type="learning_asset",
            aggregate_id=asset.id,
            event_type="asset_status_changed",
            payload={
                "old_status": old_status,
                "new_status": asset.status,
                "triggered_by": reason,
            }
        )

        await db.flush()
        return asset

    # === Suggestion System ===

    async def record_lookup(
        self,
        db: AsyncSession,
        user_id: UUID,
        session_id: str,
        selected_text: str,
        translation: Optional[str] = None,
        source_file_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """
        Record a translation lookup and evaluate suggestion.

        This is called after each translation to track repeated lookups
        and potentially suggest asset creation.

        Args:
            db: Database session
            user_id: User UUID
            session_id: Client session ID
            selected_text: Text that was translated
            translation: Translation result
            source_file_id: Source document if applicable

        Returns:
            Dict with suggest_asset flag and suggestion payload
        """
        # Generate fingerprint
        fp_result = generate_fingerprints(selected_text)
        selection_fp = fp_result.selection_fp

        # Check if asset already exists
        existing = await self.check_existing_asset(db, user_id, selection_fp)
        if existing:
            # Update lookup count
            existing.lookup_count += 1
            existing.last_seen_at = datetime.utcnow()
            await db.flush()
            return {
                "suggest_asset": False,
                "reason": "already_exists",
                "asset_id": str(existing.id),
            }

        # Increment session lookup counter
        lookup_key = self._session_lookup_key(session_id, selection_fp)
        lookup_count = await cache_service.incr(lookup_key)
        await cache_service.expire(lookup_key, SESSION_TTL_HOURS * 3600)

        # Evaluate suggestion
        should_suggest, decision, reason = await self._evaluate_suggestion(
            db=db,
            user_id=user_id,
            session_id=session_id,
            selection_fp=selection_fp,
            lookup_count=lookup_count,
        )

        # Log suggestion decision
        log = AssetSuggestionLog(
            user_id=user_id,
            session_id=session_id,
            policy_id="repeat_lookup_v1",
            trigger_event="translation_lookup",
            evidence_json={
                "selection_fp": selection_fp,
                "lookup_count": lookup_count,
                "selected_text_preview": selected_text[:100],
            },
            decision=decision.value,
            decision_reason=reason,
        )
        db.add(log)
        await db.flush()

        if should_suggest:
            return {
                "suggest_asset": True,
                "suggestion_log_id": str(log.id),
                "selection_fp": selection_fp,
                "selected_text": selected_text,
                "translation": translation,
                "source_file_id": str(source_file_id) if source_file_id else None,
                "reason": reason,
            }
        else:
            return {
                "suggest_asset": False,
                "reason": reason,
            }

    async def _evaluate_suggestion(
        self,
        db: AsyncSession,
        user_id: UUID,
        session_id: str,
        selection_fp: str,
        lookup_count: int,
    ) -> Tuple[bool, SuggestionDecision, str]:
        """
        Evaluate whether to suggest asset creation.

        Rules:
        1. Must have looked up >= REPEAT_LOOKUP_THRESHOLD times
        2. Must not be in cooldown

        Returns:
            Tuple of (should_suggest, decision, reason)
        """
        # Check lookup threshold
        if lookup_count < REPEAT_LOOKUP_THRESHOLD:
            return (
                False,
                SuggestionDecision.SKIPPED,
                f"lookup_count_below_threshold ({lookup_count} < {REPEAT_LOOKUP_THRESHOLD})"
            )

        # Check cooldown
        cooldown_key = self._user_cooldown_key(user_id, "suggest_repeat_lookup")
        cooldown_until = await cache_service.get(cooldown_key)

        if cooldown_until:
            return (
                False,
                SuggestionDecision.NOT_SUGGESTED,
                f"cooldown_active_until_{cooldown_until}"
            )

        # All checks passed
        return (
            True,
            SuggestionDecision.SUGGESTED,
            f"repeated_lookup_{lookup_count}_times"
        )

    async def record_suggestion_feedback(
        self,
        db: AsyncSession,
        user_id: UUID,
        suggestion_log_id: UUID,
        response: UserSuggestionResponse,
        asset_id: Optional[UUID] = None,
    ) -> None:
        """
        Record user feedback on a suggestion.

        If dismissed, sets a cooldown to avoid re-suggesting.

        Args:
            db: Database session
            user_id: User UUID
            suggestion_log_id: ID of the suggestion log
            response: User's response (ACCEPT/DISMISS/IGNORE)
            asset_id: Created asset ID if accepted
        """
        # Get suggestion log
        log = await db.get(AssetSuggestionLog, suggestion_log_id)
        if not log or log.user_id != user_id:
            raise ValueError("Suggestion log not found or access denied")

        log.user_response = response.value
        log.response_at = datetime.utcnow()
        log.asset_id = asset_id

        # Set cooldown if dismissed
        if response == UserSuggestionResponse.DISMISS:
            cooldown_until = datetime.utcnow() + timedelta(days=DISMISS_COOLDOWN_DAYS)
            log.cooldown_until = cooldown_until

            cooldown_key = self._user_cooldown_key(user_id, "suggest_repeat_lookup")
            await cache_service.set(
                cooldown_key,
                cooldown_until.isoformat(),
                ttl=DISMISS_COOLDOWN_DAYS * 24 * 3600
            )

        await db.flush()

        logger.info(
            f"Recorded suggestion feedback: user={user_id}, "
            f"response={response.value}, cooldown_set={response == UserSuggestionResponse.DISMISS}"
        )

    # === Query Methods ===

    async def get_user_assets(
        self,
        db: AsyncSession,
        user_id: UUID,
        status: Optional[AssetStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[LearningAsset]:
        """
        Get user's learning assets with optional status filter.

        Args:
            db: Database session
            user_id: User UUID
            status: Optional status filter
            limit: Max results
            offset: Pagination offset

        Returns:
            List of LearningAsset instances
        """
        query = select(LearningAsset).where(
            and_(
                LearningAsset.user_id == user_id,
                LearningAsset.deleted_at.is_(None),
            )
        )

        if status:
            query = query.where(LearningAsset.status == status.value)

        query = query.order_by(LearningAsset.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_asset_by_id(
        self,
        db: AsyncSession,
        asset_id: UUID,
        user_id: UUID,
    ) -> Optional[LearningAsset]:
        """
        Get a specific asset by ID, ensuring user ownership.

        Args:
            db: Database session
            asset_id: Asset UUID
            user_id: User UUID for ownership check

        Returns:
            LearningAsset or None
        """
        query = select(LearningAsset).where(
            and_(
                LearningAsset.id == asset_id,
                LearningAsset.user_id == user_id,
                LearningAsset.deleted_at.is_(None),
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    # === Inbox Decay ===

    async def process_inbox_expiry(self, db: AsyncSession) -> int:
        """
        Archive expired inbox items.

        Called by scheduled task to auto-archive stale inbox items.

        Returns:
            Number of assets archived
        """
        now = datetime.utcnow()

        # Find expired inbox items
        query = select(LearningAsset).where(
            and_(
                LearningAsset.status == AssetStatus.INBOX.value,
                LearningAsset.inbox_expires_at <= now,
                LearningAsset.deleted_at.is_(None),
            )
        ).limit(100)  # Process in batches

        result = await db.execute(query)
        expired_assets = result.scalars().all()

        count = 0
        for asset in expired_assets:
            await self.archive_asset(db, asset, reason="inbox_expired")
            count += 1

        if count > 0:
            logger.info(f"Processed inbox expiry: archived {count} assets")

        return count

    # === Event Outbox ===

    async def _write_event_outbox(
        self,
        db: AsyncSession,
        aggregate_type: str,
        aggregate_id: UUID,
        event_type: str,
        payload: Dict[str, Any],
    ) -> None:
        """
        Write event to outbox for async processing.

        Uses the existing event_outbox table from CQRS infrastructure.
        The sequence_number is computed as the next number for this aggregate.
        """
        # Get next sequence number for this aggregate
        # Use a dedicated counter table to avoid races and preserve monotonicity.
        seq_result = await db.execute(
            text("""
                INSERT INTO event_sequence_counters (aggregate_type, aggregate_id, next_sequence)
                VALUES (:aggregate_type, :aggregate_id, 1)
                ON CONFLICT (aggregate_type, aggregate_id)
                DO UPDATE SET next_sequence = event_sequence_counters.next_sequence + 1
                RETURNING next_sequence
            """),
            {"aggregate_type": aggregate_type, "aggregate_id": aggregate_id}
        )
        sequence_number = seq_result.scalar()

        await db.execute(
            text("""
                INSERT INTO event_outbox
                (aggregate_type, aggregate_id, event_type, event_version, sequence_number, payload, metadata)
                VALUES (:aggregate_type, :aggregate_id, :event_type, 1, :sequence_number, :payload, :metadata)
            """),
            {
                "aggregate_type": aggregate_type,
                "aggregate_id": aggregate_id,
                "event_type": event_type,
                "sequence_number": sequence_number,
                "payload": json.dumps(payload),
                "metadata": json.dumps({"service": "learning_asset_service"}),
            }
        )


# Singleton instance
learning_asset_service = LearningAssetService()
