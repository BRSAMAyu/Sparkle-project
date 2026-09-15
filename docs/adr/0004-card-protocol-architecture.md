# ADR 0004: Card Protocol Architecture for Growth Loop System

> Status: **APPROVED** (Phase 0)
> Date: 2026-04-02
> Decision Maker: Product + Architecture
> Supersedes: Prior plan/task model discussions

---

## Context

Sparkle is an AI learning growth system. The product consensus (2026-04-02) defines six outcomes the architecture must support, centered on one closed loop:

`detect a real blockage → deliver help in an acceptable way → user adopts it → action happens → outcome is verified → the system becomes better for this user`

The current system has separate `plans`, `tasks`, `plan_states` models that conflate canonical definitions, execution instances, and presentation state. This makes it impossible to:
- Reuse tasks across contexts
- Track intervention outcomes
- Maintain planning provenance
- Prevent AI drift from user intent

## Decision

We adopt a Card Protocol with six primary persistent primitives:

1. **Card** — unified canonical semantic entity with type discriminator
2. **CardEdge** — graph relationship layer for structure, dependency, and evidence
3. **CardSnapshot** — immutable sharing/export unit
4. **TaskOccurrence** — concrete execution instance (separates scheduling from definition)
5. **PlanningArtifact** — versioned, approved AI governance records
6. **InterventionRecord** — tracked intervention lifecycle with outcome measurement

Key architectural rules:
- Cards are entities; edges are relationships; occurrences are executions
- `card_edges` connect canonical cards only; `TaskOccurrence` provenance lives on the occurrence record
- AI cannot silently mutate approved artifacts
- Execution changes compile from approved artifacts or system policies
- Interventions are structured records, not chat messages
- Legacy tables (`plans`, `tasks`, `plan_states`) survive as transitional projections
- Until full artifact governance is live, Phase 1-2 execution writebacks may be authorized by `legacy PlanState + deterministic system policy + service guardrails`

## Consequences

### Positive
- Future-safe: supports reuse, lineage, evidence, and federation
- AI anti-drift: approved artifacts govern execution writes
- Measurable: intervention records enable outcome tracking
- Clean separation: canonical vs execution vs presentation
- Compatible: legacy adapters allow incremental migration

### Negative
- More tables and joins in the near term
- Migration discipline required (dual-write, shadow validation)
- Learning curve for developers accustomed to flat plan/task model

### Risk Mitigation
- Phase 1 implements only PLAN/PHASE/TASK/KNOWLEDGE cards
- Legacy tables preserved until parity is proven
- Adapters provide backward compatibility during migration
- The Phase 1-2 writeback exception expires once `GLOBAL_COMPASS` and `STRATEGY_MAP` become authoritative in Phase 3

## Implementation Phases

| Phase | Days | Focus |
|-------|------|-------|
| Phase 0 | Complete | Protocol and vocabulary freeze |
| Phase 1 | 0-20 | Core data layer + plan execution writeback |
| Phase 2 | 21-50 | Intervention records + behavior-triggered delivery |
| Phase 3 | 51-70 | Parameter compiler + outcome verification |
| Phase 4 | 71-90 | End-to-end main scenario hardening |
| Phase 5 | Post-90 | Sharing, adoption, federation |

## References

- `docs/product/SPARKLE_PRODUCT_CONSENSUS_2026-04-02.md`
- `docs/product/SPARKLE_CARD_PROTOCOL_TAXONOMY_2026-04-02.md`
- `docs/product/SPARKLE_INTERVENTION_LANGUAGE_SYSTEM_2026-04-02.md`
- `Sparkle_Card_Protocol_Design_Final.md` (design source)
