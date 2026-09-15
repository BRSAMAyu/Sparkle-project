# ADR-0007: Research-Grade v1→v2 Migration and Deprecation

**Status**: Accepted
**Date**: 2026-05-02
**Context**: FV-25 (v1/v2 旧代码清理 + 文档同步)

## Context

The Sparkle signal pipeline evolved through two generations of research-grade modules:

- **v1** (`app.signals.research_grade.py`): Monolithic module containing CounterfactualEngine, UserSimulator, SimulatedUserProfile, DomainPack, and DomainPackMarketplace.
- **v2** (multiple focused modules): Each v1 class was replaced by a more capable, governance-compliant v2 implementation:

| v1 Class | v2 Module | v2 Replacement |
|----------|-----------|----------------|
| `CounterfactualEngine` | `counterfactual_evaluation.py` | `MatchedContextEvaluator` + `CounterfactualReportService` + 6 Iron Laws |
| `UserSimulator` | `simulation_lab.py` | `SyntheticPersonaSimulator` + `ScenarioSimulator` |
| `SimulatedUserProfile` | `simulation_lab.py` | `Persona` |
| `DomainPack` | `marketplace.py` | `SkillCard` (evidence-backed, effectiveness-tracked) |
| `DomainPackMarketplace` | `marketplace.py` | `MarketplaceRegistry` + `MarketplaceIronLaws` |

v2 advantages: evidence grading (0-5), multi-objective optimization, iron law enforcement (6 counterfactual + 10 marketplace), differential privacy, 7-stage experiment lifecycle, production persistence, audit trails.

## Decision

1. **Deprecate v1 module**: All v1 classes marked `# DEPRECATED` with explicit v2 module references in docstrings.
2. **Rename v1 exports**: In `signals/__init__.py`, v1 exports renamed with `_v1` suffix (e.g., `DomainPack_v1`) to prevent new code from importing them accidentally.
3. **Keep v1 code functional**: The module is not deleted yet — existing tests and any external consumers can still import it directly. Removal scheduled for next sprint.
4. **Test annotations**: Existing tests that test v1 functionality annotated with `# noqa: DEPRECATED v1` to distinguish from v2 test imports.
5. **No new code in v1 module**: Header explicitly states "Do not add new code here."

## Consequences

- **Positive**: Clear migration path, no broken imports, new code guided to v2 modules.
- **Negative**: Temporary namespace pollution with `_v1` suffixed exports; two test files still test v1 logic directly.
- **Migration timeline**: v1 module deleted in next sprint after all consumers verified on v2.

## Migration Map

```
CounterfactualEngine       → MatchedContextEvaluator + CounterfactualIronLawEnforcer
CounterfactualResult       → CounterfactualEstimate + PolicyComparisonReport
UserSimulator              → SyntheticPersonaSimulator
SimulatedUserProfile       → Persona
DomainPack                 → SkillCard
DomainPackMarketplace      → MarketplaceRegistry + MarketplaceIronLaws
```
