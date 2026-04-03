# Sparkle Bridge Implementation Plan

> Date: 2026-04-03  
> Status: Active implementation plan  
> Audience: Founder, product, engineering, AI agents  
> Companion docs:
> - `docs/product/SPARKLE_AI_NATIVE_SYSTEM_CONSENSUS_2026-04-03.md`
> - `docs/product/SPARKLE_PRODUCT_CONSENSUS_2026-04-02.md`
> - `docs/product/SPARKLE_CORE_VALUE_AND_ROADMAP_2026-04-03.md`
> - `docs/product/SPARKLE_GROWTH_SYSTEM_ROADMAP_2026-04-03.md`

---

## 0. Purpose

This document translates the agreed product vision into a concrete build plan for the five structural bridges we need next.

It is grounded in a direct audit of the current codebase. This is not a greenfield architecture memo. It is a reuse-first implementation plan built from the orchestration, memory, intervention, retrieval, and tool paths that already exist in Sparkle today.

The guiding rule is:

`Reuse and connect before rebuilding.`

Sparkle already has strong organs:

- event bus
- dual-core router
- memory service
- context pack builder
- cognitive service
- profile context service
- intervention lifecycle
- plan state and adaptive replanning
- tool registry
- document processing and vector retrieval

The problem is no longer "missing infrastructure."

The problem is:

- the AI does not receive a coherent picture of what matters now
- the AI cannot yet operate a bounded strategy layer
- the AI does not know enough about its own capabilities and past performance
- conversational feedback still does not reliably become durable learning
- the semantic layer is still too study-shaped

This plan closes those gaps without throwing away the current system.

---

## 1. Executive Summary

### 1.1 Build Order

The correct sequence is:

1. Bridge 1: Situation Brief
2. Bridge 2: AI Control Plane
3. Bridge 3: Growth Skills
4. Bridge 4: Conversational Feedback Binding
5. Bridge 5: Domain-Agnostic State Model

### 1.2 Dependency Logic

- Bridge 1 gives the AI a coherent read model.
- Bridge 2 gives the AI a bounded write model.
- Bridge 3 gives the AI operational self-knowledge.
- Bridge 4 closes the learning loop inside conversation.
- Bridge 5 makes the whole stack future-proof and domain-agnostic.

### 1.3 Implementation Philosophy

For all five bridges:

- prefer read-only shadow mode before replacing current behavior
- prefer new adapters over rewrites
- prefer existing services over new tables
- prefer bounded tools over one giant agent capability
- preserve current product behavior until the new path is verified

### 1.4 Audit Basis

This plan was derived from inspecting the current implementation in:

- `backend/app/orchestration/prompts.py`
- `backend/app/orchestration/context_focus.py`
- `backend/app/orchestration/orchestrator.py`
- `backend/app/orchestration/orchestrator_production.py`
- `backend/app/orchestration/session_state_mixin.py`
- `backend/app/orchestration/routing_engine.py`
- `backend/app/orchestration/adaptive_replanner.py`
- `backend/app/services/profile_context_service.py`
- `backend/app/services/progress_narrative_service.py`
- `backend/app/services/personalization/preference_service.py`
- `backend/app/services/profile_write_service.py`
- `backend/app/services/plan_state_service.py`
- `backend/app/services/routing_profile_service.py`
- `backend/app/services/intervention_record_service.py`
- `backend/app/services/intervention_strategy_learner.py`
- `backend/app/services/knowledge_service.py`
- `backend/app/services/galaxy/retrieval_service.py`
- `backend/app/agents/standard_workflow.py`
- `backend/app/api/v1/profile_transparency.py`
- `backend/app/orchestration/dynamic_tool_registry.py`
- `backend/app/tools/`
- `backend/app/models/` for memory, plan, error, galaxy, cognitive, preferences, and intervention data

The key audit conclusion is:

- a large share of the capability already exists in partial form
- the missing work is mostly bridge logic and exposure
- the correct path is to connect, normalize, and surface what Sparkle already knows

---

## 2. What Already Exists And Should Be Reused

### 2.1 Prompt and Context Assembly

Existing reusable parts:

- `backend/app/orchestration/prompts.py`
- `backend/app/orchestration/context_focus.py`
- `backend/app/core/context_pack.py`
- `backend/app/orchestration/context_builder.py`
- `backend/app/orchestration/session_state_mixin.py`
- `backend/app/services/profile_context_service.py`

Already partially doing the job:

- context budgeting and section prioritization already exist
- focused memory retrieval already exists
- context briefing already exists
- visible intelligence prompt context already exists
- companion framing already exists
- `format_user_context()` already assembles identity, goals, preferences, weak spots, focus stats, and memory into the current prompt
- `_format_visible_intelligence_section()` already exposes proactive openings, observations, and post-adaptation questions
- `FocusedContextAssembler.assemble()` already solves part of the coherence problem by creating a route-aware focused payload

What is still missing:

- one compact, structured, coherent object that answers "what matters most right now, and why?"

### 2.2 Strategy and Adaptive State

Existing reusable parts:

- `backend/app/models/user_preferences.py`
- `backend/app/services/personalization/preference_service.py`
- `backend/app/services/profile_write_service.py`
- `backend/app/services/routing_profile_service.py`
- `backend/app/models/plan_state.py`
- `backend/app/services/plan_state_service.py`
- `backend/app/orchestration/routing_engine.py`
- `backend/app/orchestration/adaptive_replanner.py`

Already partially doing the job:

- per-user inferred preference storage already exists
- per-plan state storage already exists
- per-session Redis snapshot pattern already exists
- adaptive difficulty/time adjustments already exist inside plan state
- `adaptive_adjustments` and `adaptive_meta` already persist plan-level AI adjustments
- dual-core routing already persists bounded AI judgments about the user into Redis

What is still missing:

- one merged strategy state that the AI can read and write intentionally

### 2.3 Tool and Skill Surface

Existing reusable parts:

- `backend/app/orchestration/dynamic_tool_registry.py`
- `backend/app/tools/base.py`
- `backend/app/tools/registry.py`
- existing tools in `backend/app/tools/`
- `backend/app/agents/standard_workflow.py`
- `backend/app/services/knowledge_service.py`
- `backend/app/services/galaxy/retrieval_service.py`

Current tool surface already includes:

- plan and task tools
- plan-state tools
- error tools
- preference update tool
- persona snapshot tool
- behavior pattern tool
- report, theater, simulation, translation, web, and ops tools

What is still missing:

- growth-specific skills that let the AI inspect its own track record, retrieve user materials, and adjust strategy state

### 2.4 Intervention and Feedback Loop

Existing reusable parts:

- `backend/app/services/intervention_record_service.py`
- `backend/app/services/intervention_strategy_learner.py`
- `backend/app/api/v1/profile_transparency.py`
- `backend/app/api/v1/interventions.py`
- `backend/app/services/intervention_service.py`
- `mobile/lib/features/chat/presentation/providers/chat_notifier_actions.dart`

Already partially doing the job:

- intervention lifecycle exists
- explicit feedback path exists
- chat-opening intervention delivery exists
- strategy outcome learner exists
- `profile_transparency.py` already knows how to materialize intervention-linked assistant messages into chat
- the current chat-opening flow already carries intervention IDs and marks them seen

What is still missing:

- a durable binding path from free-text conversational feedback to the active intervention or adaptation

### 2.5 Domain Abstraction

Existing reusable parts:

- `backend/app/models/memory.py`
- `backend/app/models/plan.py`
- `backend/app/models/error_book.py`
- `backend/app/models/galaxy.py`
- `backend/app/models/cognitive.py`
- `backend/app/models/card_protocol.py`
- `backend/app/services/card_protocol/global_compass_manager.py`

Already partially doing the job:

- goals exist
- progress evidence exists
- obstacles exist
- interventions and outcomes exist
- global compass and strategy artifacts exist

What is still missing:

- a stable semantic layer that maps all of that into universal primitives

---

## 3. Implementation Roadmap

### 3.1 Phase Order

Phase A:

- Bridge 1 design and shadow builder

Phase B:

- Bridge 1 prompt integration
- Bridge 2 schema and service

Phase C:

- Bridge 2 orchestrator integration
- Bridge 3 growth tools

Phase D:

- Bridge 4 feedback binding

Phase E:

- Bridge 5 semantic mapping layer

### 3.2 Parallelization Rules

Safe to run in parallel:

- Bridge 3 and Bridge 4 after Bridge 2 service boundaries exist
- Bridge 5 design work can begin during Bridge 2 if it stays read-only

Should not run in parallel:

- two different implementations of strategy state storage
- two different situation-brief builders
- any attempt to replace the current prompt system before shadow verification

---

## 4. Bridge 1: Situation Brief

### 4.1 Product Goal

Give the AI a coherent, compact picture of the user's present situation.

The brief must answer:

`What matters most for this user right now, and why?`

### 4.2 Reuse Inventory

Reuse these existing systems directly:

- `FocusedContextAssembler.assemble()` in `backend/app/orchestration/context_focus.py`
- `ContextPackBuilder.build()` in `backend/app/core/context_pack.py`
- `ProfileContextService.get_profile_context()` in `backend/app/services/profile_context_service.py`
- `SessionStateMixin._build_system_update_prompt_context()` in `backend/app/orchestration/session_state_mixin.py`
- dual-core routing snapshot in `backend/app/orchestration/routing_engine.py`
- `ProgressNarrativeService.maybe_get_lightweight_snapshot()` in `backend/app/services/progress_narrative_service.py`
- prompt rendering in `backend/app/orchestration/prompts.py`

Do not rebuild:

- context pack ranking
- context focusing
- prompt budgeting
- visible intelligence prompt context
- companion framing

### 4.3 Recommended Artifact

Create a new structured object:

`SituationBrief`

Recommended file:

- `backend/app/orchestration/situation_brief.py`

Recommended shape:

```python
@dataclass
class SituationBrief:
    focus_question: str
    summary: str
    vision: dict[str, Any]
    current_state: dict[str, Any]
    primary_obstacle: dict[str, Any]
    evidence: dict[str, Any]
    sparkle_self_state: dict[str, Any]
    recommended_stance: dict[str, Any]
    source_trace: dict[str, Any]
```

### 4.4 Field Sources

| SituationBrief field | Reuse source |
|---|---|
| `vision` | `active_goals`, `MemoryGoal`, active `Plan`, `GLOBAL_COMPASS.north_star` when available |
| `current_state` | `UserService.get_context()`, `ProfileContextService`, `focus_stats`, `analytics_summary`, `exam_urgency`, progress snapshot |
| `primary_obstacle` | `learning_gaps_summary`, `cognitive_insights`, top `BehaviorPattern`, recent `ErrorRecord`, plan health / stall signals |
| `evidence` | recent errors, mastery changes, task completion, progress deltas, recent intervention outcome |
| `sparkle_self_state` | last dual-core mode, recent intervention acceptance/effectiveness, evidence freshness, confidence estimate |
| `recommended_stance` | dual-core prompt instruction, session feedback signal, current strategy state once Bridge 2 exists |

### 4.5 Required Output Rules

The SituationBrief should be:

- structured first
- rendered second
- compact enough to fit in roughly 200-400 tokens when rendered
- grounded in the freshest evidence, not the largest amount of evidence
- cheap to build from already assembled payloads before it performs new heavy reads

It should not be:

- a giant summary blob
- a replacement for full memory retrieval
- a place to dump all user history

### 4.6 Stage Plan

#### Stage 1A: Source Audit And Schema Lock

Deliverables:

- source mapping table for every SituationBrief field
- fallback logic for missing sources
- confidence heuristics for evidence freshness and coherence

Implementation notes:

- audit every field currently injected in `prompts.py`
- audit every field currently produced by `FocusedContextAssembler`
- decide which fields stay only in raw context and which are promoted into the brief

Acceptance:

- every SituationBrief field has a clearly named data source or fallback

#### Stage 1B: Read-Only Builder

Deliverables:

- `SituationBriefBuilder`
- read-only build path from existing context payloads
- no prompt integration yet

Implementation notes:

- builder should consume `user_context_payload`, `plan_context`, `focused_memory`, `context_briefing_note`, visible update context, and dual-core snapshot
- builder should not fetch huge new datasets if equivalent data already exists in the assembled payload

Acceptance:

- a brief can be produced for normal chat, plan chat, error chat, and emotional chat

#### Stage 1C: Orchestrator Shadow Integration

Deliverables:

- write `situation_brief` into `state.context_data`
- expose it in response metadata or tracing for inspection
- do not yet make it the primary prompt section

Recommended touch points:

- `backend/app/orchestration/orchestrator.py`
- `backend/app/orchestration/orchestrator_production.py`
- `backend/app/orchestration/execution_engine.py`

Acceptance:

- the brief is visible in logs or response metadata for all major routes

#### Stage 1D: Prompt Integration

Deliverables:

- new prompt formatter such as `_format_situation_brief_section()`
- new prompt section budget and priority
- prompt template placement before broad user context blocks

Recommended touch points:

- `backend/app/orchestration/prompts.py`

Acceptance:

- the rendered brief survives budget compression
- the prompt still includes companion framing and visible intelligence

#### Stage 1E: Evaluation And Pruning

Deliverables:

- compare prompt size and coherence before vs after
- identify sections that can be demoted once SituationBrief proves reliable

Acceptance:

- no regression in existing prompt tests
- improved clarity in inspected prompt snapshots

### 4.7 Verification

Required tests:

- unit test for SituationBriefBuilder with representative payloads
- prompt integration test ensuring the section renders
- budget test ensuring it survives compression
- regression tests for visible intelligence and companion sections

### 4.8 Out Of Scope

Not in Bridge 1:

- strategy writes
- new database tables
- new retrieval stack
- replacing context pack

---

## 5. Bridge 2: AI Control Plane (UserStrategyState)

### 5.1 Product Goal

Allow the AI to make bounded, persistent strategy adjustments that affect the user's experience now and later.

The AI should be able to say:

- "I'm lowering the difficulty"
- "I'm switching to recovery mode"
- "I'm leaning more supportive for this week"

and have that change actually stick at the correct layer.

### 5.2 Reuse Inventory

Reuse these systems directly:

- `UserPreferencesCenter` in `backend/app/models/user_preferences.py`
- `PreferenceService` in `backend/app/services/personalization/preference_service.py`
- `ProfileWriteService` in `backend/app/services/profile_write_service.py`
- `PlanState` and `PlanStateService`
- Redis snapshot pattern from `_persist_dual_core_decision_snapshot()` in `backend/app/orchestration/routing_engine.py`
- existing adaptive plan facts in `backend/app/orchestration/adaptive_replanner.py`

Do not build:

- a brand new preference table
- a brand new plan-scoped strategy table
- a fully autonomous system-layer self-modifier yet

### 5.3 Recommended Storage Model

Implement `UserStrategyState` as a merged view across existing layers.

Recommended service:

- `backend/app/services/user_strategy_state_service.py`

Recommended persistence model:

- session layer: Redis
- episode layer: `PlanState.facts`
- profile layer: `UserPreferencesCenter.inferred`

### 5.4 Minimal Initial Schema

Start with these fields:

```python
{
    "difficulty_level": 3,                  # 1..5
    "push_vs_support": 0.5,                 # 0.0..1.0
    "session_mode": "guided",               # guided|exploratory|review|recovery
    "intervention_intensity": "medium",     # low|medium|high
    "explanation_style": "conceptual",      # conceptual|example_based|step_by_step
    "retrieval_emphasis": "balanced",       # user_materials|balanced|general_knowledge
    "current_episode_note": "",             # short string
}
```

### 5.5 Write Audit Shape

Every write should record:

```python
{
    "field": "difficulty_level",
    "layer": "episode",
    "old_value": 4,
    "new_value": 2,
    "reason": "user said current tasks are overwhelming",
    "evidence": {
        "source": "conversation",
        "snippet": "this is overwhelming",
    },
    "confidence": 0.86,
    "timestamp": "...",
    "expires_at": "...",
}
```

### 5.6 Layering Rules

#### Session Layer

Recommended storage:

- Redis key like `session:strategy:{session_id}`

Use for:

- immediate conversational adaptations
- ephemeral tone or pacing changes

#### Episode Layer

Recommended storage:

- `plan_states.facts["user_strategy_state"]`
- `plan_states.facts["user_strategy_history"]`

Use for:

- exam week adjustments
- current recovery mode
- current episode note
- current retrieval emphasis for this goal

#### Profile Layer

Recommended storage:

- `user_preferences_center.inferred["user_strategy_state"]`
- `user_preferences_center.inferred["user_strategy_meta"]`

Use for:

- repeated evidence about the user's long-term tendencies

### 5.7 Existing Adaptive Replanner Reuse

Do not replace `adaptive_replanner`.

Instead:

- map existing `adaptive_adjustments` into the episode-layer strategy view
- let `difficulty_shift` and `time_multiplier` remain valid internal mechanics
- surface them through UserStrategyState in a human-readable form

This preserves current reliability while exposing a cleaner AI-facing control plane.

### 5.8 Stage Plan

#### Stage 2A: Schema And Merge Semantics

Deliverables:

- `UserStrategyState` schema
- precedence rules: session > episode > profile > defaults
- write policy for each field

Acceptance:

- every field has a default, bounds, layer policy, and expiration policy

#### Stage 2B: Read Service

Deliverables:

- merged read API
- history read API
- no writes yet

Recommended methods:

- `get_effective_state(user_id, plan_id=None, session_id=None)`
- `get_recent_changes(user_id, plan_id=None, session_id=None)`

Acceptance:

- merged strategy state can be returned for users with any subset of layers populated

#### Stage 2C: Write Service

Deliverables:

- bounded write API
- clamping and validation
- audit history

Recommended method:

- `apply_adjustment(user_id, changes, layer, reason, evidence, confidence, session_id=None, plan_id=None)`

Acceptance:

- writes are bounded, durable at the correct layer, and inspectable

#### Stage 2D: Orchestrator Integration

Deliverables:

- effective strategy state merged into `context_data`
- strategy state available to SituationBrief
- strategy writes callable from tools in Bridge 3

Recommended touch points:

- `backend/app/orchestration/orchestrator.py`
- `backend/app/orchestration/orchestrator_production.py`
- `backend/app/orchestration/execution_engine.py`

Acceptance:

- a strategy write in one turn changes the next turn's behavior without restarting the system

#### Stage 2E: Safety And Rollback

Deliverables:

- bounds enforcement
- TTL or expiry for session and episode adjustments
- no writes to constitutional or system layers

Acceptance:

- invalid writes are rejected
- no strategy write can corrupt preferences or factual history

### 5.9 Verification

Required tests:

- merge precedence tests
- write-and-readback tests for each layer
- cache invalidation tests for profile updates
- integration test that a write changes subsequent prompt context

### 5.10 Out Of Scope

Not in Bridge 2:

- fully AI-controlled system-level routing policies
- feature flag mutation
- new UI for manual editing of all strategy fields

---

## 6. Bridge 3: Growth Skills As AI Self-Knowledge

### 6.1 Product Goal

Teach the AI what it can do for growth, not only what external tools it can call.

The AI needs skills for:

- reading the current situation
- reading and adjusting strategy
- checking whether past interventions worked
- retrieving the user's own materials
- writing short-lived episode guidance

### 6.2 Reuse Inventory

Reuse the existing tool system directly:

- `DynamicToolRegistry`
- `BaseTool`
- `ToolResult`
- existing tool registration path from `app.tools`

Relevant existing tools already worth keeping:

- `get_plan_state`
- `get_task_summary`
- `query_plan_tasks`
- `modify_plan_task`
- `record_error`
- `query_error_history`
- `get_user_behavior_patterns`
- `get_persona_snapshot`
- `update_user_preference`
- `generate_learning_report`
- `launch_prediction`
- `run_quick_simulation`

Do not build:

- a second tool runtime
- a second skill registry for execution

If a higher-level "skill catalog" is added later, it should sit on top of the same `BaseTool` surface.

### 6.3 Recommended New Tool Modules

Recommended files:

- `backend/app/tools/growth_strategy_tools.py`
- `backend/app/tools/material_retrieval_tools.py`
- `backend/app/tools/intervention_tools.py`

### 6.4 Recommended Initial Growth Skills

#### Skill 1: `get_situation_brief`

Purpose:

- read the compact SituationBrief directly

Reads:

- `SituationBriefBuilder`

Writes:

- nothing

Constraints:

- read-only

#### Skill 2: `get_user_strategy_state`

Purpose:

- retrieve effective strategy state and recent changes

Reads:

- session strategy
- plan-state strategy
- profile strategy

Writes:

- nothing

Constraints:

- read-only

#### Skill 3: `adjust_user_strategy_state`

Purpose:

- write bounded changes to session, episode, or profile strategy

Reads:

- current effective strategy state

Writes:

- strategy layer only

Constraints:

- field allowlist only
- layer allowlist only
- bounded numeric ranges only

#### Skill 4: `retrieve_user_material`

Purpose:

- retrieve relevant passages from the user's uploaded files

Reads:

- `StoredFile`
- `DocumentChunk`
- `KnowledgeRetrievalService.document_vector_search()`
- the existing hybrid retrieval path used in `standard_workflow.retrieval_node()`

Writes:

- nothing

Constraints:

- current user's files only
- bounded `limit`

#### Skill 5: `get_intervention_track_record`

Purpose:

- let the AI inspect how Sparkle has recently been doing with this user

Reads:

- `InterventionRecordService.get_recent_for_user()`
- `InterventionRecordService.get_acceptance_stats()`
- `InterventionRecordService.get_outcome_stats()`
- `InterventionStrategyLearner.get_user_response_profile()`

Writes:

- nothing

Constraints:

- read-only

#### Skill 6: `record_intervention_feedback`

Purpose:

- write conversational feedback onto the active or specified intervention

Reads:

- active intervention resolver
- intervention record

Writes:

- intervention acceptance/action payload

Constraints:

- current user's intervention only
- must not create arbitrary new intervention records

#### Skill 7: `write_episode_note`

Purpose:

- persist short-lived episode guidance like "exam prep week, high stress"

Reads:

- current episode state

Writes:

- episode-layer strategy state only

Constraints:

- short bounded note length

### 6.5 Stage Plan

#### Stage 3A: Tool Design

Deliverables:

- tool names
- schemas
- read/write scopes
- validation rules
- routing guidance for when the AI should prefer a growth skill over raw prompt context

Acceptance:

- every tool has explicit read and write boundaries

#### Stage 3B: Tool Implementation

Deliverables:

- new tool modules
- auto-registration through `DynamicToolRegistry`

Acceptance:

- tools appear in the registry with valid OpenAI schemas

#### Stage 3C: Orchestrator Exposure

Deliverables:

- include growth tools in active tool sets for standard chat where appropriate

Acceptance:

- the AI can call the tools in real conversation flows

#### Stage 3D: Prompt/Policy Guidance

Deliverables:

- lightweight tool-use guidance in prompt or mode strategy where necessary

Acceptance:

- the AI prefers growth tools when the situation calls for them

### 6.6 Verification

Required tests:

- registry tests for new tools
- tool execution tests
- integration tests for retrieval and strategy writes

### 6.7 Out Of Scope

Not in Bridge 3:

- autonomous multi-step planning engine for tool composition
- unrestricted self-modification

---

## 7. Bridge 4: Conversational Feedback Binding

### 7.1 Product Goal

Make user words count as feedback.

When the user says:

- "yes, that helped"
- "not really"
- "this is still too hard"
- "I like this better"

the system should be able to bind that to the relevant intervention or adaptation without requiring a chip tap.

### 7.2 Reuse Inventory

Reuse these existing systems directly:

- `InterventionRecordService`
- `InterventionStrategyLearner`
- `profile_transparency.py` chat-opening flow
- existing explicit feedback actions in chat
- existing intervention record and outcome models

Already partially available:

- intervention IDs are already present in chat-opening metadata
- intervention acceptance lifecycle already exists
- strategy outcome learner already exists

What is still missing:

- a resolver for "which intervention is currently active?"
- a tool path for AI-triggered feedback writes during conversation

### 7.3 Recommended New Components

Recommended files:

- `backend/app/services/intervention_feedback_binding_service.py`
- `backend/app/tools/intervention_tools.py`

Recommended state additions:

- `state.context_data["active_interventions"]`
- `state.context_data["last_feedback_binding"]`

### 7.4 Active Intervention Resolution

Resolution order should be:

1. intervention ID explicitly present in current tool/widget context
2. recent relevant intervention ID from drained system updates
3. unresolved recent intervention from `InterventionRecordService.get_pending_for_user()`
4. fresh recent intervention from `get_recent_for_user()` if still plausible

This should remain heuristic but bounded.

### 7.5 Recommended Feedback Tool Schema

```python
{
    "intervention_id": "optional uuid",
    "sentiment": "helped|accepted|dismissed|not_helped|mixed",
    "user_words": "raw user words",
    "confidence": 0.0-1.0
}
```

### 7.6 Write Policy

Map conversational feedback carefully:

- `helped` or `accepted`:
  - mark `SEEN` if needed
  - mark `ACTED` when appropriate
  - append conversational evidence

- `dismissed` or `not_helped`:
  - mark `SEEN` if needed
  - mark `DISMISSED` when appropriate
  - append conversational evidence

- `mixed`:
  - append feedback evidence
  - do not necessarily force terminal status

Do not:

- infer final effectiveness too early
- overwrite factual outcome evidence

### 7.7 Stage Plan

#### Stage 4A: Active Intervention Tracking

Deliverables:

- session-state field for active interventions
- resolver service

Acceptance:

- the system can identify the current intervention candidate during conversation

#### Stage 4B: Feedback Tool

Deliverables:

- `record_intervention_feedback` tool
- append raw words and metadata into the intervention record

Acceptance:

- AI can persist feedback from free-text conversation

#### Stage 4C: Learner Hook

Deliverables:

- handoff from feedback binding to strategy learner or outcome pipeline

Acceptance:

- the feedback becomes usable for future intervention selection

#### Stage 4D: Duplicate Protection

Deliverables:

- simple dedupe rule using message hash or last bound message ID

Acceptance:

- the same user sentence is not bound repeatedly

### 7.8 Verification

Required tests:

- positive free-text feedback binding
- negative free-text feedback binding
- no active intervention fallback behavior
- duplicate suppression

### 7.9 Out Of Scope

Not in Bridge 4:

- a separate NLP classifier service
- heavyweight sentiment pipeline

The AI is the classifier.

---

## 8. Bridge 5: Domain-Agnostic State Model

### 8.1 Product Goal

Make Sparkle's deep reasoning layer domain-agnostic without rewriting the current study-domain data model.

This is a semantic bridge, not a migration project.

### 8.2 Reuse Inventory

Map existing models upward instead of renaming them.

Primary study-domain sources already available:

- `MemoryGoal`
- `Plan`
- `GlobalCompass`
- `ErrorRecord`
- `UserNodeStatus`
- `StudyRecord`
- `BehaviorPattern`
- `CognitiveFragment`
- `InterventionRecord`
- `InterventionStrategyOutcome`

### 8.3 Recommended Primitive Types

Define these primitives first:

- `Vision`
- `CurrentState`
- `Obstacle`
- `Evidence`
- `Intervention`
- `Outcome`

Optional later:

- `Resource`

### 8.4 Mapping Layer

Recommended file:

- `backend/app/semantic/state_primitives.py`
- or `backend/app/services/semantic_state_mapper.py`

Recommended initial mapping:

| Universal primitive | Existing study-domain source |
|---|---|
| `Vision` | `MemoryGoal`, `Plan`, `GLOBAL_COMPASS.north_star`, strategy map |
| `CurrentState` | `UserContext`, `ProfileContext`, `PlanState`, focus stats, schedule/time capacity |
| `Obstacle` | `ErrorRecord`, weak spots, `BehaviorPattern`, `CognitiveFragment`, plan risk flags |
| `Evidence` | `UserNodeStatus`, `StudyRecord`, task completion, progress narrative, retrieved document passages |
| `Intervention` | `InterventionRecord`, adaptive replanner records, visible intelligence messages |
| `Outcome` | intervention acceptance/outcome, strategy outcomes, mastery changes, recurring error deltas |

### 8.5 Important Rule

The SituationBrief should speak in these universal primitives even when its sources remain study-specific.

That is how we prepare for future domains without breaking current reliability.

### 8.6 Stage Plan

#### Stage 5A: Primitive Spec

Deliverables:

- field definitions for all six primitives
- source mapping from current models

Acceptance:

- every current study-domain signal can be mapped into at least one primitive

#### Stage 5B: Read-Only Mapper

Deliverables:

- semantic mapper that produces primitive payloads from current study models

Acceptance:

- no database schema changes
- no behavior regressions

#### Stage 5C: SituationBrief Consumption

Deliverables:

- SituationBrief builder updated to consume primitive layer names

Acceptance:

- the brief can be described without study-specific language at the top level

#### Stage 5D: Future Domain Readiness

Deliverables:

- clear adapter contract for future domains like fitness or creative practice

Acceptance:

- adding a new domain becomes a new adapter, not a rewrite

### 8.7 Verification

Required tests:

- mapper tests from study-domain fixtures to universal primitive fixtures
- SituationBrief tests that verify semantic abstraction

### 8.8 Out Of Scope

Not in Bridge 5:

- replacing study-domain models
- data migration
- UI rewrite for non-study domains

---

## 9. Recommended File Touch Points By Bridge

### Bridge 1

- `backend/app/orchestration/prompts.py`
- `backend/app/orchestration/context_focus.py`
- `backend/app/orchestration/orchestrator.py`
- `backend/app/orchestration/orchestrator_production.py`
- `backend/app/orchestration/execution_engine.py`
- `backend/app/orchestration/session_state_mixin.py`
- new `backend/app/orchestration/situation_brief.py`

### Bridge 2

- `backend/app/services/personalization/preference_service.py`
- `backend/app/services/profile_write_service.py`
- `backend/app/services/plan_state_service.py`
- `backend/app/models/user_preferences.py`
- `backend/app/models/plan_state.py`
- `backend/app/orchestration/routing_engine.py`
- new `backend/app/services/user_strategy_state_service.py`

### Bridge 3

- `backend/app/orchestration/dynamic_tool_registry.py`
- `backend/app/tools/base.py`
- existing tool modules under `backend/app/tools/`
- new growth tool modules

### Bridge 4

- `backend/app/services/intervention_record_service.py`
- `backend/app/services/intervention_strategy_learner.py`
- `backend/app/api/v1/profile_transparency.py`
- `backend/app/orchestration/orchestrator.py`
- new feedback binding service and tool module

### Bridge 5

- new semantic mapping module
- SituationBrief builder once Bridge 1 exists

---

## 10. Acceptance Standard Per Bridge

### Bridge 1 Is Done When

- the AI receives a compact SituationBrief
- the brief is visible in prompt or debug metadata
- the brief survives budget pressure

### Bridge 2 Is Done When

- the AI can make bounded strategy writes
- those writes persist at the right layer
- the next turn reflects the change

### Bridge 3 Is Done When

- the AI can inspect its own track record
- the AI can retrieve user materials on demand
- the AI can adjust strategy using registered growth tools

### Bridge 4 Is Done When

- free-text feedback updates intervention records
- button taps are no longer the only learning channel

### Bridge 5 Is Done When

- SituationBrief and future orchestration can reason in universal primitives
- current study-domain models remain intact underneath

---

## 11. Implementation Guidance For The Next Codex

If this plan is executed by separate agents, the handoff order should be:

### Codex Task 1

Bridge 1 only:

- design `SituationBrief`
- implement read-only builder
- integrate in shadow mode
- no prompt replacement until reviewed

### Codex Task 2

Finish Bridge 1 prompt integration after review:

- add prompt section
- add tests
- verify no regression in visible intelligence or companion framing

### Codex Task 3

Bridge 2:

- implement `UserStrategyStateService`
- integrate read path
- then add bounded writes

### Codex Task 4

Bridge 3 and Bridge 4:

- add growth tools
- add feedback binding path

### Codex Task 5

Bridge 5:

- implement semantic mapping layer
- update SituationBrief to consume primitive terminology

---

## 12. Final Guidance

The fastest path is not to invent a second Sparkle inside Sparkle.

The fastest path is:

- connect what already exists
- compress what is currently diffuse
- expose what is currently invisible
- let the AI read and write only where it genuinely helps the user
- verify every bridge against the north-star user outcome, not just architectural neatness

If these bridges are built correctly, Sparkle will stop feeling like a system with many modules and start feeling like one coherent intelligence.
