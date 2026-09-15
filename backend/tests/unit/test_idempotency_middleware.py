from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.middleware import IdempotencyMiddleware
from app.core.idempotency import get_idempotency_store


def _create_app():
    app = FastAPI()
    store = get_idempotency_store("memory")
    app.add_middleware(IdempotencyMiddleware, store=store)

    @app.post("/api/v1/events/ingest")
    async def ingest(payload: dict):
        return {"echo": payload}

    return app


def test_idempotency_conflict_on_payload_mismatch():
    client = TestClient(_create_app())

    headers = {"X-Idempotency-Key": "abc123"}
    resp1 = client.post("/api/v1/events/ingest", json={"events": [1]}, headers=headers)
    assert resp1.status_code == 200

    resp2 = client.post("/api/v1/events/ingest", json={"events": [1]}, headers=headers)
    assert resp2.status_code == 200
    assert resp2.headers.get("X-Idempotency-Replayed") == "true"

    resp3 = client.post("/api/v1/events/ingest", json={"events": [2]}, headers=headers)
    assert resp3.status_code == 409
