# SPARKLE Aurora Successor Codex Alignment (2026-04-20)

> **Status**: frozen successor handoff after Stage 13 final-accept
> **Audience**: the next Codex instance that will replace the current executor in this workflow
> **Purpose**: let a new Codex take over without rediscovering context, reopening settled work, or breaking the existing Claude / GLM / MIMO operating rhythm

## 1. What You Are Replacing

You are replacing the prior Codex as the **execution owner** of the Sparkle Aurora staged program.

Your job is **not** to re-argue product direction from scratch. Your job is to:

1. read the frozen truth sources
2. continue the staged execution from the latest accepted baseline
3. preserve the governance discipline that made Stages 5-13 work
4. make concrete engineering decisions locally unless a frozen hard boundary says you must not
5. leave behind clean handoff artifacts, clean commit chains, and auditable verification evidence

If you do this well, the user should feel that the executor changed invisibly.

## 2. The Real Workflow You Must Fit Into

This project is not using a generic "assistant helps with code" pattern. It is using a **multi-role governance workflow**:

| Role | Real function | How you should treat it |
| --- | --- | --- |
| **User** | principal and final operator | their accepted rulings freeze reality; do not quietly override them |
| **Claude** | chief architect / final-accept arbiter | treat Claude rulings as architecture and governance authority once issued |
| **GLM-observer / GLM1** | pre-review, code-fact challenge, governance pressure | use them as pressure tests; absorb valid corrections without ego |
| **MIMO** | strategic anchor / vision continuity | use MIMO outputs to guard against drift between execution and long-term vision |
| **Codex (you)** | executor / integrator / verifier | you own implementation, replay, artifact quality, and keeping momentum |

Default behavior in this workflow:

1. **Do not reopen accepted stages.**
2. **Do not wait for menus.** Make the best bounded engineering decision you can, then let Claude/GLM overturn it if needed.
3. **Do not hide uncertainty.** If something is unproven, turn it into an artifact, a test, or a known limit.
4. **Do not claim closure without a real consumer path, test proof, and handoff evidence.**

## 3. Mandatory Read Order Before You Touch Anything

Read these in order when you take over:

1. [SPARKLE_VISION_ANCHOR_LIST_2026-04-19.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_VISION_ANCHOR_LIST_2026-04-19.md)
2. [SPARKLE_USER_MODEL_LAYERED_ARCHITECTURE_2026-04-19.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_USER_MODEL_LAYERED_ARCHITECTURE_2026-04-19.md)
3. [SPARKLE_AURORA_STAGE13_HANDOFF_2026-04-20.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE13_HANDOFF_2026-04-20.md)
4. [SPARKLE_AURORA_STAGE13_DISPATCH_PLAN_2026-04-20.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE13_DISPATCH_PLAN_2026-04-20.md)
5. [SPARKLE_AURORA_STAGE13_SIGNAL_QUALITY_AUDIT_METHOD_2026-04-20.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE13_SIGNAL_QUALITY_AUDIT_METHOD_2026-04-20.md)
6. [SPARKLE_AURORA_STAGE13_PERSISTENT_BAYESIAN_SQAM_BASELINE_2026-04-20.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE13_PERSISTENT_BAYESIAN_SQAM_BASELINE_2026-04-20.md)
7. [SPARKLE_AURORA_STAGE13_PERSISTENT_BAYESIAN_SQAM_RERUN_2026-04-20.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE13_PERSISTENT_BAYESIAN_SQAM_RERUN_2026-04-20.md)

If you skip this and "infer from code," you will almost certainly violate a frozen boundary or accidentally reopen settled debate.

## 4. Frozen Reality As Of Handoff

These facts are already accepted. Do not debate them again unless the user explicitly asks for re-litigation.

### 4.1 Program state

- Stages 5 through 13 are accepted and frozen.
- Stage 13 is the current execution baseline.
- Stage 14 has **not** been executed yet.

### 4.2 Governance state

- Rules `G` through `W` are live.
- `Rule W` is now the gate for any continuous-learning component entering a user-visible path.
- `Rule U` and `Rule V` are already real enforcement mechanisms, not aspirational wording.

### 4.3 Continuous-learning state

- `PersistentBayesianLearner` is the **only** continuous-learning component that has passed SQAM and is now `wire-ready`.
- `PromptBandit`, `distiller`, `multi_dimensional_learner`, and `strategy_store` do **not** inherit that pass.
- Stage 14 may only propose a **bounded `WS-CL1` candidate for `PersistentBayesianLearner`**.

### 4.4 User-surface state

- In-chat profile query and correction are already landed.
- Clickable evidence is already landed.
- `practice_outcome` evidence is already landed through the memory lane and mobile route path.
- Graph diagnostic has a chat-native surface, but deeper Galaxy/productization is still deferred.

## 5. The One Correct Starting Point For Stage 14

Stage 14 starts from **Path A**, and only from Path A.

That means:

1. You may design a bounded `WS-CL1` candidate for `PersistentBayesianLearner`.
2. You may not treat Stage 13 as blanket permission to wire all learning signals into the front door.
3. You must explicitly address the Stage 13 final-accept concern:
   - the SQAM pass came from a small frozen fixture (`3` states / `22` observations)
   - Stage 14 must not let fixture scale become a hidden loophole

If you need one sentence to keep yourself honest, use this:

> **Stage 14 is not "continuous learning is ready now"; it is "can we bound and prove one safe front-door read path for the only component that actually passed Rule W?"**

## 6. How To Behave Inside This Workflow

### 6.1 Your decision style

- Make bounded architecture decisions locally.
- Do not dump Q1-Q7 menus back on the user by default.
- If a decision has already been frozen by accepted docs, treat it as law.
- If a decision is truly open, choose the narrowest path that preserves reversibility.

### 6.2 Your execution style

For every stage, the normal cadence is:

1. dispatch plan doc
2. pre-code artifacts for each WS
3. code implementation
4. verification replay
5. handoff doc
6. anchor sync

Do not skip the artifact step. This workflow uses docs as boundary locks, not as decoration.

### 6.3 Your commit style

- Follow `Rule G`: one WS, one commit.
- Dispatch / gate / handoff / anchor sync can be separate docs commits.
- Do not mix multiple WS into one engineering commit because "they touched adjacent code anyway."

### 6.4 Your verification style

Every closure claim must be backed by:

1. the frozen baseline replay
2. WS-local targeted sweeps
3. any standing governance guard (`Rule K`, `Rule V`, etc.)
4. representative output samples when the WS changes user-visible payloads

## 7. Hard Things You Must Not Break

These are common failure modes in this program. Avoid them.

### 7.1 Do not silently widen write authority

- `Aurora` write authority is heavily constrained.
- `memory` lane, `User Correction` lane, `evaluation_records_only`, and `L2 inference cache` distinctions matter.
- If you cannot name the lane, you should not be writing to it.

### 7.2 Do not claim "closed loop" without a real consumer

This workflow has repeatedly hardened against backend-only fake closure.
If a user can supposedly click, inspect, or consume a thing, there must be a real surface and test proof.

### 7.3 Do not inherit passes across components

`PersistentBayesianLearner` passing SQAM does **not** lift the rest of the stack.
Each component earns wire eligibility separately.

### 7.4 Do not downgrade known limits into silence

If you choose not to build a route, consumer, or secondary refinement, record it in `Known Limits`.
Never let missing capability disappear from the narrative.

## 8. Commands You Will Reuse Often

### Stage frozen baseline

```bash
cd backend && ./.venv/bin/python -m pytest \
  tests/aurora \
  tests/api/test_profile_transparency_api.py \
  tests/profile/eval/test_profile_eval_skeleton.py \
  tests/profile/test_intervention_verification_loop.py \
  tests/unit/test_situation_brief.py \
  tests/unit/test_phase2_intervention_pipeline.py \
  -q
```

Expected baseline after Stage 13:

- `144 passed`

### Rule V suite

```bash
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_persistent_bayesian_learner_contract.py \
  tests/unit/test_multi_dimensional_learner_contract.py \
  tests/unit/test_distilled_strategy_store_contract.py \
  -q
```

Expected:

- `8 passed`

### Rule K guard

```bash
./backend/.venv/bin/python scripts/check_rule_k_write_paths.py
```

Expected:

- `35 files scanned / 0 violation`

### Stage 13 local sweeps worth preserving

```bash
cd backend && ./.venv/bin/python -m pytest \
  tests/unit/test_tool_preference_router.py \
  tests/unit/test_evidence_resolve.py \
  tests/tools/test_growth_tools.py \
  -q
```

```bash
cd mobile && flutter test \
  test/widget/evidence_card_navigation_test.dart \
  test/features/memory/presentation/widgets/evidence_cards_test.dart
```

## 9. Current Repository Reality

At handoff time:

- branch: `Aurora-&-adaptive-harness-engineering`
- last accepted stage: `Stage 13`
- latest accepted closeout commit: `743523e3`
- unrelated untracked directory exists:
  - `.claude/worktrees/youthful-sutherland-0b2ce7/`

Also note:

- the anchor list header should read `v11`
- if the working tree contains only that header sync plus the unrelated `.claude` directory, that is expected and should be normalized before deeper Stage 14 work

## 10. What "Perfect Replacement" Looks Like

You are replacing the previous Codex well if:

1. the user does not have to restate Stage 5-13 history
2. Claude can still do chief-architect / final-accept review against crisp artifacts
3. GLM can still grep-test your claims and find code-level evidence rather than vague prose
4. MIMO can still map your execution back onto the long-term anchor without discovering drift
5. every new stage leaves a cleaner baseline than it inherited

The practical formula is:

> **Frozen truth first, bounded design second, implementation third, verification fourth, narrative honesty always.**

## 11. Suggested First Move For The Successor

If the user says nothing except "continue," your first move should be:

1. replay the Stage 13 frozen context from the docs listed in §3
2. confirm the repository is on the accepted Stage 13 baseline
3. begin Stage 14 design from **Path A only**
4. make fixture-scale robustness the central design problem of bounded `WS-CL1`

Do **not** start by expanding evidence types, graph depth, or dual interaction modes.

## 12. Final Reminder

The biggest thing to preserve is not any single file. It is the **discipline** that emerged across Stages 8-13:

- explicit boundaries before code
- single-WS commit chains
- tests named after the actual failure they guard
- handoffs that tell the truth even when the answer is "still not ready"

That honesty is why the workflow works.
