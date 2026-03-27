from __future__ import annotations

import json
import os
import time

import httpx

from _acceptance_common import login as shared_login


USERNAME = os.getenv("LOCAL_SMOKE_USERNAME", "chat_test")
PASSWORD = os.getenv("LOCAL_SMOKE_PASSWORD", "Chat123456")
BASE_URL = os.getenv("LOCAL_SMOKE_BASE_URL", "http://127.0.0.1:8080/api/v1")


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)

def poll_until(callback, *, timeout_seconds: int = 25, interval_seconds: float = 1.5):
    deadline = time.monotonic() + timeout_seconds
    last_value = None
    while time.monotonic() < deadline:
        last_value = callback()
        if last_value:
            return last_value
        time.sleep(interval_seconds)
    return last_value


def main() -> None:
    with httpx.Client(timeout=60.0) as client:
        token = shared_login(client)
        headers = {"Authorization": f"Bearer {token}"}

        baseline_fragments = client.get(f"{BASE_URL}/cognitive/fragments", headers=headers)
        ensure(
            baseline_fragments.status_code == 200,
            f"baseline fragments failed: {baseline_fragments.status_code} {baseline_fragments.text[:400]}",
        )
        baseline_fragment_count = len(baseline_fragments.json())

        fragment_resp = client.post(
            f"{BASE_URL}/cognitive/fragments",
            headers=headers,
            json={
                "content": "今天做题时我总会先怀疑自己，再来回改答案，导致节奏被打断。",
                "source_type": "quick_note",
                "context_tags": {"module": "notes_errorbook_acceptance"},
            },
        )
        ensure(
            fragment_resp.status_code == 200,
            f"create fragment failed: {fragment_resp.status_code} {fragment_resp.text[:400]}",
        )
        fragment_payload = fragment_resp.json()
        fragment_id = fragment_payload["id"]

        fragments_after = client.get(f"{BASE_URL}/cognitive/fragments", headers=headers)
        ensure(fragments_after.status_code == 200, f"fragment list failed: {fragments_after.status_code}")
        ensure(
            any(item["id"] == fragment_id for item in fragments_after.json()),
            "quick note fragment missing from /cognitive/fragments",
        )

        error_resp = client.post(
            f"{BASE_URL}/errors",
            headers=headers,
            json={
                "question_text": "CS101 指针题里 *p 和 p 的意义分别是什么？",
                "user_answer": "我把 p 当成了值本身",
                "correct_answer": "p 是地址，*p 才是地址指向的值",
                "subject": "computer",
                "chapter": "指针与内存",
                "cognitive_tags": ["analysis"],
                "ai_analysis_summary": "闪念胶囊快速记录的概念混淆线索",
            },
        )
        ensure(error_resp.status_code == 201, f"create error failed: {error_resp.status_code} {error_resp.text[:400]}")
        error_payload = error_resp.json()
        error_id = error_payload["id"]

        analyzed_error = poll_until(
            lambda: (
                response.json()
                if (response := client.get(f"{BASE_URL}/errors/{error_id}", headers=headers)).status_code == 200
                and response.json().get("latest_analysis")
                else None
            )
        )
        ensure(analyzed_error is not None, "error analysis did not complete in time")

        semantic_resp = client.get(f"{BASE_URL}/errors/{error_id}/semantic", headers=headers)
        ensure(
            semantic_resp.status_code == 200,
            f"semantic summary failed: {semantic_resp.status_code} {semantic_resp.text[:400]}",
        )
        semantic_payload = semantic_resp.json()
        ensure(semantic_payload["error_id"] == error_id, f"unexpected semantic payload: {semantic_payload}")

        filtered_errors = client.get(
            f"{BASE_URL}/errors",
            headers=headers,
            params={"cognitive_dimension": "analysis", "page": 1, "page_size": 50},
        )
        ensure(
            filtered_errors.status_code == 200,
            f"filtered errors failed: {filtered_errors.status_code} {filtered_errors.text[:400]}",
        )
        filtered_payload = filtered_errors.json()
        ensure(
            any(item["id"] == error_id for item in filtered_payload.get("items", [])),
            "created error missing from cognitive_dimension=analysis filter",
        )

        review_resp = client.post(
            f"{BASE_URL}/errors/{error_id}/review",
            headers=headers,
            json={"performance": "remembered", "time_spent_seconds": 45},
        )
        ensure(review_resp.status_code == 200, f"submit review failed: {review_resp.status_code} {review_resp.text[:400]}")
        review_payload = review_resp.json()
        ensure(review_payload["review_count"] >= 1, f"review count did not update: {review_payload}")

        inferred_payload = poll_until(
            lambda: (
                payload
                if (
                    payload := client.get(f"{BASE_URL}/profile/inferred-preferences", headers=headers).json()
                )
                and any(item.get("key") == "error_density_score" for item in payload)
                else None
            ),
            timeout_seconds=20,
        )
        ensure(inferred_payload is not None, "profile inferred preferences did not receive error book signals")

        print(
            json.dumps(
                {
                    "status": "ALL_OK",
                    "fragment_id": fragment_id,
                    "baseline_fragment_count": baseline_fragment_count,
                    "current_fragment_count": len(fragments_after.json()),
                    "error_id": error_id,
                    "semantic_strategy_count": len(semantic_payload.get("strategies", [])),
                    "semantic_similar_error_count": len(semantic_payload.get("similar_errors", [])),
                    "filtered_total": filtered_payload.get("total"),
                    "review_count": review_payload.get("review_count"),
                    "inferred_keys": [item.get("key") for item in inferred_payload],
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
