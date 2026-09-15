"""
Core: testing / infra
Phase: adapt
Stage: T6.1 — Performance SLO metrics and alerting

Tests that SLO histogram metrics are registered and can observe values,
and that the alert rule file is valid YAML with expected alert names.
"""

from __future__ import annotations

import yaml

import pytest


class TestSLOMetricsRegistration:
    """Test that all Phase 6 SLO histogram metrics are registered."""

    def test_chat_first_token_histogram_exists(self):
        from app.core.metrics import AI_RESPONSE_FIRST_TOKEN_DURATION
        assert AI_RESPONSE_FIRST_TOKEN_DURATION is not None
        AI_RESPONSE_FIRST_TOKEN_DURATION.labels(chat_mode="stream", reasoning_mode="none").observe(0.5)

    def test_task_generation_e2e_histogram_exists(self):
        from app.core.metrics import TASK_GENERATION_E2E_LATENCY
        assert TASK_GENERATION_E2E_LATENCY is not None
        TASK_GENERATION_E2E_LATENCY.labels(source="langgraph").observe(3.0)

    def test_rag_retrieval_histogram_exists(self):
        from app.core.metrics import RAG_RETRIEVAL_LATENCY
        assert RAG_RETRIEVAL_LATENCY is not None
        RAG_RETRIEVAL_LATENCY.labels(source="pgvector", stage="retrieve").observe(0.3)

    def test_galaxy_e2e_histogram_exists(self):
        from app.core.metrics import GALAXY_E2E_LATENCY
        assert GALAXY_E2E_LATENCY is not None
        GALAXY_E2E_LATENCY.labels(operation="get_nodes").observe(1.5)

    def test_aurora_tier_latency_histogram_exists(self):
        """Aurora tier latency histogram exists with tier label."""
        from app.core.metrics import get_or_create_metric, Histogram
        aurora_hist = get_or_create_metric(
            Histogram, "sparkle_aurora_tier_latency_seconds",
            "test doc", ["tier", "trigger_point"],
        )
        assert aurora_hist is not None
        aurora_hist.labels(tier="L3", trigger_point="wake").observe(10.0)

    def test_planning_latency_histogram_exists(self):
        from app.core.metrics import LANGGRAPH_PLANNING_LATENCY
        assert LANGGRAPH_PLANNING_LATENCY is not None
        LANGGRAPH_PLANNING_LATENCY.labels(collaboration_mode="multi").observe(2.0)


class TestSLOHistogramBuckets:
    """Verify bucket boundaries cover the SLO thresholds."""

    def test_chat_first_token_covers_2s(self):
        from app.core.metrics import AI_RESPONSE_FIRST_TOKEN_DURATION
        assert any(b >= 2.0 for b in AI_RESPONSE_FIRST_TOKEN_DURATION._upper_bounds)

    def test_task_gen_covers_5s(self):
        from app.core.metrics import TASK_GENERATION_E2E_LATENCY
        assert any(b >= 5.0 for b in TASK_GENERATION_E2E_LATENCY._upper_bounds)

    def test_rag_covers_1s(self):
        from app.core.metrics import RAG_RETRIEVAL_LATENCY
        assert any(b >= 1.0 for b in RAG_RETRIEVAL_LATENCY._upper_bounds)

    def test_galaxy_covers_3s(self):
        from app.core.metrics import GALAXY_E2E_LATENCY
        assert any(b >= 3.0 for b in GALAXY_E2E_LATENCY._upper_bounds)


class TestSLOAlertRules:
    """Test that the SLO alert rule file is valid and contains expected alerts."""

    @pytest.fixture
    def slo_rules(self):
        import pathlib
        rule_file = pathlib.Path(__file__).parent.parent.parent.parent / "monitoring" / "sparkle_t6_slo_alerts.yml"
        with open(rule_file) as f:
            return yaml.safe_load(f)

    def test_file_is_valid_yaml(self, slo_rules):
        assert slo_rules is not None
        assert "groups" in slo_rules

    def test_contains_chat_first_token_alert(self, slo_rules):
        alerts = slo_rules["groups"][0]["rules"]
        names = [a["alert"] for a in alerts]
        assert "SparkleSLOChatFirstTokenSlow" in names

    def test_contains_task_generation_alert(self, slo_rules):
        alerts = slo_rules["groups"][0]["rules"]
        names = [a["alert"] for a in alerts]
        assert "SparkleSLOTaskGenerationSlow" in names

    def test_contains_retrieval_alert(self, slo_rules):
        alerts = slo_rules["groups"][0]["rules"]
        names = [a["alert"] for a in alerts]
        assert "SparkleSLORetrievalSlow" in names

    def test_contains_galaxy_alert(self, slo_rules):
        alerts = slo_rules["groups"][0]["rules"]
        names = [a["alert"] for a in alerts]
        assert "SparkleSLOGalaxySlow" in names

    def test_contains_aurora_l3_alert(self, slo_rules):
        alerts = slo_rules["groups"][0]["rules"]
        names = [a["alert"] for a in alerts]
        assert "SparkleSLOAuroraL3Slow" in names

    def test_alerts_have_slo_labels(self, slo_rules):
        alerts = slo_rules["groups"][0]["rules"]
        for alert in alerts:
            assert "slo" in alert.get("labels", {}), f"Alert {alert['alert']} missing slo label"

    def test_all_alerts_are_warning_severity(self, slo_rules):
        alerts = slo_rules["groups"][0]["rules"]
        for alert in alerts:
            assert alert["labels"]["severity"] == "warning"


class TestSLOPrometheusConfig:
    """Test that prometheus.yml includes the T6 SLO alert file."""

    def test_t6_slo_rules_in_prometheus_config(self):
        import pathlib
        prom_file = pathlib.Path(__file__).parent.parent.parent.parent / "monitoring" / "prometheus.yml"
        with open(prom_file) as f:
            config = yaml.safe_load(f)
        assert "sparkle_t6_slo_alerts.yml" in config["rule_files"]
