# Mobile UI Rollout Inventory

Last updated: 2026-03-20

## Inventory Snapshot

- Feature systems: 33
- Feature Dart files under `mobile/lib/features`: 589
- Screen files under `mobile/lib/features`: 100
- Non-screen feature files: 489
- Core Dart files under `mobile/lib/core`: 188
- Design-system Dart files under `mobile/lib/core/design`: 47
- Shared Dart files under `mobile/lib/shared`: 26
- Approximate widget-class count under `mobile/lib`: 963

## Feature Matrix

| System | Screens | Other Dart | Total |
|---|---:|---:|---:|
| achievement | 5 | 17 | 22 |
| admin | 0 | 1 | 1 |
| auth | 5 | 7 | 12 |
| calendar | 2 | 11 | 13 |
| chat | 3 | 66 | 69 |
| cognitive | 4 | 28 | 32 |
| community | 19 | 36 | 55 |
| demo | 1 | 0 | 1 |
| document | 0 | 9 | 9 |
| error_book | 4 | 14 | 18 |
| file | 0 | 6 | 6 |
| focus | 3 | 26 | 29 |
| galaxy | 1 | 35 | 36 |
| home | 3 | 61 | 64 |
| insights | 1 | 9 | 10 |
| intent | 0 | 5 | 5 |
| knowledge | 1 | 9 | 10 |
| leaderboard | 1 | 2 | 3 |
| memory | 3 | 5 | 8 |
| notification_center | 2 | 12 | 14 |
| onboarding | 1 | 2 | 3 |
| photon | 1 | 5 | 6 |
| plan | 7 | 21 | 28 |
| reviews | 0 | 4 | 4 |
| seed_library | 3 | 7 | 10 |
| settings | 1 | 1 | 2 |
| shop | 1 | 10 | 11 |
| splash | 1 | 2 | 3 |
| task | 5 | 22 | 27 |
| tools | 2 | 18 | 20 |
| translation | 1 | 10 | 11 |
| user | 18 | 15 | 33 |
| visual_elements | 1 | 10 | 11 |
| vocabulary | 0 | 3 | 3 |

## Coverage Checklist

Legend:
- `Visual`: color, contrast, spacing, surfaces, dark/light parity
- `Motion`: page transition, press motion, sheet/dialog entrance, list/card choreography
- `Audio`: trigger SFX, state-change SFX, persistent ambience where appropriate
- `Haptic`: tap, selection, confirm, success, warning, error

| Chain | Visual | Motion | Audio | Haptic | Status |
|---|---|---|---|---|---|
| Home dashboard | In progress | In progress | In progress | In progress | Active |
| AI chat | In progress | In progress | In progress | In progress | Active |
| Community | In progress | In progress | In progress | In progress | Active |
| Achievement | In progress | In progress | In progress | In progress | Active |
| Galaxy | In progress | In progress | Planned | In progress | Active |
| Calendar | In progress | In progress | In progress | In progress | Active |
| Task | In progress | Planned | Planned | Planned | Queued |
| Tools | In progress | In progress | In progress | In progress | Active |
| Cognitive | Planned | Planned | Planned | Planned | Queued |
| Focus | Planned | Planned | Planned | Planned | Queued |
| User/settings | In progress | Planned | Planned | Planned | Queued |
| Auth/onboarding | Planned | Planned | Planned | Planned | Queued |
| Error/low-frequency overlays | In progress | Planned | Planned | Planned | Active |

## Screen Inventory By System

### achievement
- `achievement_contract_screen.dart`
- `achievement_detail_screen.dart`
- `achievement_list_screen.dart`
- `achievement_map_screen.dart`
- `streak_details_screen.dart`

### auth
- `forgot_password_screen.dart`
- `legal_document_screen.dart`
- `login_screen.dart`
- `register_screen.dart`
- `reset_password_screen.dart`

### calendar
- `calendar_stats_screen.dart`
- `daily_detail_screen.dart`

### chat
- `chat_screen.dart`
- `group_chat_screen.dart`
- `private_chat_screen.dart`

### cognitive
- `capsule_detail_screen.dart`
- `capsule_jobs_screen.dart`
- `curiosity_capsule_screen.dart`
- `pattern_list_screen.dart`

### community
- `accountability_detail_screen.dart`
- `accountability_screen.dart`
- `blocked_users_screen.dart`
- `community_main_screen.dart`
- `community_screen.dart`
- `create_group_screen.dart`
- `create_post_screen.dart`
- `favorites_screen.dart`
- `friend_profile_screen.dart`
- `friends_screen.dart`
- `group_detail_screen.dart`
- `group_discover_screen.dart`
- `group_files_screen.dart`
- `group_list_screen.dart`
- `group_members_screen.dart`
- `group_moderation_screen.dart`
- `group_search_screen.dart`
- `group_tasks_screen.dart`
- `user_search_screen.dart`

### demo
- `competition_demo_screen.dart`

### error_book
- `add_error_screen.dart`
- `error_detail_screen.dart`
- `error_list_screen.dart`
- `review_screen.dart`

### focus
- `focus_main_screen.dart`
- `focus_statistics_screen.dart`
- `mindfulness_mode_screen.dart`

### galaxy
- `galaxy_screen.dart`

### home
- `dashboard_screen.dart`
- `notification_list_screen.dart`
- `task_monitor_screen.dart`

### insights
- `learning_forecast_screen.dart`

### knowledge
- `knowledge_detail_screen.dart`

### leaderboard
- `leaderboard_screen.dart`

### memory
- `memory_detail_screen.dart`
- `memory_panel_screen.dart`
- `memory_settings_screen.dart`

### notification_center
- `notification_analytics_screen.dart`
- `notification_center_screen.dart`

### onboarding
- `interactive_onboarding_screen.dart`

### photon
- `photon_transfer_screen.dart`

### plan
- `growth_screen.dart`
- `plan_create_screen.dart`
- `plan_detail_screen.dart`
- `plan_edit_screen.dart`
- `plan_history_screen.dart`
- `sprint_history_screen.dart`
- `sprint_screen.dart`

### seed_library
- `create_library_screen.dart`
- `seed_library_detail_screen.dart`
- `seed_library_list_screen.dart`

### settings
- `transparency_settings_screen.dart`

### shop
- `shop_screen.dart`

### splash
- `splash_screen.dart`

### task
- `task_create_screen.dart`
- `task_detail_screen.dart`
- `task_execution_screen.dart`
- `task_list_screen.dart`
- `task_reminder_settings_screen.dart`

### tools
- `tool_host_screen.dart`
- `tool_library_screen.dart`

### translation
- `translation_history_screen.dart`

### user
- `account_security_screen.dart`
- `delete_account_screen.dart`
- `edit_profile_screen.dart`
- `guest_upgrade_screen.dart`
- `learning_mode_screen.dart`
- `password_reset_screen.dart`
- `persona_onboarding_screen.dart`
- `profile_screen.dart`
- `schedule_preferences_screen.dart`
- `security_log_screen.dart`
- `session_management_screen.dart`
- `smart_push_settings_screen.dart`
- `social_accounts_screen.dart`
- `sync_center_screen.dart`
- `system_updates_screen.dart`
- `theme_settings_screen.dart`
- `unified_settings_screen.dart`
- `user_persona_screen.dart`

### visual_elements
- `visual_elements_screen.dart`

## Shared Surfaces To Cover Globally

- `SparklePressable`
- `SparkleButton`
- `SparkleIconButton`
- `CustomButton`
- `AppFeedback`
- `ResponsiveScaffold`
- `ConfirmationDialog`
- `UniversalShareBottomSheet`
- Route transitions powered by `GoRouter` and `CustomTransitionPage`
- Navigation shell and tab destinations

## Rollout Notes

- This checklist is the tracking baseline for full-app motion, audio, haptic, and visual polish.
- Priority order: shared surfaces first, then core chains, then secondary pages, then low-frequency states and error overlays.
- UI-only rule: no provider contract, repository contract, network API, or backend protocol changes should be introduced during rollout.
