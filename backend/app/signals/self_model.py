"""
Core: execution
Phase: reflect→adapt
Stage: Signal-to-Action Spine P1-5 SparkleSelfModel

Sparkle 自我模型 — 系统建模自己的策略效果。

核心原则：
- 系统不只建模用户，也要建模自己
- 每次策略调整都记录假设和结果
- 结果回流更新自我认知
- 不直接写长期人格，只写策略效果

对象：SelfModelClaim — 关于策略效果的假设。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from app.signals.types import _uid


@dataclass
class SelfModelClaim:
    """Sparkle 关于自身策略的一个判断。"""
    claim_id: str
    claim: str                          # 判断内容
    confidence: float                   # 置信度
    scope: str                          # "current_sprint" | "strategy" | "user_pair"
    evidence: list[str]                 # 支持证据
    counter_evidence: list[str]         # 反证
    policy_effects: list[str]           # 影响了哪些策略
    outcome: str | None = None          # "effective" | "insufficient" | "backfired" | None
    retract_conditions: list[str] = field(default_factory=list)  # 收回条件
    created_at: str = field(default_factory=lambda: "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "claim": self.claim,
            "confidence": self.confidence,
            "scope": self.scope,
            "evidence": self.evidence,
            "counter_evidence": self.counter_evidence,
            "policy_effects": self.policy_effects,
            "outcome": self.outcome,
            "retract_conditions": self.retract_conditions,
        }


@dataclass
class StrategyOutcome:
    """策略执行结果记录。"""
    outcome_id: str
    directive_id: str                   # 关联的 directive
    claim_id: str                       # 关联的 self-model claim
    expected_outcome: str               # 预期效果
    actual_outcome: dict[str, Any]      # 实际结果
    attribution: dict[str, Any]         # 归因
    next_policy_suggestion: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "directive_id": self.directive_id,
            "claim_id": self.claim_id,
            "expected_outcome": self.expected_outcome,
            "actual_outcome": self.actual_outcome,
            "attribution": self.attribution,
            "next_policy_suggestion": self.next_policy_suggestion,
        }


# Redis key patterns
_CLAIM_KEY = "spine:self_model:claim:{user_id}:{claim_id}"
_USER_CLAIMS_KEY = "spine:self_model:claims:{user_id}"
_OUTCOME_KEY = "spine:self_model:outcome:{user_id}:{outcome_id}"
_MAX_CLAIMS = 50
_CLAIM_TTL = 30 * 24 * 3600  # 30 days


class SparkleSelfModelService:
    """
    P1-5: Sparkle 自我模型服务。

    职责：
    1. 记录策略假设（每次 directive 生成时）
    2. 记录策略结果（outcome 回流时）
    3. 更新自我模型置信度
    4. 判断是否需要收回策略
    """

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    async def record_claim(
        self,
        *,
        user_id: str,
        claim: str,
        confidence: float,
        scope: str,
        evidence: list[str] | None = None,
        counter_evidence: list[str] | None = None,
        policy_effects: list[str] | None = None,
        retract_conditions: list[str] | None = None,
    ) -> SelfModelClaim:
        """记录一个新的自我模型判断。"""
        from datetime import UTC, datetime
        claim_obj = SelfModelClaim(
            claim_id=_uid("smc"),
            claim=claim,
            confidence=confidence,
            scope=scope,
            evidence=evidence or [],
            counter_evidence=counter_evidence or [],
            policy_effects=policy_effects or [],
            retract_conditions=retract_conditions or [],
            created_at=datetime.now(UTC).isoformat(),
        )

        # 存储到 Redis
        key = _CLAIM_KEY.format(user_id=user_id, claim_id=claim_obj.claim_id)
        await self.redis.set(key, json.dumps(claim_obj.to_dict()), ex=_CLAIM_TTL)

        # 添加到用户 claims 列表
        claims_key = _USER_CLAIMS_KEY.format(user_id=user_id)
        await self.redis.lpush(claims_key, claim_obj.claim_id)
        await self.redis.ltrim(claims_key, 0, _MAX_CLAIMS - 1)

        logger.info(
            "SelfModel claim: user={} claim_id={} scope={} conf={:.2f}",
            user_id, claim_obj.claim_id, scope, confidence,
        )

        return claim_obj

    async def record_outcome(
        self,
        *,
        user_id: str,
        directive_id: str,
        claim_id: str,
        expected_outcome: str,
        actual_outcome: dict[str, Any],
    ) -> StrategyOutcome:
        """记录策略执行结果，并更新关联的 self-model claim。"""
        # 归因分析
        attribution = self._attribute(
            expected=expected_outcome,
            actual=actual_outcome,
        )

        # 生成下一步建议
        next_suggestion = self._suggest_next(attribution)

        outcome = StrategyOutcome(
            outcome_id=_uid("smo"),
            directive_id=directive_id,
            claim_id=claim_id,
            expected_outcome=expected_outcome,
            actual_outcome=actual_outcome,
            attribution=attribution,
            next_policy_suggestion=next_suggestion,
        )

        # 存储结果
        key = _OUTCOME_KEY.format(user_id=user_id, outcome_id=outcome.outcome_id)
        await self.redis.set(key, json.dumps(outcome.to_dict()), ex=_CLAIM_TTL)

        # 更新关联 claim 的 outcome 和置信度
        await self._update_claim_outcome(user_id, claim_id, attribution)

        logger.info(
            "SelfModel outcome: user={} claim={} effect={} suggestion={}",
            user_id, claim_id, attribution.get("effect"), next_suggestion,
        )

        return outcome

    async def get_active_claims(
        self,
        user_id: str,
        limit: int = 10,
    ) -> list[SelfModelClaim]:
        """获取用户当前的活跃自我模型判断。"""
        claims_key = _USER_CLAIMS_KEY.format(user_id=user_id)
        claim_ids = await self.redis.lrange(claims_key, 0, limit - 1)

        claims = []
        for cid in claim_ids:
            key = _CLAIM_KEY.format(user_id=user_id, claim_id=cid)
            raw = await self.redis.get(key)
            if raw:
                d = json.loads(raw)
                claims.append(SelfModelClaim(
                    claim_id=d["claim_id"],
                    claim=d["claim"],
                    confidence=d["confidence"],
                    scope=d["scope"],
                    evidence=d.get("evidence", []),
                    counter_evidence=d.get("counter_evidence", []),
                    policy_effects=d.get("policy_effects", []),
                    outcome=d.get("outcome"),
                    retract_conditions=d.get("retract_conditions", []),
                ))
        return claims

    async def record_user_correction(
        self,
        *,
        user_id: str,
        signal_id: str,
        reason: str,
        source: str = "user_correction",
    ) -> SelfModelClaim:
        """用户纠正了系统判断 → 记录到自我模型。"""
        return await self.record_claim(
            user_id=user_id,
            claim=f"用户纠正了系统判断: {reason}",
            confidence=0.90,  # 用户纠正置信度最高
            scope="current_sprint",
            evidence=[f"source={source}", f"signal={signal_id}"],
            policy_effects=["retract_related_directive"],
        )

    def _attribute(
        self,
        expected: str,
        actual: dict[str, Any],
    ) -> dict[str, Any]:
        """归因分析 — 策略是否有效。"""
        completed = actual.get("completed", False)
        feedback = actual.get("user_feedback", "")

        if completed and feedback in ("", "positive"):
            effect = "effective"
            new_confidence = 0.15  # 增量
        elif completed and feedback == "negative":
            effect = "completed_but_resented"
            new_confidence = -0.10
        elif not completed and "不会做" in feedback or "看不懂" in feedback:
            effect = "insufficient"
            new_confidence = -0.20
        else:
            effect = "inconclusive"
            new_confidence = 0.0

        hypothesis = None
        if effect == "insufficient":
            hypothesis = "problem_may_not_be_duration_but_understanding"
        elif effect == "completed_but_resented":
            hypothesis = "strategy_correct_but_tone_wrong"

        return {
            "effect": effect,
            "confidence_delta": new_confidence,
            "new_hypothesis": hypothesis,
        }

    def _suggest_next(self, attribution: dict[str, Any]) -> str | None:
        """基于归因生成下一步建议。"""
        effect = attribution.get("effect")
        hypothesis = attribution.get("new_hypothesis")

        if effect == "insufficient" and hypothesis:
            return f"switch_strategy:{hypothesis}"
        if effect == "completed_but_resented":
            return "adjust_tone"
        if effect == "effective":
            return "maintain_current_strategy"
        return None

    async def _update_claim_outcome(
        self,
        user_id: str,
        claim_id: str,
        attribution: dict[str, Any],
    ) -> None:
        """更新关联 claim 的 outcome。"""
        key = _CLAIM_KEY.format(user_id=user_id, claim_id=claim_id)
        raw = await self.redis.get(key)
        if not raw:
            return

        d = json.loads(raw)
        d["outcome"] = attribution.get("effect")
        # 调整置信度
        delta = attribution.get("confidence_delta", 0)
        d["confidence"] = max(0.0, min(1.0, d.get("confidence", 0.5) + delta))

        # 检查是否需要添加反证
        if delta < 0:
            d.setdefault("counter_evidence", []).append(
                f"outcome={attribution.get('effect')}"
            )

        await self.redis.set(key, json.dumps(d), ex=_CLAIM_TTL)
