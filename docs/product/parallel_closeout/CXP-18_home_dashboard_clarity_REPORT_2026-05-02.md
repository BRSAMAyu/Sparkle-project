# CXP-18 Home Dashboard And First-Viewport Clarity Report

Date: 2026-05-02
Branch: `codex/CXP-18-home-dashboard-clarity`

## What Changed

- Reworked the first dashboard viewport around a single command-center card in `mobile/lib/features/home/presentation/screens/dashboard_screen.dart`.
- Consolidated next action, today's task progress, active plan health, deadline, and risk into one actionable surface.
- Kept Aurora's status band directly below the command center so Aurora judgment remains visible without competing with the main action.
- Removed redundant first-viewport growth cards (`TodayGrowthStatusCard`, `ActiveBottleneckAlert`, `NextActionPrompt`) from the dashboard top stack.
- Prevented normal growth header content from appearing above dashboard auth/offline/error states.

## User Impact

Within five seconds, the user now sees:

- Who/where they are: compact status bar with identity, rhythm, weather, and settings route.
- What to do next: command-center primary action opens the chosen task, task list, or first-plan creation.
- How progress looks: task completion count, plan health, plan label, deadline, and progress bar.
- What risk exists: bottleneck/deadline/low-health risk banner routes to Aurora/chat correction.
- What Aurora thinks: the existing Aurora status band remains immediately after the command center with correction chips intact.

## Dashboard Paths

- New user: no active plan renders the command center as "Set a goal you can start today" with a Start with AI/create-plan action.
- Active user: a selected `HomeGrowthTask` becomes the primary command-center title and starts execution through the existing task route.
- Returning user: daily context line stays above the command center, while progress and Aurora status summarize the current situation.
- Error/offline/auth: normal growth header is suppressed; the existing failure-specific dashboard error state is shown without misleading active cards above it.

## QA Evidence

- Ran `dart format lib/features/home/presentation/screens/dashboard_screen.dart`.
- Ran `flutter analyze lib/features/home/presentation/screens/dashboard_screen.dart`.
  - Result: no errors after fixing a bad design token reference.
  - Remaining output is style/info lint only in the existing screen file (`directives_ordering`, `require_trailing_commas`, `discarded_futures`, and similar).

## Manual Screenshot Steps

1. Light/en: launch mobile, open `/home`, verify top order is status bar, daily context, command center, Aurora band.
2. Dark/en: repeat with dark mode and confirm command-center chips, risk banner, and progress bar preserve contrast.
3. zh: switch app language to Chinese and verify command-center title, risk text, and actions fit without overflow.
4. Offline/error: disable network or force `/dashboard/status` failure and verify no normal command/growth cards appear above the error state.
