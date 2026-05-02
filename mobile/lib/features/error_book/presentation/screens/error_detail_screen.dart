import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/utils/formatters.dart';
import 'package:sparkle/features/error_book/data/models/error_record.dart';
import 'package:sparkle/features/error_book/data/models/error_semantic_summary.dart';
import 'package:sparkle/features/error_book/data/providers/error_book_provider.dart';
import 'package:sparkle/features/error_book/presentation/widgets/analysis_card.dart';
import 'package:sparkle/features/error_book/presentation/widgets/error_question_image.dart';
import 'package:sparkle/features/error_book/presentation/widgets/subject_chips.dart';

/// 错题详情页面
///
/// 设计原则：
/// 1. 信息完整：展示题目、答案、分析、关联知识点、复习记录
/// 2. 操作便捷：编辑、删除、重新分析、开始复习
/// 3. 视觉清晰：分段展示，关键信息突出
class ErrorDetailScreen extends ConsumerWidget {
  const ErrorDetailScreen({
    required this.errorId,
    super.key,
  });
  final String errorId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final errorAsync = ref.watch(errorDetailProvider(errorId));

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: Text(l10n.errorBookDetailTitle),
        actions: [
          // 编辑按钮
          errorAsync.whenOrNull(
                data: (error) => Tooltip(
                  message: l10n.errorBookEdit,
                  child: SparkleIconButton(
                    variant: ButtonVariant.ghost,
                    icon: const Icon(Icons.edit_outlined),
                    onPressed: () => _navigateToEdit(context, error),
                  ),
                ),
              ) ??
              const SizedBox.shrink(),
          // 更多操作
          errorAsync.whenOrNull(
                data: (error) => PopupMenuButton<String>(
                  icon: const Icon(Icons.more_vert),
                  onSelected: (value) {
                    switch (value) {
                      case 'reanalyze':
                        unawaited(_reanalyze(context, ref, error));
                      case 'delete':
                        unawaited(_confirmDelete(context, ref, error));
                    }
                  },
                  itemBuilder: (context) => [
                    PopupMenuItem(
                      value: 'reanalyze',
                      child: Row(
                        children: [
                          const Icon(Icons.psychology_outlined),
                          const SizedBox(width: DS.spacing12),
                          Text(l10n.errorBookReanalyze),
                        ],
                      ),
                    ),
                    PopupMenuItem(
                      value: 'delete',
                      child: Row(
                        children: [
                          Icon(Icons.delete_outline, color: DS.error),
                          const SizedBox(width: DS.spacing12),
                          Text(
                            l10n.errorBookDelete,
                            style: TextStyle(color: DS.error),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ) ??
              const SizedBox.shrink(),
        ],
      ),
      bottomNavigationBar: errorAsync.whenOrNull(
        data: (error) => _buildBottomBar(context, ref, error),
      ),
      child: errorAsync.when(
        data: (error) => _buildDetailContent(context, ref, error),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) =>
            _buildErrorState(context, ref, error.toString()),
      ),
    );
  }

  Widget _buildDetailContent(
    BuildContext context,
    WidgetRef ref,
    ErrorRecord error,
  ) =>
      ContentConstraint(
        child: SingleChildScrollView(
          padding: const EdgeInsets.only(bottom: 80),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 科目和元数据
              _buildMetadataSection(context, error),

              const Divider(height: 1),

              // 题目内容
              _buildQuestionSection(context, error),

              const Divider(height: 1),

              // 答案对比
              _buildAnswerSection(context, error),

              const Divider(height: 1),

              // AI 分析
              if (error.latestAnalysis != null) ...[
                _buildAnalysisSection(context, error),
                const Divider(height: 1),
              ],

              // 同类错因语义摘要
              _buildSemanticSummarySection(
                context,
                ref.watch(errorSemanticSummaryProvider(error.id)),
              ),

              // 关联知识点
              if (error.knowledgeLinks.isNotEmpty) ...[
                _buildKnowledgeSection(context, error),
                const Divider(height: 1),
              ],

              // 复习统计
              _buildReviewStatsSection(context, error),
            ],
          ),
        ),
      );

  Widget _buildMetadataSection(BuildContext context, ErrorRecord error) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 科目徽章
          Row(
            children: [
              SubjectChip(subjectCode: error.subject),
              if (error.chapter != null) ...[
                const SizedBox(width: DS.spacing8),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.spacing10,
                    vertical: DS.spacing4,
                  ),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.surfaceContainerHighest,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.folder_outlined,
                        size: 14,
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        error.chapter!,
                        style: theme.textTheme.labelMedium?.copyWith(
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
              const Spacer(),
              // 掌握度
              _buildMasteryBadge(context, theme, error.masteryLevel),
            ],
          ),
          const SizedBox(height: DS.spacing12),

          // 创建时间
          Row(
            children: [
              Icon(
                Icons.access_time,
                size: 14,
                color: theme.colorScheme.onSurfaceVariant,
              ),
              const SizedBox(width: 4),
              Text(
                context.l10n
                    .errorBookCreatedAt(_formatDateTime(error.createdAt)),
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildMasteryBadge(
    BuildContext context,
    ThemeData theme,
    double mastery,
  ) {
    final color = mastery >= 0.8
        ? DS.success
        : mastery >= 0.5
            ? DS.warningLight
            : DS.error;

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing12,
        vertical: DS.spacing6,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            mastery >= 0.8
                ? Icons.star
                : mastery >= 0.5
                    ? Icons.star_half
                    : Icons.star_outline,
            size: 16,
            color: color,
          ),
          const SizedBox(width: 4),
          Text(
            context.l10n.errorBookMasteryPercent(
              (mastery * 100).toInt(),
            ),
            style: theme.textTheme.labelMedium?.copyWith(
              color: color,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSemanticSummarySection(
    BuildContext context,
    AsyncValue<ErrorSemanticSummary> summaryAsync,
  ) =>
      summaryAsync.when(
        loading: () => const SizedBox.shrink(),
        error: (_, __) => const SizedBox.shrink(),
        data: (summary) {
          final hasContent = (summary.rootCause?.isNotEmpty ?? false) ||
              summary.strategies.isNotEmpty ||
              summary.similarErrors.isNotEmpty;
          if (!hasContent) {
            return const SizedBox.shrink();
          }

          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildSectionHeader(
                context,
                context.l10n.errorBookSimilarSummary,
              ),
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing16,
                  vertical: DS.spacing12,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (summary.rootCause != null &&
                        summary.rootCause!.isNotEmpty) ...[
                      _buildLabeledText(
                        context,
                        label: context.l10n.errorBookRootCause,
                        value: summary.rootCause!,
                      ),
                      const SizedBox(height: DS.spacing12),
                    ],
                    if (summary.strategies.isNotEmpty) ...[
                      _buildSectionSubtitle(
                        context,
                        context.l10n.errorBookStrategySuggestions,
                      ),
                      const SizedBox(height: DS.spacing8),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: summary.strategies
                            .map(
                              (strategy) =>
                                  _buildTagChip(context, strategy.title),
                            )
                            .toList(),
                      ),
                      const SizedBox(height: DS.spacing12),
                    ],
                    if (summary.similarErrors.isNotEmpty) ...[
                      _buildSectionSubtitle(
                        context,
                        context.l10n.errorBookSimilarErrors,
                      ),
                      const SizedBox(height: DS.spacing8),
                      ...summary.similarErrors.map(
                        (item) => _buildBulletText(
                          context,
                          '${item.subjectCode} • ${item.rootCause ?? context.l10n.errorBookSimilarCauseFallback}',
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              const Divider(height: 1),
            ],
          );
        },
      );

  Widget _buildSectionHeader(BuildContext context, String title) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        DS.spacing16,
        DS.spacing12,
        DS.spacing16,
        DS.spacing4,
      ),
      child: Text(
        title,
        style:
            theme.textTheme.titleMedium?.copyWith(fontWeight: DS.fontWeightBold),
      ),
    );
  }

  Widget _buildSectionSubtitle(BuildContext context, String title) {
    final theme = Theme.of(context);
    return Text(
      title,
      style: theme.textTheme.bodyMedium?.copyWith(
        fontWeight: DS.fontWeightSemibold,
        color: theme.colorScheme.onSurface,
      ),
    );
  }

  Widget _buildLabeledText(
    BuildContext context, {
    required String label,
    required String value,
  }) {
    final theme = Theme.of(context);
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '$label：',
          style: theme.textTheme.bodyMedium?.copyWith(
            fontWeight: DS.fontWeightSemibold,
            color: theme.colorScheme.onSurface,
          ),
        ),
        Expanded(
          child: Text(
            value,
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildTagChip(BuildContext context, String text) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing10,
        vertical: DS.spacing6,
      ),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        text,
        style: theme.textTheme.labelMedium?.copyWith(
          color: theme.colorScheme.onSurfaceVariant,
        ),
      ),
    );
  }

  Widget _buildBulletText(BuildContext context, String text) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: DS.spacing6),
      child: Row(
        children: [
          Icon(
            Icons.arrow_right_rounded,
            size: 16,
            color: theme.colorScheme.onSurfaceVariant,
          ),
          const SizedBox(width: 4),
          Expanded(
            child: Text(
              text,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildQuestionSection(BuildContext context, ErrorRecord error) {
    final theme = Theme.of(context);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.errorBookQuestionContent,
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
          const SizedBox(height: DS.spacing12),
          Container(
            padding: const EdgeInsets.all(DS.spacing16),
            decoration: BoxDecoration(
              color: theme.colorScheme.surfaceContainerHighest
                  .withValues(alpha: 0.5),
              borderRadius: BorderRadius.circular(12),
            ),
            child: SelectableText(
              error.questionText,
              style: theme.textTheme.bodyLarge?.copyWith(
                height: 1.6,
              ),
            ),
          ),
          if (error.questionImageUrl != null &&
              error.questionImageUrl!.trim().isNotEmpty) ...[
            const SizedBox(height: DS.spacing12),
            ErrorQuestionImage(
              imageReference: error.questionImageUrl!,
              height: 220,
              borderRadius: BorderRadius.circular(12),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildAnswerSection(BuildContext context, ErrorRecord error) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.errorBookAnswerComparison,
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
          const SizedBox(height: DS.spacing16),

          // 你的答案
          _buildAnswerCard(
            context: context,
            label: context.l10n.errorBookYourAnswer,
            content: error.userAnswer,
            icon: Icons.edit_outlined,
            color: theme.colorScheme.error,
            isCorrect: false,
          ),
          const SizedBox(height: DS.spacing12),

          // 正确答案
          _buildAnswerCard(
            context: context,
            label: context.l10n.errorBookCorrectAnswer,
            content: error.correctAnswer,
            icon: Icons.check_circle_outline,
            color: DS.success,
            isCorrect: true,
          ),
        ],
      ),
    );
  }

  Widget _buildAnswerCard({
    required BuildContext context,
    required String label,
    required String content,
    required IconData icon,
    required Color color,
    required bool isCorrect,
  }) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: color.withValues(alpha: 0.2),
          width: 1.5,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 18, color: color),
              const SizedBox(width: 6),
              Text(
                label,
                style: theme.textTheme.titleSmall?.copyWith(
                  color: color,
                  fontWeight: DS.fontWeightSemibold,
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing12),
          SelectableText(
            content,
            style: theme.textTheme.bodyMedium?.copyWith(
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAnalysisSection(BuildContext context, ErrorRecord error) =>
      Padding(
        padding: const EdgeInsets.all(DS.spacing16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.psychology,
                  size: 20,
                  color: Theme.of(context).colorScheme.primary,
                ),
                const SizedBox(width: DS.spacing8),
                Text(
                  context.l10n.errorBookAiAnalysis,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: DS.fontWeightSemibold,
                      ),
                ),
                const Spacer(),
                if (error.latestAnalysis?.analyzedAt != null)
                  Text(
                    _formatDateTime(error.latestAnalysis!.analyzedAt!),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                  ),
              ],
            ),
            const SizedBox(height: DS.spacing16),
            AnalysisCard(analysis: error.latestAnalysis!),
          ],
        ),
      );

  Widget _buildKnowledgeSection(BuildContext context, ErrorRecord error) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.auto_graph,
                size: 20,
                color: theme.colorScheme.primary,
              ),
              const SizedBox(width: DS.spacing8),
              Text(
                context.l10n.errorBookKnowledgeLinks,
                style: theme.textTheme.titleMedium?.copyWith(
                  fontWeight: DS.fontWeightSemibold,
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: error.knowledgeLinks
                .map(
                  (link) => ActionChip(
                    avatar: const Icon(Icons.timeline, size: 16),
                    label: Text(link.nodeName),
                    tooltip: context.l10n.errorBookKnowledgeLinkTooltip,
                    onPressed: () =>
                        context.push('/galaxy/node/${link.nodeId}'),
                  ),
                )
                .toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildReviewStatsSection(BuildContext context, ErrorRecord error) {
    final theme = Theme.of(context);
    final isMobile = context.isMobile;

    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.errorBookReviewStats,
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
          const SizedBox(height: DS.spacing16),
          if (isMobile)
            Column(
              children: [
                _buildStatCard(
                  context: context,
                  label: context.l10n.errorBookReviewCount(error.reviewCount),
                  value: error.reviewCount.toString(),
                  icon: Icons.repeat,
                  color: DS.info,
                ),
                const SizedBox(height: DS.spacing12),
                _buildStatCard(
                  context: context,
                  label: context.l10n.masteryScore,
                  value: '${(error.masteryLevel * 100).toInt()}%',
                  icon: Icons.trending_up,
                  color: error.masteryLevel >= 0.8
                      ? DS.success
                      : error.masteryLevel >= 0.5
                          ? DS.warningLight
                          : DS.error,
                ),
              ],
            )
          else
            Row(
              children: [
                Expanded(
                  child: _buildStatCard(
                    context: context,
                    label: context.l10n.errorBookReviewCount(error.reviewCount),
                    value: error.reviewCount.toString(),
                    icon: Icons.repeat,
                    color: DS.info,
                  ),
                ),
                const SizedBox(width: DS.spacing12),
                Expanded(
                  child: _buildStatCard(
                    context: context,
                    label: context.l10n.masteryScore,
                    value: '${(error.masteryLevel * 100).toInt()}%',
                    icon: Icons.trending_up,
                    color: error.masteryLevel >= 0.8
                        ? DS.success
                        : error.masteryLevel >= 0.5
                            ? DS.warningLight
                            : DS.error,
                  ),
                ),
              ],
            ),
          const SizedBox(height: DS.spacing12),
          if (error.lastReviewedAt != null)
            _buildInfoRow(
              context,
              context.l10n.errorBookLastReview,
              _formatDateTime(error.lastReviewedAt!),
              Icons.history,
            ),
          if (error.nextReviewAt != null) ...[
            const SizedBox(height: DS.spacing8),
            _buildInfoRow(
              context,
              context.l10n.errorBookNextReview,
              _formatDateTime(error.nextReviewAt!),
              Icons.event,
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildStatCard({
    required BuildContext context,
    required String label,
    required String value,
    required IconData icon,
    required Color color,
  }) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: color.withValues(alpha: 0.3),
        ),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 28),
          const SizedBox(height: DS.spacing8),
          Text(
            value,
            style: theme.textTheme.headlineSmall?.copyWith(
              color: color,
              fontWeight: DS.fontWeightBold,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoRow(
    BuildContext context,
    String label,
    String value,
    IconData icon,
  ) {
    final theme = Theme.of(context);

    return Row(
      children: [
        Icon(
          icon,
          size: 16,
          color: theme.colorScheme.onSurfaceVariant,
        ),
        const SizedBox(width: DS.spacing8),
        Text(
          '$label: ',
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
        Text(
          value,
          style: theme.textTheme.bodyMedium?.copyWith(
            fontWeight: DS.fontWeightMedium,
          ),
        ),
      ],
    );
  }

  Widget _buildBottomBar(
    BuildContext context,
    WidgetRef ref,
    ErrorRecord error,
  ) =>
      SafeArea(
        child: Container(
          padding: const EdgeInsets.all(DS.spacing16),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            boxShadow: [
              BoxShadow(
                color: DS.textPrimary.withValues(alpha: 0.05),
                blurRadius: 10,
                offset: const Offset(0, -2),
              ),
            ],
          ),
          child: FilledButton.icon(
            onPressed: () => _startReview(context, ref, error),
            icon: const Icon(Icons.play_circle_outline),
            label: Text(context.l10n.errorBookStartReview),
            style: FilledButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 16),
              textStyle: const TextStyle(
                fontSize: 16,
                fontWeight: DS.fontWeightSemibold,
              ),
            ),
          ),
        ),
      );

  Widget _buildErrorState(BuildContext context, WidgetRef ref, String error) =>
      Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 80,
              color: DS.error,
            ),
            const SizedBox(height: DS.spacing16),
            Text(
              context.l10n.errorBookLoadFailed,
              style: const TextStyle(
                fontSize: 18,
                fontWeight: DS.fontWeightMedium,
              ),
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              error,
              style: TextStyle(
                fontSize: 14,
                color: DS.textSecondary,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: DS.spacing24),
            FilledButton.icon(
              onPressed: () {
                ref.invalidate(errorDetailProvider(errorId));
              },
              icon: const Icon(Icons.refresh),
              label: Text(context.l10n.retry),
            ),
          ],
        ),
      );

  String _formatDateTime(DateTime dateTime) {
    final now = DateTime.now();
    final diffDays = now.difference(dateTime).inDays.abs();
    if (diffDays < 7) {
      return Formatters.formatRelativeTime(dateTime);
    }
    return Formatters.formatDateShort(dateTime);
  }

  void _navigateToEdit(BuildContext context, ErrorRecord error) {
    unawaited(
      context.push<bool>(
        '/errors/${error.id}/edit',
        extra: error,
      ),
    );
  }

  Future<void> _reanalyze(
    BuildContext context,
    WidgetRef ref,
    ErrorRecord error,
  ) async {
    unawaited(ref.read(errorOperationsProvider.notifier).reAnalyze(error.id));
    ScaffoldMessenger.of(context).showSnackBar(
      SparkleSnackBar.info(
        context.l10n.errorBookReanalyzing,
        duration: const Duration(seconds: 2),
      ),
    );
  }

  Future<void> _confirmDelete(
    BuildContext context,
    WidgetRef ref,
    ErrorRecord error,
  ) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(context.l10n.errorBookDeleteConfirmTitle),
        content: Text(context.l10n.errorBookDeleteConfirmMessage),
        actions: [
          SparkleButton.ghost(
            onPressed: () => Navigator.of(context).pop(false),
            label: context.l10n.cancel,
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: FilledButton.styleFrom(
              backgroundColor: DS.error,
            ),
            child: Text(context.l10n.delete),
          ),
        ],
      ),
    );

    if ((confirmed ?? false) && context.mounted) {
      try {
        await ref.read(errorOperationsProvider.notifier).deleteError(error.id);

        if (context.mounted) {
          Navigator.of(context).pop(true); // 返回列表页
          ScaffoldMessenger.of(context).showSnackBar(
            SparkleSnackBar.success(context.l10n.errorBookDeleteSuccess),
          );
        }
      } catch (e) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SparkleSnackBar.error(
              context.l10n.errorBookDeleteFailedMessage(e.toString()),
            ),
          );
        }
      }
    }
  }

  void _startReview(
    BuildContext context,
    WidgetRef ref,
    ErrorRecord error,
  ) {
    unawaited(
      context.push(
        Uri(
          path: '/review',
          queryParameters: {
            'mode': 'today',
            if (error.subject.trim().isNotEmpty) 'subject': error.subject,
          },
        ).toString(),
      ),
    );
  }
}
