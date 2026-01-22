import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/rpg/data/models/task_models.dart';
import 'package:sparkle/features/rpg/presentation/providers/task_providers.dart';

/// 任务列表页面
class TaskListScreen extends ConsumerWidget {
  const TaskListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final taskSystem = ref.watch(taskSystemProvider);

    return DefaultTabController(
      length: 4,
      child: Scaffold(
        backgroundColor: DS.neutral50,
        appBar: AppBar(
          title: const Text('任务中心'),
          backgroundColor: DS.brandPrimary,
          foregroundColor: Colors.white,
          bottom: TabBar(
            tabs: const [
              Tab(text: '每日任务'),
              Tab(text: '成就'),
              Tab(text: '连续登录'),
              Tab(text: '活动'),
            ],
            labelColor: Colors.white,
            unselectedLabelColor: Colors.white70,
            indicatorColor: Colors.white,
          ),
        ),
        body: TabBarView(
          children: [
            // 每日任务
            _TaskList(
              tasks: taskSystem.dailyTasks,
              onClaimReward: (taskId) => ref.read(taskSystemProvider.notifier).claimTaskReward(taskId),
            ),
            
            // 成就任务
            _TaskList(
              tasks: taskSystem.achievementTasks,
              onClaimReward: (taskId) => ref.read(taskSystemProvider.notifier).claimTaskReward(taskId),
            ),
            
            // 连续登录任务
            _TaskList(
              tasks: taskSystem.loginStreakTasks,
              onClaimReward: (taskId) => ref.read(taskSystemProvider.notifier).claimTaskReward(taskId),
            ),
            
            // 活动任务
            _TaskList(
              tasks: taskSystem.activityTasks,
              onClaimReward: (taskId) => ref.read(taskSystemProvider.notifier).claimTaskReward(taskId),
            ),
          ],
        ),
      ),
    );
  }
}

/// 任务列表组件
class _TaskList extends StatelessWidget {
  const _TaskList({
    required this.tasks,
    required this.onClaimReward,
  });

  final List<Task> tasks;
  final Function(String) onClaimReward;

  @override
  Widget build(BuildContext context) {
    if (tasks.isEmpty) {
      return const Center(
        child: Text('暂无任务'),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(DS.spacing16),
      itemCount: tasks.length,
      itemBuilder: (context, index) {
        final task = tasks[index];
        return Padding(
          padding: const EdgeInsets.only(bottom: DS.spacing16),
          child: _TaskCard(
            task: task,
            onClaimReward: () => onClaimReward(task.id),
          ),
        );
      },
    );
  }
}

/// 任务卡片组件
class _TaskCard extends StatelessWidget {
  const _TaskCard({
    required this.task,
    required this.onClaimReward,
  });

  final Task task;
  final VoidCallback onClaimReward;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: DS.borderRadius16,
        boxShadow: DS.shadowSm,
        border: Border.all(
          color: _getStatusColor(task.status),
          width: 2,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 任务标题和状态
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                task.title,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: DS.textPrimary,
                      fontWeight: DS.fontWeightBold,
                    ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: DS.spacing8, vertical: DS.spacing4),
                decoration: BoxDecoration(
                  color: _getStatusColor(task.status),
                  borderRadius: DS.borderRadius8,
                ),
                child: Text(
                  _getStatusName(task.status),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          
          const SizedBox(height: DS.spacing8),
          
          // 任务描述
          Text(
            task.description,
            style: TextStyle(
              color: DS.textSecondary,
              fontSize: 14,
            ),
          ),
          
          const SizedBox(height: DS.spacing16),
          
          // 任务进度
          if (task.type != TaskType.achievement || task.target > 1) ...[
            LinearProgressIndicator(
              value: task.progress / task.target,
              backgroundColor: DS.neutral300,
              color: _getStatusColor(task.status),
              minHeight: 8,
            ),
            
            const SizedBox(height: DS.spacing8),
            
            Text(
              '${task.progress}/${task.target}',
              style: TextStyle(
                color: DS.textSecondary,
                fontSize: 12,
              ),
              textAlign: TextAlign.right,
            ),
            
            const SizedBox(height: DS.spacing16),
          ],
          
          // 任务奖励
          const Text(
            '奖励:',
            style: TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 14,
            ),
          ),
          
          const SizedBox(height: DS.spacing8),
          
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: task.rewards.map((reward) {
              return Container(
                padding: const EdgeInsets.symmetric(horizontal: DS.spacing12, vertical: DS.spacing4),
                decoration: BoxDecoration(
                  color: DS.surfacePrimary,
                  borderRadius: DS.borderRadius8,
                  border: Border.all(
                    color: DS.neutral300,
                    width: 1,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      _getRewardIcon(reward.type),
                      size: 16,
                      color: DS.primaryBase,
                    ),
                    const SizedBox(width: DS.spacing4),
                    Text(
                      _getRewardText(reward),
                      style: TextStyle(
                        color: DS.textPrimary,
                        fontSize: 14,
                      ),
                    ),
                  ],
                ),
              );
            }).toList(),
          ),
          
          const SizedBox(height: DS.spacing16),
          
          // 领取奖励按钮
          if (task.status == TaskStatus.completed) ...[
            SizedBox(
              width: double.infinity,
              height: 44,
              child: ElevatedButton(
                onPressed: onClaimReward,
                style: ElevatedButton.styleFrom(
                  backgroundColor: DS.brandPrimary,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: DS.borderRadius12,
                  ),
                ),
                child: const Text('领取奖励'),
              ),
            ),
          ] else if (task.status == TaskStatus.claimed) ...[
            Center(
              child: Text(
                '已领取奖励',
                style: TextStyle(
                  color: DS.success,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  /// 获取任务状态颜色
  Color _getStatusColor(TaskStatus status) {
    switch (status) {
      case TaskStatus.pending:
        return DS.neutral400;
      case TaskStatus.completed:
        return DS.success;
      case TaskStatus.claimed:
        return DS.primaryBase;
    }
  }

  /// 获取任务状态名称
  String _getStatusName(TaskStatus status) {
    switch (status) {
      case TaskStatus.pending:
        return '进行中';
      case TaskStatus.completed:
        return '已完成';
      case TaskStatus.claimed:
        return '已领取';
    }
  }

  /// 获取奖励图标
  IconData _getRewardIcon(RewardType type) {
    switch (type) {
      case RewardType.experience:
        return Icons.stars;
      case RewardType.equipment:
        return Icons.shield;
      case RewardType.attribute:
        return Icons.fitness_center;
    }
  }

  /// 获取奖励文本
  String _getRewardText(TaskReward reward) {
    switch (reward.type) {
      case RewardType.experience:
        return '经验值 +${reward.value}';
      case RewardType.equipment:
        return '装备 x1';
      case RewardType.attribute:
        return '属性点 +${reward.value}';
    }
  }
}
