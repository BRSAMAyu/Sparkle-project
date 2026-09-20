"""C-08 · Context Decision Utility ablation 评测——冻结场景 schema。

`c08-context-eval.v1`。全部场景为**构造的合成材料**（无任何真实用户数据），
评测全程 hermetic：模拟模型按确定性规则作答，真实 LLM 调用 0 次
（对齐 EVAL_PROTOCOL §2：不允许模型自评作为唯一证据——utility 判定用
C-04 确定性解析规则 + 构造的 gold label，零模型参与）。

覆盖矩阵（机检）：四臂 × 四维度（rag/memory/mixed/adversarial），
场景总数 ≥ 50（acceptance 硬线）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "c08-context-eval.v1"

#: 评测臂（冻结）：消融哪个注入面。
ARM_FULL = "full"
ARM_NO_MEMORY = "no_memory"
ARM_NO_RAG = "no_rag"
ARM_NO_OUTCOME = "no_outcome"
ARMS: tuple[str, ...] = (ARM_FULL, ARM_NO_MEMORY, ARM_NO_RAG, ARM_NO_OUTCOME)

#: 场景维度（冻结，用于覆盖矩阵机检）。
DIM_RAG = "rag"
DIM_MEMORY = "memory"
DIM_MIXED = "mixed"
DIM_ADVERSARIAL = "adversarial"
DIMENSIONS: tuple[str, ...] = (DIM_RAG, DIM_MEMORY, DIM_MIXED, DIM_ADVERSARIAL)

#: outcome 方向（与 M-06 experience 记忆的 direction 同词表）。
OUTCOME_NONE = "none"
OUTCOME_POSITIVE = "positive"
OUTCOME_NEGATIVE = "negative"

MIN_SCENARIOS = 50


@dataclass(frozen=True)
class Material:
    """RAG 候选材料（构造正文，仅评测域内使用）。"""

    ref: str
    content: str
    relevant: bool
    relevance_score: float


@dataclass(frozen=True)
class MemoryItem:
    """记忆候选（构造正文；outcome 对齐 M-06 direction 词表）。"""

    ref: str
    content: str
    relevant: bool
    outcome: str = OUTCOME_NONE


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    dimension: str
    query: str
    materials: tuple[Material, ...] = field(default_factory=tuple)
    memories: tuple[MemoryItem, ...] = field(default_factory=tuple)

    @property
    def gold_ref_ids(self) -> list[str]:
        return [material.ref for material in self.materials if material.relevant]

    @property
    def must_use_memory_refs(self) -> list[str]:
        return [memory.ref for memory in self.memories if memory.relevant]

    def to_payload(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "dimension": self.dimension,
            "query": self.query,
            "materials": [
                {
                    "ref": material.ref,
                    "content": material.content,
                    "relevant": material.relevant,
                    "relevance_score": material.relevance_score,
                }
                for material in self.materials
            ],
            "memories": [
                {
                    "ref": memory.ref,
                    "content": memory.content,
                    "relevant": memory.relevant,
                    "outcome": memory.outcome,
                }
                for memory in self.memories
            ],
            "gold_ref_ids": self.gold_ref_ids,
            "must_use_memory_refs": self.must_use_memory_refs,
        }


def validate_scenario(scenario: Scenario) -> list[str]:
    """装载校验：id/维度合法、gold 与候选一致、adversarial 无 gold。"""
    errors: list[str] = []
    if not scenario.scenario_id:
        errors.append("scenario_id empty")
    if scenario.dimension not in DIMENSIONS:
        errors.append(f"{scenario.scenario_id}: unknown dimension {scenario.dimension}")
    if not scenario.query.strip():
        errors.append(f"{scenario.scenario_id}: query empty")
    material_refs = [material.ref for material in scenario.materials]
    if len(set(material_refs)) != len(material_refs):
        errors.append(f"{scenario.scenario_id}: duplicate material refs")
    memory_refs = [memory.ref for memory in scenario.memories]
    if len(set(memory_refs)) != len(memory_refs):
        errors.append(f"{scenario.scenario_id}: duplicate memory refs")
    for material in scenario.materials:
        if not 0.0 <= material.relevance_score <= 1.0:
            errors.append(f"{scenario.scenario_id}: relevance out of range on {material.ref}")
    for memory in scenario.memories:
        if memory.outcome not in {OUTCOME_NONE, OUTCOME_POSITIVE, OUTCOME_NEGATIVE}:
            errors.append(f"{scenario.scenario_id}: unknown outcome on {memory.ref}")
    if scenario.dimension == DIM_ADVERSARIAL and (scenario.gold_ref_ids or scenario.must_use_memory_refs):
        errors.append(f"{scenario.scenario_id}: adversarial scenario must have no gold")
    if scenario.dimension in {DIM_RAG, DIM_MIXED} and not scenario.gold_ref_ids:
        errors.append(f"{scenario.scenario_id}: {scenario.dimension} scenario needs gold materials")
    if scenario.dimension in {DIM_MEMORY, DIM_MIXED} and not scenario.must_use_memory_refs:
        errors.append(f"{scenario.scenario_id}: {scenario.dimension} scenario needs gold memories")
    if scenario.dimension == DIM_RAG and scenario.must_use_memory_refs:
        errors.append(f"{scenario.scenario_id}: rag scenario must not require memories")
    if scenario.dimension == DIM_MEMORY and scenario.gold_ref_ids:
        errors.append(f"{scenario.scenario_id}: memory scenario must not require materials")
    return errors


def check_coverage(scenarios: list[Scenario]) -> list[str]:
    """覆盖矩阵机检：总数 ≥ 50；每维度非空；四臂定义冻结存在。"""
    errors: list[str] = []
    if len(scenarios) < MIN_SCENARIOS:
        errors.append(f"scenario count {len(scenarios)} < {MIN_SCENARIOS}")
    counts = {dimension: 0 for dimension in DIMENSIONS}
    for scenario in scenarios:
        counts[scenario.dimension] = counts.get(scenario.dimension, 0) + 1
    for dimension, count in counts.items():
        if count == 0:
            errors.append(f"dimension {dimension} has no scenarios")
    ids = [scenario.scenario_id for scenario in scenarios]
    if len(set(ids)) != len(ids):
        errors.append("duplicate scenario ids")
    return errors


def load_scenarios_json(path: Path) -> list[Scenario]:
    """从导出 JSON 装载（round-trip 稳定性校验用）。"""
    raw = json.loads(path.read_text(encoding="utf-8"))
    scenarios: list[Scenario] = []
    for entry in raw:
        scenarios.append(
            Scenario(
                scenario_id=str(entry["scenario_id"]),
                dimension=str(entry["dimension"]),
                query=str(entry["query"]),
                materials=tuple(
                    Material(
                        ref=str(item["ref"]),
                        content=str(item["content"]),
                        relevant=bool(item["relevant"]),
                        relevance_score=float(item["relevance_score"]),
                    )
                    for item in entry.get("materials") or []
                ),
                memories=tuple(
                    MemoryItem(
                        ref=str(item["ref"]),
                        content=str(item["content"]),
                        relevant=bool(item["relevant"]),
                        outcome=str(item.get("outcome") or OUTCOME_NONE),
                    )
                    for item in entry.get("memories") or []
                ),
            )
        )
    return scenarios
