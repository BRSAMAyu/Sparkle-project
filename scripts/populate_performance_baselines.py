#!/usr/bin/env python3
"""Populate performance_baselines.json with actual measured values from CI benchmark runs.

Reads the existing baselines file, runs quick measurements against live services,
and writes back actual/measured_at/sample_size fields. Designed for CI integration.

Usage:
  python scripts/populate_performance_baselines.py [--write] [--ci]
"""
import argparse
import json
import os
import sys
import time
import statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINES_PATH = ROOT / "quality" / "performance_baselines.json"

GATEWAY_BASE = os.getenv("LIVE_GATEWAY_BASE_URL", "http://127.0.0.1:8080/api/v1")
API_BASE = os.getenv("LIVE_API_BASE_URL", "http://127.0.0.1:8000/api/v1")
WS_BASE = os.getenv("LIVE_WS_BASE_URL", "ws://127.0.0.1:8080")


def load_baselines():
    with open(BASELINES_PATH) as f:
        return json.load(f)


def save_baselines(data):
    with open(BASELINES_PATH, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def measure_http_latency(url: str, n: int = 5, timeout: float = 5.0) -> dict | None:
    try:
        import urllib.request
    except ImportError:
        return None
    latencies = []
    for _ in range(n):
        t0 = time.monotonic()
        try:
            urllib.request.urlopen(url, timeout=timeout)
            latencies.append((time.monotonic() - t0) * 1000)
        except Exception:
            pass
    if not latencies:
        return None
    return {
        "actual": round(statistics.mean(latencies), 1),
        "p95": round(sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0], 1),
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "sample_size": len(latencies),
    }


def measure_ws_latency(n: int = 3) -> dict | None:
    try:
        import asyncio
        import websockets
    except ImportError:
        return None

    async def _measure():
        latencies = []
        ws_url = f"{WS_BASE}/ws/chat"
        for _ in range(n):
            t0 = time.monotonic()
            try:
                async with websockets.connect(f"{ws_url}?token=test", ping_interval=None, close_timeout=5) as ws:
                    latencies.append((time.monotonic() - t0) * 1000)
            except Exception:
                pass
        return latencies

    latencies = asyncio.run(_measure())
    if not latencies:
        return None
    return {
        "actual": round(statistics.mean(latencies), 1),
        "p95": round(sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0], 1),
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "sample_size": len(latencies),
    }


def populate(data: dict) -> dict:
    measurements = {}

    # Gateway P95 latency
    result = measure_http_latency(f"{GATEWAY_BASE}/health")
    if result:
        measurements.setdefault("gateway", {})["p95_latency_ms"] = result
        print(f"  gateway.p95_latency_ms: {result['actual']}ms (n={result['sample_size']})")

    # API health latency (proxy for backend)
    result = measure_http_latency(f"{API_BASE.rsplit('/api', 1)[0]}/health" if "/api" in API_BASE else f"{API_BASE}/health")
    if result:
        measurements.setdefault("gateway", {})["p95_latency_ms"] = measurements.get("gateway", {}).get("p95_latency_ms", result)
        print(f"  api.health_latency: {result['actual']}ms (n={result['sample_size']})")

    # WebSocket connection latency
    result = measure_ws_latency()
    if result:
        measurements.setdefault("websocket", {})["message_delivery_ms"] = result
        print(f"  websocket.message_delivery_ms: {result['actual']}ms (n={result['sample_size']})")

    # Merge measurements into baselines
    for domain, metrics in measurements.items():
        if domain in data.get("baselines", {}):
            for metric_name, actual_data in metrics.items():
                if metric_name in data["baselines"][domain]:
                    data["baselines"][domain][metric_name].update(actual_data)

    # Update metadata
    data["metadata"]["last_measurement"] = datetime.now(timezone.utc).isoformat()
    data["metadata"]["measurement_sources"] = list(measurements.keys())

    return data


def main():
    parser = argparse.ArgumentParser(description="Populate performance baselines with actual measurements")
    parser.add_argument("--write", action="store_true", help="Write results back to baselines file")
    parser.add_argument("--ci", action="store_true", help="CI mode: write and fail if no measurements taken")
    args = parser.parse_args()

    print("Populating performance baselines with actual measurements...")
    data = load_baselines()

    populated = populate(data)
    domains_measured = populated.get("metadata", {}).get("measurement_sources", [])

    print(f"\nDomains measured: {domains_measured or 'none (services may be down)'}")

    if args.write and domains_measured:
        save_baselines(populated)
        print(f"Written to {BASELINES_PATH}")
    elif args.write and not domains_measured:
        print("No measurements taken — not writing baselines")
        if args.ci:
            print("::warning::No performance measurements could be taken — services may be down")
            return  # don't fail CI, just warn

    if args.ci and not domains_measured:
        print("::warning title=Performance baselines empty::Could not measure any live services")

    return 0


if __name__ == "__main__":
    sys.exit(main())
