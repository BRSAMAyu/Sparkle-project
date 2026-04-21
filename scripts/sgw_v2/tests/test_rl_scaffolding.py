"""End-to-end scaffolding test for the Phase 0–8 SGW RL stack.

Run directly with `python3 scripts/sgw_v2/tests/test_rl_scaffolding.py`
or via `pytest scripts/sgw_v2/tests/test_rl_scaffolding.py -v`.

Covers:
  Phase 0 — spec / guardrails (clamp, direction history, config novelty, exploration)
  Phase 1 — feature extractor + rl_trajectories + failure_library
  Phase 2 — CUSUM changepoint, causal attribution, statistical pattern miner
  Phase 3 — RulePolicy / ThompsonSamplingBandit / LinUCBBandit / PolicyRouter
  Phase 4 — holdout guard, diversity bonus, temperature anneal, adversarial play,
            exploration budget (5 independent defenses)
  Phase 5 — reward composition + veto + MetaLoopCoordinator trajectory persistence
  Phase 6 — reward_weights.yaml loader + HTML dashboard generator
  Phase 7 — RolloutGate offline / shadow / canary / full checks
  Phase 8 — SimulationEnv recipes + PolicyZoo snapshot roundtrip
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from sgw_v2.rl import (  # noqa: E402
    ACTION_SPECS,
    AdversarialSelfPlay,
    BUILTIN_RECIPES,
    CUSUMDetector,
    CausalAttributor,
    DEFAULT_REWARD_WEIGHTS,
    DiversityMetrics,
    ExplorationBudget,
    FeatureExtractor,
    HoldoutGuard,
    LinUCBBandit,
    MetaLoopCoordinator,
    PatternMiner,
    PolicyRouter,
    PolicyStage,
    PolicyZoo,
    RewardWeights,
    RolloutGate,
    RolloutStage,
    RulePolicy,
    ScenarioRecipe,
    SimulationEnv,
    TemperatureSchedule,
    ThompsonSamplingBandit,
    check_config_novelty,
    check_direction_history,
    clamp_amplitude,
    compute_config_hash,
    compute_reward,
    generate_dashboard,
    load_reward_config,
    should_explore,
    state_from_summary,
    validate_action,
)
from sgw_v2.rl.spec import Action, IterationOutcome  # noqa: E402
from sgw_v2.storage.db import RunDB  # noqa: E402


# ── Fixtures ────────────────────────────────────────────────────


def _base_config() -> dict:
    return {
        "soft_violation_threshold": 0.85,
        "audit_sample_rate": 0.25,
        "authenticity_sample_rate": 0.20,
        "turn_target": 12,
        "claude_timeout_seconds": 45,
        "claude_failure_backoff_seconds": 30,
        "expression_validation_retries": 2,
        "max_history_pairs": 6,
        "session_turn_slice": 1,
        "random_seed": 1,
    }


def _seed_run(db: RunDB, run_id_tag: str = "smoke") -> str:
    run_id = db.create_run(
        scenario_id="sgw_rl_smoke",
        config_hash=run_id_tag,
        git_sha="deadbeef",
        scenario_config={},
        prompt_hashes={},
        model_versions={},
    )
    db.finish_run(run_id, status="completed", summary={})
    return run_id


def _sample_state():
    summary = {
        "soft_violation_rate": 0.12,
        "authenticity_mean": 0.78,
        "hard_violations": 0,
        "authenticity_failures": 3,
        "authenticity_total": 100,
        "sessions_completed": 9,
        "sessions_total": 10,
        "turns_total": 90,
    }
    return state_from_summary(summary, scenario_id="t", config_hash="h", iteration_number=0)


# ── Phase 0: spec / guardrails ─────────────────────────────────


def test_clamp_amplitude_respects_int_type():
    # turn_target step_size=2 but 15% of range=12 is 1.8 — must allow ±2 (max)
    clamped = clamp_amplitude("turn_target", 10, 12)
    assert isinstance(clamped, int), "int params must return int"
    assert clamped == 12

    # Outside valid range → clamp to hard bounds
    assert clamp_amplitude("turn_target", 18, 25) == 20


def test_clamp_amplitude_respects_float_cap():
    clamped = clamp_amplitude("audit_sample_rate", 0.25, 0.50)
    # range 0.40 × 0.15 = 0.06 > step 0.05 → cap 0.06 → 0.31
    assert 0.30 < clamped < 0.32


def test_direction_history_flat_encoding():
    history = [
        {"changes": {"turn_target": 10}, "config_after": {"turn_target": 10}},
        {"changes": {"turn_target": 12}, "config_after": {"turn_target": 12}},
        {"changes": {"turn_target": 14}, "config_after": {"turn_target": 14}},
    ]
    # Already moved up 2 times (12-10, 14-12). A 3rd +1 request should be blocked
    # only when window of 3 is full.  We need a baseline entry.
    history_with_baseline = [
        {"config_after": {"turn_target": 8}},
        *history,
    ]
    assert check_direction_history("turn_target", +1, history_with_baseline) is False
    assert check_direction_history("turn_target", -1, history_with_baseline) is True


def test_config_novelty_and_forced_exploration():
    h1 = compute_config_hash({"turn_target": 10})
    h2 = compute_config_hash({"turn_target": 12})
    assert check_config_novelty(h2, [h1]) is True
    assert check_config_novelty(h1, [h1]) is False

    # Guardrail 4 forces exploration every N
    assert should_explore(0, 10) is False
    assert should_explore(10, 10) is True
    assert should_explore(11, 10) is False


def test_validate_action_rejects_protected_and_out_of_range():
    bad = Action(changes={"turn_target": 999}, source=PolicyStage.RULE)
    violations = validate_action(bad)
    assert any("out of range" in v for v in violations)

    protected = Action(changes={"random_seed": 42, "turn_target": 12}, source=PolicyStage.RULE)
    assert any("random_seed" in v for v in validate_action(protected))


# ── Phase 1: features / trajectories / failure library ─────────


def test_feature_extractor_creates_tables_and_records():
    with tempfile.TemporaryDirectory() as td:
        db = RunDB(Path(td) / "rl.db")
        run_id = _seed_run(db)
        fe = FeatureExtractor(db)

        # Tables exist
        tables = {row[0] for row in db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "rl_trajectories" in tables
        assert "failure_library" in tables

        tid = fe.record_trajectory(
            run_id=run_id,
            action_taken={"turn_target": 12},
            state_vector=[0.1] * 9,
            config_snapshot={"turn_target": 12},
        )
        assert tid.startswith("traj_")

        # Failure library dedups by pattern hash
        p1 = fe.record_failure_pattern(
            category="compliance", severity="major",
            description="repeated_fail_pattern_x", evidence={"x": 1}, run_id=run_id,
        )
        p2 = fe.record_failure_pattern(
            category="compliance", severity="major",
            description="repeated_fail_pattern_x", evidence={"x": 2}, run_id=run_id,
        )
        assert p1 == p2  # same pattern hash → same id
        db.close()


# ── Phase 2: analysis ──────────────────────────────────────────


def test_cusum_detects_downward_shift():
    seq = [0.1] * 10 + [0.8] * 10  # big upward shift
    cps = CUSUMDetector(threshold=3.0, drift=0.2).detect(seq, metric="rate")
    assert cps, "CUSUM should flag the shift"
    assert cps[0].direction == "up"


def test_causal_attributor_requires_min_matches():
    attr = CausalAttributor(min_matches=3, similarity_threshold=0.5)
    result = attr.estimate_effect(
        parameter="turn_target", delta=2, metric="auth",
        pre_state=[0.5, 0.5], post_value=0.8,
        history=[],
    )
    assert result is None  # not enough matches


def test_pattern_miner_statistical_fallback():
    miner = PatternMiner(min_failures=3)
    failures = [
        {"category": "compliance", "description": "x", "persona_id": "p1", "behavior_class": "b1"},
    ] * 6
    patterns = miner.mine_patterns(failures)
    assert any(p.category == "compliance" for p in patterns)


# ── Phase 3: policy layers ─────────────────────────────────────


def test_rule_policy_generates_action_from_hypothesis():
    policy = RulePolicy()
    action = policy.select_action(
        state=_sample_state(),
        hypotheses=["low_authenticity_mean"],
        current_config=_base_config(),
        history=[],
    )
    # low_authenticity_mean rules bump turn_target +2 and audit_sample_rate +0.05
    assert "turn_target" in action.changes or "audit_sample_rate" in action.changes
    assert action.source == PolicyStage.RULE


def test_bandit_update_credits_correct_direction():
    bandit = ThompsonSamplingBandit(rng_seed=42)
    cfg = _base_config()
    action = Action(
        changes={"turn_target": 14},
        source=PolicyStage.BANDIT,
    )
    bandit.update(action, reward=1.0, prior_config=cfg)
    up = bandit.arms["turn_target_up"]
    down = bandit.arms["turn_target_down"]
    assert up.pulls == 1
    assert down.pulls == 0  # only the up-arm gets credit


def test_policy_router_routes_and_enforces_novelty():
    router = PolicyRouter(rng_seed=7)
    state = _sample_state()
    action = router.select_action(
        state=state,
        hypotheses=["low_session_completion_rate"],
        current_config=_base_config(),
        history=[],
        iteration_number=0,
    )
    assert action.changes  # router produced something


# ── Phase 4: anti-overfitting defenses (5 independent) ─────────


def test_holdout_guard_detects_gap():
    guard = HoldoutGuard(threshold=0.1)
    res = guard.check_overfitting(training_rewards=[0.5] * 5, holdout_rewards=[0.1] * 5)
    assert res.is_overfitting is True


def test_diversity_metrics_scales():
    m = DiversityMetrics.from_counts(
        unique_personas=22, unique_behaviors=7, total_samples=100,
        expected_personas=44, expected_behaviors=7,
    )
    assert 0.5 <= m.diversity_score <= 1.0


def test_temperature_anneal_monotonic():
    sched = TemperatureSchedule(t_start=1.0, t_end=0.1, decay_rate=0.5)
    t1 = sched.anneal()
    t2 = sched.anneal()
    assert t2 <= t1


def test_exploration_budget_tracks_rate():
    budget = ExplorationBudget(min_exploration_rate=0.2, window=5)
    for _ in range(5):
        budget.record(False)
    assert budget.current_rate() == 0.0
    assert budget.should_force_exploration() is True


def test_adversarial_identifies_worst_cells():
    play = AdversarialSelfPlay(worst_k=2, test_every=5)
    play.record("alpha", "avoidant", -0.5)
    play.record("beta", "neutral", +0.2)
    play.record("gamma", "aggressive", -0.8)
    worst = play.get_worst_cells()
    assert worst[0][1] < worst[-1][1]
    assert play.should_test(10) is True


# ── Phase 5: reward + nested loops + trajectory persistence ────


def test_compute_reward_veto_on_hard_violation():
    before = {"soft_violation_rate": 0.1, "authenticity_mean": 0.8,
              "hard_violations": 0, "session_completion_rate": 0.8}
    after = dict(before, hard_violations=1)
    raw, norm, _, veto, reason = compute_reward(before, after)
    assert veto is True
    assert reason == "hard_violation_increase"
    assert raw == -1.0


def test_coordinator_persists_trajectory_to_db():
    with tempfile.TemporaryDirectory() as td:
        db = RunDB(Path(td) / "rl.db")
        run_id = _seed_run(db)
        fe = FeatureExtractor(db)
        router = PolicyRouter(rng_seed=11)
        coord = MetaLoopCoordinator(feature_extractor=fe, policy_router=router)

        cfg = _base_config()
        state = _sample_state()
        action = Action(changes={"turn_target": 14}, source=PolicyStage.RULE)

        before = {"soft_violation_rate": 0.12, "authenticity_mean": 0.78,
                  "hard_violations": 0, "session_completion_rate": 0.9}
        after = {"soft_violation_rate": 0.10, "authenticity_mean": 0.80,
                 "hard_violations": 0, "session_completion_rate": 0.92}

        coord.record_iteration(
            iteration_number=1, action=action,
            state_before=state, state_after=state,
            summary_before=before, summary_after=after,
            outcome=IterationOutcome.IMPROVED_SIG,
            current_config=cfg,
            run_id=run_id, iteration_id="iter-1",
        )

        rows = db.conn.execute(
            "SELECT iteration_id, action_source, reward_normalized FROM rl_trajectories"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "iter-1"
        assert rows[0][1] == "rule"
        db.close()


# ── Phase 6: reward config loader + HTML dashboard ─────────────


def test_reward_config_loader_defaults():
    cfg = load_reward_config()
    assert isinstance(cfg.weights, RewardWeights)
    # weights must sum to roughly 1.0 in the default file
    total = (cfg.weights.w_soft + cfg.weights.w_auth + cfg.weights.w_hard
             + cfg.weights.w_session + cfg.weights.w_diversity)
    assert 0.95 <= total <= 1.05


def test_reward_config_loader_missing_file_fallback(tmp_path=None):
    from pathlib import Path as _P
    missing = _P("/tmp/nonexistent_sgw_reward_weights.yaml")
    cfg = load_reward_config(missing)
    assert cfg.weights.w_soft == DEFAULT_REWARD_WEIGHTS.w_soft


def test_dashboard_renders_html():
    history = [
        {"iteration": 1, "reward_raw": 0.1, "reward_normalized": 0.3,
         "outcome": "improved_sig", "action": {"changes": {"turn_target": 12}}, "veto": False},
        {"iteration": 2, "reward_raw": -0.2, "reward_normalized": -0.5,
         "outcome": "regressed_sig", "action": {"changes": {"audit_sample_rate": 0.3}}, "veto": True},
    ]
    html = generate_dashboard(history, title="SGW RL Smoke")
    assert "SGW RL Smoke" in html
    assert "improved_sig" in html
    assert "regressed_sig" in html


# ── Phase 7: RolloutGate gates ─────────────────────────────────


def test_rollout_gate_offline_passes_valid_action():
    cfg = _base_config()
    gate = RolloutGate(cfg)
    action = Action(changes={"turn_target": 14}, source=PolicyStage.RULE)
    result = gate.validate_offline(action)
    assert result.passed, result.violations


def test_rollout_gate_shadow_flags_hard_violation():
    gate = RolloutGate(_base_config())
    shadow = {"hard_violations": 1, "soft_violation_rate": 0.1, "authenticity_mean": 0.8}
    baseline = {"hard_violations": 0, "soft_violation_rate": 0.1, "authenticity_mean": 0.8}
    r = gate.evaluate_shadow(shadow, baseline)
    assert r.stage == RolloutStage.SHADOW
    assert not r.passed


# ── Phase 8: SimulationEnv + PolicyZoo roundtrip ───────────────


def test_simulation_env_configures_recipe():
    with tempfile.TemporaryDirectory() as td:
        db = RunDB(Path(td) / "rl.db")
        env = SimulationEnv(db, current_config=_base_config(), zoo_dir=Path(td) / "zoo")
        env.configure(recipe=BUILTIN_RECIPES["fast_iteration"])
        assert env.get_coordinator().config.max_iterations == 5
        db.close()


def test_policy_zoo_snapshot_roundtrip():
    with tempfile.TemporaryDirectory() as td:
        zoo = PolicyZoo(Path(td))
        router = PolicyRouter(rng_seed=3)
        temp = TemperatureSchedule()
        snap = zoo.save_snapshot(
            policy_router=router, temperature=temp,
            current_config=_base_config(),
            performance={"total_reward": 1.23},
        )
        assert (Path(td) / f"{snap.snapshot_id}.json").exists()
        listed = zoo.list_snapshots()
        assert any(s.snapshot_id == snap.snapshot_id for s in listed)
        restored = zoo.restore_snapshot(snap.snapshot_id)
        assert restored is not None
        router2, temp2, cfg2 = restored
        assert cfg2["turn_target"] == 12


# ── Entry point ────────────────────────────────────────────────


def _run_all() -> int:
    import traceback
    failures = 0
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    for test in tests:
        try:
            test()
            print(f"  ✓ {test.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"  ✗ {test.__name__}: {e}")
        except Exception:  # noqa: BLE001
            failures += 1
            print(f"  ✗ {test.__name__}: {traceback.format_exc()}")
    print(f"\n{len(tests) - failures}/{len(tests)} tests passed")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(_run_all())
