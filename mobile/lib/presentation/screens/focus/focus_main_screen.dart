import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/task_model.dart';
import 'package:sparkle/presentation/providers/task_provider.dart';

class FocusMainScreen extends ConsumerWidget {
  const FocusMainScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final taskState = ref.watch(taskListProvider);
    final todayTasks = taskState.todayTasks.where((t) => t.status != TaskStatus.completed).toList();

    return Scaffold(
      backgroundColor: AppDesignTokens.deepSpaceStart,
      appBar: AppBar(
        title: const Text('选择专注任务'),
        backgroundColor: Colors.transparent,
        elevation: 0,
        foregroundColor: DS.brandPrimary,
      ),
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.all(DS.xl),
              child: Text(
                '准备好开始专注了吗？',
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                  color: DS.brandPrimaryConst,
                ),
              ),
            ),
            Expanded(
              child: todayTasks.isEmpty
                  ? _buildEmptyState(context)
                  : ListView.builder(
                      padding: const EdgeInsets.symmetric(horizontal: 20),
                      itemCount: todayTasks.length,
                      itemBuilder: (context, index) {
                        final task = todayTasks[index];
                        return _buildTaskItem(context, task);
                      },
                    ),
            ),
            _buildQuickFocusButton(context),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context) => Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.assignment_turned_in_outlined, size: 64, color: DS.brandPrimary.withValues(alpha: 0.3)),
          const SizedBox(height: DS.lg),
          Text(
            '没有待办任务',
            style: TextStyle(color: DS.brandPrimary70Const, fontSize: 16),
          ),
          const SizedBox(height: DS.sm),
          SparkleButton.ghost(label: '创建一个新任务', onPressed: () => context.push('/tasks/new')),
        ],
      ),
    );

  Widget _buildTaskItem(BuildContext context, TaskModel task) => Card(
      margin: const EdgeInsets.only(bottom: 12),
      color: DS.brandPrimary.withValues(alpha: 0.1),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
        title: Text(
          task.title,
          style: TextStyle(color: DS.brandPrimaryConst, fontWeight: FontWeight.bold),
        ),
        subtitle: Text(
          '预计 ${task.estimatedMinutes} 分钟',
          style: TextStyle(color: DS.brandPrimary.withValues(alpha: 0.6)),
        ),
        trailing: Icon(Icons.arrow_forward_ios, color: DS.brandPrimary54, size: 16),
        onTap: () {
          context.push('/focus/mindfulness', extra: task);
        },
      ),
    );

  Widget _buildQuickFocusButton(BuildContext context) => Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: ElevatedButton(
        onPressed: () {
          // Create a dummy task for quick focus if needed, or just push a generic task
          final dummyTask = TaskModel(
            id: 'quick_focus',
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
          context.push('/focus/mindfulness', extra: dummyTask);
        },
        style: ElevatedButton.styleFrom(
          backgroundColor: AppDesignTokens.primaryBase,
          foregroundColor: DS.brandPrimary,
          minimumSize: const Size(double.infinity, 56),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
        child: const Text('快速开启专注 (25min)', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
      ),
    );
}
