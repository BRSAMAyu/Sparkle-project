from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from app.services.learning_feature_rollup_service import LearningFeatureRollupService
from app.services.task_motif_registry_service import TaskMotifRegistryService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CognitivePatternMiningService:
    """Mine structured cognitive rules from rollups for research track."""

    SUPPORTED_TASK_TYPES = {"study_plan", "error_diagnosis", "deep_analysis"}

    def __init__(self, redis_client=None):
        self.rollups = LearningFeatureRollupService(redis_client=redis_client)
        self.registry = TaskMotifRegistryService()
        self.redis = redis_client

    async def run_mining_job(self, *, days: int = 14) -> dict[str, Any]:
        rows = await self.rollups.list_rollups(days=days)
        candidates: list[dict[str, Any]] = []
        graphs: list[dict[str, Any]] = []

        for row in rows:
            task_type = str(row.get("task_type", ""))
            if task_type not in self.SUPPORTED_TASK_TYPES:
                continue
            support = int((row.get("counts") or {}).get("expert_selected", 0))
            if support < 20:
                continue

            motif_graph = self._build_motif_graph(row=row, days=days)
            graphs.append(motif_graph)

            candidates.extend(
                self._build_rule_candidates(
                    row=row,
                    motif_graph_id=str(motif_graph["graph_id"]),
                    days=days,
                )
            )

        created = 0
        for item in candidates:
            await self.registry.register_rule_candidate(
                rule=item,
                motif_graph=None,
                redis_client=self.redis,
            )
            created += 1

        for graph in graphs:
            await self.registry.upsert_graph(graph, redis_client=self.redis)

        return {
            "status": "ok",
            "window_days": days,
            "candidate_count": created,
            "motif_graph_count": len(graphs),
        }

    def _build_rule_candidates(self, *, row: dict[str, Any], motif_graph_id: str, days: int) -> list[dict[str, Any]]:
        counts = row.get("counts") if isinstance(row.get("counts"), dict) else {}
        task_type = str(row.get("task_type", ""))
        complexity_tier = str(row.get("complexity_tier", "unknown"))
        support_size = int(counts.get("expert_selected", 0))
        fallback_rate = float(row.get("fallback_rate", 0.0) or 0.0)
        q_score = float(row.get("q_score", 0.0) or 0.0)
        latency = float(row.get("normalized_latency", 0.0) or 0.0)
        repair_success = float(row.get("repair_success_rate", 0.0) or 0.0)
        quality_gate_blocks = int(counts.get("quality_gate_blocked", 0))
        feedback_up_rate = float(row.get("feedback_up_rate", 0.0) or 0.0)

        domain = self._infer_domain(task_type=task_type)
        evidence_window = f"last_{days}d"
        scope_type, scope_key = self._infer_scope(row=row)
        out: list[dict[str, Any]] = []

        # decomposition motif
        if quality_gate_blocks >= 5 or q_score < 0.62:
            out.append(
                self._make_rule(
                    domain=domain,
                    task_type=task_type,
                    complexity_tier=complexity_tier,
                    rule_type="decomposition",
                    motif_graph_id=motif_graph_id,
                    support_size=support_size,
                    confidence=self._confidence(support=support_size, quality=q_score),
                    expected_delta_q=max(0.02, min(0.15, 0.68 - q_score)),
                    fairness_risk=max(0.0, min(0.3, fallback_rate)),
                    latency_risk=max(0.0, min(0.3, latency)),
                    evidence_window=evidence_window,
                    trigger_conditions={
                        "quality_gate_blocked_min": 5,
                        "q_score_max": 0.62,
                    },
                    recommended_actions=[
                        "raise_contract_gate_weight",
                        "enforce_acceptance_criteria",
                        "prioritize_goal_traceability",
                    ],
                    channel="routing",
                    scope_type=scope_type,
                    scope_key=scope_key,
                )
            )

        # execution rhythm motif
        if latency > 0.55 or fallback_rate > 0.08:
            out.append(
                self._make_rule(
                    domain=domain,
                    task_type=task_type,
                    complexity_tier=complexity_tier,
                    rule_type="execution_rhythm",
                    motif_graph_id=motif_graph_id,
                    support_size=support_size,
                    confidence=self._confidence(support=support_size, quality=1.0 - latency),
                    expected_delta_q=max(0.015, min(0.12, latency - 0.45)),
                    fairness_risk=max(0.0, min(0.3, fallback_rate)),
                    latency_risk=max(0.0, min(0.5, latency)),
                    evidence_window=evidence_window,
                    trigger_conditions={
                        "normalized_latency_min": 0.55,
                        "fallback_rate_min": 0.08,
                    },
                    recommended_actions=[
                        "degrade_parallelism",
                        "tighten_dependency_order",
                    ],
                    channel="toolchain",
                    scope_type=scope_type,
                    scope_key=scope_key,
                )
            )

        # clarification motif
        if quality_gate_blocks >= 3:
            out.append(
                self._make_rule(
                    domain=domain,
                    task_type=task_type,
                    complexity_tier=complexity_tier,
                    rule_type="clarification",
                    motif_graph_id=motif_graph_id,
                    support_size=support_size,
                    confidence=self._confidence(support=support_size, quality=0.65),
                    expected_delta_q=max(0.01, min(0.1, quality_gate_blocks / 100.0)),
                    fairness_risk=max(0.0, min(0.25, 1.0 - feedback_up_rate)),
                    latency_risk=max(0.0, min(0.3, latency)),
                    evidence_window=evidence_window,
                    trigger_conditions={
                        "quality_gate_blocked_min": 3,
                    },
                    recommended_actions=[
                        "require_minimal_clarification",
                        "inject_clarification_points",
                    ],
                    channel="prompt",
                    scope_type=scope_type,
                    scope_key=scope_key,
                )
            )

        # repair motif
        repair_triggered = int(counts.get("plan_repair_triggered", 0))
        if repair_triggered >= 5 and repair_success < 0.65:
            out.append(
                self._make_rule(
                    domain=domain,
                    task_type=task_type,
                    complexity_tier=complexity_tier,
                    rule_type="repair",
                    motif_graph_id=motif_graph_id,
                    support_size=support_size,
                    confidence=self._confidence(support=support_size, quality=repair_success),
                    expected_delta_q=max(0.01, min(0.12, 0.7 - repair_success)),
                    fairness_risk=max(0.0, min(0.2, fallback_rate)),
                    latency_risk=max(0.0, min(0.3, latency)),
                    evidence_window=evidence_window,
                    trigger_conditions={
                        "plan_repair_triggered_min": 5,
                        "repair_success_rate_max": 0.65,
                    },
                    recommended_actions=[
                        "output_contract_hardening",
                        "timeout_rebudget",
                    ],
                    channel="toolchain",
                    scope_type=scope_type,
                    scope_key=scope_key,
                )
            )

        return out

    def _build_motif_graph(self, *, row: dict[str, Any], days: int) -> dict[str, Any]:
        task_type = str(row.get("task_type", ""))
        complexity = str(row.get("complexity_tier", "unknown"))
        strategy_pack = str(row.get("strategy_pack", "default"))
        seed = f"{task_type}|{complexity}|{strategy_pack}|{days}"
        graph_id = f"motif_{hashlib.sha1(seed.encode('utf-8')).hexdigest()[:10]}"
        failure_patterns = row.get("failure_pattern_topn") if isinstance(row.get("failure_pattern_topn"), list) else []

        nodes = [
            {"id": "goal", "type": "goal"},
            {"id": "constraints", "type": "constraint"},
            {"id": "milestones", "type": "milestone"},
            {"id": "acceptance", "type": "acceptance"},
            {"id": "risks", "type": "risk"},
            {"id": "repair", "type": "repair"},
        ]
        edges = [
            {"source": "goal", "target": "milestones", "relation": "decompose"},
            {"source": "constraints", "target": "milestones", "relation": "bound"},
            {"source": "milestones", "target": "acceptance", "relation": "verify"},
            {"source": "risks", "target": "repair", "relation": "mitigate"},
        ]
        for item in failure_patterns[:3]:
            if isinstance(item, dict):
                pattern = str(item.get("pattern", ""))
                if pattern:
                    edges.append({"source": "risks", "target": "repair", "relation": f"pattern::{pattern}"})

        coverage = min(1.0, max(0.0, float(row.get("q_score", 0.0) or 0.0) + 0.2))
        stability = min(1.0, max(0.0, 1.0 - float(row.get("fallback_rate", 0.0) or 0.0)))
        return {
            "graph_id": graph_id,
            "domain": self._infer_domain(task_type=task_type),
            "task_type": task_type,
            "complexity_tier": complexity,
            "nodes": nodes,
            "edges": edges,
            "coverage": round(coverage, 4),
            "stability_score": round(stability, 4),
            "evidence_window": f"last_{days}d",
            "version": "v1",
            "created_at": _utcnow().isoformat(),
        }

    @staticmethod
    def _make_rule(
        *,
        domain: str,
        task_type: str,
        complexity_tier: str,
        rule_type: str,
        motif_graph_id: str,
        support_size: int,
        confidence: float,
        expected_delta_q: float,
        fairness_risk: float,
        latency_risk: float,
        evidence_window: str,
        trigger_conditions: dict[str, Any],
        recommended_actions: list[str],
        channel: str,
        scope_type: str,
        scope_key: str,
    ) -> dict[str, Any]:
        raw_seed = f"{domain}|{task_type}|{complexity_tier}|{rule_type}|{channel}|{evidence_window}"
        rule_id = f"cr_{hashlib.sha1(raw_seed.encode('utf-8')).hexdigest()[:12]}"
        return {
            "rule_id": rule_id,
            "domain": domain,
            "task_type": task_type,
            "complexity_tier": complexity_tier,
            "rule_type": rule_type,
            "trigger_conditions": trigger_conditions,
            "recommended_actions": recommended_actions,
            "channel": channel,
            "scope_type": scope_type,
            "scope_key": scope_key,
            "expected_delta_q": round(expected_delta_q, 4),
            "support_size": max(0, int(support_size)),
            "confidence": round(max(0.0, min(confidence, 1.0)), 4),
            "fairness_risk": round(max(0.0, min(fairness_risk, 1.0)), 4),
            "latency_risk": round(max(0.0, min(latency_risk, 1.0)), 4),
            "evidence_window": evidence_window,
            "status": "draft",
            "motif_graph_id": motif_graph_id,
            "version": "v1",
            "created_at": _utcnow().isoformat(),
        }

    @staticmethod
    def _infer_domain(*, task_type: str) -> str:
        if task_type in {"study_plan", "error_diagnosis", "deep_analysis"}:
            return "education"
        return "general"

    @staticmethod
    def _confidence(*, support: int, quality: float) -> float:
        support_norm = min(1.0, max(0.0, support / 200.0))
        quality_norm = min(1.0, max(0.0, quality))
        return 0.55 * support_norm + 0.45 * quality_norm

    @staticmethod
    def _infer_scope(*, row: dict[str, Any]) -> tuple[str, str]:
        user_scope = str(row.get("user_scope", "") or "")
        cohort_id = str(row.get("cohort_id", "") or "")
        if user_scope and user_scope != "usr::anon":
            return "personal", user_scope
        if cohort_id:
            return "cohort", cohort_id
        return "global", "all"
