# CXP-01 Report — Aurora Everyday Presence

## Goal
Make Aurora show up in normal home and chat usage as a compact, correctable judgment instead of a separate demo surface. The user should see what Aurora thinks, why it might be uncertain, and how to correct it.

## Work Completed
- Chat presence: ordinary chat context now reads the existing Aurora control surface and produces an `aurora_everyday_presence` payload with status, uncertainty, evidence, memory references, return tier, last correction effect, and next-step suggestion.
- Chat receipts: response metadata now turns that payload into a correctable Aurora receipt only when it matters, such as risk, needed confirmation, stale/fallback conversation state, return after absence, or a recent correction.
- Home status band: the dashboard Aurora band can expand into a short explanation of the current read, explicitly says the read may be wrong, and keeps a correction path visible through chips or chat.
- Tests: response-builder coverage now proves the everyday presence payload becomes a correctable receipt and stays quiet when the control surface says not to surface it.

## User Experience Before / After
- First open: before, the home band could show a status line but did not unpack the judgment. After, tapping the band reveals the current read and correction affordance.
- Ordinary chat: before, Aurora receipts covered memory/source/spine lanes but not the everyday status judgment. After, chat can show "I may be misreading this" with evidence and correction actions when the state is uncertain.
- Status-band correction: before, correction chips existed but the reason to use them was less explicit. After, expanded copy frames the band as a correctable read.
- Return after absence: before, return context could exist separately. After, personalized/checkpoint returns can surface through the same Aurora presence receipt so the user sees that Sparkle is intentionally resuming from prior context.

## Cross-System Links
- Backend context: `backend/app/orchestration/context_builder.py`
- Backend response metadata/receipts: `backend/app/orchestration/response_builder.py`
- Backend tests: `backend/tests/unit/orchestrator/mixins/test_response_builder_mixin.py`
- Mobile dashboard UI: `mobile/lib/features/home/presentation/widgets/aurora_status_band.dart`

## Verification
- `cd backend && .venv/bin/python -m pytest tests/unit/orchestrator/mixins/test_response_builder_mixin.py` — 16 passed.
- `cd mobile && flutter analyze lib/features/home/presentation/widgets/aurora_status_band.dart` — no issues found.
- Manual QA expectation: open dashboard, tap Aurora band with a non-empty summary, verify expanded copy says the judgment may be wrong and shows correction chips or "Correct in chat"; in chat, create a needs-confirm/risk/fallback/returning context and verify metadata includes an `aurora_experience_receipt` sourced from `aurora_everyday_presence`.

## Remaining Risks
- The control-surface read is attached in the main cognitive-context path; if a fallback user-context branch is used, Aurora presence may stay quiet. Owner suggestion: final integration should add the same helper to fallback branches if those are still live.
- This slice did not add screenshots because local branch ownership was unstable during parallel execution. Owner suggestion: final reviewer should capture one dashboard expanded-band screenshot and one chat receipt screenshot after merging.

## Commit
Branch: `codex/CXP-01-aurora-everyday-presence`
Commit: `1998b080c`
