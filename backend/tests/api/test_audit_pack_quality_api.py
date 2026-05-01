from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_active_superuser, get_db
from app.api.v1.audit import router as audit_router
from app.schemas.exam_sprint import PackQualityReport


def test_pack_quality_endpoint_returns_expected_report_shape() -> None:
    app = FastAPI()
    app.include_router(audit_router)

    async def _override_get_db():
        yield object()

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_active_superuser] = lambda: SimpleNamespace(
        id="admin-1",
        is_superuser=True,
        is_active=True,
    )

    report = PackQualityReport(
        pack_id="computer_networks@v1",
        pack_name="Computer Networks Sprint Pack",
        total_nodes=62,
        nodes_analyzed=62,
        insufficient_data_nodes=3,
        alerts=[
            {
                "node_id": "cn.subnetting",
                "node_label": "子网划分与 CIDR",
                "current_difficulty": 2,
                "suggested_difficulty": 3,
                "average_post_sprint_mastery": 0.35,
                "expected_mastery": 0.65,
                "evidence_count": 60,
            }
        ],
    )

    with TestClient(app) as client, patch(
        "app.api.v1.audit.cache_service.get",
        new=AsyncMock(return_value=None),
    ), patch(
        "app.api.v1.audit.ExamSprintReviewService.build_pack_quality_report",
        new=AsyncMock(return_value=report),
    ) as mock_report:
        response = client.get("/audit/pack-quality", params={"pack_id": "computer_networks@v1"})

    assert response.status_code == 200
    assert response.json() == report.model_dump(mode="json")
    mock_report.assert_awaited_once_with("computer_networks@v1")
