import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

/// Close-to-unlock banner state
class CloseToUnlockState {
  const CloseToUnlockState({
    this.item,
    this.isVisible = false,
  });

  final AchievementWithProgress? item;
  final bool isVisible;

  CloseToUnlockState copyWith({
    AchievementWithProgress? item,
    bool? isVisible,
  }) =>
      CloseToUnlockState(
        item: item ?? this.item,
        isVisible: isVisible ?? this.isVisible,
      );
}

/// Provider for close-to-unlock achievement banner
/// Handles throttling, auto-dismiss, and state management
final closeToUnlockProvider =
    StateNotifierProvider<CloseToUnlockNotifier, CloseToUnlockState>(
  (ref) => CloseToUnlockNotifier(ref),
);

class CloseToUnlockNotifier extends StateNotifier<CloseToUnlockState> {
  CloseToUnlockNotifier(this._ref) : super(const CloseToUnlockState());

  final Ref _ref;
  Timer? _dismissTimer;
  DateTime? _lastCheckTime;

  /// Throttle duration between checks (5 minutes)
  static const _throttleDuration = Duration(minutes: 5);
  /// Banner display duration (4 seconds)
  static const _bannerDisplayDuration = Duration(seconds: 4);

  /// Trigger a check for close-to-unlock achievements
  /// 调用此方法触发接近解锁成就检查
  Future<void> triggerCheck({String? category}) async {
    // Throttle: skip if checked within last 5 minutes
    if (_lastCheckTime != null) {
      final timeSinceLastCheck = DateTime.now().difference(_lastCheckTime!);
      if (timeSinceLastCheck < _throttleDuration) {
        debugPrint('🏆 Close-to-unlock check throttled '
            '(${timeSinceLastCheck.inSeconds}s ago)');
        return;
      }
    }

    _lastCheckTime = DateTime.now();

    try {
      // Get close-to-unlock achievements (80%+ progress)
      final closeAchievements =
          await _ref.read(achievementProvider.notifier).getCloseToUnlockAchievements(
                category: category,
                threshold: 0.8,
              );

      if (closeAchievements.isEmpty) {
        debugPrint('🏆 No close-to-unlock achievements found');
        return;
      }

      // Find the one with highest progress percentage that's not yet unlocked
      AchievementWithProgress? bestMatch;
      int highestProgress = 0;

      for (final item in closeAchievements) {
        // Skip already unlocked achievements
        if (item.isUnlocked) continue;

        if (item.progressPercentage > highestProgress) {
          highestProgress = item.progressPercentage;
          bestMatch = item;
        }
      }

      if (bestMatch == null) {
        debugPrint('🏆 All close achievements are already unlocked');
        return;
      }

      // Show banner with the best match
      debugPrint('🏆 Showing close-to-unlock banner: ${bestMatch.achievement.name} '
          '($highestProgress%)');

      state = CloseToUnlockState(
        item: bestMatch,
        isVisible: true,
      );

      // Auto-dismiss after 4 seconds
      _dismissTimer?.cancel();
      _dismissTimer = Timer(_bannerDisplayDuration, dismiss);
    } catch (e) {
      debugPrint('❌ Error checking close-to-unlock achievements: $e');
    }
  }

  /// Manually dismiss the banner
  /// 手动关闭提示条
  void dismiss() {
    if (state.isVisible) {
      _dismissTimer?.cancel();
      state = const CloseToUnlockState();
    }
  }

  @override
  void dispose() {
    _dismissTimer?.cancel();
    super.dispose();
  }
}
