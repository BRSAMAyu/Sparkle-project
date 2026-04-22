#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RATE_LIMITER = REPO_ROOT / "backend/gateway/internal/middleware/distributed_rate_limiter.go"
RATE_LIMITER_TEST = REPO_ROOT / "backend/gateway/internal/middleware/distributed_rate_limiter_test.go"


def scan_rule_aw() -> list[str]:
    violations: list[str] = []
    source = RATE_LIMITER.read_text(encoding="utf-8")
    tests = RATE_LIMITER_TEST.read_text(encoding="utf-8")

    required_source_tokens = (
        "elapsed_unit=ms",
        "rate_unit=tokens/s",
        "tokens_added = (elapsed_ms / 1000.0) * (rate_per_s)",
        "rate_limiter_tokens_current",
        "rate_limiter_rejections_total",
    )
    for token in required_source_tokens:
        if token not in source:
            violations.append(f"AW001 missing token `{token}` in {RATE_LIMITER}")

    if "TestRateLimiter_DimensionalCorrectness" not in tests:
        violations.append(
            f"AW002 missing TestRateLimiter_DimensionalCorrectness in {RATE_LIMITER_TEST}"
        )

    return violations


def main() -> int:
    violations = scan_rule_aw()
    if violations:
        print("[Rule AW] FAIL")
        for violation in violations:
            print(violation)
        return 1
    print("[Rule AW] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
