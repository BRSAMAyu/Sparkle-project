"""Alerting for SGW long-term operation.

Monitors run metrics and raises alerts when thresholds are breached.
Alerts are written to SQLite for persistence and optionally to stdout.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..storage.db import RunDB


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


# SQL for alerts table
_ALERTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS alerts (
    alert_id    TEXT PRIMARY KEY,
    run_id      TEXT,
    severity    TEXT NOT NULL DEFAULT 'warning',
    category    TEXT NOT NULL,
    message     TEXT NOT NULL,
    metric_name TEXT,
    metric_value REAL,
    threshold   REAL,
    dismissed   INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_alerts_run ON alerts(run_id);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_dismissed ON alerts(dismissed);
"""


@dataclass
class AlertRule:
    """A single alerting rule."""
    name: str
    category: str
    severity: str                   # "info" | "warning" | "critical"
    metric_path: str                # Dot-notation path in run summary
    threshold: float
    comparison: str                 # "gt" | "lt" | "eq"
    message_template: str


# Pre-defined alert rules
DEFAULT_ALERT_RULES: list[AlertRule] = [
    AlertRule(
        name="high_soft_violation_rate",
        category="compliance",
        severity="warning",
        metric_path="soft_violation_rate",
        threshold=0.10,
        comparison="gt",
        message_template="Soft violation rate {value:.4f} exceeds threshold {threshold}",
    ),
    AlertRule(
        name="critical_soft_violation_rate",
        category="compliance",
        severity="critical",
        metric_path="soft_violation_rate",
        threshold=0.20,
        comparison="gt",
        message_template="CRITICAL: Soft violation rate {value:.4f} far exceeds threshold {threshold}",
    ),
    AlertRule(
        name="hard_violations",
        category="compliance",
        severity="critical",
        metric_path="hard_violations",
        threshold=0,
        comparison="gt",
        message_template="Hard violations detected: {value}",
    ),
    AlertRule(
        name="low_authenticity",
        category="authenticity",
        severity="warning",
        metric_path="authenticity_mean",
        threshold=0.60,
        comparison="lt",
        message_template="Authenticity mean {value:.4f} below threshold {threshold}",
    ),
    AlertRule(
        name="low_session_completion",
        category="performance",
        severity="warning",
        metric_path="sessions_completed",
        threshold=100,
        comparison="lt",
        message_template="Session completion {value} below minimum {threshold}",
    ),
]


class Notifier:
    """Simple notification transport for alerts.

    Supports: stdout (always), file append, and optional webhook.
    """

    def __init__(
        self,
        *,
        log_file: Path | None = None,
        webhook_url: str | None = None,
    ):
        self.log_file = log_file
        self.webhook_url = webhook_url

    def notify(self, alert: dict[str, Any]) -> None:
        """Send alert through all configured transports."""
        msg = f"[{alert['severity'].upper()}] {alert['message']} (run={alert.get('run_id', '?')[:12]})"

        # Always print to stdout
        print(f"[sgw-alert] {msg}")

        # Append to log file
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"{alert['created_at']} {msg}\n")

        # Webhook (best-effort, non-blocking)
        if self.webhook_url:
            self._send_webhook(alert)

    def _send_webhook(self, alert: dict[str, Any]) -> None:
        """Best-effort webhook notification."""
        try:
            import urllib.request
            import urllib.error
            data = json.dumps(alert, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                pass  # Best effort
        except Exception:  # noqa: BLE001
            pass  # Silently ignore webhook failures


class AlertManager:
    """Monitors run metrics and raises alerts."""

    def __init__(
        self,
        run_db: RunDB,
        rules: list[AlertRule] | None = None,
        notifier: Notifier | None = None,
    ):
        self.run_db = run_db
        self.rules = rules or DEFAULT_ALERT_RULES
        self.notifier = notifier or Notifier()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.run_db.conn.executescript(_ALERTS_SCHEMA)
        self.run_db.conn.commit()

    def check_run(self, run_id: str) -> list[dict[str, Any]]:
        """Check a run against all alert rules. Returns list of triggered alerts."""
        summary = self.run_db.run_summary(run_id)
        if not summary:
            return []

        triggered: list[dict[str, Any]] = []
        for rule in self.rules:
            value = summary.get(rule.metric_path)
            if value is None:
                continue

            breached = False
            if rule.comparison == "gt" and value > rule.threshold:
                breached = True
            elif rule.comparison == "lt" and value < rule.threshold:
                breached = True
            elif rule.comparison == "eq" and value == rule.threshold:
                breached = True

            if breached:
                alert = {
                    "alert_id": f"alert_{uuid.uuid4().hex[:12]}",
                    "run_id": run_id,
                    "severity": rule.severity,
                    "category": rule.category,
                    "message": rule.message_template.format(
                        value=value, threshold=rule.threshold
                    ),
                    "metric_name": rule.metric_path,
                    "metric_value": value,
                    "threshold": rule.threshold,
                    "dismissed": 0,
                    "created_at": _utcnow_iso(),
                }
                self._save_alert(alert)
                triggered.append(alert)

                if rule.severity == "critical":
                    print(f"[sgw-alert] CRITICAL: {alert['message']}")

        return triggered

    def _save_alert(self, alert: dict[str, Any]) -> None:
        # Persist to SQLite
        self.run_db.conn.execute(
            """INSERT INTO alerts
               (alert_id, run_id, severity, category, message, metric_name,
                metric_value, threshold, dismissed, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                alert["alert_id"],
                alert["run_id"],
                alert["severity"],
                alert["category"],
                alert["message"],
                alert["metric_name"],
                alert["metric_value"],
                alert["threshold"],
                alert["dismissed"],
                alert["created_at"],
            ),
        )
        self.run_db.conn.commit()

        # Notify via transport (stdout/file/webhook)
        if alert.get("severity") in ("critical", "warning"):
            self.notifier.notify(alert)

    def get_active_alerts(self) -> list[dict[str, Any]]:
        """Return all non-dismissed alerts."""
        rows = self.run_db.conn.execute(
            "SELECT * FROM alerts WHERE dismissed = 0 ORDER BY created_at DESC"
        ).fetchall()
        cols = [desc[0] for desc in self.run_db.conn.execute("SELECT * FROM alerts LIMIT 0").description]
        return [dict(zip(cols, row)) for row in rows]

    def dismiss_alert(self, alert_id: str) -> None:
        self.run_db.conn.execute(
            "UPDATE alerts SET dismissed = 1 WHERE alert_id = ?", (alert_id,)
        )
        self.run_db.conn.commit()

    def get_alert_history(self, run_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """Return alert history, optionally filtered by run_id."""
        if run_id:
            rows = self.run_db.conn.execute(
                "SELECT * FROM alerts WHERE run_id = ? ORDER BY created_at DESC LIMIT ?",
                (run_id, limit),
            ).fetchall()
        else:
            rows = self.run_db.conn.execute(
                "SELECT * FROM alerts ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()

        cols = [desc[0] for desc in self.run_db.conn.execute("SELECT * FROM alerts LIMIT 0").description]
        return [dict(zip(cols, row)) for row in rows]
