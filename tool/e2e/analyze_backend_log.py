#!/usr/bin/env python3
"""tool/e2e/analyze_backend_log.py — Scan backend logs for errors"""

import re
import sys
from pathlib import Path

# P0 patterns
P0_PATTERNS = [
    (r"Traceback \(most recent call last\)", "PYTHON_TRACEBACK"),
    (r"panic: ", "GO_PANIC"),
    (r"FATAL", "FATAL"),
    (r"migration error", "MIGRATION_ERROR"),
    (r"connection refused", "CONNECTION_REFUSED"),
    (r"Redis error", "REDIS_ERROR"),
    (r"gRPC error", "GRPC_ERROR"),
    (r"unhandled exception", "UNHANDLED_EXCEPTION"),
    (r" 500 ", "HTTP_500"),
    (r"SQLAlchemy.*Error", "SQLALCHEMY_ERROR"),
    (r"OperationalError", "DB_OPERATIONAL_ERROR"),
    (r"IntegrityError", "DB_INTEGRITY_ERROR"),
]

# P1 patterns
P1_PATTERNS = [
    (r"ERROR", "ERROR_LOG"),
    (r"WARNING", "WARNING_LOG"),
    (r"upstream timeout", "UPSTREAM_TIMEOUT"),
    (r"websocket close.*abnormal", "WS_CLOSE_ABNORMAL"),
    (r"failed to proxy", "PROXY_FAILED"),
    (r"unsafe error leakage", "UNSAFE_ERROR_LEAKAGE"),
    (r"config missing", "CONFIG_MISSING"),
    (r"MinIO.*error", "MINIO_ERROR"),
    (r"rate limit exceeded", "RATE_LIMITED"),
    (r" 4\d{2} ", "HTTP_4XX"),
]

# P2 patterns
P2_PATTERNS = [
    (r"DEBUG", "DEBUG_LOG"),
    (r"slow query", "SLOW_QUERY"),
    (r"deprecated", "DEPRECATED"),
]


def analyze_log(log_path: Path) -> dict:
    results = {
        "file": str(log_path),
        "p0": [],
        "p1": [],
        "p2": [],
        "total_lines": 0,
    }

    if not log_path.exists():
        results["error"] = "File not found"
        return results

    try:
        content = log_path.read_text(errors="replace")
    except Exception as e:
        results["error"] = str(e)
        return results

    lines = content.splitlines()
    results["total_lines"] = len(lines)

    for i, line in enumerate(lines, 1):
        for pattern, name in P0_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                results["p0"].append({"line": i, "name": name, "text": line[:200]})
                break
        else:
            for pattern, name in P1_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    results["p1"].append({"line": i, "name": name, "text": line[:200]})
                    break
            else:
                for pattern, name in P2_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        results["p2"].append({"line": i, "name": name, "text": line[:200]})
                        break

    return results


def main():
    log_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("artifacts/e2e/logs")

    if not log_dir.exists():
        print(f"Log directory not found: {log_dir}")
        return 1

    log_files = sorted(log_dir.glob("*.log"))

    all_results = []
    total_p0 = 0
    total_p1 = 0

    for log_file in log_files:
        if "flutter" in log_file.name.lower():
            continue  # Skip Flutter logs (handled separately)
        result = analyze_log(log_file)
        all_results.append(result)
        total_p0 += len(result["p0"])
        total_p1 += len(result["p1"])

    print(f"Backend Log Analysis: {len(all_results)} files")
    print(f"  P0 (blocker): {total_p0}")
    print(f"  P1 (impact):  {total_p1}")
    print()

    for result in all_results:
        if result["p0"] or result["p1"]:
            print(f"File: {result['file']}")
            for item in result["p0"][:10]:
                print(f"  [P0] L{item['line']}: {item['name']} — {item['text'][:100]}")
            for item in result["p1"][:10]:
                print(f"  [P1] L{item['line']}: {item['name']} — {item['text'][:100]}")
            if len(result["p0"]) > 10 or len(result["p1"]) > 10:
                print(f"  ... and {max(0, len(result['p0'])-10)} more P0, {max(0, len(result['p1'])-10)} more P1")
            print()

    return 1 if total_p0 > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
