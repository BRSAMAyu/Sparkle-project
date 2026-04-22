#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PHOTON_SERVICE = REPO_ROOT / "backend/app/services/photon_service.py"
DEFAULT_ACHIEVEMENT_ENGINE = REPO_ROOT / "backend/app/services/achievement_engine.py"


def scan_rule_bb(
    *,
    photon_service: Path = DEFAULT_PHOTON_SERVICE,
    achievement_engine: Path = DEFAULT_ACHIEVEMENT_ENGINE,
) -> list[str]:
    violations: list[str] = []
    photon_source = photon_service.read_text(encoding="utf-8")
    achievement_source = achievement_engine.read_text(encoding="utf-8")

    photon_required = (
        "_deduct_balance_atomically",
        "update(User)",
        "photon_balance=User.photon_balance - amount",
        "update_stmt.where(User.photon_balance >= amount)",
        "update_stmt.returning(User.photon_balance)",
    )
    for token in photon_required:
        if token not in photon_source:
            violations.append(f"BB001 missing token `{token}` in {photon_service}")

    achievement_required = (
        "_EXTERNAL_TRANSACTION_MANAGED_KEY",
        "begin_nested",
        "grant_photons",
    )
    for token in achievement_required:
        if token not in achievement_source:
            violations.append(f"BB002 missing token `{token}` in {achievement_engine}")

    return violations


def main() -> int:
    violations = scan_rule_bb()
    if violations:
        print("[Rule BB] FAIL")
        for violation in violations:
            print(violation)
        return 1
    print("[Rule BB] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
