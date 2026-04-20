# SPARKLE Aurora Stage 12 Dispatch Plan (2026-04-20)

> **Status**: Stage 12 dispatch baseline v0 after Stage 11 final-accept
> **Authority**: `SPARKLE_AURORA_STAGE11_HANDOFF_2026-04-20.md` is the only Stage 11 truth source; this plan starts from that frozen baseline and must not reopen completed Stage 5 / Stage 6 / Stage 7 / Stage 8 / Stage 9 / Stage 10 / Stage 11 work.
> **Depends on**:
> - `SPARKLE_VISION_ANCHOR_LIST_2026-04-19.md`
> - `SPARKLE_USER_MODEL_LAYERED_ARCHITECTURE_2026-04-19.md`
> - `SPARKLE_AURORA_STAGE11_HANDOFF_2026-04-20.md`
> - `SPARKLE_AURORA_STAGE11_CL0_AUDIT_2026-04-20.md`
> - `SPARKLE_AURORA_STAGE11_CL0_AUDIT_METHOD_2026-04-20.md`
> - `SPARKLE_AURORA_STAGE11_MOBILE_TRIAGE_2026-04-20.md`
> **Scope**: Stage 12 execution design. Repairs the continuous-learning substrate defects exposed by `WS-CL0` so Stage 13 can re-audit the learning layer honestly.

## 0. Stage 12 Positioning

Stage 9 through Stage 11 built Sparkle's user front door: the profile is queryable, correctable, diagnosable, and evidence-linked. Stage 11 `CL0` then proved the back side of that promise is still too weak to trust: the learning substrate is fragmented, partially dormant, and not yet eligible for user-facing claims.

### One-sentence definition

**Stage 12 is the stage where Sparkle repairs the learning substrate so future user-facing "I learned from you" claims can be re-audited on real engineering evidence instead of optimism.**

### What Stage 12 must treat as already settled

1. Stage 11 frozen baseline remains `144 passed`
2. Stage 11 backend sweep remains `14 passed`
3. Stage 11 mobile sweep remains `51 tests passed`
4. Rule K guard remains merge-blocking and must stay `35 files / 0 violation`
5. `WS-CL0` concluded that no current continuous-learning component is allowed onto the user front door
6. `WS-CL1` is explicitly blocked until a later re-audit proves otherwise

### Stage 12 starting gaps

1. `PersistentBayesianLearner` uses mismatched Redis key paths across its live code and persistence helper
2. `multi_dimensional_learner` exposes no `save_state()` API even though a Celery path attempts to call one
3. `strategy_store` is still an in-memory sidecar, which means restart wipes the current strategy layer
4. mobile old debt has been triaged but not actually closed; Stage 11 refused to defer it invisibly, and Stage 12 must now finish that hygiene work

## 1. Governance Layering

### Rule Families

| Alias | Rules | Meaning |
| --- | --- | --- |
| `[Write-K Family]` | `K / N / P / S / T` | write-lane isolation and merge-blocking safeguards |
| `[Eval Family]` | `L / R` | consumer / runner closure and evaluation read-only discipline |
| `[Close Family]` | `G / I / J` | single-WS commit chain, handoff integrity, user-value closure |
| `[Boundary Family]` | `H / M / O` | allowlists, no third compiler, no silent bounded-steering expansion |
| `[Legibility]` | `Q` | evidence legibility and no fact masquerading |
| `[Verification]` | `U / V` | operability proof and audit-regression proof |

Stage 12 does not merge any rule text. It introduces only one new rule and uses aliases purely to reduce reading cost.

### Rule V · Audit-Driven Fixes Must Carry Regression Proof

Any defect that was discovered and formally recorded by a **formal audit artifact** must ship with a regression test that directly reproduces the audited symptom and proves the repaired path stays fixed.

Hard interpretation:

1. the regression test must encode the original audited symptom, not just a nearby happy path
2. the repaired assertion must be permanent and stay in the suite as a future guardrail
3. if the WS claims an audit bug is fixed but no direct regression proof exists, final-accept is blocked

## 2. Stage 12 Scope

| ID | Goal | CL0 / Stage 11 defect source | Difficulty |
| --- | --- | --- | --- |
| `Gate S12-0` | frozen baseline replay + per-WS fix-design artifacts | entry gate | low |
| `WS-CL2a` | align `PersistentBayesianLearner` Redis key usage, TTL strategy, and compatibility path | CL0 Redis key mismatch | low |
| `WS-CL2b` | repair `multi_dimensional_learner.save_state()` and the Celery invocation path | CL0 missing API / broken Celery seam | medium |
| `WS-CL2c` | replace `InMemoryDistilledStrategyStore` with a DB-backed store plus migration | CL0 restart-loss / in-memory only | high |
| `WS-MOB1` | close the 9 mobile old-debt failures with explicit `fix / isolate / delete` decisions | Stage 11 mobile triage | medium |

### Explicitly deferred beyond Stage 12

1. `WS-CL1` user-facing continuous-learning wiring
2. `WS-EVD3` evidence type expansion
3. deeper graph diagnostic workspace
4. dual interaction mode formalization
5. any attempt to flip `SPARKLE_WS7_DISTILLER_ENABLED`

## 3. Wave Order

`Gate S12-0 -> WS-CL2a -> (WS-CL2b || WS-MOB1) -> WS-CL2c -> Gate S12-FINAL`

Hard interpretation:

1. `Gate S12-0` must land before any Stage 12 code commit
2. `WS-CL2a` goes first because it is the lowest-risk, highest-ROI substrate fix
3. `WS-CL2b` and `WS-MOB1` may run in parallel once their artifacts are frozen
4. `WS-CL2c` lands last because it carries the highest migration risk
5. `Gate S12-FINAL` must rerun the Stage 11 continuous-learning audit using **the exact same method document**: `SPARKLE_AURORA_STAGE11_CL0_AUDIT_METHOD_2026-04-20.md`
6. Stage 12 may not silently rewrite the audit method just to make the final verdict easier to pass

## 4. Gate S12-0 Requirements

Stage 12 may not enter Wave 1 until the following artifacts are committed:

1. frozen baseline replay report showing:
   - Stage 11 frozen baseline `144 passed`
   - Stage 11 backend sweep `14 passed`
   - Stage 11 mobile sweep `51 tests passed`
   - Rule K guard `35 / 0`
2. `WS-CL2a` fix-design artifact
3. `WS-CL2b` fix-design artifact
4. `WS-CL2c` fix-design artifact
5. `WS-MOB1` decision artifact

## 5. Workstream Artifacts That Must Land Before Code

### 5.1 `WS-CL2a`

Artifact must lock:

1. current key mismatch:
   - persistence helper writes `bayesian_learner:{user_id}`
   - learner live path reads / writes `learner:{user_id}`
2. target key
3. compatibility approach:
   - prefer write-path alignment plus compatibility read / optional dual-write
   - old `bayesian_learner:` keys may age out naturally under TTL; no heavyweight migration script is required unless verification proves otherwise
4. TTL strategy
5. Rule V regression assertions

### 5.2 `WS-CL2b`

Artifact must lock:

1. `save_state()` payload schema
2. relationship between `save_state()` and existing `_save()`
3. Celery invocation repair plan
4. Rule V regression assertions proving the original missing-API symptom is gone

### 5.3 `WS-CL2c`

Artifact must lock:

1. DB schema and Alembic migration plan
2. storage-layer classification:
   - `strategy_store` remains **L2 inference cache**
   - it is **not** a compiler, not a new inference engine, and not a new Aurora write surface
   - Aurora remains read-only to this store
3. replacement plan for `InMemoryDistilledStrategyStore`
4. data migration note:
   - there is no durable in-memory data to migrate; restart-loss is the problem, not historical conversion
5. Rule V regression assertions

### 5.4 `WS-MOB1`

Artifact must lock:

1. each of the 9 failures from Stage 11 triage
2. the exact decision per failure:
   - `fix`
   - `isolate`
   - `delete`
3. why that decision was chosen
4. any new verification to keep the decision honest

## 6. Non-Negotiable Constraints

1. Stage 12 inherits Rule G through Rule V
2. `WS-CL2a`, `WS-CL2b`, `WS-CL2c`, and `WS-MOB1` must all satisfy Rule V with direct audit-symptom regression tests
3. `WS-CL2c` may create a DB-backed store, but it may not become a third compiler or a new inference entrypoint
4. `WS-CL2c` writes are confined to the store's own **L2 inference-cache lane**
5. no Stage 12 change may touch L0 raw evidence, L1 profile fact storage, or L3 Aurora write authority
6. Stage 12 may not enable `SPARKLE_WS7_DISTILLER_ENABLED`
7. `WS-MOB1` may not use "defer to Stage 13+" as an outcome; every listed failure must end as `fix`, `isolate`, or `delete`

## 7. Workstream Cards

### 7.1 `WS-CL2a` — PersistentBayesianLearner Key Alignment

**Goal**

Repair the substrate's most concrete persistence defect so the live learner and its helper path speak the same storage language.

**In-scope**

- align live read / write key usage
- confirm TTL strategy
- decide whether compatibility read or temporary dual-write is needed
- permanent Rule V regression coverage for the original mismatch

**Out-of-scope**

- redesigning the learner itself
- changing user-facing routing semantics
- enabling any new front-door learning signal

**Accept requires**

1. fix-design artifact lands before code
2. direct regression test reproduces the original key mismatch symptom
3. repaired path proves a helper-written state is now visible to the live learner
4. Rule K remains untouched

### 7.2 `WS-CL2b` — multi_dimensional_learner Save Path Repair

**Goal**

Turn the dormant Celery seam into a real callable persistence path instead of a guaranteed broken handoff.

**In-scope**

- add or align `save_state()` support
- repair the Celery task invocation path
- preserve current learner semantics unless the artifact explicitly freezes a narrow compatibility change
- direct Rule V regression coverage for the missing-API symptom

**Out-of-scope**

- surfacing this learner to users
- redesigning the multi-dimensional scoring model
- widening write scope outside the learner's own lane

**Accept requires**

1. fix-design artifact lands before code
2. regression test proves the old call path would have failed and now succeeds
3. Celery seam no longer depends on a missing method
4. no new write lane appears

### 7.3 `WS-CL2c` — DB-Backed strategy_store

**Goal**

Replace restart-loss-prone in-memory strategy storage with a durable L2 cache so future audits can judge a real substrate instead of a volatile stub.

**In-scope**

- new DB-backed repository plus Alembic migration
- repository interface that can replace or sit behind the in-memory implementation
- tests for persistence and restart-safe retrieval
- Rule V regression proof for the restart-loss symptom

**Out-of-scope**

- user-facing continuous-learning wiring
- turning the store into a compiler or autonomous inference path
- enabling distiller by default

**Accept requires**

1. fix-design artifact lands before code
2. artifact explicitly labels the store as `L2 inference cache, Aurora read-only`
3. persistence survives repository recreation / process restart in tests
4. migration and repository tests prove the in-memory-only failure mode is closed

### 7.4 `WS-MOB1` — Mobile Old-Debt Closure

**Goal**

Finish the debt classification work that Stage 11 refused to hide by making every known mobile failure end in an explicit durable state.

**In-scope**

- each previously triaged failure must become `fix`, `isolate`, or `delete`
- any chosen isolation must be explicit and justified
- any chosen deletion must explain why the test no longer reflects a supported product path

**Out-of-scope**

- inventing new Stage 12 feature scope on mobile
- carrying failures forward under a new defer label

**Accept requires**

1. decision artifact lands before code
2. all 9 Stage 11 entries resolve to `fix`, `isolate`, or `delete`
3. any fixed item includes direct verification
4. any isolated or deleted item is surfaced plainly in handoff evidence

## 8. Validation Baseline

Stage 12 must preserve:

1. Stage 11 frozen baseline: `144 passed`
2. Stage 11 backend sweep: `14 passed`
3. Stage 11 mobile sweep: `51 tests passed`
4. Rule K guard: `35 files / 0 violation`

Stage 12 closeout is expected to add:

1. backend Stage 12 sweep covering `WS-CL2a / WS-CL2b / WS-CL2c`
2. mobile sweep covering all `WS-MOB1` decisions
3. a rerun of the Stage 11 CL0 audit, using the unchanged Stage 11 audit method
4. Rule V proof snippets in handoff verification evidence

## 9. Stage 13 Decision Lock

Stage 12 final-accept must rerun CL0 and then freeze one of these paths:

1. if at least 2 components become audit-ready -> Stage 13 may open `WS-CL1` for those components only
2. if exactly 1 component becomes audit-ready -> Stage 13 skips `WS-CL1` and prioritizes `WS-EVD3` plus graph deepening
3. if no component becomes audit-ready -> Stage 13 becomes architecture repair / rethink first

This decision tree is part of the Stage 12 handoff contract and must not be improvised later.
