import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/plan_model.dart';
import 'package:sparkle/presentation/providers/auth_provider.dart';
import 'package:sparkle/presentation/providers/plan_provider.dart';
import 'package:sparkle/presentation/providers/task_provider.dart';
import 'package:sparkle/presentation/providers/capsule_provider.dart';
import 'package:sparkle/presentation/screens/chat/chat_screen.dart';
import 'package:sparkle/presentation/screens/galaxy_screen.dart';
import 'package:sparkle/presentation/screens/community/community_screen.dart';
import 'package:sparkle/presentation/screens/profile/profile_screen.dart';
import 'package:sparkle/presentation/widgets/common/custom_button.dart';
import 'package:sparkle/presentation/widgets/task/task_card.dart';

import 'package:sparkle/presentation/widgets/common/empty_state.dart';
import 'package:sparkle/presentation/widgets/home/curiosity_capsule_card.dart';
import 'package:go_router/go_router.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _selectedIndex = 0;
  bool _isSprintMode = false;

  List<Widget> get _widgetOptions => <Widget>[
    _DashboardTab(
      isSprintMode: _isSprintMode,
      onSprintModeChanged: (value) => setState(() => _isSprintMode = value),
      onNavigateToChat: () => setState(() => _selectedIndex = 2),
    ),
    const GalaxyScreen(),
    const ChatScreen(),
    const CommunityScreen(),
    const ProfileScreen(),
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
  final bool isSprintMode;
  final ValueChanged<bool> onSprintModeChanged;
  final VoidCallback onNavigateToChat;

  const _DashboardTab({
    required this.isSprintMode,
    required this.onSprintModeChanged,
    required this.onNavigateToChat,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: isDark ? AppDesignTokens.neutral900 : AppDesignTokens.neutral50,
      body: RefreshIndicator(
        onRefresh: () async {
          await ref.read(taskListProvider.notifier).refreshTasks();
          await ref.read(planListProvider.notifier).refresh();
          await ref.read(capsuleProvider.notifier).fetchTodayCapsules();
        },
        child: CustomScrollView(
          slivers: [
            _buildModernAppBar(context, user, isDark),
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  children: [
                    // 1. Sprint Mode Switch (Prominent)
                    _buildSprintModeCard(context, isDark),
                    const SizedBox(height: 20),

                    // 2. Main Chat/AI Interaction Window (Replaces small task icons)
                    _buildMainChatEntry(context, isDark),
                    const SizedBox(height: 24),

                    // 3. Stats (Optional, keep for context but make subtle)
                    _buildStatsRow(isDark),
                    const SizedBox(height: 24),

                    // Curiosity Capsules (Only in Growth Mode)
                    if (!isSprintMode) ...[
                      const _CuriosityCapsuleSection(),
                      const SizedBox(height: 24),
                    ],

                    // 4. Active Plans
                    _ActivePlanSection(isSprintMode: isSprintMode),
                    const SizedBox(height: 24),
                    
                    // 5. Today's Tasks
                    const _TodayTasksSection(),

                    const SizedBox(height: 80), 
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSprintModeCard(BuildContext context, bool isDark) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: isSprintMode
            ? const LinearGradient(
                colors: [Color(0xFFFF416C), Color(0xFFFF4B2B)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              )
            : null,
        color: isSprintMode ? null : (isDark ? AppDesignTokens.neutral800 : Colors.white),
        borderRadius: AppDesignTokens.borderRadius20,
        boxShadow: isSprintMode
            ? [
                BoxShadow(
                  color: const Color(0xFFFF416C).withOpacity(0.4),
                  blurRadius: 20,
                  offset: const Offset(0, 8),
                ),
              ]
            : AppDesignTokens.shadowSm,
        border: isSprintMode ? null : Border.all(color: isDark ? AppDesignTokens.neutral700 : AppDesignTokens.neutral200),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(isSprintMode ? 0.2 : 0.0),
              shape: BoxShape.circle,
              border: Border.all(color: isSprintMode ? Colors.white30 : AppDesignTokens.neutral200),
            ),
            child: Icon(
              Icons.flash_on_rounded,
              color: isSprintMode ? Colors.white : AppDesignTokens.neutral400,
              size: 28,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '冲刺模式',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: isSprintMode ? Colors.white : (isDark ? Colors.white : AppDesignTokens.neutral900),
                  ),
                ),
                Text(
                  isSprintMode ? '高强度备考中 · 屏蔽干扰' : '点击开启沉浸式学习',
                  style: TextStyle(
                    fontSize: 13,
                    color: isSprintMode ? Colors.white70 : (isDark ? Colors.white54 : AppDesignTokens.neutral500),
                  ),
                ),
              ],
            ),
          ),
          Switch(
            value: isSprintMode,
            onChanged: onSprintModeChanged,
            activeColor: Colors.white,
            activeTrackColor: Colors.white.withOpacity(0.3),
            inactiveThumbColor: AppDesignTokens.neutral400,
            inactiveTrackColor: AppDesignTokens.neutral200,
          ),
        ],
      ),
    );
  }

  Widget _buildMainChatEntry(BuildContext context, bool isDark) {
    return GestureDetector(
      onTap: onNavigateToChat,
      child: Container(
        height: 180,
        width: double.infinity,
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            colors: [Color(0xFF6366F1), Color(0xFF4F46E5)], // Indigo/Purple theme for AI
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: AppDesignTokens.borderRadius24,
          boxShadow: [
            BoxShadow(
              color: const Color(0xFF4F46E5).withOpacity(0.3),
              blurRadius: 20,
              offset: const Offset(0, 10),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(Icons.auto_awesome, color: Colors.white, size: 24),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: Colors.black.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: const Text(
                    'AI 导师在线',
                    style: TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
            const Spacer(),
            const Text(
              '今天想学点什么？',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: Colors.white,
              ),
            ),
            const SizedBox(height: 8),
            const Row(
              children: [
                Text(
                  '点击开始对话 · 扫题 · 错题分析 · 制定计划',
                  style: TextStyle(
                    fontSize: 13,
                    color: Colors.white70,
                  ),
                ),
                Spacer(),
                Icon(Icons.arrow_forward_rounded, color: Colors.white70, size: 20),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildModernAppBar(BuildContext context, dynamic user, bool isDark) {
    return SliverAppBar(
      expandedHeight: 120.0, // Reduced height
      floating: false,
      pinned: true,
      backgroundColor: Colors.transparent,
      flexibleSpace: FlexibleSpaceBar(
        background: Container(
          color: isDark ? AppDesignTokens.neutral900 : AppDesignTokens.neutral50, // Match background
          child: SafeArea(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 10.0),
              child: Row(
                children: [
                   CircleAvatar(
                    radius: 20,
                    backgroundImage: user?.avatarUrl != null ? NetworkImage(user!.avatarUrl!) : null,
                    backgroundColor: AppDesignTokens.primaryBase,
                    child: user?.avatarUrl == null
                        ? Text(
                            (user?.nickname ?? 'U')[0].toUpperCase(),
                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                          )
                        : null,
                  ),
                  const SizedBox(width: 12),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        '早安, ${user?.nickname ?? "同学"}',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: isDark ? Colors.white : AppDesignTokens.neutral900,
                        ),
                      ),
                      Text(
                        '保持好奇，探索未知',
                        style: TextStyle(
                          fontSize: 12,
                          color: isDark ? Colors.white54 : AppDesignTokens.neutral500,
                        ),
                      ),
                    ],
                  ),
                  const Spacer(),
                  // Flame Icon (Simple)
                  Icon(Icons.local_fire_department_rounded, color: Colors.orange, size: 24),
                  Text(
                    ' Lv.${user?.flameLevel ?? 1}',
                    style: TextStyle(
                      fontWeight: FontWeight.bold, 
                      color: isDark ? Colors.white : AppDesignTokens.neutral900
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

  Widget _buildStatsRow(bool isDark) {
    return Row(
      children: [
        _buildStatCard('专注时长', '3.5h', Icons.timer, Colors.blue, isDark),
        const SizedBox(width: 12),
        _buildStatCard('掌握知识', '12', Icons.hub_outlined, Colors.purple, isDark), // Changed to Knowledge count
        const SizedBox(width: 12),
        _buildStatCard('连续打卡', '12天', Icons.calendar_today, Colors.orange, isDark),
      ],
    );
  }

  Widget _buildStatCard(String label, String value, IconData icon, Color color, bool isDark) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
          color: isDark ? AppDesignTokens.neutral800 : Colors.white,
          borderRadius: BorderRadius.circular(14),
          boxShadow: isDark ? null : AppDesignTokens.shadowSm,
          border: isDark ? Border.all(color: AppDesignTokens.neutral700) : null,
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 22),
            const SizedBox(height: 6),
            Text(
              value,
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: isDark ? Colors.white : AppDesignTokens.neutral900,
              ),
            ),
            Text(
              label,
              style: TextStyle(
                fontSize: 11,
                color: isDark ? Colors.white54 : AppDesignTokens.neutral500,
              ),
            ),
          ],
        ),
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



class _ActivePlanSection extends ConsumerWidget {
  final bool isSprintMode;

  const _ActivePlanSection({required this.isSprintMode});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final planState = ref.watch(planListProvider);
    final activePlans = planState.activePlans;
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    // In Sprint Mode, we prioritize Sprint Plans
    final displayPlans = isSprintMode
        ? activePlans.where((p) => p.type == PlanType.sprint).toList()
        : activePlans;

    if (displayPlans.isEmpty) {
      if (isSprintMode) {
        return Container(
          width: double.infinity,
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: isDark ? AppDesignTokens.neutral800 : const Color(0xFFFFF0F0),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: Colors.red.shade100),
          ),
          child: Column(
            children: [
              Icon(Icons.timer_off_outlined, color: Colors.red.shade400, size: 32),
              const SizedBox(height: 12),
              Text(
                "暂无冲刺计划",
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: isDark ? Colors.white : AppDesignTokens.neutral900,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                "告诉 AI 你的考试时间，立即生成冲刺计划",
                style: TextStyle(
                  fontSize: 12,
                  color: isDark ? Colors.white54 : AppDesignTokens.neutral500,
                ),
              ),
            ],
          ),
        );
      }
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              isSprintMode ? '冲刺进度' : '长期计划',
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: AppDesignTokens.fontWeightBold,
                color: isDark ? Colors.white : AppDesignTokens.neutral900,
              ),
            ),
            if (activePlans.isNotEmpty)
              CustomButton.text(
                text: '全部计划',
                onPressed: () {
                   // Navigate to plans
                },
                size: ButtonSize.small,
              ),
          ],
        ),
        const SizedBox(height: 12),
        ...displayPlans.map((plan) => _buildPlanCard(context, plan, isDark)),
      ],
    );
  }

  Widget _buildPlanCard(BuildContext context, PlanModel plan, bool isDark) {
    final daysLeft = plan.targetDate != null
        ? plan.targetDate!.difference(DateTime.now()).inDays
        : null;
    
    final isSprint = plan.type == PlanType.sprint;

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: isDark ? AppDesignTokens.neutral800 : Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: isDark ? null : AppDesignTokens.shadowSm,
        border: Border.all(
          color: isSprint 
              ? (isDark ? Colors.red.shade900 : Colors.red.shade100) 
              : (isDark ? AppDesignTokens.neutral700 : AppDesignTokens.neutral200),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: isSprint ? Colors.red.withOpacity(0.1) : Colors.blue.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(
                  isSprint ? Icons.flash_on_rounded : Icons.flag_rounded,
                  color: isSprint ? Colors.red : Colors.blue,
                  size: 20,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      plan.name,
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: isDark ? Colors.white : AppDesignTokens.neutral900,
                      ),
                    ),
                    if (daysLeft != null)
                      Text(
                        daysLeft > 0 ? '距离目标还有 $daysLeft 天' : '今日截止',
                        style: TextStyle(
                          fontSize: 12,
                          color: daysLeft <= 3 ? Colors.red : (isDark ? Colors.white54 : AppDesignTokens.neutral500),
                          fontWeight: daysLeft <= 3 ? FontWeight.bold : FontWeight.normal,
                        ),
                      ),
                  ],
                ),
              ),
              CircularProgressIndicator(
                value: plan.progress,
                backgroundColor: isDark ? AppDesignTokens.neutral700 : AppDesignTokens.neutral100,
                valueColor: AlwaysStoppedAnimation<Color>(isSprint ? Colors.red : Colors.blue),
                strokeWidth: 6,
              ),
            ],
          ),
          const SizedBox(height: 16),
          // Progress Bar
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: plan.progress,
              backgroundColor: isDark ? AppDesignTokens.neutral700 : AppDesignTokens.neutral100,
              valueColor: AlwaysStoppedAnimation<Color>(isSprint ? Colors.red : Colors.blue),
              minHeight: 8,
            ),
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '进度 ${(plan.progress * 100).toInt()}%',
                style: TextStyle(
                  fontSize: 12,
                  color: isDark ? Colors.white54 : AppDesignTokens.neutral500,
                ),
              ),
              Text(
                '每日 ${plan.dailyAvailableMinutes} min',
                style: TextStyle(
                  fontSize: 12,
                  color: isDark ? Colors.white54 : AppDesignTokens.neutral500,
                ),
              ),
            ],
          ),
        ],
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


