#!/usr/bin/env python3
"""Acceptance coverage for insights, profile surfaces, prediction, and decay timeline."""

from __future__ import annotations

import json

from _acceptance_common import BASE_URL, assert_status, auth_headers, create_client, ensure, login


def main() -> None:
    with create_client(timeout_seconds=90.0) as client:
        token = login(client)
        headers = auth_headers(token)

        dashboard = client.get(f"{BASE_URL}/dashboard/status", headers=headers)
        assert_status(dashboard, 200, "dashboard status")
        dashboard_data = dashboard.json()

        context_resp = client.get(f"{BASE_URL}/profile/context", headers=headers)
        assert_status(context_resp, 200, "profile context")
        context_data = context_resp.json()

        transparent_resp = client.get(f"{BASE_URL}/profile/transparent", headers=headers)
        assert_status(transparent_resp, 200, "profile transparent")
        transparent_data = transparent_resp.json()

        inferred_resp = client.get(f"{BASE_URL}/profile/inferred-preferences", headers=headers)
        assert_status(inferred_resp, 200, "profile inferred preferences")
        inferred_data = inferred_resp.json()

        policies_resp = client.get(f"{BASE_URL}/profile/active-policies", headers=headers)
        assert_status(policies_resp, 200, "profile active policies")
        policies_data = policies_resp.json()

        updates_resp = client.get(f"{BASE_URL}/profile/system-updates", headers=headers)
        assert_status(updates_resp, 200, "profile system updates")
        updates_data = updates_resp.json()

        predictive_dashboard = client.get(f"{BASE_URL}/predictive/dashboard", headers=headers)
        assert_status(predictive_dashboard, 200, "predictive dashboard")
        predictive_dashboard_data = predictive_dashboard.json()

        engagement = client.get(f"{BASE_URL}/predictive/engagement", headers=headers)
        assert_status(engagement, 200, "predictive engagement")
        engagement_data = engagement.json()

        optimal_time = client.get(f"{BASE_URL}/predictive/optimal-time", headers=headers)
        assert_status(optimal_time, 200, "predictive optimal time")
        optimal_time_data = optimal_time.json()

        dropout = client.get(f"{BASE_URL}/predictive/dropout-risk", headers=headers)
        assert_status(dropout, 200, "predictive dropout risk")
        dropout_data = dropout.json()

        focus_heatmap = client.get(
            f"{BASE_URL}/focus/stats/heatmap",
            headers=headers,
            params={"days": 90},
        )
        assert_status(focus_heatmap, 200, "focus heatmap")
        focus_heatmap_data = focus_heatmap.json()

        timemachine_future = client.get(
            f"{BASE_URL}/decay/timemachine/future",
            headers=headers,
            params={"days_ahead": 30},
        )
        assert_status(timemachine_future, 200, "decay timemachine future")
        timemachine_future_data = timemachine_future.json()

        timemachine_compare = client.get(
            f"{BASE_URL}/decay/timemachine/comparison",
            headers=headers,
            params={"days_ahead": 14},
        )
        assert_status(timemachine_compare, 200, "decay timemachine comparison")
        timemachine_compare_data = timemachine_compare.json()

        ensure(dashboard_data.get("weather"), f"dashboard missing weather: {dashboard_data}")
        ensure(dashboard_data.get("flame"), f"dashboard missing flame: {dashboard_data}")
        ensure(isinstance(dashboard_data.get("next_actions"), list), f"dashboard next_actions invalid: {dashboard_data}")

        preferences = context_data.get("preferences") or {}
        ensure(preferences, f"profile context preferences empty: {context_data}")
        ensure(
            any(key in preferences for key in ("learning_style", "depth_preference", "curiosity_preference")),
            f"profile context missing expected preference dimensions: {context_data}",
        )

        layer_1 = transparent_data.get("layer_1") or {}
        ensure(layer_1.get("preferences"), f"transparent layer_1 preferences empty: {transparent_data}")
        ensure("layer_2" in transparent_data and "layer_3" in transparent_data, "transparent profile missing expected layers")

        ensure(len(inferred_data) >= 1, "inferred preferences empty")
        ensure(
            any(item.get("key") in {"avg_question_complexity", "community_engagement_level", "social_learning_preference"} for item in inferred_data),
            f"inferred preferences missing behavioral dimensions: {inferred_data}",
        )

        if isinstance(policies_data, dict):
            ensure(
                "profiles" in policies_data or "active_explanations" in policies_data,
                f"active policies invalid: {policies_data}",
            )
            active_policy_count = len(policies_data.get("active_explanations") or policies_data.get("profiles") or [])
        else:
            ensure(isinstance(policies_data, list), f"active policies invalid: {policies_data}")
            active_policy_count = len(policies_data)
        ensure(isinstance(updates_data.get("items"), list), f"system updates invalid: {updates_data}")

        predictive_payload = predictive_dashboard_data.get("data") or {}
        ensure(predictive_payload.get("engagement_forecast"), f"predictive dashboard missing engagement forecast: {predictive_dashboard_data}")
        ensure(predictive_payload.get("next_intent_forecast"), f"predictive dashboard missing next intent forecast: {predictive_dashboard_data}")
        ensure(engagement_data.get("status") == "success", f"engagement prediction invalid: {engagement_data}")
        ensure(dropout_data.get("status") == "success", f"dropout prediction invalid: {dropout_data}")
        ensure(optimal_time_data.get("status") == "success", f"optimal-time prediction invalid: {optimal_time_data}")

        ensure(len(focus_heatmap_data) >= 1, f"focus heatmap empty: {focus_heatmap_data}")

        projections = timemachine_future_data.get("projections") or {}
        ensure(timemachine_future_data.get("total_nodes", 0) >= 1, f"timemachine future empty: {timemachine_future_data}")
        ensure(projections, f"timemachine future missing projections: {timemachine_future_data}")
        ensure(
            all(key in timemachine_compare_data for key in ("scenario_no_review", "scenario_with_review", "improvement")),
            f"timemachine comparison invalid: {timemachine_compare_data}",
        )

        dashboard_next_actions = dashboard_data.get("next_actions") or []
        engagement_forecast = predictive_payload.get("engagement_forecast") or {}
        intent_forecast = predictive_payload.get("next_intent_forecast") or {}

        print(
            json.dumps(
                {
                    "status": "ALL_OK",
                    "dashboard_next_actions": len(dashboard_next_actions),
                    "context_preference_keys": sorted(list(preferences.keys()))[:10],
                    "transparent_layer1_preferences": len(layer_1.get("preferences") or []),
                    "inferred_keys": [item.get("key") for item in inferred_data[:8]],
                    "active_policy_count": active_policy_count,
                    "system_update_count": len(updates_data.get("items") or []),
                    "engagement_next_active_time": engagement_forecast.get("next_active_time"),
                    "intent_title": intent_forecast.get("title"),
                    "heatmap_days": len(focus_heatmap_data),
                    "timemachine_total_nodes": timemachine_future_data.get("total_nodes"),
                    "comparison_keys": sorted(list(timemachine_compare_data.keys())),
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
