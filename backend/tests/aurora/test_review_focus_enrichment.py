import pytest

from app.aurora.runtime_v1.service import AuroraRuntimeV1Service


@pytest.fixture()
def svc() -> AuroraRuntimeV1Service:
    return AuroraRuntimeV1Service.__new__(AuroraRuntimeV1Service)


class TestReviewFocusFromContext:
    def test_returns_none_when_no_review_node(self, svc: AuroraRuntimeV1Service) -> None:
        result = svc._review_focus_from_context({})
        assert result is None

    def test_extracts_basic_fields(self, svc: AuroraRuntimeV1Service) -> None:
        result = svc._review_focus_from_context(
            {
                "review_node": "cn.tcp_flow",
                "node_label": "TCP流量控制",
            }
        )
        assert result is not None
        assert result["review_node"] == "cn.tcp_flow"
        assert result["node_label"] == "TCP流量控制"

    def test_extracts_enriched_fields(self, svc: AuroraRuntimeV1Service) -> None:
        result = svc._review_focus_from_context(
            {
                "review_node": "cn.tcp_flow",
                "node_label": "TCP流量控制",
                "mastery": 0.65,
                "study_count": 3,
                "related_error_count": 2,
                "related_errors": [
                    {
                        "question_text": "rwnd 和 cwnd 的区别是什么？",
                        "analysis_summary": "窗口变量混淆",
                    }
                ],
            }
        )
        assert result is not None
        assert result["mastery"] == 0.65
        assert result["study_count"] == 3
        assert result["related_error_count"] == 2
        assert result["related_errors"] == [
            {
                "question_text": "rwnd 和 cwnd 的区别是什么？",
                "analysis_summary": "窗口变量混淆",
            }
        ]

    def test_ignores_non_numeric_mastery(self, svc: AuroraRuntimeV1Service) -> None:
        result = svc._review_focus_from_context(
            {
                "review_node": "cn.tcp_flow",
                "node_label": "TCP",
                "mastery": "high",
            }
        )
        assert result is not None
        assert "mastery" not in result

    def test_ignores_non_int_counts(self, svc: AuroraRuntimeV1Service) -> None:
        result = svc._review_focus_from_context(
            {
                "review_node": "cn.tcp_flow",
                "node_label": "TCP",
                "study_count": "three",
                "related_error_count": 1.5,
            }
        )
        assert result is not None
        assert "study_count" not in result
        assert "related_error_count" not in result


class TestBuildReviewNodeFirstTurnMessage:
    def test_new_node_no_mastery(self) -> None:
        msg = AuroraRuntimeV1Service._build_review_node_first_turn_message(
            {
                "review_node": "cn.tcp_flow",
                "node_label": "TCP流量控制",
                "mastery": 0.0,
                "study_count": 0,
            }
        )
        assert "开始学习" in msg
        assert "TCP流量控制" in msg
        assert "用户当前对该节点掌握 0%" in msg
        assert "基础题" in msg
        assert "复习" not in msg

    def test_low_mastery(self) -> None:
        msg = AuroraRuntimeV1Service._build_review_node_first_turn_message(
            {
                "review_node": "cn.tcp_flow",
                "node_label": "TCP流量控制",
                "mastery": 0.25,
                "study_count": 1,
            }
        )
        assert "复习" in msg
        assert "用户当前对该节点掌握 25%" in msg
        assert "生疏" in msg
        assert "基础题" in msg

    def test_mid_mastery_with_errors(self) -> None:
        msg = AuroraRuntimeV1Service._build_review_node_first_turn_message(
            {
                "review_node": "cn.tcp_flow",
                "node_label": "TCP流量控制",
                "mastery": 0.5,
                "study_count": 3,
                "related_error_count": 4,
            }
        )
        assert "复习" in msg
        assert "用户当前对该节点掌握 50%" in msg
        assert "薄弱" in msg
        assert "4 道相关错题" in msg

    def test_high_mastery(self) -> None:
        msg = AuroraRuntimeV1Service._build_review_node_first_turn_message(
            {
                "review_node": "cn.tcp_flow",
                "node_label": "TCP流量控制",
                "mastery": 0.85,
                "study_count": 10,
            }
        )
        assert "复习" in msg
        assert "用户当前对该节点掌握 85%" in msg
        assert "查漏补缺" in msg
        assert "挑战题" in msg

    def test_includes_related_error_summaries(self) -> None:
        msg = AuroraRuntimeV1Service._build_review_node_first_turn_message(
            {
                "review_node": "cn.tcp_flow",
                "node_label": "TCP流量控制",
                "mastery": 0.35,
                "study_count": 2,
                "related_errors": [
                    {"analysis_summary": "窗口变量混淆"},
                    {"question_text": "为什么 advertised window 会变小？"},
                ],
            }
        )
        assert "窗口变量混淆" in msg
        assert "为什么 advertised window 会变小？" in msg

    def test_no_mastery_field_falls_back_gracefully(self) -> None:
        msg = AuroraRuntimeV1Service._build_review_node_first_turn_message(
            {
                "review_node": "cn.tcp_flow",
                "node_label": "TCP流量控制",
            }
        )
        assert "TCP流量控制" in msg
