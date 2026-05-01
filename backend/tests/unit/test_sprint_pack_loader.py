"""Unit tests for sprint_pack_loader — priority sorting, load, and query helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make the backend app importable without the full FastAPI stack
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.sprint_packs.sprint_pack_loader import (
    get_archetypes_by_nodes,
    get_mistake_by_nodes,
    get_task_template,
    load_pack,
    query_nodes_by_priority,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def cn_pack() -> dict:
    pack = load_pack("计算机网络", "v1")
    assert pack is not None, "computer_networks_v1.json must be loadable"
    return pack


@pytest.fixture(scope="module")
def ds_pack() -> dict:
    pack = load_pack("数据结构", "v1")
    assert pack is not None, "data_structures_algorithms_v1.json must be loadable"
    return pack


@pytest.fixture(scope="module")
def mathematics_pack() -> dict:
    pack = load_pack("高数", "v1")
    assert pack is not None, "mathematics_v1.json must be loadable"
    return pack


# ---------------------------------------------------------------------------
# load_pack
# ---------------------------------------------------------------------------

class TestLoadPack:
    def test_load_by_chinese_name(self):
        pack = load_pack("计算机网络")
        assert pack is not None

    def test_load_by_alias(self):
        assert load_pack("计网") is not None
        assert load_pack("computer_networks") is not None

    def test_load_data_structures_algorithm_aliases(self):
        assert load_pack("数据结构") is not None
        assert load_pack("数结") is not None
        assert load_pack("ds") is not None
        assert load_pack("算法") is not None
        assert load_pack("algo") is not None

    def test_load_mathematics_aliases(self):
        assert load_pack("高数") is not None
        assert load_pack("高等数学") is not None
        assert load_pack("线代") is not None
        assert load_pack("线性代数") is not None
        assert load_pack("数学") is not None
        assert load_pack("math") is not None

    def test_missing_subject_returns_none(self):
        assert load_pack("nonexistent_subject_xyz") is None

    def test_empty_subject_returns_none(self):
        assert load_pack("") is None

    def test_pack_has_required_top_level_keys(self, cn_pack):
        required = {
            "knowledge_nodes",
            "question_archetypes",
            "mistake_types",
            "paths",
            "strategy_presets",
            "task_card_templates",
            "aurora_rules",
            "last_24h_strategy",
            "priority_matrix",
        }
        assert required.issubset(set(cn_pack.keys()))

    def test_priority_matrix_has_formula(self, cn_pack):
        pm = cn_pack.get("priority_matrix", {})
        assert "formula" in pm
        formula = pm["formula"]
        # Formula must reference the key variables
        for term in ("exam_weight", "frequency", "gap", "trainability", "time_cost", "difficulty"):
            assert term in formula, f"Formula missing term: {term}"


# ---------------------------------------------------------------------------
# JSON data quality
# ---------------------------------------------------------------------------

class TestJsonDataQuality:
    def test_minimum_node_count(self, cn_pack):
        assert len(cn_pack["knowledge_nodes"]) >= 35

    def test_minimum_archetype_count(self, cn_pack):
        assert len(cn_pack["question_archetypes"]) >= 15

    def test_minimum_mistake_count(self, cn_pack):
        assert len(cn_pack["mistake_types"]) >= 8

    def test_mathematics_pack_acceptance_shape(self, mathematics_pack):
        assert len(mathematics_pack["knowledge_nodes"]) >= 50
        assert len(mathematics_pack["mistake_types"]) == 55
        assert len(mathematics_pack["question_archetypes"]) == 20

    def test_node_weights_in_range(self, cn_pack):
        for node in cn_pack["knowledge_nodes"]:
            nid = node["node_id"]
            assert 0.0 <= node["exam_weight"] <= 1.0, f"{nid}: exam_weight={node['exam_weight']} out of [0,1]"
            assert 0.0 <= node["frequency"] <= 1.0, f"{nid}: frequency={node['frequency']} out of [0,1]"
            assert 0.0 <= node["trainability"] <= 1.0, f"{nid}: trainability={node['trainability']} out of [0,1]"
            assert node["time_cost"] > 0, f"{nid}: time_cost must be positive"
            assert node["difficulty"] >= 1, f"{nid}: difficulty must be ≥1"

    def test_minimum_pass_top5_are_high_frequency(self, cn_pack):
        """The top-5 minimum-pass nodes must be genuinely high-frequency exam topics."""
        mp_nodes = cn_pack["paths"]["minimum_pass"]["ordered_nodes"][:5]
        nodes_by_id = {n["node_id"]: n for n in cn_pack["knowledge_nodes"]}
        for nid in mp_nodes:
            node = nodes_by_id[nid]
            score = node["exam_weight"] * node["frequency"]
            assert score >= 0.4, (
                f"{nid} is in min-pass top-5 but exam_weight*frequency={score:.2f} < 0.4"
            )

    def test_paths_have_required_keys(self, cn_pack):
        paths = cn_pack["paths"]
        assert "minimum_pass" in paths
        assert "score_max" in paths
        assert len(paths["minimum_pass"].get("ordered_nodes", [])) > 0
        assert len(paths["score_max"].get("ordered_nodes", [])) > 0

    def test_strategy_7d_daily_ratio_sums_to_one(self, cn_pack):
        ratio = cn_pack["strategy_presets"]["7d"]["daily_ratio"]
        total = sum(ratio.values())
        assert abs(total - 1.0) < 1e-6, f"7d daily_ratio sums to {total}, expected 1.0"

    def test_task_card_templates_count(self, cn_pack):
        count = len(cn_pack["task_card_templates"])
        assert 3 <= count <= 10

    def test_aurora_rules_have_trigger_conditions(self, cn_pack):
        for key, rule in cn_pack["aurora_rules"].items():
            assert "trigger_conditions" in rule or "trigger_condition" in rule, (
                f"aurora_rules.{key} missing trigger_conditions"
            )

    def test_json_is_valid_and_reloadable(self, cn_pack):
        import json
        from pathlib import Path
        path = Path(__file__).parents[2] / "app/sprint_packs/computer_networks_v1.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["id"] == "computer_networks@v1"

    def test_data_structures_algorithms_pack_acceptance(self, ds_pack):
        assert len(ds_pack["knowledge_nodes"]) >= 45
        quicksort_mistakes = get_mistake_by_nodes(ds_pack, ["ds.quicksort"])
        assert len(quicksort_mistakes) >= 2
        assert "ds.quicksort" in ds_pack["paths"]["minimum_pass"]["ordered_nodes"]

    def test_data_structures_algorithms_templates_and_checkpoints_are_complete(self, ds_pack):
        assert ds_pack["checkpoint_rules"]["pass_threshold"] == 60
        assert ds_pack["checkpoint_rules"]["checkpoint_intervals"]["7d"] == [3, 5, 7]
        for template in ds_pack["task_card_templates"]:
            assert template["description"]
            assert template["steps"]
            assert template["done_criteria"]
            assert template["duration_minutes"] > 0


# ---------------------------------------------------------------------------
# query_nodes_by_priority — sorting logic
# ---------------------------------------------------------------------------

class TestQueryNodesByPriority:
    def test_returns_list_of_nodes(self, cn_pack):
        result = query_nodes_by_priority(cn_pack)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_mathematics_last_day_first_node_is_minimum_pass(self, mathematics_pack):
        result = query_nodes_by_priority(mathematics_pack, days_left=1)
        assert result[0]["minimum_pass_required"] is True

    def test_fully_mastered_node_ranks_lower(self, cn_pack):
        """A node with gap=0 (mastery=1.0) should rank lower than same node with gap=1.0."""
        # Pick a real high-weight node
        target = "cn.tcp_congestion_control"
        mastered = query_nodes_by_priority(cn_pack, current_mastery={target: 1.0}, path_mode="all")
        not_mastered = query_nodes_by_priority(cn_pack, current_mastery={target: 0.0}, path_mode="all")

        def rank_of(results: list, nid: str) -> int:
            ids = [n["node_id"] for n in results]
            return ids.index(nid) if nid in ids else len(ids)

        assert rank_of(mastered, target) > rank_of(not_mastered, target), (
            "Fully mastered node should rank lower (higher index) than unmastered"
        )

    def test_high_weight_node_ranks_above_low_weight(self, cn_pack):
        """cn.subnetting (w=1.0) should outrank cn.multiplexing (w=0.40) when both are unmastered."""
        result = query_nodes_by_priority(cn_pack, current_mastery={}, path_mode="all")
        ids = [n["node_id"] for n in result]
        assert "cn.subnetting" in ids and "cn.multiplexing" in ids
        assert ids.index("cn.subnetting") < ids.index("cn.multiplexing"), (
            "cn.subnetting (w=1.0) should rank ahead of cn.multiplexing (w=0.4)"
        )

    def test_time_pressure_boosts_minimum_pass_nodes(self, cn_pack):
        """With days_left=2, minimum_pass nodes should occupy the majority of top-10."""
        result = query_nodes_by_priority(cn_pack, days_left=2, path_mode="minimum_pass")
        top_10 = result[:10]
        mp_nodes = set(cn_pack["paths"]["minimum_pass"]["ordered_nodes"])
        mp_in_top = sum(1 for n in top_10 if n["node_id"] in mp_nodes)
        assert mp_in_top >= 5, (
            f"Under high time pressure only {mp_in_top}/10 top nodes are minimum_pass nodes"
        )

    def test_priority_score_ordering_is_monotone_descending(self, cn_pack):
        """Computed priority scores should be non-increasing."""
        mastery = {}
        nodes_by_id = {n["node_id"]: n for n in cn_pack["knowledge_nodes"]}
        result = query_nodes_by_priority(cn_pack, current_mastery=mastery, path_mode="all")

        scores = []
        for node in result:
            ew = node["exam_weight"]
            fr = node["frequency"]
            gap = 1.0
            tr = node["trainability"]
            tc = max(1.0, node["time_cost"])
            di = max(1.0, node["difficulty"])
            mp_boost = 1.2 if node.get("minimum_pass_required") else 1.0
            scores.append(ew * fr * gap * tr * mp_boost / (tc * di))

        for i in range(1, len(scores)):
            assert scores[i] <= scores[i - 1] + 1e-9, (
                f"Score is not monotone descending at index {i}: {scores[i-1]:.6f} -> {scores[i]:.6f}"
            )

    def test_empty_mastery_dict_treated_as_zero_mastery(self, cn_pack):
        r1 = query_nodes_by_priority(cn_pack, current_mastery=None, path_mode="all")
        r2 = query_nodes_by_priority(cn_pack, current_mastery={}, path_mode="all")
        assert [n["node_id"] for n in r1] == [n["node_id"] for n in r2]

    def test_path_mode_minimum_pass_filters_to_path_nodes(self, cn_pack):
        mp_ids = set(cn_pack["paths"]["minimum_pass"]["ordered_nodes"])
        result = query_nodes_by_priority(cn_pack, path_mode="minimum_pass")
        result_ids = {n["node_id"] for n in result}
        assert result_ids == mp_ids, "minimum_pass mode must return only path nodes"

    def test_path_mode_all_returns_all_nodes(self, cn_pack):
        all_ids = {n["node_id"] for n in cn_pack["knowledge_nodes"]}
        result = query_nodes_by_priority(cn_pack, path_mode="all")
        result_ids = {n["node_id"] for n in result}
        assert result_ids == all_ids


# ---------------------------------------------------------------------------
# get_mistake_by_nodes
# ---------------------------------------------------------------------------

class TestGetMistakeByNodes:
    def test_returns_mistakes_for_known_node(self, cn_pack):
        # cn.osi_model appears in multiple mistake related_nodes
        mistakes = get_mistake_by_nodes(cn_pack, ["cn.osi_model"])
        assert len(mistakes) >= 1
        assert all("repair_strategy" in m for m in mistakes)

    def test_no_match_for_unknown_node(self, cn_pack):
        result = get_mistake_by_nodes(cn_pack, ["cn.nonexistent_node_xyz"])
        assert result == []

    def test_empty_node_list_returns_empty(self, cn_pack):
        assert get_mistake_by_nodes(cn_pack, []) == []

    def test_tcp_nodes_return_tcp_specific_mistakes(self, cn_pack):
        mistakes = get_mistake_by_nodes(cn_pack, ["cn.tcp_three_way", "cn.tcp_reliable_transport"])
        mistake_ids = {m["mistake_id"] for m in mistakes}
        # Should find at least one TCP-specific mistake
        assert any("tcp" in mid or "ack" in mid or "window" in mid for mid in mistake_ids), (
            f"Expected TCP-related mistakes, got: {mistake_ids}"
        )


# ---------------------------------------------------------------------------
# get_archetypes_by_nodes
# ---------------------------------------------------------------------------

class TestGetArchetypesByNodes:
    def test_returns_archetypes_for_subnetting_node(self, cn_pack):
        archetypes = get_archetypes_by_nodes(cn_pack, ["cn.subnetting"])
        assert len(archetypes) >= 1

    def test_no_match_for_unknown_node(self, cn_pack):
        result = get_archetypes_by_nodes(cn_pack, ["cn.unknown_xyz"])
        assert result == []

    def test_archetypes_have_required_fields(self, cn_pack):
        archetypes = get_archetypes_by_nodes(cn_pack, ["cn.tcp_three_way"])
        for a in archetypes:
            assert "archetype_id" in a
            assert "label" in a
            assert "knowledge_nodes" in a
            assert "difficulty" in a


# ---------------------------------------------------------------------------
# get_task_template
# ---------------------------------------------------------------------------

class TestGetTaskTemplate:
    def test_find_by_template_id(self, cn_pack):
        result = get_task_template(cn_pack, "concept_recall_card")
        assert result is not None
        assert result["template_id"] == "concept_recall_card"

    def test_case_insensitive(self, cn_pack):
        result = get_task_template(cn_pack, "CONCEPT_RECALL_CARD")
        assert result is not None

    def test_missing_template_returns_none(self, cn_pack):
        assert get_task_template(cn_pack, "nonexistent_template_xyz") is None

    def test_all_known_templates_are_findable(self, cn_pack):
        for template in cn_pack["task_card_templates"]:
            tid = template["template_id"]
            assert get_task_template(cn_pack, tid) is not None, f"Template {tid} not findable"
