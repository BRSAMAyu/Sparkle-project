# Phase 3 Dispatch: Flutter Feature Layer (Part 2)

**3 Parallel Agents** — Plan for after Phase 2 review

## !!! CRITICAL WARNING !!!
Previous agents introduced auto-generated l10n hash keys (like `S.auth4b6c2b`, `S.calendar12345`) that DON'T EXIST. These cause compilation errors.
**NEVER create `S.xxx12345` style references. Always use English string literals instead.**
If you see existing `S.xxx12345` in a file, replace it with an English string literal.

## Agent 3A: Achievement + Insights + Cognitive Features

- `mobile/lib/features/achievement/achievement_routes.dart`
- `mobile/lib/features/achievement/presentation/widgets/achievement_unlock_dialog.dart`
- `mobile/lib/features/achievement/presentation/widgets/achievement_progress_card.dart`
- `mobile/lib/features/achievement/presentation/widgets/achievement_stats_panel.dart`
- `mobile/lib/features/achievement/presentation/widgets/streak_indicator.dart`
- `mobile/lib/features/achievement/presentation/widgets/rarity_badge.dart`
- `mobile/lib/features/achievement/presentation/widgets/achievement_card.dart`
- `mobile/lib/features/achievement/presentation/screens/achievement_detail_screen.dart`
- `mobile/lib/features/achievement/presentation/screens/achievement_map_screen.dart`
- `mobile/lib/features/achievement/presentation/screens/achievement_list_screen.dart`
- `mobile/lib/features/achievement/presentation/screens/milestone_celebration_screen.dart`
- `mobile/lib/features/achievement/presentation/providers/close_to_unlock_provider.dart`
- `mobile/lib/features/achievement/presentation/providers/achievement_provider.dart`
- `mobile/lib/features/achievement/data/repositories/achievement_repository.dart`
- `mobile/lib/features/insights/presentation/widgets/predictive_insights_card.dart`
- `mobile/lib/features/insights/presentation/widgets/weekly_growth_narrative_card.dart`
- `mobile/lib/features/insights/presentation/widgets/learning_path_dialog.dart`
- `mobile/lib/features/insights/presentation/screens/learning_forecast_screen.dart`
- `mobile/lib/features/insights/presentation/screens/learning_insights_overview_screen.dart`
- `mobile/lib/features/insights/data/models/weekly_growth_narrative.dart`
- `mobile/lib/features/cognitive/presentation/widgets/interactive_decay_timeline.dart`
- `mobile/lib/features/cognitive/presentation/widgets/prism_behavior_card.dart`
- `mobile/lib/features/cognitive/presentation/widgets/capsule/capsule_generation_preview.dart`
- `mobile/lib/features/cognitive/presentation/screens/capsule/capsule_detail_screen.dart`
- `mobile/lib/features/cognitive/presentation/screens/capsule/capsule_jobs_screen.dart`
- `mobile/lib/features/cognitive/presentation/screens/pattern_list_screen.dart`
- `mobile/lib/features/cognitive/presentation/providers/capsule_provider.dart`
- `mobile/lib/features/cognitive/data/models/curiosity_capsule_model.dart`
- `mobile/lib/features/cognitive/data/models/capsule_feedback_model.dart`
- `mobile/lib/features/cognitive/data/models/capsule_stats_model.dart`
- `mobile/lib/features/cognitive/data/models/capsule_generation_job_model.dart`
- `mobile/lib/features/cognitive/data/repositories/capsule_repository.dart`

## Agent 3B: Community + Galaxy Features

- `mobile/lib/features/community/presentation/widgets/checkin_interaction.dart`
- `mobile/lib/features/community/presentation/widgets/accountability_heatmap.dart`
- `mobile/lib/features/community/presentation/widgets/group_chat_bubble.dart`
- `mobile/lib/features/community/presentation/widgets/community_widgets.dart`
- `mobile/lib/features/community/presentation/widgets/friends_hub_view.dart`
- `mobile/lib/features/community/presentation/widgets/accountability/checkin_cadence_card.dart`
- `mobile/lib/features/community/presentation/widgets/groups_hub_view.dart`
- `mobile/lib/features/community/presentation/widgets/quick_share_picker_sheet.dart`
- `mobile/lib/features/community/presentation/widgets/achievement_badge.dart`
- `mobile/lib/features/community/presentation/screens/friend_profile_screen.dart`
- `mobile/lib/features/community/presentation/screens/accountability_screen.dart`
- `mobile/lib/features/community/presentation/screens/accountability_detail_screen.dart`
- `mobile/lib/features/community/presentation/providers/community_provider.dart`
- `mobile/lib/features/community/data/models/community_model.dart`
- `mobile/lib/features/community/data/models/accountability_model.dart`
- `mobile/lib/features/community/data/repositories/accountability_repository.dart`
- `mobile/lib/features/community/data/repositories/community_repository.dart`
- `mobile/lib/features/community/data/repositories/mock_community_repository.dart`
- `mobile/lib/features/galaxy/presentation/widgets/node_detail_sheet.dart`
- `mobile/lib/features/galaxy/presentation/widgets/galaxy_contribution_banner.dart`
- `mobile/lib/features/galaxy/presentation/widgets/galaxy/graphrag_visualizer.dart`
- `mobile/lib/features/galaxy/presentation/widgets/galaxy/galaxy_node_preview_card.dart`
- `mobile/lib/features/galaxy/presentation/widgets/galaxy/sector_config.dart`
- `mobile/lib/features/galaxy/presentation/widgets/galaxy/galaxy_simulation_settings_sheet.dart`
- `mobile/lib/features/galaxy/presentation/widgets/galaxy/galaxy_error_dialog.dart`
- `mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart`
- `mobile/lib/features/galaxy/presentation/providers/galaxy_provider.dart`
- `mobile/lib/features/galaxy/data/models/user_galaxy_contribution.dart`
- `mobile/lib/features/galaxy/data/services/galaxy_monitoring_integration.dart`
- `mobile/lib/features/galaxy/data/services/galaxy_layout_engine.dart`
- `mobile/lib/features/galaxy/data/services/galaxy_llm_service.dart`
- `mobile/lib/features/galaxy/data/repositories/enhanced_galaxy_repository.dart`
- `mobile/lib/features/galaxy/data/repositories/galaxy_repository.dart`
- `mobile/lib/features/galaxy/domain/entities/galaxy_llm_protocol.dart`

## Agent 3C: Remaining Features (tools, settings, user, notification, etc.)

- All remaining files from:
  - features/tools/
  - features/settings/
  - features/user/
  - features/notification_center/
  - features/photon/
  - features/seed_library/
  - features/translation/
  - features/visual_elements/
  - features/report/
  - features/document/
  - features/simulation/
  - features/error_book/
  - features/theater/
  - features/onboarding/
  - features/aurora/
  - features/memory/
  - features/knowledge/
  - features/mirofish/
