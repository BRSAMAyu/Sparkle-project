#!/usr/bin/env python3
"""CI guard: verify SECRET_KEY strength in config files.

Checks that .env files (excluding .env.example/.env.template) contain
SECRET_KEY values meeting minimum entropy requirements.
"""

import os
import re
import sys
import math
import string

MIN_ENTROPY_BITS = 80
MIN_LENGTH = 32
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    freq = {}
    for c in s:
        freq[c] = freq.get(c, 0) + 1
    length = len(s)
    return -sum((count / length) * math.log2(count / length) for count in freq.values())


def check_env_file(path: str) -> list[str]:
    findings = []
    try:
        with open(path) as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                match = re.match(r'^(SECRET_KEY|JWT_SECRET|INTERNAL_API_KEY)\s*=\s*["\']?(.+?)["\']?\s*$', line)
                if not match:
                    continue
                key_name = match.group(1)
                value = match.group(2)
                if value in ("change-me", "your-secret-key", "changeme", "secret", ""):
                    findings.append(f"{path}:{lineno}: {key_name} has placeholder value")
                    continue
                entropy = shannon_entropy(value) * len(value)
                if len(value) < MIN_LENGTH:
                    findings.append(f"{path}:{lineno}: {key_name} too short ({len(value)} chars, min {MIN_LENGTH})")
                if entropy < MIN_ENTROPY_BITS:
                    findings.append(f"{path}:{lineno}: {key_name} low entropy ({entropy:.0f} bits, min {MIN_ENTROPY_BITS})")
    except Exception as e:
        findings.append(f"{path}: error reading file: {e}")
    return findings


def main():
    findings = []
    skip_patterns = (".example", ".template", ".migration", ".sample")

    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__", ".venv", "venv")]
        for fname in files:
            if fname == ".env" or (fname.startswith(".env") and not fname.startswith(".env.")):
                path = os.path.join(root, fname)
                if any(p in fname for p in skip_patterns):
                    continue
                findings.extend(check_env_file(path))

    if findings:
        print("SECRET STRENGTH CHECK FAILED:")
        for f in findings:
            print(f"  {f}")
        sys.exit(1)
    else:
        print("SECRET STRENGTH CHECK PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
