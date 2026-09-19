"""证据采集：一次 journey run 的产物目录、截图、API 留存、DB 探针、manifest。

目录布局（默认落在 worktree v3-output/B-03/evidence/ 下）：
  <evidence_root>/<run_id>/
    run_manifest.json     # 环境：SHA/device/time/gateway/build metadata/步骤结果
    screenshots/*.png     # 每步 UI 现场（web/android/macos backend）
    api_log.jsonl         # 逐条 HTTP/WS 请求-响应留存（api backend；web backend 记录 CDP 网络事件）
    db_probes.jsonl       # 只读 DB 探针（SELECT-only，docker exec psql）
    steps.json            # 步骤级 PASS/FAIL 明细
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import RunManifest, StepResult

DB_CONTAINER = "sparkle_db"
DB_NAME = "sparkle"


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class EvidenceCollector:
    def __init__(self, evidence_root: Path, run_id: str) -> None:
        self.run_dir = Path(evidence_root) / run_id
        self.shot_dir = self.run_dir / "screenshots"
        self.shot_dir.mkdir(parents=True, exist_ok=True)
        self._api_log = self.run_dir / "api_log.jsonl"
        self._db_log = self.run_dir / "db_probes.jsonl"

    # ---------- 留存原语 ----------
    def log_api(self, kind: str, payload: dict[str, Any]) -> None:
        entry = {"ts": utcnow_iso(), "kind": kind, **payload}
        with self._api_log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def save_text(self, name: str, text: str) -> Path:
        path = self.run_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def save_bytes(self, rel: str, data: bytes) -> Path:
        path = self.run_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def save_screenshot(self, rel: str, data: bytes) -> Path:
        if not rel.startswith("screenshots/"):
            rel = f"screenshots/{rel}"
        return self.save_bytes(rel, data)

    # ---------- DB 只读探针（SELECT-only；主仓 DB 纪律：不写库） ----------
    def db_scalar(self, sql: str) -> str:
        out = subprocess.run(
            ["docker", "exec", DB_CONTAINER, "psql", "-U", "postgres", "-d", DB_NAME, "-tAc", sql],
            capture_output=True,
            text=True,
            timeout=30,
        )
        value = (out.stdout or "").strip()
        with self._db_log.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {"ts": utcnow_iso(), "sql": sql, "result": value, "stderr": (out.stderr or "").strip()[:400]},
                    ensure_ascii=False,
                )
                + "\n"
            )
        return value

    # ---------- 汇总 ----------
    def write_steps(self, steps: list[StepResult]) -> Path:
        path = self.run_dir / "steps.json"
        path.write_text(
            json.dumps([s.to_dict() for s in steps], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    def write_manifest(self, manifest: RunManifest) -> Path:
        path = self.run_dir / "run_manifest.json"
        path.write_text(
            json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path
