#!/usr/bin/env python3
"""Rule BI: Hardcoded secrets / credentials guard.

Scans Python, Go, and Dart source files for hardcoded credential patterns
that match the CLAUDE.md Security Checklist item:
"No hardcoded tokens or passwords (including test files)"

Exit 0 on clean, non-zero on findings.

Allow marker: a line whose raw text contains `guard-bi-allow:` is exempt
(inline form — `# guard-bi-allow: <reason>` in Python, `// guard-bi-allow:`
in Go/Dart). Use it only for deliberate non-secret probe/fixture values the
patterns cannot distinguish from real credentials; every marker must carry a
reason. Run `--self-test` for the fixture round-trip (marker exempts, marker-
less twin still caught).
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Inline allow marker, checked against the RAW line (before comment stripping).
_ALLOW_MARKER = "guard-bi-allow"

# ── Direct patterns (independent of assignment syntax) ─────────────────
_OPENAI_KEY = re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")
_GITHUB_TOKEN = re.compile(r"\bghp_[A-Za-z0-9]{36,}\b")
_GITHUB_PAT = re.compile(r"github_pat_[A-Za-z0-9_]{20,}\b")
_AWS_KEY = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
_GOOGLE_KEY = re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b")

# Assignment-based: credential keywords followed by = or : with a string value.
# The keyword must be a standalone identifier part (preceded by _ or start),
# not merely a substring inside a camelCase name like `keyAccessToken`.
_ASSIGNMENT_RE = re.compile(
    r"""(?ix)
    (?:^|[_\s])(api[_\s]?key|secret|token|password|passwd|auth[_\s]?token)
    \s*[:=]\s*
    ["']([^"']{8,})["']
    """
)

# ── Exclusions ─────────────────────────────────────────────────────────
_EXCLUDE_FILES = {
    "llm_secure_io.py",        # regex definitions for detection
    "llm_output_validator.py",  # test examples of LLM output
    "llm_safety.py",            # test examples for safety checks
    "llm_monitoring.py",        # legit token_usage monitoring
    "security.py",              # token validation logic
    "_credentials.py",          # centralized test credential fixtures
}

_EXCLUDE_DIRS = {
    "__pycache__",
    "node_modules",
    ".git",
    ".dart_tool",
    "build",
    ".claude",
    "gen",
    ".venv",
    "site-packages",
    "tool",                     # dev/smoke tools not shipped to users
}

_SAFE_ASSIGNMENT_VALUES = {
    "",
    "your_api_key_here", "your-secret-key", "your_token", "your_password",
    "placeholder", "changeme", "change_me",
    "test_key", "test_token", "test_secret", "test_api_key",
    "dummy", "example", "xxx", "secret_key",
    "access_token", "refresh_token", "demo_token", "demo_refresh_token",
    "system-managed", "hashed",
    "null", "none", "undefined",
}


def _strip_inline_comment(line: str, ext: str) -> str:
    """Remove inline comments so we don't flag commented-out examples."""
    if ext == ".py":
        idx = line.find("#")
        if idx >= 0:
            return line[:idx]
    elif ext in (".go", ".dart", ".ts", ".js"):
        idx = line.find("//")
        if idx >= 0:
            return line[:idx]
    return line


def _is_type_annotation(line: str) -> bool:
    """Skip lines like `password: str = ""` or `token: String = ""`."""
    return bool(re.search(r':\s*(str|String|Text|VARCHAR)\s*=\s*""', line))


def _is_regex_or_security_code(line: str) -> bool:
    """Skip lines defining regex patterns or security masking code."""
    if re.search(r"re\.compile\(|RegExp\(|regexp\.MustCompile", line):
        return True
    if re.search(r"_maskSecret|masked\s*=|replaceAllMapped.*token", line):
        return True
    return False


def _value_is_placeholder(value: str) -> bool:
    """Check if the captured value looks like a placeholder, not a real secret."""
    lowered = value.lower().strip()
    if lowered in _SAFE_ASSIGNMENT_VALUES:
        return True
    if lowered.startswith("your_") or lowered.startswith("your-"):
        return True
    if lowered.startswith("test-") or lowered.startswith("demo_"):
        return True
    # Repeated same character (e.g., "xxxx", "****", "----")
    if len(set(lowered)) <= 2 and len(lowered) >= 4:
        return True
    return False


def _is_log_masking_context(lines: list[str], lineno: int) -> bool:
    """Check surrounding lines for log-masking / security sanitization context."""
    start = max(0, lineno - 3)
    end = min(len(lines), lineno + 3)
    context = "\n".join(lines[start:end]).lower()
    return bool(re.search(r"mask|sanitize|redact|secret.*detect", context))


def scan_file(filepath: Path) -> list[str]:
    """Scan a single file for hardcoded secrets. Returns list of violation descriptions."""
    violations: list[str] = []
    ext = filepath.suffix

    try:
        lines = filepath.read_text().splitlines()
    except (OSError, UnicodeDecodeError):
        return violations

    try:
        rel = filepath.relative_to(REPO_ROOT)
    except ValueError:  # fixtures outside the repo (self-test tempdir)
        rel = filepath

    for lineno, raw_line in enumerate(lines, start=1):
        # Inline allow marker wins first: check the raw line so the marker
        # survives even though `_strip_inline_comment` would drop the comment.
        if _ALLOW_MARKER in raw_line:
            continue

        line = _strip_inline_comment(raw_line, ext)
        stripped = line.strip()

        if not stripped:
            continue

        if _is_type_annotation(line):
            continue
        if _is_regex_or_security_code(line):
            continue

        # Direct pattern matches
        for pattern, desc in [
            (_OPENAI_KEY, "OpenAI API key"),
            (_GITHUB_TOKEN, "GitHub classic token"),
            (_GITHUB_PAT, "GitHub fine-grained PAT"),
            (_AWS_KEY, "AWS access key ID"),
            (_GOOGLE_KEY, "Google API key"),
        ]:
            for match in pattern.finditer(line):
                value = match.group(0)
                violations.append(
                    f"{rel}:{lineno}: {desc} detected: {value[:12]}..."
                )

        # Assignment-based detection
        for match in _ASSIGNMENT_RE.finditer(line):
            value = match.group(2)
            if _value_is_placeholder(value):
                continue
            if value.startswith(("/", "./", "http://", "https://", "${", "$(")):
                continue
            if value.startswith(("$", "%", "{")):
                continue
            # Skip if the assignment appears in log-masking context
            if _is_log_masking_context(lines, lineno):
                continue
            keyword = match.group(1)
            violations.append(
                f"{rel}:{lineno}: hardcoded '{keyword}' assignment"
            )

    return violations


def _should_skip(filepath: Path) -> bool:
    """Determine if a file should be skipped."""
    parts = filepath.parts
    for excluded in _EXCLUDE_DIRS:
        if excluded in parts:
            return True

    if filepath.name in _EXCLUDE_FILES:
        return True

    # Skip test files
    if filepath.name.startswith("test_") or filepath.name.endswith("_test.py"):
        return True
    if filepath.name.endswith("_test.dart") or filepath.name.endswith("_test.go"):
        return True

    suffix = filepath.suffix
    return suffix not in (".py", ".go", ".dart")


# --- self-test (fixtures only; never touches the real tree) -----------------

def _self_test() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "backend"
        root.mkdir(parents=True)

        def _violations(source: str) -> list[str]:
            f = root / "fixture_tour.py"
            f.write_text(source, encoding="utf-8")
            out = scan_file(f)
            f.unlink()
            return out

        # 1) The exact registered false-positive shape, now marked:
        #    marker line must pass.
        marked = (
            'probe = self.client.get(path, token="tour-route-probe-invalid")'
            "  # guard-bi-allow: deliberate 404 route probe, not a secret\n"
        )
        if _violations(marked):
            failures.append(f"allow-marked probe line should pass: {_violations(marked)}")

        # 2) Marker-less twin of the same line must STILL be caught
        #    (allow is per-line, never blanket).
        bare = 'probe = self.client.get(path, token="tour-route-probe-invalid")\n'
        v = _violations(bare)
        if len(v) != 1 or "hardcoded 'token' assignment" not in v[0]:
            failures.append(f"marker-less twin should still violate: {v}")

        # 3) A different secret on a non-marked line in the same file is caught
        #    even when another line carries the marker.
        mixed = (
            'ok = client.get(path, token="tour-route-probe-invalid")'
            "  # guard-bi-allow: route probe\n"
            'password = "hunter2hunter2!"\n'
        )
        v = _violations(mixed)
        if len(v) != 1 or ":2:" not in v[0]:
            failures.append(f"unmarked sibling violation must be caught: {v}")

        # 4) Direct credential patterns are also exempted by the marker.
        marked_key = 'cfg = {"k": "sk-proj-abcdefghijklmnopqrstuvwx"}  # guard-bi-allow: fixture pattern\n'
        if _violations(marked_key):
            failures.append(f"allow-marked direct-pattern line should pass: {_violations(marked_key)}")

        bare_key = 'cfg = {"k": "sk-proj-abcdefghijklmnopqrstuvwx"}\n'
        v = _violations(bare_key)
        if len(v) != 1 or "OpenAI API key" not in v[0]:
            failures.append(f"marker-less direct pattern should still violate: {v}")

    if failures:
        print("[bi-hardcoded-secrets] SELF-TEST FAIL")
        for f in failures:
            print(f"  {f}")
        return 1
    print(
        "[bi-hardcoded-secrets] SELF-TEST PASS "
        "(guard-bi-allow marker exempts its own line only; marker-less twins "
        "and unmarked siblings still caught, direct patterns covered)"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run fixture self-test in a temp dir")
    args = parser.parse_args()

    if args.self_test:
        return _self_test()

    all_violations: list[str] = []

    backend = REPO_ROOT / "backend"
    if backend.exists():
        for py_file in backend.rglob("*.py"):
            if _should_skip(py_file):
                continue
            all_violations.extend(scan_file(py_file))

    gateway = REPO_ROOT / "backend" / "gateway"
    if gateway.exists():
        for go_file in gateway.rglob("*.go"):
            if _should_skip(go_file):
                continue
            all_violations.extend(scan_file(go_file))

    mobile = REPO_ROOT / "mobile"
    if mobile.exists():
        for dart_file in mobile.rglob("*.dart"):
            if _should_skip(dart_file):
                continue
            all_violations.extend(scan_file(dart_file))

    if all_violations:
        print("Rule BI: hardcoded secrets detected:")
        for v in all_violations:
            print(f"  - {v}")
        return 1

    print("Rule BI: hardcoded secrets scan — PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
