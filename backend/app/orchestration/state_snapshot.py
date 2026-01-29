"""
State Snapshot Manager - Phase 2

Responsibilities:
1. Generate state snapshots before LangGraph planning
2. Store snapshots in Redis with TTL
3. Provide version comparison functionality
4. Track context versions for conflict detection
"""
import contextlib
import json
import uuid
from datetime import datetime
from typing import Any

from loguru import logger

from app.orchestration.schemas import StateSnapshot


class StateSnapshotManager:
    """State Snapshot Manager (Phase 2)

    Responsibilities:
    1. Create snapshots before calling LangGraph
    2. Store snapshots in Redis (TTL 1 hour)
    3. Provide version comparison for conflict detection
    """

    SNAPSHOT_KEY_PREFIX = "snapshot:"
    SNAPSHOT_TTL = 3600  # 1 hour
    VERSION_KEY_PREFIX = "user:context:versions:"

    def __init__(self, redis_client):
        self.redis = redis_client

    async def create_snapshot(
        self,
        user_id: str,
        session_id: str,
        db_session=None
    ) -> StateSnapshot:
        """Create a state snapshot

        Args:
            user_id: User ID
            session_id: Session ID
            db_session: Database session (optional, for fetching latest state)

        Returns:
            StateSnapshot: The created snapshot
        """
        snapshot = StateSnapshot(
            user_id=user_id,
            session_id=session_id
        )

        # Load context versions from Redis
        snapshot.context_versions = await self._load_context_versions(user_id)

        # If db_session is provided, fetch additional information
        if db_session:
            snapshot.pending_tasks_count = await self._count_pending_tasks(user_id, db_session)
            snapshot.user_quota_remaining = await self._get_user_quota(user_id, db_session)
            snapshot.active_focus_id = await self._get_active_focus(user_id, db_session)

        # Store snapshot in Redis
        await self._save_snapshot(snapshot)

        logger.info(
            f"Snapshot created: {snapshot.snapshot_id} "
            f"context={snapshot.context_versions} "
            f"pending_tasks={snapshot.pending_tasks_count}"
        )

        return snapshot

    async def get_snapshot(self, snapshot_id: str) -> StateSnapshot | None:
        """Retrieve a snapshot by ID

        Args:
            snapshot_id: The snapshot ID

        Returns:
            StateSnapshot if found, None otherwise
        """
        if not self.redis:
            return None

        key = f"{self.SNAPSHOT_KEY_PREFIX}{snapshot_id}"
        try:
            raw = await self.redis.get(key)
            if raw:
                data = json.loads(raw)
                return StateSnapshot(**data)
        except Exception as e:
            logger.warning(f"Failed to get snapshot {snapshot_id}: {e}")

        return None

    async def compare_versions(
        self,
        snapshot: StateSnapshot,
        current_versions: dict[str, str]
    ) -> dict[str, Any]:
        """Compare snapshot versions with current versions

        Args:
            snapshot: The snapshot to compare
            current_versions: Current context versions

        Returns:
            Dict with:
            - has_conflict: bool
            - conflicted_domains: List[str]
            - snapshot_versions: Dict
            - current_versions: Dict
        """
        if not snapshot or not snapshot.context_versions:
            return {
                "has_conflict": False,
                "conflicted_domains": [],
                "snapshot_versions": {},
                "current_versions": current_versions
            }

        conflicted_domains = []

        for domain, snapshot_version in snapshot.context_versions.items():
            current_version = current_versions.get(domain)
            if current_version and current_version != snapshot_version:
                conflicted_domains.append(domain)

        result = {
            "has_conflict": len(conflicted_domains) > 0,
            "conflicted_domains": conflicted_domains,
            "snapshot_versions": snapshot.context_versions,
            "current_versions": current_versions
        }

        if result["has_conflict"]:
            logger.warning(
                f"Version conflict detected for snapshot {snapshot.snapshot_id}: "
                f"{conflicted_domains}"
            )

        return result

    async def invalidate_user_snapshots(self, user_id: str) -> int:
        """Invalidate all snapshots for a user (called after state changes)

        Args:
            user_id: User ID

        Returns:
            Number of snapshots invalidated
        """
        if not self.redis:
            return 0

        try:
            # Scan for snapshot keys
            pattern = f"{self.SNAPSHOT_KEY_PREFIX}*"
            count = 0

            async for key in self.redis.scan_iter(match=pattern):
                try:
                    raw = await self.redis.get(key)
                    if raw:
                        data = json.loads(raw)
                        if data.get("user_id") == user_id:
                            await self.redis.delete(key)
                            count += 1
                except Exception:
                    continue

            if count > 0:
                logger.info(f"Invalidated {count} snapshots for user {user_id}")

            return count
        except Exception as e:
            logger.warning(f"Failed to invalidate snapshots for user {user_id}: {e}")
            return 0

    async def _load_context_versions(self, user_id: str) -> dict[str, str]:
        """Load context versions from Redis

        Args:
            user_id: User ID

        Returns:
            Dict of domain -> version
        """
        if not self.redis:
            return {}

        key = f"{self.VERSION_KEY_PREFIX}{user_id}"
        try:
            raw = await self.redis.get(key)
            if raw:
                return json.loads(raw)
        except Exception as e:
            logger.warning(f"Failed to load context versions for user {user_id}: {e}")

        return {}

    async def _save_snapshot(self, snapshot: StateSnapshot):
        """Store snapshot in Redis

        Args:
            snapshot: The snapshot to save
        """
        if not self.redis:
            return

        key = f"{self.SNAPSHOT_KEY_PREFIX}{snapshot.snapshot_id}"
        try:
            payload = json.dumps({
                "snapshot_id": snapshot.snapshot_id,
                "user_id": snapshot.user_id,
                "session_id": snapshot.session_id,
                "timestamp": snapshot.timestamp,
                "context_versions": snapshot.context_versions,
                "active_focus_id": snapshot.active_focus_id,
                "pending_tasks_count": snapshot.pending_tasks_count,
                "user_quota_remaining": snapshot.user_quota_remaining
            })
            await self.redis.setex(key, self.SNAPSHOT_TTL, payload)
        except Exception as e:
            logger.warning(f"Failed to save snapshot {snapshot.snapshot_id}: {e}")

    async def _count_pending_tasks(self, user_id: str, db_session) -> int:
        """Count pending tasks for a user

        Args:
            user_id: User ID
            db_session: Database session

        Returns:
            Number of pending tasks
        """
        try:
            from sqlalchemy import select

            from app.models.task import Task, TaskStatus

            result = await db_session.execute(
                select(Task).where(
                    Task.user_id == uuid.UUID(user_id),
                    Task.status == TaskStatus.PENDING
                )
            )
            return len(result.scalars().all())
        except Exception as e:
            logger.warning(f"Failed to count pending tasks for user {user_id}: {e}")
            await self._safe_rollback(db_session)
            return 0

    async def _get_user_quota(self, user_id: str, db_session) -> int:
        """Get remaining user quota

        Args:
            user_id: User ID
            db_session: Database session

        Returns:
            Remaining quota count
        """
        try:
            from sqlalchemy import select

            from app.models.user import User

            result = await db_session.execute(
                select(User).where(User.id == uuid.UUID(user_id))
            )
            user = result.scalar_one_or_none()

            if user:
                # Check if user has daily_quota attribute
                if hasattr(user, 'daily_quota'):
                    # For simplicity, return a fixed value
                    # In production, this would check actual usage
                    return max(0, user.daily_quota - 0)

            return 100  # Default quota
        except Exception as e:
            logger.warning(f"Failed to get user quota for {user_id}: {e}")
            await self._safe_rollback(db_session)
            return 100

    async def _get_active_focus(self, user_id: str, db_session) -> str | None:
        """Get active focus ID for user

        Args:
            user_id: User ID
            db_session: Database session

        Returns:
            Active focus ID or None
        """
        try:
            from sqlalchemy import desc, select

            from app.models.focus import FocusSession

            result = await db_session.execute(
                select(FocusSession)
                .where(FocusSession.user_id == uuid.UUID(user_id))
                .order_by(desc(FocusSession.start_time))
                .limit(1)
            )
            session = result.scalars().first()
            return str(session.id) if session else None
        except Exception as e:
            logger.warning(f"Failed to get active focus for user {user_id}: {e}")
            await self._safe_rollback(db_session)
            return None

    async def _safe_rollback(self, db_session) -> None:
        with contextlib.suppress(Exception):
            await db_session.rollback()

    async def update_context_version(
        self,
        user_id: str,
        domain: str,
        version: str
    ) -> None:
        """Update a specific context version domain

        This should be called when state changes (e.g., task created/updated)

        Args:
            user_id: User ID
            domain: Domain name (e.g., "tasks", "plans", "focus")
            version: New version identifier
        """
        if not self.redis:
            return

        key = f"{self.VERSION_KEY_PREFIX}{user_id}"
        try:
            # Get existing versions
            raw = await self.redis.get(key)
            versions = json.loads(raw) if raw else {}

            # Update the domain
            versions[domain] = version
            versions["_last_updated"] = datetime.utcnow().isoformat()

            # Save back
            payload = json.dumps(versions, ensure_ascii=False)
            await self.redis.setex(key, 6 * 60 * 60, payload)  # 6 hours TTL

            logger.debug(f"Updated context version for user {user_id}: {domain}={version}")

            # Invalidate existing snapshots for this user
            await self.invalidate_user_snapshots(user_id)

        except Exception as e:
            logger.warning(f"Failed to update context version: {e}")
