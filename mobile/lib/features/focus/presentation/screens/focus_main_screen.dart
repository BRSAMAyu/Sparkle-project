import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class FocusMainScreen extends ConsumerWidget {
  const FocusMainScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final taskState = ref.watch(taskListProvider);
    final todayTasks = taskState.todayTasks
        .where((t) => t.status != TaskStatus.completed)
        .toList();

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          size: DS.touchTargetMinSize,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: const Text('选择专注任务'),
      ),
      safeArea: false,
      child: SafeArea(
        child: ContentConstraint(
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  DS.spacing20,
                  DS.spacing16,
                  DS.spacing20,
                  DS.spacing12,
                ),
                child: Text(
                  '准备好开始专注了吗？',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                    color: DS.textPrimary,
                  ),
                ),
              ),
              Expanded(
                child: todayTasks.isEmpty
                    ? _buildEmptyState(context, ref)
                    : ListView.builder(
                        padding: const EdgeInsets.symmetric(horizontal: 20),
                        itemCount: todayTasks.length,
                        itemBuilder: (context, index) {
                          final task = todayTasks[index];
                          return _buildTaskItem(context, task);
                        },
                      ),
              ),
              _buildQuickFocusButton(context, ref),
              const SizedBox(height: 20),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context, WidgetRef ref) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.assignment_turned_in_outlined,
              size: 64,
              color: DS.textSecondary.withValues(alpha: 0.3),
            ),
            const SizedBox(height: DS.lg),
            Text(
              '没有待办任务',
              style: TextStyle(color: DS.textSecondary, fontSize: 16),
            ),
            const SizedBox(height: DS.md),
            Text(
              '不过你依然可以直接开始专注！',
              style: TextStyle(color: DS.textSecondary, fontSize: 14),
            ),
            const SizedBox(height: DS.lg),
            // 🆕 在空状态下也显示快速专注按钮
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 40),
              child: SparkleButton(
                expand: true,
                onPressed: () {
                  final dummyTask = TaskModel(
                    id: 'quick_focus_${DateTime.now().millisecondsSinceEpoch}',
                    userId: '',
                    title: '自由专注',
                    type: TaskType.learning,
                    estimatedMinutes: 25,
                    difficulty: 1,
                    energyCost: 1,
                    priority: 1,
                    tags: [],
                    status: TaskStatus.pending,
                    createdAt: DateTime.now(),
                    updatedAt: DateTime.now(),
                  );
                  // 🔧 修复：设置activeTaskProvider以便TaskExecutionScreen能读取
                  ref.read(activeTaskProvider.notifier).state = dummyTask;
                  context.push('/tasks/${dummyTask.id}/execute');
                },
                icon: const Icon(Icons.play_circle_outline),
                label: '立即开始专注',
              ),
            ),
            const SizedBox(height: DS.sm),
            SparkleButton.ghost(
              label: '或者创建一个新任务',
              onPressed: () => context.push('/tasks/new'),
            ),
          ],
        ),
      );

  Widget _buildTaskItem(BuildContext context, TaskModel task) =>
      GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        margin: const EdgeInsets.only(bottom: 12),
        padding: EdgeInsets.zero,
        child: Consumer(
          builder: (context, ref, child) => ListTile(
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
            title: Text(
              task.title,
              style: TextStyle(
                color: DS.textPrimary,
                fontWeight: FontWeight.w600,
              ),
            ),
            subtitle: Text(
              '预计 ${task.estimatedMinutes} 分钟',
              style: TextStyle(color: DS.textSecondary),
            ),
            trailing: Icon(
              Icons.arrow_forward_ios,
              color: DS.textSecondary.withValues(alpha: 0.5),
              size: 16,
            ),
            onTap: () {
              // 🔧 修复：设置activeTaskProvider以便TaskExecutionScreen能读取
              ref.read(activeTaskProvider.notifier).state = task;
              context.push('/tasks/${task.id}/execute');
            },
          ),
        ),
      );

  Widget _buildQuickFocusButton(BuildContext context, WidgetRef ref) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20),
        child: SparkleButton(
          expand: true,
          label: '快速开启专注 (25min)',
          onPressed: () {
            // Create a dummy task for quick focus if needed, or just push a generic task
            final dummyTask = TaskModel(
              id: 'quick_focus_${DateTime.now().millisecondsSinceEpoch}',
              userId: '',
              title: '快速专注',
              type: TaskType.learning,
              estimatedMinutes: 25,
              difficulty: 1,
              energyCost: 1,
              priority: 1,
              tags: [],
              status: TaskStatus.pending,
              createdAt: DateTime.now(),
              updatedAt: DateTime.now(),
            );
            // 🔧 修复：设置activeTaskProvider以便TaskExecutionScreen能读取
            ref.read(activeTaskProvider.notifier).state = dummyTask;
            context.push('/tasks/${dummyTask.id}/execute');
          },
        ),
      );
}
