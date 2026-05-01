"""
Chat signal collector - infer preferences from conversation behavior.
"""
from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from loguru import logger

from app.core.cache import cache_service
from app.db.session import AsyncSessionLocal
from app.services.profile_write_service import ProfileWriteService
from app.services.signal_adaptation import recency_weight, weighted_average


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ChatSignalCollector:
    """Collect chat signals and update inferred preferences periodically."""

    WINDOW_SIZE = 20
    WINDOW_TTL_SECONDS = 7 * 24 * 3600
    TOPIC_SIMILARITY_THRESHOLD = 0.4

    def __init__(self, redis=None):
        self.redis = redis or cache_service.redis

    async def collect_signals(
        self,
        user_id: UUID,
        user_message: str,
        ai_response: str,
        conversation_id: str,
        turn_index: int,
        timestamp: datetime | None = None,
    ) -> None:
        if not self.redis:
            return
        _ = ai_response

        ts = timestamp or _utcnow()
        tokens = self._extract_tokens(user_message)
        prev_entry = await self._get_latest_entry(user_id)
        follow_up = self._is_follow_up(tokens, prev_entry.get("tokens") if prev_entry else [])
        gratitude = self._detect_gratitude(user_message)
        dissatisfaction = self._detect_dissatisfaction(user_message)
        complexity = self._estimate_complexity(user_message)

        entry = {
            "ts": ts.isoformat(),
            "hour": ts.hour,
            "tokens": tokens,
            "follow_up": follow_up,
            "gratitude": gratitude,
            "dissatisfaction": dissatisfaction,
            "complexity": complexity,
            "conversation_id": conversation_id,
            "turn_index": turn_index,
        }
        await self._store_entry(user_id, entry)

        counter = await self._increment_counter(user_id)
        if counter % self.WINDOW_SIZE != 0:
            return

        entries = await self._load_entries(user_id)
        if not entries:
            return

        updates = self._build_updates(entries)
        if not updates:
            return

        try:
            async with AsyncSessionLocal() as db:
                service = ProfileWriteService(db, self.redis)
                await service.update_inferred_preference(
                    user_id=user_id,
                    updates=updates,
                    source="ai_inferred",
                )
        except Exception as exc:
            logger.warning("ChatSignalCollector failed to persist updates: %s", exc)

    async def _store_entry(self, user_id: UUID, entry: dict[str, Any]) -> None:
        key = f"user:chat:signals:{user_id}"
        try:
            await self.redis.lpush(key, json.dumps(entry, ensure_ascii=False))
            await self.redis.ltrim(key, 0, self.WINDOW_SIZE - 1)
            await self.redis.expire(key, self.WINDOW_TTL_SECONDS)
        except Exception as exc:
            logger.warning("Failed to cache chat signal entry: %s", exc)

    async def _get_latest_entry(self, user_id: UUID) -> dict[str, Any] | None:
        key = f"user:chat:signals:{user_id}"
        try:
            raw = await self.redis.lindex(key, 0)
        except Exception:
            return None
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
        except Exception:
            return None
        return parsed if isinstance(parsed, dict) else None

    async def _increment_counter(self, user_id: UUID) -> int:
        key = f"user:chat:signals:count:{user_id}"
        try:
            counter = await self.redis.incr(key)
            await self.redis.expire(key, self.WINDOW_TTL_SECONDS)
            return int(counter)
        except Exception as exc:
            logger.warning("Failed to increment chat signal counter: %s", exc)
            return 0

    async def _load_entries(self, user_id: UUID) -> list[dict[str, Any]]:
        key = f"user:chat:signals:{user_id}"
        try:
            raw_entries = await self.redis.lrange(key, 0, self.WINDOW_SIZE - 1)
        except Exception as exc:
            logger.warning("Failed to load chat signal entries: %s", exc)
            return []
        entries: list[dict[str, Any]] = []
        for raw in raw_entries or []:
            try:
                parsed = json.loads(raw)
            except Exception:
                continue
            if isinstance(parsed, dict):
                entries.append(parsed)
        return list(reversed(entries))

    def _build_updates(self, entries: list[dict[str, Any]]) -> dict[str, Any]:
        if not entries:
            return {}

        weighted_complexity: list[tuple[float, float]] = []
        for entry in entries:
            weight = self._entry_weight(entry)
            weighted_complexity.append((float(entry.get("complexity") or 0.0), weight))

        avg_complexity = weighted_average(weighted_complexity)
        if avg_complexity is None:
            return {}

        topic_streak_score = self._topic_streak_score(entries)
        satisfaction_rate = self._satisfaction_rate(entries)
        active_hours = self._active_hours(entries)

        updates: dict[str, Any] = {
            "avg_question_complexity": round(avg_complexity, 3),
            "response_satisfaction_rate": round(satisfaction_rate, 3),
        }
        if topic_streak_score >= 2.1:
            updates["depth_preference_signal"] = 0.8
        if active_hours:
            updates["chat_active_hours"] = active_hours
        return updates

    def _topic_streak_score(self, entries: list[dict[str, Any]]) -> float:
        max_streak = 1.0
        current = 1.0
        for idx in range(1, len(entries)):
            tokens_a = entries[idx - 1].get("tokens") or []
            tokens_b = entries[idx].get("tokens") or []
            similarity = self._topic_similarity(tokens_a, tokens_b)
            if similarity >= self.TOPIC_SIMILARITY_THRESHOLD:
                pair_weight = (self._entry_weight(entries[idx - 1]) + self._entry_weight(entries[idx])) / 2.0
                current += pair_weight
            else:
                current = 1.0
            max_streak = max(max_streak, current)
        return max_streak

    def _satisfaction_rate(self, entries: list[dict[str, Any]]) -> float:
        score = 0.0
        total = 0.0
        for entry in entries:
            weight = self._entry_weight(entry)
            gratitude = bool(entry.get("gratitude"))
            dissatisfaction = bool(entry.get("dissatisfaction"))
            follow_up = bool(entry.get("follow_up"))
            if gratitude:
                score += 1.0 * weight
            elif dissatisfaction:
                score += 0.0
            elif follow_up:
                score += 0.25 * weight
            else:
                # Most plain messages are neutral rather than affirmative.
                score += 0.5 * weight
            total += weight
        return score / total if total else 0.0

    def _active_hours(self, entries: list[dict[str, Any]]) -> list[int]:
        counts: dict[int, float] = {}
        for entry in entries:
            hour = entry.get("hour")
            try:
                hour_int = int(hour)
            except (TypeError, ValueError):
                continue
            if 0 <= hour_int <= 23:
                counts[hour_int] = counts.get(hour_int, 0.0) + self._entry_weight(entry)
        sorted_hours = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return [hour for hour, _ in sorted_hours[:3]]

    @staticmethod
    def _entry_weight(entry: dict[str, Any]) -> float:
        raw_ts = entry.get("ts")
        if not raw_ts:
            return 0.3
        try:
            parsed = datetime.fromisoformat(str(raw_ts))
        except Exception:
            return 0.3
        return recency_weight(parsed, now=_utcnow(), half_life_days=2.5, min_weight=0.3)

    def _is_follow_up(self, tokens: list[str], prev_tokens: list[str]) -> bool:
        if not tokens or not prev_tokens:
            return False
        similarity = self._topic_similarity(tokens, prev_tokens)
        return similarity >= self.TOPIC_SIMILARITY_THRESHOLD

    @staticmethod
    def _topic_similarity(tokens_a: list[str], tokens_b: list[str]) -> float:
        set_a = set(tokens_a)
        set_b = set(tokens_b)
        if not set_a or not set_b:
            return 0.0
        intersection = set_a.intersection(set_b)
        union = set_a.union(set_b)
        return len(intersection) / len(union)

    @staticmethod
    def _detect_gratitude(message: str) -> bool:
        if not message:
            return False
        lowered = message.lower()
        markers = [
            "\u8c22\u8c22",
            "\u660e\u767d\u4e86",
            "\u61c2\u4e86",
            "got it",
            "thank",
            "thanks",
            "thx",
            "understood",
        ]
        return any(marker in lowered for marker in markers)

    @staticmethod
    def _detect_dissatisfaction(message: str) -> bool:
        if not message:
            return False
        lowered = message.lower()
        markers = [
            "不对",
            "不太对",
            "不明白",
            "没懂",
            "还是不懂",
            "这不行",
            "不满意",
            "不准确",
            "错误",
            "wrong",
            "not right",
            "not helpful",
            "still confused",
        ]
        return any(marker in lowered for marker in markers)

    @staticmethod
    def _estimate_complexity(message: str) -> float:
        if not message:
            return 0.0
        length_score = min(len(message) / 400.0, 1.0)
        code_markers = bool(re.search(r"```|`.+?`|\\{|\\}|;|==|\\bdef\\b|\\bclass\\b", message))
        formula_markers = bool(re.search(r"=|\\^|sqrt|∑|∫|\\bcalc\\b", message))
        question_markers = bool(re.search(r"[?？]|如何|为什么|why|how", message.lower()))

        score = length_score
        if code_markers:
            score += 0.2
        if formula_markers:
            score += 0.1
        if question_markers:
            score += 0.1
        return min(score, 1.0)

    @staticmethod
    def _extract_tokens(message: str) -> list[str]:
        if not message:
            return []
        tokens = re.findall(r"[a-zA-Z0-9\\u4e00-\\u9fff]+", message.lower())
        stopwords = {
            "the", "and", "for", "with", "this", "that", "you", "your", "are", "was", "were",
            "\u7684", "\u4e86", "\u662f", "\u6211", "\u4f60", "\u4ed6", "\u5979", "\u5b83",
            "\u5728", "\u548c", "\u5c31", "\u6709", "\u4e5f", "\u90fd", "\u8fd8", "\u5417",
        }
        filtered = [token for token in tokens if len(token) > 1 and token not in stopwords]
        return filtered[:8]
