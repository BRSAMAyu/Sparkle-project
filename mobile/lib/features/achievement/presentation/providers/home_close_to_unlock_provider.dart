import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

/// State for the home screen achievement progress card.
/// Holds a list (up to 3) of closest-to-unlock achievements.
class HomeCloseToUnlockState {
  const HomeCloseToUnlockState({
    this.items = const [],
    this.isLoading = false,
  });

  final List<AchievementWithProgress> items;
  final bool isLoading;

  HomeCloseToUnlockState copyWith({
    List<AchievementWithProgress>? items,
    bool? isLoading,
  }) =>
      HomeCloseToUnlockState(
        items: items ?? this.items,
        isLoading: isLoading ?? this.isLoading,
      );
}

final homeCloseToUnlockProvider = StateNotifierProvider<
    HomeCloseToUnlockNotifier, HomeCloseToUnlockState>(
  (ref) => HomeCloseToUnlockNotifier(ref),
);

class HomeCloseToUnlockNotifier
    extends StateNotifier<HomeCloseToUnlockState> {
  HomeCloseToUnlockNotifier(this._ref) : super(const HomeCloseToUnlockState());

  final Ref _ref;
  DateTime? _lastFetchTime;

  static const _cacheDuration = Duration(minutes: 5);
  static const _maxItems = 3;

  /// Fetch close-to-unlock achievements for the home card.
  /// Skips if data was fetched within the last 5 minutes.
  Future<void> fetch({bool forceRefresh = false}) async {
    if (!forceRefresh && _lastFetchTime != null) {
      final elapsed = DateTime.now().difference(_lastFetchTime!);
      if (elapsed < _cacheDuration) {
        debugPrint('🏆 HomeCloseToUnlock: using cached data');
        return;
      }
    }

    state = state.copyWith(isLoading: true);
    try {
      final all = await _ref
          .read(achievementProvider.notifier)
          .getCloseToUnlockAchievements();

      // Sort by progress descending, take top 3 non-unlocked items
      final sorted = all
          .where((a) => !a.isUnlocked)
          .toList()
        ..sort((a, b) =>
            b.progressPercentage.compareTo(a.progressPercentage),);

      _lastFetchTime = DateTime.now();
      state = state.copyWith(
        items: sorted.take(_maxItems).toList(),
        isLoading: false,
      );
    } catch (e) {
      debugPrint('❌ HomeCloseToUnlock fetch error: $e');
      state = state.copyWith(isLoading: false);
    }
  }
}
