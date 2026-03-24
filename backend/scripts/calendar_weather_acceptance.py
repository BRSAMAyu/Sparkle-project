import json
from datetime import UTC, datetime, timedelta

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
        timeout=60,
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

    dashboard = _request("GET", "/dashboard/status", token=token).json()
    weather = dashboard["weather"]
    flame = dashboard["flame"]
    sprint = dashboard.get("sprint")
    growth = dashboard.get("growth")
    next_actions = dashboard["next_actions"]
    cognitive = dashboard["cognitive"]

    assert weather["type"] in {"sunny", "cloudy", "rainy", "meteor"}
    assert isinstance(weather["condition"], str) and weather["condition"]
    assert "level" in flame and "brightness" in flame and "today_focus_minutes" in flame
    assert isinstance(next_actions, list)
    assert "status" in cognitive

    link_task_id = next_actions[0]["id"] if next_actions else None
    link_plan_id = (sprint or growth or {}).get("id")

    start_time = (datetime.now(UTC) + timedelta(hours=2)).replace(microsecond=0).isoformat()
    end_time = (datetime.now(UTC) + timedelta(hours=3)).replace(microsecond=0).isoformat()

    created = _request(
        "POST",
        "/calendar",
        token=token,
        expected_status=201,
        json={
            "title": "日历天气全链路验收",
            "description": "验证 calendar 与 dashboard/weather 联动",
            "start_time": start_time,
            "end_time": end_time,
            "location": "Sparkle Acceptance Lab",
            "color": "#00BCD4",
            "reminder_minutes": [15],
            "source": "ai",
            "source_metadata": {"from": "calendar_weather_acceptance"},
            "task_id": link_task_id,
            "plan_id": link_plan_id,
        },
    ).json()

    event_id = created["id"]
    fetched = _request("GET", f"/calendar/{event_id}", token=token).json()
    listed = _request("GET", "/calendar?include_deleted=true&page=1&page_size=100", token=token).json()
    summary = _request("GET", "/calendar/summary", token=token).json()
    suggested = _request(
        "POST",
        "/calendar/suggest-time",
        token=token,
        json={
            "estimated_minutes": 60,
            "energy_cost": 3,
            "difficulty": 3,
            "preferred_date": datetime.now(UTC).date().isoformat(),
        },
    ).json()

    updated = _request(
        "PUT",
        f"/calendar/{event_id}",
        token=token,
        json={
            "title": "日历天气全链路验收-更新",
            "location": "Sparkle Acceptance Lab 2",
        },
    ).json()

    batch = _request(
        "POST",
        "/calendar/batch",
        token=token,
        json={
            "operations": [
                {
                    "action": "create",
                    "data": {
                        "title": "批量日程验收",
                        "start_time": (datetime.now(UTC) + timedelta(hours=4)).replace(microsecond=0).isoformat(),
                        "end_time": (datetime.now(UTC) + timedelta(hours=5)).replace(microsecond=0).isoformat(),
                        "source": "manual",
                    },
                }
            ]
        },
    ).json()

    delete_result = _request("DELETE", f"/calendar/{event_id}", token=token).json()
    restored = _request("POST", f"/calendar/{event_id}/restore", token=token).json()

    assert fetched["id"] == event_id
    assert fetched["task_id"] == link_task_id
    assert fetched["plan_id"] == link_plan_id
    assert any(item["id"] == event_id for item in listed["data"])
    assert summary["total"] >= 1
    assert len(suggested["suggestions"]) >= 1
    assert updated["title"] == "日历天气全链路验收-更新"
    assert updated["location"] == "Sparkle Acceptance Lab 2"
    assert batch["success_count"] == 1
    assert delete_result["success"] is True
    assert restored["success"] is True

    result = {
        "weather_type": weather["type"],
        "weather_condition": weather["condition"],
        "next_action_count": len(next_actions),
        "linked_task_id": link_task_id,
        "linked_plan_id": link_plan_id,
        "calendar_total": summary["total"],
        "suggestion_count": len(suggested["suggestions"]),
        "batch_success_count": batch["success_count"],
        "restored_event_id": restored["data"]["id"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("ALL_OK")


if __name__ == "__main__":
    main()
