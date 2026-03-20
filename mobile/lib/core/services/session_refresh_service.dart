import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/calendar/presentation/providers/calendar_provider.dart';
import 'package:sparkle/features/calendar/presentation/providers/unified_calendar_provider.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';
import 'package:sparkle/features/focus/presentation/providers/focus_statistics_provider.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/notification_provider.dart';
import 'package:sparkle/features/leaderboard/presentation/providers/leaderboard_provider.dart';
import 'package:sparkle/features/notification_center/presentation/providers/notification_center_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';
import 'package:sparkle/features/user/presentation/providers/profile_context_provider.dart';

class SessionRefreshService {
  const SessionRefreshService._();

  static void refreshSessionBoundProviders(Ref ref) {
    DemoDataService().resetDemoState();
    ref
      ..invalidate(dashboardProvider)
      ..invalidate(unreadNotificationsProvider)
      ..invalidate(notificationCenterProvider)
      ..invalidate(taskListProvider)
      ..invalidate(planListProvider)
      ..invalidate(calendarProvider)
      ..invalidate(unifiedCalendarProvider)
      ..invalidate(friendsProvider)
      ..invalidate(pendingRequestsProvider)
      ..invalidate(friendRecommendationsProvider)
      ..invalidate(groupRecommendationsProvider)
      ..invalidate(myGroupsProvider)
      ..invalidate(achievementProvider)
      ..invalidate(streakHistoryProvider)
      ..invalidate(leaderboardProvider)
      ..invalidate(myRankProvider)
      ..invalidate(focusStatisticsProvider)
      ..invalidate(profileContextProvider)
      ..invalidate(transparentProfileProvider)
      ..invalidate(inferredPreferencesProvider)
      ..invalidate(activePoliciesProvider)
      ..invalidate(systemUpdatesProvider);
  }
}
