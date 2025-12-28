import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/task_model.dart';
import 'package:sparkle/presentation/providers/task_provider.dart';
import 'package:sparkle/presentation/widgets/common/custom_button.dart';
import 'package:sparkle/presentation/widgets/common/error_widget.dart';
import 'package:sparkle/presentation/widgets/common/loading_indicator.dart';

class TaskDetailScreen extends ConsumerWidget {

  const TaskDetailScreen({required this.taskId, super.key});
  final String taskId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final taskAsync = ref.watch(taskDetailProvider(taskId));

    return Scaffold(
      body: taskAsync.when(
        data: (task) => _TaskDetailView(task: task),
        loading: () => Center(
          child: LoadingIndicator.circular(
            showText: true,
            loadingText: '加载任务详情...',
          ),
        ),
        error: (err, stack) => CustomErrorWidget.page(
          message: '任务加载失败：$err',
          onRetry: () => ref.refresh(taskDetailProvider(taskId)),
        ),
      ),
    );
  }
}

class _TaskDetailView extends ConsumerWidget {

  const _TaskDetailView({required this.task});
  final TaskModel task;

  @override
  Widget build(BuildContext context, WidgetRef ref) => Column(
      children: [
        Expanded(
          child: CustomScrollView(
            slivers: [
              _buildSliverAppBar(context),
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.all(AppDesignTokens.spacing16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildInfoSection(context),
                      const SizedBox(height: AppDesignTokens.spacing24),
                      Text(
                        '执行指南',
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          fontWeight: AppDesignTokens.fontWeightBold,
                        ),
                      ),
                      const SizedBox(height: AppDesignTokens.spacing12),
                      _buildGuideSection(context),
                      const SizedBox(height: 100), // Space for bottom bar
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
        _BottomActionBar(task: task),
      ],
    );

  LinearGradient _getBackgroundGradient(TaskType type) {
    switch (type) {
      case TaskType.learning:
        return LinearGradient(colors: [DS.brandPrimary.shade50, DS.brandPrimary], begin: Alignment.topLeft, end: Alignment.bottomRight);
      case TaskType.training:
        return LinearGradient(colors: [DS.brandPrimary.shade50, DS.brandPrimary], begin: Alignment.topLeft, end: Alignment.bottomRight);
      case TaskType.errorFix:
        return LinearGradient(colors: [DS.error.shade50, DS.brandPrimary], begin: Alignment.topLeft, end: Alignment.bottomRight);
      case TaskType.reflection:
        return LinearGradient(colors: [Colors.purple.shade50, DS.brandPrimary], begin: Alignment.topLeft, end: Alignment.bottomRight);
      case TaskType.social:
        return LinearGradient(colors: [DS.success.shade50, DS.brandPrimary], begin: Alignment.topLeft, end: Alignment.bottomRight);
      case TaskType.planning:
        return LinearGradient(colors: [Colors.teal.shade50, DS.brandPrimary], begin: Alignment.topLeft, end: Alignment.bottomRight);
    }
  }

  Widget _buildSliverAppBar(BuildContext context) => SliverAppBar(
      expandedHeight: 200.0,
      pinned: true,
      flexibleSpace: FlexibleSpaceBar(
        background: Hero(
          tag: 'task-${task.id}',
          child: Material(
            type: MaterialType.transparency,
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: _getBackgroundGradient(task.type),
              ),
              child: SafeArea(
                child: Padding(
                  padding: const EdgeInsets.all(AppDesignTokens.spacing16),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.end,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        task.title,
                        style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                          fontWeight: AppDesignTokens.fontWeightBold,
                          color: AppDesignTokens.neutral900,
                        ),
                      ),
                      const SizedBox(height: AppDesignTokens.spacing8),
                      Wrap(
                        spacing: AppDesignTokens.spacing8,
                        children: [
                          Chip(
                            label: Text(toBeginningOfSentenceCase(task.type.name) ?? task.type.name),
                            backgroundColor: DS.brandPrimary.withValues(alpha: 0.8),
                            avatar: const Icon(Icons.category, size: 16, color: AppDesignTokens.primaryBase),
                          ),
                          Chip(
                            label: Text(toBeginningOfSentenceCase(task.status.name) ?? task.status.name),
                            backgroundColor: _getStatusColor(task.status).withValues(alpha: 0.2),
                            labelStyle: TextStyle(color: _getStatusColor(task.status), fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );

  Widget _buildInfoSection(BuildContext context) => Column(
      children: [
        _InfoTileCard(
          icon: Icons.timer_outlined,
          title: '预计时长',
          content: '${task.estimatedMinutes} 分钟',
          gradient: AppDesignTokens.primaryGradient,
        ),
        const SizedBox(height: AppDesignTokens.spacing12),
        Row(
          children: [
            Expanded(
              child: _InfoTileCard(
                icon: Icons.star_border,
                title: '难度',
                content: '${task.difficulty} / 5',
                gradient: AppDesignTokens.warningGradient,
              ),
            ),
            const SizedBox(width: AppDesignTokens.spacing12),
            Expanded(
              child: _InfoTileCard(
                icon: Icons.local_fire_department,
                title: '消耗能量',
                content: '${task.energyCost} / 5',
                gradient: AppDesignTokens.errorGradient,
              ),
            ),
          ],
        ),
        if (task.dueDate != null) ...[
          const SizedBox(height: AppDesignTokens.spacing12),
          _InfoTileCard(
            icon: Icons.calendar_today,
            title: '截止日期',
            content: DateFormat.yMMMd().format(task.dueDate!),
            gradient: AppDesignTokens.infoGradient,
          ),
        ],
      ],
    );

  Widget _buildGuideSection(BuildContext context) => Container(
      padding: const EdgeInsets.all(AppDesignTokens.spacing16),
      decoration: BoxDecoration(
        color: DS.brandPrimary,
        borderRadius: AppDesignTokens.borderRadius12,
        border: Border.all(color: AppDesignTokens.neutral200),
        boxShadow: AppDesignTokens.shadowSm,
      ),
      child: MarkdownBody(
        data: task.guideContent ?? '暂无执行指南',
        styleSheet: MarkdownStyleSheet(
          h1: Theme.of(context).textTheme.titleLarge?.copyWith(
            fontWeight: AppDesignTokens.fontWeightBold,
            color: AppDesignTokens.neutral900,
          ),
          h2: Theme.of(context).textTheme.titleMedium?.copyWith(
            fontWeight: AppDesignTokens.fontWeightBold,
            color: AppDesignTokens.neutral800,
          ),
          h3: Theme.of(context).textTheme.titleSmall?.copyWith(
            fontWeight: AppDesignTokens.fontWeightBold,
            color: AppDesignTokens.neutral700,
          ),
          p: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: AppDesignTokens.neutral700,
            height: 1.6,
          ),
          listBullet: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: AppDesignTokens.primaryBase,
          ),
          code: const TextStyle(
            backgroundColor: AppDesignTokens.neutral100,
            color: AppDesignTokens.primaryDark,
            fontFamily: 'monospace',
            fontSize: AppDesignTokens.fontSizeSm,
          ),
          codeblockDecoration: BoxDecoration(
            color: AppDesignTokens.neutral50,
            borderRadius: AppDesignTokens.borderRadius8,
            border: Border.all(color: AppDesignTokens.neutral200),
          ),
          blockquote: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: AppDesignTokens.neutral600,
            fontStyle: FontStyle.italic,
          ),
          blockquoteDecoration: BoxDecoration(
            color: AppDesignTokens.neutral50,
            borderRadius: AppDesignTokens.borderRadius8,
            border: const Border(
              left: BorderSide(
                color: AppDesignTokens.primaryBase,
                width: 4,
              ),
            ),
          ),
        ),
      ),
    );

  Color _getStatusColor(TaskStatus status) {
    switch (status) {
      case TaskStatus.pending: return AppDesignTokens.warning;
      case TaskStatus.inProgress: return AppDesignTokens.info;
      case TaskStatus.completed: return AppDesignTokens.success;
      case TaskStatus.abandoned: return AppDesignTokens.neutral500;
    }
  }
}

class _InfoTileCard extends StatefulWidget {

  const _InfoTileCard({
    required this.icon,
    required this.title,
    required this.content,
    required this.gradient,
  });
  final IconData icon;
  final String title;
  final String content;
  final LinearGradient gradient;

  @override
  State<_InfoTileCard> createState() => _InfoTileCardState();
}

class _InfoTileCardState extends State<_InfoTileCard> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 150),
      vsync: this,
    );
    _scaleAnimation = Tween<double>(begin: 1.0, end: 0.95).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => GestureDetector(
      onTapDown: (_) => _controller.forward(),
      onTapUp: (_) => _controller.reverse(),
      onTapCancel: () => _controller.reverse(),
      child: ScaleTransition(
        scale: _scaleAnimation,
        child: Container(
          padding: const EdgeInsets.all(AppDesignTokens.spacing16),
          decoration: BoxDecoration(
            color: DS.brandPrimary,
            borderRadius: AppDesignTokens.borderRadius12,
            boxShadow: [
              BoxShadow(
                color: widget.gradient.colors.first.withValues(alpha: 0.15),
                blurRadius: 10,
                offset: const Offset(0, 4),
              ),
              BoxShadow(
                color: DS.brandPrimary.withValues(alpha: 0.05),
                blurRadius: 6,
                offset: const Offset(0, 2),
              ),
            ],
            border: Border.all(
              color: widget.gradient.colors.first.withValues(alpha: 0.1),
            ),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  gradient: widget.gradient,
                  borderRadius: AppDesignTokens.borderRadius8,
                  boxShadow: [
                    BoxShadow(
                      color: widget.gradient.colors.first.withValues(alpha: 0.3),
                      blurRadius: 8,
                      offset: const Offset(0, 2),
                    ),
                  ],
                ),
                child: Icon(widget.icon, color: DS.brandPrimary, size: 22),
              ),
              const SizedBox(width: AppDesignTokens.spacing16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.title,
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: AppDesignTokens.neutral600,
                        fontWeight: AppDesignTokens.fontWeightMedium,
                        letterSpacing: 0.5,
                      ),
                    ),
                    const SizedBox(height: DS.xs),
                    Text(
                      widget.content,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: AppDesignTokens.fontWeightBold,
                        color: AppDesignTokens.neutral900,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
}

class _BottomActionBar extends ConsumerWidget {
  const _BottomActionBar({required this.task});
  final TaskModel task;

  @override
  Widget build(BuildContext context, WidgetRef ref) => SafeArea(
      child: Container(
        padding: const EdgeInsets.all(AppDesignTokens.spacing16),
        decoration: BoxDecoration(
          color: DS.brandPrimary,
          boxShadow: AppDesignTokens.shadowMd,
          border: const Border(
            top: BorderSide(
              color: AppDesignTokens.neutral200,
            ),
          ),
        ),
        child: Row(
          children: [
            Expanded(
              child: CustomButton.secondary(
                text: '编辑',
                icon: Icons.edit_outlined,
                onPressed: () {
                  HapticFeedback.mediumImpact();
                  // TODO: 需要创建任务编辑页面，暂时导航到创建页面
                  context.push('/tasks/new');
                },
              ),
            ),
            const SizedBox(width: AppDesignTokens.spacing12),
            Expanded(
              flex: 2,
              child: CustomButton.primary(
                text: '开始任务',
                icon: Icons.play_arrow_rounded,
                onPressed: () {
                  HapticFeedback.heavyImpact();
                  ref.read(activeTaskProvider.notifier).state = task;
                  context.push('/tasks/${task.id}/execute');
                },
              ),
            ),
            const SizedBox(width: AppDesignTokens.spacing12),
            DecoratedBox(
              decoration: BoxDecoration(
                border: Border.all(
                  color: AppDesignTokens.error.withValues(alpha: 0.3),
                  width: 1.5,
                ),
                borderRadius: AppDesignTokens.borderRadius12,
              ),
              child: IconButton(
                icon: const Icon(Icons.delete_outline, color: AppDesignTokens.error),
                onPressed: () {
                  HapticFeedback.mediumImpact();
                  showDialog(
                    context: context,
                    builder: (ctx) => AlertDialog(
                      shape: RoundedRectangleBorder(
                        borderRadius: AppDesignTokens.borderRadius20,
                      ),
                      title: const Text(
                        '删除任务',
                        style: TextStyle(
                          fontWeight: AppDesignTokens.fontWeightBold,
                        ),
                      ),
                      content: const Text('确定要删除这个任务吗？此操作无法撤销。'),
                      actions: [
                        CustomButton.text(
                          text: '取消',
                          onPressed: () => Navigator.of(ctx).pop(),
                        ),
                        CustomButton.primary(
                          text: '删除',
                          icon: Icons.delete_rounded,
                          onPressed: () {
                            HapticFeedback.heavyImpact();
                            Navigator.of(ctx).pop();
                            ref.read(taskListProvider.notifier).deleteTask(task.id);
                            context.pop();
                          },
                          customGradient: AppDesignTokens.errorGradient,
                          size: CustomButtonSize.small,
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
}