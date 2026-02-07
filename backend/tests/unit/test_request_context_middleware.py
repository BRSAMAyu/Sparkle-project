from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.api.middleware import RequestContextMiddleware


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/ping")
    async def ping(request: Request):
        return {
            "request_id": request.state.request_id,
            "trace_id": request.state.trace_id,
        }

    return app


def test_request_context_generates_ids_when_absent():
    client = TestClient(_build_app())
    response = client.get("/ping")
    assert response.status_code == 200

    payload = response.json()
    assert payload["request_id"]
    assert payload["trace_id"]
    assert response.headers["X-Request-ID"] == payload["request_id"]
    assert response.headers["X-Trace-ID"] == payload["trace_id"]


def test_request_context_respects_incoming_headers():
    client = TestClient(_build_app())
    response = client.get(
        "/ping",
        headers={
            "X-Request-ID": "req-fixed",
            "X-Trace-ID": "trace-fixed",
        },
    )
    assert response.status_code == 200
    assert response.json()["request_id"] == "req-fixed"
    assert response.json()["trace_id"] == "trace-fixed"
    assert response.headers["X-Request-ID"] == "req-fixed"
    assert response.headers["X-Trace-ID"] == "trace-fixed"
