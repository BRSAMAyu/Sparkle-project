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
