# Sparkle Phase E Five-Layer Baseline Audit

> Date: 2026-04-05  
> Scope: Pack E0 baseline before the Phase E runtime changes become the primary substrate

## Purpose

This audit captures the actual pre-Phase-E shape of the five-layer learning system so later verification can compare implementation against a concrete baseline instead of a remembered one.

## Current Write Map

| Layer | Current store | Main writers | Current strengths | Current gaps |
|---|---|---|---|---|
| constitutional | code artifacts | `soul_compiler.py`, companion constitution artifacts | identity and anti-drift language already exists | promotion checks are mostly implicit, not enforced at every durable write |
| session | Redis | `CompanionStateService`, `UserStrategyStateService`, `OutcomePromotionGovernor` | cheap reversible writes already work | no shared contract, conflict handling fragmented |
| episode | `PlanState.facts` | `SelfRevisionService`, `UserStrategyStateService`, `OutcomePromotionGovernor` | episode substrate exists in the active plan store | metadata shape differs by subsystem and demotion is weak |
| profile | `UserPreferencesCenter.inferred` | `SelfRevisionService`, `RelationshipProfileService`, `OutcomePromotionGovernor`, strategy/profile services | durable store already exists | profile claims can be promoted without one canonical evidence model |
| system | capability registry metadata | `CapabilityRegistryService`, `CapabilityKnobGovernor` | rights discussion already exists | bounded rights were incomplete and constitutional review was not first-class |

## Baseline Risks

1. Session, episode, and profile each had partial thresholds, but they were encoded separately in companion, strategy, and outcome services.
2. Outcome learning had conflict and demotion signals, but companion-state and strategy-state conflict handling still lived mostly inside local heuristics.
3. Durable self-description and relationship profile growth relied on good behavior plus prompt discipline more than on a shared firewall.
4. The system layer described bounded control, but the knob contract was not yet explicit enough to serve as a freezeable rights model.
5. Auditability existed in multiple ledgers, but there was no compact Phase E read model that could answer "what does Sparkle believe at each layer and why?"

## Scenario Set

The canonical baseline scenario fixture for Phase E lives at:

- `backend/tests/fixtures/phase_e_five_layer_learning_scenarios.json`

It covers ten multi-session journeys:

1. exam sprint continuity
2. overload and recovery
3. confidence rebuilding
4. project burst
5. one-off emotional reaction
6. contradictory history vs self-report
7. stale learning reversal
8. relationship-boundary confirmation
9. forbidden system-rights request
10. constitution-adjacent drift proposal

## What Phase E Must Improve Relative To This Baseline

- one machine-readable five-layer contract
- one shared cross-layer conflict resolver
- one constitutional firewall on durable learning and system rights
- standardized episode/profile governance metadata
- one deterministic personalization maturity harness

## Freeze Notes

This document is the Pack E0 baseline reference. The matching post-implementation comparison is:

- `docs/verification/SPARKLE_PHASE_E_FIVE_LAYER_VERIFICATION_REPORT_2026-04-05.md`
