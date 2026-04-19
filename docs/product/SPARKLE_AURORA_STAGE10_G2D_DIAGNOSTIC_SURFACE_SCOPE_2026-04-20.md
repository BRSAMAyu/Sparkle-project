# SPARKLE Aurora Stage 10 G2D Diagnostic Surface Scope (2026-04-20)

> **Status**: pre-implementation artifact for `WS-G2D`
> **Purpose**: freeze the user-visible graph-diagnostic scope before implementation.

## 1. Why This Exists

Sparkle already has graph / galaxy infrastructure, but users still cannot ask the system for a compact, evidence-based answer to "我哪里弱".

## 2. Questions This Surface Must Answer

Stage 10 `WS-G2D` is allowed to answer:

1. which concepts are currently weakest
2. which concepts are at risk because of low mastery or dependency pressure
3. which prerequisite gaps are blocking a target
4. what the next review or revisit candidates are

Stage 10 `WS-G2D` is not required to answer:

1. continuous-learning strategy evolution
2. auto-remediation writes
3. personalized intervention generation outside current intervention lanes

## 3. Allowed Data Sources

The diagnostic surface may consume only existing read surfaces such as:

1. `GraphReasoningService`
2. `GalaxyService` retrieval / graph reads
3. `UserNodeStatus` mastery and unlock state
4. current graph relationships and dependency structure
5. current graph-related retrieval or trace summaries when already read-safe

## 4. Output Shape

Stage 10 may ship either or both:

1. a chat-native diagnostic card for prompts like "我哪里弱"
2. a dedicated galaxy-side diagnostic panel or section

Minimum payload should include:

1. `weak_nodes`
2. `at_risk_nodes`
3. `why_now`
4. `recommended_next_review`
5. `graph_basis`

## 5. Allowed User Actions

The diagnostic surface may allow:

1. navigation to a galaxy node
2. navigation to review / learning path surfaces
3. chat prompts asking for deeper explanation

It may not directly:

1. mutate mastery
2. mutate strategy state
3. mutate profile truth
4. create a new graph-specific write channel

## 6. Visual / Product Guardrail

The surface must read as a diagnostic answer, not just a node browser.
That means it should prioritize:

1. weakest concepts
2. why they are weak
3. what is blocked
4. what to review next

over generic graph browsing.

## 7. Minimum Acceptance Shape

`WS-G2D` is accepted only if:

1. the system can answer at least one real "我哪里弱" scenario
2. the answer is graph-derived and user-visible
3. follow-up actions stay inside existing navigation / correction / intervention lanes
4. no new write lane exists
