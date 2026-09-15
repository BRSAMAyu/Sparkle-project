"""E2E test against running backend/gateway services."""

import os
import sys
import httpx


def main() -> int:
    base_url = os.getenv("API_BASE_URL", "http://localhost:8080/api/v1")
    token = os.getenv("API_TOKEN")
    if not token:
        print("Missing API_TOKEN env var", file=sys.stderr)
        return 1

    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "type": "idle_trigger",
        "urgency": 0.5,
        "context": {"task_name": "数学作业", "suggested_step": "读题"},
        "edge_state": {"focus_score": 0.2, "switching_rate": 0.1},
    }

    with httpx.Client(timeout=10.0) as client:
        resp = client.post(f"{base_url}/interventions/request", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        request_id = data.get("id")
        if not request_id:
            print("Missing request id in response", file=sys.stderr)
            return 1

        feedback_payload = {
            "feedback_type": "accept",
            "extra_data": {"action_taken": "start_now"},
        }
        feedback = client.post(
            f"{base_url}/interventions/requests/{request_id}/feedback",
            json=feedback_payload,
            headers=headers,
        )
        feedback.raise_for_status()

    print("✅ E2E intervention flow ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
