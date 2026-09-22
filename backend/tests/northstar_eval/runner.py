"""NORTHSTAR · 北极星评估 runner CLI（三臂旅程推演，Q-01 runner 模式复刻）。

用法（backend/ 下）::

    SECRET_KEY=test python3 -m tests.northstar_eval.runner                          # 空库 → 汇总诚实为 0
    SECRET_KEY=test python3 -m tests.northstar_eval.runner --spec-case              # NS-001 spec case 三臂推演
    SECRET_KEY=test python3 -m tests.northstar_eval.runner --journeys /tmp/ns.jsonl --out /tmp/nsrun.json

acceptance 钉面：结果 JSON schema 稳定（版本字段 + 固定键集）；unsupported 不算 PASS
（诚实降级）；真实 LLM 0 次；臂效应参数是假设先验并逐轮披露（meta.prior_disclosure）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .grading import VERDICT_UNSUPPORTED, AttemptResult, attempt_verdict, grade_attempt
from .journey_schema import ARM_SPARKLE, Journey, default_journeys_path, load_journeys, spec_case_journey
from .metrics import compute_journey_metrics
from .simulator import simulate_journey

RESULTS_SCHEMA_VERSION = "sparkle.northstar.journey-results.v1"

#: verdict 语义声明（冻结文案；写入每轮 meta，防误读为增益证据）。
VERDICT_SEMANTICS = (
    "gain-simulation: verdicts judge a deterministic hypothesis-prior reference simulation of the "
    "NORTHSTAR spec-case contract, NOT the production system and NOT evidence of learning gain; "
    "per-checkpoint provenance in evidence; real-world checkpoints degrade honestly and never count as PASS"
)

#: 先验披露（冻结文案；任何一轮都必须携带，防止 surrogate 数字被当成实测）。
PRIOR_DISCLOSURE = (
    "ARM_PRIORS are hypothesis priors wired for pipeline smoke only; gain evidence may only come "
    "from the real three-arm control protocol (v3-output/NORTHSTAR/EVAL_FRAMEWORK.md section 2)"
)

#: summary 臂间比较的冻结键集（sparkle − 最优对照；forgetting 取对照最小值）。
DELTA_KEYS = ("gain", "gain_per_hour", "weighted_coverage", "review_hit_rate")


@dataclass(frozen=True)
class ProviderConfig:
    """provider 配置（--provider-config JSON 的冻结 schema；本轮只允许 mock）。"""

    provider: str = "mock"
    model: str = "reference-mock-v1"

    @property
    def is_mock(self) -> bool:
        return self.provider == "mock"

    def to_payload(self) -> dict[str, Any]:
        return {"provider": self.provider, "model": self.model}


def parse_provider_config(raw: dict[str, Any] | None) -> ProviderConfig:
    raw = raw or {}
    return ProviderConfig(provider=str(raw.get("provider", "mock")), model=str(raw.get("model", "reference-mock-v1")))


def _git_sha() -> str:
    override = os.environ.get("NORTHSTAR_EVAL_GIT_SHA")
    if override:
        return override
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=5, check=True
        ).stdout.strip()
    except Exception:
        return "unknown"


def derive_attempt_seed(run_seed: int, journey_id: str, arm: str, attempt: int) -> int:
    """per-(journey, arm, attempt) seed（sha256 稳定派生；跨进程/跨平台一致）。"""
    digest = hashlib.sha256(f"{run_seed}:{journey_id}:{arm}:{attempt}".encode()).digest()
    return int.from_bytes(digest[:4], "big")


def _unsupported_reason(attempt_result: AttemptResult) -> str | None:
    if attempt_result.verdict != VERDICT_UNSUPPORTED:
        return None
    reasons = [item.detail for item in attempt_result.items if item.status == "unsupported"]
    return "; ".join(sorted(set(reasons)))


def run_case_arm(
    journey: Journey, arm: str, run_seed: int, attempt: int, provider_config: ProviderConfig
) -> dict[str, Any]:
    """单旅程单臂单 attempt：模拟 → 指标 → 判定（provider_config 只进 provenance，本轮 mock-only）。"""
    seed = derive_attempt_seed(run_seed, journey.journey_id, arm, attempt)
    run = simulate_journey(journey, arm, seed)
    metrics = compute_journey_metrics(run.observations)
    items = grade_attempt(journey.expected, run.observations, metrics)
    attempt_result = AttemptResult(
        attempt=attempt, seed=seed, verdict=attempt_verdict(items), items=items, metrics=metrics
    )
    return {
        "journey_id": journey.journey_id,
        "arm": arm,
        "attempt": attempt,
        "seed": seed,
        "verdict": attempt_result.verdict,
        "reason": _unsupported_reason(attempt_result),
        "checkpoints": attempt_result.to_payload()["items"],
        "metrics": dict(metrics),
        "trace_ref": None,  # 由 write_evidence 落盘时回填
        "evidence": {
            "provenance": "reference-mock" if provider_config.is_mock else provider_config.provider,
            "seed_base": run_seed,
        },
    }


def _arm_mean_metrics(cases: list[dict[str, Any]]) -> dict[str, float]:
    keys = (
        "gain",
        "gain_per_hour",
        "forgetting_rate",
        "weighted_coverage",
        "review_hit_rate",
        "mistake_sync_ratio",
        "adaptive_day_ratio",
        "mastery_calibration_error",
    )
    if not cases:
        return dict.fromkeys(keys, 0.0)
    return {key: round(sum(case["metrics"][key] for case in cases) / len(cases), 4) for key in keys}


def _summarize(cases: list[dict[str, Any]]) -> dict[str, Any]:
    by_arm_verdicts: dict[str, dict[str, int]] = {}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for case in cases:
        arm_bucket = by_arm_verdicts.setdefault(case["arm"], {"pass": 0, "fail": 0, "unsupported": 0})
        arm_bucket[case["verdict"]] += 1
        grouped.setdefault(case["arm"], []).append(case)
    verdict_totals = {"pass": 0, "fail": 0, "unsupported": 0}
    for bucket in by_arm_verdicts.values():
        for verdict, count in bucket.items():
            verdict_totals[verdict] += count
    metrics_by_arm = {arm: _arm_mean_metrics(cases_of_arm) for arm, cases_of_arm in sorted(grouped.items())}
    delta: dict[str, float] = {}
    if ARM_SPARKLE in grouped:
        controls = [arm for arm in grouped if arm != ARM_SPARKLE]
        if controls:
            sparkle = metrics_by_arm[ARM_SPARKLE]
            best = {key: max(metrics_by_arm[arm][key] for arm in controls) for key in DELTA_KEYS}
            best["forgetting_rate"] = min(metrics_by_arm[arm]["forgetting_rate"] for arm in controls)
            delta = {key: round(sparkle[key] - best[key], 4) for key in DELTA_KEYS + ("forgetting_rate",)}
    return {
        "total": len(cases),
        "pass": verdict_totals["pass"],
        "fail": verdict_totals["fail"],
        "unsupported": verdict_totals["unsupported"],
        "by_arm": by_arm_verdicts,
        "metrics_by_arm": metrics_by_arm,
        "sparkle_minus_best_control": delta,
    }


def run_round(
    run_seed: int = 7,
    journeys: list[Journey] | None = None,
    provider_raw: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """全量一轮：旅程 × 臂 枚举（每臂 1 attempt/轮；重复用不同 run_seed 调用）→ 稳定 payload。"""
    provider_config = parse_provider_config(provider_raw)
    if not provider_config.is_mock:
        raise ValueError(
            f"provider {provider_config.provider!r} refused: real LLM calls are forbidden this round "
            "(zero-call red line); only provider='mock' is accepted"
        )
    journeys = journeys or []
    cases = [run_case_arm(journey, arm, run_seed, 1, provider_config) for journey in journeys for arm in journey.arms]
    return {
        "schema": RESULTS_SCHEMA_VERSION,
        "meta": {
            "git_sha": _git_sha(),
            "generated_at": datetime.now(UTC).isoformat(),
            "run_seed": run_seed,
            "provider_config": provider_config.to_payload(),
            "real_llm_calls": 0,
            "journey_source": "inline" if journeys else str(default_journeys_path()),
            "journey_count": len(journeys),
            "verdict_semantics": VERDICT_SEMANTICS,
            "prior_disclosure": PRIOR_DISCLOSURE,
        },
        "summary": _summarize(cases),
        "cases": cases,
    }


def strip_volatile(payload: dict[str, Any]) -> dict[str, Any]:
    """剔除时间戳/git 等易变字段，供逐字节确定性比对。"""
    cloned = json.loads(json.dumps(payload, ensure_ascii=False))
    cloned["meta"].pop("generated_at", None)
    cloned["meta"].pop("git_sha", None)
    return cloned


def write_evidence(payload: dict[str, Any], out_path: Path) -> None:
    """落盘 results JSON + 逐 case evidence 文件，并回填 trace_ref。"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_dir = out_path.parent / "evidence"
    evidence_dir.mkdir(exist_ok=True)
    for case in payload["cases"]:
        case_id = f"{case['journey_id']}_{case['arm']}_{case['attempt']:02d}"
        evidence = {
            "schema": RESULTS_SCHEMA_VERSION,
            "journey_id": case["journey_id"],
            "arm": case["arm"],
            "verdict": case["verdict"],
            "reason": case["reason"],
            "checkpoints": case["checkpoints"],
            "metrics": case["metrics"],
            "provenance": case["evidence"]["provenance"],
        }
        evidence_file = evidence_dir / f"{case_id}.json"
        evidence_file.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        case["trace_ref"] = f"evidence/{case_id}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NORTHSTAR journey runner skeleton (three arms)")
    parser.add_argument("--out", type=Path, default=None, help="write JSON here (default stdout)")
    parser.add_argument("--seed", type=int, default=7, help="base run seed (default 7)")
    parser.add_argument(
        "--journeys", type=Path, default=None, help="journey JSONL path (default env or package default)"
    )
    parser.add_argument("--spec-case", action="store_true", help="run the frozen NS-001 spec case (three arms)")
    parser.add_argument("--provider-config", type=Path, default=None, help="provider config JSON; mock-only this round")
    args = parser.parse_args(argv)

    if args.spec_case:
        journeys = [spec_case_journey()]
    else:
        journeys_path = args.journeys or default_journeys_path()
        journeys = load_journeys(journeys_path) if journeys_path.exists() else []

    provider_raw = None
    if args.provider_config:
        provider_raw = json.loads(args.provider_config.read_text(encoding="utf-8"))
    payload = run_round(run_seed=args.seed, journeys=journeys, provider_raw=provider_raw)
    if args.out:
        write_evidence(payload, args.out)
        print(
            f"wrote {payload['summary']['total']} case results -> {args.out} "
            f"(pass={payload['summary']['pass']} fail={payload['summary']['fail']} "
            f"unsupported={payload['summary']['unsupported']} real_llm_calls={payload['meta']['real_llm_calls']})",
            file=sys.stderr,
        )
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
