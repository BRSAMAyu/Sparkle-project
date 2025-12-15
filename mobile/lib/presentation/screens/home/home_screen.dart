import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/providers/auth_provider.dart';
import 'package:sparkle/presentation/providers/plan_provider.dart';
import 'package:sparkle/presentation/providers/task_provider.dart';
import 'package:sparkle/presentation/screens/chat/chat_screen.dart';
import 'package:sparkle/presentation/screens/plan/growth_screen.dart';
import 'package:sparkle/presentation/screens/task/task_list_screen.dart';
import 'package:sparkle/presentation/widgets/empty_state.dart';
import 'package:sparkle/presentation/widgets/error_widget.dart';
import 'package:sparkle/presentation/widgets/flame_indicator.dart';
import 'package:sparkle/presentation/widgets/loading_indicator.dart';
// import 'package:sparkle/presentation/widgets/task/task_card.dart'; // Assuming available

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
    GrowthScreen(), // Using GrowthScreen as a placeholder for a combined plan screen
    Text('Profile Screen Placeholder'), // Placeholder
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
      appBar: AppBar(
        title: Text('Welcome, ${user?.nickname ?? user?.username ?? ''}'),
      ),
      body: isLoading
          ? const LoadingIndicator(isLoading: true)
          : errorMessage != null
              ? AppErrorWidget(
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
                  },
                  child: SingleChildScrollView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.all(AppDesignTokens.spacing16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _FlameStatusCard(),
                        SizedBox(height: AppDesignTokens.spacing16),
                        _TodayTasksSection(),
                        SizedBox(height: AppDesignTokens.spacing16),
                        _RecommendedTasksSection(),
                      ],
                    ),
                  ),
                ),
    );
  }
}

class _FlameStatusCard extends ConsumerWidget {
  const _FlameStatusCard();
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    return Card(
      margin: EdgeInsets.zero, // Remove default card margin
      shape: RoundedRectangleBorder(
        borderRadius: AppDesignTokens.borderRadius12,
      ),
      elevation: 0, // Handled by AppThemeExtension shadows
      child: Container(
        padding: const EdgeInsets.all(AppDesignTokens.spacing16),
        decoration: BoxDecoration(
          color: Theme.of(context).cardColor,
          borderRadius: AppDesignTokens.borderRadius12,
          boxShadow: Theme.of(context).appExtension?.cardShadow,
        ),
        child: Row(
          children: [
            FlameIndicator(currentLevel: user?.flameLevel ?? 0),
            const SizedBox(width: AppDesignTokens.spacing16),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Flame Level', style: Theme.of(context).textTheme.titleMedium),
                Text('${user?.flameLevel ?? 0}', style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                  color: AppDesignTokens.primaryBase,
                )),
                Text('Brightness: ${(user?.flameBrightness ?? 0) * 100}%', style: Theme.of(context).textTheme.bodyMedium),
              ],
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
        Text('Today\'s Tasks', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: AppDesignTokens.spacing8),
        if (todayTasks.isEmpty)
          EmptyState(
            message: 'No tasks for today. Time to relax or plan something new!',
            icon: Icons.check_circle_outline,
            title: 'All Done!',
            actionButtonText: 'Add New Task',
            onActionPressed: () {
              // TODO: Navigate to add task screen
            },
          )
        else
          SizedBox(
            height: 150, // Card height, adjust as needed
            child: ListView.builder(
              scrollDirection: Axis.horizontal,
              itemCount: todayTasks.length,
              itemBuilder: (context, index) {
                final task = todayTasks[index];
                return SizedBox(
                  width: 300, // Card width
                  child: ListTile(title: Text(task.title)), // Placeholder for TaskCard
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
        Text('Recommended For You', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: AppDesignTokens.spacing8),
        if (recommendedTasks.isEmpty)
          EmptyState(
            message: 'Explore new opportunities or continue your journey.',
            icon: Icons.lightbulb_outline,
            title: 'No Recommendations Yet',
            actionButtonText: 'Explore Plans',
            onActionPressed: () {
              // TODO: Navigate to plans screen
            },
          )
        else
          ListView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: recommendedTasks.length,
            itemBuilder: (context, index) {
              final task = recommendedTasks[index];
              return ListTile(title: Text(task.title)); // Placeholder for TaskCard
            },
          ),
      ],
    );
  }
}
