import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/calendar/presentation/providers/calendar_provider.dart';
import 'package:sparkle/features/home/presentation/providers/calendar_preview_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/calendar/compact_task_card.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// Date utility functions
class _DateUtils {
  /// Check if two dates are the same day (ignoring time)
  static bool isSameDay(DateTime? a, DateTime? b) {
    if (a == null || b == null) return false;
    return a.year == b.year && a.month == b.month && a.day == b.day;
  }
}

/// Task preview panel - expandable panel showing tasks for selected date
class TaskPreviewPanel extends ConsumerWidget {
  const TaskPreviewPanel({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final previewState = ref.watch(calendarPreviewProvider);
    final selectedDate = previewState.selectedDate;
    final isExpanded = previewState.isExpanded;

    if (!isExpanded || selectedDate == null) {
      return const SizedBox.shrink();
    }

    final tasksAsync = ref.watch(dayTasksAsyncProvider(selectedDate));

    return AnimatedContainer(
      duration: const Duration(milliseconds: 250),
      curve: Curves.easeOut,
      margin: const EdgeInsets.only(top: DS.sm),
      child: MaterialStyler(
        material: AppMaterials.ceramic,
        borderRadius: DS.borderRadius16,
        padding: const EdgeInsets.all(DS.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildHeader(context, ref, selectedDate, tasksAsync),
            const SizedBox(height: DS.spacing12),
            _buildContent(context, ref, selectedDate, tasksAsync),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader(
    BuildContext context,
    WidgetRef ref,
    DateTime selectedDate,
    AsyncValue<List<TaskModel>> tasksAsync,
  ) {
    final today = DateTime.now();
    final isToday = _DateUtils.isSameDay(selectedDate, today);

    final taskCount = tasksAsync.valueOrNull?.length ?? 0;

    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(
                    isToday ? '今天' : DateFormat('M月d日', 'zh_CN').format(selectedDate),
                    style: context.sparkleTypography.titleLarge.copyWith(
                      fontWeight: FontWeight.w600,
                      color: DS.textPrimary,
                    ),
                  ),
                  if (!isToday) ...[
                    const SizedBox(width: DS.spacing6),
                    Text(
                      _getWeekdayName(selectedDate),
                      style: context.sparkleTypography.labelSmall.copyWith(
                        color: DS.textSecondary,
                      ),
                    ),
                  ],
                ],
              ),
              const SizedBox(height: DS.spacing4),
              Text(
                '$taskCount 个任务',
                style: context.sparkleTypography.labelSmall.copyWith(
                  color: DS.textSecondary,
                ),
              ),
            ],
          ),
        ),
        _CloseButton(
          onPressed: () =>
              ref.read(calendarPreviewProvider.notifier).collapse(),
        ),
      ],
    );
  }

  Widget _buildContent(
    BuildContext context,
    WidgetRef ref,
    DateTime selectedDate,
    AsyncValue<List<TaskModel>> tasksAsync,
  ) => tasksAsync.when(
      data: (tasks) {
        if (tasks.isEmpty) {
          return _buildEmptyState(context);
        }

        final displayTasks = tasks.take(3).toList();
        final hasMore = tasks.length > 3;

        return Column(
          children: [
            ...List.generate(displayTasks.length, (index) => Padding(
                padding: index < displayTasks.length - 1
                    ? const EdgeInsets.only(bottom: DS.spacing8)
                    : EdgeInsets.zero,
                child: _AnimatedTaskItem(
                  index: index,
                  child: CompactTaskCard(task: displayTasks[index]),
                ),
              ),),
            if (hasMore) ...[
              const SizedBox(height: DS.spacing12),
              _buildViewAllLink(context, selectedDate, tasks.length),
            ],
          ],
        );
      },
      loading: _buildLoadingState,
      error: (_, __) => _buildErrorState(context),
    );

  Widget _buildEmptyState(BuildContext context) => Container(
      padding: const EdgeInsets.symmetric(vertical: DS.spacing24),
      child: Column(
        children: [
          Icon(
            Icons.event_available_rounded,
            size: 40,
            color: DS.textSecondary.withValues(alpha: 0.5),
          ),
          const SizedBox(height: DS.spacing12),
          Text(
            '今天没有任务',
            style: context.sparkleTypography.bodyMedium.copyWith(
              color: DS.textSecondary,
            ),
          ),
          const SizedBox(height: DS.spacing4),
          Text(
            '享受你的自由时间',
            style: context.sparkleTypography.labelSmall.copyWith(
              color: DS.textTertiary,
            ),
          ),
        ],
      ),
    );

  Widget _buildLoadingState() => const SizedBox(
      height: 120,
      child: Center(
        child: CircularProgressIndicator(),
      ),
    );

  Widget _buildErrorState(BuildContext context) => Container(
      padding: const EdgeInsets.symmetric(vertical: DS.spacing16),
      child: Text(
        '加载任务失败，请稍后重试',
        style: context.sparkleTypography.bodyMedium.copyWith(
          color: DS.error,
        ),
        textAlign: TextAlign.center,
      ),
    );

  Widget _buildViewAllLink(BuildContext context, DateTime date, int totalCount) => InkWell(
      onTap: () => context.push('/calendar?date=${date.toIso8601String()}'),
      borderRadius: DS.borderRadius8,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing12,
          vertical: DS.spacing8,
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              '查看全部 $totalCount 个任务',
              style: context.sparkleTypography.labelSmall.copyWith(
                color: DS.brandPrimaryConst,
                fontWeight: FontWeight.w500,
              ),
            ),
            const SizedBox(width: DS.spacing4),
            Icon(
              Icons.arrow_forward_rounded,
              size: DS.iconSizeXs,
              color: DS.brandPrimaryConst,
            ),
          ],
        ),
      ),
    );

  String _getWeekdayName(DateTime date) {
    const weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
    return weekdays[date.weekday - 1];
  }
}

class _CloseButton extends StatelessWidget {
  const _CloseButton({required this.onPressed});

  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) => Material(
      color: DS.surfaceTertiary.withValues(alpha: 0.5),
      borderRadius: DS.borderRadiusFull,
      child: InkWell(
        onTap: onPressed,
        borderRadius: DS.borderRadiusFull,
        child: Container(
          padding: const EdgeInsets.all(DS.spacing6),
          child: Icon(
            Icons.close_rounded,
            size: DS.iconSizeSm,
            color: DS.textSecondary,
          ),
        ),
      ),
    );
}

/// Animated task item for staggered fade-in effect
class _AnimatedTaskItem extends StatefulWidget {
  const _AnimatedTaskItem({
    required this.index,
    required this.child,
  });

  final int index;
  final Widget child;

  @override
  State<_AnimatedTaskItem> createState() => _AnimatedTaskItemState();
}

class _AnimatedTaskItemState extends State<_AnimatedTaskItem>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 200),
      vsync: this,
    );
    _animation = CurvedAnimation(
      parent: _controller,
      curve: Curves.easeOut,
    );
    // Stagger animation based on index
    Future.delayed(Duration(milliseconds: widget.index * 50), () {
      if (mounted) {
        _controller.forward();
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => FadeTransition(
      opacity: _animation,
      child: SlideTransition(
        position: Tween<Offset>(
          begin: const Offset(0, -0.1),
          end: Offset.zero,
        ).animate(_animation),
        child: widget.child,
      ),
    );
}
