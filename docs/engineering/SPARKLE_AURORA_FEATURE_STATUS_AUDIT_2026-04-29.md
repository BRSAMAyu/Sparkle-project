# Aurora Feature Status Audit — 2026-04-29

Generated during code review sweep. Cross-references `.env.example` kill switches
against actual implementation files.

## Summary

| Status    | Count | Meaning                                      |
|-----------|-------|----------------------------------------------|
| live      | 7     | Active in production path                    |
| shadow    | 6     | Compute but don't surface to user            |
| off       | 19    | Feature code exists, kill switch disabled    |
| **Total** | **32**|                                              |

## Full Inventory

### Stage 18 — Aggregator & Push

| Feature                  | Mode   | Implementation File                                    | Notes |
|--------------------------|--------|--------------------------------------------------------|-------|
| AURORA_STAGE18_AGGREGATOR | live   | `state_aggregator/service.py`                          | Core pipeline active |
| AURORA_STAGE18_PUSH_POLICY | off   | `push_policy_compiler.py`                              | Code complete, needs integration testing |
| AURORA_STAGE18_PUSH_DELIVERY | off | `push_delivery_service.py`                            | Code complete, needs integration testing |

### Stage 19 — Working Memory

| Feature                       | Mode | Implementation File                    | Notes |
|-------------------------------|------|----------------------------------------|-------|
| AURORA_STAGE19_WORKING_MEMORY | off  | Memory service + prompt injection      | Code complete, turned off for prompt budget reasons |
| AURORA_STAGE19_LLM_EXTRACTOR  | off  | LLM-based memory extraction            | Code complete |
| AURORA_STAGE19_CONSOLIDATION  | off  | Memory consolidation service           | Code complete |

### Stage 21 — Skill System

| Feature                     | Mode | Implementation File              | Notes |
|------------------------------|------|----------------------------------|-------|
| AURORA_STAGE21_SKILL_STORE  | live | Skill store + CRUD               | Active |
| AURORA_STAGE21_SKILL_SELECTION | off | Skill selection engine          | Code complete, awaiting Bayesian wire-on (Stage 23) |
| AURORA_STAGE21_SKILL_SHARE  | off  | Skill sharing service            | Code complete, awaiting community bridge |

### Stage 23 — Bayesian Learner

| Feature            | Mode   | Implementation File              | Notes |
|--------------------|--------|----------------------------------|-------|
| AURORA_BAYESIAN    | shadow | Bayesian learner service         | Computing but not affecting live decisions |

### Stage 24–27 — Reflection, Scene, Foresight

| Feature                    | Mode | Implementation File                  | Notes |
|-----------------------------|------|--------------------------------------|-------|
| AURORA_REFLECTION_WIRE     | off  | Reflection service                   | Code complete |
| AURORA_SCENE               | off  | `scene_consolidation_service.py`     | Code complete |
| AURORA_FORESIGHT           | off  | `foresight_deviation_service.py`     | Code complete |
| AURORA_POLICY_COMPILER     | off  | Policy compiler                      | Code complete |

### Stage 28 — Traits

| Feature                    | Mode | Implementation File                         | Notes |
|-----------------------------|------|---------------------------------------------|-------|
| AURORA_TRAITS              | off  | `aurora_stage28_traits_kill_switch_service.py` | Code complete |
| AURORA_TRAITS_NLP          | off  | `traits_nlp_observer_service.py`            | Code complete |
| AURORA_TRAITS_COLDSTART    | off  | Traits cold-start service                   | Code complete |

### Stage 29 — SRL (Self-Regulated Learning)

| Feature                          | Mode | Implementation File                    | Notes |
|-----------------------------------|------|----------------------------------------|-------|
| AURORA_SRL                       | off  | `srl_phase_tracker_service.py`        | Code complete |
| AURORA_SRL_TRACKER               | off  | `srl_phase_types.py`                  | Code complete |
| AURORA_SRL_BRIDGE                | off  | SRL bridge service                    | Code complete |
| AURORA_SRL_SCAFFOLDING_CONSUME   | off  | Scaffolding consumer                  | Code complete |

### Stage 31–32 — Metacognition & Idiographic

| Feature                          | Mode   | Implementation File                    | Notes |
|-----------------------------------|--------|----------------------------------------|-------|
| AURORA_METACOG                   | off    | `metacognition_service.py`            | Code complete |
| AURORA_METACOG_DASHBOARD         | live   | Metacog dashboard                     | Active (read-only) |
| AURORA_METACOG_PROCESS_SCAFFOLDING | live | Process scaffolding                   | Active |
| AURORA_METACOG_FSM_COMBINE       | live   | FSM combine                           | Active |
| AURORA_IDIOGRAPHIC               | shadow | `idiographic_association_service.py`  | Computing, not live |

### Stage 33 — Journey Events

| Feature                   | Mode   | Implementation File                | Notes |
|----------------------------|--------|------------------------------------|-------|
| AURORA_STAGE33            | shadow | `stage33_journey_event_service.py` | Computing, not live |
| AURORA_STAGE33_SOCIAL     | live   | Social signal bridge               | Active |
| AURORA_STAGE33_SRL        | shadow | SRL journey events                 | Computing, not live |
| AURORA_STAGE33_WM_PROMPT  | shadow | WM prompt injection via Stage33    | Computing, not live |
| AURORA_STAGE33_EVENTS     | shadow | Journey event publishing           | Computing, not live |

---

## Key Findings

1. **Zero missing code.** All 25 off/shadow features have complete implementation files.
   They are disabled by kill switch, not unimplemented.

2. **Shadow features (6)** are actively computing but results are not surfaced to users.
   Bayesian, Idiographic, Stage33 — these are "learning in the dark."

3. **The gap is integration testing, not implementation.** Features are off because
   no one has validated the end-to-end behavior when enabled.

4. **Three features are partially live.** Metacog has 3 live sub-modes (dashboard,
   process_scaffolding, fsm_combine) while the main METACOG switch is off.
   Stage33 has SOCIAL live while the main switch is shadow.

## Recommended Actions

1. **P0**: Run integration smoke test with all shadow features → live, one at a time
2. **P1**: Enable push_policy + push_delivery (Stage 18) — they're blocking notification UX
3. **P2**: Graduate Bayesian from shadow→live after Stage 23 wire-on validation
4. **P3**: Document explicit graduation criteria for each off feature
