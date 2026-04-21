# SPARKLE Aurora Stage 32 — CL SQAM Tail Closeout Preresearch Report

> Status: prerearch (input to dispatch plan)
> Scope: 4 remaining CL components, SQAM four-dimensional quality gates, guard automation, closeout criteria
> Date: 2026-04-21
> Fact-check: 10 code-level claims verified against source (9 TRUE, 1 PARTIAL)

---

## 0. Self-Review Audit Trail

Before presenting findings, the author (Claude Opus 4.6) performed a critical self-audit. The following issues were identified and corrected between the initial draft and this final version:

| Issue | Original Claim | Correction | Impact |
|-------|---------------|------------|--------|
| **DP1 ε overestimated** | Recommended Laplace ε=1.0 | Revised to ε=0.3. Educational AI is EU AI Act high-risk; ε=1.0 is too permissive. | All DP1 noise recommendations revised |
| **PSI sparse-data limitation unmentioned** | Recommended PSI > 0.25 threshold without caveat | Added: PSI unreliable with <30 samples; KS test or binomial proportion preferred for Sparkle's sparse data | Drift detection recommendations reordered |
| **JITAI auto-recovery generalized to SRL** | Implied no CL component has auto-recovery | SRL kill switch already has `record_misjudgment_rate()` with lag-streak auto-downgrade AND auto-reset. Only JITAI lacks recovery. | ST1 recommendations differentiated per component |
| **Existing kill switch infrastructure underweighted** | Proposed new SQAM monitoring mechanisms | Both Stage 27 (`AuroraStage27ForesightKillSwitchService`) and Stage 29 (`AuroraStage29SRLKillSwitchService`) have off/shadow/live modes with auto-downgrade. SQAM must leverage these, not reinvent. | Runtime monitoring strategy revised to build on existing kill switches |
| **EU AI Act emotional inference ban not highlighted** | Mentioned only in recommended reading | EU AI Act explicitly **bans** emotional inference in educational contexts. PersDyn's `mood_valence` dimension is a direct compliance risk. | New §0.1 compliance flag added |
| **Guard count overcounted** | Proposed 16 guards (4 × 4) | Some dimensions already guarded by existing mechanisms (kill switch, Prometheus metrics). Actual new guards needed: 11, not 16. | Guard design reduced |
| **Stage 31 dependency direction** | Said Stage 31 "not blocking Stage 32" | Roadmap v2.1 §5 shows `Stage 31 complete → Stage 32`. Stage 32 cannot close until Stage 31 finishes. | Closeout criteria revised |
| **SRL evidence_id bypass risk** | Stated "evidence_ids contain only trigger_event_type:timestamp" | Fact-check showed PARTIAL: default is safe, but external events can inject arbitrary `evidence_id`. API doesn't enforce format. | DP1 flag added |

### §0.1 EU AI Act Compliance Flag (Critical)

EU AI Act classifies educational AI as **high-risk** (Annex III §3(a)). Two provisions directly impact SQAM design:

1. **Emotional inference ban**: The Act **prohibits** inferring emotions in educational settings. PersDyn's `mood_valence` dimension (`persdyn_attractor_service.py` L80-87) maps reflection categories to a 0.1–0.4 valence scale. While this is derived from self-reported reflection tags (not raw emotion detection), the downstream use must be audited to ensure `mood_valence` never becomes a **sole decision factor** for any intervention or routing.

2. **Human oversight requirement**: High-risk AI must allow effective human oversight during operation. All 4 CL components already support kill switches (off/shadow/live), partially satisfying this. SQAM must verify kill switches are documented and accessible to operators.

---

## 1. SQAM Four-Dimensional Standards — Component Specifications

### 1.1 PersDyn Attractor Service

File: `backend/app/services/persdyn_attractor_service.py` (464 lines)
Learning mechanism: EMA (α=0.1) over 14-day windows, 5 dimensions × 3 parameters
Kill switch: `AuroraStage27ForesightKillSwitchService` (off/shadow/live, per-feature)

#### ID1 — Input Distribution Drift

**What to detect**: Shift in the distribution of 5-dimensional daily observation vectors over time.

**Code gap verified**: `_build_observation_for_day()` (L284-340) produces raw values with no distribution tracking. `study_pace` (L329) has no upper bound — confirmed by fact-check: `(300/60.0)/3.0 = 1.67` for 5 hours of study in 3-day window. No `clamp(value, 0.0, 1.0)`.

**Recommended method**: **Sliding-window KS test** (window=7 days, compare first half vs second half). Rationale: Sparkle's data is sparse (user may have <14 active days in 28-day lookback). KS test works with n≥10; PSI requires n≥30 for reliability. MMD is unstable below n=30.

**Threshold**: KS statistic > 0.4 triggers shadow mode via existing kill switch.

**Operational guard**: AST-level — verify `_build_observation_for_day` return dict has `min(max(..., 0.0), 1.0)` for all 5 dimensions. This also fixes the `study_pace` overflow.

#### ST1 — Stability

**What to detect**: EMA baseline drifting too rapidly or oscillating.

**Code gap verified**: `_ema()` (L391-397) has no `math.isfinite()` check. If any value in the 14-day series is NaN/Inf, the entire EMA cascade corrupts. Confirmed: no finiteness guard anywhere in the file.

**Recommended method**: Track |Δbaseline/day| across consecutive `recompute_user_attractors` calls. If 3 consecutive days show |Δbaseline| > 2 × variability, flag as unstable. Additionally: add `math.isfinite()` gate in `_ema()`.

**Threshold**: |Δbaseline/day| > 2σ for 3 consecutive days → alert. Not auto-downgrade (EMA is inherently smooth).

**Operational guard**: Structure-level — verify `_ema` body contains `isfinite` or equivalent check.

#### DP1 — Data Privacy

**What to detect**: Aggregate outputs enabling user re-identification.

**Code verified (PASS)**: EventBus payload (L435-445) publishes only `dimensions` (list of dimension names), not values. No raw content in output. `_extract_reflection_category()` (L448-452) extracts category tag, not reflection body text.

**Remaining gap**: `active_days` count (L342-358) is exact. In small cohorts (e.g., 3 users started same day), knowing active_days could narrow identity. Add Laplace noise: `reported_active_days = active_days + Laplace(0, 1/ε)` with ε=0.3.

**Operational guard**: Token-level — verify EventBus publish payload does not contain `baseline`, `variability`, `recovery_rate`, or `confidence` keys.

#### SM1 — Safety Margin

**What to detect**: Attractor outputs leaving safe range or being used as sole decision factors.

**Code gap verified**: `_confidence()` (L382-389) caps at 0.95 — correct. But no minimum output quality gate: if `active_days < HISTORY_DAYS (14)`, confidence is ≤0.29, yet `get_snapshot_attractors()` still returns these values unless caller explicitly passes `include_low_confidence=False`. Default path (L110-115) filters by `AURORA_FORESIGHT_ATTRACTOR_MIN_CONFIDENCE` (0.3) — adequate but should be an explicit SQAM assertion.

**Additional SM1 concern**: Per EU AI Act emotional inference ban, `mood_valence` must not be a sole decision factor. Guard: verify no code path branches solely on `mood_valence` without at least one other dimension.

**Operational guard**: AST-level — verify `_build_observation_for_day` output values are clamped to [0.0, 1.0].

---

### 1.2 JITAI Trigger Service

File: `backend/app/services/jitai_trigger_service.py` (321 lines)
Learning mechanism: Budget counter + cooldown + misfire rate monitoring
Kill switch: `AuroraStage27ForesightKillSwitchService` (shared with PersDyn/Predictive)

#### ID1 — Input Distribution Drift

**What to detect**: Shift in triggering conditions (z-score distribution, confidence distribution, dimension frequency).

**Code gap verified**: L101 `abs(float(deviation.z_score))` — no `math.isfinite()` check. If `deviation.z_score` is NaN, `abs(NaN)` is NaN, and NaN < 1.5 is False, so the check passes incorrectly. Confirmed: no finiteness guard.

**Recommended method**: **Binomial proportion test** on daily trigger/no-trigger ratio per dimension. For 7-day windows, if trigger rate shifts >50% from 14-day baseline, flag.

**Threshold**: Trigger rate ratio (7d/14d baseline) outside [0.5, 2.0] → alert.

**Operational guard**: AST-level — verify z_score check includes `math.isfinite()`.

#### ST1 — Stability

**What to detect**: Trigger accuracy degradation (misfire rate drift).

**Code verified (existing mechanism)**: `_evaluate_auto_downgrade()` (L183-189) monitors 3-day rolling misfire rate. If all 3 days exceed 15%, auto-downgrades from live→shadow.

**Code gap verified**: No auto-recovery path. Once downgraded to shadow, system stays shadow until manual intervention. Confirmed: `grep` found no `set_feature_mode.*live` in the codebase. This is a deliberate safety design (one-way degradation), but SQAM should document the manual recovery requirement.

**Recommended addition**: Log downgrade events to `routing_decision_log` for audit trail. Recovery requires explicit operator action with documented justification.

**Operational guard**: Structure-level — verify `_evaluate_auto_downgrade` exists and records to decision log.

#### DP1 — Data Privacy

**What to detect**: Redis keys or event payloads leaking user identity.

**Code gap verified**: Redis keys use plaintext user_id: `jitai:budget:{user_id}:...` (L234-235), `jitai:cooldown:{user_id}:{dim}` (L238-239). Redis is internal infrastructure, but defense-in-depth requires hashing.

**Recommended fix**: Hash user_id in keys: `jitai:budget:{sha256(user_id)[:16]}:...`. This is a code change, not just a guard.

**EventBus payload verified (PASS)**: L169-180 publishes `user_id`, `dim`, `hint_id`, `template_id`, `generated_at`. No raw behavioral data. Template messages (L33-74) are static strings, not user-derived.

**Operational guard**: Token-level — verify Redis key construction methods contain `sha256` or `hashlib`.

#### SM1 — Safety Margin

**What to detect**: Intervention burden exceeding safe limits.

**Code verified (existing mechanism)**: Daily budget ≤ 3 (L114), per-dimension cooldown 24h (L111-113, L214), template-only messages (L33-74, no dynamic content). This is a strong SM1 framework already.

**Recommended addition**: Cross-user burden aggregation — if >30% of users exhaust daily budget on the same day, system-level alert. This detects over-triggering due to model drift.

**Operational guard**: Structure-level — verify `AURORA_FORESIGHT_JITAI_DAILY_BUDGET` is referenced in budget check, and `COOLDOWN_HOURS` in cooldown check.

---

### 1.3 Predictive Service (Foresight Engine)

File: `backend/app/services/predictive_service.py` (~1800 lines)
Learning mechanism: LLM-based prediction + rule-based fallback + analytics feedback loop
Kill switch: `AuroraStage27ForesightKillSwitchService`

#### ID1 — Input Distribution Drift

**What to detect**: Shift in prediction input signals or CTR as proxy for input quality.

**Code verified (existing mechanism)**: `get_prediction_analytics()` (L1608-1747) already tracks CTR, execution rate, and impression-to-execution funnel across multiple dimensions (surface, horizon, source, action_type).

**Code gap verified**: No drift detection logic consuming the analytics. Data is computed but not compared against baseline.

**Recommended method**: **Page-Hinkley test** on daily CTR. Page-Hinkley is sensitive to gradual drift (appropriate for LLM quality degradation) and works well with streaming data. 5-day sliding window.

**Threshold**: CTR drops >20% from 14-day baseline → shadow mode. Fallback rate (FREE→FAST tier transitions) >30% → alert.

**Operational guard**: Structure-level — verify `get_prediction_analytics` exists and returns CTR fields.

#### ST1 — Stability

**What to detect**: Prediction accuracy degradation over time.

**Code verified (existing mechanism)**: Three-tier fallback (L1330-1367: FREE → FREE_FAST → FAST), confidence cap at 0.95 (L1273), timeout enforcement (L125-127).

**Code gap verified**: No baseline persistence. Analytics are computed on-the-fly with no historical comparison. Need: write daily CTR baseline to `routing_decision_log`.

**Recommended method**: Track daily `execution_rate_percent` against 14-day rolling baseline. Degradation >10pp triggers alert.

**Operational guard**: Structure-level — verify confidence cap ≤ 0.95 exists.

#### DP1 — Data Privacy

**What to detect**: LLM payload leaking PII; analytics exposing exact counts.

**Code gap verified (CRITICAL)**: `_build_realtime_llm_messages()` (L1280-1310) sends `partial_text[:180]` directly to external LLM with **no PII redaction**. If user types a phone number, email, or real name in chat, it reaches the LLM provider. Fact-check confirmed: no PII stripping before payload construction.

**Code gap verified (MODERATE)**: `_finalize()` (L1695-1710) in analytics outputs exact impression/accept/execution counts via `**bucket`. No differential privacy noise. For single-user analytics this is acceptable (user sees own data), but if analytics are ever aggregated across users or logged, exact counts enable re-identification in small cohorts.

**Recommended fixes**:
1. Add PII redaction function (regex for phone, email, ID numbers) before `partial_text[:180]` enters LLM payload.
2. Add Laplace noise (ε=0.3) to cross-user analytics aggregates only. Single-user analytics can remain exact.

**Operational guard**: AST-level — verify `_build_realtime_llm_messages` calls a redaction function on `partial_text`.

#### SM1 — Safety Margin

**What to detect**: Prediction outputs suggesting harmful or high-risk actions.

**Code verified (existing mechanism)**: `action_type` route mapping (L1596-1606) is a fixed whitelist of 8 action types. Unknown types default to `/chat`. Confidence cap at 0.95. `risk_level` field exists on `EngagementForecast` (L74).

**Code gap verified**: `risk_level` is set but never consumed — no code path checks risk_level before triggering downstream actions (JITAI, notifications).

**Recommended fix**: When `EngagementForecast.risk_level == "high"`, suppress JITAI triggering for that user. This connects existing risk_level to existing JITAI budget.

**Operational guard**: Token-level — verify `risk_level` is referenced in JITAI or foresight generation path.

---

### 1.4 SRL Phase Tracker

File: `backend/app/services/srl_phase_tracker_service.py` (448 lines)
Learning mechanism: 36-rule transition matrix + evidence chain + cold-start traits
Kill switch: `AuroraStage29SRLKillSwitchService` (off/shadow/live, with auto-downgrade)

#### ID1 — Input Distribution Drift

**What to detect**: Shift in event type distribution consumed by the tracker.

**Code verified**: `SRL_EVENT_CONSUMED_TOTAL` Prometheus counter (L127-138) tracks per-trigger-event-type counts with status labels (ignored/rejected/applied). Existing metric infrastructure.

**Recommended method**: **Chi-squared test** on weekly event_type distribution. If single trigger type exceeds 80% for 7 consecutive days, flag as distribution collapse (transition rules not exercising full range).

**Threshold**: Single trigger >80% for 7 days → alert (not downgrade — tracker may be correctly reflecting user behavior).

**Operational guard**: Structure-level — verify `SRL_EVENT_CONSUMED_TOTAL` counter exists with `trigger_event_type` label.

#### ST1 — Stability

**What to detect**: Phase misclassification rate and rapid oscillation.

**Code verified (existing mechanism — STRONG)**: `AuroraStage29SRLKillSwitchService` already has:
- `record_event_lag_p95()` (L76-114): Auto-downgrade bridge+scaffolding to shadow if P95 lag exceeds threshold for 3 consecutive checks within 3 minutes. Auto-resets when lag recovers.
- `record_misjudgment_rate()` (L116-148): Auto-downgrade bridge+scaffolding to shadow if misjudgment exceeds threshold for 3 consecutive days. Auto-resets when rate recovers.

This is the most mature auto-downgrade pattern in the codebase — superior to JITAI's one-way degradation. SQAM should reference this as the gold standard.

**Code gap verified**: No oscillation detection. 36-rule transition matrix allows FORETHOUGHT→PERFORMANCE→FORETHOUGHT cycling. If user oscillates >4 transitions in 24h, confidence should degrade.

**Recommended addition**: Track hourly transition count per user. If >4 transitions in any 24h window, set confidence to min(current, 0.3) for next 24h.

**Operational guard**: AST-level — verify `_transition_state` or `handle_transition_event` references a transition rate check.

#### DP1 — Data Privacy

**What to detect**: Evidence chain leaking user content.

**Code verified (PARTIAL)**: Default evidence_id format at L115 is `f"{trigger_event_type}:{timestamp}"` — safe, no free text. BUT: external events can inject arbitrary `evidence_id` via the event payload, and the API doesn't enforce the safe format. L335-336 appends `plan:{metadata['plan_id']}` — plan IDs are UUIDs, safe.

**Recommended fix**: Validate `evidence_id` format on ingestion (regex: `^[a-z_.]+:[\dT:.+-]+$` or UUID pattern). Reject free-form text.

**Redis keys**: Cache keys use `aurora:stage29:srl:state:{user_id}` (L446-447) — plaintext UUID. Same hashing recommendation as JITAI.

**Operational guard**: AST-level — verify evidence_id validation regex exists in `handle_transition_event`.

#### SM1 — Safety Margin

**What to detect**: Phase labels causing negative psychological impact.

**Code verified (PASS)**: `SRLPhase` enum values (FORETHOUGHT, PERFORMANCE, SELF_REFLECTION, UNKNOWN) are standard SRL academic terms, not diagnostic labels. Rule AM (no diagnostic terms in metacognition output) covers this territory. No user-facing UI surfaces phase labels directly.

**Additional SM1 concern**: `force_reset()` (L169-198) sets confidence=1.0 unconditionally. If an admin miscategorizes a user's phase, the user receives highest-confidence wrong phase. Recommend: force_reset caps confidence at 0.8, requires justification string.

**Operational guard**: Token-level — verify `SRLPhase` enum values do not include diagnostic terms (ADHD, depression, anxiety, etc.). Already true; guard prevents regression.

---

## 2. Automated Guard Design

### 2.1 Guard Inventory (Revised: 11 guards, not 16)

Five dimensions are already adequately covered by existing mechanisms and don't need new guards:

| Component | Dimension | Already Covered By | New Guard Needed? |
|-----------|-----------|-------------------|-------------------|
| PersDyn | SM1 confidence cap | `_confidence()` caps at 0.95 | No |
| JITAI | SM1 budget+cooldown | L114 budget, L111 cooldown | No |
| JITAI | ST1 misfire downgrade | `_evaluate_auto_downgrade()` | No |
| SRL | ST1 lag/misjudgment | Kill switch auto-downgrade | No |
| SRL | SM1 no diagnostic labels | Rule AM guard exists | No |

**New guards needed (11):**

```
scripts/stage32/
├── check_sqam_persdyn_id1.py       # AST: observation values clamped to [0,1]
├── check_sqam_persdyn_st1.py       # AST: _ema contains isfinite check
├── check_sqam_persdyn_dp1.py       # Token: event payload excludes value keys
├── check_sqam_persdyn_sm1_mood.py  # AST: mood_valence not sole branch condition
├── check_sqam_jitai_id1.py         # AST: z_score has isfinite guard
├── check_sqam_jitai_dp1.py         # Token: Redis keys use hashed user_id
├── check_sqam_predictive_id1.py    # Structure: analytics returns CTR fields
├── check_sqam_predictive_st1.py    # Structure: confidence cap ≤ 0.95
├── check_sqam_predictive_dp1.py    # AST: LLM messages call PII redaction
├── check_sqam_predictive_sm1.py    # Token: risk_level consumed in JITAI path
└── check_sqam_srl_dp1.py           # AST: evidence_id format validation exists
```

### 2.2 Guard Implementation Pattern

Follow existing codebase conventions (confirmed by reading 11 `scripts/check_rule_*.py` files):

**Pattern A — AST static scan** (for structural requirements):
```python
# Uses ast_guard_utils.parse_module() and call_name()
# Example: check_rule_ae_conflict_audit.py
def check_sqam_persdyn_st1(path: Path) -> list[str]:
    tree = parse_module(path)
    ema_fn = next(
        (n for n in ast.walk(tree)
         if isinstance(n, ast.FunctionDef) and n.name == "_ema"),
        None,
    )
    if ema_fn is None:
        return ["SQAM-PD-ST1: _ema function not found"]
    has_isfinite = any(
        isinstance(n, ast.Call) and "isfinite" in (call_name(n) or "")
        for n in ast.walk(ema_fn)
    )
    if not has_isfinite:
        return ["SQAM-PD-ST1: _ema missing isfinite guard"]
    return []
```

**Pattern B — Token/text scan** (for forbidden patterns):
```python
# Example: check_rule_al_foresight_not_router.py
FORBIDDEN_VALUE_KEYS = {"baseline", "variability", "recovery_rate", "confidence"}
# Scan event_bus.publish calls for value leakage
```

**Pattern C — Structure assertion** (for existence checks):
```python
# Example: check_srl_user_isolation.py
REQUIRED_SNIPPETS = (
    'math.isfinite',
    'clamp',
)
```

### 2.3 CI Integration

Add to `.github/workflows/ci.yml` in the `lint` job:
```yaml
- name: Stage 32 SQAM Guards
  run: |
    for script in scripts/stage32/check_sqam_*.py; do
      python "$script" || exit 1
    done
```

### 2.4 Runtime Monitoring (Prometheus Alerts)

SQAM runtime monitoring builds on **existing** Prometheus metrics, not new instrumentation:

| Alert | Source Metric | Condition | Severity |
|-------|--------------|-----------|----------|
| `SQAMPersDynDrift` | `sparkle_persdyn_attractor_updated_total` | Any dim update rate drops >50% over 7d | P3 |
| `SQAMJITAITriggerCollapse` | `sparkle_jitai_triggered_total` | Single dim >80% of triggers for 7d | P3 |
| `SQAMJITAIBurdenHigh` | `sparkle_jitai_skipped_total{reason="budget"}` | >30% users budget-exhausted same day | P2 |
| `SQAMPredictiveCTRDrop` | Computed from `CandidateActionFeedback` | CTR drops >20% over 5d | P2 |
| `SQAMSRLUnknownRate` | `sparkle_srl_phase_unknown_rate` | >0.4 for 3 consecutive days | P3 |
| `SQAMSRLOscillation` | `sparkle_srl_phase_transition_total` | >4 transitions/user/24h | P2 |

---

## 3. Distribution Shift Detection Recommendations

### Component-Specific Method Selection

| Component | Recommended Method | Rationale | Min Sample Size |
|-----------|-------------------|-----------|-----------------|
| **PersDyn** | Sliding-window KS test (7d) | 5D continuous values; KS works with n≥10; PSI needs n≥30 which Sparkle can't guarantee | 10 daily observations |
| **JITAI** | Binomial proportion test | Trigger/no-trigger is binary; more appropriate than KS for discrete decisions | 30 trigger events |
| **Predictive** | Page-Hinkley on CTR | LLM quality drift is gradual; PH is sensitive to slow mean shifts in streaming data | Daily CTR measurement |
| **SRL** | Chi-squared on event_type distribution | Event types are categorical; χ² is the standard test for categorical distribution shifts | 5+ events per type |

### Why Not Other Methods

- **MMD (Maximum Mean Discrepancy)**: Requires n≥30 for stability. Sparkle users may have <14 active days. Rejected.
- **ADWIN**: Good for concept drift but computationally heavier than needed for Sparkle's low-frequency updates (daily, not streaming). Deferred.
- **DDM (Drift Detection Method)**: Designed for classification error monitoring. Sparkle's CL components are not classifiers. Rejected.
- **PSI**: Industry standard for model monitoring, but requires n≥30 for reliable estimation. Use as secondary metric when data volume supports it.

---

## 4. Privacy Audit Checklist

### Per-Component DP1 Checkpoints

| Component | Checkpoint | Code Location | Status | Fix |
|-----------|-----------|---------------|--------|-----|
| PersDyn | EventBus payload excludes values | L435-445 | PASS (verified) | None |
| PersDyn | active_days gets DP noise | L342-358 | GAP | Add Laplace(0, 1/0.3) noise |
| PersDyn | `mood_valence` not sole decision factor | L338 | GAP (no guard) | AST guard for EU AI Act |
| JITAI | Redis keys hash user_id | L234-239 | GAP (plaintext) | sha256(user_id)[:16] |
| JITAI | EventBus payload excludes raw data | L169-180 | PASS (verified) | None |
| JITAI | Misfire rate不含用户级明细 | L143-149 | PASS (aggregate) | None |
| Predictive | LLM payload has PII redaction | L1280-1310 | GAP (critical) | Add regex redaction |
| Predictive | Analytics counts get DP noise (cross-user only) | L1695-1710 | GAP (exact counts) | Laplace(0, 1/0.3) on aggregates |
| SRL | evidence_id format enforced | L115 | PARTIAL (default safe, bypassable) | Add format validation |
| SRL | Redis keys hash user_id | L446-447 | GAP (plaintext) | sha256(user_id)[:16] |
| SRL | force_reset caps confidence | L169-198 | GAP (hardcoded 1.0) | Cap at 0.8 |

### Rule Z (Cross-User Privacy) Coordination

| Component | Cross-User Risk | Mitigation |
|-----------|----------------|------------|
| PersDyn | `recompute_all_users()` (L151-176) iterates all users | Confirm admin-only access; no single-user results exposed |
| JITAI | Consumer group isolation | `sparkle_events` stream has separate consumer groups per service — no cross-leak |
| Predictive | Cache keys per-user with TTL | No aggregation endpoint exposed to non-admin — PASS |
| SRL | Distributed lock per-user | Redis lock scope is `{user_id}` — no cross-user state — PASS |

---

## 5. Closeout Criteria

### Aurora CL Quality Track Official Closeout Conditions

All 6 conditions must be met:

1. **11/11 SQAM guard scripts PASS** in CI (continuous, not one-time)
2. **6 Prometheus alert rules deployed** to AlertManager with 14-day no-trigger baseline
3. **All 4 components run in shadow mode ≥7 days** with no auto-downgrade events
4. **Privacy audit PASS**: DP1 gaps fixed (PII redaction, Redis hashing, evidence_id validation)
5. **Grafana SQAM dashboard operational** with panels for each component's ID1/ST1/DP1/SM1 metrics
6. **Closeout document signed**: `docs/product/SPARKLE_AURORA_CL_SQAM_CLOSEOUT_2026-04-XX.md`

### Signoff Checklist

```
□ scripts/stage32/check_sqam_*.py (11 files) all PASS in CI
□ .github/workflows/ci.yml includes stage32 guard step
□ 6 Prometheus alert rules deployed and firing to correct channels
□ Grafana SQAM dashboard URL accessible and showing data
□ JITAI + SRL Redis key hashing implemented
□ Predictive LLM payload PII redaction implemented
□ SRL evidence_id format validation implemented
□ PersDyn mood_valence sole-factor guard implemented
□ Shadow mode 7-day run with no auto-downgrade events
□ Privacy audit report completed and signed
□ Stage 31 (Idiographic Lite) complete or explicitly deferred with §8 future obligation
□ Closeout document completed with architect sign-off
```

### Stage 31 Dependency

Per roadmap v2.1 §5: `Stage 31 complete → Stage 32`. The closeout document must either:
- Include Stage 31's Idiographic Lite SQAM results (if Stage 31 completes first), OR
- Include §8 "Future SQAM Obligations" declaring Idiographic Lite requires independent DP1/SM1 verification under Rule AN (cross-user association ban)

---

## 6. Recommended Reading

| # | Title | Author/Org | Year | Key Finding for SQAM |
|---|-------|-----------|------|---------------------|
| 1 | Just-in-Time Adaptive Interventions (JITAIs) in Mobile Health | Nahum-Shani et al. / PMC | 2018 | Five-component JITAI framework (Decision Points, Tailoring Variables, Decision Rules, Intervention Options, Proximal Outcomes) — theoretical basis for JITAI SQAM |
| 2 | Continual Learning and Catastrophic Forgetting | van de Ven / arXiv:2403.05175 | 2024 | BWT (Backward Transfer) metric for detecting knowledge loss — reference for PersDyn/Predictive ST1 |
| 3 | The Algorithmic Foundations of Differential Privacy | Dwork & Roth / Foundations and Trends | 2014 | Laplace mechanism, ε-differential privacy — direct basis for DP1 noise design |
| 4 | EU AI Act Annex III §3(a): Education and Vocational Training | European Parliament | 2024 | Educational AI = high-risk; emotional inference ban; human oversight requirement — compliance framework for all 4 components |
| 5 | A Survey on Concept Drift Adaptation | Gama et al. / ACM Computing Surveys | 2014 | Drift detection taxonomy (sudden/gradual/incremental/recurring); ADWIN/Page-Hinkley/DDM selection criteria |
| 6 | Intervention Optimization: A Paradigm Shift and Its Potential | Nahum-Shani et al. / PMC | 2024 | MOST framework for optimizing multi-component interventions — JITAI budget control theoretical basis |
| 7 | Differential Privacy in Continual Learning: Which Labels to Update? | arXiv:2411.04680 | 2024 | Tension between CL knowledge retention and DP constraints; User-Entity DP (UeDP) — advanced DP1 reference |
| 8 | ISO/IEC 25059: AI Quality Evaluation Framework | ISO/IEC | 2025 | AI-specific quality characteristics including learning capability — external benchmark for SQAM framework |

---

## 7. Stage 30-31 Interface

### Stage 30 (Metacognition Extension)

Extends existing `ScaffoldingFSM` calibration tracking to three-axis bias surface. **Not a new independent CL component** — it modifies an existing Stage 29 component.

**SQAM approach**: Extend Stage 29 SRL guards with additional Rule AM check (no diagnostic terms in metacognition output). No independent SQAM needed.

### Stage 31 (Idiographic Lite)

Discovers user-specific behavioral associations (not causal claims). This **is** a new CL component with significant privacy implications.

**SQAM approach**: Requires independent SQAM with special emphasis on:
- **DP1**: Rule AN (no cross-user association) is the strictest privacy constraint in Aurora. Idiographic patterns must never leak between users.
- **SM1**: Associations must be presented as "we noticed X tends to coincide with Y for you" (correlation), never "X causes Y" (causation).

**Recommendation**: Stage 32 implements the SQAM framework and closes out the 4 current components. Stage 31 delivers Idiographic Lite and runs its own SQAM (2 additional guards: `check_sqam_idiographic_dp1.py` and `check_sqam_idiographic_sm1.py`). **Aurora CL quality track closes after Stage 31's SQAM passes.**

The `scripts/stage32/` directory naming convention (`check_sqam_{component}_{dim}.py`) is designed to accommodate these additions without restructuring.

---

*Report version: 2.0 (post self-audit)*
*Total code assertions fact-checked: 10 (9 TRUE, 1 PARTIAL)*
*Guard scripts: 11 new (5 dimensions covered by existing mechanisms)*
*Runtime alerts: 6 (all building on existing Prometheus metrics)*
