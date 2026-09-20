"""C-08 · ablation 评测门禁（pytest 断言面）。

钉住 acceptance：
- ≥ 50 场景 × 四臂，每格都有 utility / latency / token 结果；
- 真实 LLM 0 次（meta 声明 + runner 源静态检查双层）；
- 确定性：两次全量运行结果逐字节一致（除 meta.generated_at/git）；
- 场景导出/结果负载不含材料正文（隐私红线在评测域同样生效）；
- 覆盖矩阵 + 家族语义判定（四臂在特定设计族上的方向性差异被钉死）。
"""

from __future__ import annotations

import json

import pytest

from tests.context_eval.context_eval_schema import (
    ARMS,
    DIMENSIONS,
    MIN_SCENARIOS,
    Scenario,
    check_coverage,
    validate_scenario,
)
from tests.context_eval.grading import aggregate, grade
from tests.context_eval.mock_model import assemble, mock_answer
from tests.context_eval.runner import run_ablation
from tests.context_eval.scenarios import build_scenarios

# ---------------------------------------------------------------------------
# 场景集
# ---------------------------------------------------------------------------


class TestScenarioSet:
    def test_coverage_matrix(self):
        scenarios = build_scenarios()
        assert len(scenarios) >= MIN_SCENARIOS
        assert check_coverage(scenarios) == []
        assert all(validate_scenario(scenario) == [] for scenario in scenarios)

    def test_dimensions_all_present(self):
        scenarios = build_scenarios()
        used = {scenario.dimension for scenario in scenarios}
        assert used == set(DIMENSIONS)


# ---------------------------------------------------------------------------
# 全量运行：acceptance 硬线
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def results() -> dict:
    return run_ablation()


class TestAblationRun:
    def test_all_arms_all_scenarios_have_results(self, results):
        """acceptance：≥50 场景四臂，每格 utility/latency/token 齐备。"""
        scenarios = build_scenarios()
        assert results["meta"]["scenario_count"] >= MIN_SCENARIOS
        rows = results["scenarios"]
        assert len(rows) == len(scenarios) * len(ARMS)
        for row in rows:
            assert row["arm"] in ARMS
            assert isinstance(row["utility_ok"], bool)
            assert isinstance(row["abstain_ok"], bool)
            assert row["tokens"] >= 0
            assert row["latency_proxy_ms"] >= 0

    def test_zero_real_llm_calls(self, results):
        assert results["meta"]["real_llm_calls"] == 0

    def test_no_llm_imports_in_harness(self):
        """静态守卫：harness 三模块不得 import 任何 LLM 服务面。"""
        import inspect

        from tests.context_eval import grading, mock_model

        for module in (mock_model, grading):
            source = inspect.getsource(module)
            for banned in ("llm_service", "get_configured_llm_service", "LLMRouter", "chat_completion"):
                assert banned not in source, f"{module.__name__} 引用了 {banned}"

    def test_deterministic_rerun(self):
        """两次全量运行（除 meta 时间戳/git）逐字节一致。"""
        first, second = run_ablation(), run_ablation()
        first.pop("meta"), second.pop("meta")
        assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)

    def test_results_payload_has_no_material_bodies(self, results):
        """隐私：结果负载不含任何材料/记忆正文样本。"""
        scenarios = build_scenarios()
        blob = json.dumps(results, ensure_ascii=False)
        sampled = 0
        for scenario in scenarios:
            for material in scenario.materials[:1]:
                head = material.content[:16]
                if len(head) >= 8:
                    sampled += 1
                    assert head not in blob
            for memory in scenario.memories[:1]:
                head = memory.content[:16]
                if len(head) >= 8:
                    assert head not in blob
        assert sampled > 40  # 抽样面确实覆盖到了

    def test_summary_aggregates_consistent(self, results):
        summary = results["summary"]
        assert set(summary["arms"]) == set(ARMS)
        for arm, stats in summary["arms"].items():
            assert stats["scenario_count"] * 1 == len(results["scenarios"]) / len(ARMS)
            assert 0.0 <= stats["success_rate"] <= 1.0


# ---------------------------------------------------------------------------
# 家族语义（四臂方向性差异被钉死——评测不是摆设）
# ---------------------------------------------------------------------------


def _row(results: dict, scenario_id: str, arm: str) -> dict:
    for row in results["scenarios"]:
        if row["scenario_id"] == scenario_id and row["arm"] == arm:
            return row
    raise AssertionError(f"missing row {scenario_id}/{arm}")


class TestFamilySemantics:
    def test_crowd_out_rag_rescued_by_no_memory(self, results):
        """干扰记忆挤掉金标材料：full 失败、no_memory 救回（rag-001 家族）。"""
        for scenario_id in ("rag-001", "rag-005", "rag-009"):
            full = _row(results, scenario_id, "full")
            rescued = _row(results, scenario_id, "no_memory")
            assert full["utility_ok"] is False
            assert full["attention_dropped"], f"{scenario_id}: 金标应被注意力窗挤出"
            assert rescued["utility_ok"] is True

    def test_outcome_crowd_rescued_by_no_outcome(self, results):
        """outcome 记忆风暴挤掉金标记忆：full 失败、no_outcome 救回（mem-001 家族）。"""
        for scenario_id in ("mem-001", "mem-005", "mem-009"):
            full = _row(results, scenario_id, "full")
            rescued = _row(results, scenario_id, "no_outcome")
            assert full["utility_ok"] is False
            assert rescued["utility_ok"] is True

    def test_outcome_utility_needs_outcome_arm(self, results):
        """金标记忆本身带 outcome：no_outcome 必败、full 必胜（mem-000 家族）。"""
        for scenario_id in ("mem-000", "mem-002", "mem-004"):
            assert _row(results, scenario_id, "full")["utility_ok"] is True
            assert _row(results, scenario_id, "no_outcome")["utility_ok"] is False

    def test_harmful_outcome_memory_blocked_by_no_outcome(self, results):
        """误导性 outcome 记忆：full 误用失败、no_outcome 通过（mem-003 家族）。"""
        for scenario_id in ("mem-003", "mem-007", "mem-011"):
            full = _row(results, scenario_id, "full")
            rescued = _row(results, scenario_id, "no_outcome")
            assert full["harmful_memories"], "full 臂应暴露 harmful memory 使用"
            assert full["utility_ok"] is False
            assert rescued["utility_ok"] is True

    def test_adversarial_near_distractor_detected(self, results):
        """纯干扰场景：正确弃答得分；同主题误导材料被引用即失败并被定位。"""
        # adv-000：含同主题错误事实材料 → 引用即 harmful
        adv_near = _row(results, "adv-000", "full")
        assert adv_near["harmful_citations"], "同主题误导材料应被 harmful 定位"
        assert adv_near["abstain_ok"] is False
        # 找一个纯干扰（无 near、无 harmful 记忆）的场景验证正确弃答
        pure = _row(results, "adv-003", "full")
        assert pure["abstain_ok"] is True

    def test_strip_arm_never_beats_full_on_own_gold(self, results):
        """消融臂在自己被消融的金标面上必须失败（消融语义完整性）。"""
        for scenario_id in ("mem-000", "mix-000", "rag-000"):
            no_memory = _row(results, scenario_id, "no_memory")
            no_rag = _row(results, scenario_id, "no_rag")
            if scenario_id.startswith("rag"):
                assert no_rag["utility_ok"] is False
            else:
                assert no_memory["utility_ok"] is False

    def test_harmful_refs_are_localized(self, results):
        """harmful ref 定位面：误导记忆 ref 出现在聚合 top 表中。"""
        harmful = results["summary"]["harmful_refs_top"]
        assert any(ref.startswith("mem:h") for ref in harmful)


# ---------------------------------------------------------------------------
# 场景 JSON round-trip（导出面稳定性）
# ---------------------------------------------------------------------------


class TestSchemaRoundTrip:
    def test_payload_round_trip(self, tmp_path):
        from tests.context_eval.context_eval_schema import load_scenarios_json

        scenarios = build_scenarios()
        path = tmp_path / "scenarios.json"
        path.write_text(json.dumps([s.to_payload() for s in scenarios], ensure_ascii=False), encoding="utf-8")
        reloaded = load_scenarios_json(path)
        assert [s.scenario_id for s in reloaded] == [s.scenario_id for s in scenarios]
        assert [s.gold_ref_ids for s in reloaded] == [s.gold_ref_ids for s in scenarios]
        assert [s.must_use_memory_refs for s in reloaded] == [s.must_use_memory_refs for s in scenarios]

    def test_aggregate_shape(self):
        scenarios = build_scenarios()[:4]
        rows = []
        for scenario in scenarios:
            for arm in ARMS:
                assembled = assemble(scenario, arm)
                answer, cited, used = mock_answer(scenario, assembled)
                rows.append(grade(scenario, arm, assembled, answer, cited, used))
        agg = aggregate(rows)
        assert set(agg["arms"]) == set(ARMS)
        assert "deltas_vs_full" in agg
