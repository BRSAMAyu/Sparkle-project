import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/utils/formatters.dart';
import 'package:sparkle/features/cognitive/data/models/capsule_generation_job_model.dart';
import 'package:sparkle/features/cognitive/presentation/providers/capsule_provider.dart';
import 'package:sparkle/features/cognitive/presentation/screens/capsule/capsule_detail_screen.dart';

/// 胶囊生成任务状态页
///
/// 显示所有胶囊生成任务的状态，支持查看详情和重试
class CapsuleJobsScreen extends ConsumerStatefulWidget {
  const CapsuleJobsScreen({super.key});

  @override
  ConsumerState<CapsuleJobsScreen> createState() => _CapsuleJobsScreenState();
}

class _CapsuleJobsScreenState extends ConsumerState<CapsuleJobsScreen> {
  @override
  void initState() {
    super.initState();
    // Load jobs on init
    unawaited(
      Future.microtask(
        () => ref.read(generationJobsProvider.notifier).fetchJobs(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final jobsState = ref.watch(generationJobsProvider);
    final l10n = context.l10n;

    return Scaffold(
      appBar: AppBar(
        leading: SparkleIconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
          variant: ButtonVariant.ghost,
        ),
        title: Text(l10n.capsuleJobsTitle),
        actions: [
          SparkleIconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              unawaited(
                SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
              );
              unawaited(ref.read(generationJobsProvider.notifier).fetchJobs());
            },
            variant: ButtonVariant.ghost,
          ),
        ],
      ),
      body: ContentConstraint(
        child: jobsState.when(
          data: (jobs) => jobs.isEmpty
              ? _buildEmptyState()
              : RefreshIndicator(
                  onRefresh: () =>
                      ref.read(generationJobsProvider.notifier).fetchJobs(),
                  child: ListView.builder(
                    padding: EdgeInsets.zero,
                    itemCount: jobs.length,
                    itemBuilder: (context, index) {
                      final job = jobs[index];
                      return Padding(
                        padding: const EdgeInsets.only(bottom: DS.spacing16),
                        child: SparkleStaggerItem(
                          index: index,
                          child: _JobCard(job: job),
                        ),
                      );
                    },
                  ),
                ),
          loading: () => LoadingIndicator.circular(
            showText: true,
            loadingText: '正在同步生成任务...',
          ),
          error: (err, stack) => CustomErrorWidget.page(
            context: context,
            title: '生成任务加载失败',
            message: l10n.capsuleLoadFailed('$err'),
            onRetry: () => ref.read(generationJobsProvider.notifier).fetchJobs(),
          ),
        ),
      ),
    );
  }

  Widget _buildEmptyState() => Builder(
        builder: (context) => EmptyState(
          title: context.l10n.capsuleNoJobs,
          description: context.l10n.capsuleNoJobsSubtitle,
          icon: Icons.task_alt_outlined,
        ),
      );
}

class _JobCard extends ConsumerWidget {
  const _JobCard({required this.job});

  final CapsuleGenerationJobModel job;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final l10n = context.l10n;

    return Container(
      margin: const EdgeInsets.only(bottom: DS.spacing16),
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: isDark ? DS.surfaceTertiary : DS.surfaceSecondary,
        borderRadius: DS.borderRadius16,
        border: Border.all(
          color: _getStatusColor().withValues(alpha: 0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 头部：状态和类型
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing8,
                  vertical: DS.spacing4,
                ),
                decoration: BoxDecoration(
                  color: _getStatusColor().withValues(alpha: 0.15),
                  borderRadius: DS.borderRadius8,
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(job.statusEmoji),
                    const SizedBox(width: 4),
                    Text(
                      job.statusLabel,
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: _getStatusColor(),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: DS.spacing8),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing8,
                  vertical: DS.spacing4,
                ),
                decoration: BoxDecoration(
                  color: isDark ? DS.neutral700 : DS.neutral200,
                  borderRadius: DS.borderRadius8,
                ),
                child: Text(
                  job.generationTypeLabel,
                  style: TextStyle(
                    fontSize: 12,
                    color: DS.textSecondary,
                  ),
                ),
              ),
              const Spacer(),
              Text(
                Formatters.formatRelativeTime(job.createdAt),
                style: TextStyle(fontSize: 12, color: DS.textSecondary),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing12),

          // 进度条 (仅在生成中时显示)
          if (job.isGenerating) ...[
            LinearProgressIndicator(
              value: job.progress,
              backgroundColor: isDark ? DS.neutral700 : DS.neutral200,
              valueColor: AlwaysStoppedAnimation<Color>(DS.primaryBase),
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              l10n.capsuleGeneratingProgress(job.progressPercent),
              style: TextStyle(fontSize: 12, color: DS.textSecondary),
            ),
            const SizedBox(height: DS.spacing12),
          ],

          // 偏好信息
          Row(
            children: [
              Icon(Icons.timeline_outlined, size: 14, color: DS.info),
              const SizedBox(width: 4),
              Text(
                l10n.capsuleDepthPercent((job.depthPreference * 100).toInt()),
                style: TextStyle(fontSize: 12, color: DS.textSecondary),
              ),
              const SizedBox(width: DS.spacing16),
              Icon(Icons.lightbulb_outline, size: 14, color: DS.warning),
              const SizedBox(width: 4),
              Text(
                l10n.capsuleCuriosityPercent(
                  (job.curiosityPreference * 100).toInt(),
                ),
                style: TextStyle(fontSize: 12, color: DS.textSecondary),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),

          // 数量信息
          Row(
            children: [
              Text(
                l10n.capsuleRequestedCount(job.requestedCount),
                style: TextStyle(fontSize: 12, color: DS.textSecondary),
              ),
              const SizedBox(width: DS.spacing16),
              if (job.actualCount != null)
                Text(
                  l10n.capsuleActualCount(job.actualCount!),
                  style: TextStyle(
                    fontSize: 12,
                    color: job.isCompleted ? DS.success : DS.textSecondary,
                  ),
                ),
            ],
          ),

          // 错误信息 (仅失败时显示)
          if (job.isFailed && job.errorMessage != null) ...[
            const SizedBox(height: DS.spacing12),
            Container(
              padding: const EdgeInsets.all(DS.spacing12),
              decoration: BoxDecoration(
                color: DS.error.withValues(alpha: 0.1),
                borderRadius: DS.borderRadius8,
                border: Border.all(color: DS.error.withValues(alpha: 0.3)),
              ),
              child: Row(
                children: [
                  Icon(Icons.error_outline, size: 16, color: DS.error),
                  const SizedBox(width: DS.sm),
                  Expanded(
                    child: Text(
                      job.errorMessage!,
                      style: TextStyle(fontSize: 12, color: DS.error),
                    ),
                  ),
                ],
              ),
            ),
          ],

          // 完成后的胶囊链接
          if (job.isCompleted &&
              job.capsuleIds != null &&
              job.capsuleIds!.isNotEmpty) ...[
            const SizedBox(height: DS.spacing12),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: job.capsuleIds!
                  .map(
                    (id) => RawChip(
                      label: Text(l10n.capsuleChipLabel(id)),
                      avatar: const Icon(Icons.check_circle_outline, size: 16),
                      backgroundColor: isDark ? DS.neutral700 : DS.neutral200,
                      onPressed: () => Navigator.of(context).push(
                        MaterialPageRoute<void>(
                          builder: (_) => CapsuleDetailScreen(capsuleId: id),
                        ),
                      ),
                    ),
                  )
                  .toList(),
            ),
          ],

          // 操作按钮
          const SizedBox(height: DS.spacing12),
          Row(
            children: [
              if (job.isFailed)
                Expanded(
                  child: SparkleButton.outline(
                    label: l10n.commonRetry,
                    onPressed: () => ref
                        .read(generationJobsProvider.notifier)
                        .requestBatchGeneration(
                          depthPreference: job.depthPreference,
                          curiosityPreference: job.curiosityPreference,
                          requestedCount: job.requestedCount,
                        ),
                    icon: const Icon(Icons.refresh),
                  ),
                ),
              if (job.isFailed) const SizedBox(width: DS.spacing8),
              if (job.isCompleted &&
                  job.capsuleIds != null &&
                  job.capsuleIds!.isNotEmpty)
                Expanded(
                  child: SparkleButton.primary(
                    label: l10n.capsuleViewCapsules,
                    onPressed: () => context.push('/curiosity-capsule'),
                    icon: const Icon(Icons.visibility),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }

  Color _getStatusColor() {
    switch (job.statusEnum) {
      case JobStatus.pending:
        return DS.textSecondary;
      case JobStatus.generating:
        return DS.info;
      case JobStatus.completed:
        return DS.success;
      case JobStatus.failed:
        return DS.error;
    }
  }

}
