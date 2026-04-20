# SPARKLE Aurora Stage 12 CL0 Rerun (2026-04-20)

> **Status**: Gate `S12-FINAL` audit rerun artifact
> **Purpose**: re-run the Stage 11 `CL0` audit with the **same method document** after `WS-CL2a` / `WS-CL2b` / `WS-CL2c` closeout.
> **Method source**: `SPARKLE_AURORA_STAGE11_CL0_AUDIT_METHOD_2026-04-20.md`

## 1. Final Verdict

Stage 12 repaired the continuous-learning substrate, but it did **not** produce a user-facing-ready learning signal.

The repaired components are now materially healthier than they were in Stage 11:

1. `PersistentBayesianLearner` key usage is coherent
2. `multi_dimensional_learner` no longer exposes a broken `save_state()` seam
3. `strategy_store` is now durable instead of restart-loss-prone

However, **no component reaches `wire`** under the unchanged Stage 11 audit method. The remaining blockers are no longer "obvious implementation bugs"; they are product-path and signal-quality gaps.

Result: Stage 13 locks to **Decision Path C** from the Stage 12 dispatch plan.

## 2. Comparison Grid

| Component | Stage 11 verdict | Stage 12 production status | Stage 12 signal quality | Stage 12 known defects | Stage 12 recommendation |
| --- | --- | --- | --- | --- | --- |
| `PromptBandit` | `do_not_wire` | **active in production traffic** via `StreamChat`, `TemplateService`, `InterventionService`, and `ResponseFeedbackService` | **trusted for internal optimization, not user-perceptible**; it still chooses prompt/template arms rather than surfacing a growth claim | reward remains binary and optimization-local; no semantic layer translates arm stats into a user-facing “Sparkle learned X about me” statement | `do_not_wire` |
| `PersistentBayesianLearner` | `repair_first` | **partially active with repaired persistence contract**; canonical key + TTL are now aligned, and the learner can round-trip its state | **internal-only routing confidence**; useful for route choice, still not a user-facing progress signal | `RouterNode` still instantiates `ToolPreferenceRouter(..., redis_client=None)` on one important path, which falls back to non-persistent `BayesianLearner`; no user-perceptible interpretation layer exists | `repair_first` |
| `distiller` | `repair_first` | **still not active in the default production path**; feature flag remains off by default | **not yet trustworthy** because no live user validation loop exists and the feature still short-circuits by default | durable storage is now available, but `SPARKLE_WS7_DISTILLER_ENABLED` remains the gating condition and there is still no user-review / front-door path | `repair_first` |
| `multi_dimensional_learner` | `do_not_wire` | **dormant but no longer broken**; the Celery persistence seam now calls a real `save_state()` implementation | **untrusted for user-facing use** because no live product consumer exercises or validates its breakdowns | Stage 12 repaired persistence only; there is still no audited production read surface or semantic mapping into a user-facing learning claim | `repair_first` |
| `strategy_store` | `repair_first` | **durable L2 inference cache now exists**; records survive repository re-instantiation and optional retrieval can read persisted state | **not yet trustworthy for front-door recall** because the store is still only reached by flagged distillation / retrieval seams | restart-loss is fixed, but retrieval remains behind `SPARKLE_WS7_RETRIEVAL_ENABLED` and there is still no authoritative product loop that turns stored strategies into trusted user-facing learning evidence | `repair_first` |

## 3. Evidence Notes

### 3.1 `PromptBandit`

- Active production call paths remain:
  - `backend/app/services/agent_grpc_service.py`
  - `backend/app/services/template_service.py`
  - `backend/app/services/intervention_service.py`
  - `backend/app/services/response_feedback_service.py`
- Stage 12 change impact:
  - none; this remains a strong optimization seam, but not a user-perceptible learning seam

### 3.2 `PersistentBayesianLearner`

- Stage 12 repairs landed:
  - canonical key alignment in `backend/app/learning/persistent_bayesian_learner.py`
  - Celery persistence alignment in `backend/app/core/celery_tasks.py`
- Remaining blocker:
  - `backend/app/routing/router_node.py` still creates `ToolPreferenceRouter(..., redis_client=None)` on a key path, so persistence is not yet universal

### 3.3 `distiller`

- Feature gate remains:
  - `backend/app/learning/distiller.py`
- Stage 12 improvement:
  - when the feature is enabled, it now has a durable downstream store
- Remaining blocker:
  - default product path still returns `distiller_disabled`; no user validation loop exists

### 3.4 `multi_dimensional_learner`

- Stage 12 repairs landed:
  - `backend/app/learning/multi_dimensional_learner.py`
  - `backend/app/core/celery_tasks.py`
- Remaining blocker:
  - no production-facing consumer currently reads or interprets the persisted multidimensional breakdown

### 3.5 `strategy_store`

- Stage 12 repairs landed:
  - `backend/app/learning/strategy_store.py`
  - `backend/app/models/distilled_strategy_cache.py`
  - `backend/alembic/versions/cl2c1d2e3f4_add_distilled_strategy_cache.py`
- Rule V evidence:
  - `backend/tests/unit/test_distilled_strategy_store_contract.py` proves restart survival, durable lifecycle transitions, and retrieval against a re-instantiated store
- Remaining blocker:
  - still no default product loop turns stored strategies into user-trustworthy front-door evidence

## 4. Stage 13 Path Decision

Stage 12 triggers **Path C**:

```text
no component reached wire / audit-ready
→ Stage 13 must not open WS-CL1
→ Stage 13 should treat continuous learning as a substrate / architecture problem first
```

That means the next stage should prioritize one of:

1. deeper substrate repair for the learning components that are still only partially active
2. evidence / graph deepening that does **not** falsely claim continuous-learning front-door readiness
3. an explicit architecture-level decision about whether one repaired component should become the nucleus of future user-facing learning signals
