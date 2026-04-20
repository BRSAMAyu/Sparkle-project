# SPARKLE Aurora Stage 17 Dispatch Plan (2026-04-20)

> Workstream Bundle: `WS-SOC-*` + `WS-ACCT-MVP` + `WS-SOC-ROUTER-READ`
> Phase Mapping: Roadmap v2.0 Phase 1A
> Strategic Positioning: connect the Stage 16 Memory write lane to downstream read-only consumers for the first time.
> Status: dispatched and anchored; implementation remains locked pending the Stage 16 gray-window declaration.

---

## 0. Stage 17 Meta

### 0.1 7-Phase Growth Ring Mapping

| Phase | Unlock | Explicitly not in scope |
| --- | --- | --- |
| Sense | people / relationship / commitment facts in chat are captured structurally for the first time | no LLM extraction; rules only |
| Reflect | overdue commitment facts can surface at the front door | no proactive push |
| Adapt | Router may read social context | Router must not use social facts as a routing decision signal |

Any attempt to introduce LLM extraction in Sense, push in Reflect, or routing-branch decisions in Adapt must stop and go through a dispatch addendum.

### 0.2 Aurora Three-Layer Placement

- Write path: still uses the Stage 16 governed `EpisodicMemory.inferred_extraction` lane; Stage 17 only adds `subject_type` subtyping and does not create a new lane.
- Read path: adds two read-only consumers, `AccountabilityMvpService` and `RouterContextReader`.
- Aurora L3: untouched in this stage. No Aurora decision log may cite social facts.

### 0.3 Rule Audit Checklist

- Rule G: 7 workstreams, at least 7 commits once implementation starts; Rule Z definition stays in its own commit.
- Rule H: social facts may live only in L1 EpisodicMemory; no L0 person / relationship tables.
- Rule K + Rule Y: all Stage 17 writes remain governed by Rule Y.
- Rule Z: new in Stage 17, defines cross-user privacy boundaries.
- Rule P: explicit user correction remains authoritative; social facts support explicit retraction.
- Rule Q: every social fact must be front-door readable and visibly labeled with `subject_type`.
- Rule U: every `person_mention` / `commitment` entry must be widget-actionable (`retract`, `resolve`).
- Rule V: add at least 3 new regression contracts for Router read boundary, overdue commitment visibility, and Rule Z guard failures.
- Rule W: not applicable in Stage 17.

### 0.4 Path A / B / C

| Path | Trigger | Scope |
| --- | --- | --- |
| A | Stage 16 gray window >= 7 days + write flag on in production + no Rule Y exception | all 7 workstreams |
| B | production `inferred_extraction` precision drops below `0.85` | only Rule Z + `person_mention` extraction |
| C | any Rule Y exception is observed | stop Stage 17 and return to Stage 16 remediation |

### 0.5 Codex Self-Check Before Implementation

1. Are we using governance language to dodge the real routing-capability problem?
2. Are we using "read-only" language to skip the real Rule Z privacy boundary?
3. Do the Stage 18 entry conditions truly block State Aggregator / push from bypassing the boundaries created here?
4. If Stage 17 rolls back, can we still trace every social fact that Router ever read?

The dispatch may be anchored now, but implementation remains blocked until the user explicitly declares the Stage 16 gray window passed.

---

## 1. Stage 17 Goal

Stage 17 connects the Stage 16 Memory write lane to downstream read-only consumers for the first time and formalizes where "the user's social circle" lives inside the profile system.

It must land all three of the following:

1. Rule Z is formally defined and guarded in CI.
2. The governed Memory lane can carry social semantics through `subject_type`.
3. Two read-only consumers go live:
   - Accountability MVP: overdue commitments are visible, resolvable, and dismissable at the profile front door.
   - Router read-only context: Router may render a bounded social snapshot into the prompt, but may not branch on it.

Out of scope for Stage 17:

1. proactive push, reminders, badges, or red dots
2. Router decision branches that depend on social facts
3. LLM extraction
4. Skill reads from Memory
5. any cross-user data flow

---

## 2. Gate S17-0 Entry Baseline

Before any implementation begins, Codex must replay the baseline and receive a user-provided Stage 16 gray-window proof.

```bash
cd backend && ./.venv/bin/python -m pytest tests/aurora ... -q
cd backend && ./.venv/bin/python -m pytest tests/unit/test_persistent_bayesian_learner_contract.py tests/unit/test_multi_dimensional_learner_contract.py tests/unit/test_distilled_strategy_store_contract.py -q
./backend/.venv/bin/python scripts/check_rule_k_write_paths.py
```

Additionally required:

- Stage 13+14+15+16 carry-forward sweeps still green
- at least one ops report covering 7 consecutive production days with inferred-extraction counts, precision spot checks, and zero Rule Y exceptions

If any baseline fails or the gray-window evidence is missing, Stage 17 does not start.

---

## 3. Workstreams

### WS-SOC-RULE-Z

Purpose: define the privacy boundary for "user A mentioned person B" once and remove ambiguity from later stages.

Mandatory contents:

1. One-sentence definition:
   user A mentioning person B may only generate derived facts inside A's profile; those facts may not be written into B's profile, aggregated across users, or exported as identifiable identity data about B.
2. Coverage:
   all inferred writes whose subject is a person or relationship; Stage 20 skill sharing references this rule, while its own sharing boundary is governed by Rule AA.
3. Mandatory constraints:
   - every write must set `mentioned_entity_owner_user_id == self_user_id`
   - any read with mismatched ownership must hard-fail, not silently degrade
   - mentioned-entity lookup keys must use a per-user salted hash, not raw names
4. Hashing strategy ruling:
   - use `hash(self_user_id + normalized_local_name)` as the user-local semantic key
   - the hash is deterministic only within the same owner user
   - raw names must not be stored as lookup keys
   - if the user needs human-readable context, the UI must resolve it through `evidence_token` back to the original chat turn instead of reading a name from the profile row
5. Five forbidden scenarios:
   - searching "all users who mentioned Zhang San"
   - counting how many users mentioned a real person
   - using `person_mention` as a cold-start recommendation signal
   - showing raw mention text directly in support / ops tooling
   - feeding mention data into the Stage 21 Bayesian learner `source_state`
6. CI guard upgrade:
   extend `scripts/check_rule_k_write_paths.py` with Rule Z checks for forbidden imports, joins, and mention-ownership bypass patterns

Artifact:

- `docs/product/SPARKLE_AURORA_STAGE17_RULE_Z_DEFINITION_2026-04-20.md`

### WS-SOC-EXTRACT

Purpose: let the Stage 16 extractor classify social subjects without LLMs or threshold changes.

Mandatory contents:

1. Add `subject_type` to `InferredEpisodicCandidate` with:
   `self`, `person_mention`, `relationship`, `commitment`
2. Keep the classifier rules-only:
   - `person_mention`: third-person references such as "he / she / my mom / Lao Zhang / colleague X"
   - `relationship`: explicit relationship descriptions such as "my relationship with X"
   - `commitment`: promise-like tense plus an action verb, such as "I will", "I plan to", "within this week"
   - `self`: fallback only when the current Stage 16 semantics still apply
3. If classification fails, do not write anything.
4. Keep the Stage 16 dual feature-flag governance; subtypes may not bypass the master switch.
5. Expand the cold dataset to at least 24 cases:
   - each new `subject_type` must have at least 4 positive and 2 negative cases
   - `commitment` must have at least 8 cases total
   - at least 3 `commitment` cases must cover time-boundary patterns

### WS-SOC-COMMIT

Purpose: make `commitment` entries actually usable by Accountability MVP.

Mandatory contents:

1. `commitment` extraction must produce `due_at`; if no clear time anchor exists, the whole candidate is dropped.
2. Time parsing remains rules-only and supports a bounded set such as:
   `today`, `tomorrow`, `this week`, `month end`, `X days`, `X month X day`
3. Required boundary handling in the cold dataset:
   - define what "this week" means
   - cover "month end"
   - cover at least one composite boundary case
4. If time parsing fails, do not write a commitment.
5. Land the database column changes via Alembic migration before code.
6. `commitment` rows use `due_at + 7d` as the default decay horizon.

### WS-ACCT-MVP

Purpose: make overdue commitments visible at the profile front door without push.

Mandatory contents:

1. Add `AccountabilityMvpService` in its own file. It fetches current-user entries where:
   `subject_type=commitment`, `due_at <= now`, `revoked_at IS NULL`, and not user-resolved.
2. Expose `GET /memory/accountability/pending`.
3. The UI must provide:
   - `resolved`: write `resolved_at` without deleting evidence
   - `dismiss`: trigger the inferred kill path from Stage 16 soft revocation
4. No proactive notifications, push, or red-dot signals.
5. Mobile shows these under a dedicated subsection below `AI 自动记忆`: `待跟进承诺`.

### WS-SOC-ROUTER-READ

Purpose: let Router render a bounded social snapshot into the prompt while keeping routing decisions untouched.

Mandatory contents:

1. Add `RouterContextReader.fetch_social_snapshot(user_id)` returning:
   - `recent_person_mentions`: up to 3 items from the last 7 days
   - `pending_commitments_count`: overdue unresolved count, without raw text
2. Hard token budget:
   the serialized snapshot must stay within 200 tokens; truncate values, not fields.
3. The snapshot is prompt context only; Router decision code may not branch on it.
4. CI guard:
   any import of `RouterContextReader` under router code must remain inside a prompt-render whitelist.
5. Feature flag:
   `SPARKLE_ROUTER_SOCIAL_CONTEXT_READ_ENABLED`, default `OFF`
6. Boundary warning must appear twice, once in the docstring and once in config comments:
   "This data is prompt context only, not a routing decision signal. Any if/switch logic based on it requires Stage 19B Sufficiency Judge acceptance."
7. Known limit to record explicitly:
   even with CI import guards, prompt-level exposure can still indirectly influence LLM-generated tool calls or outputs. Stage 17 accepts this as a documented limit, and Stage 19B must measure the effect before any decision-path consumption is allowed.

### WS-SOC-MOBILE

Purpose: make `person_mention`, `commitment`, and `relationship` satisfy Rule Q and Rule U at the front door.

Mandatory contents:

1. Add `subject_type` chips in the `AI 自动记忆` section.
2. `person_mention` rows must render the caveat:
   `涉及他人，仅记录在你的画像中（Rule Z）`
3. `commitment` rows live in the Accountability MVP subsection.
4. Keep `SPARKLE_MEMORY_INFERRED_WRITE_ENABLED` as the master switch and add four per-type mobile toggles.

### WS-SOC-KILL

Purpose: make it possible to shut down one `subject_type` without taking down the whole inferred lane.

Mandatory contents:

1. Extend admin revocation to support per-`subject_type` soft revoke.
2. Add at least 3 regression tests proving that killing one subtype leaves the other two alive.
3. Document the effective delay and confirm that killed entries disappear from Accountability MVP immediately.

---

## 4. Gate S17-FINAL

All of the following must be true, in order:

1. Gate S17-0 baseline is green and the Stage 16 gray-window proof is attached.
2. Rule Z definition doc is landed and the CI guard upgrade reports zero violations.
3. Alembic migration for commitment fields is applied and rollback-tested.
4. Stage 17 targeted backend sweep has at least 14 passing tests.
5. Stage 17 targeted mobile sweep has at least 6 passing tests.
6. Whole-codebase grep verification proves:
   - `subject_type` only appears in the approved write-lane, read, admin, policy, accountability, router-reader, test, and mobile presentation files
   - `RouterContextReader` only appears in the prompt-render whitelist
   - `mentioned_entity_owner_user_id` exists on every `person_mention` / `relationship` write path
   - `recent_person_mentions` has zero hits in routing decision branches
7. Path A readiness statement includes the draft Stage 18 entry conditions for State Aggregator / push.

---

## 5. Explicitly Delayed Until Stage 18+

Stage 17 does not do, discuss, or quietly smuggle in:

1. proactive push, reminders, red dots, or badges
2. Router decision branches based on social facts
3. LLM extraction
4. any cross-user data flow
5. State Aggregator reading social snapshots as an input feature
6. Skill-system reads from Memory

Known limit carried forward from pre-review:

- Router prompt context may still indirectly shape LLM outputs even when Router code itself never branches on social facts. This is documented, accepted for Stage 17, and must be revisited by Stage 19B Sufficiency Judge before any stronger consumption is allowed.

---

## 6. Stage 18 Entry Conditions

- Path A:
  all 7 Stage 17 workstreams are green, followed by at least one production-gray week, zero Rule Z exceptions, and at least 50 real resolve/dismiss Accountability events.
- Path B:
  Accountability MVP ships, but user-behavior volume is still insufficient; Stage 18 may build State Aggregator without push.
- Path C:
  any Rule Z exception or any leakage of Router social fields into decision branches pauses Stage 18 and sends the work back to Stage 17 remediation.

---

## 7. Codex Execution Guardrails

1. Follow Rule G once implementation starts: at least 7 commits; Rule Z definition and Alembic migration each get their own commit.
2. This dispatch file must be landed before any Stage 17 workstream starts.
3. After landing this dispatch, wait for the user's explicit declaration that the Stage 16 gray window passed; do not self-authorize implementation.
4. Any scope expansion in Section 3 requires a dispatch addendum.
5. Closeout must produce:
   `docs/product/SPARKLE_AURORA_STAGE17_HANDOFF_2026-04-20.md`
6. Final acceptance still requires independent review from GLM1, GLM-observer, and MIMO, followed by Chief Architect final-accept.

---

## 8. Pre-Review Responses (P1-P3)

### P1. Rule Z Hashing Strategy

Adopt a per-user salted semantic key:

- `mentioned_entity_hash = hash(self_user_id + normalized_local_name)`
- same-user repeated mentions can dedupe
- cross-user matching is impossible by construction
- raw names are never stored as lookup keys

### P2. Router Indirect Influence Risk

Accepted as a known limit, not as a blocker for dispatch:

- CI can guard direct code imports and branch reads
- CI cannot prevent an LLM from being indirectly influenced by prompt context
- therefore Stage 17 keeps this path read-only and explicitly non-authoritative for routing decisions

### P3. Commitment Time-Boundary Coverage

The Stage 17 cold dataset must include at least 8 `commitment` cases, with at least 3 boundary-focused cases that cover examples such as:

- `这周` with an explicit week-start definition
- `月底`
- at least one composite boundary form such as `这周五之前`

Dispatch anchored. Implementation remains locked pending the gray-window declaration.
