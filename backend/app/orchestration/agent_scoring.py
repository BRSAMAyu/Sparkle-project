from __future__ import annotations

import json
import random
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, UTC
from typing import Any

from loguru import logger

from app.orchestration.agent_memory import AgentMemoryService, extract_topics


def _utcnow_iso() -> str:
    return datetime.now(UTC).replace(tzinfo=None).isoformat()


@dataclass
class AgentPerformanceRecord:
    agent_id: str
    user_id: str
    session_id: str
    latency_ms: float
    success: bool
    tool_calls_count: int
    result_used: bool | None = None
    user_feedback: str | None = None
    response_id: str | None = None
    intent_type: str | None = None
    timestamp: str = field(default_factory=_utcnow_iso)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["latency_ms"] = round(float(self.latency_ms), 2)
        return payload


@dataclass
class AgentQualityScore:
    agent_id: str
    quality_score: float
    success_rate: float
    feedback_score: float
    usage_rate: float
    speed_score: float
    sample_size: int
    recent_summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "quality_score": round(self.quality_score, 4),
            "success_rate": round(self.success_rate, 4),
            "feedback_score": round(self.feedback_score, 4),
            "usage_rate": round(self.usage_rate, 4),
            "speed_score": round(self.speed_score, 4),
            "sample_size": self.sample_size,
            "recent_summary": self.recent_summary,
        }


class AgentScoringService:
    PERF_LIMIT = 100
    RESPONSE_HISTORY_LIMIT = 200
    RESPONSE_MAP_TTL_SECONDS = 86400 * 30

    def __init__(self, redis_client):
        self.redis = redis_client

    @staticmethod
    def _perf_key(agent_id: str, user_id: str) -> str:
        return f"agent_perf:{agent_id}:{user_id}"

    @staticmethod
    def _response_map_key(response_id: str) -> str:
        return f"agent_response_map:{response_id}"

    @staticmethod
    def _response_history_key(user_id: str) -> str:
        return f"agent_response_history:{user_id}"

    async def record_performance(self, record: AgentPerformanceRecord) -> None:
        if not self.redis:
            return
        try:
            key = self._perf_key(record.agent_id, record.user_id)
            score = datetime.fromisoformat(record.timestamp).timestamp()
            await self.redis.zadd(
                key,
                {json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True): score},
            )
            overflow = await self.redis.zcard(key) - self.PERF_LIMIT
            if overflow > 0:
                await self.redis.zremrangebyrank(key, 0, overflow - 1)
        except Exception as exc:
            logger.debug(f"Failed to record agent performance: {exc}")

    async def record_from_runtime(
        self,
        *,
        redis_client,
        state: dict[str, Any],
        agent_id: str,
        latency_ms: float,
        success: bool,
        tool_calls_count: int,
        result_used: bool | None,
        intent_type: str | None,
    ) -> None:
        if not redis_client:
            return
        user_id = str(state.get("user_id") or "").strip()
        session_id = str(state.get("session_id") or "").strip()
        if not user_id or not session_id:
            return
        await AgentScoringService(redis_client).record_performance(
            AgentPerformanceRecord(
                agent_id=agent_id,
                user_id=user_id,
                session_id=session_id,
                latency_ms=latency_ms,
                success=success,
                tool_calls_count=tool_calls_count,
                result_used=result_used,
                intent_type=intent_type,
            )
        )
        if success:
            try:
                user_message = ""
                collaboration_context = str(state.get("collaboration_context") or "").strip()
                if collaboration_context:
                    user_message = collaboration_context
                else:
                    for message in reversed(list(state.get("messages") or [])):
                        content = getattr(message, "content", None)
                        if content:
                            user_message = str(content)
                            break
                topics = extract_topics(user_message)
                await AgentMemoryService(redis_client).record_interaction(
                    agent_id=agent_id,
                    user_id=user_id,
                    topics=topics,
                )
            except Exception as exc:
                logger.debug(f"Failed to record agent memory interaction: {exc}")

    async def bind_response_to_recent_records(
        self,
        *,
        user_id: str,
        session_id: str,
        response_id: str,
        agents: list[str],
        intent_type: str | None = None,
    ) -> None:
        if not self.redis or not response_id:
            return
        for agent_id in agents:
            records = await self._load_records(agent_id, user_id)
            updated = False
            for record in reversed(records):
                if record.response_id:
                    continue
                if record.session_id != session_id:
                    continue
                record.response_id = response_id
                record.result_used = True
                if intent_type and not record.intent_type:
                    record.intent_type = intent_type
                await self._rewrite_records(agent_id, user_id, records)
                updated = True
                break
            if not updated:
                continue

    async def store_response_agent_mapping(
        self,
        *,
        response_id: str,
        user_id: str,
        session_id: str,
        agents: list[str],
        intent_type: str | None,
        workflow_id: str | None,
    ) -> None:
        if not self.redis or not response_id or not user_id:
            return
        payload = {
            "response_id": response_id,
            "user_id": user_id,
            "session_id": session_id,
            "agents": agents,
            "intent_type": intent_type or "unknown",
            "workflow_id": workflow_id or "",
            "feedback": None,
            "timestamp": _utcnow_iso(),
        }
        member = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        score = time.time()
        try:
            await self.redis.set(
                self._response_map_key(response_id),
                member,
                ex=self.RESPONSE_MAP_TTL_SECONDS,
            )
            history_key = self._response_history_key(user_id)
            await self.redis.zadd(history_key, {member: score})
            overflow = await self.redis.zcard(history_key) - self.RESPONSE_HISTORY_LIMIT
            if overflow > 0:
                await self.redis.zremrangebyrank(history_key, 0, overflow - 1)
        except Exception as exc:
            logger.debug(f"Failed to store response-agent mapping: {exc}")

    async def apply_response_feedback(
        self,
        *,
        user_id: str,
        response_id: str,
        feedback_type: str,
    ) -> list[str]:
        if not self.redis:
            return []
        mapping = await self.get_response_agent_mapping(response_id)
        if not mapping:
            return []
        if str(mapping.get("user_id") or "") != str(user_id):
            return []
        agents = [str(agent).strip() for agent in (mapping.get("agents") or []) if str(agent).strip()]
        if not agents:
            return []
        normalized_feedback = "up" if feedback_type.lower() == "up" else "down"
        for agent_id in agents:
            records = await self._load_records(agent_id, user_id)
            touched = False
            for record in records:
                if record.response_id == response_id:
                    record.user_feedback = normalized_feedback
                    touched = True
            if touched:
                await self._rewrite_records(agent_id, user_id, records)
        await self._update_response_history_feedback(response_id=response_id, user_id=user_id, feedback=normalized_feedback)
        return agents

    async def get_response_agent_mapping(self, response_id: str) -> dict[str, Any] | None:
        if not self.redis or not response_id:
            return None
        try:
            raw = await self.redis.get(self._response_map_key(response_id))
            if not raw:
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.debug(f"Failed to load response-agent mapping: {exc}")
            return None

    async def get_quality_scores(
        self,
        *,
        user_id: str,
        agent_ids: list[str],
    ) -> dict[str, AgentQualityScore]:
        snapshots: dict[str, list[AgentPerformanceRecord]] = {}
        for agent_id in agent_ids:
            snapshots[agent_id] = await self._load_records(agent_id, user_id)

        avg_latencies = {
            agent_id: (
                sum(record.latency_ms for record in records) / len(records)
                if records
                else None
            )
            for agent_id, records in snapshots.items()
        }
        comparable = [
            (agent_id, latency)
            for agent_id, latency in avg_latencies.items()
            if latency is not None
        ]
        comparable.sort(key=lambda item: item[1])

        speed_scores: dict[str, float] = dict.fromkeys(agent_ids, 0.5)
        total = len(comparable)
        if total > 1:
            for rank, (agent_id, _) in enumerate(comparable):
                speed_scores[agent_id] = max(0.0, min(1.0, 1 - (rank / (total - 1))))
        elif total == 1:
            speed_scores[comparable[0][0]] = 1.0

        scores: dict[str, AgentQualityScore] = {}
        for agent_id in agent_ids:
            records = snapshots.get(agent_id, [])
            if not records:
                scores[agent_id] = AgentQualityScore(
                    agent_id=agent_id,
                    quality_score=0.5,
                    success_rate=0.5,
                    feedback_score=0.5,
                    usage_rate=0.5,
                    speed_score=speed_scores.get(agent_id, 0.5),
                    sample_size=0,
                    recent_summary="暂无历史表现，按中性质量处理。",
                )
                continue

            success_rate = sum(1 for item in records if item.success) / len(records)
            feedback_values = []
            for item in records:
                if item.user_feedback == "up":
                    feedback_values.append(1.0)
                elif item.user_feedback == "down":
                    feedback_values.append(0.0)
            feedback_score = (
                sum(feedback_values) / len(feedback_values)
                if feedback_values
                else 0.5
            )
            usage_values = [
                1.0 if item.result_used else 0.0
                for item in records
                if item.result_used is not None
            ]
            usage_rate = (
                sum(usage_values) / len(usage_values)
                if usage_values
                else 0.5
            )
            speed_score = speed_scores.get(agent_id, 0.5)
            quality_score = (
                0.4 * success_rate
                + 0.3 * feedback_score
                + 0.2 * usage_rate
                + 0.1 * speed_score
            )
            scores[agent_id] = AgentQualityScore(
                agent_id=agent_id,
                quality_score=quality_score,
                success_rate=success_rate,
                feedback_score=feedback_score,
                usage_rate=usage_rate,
                speed_score=speed_score,
                sample_size=len(records),
                recent_summary=(
                    f"成功率 {success_rate:.0%}，反馈分 {feedback_score:.2f}，"
                    f"贡献率 {usage_rate:.0%}，速度分 {speed_score:.2f}"
                ),
            )
        return scores

    async def get_quality_prompt_lines(
        self,
        *,
        user_id: str,
        agent_ids: list[str],
    ) -> list[str]:
        scores = await self.get_quality_scores(user_id=user_id, agent_ids=agent_ids)
        lines = []
        for agent_id in agent_ids:
            snapshot = scores.get(agent_id)
            if not snapshot:
                continue
            lines.append(
                f"- {agent_id}: quality={snapshot.quality_score:.2f}, "
                f"success_rate={snapshot.success_rate:.0%}, "
                f"feedback={snapshot.feedback_score:.2f}, "
                f"usage={snapshot.usage_rate:.0%}, "
                f"speed={snapshot.speed_score:.2f}, "
                f"samples={snapshot.sample_size}"
            )
        return lines

    async def rank_agents(
        self,
        *,
        user_id: str,
        agent_ids: list[str],
    ) -> list[str]:
        scores = await self.get_quality_scores(user_id=user_id, agent_ids=agent_ids)
        return sorted(
            agent_ids,
            key=lambda agent_id: (
                -(scores.get(agent_id).quality_score if scores.get(agent_id) else 0.5),
                agent_id,
            ),
        )

    async def analyze_best_combinations(
        self,
        *,
        user_id: str,
        intent_type: str,
        min_samples: int = 5,
    ) -> list[dict[str, Any]]:
        if not self.redis:
            return []
        try:
            raw_items = await self.redis.zrange(self._response_history_key(user_id), 0, -1)
        except Exception as exc:
            logger.debug(f"Failed to load response history: {exc}")
            return []

        grouped: dict[tuple[str, ...], list[dict[str, Any]]] = {}
        for raw in raw_items:
            try:
                payload = json.loads(raw)
            except Exception:
                continue
            if str(payload.get("intent_type") or "unknown") != str(intent_type):
                continue
            agents = tuple(sorted(str(agent) for agent in (payload.get("agents") or []) if str(agent).strip()))
            if len(agents) < 2:
                continue
            grouped.setdefault(agents, []).append(payload)

        results = []
        for agents, items in grouped.items():
            if len(items) < min_samples:
                continue
            feedback_values = []
            for item in items:
                if item.get("feedback") == "up":
                    feedback_values.append(1.0)
                elif item.get("feedback") == "down":
                    feedback_values.append(0.0)
            if not feedback_values:
                continue
            avg_feedback = sum(feedback_values) / len(feedback_values)
            results.append(
                {
                    "agents": list(agents),
                    "sample_size": len(items),
                    "feedback_score": round(avg_feedback, 4),
                }
            )
        return sorted(results, key=lambda item: (-item["feedback_score"], -item["sample_size"]))

    async def maybe_apply_exploration(
        self,
        *,
        user_id: str,
        intent_type: str,
        current_agents: list[str],
        exploration_rate: float,
        available_agents: list[str] | None = None,
    ) -> list[str]:
        if random.random() >= exploration_rate:
            return current_agents
        candidates = await self.analyze_best_combinations(
            user_id=user_id,
            intent_type=intent_type,
            min_samples=1,
        )
        for candidate in candidates:
            agents = [str(agent).strip() for agent in candidate.get("agents", []) if str(agent).strip()]
            if agents and agents != current_agents:
                return agents
        available = [str(agent).strip() for agent in (available_agents or []) if str(agent).strip()]
        if available and current_agents:
            alternative = next((agent for agent in available if agent not in current_agents), None)
            if alternative:
                exploratory = list(current_agents)
                exploratory[-1] = alternative
                if exploratory != current_agents:
                    return exploratory
        return current_agents

    async def _update_response_history_feedback(
        self,
        *,
        response_id: str,
        user_id: str,
        feedback: str,
    ) -> None:
        if not self.redis:
            return
        key = self._response_history_key(user_id)
        raw_items = await self.redis.zrange(key, 0, -1, withscores=True)
        replacement = None
        old_member = None
        old_score = None
        for raw, score in raw_items:
            try:
                payload = json.loads(raw)
            except Exception:
                continue
            if payload.get("response_id") != response_id:
                continue
            payload["feedback"] = feedback
            replacement = json.dumps(payload, ensure_ascii=False, sort_keys=True)
            old_member = raw
            old_score = score
            break
        if replacement is None or old_member is None or old_score is None:
            mapping = await self.get_response_agent_mapping(response_id)
            if mapping:
                mapping["feedback"] = feedback
                await self.redis.set(
                    self._response_map_key(response_id),
                    json.dumps(mapping, ensure_ascii=False, sort_keys=True),
                    ex=self.RESPONSE_MAP_TTL_SECONDS,
                )
            return
        await self.redis.zrem(key, old_member)
        await self.redis.zadd(key, {replacement: old_score})
        mapping = await self.get_response_agent_mapping(response_id)
        if mapping:
            mapping["feedback"] = feedback
            await self.redis.set(
                self._response_map_key(response_id),
                json.dumps(mapping, ensure_ascii=False, sort_keys=True),
                ex=self.RESPONSE_MAP_TTL_SECONDS,
            )

    async def _load_records(
        self,
        agent_id: str,
        user_id: str,
    ) -> list[AgentPerformanceRecord]:
        if not self.redis:
            return []
        try:
            raw_items = await self.redis.zrange(self._perf_key(agent_id, user_id), 0, -1)
        except Exception as exc:
            logger.debug(f"Failed to load agent performance records: {exc}")
            return []
        records = []
        for raw in raw_items:
            try:
                payload = json.loads(raw)
                records.append(AgentPerformanceRecord(**payload))
            except Exception:
                continue
        return records

    async def _rewrite_records(
        self,
        agent_id: str,
        user_id: str,
        records: list[AgentPerformanceRecord],
    ) -> None:
        if not self.redis:
            return
        key = self._perf_key(agent_id, user_id)
        try:
            await self.redis.delete(key)
            mapping = {}
            for record in records[-self.PERF_LIMIT:]:
                score = datetime.fromisoformat(record.timestamp).timestamp()
                mapping[json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True)] = score
            if mapping:
                await self.redis.zadd(key, mapping)
        except Exception as exc:
            logger.debug(f"Failed to rewrite performance records: {exc}")
