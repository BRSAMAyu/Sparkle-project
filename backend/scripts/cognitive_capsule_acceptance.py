#!/usr/bin/env python3
"""Gateway-backed acceptance for cognitive prism, curiosity capsules, and profile surfaces."""

from __future__ import annotations

import json
import time
import uuid

import requests


AUTH_BASE_URL = "http://127.0.0.1:8000/api/v1"
BASE_URL = "http://127.0.0.1:8080/api/v1"
USERNAME = "chat_test"
PASSWORD = "Chat123456"
REQUEST_TIMEOUT_SECONDS = 180


def _request(method: str, path: str, *, token: str | None = None, expected_status: int = 200, **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers = {"Authorization": f"Bearer {token}", **headers}

    response = requests.request(
        method,
        f"{BASE_URL}{path}",
        headers=headers,
        timeout=REQUEST_TIMEOUT_SECONDS,
        **kwargs,
    )
    if response.status_code != expected_status:
        raise RuntimeError(
            f"{method} {path} expected {expected_status}, got {response.status_code}: {response.text[:800]}"
        )
    return response


def _login() -> str:
    response = requests.post(
        f"{AUTH_BASE_URL}/auth/login",
        json={"username": USERNAME, "password": PASSWORD},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code != 200:
        raise RuntimeError(f"POST /auth/login failed: {response.status_code} {response.text[:800]}")
    return response.json()["access_token"]


def _poll_until(predicate, *, timeout_seconds: int, interval_seconds: float = 1.0):
    deadline = time.monotonic() + timeout_seconds
    last_value = None
    while time.monotonic() < deadline:
        last_value = predicate()
        if last_value:
            return last_value
        time.sleep(interval_seconds)
    return last_value


def main() -> None:
    token = _login()

    baseline_dashboard = _request("GET", "/dashboard/status", token=token).json()
    baseline_context = _request("GET", "/profile/context", token=token).json()
    baseline_transparent = _request("GET", "/profile/transparent", token=token).json()
    baseline_inferred = _request("GET", "/profile/inferred-preferences", token=token).json()
    baseline_policies = _request("GET", "/profile/active-policies", token=token).json()
    baseline_updates = _request("GET", "/profile/system-updates", token=token).json()
    baseline_fragments = _request("GET", "/cognitive/fragments", token=token).json()
    baseline_patterns = _request("GET", "/cognitive/patterns", token=token).json()
    baseline_capsules = _request("GET", "/capsules/today", token=token).json()
    baseline_stats = _request("GET", "/capsules/stats", token=token).json()
    baseline_jobs = _request("GET", "/capsules/generation/jobs", token=token).json()
    groups = _request("GET", "/community/groups", token=token).json()

    target_group_id = groups[0]["id"] if groups else _request(
        "POST",
        "/community/groups",
        token=token,
        json={
            "name": "画像验收群",
            "description": "好奇心胶囊与认知棱镜验收群",
            "is_public": False,
            "max_members": 20,
            "tags": ["acceptance", "persona"],
        },
    ).json()["id"]

    source_event_id = f"acceptance-{uuid.uuid4().hex}"
    fragment_resp = _request(
        "POST",
        "/cognitive/fragments",
        token=token,
        json={
            "content": "我会因为担心做不好而反复拖延开始，直到最后一刻才动手。",
            "source_type": "behavior",
            "resource_type": "text",
            "context_tags": {"scene": "acceptance", "module": "cognitive_prism"},
            "error_tags": ["procrastination", "deadline_anxiety"],
            "severity": 4,
            "source_event_id": source_event_id,
        },
    ).json()
    fragment_id = fragment_resp["id"]

    update_item = _poll_until(
        lambda: next(
            (
                item
                for item in (_request("GET", "/profile/system-updates", token=token).json().get("items") or [])
                if item.get("type") == "cognitive_fragment_created"
                and item.get("metadata", {}).get("fragment_id") == fragment_id
            ),
            None,
        ),
        timeout_seconds=20,
    )
    if not update_item:
        raise RuntimeError("System updates did not record cognitive_fragment_created")

    fragments_after = _request("GET", "/cognitive/fragments", token=token).json()
    fragment_item = next((item for item in fragments_after if item["id"] == fragment_id), None)
    if not fragment_item:
        raise RuntimeError("Created cognitive fragment missing from /cognitive/fragments")

    transparent_after = _request("GET", "/profile/transparent", token=token).json()
    transparent_fragment = next(
        (item for item in transparent_after["layer_3"]["fragments"] if item["id"] == fragment_id),
        None,
    )
    if not transparent_fragment:
        raise RuntimeError("Created cognitive fragment missing from transparent profile layer_3")

    pattern_item = _poll_until(
        lambda: (_request("GET", "/cognitive/patterns", token=token).json() or [None])[0],
        timeout_seconds=30,
        interval_seconds=2,
    )
    if not pattern_item:
        raise RuntimeError("Created cognitive fragment did not yield a behavior pattern in /cognitive/patterns")

    context_after = _poll_until(
        lambda: _request("GET", "/profile/context", token=token).json(),
        timeout_seconds=10,
        interval_seconds=1,
    ) or {}
    active_patterns = (context_after.get("cognitive_summary") or {}).get("active_patterns") or []
    if not active_patterns:
        raise RuntimeError(f"Profile context did not expose active patterns: {json.dumps(context_after, ensure_ascii=False)}")

    dashboard_after = _poll_until(
        lambda: _request("GET", "/dashboard/status", token=token).json(),
        timeout_seconds=10,
        interval_seconds=1,
    ) or {}
    dashboard_cognitive = dashboard_after.get("cognitive") or {}
    if dashboard_cognitive.get("status") == "empty":
        raise RuntimeError(f"Dashboard cognitive summary remained empty: {json.dumps(dashboard_cognitive, ensure_ascii=False)}")

    generation_started = time.monotonic()
    batch_resp = _request(
        "POST",
        "/capsules/generate/batch",
        token=token,
        json={
            "depth_preference": 0.62,
            "curiosity_preference": 0.78,
            "requested_count": 1,
        },
    ).json()
    job_id = batch_resp.get("job_id")
    baseline_job_ids = {item["id"] for item in baseline_jobs}

    if job_id:
        jobs = _request("GET", "/capsules/generation/jobs", token=token).json()
        job = next((item for item in jobs if item["id"] == job_id), None)
    else:
        task_id = batch_resp.get("task_id")
        if not task_id:
            raise RuntimeError(f"Batch generation returned neither job_id nor task_id: {json.dumps(batch_resp, ensure_ascii=False)}")
        job = _poll_until(
            lambda: next(
                (
                    item
                    for item in _request("GET", "/capsules/generation/jobs", token=token).json()
                    if item["id"] not in baseline_job_ids
                ),
                None,
            ),
            timeout_seconds=120,
            interval_seconds=2,
        )
        if not job:
            raise RuntimeError(
                "Batch generation task was accepted but no new capsule generation job appeared"
            )

    if not job:
        raise RuntimeError("Generated capsule job missing from /capsules/generation/jobs")
    job_id = job["id"]
    if job.get("status") != "completed":
        job = _poll_until(
            lambda: next(
                (
                    item
                    for item in _request("GET", "/capsules/generation/jobs", token=token).json()
                    if item["id"] == job_id and item.get("status") == "completed"
                ),
                None,
            ),
            timeout_seconds=180,
            interval_seconds=2,
        )
    if not job:
        raise RuntimeError("Generated capsule job did not reach completed status")
    if not job:
        raise RuntimeError("Generated capsule job missing from /capsules/generation/jobs")
    if job.get("status") != "completed":
        raise RuntimeError(f"Generated capsule job not completed: {json.dumps(job, ensure_ascii=False)}")
    capsule_ids = job.get("capsule_ids") or []
    if not capsule_ids:
        raise RuntimeError(f"Generated capsule job returned no capsule_ids: {json.dumps(job, ensure_ascii=False)}")
    capsule_id = capsule_ids[0]

    favorite_before = baseline_stats["total_favorited"]
    favorite_resp = _request("POST", f"/capsules/{capsule_id}/favorite", token=token).json()
    if not favorite_resp.get("is_favorited"):
        raise RuntimeError(f"Newly generated capsule was not favorited: {json.dumps(favorite_resp, ensure_ascii=False)}")

    feedback_before = baseline_stats["total_feedback_given"]
    feedback_resp = _request(
        "POST",
        f"/capsules/{capsule_id}/feedback",
        token=token,
        json={
            "rating": 5,
            "helpful": True,
            "category": "too_short",
            "comment": "希望延展得更深入一些",
        },
    ).json()

    inferred_after = _poll_until(
        lambda: _request("GET", "/profile/inferred-preferences", token=token).json(),
        timeout_seconds=10,
    ) or []
    inferred_map = {item["key"]: item for item in inferred_after}
    if "depth_preference" not in inferred_map or "curiosity_preference" not in inferred_map:
        raise RuntimeError(f"Inferred preferences were not updated after feedback: {json.dumps(inferred_after, ensure_ascii=False)}")

    stats_after = _request("GET", "/capsules/stats", token=token).json()
    if stats_after["total_feedback_given"] < feedback_before + 1:
        raise RuntimeError(f"Capsule feedback stats did not increase: before={feedback_before}, after={stats_after}")
    if stats_after["total_favorited"] < favorite_before + 1:
        raise RuntimeError(f"Capsule favorite stats did not increase: before={favorite_before}, after={stats_after}")

    fragment_share = _request(
        "POST",
        "/community/share",
        token=token,
        json={
            "resource_type": "cognitive_fragment",
            "resource_id": fragment_id,
            "target_group_id": target_group_id,
            "permission": "view",
            "comment": "认知棱镜验收分享",
        },
    ).json()
    capsule_share = _request(
        "POST",
        "/community/share",
        token=token,
        json={
            "resource_type": "curiosity_capsule",
            "resource_id": capsule_id,
            "target_group_id": target_group_id,
            "permission": "view",
            "comment": "胶囊验收分享",
        },
    ).json()
    group_resources = _request("GET", f"/community/groups/{target_group_id}/resources", token=token).json()
    if not any(item.get("cognitive_fragment_id") == fragment_id for item in group_resources):
        raise RuntimeError("Shared cognitive fragment missing from group resources")
    if not any(item.get("curiosity_capsule_id") == capsule_id for item in group_resources):
        raise RuntimeError("Shared curiosity capsule missing from group resources")

    result = {
        "profile": {
            "dashboard_initial_status": (baseline_dashboard.get("cognitive") or {}).get("status"),
            "dashboard_final_status": dashboard_cognitive.get("status"),
            "context_ok": bool(baseline_context),
            "transparent_layer3_fragment_count": len(transparent_after["layer_3"]["fragments"]),
            "baseline_inferred_count": len(baseline_inferred),
            "active_policy_count": len(baseline_policies),
            "system_update_count": len((baseline_updates or {}).get("items") or []),
        },
        "cognitive": {
            "baseline_fragment_count": len(baseline_fragments),
            "baseline_pattern_count": len(baseline_patterns),
            "fragment_id": fragment_id,
            "analysis_status": fragment_item["analysis_status"],
            "system_update_type": update_item["type"],
            "pattern_id": pattern_item["id"],
            "pattern_name": pattern_item["pattern_name"],
            "active_pattern_count": len(active_patterns),
        },
        "capsules": {
            "baseline_today_count": len(baseline_capsules),
            "job_id": job_id,
            "generated_capsule_id": capsule_id,
            "generation_elapsed_seconds": round(time.monotonic() - generation_started, 2),
            "favorite_id_present": favorite_resp.get("favorite_id") is not None,
            "feedback_id": feedback_resp["id"],
        },
        "inferred_preferences": {
            "depth_preference": inferred_map["depth_preference"]["value"],
            "curiosity_preference": inferred_map["curiosity_preference"]["value"],
        },
        "stats": {
            "total_received": stats_after["total_received"],
            "total_favorited": stats_after["total_favorited"],
            "total_feedback_given": stats_after["total_feedback_given"],
        },
        "community": {
            "target_group_id": target_group_id,
            "fragment_share_id": fragment_share["id"],
            "capsule_share_id": capsule_share["id"],
            "resource_types": sorted({item["resource_type"] for item in group_resources}),
        },
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("ALL_OK")


if __name__ == "__main__":
    main()
