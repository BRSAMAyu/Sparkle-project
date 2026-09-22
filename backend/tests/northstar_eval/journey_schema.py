"""NORTHSTAR · 旅程 spec 冻结 schema（``northstar-journey.v1``）与装载校验。

冻结面（改动需走规格变更，真源 `v3-output/NORTHSTAR/SCENARIO.md` §1/§3）：

- 字段九项（journey_id/persona_id/subject/horizon_days/daily_minutes/pretest_score/nodes/arms/expected）；
- arm 三值（sparkle / control_gpt / control_dsk）↔ 三臂对照协议（EVAL_FRAMEWORK §2.1）；
- checkpoint 词表（CP-00..CP-99）与 SCENARIO.md 检查点一一对应；
  CP-98/CP-99 属真实世界判据（真人自报 / 真墙钟），API 级推演一律 honest-unsupported；
- node 形状对齐 sprint pack ``KnowledgeNode``（node_id/exam_weight/difficulty/trainability）。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "northstar-journey.v1"

#: arm 冻结词表（三臂对照）。
ARM_SPARKLE = "sparkle"
ARM_CONTROL_GPT = "control_gpt"
ARM_CONTROL_DSK = "control_dsk"
ARMS = (ARM_SPARKLE, ARM_CONTROL_GPT, ARM_CONTROL_DSK)

JOURNEY_ID_PREFIX = "NS-"

#: checkpoint 冻结词表（确定性可判 + 诚实降级两类）。
CHECKPOINT_DETERMINISTIC = (
    "CP-00 baseline recorded and syllabus mapped",
    "CP-01 plan targets weakest exam-weighted nodes with human confirmation",
    "CP-02 quiz score trajectory non-decreasing",
    "CP-03 mistakes fully land in error book with mastery sync",
    "CP-04 next-day plan adapts to previous outcome",
    "CP-05 review hit rate at or above threshold",
    "CP-06 weighted coverage at or above threshold by last study day",
    "CP-07 posttest gain at or above MDE",
    "CP-08 forgetting rate at or below threshold",
)
#: 真实世界判据：API 级推演（确定性 surrogate）永远判 unsupported，绝不折算 pass。
CHECKPOINT_UNSUPPORTED = (
    "CP-98 daily cognitive load self-report",  # 真人 NASA-TLX 简化量表（EVAL_FRAMEWORK M7）
    "CP-99 full mock exam wall clock at or below budget",  # 真实墙钟属性（SCENARIO Day7）
)
CHECKPOINT_VOCAB = CHECKPOINT_DETERMINISTIC + CHECKPOINT_UNSUPPORTED

JOURNEY_FIELDS = (
    "journey_id",
    "persona_id",
    "subject",
    "horizon_days",
    "daily_minutes",
    "pretest_score",
    "nodes",
    "arms",
    "expected",
)


@dataclass(frozen=True)
class JourneyNode:
    """考纲节点（字段对齐 sprint pack KnowledgeNode 的评估必要子集）。"""

    node_id: str
    label: str
    exam_weight: float
    difficulty: int
    trainability: float

    def to_payload(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "label": self.label,
            "exam_weight": self.exam_weight,
            "difficulty": self.difficulty,
            "trainability": self.trainability,
        }


@dataclass(frozen=True)
class Journey:
    """单条北极星旅程 spec（字段与 jsonl 行一一对应，不做语义改写）。"""

    journey_id: str
    persona_id: str
    subject: str
    horizon_days: int
    daily_minutes: float
    pretest_score: float
    nodes: tuple[JourneyNode, ...]
    arms: tuple[str, ...]
    expected: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "journey_id": self.journey_id,
            "persona_id": self.persona_id,
            "subject": self.subject,
            "horizon_days": self.horizon_days,
            "daily_minutes": self.daily_minutes,
            "pretest_score": self.pretest_score,
            "nodes": [node.to_payload() for node in self.nodes],
            "arms": list(self.arms),
            "expected": list(self.expected),
        }


def validate_journey(journey: Journey) -> list[str]:
    """单旅程装载校验（schema/词表/数值域）。"""
    errors: list[str] = []
    if not journey.journey_id.startswith(JOURNEY_ID_PREFIX):
        errors.append(f"bad journey_id format: {journey.journey_id}")
    if not journey.persona_id:
        errors.append(f"{journey.journey_id}: persona_id empty")
    if journey.horizon_days < 1:
        errors.append(f"{journey.journey_id}: horizon_days must be >= 1")
    if journey.daily_minutes <= 0:
        errors.append(f"{journey.journey_id}: daily_minutes must be positive")
    if not 0 <= journey.pretest_score <= 100:
        errors.append(f"{journey.journey_id}: pretest_score outside [0, 100]")
    if not journey.nodes:
        errors.append(f"{journey.journey_id}: nodes empty")
    for node in journey.nodes:
        if not 0 < node.exam_weight <= 1:
            errors.append(f"{journey.journey_id}: node {node.node_id} exam_weight outside (0, 1]")
        if not 1 <= node.difficulty <= 5:
            errors.append(f"{journey.journey_id}: node {node.node_id} difficulty outside [1, 5]")
        if not 0 < node.trainability <= 1:
            errors.append(f"{journey.journey_id}: node {node.node_id} trainability outside (0, 1]")
    unknown_arms = set(journey.arms) - set(ARMS)
    if unknown_arms:
        errors.append(f"{journey.journey_id}: unknown arms {sorted(unknown_arms)}")
    if not journey.arms:
        errors.append(f"{journey.journey_id}: arms empty")
    unknown_checkpoints = set(journey.expected) - set(CHECKPOINT_VOCAB)
    if unknown_checkpoints:
        errors.append(f"{journey.journey_id}: expected outside frozen checkpoint vocab: {sorted(unknown_checkpoints)}")
    if not journey.expected:
        errors.append(f"{journey.journey_id}: expected empty")
    return errors


def parse_journey(raw: dict[str, Any], *, origin: str = "<inline>") -> Journey:
    """dict → Journey（缺字段直接 raise，不做默认值补齐）。"""
    missing = [field for field in JOURNEY_FIELDS if field not in raw]
    if missing:
        raise ValueError(f"{origin}: missing fields {missing}")
    journey = Journey(
        journey_id=str(raw["journey_id"]),
        persona_id=str(raw["persona_id"]),
        subject=str(raw["subject"]),
        horizon_days=int(raw["horizon_days"]),
        daily_minutes=float(raw["daily_minutes"]),
        pretest_score=float(raw["pretest_score"]),
        nodes=tuple(
            JourneyNode(
                node_id=str(node["node_id"]),
                label=str(node.get("label", node["node_id"])),
                exam_weight=float(node["exam_weight"]),
                difficulty=int(node["difficulty"]),
                trainability=float(node["trainability"]),
            )
            for node in raw["nodes"]
        ),
        arms=tuple(str(arm) for arm in raw["arms"]),
        expected=tuple(str(item) for item in raw["expected"]),
    )
    errors = validate_journey(journey)
    if errors:
        raise ValueError("; ".join(errors))
    return journey


def load_journeys(path: Path) -> list[Journey]:
    """从 JSONL 装载旅程；空文件合法（返回 []，runner 汇总诚实为 0）。"""
    journeys: list[Journey] = []
    seen: set[str] = set()
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            journey = parse_journey(json.loads(line), origin=f"{path}:{line_no}")
            if journey.journey_id in seen:
                raise ValueError(f"{path}:{line_no}: duplicate journey_id {journey.journey_id}")
            seen.add(journey.journey_id)
            journeys.append(journey)
    return journeys


def default_journeys_path() -> Path:
    """旅程库路径（环境变量可覆盖；骨架默认无内置库——空库是合法初始态）。"""
    override = os.environ.get("NORTHSTAR_JOURNEYS_PATH")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent / "journeys_northstar.jsonl"


# ---------------------------------------------------------------------------
# SCENARIO.md §1 冻结 spec case（7 天离散数学期末冲刺）的程序化构造
# ---------------------------------------------------------------------------

#: 6 章 × 4 节点 = 24 节点（SCENARIO §1「24 个考纲节点」）；
#: 章权重 0.06/0.055/0.045/0.045/0.025/0.02，总权恰为 1.0；
#: 权重 Top18 节点合计 0.87 ≥ 覆盖阈值 0.8（SCENARIO CP-06）。
_CHAPTERS = (
    ("ch1_logic", "CH1 数理逻辑", 0.06),
    ("ch2_sets_relations", "CH2 集合与关系", 0.055),
    ("ch3_functions", "CH3 函数与基数", 0.045),
    ("ch4_graph_theory", "CH4 图论", 0.045),
    ("ch5_combinatorics", "CH5 组合数学", 0.025),
    ("ch6_algebraic_systems", "CH6 代数系统", 0.02),
)
_NODES_PER_CHAPTER = 4


def spec_case_journey() -> Journey:
    """SCENARIO.md §1 冻结 spec case：NS-001 林晓离散数学 7 天（42→57+）。"""
    nodes: list[JourneyNode] = []
    for slug, label, weight in _CHAPTERS:
        for index in range(1, _NODES_PER_CHAPTER + 1):
            nodes.append(
                JourneyNode(
                    node_id=f"dm.{slug}.{index:02d}",
                    label=f"{label} 节点{index}",
                    exam_weight=weight,
                    difficulty=min(5, 2 + index % 3),
                    trainability=0.8,
                )
            )
    return Journey(
        journey_id="NS-001",
        persona_id="persona.lin-xiao.sophomore",
        subject="离散数学",
        horizon_days=7,
        daily_minutes=165.0,
        pretest_score=42.0,
        nodes=tuple(nodes),
        arms=ARMS,
        expected=CHECKPOINT_VOCAB,
    )
