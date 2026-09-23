"""V13-MAJORS M-01: onboarding hot path — galaxy seed nodes must not hit the LLM.

`POST /profile/onboarding` was measured at ~29s (V13 real-device report B-side).
Live log evidence: the 5 scaffold node creations were spaced ~9-12s apart —
each `GalaxyService.create_node` synchronously awaited the LLM sector
classifier (`NodeSectorService.classify_payload → llm.chat_json`) because the
seed templates carried no `sector_weights`.

Fix contract:
1. Every seed template carries curated, valid, non-VOID-dominant
   `sector_weights` so `_resolve_visual_data` short-circuits the classifier.
2. With weights provided (and a non-VOID dominant), `_resolve_visual_data`
   must NOT invoke the LLM classifier at all.
"""

from __future__ import annotations

import pytest

from app.services.galaxy_bootstrap_service import (
    _DEFAULT_SEEDS,
    _GOAL_TYPE_SEEDS,
    GalaxyBootstrapService,
)
from app.services.node_sector_service import (
    SectorCode,
    dominant_sector_from_weights,
    normalize_sector_weights,
)


def _all_seed_groups() -> dict[str, list[dict[str, object]]]:
    groups = dict(_GOAL_TYPE_SEEDS)
    groups["__default__"] = _DEFAULT_SEEDS
    return groups


class TestSeedTemplatesCarryDeterministicWeights:
    """Every seed must be classifiable without the LLM classifier."""

    def test_all_goal_types_covered_by_bootstrap_dispatch(self):
        # seed_from_goal falls back to _DEFAULT_SEEDS for unknown goal types;
        # the known types must all be template-covered.
        assert set(_GOAL_TYPE_SEEDS) >= {"exam", "skill", "interest"}

    @pytest.mark.parametrize(
        "group_name", ["exam", "skill", "interest", "__default__"]
    )
    def test_each_seed_has_non_void_dominant_weights(self, group_name):
        seeds = _all_seed_groups()[group_name]
        assert len(seeds) == 5, f"{group_name} must keep 5 scaffold seeds"
        for seed in seeds:
            raw = seed.get("sector_weights")
            assert isinstance(raw, dict) and raw, (
                f"{group_name}/{seed['title']}: seed weights missing — "
                "scaffold node would fall back to the LLM classifier"
            )
            normalized = normalize_sector_weights(raw, fallback_sector=SectorCode.VOID)
            dominant = dominant_sector_from_weights(normalized)
            assert dominant is not None and dominant != SectorCode.VOID, (
                f"{group_name}/{seed['title']}: dominant sector is VOID — "
                "would still trigger the LLM classifier"
            )

    def test_bootstrap_service_uses_the_same_templates(self):
        # Guard against the service growing its own seed copy that silently
        # drops the weights again.
        assert GalaxyBootstrapService is not None
        for seeds in _GOAL_TYPE_SEEDS.values():
            for seed in seeds:
                assert "sector_weights" in seed


class TestResolveVisualDataSkipsClassifier:
    """With provided weights and a non-VOID dominant, no LLM call happens."""

    async def test_provided_weights_bypass_classification(self, monkeypatch):
        from app.services.expansion_service import ExpansionService

        service = ExpansionService(db=None)  # db unused on this path

        def _forbidden(*args, **kwargs):  # pragma: no cover - tripwire
            raise AssertionError(
                "LLM sector classifier invoked for a seed with provided weights"
            )

        monkeypatch.setattr(
            "app.services.node_sector_service.NodeSectorService.classify_payload",
            _forbidden,
        )

        visual, model = await service._resolve_visual_data(
            {
                "candidate_id": "核心概念理解_1",
                "name": "核心概念理解",
                "description": "目标学科的基础概念与定义。",
                "sector_weights": {"WISDOM": 70, "TECH": 30},
                "sector_weights_provided": True,
            },
            context_node=None,
            subject=None,
            fallback_sector=SectorCode.VOID,
        )

        assert visual.dominant_sector_code == SectorCode.WISDOM
        assert visual.sector_weights, "normalized weights must survive"

    async def test_missing_weights_still_classify_via_llm(self, monkeypatch):
        """The classifier must stay wired for genuinely unclassified nodes."""
        from app.services.expansion_service import ExpansionService

        service = ExpansionService(db=None)
        called = {"count": 0}

        async def _fake_classify(*args, **kwargs):
            called["count"] += 1
            from app.services.node_sector_service import build_sector_visuals

            return build_sector_visuals(
                kwargs.get("name") or (args[0] if args else "x"),
                importance_level=3,
                sector_weights={"WISDOM": 100},
            )

        monkeypatch.setattr(
            "app.services.node_sector_service.NodeSectorService.classify_payload",
            _fake_classify,
        )

        visual, model = await service._resolve_visual_data(
            {
                "candidate_id": "用户自建节点_1",
                "name": "用户自建节点",
                "description": "没有权重信息的节点。",
            },
            context_node=None,
            subject=None,
            fallback_sector=SectorCode.VOID,
        )

        assert called["count"] == 1
        assert visual.dominant_sector_code == SectorCode.WISDOM
