"""M-02 Storage Gate 写入场景评测基准（precision/recall 回归守卫）。

数据驱动：backend/tests/fixtures/memory_storage_gate_eval_v1.json（50+ 场景）。
口径：规则层（语义层关闭）+ gate live 模式 —— 基准数字可复现、不依赖 LLM。
任何场景误判都会在此处失败，防止 gate 词表/规则顺序回归。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from app.config import settings
from app.services.memory_storage_gate import (
    MemoryStorageGate,
    StorageGateCandidate,
    StorageGateVerdict,
    reset_gate_state,
)

EVAL_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "memory_storage_gate_eval_v1.json"

# 回归阈值：每类 precision / recall 下限（当前基准为 1.0，词表演进时允许
# 审慎下调，但不得低于任务卡验收口径的可用下限）。
MIN_SCENARIOS = 50
PER_CLASS_MIN_PRECISION = 1.0
PER_CLASS_MIN_RECALL = 1.0


def load_scenarios() -> list[dict]:
    payload = json.loads(EVAL_FIXTURE.read_text(encoding="utf-8"))
    return payload["scenarios"]


def _to_candidate(scenario: dict, index: int) -> StorageGateCandidate:
    due_at_raw = scenario.get("due_at")
    return StorageGateCandidate(
        user_id="eval-user",
        summary=scenario["summary"],
        subject_type=scenario.get("subject_type", "self"),
        source_type=scenario.get("source_type", "chat"),
        source_lane=scenario.get("source_lane", "inferred_extraction"),
        semantic_key=scenario.get("semantic_key") or f"eval-{scenario['id']}-{index}",
        evidence_token=f"eval-token-{index}",
        confidence=float(scenario.get("confidence", 0.8)),
        due_at=datetime.fromisoformat(due_at_raw) if due_at_raw else None,
        tags=(),
        evidence_schema_versions=tuple(scenario.get("evidence_schema_versions", ())),
    )


async def run_eval() -> tuple[list[dict], dict[str, dict[str, float]]]:
    """Run the fixture through the gate; return per-scenario results + metrics."""
    reset_gate_state()
    gate = MemoryStorageGate()
    results: list[dict] = []
    for index, scenario in enumerate(load_scenarios()):
        decision = await gate.evaluate(_to_candidate(scenario, index))
        results.append(
            {
                "id": scenario["id"],
                "expected": scenario["expected"],
                "predicted": decision.verdict,
                "reason": decision.reason,
                "layer": decision.layer,
            }
        )
    metrics: dict[str, dict[str, float]] = {}
    for klass in StorageGateVerdict:
        expected = sum(1 for r in results if r["expected"] == klass.value)
        predicted = sum(1 for r in results if r["predicted"] == klass.value)
        tp = sum(1 for r in results if r["expected"] == klass.value and r["predicted"] == klass.value)
        precision = tp / predicted if predicted else 1.0
        recall = tp / expected if expected else 1.0
        metrics[klass.value] = {
            "expected": expected,
            "predicted": predicted,
            "tp": tp,
            "precision": precision,
            "recall": recall,
        }
    return results, metrics


@pytest.fixture(autouse=True)
def _deterministic_gate(monkeypatch):
    reset_gate_state()
    monkeypatch.setattr(settings, "SPARKLE_STORAGE_GATE_SEMANTIC_ENABLED", False, raising=False)

    async def _live_mode(self):
        return "live"

    monkeypatch.setattr(MemoryStorageGate, "_gate_mode", _live_mode)
    yield
    reset_gate_state()


@pytest.mark.asyncio
async def test_eval_set_has_at_least_50_scenarios():
    scenarios = load_scenarios()
    assert len(scenarios) >= MIN_SCENARIOS
    classes = {s["expected"] for s in scenarios}
    assert classes == {v.value for v in StorageGateVerdict}


@pytest.mark.asyncio
async def test_eval_precision_recall_thresholds():
    results, metrics = await run_eval()
    for klass, m in metrics.items():
        assert m["precision"] >= PER_CLASS_MIN_PRECISION, f"{klass} precision {m}"
        assert m["recall"] >= PER_CLASS_MIN_RECALL, f"{klass} recall {m}"
    # 全对：隐含 accuracy == 1.0
    assert all(r["expected"] == r["predicted"] for r in results)


@pytest.mark.asyncio
async def test_eval_transient_today_constraint_not_global():
    """验收专项：一次性时间约束（明早8点/今天下午N点）判 event（有界 scope），
    绝不默认 store/global。"""
    results, _ = await run_eval()
    by_id = {r["id"]: r for r in results}
    for scenario_id in ("m02-ev01", "m02-ev09"):
        assert by_id[scenario_id]["predicted"] == "event", by_id[scenario_id]
