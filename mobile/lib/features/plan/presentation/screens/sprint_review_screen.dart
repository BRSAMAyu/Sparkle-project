import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';

/// Sprint Review Screen — structured checkpoint experience showing accumulated
/// sprint progress, bottleneck analysis, and plan adjustment options.
class SprintReviewScreen extends ConsumerWidget {
  const SprintReviewScreen({super.key, required this.planId});
  final String planId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashboard = ref.watch(dashboardProvider);
    final sprint = dashboard.sprint;
    final zh = I18nService.instance.isChinese;
    final planState = ref.watch(planListProvider);
    final plan = planState.activePlans.where((p) => p.id == planId).firstOrNull;
    final isLoading = dashboard.isLoading || planState.isLoading;
    final error = dashboard.error ?? planState.error;

    final progress = sprint?.progress ?? plan?.progress ?? 0.0;
    final daysLeft = sprint?.daysLeft ?? 0;
    final sprintName = sprint?.name ?? plan?.name ?? (zh ? '冲刺' : 'Sprint');

    return Scaffold(
      backgroundColor: DS.surfacePrimary,
      appBar: AppBar(
        backgroundColor: DS.surfacePrimary,
        elevation: 0,
        leading: SparkleIconButton(
          icon: Icon(Icons.arrow_back_rounded, color: DS.textSecondary),
          onPressed: () => context.pop(),
          semanticLabel: context.l10n.back,
          variant: ButtonVariant.ghost,
        ),
        title: Text(
          zh ? '冲刺复盘' : 'Sprint Review',
          style: DS.bodyMedium.copyWith(
            color: DS.textPrimary,
            fontWeight: DS.fontWeightBold,
          ),
        ),
      ),
      body: isLoading
          ? const _SprintReviewSkeleton()
          : ListView(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 40),
              children: [
                if (error != null) ...[
                  _ReviewStatusBanner(
                    message: error,
                    onRetry: () {
                      unawaited(ref.read(dashboardProvider.notifier).refresh());
                      unawaited(ref.read(planListProvider.notifier).refresh());
                    },
                  ),
                  const SizedBox(height: 12),
                ],
                _ProgressHero(
                  name: sprintName,
                  progress: progress,
                  daysLeft: daysLeft,
                ),
                const SizedBox(height: 20),
                _StatsRow(progress: progress, daysLeft: daysLeft),
                const SizedBox(height: 24),
                _SectionHeader(
                  icon: Icons.psychology_outlined,
                  title: zh ? '瓶颈分析' : 'Bottleneck Analysis',
                ),
                const SizedBox(height: 8),
                _BottleneckCard(
                  planId: planId,
                  progress: progress,
                  daysLeft: daysLeft,
                ),
                const SizedBox(height: 24),
                _SectionHeader(
                  icon: Icons.edit_note_rounded,
                  title: zh ? '复盘笔记' : 'Review Notes',
                ),
                const SizedBox(height: 8),
                _ReviewNotesCard(planId: planId, ref: ref),
                const SizedBox(height: 32),
                _ActionButtons(planId: planId),
              ],
            ),
    );
  }
}

class _SprintReviewSkeleton extends StatelessWidget {
  const _SprintReviewSkeleton();

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 40),
        physics: const NeverScrollableScrollPhysics(),
        children: [
          const SparkleCardSkeleton(),
          const SizedBox(height: 20),
          Row(
            children: List.generate(
              3,
              (_) => const Expanded(
                child: Padding(
                  padding: EdgeInsets.symmetric(horizontal: 5),
                  child: Column(
                    children: [
                      SparkleSkeleton(width: 20, height: 20, borderRadius: 10),
                      SizedBox(height: 6),
                      SparkleSkeleton(height: 16, borderRadius: 6),
                      SizedBox(height: 4),
                      SparkleSkeleton(width: 40, height: 12, borderRadius: 6),
                    ],
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 24),
          const SparkleCardSkeleton(),
          const SizedBox(height: 24),
          const SparkleCardSkeleton(),
        ],
      );
}

class _ProgressHero extends StatelessWidget {
  const _ProgressHero({
    required this.name,
    required this.progress,
    required this.daysLeft,
  });

  final String name;
  final double progress;
  final int daysLeft;

  @override
  Widget build(BuildContext context) {
    final zh = I18nService.instance.isChinese;
    final percent = (progress.clamp(0.0, 1.0) * 100).toInt();
    final isUrgent = daysLeft <= 3;
    final color = isUrgent ? DS.error : DS.brandPrimary;

    return Container(
      padding: const EdgeInsets.all(DS.spacing20),
      decoration: BoxDecoration(
        color: DS.surfaceHigh,
        borderRadius: DS.borderRadius20,
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Column(
        children: [
          Text(
            name,
            style: DS.bodyMedium.copyWith(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightBold,
            ),
          ),
          const SizedBox(height: 16),
          TweenAnimationBuilder<double>(
            tween: Tween(begin: 0, end: progress.clamp(0.0, 1.0)),
            duration: DS.durationSlow,
            builder: (context, value, child) => Column(
              children: [
                Text(
                  '$percent%',
                  style: DS.headingLarge.copyWith(
                    color: color,
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
                const SizedBox(height: 8),
                ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(
                    value: value,
                    minHeight: 8,
                    backgroundColor: color.withValues(alpha: 0.12),
                    valueColor: AlwaysStoppedAnimation(color),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Text(
            zh
                ? (daysLeft > 0 ? '还剩 $daysLeft 天' : '冲刺已到期')
                : (daysLeft > 0 ? '$daysLeft days left' : 'Sprint overdue'),
            style: DS.labelSmall.copyWith(
              color: isUrgent ? DS.error : DS.textSecondary,
            ),
          ),
        ],
      ),
    );
  }
}

class _StatsRow extends StatelessWidget {
  const _StatsRow({required this.progress, required this.daysLeft});

  final double progress;
  final int daysLeft;

  @override
  Widget build(BuildContext context) {
    final zh = I18nService.instance.isChinese;
    final completed = (progress * 10).round();
    final remaining = 10 - completed;

    return Row(
      children: [
        Expanded(
          child: _StatChip(
            icon: Icons.check_circle_outline,
            label: zh ? '已完成' : 'Done',
            value: '$completed',
            color: DS.success,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _StatChip(
            icon: Icons.pending_outlined,
            label: zh ? '待完成' : 'Left',
            value: '$remaining',
            color: DS.warning,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _StatChip(
            icon: Icons.timer_outlined,
            label: zh ? '天数' : 'Days',
            value: '$daysLeft',
            color: daysLeft <= 3 ? DS.error : DS.info,
          ),
        ),
      ],
    );
  }
}

class _StatChip extends StatelessWidget {
  const _StatChip({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          vertical: DS.spacing12,
          horizontal: DS.spacing10,
        ),
        decoration: BoxDecoration(
          color: DS.surfaceHigh,
          borderRadius: DS.borderRadius12,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Column(
          children: [
            Icon(icon, size: 20, color: color),
            const SizedBox(height: 4),
            Text(
              value,
              style: DS.bodyMedium.copyWith(
                color: DS.textPrimary,
                fontWeight: DS.fontWeightBold,
              ),
            ),
            Text(
              label,
              style: DS.labelSmall.copyWith(color: DS.textSecondary),
            ),
          ],
        ),
      );
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({required this.icon, required this.title});

  final IconData icon;
  final String title;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Icon(icon, size: 18, color: DS.brandPrimary),
          const SizedBox(width: 8),
          Text(
            title,
            style: DS.bodySmall.copyWith(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightBold,
            ),
          ),
        ],
      );
}

class _BottleneckCard extends ConsumerWidget {
  const _BottleneckCard({
    required this.planId,
    required this.progress,
    required this.daysLeft,
  });

  final String planId;
  final double progress;
  final int daysLeft;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final zh = I18nService.instance.isChinese;

    // Derive bottleneck insights from available data
    final insights = <_Insight>[];

    if (progress < 0.3 && daysLeft <= 3) {
      insights.add(_Insight(
        icon: Icons.warning_amber_rounded,
        color: DS.error,
        title: zh ? '进度严重落后' : 'Significantly behind',
        detail: zh
            ? '冲刺进度不足 30%，且剩余时间不多。建议缩小范围，聚焦最高优先级任务。'
            : 'Sprint is under 30% with little time left. Consider reducing scope to top-priority tasks.',
      ));
    } else if (progress < 0.5) {
      insights.add(_Insight(
        icon: Icons.info_outline,
        color: DS.warning,
        title: zh ? '进度偏慢' : 'Progress slower than expected',
        detail: zh
            ? '完成度未过半。可以检查任务粒度是否合适，或考虑拆分大任务。'
            : 'Less than halfway done. Check if tasks are too large or need splitting.',
      ));
    }

    if (daysLeft <= 1) {
      insights.add(_Insight(
        icon: Icons.schedule_outlined,
        color: DS.warning,
        title: zh ? '冲刺即将结束' : 'Sprint ending soon',
        detail: zh
            ? '考虑记录当前冲刺的经验教训，为下一个冲刺做准备。'
            : 'Consider documenting lessons learned for the next sprint.',
      ));
    }

    if (insights.isEmpty) {
      insights.add(_Insight(
        icon: Icons.trending_up_rounded,
        color: DS.success,
        title: zh ? '进展顺利' : 'On track',
        detail: zh
            ? '冲刺进度正常，继续保持当前节奏。'
            : 'Sprint progress is healthy. Keep up the current pace.',
      ));
    }

    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: DS.surfaceHigh,
        borderRadius: DS.borderRadius12,
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: insights
            .map((i) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(i.icon, size: 18, color: i.color),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              i.title,
                              style: DS.bodySmall.copyWith(
                                color: DS.textPrimary,
                                fontWeight: DS.fontWeightSemibold,
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              i.detail,
                              style: DS.labelSmall.copyWith(
                                color: DS.textSecondary,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ))
            .toList(),
      ),
    );
  }
}

class _Insight {
  const _Insight({
    required this.icon,
    required this.color,
    required this.title,
    required this.detail,
  });

  final IconData icon;
  final Color color;
  final String title;
  final String detail;
}

class _ReviewNotesCard extends StatefulWidget {
  const _ReviewNotesCard({required this.planId, required this.ref});

  final String planId;
  final WidgetRef ref;

  @override
  State<_ReviewNotesCard> createState() => _ReviewNotesCardState();
}

class _ReviewNotesCardState extends State<_ReviewNotesCard> {
  final _controller = TextEditingController();
  bool _loading = true;
  bool _saving = false;

  static const _keyPrefix = 'sprint_review_notes_';

  @override
  void initState() {
    super.initState();
    unawaited(_loadNotes());
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final zh = I18nService.instance.isChinese;

    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: DS.surfaceHigh,
        borderRadius: DS.borderRadius12,
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            controller: _controller,
            enabled: !_loading && !_saving,
            style: DS.bodySmall.copyWith(color: DS.textPrimary),
            maxLines: 4,
            decoration: InputDecoration(
              hintText: zh
                  ? '记录这次冲刺中做得好的和需要改进的...'
                  : 'What went well? What could improve?',
              hintStyle: DS.labelSmall.copyWith(color: DS.textTertiary),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: BorderSide(color: DS.borderSubtle),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: BorderSide(color: DS.borderSubtle),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: BorderSide(color: DS.brandPrimary),
              ),
            ),
          ),
          const SizedBox(height: 12),
          Align(
            alignment: Alignment.centerRight,
            child: OutlinedButton.icon(
              onPressed: _loading || _saving ? null : () => unawaited(_save()),
              icon: _saving
                  ? const SizedBox(
                      width: 14,
                      height: 14,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.save_outlined, size: 16),
              label: Text(zh ? '保存笔记' : 'Save notes'),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _loadNotes() async {
    final prefs = await SharedPreferences.getInstance();
    if (!mounted) return;
    var notes = prefs.getString('$_keyPrefix${widget.planId}') ?? '';
    if (notes.isEmpty) {
      final planState = widget.ref.read(planListProvider);
      final plan = planState.activePlans
          .where((p) => p.id == widget.planId)
          .firstOrNull;
      final serverNotes = plan?.sourceMetadata?['sprint_review_notes'] as String?;
      if (serverNotes != null && serverNotes.isNotEmpty) {
        notes = serverNotes;
        await prefs.setString('$_keyPrefix${widget.planId}', notes);
      }
    }
    _controller.text = notes;
    setState(() => _loading = false);
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    final notes = _controller.text.trim();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('$_keyPrefix${widget.planId}', notes);
    unawaited(
      widget.ref
          .read(planRepositoryProvider)
          .saveSprintReviewNotes(widget.planId, notes),
    );
    if (!mounted) return;
    setState(() => _saving = false);
    final zh = I18nService.instance.isChinese;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(zh ? '复盘笔记已保存' : 'Review notes saved')),
    );
  }
}

class _ReviewStatusBanner extends StatelessWidget {
  const _ReviewStatusBanner({
    required this.message,
    required this.onRetry,
  });

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final zh = I18nService.instance.isChinese;
    return Semantics(
      container: true,
      label: zh ? '冲刺复盘加载异常：$message' : 'Sprint review load issue: $message',
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: DS.warning.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: DS.warning.withValues(alpha: 0.3)),
        ),
        child: Row(
          children: [
            Icon(Icons.info_outline, color: DS.warning, size: 18),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                message,
                style: DS.labelSmall.copyWith(color: DS.textSecondary),
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            TextButton(
              onPressed: onRetry,
              child: Text(zh ? '重试' : 'Retry'),
            ),
          ],
        ),
      ),
    );
  }
}

class _ActionButtons extends ConsumerWidget {
  const _ActionButtons({required this.planId});

  final String planId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final zh = I18nService.instance.isChinese;

    return Column(
      children: [
        SizedBox(
          width: double.infinity,
          child: FilledButton(
            onPressed: () {
              SensoryFeedbackService.emit(SensoryFeedbackEvent.selection);
              context.pop();
            },
            style: FilledButton.styleFrom(
              backgroundColor: DS.brandPrimary,
              foregroundColor: DS.textOnPrimary,
              padding: const EdgeInsets.symmetric(vertical: 14),
              shape: RoundedRectangleBorder(
                borderRadius: DS.borderRadius12,
              ),
            ),
            child: Text(
              zh ? '继续冲刺' : 'Continue Sprint',
              style: DS.bodySmall.copyWith(
                fontWeight: DS.fontWeightBold,
                color: DS.textOnPrimary,
              ),
            ),
          ),
        ),
        const SizedBox(height: 10),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton(
            onPressed: () {
              SensoryFeedbackService.emit(SensoryFeedbackEvent.selection);
              unawaited(context.push('/plans/$planId/edit'));
            },
            style: OutlinedButton.styleFrom(
              foregroundColor: DS.textSecondary,
              padding: const EdgeInsets.symmetric(vertical: 14),
              shape: RoundedRectangleBorder(
                borderRadius: DS.borderRadius12,
              ),
              side: BorderSide(color: DS.borderSubtle),
            ),
            child: Text(
              zh ? '调整计划' : 'Adjust Plan',
              style: DS.bodySmall.copyWith(
                fontWeight: DS.fontWeightMedium,
                color: DS.textSecondary,
              ),
            ),
          ),
        ),
      ],
    );
  }
}
