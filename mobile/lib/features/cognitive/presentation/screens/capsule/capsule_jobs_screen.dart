import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/display/lexicon/error_lexicon.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/state/staged_loading.dart';
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
          // A11Y-BATCH6A：甲式单节点（semanticLabel 直挂按钮）。
          semanticLabel: l10n.back,
          onPressed: () => context.pop(),
          variant: ButtonVariant.ghost,
        ),
        title: Text(l10n.capsuleJobsTitle),
        actions: [
          SparkleIconButton(
            icon: const Icon(Icons.refresh),
            // A11Y-BATCH6A：甲式单节点（semanticLabel 直挂按钮）。
            semanticLabel: l10n.commonRefresh,
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
              : SparkleRefreshIndicator(
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
          // U-06 续：统一分阶等待——原字面量为无 locale 判定的纯中文串
          // （英文用户也看到中文），统一组件按 arb 出双语阶段文案。
          loading: () => const StagedSurfaceLoader(),
          error: (err, stack) => CustomErrorWidget.page(
            context: context,
            title: context.l10n.cogJobsLoadFailed,
            // 错误文案单源：类别人话（error_lexicon），不透传原始异常。
            message: uiErrorMessage(l10n, categorizeUiError(err)),
            onRetry: () =>
                ref.read(generationJobsProvider.notifier).fetchJobs(),
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
                  // V4-G03 四风格对比度复算：状态色 12sp 标签对 0.15 tint
                  // 合成底在 classic 两档仅 3.61–4.16:1（classic-dark 的
                  // success/error 对 tertiary 容器裸比也 <4.5）；标签改
                  // textPrimary（全档 ≥7.3:1），状态色由 emoji+描边承载，
                  // tint 0.06 保证色点/图标 ≥3:1 图形对比。
                  color: _getStatusColor().withValues(alpha: 0.06),
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
                        fontSize: DS.fontSizeXs,
                        fontWeight: DS.fontWeightSemibold,
                        color: DS.textPrimary,
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
                  // V4-G03：dark 侧 neutral700 是浅灰，对 textSecondary/textPrimary
                  // 均 <2.5:1（dusk 1.61 实测口径）；dark 侧换 surfaceTertiary，
                  // 标签 textPrimary（全档 ≥8:1）。
                  color: isDark ? DS.surfaceTertiary : DS.neutral200,
                  borderRadius: DS.borderRadius8,
                ),
                child: Text(
                  job.generationTypeLabel,
                  style: TextStyle(
                    fontSize: DS.fontSizeXs,
                    color: DS.textPrimary,
                  ),
                ),
              ),
              const Spacer(),
              Text(
                Formatters.formatRelativeTime(job.createdAt),
                style: TextStyle(fontSize: DS.fontSizeXs, color: DS.textSecondary),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing12),

          // 进度条 (仅在生成中时显示)
          if (job.isGenerating) ...[
            LinearProgressIndicator(
              value: job.progress,
              // V4-G03：dark 侧轨道 neutral700（浅灰）对 brandPrimary 填充
              // 仅 1.68–1.86:1（进度条非文字部件需 ≥3:1）；换 surfaceTertiary
              // 后全档 ≥3.4:1。
              backgroundColor: isDark ? DS.surfaceTertiary : DS.neutral200,
              valueColor: AlwaysStoppedAnimation<Color>(DS.primaryBase),
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              l10n.capsuleGeneratingProgress(job.progressPercent),
              style: TextStyle(fontSize: DS.fontSizeXs, color: DS.textSecondary),
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
                style: TextStyle(fontSize: DS.fontSizeXs, color: DS.textSecondary),
              ),
              const SizedBox(width: DS.spacing16),
              Icon(Icons.lightbulb_outline, size: 14, color: DS.warning),
              const SizedBox(width: 4),
              Text(
                l10n.capsuleCuriosityPercent(
                  (job.curiosityPreference * 100).toInt(),
                ),
                style: TextStyle(fontSize: DS.fontSizeXs, color: DS.textSecondary),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),

          // 数量信息
          Row(
            children: [
              Text(
                l10n.capsuleRequestedCount(job.requestedCount),
                style: TextStyle(fontSize: DS.fontSizeXs, color: DS.textSecondary),
              ),
              const SizedBox(width: DS.spacing16),
              if (job.actualCount != null)
                Text(
                  l10n.capsuleActualCount(job.actualCount!),
                  // V4-G03：success 12sp 在 classic-dark tertiary 容器上裸比
                  // <4.5:1；数量强调改 textPrimary（全档 ≥9:1），完成态由
                  // 状态徽章与胶囊 chips 承载。
                  style: TextStyle(
                    fontSize: DS.fontSizeXs,
                    color: job.isCompleted ? DS.textPrimary : DS.textSecondary,
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
                // V4-G03：错误正文是关键文本——DS.error 12sp 对 0.1 tint
                // 合成底在 classic-dark 仅 3.6:1；正文改 textPrimary，
                // error 色保留在图标（≥3:1 图形对比）与描边。
                color: DS.error.withValues(alpha: 0.06),
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
                      style: TextStyle(fontSize: DS.fontSizeXs, color: DS.textPrimary),
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
                      label: Text(
                        l10n.capsuleChipLabel(id),
                        // V4-G03：dark 侧 neutral700 浅灰底 + 默认浅墨标签
                        // 对比不足；显式 textPrimary 并把 dark 底换
                        // surfaceTertiary（同 generationType chip 口径）。
                        style: TextStyle(fontSize: DS.fontSizeXs, color: DS.textPrimary),
                      ),
                      avatar: const Icon(Icons.check_circle_outline, size: 16),
                      backgroundColor:
                          isDark ? DS.surfaceTertiary : DS.neutral200,
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
