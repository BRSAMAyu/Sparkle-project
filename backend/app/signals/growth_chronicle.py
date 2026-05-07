"""
Core: execution
Phase: reflect→reinforce
Stage: Signal-to-Action Spine P3-2 GrowthChronicle

Growth Chronicle — user-co-owned growth narrative.

Chronicle entries turn verified outcomes, user corrections, and repeated
strategy patterns into editable narrative moments. This is not surveillance:
entries are user-visible, user-editable, and can be hidden without deletion.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy import select

from app.signals.types import _uid

_CHRONICLE_KEY = "spine:chronicle:{user_id}"
_CHRONICLE_TTL_SECONDS = 730 * 24 * 3600  # 2 years; DB is source of truth, Redis is fast-read cache
_MAX_STORED_ENTRIES = 100
_VALID_ENTRY_TYPES = {"milestone", "turning_point", "pattern_discovered", "user_reflection"}
_VALID_USER_STATUSES = {"pending", "confirmed", "edited", "rejected", "hidden"}


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_dict"):
        data = value.to_dict()
        if isinstance(data, dict):
            return data
    return {}


def _parse_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except ValueError:
        return None


@dataclass
class ChronicleEntry:
    """A user-visible, user-editable growth narrative entry.

    P3-4 ruling: Long-term insights must be user-visible, user-confirmable.
    Unconfirmed insights cannot be used as hard constraints.
    """

    entry_id: str
    user_id: str
    entry_type: str
    timestamp: str
    title: str
    narrative: str
    evidence_refs: list[str]
    user_editable: bool
    user_hidden: bool = False
    # P3-4 fields
    claim: str = ""
    scope: str = "general"  # e.g. "exam_sprint_context"
    confidence: float = 0.5
    user_status: str = "pending"  # pending / confirmed / edited / rejected / hidden
    recommended_future_use: list[str] = field(default_factory=list)
    retract_if: list[str] = field(default_factory=list)

    @property
    def is_confirmed(self) -> bool:
        return self.user_status == "confirmed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "user_id": self.user_id,
            "entry_type": self.entry_type,
            "timestamp": self.timestamp,
            "title": self.title,
            "narrative": self.narrative,
            "evidence_refs": self.evidence_refs,
            "user_editable": self.user_editable,
            "user_hidden": self.user_hidden,
            "claim": self.claim,
            "scope": self.scope,
            "confidence": self.confidence,
            "user_status": self.user_status,
            "recommended_future_use": self.recommended_future_use,
            "retract_if": self.retract_if,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ChronicleEntry:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class GrowthChronicleService:
    """Build and store user-governed growth narrative entries."""

    def __init__(self, redis_client: Any, db_session: Any | None = None):
        self.redis = redis_client
        self.db = db_session

    async def add_entry(self, user_id: str, entry: ChronicleEntry) -> None:
        """Add an entry to a user's chronicle JSON list. Uses WATCH for atomicity."""
        if entry.user_id != user_id:
            raise ValueError("chronicle entry user_id must match storage user_id")
        if entry.entry_type not in _VALID_ENTRY_TYPES:
            raise ValueError(f"invalid chronicle entry type: {entry.entry_type}")

        key = _CHRONICLE_KEY.format(user_id=user_id)
        entries = await self._load_entries(user_id)
        entries = [existing for existing in entries if existing.entry_id != entry.entry_id]
        entries.insert(0, entry)
        payload = json.dumps([e.to_dict() for e in entries[:_MAX_STORED_ENTRIES]], ensure_ascii=False)

        try:
            await self.redis.watch(key)
            try:
                async with self.redis.pipeline() as pipe:
                    pipe.multi()
                    pipe.set(key, payload, ex=_CHRONICLE_TTL_SECONDS)
                    await pipe.execute()
            except (AttributeError, TypeError, RuntimeError):
                await self.redis.set(key, payload, ex=_CHRONICLE_TTL_SECONDS)
        except Exception:
            # WATCH not supported (FakeRedis) — just write directly
            logger.debug("chronicle add_entry: WATCH fallback for user={}", user_id)
            await self._save_entries(user_id, entries[:_MAX_STORED_ENTRIES])
        finally:
            try:
                await self.redis.unwatch()
            except Exception:
                logger.debug("chronicle add_entry: unwatch failed for user={}", user_id)

        # Persist to DB as source of truth (Redis is a fast-read cache)
        await self._save_durable_entries(user_id, entries[:_MAX_STORED_ENTRIES])

        logger.info(
            "GrowthChronicle entry added: user={} entry={} type={}",
            user_id, entry.entry_id, entry.entry_type,
        )

    async def get_chronicle(self, user_id: str, limit: int = 20) -> list[ChronicleEntry]:
        """Return visible chronicle entries, newest first."""
        entries = [entry for entry in await self._load_entries(user_id) if not entry.user_hidden]
        entries.sort(key=lambda entry: _parse_time(entry.timestamp) or datetime.min.replace(tzinfo=UTC), reverse=True)
        return entries[:limit]

    async def hide_entry(self, user_id: str, entry_id: str) -> None:
        """Hide an entry without deleting its evidence-backed record. Uses WATCH for atomicity."""
        key = _CHRONICLE_KEY.format(user_id=user_id)
        entries = await self._load_entries(user_id)
        changed = False
        for entry in entries:
            if entry.entry_id == entry_id:
                entry.user_hidden = True
                changed = True
                break
        if changed:
            payload = json.dumps([e.to_dict() for e in entries], ensure_ascii=False)
            try:
                await self.redis.watch(key)
                try:
                    async with self.redis.pipeline() as pipe:
                        pipe.multi()
                        pipe.set(key, payload, ex=_CHRONICLE_TTL_SECONDS)
                        await pipe.execute()
                except (AttributeError, TypeError, RuntimeError):
                    await self.redis.set(key, payload, ex=_CHRONICLE_TTL_SECONDS)
            except Exception:
                logger.debug("chronicle hide_entry: WATCH fallback for user={}", user_id)
                await self._save_entries(user_id, entries)
            finally:
                try:
                    await self.redis.unwatch()
                except Exception:
                    logger.debug("chronicle hide_entry: unwatch failed for user={}", user_id)
        logger.info("GrowthChronicle entry hidden: user={} entry={}", user_id, entry_id)

    async def edit_entry(self, user_id: str, entry_id: str, new_narrative: str) -> None:
        """Edit the user-facing narrative text for an editable entry. Uses WATCH for atomicity."""
        key = _CHRONICLE_KEY.format(user_id=user_id)
        entries = await self._load_entries(user_id)
        for entry in entries:
            if entry.entry_id != entry_id:
                continue
            if not entry.user_editable:
                raise ValueError(f"chronicle entry is not editable: {entry_id}")
            entry.narrative = new_narrative
            entry.user_status = "edited"
            payload = json.dumps([e.to_dict() for e in entries], ensure_ascii=False)
            try:
                await self.redis.watch(key)
                try:
                    async with self.redis.pipeline() as pipe:
                        pipe.multi()
                        pipe.set(key, payload, ex=_CHRONICLE_TTL_SECONDS)
                        await pipe.execute()
                except (AttributeError, TypeError, RuntimeError):
                    await self.redis.set(key, payload, ex=_CHRONICLE_TTL_SECONDS)
            except Exception:
                logger.debug("chronicle edit_entry: WATCH fallback for user={}", user_id)
                await self._save_entries(user_id, entries)
            finally:
                try:
                    await self.redis.unwatch()
                except Exception:
                    logger.debug("chronicle edit_entry: unwatch failed for user={}", user_id)
            logger.info("GrowthChronicle entry edited: user={} entry={}", user_id, entry_id)
            return

    async def confirm_entry(self, user_id: str, entry_id: str) -> bool:
        """P3-4: User confirms a chronicle entry. Only confirmed entries become hard constraints."""
        entries = await self._load_entries(user_id)
        for entry in entries:
            if entry.entry_id == entry_id:
                if entry.user_status not in _VALID_USER_STATUSES:
                    entry.user_status = "pending"
                entry.user_status = "confirmed"
                await self._save_entries(user_id, entries)
                logger.info("GrowthChronicle entry confirmed: user={} entry={}", user_id, entry_id)
                return True
        return False

    async def reject_entry(self, user_id: str, entry_id: str) -> bool:
        """P3-4: User rejects a chronicle entry. Rejected entries are hidden."""
        entries = await self._load_entries(user_id)
        for entry in entries:
            if entry.entry_id == entry_id:
                entry.user_status = "rejected"
                entry.user_hidden = True
                await self._save_entries(user_id, entries)
                logger.info("GrowthChronicle entry rejected: user={} entry={}", user_id, entry_id)
                return True
        return False

    async def get_confirmed_entries(self, user_id: str) -> list[ChronicleEntry]:
        """P3-4: Get only confirmed entries that pass retraction checks."""
        entries = await self._load_entries(user_id)
        confirmed = [e for e in entries if e.is_confirmed and not e.user_hidden]
        return [e for e in confirmed if not self._should_retract(e, user_id)]

    def _should_retract(self, entry: ChronicleEntry, user_id: str) -> bool:
        """Check if a confirmed entry should be retracted based on its conditions."""
        import re

        for condition in entry.retract_if:
            if condition.startswith("outcome_reverted:"):
                outcome_id = condition.split(":", 1)[1]
                if outcome_id:
                    key = f"spine:outcome:reverted:{outcome_id}"
                    if self.redis and self.redis.exists(key):
                        logger.info(
                            "GrowthChronicle retracting entry {}: outcome {} reverted",
                            entry.entry_id,
                            outcome_id,
                        )
                        return True
            elif condition == "user_inactive:30d" or condition == "user_inactive:60d":
                days = 30 if condition == "user_inactive:30d" else 60
                active_key = f"spine:user:{user_id}:last_active_ts"
                if self.redis:
                    last_active = self.redis.get(active_key)
                    if last_active:
                        try:
                            last_active_ts = float(last_active)
                            since = datetime.now(UTC).timestamp() - last_active_ts
                            if since > days * 24 * 3600:
                                return True
                        except (TypeError, ValueError):
                            pass
            elif condition.startswith("strategy_negative_streak:"):
                parsed = re.search(r"strategy_negative_streak:(?:.*:)?(\d+)", condition)
                if parsed:
                    threshold = int(parsed.group(1))
                    streak_key = f"spine:strategy:{entry.entry_id}:negative_streak"
                    if self.redis:
                        streak_val = self.redis.get(streak_key)
                        if streak_val:
                            try:
                                if int(streak_val) >= threshold:
                                    return True
                            except (TypeError, ValueError):
                                pass
        return False

    async def build_return_case_file(self, user_id: str) -> dict[str, Any]:
        """P3-4: Generate a ReturnCaseFile from chronicle for returning users."""
        entries = await self.get_chronicle(user_id, limit=20)
        confirmed = [e for e in entries if e.is_confirmed]
        pending = [e for e in entries if e.user_status == "pending"]

        return {
            "user_id": user_id,
            "chronicle_summary": {
                "total_entries": len(entries),
                "confirmed_count": len(confirmed),
                "pending_count": len(pending),
            },
            "confirmed_insights": [
                {
                    "claim": e.claim,
                    "scope": e.scope,
                    "confidence": e.confidence,
                    "recommended_future_use": e.recommended_future_use,
                }
                for e in confirmed[:10]
            ],
            "pending_review": [e.entry_id for e in pending],
            "generated_at": _utcnow(),
        }

    def build_milestone_from_outcome(self, outcome: dict[str, Any]) -> ChronicleEntry | None:
        """
        Build a milestone entry from a positive OutcomeRecord.

        Only effective outcomes with high attribution confidence become
        chronicle material, keeping the story grounded in verified evidence.
        """
        data = _as_dict(outcome)
        if data.get("attribution") != "effective":
            return None
        if float(data.get("attribution_confidence", 0.0)) < 0.8:
            return None

        actual = _as_dict(data.get("actual_outcome"))
        user_id = str(data.get("user_id") or actual.get("user_id") or "")
        count = int(actual.get("count") or data.get("count") or 1)
        task_type = str(actual.get("type") or actual.get("task_type") or data.get("task_type") or "学习")
        strategy = str(
            actual.get("strategy")
            or data.get("strategy")
            or data.get("reason")
            or "这个策略"
        )
        intervention = str(
            data.get("intervention_summary")
            or data.get("intervention")
            or "一次有效策略"
        )

        evidence_refs = self._collect_evidence_refs(
            data,
            ["outcome_id", "causal_trace_id", "trace_id", "achievement_id"],
        )

        return ChronicleEntry(
            entry_id=_uid("chron"),
            user_id=user_id,
            entry_type="milestone",
            timestamp=str(data.get("created_at") or _utcnow()),
            title=f"里程碑：{intervention}",
            narrative=f"你连续{count}次完成了{task_type}任务，系统发现{strategy}对你特别有效。",
            evidence_refs=evidence_refs,
            user_editable=True,
            retract_if=[
                f"outcome_reverted:{data.get('outcome_id', '')}",
                "user_inactive:30d",
            ],
        )

    def build_turning_point_from_correction(self, correction: dict[str, Any]) -> ChronicleEntry:
        """Build a turning point from a user correction."""
        data = _as_dict(correction)
        topic = str(data.get("topic") or data.get("state_key") or "这个问题")
        lesson = str(data.get("lesson") or data.get("new_hypothesis") or "以后先确认关键假设")
        evidence_refs = self._collect_evidence_refs(
            data,
            ["correction_id", "trace_id", "signal_id", "outcome_id"],
        )

        return ChronicleEntry(
            entry_id=_uid("chron"),
            user_id=str(data.get("user_id") or ""),
            entry_type="turning_point",
            timestamp=str(data.get("timestamp") or data.get("created_at") or _utcnow()),
            title=f"转折点：你修正了{topic}",
            narrative=f"系统对{topic}的判断有偏差，你纠正了它。这让系统学会了{lesson}。",
            evidence_refs=evidence_refs,
            user_editable=True,
        )

    def build_pattern_discovery(self, patterns: list[dict[str, Any]]) -> ChronicleEntry | None:
        """
        Build a pattern discovery from multiple outcomes.

        Needs at least five outcomes with the same strategy before presenting it
        as a user-facing pattern.
        """
        by_strategy: dict[str, list[dict[str, Any]]] = {}
        for pattern in patterns:
            data = _as_dict(pattern)
            strategy = self._strategy_from_pattern(data)
            if not strategy:
                continue
            by_strategy.setdefault(strategy, []).append(data)

        eligible = [
            (strategy, items)
            for strategy, items in by_strategy.items()
            if len(items) >= 5
        ]
        if not eligible:
            return None

        strategy, items = max(eligible, key=lambda pair: len(pair[1]))
        user_id = str(items[0].get("user_id") or _as_dict(items[0].get("actual_outcome")).get("user_id") or "")
        task_type = self._common_task_type(items)
        evidence_refs = []
        for item in items[:10]:
            evidence_refs.extend(self._collect_evidence_refs(item, ["outcome_id", "causal_trace_id", "trace_id"]))

        return ChronicleEntry(
            entry_id=_uid("chron"),
            user_id=user_id,
            entry_type="pattern_discovered",
            timestamp=_utcnow(),
            title=f"发现模式：{strategy}",
            narrative=f"最近{len(items)}次{task_type}任务里，{strategy}反复带来更好的结果。这个模式可以作为下一轮计划的参考。",
            evidence_refs=list(dict.fromkeys(evidence_refs)),
            user_editable=True,
            retract_if=[
                f"strategy_negative_streak:{strategy}:3",
                "user_inactive:60d",
            ],
        )

    async def generate_weekly_summary(self, user_id: str) -> str:
        """
        Generate a template-based weekly narrative summary.

        This deliberately avoids AI generation and uses only user-visible
        ChronicleEntry aggregation.
        """
        visible_entries = await self.get_chronicle(user_id, limit=_MAX_STORED_ENTRIES)
        cutoff = datetime.now(UTC) - timedelta(days=7)
        weekly_entries = [
            entry
            for entry in visible_entries
            if (_parse_time(entry.timestamp) or datetime.now(UTC)) >= cutoff
        ]

        if not weekly_entries:
            return "这周还没有形成新的成长叙事。等出现可靠的里程碑、修正或模式后，系统会把它整理成你可以编辑的记录。"

        counts = {
            "milestone": sum(1 for entry in weekly_entries if entry.entry_type == "milestone"),
            "turning_point": sum(1 for entry in weekly_entries if entry.entry_type == "turning_point"),
            "pattern_discovered": sum(1 for entry in weekly_entries if entry.entry_type == "pattern_discovered"),
            "user_reflection": sum(1 for entry in weekly_entries if entry.entry_type == "user_reflection"),
        }
        highlights = "；".join(entry.title for entry in weekly_entries[:3])
        parts = [f"这周你的成长编年史新增了{len(weekly_entries)}条记录"]
        if counts["milestone"]:
            parts.append(f"{counts['milestone']}个里程碑")
        if counts["turning_point"]:
            parts.append(f"{counts['turning_point']}次重要修正")
        if counts["pattern_discovered"]:
            parts.append(f"{counts['pattern_discovered']}个被验证的模式")
        if counts["user_reflection"]:
            parts.append(f"{counts['user_reflection']}条你的反思")

        return f"{'，'.join(parts)}。本周重点：{highlights}。你可以继续编辑或隐藏这些叙事。"

    async def _load_entries(self, user_id: str) -> list[ChronicleEntry]:
        raw = await self.redis.get(_CHRONICLE_KEY.format(user_id=user_id))
        entries = self._parse_raw_entries(raw)
        if entries:
            return entries
        durable = await self._load_durable_entries(user_id)
        if durable:
            await self._save_entries(user_id, durable)
        return durable

    @staticmethod
    def _parse_raw_entries(raw: Any) -> list[ChronicleEntry]:
        """Parse raw Redis response into ChronicleEntry list."""
        if raw is None:
            return []
        if not raw:
            return []
        try:
            data = json.loads(raw if isinstance(raw, str) else raw.decode() if isinstance(raw, bytes) else "[]")
        except (json.JSONDecodeError, TypeError, AttributeError):
            return []
        if not isinstance(data, list):
            return []
        return [
            ChronicleEntry.from_dict(item)
            for item in data
            if isinstance(item, dict)
        ]

    async def _save_entries(self, user_id: str, entries: list[ChronicleEntry]) -> None:
        await self.redis.set(
            _CHRONICLE_KEY.format(user_id=user_id),
            json.dumps([entry.to_dict() for entry in entries], ensure_ascii=False),
            ex=_CHRONICLE_TTL_SECONDS,
        )
        await self._save_durable_entries(user_id, entries)

    async def _save_durable_entries(self, user_id: str, entries: list[ChronicleEntry]) -> None:
        if self.db is None:
            return
        try:
            from app.aurora.runtime_v1.models import GrowthChronicleSnapshot

            result = await self.db.execute(
                select(GrowthChronicleSnapshot).where(
                    GrowthChronicleSnapshot.user_id == user_id,
                    GrowthChronicleSnapshot.deleted_at.is_(None),
                )
            )
            record = result.scalar_one_or_none()
            if record is None:
                record = GrowthChronicleSnapshot(user_id=user_id)
            record.entry_count = len(entries)
            record.confirmed_count = sum(1 for entry in entries if entry.is_confirmed and not entry.user_hidden)
            record.payload = [entry.to_dict() for entry in entries[:_MAX_STORED_ENTRIES]]
            record.last_saved_at = datetime.now(UTC).replace(tzinfo=None)
            record.runtime_metadata = {
                "source": "growth_chronicle_service",
                "user_visible": True,
                "editable": True,
            }
            self.db.add(record)
            await self.db.commit()
        except Exception as exc:
            logger.warning("GrowthChronicle durable save skipped user={}: {}", user_id, exc)

    async def _load_durable_entries(self, user_id: str) -> list[ChronicleEntry]:
        if self.db is None:
            return []
        try:
            from app.aurora.runtime_v1.models import GrowthChronicleSnapshot

            result = await self.db.execute(
                select(GrowthChronicleSnapshot)
                .where(
                    GrowthChronicleSnapshot.user_id == user_id,
                    GrowthChronicleSnapshot.deleted_at.is_(None),
                )
                .order_by(GrowthChronicleSnapshot.last_saved_at.desc())
                .limit(1)
            )
            record = result.scalar_one_or_none()
            if record is None:
                return []
            return self._parse_raw_entries(json.dumps(record.payload or [], ensure_ascii=False))
        except Exception as exc:
            logger.warning("GrowthChronicle durable load skipped user={}: {}", user_id, exc)
            return []

    @staticmethod
    def _collect_evidence_refs(data: dict[str, Any], keys: list[str]) -> list[str]:
        refs = []
        for key in keys:
            value = data.get(key)
            if value:
                refs.append(str(value))
        return list(dict.fromkeys(refs))

    @staticmethod
    def _strategy_from_pattern(pattern: dict[str, Any]) -> str:
        actual = _as_dict(pattern.get("actual_outcome"))
        value = (
            pattern.get("strategy")
            or actual.get("strategy")
            or pattern.get("policy_key")
            or pattern.get("reason")
            or pattern.get("intervention_summary")
            or pattern.get("intervention")
        )
        return str(value) if value else ""

    @staticmethod
    def _common_task_type(items: list[dict[str, Any]]) -> str:
        counts: dict[str, int] = {}
        for item in items:
            actual = _as_dict(item.get("actual_outcome"))
            task_type = str(actual.get("type") or actual.get("task_type") or item.get("task_type") or "学习")
            counts[task_type] = counts.get(task_type, 0) + 1
        return max(counts.items(), key=lambda pair: pair[1])[0] if counts else "学习"
