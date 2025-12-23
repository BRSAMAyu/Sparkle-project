import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_staggered_grid_view/flutter_staggered_grid_view.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/core/utils/responsive_utils.dart';
import 'package:sparkle/presentation/providers/auth_provider.dart';
import 'package:sparkle/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/presentation/providers/task_provider.dart';
import 'package:sparkle/presentation/providers/plan_provider.dart';
import 'package:sparkle/presentation/screens/chat/chat_screen.dart';
import 'package:sparkle/presentation/screens/galaxy_screen.dart';
import 'package:sparkle/presentation/screens/community/community_screen.dart';
import 'package:sparkle/presentation/screens/profile/profile_screen.dart';
import 'package:sparkle/presentation/widgets/home/weather_header.dart';
import 'package:sparkle/presentation/widgets/home/focus_card.dart';
import 'package:sparkle/presentation/widgets/home/prism_card.dart';
import 'package:sparkle/presentation/widgets/home/sprint_card.dart';
import 'package:sparkle/presentation/widgets/home/next_actions_card.dart';
import 'package:sparkle/presentation/widgets/home/omnibar.dart';

/// HomeScreen v2.0 - Project Cockpit
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
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
    if (_selectedIndex == 0) return _screens[0];

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: _screens[_selectedIndex],
      bottomNavigationBar: _buildNavigationBar(),
    );
  }

  Widget _buildNavigationBar() {
    return BottomNavigationBar(
      items: const <BottomNavigationBarItem>[
        BottomNavigationBarItem(icon: Icon(Icons.home_outlined), activeIcon: Icon(Icons.home), label: '驾驶舱'),
        BottomNavigationBarItem(icon: Icon(Icons.auto_awesome_outlined), activeIcon: Icon(Icons.auto_awesome), label: '星图'),
        BottomNavigationBarItem(icon: Icon(Icons.forum_outlined), activeIcon: Icon(Icons.forum), label: '对话'),
        BottomNavigationBarItem(icon: Icon(Icons.groups_outlined), activeIcon: Icon(Icons.groups), label: '社群'),
        BottomNavigationBarItem(icon: Icon(Icons.person_outlined), activeIcon: Icon(Icons.person), label: '我的'),
      ],
      currentIndex: _selectedIndex,
      onTap: (index) => setState(() => _selectedIndex = index),
      type: BottomNavigationBarType.fixed,
      backgroundColor: const Color(0xFF0D1B2A),
      unselectedItemColor: Colors.white54,
      selectedItemColor: AppDesignTokens.primaryBase,
    );
  }
}

class _DashboardScreen extends ConsumerWidget {
  const _DashboardScreen();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final dashboardState = ref.watch(dashboardProvider);

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
                  SliverToBoxAdapter(child: _buildTopOverlay(context, user)),
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
            bottom: MediaQuery.of(context).padding.bottom + 16,
            child: const OmniBar(),
          ),
        ],
      ),
    );
  }

  Widget _buildTopOverlay(BuildContext context, dynamic user) {
    return Padding(
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
                style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.orangeAccent),
              ),
              Text(
                user?.nickname ?? '探索者',
                style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.white),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildBentoGrid(BuildContext context, DashboardState state) {
    return StaggeredGrid.count(
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
        // Card C: Next Actions (1x2)
        StaggeredGridTile.count(
          crossAxisCellCount: 1,
          mainAxisCellCount: 2,
          child: NextActionsCard(onViewAll: () => context.push('/tasks')),
        ),
      ],
    );
  }
}
