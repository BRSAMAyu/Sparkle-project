"""Q-01 · V3 scenario library 装载与冻结校验（`v3/05_metrics_eval/scenarios_v3.jsonl`）。

单一事实来源是 `scenarios_v3.jsonl`（260 行，每行一个 case）。本模块只做装载与
校验，不改写场景语义。冻结面：

- 字段集九项（case_id/category/persona_id/goal/run_mode/must_preserve/repeat/input/expected）；
- run_mode 三值 ↔ harness 三类路由（integration→deterministic / model→model / simulator→simulator）；
- persona_id 必须存在于 `persona_library.json`；
- case_id 必须恰为 V3-001..V3-260 无缺无重（acceptance：260 case 可枚举）；
- must_preserve 词表 ⊆ 冻结三项（truthfulness / user isolation / no false success）。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCENARIO_COUNT = 260
SCENARIO_FIELDS = (
    "case_id",
    "category",
    "persona_id",
    "goal",
    "run_mode",
    "must_preserve",
    "repeat",
    "input",
    "expected",
)

#: run_mode 词表（冻结，来自场景库实测三值）。
RUN_MODE_INTEGRATION = "integration"
RUN_MODE_MODEL = "model"
RUN_MODE_SIMULATOR = "simulator"
RUN_MODES = (RUN_MODE_INTEGRATION, RUN_MODE_MODEL, RUN_MODE_SIMULATOR)

#: run_mode → harness 路由（冻结）。
HARNESS_DETERMINISTIC = "deterministic"
HARNESS_MODEL = "model"
HARNESS_SIMULATOR = "simulator"
HARNESS_BY_RUN_MODE = {
    RUN_MODE_INTEGRATION: HARNESS_DETERMINISTIC,
    RUN_MODE_MODEL: HARNESS_MODEL,
    RUN_MODE_SIMULATOR: HARNESS_SIMULATOR,
}

#: must_preserve 冻结词表（当前 260 case 全量取值即此三项）。
MUST_PRESERVE_VOCAB = frozenset({"truthfulness", "user isolation", "no false success"})

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCENARIOS_PATH = _REPO_ROOT / "v3" / "05_metrics_eval" / "scenarios_v3.jsonl"
DEFAULT_PERSONA_LIBRARY_PATH = _REPO_ROOT / "v3" / "05_metrics_eval" / "persona_library.json"


def scenarios_path() -> Path:
    """场景库路径（环境变量可覆盖；默认指向 v3/05_metrics_eval/scenarios_v3.jsonl）。"""
    override = os.environ.get("V3_SCENARIOS_PATH")
    return Path(override) if override else DEFAULT_SCENARIOS_PATH


def persona_library_path() -> Path:
    override = os.environ.get("V3_PERSONA_LIBRARY_PATH")
    return Path(override) if override else DEFAULT_PERSONA_LIBRARY_PATH


def load_persona_ids(path: Path | None = None) -> tuple[str, ...]:
    """从 persona_library.json 装载冻结 persona id 集。"""
    target = path or persona_library_path()
    raw = json.loads(target.read_text(encoding="utf-8"))
    ids = tuple(sorted(str(entry["id"]) for entry in raw))
    if not ids:
        raise ValueError(f"persona library empty: {target}")
    return ids


@dataclass(frozen=True)
class Scenario:
    """单条场景（字段与 jsonl 行一一对应，不做语义改写）。"""

    case_id: str
    category: str
    persona_id: str
    goal: str
    run_mode: str
    must_preserve: tuple[str, ...]
    repeat: int
    input: str
    expected: tuple[str, ...]

    @property
    def harness(self) -> str:
        return HARNESS_BY_RUN_MODE[self.run_mode]

    def to_payload(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "persona_id": self.persona_id,
            "goal": self.goal,
            "run_mode": self.run_mode,
            "harness": self.harness,
            "must_preserve": list(self.must_preserve),
            "repeat": self.repeat,
            "input": self.input,
            "expected": list(self.expected),
        }


def validate_scenario(scenario: Scenario, persona_ids: tuple[str, ...]) -> list[str]:
    """单场景装载校验（schema/词表/引用完整性）。"""
    errors: list[str] = []
    if not scenario.case_id.startswith("V3-") or not scenario.case_id[3:].isdigit():
        errors.append(f"bad case_id format: {scenario.case_id}")
    if scenario.run_mode not in RUN_MODES:
        errors.append(f"{scenario.case_id}: unknown run_mode {scenario.run_mode}")
    if scenario.persona_id not in persona_ids:
        errors.append(f"{scenario.case_id}: unknown persona {scenario.persona_id}")
    if scenario.repeat < 1:
        errors.append(f"{scenario.case_id}: repeat must be >= 1")
    unknown_preserve = set(scenario.must_preserve) - MUST_PRESERVE_VOCAB
    if unknown_preserve:
        errors.append(f"{scenario.case_id}: must_preserve outside frozen vocab: {sorted(unknown_preserve)}")
    if not scenario.expected:
        errors.append(f"{scenario.case_id}: expected rubric empty")
    if not scenario.input:
        errors.append(f"{scenario.case_id}: input empty")
    return errors


def load_scenarios(path: Path | None = None) -> list[Scenario]:
    """装载全部场景；任何结构/枚举/引用问题直接 raise（acceptance：枚举完整性是硬线）。"""
    target = path or scenarios_path()
    persona_ids = load_persona_ids()
    scenarios: list[Scenario] = []
    seen_ids: set[str] = set()
    with target.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            missing = [field for field in SCENARIO_FIELDS if field not in raw]
            if missing:
                raise ValueError(f"{target}:{line_no}: missing fields {missing}")
            scenario = Scenario(
                case_id=str(raw["case_id"]),
                category=str(raw["category"]),
                persona_id=str(raw["persona_id"]),
                goal=str(raw["goal"]),
                run_mode=str(raw["run_mode"]),
                must_preserve=tuple(str(item) for item in raw["must_preserve"]),
                repeat=int(raw["repeat"]),
                input=str(raw["input"]),
                expected=tuple(str(item) for item in raw["expected"]),
            )
            errors = validate_scenario(scenario, persona_ids)
            if errors:
                raise ValueError("; ".join(errors))
            if scenario.case_id in seen_ids:
                raise ValueError(f"duplicate case_id {scenario.case_id}")
            seen_ids.add(scenario.case_id)
            scenarios.append(scenario)

    if len(scenarios) != SCENARIO_COUNT:
        raise ValueError(f"scenario count {len(scenarios)} != {SCENARIO_COUNT}")
    expected_ids = {f"V3-{index:03d}" for index in range(1, SCENARIO_COUNT + 1)}
    missing_ids = sorted(expected_ids - seen_ids)
    if missing_ids:
        raise ValueError(f"missing case ids: {missing_ids[:5]}... ({len(missing_ids)} total)")
    return sorted(scenarios, key=lambda scenario: scenario.case_id)
