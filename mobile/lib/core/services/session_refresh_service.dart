import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/aurora/presentation/providers/aurora_preferences_provider.dart';
import 'package:sparkle/features/calendar/presentation/providers/calendar_provider.dart';
import 'package:sparkle/features/calendar/presentation/providers/unified_calendar_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
// chat_provider_wiring.dart is a `part of chat_provider.dart` — no separate import needed
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';
import 'package:sparkle/features/focus/presentation/providers/focus_statistics_provider.dart';
import 'package:sparkle/features/galaxy/data/repositories/enhanced_galaxy_repository.dart';
import 'package:sparkle/features/galaxy/data/repositories/galaxy_repository.dart';
import 'package:sparkle/features/galaxy/presentation/providers/galaxy_provider.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/notification_provider.dart';
import 'package:sparkle/features/leaderboard/presentation/providers/leaderboard_provider.dart';
import 'package:sparkle/features/notification_center/presentation/providers/notification_center_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/active_plan_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';
import 'package:sparkle/features/user/presentation/providers/profile_context_provider.dart';

final sessionBoundProvidersProvider = Provider<List<ProviderOrFamily>>(
  (ref) => [
    dashboardProvider,
    unreadNotificationsProvider,
    notificationCenterProvider,
    chatProvider,
    chatRepositoryProvider,
    auroraStatusProvider,
    auroraPreferencesProvider,
    taskListProvider,
    planListProvider,
    activePlanProvider,
    calendarProvider,
    unifiedCalendarProvider,
    friendsProvider,
    pendingRequestsProvider,
    friendRecommendationsProvider,
    groupRecommendationsProvider,
    myGroupsProvider,
    achievementProvider,
    streakHistoryProvider,
    leaderboardProvider,
    myRankProvider,
    focusStatisticsProvider,
    galaxyProvider,
    enhancedGalaxyRepositoryProvider,
    galaxyRepositoryProvider,
    profileContextProvider,
    transparentProfileProvider,
    inferredPreferencesProvider,
    activePoliciesProvider,
    systemUpdatesProvider,
  ],
);

class SessionRefreshService {
  const SessionRefreshService._();

  static Future<void> refreshSessionBoundProviders(Ref ref) async {
    DemoDataService().resetDemoState();
    for (final provider in ref.read(sessionBoundProvidersProvider)) {
      if (provider is ProviderBase<Object?> && ref.exists(provider)) {
        ref.invalidate(provider);
      }
    }
    // R5-P1-22: Ensure WebSocket reconnects after provider invalidation
    await _ensureWebSocketReconnect(ref);
  }

  static Future<void> _ensureWebSocketReconnect(Ref ref) async {
    // After session-bound providers are invalidated (e.g., logout/login),
    // trigger WebSocket reconnection by reinitializing the chatProvider.
    // The next sendMessage will establish a fresh connection.
    try {
      ref.read(chatProvider.notifier).warmUpConnection();
    } catch (_) {
      // Silently handle — next sendMessage will reconnect naturally
    }
  }
}
