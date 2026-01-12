from prometheus_client import Counter, Histogram, Gauge

class ChaosMetrics:
    def __init__(self):
        self.injection_count = Counter('chaos_injection_total', 'Total chaos injections', ['type', 'target'])
        self.recovery_time = Histogram('chaos_recovery_seconds', 'Time to recover from chaos', ['type'])
        self.system_health = Gauge('chaos_system_health', 'System health score (0-1)', ['component'])
    
    def record_injection(self, type: str, target: str):
        self.injection_count.labels(type=type, target=target).inc()
    
    def record_recovery(self, type: str, duration: float):
        self.recovery_time.labels(type=type).observe(duration)
    
    def set_health(self, component: str, score: float):
        self.system_health.labels(component=component).set(score)

chaos_metrics = ChaosMetrics()
