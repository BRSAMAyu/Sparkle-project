import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/visual_elements/domain/services/visual_recommendation_service.dart';
import 'package:sparkle/features/visual_elements/presentation/providers/visual_elements_provider.dart';

final visualRecommendationServiceProvider =
    Provider<VisualRecommendationService>((ref) => VisualRecommendationService());

/// Derive current user activity state from dashboard + streak signals.
final userActivityStateProvider = Provider<UserActivityState>((ref) {
  final dashboard = ref.watch(dashboardProvider);
  final achievement = ref.watch(achievementProvider);
  final now = TimeOfDay.now();
  final isNight = now.hour >= 21 || now.hour < 6;

  if (dashboard.isLoading) {
    return isNight ? UserActivityState.night : UserActivityState.relax;
  }

  if (dashboard.sprint != null) return UserActivityState.sprint;
  if (achievement.streakStats.currentStreak >= 3) {
    return UserActivityState.streak;
  }
  if (isNight) return UserActivityState.night;
  if (dashboard.flame.todayFocusMinutes >= 60) {
    return UserActivityState.focus;
  }
  return UserActivityState.relax;
});

final visualRecommendationProvider =
    FutureProvider<List<VisualRecommendation>>((ref) async {
  final service = ref.watch(visualRecommendationServiceProvider);
  final state = ref.watch(visualElementsNotifierProvider);
  final activityState = ref.watch(userActivityStateProvider);

  if (state.isLoading) return [];

  final availableElements = state.unlockedElements.isNotEmpty
      ? state.unlockedElements
      : state.allElements;

  return service.getRecommendations(
    state: activityState,
    timeOfDay: TimeOfDay.now(),
    availableElements: availableElements,
  );
});
