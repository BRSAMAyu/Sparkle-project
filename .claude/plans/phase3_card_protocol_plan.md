# Phase 3: Connect Parameters and Outcome Verification

**Timeline**: Days 51-70 | **Acceptance Gate A3**: Sparkle can distinguish between an intervention that sounded good and one that actually improved outcomes

---

## Design Analysis

### The Core Problem (Breakpoint 5)
`cognitive_adjustments` in DualCoreDecision are **free-form text strings** injected into LLM prompts. The AI may or may not follow them. There is no enforcement mechanism, no tracking, no learning loop.

### The Phase 3 Solution
Build a **Parameter Compiler** that:
1. Reads approved PlanningArtifacts (GLOBAL_COMPASS, STRATEGY_MAP)
2. Compiles them into concrete execution parameters (`PlanState.facts["adaptive_adjustments"]`)
3. Records each compilation as a Decision Log artifact
4. Tracks Risk Register entries for detected risks
5. Verifies outcomes against compiled parameters and feeds learning back

### Integration Flow
```
PlanningArtifact (GLOBAL_COMPASS + STRATEGY_MAP)
    ↓ ParameterCompiler.compile()
PlanState.facts["adaptive_adjustments"]
    ↓ PlanAdjustmentApplier.apply_incremental_changes()
Task entities (time, difficulty, concurrency)
    ↓ User executes tasks + TaskOccurrence feedback
InterventionOutcomeVerifier._check_improvement()
    ↓ Outcome → DecisionLog artifact → RiskRegister updates
Parameter learning feeds back into next compilation cycle
```

### Key Architectural Invariants (from Section 8.3)
1. AI must read approved artifacts before planning writes
2. AI cannot silently mutate the compass
3. Execution changes must be compiled from approved artifacts or deterministic system policies
4. Every artifact write must record input versions and assumptions
5. Writes based on stale artifacts are rejected

### Phase 1-2 Governance Exception Retirement
Phase 1-2 used `legacy PlanState + deterministic system policy` to authorize execution writebacks. Phase 3 replaces this with full artifact governance:
- GLOBAL_COMPASS becomes the authoritative source for user parameters
- STRATEGY_MAP becomes the authoritative source for execution strategy
- ACTIVE_PHASE_PACK is compiled from these two, not from ad-hoc adjustments

---

## Implementation Steps

### Step 1: PlanningArtifactService
**File**: `backend/app/services/planning_artifact_service.py`

CRUD operations for PlanningArtifact with governance enforcement:
- `create_artifact()` — create DRAFT artifact with payload
- `propose_artifact()` — DRAFT → PROPOSED
- `approve_artifact()` — PROPOSED → APPROVED (sets approved_by_user_id, approved_at)
- `reject_artifact()` — PROPOSED → REJECTED
- `supersede_artifact()` — APPROVED → SUPERSEDED (creates new version)
- `get_approved_artifact()` — get latest APPROVED artifact for a plan_card_id + type
- `get_artifact_chain()` — get version history for traceability

Key rules:
- Only one APPROVED artifact per (plan_card_id, artifact_type) at a time
- New versions auto-supersede previous APPROVED versions
- `based_on_versions` records which artifact versions were read before writing
- Anti-drift: reject writes if based_on_versions doesn't match current APPROVED versions

### Step 2: GlobalCompassManager
**File**: `backend/app/services/card_protocol/global_compass_manager.py`

Manages the GLOBAL_COMPASS artifact lifecycle:

**Payload Schema**:
```json
{
  "north_star": "string — user's top-level goal",
  "success_criteria": ["measurable outcome 1", "..."],
  "values": ["non-negotiable value 1", "..."],
  "hard_constraints": {
    "max_session_minutes": 90,
    "min_break_minutes": 10,
    "preferred_time_slots": ["morning", "evening"],
    "max_concurrent_tasks": 3
  },
  "pacing_philosophy": "steady|sprint|adaptive",
  "risk_tolerance": "cautious|moderate|aggressive",
  "learning_style_hints": {
    "reflection_depth": "none|light|deep",
    "feedback_preference": "minimal|regular|detailed"
  }
}
```

Methods:
- `initialize_compass()` — create initial GLOBAL_COMPASS from user profile + plan context
- `update_compass()` — propose compass update with evidence (auto-increment version)
- `get_current_parameters()` — return approved compass parameters
- `propose_from_outcome()` — suggest compass update based on intervention outcome

### Step 3: StrategyMapManager
**File**: `backend/app/services/card_protocol/strategy_map_manager.py`

Manages the STRATEGY_MAP artifact lifecycle:

**Payload Schema**:
```json
{
  "phase_sequence": [
    {"phase_index": 0, "name": "基础", "milestone_criteria": {"mastery_threshold": 0.6}},
    {"phase_index": 1, "name": "进阶", "milestone_criteria": {"mastery_threshold": 0.8}}
  ],
  "adaptation_rules": {
    "on_stall": {"action": "reduce_concurrency", "params": {"max_tasks": 2}},
    "on_overload": {"action": "extend_timeline", "params": {"multiplier": 1.3}},
    "on_difficulty_resistance": {"action": "insert_prerequisite", "params": {}},
    "on_fast_progress": {"action": "increase_difficulty", "params": {"shift": 0.1}}
  },
  "execution_parameters": {
    "default_time_multiplier": 1.0,
    "default_difficulty_shift": 0.0,
    "max_concurrent_phases": 1,
    "checkpoint_frequency_days": 7
  }
}
```

Methods:
- `initialize_strategy_map()` — create from plan structure + compass constraints
- `get_adaptation_rule()` — look up rule for a given trigger (stall, overload, etc.)
- `get_execution_parameters()` — return current approved execution parameters
- `propose_from_outcome()` — suggest strategy update based on intervention outcome

### Step 4: ParameterCompiler
**File**: `backend/app/services/card_protocol/parameter_compiler.py`

The core Phase 3 component — compiles artifacts into execution parameters:

```python
class ParameterCompiler:
    async def compile(
        self, user_id: UUID, plan_card_id: UUID, *, trigger: str, context: dict
    ) -> ParameterCompilationResult:
        """
        1. Read APPROVED GLOBAL_COMPASS (fail if missing)
        2. Read APPROVED STRATEGY_MAP (fail if missing)
        3. Read current PlanState for baseline
        4. Apply adaptation rules based on trigger
        5. Compile into PlanState.facts["adaptive_adjustments"]
        6. Record compilation in Decision Log artifact
        7. Return result with compiled parameters + decision log
        """
```

**Anti-Drift Enforcement**:
- Step 1-2 reads the current APPROVED artifact versions
- Step 6 records `based_on_versions = {GLOBAL_COMPASS: v3, STRATEGY_MAP: v2}`
- Next compilation checks these match — rejects if stale

**Compilation Output** (writes to PlanState.facts):
```json
{
  "adaptive_adjustments": {
    "time_multiplier": 1.15,
    "difficulty_shift": -0.1,
    "max_concurrent_tasks": 2,
    "insert_prerequisite_review": false,
    "compilation_meta": {
      "compiled_at": "2026-04-15T10:00:00",
      "compass_version": 3,
      "strategy_map_version": 2,
      "trigger": "stall_pattern_detected",
      "decision_log_artifact_id": "uuid"
    }
  }
}
```

**Integration Point**: Called from `AdaptiveReplanner._apply_incremental_adjustment()` and `_trigger_full_replan()` — replaces the ad-hoc adjustment generation with compiled parameters.

### Step 5: DecisionLogService
**File**: `backend/app/services/card_protocol/decision_log_service.py`

Records parameter compilation decisions for traceability:

**Decision Log Entry Schema** (stored as PlanningArtifact payload):
```json
{
  "entries": [
    {
      "id": "uuid",
      "timestamp": "2026-04-15T10:00:00",
      "decision": "Reduced time multiplier from 1.0 to 1.15",
      "rationale": "User showed 3 consecutive tasks exceeding estimate by 50%+",
      "trigger": "overrun_streak",
      "input_artifacts": {"GLOBAL_COMPASS": "v3", "STRATEGY_MAP": "v2"},
      "expected_observation": "Tasks complete closer to estimated time",
      "confirmation_status": "pending",
      "linked_intervention_id": "uuid or null",
      "linked_occurrence_ids": ["uuid"]
    }
  ]
}
```

Methods:
- `record_decision()` — append entry to decision log artifact
- `confirm_decision()` — update confirmation_status to CONFIRMED
- `contradict_decision()` — update to CONTRADICTED with evidence
- `get_pending_confirmations()` — entries awaiting outcome verification

### Step 6: RiskRegisterService
**File**: `backend/app/services/card_protocol/risk_register_service.py`

Tracks detected risks and mitigation outcomes:

**Risk Register Schema** (stored as PlanningArtifact payload):
```json
{
  "risks": [
    {
      "id": "uuid",
      "description": "User consistently underestimates task duration",
      "likelihood": "high",
      "impact_level": "medium",
      "mitigation_strategy": "Apply time_multiplier buffer from strategy map",
      "trigger_threshold": "3 consecutive overruns",
      "status": "MITIGATED",
      "detected_at": "2026-04-10",
      "mitigated_at": "2026-04-15",
      "evidence": {"overrun_count": 4, "avg_ratio": 1.6, "post_intervention_ratio": 1.1}
    }
  ]
}
```

Methods:
- `register_risk()` — add risk entry
- `update_risk_status()` — ACTIVE → MITIGATED / ACCEPTED / CLOSED
- `get_active_risks()` — currently active risks for a plan
- `auto_register_from_intervention()` — create risk from intervention patterns

### Step 7: Enhanced Outcome Verifier
**File**: Modify `backend/app/services/card_protocol/outcome_verifier.py`

Deepen Phase 2's basic verifier with:
1. **Parameter tracking**: Check if compiled parameters were consumed by PlanAdjustmentApplier
2. **Decision log verification**: Update confirmation_status in Decision Log
3. **Risk register updates**: MITIGATED if intervention improved outcomes, ACTIVE if not
4. **Learning feedback**: Propose parameter adjustments based on effectiveness

```python
async def _evaluate_outcome(self, record):
    # ... existing logic ...

    # Phase 3 addition: Check compiled parameters
    compilation_meta = await self._get_compilation_meta(record)
    if compilation_meta:
        parameter_effective = await self._check_parameter_effectiveness(
            record, compilation_meta
        )
        evidence["parameter_compilation_id"] = compilation_meta["decision_log_artifact_id"]
        evidence["parameter_effective"] = parameter_effective

        # Update decision log confirmation status
        await self.decision_log.confirm_or_contradict(
            compilation_meta["decision_log_artifact_id"],
            confirmed=parameter_effective,
            evidence=evidence,
        )

        # Update risk register
        await self.risk_register.update_from_outcome(record, parameter_effective)

        # Propose parameter learning
        if outcome == EFFECTIVE:
            await self._reinforce_parameters(compilation_meta)
        else:
            await self._weaken_parameters(compilation_meta)
```

### Step 8: Wire Parameter Compiler into Existing Systems

**Modify** `backend/app/orchestration/adaptive_replanner.py`:
- Replace ad-hoc adjustment generation with `ParameterCompiler.compile()`
- Ensure ReplannerCardBridge reads compiled parameters

**Modify** `backend/app/orchestration/dual_core_router.py`:
- Keep `cognitive_adjustments` for prompt-level hints (backward compatible)
- Add `parameter_compilation_trigger` field to DualCoreDecision
- Router output feeds into ParameterCompiler as trigger context

**Modify** `backend/app/services/plan_adjustment_applier.py`:
- Read compiled parameters from PlanState.facts["adaptive_adjustments"]["compilation_meta"]
- Validate that compilation_meta.compass_version and strategy_map_version are current

### Step 9: Auto-Initialize Artifacts for New Plans

**Modify** `backend/app/services/card_protocol/legacy_adapter.py`:
- PlanAdapter: When creating a plan card, auto-initialize GLOBAL_COMPASS and STRATEGY_MAP artifacts
- Use user profile data for initial compass parameters
- Use plan structure for initial strategy map parameters

### Step 10: Integration Tests
**File**: `backend/tests/unit/test_phase3_parameter_compiler.py`

Test coverage:
1. ParameterCompiler compiles GLOBAL_COMPASS + STRATEGY_MAP → adaptive_adjustments
2. Anti-drift: rejects compilation if based_on_versions are stale
3. Decision Log records each compilation with traceability
4. Risk Register auto-updates from intervention outcomes
5. Enhanced outcome verifier updates decision log confirmation status
6. Full loop: intervention → compilation → execution → outcome → learning
7. Legacy adapter auto-initializes compass + strategy for new plans

---

## Dependency Order

```
Step 1 (PlanningArtifactService)
    ↓
Step 2 (GlobalCompassManager) + Step 3 (StrategyMapManager)
    ↓
Step 4 (ParameterCompiler) ← depends on 1, 2, 3
    ↓
Step 5 (DecisionLogService) + Step 6 (RiskRegisterService)
    ↓
Step 7 (Enhanced Outcome Verifier) ← depends on 5, 6
    ↓
Step 8 (Wire into existing systems) ← depends on 4, 7
    ↓
Step 9 (Auto-initialize) ← depends on 2, 3
    ↓
Step 10 (Tests)
```

Steps 2+3 can run in parallel. Steps 5+6 can run in parallel.

---

## Acceptance Gate A3 Checklist

- [ ] Parameter compiler writes real execution strategy from APPROVED artifacts
- [ ] GLOBAL_COMPASS is authoritative (no more legacy exception for user parameters)
- [ ] STRATEGY_MAP drives compilation (no more ad-hoc adjustment generation)
- [ ] Decision Log records: "We tried X because Y, observed Z, confirmed/contradicted"
- [ ] Risk Register tracks: "Risk A occurred 3x, mitigation B worked 2/3 times"
- [ ] Outcome verifier updates decision log confirmation status
- [ ] Outcome verifier proposes parameter adjustments based on effectiveness
- [ ] Anti-drift rules enforced: stale artifact versions rejected
- [ ] Legacy adapter auto-initializes compass + strategy for new plans
- [ ] Full loop: sense → diagnose → deliver → accept → act → verify → learn
