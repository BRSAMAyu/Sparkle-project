"""
Unit tests for app.core.metrics module.
Tests prometheus metrics initialization and decorator functionality.
"""
import pytest
from unittest.mock import patch, MagicMock
from prometheus_client import REGISTRY

from app.core import metrics


class TestMetricsInitialization:
    """Test metrics initialization"""

    def test_request_metrics_exist(self):
        """Test request metrics are properly initialized"""
        assert metrics.REQUEST_COUNT is not None
        assert metrics.REQUEST_LATENCY is not None

    def test_llm_metrics_exist(self):
        """Test LLM metrics are properly initialized"""
        assert metrics.TOKEN_USAGE is not None
        assert metrics.LLM_CALL_DURATION is not None

    def test_cache_metrics_exist(self):
        """Test cache metrics are properly initialized"""
        assert metrics.CACHE_HIT_COUNT is not None
        assert metrics.SEMANTIC_CACHE_HIT_TOTAL is not None
        assert metrics.SEMANTIC_CACHE_MISS_TOTAL is not None

    def test_tool_metrics_exist(self):
        """Test tool metrics are properly initialized"""
        assert metrics.TOOL_EXECUTION_COUNT is not None

    def test_system_metrics_exist(self):
        """Test system metrics are properly initialized"""
        assert metrics.ACTIVE_SESSIONS is not None
        assert metrics.KNOWLEDGE_NODE_UPDATES is not None
        assert metrics.RAG_RETRIEVAL_LATENCY is not None

    def test_feedback_metrics_exist(self):
        """Test feedback metrics are properly initialized"""
        assert metrics.RESPONSE_FEEDBACK_INGESTED is not None
        assert metrics.RESPONSE_FEEDBACK_DEDUPE_TOTAL is not None

    def test_metrics_in_registry(self):
        """Test that metrics are registered in prometheus registry"""
        assert 'sparkle_requests_total' in REGISTRY._names_to_collectors
        assert 'sparkle_tokens_total' in REGISTRY._names_to_collectors
        assert 'sparkle_cache_hits_total' in REGISTRY._names_to_collectors


class TestGetOrCreateMetric:
    """Test get_or_create_metric utility function"""

    def test_create_new_metric(self):
        """Test creating a new metric"""
        from prometheus_client import Counter

        # Remove if exists
        if 'test_new_metric' in REGISTRY._names_to_collectors:
            del REGISTRY._names_to_collectors['test_new_metric']

        metric = metrics.get_or_create_metric(
            Counter,
            'test_new_metric',
            'Test metric description',
            ['label1', 'label2']
        )

        assert metric is not None
        assert 'test_new_metric' in REGISTRY._names_to_collectors

    def test_get_existing_metric(self):
        """Test getting an existing metric returns same instance"""
        from prometheus_client import Counter

        # Create metric
        metric1 = metrics.get_or_create_metric(
            Counter,
            'sparkle_requests_total',
            'Test',
            ['module', 'method', 'status']
        )

        # Get same metric
        metric2 = metrics.get_or_create_metric(
            Counter,
            'sparkle_requests_total',
            'Test',
            ['module', 'method', 'status']
        )

        # Should return same instance
        assert metric1 is metric2


class TestTrackLatencyDecorator:
    """Test track_latency decorator"""

    @pytest.mark.asyncio
    async def test_async_function_success(self):
        """Test decorator with async function that succeeds"""
        # Mock opentelemetry trace
        with patch('app.core.metrics.trace') as mock_trace:
            mock_span = MagicMock()
            mock_span.get_span_context().trace_id = 12345
            mock_trace.get_current_span.return_value = mock_span

            @metrics.track_latency('test_module', 'test_method')
            async def test_func():
                return "success"

            result = await test_func()

            assert result == "success"
            # Verify metrics were recorded (via side effects)

    @pytest.mark.asyncio
    async def test_async_function_error(self):
        """Test decorator with async function that raises exception"""
        with patch('app.core.metrics.trace') as mock_trace:
            with patch('app.core.metrics.logger') as mock_logger:
                mock_span = MagicMock()
                mock_span.get_span_context().trace_id = 67890
                mock_trace.get_current_span.return_value = mock_span

                @metrics.track_latency('test_module', 'test_method')
                async def test_func():
                    raise ValueError("test error")

                with pytest.raises(ValueError):
                    await test_func()

                # Verify error was logged with correct module/method info
                mock_logger.error.assert_called_once()
                error_msg = mock_logger.error.call_args[0][0]
                assert "test_module.test_method" in error_msg
                assert "test error" in error_msg
                assert "TraceID" in error_msg  # async path includes trace ID

    def test_sync_function_success(self):
        """Test decorator with sync function that succeeds"""
        @metrics.track_latency('test_module', 'test_method')
        def test_func():
            return "sync_success"

        result = test_func()
        assert result == "sync_success"

    def test_sync_function_error(self):
        """Test decorator with sync function that raises exception"""
        with patch('app.core.metrics.logger') as mock_logger:
            @metrics.track_latency('test_module', 'test_method')
            def test_func():
                raise ValueError("sync error")

            with pytest.raises(ValueError):
                test_func()

            # Verify error was logged with correct module/method info
            mock_logger.error.assert_called_once()
            error_msg = mock_logger.error.call_args[0][0]
            assert "test_module.test_method" in error_msg
            assert "sync error" in error_msg


class TestMetricLabelUpdates:
    """Test metric label updates"""

    def test_request_count_labels(self):
        """Test REQUEST_COUNT accepts correct labels"""
        # Should not raise exception
        metrics.REQUEST_COUNT.labels(
            module='test',
            method='test_method',
            status='success'
        )

    def test_feedback_ingested_labels(self):
        """Test RESPONSE_FEEDBACK_INGESTED accepts correct labels"""
        # Should not raise exception
        metrics.RESPONSE_FEEDBACK_INGESTED.labels(
            feedback_type='up'
        )

    def test_token_usage_labels(self):
        """Test TOKEN_USAGE accepts correct labels"""
        metrics.TOKEN_USAGE.labels(
            model='gpt-4',
            type='prompt'
        ).inc()


class TestCollaborationMetrics:
    """Test collaboration-related metrics"""

    def test_collaboration_metrics_exist(self):
        """Test collaboration metrics are initialized"""
        assert metrics.LANGGRAPH_PLANNING_TOTAL is not None
        assert metrics.CIRCUIT_BREAKER_TRIPS is not None
        assert metrics.COLLABORATION_SUCCESS is not None
        assert metrics.COLLABORATION_LATENCY is not None

    def test_collaboration_metric_labels(self):
        """Test collaboration metrics accept correct labels"""
        metrics.LANGGRAPH_PLANNING_TOTAL.labels(
            collaboration_mode='sequential',
            agents_count='3'
        )

        metrics.CIRCUIT_BREAKER_TRIPS.labels(
            circuit_name='test_circuit'
        )

        metrics.COLLABORATION_SUCCESS.labels(
            workflow_type='planning',
            agents_used='2',
            outcome='success'
        )


class TestPreferenceMetrics:
    """Test preference-related metrics"""

    def test_preference_metrics_exist(self):
        """Test preference metrics are initialized"""
        assert metrics.PREFERENCE_INFERENCE_TOTAL is not None
        assert metrics.PREFERENCE_INFERENCE_CONFIDENCE is not None
        assert metrics.PREFERENCE_DECAY_APPLIED_TOTAL is not None

    def test_preference_metric_labels(self):
        """Test preference metrics accept correct labels"""
        metrics.PREFERENCE_INFERENCE_TOTAL.labels(
            preference_key='verbosity',
            direction='increase',
            source='feedback'
        ).inc()

        metrics.PREFERENCE_DECAY_APPLIED_TOTAL.labels(
            preference_key='verbosity',
            action='decay'
        ).inc()
