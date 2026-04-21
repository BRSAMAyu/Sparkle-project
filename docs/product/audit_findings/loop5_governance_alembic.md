# Loop 5: Governance Rule Guard Quality

> Executed: 2026-04-21
> Sub-agents used: 3 Explore agents (Rules K-M, Rules AE-AL, Rules AM-AN + missing guards)
> Duration: ~12 min

> Normalization note: this file is a raw per-loop record. Final severity, dedupe, and closeout status are maintained in the full report. Rule AH's CWD fragility was subsequently fixed during closeout.

## Findings

| # | Severity | Stage | Category | Finding | File:Line | Evidence |
|---|----------|-------|----------|---------|-----------|----------|
| L5-1 | P1 | S4 | Missing Guard | Rules G (single-WS commit) and H (agent allowlist) have NO automated enforcement | scripts/rule_guard_manifest.tsv | Not listed in manifest; relies on manual discipline only |
| L5-2 | P1 | S17 | Missing Guard | Rules P, Q, U (social fact governance) have NO automated enforcement | scripts/rule_guard_manifest.tsv | Convention-only enforcement |
| L5-3 | P1 | S28 | Fragile Guard | `check_nlp_no_direct_write.py` uses simple string-match — bypassable via method chaining | scripts/stage28/check_nlp_no_direct_write.py | Checks `.traits_prior =` as text, not AST |
| L5-4 | P1 | S24 | Fragile Guard | `check_rule_ai_policy_purity.py` uses string-match for LLM import detection — bypassable via import aliases | scripts/stage24/check_rule_ai_policy_purity.py | Checks "openai" as text token |
| L5-5 | P2 | S23 | CWD Dependency | `check_rule_ah_dimension_registry.py` uses relative path `Path("docs/aurora/...")` — breaks if not run from repo root | scripts/stage23/check_rule_ah_dimension_registry.py | CI mitigates via PYTHONPATH but fragile |

## Guard Quality Matrix

### Rules WITH Guards (18 rules, 23 scripts)

| Rule | Guard Script | Method | Rating | Bypass Risk | CI |
|------|-------------|--------|--------|-------------|-----|
| K | check_rule_k_write_paths.py | String-match | ADEQUATE | HIGH | YES |
| Y | check_rule_y_inferred_extraction.py | AST | ROBUST | MEDIUM | YES |
| Z | check_rule_z_social_boundary.py | String-match | ADEQUATE | HIGH | YES |
| AB | check_rule_ab_aggregator_integrity.py | AST | ROBUST | LOW | YES |
| AC | check_rule_ac_working_memory.py | String-match | FRAGILE | HIGH | YES |
| AD | check_rule_ad_sufficiency_split.py | String-match | FRAGILE | HIGH | YES |
| AE | check_rule_ae_conflict_audit.py | AST | ROBUST | LOW | YES |
| AF-1 | check_rule_af_skill_share_isolation.py | String-match | ADEQUATE | MED-HIGH | YES |
| AF-2 | check_rule_af_skill_pii_pipeline.py | String-match | FRAGILE | HIGH | YES |
| AG | check_rule_ag_baseline_prerequisite.py | Hybrid | ADEQUATE | MEDIUM | YES |
| AH | check_rule_ah_dimension_registry.py | String-match | FRAGILE | HIGH | YES |
| AI | check_rule_ai_policy_purity.py | String-match | FRAGILE | HIGH | YES |
| AJ | check_rule_aj_user_id_isolation.py | AST | ROBUST | LOW | YES |
| AK | check_rule_ak_algorithm_constraint.py | String-match | ADEQUATE | MEDIUM | YES |
| AL-1 | check_rule_al_foresight_not_router.py | String-match | ADEQUATE | MEDIUM | YES |
| AL-2 | check_rule_al_sdt_language.py | String-match | ADEQUATE | MEDIUM | YES |
| AM | check_rule_am_confidence_cap.py | AST+Hybrid | ROBUST | LOW | YES |
| AN-1 | check_rule_an_orchestrator_isolation.py | String-match | ADEQUATE | MEDIUM | YES |
| AN-2 | check_rule_an_orchestrator_no_hardcoded_phase.py | String-match | ADEQUATE | MEDIUM | YES |
| AN-3 | check_scaffolding_aggregator_only.py | String-match | ADEQUATE | MEDIUM | YES |
| AQ | check_rule_aq_python_proto_parity.py | Runtime+AST | ROBUST | LOW | YES |

### Additional Stage-Specific Guards

| Guard | Method | Rating | Bypass Risk |
|-------|--------|--------|-------------|
| check_trait_not_router.py | String-match | ADEQUATE | MEDIUM |
| check_nlp_no_direct_write.py | String-match | FRAGILE | HIGH |
| check_nlp_bias_calibration.py | Runtime | ROBUST | LOW |
| check_traits_no_diagnostic_labels.py | String-match | ADEQUATE | MEDIUM |
| check_srl_not_router.py | String-match | ADEQUATE | MEDIUM |
| check_srl_no_llm_import.py | String-match | ADEQUATE | MEDIUM |
| check_srl_user_isolation.py | String-match | ADEQUATE | MEDIUM |

### Rules WITHOUT Guards (7+ rules)

| Rule | Description | Stage | Enforcement | Risk |
|------|-------------|-------|-------------|------|
| G | Single-WS commit discipline | S4 | Manual only | HIGH |
| H | Agent allowlist + escalation | S4 | Manual only | HIGH |
| I | Mandatory handoff artifact | S4 | Manual only | MEDIUM |
| P | User correction authority | S17 | Convention only | MEDIUM |
| Q | Front-door readable social facts | S17 | API design only | MEDIUM |
| U | Widget-actionable entries | S17 | UI convention only | MEDIUM |
| V | Regression contracts | S17 | Test coverage only | MEDIUM |

## Verified OK

| # | Claim | Verified In | Notes |
|---|-------|-------------|-------|
| V5-1 | All guard scripts use no CWD dependency (except AH) | All scripts use Path(__file__).resolve() | 1 exception (AH) |
| V5-2 | All guards CI-integrated via manifest | rule_guard_manifest.tsv | 23 entries, all in CI |
| V5-3 | Rule K has dual CI coverage | ci.yml:228 + manifest | Explicit + manifest |
| V5-4 | Parallel guard execution supported | run_all_rule_guards.sh --jobs 4 | CI runs 4-way parallel |

## Summary

- P0 findings: 0
- P1 findings: 5 (2 missing guards for critical rules, 3 fragile guards)
- P2 findings: 1 (CWD dependency in AH)
- Items verified OK: 4

### Guard Quality Distribution
- ROBUST: 7 (Y, AB, AE, AJ, AM, AQ, NLP-bias) — 26%
- ADEQUATE: 15 — 56%
- FRAGILE: 5 (AC, AD, AF-pipeline, AH, AI, NLP-no-direct-write) — 19%
