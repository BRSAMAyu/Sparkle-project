# Aurora Kernel & Governance Audit

**Auditor**: Agent (Opus)
**Date**: 2026-05-07
**Status**: PASS WITH ISSUES

## Summary

The Aurora Adaptive Kernel and Governance system is architecturally sound. The tri-state kill switch protocol is properly implemented across 22 dedicated kill switch service files, all importing the shared `app.core.kill_switch` helper. The rule guard manifest contains 67 unique rules with valid, existing script references. Docker-compose files are perfectly synchronized (68/68 AURORA switches match between `docker-compose.yml` and `docker-compose.prod.yml`). Drill scripts cover stages 18-35, 37-40 via a consolidated `stage40/run_kill_switch_drills.py` harness. PII redaction, Laplace noise differential privacy, and data retention (90-day) are enforced. Several medium-severity gaps were found around missing docker-compose exposure for newer settings and one stale empty file.

## Critical Issues (P0)

None found.

## High Issues (P1)

### P1-01: 20 Aurora mode settings not exposed in docker-compose

**Files**:
- `docker-compose.yml` (lines 130-161)
- `docker-compose.prod.yml` (lines 213-244)
- `backend/app/config/settings.py`

**Finding**: Settings.py defines 53 Aurora mode settings, but docker-compose only exposes 33 of them via environment variable passthrough. The 20 missing settings include critical ones:

- `AURORA_STAGE40_CALENDAR_MODE` (newest stage, default "live")
- `AURORA_STAGE37_LLM_SAFETY_MODE` (security feature, default "live")
- `AURORA_STAGE39_MODE` + 3 sub-modes (default "live")
- `AURORA_DUAL_CORE_ROUTER_MODE` (core routing, default "live")
- `AURORA_PRIVACY_PII_REDACTION_MODE` (PII redaction, default "live")

**Impact**: In production, ops cannot override these settings via environment variables without rebuilding. All default to "live" so this is not a safety risk, but it violates the kill switch protocol's operational requirement that every feature be controllable at deployment time.

**Recommendation**: Add the missing 20 settings to both docker-compose files following the existing `AURORA_*=${AURORA_*:-live}` pattern.

### P1-02: Stage 36 referenced in docs but has no implementation

**Files**:
- `docs/aurora/rule_aw_rate_limiter_sanity.md` (line 13)
- `docs/aurora/rule_au_exceptions.md` (line 10)
- `docs/aurora/stage35_backend_only_fields.md` (line 14)

**Finding**: Multiple Aurora governance docs reference "Stage 36" as a milestone, but there is no `scripts/stage36/` directory, no `aurora_stage36_kill_switch_service.py`, and no Stage 36 drill script. The stage appears to have been absorbed into later stages (37-40) but documentation was not updated.

**Impact**: Documentation inconsistency could confuse future contributors. No runtime impact since the functionality shipped in later stages.

**Recommendation**: Update docs to reflect that Stage 36 was folded into Stages 37-40, or add a `docs/aurora/stage36_merge_note.md` explaining the consolidation.

## Medium Issues (P2)

### P2-01: FME L3 closure bridge bypasses kill switch

**File**: `backend/app/services/fme_l3_closure_bridge.py` (lines 38-93)

**Finding**: The `apply_l3_closure_to_spine()` function does not check the FME kill switch before propagating L3 session closure data (state patches, policy changes) through the Spine. The FME kill switch (`FmeKillSwitchService`) controls `goal_first_minute` and `task_card_protocol_v2`, but L3 closures from `AuroraCoreSession` are not gated.

**Impact**: If FME is set to "off", L3 closures could still modify spine state. Low practical risk since L3 sessions are rare and require explicit user initiation, but it breaks the kill switch completeness invariant.

### P2-02: SpineOrchestrator has no direct kill switch integration

**File**: `backend/app/signals/spine_orchestrator.py` (4896 lines)

**Finding**: The `SpineOrchestrator` class does not import or check any kill switch directly. Kill switch gating happens in the individual services it calls (state aggregator, SRL tracker, etc.), not at the orchestrator level. This is a design choice, not a bug, but means there is no single "spine off" switch.

**Impact**: If someone adds a new signal path to `SpineOrchestrator` without delegating to a kill-switch-gated service, it would bypass the governance protocol.

**Recommendation**: Consider adding a top-level spine kill switch check as a defensive wrapper, or document the design decision that kill switch gating is enforced at the service layer, not the orchestrator layer.

### P2-03: Empty markdown file in signals directory

**File**: `backend/app/signals/Sparkle 项目全面问题与改进清单.md` (0 bytes)

**Finding**: An empty Chinese-named markdown file exists in the signals directory. This is a stray file that should not be in the Python package.

**Recommendation**: Delete the file and ensure `.gitignore` covers `*.md` in `backend/app/signals/` (excluding legitimate docs).

### P2-04: .DS_Store files tracked in source directories

**Files**:
- `backend/app/aurora/.DS_Store`
- `scripts/.DS_Store`

**Finding**: macOS `.DS_Store` files are present in two source directories. These should be in `.gitignore`.

**Recommendation**: Add `.DS_Store` to the root `.gitignore` if not already present, and remove the tracked files.

### P2-05: Data retention only enforced on `AuroraDecisionTelemetry` model

**File**: `backend/app/aurora/runtime_v1/telemetry.py` (lines 25, 775-777)

**Finding**: The 90-day retention policy (`RETENTION_DAYS = 90`) is only enforced for `AuroraDecisionTelemetry` records. Other Aurora data stores (Redis keys in `SpineAuroraBridge`, directive store, outcome tracker) use TTLs but there is no unified retention enforcement for all Aurora-related persistent data.

**Impact**: Over time, Redis keys and other stores may accumulate stale data beyond the intended retention window.

## Low Issues (P3)

### P3-01: Rule guard manifest count discrepancy

**Files**:
- `scripts/rule_guard_manifest.tsv`

**Finding**: CLAUDE.md states "62/62 governance rules passing" (Phase 2 report) and "53+ governance rules" (Aurora section). The manifest currently contains 67 rules. The numbers are consistent with growth (53 -> 62 -> 67) but CLAUDE.md's Aurora section text is stale.

**Recommendation**: Update CLAUDE.md to reflect current count (67 rules).

### P3-02: `AuroraConfig.mode` returns "disabled"/"shadow"/"active" instead of tri-state values

**File**: `backend/app/aurora/config.py` (lines 29-33)

**Finding**: `AuroraRuntimeConfig.mode` returns "active" instead of "live" and "disabled" instead of "off". This is a separate config system from the kill switch tri-state (off/shadow/live). While not a bug, it creates two parallel mode representations that could confuse developers.

**Recommendation**: Document the distinction between `AuroraRuntimeConfig.mode` (Wave 1a feature flag) and kill switch tri-state (per-stage operational control).

### P3-03: Some Celery tasks lack explicit queue assignment

**File**: `backend/app/core/celery_tasks.py` (74 task definitions)

**Finding**: Most of the 74 Celery tasks do not specify an explicit queue, relying on the default queue. High-priority tasks (like `health_check_task`) and low-priority tasks (like `run_research_improvement_loop`) compete for the same worker pool.

**Recommendation**: Consider routing long-running analytics tasks to a dedicated low-priority queue.

### P3-04: Deprecated exports in signals `__init__.py`

**File**: `backend/app/signals/__init__.py` (lines 100-104)

**Finding**: Four deprecated aliases are exported (`DomainPack_v1`, `DomainPackMarketplace_v1`, `SimulatedUserProfile_v1`, `UserSimulator_v1`). These are properly marked with DEPRECATED comments and type hints pointing to replacements, which is correct practice.

## Positive Findings

1. **Kill switch architecture is exemplary**: All 22 kill switch service files follow the same pattern, import the shared `KillSwitchBinding`/`read_mode`/`write_mode` from `app.core.kill_switch`, and record Prometheus gauges. The `record_gauge=True` default on `read_mode()` ensures no gauge is silently missed.

2. **Rule guard infrastructure is robust**: The `run_all_rule_guards.sh` supports parallel execution (`--jobs N`), per-rule filtering (`--rule AB`), listing mode, and proper temp-file based output collection. The 67 rule guard scripts use a mix of AST-level verification (e.g., `check_rule_be_shadow_semantics.py`), regex scanning (e.g., `check_rule_bi_hardcoded_secrets.py`), and dynamic discovery (e.g., `check_rule_av_kill_switch_mode_enum.py`).

3. **Docker-compose parity is perfect**: All 68 AURORA environment variables are identical between `docker-compose.yml` and `docker-compose.prod.yml` (verified with diff, zero differences).

4. **PII redaction is thorough**: `backend/app/aurora/privacy.py` covers email, phone, CN ID numbers, bank card numbers, and both Chinese and English names. It uses the kill switch protocol for mode control with fallback to "live".

5. **Differential privacy is properly implemented**: `laplace_noise()` in `privacy.py` validates epsilon > 0, sensitivity > 0, and finite values. The Laplace mechanism implementation is mathematically correct.

6. **Drill scripts are comprehensive**: The consolidated `stage40/run_kill_switch_drills.py` exercises all 22 kill switch services through the full transition cycle (`off -> shadow -> live -> shadow -> off`), validates that each mode key matches the expected value, and writes a JSONL audit trail.

7. **Policy version is frozen and validated**: `backend/app/aurora/policies/v1.0.yaml` is a complete, frozen Gate 0 policy fixture validated by `AuroraPolicyVersion` Pydantic model with conservative defaults.

8. **Data minimization governance is enforced at CI level**: `scripts/guards/check_data_minimization_coverage.py` dynamically discovers high-risk cross-user models via AST parsing and verifies they are registered in the minimization scope registry.

9. **Aurora schemas are properly frozen**: All schema models use `AuroraSchemaBase` with `frozen=True` and `extra="ignore"`, preventing accidental mutation.

10. **Comprehensive test coverage**: 28 test files in `backend/tests/aurora/` and 26 test files in `backend/tests/unit/spine/` cover the Aurora kernel, spine pipeline, kill switches, and governance rules.

## Files Audited

### Aurora Core (backend/app/aurora/)
- `__init__.py`
- `common.py`
- `config.py`
- `context.py`
- `core_session.py`
- `engine.py`
- `growth_signal_contract.py`
- `llm_bridge.py`
- `migration.py`
- `policy_loader.py`
- `predicted_reply_engine.py`
- `privacy.py`
- `profile_translator.py`
- `relationship_state.py`
- `signal_aggregator.py`
- `signal_processor.py`
- `tasks.py`
- `schemas/__init__.py`
- `schemas/enums.py`
- `schemas/primitives.py`
- `policies/v1.0.yaml`
- `policies/__init__.py`
- `bayesian/__init__.py`
- `decision_fns/__init__.py`
- `decision_fns/backbone.py`
- `decision_fns/escalation.py`
- `decision_fns/fallback.py`
- `decision_fns/materiality.py`
- `decision_fns/triggers.py`
- `observability/__init__.py`
- `observability/benchmark.py`
- `observability/metrics.py`
- `observability/tiering.py`
- `runtime_v1/` (25 files, including service.py, decision_loop.py, telemetry.py, models.py, etc.)

### Core Infrastructure
- `backend/app/core/kill_switch.py`
- `backend/app/core/celery_tasks.py` (3449 lines, 74 tasks)
- `backend/app/core/metrics.py` (1090 lines)
- `backend/app/core/data_minimization.py`

### Signal Processing (backend/app/signals/)
- `__init__.py` (329 lines)
- `spine_orchestrator.py` (4896 lines)
- `spine_aurora_bridge.py`
- `spine_quality_guard.py`
- `spine_metrics.py`
- `spine_quality_guard.py`
- `types.py` (58293 bytes)

### Configuration
- `backend/app/config/aurora.py`
- `backend/app/config/settings.py` (Aurora-related settings)

### Docker
- `docker-compose.yml`
- `docker-compose.prod.yml`

### Governance Scripts
- `scripts/run_all_rule_guards.sh`
- `scripts/rule_guard_manifest.tsv` (67 rules)
- `scripts/guards/` (23 guard scripts)
- `scripts/check_rule_*.py` (15 rule check scripts)
- `scripts/check_tech_debt_budget.py`
- `scripts/journey_smoke.sh`
- `scripts/stage*/drill_transitions.sh` (stages 18-40)
- `scripts/stage40/run_kill_switch_drills.py` (504 lines)
- `scripts/stage32/run_sqam_suite.sh`
- `scripts/production_readiness_check.sh`

### Kill Switch Services (22 files)
- `backend/app/services/aurora_stage18_kill_switch_service.py` through `aurora_stage40_calendar_kill_switch_service.py`
- `backend/app/services/fme_kill_switch_service.py`

### Quality
- `quality/tech_debt_budget.json`
