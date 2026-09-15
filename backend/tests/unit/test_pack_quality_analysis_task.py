from __future__ import annotations

from unittest.mock import AsyncMock, patch

from app.core.cache import cache_service
from app.core.celery_tasks import pack_quality_analysis_task
from app.schemas.exam_sprint import NodeQualityAlert, PackQualityReport


class _AsyncSessionFactoryStub:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, tb):
        return False


def test_pack_quality_analysis_task_persists_filtered_report(monkeypatch) -> None:
    cache_service._local_cache.clear()
    monkeypatch.setattr(cache_service, "redis", None)
    monkeypatch.setattr(cache_service, "init_redis", AsyncMock())

    alerts = [
        NodeQualityAlert(
            node_id="cn.subnetting",
            node_label="子网划分与 CIDR",
            current_difficulty=2,
            suggested_difficulty=3,
            average_post_sprint_mastery=0.35,
            expected_mastery=0.65,
            evidence_count=60,
        ),
        NodeQualityAlert(
            node_id="cn.arp",
            node_label="ARP",
            current_difficulty=2,
            suggested_difficulty=3,
            average_post_sprint_mastery=0.34,
            expected_mastery=0.65,
            evidence_count=49,
        ),
    ]
    report = PackQualityReport(
        pack_id="computer_networks@v1",
        pack_name="Computer Networks Sprint Pack",
        total_nodes=62,
        nodes_analyzed=62,
        insufficient_data_nodes=1,
        alerts=[alerts[0]],
    )

    with patch("app.db.session.AsyncSessionLocal", return_value=_AsyncSessionFactoryStub()), patch(
        "app.services.exam_sprint_review_service.ExamSprintReviewService.analyze_pack_node_effectiveness",
        new=AsyncMock(return_value=alerts),
    ), patch(
        "app.services.exam_sprint_review_service.ExamSprintReviewService.build_pack_quality_report",
        new=AsyncMock(return_value=report),
    ):
        result = pack_quality_analysis_task.run("computer_networks@v1")

    stored = cache_service._local_cache["aurora:pack_quality_alerts:computer_networks@v1"][0]

    assert result == report.model_dump(mode="json")
    assert stored["alerts"] == [alerts[0].model_dump(mode="json")]
