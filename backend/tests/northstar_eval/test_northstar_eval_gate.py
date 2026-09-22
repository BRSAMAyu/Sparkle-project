"""NORTHSTAR · 北极星评估 runner 骨架冒烟门禁（pytest 断言面）。

钉住 acceptance：
- **空场景冒烟 ×2**：空旅程库 run_round 汇总诚实为 0 且 schema 稳定；CLI 默认（无库文件）同；
- **spec case 冒烟**：NS-001 三臂出全；sparkle 臂确定性 checkpoint 全过；CP-98/99 诚实
  unsupported 且永不折算 pass；臂间比较方向与结构性论证一致（假设先验下）；
- **确定性**：同 seed 逐字节一致；跨 seed 判定稳定而指标可见 seed 生效；
- **红线**：真实 LLM 0 次（mock-only provider 门）。
"""

from __future__ import annotations

import json

import pytest

from tests.northstar_eval.grading import (
    ITEM_PASS,
    ITEM_UNSUPPORTED,
    REASON_REQUIRES_HUMAN_SELF_REPORT,
    REASON_REQUIRES_REAL_WALL_CLOCK,
    VERDICT_UNSUPPORTED,
    unsupported_must_not_pass,
)
from tests.northstar_eval.journey_schema import (
    CHECKPOINT_UNSUPPORTED,
    load_journeys,
    spec_case_journey,
)
from tests.northstar_eval.runner import (
    RESULTS_SCHEMA_VERSION,
    main,
    run_round,
    strip_volatile,
    write_evidence,
)

EXPECTED_TOP_KEYS = {"schema", "meta", "summary", "cases"}
EXPECTED_META_KEYS = {
    "git_sha",
    "generated_at",
    "run_seed",
    "provider_config",
    "real_llm_calls",
    "journey_source",
    "journey_count",
    "verdict_semantics",
    "prior_disclosure",
}
EXPECTED_CASE_KEYS = {
    "journey_id",
    "arm",
    "attempt",
    "seed",
    "verdict",
    "reason",
    "checkpoints",
    "metrics",
    "trace_ref",
    "evidence",
}
EXPECTED_ITEM_KEYS = {"text", "status", "detail"}
DETERMINISTIC_CHECKPOINTS = [
    "CP-00 baseline recorded and syllabus mapped",
    "CP-01 plan targets weakest exam-weighted nodes with human confirmation",
    "CP-02 quiz score trajectory non-decreasing",
    "CP-03 mistakes fully land in error book with mastery sync",
    "CP-04 next-day plan adapts to previous outcome",
    "CP-05 review hit rate at or above threshold",
    "CP-06 weighted coverage at or above threshold by last study day",
    "CP-07 posttest gain at or above MDE",
    "CP-08 forgetting rate at or below threshold",
]


@pytest.fixture(scope="module")
def spec_results() -> dict:
    return run_round(run_seed=7, journeys=[spec_case_journey()])


# ---------------------------------------------------------------------------
# 空场景冒烟 ×2（acceptance 最低钉面）
# ---------------------------------------------------------------------------


class TestEmptySmokes:
    def test_empty_library_round_is_zero_and_schema_stable(self, tmp_path):
        library = tmp_path / "empty.jsonl"
        library.write_text("", encoding="utf-8")
        journeys = load_journeys(library)
        assert journeys == []
        payload = run_round(run_seed=7, journeys=journeys)
        assert payload["schema"] == RESULTS_SCHEMA_VERSION
        assert set(payload) == EXPECTED_TOP_KEYS
        assert set(payload["meta"]) == EXPECTED_META_KEYS
        assert payload["summary"]["total"] == 0
        assert payload["summary"]["pass"] == 0
        assert payload["meta"]["real_llm_calls"] == 0
        assert payload["meta"]["journey_count"] == 0

    def test_cli_without_library_runs_honest_zero(self, tmp_path, capsys, monkeypatch):
        monkeypatch.delenv("NORTHSTAR_JOURNEYS_PATH", raising=False)
        out = tmp_path / "nsrun" / "results.json"
        assert main(["--out", str(out)]) == 0
        captured = capsys.readouterr()
        assert "wrote 0 case results" in captured.err
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["summary"]["total"] == 0
        assert payload["meta"]["real_llm_calls"] == 0

    def test_loader_rejects_malformed_journey(self, tmp_path):
        good = spec_case_journey().to_payload()
        # 缺字段
        broken = tmp_path / "missing.jsonl"
        broken.write_text(json.dumps({key: value for key, value in good.items() if key != "arms"}), encoding="utf-8")
        with pytest.raises(ValueError, match="missing fields"):
            load_journeys(broken)
        # 未知 arm
        bad_arm = tmp_path / "bad_arm.jsonl"
        bad_arm.write_text(json.dumps({**good, "arms": ["control_claude"]}), encoding="utf-8")
        with pytest.raises(ValueError, match="unknown arms"):
            load_journeys(bad_arm)
        # checkpoint 越词表
        bad_cp = tmp_path / "bad_cp.jsonl"
        bad_cp.write_text(json.dumps({**good, "expected": ["CP-77 invented checkpoint"]}), encoding="utf-8")
        with pytest.raises(ValueError, match="outside frozen checkpoint vocab"):
            load_journeys(bad_cp)
        # 重复 journey_id
        dup = tmp_path / "dup.jsonl"
        dup.write_text("\n".join([json.dumps(good), json.dumps(good)]), encoding="utf-8")
        with pytest.raises(ValueError, match="duplicate journey_id"):
            load_journeys(dup)


# ---------------------------------------------------------------------------
# spec case（NS-001）三臂冒烟
# ---------------------------------------------------------------------------


class TestSpecCase:
    def test_three_arms_present_with_frozen_keys(self, spec_results):
        assert spec_results["schema"] == RESULTS_SCHEMA_VERSION
        assert len(spec_results["cases"]) == 3
        assert {case["arm"] for case in spec_results["cases"]} == {"sparkle", "control_gpt", "control_dsk"}
        assert {case["journey_id"] for case in spec_results["cases"]} == {"NS-001"}
        for case in spec_results["cases"]:
            assert set(case) == EXPECTED_CASE_KEYS
            assert {item["text"] for item in case["checkpoints"]} == set(
                DETERMINISTIC_CHECKPOINTS + list(CHECKPOINT_UNSUPPORTED)
            )
            for item in case["checkpoints"]:
                assert set(item) == EXPECTED_ITEM_KEYS

    @pytest.mark.parametrize("seed", [7, 99, 1234])
    def test_sparkle_deterministic_checkpoints_all_pass(self, seed):
        payload = run_round(run_seed=seed, journeys=[spec_case_journey()])
        sparkle = next(case for case in payload["cases"] if case["arm"] == "sparkle")
        by_text = {item["text"]: item for item in sparkle["checkpoints"]}
        for text in DETERMINISTIC_CHECKPOINTS:
            assert by_text[text]["status"] == ITEM_PASS, f"seed={seed} {text}: {by_text[text]['detail']}"

    def test_real_world_checkpoints_honest_unsupported_and_never_pass(self, spec_results):
        for case in spec_results["cases"]:
            assert case["verdict"] == VERDICT_UNSUPPORTED
            assert case["reason"], f"{case['arm']}: unsupported without reason"
            assert unsupported_must_not_pass(case)
            by_text = {item["text"]: item for item in case["checkpoints"]}
            cp98 = by_text["CP-98 daily cognitive load self-report"]
            cp99 = by_text["CP-99 full mock exam wall clock at or below budget"]
            assert cp98["status"] == ITEM_UNSUPPORTED and cp98["detail"] == REASON_REQUIRES_HUMAN_SELF_REPORT
            assert cp99["status"] == ITEM_UNSUPPORTED and cp99["detail"] == REASON_REQUIRES_REAL_WALL_CLOCK

    def test_sparkle_outperforms_controls_under_priors(self, spec_results):
        """假设先验下臂间方向必须与结构性论证一致（这不是增益证据，是管线自检）。"""
        delta = spec_results["summary"]["sparkle_minus_best_control"]
        assert delta["gain"] > 0
        assert delta["gain_per_hour"] > 0
        assert delta["forgetting_rate"] < 0
        assert delta["weighted_coverage"] > 0
        assert delta["review_hit_rate"] > 0
        sparkle = next(case for case in spec_results["cases"] if case["arm"] == "sparkle")
        assert sparkle["metrics"]["stale_memory_surfaces"] == 0.0
        assert sparkle["metrics"]["mastery_calibration_error"] < 0.15

    def test_determinism_and_cross_seed_stability(self):
        first = strip_volatile(run_round(run_seed=7, journeys=[spec_case_journey()]))
        second = strip_volatile(run_round(run_seed=7, journeys=[spec_case_journey()]))
        assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
        other = strip_volatile(run_round(run_seed=99, journeys=[spec_case_journey()]))
        verdict_shape = [
            (case["journey_id"], case["arm"], case["verdict"], tuple(item["status"] for item in case["checkpoints"]))
            for case in first["cases"]
        ]
        verdict_shape_other = [
            (case["journey_id"], case["arm"], case["verdict"], tuple(item["status"] for item in case["checkpoints"]))
            for case in other["cases"]
        ]
        assert verdict_shape == verdict_shape_other
        metrics_moved = any(
            first["cases"][i]["metrics"] != other["cases"][i]["metrics"] for i in range(len(first["cases"]))
        )
        assert metrics_moved, "seed 未生效：跨 seed 指标完全不变"

    def test_mock_only_provider_red_line(self):
        with pytest.raises(ValueError, match="zero-call red line"):
            run_round(run_seed=7, journeys=[spec_case_journey()], provider_raw={"provider": "zhipu"})

    def test_write_evidence_round(self, spec_results, tmp_path):
        out = tmp_path / "nsrun" / "results.json"
        write_evidence(json.loads(json.dumps(spec_results, ensure_ascii=False)), out)
        assert out.exists()
        evidence_files = sorted((out.parent / "evidence").glob("NS-001_*.json"))
        assert len(evidence_files) == 3
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert all(case["trace_ref"] for case in payload["cases"])
        sample = json.loads(evidence_files[0].read_text(encoding="utf-8"))
        assert {"schema", "journey_id", "arm", "verdict", "checkpoints", "metrics", "provenance"} <= set(sample)
