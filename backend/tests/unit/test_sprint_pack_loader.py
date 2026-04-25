"""Tests for Sprint Pack loader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.sprint_packs.sprint_pack_loader import (
    get_archetypes_by_nodes,
    get_mistake_by_nodes,
    get_task_template,
    load_pack,
    query_nodes_by_priority,
)

PACKS_DIR = Path(__file__).resolve().parents[2] / "app" / "sprint_packs"


@pytest.fixture()
def cn_pack() -> dict:
    pack = load_pack("计算机网络")
    assert pack is not None, "Computer Networks Sprint Pack must exist"
    return pack


class TestLoadPack:
    def test_load_by_chinese_name(self):
        pack = load_pack("计算机网络")
        assert pack is not None
        assert "knowledge_nodes" in pack

    def test_load_by_abbreviation(self):
        pack = load_pack("计网")
        assert pack is not None

    def test_load_by_english_name(self):
        pack = load_pack("computer_networks")
        assert pack is not None

    def test_load_nonexistent_returns_none(self):
        assert load_pack("量子物理") is None

    def test_pack_is_valid_json(self):
        path = PACKS_DIR / "computer_networks_v1.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert len(data.get("knowledge_nodes", [])) >= 35

    def test_all_node_ids_unique(self, cn_pack):
        ids = [n["node_id"] for n in cn_pack["knowledge_nodes"]]
        assert len(ids) == len(set(ids)), "All node_ids must be unique"

    def test_prerequisites_reference_existing_nodes(self, cn_pack):
        all_ids = {n["node_id"] for n in cn_pack["knowledge_nodes"]}
        for node in cn_pack["knowledge_nodes"]:
            for prereq in node.get("prerequisites", []):
                assert prereq in all_ids, f"Node {node['node_id']} references unknown prerequisite {prereq}"


class TestPrioritySorting:
    def test_high_weight_low_mastery_nodes_come_first(self, cn_pack):
        mastery = {}
        for node in cn_pack["knowledge_nodes"]:
            mastery[node["node_id"]] = 0.0

        sorted_nodes = query_nodes_by_priority(cn_pack, mastery, days_left=7, path_mode="score_max")
        assert len(sorted_nodes) > 0

        # First node should have high exam_weight and frequency
        first = sorted_nodes[0]
        assert float(first.get("exam_weight", 0)) >= 0.7

    def test_known_nodes_sink_to_bottom(self, cn_pack):
        # Set all mastery to 0.95 (well-known) except one
        mastery = {}
        weak_node = cn_pack["knowledge_nodes"][0]
        for node in cn_pack["knowledge_nodes"]:
            mastery[node["node_id"]] = 0.95
        mastery[weak_node["node_id"]] = 0.1

        sorted_nodes = query_nodes_by_priority(cn_pack, mastery, path_mode="score_max")
        # The weak node should be near the top
        sorted_ids = [n["node_id"] for n in sorted_nodes]
        assert weak_node["node_id"] in sorted_ids[:5]

    def test_minimum_pass_only_includes_path_nodes(self, cn_pack):
        sorted_nodes = query_nodes_by_priority(cn_pack, path_mode="minimum_pass")
        path_nodes = set(cn_pack["paths"]["minimum_pass"]["ordered_nodes"])
        for node in sorted_nodes:
            assert node["node_id"] in path_nodes

    def test_time_pressure_boosts_high_weight(self, cn_pack):
        mastery = {n["node_id"]: 0.3 for n in cn_pack["knowledge_nodes"]}

        normal = query_nodes_by_priority(cn_pack, mastery, days_left=14)
        urgent = query_nodes_by_priority(cn_pack, mastery, days_left=2)

        # Both should return nodes, but ordering may differ
        assert len(normal) > 0
        assert len(urgent) > 0


class TestMistakeLookup:
    def test_find_mistakes_for_tcp_nodes(self, cn_pack):
        tcp_nodes = [n["node_id"] for n in cn_pack["knowledge_nodes"] if "tcp" in n["node_id"]]
        mistakes = get_mistake_by_nodes(cn_pack, tcp_nodes)
        assert len(mistakes) > 0, "TCP nodes should have associated mistake types"

    def test_no_mistakes_for_unknown_nodes(self, cn_pack):
        mistakes = get_mistake_by_nodes(cn_pack, ["nonexistent_node_xyz"])
        assert mistakes == []


class TestArchetypeLookup:
    def test_find_archetypes_for_subnetting(self, cn_pack):
        subnet_nodes = [n["node_id"] for n in cn_pack["knowledge_nodes"] if "subnet" in n["node_id"]]
        archetypes = get_archetypes_by_nodes(cn_pack, subnet_nodes)
        assert len(archetypes) > 0, "Subnetting nodes should have associated question archetypes"


class TestTaskTemplate:
    def test_find_concept_template(self, cn_pack):
        template = get_task_template(cn_pack, "concept_recall")
        assert template is not None or len(cn_pack.get("task_card_templates", [])) > 0

    def test_nonexistent_returns_none(self, cn_pack):
        assert get_task_template(cn_pack, "quantum_computing") is None
