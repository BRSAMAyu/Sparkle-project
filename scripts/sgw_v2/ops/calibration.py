"""Human calibration infrastructure for audit reliability.

Provides:
- human_labels table for storing human audit scores
- CSV export for blind review
- Cohen's kappa calculation
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from ..storage.db import RunDB


_HUMAN_LABELS_SCHEMA = """
CREATE TABLE IF NOT EXISTS human_labels (
    label_id    TEXT PRIMARY KEY,
    audit_id    TEXT NOT NULL,
    run_id      TEXT NOT NULL,
    audit_type  TEXT NOT NULL DEFAULT 'compliance',
    ai_score    REAL,
    human_score REAL NOT NULL,
    human_pass  INTEGER NOT NULL,
    labeler     TEXT NOT NULL DEFAULT 'unknown',
    notes       TEXT,
    labeled_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_human_labels_audit ON human_labels(audit_id);
CREATE INDEX IF NOT EXISTS idx_human_labels_run ON human_labels(run_id);
CREATE INDEX IF NOT EXISTS idx_human_labels_labeler ON human_labels(labeler);
"""


class CalibrationManager:
    """Manages human calibration data and computes inter-rater agreement."""

    def __init__(self, run_db: RunDB):
        self.run_db = run_db
        self.run_db.conn.executescript(_HUMAN_LABELS_SCHEMA)
        self.run_db.conn.commit()

    def sample_for_review(self, run_id: str, n: int = 100, output_path: Path | None = None) -> list[dict[str, Any]]:
        """Export a random sample of audits for human review."""
        rows = self.run_db.conn.execute(
            """SELECT a.audit_id, a.run_id, a.audit_type, a.overall, a.is_violation,
                      a.reason, a.scores, s.seed_persona_id
               FROM audits a
               LEFT JOIN sessions s ON s.session_id = a.session_id
               WHERE a.run_id = ? AND a.status = 'completed'
               ORDER BY RANDOM() LIMIT ?""",
            (run_id, n),
        ).fetchall()
        cols = [desc[0] for desc in self.run_db.conn.execute("SELECT * FROM audits LIMIT 0").description]
        samples = [dict(zip(cols, row)) for row in rows]

        if output_path:
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "audit_id", "run_id", "audit_type", "overall", "is_violation",
                    "reason", "scores", "seed_persona_id",
                    "human_score", "human_pass", "labeler", "notes",
                ])
                writer.writeheader()
                for s in samples:
                    s["human_score"] = ""
                    s["human_pass"] = ""
                    s["labeler"] = ""
                    s["notes"] = ""
                    if isinstance(s.get("scores"), str):
                        pass
                    else:
                        s["scores"] = json.dumps(s.get("scores", {}), ensure_ascii=False)
                    writer.writerow(s)

        return samples

    def import_labels(self, csv_path: Path, labeler: str = "unknown") -> int:
        """Import human-labeled CSV back into the database."""
        imported = 0
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row.get("human_score") or not row.get("human_pass"):
                    continue
                from datetime import datetime, timezone
                self.run_db.conn.execute(
                    """INSERT OR REPLACE INTO human_labels
                       (label_id, audit_id, run_id, audit_type, ai_score, human_score,
                        human_pass, labeler, notes, labeled_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        f"hl_{row['audit_id']}",
                        row["audit_id"],
                        row["run_id"],
                        row.get("audit_type", "compliance"),
                        float(row.get("overall", 0)) if row.get("overall") else None,
                        float(row["human_score"]),
                        int(row["human_pass"]),
                        labeler,
                        row.get("notes", ""),
                        datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds"),
                    ),
                )
                imported += 1
        self.run_db.conn.commit()
        return imported

    def compute_kappa(self, run_id: str | None = None) -> dict[str, Any]:
        """Compute Cohen's kappa between AI and human labels."""
        if run_id:
            rows = self.run_db.conn.execute(
                "SELECT ai_score, human_score, human_pass FROM human_labels WHERE run_id = ?",
                (run_id,),
            ).fetchall()
        else:
            rows = self.run_db.conn.execute(
                "SELECT ai_score, human_score, human_pass FROM human_labels"
            ).fetchall()

        if len(rows) < 10:
            return {"kappa": None, "n": len(rows), "warning": "insufficient samples (need >= 10)"}

        # Binary agreement: AI pass/fail vs human pass/fail
        ai_pass_threshold = 0.85
        ai_passes = sum(1 for r in rows if (r[0] or 0) >= ai_pass_threshold)
        human_passes = sum(1 for r in rows if r[2] == 1)

        # Both agree pass
        both_pass = sum(1 for r in rows if (r[0] or 0) >= ai_pass_threshold and r[2] == 1)
        # Both agree fail
        both_fail = sum(1 for r in rows if (r[0] or 0) < ai_pass_threshold and r[2] == 0)

        n = len(rows)
        p_observed = (both_pass + both_fail) / n
        p_ai_pass = ai_passes / n
        p_ai_fail = 1 - p_ai_pass
        p_human_pass = human_passes / n
        p_human_fail = 1 - p_human_pass

        p_expected = p_ai_pass * p_human_pass + p_ai_fail * p_human_fail
        kappa = (p_observed - p_expected) / max(1 - p_expected, 1e-10)

        return {
            "kappa": round(kappa, 4),
            "n": n,
            "p_observed": round(p_observed, 4),
            "p_expected": round(p_expected, 4),
            "ai_pass_rate": round(p_ai_pass, 4),
            "human_pass_rate": round(p_human_pass, 4),
            "alert": kappa < 0.6,
        }
