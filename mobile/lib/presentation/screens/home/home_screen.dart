import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/providers/auth_provider.dart';
import 'package:sparkle/presentation/providers/plan_provider.dart';
import 'package:sparkle/presentation/providers/task_provider.dart';
import 'package:sparkle/presentation/providers/capsule_provider.dart';
import 'package:sparkle/presentation/screens/chat/chat_screen.dart';
import 'package:sparkle/presentation/screens/galaxy/galaxy_screen.dart';
import 'package:sparkle/presentation/screens/community/community_screen.dart';
import 'package:sparkle/presentation/screens/profile/profile_screen.dart';
import 'package:sparkle/presentation/widgets/common/custom_button.dart';
import 'package:sparkle/presentation/widgets/task/task_card.dart';
import 'package:sparkle/presentation/widgets/common/flame_indicator.dart';
import 'package:sparkle/presentation/widgets/common/empty_state.dart';
import 'package:sparkle/presentation/widgets/common/loading_indicator.dart';
import 'package:sparkle/presentation/widgets/common/error_widget.dart';
import 'package:sparkle/presentation/providers/notification_provider.dart';
import 'package:sparkle/presentation/screens/home/notification_list_screen.dart';
import 'package:sparkle/presentation/widgets/home/curiosity_capsule_card.dart';
import 'package:go_router/go_router.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _selectedIndex = 0;

  static const List<Widget> _widgetOptions = <Widget>[
    _DashboardTab(),
    GalaxyScreen(),
    ChatScreen(),
    CommunityScreen(),
    ProfileScreen(),
  ];

  void _onItemTapped(int index) {
    setState(() {
      _selectedIndex = index;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: _widgetOptions.elementAt(_selectedIndex),
      ),
      bottomNavigationBar: BottomNavigationBar(
        items: const <BottomNavigationBarItem>[
          BottomNavigationBarItem(icon: Icon(Icons.home_outlined), activeIcon: Icon(Icons.home), label: '首页'),
          BottomNavigationBarItem(icon: Icon(Icons.auto_awesome_outlined), activeIcon: Icon(Icons.auto_awesome), label: '星图'),
          BottomNavigationBarItem(icon: Icon(Icons.forum_outlined), activeIcon: Icon(Icons.forum), label: '对话'),
          BottomNavigationBarItem(icon: Icon(Icons.groups_outlined), activeIcon: Icon(Icons.groups), label: '社群'),
          BottomNavigationBarItem(icon: Icon(Icons.person_outlined), activeIcon: Icon(Icons.person), label: '我的'),
        ],
        currentIndex: _selectedIndex,
        onTap: _onItemTapped,
        type: BottomNavigationBarType.fixed,
      ),
    );
  }
}

class _DashboardTab extends ConsumerWidget {
  const _DashboardTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final taskListState = ref.watch(taskListProvider);
    final planListState = ref.watch(planListProvider);

    return Scaffold(
      backgroundColor: AppDesignTokens.neutral50,
      body: RefreshIndicator(
        onRefresh: () async {
          await ref.read(taskListProvider.notifier).refreshTasks();
          await ref.read(planListProvider.notifier).refresh();
          await ref.read(capsuleProvider.notifier).fetchTodayCapsules();
        },
        child: CustomScrollView(
          slivers: [
            _buildModernAppBar(context, user),
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  children: [
                    _buildStatsRow(),
                    const SizedBox(height: 20),
                    _buildQuickActions(context),
                    const SizedBox(height: 20),
                    const _TodayTasksSection(),
                    const SizedBox(height: 20),
                    const _RecommendedTasksSection(),
                    const SizedBox(height: 80), // Bottom padding
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => context.push('/tasks/new'),
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildModernAppBar(BuildContext context, dynamic user) {
    return SliverAppBar(
      expandedHeight: 180.0,
      floating: false,
      pinned: true,
      backgroundColor: Colors.transparent,
      flexibleSpace: FlexibleSpaceBar(
        background: Container(
          decoration: const BoxDecoration(
            gradient: AppDesignTokens.primaryGradient,
            borderRadius: BorderRadius.only(
              bottomLeft: Radius.circular(30),
              bottomRight: Radius.circular(30),
            ),
          ),
          child: SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(20.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '早安, ${user?.nickname ?? "同学"}',
                            style: const TextStyle(
                              fontSize: 24,
                              fontWeight: FontWeight.bold,
                              color: Colors.white,
                            ),
                          ),
                          const Text(
                            '今天也要保持好奇心哦',
                            style: TextStyle(
                              color: Colors.white70,
                              fontSize: 14,
                            ),
                          ),
                        ],
                      ),
                      CircleAvatar(
                        radius: 24,
                        backgroundImage: user?.avatarUrl != null ? NetworkImage(user!.avatarUrl!) : null,
                        child: user?.avatarUrl == null ? const Icon(Icons.person) : null,
                      ),
                    ],
                  ),
                  const Spacer(),
                  // Flame / Level Info
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: Colors.white30),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.local_fire_department, color: Colors.orangeAccent, size: 28),
                        const SizedBox(width: 12),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '学习火焰 Lv.${user?.flameLevel ?? 1}',
                              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                            ),
                            Text(
                              '亮度 ${(user?.flameBrightness ?? 0.5) * 100}%',
                              style: const TextStyle(color: Colors.white70, fontSize: 12),
                            ),
                          ],
                        ),
                        const Spacer(),
                        const Icon(Icons.chevron_right, color: Colors.white54),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildStatsRow() {
    return Row(
      children: [
        _buildStatCard('专注时长', '3.5h', Icons.timer, Colors.blue),
        const SizedBox(width: 12),
        _buildStatCard('完成任务', '5', Icons.check_circle, Colors.green),
        const SizedBox(width: 12),
        _buildStatCard('连续打卡', '12天', Icons.calendar_today, Colors.orange),
      ],
    );
  }

  Widget _buildStatCard(String label, String value, IconData icon, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          boxShadow: AppDesignTokens.shadowSm,
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 24),
            const SizedBox(height: 8),
            Text(
              value,
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: AppDesignTokens.neutral900,
              ),
            ),
            Text(
              label,
              style: const TextStyle(
                fontSize: 12,
                color: AppDesignTokens.neutral500,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildQuickActions(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceAround,
      children: [
        _buildActionBtn(context, Icons.add_task, '新建任务', () => context.push('/tasks/new')),
        _buildActionBtn(context, Icons.qr_code_scanner, '扫题', () {}),
        _buildActionBtn(context, Icons.auto_awesome_motion, '生成计划', () {}),
        _buildActionBtn(context, Icons.history_edu, '错题本', () {}),
      ],
    );
  }

  Widget _buildActionBtn(BuildContext context, IconData icon, String label, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.white,
              shape: BoxShape.circle,
              boxShadow: AppDesignTokens.shadowSm,
            ),
            child: Icon(icon, color: AppDesignTokens.primaryBase),
          ),
          const SizedBox(height: 8),
          Text(label, style: const TextStyle(fontSize: 12, color: AppDesignTokens.neutral700)),
        ],
      ),
    );
  }
}

class _CuriosityCapsuleSection extends ConsumerWidget {
  const _CuriosityCapsuleSection();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final capsuleState = ref.watch(capsuleProvider);

    return capsuleState.when(
      data: (capsules) {
        if (capsules.isEmpty) return const SizedBox.shrink();
        return Column(
          children: [
            ...capsules.map((capsule) => CuriosityCapsuleCard(capsule: capsule)),
          ],
        );
      },
      loading: () => const SizedBox.shrink(),
      error: (_, __) => const SizedBox.shrink(),
    );
  }
}

class _FlameStatusCard extends ConsumerWidget {
  const _FlameStatusCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final flameLevel = user?.flameLevel ?? 0;
    final flameBrightness = ((user?.flameBrightness ?? 0) * 100).toInt();

    return GestureDetector(
      onTap: () {
        // TODO: Navigate to detailed statistics
      },
      child: Container(
        padding: const EdgeInsets.all(AppDesignTokens.spacing20),
        decoration: BoxDecoration(
          gradient: AppDesignTokens.cardGradientPrimary,
          borderRadius: AppDesignTokens.borderRadius20,
          boxShadow: AppDesignTokens.shadowPrimary,
        ),
        child: Row(
          children: [
            // Flame Indicator
            FlameIndicator(
              level: flameLevel,
              brightness: flameBrightness,
              size: 100.0,
              showLabel: false,
            ),
            const SizedBox(width: AppDesignTokens.spacing20),
            // Info Section
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    '学习火焰',
                    style: TextStyle(
                      fontSize: AppDesignTokens.fontSizeSm,
                      color: Colors.white70,
                      fontWeight: AppDesignTokens.fontWeightMedium,
                    ),
                  ),
                  const SizedBox(height: AppDesignTokens.spacing4),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text(
                        'Lv.$flameLevel',
                        style: const TextStyle(
                          fontSize: AppDesignTokens.fontSize3xl,
                          color: Colors.white,
                          fontWeight: AppDesignTokens.fontWeightBold,
                        ),
                      ),
                      const SizedBox(width: AppDesignTokens.spacing8),
                      Padding(
                        padding: const EdgeInsets.only(bottom: 4.0),
                        child: Text(
                          '亮度 $flameBrightness%',
                          style: const TextStyle(
                            fontSize: AppDesignTokens.fontSizeBase,
                            color: Colors.white70,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppDesignTokens.spacing12),
                  const Row(
                    children: [
                      Icon(
                        Icons.trending_up_rounded,
                        size: AppDesignTokens.iconSizeSm,
                        color: Colors.white70,
                      ),
                      SizedBox(width: AppDesignTokens.spacing4),
                      Text(
                        '持续学习中',
                        style: TextStyle(
                          fontSize: AppDesignTokens.fontSizeSm,
                          color: Colors.white70,
                        ),
                      ),
                      Spacer(),
                      Icon(
                        Icons.arrow_forward_ios_rounded,
                        size: AppDesignTokens.iconSizeSm,
                        color: Colors.white54,
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TodayTasksSection extends ConsumerWidget {
  const _TodayTasksSection();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final todayTasks = ref.watch(taskListProvider).todayTasks;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              '今日任务',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: AppDesignTokens.fontWeightBold,
              ),
            ),
            if (todayTasks.isNotEmpty)
              CustomButton.text(
                text: '查看全部',
                onPressed: () {
                  // Navigate to task list
                },
                size: ButtonSize.small,
              ),
          ],
        ),
        const SizedBox(height: AppDesignTokens.spacing12),
        if (todayTasks.isEmpty)
          CompactEmptyState(
            message: '今天没有任务，可以休息或规划新任务',
            icon: Icons.check_circle_outline_rounded,
            actionText: '创建任务',
            onAction: () {
              // TODO: Navigate to add task screen
            },
          )
        else
          SizedBox(
            height: 160,
            child: ListView.builder(
              scrollDirection: Axis.horizontal,
              itemCount: todayTasks.length,
              padding: const EdgeInsets.symmetric(horizontal: 4),
              itemBuilder: (context, index) {
                final task = todayTasks[index];
                return SizedBox(
                  width: 320,
                  child: TaskCard(
                    task: task,
                    onTap: () {
                      // TODO: Navigate to task detail
                      context.push('/tasks/${task.id}');
                    },
                    onStart: () {
                      // TODO: Start task execution
                    },
                    onComplete: () async {
                      await ref.read(taskListProvider.notifier).completeTask(
                        task.id,
                        task.estimatedMinutes,
                        null,
                      );
                    },
                  ),
                );
              },
            ),
          ),
      ],
    );
  }
}

class _RecommendedTasksSection extends ConsumerWidget {
  const _RecommendedTasksSection();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final recommendedTasks = ref.watch(taskListProvider).recommendedTasks;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              '为你推荐',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: AppDesignTokens.fontWeightBold,
              ),
            ),
            if (recommendedTasks.isNotEmpty)
              CustomButton.text(
                text: '更多推荐',
                onPressed: () {
                  // Navigate to recommendations
                },
                size: ButtonSize.small,
              ),
          ],
        ),
        const SizedBox(height: AppDesignTokens.spacing12),
        if (recommendedTasks.isEmpty)
          CompactEmptyState(
            message: '暂无推荐任务，探索更多学习计划',
            icon: Icons.lightbulb_outline_rounded,
            actionText: '浏览计划',
            onAction: () {
              // TODO: Navigate to plans screen
            },
          )
        else
          ListView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: recommendedTasks.length > 3 ? 3 : recommendedTasks.length,
            itemBuilder: (context, index) {
              final task = recommendedTasks[index];
              return Padding(
                padding: const EdgeInsets.only(bottom: AppDesignTokens.spacing8),
                child: TaskCard(
                  task: task,
                  compact: true,
                  onTap: () {
                    context.push('/tasks/${task.id}');
                  },
                  onStart: () {
                    // TODO: Start task execution
                  },
                  onComplete: () async {
                    await ref.read(taskListProvider.notifier).completeTask(
                      task.id,
                      task.estimatedMinutes,
                      null,
                    );
                  },
                ),
              );
            },
          ),
      ],
    );
  }
}
