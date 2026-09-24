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
import 'package:sparkle/features/community/presentation/providers/focus_mode_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/providers/visual_element_provider.dart';

/// Signal incremented when the active tab is re-tapped, triggering
/// [TapToTopListener] to scroll the tab's primary scroll view to top.
final scrollToTopSignalProvider = StateProvider<int>((ref) => 0);

///社群分支在 StatefulShellRoute.branches 中的下标（badge 进入即清用）。
const int _communityBranchIndex = 3;

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
  final ScrollController _shellScrollController = ScrollController();

  void _handleDestinationSelected(int index) {
    if (index == widget.navigationShell.currentIndex) {
      // Scroll current tab content to top
      if (_shellScrollController.hasClients) {
        _shellScrollController.animateTo(
          0,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeInOut,
        );
      }
      return;
    }
    if (index == _communityBranchIndex) {
      // IR-G2/N24：点 tab 进入社群 = badge「进入即清」主路径。
      ref.read(unreadMessageCountProvider.notifier).reset();
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
      // N24（IR-G2）：冷启动/深链直接落在社群分支时，badge「进入即清」。
      _clearCommunityUnreadBadgeIfEntered();
    });
  }

  @override
  void didUpdateWidget(MainNavigationShell oldWidget) {
    super.didUpdateWidget(oldWidget);
    // N24：路由驱动进入社群分支（如 home 横幅 go('/community')、深链切换）
    // 与 tab 点击（_handleDestinationSelected）同一清除语义。
    _clearCommunityUnreadBadgeIfEntered();
  }

  /// IR-G2/N24 badge 生命周期「清除时机」：进入社群 tab 即清。
  ///
  /// 角标是召回钩子不是资产（对标 Linear「打开即清」/ iOS「进 app 即清」）：
  /// 用户到达 /community 分支后钩子已 discharged，聚合计数归零；
  /// 群聊会话内逐条已读另由 GroupChatNotifier._markVisibleMessagesAsRead
  /// 走 decrementBy 精确抵消。三声明全文钉在
  /// unreadMessageCountProvider 定义处（message_notification_service.dart）。
  void _clearCommunityUnreadBadgeIfEntered() {
    if (widget.navigationShell.currentIndex != _communityBranchIndex) {
      return;
    }
    ref.read(unreadMessageCountProvider.notifier).reset();
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
              // N22 庆典单通道·专注豁免：focusMode 对庆典类打断拥有
              // 一票否决权（与消息横幅 message_notification_service
              // 的豁免同制）；挂起的庆典在专注结束时补放（见下方监听）。
              !ref.read(focusModeProvider) &&
              !_isShowingAchievementDialog) {
            unawaited(_showAchievementDialog(next.event, next.comboCount));
          }
        },
      )
      // N22：专注结束时补放专注期间挂起的成就庆典（pending 仍在）。
      ..listenManual(
        focusModeProvider,
        (previous, next) {
          if ((previous ?? false) &&
              next == false &&
              mounted &&
              !_isShowingAchievementDialog) {
            final pending = ref.read(pendingAchievementUnlockProvider);
            if (pending != null) {
              unawaited(
                _showAchievementDialog(pending.event, pending.comboCount),
              );
            }
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

    final badgeOverflowLabel = l10n.badgeOverflow;
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
        icon: _buildBadgedIcon(
            Icons.groups_outlined, unreadCount, badgeOverflowLabel,),
        selectedIcon:
            _buildBadgedIcon(Icons.groups, unreadCount, badgeOverflowLabel),
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
            title: l10n.appTitle,
            body: PrimaryScrollController(
              controller: _shellScrollController,
              // N20（A-SPEC4）：tab 切换零转场是唯一语法——原
              // _ShellBranchTransition（240ms opacity+slide，chat 另有
              // 方向特判）已删；tab 感知「重」的 IR-G9 同源问题由
              // chat 分支改 NoTransitionPage 一并收口。
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
  Widget _buildBadgedIcon(IconData icon, int count, String badgeOverflowLabel) {
    if (count == 0) return Icon(icon);
    return Semantics(
      label: AppLocalizations.of(context)!.unreadNotifications(count),
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
                count > 9 ? badgeOverflowLabel : '$count',
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
    _shellScrollController.dispose();
    super.dispose();
  }
}
