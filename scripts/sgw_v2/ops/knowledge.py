"""Knowledge retrieval across SGW runs.

Provides cross-run analysis to identify:
- Persistent failure patterns (recurrent across runs)
- Config changes that improved/regressed metrics
- Persona types that consistently fail
- Seasonal/time-based patterns
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..storage.db import RunDB


class KnowledgeRetriever:
    """Cross-run knowledge retrieval for SGW observability."""

    def __init__(self, run_db: RunDB):
        self.run_db = run_db

    def find_persistent_failures(self, min_runs: int = 3) -> list[dict[str, Any]]:
        """Find persona types that consistently produce failures across runs."""
        rows = self.run_db.conn.execute(
            """SELECT s.seed_persona_id, COUNT(DISTINCT s.run_id) as run_count,
                      COUNT(*) as total_sessions,
                      SUM(CASE WHEN a.is_violation = 1 THEN 1 ELSE 0 END) as violations
               FROM sessions s
               LEFT JOIN audits a ON a.session_id = s.session_id AND a.audit_type = 'compliance'
               WHERE s.seed_persona_id IS NOT NULL AND s.status = 'completed'
               GROUP BY s.seed_persona_id
               HAVING COUNT(DISTINCT s.run_id) >= ?
               ORDER BY violations DESC""",
            (min_runs,),
        ).fetchall()

        results = []
        for row in rows:
            persona_id, run_count, total_sessions, violations = row
            violation_rate = violations / max(total_sessions, 1)
            results.append({
                "persona_id": persona_id,
                "runs_seen": run_count,
                "total_sessions": total_sessions,
                "violations": violations or 0,
                "violation_rate": round(violation_rate, 4),
            })

        return results

    def find_effective_changes(self) -> list[dict[str, Any]]:
        """Find config changes that improved metrics across runs.

        Compares consecutive runs and identifies config_hash changes
        that correlated with metric improvements.
        """
        rows = self.run_db.conn.execute(
            """SELECT r1.run_id, r1.config_hash, r1.started_at,
                      r2.run_id as next_run_id, r2.config_hash as next_config_hash
               FROM runs r1
               JOIN runs r2 ON r2.started_at > r1.started_at
               WHERE r1.status = 'completed' AND r2.status = 'completed'
               ORDER BY r1.started_at DESC
               LIMIT 10"""
        ).fetchall()

        results = []
        for row in rows:
            run_a_id, config_a, started_a, run_b_id, config_b = row[:5]
            summary_a = self.run_db.run_summary(run_a_id)
            summary_b = self.run_db.run_summary(run_b_id)

            if not summary_a or not summary_b:
                continue

            delta_soft = summary_a.get("soft_violation_rate", 0) - summary_b.get("soft_violation_rate", 0)
            delta_auth = summary_b.get("authenticity_mean", 0) - summary_a.get("authenticity_mean", 0)

            if delta_soft > 0.02 or delta_auth > 0.03:
                results.append({
                    "before_run": run_a_id[:12],
                    "after_run": run_b_id[:12],
                    "config_before": config_a,
                    "config_after": config_b,
                    "soft_violation_delta": round(delta_soft, 4),
                    "authenticity_delta": round(delta_auth, 4),
                    "improved": delta_soft > 0 or delta_auth > 0,
                })

        return results

    def get_persona_behavior_profile(self, persona_id: str) -> dict[str, Any]:
        """Get aggregated behavior profile for a specific persona."""
        # AI behavior distribution for this persona
        behavior_rows = self.run_db.conn.execute(
            """SELECT t.ai_behavior_class, COUNT(*) FROM turns t
               JOIN sessions s ON s.session_id = t.session_id
               WHERE s.seed_persona_id = ? AND t.ai_behavior_class IS NOT NULL
               GROUP BY t.ai_behavior_class""",
            (persona_id,),
        ).fetchall()

        # Audit results for this persona
        audit_rows = self.run_db.conn.execute(
            """SELECT a.audit_type, AVG(a.overall), COUNT(*),
                      SUM(CASE WHEN a.is_violation = 1 THEN 1 ELSE 0 END)
               FROM audits a
               JOIN sessions s ON s.session_id = a.session_id
               WHERE s.seed_persona_id = ?
               GROUP BY a.audit_type""",
            (persona_id,),
        ).fetchall()

        behavior_dist = {row[0]: row[1] for row in behavior_rows}
        audit_profile = {}
        for row in audit_rows:
            audit_type, mean_score, total, violations = row
            audit_profile[audit_type] = {
                "mean_score": round(mean_score or 0, 4),
                "total": total,
                "violations": violations or 0,
                "violation_rate": round((violations or 0) / max(total, 1), 4),
            }

        return {
            "persona_id": persona_id,
            "behavior_distribution": behavior_dist,
            "audit_profile": audit_profile,
        }

    def get_run_health_score(self, run_id: str) -> float:
        """Compute a composite health score for a run (0.0 to 1.0)."""
        summary = self.run_db.run_summary(run_id)
        if not summary:
            return 0.0

        # Component scores
        soft_score = 1.0 - min(summary.get("soft_violation_rate", 0) * 5, 1.0)
        auth_score = min(summary.get("authenticity_mean", 0), 1.0)
        completion_score = min(
            summary.get("sessions_completed", 0) / max(summary.get("sessions_total", 1), 1),
            1.0,
        )
        hard_penalty = 0.0 if summary.get("hard_violations", 0) == 0 else 0.3

        # Weighted composite
        health = (soft_score * 0.35 + auth_score * 0.35 + completion_score * 0.30) - hard_penalty
        return round(max(0.0, min(1.0, health)), 4)
