"""X-10 · 场景集加载与校验（封闭 schema；stdlib + pydantic-free 纯数据）.

单一事实来源：``backend/tests/fixtures/x10_action_e2e_scenarios_v1.json``。
本模块只做加载、计数、覆盖矩阵与防御性校验——判定/执行逻辑分属
``verdicts.py`` / ``executors.py``（同 Q-01 三模块纪律）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCENARIOS_SCHEMA_VERSION = "sparkle.x10.action-e2e.scenarios.v1"

#: 场景家族（封闭）：allocation × action 闭环 × golden journeys。
FAMILIES: frozenset[str] = frozenset(
    {"allocation", "authorization", "proposal", "run_steps", "outcome", "journey"}
)

GOLDEN_JOURNEYS: frozenset[str] = frozenset({"GJ04", "GJ05", "GJ06", "GJ07"})

#: 六元组字段（每场景必须完整记录）。
SIX_TUPLE_KEYS: tuple[str, ...] = (
    "decision",
    "execution",
    "result",
    "outcome",
    "latency",
    "cost",
)

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "x10_action_e2e_scenarios_v1.json"


@dataclass(frozen=True)
class Scenario:
    """一个评测场景（不可变；inputs/expected 原样保留供 executor/verdict 消费）。"""

    scenario_id: str
    family: str
    category: str
    summary: str
    inputs: dict[str, Any]
    expected: dict[str, Any]
    journey: str | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


def load_scenarios(path: Path | None = None) -> list[Scenario]:
    """加载并校验场景集（fail-closed：schema/id/家族越界即 ValueError）。"""
    fixture = path or FIXTURE_PATH
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    if payload.get("schema") != SCENARIOS_SCHEMA_VERSION:
        raise ValueError(f"scenario fixture schema mismatch: {payload.get('schema')!r}")
    scenarios: list[Scenario] = []
    seen: set[str] = set()
    for raw in payload.get("scenarios", []):
        sid = str(raw.get("id") or "").strip()
        if not sid:
            raise ValueError("scenario id required")
        if sid in seen:
            raise ValueError(f"duplicate scenario id {sid!r}")
        seen.add(sid)
        family = str(raw.get("family") or "").strip()
        if family not in FAMILIES:
            raise ValueError(f"scenario {sid!r} family {family!r} out of vocabulary (closed: {sorted(FAMILIES)})")
        journey = raw.get("journey")
        if journey is not None and journey not in GOLDEN_JOURNEYS:
            raise ValueError(f"scenario {sid!r} journey {journey!r} out of vocabulary")
        if not isinstance(raw.get("inputs"), dict) or not isinstance(raw.get("expected"), dict):
            raise ValueError(f"scenario {sid!r} requires dict inputs and expected")
        scenarios.append(
            Scenario(
                scenario_id=sid,
                family=family,
                category=str(raw.get("category") or family),
                summary=str(raw.get("summary") or ""),
                inputs=dict(raw["inputs"]),
                expected=dict(raw["expected"]),
                journey=journey,
                raw=dict(raw),
            )
        )
    if not scenarios:
        raise ValueError("scenario set is empty")
    return scenarios


def scenarios_path(path: Path | None = None) -> Path:
    return path or FIXTURE_PATH


def coverage_matrix(scenarios: list[Scenario]) -> dict[str, Any]:
    """家族×类别覆盖矩阵（报告与守卫共用）。"""
    matrix: dict[str, dict[str, int]] = {}
    for scenario in scenarios:
        matrix.setdefault(scenario.family, {}).setdefault(scenario.category, 0)
        matrix[scenario.family][scenario.category] += 1
    journeys = sorted({s.journey for s in scenarios if s.journey})
    return {
        "total": len(scenarios),
        "families": {f: sum(m.values()) for f, m in matrix.items()},
        "categories": matrix,
        "journeys": journeys,
    }
