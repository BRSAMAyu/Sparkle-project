import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/providers/auth_provider.dart';
import 'package:sparkle/presentation/providers/plan_provider.dart';
import 'package:sparkle/presentation/providers/task_provider.dart';
import 'package:sparkle/presentation/providers/capsule_provider.dart';
import 'package:sparkle/presentation/screens/chat/chat_screen.dart';
import 'package:sparkle/presentation/screens/plan/growth_screen.dart';
import 'package:sparkle/presentation/screens/task/task_list_screen.dart';
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
    TaskListScreen(),
    ChatScreen(),
    GrowthScreen(),
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
          BottomNavigationBarItem(icon: Icon(Icons.home_outlined), activeIcon: Icon(Icons.home), label: 'Home'),
          BottomNavigationBarItem(icon: Icon(Icons.task_alt_outlined), activeIcon: Icon(Icons.task_alt), label: 'Tasks'),
          BottomNavigationBarItem(icon: Icon(Icons.forum_outlined), activeIcon: Icon(Icons.forum), label: 'Chat'),
          BottomNavigationBarItem(icon: Icon(Icons.explore_outlined), activeIcon: Icon(Icons.explore), label: 'Plans'),
          BottomNavigationBarItem(icon: Icon(Icons.person_outlined), activeIcon: Icon(Icons.person), label: 'Me'),
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

    final bool isLoading = taskListState.isLoading || planListState.isLoading;
    final String? errorMessage = taskListState.error ?? planListState.error;

    return Scaffold(
      floatingActionButton: CustomButton.icon(
        icon: Icons.add_rounded,
        onPressed: () {
           // TODO: Navigate to add task
           context.push('/tasks/new'); 
        },
        size: ButtonSize.large,
        isCircular: true,
      ),
      body: isLoading
          ? Center(child: LoadingIndicator.circular(showText: true, loadingText: '加载中...'))
          : errorMessage != null
              ? CustomErrorWidget.page(
                  message: errorMessage,
                  onRetry: () {
                    ref.read(taskListProvider.notifier).refreshTasks();
                    ref.read(planListProvider.notifier).refresh();
                  },
                )
              : RefreshIndicator(
                  onRefresh: () async {
                    await ref.read(taskListProvider.notifier).refreshTasks();
                    await ref.read(planListProvider.notifier).refresh();
                    await ref.read(capsuleProvider.notifier).fetchTodayCapsules();
                  },
                  child: CustomScrollView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    slivers: [
                      // 渐变AppBar with greeting
                      _buildGradientAppBar(context, user),
                      // Content
                      SliverPadding(
                        padding: const EdgeInsets.all(AppDesignTokens.spacing16),
                        sliver: SliverList(
                          delegate: SliverChildListDelegate([
                            const _FlameStatusCard(),
                            const SizedBox(height: AppDesignTokens.spacing24),
                            const _CuriosityCapsuleSection(),
                            const SizedBox(height: AppDesignTokens.spacing24),
                            const _TodayTasksSection(),
                            const SizedBox(height: AppDesignTokens.spacing24),
                            const _RecommendedTasksSection(),
                            const SizedBox(height: AppDesignTokens.spacing32),
                          ]),
                        ),
                      ),
                    ],
                  ),
                ),
    );
  }

  Widget _buildGradientAppBar(BuildContext context, dynamic user) {
    return Consumer(
      builder: (context, ref, child) {
        final hour = DateTime.now().hour;
        String greeting;
        if (hour < 12) {
          greeting = '早上好';
        } else if (hour < 18) {
          greeting = '下午好';
        } else {
          greeting = '晚上好';
        }

        final unreadCountAsync = ref.watch(unreadNotificationsProvider);
        final unreadCount = unreadCountAsync.value?.length ?? 0;

        return SliverAppBar(
          expandedHeight: 120.0,
          floating: false,
          pinned: true,
          flexibleSpace: FlexibleSpaceBar(
            background: Container(
              decoration: const BoxDecoration(
                gradient: AppDesignTokens.primaryGradient,
              ),
              child: SafeArea(
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppDesignTokens.spacing20,
                    vertical: AppDesignTokens.spacing16,
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisAlignment: MainAxisAlignment.end,
                        children: [
                          Text(
                            greeting,
                            style: const TextStyle(
                              fontSize: AppDesignTokens.fontSizeLg,
                              color: Colors.white70,
                              fontWeight: AppDesignTokens.fontWeightMedium,
                            ),
                          ),
                          const SizedBox(height: AppDesignTokens.spacing4),
                          Text(
                            user?.nickname ?? user?.username ?? '学习者',
                            style: const TextStyle(
                              fontSize: AppDesignTokens.fontSize3xl,
                              color: Colors.white,
                              fontWeight: AppDesignTokens.fontWeightBold,
                            ),
                          ),
                        ],
                      ),
                       IconButton(
                        onPressed: () {
                           Navigator.of(context).push(MaterialPageRoute(builder: (_) => const NotificationListScreen()));
                        },
                        icon: Badge(
                          isLabelVisible: unreadCount > 0,
                          label: Text('$unreadCount'),
                          child: const Icon(Icons.notifications_none_rounded, color: Colors.white, size: 28),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        );
      },
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
