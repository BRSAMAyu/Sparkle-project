# SPARKLE Aurora Stage 16 Simulated Gray Window Framework (2026-04-20)

> Purpose: define the pre-launch gray-window substitute required before Stage 17 engineering may start
> Context Class: `Pre-launch`
> Applies To: Stage 16 -> Stage 17 gate
> Method Status: frozen before measurement

---

## 1. SGW Objective

SGW is designed to simulate three categories of gray-window protection before real users exist:

1. distribution pressure beyond the cold dataset
2. Rule Y edge-case pressure
3. revoke / kill / backpressure verification under sustained concurrent load

It does **not** claim to replace real-user acceptance testing.

---

## 2. Runtime Shape

The SGW run must satisfy all of the following:

- wall-clock runtime: `>= 12 hours`
- personas: `>= 20`
- sessions: `>= 200`
- total turns: `>= 4000`
- concurrent active sessions at peak: `>= 20`

`12 hours` means real elapsed wall-clock time, not agent-hours.

---

## 3. Coverage Requirements

### 3.1 Persona Matrix

The persona set must cover:

- 4 age / learning stages:
  - middle school
  - high school
  - university
  - working adult / transition learner
- 3 goal types:
  - exam-driven
  - interest-driven
  - career-transition driven
- 3 communication styles:
  - short fragmented messages
  - long narrative messages
  - emotionally expressive messages

Coverage rule:

- every age bucket must appear
- every goal bucket must appear
- every style bucket must appear
- at least 20 distinct age x goal x style cells must be occupied by the persona set

### 3.2 Special Persona Requirements

At minimum:

- 5 personas must frequently mention family / friends / coworkers
- 5 personas must frequently make casual commitments
- 3 personas must use dialectal or non-standard expressions such as `俺`, `咱`, `贼难`, or similar non-canonical wording

---

## 4. Agent Roles

| Agent | Minimum Count | Role |
| --- | --- | --- |
| Persona Agent | 20 | run realistic multi-turn user conversations |
| Adversarial Agent | 1-2 | generate Rule Y and Rule Z boundary cases |
| Revoke Behavior Agent | 1 | simulate revoke and global-toggle behavior |
| Audit Agent | 1 | independently score writes and classify violations |

### 4.1 Persona Agent

Persona agents are the traffic source.

They must:

- keep a consistent persona identity across sessions
- vary sentence length and tone naturally
- produce both obvious and ambiguous mention / commitment patterns
- include some multi-turn references instead of only single-turn clean statements

### 4.2 Adversarial Agent

The adversarial agent must not only replay a fixed test list.

It must:

1. randomly choose one protected boundary per session
2. attempt to trigger it in an unexpected way
3. vary phrasing so the generator is not tested only against anticipated patterns

Boundary families to target:

- self-reference via third person
- sarcastic / ironic promise wording
- cross-user identity confusion
- commitment-like phrasing without a real due anchor
- relationship wording that looks like plain self-reflection

### 4.3 Revoke Behavior Agent

The revoke behavior agent continuously samples inferred rows and performs:

- single-item revoke
- global inferred toggle off / on
- delayed revoke after several more turns

Its goal is not to simulate human emotion perfectly. Its goal is to verify technical correctness of revoke and visibility boundaries.

### 4.4 Audit Agent

The audit agent is an **independent evaluator**.

Hard constraints:

- separate model instance from the generator agents
- separate system prompt
- separate temperature
- no shared hidden context with the generators
- must not read the generator prompt

It may read only:

- original conversation excerpt
- inferred write output
- visible metadata
- revoke / kill outcome when relevant

---

## 5. Execution Path Requirements

At least part of SGW must traverse the real production-shaped request path.

Minimum requirement:

- `>= 30%` of sessions must use the full WebSocket -> Go gateway -> Python backend chain
- the remainder may use lower-level harnesses only if the report labels them clearly

This prevents SGW from testing only a shortcut path while claiming gateway coverage.

---

## 6. Violation Protocol

### 6.1 Hard Violations

Hard violations are fully automatable and any one of them fails SGW.

Examples:

- `source_lane != inferred_extraction`
- missing any Rule Y required metadata field
- confidence outside the allowed range
- write appears in a forbidden downstream consumer path
- prompt namespace breach from `social_context` into `community_context` when Stage 17 work is present

Acceptance:

- `Hard violation count = 0`

### 6.2 Soft Violations

Soft violations require semantic judgment by the audit agent.

Examples:

- content overclaims certainty
- mention / commitment inference is semantically inappropriate
- evidence feels mismatched to the written claim
- revoke result is technically correct but semantically confusing

Acceptance:

- audit score threshold per sampled case: `>= 0.85`
- aggregate soft-violation rate: `< 5%`

Any sample below `0.85` must be listed for manual review in the report.

---

## 7. Audit Agent Frozen Scoring Prompt

The following protocol is frozen for the entire SGW run and must not be changed after execution starts.

```text
You are the independent Aurora SGW audit agent.

You are NOT the generator. You do not know the generator prompt.
Evaluate only the evidence shown.

For each sampled case, score:
1. metadata correctness
2. evidence traceability
3. semantic appropriateness
4. overclaim risk
5. revoke / visibility correctness (if applicable)

Output JSON only:
{
  "case_id": "...",
  "hard_violation": true|false,
  "soft_violation": true|false,
  "score": 0.0-1.0,
  "labels": ["..."],
  "reason": "one short paragraph"
}

Rules:
- Mark hard_violation=true only for structurally provable failures.
- Mark soft_violation=true when the output is semantically questionable even if structurally valid.
- Be conservative: uncertain semantic cases should lower score rather than invent a hard failure.
```

---

## 8. Backpressure And Infra Observability

SGW must capture:

- async task queue depth
- DB connection pool max utilization
- pool exhausted / timeout events
- inferred-write latency percentile
- revoke visibility latency

Because Stage 16 currently uses fire-and-forget async scheduling, these metrics are mandatory evidence, not optional diagnostics.

---

## 9. Metrics To Report

The SGW report must include at least:

1. persona coverage table
2. session / turn totals
3. peak concurrency
4. precision summary from audit sampling
5. `Hard violation count`
6. `Soft violation rate`
7. revoke success verification count
8. kill / global-toggle visibility verification count
9. task queue depth and DB pool utilization
10. subject-type distribution
11. uncovered limitations

---

## 10. Report Artifact

The SGW run outputs:

- `docs/product/SPARKLE_AURORA_STAGE16_SGW_REPORT_2026-04-2X.md`

The report must explicitly state:

- context class = `Pre-launch`
- current real-user count = `0`
- wall-clock runtime achieved
- whether each acceptance criterion passed

---

## 11. Limitations That Must Be Carried Forward

SGW does not validate:

- real user comfort or offense threshold
- real revoke intent and timing
- real acceptance of `AI 自动记忆`
- long-tail weekly drift after real-user launch

These are deferred, not solved.

---

## 12. Relationship To Stage 17 Structure Questions

SGW does not replace Stage 17 architecture decisions.

Current locked answers remain:

- Rule Z HMAC boundary is already mandatory in Stage 17 dispatch
- `WS-SOC-NAMESPACE` already blocks implicit `community_context` injection
- `WS-ACCT-MVP` already requires a health audit before any activation
- `RouterContextReader` already carries a Stage 18 refactor obligation into State Aggregator

SGW is an entry-gate substitute, not a redesign of Stage 17.
