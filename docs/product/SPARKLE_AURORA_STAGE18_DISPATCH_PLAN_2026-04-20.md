# SPARKLE Aurora Stage 18 Dispatch Plan (2026-04-20)

> Workstream Bundle: `WS-SA-*`
> Phase Mapping: Roadmap v2.0 Phase 1B
> Strategic Focus: build the single read-only `user_state.v1` source of truth and prepare the first governed active-touch path.

## 0. Locked Meta

### 0.1 Scope

Stage 18 does three things:

1. freeze a pull-only `user_state.v1`
2. migrate the Stage 17 social provider seam toward Aggregator-backed reads
3. lay the governed push foundation for commitment follow-up and engagement recovery only

Stage 18 does not do:

1. emotion-triggered push
2. motivation-generation push
3. social-pressure push
4. new-goal proposal push
5. Working Memory
6. LLM extraction
7. Skill consumption of Aggregator output

### 0.2 Rule Audit

- Rule G / H / K / V / Y / Z remain active
- Rule AB is introduced in this stage
- Aggregator is L1 derived, read-only, and may not write back to L0/L1 systems
- Push policy is deterministic and template-based, never free-form LLM text

### 0.3 Codex Self-Answer

1. Router decision logic is not being expanded under the name of Aggregator.
2. Push MVP does not claim to create new motivation; it is limited to commitment follow-up and engagement recovery.
3. No Aggregator field may be written back into source systems.
4. Push design must preserve post-send retraction and correction paths.

## 1. Gate S18-0

Before Stage 18 code claims green, replay:

1. Stage 12 frozen baseline (`144 passed`)
2. Rule V regression (`8 passed`)
3. Rule K + Rule Z CI guards (`0 violation`)
4. Stage 13+14+15+16+17 carry-forward sweep, including Stage 17 new tests
5. Stage 17 handoff Router migrate obligation check (`RouterContextReader` and `SocialContextProvider` remain source-compatible)
6. Stage 17 Router A/B artifact exists and is explicitly interpreted as a source-based engineering audit

## 2. Workstreams

### WS-SA-RULE-AB

Deliver:

- `docs/product/SPARKLE_AURORA_STAGE18_RULE_AB_DEFINITION_2026-04-20.md`
- `scripts/check_rule_ab_aggregator_integrity.py`

### WS-SA-CORE

Deliver:

- frozen Python dataclass schema for `user_state.v1`
- `proto/user_state.proto`
- pull-only `get_user_state(user_id, required_fields)`
- freshness metadata per field

### WS-SA-ROUTER-MIGRATE

Deliver:

- Aggregator-backed `SocialContextProvider` implementation
- source-compatible `FrozenSocialSnapshot` contract preservation
- equivalence tests against Stage 17 direct reader

### WS-SA-PUSH-POLICY

Deliver:

- deterministic `UserState -> Optional[PushDecision]`
- frozen message templates
- daily cap and quiet-hours enforcement at policy layer

### WS-SA-PUSH-CHANNEL

Deliver:

- push delivery abstraction
- delivery record
- retractable window support

### WS-SA-MOBILE

Deliver:

- opt-in default OFF
- category toggles
- inbox with evidence and dismiss actions

### WS-SA-KILL

Deliver:

- three-level kill switch
- admin control surface
- regression coverage

## 3. Frozen `user_state.v1` Field Set

Required fields:

1. `commitment_summary`
2. `recent_person_mentions`
3. `engagement_state`
4. `learning_state`

Reserved but intentionally unset:

1. `emotion_hint`

Each populated field must carry:

1. `value`
2. `computed_at`
3. `source_snapshot_ids`
4. `freshness_seconds`

## 4. Feature Flags

Default OFF:

- `SPARKLE_AGGREGATOR_ENABLED`
- `SPARKLE_ROUTER_USE_AGGREGATOR_PROVIDER`
- `SPARKLE_PUSH_POLICY_ENABLED`
- `SPARKLE_PUSH_DELIVERY_ENABLED`

## 5. Gate S18-FINAL

Stage 18 may claim final green only when:

1. Gate S18-0 replay remains green
2. Rule AB doc and guard both land
3. schema contract tests are green
4. router migrate equivalence remains source-compatible
5. push policy and delivery tests are green
6. mobile opt-in and inbox tests are green
7. Stage 19A roadmap obligation is recorded: Working Memory must consume Aggregator input instead of building a parallel state layer

