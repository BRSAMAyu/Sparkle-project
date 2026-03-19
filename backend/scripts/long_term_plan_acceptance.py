import json
from datetime import date, timedelta

import requests


BASE_URL = "http://127.0.0.1:8000/api/v1"
USERNAME = "chat_test"
PASSWORD = "Chat123456"


def _request(
    method: str,
    path: str,
    *,
    token: str | None = None,
    expected_status: int = 200,
    **kwargs,
):
    headers = kwargs.pop("headers", {})
    if token:
        headers = {"Authorization": f"Bearer {token}", **headers}
    response = requests.request(
        method,
        f"{BASE_URL}{path}",
        headers=headers,
        timeout=90,
        **kwargs,
    )
    if response.status_code != expected_status:
        raise RuntimeError(
            f"{method} {path} expected {expected_status}, got {response.status_code}: {response.text[:500]}"
        )
    return response


def _login() -> str:
    response = _request(
        "POST",
        "/auth/login",
        json={"username": USERNAME, "password": PASSWORD},
    )
    return response.json()["access_token"]


def main() -> None:
    token = _login()

    list_all = _request("GET", "/plans", token=token).json()
    growth_before = _request("GET", "/plans?type=growth&is_active=true", token=token).json()
    quota = _request("GET", "/plans/quota/status", token=token).json()
    primary = _request("GET", "/plans/primary", token=token).json()

    created = _request(
        "POST",
        "/plans",
        token=token,
        expected_status=201,
        json={
            "name": "长期计划验收",
            "type": "growth",
            "description": "验证长期计划全链路可用性",
            "subject": "系统设计",
            "target_date": (date.today() + timedelta(days=120)).isoformat(),
            "daily_available_minutes": 45,
            "total_estimated_hours": 48,
            "priority": "high",
            "plan_stage": "daily",
        },
    ).json()
    plan_id = created["id"]

    updated = _request(
        "PUT",
        f"/plans/{plan_id}",
        token=token,
        json={
            "name": "长期计划验收-更新",
            "plan_stage": "review",
            "daily_available_minutes": 50,
        },
    ).json()

    generated_tasks = _request(
        "POST",
        f"/plans/{plan_id}/generate-tasks?count=2",
        token=token,
    ).json()

    detail = _request("GET", f"/plans/{plan_id}", token=token).json()
    progress = _request("GET", f"/plans/{plan_id}/progress", token=token).json()
    archived = _request("POST", f"/plans/{plan_id}/archive", token=token).json()
    archived_list = _request("GET", "/plans/archived", token=token).json()
    restored = _request("POST", f"/plans/{plan_id}/restore", token=token).json()
    detail_after_restore = _request("GET", f"/plans/{plan_id}", token=token).json()
    growth_after = _request("GET", "/plans?type=growth&is_active=true", token=token).json()

    assert list_all["total"] >= 1
    assert growth_before["total"] >= 1
    assert "used" in quota and "limit" in quota
    assert "plan" in primary

    assert created["type"] == "growth"
    assert updated["plan_stage"] == "review"
    assert updated["daily_available_minutes"] == 50

    assert len(generated_tasks) >= 1
    assert detail["task_count"] >= len(generated_tasks)
    assert detail["tasks"] is not None
    assert len(detail["tasks"]) >= len(generated_tasks)
    assert detail["tasks"][0]["plan_id"] == plan_id
    assert progress["total_tasks"] >= len(generated_tasks)

    assert archived["status"] == "archived"
    assert any(item["id"] == plan_id for item in archived_list["data"])

    assert restored["status"] == "active"
    assert detail_after_restore["is_active"] is True
    assert growth_after["total"] >= growth_before["total"]

    result = {
        "growth_before_total": growth_before["total"],
        "growth_after_total": growth_after["total"],
        "quota_used": quota["used"],
        "primary_plan_id": (primary.get("plan") or {}).get("id"),
        "generated_task_count": len(generated_tasks),
        "detail_task_count": detail["task_count"],
        "archived_total": archived_list["total"],
        "restored_plan_id": plan_id,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("ALL_OK")


if __name__ == "__main__":
    main()
