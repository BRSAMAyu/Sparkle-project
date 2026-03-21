#!/usr/bin/env python3
"""Stage 3 Celery acceptance coverage."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx
from celery.result import AsyncResult

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _derive_redis_db(url: str, db: int) -> str:
    parsed = urlparse(url)
    path = f"/{db}"
    return urlunparse(parsed._replace(path=path))


_host_redis = os.getenv("REDIS_URL", "redis://:change-me@127.0.0.1:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", _derive_redis_db(_host_redis, 1))
os.environ.setdefault("CELERY_RESULT_BACKEND", _derive_redis_db(_host_redis, 2))

from app.core.celery_app import celery_app
from app.core.security import create_access_token, get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.background_task import BackgroundTask, BackgroundTaskStatus, BackgroundTaskType
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.services.decay_service import DecayService
from app.services.nightly_review_service import NightlyReviewService
from scripts._acceptance_common import BASE_URL, REQUEST_TIMEOUT_SECONDS, assert_status, ensure


ROOT = Path(__file__).resolve().parents[2]
PASSWORD = os.getenv("LOCAL_SMOKE_PASSWORD", "Chat123456")


def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


def _username(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _run(cmd: str, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        shell=True,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=check,
    )


async def _create_user(prefix: str) -> dict[str, str]:
    async with AsyncSessionLocal() as db:
        username = _username(prefix)
        user = User(
            username=username,
            email=_email(prefix),
            hashed_password=get_password_hash(PASSWORD),
            password_login_enabled=True,
            nickname=username,
            registration_source="email",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return {
            "id": str(user.id),
            "username": username,
            "token": create_access_token({"sub": str(user.id)}),
        }


async def _seed_background_task(user_id: str) -> str:
    async with AsyncSessionLocal() as db:
        item = BackgroundTask(
            user_id=uuid.UUID(user_id),
            task_type=BackgroundTaskType.DATA_SYNC,
            name="celery acceptance seeded task",
            status=BackgroundTaskStatus.PENDING,
            progress=0.25,
            progress_message="queued",
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return str(item.id)


async def _seed_error_record(user_id: str) -> None:
    async with AsyncSessionLocal() as db:
        item = ErrorRecord(
            user_id=uuid.UUID(user_id),
            subject_code="math",
            question_text="1+1=?",
            user_answer="3",
            correct_answer="2",
            chapter="acceptance",
        )
        db.add(item)
        await db.commit()


async def _generate_nightly_review(user_id: str) -> dict[str, Any]:
    async with AsyncSessionLocal() as db:
        service = NightlyReviewService(db)
        review = await service.generate_for_user(
            user_id=uuid.UUID(user_id),
            timezone_name="Asia/Shanghai",
            review_date=(datetime.now(timezone.utc).date() - timedelta(days=1)),
        )
        return {"id": str(review.id), "summary": review.summary_text}


async def _seed_decay_node(user_id: str) -> dict[str, Any]:
    async with AsyncSessionLocal() as db:
        node = KnowledgeNode(
            name=f"decay-node-{uuid.uuid4().hex[:6]}",
            description="celery acceptance decay node",
            source_type="acceptance",
            is_seed=False,
        )
        db.add(node)
        await db.flush()

        status = UserNodeStatus(
            user_id=uuid.UUID(user_id),
            node_id=node.id,
            mastery_score=80.0,
            is_unlocked=True,
            total_minutes=60,
            total_study_minutes=60,
            last_study_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=10),
            next_review_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=2),
        )
        db.add(status)
        await db.commit()
        return {"node_id": str(node.id), "mastery_before": status.mastery_score}


async def _run_decay(user_id: str, node_id: str) -> float:
    async with AsyncSessionLocal() as db:
        service = DecayService(db)
        await service.apply_daily_decay()
        refreshed = await db.get(
            UserNodeStatus,
            {"user_id": uuid.UUID(user_id), "node_id": uuid.UUID(node_id)},
        )
        ensure(refreshed is not None, "CEL-10 failed: node status missing after decay")
        return float(refreshed.mastery_score)


async def _seed_completed_task(user_id: str) -> None:
    async with AsyncSessionLocal() as db:
        task = Task(
            user_id=uuid.UUID(user_id),
            title=f"celery-stats-{uuid.uuid4().hex[:6]}",
            type=TaskType.PLANNING,
            status=TaskStatus.COMPLETED,
            estimated_minutes=30,
            actual_minutes=30,
            completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(task)
        await db.commit()


def _poll_celery(task_id: str, *, timeout_seconds: int = 25) -> list[str]:
    deadline = time.monotonic() + timeout_seconds
    seen: list[str] = []
    while time.monotonic() < deadline:
        state = AsyncResult(task_id, app=celery_app).state
        if not seen or seen[-1] != state:
            seen.append(state)
        if state in {"SUCCESS", "FAILURE"}:
            return seen
        time.sleep(0.4)
    raise RuntimeError(f"Celery task {task_id} did not finish in time; seen={seen}")


async def main() -> int:
    summary: dict[str, Any] = {}

    celery_status = _run("make celery-status")
    ensure("celery_worker" in celery_status.stdout or "sparkle-project-celery_worker-1" in celery_status.stdout, "CEL-01 failed: default celery worker missing")
    ensure("glm_batch" in celery_status.stdout or "sparkle-project-celery_glm_batch_worker-1" in celery_status.stdout, "CEL-03 failed: glm batch worker missing")
    summary["CEL-01"] = "PASS"
    summary["CEL-03"] = "PASS"

    beat_logs = _run("docker logs --tail=200 sparkle_celery_beat", check=False)
    beat_text = f"{beat_logs.stdout}\n{beat_logs.stderr}"
    ensure("Scheduler" in beat_text or "beat:" in beat_text or "Sending due task" in beat_text, "CEL-02 failed: beat logs do not show scheduler activity")
    summary["CEL-02"] = "PASS"

    probe = celery_app.send_task("acceptance.sleep_probe_task", kwargs={"seconds": 2.2}, queue="default")
    probe_states = _poll_celery(probe.id)
    ensure(probe_states[0] in {"PENDING", "RECEIVED"} or "PENDING" in probe_states, f"CEL-04 failed: missing pending state {probe_states}")
    ensure("STARTED" in probe_states or probe_states[-1] == "SUCCESS", f"CEL-04 failed: missing started/success progression {probe_states}")
    ensure(probe_states[-1] == "SUCCESS", f"CEL-04 failed: final state not success {probe_states}")
    summary["CEL-04"] = {"result": "PASS", "states": probe_states}

    fail_probe = celery_app.send_task("acceptance.fail_probe_task", queue="default")
    fail_states = _poll_celery(fail_probe.id)
    ensure("RETRY" in fail_states or fail_states.count("PENDING") > 1, f"CEL-05 failed: retry state not observed {fail_states}")
    ensure(fail_states[-1] == "FAILURE", f"CEL-05 failed: final state not failure {fail_states}")
    summary["CEL-05"] = {"result": "PASS", "states": fail_states}

    user = await _create_user("celery_user")
    headers = {"Authorization": f"Bearer {user['token']}"}
    background_task_id = await _seed_background_task(user["id"])

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS, follow_redirects=True) as client:
        background_tasks = await client.get(f"{BASE_URL}/background-tasks/", headers=headers)
        assert_status(background_tasks, 200, "background tasks")
        data = background_tasks.json()
        ensure(any(item.get("id") == background_task_id for item in data.get("data") or []), f"CEL-06 failed: seeded task missing {data}")
        summary["CEL-06"] = "PASS"

        await _seed_error_record(user["id"])
        review = await _generate_nightly_review(user["id"])
        latest_review = await client.get(f"{BASE_URL}/reviews/nightly/latest", headers=headers)
        assert_status(latest_review, 200, "nightly review latest")
        review_payload = latest_review.json()
        ensure(review_payload.get("summary_text"), f"CEL-09 failed: nightly review summary empty {review_payload}")
        summary["CEL-09"] = {
            "result": "PASS",
            "review_id": review["id"],
            "summary_preview": str(review_payload.get("summary_text"))[:120],
        }

        decay_seed = await _seed_decay_node(user["id"])
        mastery_after = await _run_decay(user["id"], decay_seed["node_id"])
        ensure(mastery_after < float(decay_seed["mastery_before"]), f"CEL-10 failed: mastery did not decay {decay_seed['mastery_before']} -> {mastery_after}")
        summary["CEL-10"] = {
            "result": "PASS",
            "mastery_before": float(decay_seed["mastery_before"]),
            "mastery_after": mastery_after,
        }

        before_report = celery_app.send_task("daily_report", queue="default")
        _poll_celery(before_report.id)
        before_result = AsyncResult(before_report.id, app=celery_app).get(timeout=10)

        await _seed_completed_task(user["id"])

        after_report = celery_app.send_task("daily_report", queue="default")
        _poll_celery(after_report.id)
        after_result = AsyncResult(after_report.id, app=celery_app).get(timeout=10)

        weekly_stats = await client.get(f"{BASE_URL}/stats/weekly", headers=headers)
        assert_status(weekly_stats, 200, "stats weekly")
        weekly_payload = weekly_stats.json()
        ensure(int(weekly_payload.get("tasks_completed") or 0) >= 1, f"CEL-11 failed: weekly stats not updated {weekly_payload}")
        ensure(int(after_result.get("tasks_completed_today") or 0) >= int(before_result.get("tasks_completed_today") or 0), f"CEL-11 failed: daily report did not reflect stats growth {before_result} -> {after_result}")
        summary["CEL-11"] = {
            "result": "PASS",
            "before_report": before_result,
            "after_report": after_result,
            "weekly_stats": weekly_payload,
        }

    _run("make celery-flush")
    post_flush_probe = celery_app.send_task("acceptance.sleep_probe_task", kwargs={"seconds": 1.2}, queue="default")
    post_flush_states = _poll_celery(post_flush_probe.id)
    ensure(post_flush_states[-1] == "SUCCESS", f"CEL-08 failed after flush: {post_flush_states}")
    summary["CEL-08"] = {"result": "PASS", "states": post_flush_states}

    print("ALL_OK")
    print(json.dumps(summary, ensure_ascii=False, default=str, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
