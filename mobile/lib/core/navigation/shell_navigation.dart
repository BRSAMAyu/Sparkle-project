import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/data/services/message_notification_service.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// Main navigation shell for StatefulShellRoute
///
/// This widget wraps the tab navigation system with:
/// - InAppNotificationOverlay for in-app notifications
/// - ResponsiveScaffold for adaptive layout (bottom nav on mobile, side rail on tablet, drawer on desktop)
/// - Tab switching using StatefulNavigationShell.goBranch()
class MainNavigationShell extends ConsumerWidget {
  const MainNavigationShell({
    required this.navigationShell,
    super.key,
  });

  /// The StatefulNavigationShell from StatefulShellRoute
  final StatefulNavigationShell navigationShell;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
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

    return InAppNotificationOverlay(
      child: ResponsiveScaffold(
        title: 'Sparkle',
        body: navigationShell,
        destinations: destinations,
        currentIndex: navigationShell.currentIndex,
        onDestinationSelected: navigationShell.goBranch,
      ),
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
