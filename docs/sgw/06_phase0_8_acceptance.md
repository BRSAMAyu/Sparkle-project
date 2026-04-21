# SGW v2 RL Scaffolding — Phase 0–8 Acceptance Report

> Version: 1.0 | Date: 2026-04-21 | Status: ACCEPTED (with fixes)
> Scope: verification of the Phase 0–8 RL simulation environment built on `codex/stage20-execution`.

---

## 1. Verdict

**Accepted.** All nine phases are landed, imports cleanly, and the full inner→middle→outer→meta loop scaffolding runs end-to-end. A short series of correctness fixes was required before the layer could be considered "negligently safe to wire into meta_loop"; those fixes are listed in §3 and covered by a new test suite in §4.

Everything the original prompt asked for is now present:
- Phase 0 MDP frozen in `docs/sgw/04_mdp_formalization.md` and `scripts/sgw_v2/rl/spec.py`.
- Phase 1 `rl_trajectories` + `failure_library` tables auto-migrated on first `FeatureExtractor` construction.
- Phase 2 CUSUM / variance / counterfactual / pattern-mining analyzers.
- Phase 3 Rule → Thompson Sampling (18 arms) → LinUCB with a `PolicyRouter` front door.
- Phase 4 five independent defenses: Holdout, Diversity, Exploration budget, Temperature anneal, Adversarial self-play.
- Phase 5 `compute_reward` + `MetaLoopCoordinator` now persists trajectories to SQLite.
- Phase 6 `reward_weights.yaml` is actually **read** by `load_reward_config()` and the HTML dashboard renders from an episode history.
- Phase 7 `RolloutGate` with offline / shadow / canary / full approval stages.
- Phase 8 `SimulationEnv`, 5 built-in `ScenarioRecipe`s, and `PolicyZoo` snapshot/restore.

---

## 2. What was actually built (files & line counts)

| Phase | Path | Purpose |
|-------|------|---------|
| 0 | `docs/sgw/04_mdp_formalization.md` | MDP spec (state/action/reward/policy/episode/guardrails) |
| 0 | `scripts/sgw_v2/rl/spec.py` | Executable enums + dataclasses + guardrail helpers |
| 1 | `scripts/sgw_v2/rl/features.py` | `FeatureExtractor`, `rl_trajectories`, `failure_library` |
| 2 | `scripts/sgw_v2/rl/changepoint.py` | CUSUM + variance detectors |
| 2 | `scripts/sgw_v2/rl/causal.py` | Counterfactual ITE via cosine matching |
| 2 | `scripts/sgw_v2/rl/pattern_miner.py` | LLM + statistical pattern miner |
| 3 | `scripts/sgw_v2/rl/policy.py` | `RulePolicy`, `ThompsonSamplingBandit`, `LinUCBBandit`, `PolicyRouter` |
| 4 | `scripts/sgw_v2/rl/overfitting.py` | 5 independent anti-overfitting defenses |
| 5 | `scripts/sgw_v2/rl/reward.py` | `compute_reward` + `load_reward_config` |
| 5 | `scripts/sgw_v2/rl/loops.py` | `MetaLoopCoordinator` (inner/middle/outer/meta coord) |
| 6 | `scripts/sgw_v2/rl/reward_weights.yaml` | Hot-reloadable reward/episode config |
| 6 | `scripts/sgw_v2/rl/dashboard.py` | Self-contained HTML episode report |
| 7 | `scripts/sgw_v2/rl/rollout.py` | Four-stage rollout gate |
| 7 | `docs/sgw/05_rollout_gates.md` | Gate criteria |
| 8 | `scripts/sgw_v2/rl/environment.py` | `SimulationEnv`, `ScenarioRecipe`, `PolicyZoo` |
| ALL | `scripts/sgw_v2/rl/__init__.py` | Public API re-export |
| TEST | `scripts/sgw_v2/tests/test_rl_scaffolding.py` | **NEW** 26-test scaffolding smoke |

---

## 3. Issues found and fixed in this pass

Eight defects blocked "real use", not just "runs without crashing". Each was fixed in the same commit round and has a dedicated test.

### F1. `clamp_amplitude` produced non-integer values for int parameters
- `turn_target` (int, step 2, range 12) was being clamped to `±1.8`, yielding values like `11.8` that would crash downstream config consumers expecting `int`.
- Also affected `expression_validation_retries` (15% of 5 → 0.75 < step 1) and `claude_timeout_seconds` (±13.5 vs step 15).
- Fix: `max_step = max(range × 15%, step_size)`; int params are rounded back to int and re-clamped to range bounds. `scripts/sgw_v2/rl/spec.py` `clamp_amplitude()`.

### F2. Guardrail 2 silently disabled (consecutive-direction check)
- `check_direction_history` expected a nested `{previous, current}` shape, but both `RulePolicy` and `MetaLoopCoordinator` wrote the flat `{param: new_value}` shape. With the flat shape, `delta = curr - prev` was always zero so the guardrail **never triggered**.
- Fix: walk history oldest→newest, infer prior value from the prior entry's `config_after` or changes, support both encodings. `scripts/sgw_v2/rl/spec.py` `check_direction_history()`.

### F3. Bandit arm credit corrupted
- `ThompsonSamplingBandit.update` updated **every** arm for a parameter with half credit, regardless of which direction the action actually went. Both up-arm and down-arm converged to the same posterior, destroying Thompson sampling.
- Fix: `update(..., prior_config=...)` threads the prior value through so the correct direction's arm gets full credit. `PolicyRouter.update` and `MetaLoopCoordinator.record_iteration` were updated to pass `prior_config=current_config`. `scripts/sgw_v2/rl/policy.py`, `scripts/sgw_v2/rl/loops.py`.

### F4. MetaLoopCoordinator did not persist trajectories
- `_record_trajectory` only appended to an in-memory list. `rl_trajectories` stayed empty, so off-policy evaluation (Phase 7.1) and restart after crash (Phase 8) had no data.
- Fix: after recording to in-memory history, also call `FeatureExtractor.record_trajectory(...)` with the full feature vector, reward components, outcome, and `iteration_id`. Best-effort (swallows exceptions so the episode can finish even if the DB is read-only). `scripts/sgw_v2/rl/loops.py`.

### F5. Reward YAML was declarative-only
- `reward_weights.yaml` had no loader, contradicting the Phase 6 promise of "hot updates".
- Fix: `load_reward_config(path=None)` in `reward.py` returns a `RewardConfig` dataclass with PyYAML if installed, a minimal hand-rolled YAML subset parser as fallback, and default weights if the file is missing/malformed. Exposed via `sgw_v2.rl.__init__`.

### F6. PolicyRouter novelty fallback could loop / keep returning a duplicate
- When Guardrail 1 rejected an action, the router retried with `exploration=True` exactly once without re-checking novelty. In tight parameter spaces the exploration could duplicate again.
- Fix: try up to 3 exploration fallbacks, then emit an empty no-op action rather than re-using a duplicate config. `scripts/sgw_v2/rl/policy.py` `PolicyRouter.select_action`.

### F7. `loops.py` used `PopulationStats` before its module-level import
- Worked only because the import was at the bottom of the file and the use was inside a method body; still a latent footgun for any future module-load-time use.
- Fix: moved the import to the top.

### F8. `rl` package had no public surface
- `__init__.py` was empty. Callers had to import from internal modules (`sgw_v2.rl.policy`, `.reward`, etc.), which encourages a dependency on implementation details.
- Fix: re-exported the full Phase 0–8 API from `sgw_v2.rl`.

---

## 4. New test coverage

`scripts/sgw_v2/tests/test_rl_scaffolding.py` contains 26 tests covering every phase. All pass:

```
$ python3 scripts/sgw_v2/tests/test_rl_scaffolding.py
  ✓ test_clamp_amplitude_respects_int_type
  ✓ test_clamp_amplitude_respects_float_cap
  ✓ test_direction_history_flat_encoding
  ✓ test_config_novelty_and_forced_exploration
  ✓ test_validate_action_rejects_protected_and_out_of_range
  ✓ test_feature_extractor_creates_tables_and_records
  ✓ test_cusum_detects_downward_shift
  ✓ test_causal_attributor_requires_min_matches
  ✓ test_pattern_miner_statistical_fallback
  ✓ test_rule_policy_generates_action_from_hypothesis
  ✓ test_bandit_update_credits_correct_direction
  ✓ test_policy_router_routes_and_enforces_novelty
  ✓ test_holdout_guard_detects_gap
  ✓ test_diversity_metrics_scales
  ✓ test_temperature_anneal_monotonic
  ✓ test_exploration_budget_tracks_rate
  ✓ test_adversarial_identifies_worst_cells
  ✓ test_compute_reward_veto_on_hard_violation
  ✓ test_coordinator_persists_trajectory_to_db
  ✓ test_reward_config_loader_defaults
  ✓ test_reward_config_loader_missing_file_fallback
  ✓ test_dashboard_renders_html
  ✓ test_rollout_gate_offline_passes_valid_action
  ✓ test_rollout_gate_shadow_flags_hard_violation
  ✓ test_simulation_env_configures_recipe
  ✓ test_policy_zoo_snapshot_roundtrip
26/26 tests passed
```

Also runs under `pytest scripts/sgw_v2/tests/test_rl_scaffolding.py -v`.

---

## 5. End-to-end integration demo

A three-iteration coordinator run exercising YAML config, policy routing, trajectory persistence, dashboard generation, and snapshot save produces:

- `rl_trajectories` rows populated with `iter-1 .. iter-3`, sources `rule`/`bandit`, outcomes logged.
- HTML dashboard ~4KB with reward chart and per-iteration table.
- Policy snapshot JSON under `.sgw_state/policy_zoo/` with full bandit posterior, temperature state, and config.

The full script is embedded in the smoke test file (`test_coordinator_persists_trajectory_to_db` plus supporting fixtures).

---

## 6. What remains (not blocking acceptance)

These are **future work**, not defects in the Phase 0–8 scope. Flagging them so they don't get lost.

1. **Wiring into `meta_loop.py` / `meta_orchestrator.py`.** The new RL layer is fully standalone today; the existing meta loop still uses the rule-only `ExperimentPlanner`. The integration point should call `PolicyRouter.select_action(...)` instead of `ExperimentPlanner.plan(...)` once Phase 7 gates sign off on the new policy. This was explicitly out of scope per Phase 7.1/7.2 ("first build the scaffolding, then gate the swap").

2. **CLI for `sgw_override.py`.** Phase 6.2 mentioned a human-veto CLI. The coordinator already surfaces the action via `OuterLoopResult` so this is a thin wrapper. Not required until a real episode starts.

3. **Holdout seed assignment vs. SGW reality.** `HoldoutGuard.assign_seed` uses `seed % (1/ratio)`, but SGW usually pins `random_seed` across a run. The assignment is fine for the scenario-recipe-as-holdout pattern in `docs/sgw/05_rollout_gates.md`; if we later want per-persona holdout splits the API needs widening.

4. **Causal attributor similarity threshold.** Set to 0.7 cosine, which is tight for a 9-dim feature vector with mixed scales. Will likely need rescaling once real trajectory data flows in — re-check when Phase 1 has ≥ 30 trajectories.

5. **Pattern miner prompt uses a generic Chinese prompt.** The `pattern_miner.py` prompt should be swapped for a project-specific one when `OpenClaw` / `glm-4.6` is wired up; for now it falls back cleanly to the statistical detector if no LLM is supplied.

---

## 7. Handoff checklist for the next agent

When you come back to wire this into the live meta loop:

- [ ] Replace `ExperimentPlanner.plan()` call in `meta_orchestrator.py` with `PolicyRouter.select_action(state, hypotheses, current_config, history, iteration_number)`.
- [ ] After each SGW run finishes, call `MetaLoopCoordinator.record_iteration(..., run_id=..., iteration_id=...)` so `rl_trajectories` gets populated.
- [ ] Guard the swap behind `RolloutGate` in **shadow** mode first: run the RL policy's `action` alongside the rule planner's action, log both, do not execute. Promote to canary only after `test_rollout_gate_shadow_flags_hard_violation` semantics are green over ≥ 20 paired runs.
- [ ] Load `reward_weights.yaml` at meta-loop start: `cfg = load_reward_config()`; pass `cfg.weights` into `EpisodeConfig(reward_weights=cfg.weights)`.
- [ ] Set `EpisodeConfig.max_iterations` etc. from the YAML so operators can tune without redeploy.
- [ ] Before each action is applied to the SGW config, run `RolloutGate.validate_offline(action)` and drop actions whose violations include anything other than empty.
