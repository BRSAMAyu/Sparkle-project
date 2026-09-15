"""
P2-32: Load test baseline runner — executes locust headless and validates against SLO targets.

Usage:
    python backend/tests/load/run_baseline.py --host http://localhost:8080
    python backend/tests/load/run_baseline.py --host http://localhost:8080 --users 100 --spawn-rate 10 --run-time 60s
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOCUSTFILE = HERE / "locustfile.py"
BASELINE = HERE / "baseline.json"


def load_baseline():
    with open(BASELINE) as f:
        return json.load(f)


def run_locust(host: str, users: int, spawn_rate: int, run_time: str) -> dict:
    cmd = [
        sys.executable, "-m", "locust",
        "-f", str(LOCUSTFILE),
        "--host", host,
        "--headless",
        "--users", str(users),
        "--spawn-rate", str(spawn_rate),
        "--run-time", run_time,
        "--csv", str(HERE / "results" / "baseline_run"),
        "--csv-full-history",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def parse_locust_csv(summary_csv: Path) -> dict:
    """Parse locust_stats.csv into structured metrics."""
    import csv
    metrics = {}
    with open(summary_csv) as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["Name"]
            if row["Request Count"] == "Aggregated":
                continue
            metrics[name] = {
                "request_count": int(row["Request Count"]),
                "failure_count": int(row["Failure Count"]),
                "median_ms": float(row["Median Response Time"]),
                "p95_ms": float(row["95%"]),
                "p99_ms": float(row["99%"]),
                "error_rate": (
                    int(row["Failure Count"]) / int(row["Request Count"])
                    if int(row["Request Count"]) > 0
                    else 0
                ),
                "rps": float(row["Requests/s"]),
            }
    return metrics


def evaluate(metrics: dict, baseline: dict) -> list[str]:
    """Compare locust results against baseline SLO targets. Returns list of violations."""
    violations = []
    targets = baseline.get("targets", {}).get("http", {})
    degrade = baseline.get("degradation_thresholds", {})

    for key, target in targets.items():
        actual = metrics.get(key)
        if not actual:
            violations.append(f"MISSING: {key} — no metrics collected")
            continue

        for metric_name, target_val in target.items():
            if metric_name == "target_rps":
                continue
            actual_val = actual.get(metric_name)
            if actual_val is None:
                continue
            if actual_val > target_val:
                critical_factor = degrade.get(f"{metric_name}_critical_factor", 5.0)
                severity = "CRITICAL" if actual_val > target_val * critical_factor else "WARNING"
                violations.append(
                    f"{severity}: {key}.{metric_name}={actual_val:.1f} > target={target_val} "
                    f"(×{actual_val/target_val:.1f})"
                )

    return violations


def main():
    parser = argparse.ArgumentParser(description="Sparkle load test baseline runner")
    parser.add_argument("--host", default="http://localhost:8080", help="Target host URL")
    parser.add_argument("--users", type=int, default=50, help="Number of simulated users")
    parser.add_argument("--spawn-rate", type=int, default=5, help="Users spawned per second")
    parser.add_argument("--run-time", default="60s", help="Test duration (e.g., 60s, 5m)")
    parser.add_argument("--validate-only", action="store_true", help="Skip run, validate existing CSV")
    args = parser.parse_args()

    baseline = load_baseline()
    targets = baseline.get("targets", {}).get("http", {})
    print(f"Baseline: {len(targets)} HTTP endpoint targets loaded")
    print(f"Host: {args.host} | Users: {args.users} | Runtime: {args.run_time}")

    results_dir = HERE / "results"
    results_dir.mkdir(exist_ok=True)

    if not args.validate_only:
        print("\nRunning locust...")
        result = run_locust(args.host, args.users, args.spawn_rate, args.run_time)
        if result["exit_code"] != 0:
            print(f"Locust exited with code {result['exit_code']}")
            print(result["stderr"][-2000:])
            sys.exit(result["exit_code"])

    stats_csv = results_dir / "baseline_run_stats.csv"
    if not stats_csv.exists():
        # locust sometimes appends _stats.csv differently
        candidates = sorted(results_dir.glob("*stats*.csv"))
        if candidates:
            stats_csv = candidates[-1]
        else:
            print("ERROR: No stats CSV found in results directory")
            sys.exit(1)

    metrics = parse_locust_csv(stats_csv)
    violations = evaluate(metrics, baseline)

    print(f"\n{'='*60}")
    print(f"Baseline Evaluation — {len(metrics)} endpoints measured")
    print(f"{'='*60}")

    for name, m in sorted(metrics.items()):
        target = targets.get(name, {})
        p95_target = target.get("p95_ms", "N/A")
        print(f"\n{name}:")
        print(f"  Requests: {m['request_count']} | Failures: {m['failure_count']} | RPS: {m['rps']:.1f}")
        print(f"  p50: {m['median_ms']:.0f}ms | p95: {m['p95_ms']:.0f}ms (target: {p95_target}) | p99: {m['p99_ms']:.0f}ms")
        print(f"  Error rate: {m['error_rate']:.4f} (target: {target.get('error_rate', 'N/A')})")

    print(f"\n{'='*60}")
    if violations:
        print(f"VIOLATIONS: {len(violations)}")
        for v in violations:
            print(f"  - {v}")
        sys.exit(1)
    else:
        print("PASS: All metrics within SLO targets")
        sys.exit(0)


if __name__ == "__main__":
    main()
