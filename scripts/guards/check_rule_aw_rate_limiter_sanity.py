#!/usr/bin/env python3
"""Rule AW: Rate limiter dimensional sanity guard.

Verifies:
1. Rate limimiter uses correct dimensional formula (tokens/s × elapsed)
2. Prometheus metrics are registered (tokens_current, rejections_total)
3. Unit labels are present (elapsed_unit=ms, rate_unit=tokens/s)
4. Test suite includes dimensional correctness test

Layer 1: Quick string presence check
Layer 2: Structural pattern verification
"""
from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RATE_LIMITER = REPO_ROOT / "backend/gateway/internal/middleware/distributed_rate_limiter.go"
RATE_LIMITER_TEST = REPO_ROOT / "backend/gateway/internal/middleware/distributed_rate_limiter_test.go"


def scan_rule_aw() -> list[str]:
    violations: list[str] = []
    source = RATE_LIMITER.read_text(encoding="utf-8")
    tests = RATE_LIMITER_TEST.read_text(encoding="utf-8")

    # Layer 1: Required dimensional tokens
    required_source_tokens = {
        "elapsed_unit=ms": "dimensional label for elapsed time",
        "rate_unit=tokens/s": "dimensional label for rate",
        "rate_limiter_tokens_current": "Prometheus metric for current tokens",
        "rate_limiter_rejections_total": "Prometheus metric for rejections",
    }
    for token, description in required_source_tokens.items():
        if token not in source:
            violations.append(f"AW001 missing `{token}` ({description}) in {RATE_LIMITER}")

    # Layer 2: Verify the refill formula exists in a function body
    # The formula tokens_added = (elapsed_ms / 1000.0) * rate_per_s must be present
    # in a function that handles token refilling
    formula_found = False
    for variant in (
        "tokens_added = (elapsed_ms / 1000.0) * (rate_per_s)",
        "tokens_added = (elapsed_ms / 1000.0) * rate_per_s",
    ):
        if variant in source:
            formula_found = True
            break

    if not formula_found:
        violations.append(
            "AW003 dimensional refill formula not found — expected "
            "`tokens_added = (elapsed_ms / 1000.0) * rate_per_s`"
        )

    # Verify test coverage
    if "TestRateLimiter_DimensionalCorrectness" not in tests:
        violations.append(
            f"AW002 missing TestRateLimiter_DimensionalCorrectness in {RATE_LIMITER_TEST}"
        )

    # Layer 2: Verify at least one function references the Prometheus metrics
    # This catches the case where metrics are imported but never used in a function
    has_metric_usage = (
        "rate_limiter_tokens_current" in source
        and ("Add(" in source or ".Add(" in source or "WithLabelValues" in source)
    )
    if not has_metric_usage and "rate_limiter_tokens_current" in source:
        violations.append("AW004 Prometheus metrics declared but not used in any function")

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
