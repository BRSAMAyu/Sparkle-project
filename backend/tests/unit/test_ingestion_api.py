from __future__ import annotations

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.ingestion import router as ingestion_router


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(ingestion_router, prefix="/ingestion")
    return TestClient(app)


def test_clean_document_rejects_oversized_upload():
    with _build_client() as client, patch("app.api.v1.ingestion.settings.MAX_UPLOAD_SIZE", 4):
        response = client.post(
            "/ingestion/clean",
            files={"file": ("large.txt", BytesIO(b"12345"), "text/plain")},
        )

    assert response.status_code == 413
    assert "Maximum upload size" in response.json()["detail"]


def test_background_document_task_uses_semaphore():
    semaphore = MagicMock()
    semaphore.__aenter__ = AsyncMock(return_value=semaphore)
    semaphore.__aexit__ = AsyncMock(return_value=False)

    with patch("app.api.v1.ingestion._DOCUMENT_CLEANING_SEMAPHORE", semaphore), patch(
        "app.api.v1.ingestion.document_service.clean_and_summarize",
        new=AsyncMock(),
    ) as clean_mock:
        import asyncio

        asyncio.run(
            __import__("app.api.v1.ingestion", fromlist=["_process_document_task"])._process_document_task(
                "task-1",
                "/tmp/fake.txt",
                {},
            )
        )

    semaphore.__aenter__.assert_awaited_once()
    clean_mock.assert_awaited_once()
