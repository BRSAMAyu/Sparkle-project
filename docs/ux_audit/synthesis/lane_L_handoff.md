# Lane L Handoff — 跨页数据新鲜度 + RefreshIndicator

**Status**: DONE

**Changed files**:
- `mobile/lib/features/plan/presentation/screens/learning_portfolio_screen.dart` — removed duplicate nested `RefreshIndicator` (outer one retained, wraps all states including loading/error/empty via `_ScrollableStateFill`)
- `mobile/test/features/plan/presentation/screens/learning_portfolio_screen_test.dart` — updated `_buildApp` to use GoRouter (screen now requires it for route-based refresh); added pull-to-refresh test
- `mobile/test/features/achievement/presentation/screens/achievement_list_screen_test.dart` — updated to use GoRouter; added RefreshIndicator presence test

**Pre-existing changes** (confirmed already in codebase, NOT by this lane):
- Galaxy screen already has `RefreshIndicator` + `CustomScrollView` + `AlwaysScrollableScrollPhysics` + `_handlePullToRefresh`
- Achievement list screen already has `RefreshIndicator` + `CustomScrollView` + `AlwaysScrollableScrollPhysics` + `_refreshAchievements` + route visibility listener
- Learning portfolio screen already had route visibility listener + `_ScrollableStateFill` + outer `RefreshIndicator`

**User-visible effect**: All three key pages (Galaxy, Learning Portfolio, Achievement) support pull-to-refresh. Returning to these pages via route navigation also auto-refreshes data.

**Tests passed**: 7/7 (5 portfolio + 2 achievement), 0 errors in flutter analyze.
