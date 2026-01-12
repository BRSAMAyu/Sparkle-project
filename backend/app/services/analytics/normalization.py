from typing import Dict, Any


class BehaviorNormalizer:
    """
    行为指标归一化
    依据设备性能与网络质量做分桶归一化。
    """

    @staticmethod
    def normalize(payload: Dict[str, Any]) -> Dict[str, Any]:
        duration_ms = payload.get("duration_ms")
        time_spent_ms = payload.get("time_spent_ms")
        device_score = payload.get("device_performance_score", 0.5)
        network_latency = payload.get("network_latency_ms", 200)

        perf_bucket = 1.2 if device_score < 0.4 else 1.0
        net_bucket = 1.1 if network_latency > 400 else 1.0
        factor = perf_bucket * net_bucket

        if duration_ms is not None:
            payload["duration_ms_norm"] = int(duration_ms / factor)
        if time_spent_ms is not None:
            payload["time_spent_ms_norm"] = int(time_spent_ms / factor)

        payload["normalization_factor"] = round(factor, 3)
        return payload
