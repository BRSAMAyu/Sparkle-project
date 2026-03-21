#!/usr/bin/env python3
"""Acceptance coverage for focus sessions, stats, history, heatmap, and LLM helpers."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from _acceptance_common import BASE_URL, assert_status, auth_headers, create_client, ensure, login


def main() -> None:
    with create_client(timeout_seconds=90.0) as client:
        token = login(client)
        headers = auth_headers(token)

        baseline_stats = client.get(f"{BASE_URL}/focus/stats", headers=headers)
        assert_status(baseline_stats, 200, "focus stats")
        baseline_stats_data = baseline_stats.json()

        baseline_weekly = client.get(f"{BASE_URL}/focus/stats/weekly", headers=headers)
        assert_status(baseline_weekly, 200, "focus weekly stats")
        baseline_weekly_data = baseline_weekly.json()

        baseline_history = client.get(
            f"{BASE_URL}/focus/sessions/history",
            headers=headers,
            params={"limit": 100, "offset": 0},
        )
        assert_status(baseline_history, 200, "focus history")
        baseline_history_data = baseline_history.json()

        now = datetime.now(UTC)
        completed_payload = {
            "task_id": None,
            "start_time": (now - timedelta(minutes=25)).isoformat(),
            "end_time": now.isoformat(),
            "duration_minutes": 25,
            "focus_type": "pomodoro",
            "status": "completed",
        }
        completed = client.post(
            f"{BASE_URL}/focus/sessions",
            headers=headers,
            json=completed_payload,
        )
        assert_status(completed, 200, "log completed focus session")
        completed_data = completed.json()
        ensure(completed_data["success"] is True, f"focus completed payload invalid: {completed_data}")
        ensure(completed_data["rewards"]["flame_earned"] >= 0, f"focus rewards missing: {completed_data}")

        interrupted_end = now + timedelta(minutes=10)
        interrupted_payload = {
            "task_id": None,
            "start_time": (interrupted_end - timedelta(minutes=7)).isoformat(),
            "end_time": interrupted_end.isoformat(),
            "duration_minutes": 7,
            "focus_type": "stopwatch",
            "status": "interrupted",
        }
        interrupted = client.post(
            f"{BASE_URL}/focus/sessions",
            headers=headers,
            json=interrupted_payload,
        )
        assert_status(interrupted, 200, "log interrupted focus session")
        interrupted_data = interrupted.json()
        ensure(interrupted_data["success"] is True, f"focus interrupted payload invalid: {interrupted_data}")

        stats_after = client.get(f"{BASE_URL}/focus/stats", headers=headers)
        assert_status(stats_after, 200, "focus stats after logging")
        stats_after_data = stats_after.json()

        weekly_after = client.get(f"{BASE_URL}/focus/stats/weekly", headers=headers)
        assert_status(weekly_after, 200, "focus weekly stats after logging")
        weekly_after_data = weekly_after.json()

        monthly_after = client.get(f"{BASE_URL}/focus/stats/monthly", headers=headers)
        assert_status(monthly_after, 200, "focus monthly stats")
        monthly_after_data = monthly_after.json()

        history_after = client.get(
            f"{BASE_URL}/focus/sessions/history",
            headers=headers,
            params={"limit": 100, "offset": 0},
        )
        assert_status(history_after, 200, "focus history after logging")
        history_after_data = history_after.json()

        heatmap = client.get(
            f"{BASE_URL}/focus/stats/heatmap",
            headers=headers,
            params={"days": 90},
        )
        assert_status(heatmap, 200, "focus heatmap")
        heatmap_data = heatmap.json()

        sessions_alias = client.get(
            f"{BASE_URL}/focus/sessions",
            headers=headers,
            params={"limit": 100, "offset": 0},
        )
        assert_status(sessions_alias, 200, "focus sessions alias")
        sessions_alias_data = sessions_alias.json()

        guide = client.post(
            f"{BASE_URL}/focus/llm/guide",
            headers=headers,
            json={
                "task_id": None,
                "task_context": "复习线性代数第三章并整理出知识结构图",
                "user_input": "给我一个 5 分钟进入状态的方法",
            },
        )
        assert_status(guide, 200, "focus llm guide")
        guide_data = guide.json()
        ensure(bool(guide_data.get("content")), f"focus llm guide empty: {guide_data}")

        breakdown = client.post(
            f"{BASE_URL}/focus/llm/breakdown",
            headers=headers,
            json={
                "task_title": "完成线性代数复习",
                "task_description": "需要拆成今晚可执行的小步骤",
            },
        )
        assert_status(breakdown, 200, "focus llm breakdown")
        breakdown_data = breakdown.json()
        ensure(bool(breakdown_data.get("subtasks")), f"focus llm breakdown empty: {breakdown_data}")

        ensure(
            stats_after_data["total_minutes"] >= baseline_stats_data["total_minutes"] + 25,
            f"focus total_minutes not increased as expected: before={baseline_stats_data}, after={stats_after_data}",
        )
        ensure(
            stats_after_data["pomodoro_count"] >= baseline_stats_data["pomodoro_count"] + 1,
            f"focus pomodoro_count not increased: before={baseline_stats_data}, after={stats_after_data}",
        )
        ensure(
            weekly_after_data["session_count"] >= baseline_weekly_data["session_count"] + 1,
            f"weekly session_count not increased by completed session: before={baseline_weekly_data}, after={weekly_after_data}",
        )
        ensure(
            history_after_data["total_count"] >= baseline_history_data["total_count"] + 2,
            f"history total_count not increased: before={baseline_history_data}, after={history_after_data}",
        )
        ensure(
            sessions_alias_data["total_count"] == history_after_data["total_count"],
            "focus sessions alias diverges from history endpoint",
        )
        ensure(any(value >= 25 for value in heatmap_data.values()), f"focus heatmap missing logged minutes: {heatmap_data}")
        ensure(monthly_after_data["session_count"] >= 2, f"monthly stats missing sessions: {monthly_after_data}")

        print(
            json.dumps(
                {
                    "status": "ALL_OK",
                    "completed_session_id": completed_data["id"],
                    "interrupted_session_id": interrupted_data["id"],
                    "today_total_minutes": stats_after_data["total_minutes"],
                    "today_pomodoro_count": stats_after_data["pomodoro_count"],
                    "weekly_session_count": weekly_after_data["session_count"],
                    "weekly_total_minutes": weekly_after_data["total_minutes"],
                    "monthly_session_count": monthly_after_data["session_count"],
                    "history_total_count": history_after_data["total_count"],
                    "heatmap_days": len(heatmap_data),
                    "guide_preview": guide_data["content"][:120],
                    "breakdown_count": len(breakdown_data["subtasks"]),
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
