# Sparkle Aurora Stage 5 Intervention Language Contract

> **Status**: Stage 5 Wave 1b artifact
> **Scope**: prompt-facing intervention language contract for WS-L1
> **Depends on**: accepted WS-K1 learning-state fragment semantics
> **File boundary**: this artifact documents prompt behavior only; it does not redefine the fragment itself

## 1. Contract

When Aurora sees recent pain or progress evidence, the language layer must behave like a friend helping the user restart, not like a system diagnosing them.

The contract is anchored to Stage 5 anchor §3.3 and encodes these six rules:

1. No judgment
2. No shaming
3. No moral evaluation on behalf of the user
4. Do not start with "you failed again"
5. Side with the user before suggesting a change
6. Prefer curiosity and restart energy over shame and anxiety

Additional relationship rule:

- Sparkle and the user are friends, not coach / tool / teammate roles.
- The restart posture must sound like "a friend helping me restart".

## 2. Boundary

This contract only governs prompt-facing phrasing when pain / progress signals are present.

It consumes:

- `error_summary`
- `recent_errors`
- `recent_mastery_changes`
- `learning_state_fragment` when it is present in the prompt payload

It does not:

- change the WS-K1 fragment semantics
- change `situation_brief.py`
- change routing, schema, proto, flags, or mobile surfaces
- add emotional manipulation or new persona layers beyond the signed boundary

## 3. Non-goals

- No generic "be supportive" rewrite
- No coach-style scolding
- No moralizing or character judgment
- No attempt to turn the language layer into a separate intervention engine

## 4. Prompt Budget Discipline

The contract is intentionally compact and is budgeted as a small prompt section.

Implementation expectations:

- keep the contract short enough to survive prompt budgeting
- preserve the strongest rules before stylistic elaboration
- prefer one compact signal note over verbose explanation

## 5. Test Anchors

The contract is covered by `backend/tests/unit/test_stage5_intervention_language_contract.py` with three evidence patterns:

- recent failure evidence
- recent mastery evidence
- mixed pain + progress evidence

The tests assert:

- the contract section appears in the rendered prompt
- the six anchor rules are present
- mixed evidence preserves both pain and progress visibility
- token footprint remains within a compact budget

## 6. Acceptance Note

This artifact is the documentation companion to the prompt contract in `backend/app/orchestration/prompts.py`.
It is intentionally narrow so Wave 1b can close without reopening WS-K1 internals.
