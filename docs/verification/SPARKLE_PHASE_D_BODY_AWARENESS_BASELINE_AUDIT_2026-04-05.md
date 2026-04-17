# Sparkle Phase D Body Awareness Baseline Audit

> Date: 2026-04-05
> Scope: Phase D `D0` baseline audit, organ inventory, implicit-routing map, and scenario harness entrypoint
> Scenario fixture: `/Users/brsama/code/GitHub/Sparkle-project/backend/tests/fixtures/phase_d_body_awareness_baseline_scenarios.json`
> Inventory snapshot: `/Users/brsama/code/GitHub/Sparkle-project/backend/tests/fixtures/phase_d_current_capability_inventory_snapshot.json`

## Current Runtime Entry Points

- `backend/app/services/capability_registry_service.py`
  - current canonical read model for models, agents, tools, subsystems, and advisory body-awareness guidance
- `backend/app/orchestration/situation_brief.py`
  - compiles `body_awareness_guidance` into `decision_context`, then carries planning strategy fields forward
- `backend/app/orchestration/orchestrator.py`
  - resolves implicit `route_intent` and currently hard-governs one runtime tool case through `_resolve_active_tools`
- `backend/app/core/llm_router.py`
  - owns model candidate resolution, policy-aware tier selection, health-aware fallback, and routing introspection
- `backend/app/core/agent_profiles.py`
  - defines the real agent families, public expert catalog, and per-agent model policies
- `backend/app/orchestration/decision_policy.py`
  - compiles `experience_mode`, `intervention_family`, and bounded adjustment recommendations from diagnosis
- `backend/app/services/user_strategy_state_service.py`
  - defines the actually writable strategy knobs and the real layer constraints for `session`, `episode`, and `profile`
- `backend/app/api/v1/multi_agent.py`
  - exposes the current body-map endpoint by returning `CapabilityRegistryService().build_registry()`

## Current Organ Inventory

### Operational Now

- Models
  - `LLMRouter` currently loads 22 model configs across `free`, `free_fast`, `fast`, `standard`, `plus`, `pro`, `max`, `glm_batch`, and `specialist` tiers.
  - Selection is operational and health-aware today, not hypothetical.
- Agent families
  - 20 agent profiles are live in `agent_profiles`, including core runtime roles, LangGraph specialists, collaboration roles, and review/tool-execution roles.
  - Public expert entry is already operational for specialist families such as `galaxy_guide`, `exam_oracle`, `time_tutor`, `deep_analyst`, `error_analyst`, `study_buddy`, `search_agent`, `math_agent`, `code_agent`, `writing_agent`, and `science_agent`.
- Tools
  - `CapabilityRegistryService().build_registry()` currently surfaces 44 dynamically registered tools.
  - Registered tool families by category are real today:
    - `query`: 17
    - `task`: 11
    - `growth`: 7
    - `plan`: 5
    - `focus`: 2
    - `knowledge`: 2
- Runtime pipelines
  - `SituationBriefBuilder` compiles Phase A, B, and C state into one turn brief.
  - `LLMRouter` performs real model selection with policy and health signals.
  - `DecisionPolicyCompiler` emits real bounded adjustment recommendations.
  - `ChatOrchestrator` performs real tool activation and routing decisions.
- Retrieval organs
  - `query_knowledge`
  - `retrieve_user_material`
  - retrieval agent role
  - `galaxy_guide`
  - `search_agent`
  - `web_search_pro`
- Real writable knobs
  - `UserStrategyStateService.FIELD_SPECS` defines seven actually writable fields:
    - `difficulty_level`
    - `push_vs_support`
    - `session_mode`
    - `intervention_intensity`
    - `explanation_style`
    - `retrieval_emphasis`
    - `current_episode_note`

### Advisory Only

- `CapabilityRegistryService.recommend_runtime_capabilities()` provides bounded guidance for:
  - primary subsystem choice
  - supporting subsystems
  - activation surfaces
  - evidence sources
  - bounded knob decisions
- `SituationBriefBuilder` injects that guidance into `decision_context["body_awareness_guidance"]`.
- Prompt construction reads the guidance and can mention it to the model, but this is still advisory context for most subsystems rather than a shared runtime governance contract.

### Declared But Not Governed

- `CapabilityRegistryService.build_registry()` declares:
  - 8 major subsystems
  - 3 system-layer knobs
  - configuration layers from `constitutional` through `system`
- Those declarations are useful inventory, but they do not yet govern selection through one canonical Phase D policy.
- The registry does not yet expose one live runtime body map with:
  - blocked organs
  - unhealthy organs
  - surface constraints
  - current availability gates
  - candidate organs for the current turn

## Current Implicit-Routing Map

### Chain 1: `route_intent/chat_mode -> SituationBrief body_awareness_guidance -> prompt guidance`

- `SituationBriefBuilder` calls `CapabilityRegistryService().recommend_runtime_capabilities(...)`.
- The result is stored in `decision_context["body_awareness_guidance"]`.
- Prompt builders later read `body_awareness_guidance` and phrase it as guidance for the model.
- Current status: advisory only.
- Current weakness: the guidance is not yet a stable runtime contract that downstream selection code must obey.

### Chain 2: `route_intent -> ChatOrchestrator._resolve_active_tools -> query_knowledge injection`

- `ChatOrchestrator._infer_capability_route_intent(...)` derives a coarse intent from `chat_mode` or keywords.
- `_resolve_active_tools(...)` calls `CapabilityRegistryService().recommend_runtime_capabilities(...)`.
- If the recommended primary subsystem is `galaxy` and no explicit tool scope was provided, the orchestrator injects `query_knowledge`.
- Current status: operational now.
- Current weakness: this is the only clearly hard-governed body-aware routing case in the main path today.

### Chain 3: `AgentProfile/TaskType -> LLMRouter tier/model selection`

- `agent_profiles` declares per-agent tier, preferred models, fallback tiers, and lock behavior.
- `LLMRouter.select_model(...)` and `resolve_candidate_models(...)` compile that policy with task type, reasoning mode, provider avoidance, and health state.
- `describe_agent_routing(...)` makes the choice inspectable.
- Current status: operational now.
- Current weakness: model choice is governed, but it is not yet governed by a shared Phase D requirement profile or body map.

### Chain 4: `diagnosis/experience_mode -> DecisionPolicyCompiler -> session/episode adjustment recommendations`

- `DecisionPolicyCompiler` derives `experience_mode`, `intervention_family`, `reversibility_level`, and up to four adjustment recommendations.
- Those adjustments target the real writable knobs defined in `UserStrategyStateService`.
- Current status: operational now for recommendation and downstream experience shaping.
- Current weakness: the adjustments are tied to diagnosis semantics, not to one explicit capability requirement profile or rights-aware capability selector.

## Current Organ Inventory By Family

### Models

- Current source of truth: `LLMRouter._load_model_configs()`
- Operational families:
  - lightweight general chat: `xiaomi_chat`, `dashscope_fast`, `glm_4_7_flash_no_thinking`
  - standard reasoning/chat: `xiaomi_standard_thinking`, `dashscope_standard_thinking`, `default`
  - higher-quality chat: `dashscope_chat`, `deepseek_chat`
  - deep reasoning: `dashscope_reason`, `deepseek_reason`
  - batch or background Zhipu lanes: `glm_4_7_no_thinking`, `glm_4_7_thinking`, `glm_4_5_air_batch`, `glm_4_6_batch`
  - max tier: `glm_5_max`
  - specialist OCR/translation: `zhipu_ocr`, `siliconflow_ocr`, `hunyuan_translate`, `siliconflow_translate`
- Availability reality:
  - model presence is operational
  - effective availability still depends on configured credentials, health, and tier overrides

### Agent Families

- Core runtime roles
  - `orchestrator`, `generation`, `retrieval`, `tool_execution`, `router`
- Specialist public experts
  - `galaxy_guide`, `exam_oracle`, `time_tutor`, `deep_analyst`, `error_analyst`
  - `study_buddy`, `search_agent`, `math_agent`, `code_agent`, `writing_agent`, `science_agent`
- Collaboration and support roles
  - `study_planner`, `problem_solver`, `execution_assistant`, `reviewer`
- Governance reality:
  - agent families are real and selectable
  - there is not yet one Phase D policy that chooses specialist escalation from an explicit capability requirement profile

### Tool Families

- Query / evidence / status tools
  - examples: `query_knowledge`, `web_search_pro`, `generate_learning_report`, `run_quick_simulation`, `launch_prediction`, `check_system_status`
- Task / execution scaffolding tools
  - examples: `create_task`, `update_task_status`, `breakdown_task`, `modify_plan_task`, `query_all_tasks`
- Plan tools
  - examples: `create_plan`, `generate_tasks_for_plan`, `get_plan_state`, `confirm_milestone_proposal`
- Growth / adaptation tools
  - examples: `get_situation_brief`, `get_user_strategy_state`, `adjust_user_strategy_state`, `retrieve_user_material`
- Focus tools
  - examples: `suggest_focus_session`, `suggest_quick_task`
- Knowledge graph mutation tools
  - examples: `create_knowledge_node`, `link_knowledge_nodes`
- Tool inventory nuance:
  - the dynamic registry currently logs a registration failure for `app.tools.query_plan_tasks_tool` because `QueryPlanTasksTool` lacks `parameters_schema`
  - this means the repo contains more tool-like code than the live registry actually operationalizes

### Orchestration Paths

- `SituationBriefBuilder`
- `DecisionPolicyCompiler`
- `PlanningStrategyCompiler`
- `ValidationEngine`
- `PlanQualityGate`
- `ChatOrchestrator`
- `ExecutionEngine`
- `LLMRouter`

### Retrieval Systems

- explicit knowledge tool: `query_knowledge`
- explicit user-material tool: `retrieve_user_material`
- retrieval agent role: `retrieval`
- specialist retrieval expert: `search_agent`
- knowledge-graph expert: `galaxy_guide`
- optional web search tool: `web_search_pro`

### Visible Surfaces

- Operational now
  - primary chat response
  - public expert entry catalog
  - multi-agent route preview
  - body-map endpoint returning the registry
- Declared but not governed through one capability selector
  - `community`
  - `achievements`
  - `visual_bgm`

## Baseline Reading Of Current Gaps

- Body-awareness is mostly advisory, not a shared runtime contract.
- Only a narrow knowledge-tool decision is hard-governed by current body-awareness.
- No canonical rights, preconditions, reversibility, and availability schema yet governs all organs the same way.
- No live body map currently includes blocked organs, candidate organs, surface constraints, or unhealthy-organs-by-turn.
- Model selection, agent selection, tool activation, and adaptation knobs are each real, but they are distributed across several files rather than chosen through one requirement compiler plus one selector.
- The registry reports subsystem and knob declarations, but Phase D has not yet turned those declarations into enforceable runtime policy.
- Tool inventory is not perfectly aligned with repo code; at least one tool module exists but does not successfully join the dynamic registry.

## Concrete Wrong-Organ Or Missing-Governance Cases

1. Knowledge turns have one hard-governed path today, but other evidence-heavy turns do not.
   - Sparkle can auto-inject `query_knowledge`, but it does not yet use the same governance pattern for user-material retrieval, specialist escalation, or visible-surface choice.

2. Specialist escalation exists as an agent capability, but not as a unified runtime decision.
   - The repo already has strong public experts and multi-agent entry surfaces, yet the main turn path does not compile one explicit requirement profile that says when a specialist is required versus theatrical.

3. Cost-aware model selection is real, but detached from the Phase A/B/C turn state.
   - `LLMRouter` makes real policy and health-aware choices, but those choices are not yet driven by one body-aware requirement object that knows when a simple path is enough.

4. Bounded knobs are real, but Phase D governance is not.
   - `DecisionPolicyCompiler` recommends reversible changes to real strategy fields, but the registry-level system knobs remain declared guidance rather than an enforced governance layer.

5. Visible surfaces are declared as part of the body, but not selected through a shared selector.
   - `community`, `achievements`, and `visual_bgm` appear in the registry and advisory guidance, yet they do not currently flow through one auditable capability-selection report.

## Baseline Scenario Set

The canonical D0 scenario fixture contains 10 scenarios and is intended to be reused by D3, D4, and D7:

- user materials mandatory grounding
- simple knowledge turn where light retrieval is enough
- overloaded user needing stabilization over deeper planning
- high-readiness planning where a simple path should win
- specialist escalation case
- prediction-oriented case
- community or accountability surface case
- bounded execution request with unavailable execution organ fallback
- adaptation-heavy visible-surface case
- cost-sensitive fast-enough case versus expensive overuse

Fixture file:

- `/Users/brsama/code/GitHub/Sparkle-project/backend/tests/fixtures/phase_d_body_awareness_baseline_scenarios.json`

## D0 Contract Artifacts

- Verification report:
  - `/Users/brsama/code/GitHub/Sparkle-project/docs/verification/SPARKLE_PHASE_D_BODY_AWARENESS_BASELINE_AUDIT_2026-04-05.md`
- Scenario harness seed:
  - `/Users/brsama/code/GitHub/Sparkle-project/backend/tests/fixtures/phase_d_body_awareness_baseline_scenarios.json`
- Current-body parity snapshot for D1:
  - `/Users/brsama/code/GitHub/Sparkle-project/backend/tests/fixtures/phase_d_current_capability_inventory_snapshot.json`

## Suggested Execution Flow For Later Packs

1. Use the D0 inventory snapshot to verify D1 registry coverage.
2. Use the D0 scenario fixture to define D3 requirement expectations.
3. Re-score the same D0 scenarios in D4 after capability selection becomes real routing.
4. Reuse the same D0 scenarios in D7 to measure selection correctness, missed specialist rate, and unnecessary escalation rate.

## Characterization Proof

Requested suites:

1. `cd backend && ./.venv/bin/pytest tests/services/test_capability_registry_service.py tests/unit/test_situation_brief.py tests/unit/test_planning_strategy_compiler.py tests/core/test_llm_router_policy.py tests/unit/test_mirofish_wiring_finish.py -v`

See the completion note below for actual run status and outcome.

## Completion Note

- Runtime behavior changed: `no`
- Schema changed: `no`
- New production API or proto: `no`
- New D0 contract artifacts added: `yes`
- Characterization suites run: `yes`
- Characterization result: `49 passed, 1 failed`
- Failure observed during characterization:
  - `tests/unit/test_mirofish_wiring_finish.py::test_build_trend_overview_handles_sparse_week_buckets`
  - observed mismatch: expected `["上上周", "本周"]`, got `["上上周", "上周"]`
  - D0 read: this is an existing trend-label expectation issue in the characterization suite, not a regression introduced by the D0 audit artifacts
- Warnings observed during characterization:
  - recurring Pydantic v2 deprecation warnings for class-based `config` and `json_encoders`
  - recurring LangGraph `config` typing warnings in `app/agents/graph/workflow.py`
  - one SQLite/SQLAlchemy drop-order warning for cyclic foreign keys
  - one `RuntimeWarning` in `learning_report_agent.py` for an un-awaited mocked coroutine during test execution

Executed suite:

1. `cd backend && ./.venv/bin/pytest tests/services/test_capability_registry_service.py tests/unit/test_situation_brief.py tests/unit/test_planning_strategy_compiler.py tests/core/test_llm_router_policy.py tests/unit/test_mirofish_wiring_finish.py -v`
