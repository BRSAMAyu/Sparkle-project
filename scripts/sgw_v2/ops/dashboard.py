"""Dashboard data export for SGW observability.

Generates JSON snapshots and markdown reports from SQLite run data
for dashboard consumption and long-term trend analysis.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..storage.db import RunDB


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


class DashboardExporter:
    """Export run data for dashboard visualization."""

    def __init__(self, run_db: RunDB):
        self.run_db = run_db

    def export_run_detail(self, run_id: str) -> dict[str, Any]:
        """Export comprehensive run detail as JSON-serializable dict."""
        run = self.run_db.get_run(run_id)
        if not run:
            return {}

        summary = self.run_db.run_summary(run_id)

        # Session distribution by role
        role_rows = self.run_db.conn.execute(
            "SELECT role, COUNT(*), SUM(turns_completed) FROM sessions WHERE run_id = ? GROUP BY role",
            (run_id,),
        ).fetchall()
        role_distribution = {row[0]: {"count": row[1], "total_turns": row[2] or 0} for row in role_rows}

        # Persona coverage
        persona_rows = self.run_db.conn.execute(
            "SELECT seed_persona_id, COUNT(*) FROM sessions WHERE run_id = ? AND seed_persona_id IS NOT NULL GROUP BY seed_persona_id",
            (run_id,),
        ).fetchall()
        persona_coverage = {row[0]: row[1] for row in persona_rows}

        # Audit scores distribution
        compliance_rows = self.run_db.conn.execute(
            "SELECT overall, is_violation FROM audits WHERE run_id = ? AND audit_type = 'compliance'",
            (run_id,),
        ).fetchall()
        compliance_scores = [row[0] for row in compliance_rows if row[0] is not None]
        compliance_violation_count = sum(1 for row in compliance_rows if row[1] == 1)

        authenticity_rows = self.run_db.conn.execute(
            "SELECT overall, is_violation FROM audits WHERE run_id = ? AND audit_type = 'authenticity'",
            (run_id,),
        ).fetchall()
        authenticity_scores = [row[0] for row in authenticity_rows if row[0] is not None]
        authenticity_failure_count = sum(1 for row in authenticity_rows if row[1] == 1)

        # AI behavior distribution
        behavior_rows = self.run_db.conn.execute(
            "SELECT ai_behavior_class, COUNT(*) FROM turns WHERE run_id = ? AND ai_behavior_class IS NOT NULL GROUP BY ai_behavior_class",
            (run_id,),
        ).fetchall()
        behavior_distribution = {row[0]: row[1] for row in behavior_rows}

        return {
            "run_id": run_id,
            "started_at": run.get("started_at"),
            "ended_at": run.get("ended_at"),
            "status": run.get("status"),
            "config_hash": run.get("config_hash"),
            "git_sha": run.get("git_sha"),
            "summary": summary,
            "role_distribution": role_distribution,
            "persona_coverage": persona_coverage,
            "compliance": {
                "total": len(compliance_scores),
                "violations": compliance_violation_count,
                "violation_rate": round(compliance_violation_count / max(len(compliance_scores), 1), 4),
                "mean_score": round(sum(compliance_scores) / max(len(compliance_scores), 1), 4),
                "min_score": round(min(compliance_scores), 4) if compliance_scores else None,
            },
            "authenticity": {
                "total": len(authenticity_scores),
                "failures": authenticity_failure_count,
                "failure_rate": round(authenticity_failure_count / max(len(authenticity_scores), 1), 4),
                "mean_score": round(sum(authenticity_scores) / max(len(authenticity_scores), 1), 4),
                "min_score": round(min(authenticity_scores), 4) if authenticity_scores else None,
            },
            "behavior_distribution": behavior_distribution,
        }

    def export_trends(self, limit: int = 20) -> dict[str, Any]:
        """Export trend data across recent runs."""
        rows = self.run_db.conn.execute(
            "SELECT run_id, started_at, ended_at, status, config_hash FROM runs ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()

        runs = []
        for row in rows:
            run_id = row[0]
            summary = self.run_db.run_summary(run_id)
            runs.append({
                "run_id": run_id,
                "started_at": row[1],
                "ended_at": row[2],
                "status": row[3],
                "config_hash": row[4],
                **summary,
            })

        return {
            "generated_at": _utcnow_iso(),
            "run_count": len(runs),
            "runs": runs,
        }

    def export_to_json(self, run_id: str | None, output_path: Path) -> None:
        """Export data to JSON file."""
        if run_id:
            data = self.export_run_detail(run_id)
        else:
            data = self.export_trends()

        output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def generate_markdown_report(self, run_id: str) -> str:
        """Generate a markdown report for a specific run."""
        detail = self.export_run_detail(run_id)
        if not detail:
            return f"Run {run_id} not found."

        lines = [
            f"# SGW Run Report: {run_id[:12]}",
            "",
            f"- Status: `{detail['status']}`",
            f"- Started: `{detail['started_at']}`",
            f"- Ended: `{detail['ended_at'] or 'N/A'}`",
            f"- Config Hash: `{detail['config_hash']}`",
            f"- Git SHA: `{detail['git_sha']}`",
            "",
            "## Summary",
            "",
        ]

        summary = detail.get("summary", {})
        for key, value in summary.items():
            if isinstance(value, float):
                lines.append(f"- {key}: `{value:.4f}`")
            else:
                lines.append(f"- {key}: `{value}`")

        # Compliance section
        comp = detail.get("compliance", {})
        if comp.get("total", 0) > 0:
            lines.extend([
                "",
                "## Compliance Audit",
                "",
                f"- Total Audits: `{comp['total']}`",
                f"- Violations: `{comp['violations']}`",
                f"- Violation Rate: `{comp['violation_rate']:.4f}`",
                f"- Mean Score: `{comp['mean_score']:.4f}`",
                f"- Min Score: `{comp['min_score']:.4f}`" if comp.get('min_score') else "",
            ])

        # Authenticity section
        auth = detail.get("authenticity", {})
        if auth.get("total", 0) > 0:
            lines.extend([
                "",
                "## Authenticity Audit",
                "",
                f"- Total Audits: `{auth['total']}`",
                f"- Failures: `{auth['failures']}`",
                f"- Failure Rate: `{auth['failure_rate']:.4f}`",
                f"- Mean Score: `{auth['mean_score']:.4f}`",
            ])

        # Behavior distribution
        behavior = detail.get("behavior_distribution", {})
        if behavior:
            lines.extend(["", "## AI Behavior Distribution", ""])
            for behavior_class, count in sorted(behavior.items(), key=lambda x: -x[1]):
                lines.append(f"- {behavior_class}: `{count}`")

        # Persona coverage
        coverage = detail.get("persona_coverage", {})
        if coverage:
            lines.extend(["", "## Persona Coverage", ""])
            for persona_id, count in sorted(coverage.items()):
                lines.append(f"- {persona_id}: `{count}`")

        return "\n".join(lines) + "\n"
