#!/usr/bin/env python3
"""tool/e2e/collect_logs.py — Collect logs from all services into artifacts/e2e/logs/"""

import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = ROOT_DIR / "artifacts" / "e2e" / "logs"


def run(cmd: str, output_file: Path) -> bool:
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        output = result.stdout + result.stderr
        output_file.write_text(output)
        return result.returncode == 0
    except Exception as e:
        output_file.write_text(f"COLLECTION ERROR: {e}")
        return False


def collect():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"[collect] Collecting logs to {LOG_DIR}")

    results = {}

    # Docker container logs
    for svc in ["sparkle-db", "sparkle-redis", "minio", "sparkle-gateway", "sparkle-agent", "sparkle-api"]:
        ok = run(
            f"docker compose -f {ROOT_DIR}/docker-compose.yml logs --no-color --tail=500 {svc}",
            LOG_DIR / f"docker_{svc}_{timestamp}.log",
        )
        results[f"docker_{svc}"] = "OK" if ok else "FAIL"

    # Backend logs
    backend_logs = ROOT_DIR / "backend" / "logs"
    if backend_logs.exists():
        for log_file in backend_logs.glob("*.log"):
            shutil.copy2(log_file, LOG_DIR / f"backend_{log_file.name}_{timestamp}.log")
            results[f"backend_{log_file.stem}"] = "OK"

    # Flutter run logs (if any)
    flutter_log = LOG_DIR / "flutter_ios.log"
    if flutter_log.exists():
        results["flutter_ios"] = "OK"
    flutter_android = LOG_DIR / "android_logcat.log"
    if flutter_android.exists():
        results["android_logcat"] = "OK"

    # Print summary
    print("[collect] Results:")
    for k, v in results.items():
        print(f"  {k}: {v}")

    return 0


if __name__ == "__main__":
    sys.exit(collect())
