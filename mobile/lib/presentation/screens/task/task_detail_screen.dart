import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
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
                  padding: EdgeInsets.all(DS.spacing16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildInfoSection(context),
                      SizedBox(height: DS.spacing24),
                      Text(
                        '执行指南',
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          fontWeight: DS.fontWeightBold,
                        ),
                      ),
                      SizedBox(height: DS.spacing12),
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
                  padding: EdgeInsets.all(DS.spacing16),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.end,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        task.title,
                        style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                          fontWeight: DS.fontWeightBold,
                          color: DS.neutral900,
                        ),
                      ),
                      SizedBox(height: DS.spacing8),
                      Wrap(
                        spacing: DS.spacing8,
                        children: [
                          Chip(
                            label: Text(toBeginningOfSentenceCase(task.type.name) ?? task.type.name),
                            backgroundColor: DS.brandPrimary.withValues(alpha: 0.8),
                            avatar: Icon(Icons.category, size: 16, color: DS.primaryBase),
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
          gradient: DS.primaryGradient,
        ),
        SizedBox(height: DS.spacing12),
        Row(
          children: [
            Expanded(
              child: _InfoTileCard(
                icon: Icons.star_border,
                title: '难度',
                content: '${task.difficulty} / 5',
                gradient: DS.warningGradient,
              ),
            ),
            SizedBox(width: DS.spacing12),
            Expanded(
              child: _InfoTileCard(
                icon: Icons.local_fire_department,
                title: '消耗能量',
                content: '${task.energyCost} / 5',
                gradient: DS.errorGradient,
              ),
            ),
          ],
        ),
        if (task.dueDate != null) ...[
          SizedBox(height: DS.spacing12),
          _InfoTileCard(
            icon: Icons.calendar_today,
            title: '截止日期',
            content: DateFormat.yMMMd().format(task.dueDate!),
            gradient: DS.infoGradient,
          ),
        ],
      ],
    );

  Widget _buildGuideSection(BuildContext context) => Container(
      padding: EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: DS.brandPrimary,
        borderRadius: DS.borderRadius12,
        border: Border.all(color: DS.neutral200),
        boxShadow: DS.shadowSm,
      ),
      child: MarkdownBody(
        data: task.guideContent ?? '暂无执行指南',
        styleSheet: MarkdownStyleSheet(
          h1: Theme.of(context).textTheme.titleLarge?.copyWith(
            fontWeight: DS.fontWeightBold,
            color: DS.neutral900,
          ),
          h2: Theme.of(context).textTheme.titleMedium?.copyWith(
            fontWeight: DS.fontWeightBold,
            color: DS.neutral800,
          ),
          h3: Theme.of(context).textTheme.titleSmall?.copyWith(
            fontWeight: DS.fontWeightBold,
            color: DS.neutral700,
          ),
          p: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: DS.neutral700,
            height: 1.6,
          ),
          listBullet: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: DS.primaryBase,
          ),
          code: TextStyle(
            backgroundColor: DS.neutral100,
            color: DS.primaryDark,
            fontFamily: 'monospace',
            fontSize: DS.fontSizeSm,
          ),
          codeblockDecoration: BoxDecoration(
            color: DS.neutral50,
            borderRadius: DS.borderRadius8,
            border: Border.all(color: DS.neutral200),
          ),
          blockquote: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: DS.neutral600,
            fontStyle: FontStyle.italic,
          ),
          blockquoteDecoration: BoxDecoration(
            color: DS.neutral50,
            borderRadius: DS.borderRadius8,
            border: Border(
              left: BorderSide(
                color: DS.primaryBase,
                width: 4,
              ),
            ),
          ),
        ),
      ),
    );

  Color _getStatusColor(TaskStatus status) {
    switch (status) {
      case TaskStatus.pending: return DS.warning;
      case TaskStatus.inProgress: return DS.info;
      case TaskStatus.completed: return DS.success;
      case TaskStatus.abandoned: return DS.neutral500;
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
          padding: EdgeInsets.all(DS.spacing16),
          decoration: BoxDecoration(
            color: DS.brandPrimary,
            borderRadius: DS.borderRadius12,
            boxShadow: [
              BoxShadow(
                color: widget.gradient.colors.first.withValues(alpha: 0.15),
                blurRadius: 10,
                offset: Offset(0, 4),
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
                padding: EdgeInsets.all(10),
                decoration: BoxDecoration(
                  gradient: widget.gradient,
                  borderRadius: DS.borderRadius8,
                  boxShadow: [
                    BoxShadow(
                      color: widget.gradient.colors.first.withValues(alpha: 0.3),
                      blurRadius: 8,
                      offset: Offset(0, 2),
                    ),
                  ],
                ),
                child: Icon(widget.icon, color: DS.brandPrimary, size: 22),
              ),
              SizedBox(width: DS.spacing16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.title,
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: DS.neutral600,
                        fontWeight: DS.fontWeightMedium,
                        letterSpacing: 0.5,
                      ),
                    ),
                    SizedBox(height: DS.xs),
                    Text(
                      widget.content,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: DS.fontWeightBold,
                        color: DS.neutral900,
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
  _BottomActionBar({required this.task});
  final TaskModel task;

  @override
  Widget build(BuildContext context, WidgetRef ref) => SafeArea(
      child: Container(
        padding: EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          color: DS.brandPrimary,
          boxShadow: DS.shadowMd,
          border: Border(
            top: BorderSide(
              color: DS.neutral200,
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
            SizedBox(width: DS.spacing12),
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
            SizedBox(width: DS.spacing12),
            DecoratedBox(
              decoration: BoxDecoration(
                border: Border.all(
                  color: DS.error.withValues(alpha: 0.3),
                  width: 1.5,
                ),
                borderRadius: DS.borderRadius12,
              ),
              child: IconButton(
                icon: Icon(Icons.delete_outline, color: DS.error),
                onPressed: () {
                  HapticFeedback.mediumImpact();
                  showDialog(
                    context: context,
                    builder: (ctx) => AlertDialog(
                      shape: RoundedRectangleBorder(
                        borderRadius: DS.borderRadius20,
                      ),
                      title: Text(
                        '删除任务',
                        style: TextStyle(
                          fontWeight: DS.fontWeightBold,
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
                          customGradient: DS.errorGradient,
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