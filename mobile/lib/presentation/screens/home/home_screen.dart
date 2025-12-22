import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_staggered_grid_view/flutter_staggered_grid_view.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_tokens.dart';
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

/// HomeScreen v2.3 - The Cockpit
///
/// Features:
/// - Deep Space theme with glassmorphism
/// - Bento Grid dashboard layout
/// - Weather header showing inner state
/// - OmniBar replacing BottomNavigationBar
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
    // Dashboard uses special layout with OmniBar
    if (_selectedIndex == 0) {
      return _screens[0];
    }

    return Scaffold(
      body: _screens[_selectedIndex],
      bottomNavigationBar: _buildNavigationBar(),
    );
  }

  Widget _buildNavigationBar() {
    return BottomNavigationBar(
      items: const <BottomNavigationBarItem>[
        BottomNavigationBarItem(
          icon: Icon(Icons.home_outlined),
          activeIcon: Icon(Icons.home),
          label: '首页',
        ),
        BottomNavigationBarItem(
          icon: Icon(Icons.auto_awesome_outlined),
          activeIcon: Icon(Icons.auto_awesome),
          label: '星图',
        ),
        BottomNavigationBarItem(
          icon: Icon(Icons.forum_outlined),
          activeIcon: Icon(Icons.forum),
          label: '对话',
        ),
        BottomNavigationBarItem(
          icon: Icon(Icons.groups_outlined),
          activeIcon: Icon(Icons.groups),
          label: '社群',
        ),
        BottomNavigationBarItem(
          icon: Icon(Icons.person_outlined),
          activeIcon: Icon(Icons.person),
          label: '我的',
        ),
      ],
      currentIndex: _selectedIndex,
      onTap: (index) => setState(() => _selectedIndex = index),
      type: BottomNavigationBarType.fixed,
    );
  }
}

/// Dashboard Screen with v2.3 Bento Grid layout
class _DashboardScreen extends ConsumerWidget {
  const _DashboardScreen();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final dashboardState = ref.watch(dashboardProvider);

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: AppDesignTokens.deepSpaceGradient,
        ),
        child: Stack(
          children: [
            // Background stars effect
            const _StarField(),

            // Main content
            RefreshIndicator(
              onRefresh: () async {
                await ref.read(dashboardProvider.notifier).refresh();
                await ref.read(taskListProvider.notifier).refreshTasks();
                await ref.read(planListProvider.notifier).refresh();
              },
              child: CustomScrollView(
                slivers: [
                  // App bar with user info
                  SliverToBoxAdapter(
                    child: _buildAppBar(context, user),
                  ),

                  // Weather header
                  const SliverToBoxAdapter(
                    child: WeatherHeader(),
                  ),

                  // Bento Grid
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: _buildBentoGrid(context, dashboardState),
                    ),
                  ),

                  // Extra padding for OmniBar
                  const SliverToBoxAdapter(
                    child: SizedBox(height: 100),
                  ),
                ],
              ),
            ),

            // OmniBar at bottom
            const Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: _OmniBarContainer(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAppBar(BuildContext context, dynamic user) {
    return SafeArea(
      bottom: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
        child: Row(
          children: [
            // Avatar
            CircleAvatar(
              radius: 20,
              backgroundImage:
                  user?.avatarUrl != null ? NetworkImage(user!.avatarUrl!) : null,
              backgroundColor: AppDesignTokens.primaryBase,
              child: user?.avatarUrl == null
                  ? Text(
                      (user?.nickname ?? 'U')[0].toUpperCase(),
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                      ),
                    )
                  : null,
            ),
            const SizedBox(width: 12),

            // Greeting
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _getGreeting(user?.nickname ?? '同学'),
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
                Text(
                  '保持好奇，探索未知',
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.white.withAlpha(150),
                  ),
                ),
              ],
            ),

            const Spacer(),

            // Flame level
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: Colors.white.withAlpha(20),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Row(
                children: [
                  const Icon(
                    Icons.local_fire_department_rounded,
                    color: Colors.orange,
                    size: 18,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    'Lv.${user?.flameLevel ?? 1}',
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBentoGrid(BuildContext context, DashboardState state) {
    return StaggeredGrid.count(
      crossAxisCount: 4,
      mainAxisSpacing: 10,
      crossAxisSpacing: 10,
      children: [
        // Focus Card - 2x2 (left column)
        StaggeredGridTile.count(
          crossAxisCellCount: 2,
          mainAxisCellCount: 2,
          child: FocusCard(
            onTap: () {
              context.push('/focus');
            },
          ),
        ),

        // Prism Card - 2x1 (top right)
        StaggeredGridTile.count(
          crossAxisCellCount: 2,
          mainAxisCellCount: 1,
          child: const PrismCard(),
        ),

        // Sprint Card - 2x1 (bottom right)
        StaggeredGridTile.count(
          crossAxisCellCount: 2,
          mainAxisCellCount: 1,
          child: SprintCard(
            onTap: () {
              context.push('/plans');
            },
          ),
        ),

        // Next Actions - 4x1.2 (full width bottom)
        StaggeredGridTile.count(
          crossAxisCellCount: 4,
          mainAxisCellCount: 1.2,
          child: NextActionsCard(
            onViewAll: () {
              context.push('/tasks');
            },
          ),
        ),
      ],
    );
  }

  String _getGreeting(String name) {
    final hour = DateTime.now().hour;
    String greeting;
    if (hour < 6) {
      greeting = '夜深了';
    } else if (hour < 12) {
      greeting = '早安';
    } else if (hour < 14) {
      greeting = '午安';
    } else if (hour < 18) {
      greeting = '下午好';
    } else {
      greeting = '晚上好';
    }
    return '$greeting, $name';
  }
}

/// OmniBar container with navigation items
class _OmniBarContainer extends StatelessWidget {
  const _OmniBarContainer();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Colors.transparent,
            AppDesignTokens.deepSpaceStart.withAlpha(200),
            AppDesignTokens.deepSpaceStart,
          ],
          stops: const [0.0, 0.3, 1.0],
        ),
      ),
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // OmniBar input
            const OmniBar(),
            const SizedBox(height: 8),

            // Navigation icons
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _NavItem(
                  icon: Icons.auto_awesome_outlined,
                  label: '星图',
                  onTap: () => context.push('/galaxy'),
                ),
                _NavItem(
                  icon: Icons.forum_outlined,
                  label: '对话',
                  onTap: () => context.push('/chat'),
                ),
                _NavItem(
                  icon: Icons.groups_outlined,
                  label: '社群',
                  onTap: () => context.push('/community'),
                ),
                _NavItem(
                  icon: Icons.person_outlined,
                  label: '我的',
                  onTap: () => context.push('/profile'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _NavItem({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, color: Colors.white60, size: 22),
          const SizedBox(height: 4),
          Text(
            label,
            style: const TextStyle(
              fontSize: 10,
              color: Colors.white60,
            ),
          ),
        ],
      ),
    );
  }
}

/// Decorative star field background
class _StarField extends StatelessWidget {
  const _StarField();

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      size: MediaQuery.of(context).size,
      painter: _StarPainter(),
    );
  }
}

class _StarPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = Colors.white;

    // Draw random stars
    final stars = [
      Offset(size.width * 0.1, size.height * 0.15),
      Offset(size.width * 0.3, size.height * 0.08),
      Offset(size.width * 0.5, size.height * 0.12),
      Offset(size.width * 0.7, size.height * 0.05),
      Offset(size.width * 0.85, size.height * 0.18),
      Offset(size.width * 0.15, size.height * 0.25),
      Offset(size.width * 0.6, size.height * 0.22),
      Offset(size.width * 0.9, size.height * 0.28),
      Offset(size.width * 0.25, size.height * 0.35),
      Offset(size.width * 0.75, size.height * 0.32),
    ];

    for (var i = 0; i < stars.length; i++) {
      final opacity = 0.3 + (i % 3) * 0.2;
      final radius = 1.0 + (i % 2);
      paint.color = Colors.white.withAlpha((opacity * 255).toInt());
      canvas.drawCircle(stars[i], radius, paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
