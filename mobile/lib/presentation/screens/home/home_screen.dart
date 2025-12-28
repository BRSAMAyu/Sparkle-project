import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_staggered_grid_view/flutter_staggered_grid_view.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/core/design/responsive_layout.dart';
import 'package:sparkle/core/services/message_notification_service.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/presentation/providers/auth_provider.dart';
import 'package:sparkle/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/presentation/providers/task_provider.dart';
import 'package:sparkle/presentation/screens/chat/chat_screen.dart';
import 'package:sparkle/presentation/screens/community/community_screen.dart';
import 'package:sparkle/presentation/screens/galaxy_screen.dart';
import 'package:sparkle/presentation/screens/profile/profile_screen.dart';
import 'package:sparkle/presentation/widgets/home/calendar_heatmap_card.dart';
import 'package:sparkle/presentation/widgets/home/dashboard_curiosity_card.dart';
import 'package:sparkle/presentation/widgets/home/focus_card.dart';
import 'package:sparkle/presentation/widgets/home/home_notification_card.dart';
import 'package:sparkle/presentation/widgets/home/long_term_plan_card.dart';
import 'package:sparkle/presentation/widgets/home/next_actions_card.dart';
import 'package:sparkle/presentation/widgets/home/omnibar.dart';
import 'package:sparkle/presentation/widgets/home/prism_card.dart';
import 'package:sparkle/presentation/widgets/home/sprint_card.dart';
import 'package:sparkle/presentation/widgets/home/weather_header.dart';

/// HomeScreen v2.0 - Project Cockpit
class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  int _selectedIndex = 0;

  List<Widget> get _screens => [
        const _DashboardScreen(),
        const GalaxyScreen(),
        const ChatScreen(),
        const CommunityScreen(),
        const ProfileScreen(),
      ];

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final unreadCount = ref.watch(unreadMessageCountProvider);

    final destinations = [
      NavigationDestination(
        icon: Icon(Icons.home_outlined),
        selectedIcon: Icon(Icons.home),
        label: l10n.home,
      ),
      NavigationDestination(
        icon: Icon(Icons.auto_awesome_outlined),
        selectedIcon: Icon(Icons.auto_awesome),
        label: l10n.galaxy,
      ),
      NavigationDestination(
        icon: Icon(Icons.forum_outlined),
        selectedIcon: Icon(Icons.forum),
        label: l10n.chat,
      ),
      NavigationDestination(
        icon: _buildBadgedIcon(Icons.groups_outlined, unreadCount),
        selectedIcon: _buildBadgedIcon(Icons.groups, unreadCount),
        label: l10n.community,
      ),
      NavigationDestination(
        icon: Icon(Icons.person_outlined),
        selectedIcon: Icon(Icons.person),
        label: l10n.profile,
      ),
    ];

    return InAppNotificationOverlay(
      child: ResponsiveScaffold(
        title: 'Sparkle',
        body: _screens[_selectedIndex],
        destinations: destinations,
        currentIndex: _selectedIndex,
        onDestinationSelected: (index) => setState(() => _selectedIndex = index),
      ),
    );
  }

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
              color: AppDesignTokens.error,
              borderRadius: BorderRadius.circular(8),
            ),
            constraints: const BoxConstraints(minWidth: 16, minHeight: 16),
            child: Text(
              count > 99 ? '99+' : '$count',
              style: TextStyle(color: DS.brandPrimaryConst, fontSize: 10, fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
          ),
        ),
      ],
    );
  }
}

class _DashboardScreen extends ConsumerWidget {
  const _DashboardScreen();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final dashboardState = ref.watch(dashboardProvider);
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      extendBody: true,
      backgroundColor: Colors.transparent,
      body: Stack(
        children: [
          // Layer 1: Weather Background
          const Positioned.fill(child: WeatherHeader()),

          // Layer 2: Dashboard Content
          SafeArea(
            bottom: false,
            child: RefreshIndicator(
              onRefresh: () async {
                await ref.read(dashboardProvider.notifier).refresh();
                await ref.read(taskListProvider.notifier).refreshTasks();
              },
              child: CustomScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                slivers: [
                  // Top Overlay
                  SliverToBoxAdapter(child: _buildTopOverlay(context, user, l10n)),
                  
                  // Message Notification Widget
                  const SliverToBoxAdapter(child: HomeNotificationCard()),
                  
                  const SliverToBoxAdapter(child: SizedBox(height: 10)),
                  
                  // Bento Grid
                  SliverPadding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    sliver: SliverToBoxAdapter(
                      child: _buildBentoGrid(context, dashboardState),
                    ),
                  ),
                  
                  const SliverToBoxAdapter(child: SizedBox(height: 120)),
                ],
              ),
            ),
          ),

          // Layer 3: Omni-Bar
          Positioned(
            left: 16,
            right: 16,
            bottom: 16, // Adjusted for ResponsiveScaffold which puts this inside body
            child: OmniBar(hintText: l10n.typeMessage),
          ),
        ],
      ),
    );
  }

  Widget _buildTopOverlay(BuildContext context, dynamic user, AppLocalizations l10n) => Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
      child: Row(
        children: [
          CircleAvatar(
            radius: 18,
            backgroundImage: user?.avatarUrl != null ? NetworkImage(user!.avatarUrl!) : null,
            backgroundColor: AppDesignTokens.primaryBase,
            child: user?.avatarUrl == null ? Text((user?.nickname ?? 'U')[0].toUpperCase()) : null,
          ),
          const SizedBox(width: 10),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Lv.${user?.flameLevel ?? 1}',
                style: TextStyle(
                  fontSize: AppDesignTokens.fontSizeXs,
                  fontWeight: AppDesignTokens.fontWeightBold,
                  color: AppDesignTokens.warning,
                ),
              ),
              Text(
                user?.nickname ?? (user?.username ?? l10n.exploreGalaxy),
                style: TextStyle(
                  fontSize: AppDesignTokens.fontSizeSm,
                  fontWeight: AppDesignTokens.fontWeightBold,
                  color: DS.brandPrimaryConst,
                ),
              ),
            ],
          ),
        ],
      ),
    );

  Widget _buildBentoGrid(BuildContext context, DashboardState state) {
    // Wrap with ContentConstraint for responsive width on desktop
    return ContentConstraint(
      child: StaggeredGrid.count(
        crossAxisCount: 4,
        mainAxisSpacing: 12,
        crossAxisSpacing: 12,
        children: [
          // Card A: Focus Core (2x2)
          StaggeredGridTile.count(
            crossAxisCellCount: 2,
            mainAxisCellCount: 2,
            child: FocusCard(onTap: () => context.push('/focus')),
          ),
          // Card E: Calendar Heatmap (2x1)
          const StaggeredGridTile.count(
            crossAxisCellCount: 2,
            mainAxisCellCount: 1,
            child: CalendarHeatmapCard(),
          ),
          // Card B: Cognitive Prism (2x1)
          const StaggeredGridTile.count(
            crossAxisCellCount: 2,
            mainAxisCellCount: 1,
            child: PrismCard(),
          ),
          // Card D: Sprint Ring (1x1)
          StaggeredGridTile.count(
            crossAxisCellCount: 1,
            mainAxisCellCount: 1,
            child: SprintCard(onTap: () => context.push('/plans')),
          ),
          // Card C: Next Actions (1x1) - Resized
          StaggeredGridTile.count(
            crossAxisCellCount: 1,
            mainAxisCellCount: 1,
            child: NextActionsCard(onViewAll: () => context.push('/tasks')),
          ),
          // Card F: Curiosity Capsule (1x1)
          const StaggeredGridTile.count(
            crossAxisCellCount: 1,
            mainAxisCellCount: 1,
            child: DashboardCuriosityCard(),
          ),
          // Card G: Long Term Plan (1x1) - Bottom Right
          const StaggeredGridTile.count(
            crossAxisCellCount: 1,
            mainAxisCellCount: 1,
            child: LongTermPlanCard(),
          ),
        ],
      ),
    );
  }
}
