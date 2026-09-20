"""C-08 · utility 判定与聚合（确定性，零模型参与）。

utility 判定完全建立在 **C-04 确定性解析规则**（``parse_cited_markers`` /
``build_citation_outcome``）+ **构造的 gold label** 之上：

- 材料面：cited ⊆ gold ∧ gold 全覆盖 ∧ ``faithfulness_ok``；
- 记忆面：used ⊆ gold ∧ gold 全使用；
- adversarial：正确弃答（零引用零使用）；
- 代价：注入 token（确定性近似）+ 延迟代理
  ``40 + 0.12 × tokens + 15 × surfaces``（成本模型，非真实时钟）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.citation_markers import build_citation_outcome

from .context_eval_schema import DIM_ADVERSARIAL, ARM_FULL, ARMS, Scenario
from .mock_model import AssembledContext, estimate_tokens

#: 延迟代理常量（文档化的确定性成本模型——评测内可比，不代表真实时钟）。
LATENCY_BASE_MS = 40.0
LATENCY_PER_TOKEN_MS = 0.12
LATENCY_PER_SURFACE_MS = 15.0


@dataclass
class ArmResult:
    scenario_id: str
    dimension: str
    arm: str
    utility_ok: bool
    abstain_ok: bool
    faithfulness_ok: bool
    material_coverage: float
    memory_coverage: float
    harmful_citations: list[str]
    harmful_memories: list[str]
    cited_refs: list[str]
    used_memory_refs: list[str]
    injected_refs: list[str]
    attention_dropped: list[str]
    tokens: int
    latency_proxy_ms: float
    unknown_cited: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "dimension": self.dimension,
            "arm": self.arm,
            "utility_ok": self.utility_ok,
            "abstain_ok": self.abstain_ok,
            "faithfulness_ok": self.faithfulness_ok,
            "material_coverage": round(self.material_coverage, 4),
            "memory_coverage": round(self.memory_coverage, 4),
            "harmful_citations": self.harmful_citations,
            "harmful_memories": self.harmful_memories,
            "cited_refs": self.cited_refs,
            "used_memory_refs": self.used_memory_refs,
            "injected_refs": self.injected_refs,
            "attention_dropped": self.attention_dropped,
            "tokens": self.tokens,
            "latency_proxy_ms": round(self.latency_proxy_ms, 1),
            "unknown_cited": self.unknown_cited,
        }


def grade(
    scenario: Scenario,
    arm: str,
    assembled: AssembledContext,
    answer: str,
    cited_refs: list[str],
    used_memory_refs: list[str],
) -> ArmResult:
    """单场景单臂判定（全部确定性规则）。"""
    gold_materials = set(scenario.gold_ref_ids)
    gold_memories = set(scenario.must_use_memory_refs)

    # C-04 确定性 outcome：retrieved vs cited vs answer-supported。
    outcome = build_citation_outcome(answer, assembled.document_block) if assembled.document_block else {
        "retrieved": 0,
        "cited": [],
        "unknown_cited": [],
        "answer_supported": [],
        "faithfulness_ok": True,
    }

    cited = list(cited_refs)
    used = list(used_memory_refs)
    harmful_citations = [ref for ref in cited if ref not in gold_materials]
    harmful_memories = [ref for ref in used if ref not in gold_memories]
    material_coverage = (len(gold_materials & set(cited)) / len(gold_materials)) if gold_materials else 1.0
    memory_coverage = (len(gold_memories & set(used)) / len(gold_memories)) if gold_memories else 1.0

    if scenario.dimension == DIM_ADVERSARIAL:
        abstain_ok = not cited and not used
        utility_ok = abstain_ok and bool(outcome.get("faithfulness_ok", True))
    else:
        abstain_ok = False
        utility_ok = (
            material_coverage == 1.0
            and memory_coverage == 1.0
            and not harmful_citations
            and not harmful_memories
            and bool(outcome.get("faithfulness_ok", True))
        )

    surfaces = (1 if assembled.document_block else 0) + (1 if assembled.memory_section else 0)
    tokens = estimate_tokens(assembled.document_block) + estimate_tokens(assembled.memory_section)
    latency_proxy_ms = LATENCY_BASE_MS + LATENCY_PER_TOKEN_MS * tokens + LATENCY_PER_SURFACE_MS * surfaces

    return ArmResult(
        scenario_id=scenario.scenario_id,
        dimension=scenario.dimension,
        arm=arm,
        utility_ok=utility_ok,
        abstain_ok=abstain_ok,
        faithfulness_ok=bool(outcome.get("faithfulness_ok", True)),
        material_coverage=material_coverage,
        memory_coverage=memory_coverage,
        harmful_citations=harmful_citations,
        harmful_memories=harmful_memories,
        cited_refs=cited,
        used_memory_refs=used,
        injected_refs=list(assembled.seen_material_refs) + list(assembled.seen_memory_refs),
        attention_dropped=[ref for ref, _reason in assembled.dropped_by_attention],
        tokens=tokens,
        latency_proxy_ms=latency_proxy_ms,
        unknown_cited=list(outcome.get("unknown_cited") or []),
    )


def aggregate(results: list[ArmResult]) -> dict[str, Any]:
    """四臂聚合 + 对 full 臂的 delta + inert/harmful ref 定位。"""
    summary: dict[str, Any] = {}
    for arm in ARMS:
        arm_results = [result for result in results if result.arm == arm]
        if not arm_results:
            continue
        adversarial = [result for result in arm_results if result.dimension == DIM_ADVERSARIAL]
        non_adversarial = [result for result in arm_results if result.dimension != DIM_ADVERSARIAL]
        by_dimension: dict[str, float] = {}
        for dimension in sorted({result.dimension for result in arm_results}):
            subset = [result for result in arm_results if result.dimension == dimension]
            ok_column = "abstain_ok" if dimension == DIM_ADVERSARIAL else "utility_ok"
            by_dimension[dimension] = round(sum(1 for r in subset if getattr(r, ok_column)) / len(subset), 4)
        summary[arm] = {
            "scenario_count": len(arm_results),
            "utility_rate": round(sum(1 for r in non_adversarial if r.utility_ok) / len(non_adversarial), 4)
            if non_adversarial
            else None,
            "abstain_rate": round(sum(1 for r in adversarial if r.abstain_ok) / len(adversarial), 4)
            if adversarial
            else None,
            "success_rate": round(sum(1 for r in arm_results if r.utility_ok or r.abstain_ok) / len(arm_results), 4),
            "faithfulness_rate": round(sum(1 for r in arm_results if r.faithfulness_ok) / len(arm_results), 4),
            "harmful_citation_scenarios": sum(1 for r in arm_results if r.harmful_citations),
            "harmful_memory_scenarios": sum(1 for r in arm_results if r.harmful_memories),
            "unknown_cited_scenarios": sum(1 for r in arm_results if r.unknown_cited),
            "attention_drop_scenarios": sum(1 for r in arm_results if r.attention_dropped),
            "avg_tokens": round(sum(r.tokens for r in arm_results) / len(arm_results), 1),
            "avg_latency_proxy_ms": round(sum(r.latency_proxy_ms for r in arm_results) / len(arm_results), 1),
            "by_dimension": by_dimension,
        }

    full = summary.get(ARM_FULL, {})
    deltas: dict[str, Any] = {}
    for arm in ARMS:
        if arm == ARM_FULL or arm not in summary:
            continue
        deltas[arm] = {
            "success_rate_delta": round(summary[arm]["success_rate"] - full.get("success_rate", 0.0), 4),
            "avg_tokens_delta": round(summary[arm]["avg_tokens"] - full.get("avg_tokens", 0.0), 1),
            "avg_latency_proxy_delta_ms": round(
                summary[arm]["avg_latency_proxy_ms"] - full.get("avg_latency_proxy_ms", 0.0), 1
            ),
        }

    # inert（注入但从未被引用/使用）与 harmful（被引用但非 gold）ref 定位。
    inert_counter: dict[str, int] = {}
    harmful_counter: dict[str, int] = {}
    for result in results:
        used_refs = set(result.cited_refs) | set(result.used_memory_refs)
        for ref in result.injected_refs:
            if ref not in used_refs:
                inert_counter[ref] = inert_counter.get(ref, 0) + 1
        for ref in result.harmful_citations + result.harmful_memories:
            harmful_counter[ref] = harmful_counter.get(ref, 0) + 1

    return {
        "arms": summary,
        "deltas_vs_full": deltas,
        "inert_refs_top": dict(sorted(inert_counter.items(), key=lambda kv: -kv[1])[:12]),
        "harmful_refs_top": dict(sorted(harmful_counter.items(), key=lambda kv: -kv[1])[:12]),
    }
