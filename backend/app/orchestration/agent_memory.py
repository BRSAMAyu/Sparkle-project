"""Per-agent per-user memory for personalization."""

from __future__ import annotations

import json
import re
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any

from loguru import logger


TOPIC_STOPWORDS = {
    "这个",
    "那个",
    "一下",
    "一个",
    "我们",
    "你们",
    "他们",
    "然后",
    "就是",
    "怎么",
    "什么",
    "please",
    "about",
    "with",
    "that",
    "this",
    "help",
}


def extract_topics(text: str, *, limit: int = 3) -> list[str]:
    raw = str(text or "").strip().lower()
    if not raw:
        return []
    tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z][a-zA-Z0-9_+-]{2,}", raw)
    counter: Counter[str] = Counter()
    for token in tokens:
        token = token.strip()
        if not token or token in TOPIC_STOPWORDS:
            continue
        counter[token] += 1
    return [topic for topic, _ in counter.most_common(limit)]


@dataclass
class AgentUserPreference:
    """One agent's preference profile for a specific user."""

    agent_id: str
    user_id: str
    total_interactions: int = 0
    positive_feedback_count: int = 0
    negative_feedback_count: int = 0
    preferred_detail_level: str = "medium"
    preferred_language: str = "auto"
    preferred_response_style: str = "balanced"
    frequent_topics: list[str] = field(default_factory=list)
    last_interaction_ts: float = 0.0
    custom_signals: dict[str, Any] = field(default_factory=dict)


class AgentMemoryService:
    """Redis-backed per-agent per-user memory."""

    KEY_PREFIX = "sparkle:agent_memory"
    TTL_SECONDS = 86400 * 90

    def __init__(self, redis_client):
        self.redis = redis_client

    def _key(self, agent_id: str, user_id: str) -> str:
        return f"{self.KEY_PREFIX}:{agent_id}:{user_id}"

    async def get_preference(self, agent_id: str, user_id: str) -> AgentUserPreference:
        if not self.redis:
            return AgentUserPreference(agent_id=agent_id, user_id=user_id)
        try:
            raw = await self.redis.get(self._key(agent_id, user_id))
            if not raw:
                return AgentUserPreference(agent_id=agent_id, user_id=user_id)
            data = json.loads(raw)
            return AgentUserPreference(**data)
        except Exception as exc:
            logger.debug(f"Failed to load agent memory: {exc}")
            return AgentUserPreference(agent_id=agent_id, user_id=user_id)

    async def save_preference(self, pref: AgentUserPreference) -> None:
        if not self.redis:
            return
        pref.last_interaction_ts = time.time()
        try:
            await self.redis.setex(
                self._key(pref.agent_id, pref.user_id),
                self.TTL_SECONDS,
                json.dumps(asdict(pref), ensure_ascii=False),
            )
        except Exception as exc:
            logger.debug(f"Failed to save agent memory: {exc}")

    async def record_interaction(
        self,
        agent_id: str,
        user_id: str,
        *,
        feedback: str | None = None,
        topics: list[str] | None = None,
        signals: dict[str, Any] | None = None,
    ) -> AgentUserPreference:
        pref = await self.get_preference(agent_id, user_id)
        pref.total_interactions += 1

        if feedback == "up":
            pref.positive_feedback_count += 1
        elif feedback == "down":
            pref.negative_feedback_count += 1

        if topics:
            topic_scores: Counter[str] = Counter()
            for idx, topic in enumerate(pref.frequent_topics):
                topic_scores[str(topic)] += max(1, 5 - idx)
            for topic in topics:
                cleaned = str(topic).strip()
                if cleaned:
                    topic_scores[cleaned] += 5
            pref.frequent_topics = [topic for topic, _ in topic_scores.most_common(5)]

        if signals:
            pref.custom_signals.update(dict(signals))

        await self.save_preference(pref)
        return pref

    async def infer_preferences_from_feedback(
        self,
        agent_id: str,
        user_id: str,
        feedback_type: str,
        reasons: list[str] | None = None,
    ) -> None:
        pref = await self.get_preference(agent_id, user_id)
        reasons = [str(reason).strip().lower() for reason in (reasons or []) if str(reason).strip()]

        if feedback_type == "up":
            pref.positive_feedback_count += 1
        elif feedback_type == "down":
            pref.negative_feedback_count += 1

        if "verbose" in reasons:
            pref.preferred_detail_level = "brief"
            pref.preferred_response_style = "concise"
        elif "incomplete" in reasons:
            pref.preferred_detail_level = "detailed"
            pref.preferred_response_style = "thorough"
        elif "too_hard" in reasons:
            pref.custom_signals["difficulty_preference"] = "easier"
        elif "too_simple" in reasons:
            pref.custom_signals["difficulty_preference"] = "harder"

        await self.save_preference(pref)

    async def get_prompt_context(self, agent_id: str, user_id: str) -> str:
        pref = await self.get_preference(agent_id, user_id)
        if pref.total_interactions == 0:
            return ""

        lines = [f"与该用户已交互 {pref.total_interactions} 次。"]
        if pref.frequent_topics:
            lines.append(f"用户常关注: {', '.join(pref.frequent_topics)}")

        total_fb = pref.positive_feedback_count + pref.negative_feedback_count
        if total_fb >= 3:
            pos_rate = pref.positive_feedback_count / total_fb
            if pos_rate > 0.8:
                lines.append("用户对你的回答满意度较高，保持当前风格。")
            elif pos_rate < 0.4:
                lines.append("用户过去对你的回答不太满意，注意调整深度和风格。")

        if pref.preferred_detail_level != "medium":
            level_map = {"brief": "简洁", "detailed": "详细"}
            lines.append(f"用户偏好{level_map.get(pref.preferred_detail_level, '适中')}程度的回答。")

        difficulty_preference = pref.custom_signals.get("difficulty_preference")
        if difficulty_preference == "easier":
            lines.append("最近反馈显示用户更需要降低难度和术语密度。")
        elif difficulty_preference == "harder":
            lines.append("最近反馈显示用户可以接受更高挑战和更深入内容。")

        return "\n".join(lines)

    async def get_multi_agent_prompt_context(self, agent_ids: list[str], user_id: str) -> str:
        sections: list[str] = []
        for agent_id in [str(item).strip() for item in agent_ids if str(item).strip()][:3]:
            context = await self.get_prompt_context(agent_id, user_id)
            if context:
                sections.append(f"{agent_id}:\n{context}")
        return "\n\n".join(sections)
