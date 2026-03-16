import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/achievement/presentation/providers/close_to_unlock_provider.dart';
import 'package:sparkle/features/achievement/presentation/widgets/achievement_progress_banner.dart';
import 'package:sparkle/features/achievement/presentation/widgets/achievement_unlock_dialog.dart';
import 'package:sparkle/features/chat/data/services/message_notification_service.dart';
import 'package:sparkle/l10n/app_localizations.dart';

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

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _setupAchievementListener();
    });
  }

  void _setupAchievementListener() {
    ref.listenManual(
      pendingAchievementUnlockProvider,
      (previous, next) {
        if (next != null &&
            next != previous &&
            mounted &&
            !_isShowingAchievementDialog) {
          _showAchievementDialog(next.event, next.comboCount);
        }
      },
    );
  }

  Future<void> _showAchievementDialog(
    dynamic event,
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
          // TODO: share
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
            body: widget.navigationShell,
            destinations: destinations,
            currentIndex: widget.navigationShell.currentIndex,
            onDestinationSelected: widget.navigationShell.goBranch,
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
    return Stack(
      clipBehavior: Clip.none,
      children: [
        Icon(icon),
        Positioned(
          right: -8,
          top: -4,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
            decoration: BoxDecoration(
              color: DS.error,
              borderRadius: BorderRadius.circular(8),
            ),
            constraints: const BoxConstraints(minWidth: 16, minHeight: 16),
            child: Text(
              count > 99 ? '99+' : '$count',
              style: TextStyle(
                color: DS.brandPrimaryConst,
                fontSize: 10,
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
            ),
          ),
        ),
      ],
    );
  }
}
