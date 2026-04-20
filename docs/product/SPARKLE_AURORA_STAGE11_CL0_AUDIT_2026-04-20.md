# SPARKLE Aurora Stage 11 CL0 Audit (2026-04-20)

> **Status**: final `WS-CL0` audit artifact
> **Purpose**: record the production-readiness verdict for the five continuous-learning components before any user-facing wiring is allowed.
> **Method source**: `SPARKLE_AURORA_STAGE11_CL0_AUDIT_METHOD_2026-04-20.md`

## 1. Final Verdict

No Stage 11 continuous-learning component is currently eligible for direct user-facing wiring.

The closest production-grade component is `PromptBandit`, but it optimizes prompt and template arm selection rather than a user-perceptible "Sparkle learned something about me" signal. The remaining components are either behind flags, lack durable persistence, or have broken integration seams.

## 2. Audit Grid

| Component | Production status | Signal quality | Known defects | Stage 12 recommendation |
| --- | --- | --- | --- | --- |
| `PromptBandit` | **active in production traffic** via `StreamChat`, `TemplateService`, `InterventionService`, and `ResponseFeedbackService` | **trusted for internal optimization, not user-perceptible**; output is arm choice / reward stats, not a user-visible growth insight | binary reward only; admin debug surface is read-only; no semantic mapping from arm stats to a user-facing learning claim | `do_not_wire` |
| `PersistentBayesianLearner` | **partially active** in routing when `RouterNode` receives `redis_client + user_id`; not consistently used by `ToolPreferenceRouter` because that path currently instantiates with `redis_client=None` | **internal-only routing confidence**; useful for route choice, not trustworthy as a user-facing progress signal | persistence usage is fragmented; `persist_bayesian_data` writes `bayesian_learner:{user_id}` while the learner reads `learner:{user_id}`; one important call path drops back to non-persistent `BayesianLearner` | `repair_first` |
| `distiller` | **not active in normal production path**; `run_continuous_learning_pipeline()` returns `distiller_disabled` unless `SPARKLE_WS7_DISTILLER_ENABLED` is turned on | **not yet trustworthy** because the feature is disabled by default and no user-facing validation loop exists | hard feature-flag gate; pipeline writes only to `InMemoryDistilledStrategyStore`; no durable product path into IC1 / front door | `repair_first` |
| `multi_dimensional_learner` | **effectively not in production**; only referenced by tests and a Celery task stub | **untrusted** for user-facing use because no live product path exercises or validates its output | `save_learning_state` Celery task calls `learner.save_state(...)`, but `MultiDimensionalLearner` does not implement `save_state`; no current product read surface consumes its breakdown | `do_not_wire` |
| `strategy_store` | **not production-grade**; current implementation is `InMemoryDistilledStrategyStore` used by tests, pipeline, and optional retrieval seam only | **not trustworthy for user-facing recall** because records are ephemeral and retrieval is disabled by default | no durable persistence layer; retrieval is separately gated by `SPARKLE_WS7_RETRIEVAL_ENABLED`; no authoritative lifecycle outside process memory | `repair_first` |

## 3. Evidence Notes

### 3.1 `PromptBandit`

- Active production call paths:
  - `backend/app/services/agent_grpc_service.py`
  - `backend/app/services/template_service.py`
  - `backend/app/services/intervention_service.py`
  - `backend/app/services/response_feedback_service.py`
- Operational verdict:
  - this is a real optimization seam, but it learns which prompt or template arm performs better, not whether the user is becoming more capable in a way Sparkle should surface back to them

### 3.2 `PersistentBayesianLearner`

- Active / partial call paths:
  - `backend/app/routing/router_node.py`
  - `backend/app/routing/tool_preference_router.py`
- Critical defect:
  - `backend/app/core/celery_tasks.py` persists to `bayesian_learner:{user_id}`, while `backend/app/learning/persistent_bayesian_learner.py` loads from `learner:{user_id}`
- Operational verdict:
  - worthwhile routing infrastructure, but not a stable user-facing learning signal and not yet a coherent persistent subsystem

### 3.3 `distiller`

- Feature-gated source:
  - `backend/app/learning/distiller.py`
- Product-path blocker:
  - `backend/app/learning/pipeline.py` returns `distiller_disabled` when the flag is off
- Operational verdict:
  - the conceptual path exists, but Stage 11 cannot claim this is live continuous learning while the default path short-circuits before durable storage or user review

### 3.4 `multi_dimensional_learner`

- Only notable runtime reference:
  - `backend/app/core/celery_tasks.py`
- Critical defect:
  - task code calls a missing `save_state()` API that the learner class does not expose
- Operational verdict:
  - treat as dormant infrastructure, not a candidate for front-door wiring

### 3.5 `strategy_store`

- Current store class:
  - `backend/app/learning/strategy_store.py`
- Retrieval seam:
  - `backend/app/learning/retrieval.py`
- Operational verdict:
  - useful as a local sidecar seam for tests and experiments, but not a production-trustworthy strategy memory until persistence and retrieval flags are made real

## 4. Stage 12 Decision

Stage 11 locks **Decision Path 2** from the dispatch plan:

1. `PromptBandit` is the only component with stable production traffic
2. its optimization target is **not user-perceptible learning**
3. therefore Stage 12 must **not** open `WS-CL1`
4. Stage 12 should instead prioritize `WS-EVD3` or other front-door deepening work until the continuous-learning substrate is repaired

## 5. Hard Conclusion

Until at least one component is both:

1. live in a real product path, and
2. producing a trustworthy user-perceptible learning signal,

Sparkle must not tell the user that continuous learning has become part of the front door.
