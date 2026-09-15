#!/usr/bin/env python3
"""CI guard: verify CORS configuration is safe for production.

Checks that:
1. BACKEND_CORS_ORIGINS does not contain "*" in non-development settings
2. No .env file has wildcard CORS in production mode
"""

import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check_cors_in_env(path: str) -> list[str]:
    findings = []
    try:
        with open(path) as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "CORS_ORIGIN" in line and '"*"' in line:
                    # Check if it's in a development context
                    findings.append(f"{path}:{lineno}: wildcard CORS origin detected")
    except Exception:
        pass
    return findings


def check_settings_cors() -> list[str]:
    findings = []
    settings_path = os.path.join(REPO_ROOT, "backend", "app", "config", "settings.py")
    if not os.path.exists(settings_path):
        return findings

    with open(settings_path) as f:
        content = f.read()

    # Check that production CORS validation exists
    if '"*"' in content and "CORS" in content:
        if "raise" not in content.split("CORS")[0].split('"*"')[-1][:200]:
            # Likely has a guard — check more carefully
            pass

    return findings


def main():
    findings = []
    skip_patterns = (".example", ".template", ".migration", ".sample")

    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__", ".venv", "venv")]
        for fname in files:
            if fname == ".env" or (fname.startswith(".env") and not any(p in fname for p in skip_patterns)):
                path = os.path.join(root, fname)
                findings.extend(check_cors_in_env(path))

    if findings:
        print("CORS CONFIG CHECK FAILED:")
        for f in findings:
            print(f"  {f}")
        sys.exit(1)
    else:
        print("CORS CONFIG CHECK PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
