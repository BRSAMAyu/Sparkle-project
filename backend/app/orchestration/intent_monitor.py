"""
Intent Recognition Monitoring & Metrics

Phase 2.3: Production monitoring with Prometheus metrics.
Target: Real-time observability of classification performance.

This module provides:
- Prometheus metrics for classification accuracy, latency, LLM fallback rate
- Intent distribution tracking
- Cache performance monitoring
- Tier-1/2/3 classification timing breakdown
- Export metrics for Grafana dashboard integration
"""

import time
import json
from typing import Dict, Optional, List
from collections import defaultdict
from datetime import datetime, timedelta
from loguru import logger

try:
    from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not installed, metrics disabled")


class IntentMonitor:
    """Intent classification performance monitoring

    Tracks:
    - Classification accuracy (via feedback loop)
    - Latency breakdown (Tier-1/2/3, cache, etc.)
    - LLM fallback rate
    - Intent distribution
    - Cache hit rate

    Metrics exposed at /metrics endpoint for Prometheus scraping.
    """

    def __init__(self, enabled: bool = True):
        """Initialize intent monitor

        Args:
            enabled: Enable/disable monitoring (useful for testing)
        """
        self.enabled = enabled and PROMETHEUS_AVAILABLE

        if not self.enabled:
            logger.warning("IntentMonitor disabled (prometheus_client not installed or explicitly disabled)")
            return

        # Create custom registry (to avoid conflicts with other metrics)
        self.registry = CollectorRegistry()

        # === Counters ===
        self.classification_total = Counter(
            'intent_classification_total',
            'Total number of intent classifications',
            ['intent', 'source'],  # source: keyword, bert, llm, cache
            registry=self.registry
        )

        self.llm_fallback_total = Counter(
            'intent_llm_fallback_total',
            'Total number of LLM fallbacks',
            registry=self.registry
        )

        self.cache_hits = Counter(
            'intent_cache_hits_total',
            'Total number of cache hits',
            registry=self.registry
        )

        self.cache_misses = Counter(
            'intent_cache_misses_total',
            'Total number of cache misses',
            registry=self.registry
        )

        # === Histograms (latency) ===
        self.classification_latency = Histogram(
            'intent_classification_latency_ms',
            'Intent classification latency',
            ['tier'],  # tier: tier1, tier2, tier3, cache
            buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000, 5000],
            registry=self.registry
        )

        self.end_to_end_latency = Histogram(
            'intent_end_to_end_latency_ms',
            'End-to-end intent classification latency',
            buckets=[5, 10, 25, 50, 100, 250, 500, 1000, 2000, 5000],
            registry=self.registry
        )

        # === Gauges ===
        self.llm_fallback_rate = Gauge(
            'intent_llm_fallback_rate',
            'LLM fallback rate (percentage)',
            registry=self.registry
        )

        self.cache_hit_rate = Gauge(
            'intent_cache_hit_rate',
            'Cache hit rate (percentage)',
            registry=self.registry
        )

        self.accuracy_gauge = Gauge(
            'intent_classification_accuracy',
            'Intent classification accuracy (percentage)',
            registry=self.registry
        )

        # === Info ===
        self.monitor_info = Info(
            'intent_monitor_info',
            'Intent monitor information',
            registry=self.registry
        )

        # Initialize info
        self.monitor_info.info({
            'version': '2.0',
            'features': 'keyword,bert,llm,cache,profiling'
        })

        # === Internal state for rate calculation ===
        self._total_classifications = 0
        self._llm_fallbacks = 0
        self._cache_hits_count = 0
        self._cache_misses_count = 0

        # Accuracy tracking
        self._correct_predictions = 0
        self._total_predictions = 0

        # Intent distribution (for dashboard)
        self._intent_distribution = defaultdict(int)

        logger.info("IntentMonitor initialized with Prometheus metrics")

    def record_classification(
        self,
        intent: str,
        confidence: float,
        source: str,
        tier: str = "tier1",
        latency_ms: float = 0,
        user_id: str = None
    ):
        """Record a classification event

        Args:
            intent: Predicted intent
            confidence: Confidence score
            source: Classification source (keyword, bert, llm, cache)
            tier: Classification tier (tier1, tier2, tier3, cache)
            latency_ms: Classification latency in milliseconds
            user_id: Optional user ID
        """
        if not self.enabled:
            return

        try:
            # Update counters
            self.classification_total.labels(intent=intent, source=source).inc()
            self._total_classifications += 1

            # Update intent distribution
            self._intent_distribution[intent] += 1

            # Track LLM fallback
            if source == "llm":
                self.llm_fallback_total.inc()
                self._llm_fallbacks += 1

            # Update latency histogram
            if latency_ms > 0:
                self.classification_latency.labels(tier=tier).observe(latency_ms)

            # Update rates
            self._update_rates()

            logger.debug(f"Recorded classification: {intent} (conf={confidence:.2f}, src={source}, lat={latency_ms:.1f}ms)")

        except Exception as e:
            logger.warning(f"Failed to record classification: {e}")

    def record_cache_hit(self, latency_ms: float = 0):
        """Record a cache hit

        Args:
            latency_ms: Cache lookup latency in milliseconds
        """
        if not self.enabled:
            return

        try:
            self.cache_hits.inc()
            self._cache_hits_count += 1

            if latency_ms > 0:
                self.classification_latency.labels(tier="cache").observe(latency_ms)

            self._update_rates()

            logger.debug(f"Recorded cache hit: {latency_ms:.1f}ms")

        except Exception as e:
            logger.warning(f"Failed to record cache hit: {e}")

    def record_cache_miss(self):
        """Record a cache miss"""
        if not self.enabled:
            return

        try:
            self.cache_misses.inc()
            self._cache_misses_count += 1

            self._update_rates()

            logger.debug("Recorded cache miss")

        except Exception as e:
            logger.warning(f"Failed to record cache miss: {e}")

    def record_accuracy(self, predicted_intent: str, actual_intent: str):
        """Record classification accuracy (via feedback loop)

        Args:
            predicted_intent: Intent that was predicted
            actual_intent: Ground truth intent (from user feedback)
        """
        if not self.enabled:
            return

        try:
            self._total_predictions += 1

            if predicted_intent == actual_intent:
                self._correct_predictions += 1

            # Update accuracy gauge
            if self._total_predictions > 0:
                accuracy = (self._correct_predictions / self._total_predictions) * 100
                self.accuracy_gauge.set(accuracy)

            logger.debug(f"Recorded accuracy: {predicted_intent} vs {actual_intent} (acc={accuracy:.1f}%)")

        except Exception as e:
            logger.warning(f"Failed to record accuracy: {e}")

    def record_end_to_end_latency(self, latency_ms: float):
        """Record end-to-end classification latency

        Args:
            latency_ms: Total latency in milliseconds
        """
        if not self.enabled:
            return

        try:
            self.end_to_end_latency.observe(latency_ms)
            logger.debug(f"Recorded e2e latency: {latency_ms:.1f}ms")

        except Exception as e:
            logger.warning(f"Failed to record e2e latency: {e}")

    def _update_rates(self):
        """Update rate gauges (fallback rate, cache hit rate)"""
        if not self.enabled:
            return

        try:
            # LLM fallback rate
            if self._total_classifications > 0:
                fallback_rate = (self._llm_fallbacks / self._total_classifications) * 100
                self.llm_fallback_rate.set(fallback_rate)

            # Cache hit rate
            total_cache_requests = self._cache_hits_count + self._cache_misses_count
            if total_cache_requests > 0:
                hit_rate = (self._cache_hits_count / total_cache_requests) * 100
                self.cache_hit_rate.set(hit_rate)

        except Exception as e:
            logger.warning(f"Failed to update rates: {e}")

    def get_intent_distribution(self) -> Dict[str, int]:
        """Get current intent distribution

        Returns:
            Dict mapping intent -> count
        """
        return dict(self._intent_distribution)

    def get_metrics_summary(self) -> Dict:
        """Get summary of all metrics

        Returns:
            {
                "total_classifications": 1500,
                "llm_fallback_rate": 15.2,
                "cache_hit_rate": 62.5,
                "accuracy": 95.3,
                "intent_distribution": {...}
            }
        """
        if not self.enabled:
            return {"enabled": False}

        try:
            # Get rates
            fallback_rate = self.llm_fallback_rate._value() if hasattr(self.llm_fallback_rate, '_value') else 0
            hit_rate = self.cache_hit_rate._value() if hasattr(self.cache_hit_rate, '_value') else 0
            accuracy = self.accuracy_gauge._value() if hasattr(self.accuracy_gauge, '_value') else 0

            return {
                "total_classifications": self._total_classifications,
                "llm_fallbacks": self._llm_fallbacks,
                "llm_fallback_rate": round(fallback_rate, 1),
                "cache_hits": self._cache_hits_count,
                "cache_misses": self._cache_misses_count,
                "cache_hit_rate": round(hit_rate, 1),
                "total_predictions": self._total_predictions,
                "correct_predictions": self._correct_predictions,
                "accuracy": round(accuracy, 1) if self._total_predictions > 0 else 0,
                "intent_distribution": dict(self._intent_distribution)
            }

        except Exception as e:
            logger.warning(f"Failed to get metrics summary: {e}")
            return {"error": str(e)}

    def generate_metrics_report(self) -> str:
        """Generate human-readable metrics report

        Returns:
            Formatted report string
        """
        if not self.enabled:
            return "Monitoring disabled"

        summary = self.get_metrics_summary()

        report = f"""
Intent Classification Metrics Report
{'='*50}

Total Classifications: {summary.get('total_classifications', 0)}
LLM Fallbacks: {summary.get('llm_fallbacks', 0)}
LLM Fallback Rate: {summary.get('llm_fallback_rate', 0)}%

Cache Performance:
  Hits: {summary.get('cache_hits', 0)}
  Misses: {summary.get('cache_misses', 0)}
  Hit Rate: {summary.get('cache_hit_rate', 0)}%

Accuracy:
  Predictions: {summary.get('total_predictions', 0)}
  Correct: {summary.get('correct_predictions', 0)}
  Accuracy: {summary.get('accuracy', 0)}%

Intent Distribution:
"""

        for intent, count in summary.get('intent_distribution', {}).items():
            report += f"  {intent}: {count}\n"

        return report

    def reset_metrics(self):
        """Reset all metrics (useful for testing)"""
        if not self.enabled:
            return

        try:
            self._total_classifications = 0
            self._llm_fallbacks = 0
            self._cache_hits_count = 0
            self._cache_misses_count = 0
            self._correct_predictions = 0
            self._total_predictions = 0
            self._intent_distribution.clear()

            # Reset Prometheus gauges
            self.llm_fallback_rate.set(0)
            self.cache_hit_rate.set(0)
            self.accuracy_gauge.set(0)

            logger.info("Metrics reset")

        except Exception as e:
            logger.warning(f"Failed to reset metrics: {e}")

    def get_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus text format

        Returns:
            Prometheus-compatible metrics text
        """
        if not self.enabled:
            return "# Monitoring disabled\n"

        try:
            from prometheus_client import generate_latest, REGISTRY

            # Generate from our custom registry
            return generate_latest(self.registry).decode('utf-8')

        except Exception as e:
            logger.warning(f"Failed to generate Prometheus metrics: {e}")
            return f"# Error generating metrics: {e}\n"


# Singleton instance
_intent_monitor = None


def get_intent_monitor(enabled: bool = True) -> Optional[IntentMonitor]:
    """Get singleton intent monitor instance

    Args:
        enabled: Enable/disable monitoring

    Returns:
        IntentMonitor instance or None if not available
    """
    global _intent_monitor

    if _intent_monitor is None:
        _intent_monitor = IntentMonitor(enabled=enabled)

    return _intent_monitor


def record_classification(
    intent: str,
    confidence: float,
    source: str,
    tier: str = "tier1",
    latency_ms: float = 0
):
    """Convenience function to record classification

    Args:
        intent: Predicted intent
        confidence: Confidence score
        source: Classification source
        tier: Classification tier
        latency_ms: Latency in milliseconds
    """
    monitor = get_intent_monitor()
    if monitor:
        monitor.record_classification(intent, confidence, source, tier, latency_ms)


def record_cache_result(hit: bool, latency_ms: float = 0):
    """Convenience function to record cache result

    Args:
        hit: True if cache hit, False if miss
        latency_ms: Cache lookup latency
    """
    monitor = get_intent_monitor()
    if monitor:
        if hit:
            monitor.record_cache_hit(latency_ms)
        else:
            monitor.record_cache_miss()


def get_metrics_summary() -> Dict:
    """Convenience function to get metrics summary"""
    monitor = get_intent_monitor()
    if monitor:
        return monitor.get_metrics_summary()
    return {"enabled": False}


def generate_prometheus_metrics() -> str:
    """Convenience function to generate Prometheus metrics"""
    monitor = get_intent_monitor()
    if monitor:
        return monitor.get_prometheus_metrics()
    return "# Monitoring disabled\n"
