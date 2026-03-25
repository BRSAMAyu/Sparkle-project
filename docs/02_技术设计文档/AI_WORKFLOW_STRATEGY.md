# AI Workflow Strategy (Hybrid Architecture)

## Purpose
This document captures the core consensus and turns it into executable guidance for implementation, review, and ongoing iteration. The target audience is internal coding agents and project owners.

## Core Decision
- We do NOT fully migrate to LangGraph.
- We adopt a hybrid architecture: self-built system remains the production backbone; LangGraph is an experimental and complex-flow validation layer.
- The technical moat is built on business understanding, data闭环, and user experience, not on a single framework.

## System Roles and Boundaries

### Self-Built System (Production Backbone)
Scope:
- Task cards, task decomposition, multi-stage planning, database writes.
- User journey and closed-loop feedback handling.
- Tool execution, policy, quota, and auditing.
- Metrics and data pipelines for prediction/feature extraction.

Non-negotiable:
- All writes to business DB and user state updates happen here.
- All critical SLA paths remain here.

### LangGraph (Experimental and Advanced Workflow Layer)
Scope:
- Complex collaboration workflows and HITL experiments.
- Validation of new multi-agent orchestration designs.
- Visual traceability and intermediate state logging in experiments.

Non-goals:
- No direct database writes in production.
- No exclusive ownership of core business flows.

## Workflow Vision (Target Behavior)
1) User request starts with intent alignment via a few turns of clarification.
2) System proposes a micro-task for fast execution and feedback.
3) User completes micro-task and submits feedback (explicit or implicit).
4) System adapts the plan, progressively generating staged plans and long-term goals.
5) At any point, user feedback can adjust the plan; no dead ends.
6) After each task, system predicts next state and recommended actions.

## Implementation Principles
- Business-first: use domain logic to drive tool sequences and plan updates.
- Closed-loop by default: each executed task triggers a feedback checkpoint.
- Progressive commitment: short tasks first, long plans later.
- Predictive continuity: use completion events to update user profile and next actions.
- Always explain "why" in outputs where user trust is needed.

## Execution Rules (Hard Constraints)
- Core execution path must stay in the self-built system.
- LangGraph outputs are advisory, not authoritative.
- Any plan/task created must be linked to user feedback and context version.
- Prediction must be logged with a confidence score and later validated.
 - Validator is mandatory for all execution paths (Fast or LangGraph).
 - Rollback is not assumed; compensation is required for irreversible actions.
 - Execution queue is a priority async pool; HITL tasks must not block the queue.

## Metrics (Business Outcomes First)
Primary:
- Task loop completion rate (generated -> completed -> feedback -> next action).
- Plan adaptation latency (feedback -> updated plan time).
- Prediction hit rate (next task recommended vs actual user choice).

Secondary:
- Time-to-first-microtask (from initial request).
- User-reported clarity/satisfaction after microtask.
- Agent collaboration success rate.

## Roadmap

### Short Term (Weeks 1-2) - Safety First
- Intent pre-processing + simple routing rules.
- Minimal Validator (schema + allowlist).
- Basic execution + feedback loop.
- Single state entry + context versioning.

### Mid Term (Weeks 3-6)
- LangGraph planner outputs ExecutablePlan.
- Grounding Validator 강화 (business rules + preflight).
- Version conflict handling.
 - HITL checkpoints in LangGraph experiments.

### Long Term (Quarter+)
- Mature user state prediction model.
- Build multi-stage planning that adapts to user trajectories.
- Formalize evaluation dashboards for closed-loop quality.

## Integration Contract (Between Systems)
Input to LangGraph:
- User query, context summary, current plan, recent feedback, goal state.

Output from LangGraph:
- ExecutablePlan (structured tool calls + fallbacks), rationale, confidence, HITL flags.

Validation in Self-Built System:
- Sanity checks, policy rules, data consistency.
- Apply or reject plan delta with audit logs.

## Risks and Mitigations
- Risk: Divergent states between systems.
  - Mitigation: self-built system is the single source of truth.
- Risk: HITL flow interrupts critical user path.
  - Mitigation: allow HITL only in non-blocking or experimental channels.
- Risk: Prediction quality is low initially.
  - Mitigation: start with heuristics, then iterate with data.
 - Risk: Irreversible actions cannot be rolled back.
  - Mitigation: compensation calls + double confirm + HITL for point-of-no-return.
 - Risk: Fast path bypasses safety checks.
  - Mitigation: all paths generate ExecutablePlan and pass Validator.
 - Risk: Queue blocked by long-running tasks or HITL.
  - Mitigation: priority async task pool, HITL moves to pending.

## Action Items (Immediate)
- Define ExecutablePlan schema and compensation policy.
- Add a feedback checkpoint node after tool execution.
- Add prediction hook to log and test "next-step" suggestions.
- Define LangGraph I/O contract with structured JSON schema.
 - Implement minimal Validator and make it mandatory for all paths.

## Open Questions
- What feedback formats are required (emoji, rating, text, implicit signals)?
- How do we quantify "achievement/fulfillment" reliably?
- What are the fallback strategies when predictions are wrong?

## Change Log
- 2025-01-XX: Initial consensus captured and structured.
