# Internationalization (i18n) Progress Tracking

## Objective
Ensure a complete and harmonious internationalization experience. Chinese mode should be fully Chinese, and English mode should be fully English, with no language mixing in UI, API responses, or AI prompts.

## Status Summary
- **Backend (Python):** ✅ All high-priority user-facing strings externalized (~353 strings). Locale propagation complete. NLP/intent keywords preserved (input parsing only).
- **Gateway (Go):** ✅ All user-facing strings externalized (~85 strings). Progress detection refactored to be locale-independent. Build passes.
- **Frontend (Flutter):** ✅ 196 new ARB keys added across 14 Dart files. `execution_copy.dart` refactored from `_isChinese` ternary to `AppLocalizations`. `flutter analyze` — 0 errors.
- **Remaining:** Low-priority items (tool files, prompts.py, weather guide screen, dashboard demo data, intent prediction labels, vocabulary/flash capsule tools, onboarding refactoring).

## Task List

### Phase 1: Backend (Python) i18n Infrastructure
- [x] Create `backend/app/core/i18n.py` framework.
- [x] Create initial translation files (`en.json`, `zh.json`).
- [x] Expand translation files with cognitive, context, synthesis, workflow sections.
- [x] Refactor `LangGraphPlanner` to use `I18n` for prompt generation.
- [x] Refactor `MultiAgentWorkflowAdapter` hardcoded strings.
- [x] Refactor `context_builder.py` — propagate locale, use I18n.t() for defaults.
- [x] Ensure user language preference is propagated through all AI services.

### Phase 1.5: Backend Hardcoded String Cleanup ✅
- [x] Fix `services/error_replan_bridge.py` — repair strategies, notifications, LLM prompts, button labels
- [x] Fix `services/insight_copy.py` — cognitive pattern display names, descriptions, solutions
- [x] Fix `services/metacognition_registry.py` — reflection/dashboard template strings
- [x] Fix `services/self_evolution_service.py` — LLM hints and notification descriptions
- [x] Fix `services/error_book_service.py` — error types and analysis templates
- [x] Fix `services/task_guide_service.py` — task type names, LLM prompts
- [x] Fix `services/accountability_notification_service.py` — notification text
- [x] Fix `services/notification_push_service.py` — notification templates
- [x] Fix `services/audit_service.py` — audit notifications
- [x] Fix `services/capsule_generation_service.py` — prompts and fallback text
- [x] Fix `services/nightly_review_service.py` — summary text
- [x] Fix `services/share_card_templates.py` — template descriptions
- [x] Fix `agents/tool_fallback.py` — fallback messages
- [x] Fix `orchestration/agent_activity.py` — agent names and descriptions
- [x] Fix `orchestration/session_feedback.py` — feedback prefixes and triggers
- [x] Fix `orchestration/learning_state_fragment.py` — state descriptions
- [x] Fix `core/websocket.py` — notification type labels

### Phase 2: Gateway (Go) Localization ✅
- [x] Implement i18n package (`internal/i18n/i18n.go`).
- [x] Implement middleware to respect `Accept-Language` or user preferences.
- [x] Create locale files (`locales/en.json`, `locales/zh.json`).
- [x] Fix `internal/handler/chat_orchestrator_feedback.go` — 28 strings
- [x] Fix `internal/handler/auth.go` — 6 error messages
- [x] Fix `internal/middleware/rate_limit.go` — 7 rate limit messages
- [x] Fix `internal/service/chat_history.go` — 4 "新对话" occurrences
- [x] Fix `internal/handler/chat_orchestrator_protocol.go` — evidence summaries, progress detection refactored
- [x] Fix `internal/handler/chat_orchestrator.go` — message length errors
- [x] Fix test data across 6 test files

### Phase 3: Frontend (Flutter) Hardcoded String Cleanup ✅ (Core)
- [x] Extract hardcoded strings from statistics module.
- [x] Extract hardcoded strings from `enhanced_intent_classifier.dart`.
- [x] Update `app_en.arb` and `app_zh.arb` with ~850+ keys (infrastructure).
- [x] Fix `task_card.dart` — status labels, confirmation dialogs
- [x] Fix `task_list_screen.dart` — priority labels, empty states
- [x] Fix `execution_copy.dart` — full refactor from `_isChinese` ternary
- [x] Fix `task_detail_screen.dart` — section headings, labels
- [x] Fix `task_guide_panel.dart` — ~40 guidance section titles
- [x] Fix `task_quick_action_menu.dart` — action labels
- [x] Fix `stuck_help_sheet.dart` — help copy
- [x] Fix `execution_result_renderer.dart` — result labels
- [x] Fix `execution_status_indicator.dart` — 13 status labels
- [x] Fix `review_plan_hub_screen.dart` — review screen text
- [x] Fix `knowledge_detail_screen.dart` — relation labels
- [x] Fix `knowledge_card.dart` — mastery level labels
- [x] Fix `home_notification_card.dart` — notification labels
- [x] Fix `splash_screen.dart` — welcome subtitle
- [ ] Fix `weather_guide_screen.dart` + `weather_presentation.dart` — weather glossary (~30 strings)
- [ ] Fix `dashboard_repository.dart` — demo data strings
- [ ] Fix `intent_prediction_provider.dart` — action labels (~50 strings)
- [ ] Fix `vocabulary_lookup_tool.dart` — tool UI copy (~40 strings)
- [ ] Fix `flash_capsule_tool.dart` — tool UI copy (~50 strings)
- [ ] Fix `onboarding/interactive_onboarding_screen.dart` — replace `_isChinese` ternary
- [ ] Fix `entity_card_payloads.dart` — fallback labels
- [ ] Fix `visual_element_model.dart` — display names
- [ ] Fix `error_widget.dart` — remaining error labels

### Phase 4: Validation & Quality Assurance
- [x] Go gateway build verified.
- [x] Flutter gen-l10n + analyze verified (0 errors).
- [ ] Run full system in English mode and verify no Chinese appears.
- [ ] Run full system in Chinese mode and verify no English appears (except technical terms).
- [ ] Verify AI rationale and prompts are correctly localized.
- [ ] Verify Python backend imports and tests pass.

## Change Log

### 2026-04-26 (Phase 1.5 + 2 + 3 Core Complete)
- **Commit `4a098a3c`:** Python backend ~353 strings externalized across 17 services/files.
- **Commit `3cc989fc`:** Go gateway ~85 strings externalized across 10 source + 6 test files. Progress detection refactored.
- **Commit `901976f5`:** Flutter ~196 new ARB keys across 14 Dart files. execution_copy.dart refactored.
- **Remaining:** ~6 medium-priority Flutter files and fine-tuning still open.

### 2026-04-26 (Infrastructure Complete)
- **Commit `aefbad9f`:** i18n infrastructure for all 3 stacks.
- **Commit `ccb8a6d9`:** Comprehensive I18N_PROGRESS.md.

### 2026-04-26 (Previous)
- Consolidated tracking into `I18N_PROGRESS.md`.
- Assigned Gemini B to Frontend/Gateway and high-impact backend refactors.

## Commit Audit Trail

| Commit | Description | Files |
|--------|-------------|-------|
| `aefbad9f` | i18n infra — Go pkg+middleware+locales, Python I18n class, Flutter intent_keywords | 12 files |
| `ccb8a6d9` | i18n progress tracking doc | 1 file |
| `4a098a3c` | Python backend ~353 strings externalized | 19 files |
| `3cc989fc` | Go gateway ~85 strings externalized | 19 files |
| `901976f5` | Flutter ~196 ARB keys, 14 Dart files refactored | 19 files |

## Audit Trail

Each fix commit should:
1. Add extracted Chinese strings to the appropriate locale files (en.json/zh.json or en.arb/zh.arb)
2. Modify source code to reference i18n keys via I18n.t() / i18n.T() / AppLocalizations.of()
3. Never leave Chinese strings in source code (comments are allowed only if truly developer-facing)
4. Update this document's task list
