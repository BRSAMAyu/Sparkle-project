import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/achievement/presentation/providers/home_close_to_unlock_provider.dart';
import 'package:sparkle/features/achievement/presentation/widgets/achievement_progress_banner.dart';
import 'package:sparkle/features/achievement/presentation/widgets/achievement_share_bottom_sheet.dart';
import 'package:sparkle/features/achievement/presentation/widgets/achievement_unlock_dialog.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart'
    as chat;
import 'package:sparkle/features/chat/data/services/message_notification_service.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/providers/visual_element_provider.dart';

/// Main navigation shell for StatefulShellRoute
///
/// This widget wraps the tab navigation system with:
/// - InAppNotificationOverlay for in-app notifications
/// - ResponsiveScaffold for adaptive layout (bottom nav on mobile, side rail on tablet, drawer on desktop)
/// - Tab switching using StatefulNavigationShell.goBranch()
class MainNavigationShell extends ConsumerStatefulWidget {
  const MainNavigationShell({
    required this.navigationShell,
    super.key,
  });

  /// The StatefulNavigationShell from StatefulShellRoute
  final StatefulNavigationShell navigationShell;

  @override
  ConsumerState<MainNavigationShell> createState() =>
      _MainNavigationShellState();
}

class _MainNavigationShellState extends ConsumerState<MainNavigationShell> {
  bool _isShowingAchievementDialog = false;
  bool _visualRefreshScheduled = false;
  StreamSubscription<dynamic>? _communityEventsSub;

  void _handleDestinationSelected(int index) {
    if (index == widget.navigationShell.currentIndex) {
      return;
    }
    unawaited(
      SensoryFeedbackService.emit(
        SensoryFeedbackEvent.selection,
        enableSound: false,
      ),
    );
    widget.navigationShell.goBranch(index);
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _setupAchievementListener();
    });
  }

  void _setupAchievementListener() {
    _scheduleVisualElementWarmRefresh();
    _subscribeToCommunityEvents(ref.read(communityEventsStreamProvider));
    ref
      ..listenManual<Stream<dynamic>>(
        communityEventsStreamProvider,
        (previous, next) {
          _subscribeToCommunityEvents(next);
        },
      )
      ..listenManual(
        pendingAchievementUnlockProvider,
        (previous, next) {
          if (next != null &&
              next != previous &&
              mounted &&
              !_isShowingAchievementDialog) {
            unawaited(_showAchievementDialog(next.event, next.comboCount));
          }
        },
      );
  }

  void _scheduleVisualElementWarmRefresh() {
    if (_visualRefreshScheduled) {
      return;
    }
    _visualRefreshScheduled = true;
    Future<void>.delayed(const Duration(milliseconds: 1200), () async {
      if (!mounted) {
        return;
      }
      final state = ref.read(visualElementProvider);
      if (state.isLoading ||
          state.allElements.isNotEmpty ||
          state.unlockedElements.isNotEmpty) {
        return;
      }
      await ref.read(visualElementProvider.notifier).refresh();
    });
  }

  void _subscribeToCommunityEvents(Stream<dynamic> stream) {
    unawaited(_communityEventsSub?.cancel());
    _communityEventsSub = stream.listen(
      _handleCommunityEvent,
      onError: (Object error, StackTrace stackTrace) {
        debugPrint('MainNavigationShell community stream error: $error');
        debugPrintStack(stackTrace: stackTrace);
      },
    );
  }

  void _handleCommunityEvent(dynamic event) {
    Map<String, dynamic>? payload;
    if (event is String && event.isNotEmpty) {
      try {
        final decoded = json.decode(event);
        if (decoded is Map<String, dynamic>) {
          payload = decoded;
        }
      } catch (error, stackTrace) {
        debugPrint(
          'MainNavigationShell failed to decode community event: $error',
        );
        debugPrintStack(stackTrace: stackTrace);
      }
    } else if (event is Map<String, dynamic>) {
      payload = event;
    } else if (event is Map) {
      payload = Map<String, dynamic>.from(event);
    }

    if (payload == null) {
      return;
    }

    final type = payload['type'] as String?;
    if (type != 'achievement_unlock') {
      return;
    }

    final achievementData = payload['achievement_data'];
    Map<String, dynamic>? achievementMap;
    if (achievementData is Map<String, dynamic>) {
      achievementMap = achievementData;
    } else if (achievementData is Map) {
      achievementMap = Map<String, dynamic>.from(achievementData);
    }
    if (achievementMap == null) {
      return;
    }

    final wsEvent =
        chat.AchievementUnlockEvent(achievementData: achievementMap);
    final result =
        ref.read(achievementProvider.notifier).handleAchievementUnlock(wsEvent);
    if (result == null) {
      return;
    }

    ref.read(pendingAchievementUnlockProvider.notifier).setPending(
          event: result.event,
          comboCount: result.comboCount,
        );
    unawaited(ref.read(achievementProvider.notifier).refreshAchievements());
    unawaited(ref.read(achievementProvider.notifier).refreshStats());
    unawaited(ref.read(achievementProvider.notifier).refreshStreakStats());
    unawaited(
      ref.read(homeCloseToUnlockProvider.notifier).fetch(forceRefresh: true),
    );
    unawaited(ref.read(streakHistoryProvider.notifier).loadHistory());
  }

  Future<void> _showAchievementDialog(
    chat.AchievementUnlockEvent event,
    int? comboCount,
  ) async {
    if (_isShowingAchievementDialog) return;
    _isShowingAchievementDialog = true;
    try {
      await AchievementUnlockDialog.showFromWsEvent(
        context,
        event,
        comboCount: comboCount,
        onShare: () {
          unawaited(
            showAchievementShareSheet(
              context,
              achievementId: event.achievementId,
              achievementName: event.name,
            ),
          );
        },
        onViewRewards: () {
          unawaited(context.push('/achievements/${event.achievementId}'));
        },
      );
    } finally {
      if (mounted) {
        _isShowingAchievementDialog = false;
        ref.read(pendingAchievementUnlockProvider.notifier).clear();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final unreadCount = ref.watch(unreadMessageCountProvider);

    final destinations = [
      NavigationDestination(
        icon: const Icon(Icons.home_outlined),
        selectedIcon: const Icon(Icons.home),
        label: l10n.home,
      ),
      NavigationDestination(
        icon: const Icon(Icons.auto_awesome_outlined),
        selectedIcon: const Icon(Icons.auto_awesome),
        label: l10n.galaxy,
      ),
      NavigationDestination(
        icon: const Icon(Icons.forum_outlined),
        selectedIcon: const Icon(Icons.forum),
        label: l10n.chat,
      ),
      NavigationDestination(
        icon: _buildBadgedIcon(Icons.groups_outlined, unreadCount),
        selectedIcon: _buildBadgedIcon(Icons.groups, unreadCount),
        label: l10n.community,
      ),
      NavigationDestination(
        icon: const Icon(Icons.person_outlined),
        selectedIcon: const Icon(Icons.person),
        label: l10n.profile,
      ),
    ];

    return Stack(
      children: [
        InAppNotificationOverlay(
          child: ResponsiveScaffold(
            title: 'Sparkle',
            body: _ShellBranchTransition(
              currentIndex: widget.navigationShell.currentIndex,
              child: widget.navigationShell,
            ),
            destinations: destinations,
            currentIndex: widget.navigationShell.currentIndex,
            onDestinationSelected: _handleDestinationSelected,
          ),
        ),
        // Phase 1B: Close-to-unlock progress banner
        const AchievementProgressBanner(),
      ],
    );
  }

  /// Builds a navigation icon with an unread count badge
  Widget _buildBadgedIcon(IconData icon, int count) {
    if (count == 0) return Icon(icon);
    return Semantics(
      label: '$count unread notifications',
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Icon(icon),
          Positioned(
            right: -8,
            top: -4,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
              decoration: BoxDecoration(
                color: DS.semanticError,
                borderRadius: BorderRadius.circular(8),
              ),
              constraints: const BoxConstraints(minWidth: 16, minHeight: 16),
              child: Text(
                count > 9 ? '9+' : '$count',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                  fontFeatures: [FontFeature.tabularFigures()],
                ),
                textAlign: TextAlign.center,
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    unawaited(_communityEventsSub?.cancel());
    super.dispose();
  }
}

class _ShellBranchTransition extends StatelessWidget {
  const _ShellBranchTransition({
    required this.currentIndex,
    required this.child,
  });

  final int currentIndex;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    if (context.reduceMotion) {
      return child;
    }

    final entersChat = currentIndex == 2;
    return TweenAnimationBuilder<double>(
      key: ValueKey<int>(currentIndex),
      tween: Tween<double>(begin: 0, end: 1),
      duration: const Duration(milliseconds: 240),
      curve: Curves.easeOutCubic,
      child: child,
      builder: (context, value, child) {
        final scale = MediaQuery.of(context).devicePixelRatio;
        final slide =
            (1 - value) * (entersChat ? 12 : -10) / scale.clamp(1.0, 4.0);
        return Opacity(
          opacity: value,
          child: Transform.translate(
            offset: Offset(slide, 0),
            child: child,
          ),
        );
      },
    );
  }
}
