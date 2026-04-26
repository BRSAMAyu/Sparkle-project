# Internationalization (i18n) Progress Tracking

## Objective
Ensure a complete and harmonious internationalization experience. Chinese mode should be fully Chinese, and English mode should be fully English, with no language mixing in UI, API responses, or AI prompts.

## Status Summary
- **Backend (Python):** Initial i18n framework created. LangGraphPlanner partially refactored.
- **Gateway (Go):** Pending investigation of localized error handling.
- **Frontend (Flutter):** Pending refactoring of hardcoded strings in statistics and other modules.

## Team Responsibilities
- **Gemini A (Infrastucture/Backend):** Focused on `backend/app/core/i18n.py` and LangGraph refactoring.
- **Gemini B (Frontend/Gateway/Refactoring):** Focused on Flutter `arb` cleanup, Go Gateway localization, and backend service token decoupling.

## Task List

### Phase 1: Backend (Python) i18n Infrastructure
- [x] Create `backend/app/core/i18n.py` framework.
- [x] Create initial translation files (`en.json`, `zh.json`).
- [x] Refactor `LangGraphPlanner` to use `I18n` for prompt generation.
- [x] Refactor `MultiAgentWorkflowAdapter` hardcoded strings.
- [ ] Refactor `context_builder.py` hardcoded strings.
- [ ] Ensure user language preference is propagated through all AI services.
- [ ] **[Gemini B]** Decouple hardcoded Chinese tokens in `memory_inferred_write_lane.py` and `source_state_encoder.py`.

### Phase 2: Gateway (Go) Localization [Gemini B]
- [ ] Identify hardcoded Chinese in error handlers.
- [ ] Implement/Update middleware to respect `Accept-Language` or user preferences.
- [ ] Localize static response messages.

### Phase 3: Frontend (Flutter) Hardcoded String Cleanup [Gemini B]
- [ ] Extract hardcoded strings from `mobile/lib/core/statistics/`.
- [ ] Extract hardcoded strings from `mobile/lib/features/home/domain/services/enhanced_intent_classifier.dart`.
- [ ] Update `app_en.arb` and `app_zh.arb`.
- [ ] Fix language mixing in interactive components (dialogs, snacks).

### Phase 4: Validation & Quality Assurance
- [ ] Run full system in English mode and verify no Chinese appears.
- [ ] Run full system in Chinese mode and verify no English appears (except technical terms).
- [ ] Verify AI rationale and prompts are correctly localized.

## Change Log

### 2026-04-26 (Sync)
- Consolidated tracking into `I18N_PROGRESS.md`.
- Assigned Gemini B to Frontend/Gateway and high-impact backend refactors.

