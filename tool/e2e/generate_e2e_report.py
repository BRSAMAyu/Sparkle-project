#!/usr/bin/env python3
"""tool/e2e/generate_e2e_report.py — Generate prelaunch engineering report"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = ROOT_DIR / "artifacts" / "e2e" / "logs"
REPORT_DIR = ROOT_DIR / "artifacts" / "e2e" / "reports"
SCREENSHOT_DIR = ROOT_DIR / "artifacts" / "e2e" / "screenshots"


def read_status(filename: str) -> dict:
    path = REPORT_DIR / filename
    result = {}
    if path.exists():
        for line in path.read_text().strip().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                result[k] = v.strip()
    return result


def count_findings(log_dir: Path, patterns: list[tuple[str, str]], label: str) -> list[dict]:
    findings = []
    if not log_dir.exists():
        return findings
    for log_file in sorted(log_dir.glob("*.log")):
        try:
            content = log_file.read_text(errors="replace")
        except Exception:
            continue
        for i, line in enumerate(content.splitlines(), 1):
            for pattern, name in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append({
                        "file": log_file.name,
                        "line": i,
                        "severity": name,
                        "text": line[:120],
                    })
    return findings


def get_screenshots() -> list[dict]:
    screenshots = []
    for platform in ["ios", "android"]:
        d = SCREENSHOT_DIR / platform
        if d.exists():
            for img in sorted(d.glob("*.png")):
                screenshots.append({
                    "platform": platform,
                    "name": img.name,
                    "path": str(img.relative_to(ROOT_DIR)),
                })
    # Root screenshots
    for img in sorted(SCREENSHOT_DIR.glob("*.png")):
        screenshots.append({
            "platform": "general",
            "name": img.name,
            "path": str(img.relative_to(ROOT_DIR)),
        })
    return screenshots


def generate_report():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Collect statuses
    health = read_status("healthcheck_status.txt")
    smoke = read_status("smoke_status.txt")
    backend = read_status("backend_status.txt")
    gateway = read_status("gateway_status.txt")
    flutter = read_status("flutter_status.txt")
    e2e = read_status("e2e_status.txt")
    ios = read_status("ios_status.txt")
    android = read_status("android_status.txt")

    # Collect log findings
    p0_patterns = [
        (r"EXCEPTION CAUGHT BY WIDGETS", "Flutter Exception"),
        (r"RenderFlex overflowed", "Overflow"),
        (r"panic:", "Go Panic"),
        (r"Traceback \(most recent", "Python Traceback"),
        (r"FATAL EXCEPTION", "Android Fatal"),
        (r"ANR in", "Android ANR"),
        (r"HTTP 5\d{2}", "HTTP 500"),
        (r"connection refused", "Connection Refused"),
    ]
    p1_patterns = [
        (r"HTTP 4\d{2}", "HTTP 4xx"),
        (r"ERROR", "Error Log"),
        (r"upstream timeout", "Upstream Timeout"),
        (r"SocketException", "Socket Error"),
        (r"setState.*after dispose", "State After Dispose"),
    ]

    p0_findings = count_findings(LOG_DIR, p0_patterns, "P0")
    p1_findings = count_findings(LOG_DIR, p1_patterns, "P1")
    screenshots = get_screenshots()

    # Determine overall status
    all_pass = all(
        s.get("fail", "0") == "0"
        for s in [health, smoke, backend, gateway, flutter, e2e, ios, android]
        if s
    )
    overall = "PASS" if all_pass and not p0_findings else "FAIL"

    # Build report
    lines = []
    lines.append("# Sparkle Prelaunch Engineering Report")
    lines.append(f"\n> Generated: {now} | Overall: **{overall}**")
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| Area | Status | Pass | Fail |")
    lines.append("|------|--------|------|------|")

    def row(name, status_dict):
        if not status_dict:
            return f"| {name} | SKIPPED | - | - |"
        p = status_dict.get("pass", "?")
        f = status_dict.get("fail", "?")
        status = "PASS" if f == "0" else "FAIL"
        return f"| {name} | {status} | {p} | {f} |"

    lines.append(row("Docker infra", health))
    lines.append(row("Smoke tests", smoke))
    lines.append(row("Python backend", backend))
    lines.append(row("Go Gateway", gateway))
    lines.append(row("Flutter analyze+test", flutter))
    lines.append(row("E2E core flow", e2e))
    lines.append(row("iOS Simulator", ios))
    lines.append(row("Android Emulator", android))
    lines.append("")

    # P0 Blockers
    lines.append("## P0 Blockers")
    lines.append("")
    if p0_findings:
        for f in p0_findings[:20]:
            lines.append(f"- **{f['severity']}** in `{f['file']}`:L{f['line']}: {f['text'][:80]}")
    else:
        lines.append("_No P0 blockers found._")
    lines.append("")

    # P1 Issues
    lines.append("## P1 Issues")
    lines.append("")
    if p1_findings:
        for f in p1_findings[:20]:
            lines.append(f"- **{f['severity']}** in `{f['file']}`:L{f['line']}: {f['text'][:80]}")
    else:
        lines.append("_No P1 issues found._")
    lines.append("")

    # Screenshots
    if screenshots:
        lines.append("## Screenshots")
        lines.append("")
        lines.append("| Step | Platform | Path |")
        lines.append("|------|----------|------|")
        for s in screenshots:
            lines.append(f"| {s['name']} | {s['platform']} | `{s['path']}` |")
        lines.append("")

    # Logs
    lines.append("## Logs")
    lines.append("")
    lines.append(f"| Directory | `{LOG_DIR.relative_to(ROOT_DIR)}/` |")
    lines.append("")
    if LOG_DIR.exists():
        for log_file in sorted(LOG_DIR.glob("*.log")):
            size = log_file.stat().st_size
            lines.append(f"- `{log_file.name}` ({size:,} bytes)")
    lines.append("")

    # Re-run command
    lines.append("## Re-run Command")
    lines.append("```bash")
    lines.append("bash scripts/test/run_prelaunch.sh")
    lines.append("```")
    lines.append("")

    # Write report
    report_path = REPORT_DIR / "PRELAUNCH_REPORT.md"
    report_path.write_text("\n".join(lines))
    print(f"Report written to: {report_path}")
    return 1 if overall == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(generate_report())
