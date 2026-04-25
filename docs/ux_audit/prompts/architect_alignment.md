# Architect Alignment Document — Sparkle UX Audit

> **Read this if you are the architect check-in agent, OR if you need to understand the vision behind this audit.**

---

## Project North Star

**"Zero-knowledge student passes exam after 7 days with Sparkle."**

This is not a feature checklist. It is a lived experience test. Every UX issue this audit finds should be evaluated against this question: *does this gap prevent or degrade a real student's ability to complete the 7-day sprint?*

---

## What This Audit Is Trying to Find

We are NOT looking for:
- Visual polish (wrong font size, off-brand color)
- Feature ideas or improvements
- Architecture refactors

We ARE looking for:
- **Broken chains**: user takes an action → expected result never appears in UI
- **Invisible backend**: feature implemented in Python/backend but zero mobile UI surfaces it to user
- **Dead ends**: user completes a step, has no idea what to do next, no navigation affordance
- **Phantom data**: numbers shown as 0 / empty when the user has actual history (mastery scores, streaks, completed tasks)
- **Generic AI**: Aurora responds with text that could apply to any user, with no reference to their specific goal, subject, or previous sessions
- **Silent failures**: API call fails, app shows nothing — user doesn't know, doesn't retry, data is lost

---

## The 20 Chains and Why They Matter

The 20 chains cover the **entire user lifecycle**:

| Phase | Chains | Why |
|-------|--------|-----|
| **Onboarding** | C01, C19 | First impression — broken = user abandons app |
| **Daily execution** | C02, C03, C04, C09, C12 | The core loop every day |
| **Sprint lifecycle** | C05, C14, C20 | The 7-day north star journey |
| **Intelligence** | C06, C10, C11 | What makes Aurora feel like it knows you |
| **Engagement** | C07, C08, C13, C15 | Why user comes back tomorrow |
| **Infrastructure** | C16, C17, C18 | Silent killers — broken but hard to notice |

---

## Severity Framework (Architect Use)

When reviewing findings from A/B, apply this escalation:

**Immediately escalate to top of fix queue**:
1. Any finding confirmed by BOTH reviewers independently
2. Any chain where the backend is complete but mobile never calls the API (feature is invisible)
3. Any chain with a navigation dead-end (user is stuck with no exit)
4. Any place where mastery/streak/nodes permanently show 0 for active users

**Address in second pass**:
- Aurora context fields that are null at call time (personalization broken)
- `ref.invalidate()` missing after mutations (data staleness)
- Empty states with no guidance

**Third pass**:
- Minor polish, edge cases, loading states

---

## How to Do the Architect Check-In

Read:
- `docs/ux_audit/audit_state.json` — progress, round count
- `docs/ux_audit/accumulated_findings.md` — all validated findings
- `docs/ux_audit/reviewer_a_current.md` + `reviewer_b_current.md` — latest raw output
- `docs/ux_audit/workflow_log.md` — timeline

Assess:
1. **Progress**: Are indices advancing each round? If same round for 3+ checks, something is stuck.
2. **Finding quality**: Are findings specific (file:line, observed vs expected)? If vague, set `steering_notes`.
3. **Coverage**: Are reviewers reading the right files? If they're missing key integration points (e.g., auditing only mobile but not tracing backend), steer them.
4. **Patterns**: Are the same anti-patterns appearing across chains? Note emerging themes.

Interventions available (edit `audit_state.json`):

```json
// Pause the workflow
"status": "paused"

// Quality directive — both reviewers read this before each cycle
"steering_notes": "Each finding must cite file:line. Trace backend→API→provider→widget fully."

// Force specific chain for next cycle
"architect_override_a": "C05",
"architect_override_b": "C08"
```

Output format for check-in report:
```
=== UX AUDIT ARCHITECT CHECK-IN ===
Time: [ISO timestamp]
Progress: [X]/20 chains | Round [R]
A next: [chain_id] — [name]
B next: [chain_id] — [name]
Critical issues found: [count]
Major issues found: [count]
Finding quality: [Good / Acceptable / Poor — reason]
[INTERVENTION: action taken, reason] OR [No intervention needed]
Top emerging pattern: [if any]
===
```

Append this to `workflow_log.md` and set `architect_last_check` in state.

---

## Key Implementation Context

This project uses:
- **Aurora Runtime v1**: 3-layer architecture (DashboardReadout → DecisionLoop → ChatAdapter). All AI personalization flows through here.
- **Sprint Packs**: JSON files in `backend/app/sprint_packs/` define knowledge nodes per subject. Linked to Galaxy mastery via `sprint_pack_nodes` in task specs.
- **Galaxy**: Per-user mastery per knowledge node. Updated via `galaxy_service.update_node_mastery()`. Displayed in star map with 4-tier color.
- **Riverpod**: All Flutter state. Mutations MUST call `ref.invalidate(provider)` or `ref.refresh(provider)` or UI stays stale.
- **WebSocket chat**: Real-time, Aurora responses stream token by token. Errors must be caught in `StreamSubscription.onError`.
- **Celery**: Scheduled tasks (spaced repetition, comeback, weekly narrative). Each push must have a `destination_route` handled in `push_navigation_service.dart`.

The most common gap pattern in this codebase: **backend writes data correctly, but no `ref.invalidate()` on the mobile side → user sees old data until app restart.**
