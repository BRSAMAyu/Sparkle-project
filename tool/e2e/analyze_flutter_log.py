#!/usr/bin/env python3
"""tool/e2e/analyze_flutter_log.py — Scan Flutter logs for hard errors"""

import re
import sys
from pathlib import Path

# P0 patterns: crash-level
P0_PATTERNS = [
    (r"EXCEPTION CAUGHT BY WIDGETS LIBRARY", "EXCEPTION_CAUGHT_BY_WIDGETS"),
    (r"EXCEPTION CAUGHT BY .+ LIBRARY", "EXCEPTION_CAUGHT_BY_LIBRARY"),
    (r"RenderFlex overflowed", "RENDERFLEX_OVERFLOW"),
    (r"setState\(\) called after dispose\(\)", "SETSTATE_AFTER_DISPOSE"),
    (r"LateInitializationError", "LATE_INIT_ERROR"),
    (r"Null check operator used on a null value", "NULL_CHECK_OPERATOR"),
    (r"MissingPluginException", "MISSING_PLUGIN"),
    (r"Unable to load asset", "UNABLE_TO_LOAD_ASSET"),
    (r"AppLocalizations.*lookup failed", "L10N_LOOKUP_FAILED"),
    (r"══.*Exception caught", "FLUTTER_EXCEPTION"),
    (r"HTTP 5\d{2}", "HTTP_5XX"),
    (r"SocketException", "SOCKET_EXCEPTION"),
    (r"TimeoutException", "TIMEOUT_EXCEPTION"),
    (r"HandshakeException", "HANDSHAKE_EXCEPTION"),
    (r"Connection refused", "CONNECTION_REFUSED"),
]

# P1 patterns: usability-level
P1_PATTERNS = [
    (r"HTTP 4\d{2}", "HTTP_4XX"),
    (r"Failed to load resource", "RESOURCE_LOAD_FAILED"),
    (r"DioException", "DIO_EXCEPTION"),
    (r"PlatformException", "PLATFORM_EXCEPTION"),
    (r"Unhandled exception", "UNHANDLED_EXCEPTION"),
    (r"RangeError", "RANGE_ERROR"),
    (r"TypeError", "TYPE_ERROR"),
    (r"StateError", "STATE_ERROR"),
]

# P2 patterns: quality issues
P2_PATTERNS = [
    (r".WARNING:", "WARNING"),
    (r"D/.+flutter", "FLUTTER_DEBUG_LOG"),
    (r"I/chatty", "CHATTY"),
]


def analyze_log(log_path: Path) -> dict:
    results = {
        "file": str(log_path),
        "p0": [],
        "p1": [],
        "p2": [],
        "total_lines": 0,
        "error_lines": 0,
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
        matched = False

        for pattern, name in P0_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                results["p0"].append({"line": i, "name": name, "text": line[:200]})
                matched = True
                break

        if not matched:
            for pattern, name in P1_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    results["p1"].append({"line": i, "name": name, "text": line[:200]})
                    matched = True
                    break

        if not matched:
            for pattern, name in P2_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    results["p2"].append({"line": i, "name": name, "text": line[:200]})
                    matched = True
                    break

        if matched:
            results["error_lines"] += 1

    return results


def main():
    log_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("artifacts/e2e/logs")

    if not log_dir.exists():
        print(f"Log directory not found: {log_dir}")
        return 1

    flutter_logs = list(log_dir.glob("flutter*.log")) + list(log_dir.glob("*flutter*.log"))

    if not flutter_logs:
        flutter_logs = list(log_dir.glob("*.log"))

    all_results = []
    total_p0 = 0
    total_p1 = 0

    for log_file in sorted(flutter_logs):
        result = analyze_log(log_file)
        all_results.append(result)
        total_p0 += len(result["p0"])
        total_p1 += len(result["p1"])

    print(f"Flutter Log Analysis: {len(all_results)} files")
    print(f"  P0 (blocker): {total_p0}")
    print(f"  P1 (impact):  {total_p1}")
    print()

    for result in all_results:
        if result["p0"] or result["p1"]:
            print(f"File: {result['file']}")
            for item in result["p0"]:
                print(f"  [P0] Line {item['line']}: {item['name']} — {item['text'][:100]}")
            for item in result["p1"]:
                print(f"  [P1] Line {item['line']}: {item['name']} — {item['text'][:100]}")
            print()

    return 1 if total_p0 > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
