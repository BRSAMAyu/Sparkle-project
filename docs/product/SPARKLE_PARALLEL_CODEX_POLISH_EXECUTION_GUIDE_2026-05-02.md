# Sparkle Parallel Codex Polish Execution Guide

Date: 2026-05-02
Owner: Codex final integration reviewer
Scope: full-product closeout across Aurora, AI conversation, plans, tasks, community, knowledge graph, tools, rewards, sharing, mobile UX, backend chains, gateway, observability, and production readiness.

## 1. Purpose

This guide is the dispatch document for up to 30 parallel Codex agents. The goal is not to make isolated fixes. The goal is to make Sparkle feel like a coherent AI-native goal-realization OS: Aurora understands the user, plans become executable cards, cards flow into tasks/community/knowledge graph, progress becomes memory and motivation, and every user-visible loop has correction, recovery, observability, and polish.

Each agent should deeply inspect the codebase before editing. The task cards below describe target outcomes and acceptance standards, not a rigid file list. If an agent discovers a concrete code defect, it should fix it. If it discovers a bigger architecture gap, it should document the finding, implement the safe subset, and leave a precise handoff note.

## 2. Parallel Execution Rules

1. Create one branch per task: `codex/CXP-XX-short-name`.
2. Do not edit shared roadmap ledgers or this dispatch guide unless the task explicitly says so. Each agent writes its own report at `docs/product/parallel_closeout/CXP-XX_<short_name>_REPORT_2026-05-02.md`.
3. Keep commits focused. Commit and push at the end of the task.
4. Preserve user/other-agent changes. Never reset or revert unrelated work.
5. Use existing architecture first: Aurora runtime, DualCore, SGW, StateRegister, Card Protocol, community share services, Galaxy services, l10n, design system, existing tests.
6. Acceptance requires evidence: focused tests, analyzer/lint where practical, screenshots for UI-heavy work, and a report explaining what improved.
7. User experience is the primary standard. Passing tests is necessary but not sufficient.
8. Every agent must answer: "What does the user now feel or accomplish that they could not before?"

## 3. Global Product Quality Bar

Sparkle is accepted only when these are true across the product:

- Aurora is felt in normal use, not hidden in admin-only or shadow-only paths.
- Corrections change future behavior, not just telemetry.
- AI-generated cards are valid, actionable, shareable, and routable.
- Plan/task/community/knowledge graph/share/reward loops connect without dead ends.
- Empty, loading, error, offline, auth, and permission states are human and recoverable.
- Mobile UI is clean, calm, localized, accessible, responsive, and consistent with the design system.
- Backend contracts preserve privacy, visibility, soft-delete boundaries, block boundaries, idempotency, and observability.
- Production defaults are live where intended, guarded by kill switches where safety matters, and measurable in dashboards.

## 4. Agent Task Cards

### CXP-01 Aurora Everyday Presence

Mission: Make Aurora perceptible in ordinary chat and home usage without feeling theatrical or intrusive.

Target experience: The user should feel "it remembers where I am, notices when something changed, and speaks in a way that fits me today." Aurora should not appear only when a special panel opens.

Inspect and improve: Aurora runtime v1, control surface, home status band, chat metadata, comeback context, correction receipts, mode transitions.

Acceptance:
- Normal chat can surface Aurora state gently when it matters.
- Home status band explains the current judgment and lets the user correct it.
- Aurora does not overclaim certainty; uncertainty is visible and correctable.
- Report includes before/after user journey for first open, normal chat, and return after absence.

### CXP-02 Aurora L3 Core Session Flagship Flow

Mission: Turn L3 Core Session into a flagship "deep calibration" experience.

Target experience: When the user says "you still don't get me", Sparkle pauses normal advice, opens a short explicit Aurora session, asks a few precise questions, applies updates, summarizes what changed, and returns to background.

Inspect and improve: Core Session service, sheet UI, agenda rendering, pause/resume, freeform correction, SessionClosure application, status copy.

Acceptance:
- The flow has a clear beginning, agenda, interruption behavior, completion, and summary.
- Freeform correction text changes state/policy/directive/task behavior where appropriate.
- Idle pause and resume feel natural.
- Report includes the scenario: "不是没时间，是完全不会做".

### CXP-03 Aurora Wake, Proactivity, And Notification Judgment

Mission: Make proactive Aurora wakes useful, timely, and respectful.

Target experience: Wakes feel like a friend noticing the right moment, not a notification engine firing rules.

Inspect and improve: wake policy, wake scheduler, push scheduler, notification center, cooldowns, quiet hours, recall notifications, state-driven push.

Acceptance:
- Wakes have explainable reasons and user controls.
- Repeated wrong wakes reduce future wake confidence.
- Quiet hours, cooldown, do-not-disturb, and fatigue are respected.
- Report includes wake examples for risk, comeback, recall, and missed plan drift.

### CXP-04 DualCore And SGW Learning Loop

Mission: Deepen the DualCore -> SGW -> outcome -> future routing loop.

Target experience: If Sparkle chose the wrong stance, user corrections and outcomes should change the next stance.

Inspect and improve: DualCore router, RoutingOutcomeRecorder/Evaluator, ScaffoldingFSM, routing profile, Bayesian routing, route history.

Acceptance:
- Routing decisions are traceable to signals and evaluated later.
- SGW support level changes after repeated success/failure.
- The user can see a simple explanation for stance shifts.
- Report includes a causal trace from decision to outcome learning.

### CXP-05 Memory, Profile, And Return Context

Mission: Make memory retrieval feel personal, relevant, and safe.

Target experience: Returning users hear what matters from last time, not a random recent fact dump.

Inspect and improve: MemoryService, working memory, profile context, context pack/ranker, comeback context, correction receipts, memory admin.

Acceptance:
- Memories are ranked by relevance, correction history, recency, confidence, and goal linkage.
- Inferred memories remain distinguishable from confirmed facts.
- User can inspect or correct important memory claims.
- Report includes 30min, 8h, 2d, and 4d return scenarios.

### CXP-06 AI Conversation And Card Protocol

Mission: Ensure AI conversations reliably produce usable cards and structured actions.

Target experience: When AI proposes a task, plan, knowledge node, share, review, or practice item, the card works immediately.

Inspect and improve: chat orchestrator, response builder, entity cards, Card Protocol, widget actions, gateway protocol, mobile chat bubble/actions.

Acceptance:
- Cards validate against schema and never require hidden manual steps.
- Card actions route correctly across mobile features.
- Failed card actions show recoverable errors.
- Report includes task card, plan card, knowledge card, share card, and review card journeys.

### CXP-07 Plan Creation, Review, And Replanning

Mission: Make plan generation and replanning coherent from AI chat to executable schedule.

Target experience: A vague goal becomes a plan with milestones, tasks, review points, and adaptive changes when reality differs.

Inspect and improve: planning workflow, plan review service, adaptive replanner, plan APIs, mobile plan screens.

Acceptance:
- AI-generated plans are understandable, editable, and executable.
- Replanning preserves user intent and explains what changed.
- Plan review catches impossible schedules and missing prerequisites.
- Report includes one full goal-to-plan-to-replan journey.

### CXP-08 Daily Task Bar And Execution Flow

Mission: Make daily execution feel focused, doable, and continuous.

Target experience: The user always knows "what should I do next, why this, how long, and what happens after I finish or fail."

Inspect and improve: task provider/screens, execution service, task guide, task feedback, focus mode, offline/error states.

Acceptance:
- Next task is selected from plan state, Aurora state, deadline, difficulty, and user energy.
- Completing/skipping/failing a task updates plan, Aurora, achievements, and community/share eligibility.
- Offline queue and retry states are visible.
- Report includes daily start, task completion, task too hard, and skipped task paths.

### CXP-09 Knowledge Galaxy And Learning Graph

Mission: Make the knowledge graph useful for learning, not just a visualization.

Target experience: The graph explains prerequisites, weak nodes, next review, and how a task/translation/error connects to mastery.

Inspect and improve: Galaxy services, graph UI, knowledge services, node mastery, review urgency, graph monitor, CRDT/persistence.

Acceptance:
- Nodes have meaningful states and actions.
- Tasks, documents, vocabulary, errors, and seed content can create/update graph nodes.
- Users can understand why a node is recommended.
- Report includes graph creation, mastery update, and review recommendation flows.

### CXP-10 Seed Library And Content Capsules

Mission: Make the seed library a strong source of reusable growth content.

Target experience: Seeds feel like curated starting points that can become plans, tasks, knowledge nodes, simulations, or community shares.

Inspect and improve: seed library backend/mobile, seed bridge, seed content data, capsule generation, marketplace/share paths.

Acceptance:
- Seed browse/search/adopt flows are polished.
- Adopting a seed produces concrete next actions.
- Seeds can be shared or linked to goals safely.
- Report includes seed-to-plan and seed-to-community journeys.

### CXP-11 BGM, Vocabulary, Dictionary, And Translator Tools

Mission: Polish neglected learning tools so they become part of the growth OS.

Target experience: Looking up a word, translating, or saving vocabulary should connect to memory, knowledge graph, review, and tasks.

Inspect and improve: vocabulary service/UI, translation tool, translator UI, dictionary/BGM service, save-to-vocabulary, save-to-knowledge.

Acceptance:
- Lookup/translation errors are visible and recoverable.
- Saved words appear in vocabulary and can affect review/task recommendations.
- Translation outputs can create knowledge cards or vocabulary cards.
- Report includes lookup, translate, save, review, and graph-link flows.

### CXP-12 Error Book, Reviews, And Exam Sprint

Mission: Make mistakes turn into learning strategy.

Target experience: Wrong answers become diagnosed patterns, targeted review tasks, mastery updates, and Aurora strategy changes.

Inspect and improve: error book services/UI, reviews module routing, exam sprint diagnostic/review services, mastery sync, review urgency.

Acceptance:
- Error clusters become actionable review cards.
- Reviews module is reachable and useful.
- Exam sprint flows prioritize pass probability and weak prerequisites.
- Report includes wrong-answer-to-review-to-mastery journey.

### CXP-13 Community Feed And Social Learning

Mission: Make community feel real, filtered, safe, and useful.

Target experience: The user sees relevant squad/goal/following content, can share useful resources, and can adopt others' plans/tasks without confusion.

Inspect and improve: community feed scopes, groups, friendships, accountability partnerships, moderation, mobile community UI, backend visibility/block/soft-delete boundaries.

Acceptance:
- Feed tabs have distinct semantics.
- Shared cards render and route correctly.
- Blocked/private/deleted content never leaks.
- Report includes global, squad, goal mates, following, share, adopt, report/block paths.

### CXP-14 Sharing System And Entity Card Interop

Mission: Make sharing a first-class cross-product protocol.

Target experience: A plan, task, achievement, knowledge node, seed, vocabulary set, or review result can be shared and adopted with context intact.

Inspect and improve: share card service, entity_cards, community share UI, deep links, adoption endpoints, permissions.

Acceptance:
- Shared payloads preserve resource type, owner, visibility, preview, and adoption action.
- Recipients can adopt without corrupting original owner data.
- Expired/revoked shares degrade gracefully.
- Report includes at least six shareable resource types.

### CXP-15 Accountability, Partners, Squads, And Goal Mates

Mission: Make social accountability motivating without becoming pressure spam.

Target experience: Partners and squads support progress with clear commitments, check-ins, boundaries, and gentle nudges.

Inspect and improve: accountability APIs/services/tasks, partner progress, group recommendations, social signal bridge, mobile surfaces.

Acceptance:
- Check-ins and reminders respect cadence and user preferences.
- Partner/squad signals can inform Aurora without overstepping privacy.
- Achievements and milestones can be celebrated or kept private.
- Report includes invite, accept, check-in, missed check-in, and milestone flows.

### CXP-16 Achievements, Photon, Shop, And Rewards

Mission: Make rewards reinforce growth rather than feel decorative.

Target experience: Achievements explain what behavior was recognized, grant meaningful visual/progression feedback, and can be shared.

Inspect and improve: achievement engine, achievement mobile UI, photon balance, shop, inventory/equipment, reward observability.

Acceptance:
- Achievements are triggered by real events and deduped.
- Photon/shop/inventory state remains consistent.
- Rewards are accessible, localized, and not visually noisy.
- Report includes task completion, streak, community, knowledge mastery, and Aurora calibration achievements.

### CXP-17 Visual Elements, Color System, And Identity

Mission: Make the visual progression system beautiful, coherent, and emotionally resonant.

Target experience: Colors, visual elements, achievement visuals, and identity surfaces feel like the user's growth becoming visible.

Inspect and improve: visual_elements feature, design system, achievement visuals, share posters, profile surfaces, color tokens.

Acceptance:
- Visual elements use consistent tokens and work in light/dark modes.
- Generated/earned visuals are inspectable and shareable.
- UI avoids one-note palettes and maintains readability.
- Report includes screenshots or screenshot instructions for core visual states.

### CXP-18 Home Dashboard And First-Viewport Clarity

Mission: Make the home dashboard the user's calm command center.

Target experience: Within five seconds, the user knows current state, next action, Aurora's judgment, progress, and any risk.

Inspect and improve: dashboard provider/screen, status band, daily task, progress cards, skeleton/error/empty states.

Acceptance:
- First viewport has no redundant or dead cards.
- Aurora status, next task, and progress do not compete visually.
- Refresh/error/auth states are polished.
- Report includes new user, active user, returning user, and error-state dashboard paths.

### CXP-19 Onboarding, Cold Start, And North Star Journey

Mission: Make a new user reach their first meaningful plan and task quickly.

Target experience: Sparkle learns enough to help without interrogating the user, then shows immediate value.

Inspect and improve: onboarding, traits cold start, galaxy bootstrap, first plan, cold-start route transition, north-star metrics.

Acceptance:
- First session produces a credible goal profile, plan, task, and Aurora baseline.
- User can skip or correct onboarding assumptions.
- North-star events are tracked.
- Report includes first 10 minutes and first 24 hours.

### CXP-20 Reports, Insights, Theater, And Progress Narratives

Mission: Make reflection surfaces tell the truth and motivate the next action.

Target experience: Reports explain what changed, why it matters, and what to do next.

Inspect and improve: insights, reports, progress narrative, prediction theater, weekly digest, growth dashboard.

Acceptance:
- Reports use real evidence, not generic praise.
- Visualizations are readable and linked to actions.
- Aurora corrections and plan outcomes appear in narrative when relevant.
- Report includes weekly report, insight detail, and prediction theater paths.

### CXP-21 Documents, Files, RAG, And Source Tray

Mission: Make uploaded materials become trustworthy context and actions.

Target experience: The user can add a document, ask questions, see sources, create tasks/knowledge nodes, and correct bad retrieval.

Inspect and improve: document/file features, group file service, RAG/context pack, source tray, material retrieval tools, citation feedback.

Acceptance:
- Source attribution is visible and correctable.
- Retrieval failures do not pollute long-term memory.
- Documents can produce knowledge and task cards.
- Report includes upload, ask, cite, correct, and share-material flows.

### CXP-22 Calendar, Schedule, And Time Awareness

Mission: Make time awareness operational across plans, tasks, pushes, and Aurora.

Target experience: Sparkle understands available time, deadlines, calendar pressure, and recovery windows.

Inspect and improve: calendar feature, execution schedule, smart schedule, task due dates, deadline pressure signals, push timing.

Acceptance:
- Task durations and deadlines produce realistic next actions.
- Time corrections alter future estimates.
- Calendar conflicts are visible and actionable.
- Report includes today planning, deadline crunch, missed task, and reschedule flows.

### CXP-23 Realtime Chat, Gateway, Offline, And Multi-Device

Mission: Make realtime communication reliable and understandable.

Target experience: Messages stream smoothly, offline state is visible, retries are safe, and returning on another device is coherent.

Inspect and improve: Go gateway, WebSocket services, mobile chat WebSocket, offline queue, sequence/request IDs, reconnect behavior.

Acceptance:
- Partial responses do not vanish silently.
- Retry/resume does not duplicate completed actions.
- Multi-device state shows latest Aurora/session summary even without strong locking.
- Report includes network drop, app background, duplicate send, and cross-device return.

### CXP-24 Mobile Design System, i18n, Accessibility

Mission: Bring the whole app closer to launch polish.

Target experience: The app feels consistent, localized, accessible, and calm across primary surfaces.

Inspect and improve: l10n, hardcoded copy, semantics, color/font tokens, high-traffic screens.

Acceptance:
- Core flows avoid hardcoded user-facing strings.
- Buttons, cards, chips, and failure states use design-system patterns.
- Important controls have semantics labels.
- Report includes screenshots or detailed QA notes across light/dark and zh/en.

### CXP-25 Backend Contract, Privacy, And Safety Boundaries

Mission: Ensure cross-system contracts protect user data and behavior.

Target experience: Users can trust that private/deleted/blocked/corrected data is respected everywhere.

Inspect and improve: API schemas, auth, privacy redaction, visibility filters, soft-delete guards, correction provenance, compliance services.

Acceptance:
- Shared/social surfaces enforce visibility and block boundaries.
- PII and sensitive state do not leak into logs or public payloads.
- Corrections do not become permanent facts without confidence/provenance.
- Report lists contract risks fixed and remaining.

### CXP-26 Observability, Metrics, Dashboards, And Runbooks

Mission: Make production behavior observable and operable.

Target experience: Operators can answer whether Aurora, chat, tasks, community, and pushes are working and helping.

Inspect and improve: metrics, Grafana, Prometheus rules, health endpoints, Celery tasks, alerts, runbooks.

Acceptance:
- Key loops have metrics: decision, action, outcome, correction, failure.
- Dashboards reveal user-impacting regressions.
- Runbooks explain what to do when metrics go bad.
- Report includes dashboard/query additions and operational scenarios.

### CXP-27 Performance, Cost, And Budget Governance

Mission: Keep the complete experience fast and affordable.

Target experience: Users do not feel slowness, and expensive Aurora/RAG paths are justified by value.

Inspect and improve: cost controller, RAG budgets, Aurora energy/cost, caching, context pack size, mobile rebuilds.

Acceptance:
- Expensive paths have preflight and actual spend recording.
- Slow states have graceful progress UI.
- High-traffic screens avoid unnecessary reload/rebuild loops.
- Report includes latency/cost risks and evidence.

### CXP-28 Admin, QA, And Internal Control Surfaces

Mission: Give reviewers and operators enough control to validate the system.

Target experience: Internal reviewers can inspect Aurora flags, memory, traces, routing, community moderation, and user-impacting errors.

Inspect and improve: memory admin, graph monitor, health production, telemetry endpoints, moderation/admin surfaces.

Acceptance:
- Important live/shadow/off switches are visible and auditable.
- Admin actions are safe and logged.
- QA can reproduce a user journey from trace IDs.
- Report includes reviewer workflows and missing controls fixed.

### CXP-29 End-To-End North Star Journey

Mission: Validate and polish the complete product story across systems.

Target experience: A zero-base user can onboard, create a plan, execute tasks, use tools, receive Aurora calibration, share progress, and improve over seven days.

Inspect and improve: any system needed to make this journey coherent.

Acceptance:
- Define and run a full scripted journey.
- Every dead end is fixed or documented with precise owner.
- Journey evidence includes API/mobile states and user-visible copy.
- Report becomes the canonical final E2E acceptance narrative.

### CXP-30 Final Integration Readiness And Conflict Map

Mission: Prepare all parallel work for final merge and unified polish.

Target experience: After all agents finish, the final integrator can merge without guessing intent or losing cross-system coherence.

Inspect and improve: reports from CXP-01 through CXP-29, overlapping files, API contract conflicts, migration conflicts, test gaps.

Acceptance:
- Produce a conflict map by subsystem and file cluster.
- Identify duplicate implementations, incompatible assumptions, and missing cross-links.
- Create a final integration checklist for Codex reviewer.
- This task should run near the end, not at the start.

## 4A. Full Copy-Paste Dispatch Prompts

The short cards above are the index. This section is the actual dispatch package. Give one complete prompt to each Codex agent. Agents should keep autonomy over implementation details, but each agent must be explicit about the user experience it is trying to create, the systems it inspected, the contracts it changed, and the evidence that the chain now works.

### Shared Prefix For Every Agent

Copy this prefix before the task-specific prompt:

```text
You are one of 30 parallel Codex agents closing out Sparkle for final product readiness. Work in /Users/brsama/code/GitHub/Sparkle-project. Create your own branch named codex/CXP-XX-short-name. Do not reset, revert, or overwrite unrelated user or other-agent changes. Read AGENTS.md and follow the repository workflow. Use Roadmap v3 and the Tracker as context, but do not edit shared ledgers unless your task explicitly requires it. Your output is not "some tests passed"; your output is a coherent product chain that improves what the user can feel, accomplish, recover from, or trust.

Before editing, inspect the current code deeply. Prefer existing architecture over new duplicate systems. If you discover a small concrete bug, fix it. If you discover a larger architecture risk that cannot be safely solved inside your task, document it precisely and implement the safe subset. Do not only add tests. Do not only write docs. Do not leave a feature in shadow/off mode when the product intent is that it is live, unless a safety kill switch genuinely requires it.

At the end, create docs/product/parallel_closeout/CXP-XX_<short_name>_REPORT_2026-05-02.md with the report template from this guide. Run focused verification. Commit and push your branch. Your report must answer: what user journey is better now, what systems were connected, what evidence proves it, and what residual risk remains.
```

### Full Prompt CXP-01 — Aurora Everyday Presence

```text
Task: CXP-01 Aurora Everyday Presence

Mission: Make Aurora perceptible in ordinary home and chat usage without turning it into a gimmick. The user should feel that Sparkle notices context, remembers the active struggle, explains uncertainty, asks for correction when needed, and quietly changes how it helps. Do not build a separate "Aurora demo"; make Aurora show up in normal surfaces.

Start by reading: docs/product/愿景验收清单, docs/product/SPARKLE_ROADMAP_v3_2026-04-28.md, docs/product/SPARKLE_ROADMAP_v3_TRACKER_2026-04-28.md, this dispatch guide, and recent Aurora verification/SGW docs if present. Then inspect likely starting points: backend/app/aurora/runtime_v1, backend/app/services/aurora_control_surface_service.py, backend/app/orchestration/context_builder.py, backend/app/orchestration/ux_envelope.py, backend/app/orchestration/response_builder.py, mobile/lib/features/home, mobile/lib/features/chat, and Aurora telemetry/correction services.

Target experience: when a user opens the app, Aurora has a compact current-state judgment that is explainable and correctable. In chat, Aurora can say "I may be misreading this" or "this looks different from last time" when evidence supports it. It should not overclaim mind-reading. It should surface uncertainty and ask for confirmation. Corrections must feed future behavior, not just produce a one-off message.

Implementation freedom: improve backend payloads, mobile display, copy, telemetry, routing, or state linkage as needed. Use existing Aurora runtime, control surface, DualCore, CorrectionFeedbackProcessor, and UX envelope. Avoid adding a second parallel Aurora state model.

Acceptance evidence: include before/after journeys for first open, ordinary chat, status-band correction, and return after absence. Show which signals drive the state, how the user corrects it, and how later copy/route/next action changes. Run focused backend/mobile tests or analyzer slices relevant to touched code. If screenshots are not practical, include exact manual QA steps and expected UI copy.
```

### Full Prompt CXP-02 — Aurora L3 Core Session Flagship Flow

```text
Task: CXP-02 Aurora L3 Core Session Flagship Flow

Mission: Turn L3 Core Session into the flagship "you finally understood me" calibration flow. This is one of Sparkle's deepest moat experiences. If a user says "你没懂我" or "不是没时间，是完全不会做", the system should stop giving generic advice, open an explicit short calibration agenda, ask precise questions, apply updates, summarize what changed, and then return to normal support.

Start by reading the Aurora session continuity docs, Aurora complete-body plan, Roadmap v3 tracker, and any core-session reports. Inspect backend/app/aurora/core_session.py, backend/app/aurora/runtime_v1/l3_full_core.py, backend/app/aurora/runtime_v1/service.py, backend/app/aurora/runtime_v1/state.py, backend/app/aurora/runtime_v1/correction_feedback.py, backend/app/orchestration/context_builder.py, mobile/lib/features/aurora, mobile/lib/features/home, and mobile/lib/features/chat.

Target experience: Core Session has an explicit beginning, agenda, multi-message flow, pause/resume, freeform correction, closure, and user-visible summary. The agenda should be backend-authoritative, not just UI copy. It should support interruption: if the user asks an unrelated urgent question, answer it and preserve the calibration agenda with a natural "we can continue where we paused" path. Closure must apply real state_patches, policy_changes, directives_to_regenerate, or task/plan changes where appropriate.

Implementation freedom: adjust data models, API contracts, mobile sheet behavior, persistence, or telemetry. Reuse AuroraCaseFile, AuroraAgenda, SessionClosure, correction feedback, memory/profile state, and existing persistence. If a safe migration is needed, add it with tests.

Acceptance evidence: prove the scenario "你又没懂，我不是没时间，是完全不会做" changes at least one durable behavior. Include idle pause/continue/summary behavior, Redis-miss or resume behavior if relevant, and a closure summary that tells the user exactly what changed. Verify with focused unit/integration/mobile tests or clear manual QA.
```

### Full Prompt CXP-03 — Aurora Wake, Proactivity, And Notification Judgment

```text
Task: CXP-03 Aurora Wake, Proactivity, And Notification Judgment

Mission: Make proactive Aurora wake behavior useful, explainable, and respectful. The goal is not "more notifications"; it is the feeling that Sparkle notices the right moment like a good friend, while backing off quickly when it is wrong.

Start by reading the roadmap/tracker, Aurora wake and push-related docs, and the latest audit reports. Inspect backend/app/aurora/runtime_v1/wake_policy.py, wake_scheduler.py, l4_async.py, backend/app/services/push_scheduler.py, push_service.py, state_driven_push_service.py, notification_center_service.py, notification_push_service.py, push feedback services, mobile notification surfaces, and settings/preferences related to quiet hours or push consent.

Target experience: wake reasons are specific and user-understandable: risk drift, missed plan, returning after silence, useful recall, accountability moment, or calibration opportunity. The user can see why a wake happened and correct it. Wrong or ignored wakes reduce future confidence. Quiet hours, cooldown, fatigue, and notification preferences are respected.

Implementation freedom: improve wake scoring, cooldown logic, telemetry, copy, settings, push payloads, feedback ingestion, or dashboards. Keep Aurora live by default where intended, but guard unsafe wake categories with kill switches and explicit user controls.

Acceptance evidence: include examples for at least four wake types: risk, comeback, recall, and plan drift. Show how a negative user response affects future wake behavior. Verify push scheduling logic with tests where practical; include manual QA for mobile notification copy and deep link behavior.
```

### Full Prompt CXP-04 — DualCore And SGW Learning Loop

```text
Task: CXP-04 DualCore And SGW Learning Loop

Mission: Make the DualCore routing and scaffolding/growth wheel loop self-correcting. If Sparkle picks the wrong stance, gives too much help, gives too little help, or misunderstands the user's metacognitive state, later corrections and outcomes should change the next routing decision.

Start by reading DualCore, SGW, Aurora closed-loop, and roadmap docs. Inspect backend/app/orchestration/dual_core_router.py, routing_engine.py, routing_parameter_registry.py if present, schemas.py, context_builder.py, orchestration_trace.py, backend/app/scaffolding/scaffolding_fsm.py, backend/app/services/routing_outcome_service.py, route_history_service.py, behavioral/outcome services, and correction_feedback paths.

Target experience: routing is no longer a black-box one-way prompt modulation. A decision should have signal_scores, a routing trace, scaffolding zone, and a later outcome. Repeated failure should make future support more concrete or change strategy; repeated success should reduce unnecessary scaffolding. The user-facing explanation should be short and humble, not diagnostic jargon.

Implementation freedom: refine signal consumption, outcome recording, evaluation windows, telemetry, decision schema, prompt rendering, or admin trace views. Do not duplicate the router. Strengthen the existing path from signal -> decision -> response -> outcome -> future decision.

Acceptance evidence: include one causal trace from a user signal to a route decision to a later outcome and a changed future decision. Add/adjust focused tests for signal scores, outcome recording/evaluation, correction feedback, and trace continuity.
```

### Full Prompt CXP-05 — Memory, Profile, And Return Context

```text
Task: CXP-05 Memory, Profile, And Return Context

Mission: Make Sparkle's memory feel relevant, safe, and alive. Returning users should not hear a random recap. They should hear the few things that matter now: unfinished questions, recent corrections, active goals, risks, relationships, and changes since last time.

Start by reading memory/profile/return-context docs and the vision checklist. Inspect backend/app/services/memory_service.py, memory_rank_policy_service.py, working_memory_consolidation_service.py, profile_context_service.py, user_insight_* services, backend/app/orchestration/context_builder.py, context_pack.py, context_ranker.py, backend/app/working_memory/service.py, memory_admin APIs, mobile memory/profile surfaces, and Aurora correction receipts.

Target experience: returning context follows tiers: under 30 minutes silent, under 8 hours light continuation, 8 hours to 3 days personalized return, over 3 days debrief. Memory claims should distinguish confirmed facts, inferred preferences, and temporary signals. The user must be able to correct important memory claims, and corrections must reduce future repetition of bad assumptions.

Implementation freedom: improve retrieval ranking, provenance, payloads, user-visible copy, correction flows, admin inspection, or tests. Use existing memory/profile architecture and avoid creating another memory store unless absolutely necessary.

Acceptance evidence: demonstrate 30min, 8h, 2d, and 4d return scenarios. Show selected memories, why they were selected, and how they appear in home/chat/Core Session. Include tests for ranking/provenance or manual QA with exact payloads.
```

### Full Prompt CXP-06 — AI Conversation And Card Protocol

```text
Task: CXP-06 AI Conversation And Card Protocol

Mission: Make AI conversation produce real, valid, routable product objects. When the assistant proposes a task, plan, knowledge node, review, community share, or vocabulary item, the card should work immediately and safely. The user should not feel that the AI output is decorative text.

Start by reading Card Protocol docs, roadmap tracker, and recent card/share reports. Inspect backend/app/orchestration/response_builder.py, orchestrator.py, ux_envelope.py, backend/app/signals/task_card_protocol.py, backend/app/services/card_protocol, share_card_service.py, task/plan/knowledge/review services, proto/gateway message contracts, mobile/lib/features/chat, mobile entity card widgets, navigation, and action handlers.

Target experience: chat can generate actionable cards with clear labels, valid schemas, permissions, deep links, loading states, error states, and adoption/commit actions. Internal semantic tokens should not leak into user-visible chat text. Failed actions should be recoverable and not silently disappear.

Implementation freedom: improve schema validation, action routing, mobile widgets, backend payload generation, gateway transport, idempotency, or tests. If you find duplicate card models, document and consolidate safely.

Acceptance evidence: include task card, plan card, knowledge card, share card, review card, and vocabulary/seed card if present. Verify at least schema validation plus one mobile route/action path. Report any card type still impossible to make production-ready.
```

### Full Prompt CXP-07 — Plan Creation, Review, And Replanning

```text
Task: CXP-07 Plan Creation, Review, And Replanning

Mission: Make plan generation and replanning feel like a competent coach. A vague user goal should become milestones, tasks, review points, and a realistic schedule. When reality changes, Sparkle should explain the replan instead of silently mutating the user's plan.

Start by reading planning and growth-loop docs. Inspect backend/app/orchestration/planning_workflow.py, plan_review_service.py, adaptive_replanner.py, planning_strategy_compiler.py, plan_revision_summary.py, backend/app/services/plan_service.py, plan_state_service.py, plan_progress_service.py, plan_outcome_service.py, plan_execution_validator.py, mobile plan screens/providers, task integration, calendar/schedule integration, and chat card creation.

Target experience: the user can go from "I need to pass X" or "I want to learn Y" to an editable plan with prerequisites, daily tasks, risk flags, and review cadence. Replanning preserves intent, explains tradeoffs, and updates tasks/calendar/Aurora context. Impossible schedules should be caught before they become fake confidence.

Implementation freedom: refine backend planning logic, validation, summaries, mobile UI, chat cards, or telemetry. Use existing services rather than adding a second planner.

Acceptance evidence: provide a full goal -> plan -> first task -> reality change -> replan journey. Include tests for plan review/replan logic or manual API/mobile traces. Show what is user-visible before and after replanning.
```

### Full Prompt CXP-08 — Daily Task Bar And Execution Flow

```text
Task: CXP-08 Daily Task Bar And Execution Flow

Mission: Make daily execution the calm center of action. The user should always know what to do next, why this task matters, how long it should take, how to mark difficulty/failure, and what changes afterward.

Start by reading task/execution roadmap items and recent audit reports. Inspect mobile/lib/features/task, task providers, execution screens/copy, backend/app/services/execution_service.py, execution_ingestor.py, execution_learning_service.py, task_guide_service.py, task_feedback_service.py, next_action_selection_service.py, focus_service.py, plan/task APIs, Aurora state influence, offline queue, and achievement/task event consumers.

Target experience: next action selection considers active plan, deadline, prerequisites, Aurora state, user energy, difficulty, and history. Completing, skipping, failing, or saying "too hard" should update plan state, learning graph, Aurora profile, achievements, reports, and possibly community/accountability signals. Offline and retry states must be visible.

Implementation freedom: improve selection, feedback, state propagation, mobile UI, error handling, offline behavior, or telemetry. Avoid making task state a frontend-only illusion.

Acceptance evidence: include daily start, task completion, task too hard, skipped task, offline completion, and retry paths. Verify backend state changes and mobile user-visible result.
```

### Full Prompt CXP-09 — Knowledge Galaxy And Learning Graph

```text
Task: CXP-09 Knowledge Galaxy And Learning Graph

Mission: Make the Knowledge Galaxy operational, not just pretty. The user should understand prerequisites, weak nodes, next reviews, and why Sparkle recommends a concept or task.

Start by reading knowledge graph design docs and roadmap tracker. Inspect backend/app/services/galaxy, galaxy_service.py, graph_knowledge_service.py, knowledge_integration_service.py, galaxy_event_consumer.py, galaxy_execution_consumer.py, review_urgency_service.py, graph monitor APIs, mobile Galaxy screens/widgets, CRDT/persistence code, and integrations from tasks, documents, translations, errors, and seed content.

Target experience: graph nodes have meaningful states: unknown, learning, weak, ready for review, mastered, connected to goal, or blocked by prerequisite. Actions should create/update nodes from real product events. Users should understand why a node appears and what to do next.

Implementation freedom: improve backend graph state updates, event listeners, UI affordances, edge labels, review recommendation, or instrumentation. Do not break existing graph persistence.

Acceptance evidence: include graph creation from a document/translation/error, mastery update from task/review, and review recommendation. Provide tests or trace evidence that product events actually update the graph.
```

### Full Prompt CXP-10 — Seed Library And Content Capsules

```text
Task: CXP-10 Seed Library And Content Capsules

Mission: Make the seed library a reusable growth-content engine. Seeds should not be static content; they should become plans, tasks, knowledge nodes, simulations, or shareable capsules.

Start by reading seed/capsule docs and the roadmap tracker. Inspect backend/app/services/seed_library_service.py, learning/seed_bridge.py, seed_content models/data, capsule_generation_service.py, capsule_generation_job.py, content_quality_evaluator.py, mobile seed library features, share card services, community adoption paths, and knowledge/plan/task integrations.

Target experience: a user can browse/search a seed, understand who it is for, adopt it into a plan or task, link it to a knowledge node, and share it with context. Adoption should create concrete next actions without polluting another user's original data. Bad or irrelevant seeds should have feedback paths.

Implementation freedom: improve data model, adoption service, search/filter, mobile UI, card generation, quality scoring, or share/adopt links. Keep permissions and provenance clear.

Acceptance evidence: demonstrate seed browse/search, seed-to-plan, seed-to-task, seed-to-knowledge, and seed-to-community share. Verify at least one backend adoption path and one mobile route/action.
```

### Full Prompt CXP-11 — BGM, Vocabulary, Dictionary, And Translator Tools

```text
Task: CXP-11 BGM, Vocabulary, Dictionary, And Translator Tools

Mission: Polish the neglected learning tools so they become part of the growth OS. Looking up a word, translating a sentence, or saving vocabulary should feed memory, graph, review, and tasks rather than stay isolated.

Start by reading the roadmap and any BGM/vocabulary/translation docs. Inspect backend/app/services/vocabulary_service.py, translation/dictionary tools, learning asset services, graph integration, review services, mobile vocabulary/dictionary/translator screens, BGM-related files, save-to-vocabulary flows, error handling, and l10n/copy for tool states.

Target experience: a learner can look up or translate something, understand the result, save it, connect it to a goal/knowledge node, schedule review, and later see it affect recommendations. Tool failures should explain what happened and offer retry or fallback. Saved items should not disappear into a database with no visible loop.

Implementation freedom: improve tool APIs, mobile UX, card creation, graph/review integration, offline/error states, or tests. Avoid only beautifying UI without connecting data.

Acceptance evidence: include lookup, translate, save, review, and graph-link flows. Show where the saved artifact appears later. Verify with service tests or manual API/mobile traces.
```

### Full Prompt CXP-12 — Error Book, Reviews, And Exam Sprint

```text
Task: CXP-12 Error Book, Reviews, And Exam Sprint

Mission: Make mistakes become strategy. Wrong answers should produce diagnosed patterns, targeted review tasks, mastery updates, and Aurora strategy adjustments.

Start by reading review/error/exam roadmap sections. Inspect backend/app/services/error_book_service.py, error_book_mastery_sync_service.py, error_replan_bridge.py, exam_sprint_diagnostic_service.py, exam_sprint_review_service.py, review_history_service.py, review_appeal_service.py, Galaxy review urgency, mobile review/error/exam screens, routing/navigation, and task/card integrations.

Target experience: after a wrong answer or failed review, Sparkle identifies the likely misconception, groups related errors, recommends a review path, updates mastery, and changes next tasks. Exam sprint should prioritize pass probability, weak prerequisites, and time constraints. Reviews must be reachable in the app and not feel like hidden backend work.

Implementation freedom: improve clustering, diagnostics, UI, routing, cards, mastery sync, or Aurora feedback. Do not create generic review copy detached from real errors.

Acceptance evidence: include wrong-answer -> error cluster -> review card -> mastery update -> plan/task adjustment. Verify with tests or traceable service calls.
```

### Full Prompt CXP-13 — Community Feed And Social Learning

```text
Task: CXP-13 Community Feed And Social Learning

Mission: Make community feel real, filtered, safe, and useful. Feed tabs must have distinct semantics, shared cards must work, and privacy boundaries must be enforced.

Start by reading community roadmap sections and recent review findings. Inspect backend/app/api/v1/community.py, community_service.py, community_advanced_service.py, community_signal_bridge.py, friend/accountability/group services, visibility/block/soft-delete models, mobile community providers/screens/widgets, share card widgets, report/block flows, and tests.

Target experience: the user can switch between global, squad, goal mates, and following and see genuinely different feeds. Shared cards preserve context and route correctly. Blocking, private visibility, soft deletion, moderation, and group membership boundaries are respected. Empty/error states should explain what to do next.

Implementation freedom: improve backend queries, service semantics, mobile filters, copy, share/adopt actions, tests, or moderation feedback. Do not accept visual-only tabs or swallowed feed failures.

Acceptance evidence: include global/squad/goal_mates/following examples, share/adopt path, report/block path, and visibility boundary tests or API traces.
```

### Full Prompt CXP-14 — Sharing System And Entity Card Interop

```text
Task: CXP-14 Sharing System And Entity Card Interop

Mission: Make sharing a first-class product protocol. A plan, task, achievement, knowledge node, seed, vocabulary set, or review result should be shareable and adoptable with context, permissions, and graceful failure.

Start by reading Card Protocol, community, and sharing docs. Inspect backend/app/services/share_card_service.py, backend/app/services/card_protocol, entity card schemas, community share endpoints, deep-link handling, mobile share card widgets, capsule/achievement/knowledge/task/plan/vocabulary/review card producers, permission checks, and adoption endpoints.

Target experience: shared payloads include resource type, owner, visibility, preview, source receipt, adoption action, and expiry/revocation behavior. Recipients can adopt without mutating the original owner's data. Private or revoked shares should degrade gracefully with clear copy.

Implementation freedom: improve schemas, adoption services, UI widgets, deep links, visibility enforcement, or tests. Consolidate duplicate share card representations if safe.

Acceptance evidence: demonstrate at least six shareable resource types and one revoked/expired/private case. Include schema validation and one mobile navigation/adoption path.
```

### Full Prompt CXP-15 — Accountability, Partners, Squads, And Goal Mates

```text
Task: CXP-15 Accountability, Partners, Squads, And Goal Mates

Mission: Make social accountability motivating without becoming pressure spam. Partners, squads, and goal mates should support commitments, check-ins, milestones, and recovery with clear privacy boundaries.

Start by reading accountability/social roadmap sections. Inspect backend/app/api/v1/accountability.py, accountability services/tasks, accountability_notification_service.py, friend_match_service.py, group_recommendation_service.py, social_signal_bridge.py, community relationships, achievement/social signals, mobile accountability/community surfaces, and notification preferences.

Target experience: users can invite/accept partners, set a check-in cadence, see commitments, respond to missed check-ins, celebrate milestones, and control what is shared. Aurora can use social signals in aggregate or with consent, but should not expose private partner data or guilt-trip the user.

Implementation freedom: improve relationship semantics, notification cadence, check-in UI, privacy controls, task/achievement integration, or tests. Preserve block/visibility boundaries.

Acceptance evidence: include invite, accept, check-in, missed check-in, milestone celebration, privacy toggle, and Aurora/social signal use. Verify with service tests or API/mobile traces.
```

### Full Prompt CXP-16 — Achievements, Photon, Shop, And Rewards

```text
Task: CXP-16 Achievements, Photon, Shop, And Rewards

Mission: Make rewards reinforce real growth rather than feel decorative. Achievements should explain the behavior recognized, grant consistent rewards, and create tasteful moments users may share.

Start by reading achievement/reward roadmap sections. Inspect backend/app/services/achievement_engine.py, achievement_event_consumer.py, achievement_reward_observability.py, photon_service.py, shop_service.py, inventory_service.py, equipment_service.py, models/shop.py, mobile achievement/reward/shop surfaces, task/community/knowledge/Aurora event producers, and share card integration.

Target experience: achievements trigger from real events, are deduped/idempotent, tell the user why they happened, and connect to photon/shop/inventory state. Rewards should be accessible, localized, and visually restrained. Aurora calibration, streaks, mastery, community contribution, and plan progress should be eligible for meaningful achievements.

Implementation freedom: improve event handling, reward consistency, UI/copy, shareability, observability, or tests. Do not create rewards that can be duplicated by retries.

Acceptance evidence: include task completion, streak, knowledge mastery, community share, and Aurora calibration achievement paths. Verify balance/inventory consistency and dedupe behavior.
```

### Full Prompt CXP-17 — Visual Elements, Color System, And Identity

```text
Task: CXP-17 Visual Elements, Color System, And Identity

Mission: Make Sparkle's visual growth language coherent, beautiful, and emotionally resonant. Visual elements should make the user's growth visible without harming readability or becoming noisy decoration.

Start by reading design/vision docs and visual element roadmap items. Inspect mobile design tokens/theme, visual_elements feature, profile surfaces, achievement visuals, share posters/cards, color element services if present, light/dark mode behavior, accessibility contrast, and any generated visual assets.

Target experience: earned visual elements, colors, identity surfaces, achievements, and share posters feel connected. They should work in light/dark mode, avoid one-note palettes, preserve readability, and have clear provenance: why did I get this visual state?

Implementation freedom: improve tokens, UI components, visual state mapping, profile/share surfaces, responsive layout, or screenshots. Prefer existing design system; do not create an isolated style island.

Acceptance evidence: include screenshot instructions or actual screenshots for core states: new user, active progress, achievement earned, share poster/card, dark mode. Document token/design changes and accessibility checks.
```

### Full Prompt CXP-18 — Home Dashboard And First-Viewport Clarity

```text
Task: CXP-18 Home Dashboard And First-Viewport Clarity

Mission: Make the home dashboard a calm command center. Within five seconds, the user should know current state, next action, Aurora's judgment, progress, and any risk.

Start by reading home/dashboard roadmap items and Aurora presence docs. Inspect mobile/lib/features/home/presentation/screens/dashboard_screen.dart, home providers, dashboard services, status band telemetry, daily task widgets, progress cards, skeleton/error/empty states, routing to chat/Aurora/task/plan/community, and backend dashboard_service/growth_dashboard_service.

Target experience: first viewport should not be a pile of cards. It should prioritize next action, Aurora state, progress, and risk. Every visible item should either explain, act, or route. Error/auth/offline/loading states must feel intentional. Correction chips must collect the right data and never leak internal semantic tokens to chat.

Implementation freedom: improve layout, data aggregation, copy, telemetry, navigation, or backend dashboard payload. Keep design calm and production-like.

Acceptance evidence: include new user, active user, returning user, offline/error, and Aurora correction dashboard paths. Provide screenshots or exact QA steps for light/dark and zh/en if possible.
```

### Full Prompt CXP-19 — Onboarding, Cold Start, And North Star Journey

```text
Task: CXP-19 Onboarding, Cold Start, And North Star Journey

Mission: Make a new user reach first meaningful value quickly. Sparkle should learn enough to help without interrogating the user, then produce a credible first goal profile, plan, task, and Aurora baseline.

Start by reading onboarding/cold-start/north-star docs. Inspect onboarding flows, traits_coldstart_service.py, traits_merge_service.py, traits_nlp_observer_service.py, profile translators, first plan/task generation, Galaxy bootstrap, north_star_metrics_service.py, mobile onboarding screens/providers, auth/session transitions, and first-run dashboard.

Target experience: in the first 10 minutes, the user can state a goal, correct assumptions, see a first plan/task, and understand what Sparkle will remember. In the first 24 hours, the app can measure first task completion, return, correction, and plan engagement. Skipping onboarding should still produce a safe default.

Implementation freedom: improve questions, branching, profile creation, first plan/task generation, metrics, UI, or recovery from partial onboarding. Do not hardcode fake success.

Acceptance evidence: include first 10-minute journey, first 24-hour metrics/events, skip/correct paths, and how Aurora baseline is formed. Verify with tests or manual traces.
```

### Full Prompt CXP-20 — Reports, Insights, Theater, And Progress Narratives

```text
Task: CXP-20 Reports, Insights, Theater, And Progress Narratives

Mission: Make reflection surfaces truthful and motivating. Reports should explain what changed, why it matters, and what action comes next, using evidence rather than generic praise.

Start by reading reports/insights/theater roadmap items. Inspect backend/app/services/progress_narrative_service.py, weekly_digest_service.py, growth_dashboard_service.py, prediction_theater_service.py, insight/user analysis services, intervention/outcome tracking, mobile report/insight/theater surfaces, chart components, and notification/email digest paths if present.

Target experience: weekly and daily reports show evidence: task outcomes, corrections, mastery changes, plan drift, community/accountability events, Aurora calibration, and next action. Prediction theater should be understandable and not fatalistic. Reports should link directly to actions.

Implementation freedom: improve narrative generation, data selection, visualizations, action links, mobile layout, metrics, or tests. Avoid generic "great job" copy without evidence.

Acceptance evidence: include weekly report, insight detail, prediction theater, and action-from-report paths. Show the underlying data used and how a user can act on it.
```

### Full Prompt CXP-21 — Documents, Files, RAG, And Source Tray

```text
Task: CXP-21 Documents, Files, RAG, And Source Tray

Mission: Make uploaded materials trustworthy context. Users should be able to add a document, ask questions, see sources, create tasks/knowledge nodes, and correct bad retrieval.

Start by reading document/RAG/source docs. Inspect backend document/file/group_file services, context_pack.py, context_ranker.py, RAG/retrieval services, source tray payloads, citation feedback, group file permissions, mobile document/file/source tray surfaces, chat card generation from sources, and cost/budget controls for retrieval.

Target experience: source attribution is visible and correctable. Retrieval failures do not become false memory. Documents can produce knowledge nodes, review items, tasks, or shareable material cards. Group files respect permissions. The user can tell when Sparkle is answering from source versus general reasoning.

Implementation freedom: improve retrieval ranking, citation payloads, correction flows, UI, permissions, cost governance, or tests. Do not hide source uncertainty.

Acceptance evidence: include upload, ask with citation, create task/knowledge from source, correct bad source, and share/group material paths. Verify permission and no-source failure cases.
```

### Full Prompt CXP-22 — Calendar, Schedule, And Time Awareness

```text
Task: CXP-22 Calendar, Schedule, And Time Awareness

Mission: Make time awareness operational across plans, tasks, pushes, and Aurora. Sparkle should understand available time, deadlines, calendar pressure, recovery windows, and realistic durations.

Start by reading schedule/time roadmap items. Inspect calendar features, execution_schedule_service.py, smart scheduling, task due dates/durations, deadline pressure signals, push timing, plan review constraints, Aurora energy/time signals, mobile calendar/schedule/task screens, and correction flows for "this takes longer than you think".

Target experience: next actions fit the user's real time. Deadline crunch is visible and handled. Missed tasks produce recovery options, not shame. User corrections to duration/availability change future estimates. Pushes should respect timing and calendar pressure.

Implementation freedom: improve scheduling algorithms, time signals, UI, plan review, task selection, push windows, or tests. Avoid fake precision when calendar data is missing.

Acceptance evidence: include today planning, deadline crunch, missed task, reschedule, duration correction, and calendar conflict paths. Verify backend schedule state and mobile copy/actions.
```

### Full Prompt CXP-23 — Realtime Chat, Gateway, Offline, And Multi-Device

```text
Task: CXP-23 Realtime Chat, Gateway, Offline, And Multi-Device

Mission: Make realtime communication reliable and understandable. Streaming should feel smooth, offline state should be visible, retries should be safe, and returning on another device should show coherent recent Aurora/session state.

Start by reading gateway/realtime audit reports. Inspect backend/gateway/internal/handler chat orchestrator/proxy/registry/responder files, gateway agent client, WebSocket protocol, sequence/request IDs, mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart, offline queue, reconnection UI, app background behavior, idempotency service, and backend streaming/gRPC service.

Target experience: partial responses do not vanish silently. Network drops show a recoverable state. Duplicate sends do not create duplicate actions. Cross-device return does not require strong locking but should show the latest summary and avoid contradictory active sessions.

Implementation freedom: improve gateway concurrency, mobile reconnect state, idempotency, offline queue UI, protocol metadata, tests, or logs. Preserve existing safety work and avoid broad rewrites unless needed.

Acceptance evidence: include network drop, app background, duplicate send, slow stream, and cross-device return paths. Run Go tests/mobile focused tests where practical and document manual QA.
```

### Full Prompt CXP-24 — Mobile Design System, i18n, Accessibility

```text
Task: CXP-24 Mobile Design System, i18n, Accessibility

Mission: Bring the whole mobile app closer to launch polish. Primary surfaces should feel consistent, localized, accessible, and calm.

Start by reading mobile design/UX roadmap items. Inspect mobile l10n, design tokens/theme, common widgets, high-traffic screens (home, chat, task, plan, community, Galaxy, Aurora, onboarding), hardcoded user-facing strings, Semantics usage, dark/light mode, error/empty/loading states, and navigation.

Target experience: users in zh/en see consistent copy. Controls have accessible labels where needed. Colors and typography use design-system patterns. Important buttons, chips, cards, and state messages are readable in light/dark mode. Error states are recoverable and not raw exceptions.

Implementation freedom: improve components, localization, semantics, layout, responsive constraints, or UX copy. Do not spend the whole task on low-value string churn while primary flows remain rough; prioritize high-traffic and emotionally important surfaces.

Acceptance evidence: include screenshots or detailed QA notes for zh/en, light/dark, and at least home/chat/task/community/Aurora. Run flutter analyze/tests if feasible, or focused analyzer on touched files.
```

### Full Prompt CXP-25 — Backend Contract, Privacy, And Safety Boundaries

```text
Task: CXP-25 Backend Contract, Privacy, And Safety Boundaries

Mission: Ensure cross-system contracts protect user data and behavior. Private, deleted, blocked, corrected, inferred, and sensitive data must be handled consistently.

Start by reading privacy/safety/security roadmap items and recent community/privacy findings. Inspect API schemas, auth dependencies, visibility filters, soft-delete guards, UserBlock and relationship models, privacy redaction, llm_secure_io.py, correction provenance, memory/profile writes, community/share endpoints, logs, compliance services, and tests around permissions.

Target experience: users can trust Sparkle. Private data does not leak to public/community/share payloads. Deleted or blocked content stays hidden. PII does not leak into logs or LLM prompts. Inferred memories and corrections have provenance and confidence rather than becoming unqualified facts.

Implementation freedom: improve filters, schemas, redaction, logging, provenance, permission tests, or API error copy. Do not weaken product functionality by blanket hiding data; make boundaries precise.

Acceptance evidence: list each boundary tested or improved: visibility, soft-delete, block, private share, PII/logging, correction provenance. Include focused tests or API traces.
```

### Full Prompt CXP-26 — Observability, Metrics, Dashboards, And Runbooks

```text
Task: CXP-26 Observability, Metrics, Dashboards, And Runbooks

Mission: Make production behavior observable and operable. Operators should be able to tell whether Aurora, chat, tasks, community, pushes, cards, and learning loops are working and helping.

Start by reading observability/ops roadmap items. Inspect backend/app/core/metrics.py, business_metrics.py, health endpoints, Prometheus rules, Grafana dashboards, scheduler/Celery tasks, gateway metrics/logs, Aurora/routing/correction metrics, deployment runbooks, alertmanager config, and production health docs.

Target experience: the team can answer: are users receiving useful Aurora states, are corrections changing behavior, are cards failing, are pushes annoying users, are tasks completing, are feeds healthy, and are costs/latencies safe? Alerts should map to runbooks, not just fire.

Implementation freedom: add metrics, dashboards, alerts, health checks, structured logs, or runbooks. Prefer user-impact metrics over vanity counters. Avoid adding metrics without labels or operational meaning.

Acceptance evidence: include dashboard/panel/rule/query additions and at least five operational scenarios with "symptom -> metric -> action." Verify config syntax where practical.
```

### Full Prompt CXP-27 — Performance, Cost, And Budget Governance

```text
Task: CXP-27 Performance, Cost, And Budget Governance

Mission: Keep the complete experience fast and affordable. Expensive Aurora/RAG/LLM paths should be justified by user value, budgeted, recorded, and graceful under pressure.

Start by reading performance/cost audit reports. Inspect backend/app/core/cost_controller.py, budget optimization/tuning services, Aurora energy/cost controls, RAG/context pack sizing, semantic cache, LLM service/fallbacks, mobile rebuild hotspots, chat streaming latency, gateway limits, and metrics/dashboards.

Target experience: users do not feel unexplained slowness. Expensive paths show progress and fail gracefully. Cost governance includes preflight gates and actual spend recording. Context selection is tight enough to be useful and cheap. Mobile high-traffic screens do not reload/rebuild unnecessarily.

Implementation freedom: improve budget checks, spend recording, caching, context pruning, mobile performance, timeout behavior, or tests. Do not simply disable expensive features; make them value-aware.

Acceptance evidence: include latency/cost risks addressed, where spend is recorded, what happens at budget limit, and at least one before/after or benchmark-style measurement if feasible.
```

### Full Prompt CXP-28 — Admin, QA, And Internal Control Surfaces

```text
Task: CXP-28 Admin, QA, And Internal Control Surfaces

Mission: Give reviewers and operators enough control to inspect and validate the system. Internal surfaces should make Aurora flags, memory, traces, routing, moderation, and user-impacting errors auditable.

Start by reading QA/admin/control docs. Inspect memory_admin APIs, graph_monitor, health_production, aurora_control_surface_service.py, client telemetry, moderation/reporting surfaces, routing trace endpoints, feature/kill switches, admin authorization, logs, and any internal UI or docs for QA workflows.

Target experience: a reviewer can reproduce a user journey from trace IDs, inspect Aurora decisions and memory claims, see live/shadow/off switches, moderate community issues, and safely trigger or rollback operational controls. Admin actions should be authorized and logged.

Implementation freedom: improve endpoints, admin payloads, docs, audit logging, QA tools, or tests. Do not expose sensitive admin data without auth boundaries.

Acceptance evidence: include reviewer workflows for Aurora trace, memory correction, community moderation, kill switch audit, and user-impacting error trace. Verify auth/logging where touched.
```

### Full Prompt CXP-29 — End-To-End North Star Journey

```text
Task: CXP-29 End-To-End North Star Journey

Mission: Validate and polish the complete product story across systems. This agent is responsible for user-journey truth, not one module. It can start by building the acceptance harness early, but final judgment should happen after most other CXP branches have landed or can be inspected.

Start by reading the vision checklist, Roadmap v3, tracker, this guide, and CXP reports available at the time. Inspect any systems necessary for the canonical journey: onboarding, chat, cards, plans, tasks, Aurora correction/Core Session, knowledge graph, tools, community, achievements, reports, push/return, and mobile navigation.

Target experience: a zero-base user can onboard, state a goal, receive a plan, execute a task, use a learning tool, receive Aurora calibration, correct the system, share progress, get a meaningful reward, return after absence, and see changed future behavior. The journey should feel like one intelligent product, not stitched demos.

Implementation freedom: fix dead ends directly when safe, add smoke/e2e scripts, improve copy/routing, or document exact owner for large blockers. Avoid broad rewrites that conflict with specialized agents unless necessary.

Acceptance evidence: create the canonical E2E acceptance narrative with concrete steps, expected payloads/screens, and pass/fail status. Include every dead end fixed and every remaining blocker with subsystem owner. This report becomes the final product acceptance spine.
```

### Full Prompt CXP-30 — Final Integration Readiness And Conflict Map

```text
Task: CXP-30 Final Integration Readiness And Conflict Map

Mission: Prepare all parallel work for final merge and unified polish. This task should run near the end, after most CXP branches/reports exist. The goal is to make final integration tractable: identify overlaps, duplicate implementations, incompatible assumptions, migrations, API contract conflicts, and missing cross-links.

Start by reading this dispatch guide, all docs/product/parallel_closeout/CXP-* reports, Roadmap v3, Tracker, final acceptance ledgers, and git branch diffs for the parallel work. Inspect changed files by cluster: contracts/migrations, backend services, gateway/protocol, mobile data/services, mobile UI, metrics/docs.

Target experience: the final integrator can merge without guessing intent. Product coherence wins over isolated feature success. If two agents solved the same problem differently, recommend a single path. If one chain creates data another chain needs, make the dependency explicit.

Implementation freedom: produce the conflict map, patch small integration conflicts, add missing compatibility docs/tests, and propose merge order. Do not attempt to reimplement all branches. Do not silently choose one implementation without explaining why.

Acceptance evidence: create a final integration readiness report with branch list, write-set overlaps, migration/API conflicts, duplicate systems, dependency graph, merge order, required test matrix, and unresolved decision list. This report is the handoff to the final Codex reviewer.
```

## 4B. Recommended Parallel Waves

All 30 agents can be assigned at once, but the following wave labels help the coordinator interpret dependencies:

- Wave A foundation: CXP-01 through CXP-05, CXP-23, CXP-25, CXP-26, CXP-27, CXP-28.
- Wave B product loops: CXP-06 through CXP-18, CXP-20 through CXP-22.
- Wave C journey and integration: CXP-19 can run early for cold start, CXP-29 should build the journey harness early and re-run late, CXP-30 should run near the end.

Agents should not block waiting for other waves unless their task is explicitly final integration. If a dependency is missing, implement the local contract cleanly, document the assumption, and make the final integration point obvious.

## 5. Required Agent Report Template

Each agent must create:

`docs/product/parallel_closeout/CXP-XX_<short_name>_REPORT_2026-05-02.md`

Use this structure:

```markdown
# CXP-XX Report — <Task Name>

## Goal
What experience or system quality this task improved.

## Work Completed
High-level changes, grouped by product chain, not just files.

## User Experience Before / After
Concrete user journey improvements.

## Cross-System Links
Which backend, mobile, gateway, docs, metrics, or data flows were touched.

## Verification
Commands run, screenshots taken, manual QA notes, known warnings.

## Remaining Risks
Only real residual risks, with exact owner suggestions.

## Commit
Branch and commit hash.
```

## 6. Final Integration Protocol

After parallel execution:

1. Collect all CXP reports.
2. Review all branches for overlapping write sets.
3. Merge in dependency order:
   - contracts and migrations
   - backend services
   - gateway/protocol
   - mobile data/services
   - mobile UI
   - metrics/docs
4. Run focused tests per subsystem, then a final E2E smoke.
5. Update Roadmap Tracker and Final Acceptance Ledger only once, in final integration.
6. Perform a final product review around real journeys, not around module checklists.

## 7. Non-Negotiable Acceptance Journeys

The final product must pass these journeys:

1. New user: onboarding -> first goal -> first plan -> first task -> first Aurora status.
2. Standard chat: user asks vague goal -> AI clarifies -> creates actionable cards -> cards route correctly.
3. Aurora correction: user rejects a judgment -> freeform explanation captured -> future behavior changes.
4. L3 calibration: "你没懂我" -> Core Session -> state/policy/task changes -> summary -> background.
5. Daily execution: open app -> see next action -> complete/skip/fail -> plan and Aurora update.
6. Knowledge loop: document/translation/error -> knowledge node -> review task -> mastery change.
7. Community loop: share plan/task/achievement/seed -> recipient views/adopts -> visibility respected.
8. Reward loop: meaningful achievement -> visual/photon/shop state -> shareable but private by default.
9. Comeback loop: return after 1 hour / 2 days / 4 days -> appropriate debrief and next step.
10. Failure loop: offline/API error/auth expiry -> recoverable, localized, non-destructive UX.

## 8. Guidance For The Final Reviewer

When the branches return, do not judge them only by tests. Judge them by whether the user can feel a continuous product:

- Aurora notices, explains, asks, learns, and backs off.
- Plans become tasks.
- Tasks update knowledge, achievements, reports, and community eligibility.
- Tools feed the learning graph.
- Sharing preserves context and permissions.
- Every correction and outcome has somewhere to go.

The final merge should remove duplicate paths, align copy and design language, and make the product feel like one intelligent system rather than thirty successful patches.
