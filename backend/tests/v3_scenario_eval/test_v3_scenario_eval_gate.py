"""Q-01 · V3 统一 Runner 门禁（pytest 断言面）。

钉住 acceptance：
- **枚举完整性**：260 case 全出、V3-001..V3-260 无缺无重、三类 run_mode 路由齐备；
- **unsupported 诚实**：unsupported 永不计 PASS、必带 reason、聚合唯一出口被钉住；
- **结果 JSON schema 稳定**：版本字段 + 顶层/case/attempt/item 键集冻结 + verdict 枚举合法；
- **repeat/seed 确定性**：同 seed 逐字节一致（除易变 meta）；跨 seed 判定稳定而指标可见 seed 生效；
- **红线**：真实 LLM 0 次（meta 声明 + 适配器无条件拒绝双层）；真 provider 配置只产生
  honest-unsupported，绝不发请求。
"""

from __future__ import annotations

import json

import pytest

from tests.v3_scenario_eval.grading import (
    ITEM_FAIL,
    ITEM_UNSUPPORTED,
    REASON_NO_CHECKER,
    REASON_REAL_MODEL_ZERO_CALL,
    VERDICT_PASS,
    VERDICT_UNSUPPORTED,
    VERDICTS,
    attempt_verdict,
    case_verdict,
    grade_attempt,
    unsupported_must_not_pass,
)
from tests.v3_scenario_eval.harnesses import RealModelAdapter, RealModelDisabledError
from tests.v3_scenario_eval.runner import (
    RESULTS_SCHEMA_VERSION,
    derive_attempt_seed,
    run_round,
    strip_volatile,
    write_evidence,
)
from tests.v3_scenario_eval.scenario_schema import (
    HARNESS_BY_RUN_MODE,
    SCENARIO_COUNT,
    Scenario,
    load_scenarios,
)

EXPECTED_TOP_KEYS = {"schema", "meta", "summary", "cases"}
EXPECTED_CASE_KEYS = {
    "case_id",
    "category",
    "run_mode",
    "harness",
    "persona_id",
    "repeat",
    "verdict",
    "reason",
    "attempts",
    "trace_ref",
    "evidence",
}
EXPECTED_ATTEMPT_KEYS = {"attempt", "seed", "verdict", "items", "metrics"}
EXPECTED_ITEM_KEYS = {"text", "status", "detail"}
EXPECTED_MODE_COUNTS = {"integration": 54, "model": 122, "simulator": 84}
EXPECTED_REPEAT5_COUNT = 25

#: 诚实降级三处：墙钟判据（first_value）、L3 真栈判据（journey）、渲染判据（ui_state）。
EXPECTED_UNSUPPORTED_CATEGORIES = {"first_value", "journey", "ui_state"}


@pytest.fixture(scope="module")
def scenarios() -> list[Scenario]:
    return load_scenarios()


@pytest.fixture(scope="module")
def results() -> dict:
    return run_round(run_seed=7, scenarios=load_scenarios())


# ---------------------------------------------------------------------------
# 场景库枚举完整性
# ---------------------------------------------------------------------------


class TestScenarioLibrary:
    def test_260_enumerated(self, scenarios):
        ids = {scenario.case_id for scenario in scenarios}
        assert len(scenarios) == SCENARIO_COUNT
        assert ids == {f"V3-{index:03d}" for index in range(1, SCENARIO_COUNT + 1)}

    def test_run_mode_routing_counts(self, scenarios):
        counts: dict[str, int] = {}
        for scenario in scenarios:
            counts[scenario.run_mode] = counts.get(scenario.run_mode, 0) + 1
            assert scenario.harness == HARNESS_BY_RUN_MODE[scenario.run_mode]
        assert counts == EXPECTED_MODE_COUNTS

    def test_repeat_vocabulary(self, scenarios):
        assert {scenario.repeat for scenario in scenarios} == {1, 5}
        assert sum(1 for scenario in scenarios if scenario.repeat == 5) == EXPECTED_REPEAT5_COUNT

    def test_all_categories_have_surrogate(self, scenarios):
        from tests.v3_scenario_eval.harnesses import SURROGATES

        missing = {scenario.category for scenario in scenarios} - set(SURROGATES)
        assert missing == set()

    def test_loader_rejects_corrupt_library(self, tmp_path, monkeypatch):
        good = load_scenarios()
        lines = [json.dumps(scenario.to_payload(), ensure_ascii=False) for scenario in good]
        # 缺一个 case
        broken = lines[:-1]
        path = tmp_path / "broken.jsonl"
        path.write_text("\n".join(broken), encoding="utf-8")
        monkeypatch.setenv("V3_SCENARIOS_PATH", str(path))
        with pytest.raises(ValueError, match="scenario count"):
            load_scenarios()
        # 重复 case_id
        dup = tmp_path / "dup.jsonl"
        dup.write_text("\n".join([lines[0], lines[0]] + lines[1:261]), encoding="utf-8")
        monkeypatch.setenv("V3_SCENARIOS_PATH", str(dup))
        with pytest.raises(ValueError, match="duplicate case_id"):
            load_scenarios()
        # 未知 run_mode
        payload = json.loads(lines[0])
        payload["run_mode"] = "quantum"
        bad_mode = tmp_path / "mode.jsonl"
        bad_mode.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        monkeypatch.setenv("V3_SCENARIOS_PATH", str(bad_mode))
        with pytest.raises(ValueError, match="unknown run_mode"):
            load_scenarios()


# ---------------------------------------------------------------------------
# 全量运行：acceptance 硬线
# ---------------------------------------------------------------------------


class TestFullRun:
    def test_all_260_cases_in_results(self, results):
        assert results["summary"]["total"] == 260
        assert len(results["cases"]) == 260
        case_ids = [case["case_id"] for case in results["cases"]]
        assert case_ids == sorted(case_ids)
        assert len(set(case_ids)) == 260

    def test_summary_counts_consistent(self, results):
        summary = results["summary"]
        assert summary["pass"] + summary["fail"] + summary["unsupported"] == summary["total"]
        for bucket_set in (summary["by_run_mode"], summary["by_category"]):
            totals = {
                key: sum(bucket[key] for bucket in bucket_set.values()) for key in ("pass", "fail", "unsupported")
            }
            assert totals["pass"] == summary["pass"]
            assert totals["fail"] == summary["fail"]
            assert totals["unsupported"] == summary["unsupported"]

    def test_unsupported_is_honest(self, results):
        """unsupported：不计 PASS、必带 reason、集中在本轮三处已知判据缺口。"""
        unsupported = [case for case in results["cases"] if case["verdict"] == VERDICT_UNSUPPORTED]
        assert len(unsupported) == 72
        for case in unsupported:
            assert case["verdict"] != VERDICT_PASS
            assert case["reason"], f"{case['case_id']}: unsupported without reason"
            for attempt in case["attempts"]:
                assert any(item["status"] == ITEM_UNSUPPORTED for item in attempt["items"])
        unsupported_categories = {case["category"] for case in unsupported}
        assert unsupported_categories == EXPECTED_UNSUPPORTED_CATEGORIES

    def test_unsupported_never_counted_as_pass(self, results):
        """acceptance 硬线：聚合层不允许 unsupported 折算 pass。"""
        assert results["summary"]["unsupported"] == 72
        assert results["summary"]["pass"] == 188
        for case in results["cases"]:
            assert unsupported_must_not_pass(case)

    def test_reference_contract_supported_all_pass(self, results):
        """参考实现钉面：本轮有 checker 的 188 case 全 pass（fail 路径由 TestFailPath 单测证明）。"""
        for case in results["cases"]:
            if case["verdict"] != VERDICT_PASS:
                continue
            for attempt in case["attempts"]:
                assert all(item["status"] != ITEM_FAIL for item in attempt["items"])

    def test_case_payload_schema_stable(self, results):
        assert results["schema"] == RESULTS_SCHEMA_VERSION
        assert set(results) == EXPECTED_TOP_KEYS
        assert set(results["meta"]) == {
            "git_sha",
            "generated_at",
            "run_seed",
            "provider_config",
            "real_llm_calls",
            "scenario_source",
            "scenario_count",
            "verdict_semantics",
        }
        for case in results["cases"]:
            assert set(case) == EXPECTED_CASE_KEYS
            for attempt in case["attempts"]:
                assert set(attempt) == EXPECTED_ATTEMPT_KEYS
                assert attempt["verdict"] in VERDICTS
                for item in attempt["items"]:
                    assert set(item) == EXPECTED_ITEM_KEYS
                    assert item["status"] in {"pass", "fail", "unsupported"}

    def test_round_trip_json_stable(self, results):
        text = json.dumps(results, ensure_ascii=False)
        assert json.loads(text) == results

    def test_repeat_attempts_and_derived_seeds(self, results):
        for case in results["cases"]:
            assert len(case["attempts"]) == case["repeat"]
            seeds = {attempt["seed"] for attempt in case["attempts"]}
            assert len(seeds) == len(case["attempts"])  # per-attempt seed 互不相同
        pinned = next(case for case in results["cases"] if case["case_id"] == "V3-001")
        assert pinned["attempts"][0]["seed"] == derive_attempt_seed(7, "V3-001", 1) == 2291570066
        repeat5 = [case for case in results["cases"] if case["repeat"] == 5]
        assert len(repeat5) == EXPECTED_REPEAT5_COUNT
        assert all(len(case["attempts"]) == 5 for case in repeat5)

    def test_trace_ref_null_before_write(self, results):
        assert all(case["trace_ref"] is None for case in results["cases"])


# ---------------------------------------------------------------------------
# 确定性：seed
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_seed_deterministic(self):
        first = strip_volatile(run_round(run_seed=7, scenarios=load_scenarios()))
        second = strip_volatile(run_round(run_seed=7, scenarios=load_scenarios()))
        assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)

    def test_cross_seed_verdicts_stable_and_metrics_move(self):
        base = strip_volatile(run_round(run_seed=7, scenarios=load_scenarios()))
        other = strip_volatile(run_round(run_seed=99, scenarios=load_scenarios()))
        verdict_base = [
            (
                case["case_id"],
                case["verdict"],
                tuple(item["status"] for attempt in case["attempts"] for item in attempt["items"]),
            )
            for case in base["cases"]
        ]
        verdict_other = [
            (
                case["case_id"],
                case["verdict"],
                tuple(item["status"] for attempt in case["attempts"] for item in attempt["items"]),
            )
            for case in other["cases"]
        ]
        assert verdict_base == verdict_other
        metrics_base = {case["case_id"]: case["attempts"][0]["metrics"] for case in base["cases"]}
        metrics_other = {case["case_id"]: case["attempts"][0]["metrics"] for case in other["cases"]}
        moved = [case_id for case_id in metrics_base if metrics_base[case_id] != metrics_other[case_id]]
        assert len(moved) >= 100, "seed 未生效：跨 seed 指标几乎不变"


# ---------------------------------------------------------------------------
# 失败路径：checker 会咬人（防 all-green 剧场）
# ---------------------------------------------------------------------------


class TestFailPath:
    def test_security_violation_fails(self):
        items = grade_attempt(
            "security",
            "prompt injection in PDF",
            ("unauthorized effect=0",),
            {"unauthorized_effects": 1, "cross_user_leaks": 0, "permission_overrides": 0, "detail": {}},
        )
        assert items[0].status == ITEM_FAIL
        assert attempt_verdict(items) == "fail"

    def test_duplicate_run_fails(self):
        items = grade_attempt(
            "agent_runtime",
            "duplicate approval",
            ("no duplicate side effect",),
            {
                "final_state": "running",
                "allowed_final_states": ["running", "terminal_success"],
                "side_effect_count": 0,
                "duplicate_run_started": True,
                "receipt": {"state_consistent_with_ledger": True},
                "events": [],
            },
        )
        assert items[0].status == ITEM_FAIL

    def test_proactive_action_without_value_fails(self):
        items = grade_attempt(
            "proactive",
            "no new information",
            ("NO_ACTION when no new value",),
            {"action": "suggest", "why_now": "x", "gated_by_mute_or_cooldown": False, "suppressed_by_cooldown": False},
        )
        assert items[0].status == ITEM_FAIL

    def test_unsupported_item_never_yields_pass(self):
        items = grade_attempt(
            "first_value",
            "fresh user variant 1: 两周内完成可演示的 AI 产品",
            ("≤3min reach useful action", "no fake history"),
            {"fresh_user_history_ledger": [], "cards": [], "synthetic_ttfu_seconds": 60.0},
        )
        assert items[0].status == ITEM_UNSUPPORTED
        assert attempt_verdict(items) == VERDICT_UNSUPPORTED

    def test_case_verdict_unsupported_dominates(self):
        from tests.v3_scenario_eval.grading import VERDICT_FAIL, AttemptResult

        passing = AttemptResult(attempt=1, seed=1, verdict=VERDICT_PASS)
        failing = AttemptResult(attempt=1, seed=2, verdict=VERDICT_FAIL)
        degrading = AttemptResult(attempt=1, seed=3, verdict=VERDICT_UNSUPPORTED)
        assert case_verdict([passing, failing]) == VERDICT_FAIL
        assert case_verdict([passing, degrading]) == VERDICT_UNSUPPORTED
        assert case_verdict([failing, degrading]) == VERDICT_UNSUPPORTED

    def test_no_checker_reason_is_explicit(self):
        items = grade_attempt("unknown_category", "x", ("anything",), {})
        assert items[0].status == ITEM_UNSUPPORTED
        assert items[0].detail == REASON_NO_CHECKER


# ---------------------------------------------------------------------------
# 红线：真实 LLM 0 次 + provider 配置面
# ---------------------------------------------------------------------------


class TestRealModelZeroCall:
    def test_meta_declares_zero(self, results):
        assert results["meta"]["real_llm_calls"] == 0
        assert results["meta"]["provider_config"]["provider"] == "mock"

    def test_adapter_unconditionally_refuses(self):
        adapter = RealModelAdapter()
        with pytest.raises(RealModelDisabledError):
            adapter.complete("hello", provider="zhipu", model="glm-4")

    def test_real_provider_config_yields_honest_unsupported(self):
        payload = run_round(
            run_seed=7, provider_raw={"provider": "zhipu", "model": "glm-4"}, scenarios=load_scenarios()
        )
        assert payload["meta"]["real_llm_calls"] == 0
        model_cases = [case for case in payload["cases"] if case["harness"] == "model"]
        assert model_cases
        for case in model_cases:
            assert case["verdict"] == VERDICT_UNSUPPORTED
            assert REASON_REAL_MODEL_ZERO_CALL in case["reason"]
        # 非 model 型 case 不经过模型 provider，判定面不受影响。
        non_model = [case for case in payload["cases"] if case["harness"] != "model"]
        assert all(case["verdict"] in {"pass", "unsupported"} for case in non_model)

    def test_unknown_provider_rejected(self):
        with pytest.raises(ValueError, match="unknown provider"):
            run_round(run_seed=7, provider_raw={"provider": "skynet"}, scenarios=load_scenarios())


# ---------------------------------------------------------------------------
# evidence 落盘
# ---------------------------------------------------------------------------


class TestEvidenceWrite:
    def test_write_evidence_round(self, results, tmp_path):
        out = tmp_path / "v3run" / "results.json"
        write_evidence(json.loads(json.dumps(results, ensure_ascii=False)), out)
        assert out.exists()
        evidence_dir = out.parent / "evidence"
        evidence_files = sorted(evidence_dir.glob("V3-*.json"))
        assert len(evidence_files) == 260
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert all(case["trace_ref"] == f"evidence/{case['case_id']}.json" for case in payload["cases"])
        sample = json.loads(evidence_files[0].read_text(encoding="utf-8"))
        assert {"schema", "case_id", "input", "expected", "verdict", "attempts", "provenance"} <= set(sample)
        assert payload["summary"]["total"] == 260
