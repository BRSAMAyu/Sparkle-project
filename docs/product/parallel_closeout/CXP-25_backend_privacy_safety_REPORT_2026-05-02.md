# CXP-25 Report — Backend Contract, Privacy, And Safety Boundaries

## Goal
Strengthen backend/gateway privacy boundaries so identifiers, sensitive comments, secrets, and PII do not leak through routine logs while existing community visibility, soft-delete, and block boundaries remain enforceable.

## Work Completed
- Added `backend/gateway/internal/logsafe`, a small shared log-safety helper for stable user-id hashing and redaction of common PII/secret shapes before text reaches logs.
- Wired log-safe hashing into remaining gateway auth, WebSocket auth, chat feedback, proto mastery feedback, and Galaxy cache paths that still logged raw user identifiers.
- Redacted freeform plan-review comments before logging while preserving the original comment in the backend request payload.
- Changed gateway sanitized-error logging to record redacted string fields instead of attaching the raw `error` object, reducing risk of secret, token, SQL, or user-text leakage in centralized logs.
- Rechecked community block-boundary tests covering block creation, reverse block checks, friendship/accountability cleanup, and blocked sharing rejection.

## User Experience Before / After
Before: a user could make a normal chat correction or plan-review comment containing an email, phone number, token-like value, or sensitive explanation, and that text could appear in gateway logs. Some auth/WebSocket paths also still emitted raw user identifiers.

After: the product behavior stays the same, but logs carry stable non-reversible user hashes and redacted sensitive text. Operators can still debug request flow by hash/request id/action id without exposing the user's private content.

## Cross-System Links
- Gateway privacy/logging: `backend/gateway/internal/logsafe`, chat feedback, chat protocol, error sanitizer, auth middleware, WebSocket auth middleware, Galaxy handler.
- Community safety: existing Python community service/API tests continue to enforce block, reverse block, and share rejection behavior.
- Correction provenance: current Aurora correction payloads already carry surface/source/conversation/message/routing ids; a focused Python run exposed stale test expectations around the newer routing provenance fields.

## Verification
- `cd backend/gateway && go test ./internal/logsafe`
- `cd backend/gateway && go test ./internal/logsafe ./internal/middleware ./internal/handler -run 'TestExtractErrorMessage|TestBuildExecutionSummaryToolResultPayload|TestDecodeChatRequestEnvelopePreservesAuroraCorrectionPayload'`
- `pytest backend/tests/test_community_security.py -q`
- Broader check attempted: `go test ./internal/logsafe ./internal/handler ./internal/middleware` failed in existing `TestChatOrchestrator_QuotaIntegration` (`expected error`, got `ack`).
- Broader Python check attempted: `pytest backend/tests/unit/test_aurora_correction_payload.py backend/tests/unit/test_memory_inferred_write_lane.py backend/tests/test_community_security.py -q` had 4 failures: one stale exact payload expectation missing routing provenance fields, plus three existing inferred-memory prompt/feature-flag failures.

## Remaining Risks
- Several unrelated gateway `zap.Error(err)` call sites remain outside this focused slice; they should be audited with endpoint-specific context before blanket redaction.
- The broader handler quota failure should be owned by the realtime/chat gateway slice.
- The inferred-memory test failures should be owned by the memory/profile slice; they affect feature-flag isolation and prompt inclusion, not the gateway log-safety change.
- No commit was created because the shared worktree contains many unrelated active changes across backend and mobile; staging whole files would risk committing other agents' work.

## Commit
Branch: `codex/CXP-25-backend-privacy`
Commit: not created in this shared dirty worktree.
