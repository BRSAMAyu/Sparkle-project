# SPARKLE Aurora Stage 11 CL0 Audit Method (2026-04-20)

> **Purpose**: freeze the audit steps and verdict format for `WS-CL0`.

## Components In Scope

1. `PromptBandit`
2. `PersistentBayesianLearner`
3. `distiller`
4. `multi_dimensional_learner`
5. `strategy_store`

## Audit Steps Per Component

1. locate production entrypoints and call sites
2. verify whether the component runs in the current product path or only in tests / behind flags
3. inspect persistence and lifecycle behavior
4. inspect whether outputs are user-perceptible or only internal optimization signals
5. assign one final recommendation:
   - `wire`
   - `repair_first`
   - `do_not_wire`

## Evidence Format

Each component verdict must include:

1. `production_status`
2. `signal_quality`
3. `known_defects`
4. `stage12_recommendation`

## Hard Boundaries

1. CL0 may only read code, tests, flags, and call graphs
2. CL0 may not add product wiring
3. CL0 may not create a write lane or mutate runtime behavior
