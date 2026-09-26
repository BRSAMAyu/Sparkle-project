#!/usr/bin/env python3
"""CARD-DUAL-WRITE guard: card protocol dual-write consistency (V3-FIX-274).

History: this rule shipped active in the initial commit but was disabled in
976061ab — the ``app.services.card_protocol.consistency_validator`` module it
imports had never been committed (v1 untracked leftover), so the rule could
not run. V3-FIX-274补齐该模块并复活本守卫。

Two modes:

- self-test mode (default guard environment, in-memory SQLite per
  ``run_all_rule_guards.sh``): the guard builds its own StaticPool in-memory
  engine, creates the schema, seeds deterministic fixtures covering every
  issue code, and asserts the validator reports exactly those issues — no
  more, no less. Exact-multiset matching proves both directions at once:
  every seeded defect is caught, and the consistent fixture rows produce no
  false positives.
- live mode (real ``DATABASE_URL`` / ``GUARD_DATABASE_URL``): validates real
  legacy Plan/Task rows against Card Protocol projections; exits 1 on any
  critical issue. ``--limit`` restricts per-row checks to recent rows.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.db.session import AsyncSessionLocal, engine  # noqa: E402
from app.services.card_protocol.consistency_validator import (  # noqa: E402
    CRITICAL,
    WARNING,
    CardProtocolConsistencyValidator,
    ConsistencyIssue,
)

EXPECTED_SELF_TEST_ISSUES: dict[str, str] = {
    "MISSING_PLAN_PROJECTION": CRITICAL,
    "DUPLICATE_PLAN_PROJECTION": CRITICAL,
    "PLAN_LIFECYCLE_DRIFT": CRITICAL,
    "TASK_LIFECYCLE_DRIFT": CRITICAL,
    "ORPHAN_PLAN_CARD": WARNING,
}


def _engine_is_in_memory_sqlite() -> bool:
    url = engine.url
    if not url.drivername.startswith("sqlite"):
        return False
    database = url.database
    return database in (None, "", ":memory:") or ":memory:" in str(url)


async def _self_test() -> tuple[bool, list[ConsistencyIssue]]:
    """Seed known-good/known-bad fixtures and assert exact validator output."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import StaticPool

    # Full model registry: partial registration breaks create_all's FK
    # topological sort (models reference tables from sibling modules).
    # app.models misses theater_candidate_bundle (conftest imports it
    # separately), so mirror that here.
    import app.models  # noqa: F401
    import app.models.theater_candidate_bundle  # noqa: F401
    from app.db.session import Base
    from app.models.card_protocol import Card, CardLifecycleStatus, CardType
    from app.models.plan import Plan, PlanType
    from app.models.task import Task, TaskStatus, TaskType
    from app.models.user import User

    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as db:
        user = User(username="cardguard", email="cardguard@example.invalid", hashed_password="x")
        db.add(user)
        await db.flush()

        # Consistent pair: legacy rows whose projections match the adapter mapping.
        plan_ok = Plan(user_id=user.id, name="guard-plan-ok", type=PlanType.GROWTH, progress=0.5)
        task_ok = Task(
            user_id=user.id,
            title="guard-task-ok",
            type=TaskType.LEARNING,
            estimated_minutes=30,
            status=TaskStatus.PENDING,
        )
        # Drifted plan: legacy row is inactive → adapter mapping expects ARCHIVED.
        plan_drift = Plan(user_id=user.id, name="guard-plan-drift", type=PlanType.GROWTH, is_active=False)
        # Missing projection: live plan with no card at all.
        plan_missing = Plan(user_id=user.id, name="guard-plan-missing", type=PlanType.GROWTH)
        # Duplicate: two cards claim the same legacy plan id.
        plan_dup = Plan(user_id=user.id, name="guard-plan-dup", type=PlanType.GROWTH)
        # Drifted task: COMPLETED maps to COMPLETED, card stays ACTIVE.
        task_drift = Task(
            user_id=user.id,
            title="guard-task-drift",
            type=TaskType.LEARNING,
            estimated_minutes=30,
            status=TaskStatus.COMPLETED,
        )
        db.add_all([plan_ok, task_ok, plan_drift, plan_missing, plan_dup, task_drift])
        await db.flush()

        def plan_card(plan: Plan, lifecycle: CardLifecycleStatus) -> Card:
            # NB: the column attribute is ``metadata_``; ``metadata=`` is the
            # declarative MetaData attribute and is silently ignored as a
            # constructor kwarg (the adapters go through CardService).
            return Card(
                card_type=CardType.PLAN,
                owner_id=user.id,
                holder_id=user.id,
                lifecycle_status=lifecycle,
                metadata_={"legacy_plan_id": str(plan.id), "name": plan.name},
            )

        orphan_plan_id = str(uuid.uuid4())
        task_card = Card(
            card_type=CardType.TASK,
            owner_id=user.id,
            holder_id=user.id,
            lifecycle_status=CardLifecycleStatus.ACTIVE,
            metadata_={"legacy_task_id": str(task_ok.id)},
        )
        drift_task_card = Card(
            card_type=CardType.TASK,
            owner_id=user.id,
            holder_id=user.id,
            lifecycle_status=CardLifecycleStatus.ACTIVE,
            metadata_={"legacy_task_id": str(task_drift.id)},
        )
        orphan_card = Card(
            card_type=CardType.PLAN,
            owner_id=user.id,
            holder_id=user.id,
            lifecycle_status=CardLifecycleStatus.ACTIVE,
            metadata_={"legacy_plan_id": orphan_plan_id},
        )
        db.add_all(
            [
                plan_card(plan_ok, CardLifecycleStatus.ACTIVE),
                plan_card(plan_drift, CardLifecycleStatus.ACTIVE),  # drift: expected ARCHIVED
                plan_card(plan_dup, CardLifecycleStatus.ACTIVE),
                plan_card(plan_dup, CardLifecycleStatus.ACTIVE),  # duplicate
                task_card,
                drift_task_card,
                orphan_card,
            ]
        )
        await db.commit()

        issues = await CardProtocolConsistencyValidator(db).validate()

    await test_engine.dispose()

    found_codes = Counter(issue.code for issue in issues)
    # NB: Counter(dict) would copy the dict VALUES (severities) as counts;
    # count the keys instead.
    expected_codes = Counter(EXPECTED_SELF_TEST_ISSUES.keys())
    if found_codes != expected_codes:
        return False, issues

    severity_ok = all(
        issue.severity == EXPECTED_SELF_TEST_ISSUES[issue.code]
        for issue in issues
        if issue.code in EXPECTED_SELF_TEST_ISSUES
    )
    return severity_ok, issues


async def _run_live(limit: int | None, output_json: bool) -> int:
    async with AsyncSessionLocal() as db:
        issues = await CardProtocolConsistencyValidator(db).validate(limit=limit)

    critical_count = sum(1 for issue in issues if issue.severity == CRITICAL)
    warning_count = sum(1 for issue in issues if issue.severity == WARNING)
    if output_json:
        print(
            json.dumps(
                {
                    "ok": critical_count == 0,
                    "critical_count": critical_count,
                    "warning_count": warning_count,
                    "issues": [issue.to_dict() for issue in issues],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print("Card Protocol dual-write consistency: " f"{critical_count} critical, {warning_count} warning")
        for issue in issues:
            print(
                f"[{issue.severity.upper()}] {issue.code} " f"{issue.entity_type}:{issue.entity_id} — {issue.message}"
            )
    return 1 if critical_count else 0


async def _run(limit: int | None, output_json: bool) -> int:
    if _engine_is_in_memory_sqlite():
        ok, issues = await _self_test()
        codes = sorted(issue.code for issue in issues)
        if ok:
            print(
                "[Rule CARD-DUAL-WRITE] PASS - self-test: validator caught all "
                f"{len(issues)} seeded defects with expected severities {codes}"
            )
            return 0
        print("[Rule CARD-DUAL-WRITE] FAIL - self-test mismatch")
        print(f"  expected codes: {sorted(EXPECTED_SELF_TEST_ISSUES)}")
        print(f"  actual codes:   {codes}")
        for issue in issues:
            print(
                f"  [{issue.severity.upper()}] {issue.code} " f"{issue.entity_type}:{issue.entity_id} — {issue.message}"
            )
        return 1
    return await _run_live(limit, output_json)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate legacy Plan/Task rows against Card Protocol projections.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit recent legacy plans/tasks checked.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text (live mode).")
    args = parser.parse_args()
    return asyncio.run(_run(args.limit, args.json))


if __name__ == "__main__":
    raise SystemExit(main())
