# Internationalization (i18n) Progress Tracking

## Objective
Ensure a complete and harmonious internationalization experience. Chinese mode should be fully Chinese, and English mode should be fully English, with no language mixing in UI, API responses, or AI prompts.

## Status Summary
- **Backend (Python):** Initial i18n framework created. LangGraphPlanner partially refactored.
- **Gateway (Go):** Pending investigation of localized error handling.
- **Frontend (Flutter):** Pending refactoring of hardcoded strings in statistics and other modules.

## Task List

### Phase 1: Backend (Python) i18n Infrastructure
- [x] Create `backend/app/core/i18n.py` framework.
- [x] Create initial translation files (`en.json`, `zh.json`).
- [x] Refactor `LangGraphPlanner` to use `I18n` for prompt generation.
- [ ] Refactor `MultiAgentWorkflowAdapter` hardcoded strings.
- [ ] Refactor `execution_engine.py` and `context_builder.py` hardcoded strings.
- [ ] Ensure user language preference is propagated through all AI services.

### Phase 2: Gateway (Go) Localization
- [ ] Identify hardcoded Chinese in error handlers.
- [ ] Implement/Update middleware to respect `Accept-Language` or user preferences.
- [ ] Localize static response messages.

### Phase 3: Frontend (Flutter) Hardcoded String Cleanup
- [ ] Extract hardcoded strings from `mobile/lib/core/statistics/`.
- [ ] Extract hardcoded strings from other feature modules.
- [ ] Update `app_en.arb` and `app_zh.arb`.
- [ ] Fix language mixing in interactive components (dialogs, snacks).

### Phase 4: Validation & Quality Assurance
- [ ] Run full system in English mode and verify no Chinese appears.
- [ ] Run full system in Chinese mode and verify no English appears (except technical terms).
- [ ] Verify AI rationale and prompts are correctly localized.

## Change Log

### 2026-04-26
- Created `backend/app/core/i18n.py`: Centralized i18n utility for the Python backend.
- Created `backend/app/data/i18n/en.json` and `zh.json`: Initial translation catalogs.
- Modified `backend/app/orchestration/lang_graph_planner.py`: Integrated `I18n` and refactored planning constraints prompt.
- Modified `backend/app/orchestration/execution_engine.py`: Passed user locale to the planner.
- Created `I18N_PROGRESS.md`: This tracking document.
