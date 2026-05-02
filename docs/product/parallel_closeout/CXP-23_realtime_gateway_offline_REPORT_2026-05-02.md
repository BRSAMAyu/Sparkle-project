# CXP-23 Report — Realtime Chat, Gateway, Offline, And Multi-Device

## Goal
Make realtime chat delivery understandable and safer across network drops, reconnects, duplicate sends, slow streams, and app/device return paths.

## Work Completed
Gateway delivery:
- Added legacy WebSocket accepted ACKs for normal chat and tool result messages after validation, carrying `request_id`, `message_id`, `server_ts`, and `status=received`.
- Added Redis-backed request-id admission through `ChatHistoryService.TryAcceptRealtimeRequest`, so replaying the same user/request_id during reconnect does not start a second AI stream or duplicate action side effects.
- Added duplicate request handling that returns a recoverable protocol error instead of persisting another user turn or calling the agent again.

Mobile offline/reconnect:
- Persist connected outgoing chat sends before writing to the socket, then mark them `sent` and finally `acked` when gateway ACK arrives.
- Treat `sent` without ACK and retryable `failed` rows as reconnect candidates, not dead records.
- Preserve failed pending messages in the offline queue instead of deleting them after max reconnect attempts, enabling manual reconnect/retry.
- De-duplicate restored offline rows against the in-memory pending queue before flushing, preventing double replay after reconnect.
- Parse both `timestamp` and gateway `server_ts` ACK timestamps.

Tests:
- Added gateway tests for legacy ACK payload contract and Redis request-id de-duplication.
- Updated the mobile WebSocket parser test to cover `server_ts` ACKs.

## User Experience Before / After
Before: a message sent during weak network could be written to the socket without any accepted ACK, then disappear from retry handling if the app dropped or returned later. Reconnect restore could also replay duplicated in-memory and stored pending messages.

After: the user sees a delivery path with a concrete accepted state. If the network drops, unacked sends remain retryable. If a replay uses the same `request_id`, the gateway refuses to run the AI/action chain twice.

## Cross-System Links
- Gateway protocol: `backend/gateway/internal/handler/chat_orchestrator.go`, `chat_orchestrator_responder.go`, `chat_orchestrator_chatflow.go`
- Gateway persistence/idempotency: `backend/gateway/internal/service/chat_history.go`
- Mobile offline queue: `mobile/lib/core/offline/offline_message_queue_service.dart`, `offline_chat_message.dart`
- Mobile realtime client: `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart`
- Tests: `backend/gateway/internal/handler/chat_orchestrator_test.go`, `chat_history_contract_test.go`, `mobile/test/features/chat/data/services/websocket_chat_service_v2_test.dart`

## Verification
- Passed: `cd backend/gateway && go test ./internal/handler -run 'TestLegacyAcceptedAckPayloadCarriesRequestID|TestTryAcceptRealtimeRequestDeduplicatesRequestID|TestConvertResponseToJSON|TestChatOrchestratorIdleTimeoutClosesFromHandlerLoop'`
- Passed: `git diff --check` for the CXP-23 touched files.
- Blocked by unrelated existing mobile compile errors: `cd mobile && flutter test test/features/chat/data/services/websocket_chat_service_v2_test.dart`
  - `lib/features/visual_elements/presentation/shared/visual_element_palette.dart:90-99` missing `const Color(...)`
  - `lib/features/home/presentation/widgets/openclaw_automation_panel.dart:158,318` and `openclaw_node_management_panel.dart:214` contain `const SizedBox` trees that reference non-constant `DS.textOnPrimary`

Manual QA path coverage by implementation:
- Network drop: unacked connected sends are stored as `sent`, later restored via `loadRetryableForUser`.
- App background/return: restored queue is user-scoped and de-duplicated against memory before flush.
- Duplicate send: Redis `SETNX` request-id guard prevents a second agent/action run for the same user/request_id.
- Slow stream: existing active-stream heartbeat suppression remains intact; ACK now separates delivery acceptance from long generation.
- Cross-device return: gateway request admission and existing session history restoration avoid contradictory duplicate active runs without introducing strong locking.

## Remaining Risks
- The duplicate replay response is protective rather than full response replay. If the ACK was lost and the user retries the same request from another device, they may need to refresh conversation history to see the original stream result.
- Redis outage degrades request-id de-duplication to best-effort because chat history/idempotency storage is Redis-backed.
- Mobile focused test needs the unrelated const errors fixed before it can compile in this worktree.

## Commit
Branch: `codex/CXP-23-realtime-gateway-offline`

Code commit: `ea585b410` (`CXP-23 harden realtime chat delivery`)
