"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>
"""

from __future__ import annotations

import datetime
import math
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.event_bus import FocusSessionCompletedEvent, event_bus
from app.models.focus import FocusSession, FocusStatus, FocusType
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.plan import Plan
from app.models.subject import Subject
from app.models.task import Task
from app.models.task_resources import TaskKnowledgeLink
from app.models.user import User
from app.services.cognitive.auto_fragment_collector import AutoFragmentCollector
from app.services.llm_fallback_utils import focus_llm
from app.services.memory_service import MemoryService


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


class FocusService:
    FOCUS_MASTERY_MIN_DURATION = 10
    FOCUS_MASTERY_MIN_DELTA = 2
    FOCUS_MASTERY_MAX_DELTA = 8
    FOCUS_MASTERY_MAX_NODES = 3

    @staticmethod
    def _to_utc_naive(ts: datetime.datetime) -> datetime.datetime:
        if ts.tzinfo is None:
            return ts
        return ts.astimezone(datetime.UTC).replace(tzinfo=None)

    @staticmethod
    async def log_session(
        db: AsyncSession,
        user_id: UUID,
        task_id: UUID | None,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        duration_minutes: int,
        focus_type: FocusType = FocusType.POMODORO,
        status: FocusStatus = FocusStatus.COMPLETED,
    ) -> dict[str, Any]:
        """Log a completed focus session and award flame points"""
        start_time = FocusService._to_utc_naive(start_time)
        end_time = FocusService._to_utc_naive(end_time)

        session = FocusSession(
            user_id=user_id,
            task_id=task_id,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration_minutes,
            focus_type=focus_type,
            status=status,
        )
        db.add(session)
        await db.flush()
        session_uuid = session.id
        session_id = str(session.id)

        # Calculate Rewards
        flame_earned = 0
        leveled_up = False
        new_level = 0
        task: Task | None = None

        if status == FocusStatus.COMPLETED:
            # Base logic: 1 minute = 1 point.
            # 100 points = 1.0 brightness = 1 level up.
            points = duration_minutes
            flame_earned = points

            user = await db.get(User, user_id)
            if user:
                # Add brightness (0.01 per minute)
                increment = points / 100.0
                user.flame_brightness += increment

                # Check Level Up
                if user.flame_brightness >= 1.0:
                    levels_gained = int(user.flame_brightness)
                    user.flame_level += levels_gained
                    user.flame_brightness -= levels_gained
                    leveled_up = True

                new_level = user.flame_level

            # Update Task Stats
            if task_id:
                from app.services.task_service import TaskService

                task = await TaskService.apply_focus_progress(
                    db,
                    task_id=task_id,
                    user_id=user_id,
                    duration_minutes=duration_minutes,
                    started_at=start_time,
                )

        # ========== Achievement Integration ==========
        unlocked_achievements = []
        try:
            from app.services.achievement_engine import AchievementEngine, AchievementEvent

            achievement_engine = AchievementEngine(db)

            base_kwargs = {
                "study_minutes": duration_minutes,
                "session_id": session_id,
                "session_start_time": start_time,
            }

            unlocked = await achievement_engine.process_event(
                user_id=str(user_id),
                event_type=AchievementEvent.STUDY_MINUTES_ACCUMULATED,
                **base_kwargs,
            )

            hour = start_time.hour if hasattr(start_time, "hour") else start_time.astimezone().hour
            special_unlocked = []
            if hour >= 23 or hour < 5:
                special_unlocked = await achievement_engine.process_event(
                    user_id=str(user_id),
                    event_type=AchievementEvent.NIGHT_STUDY,
                    **base_kwargs,
                )
            elif 5 <= hour < 8:
                special_unlocked = await achievement_engine.process_event(
                    user_id=str(user_id),
                    event_type=AchievementEvent.EARLY_BIRD,
                    **base_kwargs,
                )

            if special_unlocked:
                unlocked.extend(special_unlocked)

            if unlocked:
                unlocked_achievements = unlocked
        except Exception as e:
            # Don't fail the session logging if achievement processing fails
            import logging

            logging.warning(f"Achievement processing failed: {e}")
        # ============================================

        await db.commit()

        mastery_updates = []
        if status == FocusStatus.COMPLETED and duration_minutes > 0 and task is not None:
            try:
                mastery_updates = await FocusService._apply_focus_mastery_boost(
                    db=db,
                    user_id=user_id,
                    task=task,
                    duration_minutes=duration_minutes,
                    session_id=session_id,
                )
            except Exception as e:
                logger.warning(f"Focus mastery boost failed for session {session_id}: {e}")

        try:
            event = FocusSessionCompletedEvent(
                user_id=str(user_id),
                session_id=session_id,
                task_id=str(task_id) if task_id else None,
                plan_id=str(task.plan_id) if task and task.plan_id else None,
                duration_minutes=duration_minutes,
                mastery_updates=mastery_updates,
                started_at=start_time.isoformat(),
                completed=status == FocusStatus.COMPLETED,
            )
            await event_bus.publish(
                "focus.session.completed",
                event.to_dict(),
            )
        except Exception as e:
            import logging

            logging.warning(f"Focus session event publish failed: {e}")

        try:
            auto_collector = AutoFragmentCollector(db)
            await auto_collector.collect_from_focus_session(
                user_id=user_id,
                session_id=session_uuid,
                duration_minutes=duration_minutes,
                status=status,
            )
        except Exception as e:
            import logging

            logging.warning(f"Auto fragment collection failed for focus session: {e}")

        if status == FocusStatus.COMPLETED and duration_minutes > 0:
            try:
                task_title = task.title if task_id and task else None
                summary = (
                    f"{duration_minutes} 分钟专注于 {task_title}"
                    if task_title
                    else f"完成了 {duration_minutes} 分钟专注"
                )
                evidence_refs = [{"type": "event", "id": session_id, "schema_version": "event.v1"}]
                if task_id:
                    evidence_refs.append({"type": "task", "id": str(task_id), "schema_version": "task.v1"})
                memory_service = MemoryService(db)
                await memory_service.create_episodic_memory(
                    user_id=user_id,
                    summary=summary,
                    source_type="focus_session",
                    source_id=session_id,
                    occurred_at=end_time,
                    importance_score=min(1.0, max(0.2, duration_minutes / 120.0)),
                    tags=["focus", str(focus_type.value)],
                    evidence_refs=evidence_refs,
                )
            except Exception as e:
                import logging

                logging.warning(f"Focus session episodic memory write failed: {e}")

        return {
            "session_id": session_id,
            "rewards": {"flame_earned": flame_earned, "leveled_up": leveled_up, "new_level": new_level},
            "unlocked_achievements": unlocked_achievements,
            "mastery_updates": mastery_updates,
        }

    @staticmethod
    def _focus_mastery_delta(duration_minutes: int) -> int:
        """Small bounded mastery boost for meaningful completed focus sessions."""
        if duration_minutes < FocusService.FOCUS_MASTERY_MIN_DURATION:
            return 0
        scaled = math.ceil(duration_minutes / 10)
        return min(
            FocusService.FOCUS_MASTERY_MAX_DELTA,
            max(FocusService.FOCUS_MASTERY_MIN_DELTA, scaled),
        )

    @staticmethod
    async def _apply_focus_mastery_boost(
        *,
        db: AsyncSession,
        user_id: UUID,
        task: Task,
        duration_minutes: int,
        session_id: str,
    ) -> list[dict[str, Any]]:
        delta = FocusService._focus_mastery_delta(duration_minutes)
        if delta <= 0:
            return []

        nodes = await FocusService._resolve_task_mastery_nodes(db=db, user_id=user_id, task=task)
        if not nodes:
            return []

        from app.services.galaxy_service import GalaxyService

        galaxy_service = GalaxyService(db)
        updates: list[dict[str, Any]] = []
        for node in nodes[: FocusService.FOCUS_MASTERY_MAX_NODES]:
            status_result = await db.execute(
                select(UserNodeStatus.mastery_score).where(
                    UserNodeStatus.user_id == user_id,
                    UserNodeStatus.node_id == node.id,
                )
            )
            old_score = float(status_result.scalar_one_or_none() or 0.0)
            new_score = min(100, int(round(old_score + delta)))
            if new_score <= int(round(old_score)):
                continue

            try:
                result = await galaxy_service.update_node_mastery(
                    user_id=user_id,
                    node_id=node.id,
                    new_mastery=new_score,
                    reason="focus_session",
                    request_id=session_id,
                )
            except Exception as e:
                logger.warning(f"Failed to update focus mastery for node {node.id}: {e}")
                continue

            if not result or not result.get("success"):
                continue

            old_mastery = int(round(old_score))
            new_mastery = int(round(float(result.get("new_mastery", new_score))))
            if new_mastery <= old_mastery:
                continue

            updates.append(
                {
                    "node_id": str(node.id),
                    "node_name": str(node.name or "").strip(),
                    "old_mastery": old_mastery,
                    "new_mastery": new_mastery,
                    "delta": new_mastery - old_mastery,
                    "reason": "focus_session",
                }
            )

        return updates

    @staticmethod
    async def _resolve_task_mastery_nodes(
        *,
        db: AsyncSession,
        user_id: UUID,
        task: Task,
    ) -> list[KnowledgeNode]:
        node_ids: list[UUID] = []

        def add_node_id(value: object) -> None:
            if value is None:
                return
            try:
                node_id = value if isinstance(value, UUID) else UUID(str(value))
            except (TypeError, ValueError):
                return
            if node_id not in node_ids:
                node_ids.append(node_id)

        add_node_id(getattr(task, "knowledge_node_id", None))

        link_rows = (
            await db.execute(
                select(TaskKnowledgeLink.knowledge_node_id)
                .where(TaskKnowledgeLink.task_id == task.id)
                .order_by(TaskKnowledgeLink.is_primary.desc(), TaskKnowledgeLink.order_index.asc())
            )
        ).all()
        for (node_id,) in link_rows:
            add_node_id(node_id)

        for payload in (
            getattr(task, "guide_json", None),
            getattr(task, "tags", None),
            getattr(task, "galaxy_node_ids", None),
        ):
            for node_id in FocusService._extract_node_ids(payload):
                add_node_id(node_id)

        if node_ids:
            rows = (await db.execute(select(KnowledgeNode).where(KnowledgeNode.id.in_(node_ids)))).scalars().all()
            by_id = {node.id: node for node in rows}
            return [by_id[node_id] for node_id in node_ids if node_id in by_id]

        subject = await FocusService._resolve_task_subject(db=db, task=task)
        if not subject:
            return []

        subject_lower = subject.lower()
        subject_like = f"%{subject_lower}%"
        return (
            (
                await db.execute(
                    select(KnowledgeNode)
                    .outerjoin(Subject, KnowledgeNode.subject_id == Subject.id)
                    .outerjoin(
                        UserNodeStatus,
                        (UserNodeStatus.node_id == KnowledgeNode.id) & (UserNodeStatus.user_id == user_id),
                    )
                    .where(
                        or_(
                            func.lower(KnowledgeNode.name) == subject_lower,
                            func.lower(KnowledgeNode.name).like(subject_like),
                            func.lower(Subject.name) == subject_lower,
                            func.lower(Subject.category) == subject_lower,
                        )
                    )
                    .order_by(
                        UserNodeStatus.is_unlocked.desc(),
                        KnowledgeNode.importance_level.desc(),
                        KnowledgeNode.updated_at.desc(),
                    )
                    .limit(FocusService.FOCUS_MASTERY_MAX_NODES)
                )
            )
            .scalars()
            .all()
        )

    @staticmethod
    def _extract_node_ids(payload: object) -> list[UUID]:
        values: list[object] = []
        if isinstance(payload, dict):
            for key in (
                "galaxy_node_ids",
                "knowledge_node_ids",
                "knowledge_nodes",
                "node_ids",
                "knowledge_node_id",
            ):
                value = payload.get(key)
                if isinstance(value, list):
                    values.extend(value)
                elif value is not None:
                    values.append(value)
        elif isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    values.extend(FocusService._extract_node_ids(item))
                else:
                    values.append(item)
        elif payload is not None:
            values.append(payload)

        node_ids: list[UUID] = []
        for value in values:
            if isinstance(value, dict):
                value = value.get("id") or value.get("node_id") or value.get("knowledge_node_id")
            try:
                node_id = value if isinstance(value, UUID) else UUID(str(value))
            except (TypeError, ValueError):
                continue
            if node_id not in node_ids:
                node_ids.append(node_id)
        return node_ids

    @staticmethod
    async def _resolve_task_subject(*, db: AsyncSession, task: Task) -> str | None:
        guide_json = getattr(task, "guide_json", None)
        if isinstance(guide_json, dict):
            for key in ("subject", "course", "topic"):
                value = str(guide_json.get(key) or "").strip()
                if value:
                    return value

        if task.plan_id:
            result = await db.execute(select(Plan.subject).where(Plan.id == task.plan_id))
            value = str(result.scalar_one_or_none() or "").strip()
            if value:
                return value

        return None

    @staticmethod
    async def get_today_stats(db: AsyncSession, user_id: UUID) -> dict[str, Any]:
        """Get focus stats for today"""
        now = _utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Total duration
        stmt_duration = select(func.sum(FocusSession.duration_minutes)).where(
            FocusSession.user_id == user_id,
            FocusSession.start_time >= today_start,
            FocusSession.status == FocusStatus.COMPLETED,
        )
        result_duration = await db.execute(stmt_duration)
        total_minutes = result_duration.scalar() or 0

        # Count sessions
        stmt_count = select(func.count(FocusSession.id)).where(
            FocusSession.user_id == user_id,
            FocusSession.start_time >= today_start,
            FocusSession.status == FocusStatus.COMPLETED,
        )
        result_count = await db.execute(stmt_count)
        pomodoro_count = result_count.scalar() or 0

        return {"total_minutes": total_minutes, "pomodoro_count": pomodoro_count, "today_date": today_start.isoformat()}

    @staticmethod
    async def get_methodological_guidance(task_context: str, user_input: str) -> str:
        """
        Get methodological guidance from LLM (Hint/Direction, NOT Solution).
        """
        system_prompt = """
        You are a Socratic tutor and coach.
        The user is working on a task and feels stuck or needs direction.

        Goal: Provide "Methodological Guidance" - do NOT give the direct answer.
        1. Analyze the user's input and task.
        2. Suggest a framework, a mental model, or a step-by-step approach to solve it.
        3. Ask a guiding question to prompt the user's thinking.
        4. Keep it concise (under 150 words).
        5. Tone: Encouraging, Insightful, Professional.
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Task: {task_context}\n\nUser Question/Context: {user_input}"},
        ]

        return await focus_llm.call(
            messages, fallback="继续专注，你做得很好！如果感到困惑，试着把问题分解成更小的部分。", temperature=0.7
        )

    @staticmethod
    async def breakdown_task_via_llm(
        task_title: str,
        task_description: str,
        persona_prompt: str = "",
    ) -> list[dict[str, Any]]:
        """
        Break down a task into subtasks using LLM.
        Returns JSON list of subtasks.
        """
        system_prompt = """
        You are an expert Project Manager.
        Task: Break down the given task into 3-5 concrete, actionable subtasks.

        Output Format: JSON Array ONLY.
        Example: [{"title": "Step 1", "minutes": 25}, {"title": "Step 2", "minutes": 15}]

        Constraints:
        1. Subtasks should be small enough (15-45 mins).
        2. Titles should be action-oriented.
        """

        prompt = f"Task: {task_title}\nDescription: {task_description}"
        if persona_prompt:
            prompt += f"\n\n{persona_prompt}"

        result = await focus_llm.json_call(
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
            fallback=[],  # 降级返回空列表
        )
        return result if isinstance(result, list) else []

    @staticmethod
    async def get_weekly_stats(db: AsyncSession, user_id: UUID) -> dict[str, Any]:
        """Get focus stats for the current week (Monday to Sunday)"""
        now = _utcnow()
        week_start = (now - datetime.timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + datetime.timedelta(days=7)

        # Get all sessions for this week
        stmt = (
            select(FocusSession)
            .where(
                FocusSession.user_id == user_id,
                FocusSession.start_time >= week_start,
                FocusSession.start_time < week_end,
                FocusSession.status == FocusStatus.COMPLETED,
            )
            .order_by(FocusSession.start_time)
        )
        result = await db.execute(stmt)
        sessions = result.scalars().all()

        # Calculate daily breakdown
        daily_breakdown = {}
        focus_type_distribution = {FocusType.POMODORO.value: 0, FocusType.STOPWATCH.value: 0}

        for session in sessions:
            date_key = session.start_time.strftime("%Y-%m-%d")
            daily_breakdown[date_key] = daily_breakdown.get(date_key, 0) + session.duration_minutes
            focus_type_distribution[session.focus_type.value] += session.duration_minutes

        # Ensure all 7 days are present
        for i in range(7):
            day = week_start + datetime.timedelta(days=i)
            date_key = day.strftime("%Y-%m-%d")
            if date_key not in daily_breakdown:
                daily_breakdown[date_key] = 0

        total_minutes = sum(daily_breakdown.values())
        session_count = len(sessions)
        avg_duration = int(total_minutes / session_count) if session_count > 0 else 0

        # Find best day
        best_day = max(daily_breakdown, key=daily_breakdown.get) if daily_breakdown else None

        # Calculate streaks
        current_streak = await FocusService._calculate_current_streak(db, user_id)
        longest_streak = await FocusService._calculate_longest_streak(db, user_id)

        return {
            "period_start": week_start.isoformat(),
            "period_end": week_end.isoformat(),
            "total_minutes": total_minutes,
            "session_count": session_count,
            "avg_duration": avg_duration,
            "best_day": best_day,
            "daily_breakdown": daily_breakdown,
            "focus_type_distribution": focus_type_distribution,
            "streak_days": current_streak,
            "longest_streak": longest_streak,
        }

    @staticmethod
    async def get_monthly_stats(db: AsyncSession, user_id: UUID) -> dict[str, Any]:
        """Get focus stats for the current month"""
        now = _utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Calculate first day of next month
        if now.month == 12:
            next_month = now.replace(year=now.year + 1, month=1, day=1)
        else:
            next_month = now.replace(month=now.month + 1, day=1)
        month_end = next_month

        # Get all sessions for this month
        stmt = (
            select(FocusSession)
            .where(
                FocusSession.user_id == user_id,
                FocusSession.start_time >= month_start,
                FocusSession.start_time < month_end,
                FocusSession.status == FocusStatus.COMPLETED,
            )
            .order_by(FocusSession.start_time)
        )
        result = await db.execute(stmt)
        sessions = result.scalars().all()

        # Calculate daily breakdown
        daily_breakdown = {}
        focus_type_distribution = {FocusType.POMODORO.value: 0, FocusType.STOPWATCH.value: 0}

        for session in sessions:
            date_key = session.start_time.strftime("%Y-%m-%d")
            daily_breakdown[date_key] = daily_breakdown.get(date_key, 0) + session.duration_minutes
            focus_type_distribution[session.focus_type.value] += session.duration_minutes

        total_minutes = sum(daily_breakdown.values())
        session_count = len(sessions)
        avg_duration = int(total_minutes / session_count) if session_count > 0 else 0

        # Find best day
        best_day = max(daily_breakdown, key=daily_breakdown.get) if daily_breakdown else None

        # Weekly breakdown
        weekly_breakdown = {}
        for session in sessions:
            # Get ISO week number
            week_key = session.start_time.strftime("%Y-W%W")
            weekly_breakdown[week_key] = weekly_breakdown.get(week_key, 0) + session.duration_minutes

        # Calculate streaks
        current_streak = await FocusService._calculate_current_streak(db, user_id)
        longest_streak = await FocusService._calculate_longest_streak(db, user_id)

        return {
            "period_start": month_start.isoformat(),
            "period_end": month_end.isoformat(),
            "total_minutes": total_minutes,
            "session_count": session_count,
            "avg_duration": avg_duration,
            "best_day": best_day,
            "daily_breakdown": daily_breakdown,
            "weekly_breakdown": weekly_breakdown,
            "focus_type_distribution": focus_type_distribution,
            "streak_days": current_streak,
            "longest_streak": longest_streak,
        }

    @staticmethod
    async def get_session_history(db: AsyncSession, user_id: UUID, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        """Get paginated session history"""
        # Get total count
        count_stmt = select(func.count(FocusSession.id)).where(FocusSession.user_id == user_id)
        count_result = await db.execute(count_stmt)
        total_count = count_result.scalar() or 0

        # Get sessions
        stmt = (
            select(FocusSession)
            .where(FocusSession.user_id == user_id)
            .order_by(desc(FocusSession.start_time))
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        sessions = result.scalars().all()

        task_ids = [session.task_id for session in sessions if session.task_id]
        task_title_map: dict[UUID, str] = {}
        if task_ids:
            task_stmt = select(Task.id, Task.title).where(Task.id.in_(task_ids))
            task_result = await db.execute(task_stmt)
            task_title_map = dict(task_result.all())

        session_details = []
        for session in sessions:
            task_title = None
            if session.task_id:
                task_title = task_title_map.get(session.task_id)

            session_details.append(
                {
                    "id": str(session.id),
                    "start_time": session.start_time.isoformat(),
                    "end_time": session.end_time.isoformat(),
                    "duration_minutes": session.duration_minutes,
                    "focus_type": session.focus_type.value,
                    "status": session.status.value,
                    "task_id": str(session.task_id) if session.task_id else None,
                    "task_title": task_title,
                    "white_noise_type": session.white_noise_type,
                }
            )

        return {"sessions": session_details, "total_count": total_count, "limit": limit, "offset": offset}

    @staticmethod
    async def get_heatmap_data(db: AsyncSession, user_id: UUID, days: int = 90) -> dict[str, float]:
        """Get heatmap data for the last N days"""
        end_date = _utcnow()
        start_date = end_date - datetime.timedelta(days=days)

        stmt = select(FocusSession).where(
            FocusSession.user_id == user_id,
            FocusSession.start_time >= start_date,
            FocusSession.start_time < end_date,
            FocusSession.status == FocusStatus.COMPLETED,
        )
        result = await db.execute(stmt)
        sessions = result.scalars().all()

        heatmap_data = {}
        for session in sessions:
            date_key = session.start_time.strftime("%Y-%m-%d")
            heatmap_data[date_key] = heatmap_data.get(date_key, 0.0) + session.duration_minutes

        if not heatmap_data:
            heatmap_data[end_date.strftime("%Y-%m-%d")] = 0.0

        return heatmap_data

    @staticmethod
    async def _calculate_current_streak(db: AsyncSession, user_id: UUID) -> int:
        """Calculate current consecutive days streak"""
        today = _utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        check_date = today
        streak = 0

        # Check up to 365 days back
        for _ in range(365):
            next_day = check_date + datetime.timedelta(days=1)
            day_start = check_date
            day_end = next_day

            # Check if any completed session exists for this day
            stmt = select(func.count(FocusSession.id)).where(
                FocusSession.user_id == user_id,
                FocusSession.start_time >= day_start,
                FocusSession.start_time < day_end,
                FocusSession.status == FocusStatus.COMPLETED,
            )
            result = await db.execute(stmt)
            count = result.scalar() or 0

            if count > 0:
                streak += 1
                check_date = day_start - datetime.timedelta(days=1)
            else:
                # If checking today and no sessions, check yesterday
                if check_date == today:
                    check_date = day_start - datetime.timedelta(days=1)
                    continue
                break

        return streak

    @staticmethod
    async def _calculate_longest_streak(db: AsyncSession, user_id: UUID) -> int:
        """Calculate the longest consecutive days streak ever"""
        # Get all days with completed sessions
        stmt = (
            select(func.date(FocusSession.start_time))
            .where(FocusSession.user_id == user_id, FocusSession.status == FocusStatus.COMPLETED)
            .distinct()
            .order_by(func.date(FocusSession.start_time))
        )
        result = await db.execute(stmt)
        dates = [row[0] for row in result.all()]

        if not dates:
            return 0

        longest_streak = 1
        current_streak = 1
        prev_date = dates[0]

        for date in dates[1:]:
            if (date - prev_date).days == 1:
                current_streak += 1
            elif (date - prev_date).days > 1:
                longest_streak = max(longest_streak, current_streak)
                current_streak = 1
            prev_date = date

        longest_streak = max(longest_streak, current_streak)
        return longest_streak


focus_service = FocusService()
