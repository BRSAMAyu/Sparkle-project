from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


class ReportLogger:
    def __init__(self, base_dir: str | None = None):
        resolved_dir = base_dir or os.getenv(
            "SPARKLE_REPORT_LOG_DIR",
            os.path.join(tempfile.gettempdir(), "sparkle_learning_reports"),
        )
        self.base_dir = Path(resolved_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def log_jsonl(self, report_id: str, payload: dict[str, Any]) -> None:
        path = self.base_dir / f"{report_id}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def log_text(self, report_id: str, message: str) -> None:
        path = self.base_dir / f"{report_id}.log"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(message.rstrip() + "\n")
