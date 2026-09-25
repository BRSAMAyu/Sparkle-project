"""D-08 · 数据飞轮纵向协议契约锁（pytest sqlite 内存口径）。

锁的不是数字（数字在 raw/dashboard 产物），是**协议与判据的结构性正确**：
- 10 persona × 双臂（flywheel / no_feedback）× Day0/Day3/Day7 三探针；
- no_feedback 臂反馈面确实缺席（零纠正/零 patch/零 reference outcome/零撤回）；
- adaptation 因果链提取是纯函数且事件→读侧证据→行为差分三段齐备才成立；
- 无效/无效力个性化保留在账（不筛除）；
- 理解五维经真实 D-03 契约计算（缺数据 = unknown，永不默认 0/1）。
产品代码零改动；评估对象全部为真实服务面。
"""

from __future__ import annotations

import pytest

from tests.d08_flywheel.engine import run_persona_arm
from tests.d08_flywheel.metrics import (
    D08_METRICS_VERSION,
    adaptation_chains,
    build_persona_paired,
    extract_invalid_personalization,
    summarize_population,
)
from tests.d08_flywheel.protocol import (
    D08_SPEC_VERSION,
    FLYWHEEL_ARMS,
    PROBE_DAYS,
    build_population,
    memory_seeds_for,
    probe_composition,
)

pytestmark = [pytest.mark.asyncio]


# ---------------------------------------------------------------------------
# 1. 协议形状（纯函数面）
# ---------------------------------------------------------------------------


def test_population_reuses_a08_ten_personas() -> None:
    """人口 = A-08 的 10 persona（复用不重建）；探针组成逐 persona 可解析。"""
    population = build_population()
    assert len(population) == 10
    assert FLYWHEEL_ARMS == ("flywheel", "no_feedback")
    assert PROBE_DAYS == (0, 3, 7)
    seen = set()
    for spec in population:
        comp = probe_composition(spec)
        seen.add(spec.persona_id)
        # 探针摩擦真值/参数来自该 persona A-08 时间线首个 episode（零新建模）。
        from tests.aurora_ablation.persona import Episode

        first_episode = next(e for e in spec.timeline if isinstance(e, Episode))
        assert comp.friction_truth == first_episode.friction_type
        assert comp.days_stalled == first_episode.days_stalled
        assert comp.failure_count == first_episode.failure_count
        assert comp.utterance, spec.persona_id
        # 记忆种子：至少一条稳定 + 一条待失效（喜好改变对抗面）；stale 值以
        # 该 persona 探针词牌的短语入词（M-05 selfcheck 词面门可放行）。
        seeds = memory_seeds_for(spec.persona_id)
        assert len(seeds) >= 2
        assert any(seed.stale for seed in seeds)
        assert any(not seed.stale for seed in seeds)
    assert len(seen) == 10


# ---------------------------------------------------------------------------
# 2. 双臂各跑一个 persona：探针齐全 + no_feedback 反馈面缺席
# ---------------------------------------------------------------------------


async def test_no_feedback_arm_has_zero_feedback_events() -> None:
    records = await run_persona_arm(build_population()[0], arm="no_feedback")
    for r in records:
        if r.get("kind") != "event":
            continue
        assert r["event_type"] not in (
            "journey_correction",
            "patch_proposal",
            "memory_reference_outcome",
            "memory_retract",
        ), f"no_feedback arm leaked feedback event: {r['event_type']}"
    probes = [r for r in records if r.get("kind") == "probe"]
    assert len(probes) == len(PROBE_DAYS)


async def test_flywheel_arm_full_protocol_shape() -> None:
    records = await run_persona_arm(build_population()[0], arm="flywheel")
    probes = [r for r in records if r.get("kind") == "probe"]
    assert [p["sim_day"] for p in probes] == list(PROBE_DAYS)
    # 每探针五面齐全：understanding dims / memory / intervention / outcome / personalization。
    for p in probes:
        assert set(p["faces"].keys()) == {
            "understanding",
            "memory",
            "intervention",
            "outcome",
            "personalization",
        }
        # 理解五维走 D-03 真实契约词表，缺数据 = unknown。
        dims = p["faces"]["understanding"]["dimensions"]
        assert set(dims.keys()) == {
            "coverage",
            "correctness",
            "scope_precision",
            "freshness",
            "utility",
        }
        for entry in dims.values():
            assert entry["status"] in ("ok", "unknown")
            if entry["status"] == "unknown":
                assert entry["value"] is None


# ---------------------------------------------------------------------------
# 3. 因果链与无效个性化（纯函数判据）
# ---------------------------------------------------------------------------


def test_adaptation_chain_requires_event_read_and_differential() -> None:
    """因果链成立 = 事件 + 读侧证据 + 行为差分三段齐备；缺一段即不成立。"""
    event = {
        "event_type": "journey_correction",
        "sim_day": 1,
        "corrected_friction_type": "dependency",
        "correction_id": "c1",
    }
    probe_flywheel = {
        "sim_day": 3,
        "kind": "probe",
        "faces": {
            "intervention": {
                "journey": {
                    "friction_type": "skill",
                    "adjusted_by_correction": True,
                    "applied_correction_ids": ["c1"],
                    "active_corrections": 1,
                }
            }
        },
    }
    probe_control = {
        "sim_day": 3,
        "kind": "probe",
        "faces": {
            "intervention": {
                "journey": {
                    "friction_type": "dependency",
                    "adjusted_by_correction": False,
                    "applied_correction_ids": [],
                    "active_corrections": 0,
                }
            }
        },
    }
    chains = adaptation_chains(
        events=[event],
        flywheel_probes=[probe_flywheel],
        control_probes=[probe_control],
    )
    assert any(
        c["chain_type"] == "journey_correction"
        and c["established"] is True
        and c["behavior_changed"] is True
        for c in chains
    )
    # 无读侧证据（applied ids 为空）→ 链不成立。
    probe_no_read = {
        "sim_day": 3,
        "kind": "probe",
        "faces": {
            "intervention": {
                "journey": {
                    "friction_type": "skill",
                    "adjusted_by_correction": False,
                    "applied_correction_ids": [],
                    "active_corrections": 0,
                }
            }
        },
    }
    chains2 = adaptation_chains(
        events=[event],
        flywheel_probes=[probe_no_read],
        control_probes=[probe_control],
    )
    correction_chain = next(c for c in chains2 if c["chain_type"] == "journey_correction")
    assert correction_chain["established"] is False


def test_invalid_personalization_kept_not_filtered() -> None:
    """applied 但零行为差分的 patch = 无效力个性化；必须出现在台账。"""
    events = [
        {
            "event_type": "patch_proposal",
            "sim_day": 1,
            "patch_id": "p1",
            "state": "active",
            "intervention": "explain",
        }
    ]
    probe_flywheel = {
        "sim_day": 7,
        "kind": "probe",
        "faces": {
            "intervention": {
                "chat": {"selected": "explain", "applied_patch_ids": ["p1"], "patch_moves": []}
            }
        },
    }
    probe_control = {
        "sim_day": 7,
        "kind": "probe",
        "faces": {
            "intervention": {
                "chat": {"selected": "explain", "applied_patch_ids": [], "patch_moves": []}
            }
        },
    }
    invalid = extract_invalid_personalization(
        events=events,
        flywheel_probes=[probe_flywheel],
        control_probes=[probe_control],
    )
    assert any(i["kind"] == "ineffective_patch" for i in invalid)


# ---------------------------------------------------------------------------
# 4. paired result 与 summary（全由 raw 程序化复算）
# ---------------------------------------------------------------------------


def test_persona_paired_day7_vs_day0() -> None:
    records: list[dict] = [
        {
            "kind": "probe",
            "arm": "flywheel",
            "persona": "pX",
            "sim_day": 0,
            "faces": {
                "understanding": {
                    "dimensions": {
                        "coverage": {"status": "unknown", "value": None, "samples": 1},
                        "correctness": {"status": "unknown", "value": None, "samples": 0},
                        "scope_precision": {"status": "unknown", "value": None, "samples": 0},
                        "freshness": {"status": "unknown", "value": None, "samples": 0},
                        "utility": {"status": "unknown", "value": None, "samples": 0},
                    }
                },
                "memory": {"surfaced_keys": ["k1"], "usage_opportunities": 1},
                "intervention": {"chat": {"selected": "no_action"}, "journey": None},
                "outcome": {"associations_total": 0},
                "personalization": {"active_patches": 0, "active_corrections": 0},
            },
        },
        {
            "kind": "probe",
            "arm": "flywheel",
            "persona": "pX",
            "sim_day": 7,
            "faces": {
                "understanding": {
                    "dimensions": {
                        "coverage": {"status": "ok", "value": 0.5, "samples": 3},
                        "correctness": {"status": "ok", "value": 0.8, "samples": 4},
                        "scope_precision": {"status": "ok", "value": 0.0, "samples": 2},
                        "freshness": {"status": "ok", "value": 0.2, "samples": 1},
                        "utility": {"status": "ok", "value": 0.5, "samples": 2},
                    }
                },
                "memory": {"surfaced_keys": [], "usage_opportunities": 3},
                "intervention": {"chat": {"selected": "explain"}, "journey": None},
                "outcome": {"associations_total": 2},
                "personalization": {"active_patches": 1, "active_corrections": 1},
            },
        },
    ]
    paired = build_persona_paired(persona_id="pX", flywheel_records=records)
    assert paired["persona_id"] == "pX"
    cov = paired["faces"]["understanding"]["coverage"]
    assert cov["day0"]["status"] == "unknown"
    assert cov["day7"]["status"] == "ok"
    assert cov["delta_day7_vs_day0"] == "unknown->ok(0.5)"
    assert paired["faces"]["outcome"]["delta_day7_vs_day0"] == 2


def test_summary_population_shape_and_versions() -> None:
    payload = summarize_population(
        {
            "flywheel": [
                {
                    "kind": "probe",
                    "arm": "flywheel",
                    "persona": f"p{i:02d}",
                    "sim_day": d,
                    "faces": {
                        "understanding": {"dimensions": {}},
                        "memory": {},
                        "intervention": {},
                        "outcome": {"associations_total": 1},
                        "personalization": {},
                    },
                }
                for i in range(10)
                for d in PROBE_DAYS
            ],
            "no_feedback": [
                {
                    "kind": "probe",
                    "arm": "no_feedback",
                    "persona": f"p{i:02d}",
                    "sim_day": d,
                    "faces": {
                        "understanding": {"dimensions": {}},
                        "memory": {},
                        "intervention": {},
                        "outcome": {"associations_total": 1},
                        "personalization": {},
                    },
                }
                for i in range(10)
                for d in PROBE_DAYS
            ],
        }
    )
    assert payload["spec_version"] == D08_SPEC_VERSION
    assert payload["metrics_version"] == D08_METRICS_VERSION
    assert len(payload["per_persona"]) == 10
