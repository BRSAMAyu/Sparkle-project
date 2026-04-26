# Internationalization (i18n) Progress Tracking

## Objective
Ensure a complete and harmonious internationalization experience. Chinese mode should be fully Chinese, and English mode should be fully English, with no language mixing in UI, API responses, or AI prompts.

## Status Summary
- **Backend (Python):** i18n framework complete (core/i18n.py). Locale data files expanded (cognitive, context, synthesis, workflow sections). MultiAgentWorkflowAdapter, LangGraphPlanner, context_builder refactored to use I18n.t(). Locale propagated from user preferences through pipeline. **~400+ hardcoded user-facing Chinese strings remain** in error_replan_bridge.py, insight_copy.py, metacognition_registry.py, self_evolution_service.py, tool_fallback.py, agent_activity.py, capsule_generation_service.py, tool files.
- **Gateway (Go):** i18n infrastructure complete (internal/i18n package + middleware/i18n.go + locales/). Locale header parsing (X-Language, Accept-Language) implemented. **~45 hardcoded display strings remain** in chat_orchestrator_feedback.go, auth.go, rate_limit.go, chat_history.go, chat_orchestrator_protocol.go.
- **Frontend (Flutter):** l10n system fully configured with app_en.arb (~1900 keys) and app_zh.arb (~1900 keys). Intent keywords decoupled to intent_keywords.dart. EnhancedIntentClassifier refactored. Statistics aggregation labels localized. **~60-70 files with hardcoded Chinese remain** in task_card.dart, weather_guide_screen.dart, execution_copy.dart, vocabulary_lookup_tool.dart, flash_capsule_tool.dart, review_plan_hub_screen.dart, dashboard_repository.dart, knowledge_detail_screen.dart, etc.

## Team Responsibilities
- **Gemini A (Infrastructure/Backend):** Focused on `backend/app/core/i18n.py` and LangGraph refactoring. Completed.
- **Gemini B (Frontend/Gateway/Refactoring):** Flutter `arb` cleanup, Go Gateway localization, intent classifier decoupling. Completed infrastructure.
- **Phase 3 Remaining (Current):** Fix all remaining hardcoded Chinese strings across all three stacks. Ensure complete language separation.

## Task List

### Phase 1: Backend (Python) i18n Infrastructure
- [x] Create `backend/app/core/i18n.py` framework.
- [x] Create initial translation files (`en.json`, `zh.json`).
- [x] Expand translation files with cognitive, context, synthesis, workflow sections.
- [x] Refactor `LangGraphPlanner` to use `I18n` for prompt generation.
- [x] Refactor `MultiAgentWorkflowAdapter` hardcoded strings.
- [x] Refactor `context_builder.py` — propagate locale, use I18n.t() for defaults.
- [x] Ensure user language preference is propagated through all AI services.

### Phase 1.5: Backend Hardcoded String Cleanup [CURRENT]
- [ ] Fix `services/error_replan_bridge.py` — ~140 lines of Chinese repair strategies, notifications, LLM prompts, button labels
- [ ] Fix `services/insight_copy.py` — ~70 lines of Chinese cognitive pattern display names, descriptions, solutions
- [ ] Fix `services/metacognition_registry.py` — ~20 Chinese reflection/dashboard template strings
- [ ] Fix `services/self_evolution_service.py` — ~15 lines of Chinese LLM hints and notification descriptions
- [ ] Fix `services/error_book_service.py` — ~50 lines of Chinese error types and analysis templates
- [ ] Fix `services/task_guide_service.py` — ~60 lines of Chinese task type names, LLM prompts
- [ ] Fix `services/accountability_notification_service.py` — ~30 lines of Chinese notification text
- [ ] Fix `services/notification_push_service.py` — ~10 lines of Chinese notification templates
- [ ] Fix `services/audit_service.py` — ~6 lines of Chinese audit notifications
- [ ] Fix `services/capsule_generation_service.py` — ~40 lines of Chinese prompts and fallback text
- [ ] Fix `services/nightly_review_service.py` — ~8 lines of Chinese summary text
- [ ] Fix `services/share_card_templates.py` — ~8 lines of Chinese template descriptions
- [ ] Fix `agents/tool_fallback.py` — ~40 lines of Chinese fallback messages
- [ ] Fix `orchestration/agent_activity.py` — ~25 lines of Chinese agent names and descriptions
- [ ] Fix `orchestration/prompts.py` — ~25 lines of Chinese warmth/candor/relationship descriptions
- [ ] Fix `orchestration/session_feedback.py` — ~20 lines of Chinese feedback prefixes and triggers
- [ ] Fix `orchestration/learning_state_fragment.py` — ~15 lines of Chinese state descriptions
- [ ] Fix `tools/*.py` — ~150 lines of Chinese tool descriptions, error messages, examples
- [ ] Fix `core/websocket.py` — ~20 lines of Chinese notification type labels
- [ ] Fix `services/translation_service.py` — ~15 lines of Chinese domain term mappings

### Phase 2: Gateway (Go) Localization [CURRENT]
- [x] Implement i18n package (`internal/i18n/i18n.go`).
- [x] Implement middleware to respect `Accept-Language` or user preferences (`middleware/i18n.go`).
- [x] Create locale files (`locales/en.json`, `locales/zh.json`).
- [ ] Fix `internal/handler/chat_orchestrator_feedback.go` — 28 hardcoded Chinese strings
- [ ] Fix `internal/handler/auth.go` — 6 hardcoded Chinese error messages
- [ ] Fix `internal/middleware/rate_limit.go` — 7 hardcoded Chinese rate limit messages
- [ ] Fix `internal/service/chat_history.go` — 4 occurrences of "新对话"
- [ ] Fix `internal/handler/chat_orchestrator_protocol.go` — 5 hardcoded Chinese strings
- [ ] Fix `internal/handler/chat_orchestrator.go` — 2 hardcoded Chinese strings
- [ ] Fix `cmd/test_db/main.go` — log strings with Chinese
- [ ] Add all extracted strings to locales/en.json and locales/zh.json

### Phase 3: Frontend (Flutter) Hardcoded String Cleanup [CURRENT]
- [x] Extract hardcoded strings from `mobile/lib/core/statistics/`.
- [x] Extract hardcoded strings from `mobile/lib/features/home/domain/services/enhanced_intent_classifier.dart`.
- [x] Update `app_en.arb` and `app_zh.arb` with ~850+ new keys.
- [ ] Fix `features/task/presentation/screens/task_card.dart` — status labels, confirmation dialogs
- [ ] Fix `features/task/presentation/screens/task_list_screen.dart` — status filters, empty states
- [ ] Fix `features/task/presentation/widgets/execution_copy.dart` — replace `_isChinese` ternary with AppLocalizations
- [ ] Fix `features/task/presentation/screens/task_detail_screen.dart` — section headings, labels
- [ ] Fix `features/task/presentation/widgets/task_guide_panel.dart` — guidance text
- [ ] Fix `features/task/presentation/widgets/task_quick_action_menu.dart` — action labels
- [ ] Fix `features/task/presentation/widgets/stuck_help_sheet.dart` — help copy
- [ ] Fix `features/task/presentation/widgets/execution_result_renderer.dart` — result labels
- [ ] Fix `features/task/presentation/widgets/execution_status_indicator.dart` — status labels
- [ ] Fix `features/home/presentation/screens/weather_guide_screen.dart` — entire weather glossary
- [ ] Fix `features/home/presentation/widgets/weather_presentation.dart` — weather descriptions
- [ ] Fix `features/home/presentation/widgets/home_notification_card.dart` — notification labels
- [ ] Fix `features/home/data/repositories/dashboard_repository.dart` — demo data strings
- [ ] Fix `features/home/presentation/providers/intent_prediction_provider.dart` — action labels
- [ ] Fix `features/reviews/presentation/screens/review_plan_hub_screen.dart` — review screen
- [ ] Fix `features/tools/presentation/widgets/flash_capsule_tool.dart` — tool UI copy
- [ ] Fix `features/tools/presentation/widgets/vocabulary_lookup_tool.dart` — tool UI copy
- [ ] Fix `features/knowledge/presentation/screens/knowledge_detail_screen.dart` — labels
- [ ] Fix `features/knowledge/presentation/widgets/knowledge_card.dart` — status labels
- [ ] Fix `features/onboarding/presentation/screens/interactive_onboarding_screen.dart` — replace `_isChinese` ternary
- [ ] Fix `features/splash/presentation/screens/splash_screen.dart` — welcome text
- [ ] Fix `shared/utils/entity_card_payloads.dart` — fallback labels
- [ ] Fix `shared/entities/visual_element_model.dart` — display names
- [ ] Fix `core/design/widgets/error_widget.dart` — error labels

### Phase 4: Validation & Quality Assurance
- [ ] Run full system in English mode and verify no Chinese appears.
- [ ] Run full system in Chinese mode and verify no English appears (except technical terms).
- [ ] Verify AI rationale and prompts are correctly localized.
- [ ] Verify Go gateway build passes.
- [ ] Verify Flutter analyze + build passes.
- [ ] Verify Python backend imports and tests pass.

## Change Log

### 2026-04-26 (Phase 3 — Infrastructure Complete, Cleanup Underway)
- **Committed:** i18n infrastructure for all 3 stacks (commit `aefbad9f`).
- **Python backend:** core/i18n.py, locale files expanded, context_builder refactored, locale propagation.
- **Go gateway:** internal/i18n package, middleware/i18n.go, locale files with chat status strings.
- **Flutter:** ARB files expanded to ~1900 keys each, generated localization classes updated, intent_keywords.dart created.
- **Remaining catalogued:** ~400+ Python, ~45 Go, ~60-70 Flutter files with hardcoded Chinese identified for cleanup.
- **Plan:** Dispatch parallel agents to fix all remaining hardcoded strings.

### 2026-04-26 (Previous Sync)
- Consolidated tracking into `I18N_PROGRESS.md`.
- Assigned Gemini B to Frontend/Gateway and high-impact backend refactors.

## Audit Trail

Each fix commit should:
1. Add extracted Chinese strings to the appropriate locale files (en.json/zh.json or en.arb/zh.arb)
2. Modify source code to reference i18n keys via I18n.t() / i18n.T() / AppLocalizations.of()
3. Never leave Chinese strings in source code (comments are allowed only if truly developer-facing)
4. Update this document's task list
