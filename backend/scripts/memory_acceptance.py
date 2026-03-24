#!/usr/bin/env python3
"""Acceptance coverage for memory panel, preference/goals operations, corrections, and export."""

from __future__ import annotations

import json
import uuid
from datetime import date

from _acceptance_common import (
    BASE_URL,
    assert_status,
    auth_headers,
    create_client,
    ensure,
    login,
    poll_until,
)


def _find_inferred_override_key(items: list[dict]) -> str | None:
    for item in items:
        if item.get("adjustable"):
            return item.get("key")
    return None


def main() -> None:
    with create_client(timeout_seconds=90.0) as client:
        token = login(client)
        headers = auth_headers(token)

        onboarding_preview = client.post(
            f"{BASE_URL}/profile/onboarding/preview",
            headers=headers,
            json={
                "learning_goal_type": "exam",
                "learning_goal": f"记忆验收目标 {uuid.uuid4().hex[:8]}",
                "study_time_minutes": 45,
                "knowledge_level": "intermediate",
                "response_depth": 0.6,
            },
        )
        assert_status(onboarding_preview, 200, "onboarding preview for memory acceptance")

        onboarding_submit = client.post(
            f"{BASE_URL}/profile/onboarding",
            headers=headers,
            json={
                "learning_goal_type": "exam",
                "learning_goal": f"记忆验收目标 {uuid.uuid4().hex[:8]}",
                "learning_style": "structured",
                "study_time_minutes": 60,
                "knowledge_level": "intermediate",
                "response_depth": 0.7,
                "curiosity_preference": 0.65,
            },
        )
        assert_status(onboarding_submit, 200, "onboarding submit for goal creation")

        preferences_resp = client.get(f"{BASE_URL}/memory/preferences", headers=headers)
        assert_status(preferences_resp, 200, "memory preferences")
        preferences_data = preferences_resp.json()
        ensure(preferences_data.get("items"), f"memory preferences empty: {preferences_data}")

        memory_settings = client.get(f"{BASE_URL}/memory/settings", headers=headers)
        assert_status(memory_settings, 200, "memory settings")
        memory_settings_data = memory_settings.json()

        memory_settings_update = client.put(
            f"{BASE_URL}/memory/settings",
            headers=headers,
            json={
                "enabled": memory_settings_data.get("enabled", True),
                "allow_preferences": memory_settings_data.get("allow_preferences", True),
                "allow_goals": memory_settings_data.get("allow_goals", True),
                "allow_episodic": memory_settings_data.get("allow_episodic", True),
                "capture_level": memory_settings_data.get("capture_level", "medium"),
                "blocked_pref_keys": memory_settings_data.get("blocked_pref_keys", []),
                "blocked_sources": memory_settings_data.get("blocked_sources", []),
            },
        )
        assert_status(memory_settings_update, 200, "memory settings update")

        update_pref_1 = client.put(
            f"{BASE_URL}/profile/preferences",
            headers=headers,
            json={"pref_key": "ai_verbosity", "value": "detailed"},
        )
        assert_status(update_pref_1, 200, "update ai_verbosity to detailed")

        update_pref_2 = client.put(
            f"{BASE_URL}/profile/preferences",
            headers=headers,
            json={"pref_key": "ai_verbosity", "value": "concise"},
        )
        assert_status(update_pref_2, 200, "update ai_verbosity to concise")

        history_resp = client.get(f"{BASE_URL}/memory/preferences/ai_verbosity/history", headers=headers)
        assert_status(history_resp, 200, "memory preference history")
        history_data = history_resp.json()
        ensure(len(history_data.get("items") or []) >= 2, f"preference history too short: {history_data}")
        latest_preference_record_id = history_data["items"][0]["id"]

        rollback_resp = client.post(
            f"{BASE_URL}/profile/preferences/rollback",
            headers=headers,
            json={"pref_key": "ai_verbosity"},
        )
        assert_status(rollback_resp, 200, "memory preference rollback")
        rollback_data = rollback_resp.json()
        ensure(rollback_data.get("status") == "ok", f"rollback failed: {rollback_data}")

        goals_resp = client.get(f"{BASE_URL}/memory/goals", headers=headers)
        assert_status(goals_resp, 200, "memory goals")
        goals_data = goals_resp.json()
        ensure(goals_data.get("items"), f"memory goals empty after onboarding: {goals_data}")
        goal_id = goals_data["items"][0]["id"]

        target_date = date.today().isoformat()
        update_goal_resp = client.put(
            f"{BASE_URL}/profile/goals",
            headers=headers,
            json={
                "goal_id": goal_id,
                "title": f"更新后的记忆验收目标 {uuid.uuid4().hex[:6]}",
                "status": "active",
                "target_date": target_date,
            },
        )
        assert_status(update_goal_resp, 200, "update memory goal")

        goal_after = client.get(f"{BASE_URL}/memory/goals", headers=headers)
        assert_status(goal_after, 200, "memory goals after update")
        goal_after_data = goal_after.json()
        current_goal = next((item for item in goal_after_data.get("items", []) if item["id"] == goal_id), None)
        ensure(current_goal is not None, "updated goal missing from /memory/goals")
        ensure(current_goal.get("target_date") == target_date, f"goal target_date not updated: {current_goal}")

        episodic_resp = client.get(f"{BASE_URL}/memory/episodic", headers=headers)
        assert_status(episodic_resp, 200, "memory episodic")
        episodic_data = episodic_resp.json()
        ensure(episodic_data.get("items"), f"memory episodic empty: {episodic_data}")
        episodic_id = episodic_data["items"][0]["id"]

        correction_resp = client.post(
            f"{BASE_URL}/memory/correct",
            headers=headers,
            json={
                "type": "preference",
                "id": latest_preference_record_id,
                "action": "lower_confidence",
                "reason": "acceptance correction",
            },
        )
        assert_status(correction_resp, 200, "memory correction")
        correction_data = correction_resp.json()
        ensure(correction_data.get("status") == "corrected", f"memory correction failed: {correction_data}")

        retract_resp = client.post(
            f"{BASE_URL}/memory/retract",
            headers=headers,
            json={
                "type": "preference",
                "id": latest_preference_record_id,
                "reason": "acceptance retraction check",
            },
        )
        assert_status(retract_resp, 200, "memory retract preference")

        export_resp = client.get(f"{BASE_URL}/memory/export", headers=headers)
        assert_status(export_resp, 200, "memory export")
        export_data = export_resp.json()
        ensure(export_data.get("preferences"), f"memory export missing preferences: {export_data}")
        ensure(export_data.get("goals"), f"memory export missing goals: {export_data}")
        ensure(export_data.get("episodic"), f"memory export missing episodic: {export_data}")

        transparent_resp = client.get(f"{BASE_URL}/profile/transparent", headers=headers)
        assert_status(transparent_resp, 200, "profile transparent after memory updates")
        transparent_data = transparent_resp.json()

        context_resp = client.get(f"{BASE_URL}/profile/context", headers=headers)
        assert_status(context_resp, 200, "profile context after memory updates")
        context_data = context_resp.json()

        inferred_resp = client.get(f"{BASE_URL}/profile/inferred-preferences", headers=headers)
        assert_status(inferred_resp, 200, "profile inferred preferences")
        inferred_data = inferred_resp.json()

        override_key = _find_inferred_override_key(inferred_data)
        override_status = "not_applicable"
        if override_key:
            override_resp = client.post(
                f"{BASE_URL}/profile/override-inferred",
                headers=headers,
                json={"key": override_key, "value": 0.75, "reason": "acceptance override"},
            )
            assert_status(override_resp, 200, "override inferred preference")
            reset_resp = client.post(
                f"{BASE_URL}/profile/reset-override",
                headers=headers,
                json={"key": override_key},
            )
            assert_status(reset_resp, 200, "reset inferred override")
            override_status = "ok"

        system_updates = poll_until(
            lambda: client.get(f"{BASE_URL}/profile/system-updates", headers=headers).json(),
            timeout_seconds=10,
            interval_seconds=1.0,
        )
        ensure(isinstance(system_updates.get("items"), list), f"system updates invalid: {system_updates}")

        layer_1 = transparent_data.get("layer_1") or {}
        ensure(layer_1.get("preferences"), f"transparent profile missing preferences: {transparent_data}")
        ensure(layer_1.get("goals"), f"transparent profile missing goals: {transparent_data}")
        ensure(context_data.get("preferences"), f"profile context preferences empty: {context_data}")

        print(
            json.dumps(
                {
                    "status": "ALL_OK",
                    "memory_preferences": len(preferences_data.get("items") or []),
                    "preference_history_versions": len(history_data.get("items") or []),
                    "goal_id": goal_id,
                    "goal_target_date": current_goal.get("target_date"),
                    "episodic_count": len(episodic_data.get("items") or []),
                    "retracted_preference_id": latest_preference_record_id,
                    "correction_status": correction_data.get("status"),
                    "override_status": override_status,
                    "system_update_count": len(system_updates.get("items") or []),
                    "export_goal_count": len(export_data.get("goals") or []),
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
