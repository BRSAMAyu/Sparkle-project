# Rule BA - Gateway Contract Parity

Rule BA locks the Stage 38 chat history contract between Go gateway responses and Flutter chat history parsing.

## Contract

1. `backend/gateway/internal/handler/chat_history.go` must expose a JSON field set that is a superset of the keys consumed by `mobile/lib/features/chat/data/models/chat_message_model.dart`.
2. Missing Go keys are hard failures even if Flutter currently has fallbacks.
3. Extra Go keys are allowed, because BA protects minimum parity rather than forbidding superset responses.

## Source Of Truth

- Go response DTO: `backend/gateway/internal/handler/chat_history.go`
- Mobile model: `mobile/lib/features/chat/data/models/chat_message_model.dart`
- Guard: `scripts/guards/check_rule_ba_gateway_contract_parity.py`
- Repo test: `backend/tests/unit/test_rule_ba_guard.py`

## Stage 38 Scope

- The parity denominator is the chat history message payload returned by `GetConversationHistory`.
- The guard scans Go `json:"..."` tags and Dart JSON-consumed fields, including fallback keys referenced in `ChatMessageModel.fromJson(...)`.

## Stage 38 Notes

- This rule intentionally focuses on implementation parity; it does not modify proto definitions.
- `conversation_id` and `session_id` are both retained because Flutter history hydration reads both.
