# Sparkle P4 Research-Grade Adaptive Intelligence — Progress Log

> **Blueprint**: `docs/product/advanced_improvement_guide` (P4 全面落地指南, 2026-04-27)
> **Start**: 2026-04-27
> **Goal**: Upgrade Sparkle from P3 Goal OS → research-grade adaptive intelligence with 5 world-class capabilities

## P4 Capability Targets

1. 判断策略是否真的有效（反事实评估）
2. 上线前模拟策略风险（Simulation Lab）
3. 沉淀可复用知识资产（Marketplace）
4. 隐私社群→个人策略（Community Intelligence）
5. 自治审计、评估、修正（Quality Guard）

## Five Planes

```
A. Evidence Plane — InterventionEpisode, ContextSignature, OutcomeVector
B. Evaluation Plane — CounterfactualEstimate, EvidenceGrade, MatchedContext
C. Safe Adaptation Plane — SafeBandit, Shadow/Canary/Promotion/Rollback
D. Knowledge Asset Plane — SkillCard v2, DomainPack, Marketplace
E. Governance Plane — QualityGuard, RegressionDetection, AutoKillSwitch
```

---

## P4-0: Evaluation-Grade Logging

**Status**: IN PROGRESS
**File**: `backend/app/signals/intervention_episode.py`
**Tests**: `backend/tests/unit/test_signal_spine.py`

### Deliverables
- [x] Enter plan mode
- [ ] `InterventionEpisode` — core evidence unit with context_signature, candidate_policies, selection_probability, evidence_quality
- [ ] `ContextSignature` — 9-dim structure snapshot
- [ ] `OutcomeVector` — 7-class, 20+ metric multi-objective outcome
- [ ] `EvidenceQuality` — propensity_logged, counterfactual_candidates_logged, outcome_complete, user_feedback_present
- [ ] `InterventionEpisodeLedger` — CRUD + batch analysis
- [ ] Tests (8+ new)
- [ ] Commit

---

## P4-1: Counterfactual Policy Evaluation

**Status**: PENDING
**File**: `backend/app/signals/counterfactual_evaluation.py`
**Base**: enhances `research_grade.py`

### Deliverables
- [ ] `EvidenceGrade` (Grade 0-5 system)
- [ ] `MatchedContextEvaluator` — context-distance-based matching
- [ ] `CounterfactualEstimate` — estimated_effect + uncertainty + recommendation
- [ ] `PolicyComparisonReport`
- [ ] `PolicyUpdateCandidate` — allowed_mode / not_allowed
- [ ] 6 iron laws enforcement
- [ ] Tests (6+ new)

---

## P4-2: Safe Adaptive Experiment Platform

**Status**: PENDING
**File**: `backend/app/signals/safe_experiment_platform.py`
**Base**: enhances `policy_experiments.py`

### Deliverables
- [ ] Full 7-stage lifecycle (draft→shadow→canary→safe_live→paused→concluded→deprecated)
- [ ] `SafeBanditController` — risk-aware exploration with human-in-the-loop
- [ ] Multi-objective reward model (7 primary + 4 guardrail weights)
- [ ] `ExperimentGuardrails` with auto-stop conditions
- [ ] `ExperimentRollback` mechanism
- [ ] `PromotionGate` (min_episodes, min_users, evidence_grade, posterior_probability, human_review)
- [ ] Tests (8+ new)

---

## P4-3: Simulation Lab & SparkleGoalBench

**Status**: PENDING
**File**: `backend/app/signals/simulation_lab.py`
**Base**: enhances `research_grade.py` UserSimulator

### Deliverables
- [ ] `SparkleGoalBench` — 4 suites (ExamSprint, ProjectDelivery, JobSearch, MultiGoalLife)
- [ ] `ScenarioDSL` — structured scenario definition
- [ ] `TraceReplaySimulator` — replay historical traces against new policy
- [ ] `ScenarioSimulator` — 24 regression scenarios
- [ ] `SyntheticPersonaSimulator` — 7 persona types
- [ ] `RegressionReport` — scenario → passed/violations/spine_integrity/user_agency
- [ ] Tests (6+ new)

---

## P4-4: Skill & DomainPack Marketplace

**Status**: PENDING
**File**: `backend/app/signals/marketplace.py`
**Base**: enhances `skill_lifecycle.py`, `domain_pack.py`, `strategy_marketplace.py`

### Deliverables
- [ ] `SkillCardV2` — full evidence, contraindications, privacy, governance
- [ ] 14-level promotion workflow (personal_candidate → ... → marketplace_listed)
- [ ] `DomainPackRegistry` — structured domain pack with quality evidence
- [ ] `MarketplacePreview` + `UserAdoptionFlow`
- [ ] 10 marketplace iron laws enforcement
- [ ] Tests (8+ new)

---

## P4-5: Privacy-Preserving Community Intelligence v2

**Status**: PENDING
**File**: `backend/app/signals/community_intelligence_compiler.py`
**Base**: enhances `privacy_community_intelligence.py`

### Deliverables
- [ ] `CommunityInsightCompiler` — raw events → privacy filter → cohort → min-k → aggregate → confidence → signal
- [ ] `CommunityAggregateSignalV2` — rich signal types (common_mistake, resource_quality, task_template, strategy)
- [ ] `CommunityResourceQualityLedger`
- [ ] Explicit opt-out mechanism with audit trail
- [ ] 5-level privacy classification
- [ ] Tests (6+ new)

---

## P4-6: Autonomous Quality Guard v2

**Status**: PENDING
**File**: `backend/app/signals/quality_guard_v2.py`
**Base**: enhances `spine_quality_guard.py`

### Deliverables
- [ ] `SystemHealthInsight` — severity, component, symptom, possible_causes, affected_segments, recommended_actions, auto_actions_taken
- [ ] `PolicyRegressionDetector`
- [ ] `SourcePollutionDetector`
- [ ] `SkillRegressionDetector`
- [ ] `PrivacyViolationGuard` with auto-kill-switch
- [ ] `AutoKillSwitch` integration
- [ ] Tests (8+ new)

---

## P4-7: Research Mode

**Status**: PENDING
**File**: `backend/app/signals/research_mode.py`

### Deliverables
- [ ] `ResearchDatasetBuilder` — anonymized research episode builder
- [ ] `ResearchProtocolRegistry` — registered research questions with ethics boundaries
- [ ] `AnonymizationPipeline` — user_id removal, source content removal, free text redaction
- [ ] `ReproducibleAnalysisExport`
- [ ] `BenchmarkReport`
- [ ] Tests (6+ new)

---

## Module Inventory

| # | Module | P4 Phase | Status |
|---|--------|----------|--------|
| 1 | `intervention_episode.py` | P4-0 | IN PROGRESS |
| 2 | `research_grade.py` | P4-1/2/3 | EXISTS (v1) |
| 3 | `research_experiment_platform.py` | P4-4 | EXISTS (v1) |
| 4 | `privacy_community_intelligence.py` | P4-5 | EXISTS (v1) |
| 5 | `spine_quality_guard.py` | P4-6 | EXISTS (v1) |
| 6 | `policy_experiments.py` | P4-2 | EXISTS (v1) |
| 7 | `learning_base.py` | P4-1 | EXISTS (v1) |
| 8 | `counterfactual_evaluation.py` | P4-1 | PENDING |
| 9 | `safe_experiment_platform.py` | P4-2 | PENDING |
| 10 | `simulation_lab.py` | P4-3 | PENDING |
| 11 | `marketplace.py` | P4-4 | PENDING |
| 12 | `community_intelligence_compiler.py` | P4-5 | PENDING |
| 13 | `quality_guard_v2.py` | P4-6 | PENDING |
| 14 | `research_mode.py` | P4-7 | PENDING |

## Test Count Tracker

| Phase | Start | End |
|-------|-------|-----|
| P4-0 | TBD | TBD |
