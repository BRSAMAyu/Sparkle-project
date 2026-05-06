import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/features/error_book/data/models/error_record.dart';
import 'package:sparkle/features/error_book/data/providers/error_book_provider.dart';
import 'package:sparkle/features/error_book/presentation/widgets/analysis_card.dart';
import 'package:sparkle/features/error_book/presentation/widgets/error_question_image.dart';
import 'package:sparkle/features/error_book/presentation/widgets/review_performance_buttons.dart';
import 'package:sparkle/features/error_book/presentation/widgets/subject_chips.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// 复习模式枚举
enum ReviewMode {
  today('today'),
  bySubject('subject'),
  weakest('weakest'),
  random('random');

  const ReviewMode(this.code);

  final String code;

  String label(AppLocalizations l10n) => switch (this) {
    ReviewMode.today => l10n.ebReviewModeToday,
    ReviewMode.bySubject => l10n.ebReviewModeSubject,
    ReviewMode.weakest => l10n.ebReviewModeWeak,
    ReviewMode.random => l10n.ebReviewModeRandom,
  };

  String description(AppLocalizations l10n) => switch (this) {
    ReviewMode.today => l10n.ebReviewModeTodayDesc,
    ReviewMode.bySubject => l10n.ebReviewModeSubjectDesc,
    ReviewMode.weakest => l10n.ebReviewModeWeakDesc,
    ReviewMode.random => l10n.ebReviewModeRandomDesc,
  };
}

/// 复习页面
///
/// 设计原则：
/// 1. 沉浸式体验：全屏卡片式，减少干扰
/// 2. 明确反馈：记住/模糊/忘记三档评价
/// 3. 进度可见：顶部进度条，底部统计
/// 4. 智能提示：显示 AI 分析，帮助理解
class ReviewScreen extends ConsumerStatefulWidget {
  const ReviewScreen({
    super.key,
    this.mode = ReviewMode.today,
    this.subjectCode,
  });
  final ReviewMode mode;
  final String? subjectCode;

  @override
  ConsumerState<ReviewScreen> createState() => _ReviewScreenState();
}

class _ReviewScreenState extends ConsumerState<ReviewScreen> {
  int _currentIndex = 0;
  bool _showAnswer = false;
  bool _showAnalysis = false;
  final Map<String, String> _reviewResults =
      {}; // errorId -> performance (remembered/fuzzy/forgotten)
  bool _isSubmitting = false;
  DateTime? _questionStartedAt;
  String? _trackedErrorId;

  void _ensureQuestionTracking(ErrorRecord error) {
    if (_trackedErrorId == error.id) {
      return;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      setState(() {
        _trackedErrorId = error.id;
        _questionStartedAt = DateTime.now();
      });
    });
  }

  int _currentQuestionTimeSpentSeconds() {
    final startedAt = _questionStartedAt;
    if (startedAt == null) {
      return 1;
    }
    return DateTime.now().difference(startedAt).inSeconds.clamp(1, 3600);
  }

  @override
  Widget build(BuildContext context) {
    final reviewListAsync = ref.watch(todayReviewListProvider);

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: Text(widget.mode.label(context.l10n)),
        actions: [
          Tooltip(
            message: context.l10n.ebExitReview,
            child: SparkleIconButton(
              variant: ButtonVariant.ghost,
              icon: const Icon(Icons.close),
              onPressed: () => _confirmExit(context),
            ),
          ),
        ],
      ),
      child: reviewListAsync.when(
        data: (errors) {
          if (errors.isEmpty) {
            return _buildEmptyState(context);
          }

          // 根据模式筛选错题
          final filteredErrors = _filterErrors(errors);

          if (filteredErrors.isEmpty) {
            return _buildEmptyState(context, customMessage: context.l10n.ebNoMatchingErrors);
          }

          // 复习完成
          if (_currentIndex >= filteredErrors.length) {
            return _buildCompletionState(context, filteredErrors);
          }

          final currentError = filteredErrors[_currentIndex];
          _ensureQuestionTracking(currentError);

          return ContentConstraint(
            child: Column(
              children: [
                // 进度条
                _buildProgressBar(
                  context,
                  _currentIndex,
                  filteredErrors.length,
                ),

                // 卡片内容
                Expanded(
                  child: _buildReviewCard(context, currentError),
                ),

                // 底部操作栏
                if (_showAnswer)
                  _buildActionBar(context, currentError, filteredErrors.length)
                else
                  _buildRevealButton(context),
              ],
            ),
          );
        },
        loading: () => const SparkleListSkeleton(),
        error: (error, stack) => _buildErrorState(context, error.toString()),
      ),
    );
  }

  List<ErrorRecord> _filterErrors(List<ErrorRecord> errors) {
    switch (widget.mode) {
      case ReviewMode.today:
        // 已由 provider 筛选
        return errors;
      case ReviewMode.bySubject:
        if (widget.subjectCode != null) {
          return errors.where((e) => e.subject == widget.subjectCode).toList();
        }
        return errors;
      case ReviewMode.weakest:
        // 按掌握度升序排序
        final sorted = List<ErrorRecord>.from(errors)
          ..sort((a, b) => a.masteryLevel.compareTo(b.masteryLevel));
        return sorted.take(10).toList(); // 取最薄弱的 10 题
      case ReviewMode.random:
        final shuffled = List<ErrorRecord>.from(errors)..shuffle();
        return shuffled.take(20).toList(); // 随机 20 题
    }
  }

  Widget _buildProgressBar(BuildContext context, int current, int total) {
    final theme = Theme.of(context);
    final progress = total > 0 ? (current / total) : 0.0;

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing16,
        vertical: DS.spacing12,
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                context.l10n.ebProgress(current, total),
                style: theme.textTheme.titleSmall?.copyWith(
                  fontWeight: DS.fontWeightSemibold,
                ),
              ),
              Text(
                '${(progress * 100).toInt()}%',
                style: theme.textTheme.titleSmall?.copyWith(
                  color: theme.colorScheme.primary,
                  fontWeight: DS.fontWeightSemibold,
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: progress,
              minHeight: 6,
              backgroundColor: theme.colorScheme.surfaceContainerHighest,
              valueColor: AlwaysStoppedAnimation<Color>(
                theme.colorScheme.primary,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildReviewCard(BuildContext context, ErrorRecord error) {
    final theme = Theme.of(context);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(DS.spacing16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // 科目和章节
          Row(
            children: [
              SubjectChip(subjectCode: error.subject),
              if (error.chapter != null) ...[
                const SizedBox(width: DS.spacing8),
                Chip(
                  label: Text(error.chapter!),
                  avatar: const Icon(Icons.folder_outlined, size: 16),
                  visualDensity: VisualDensity.compact,
                ),
              ],
            ],
          ),
          const SizedBox(height: 20),

          // 题目内容
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: theme.colorScheme.surfaceContainerHighest
                  .withValues(alpha: 0.3),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: theme.colorScheme.outline.withValues(alpha: 0.2),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  context.l10n.ebQuestion,
                  style: theme.textTheme.labelLarge?.copyWith(
                    color: theme.colorScheme.primary,
                    fontWeight: DS.fontWeightSemibold,
                  ),
                ),
                const SizedBox(height: DS.spacing12),
                SelectableText(
                  error.questionText,
                  style: theme.textTheme.bodyLarge?.copyWith(
                    height: 1.6,
                    fontSize: 16,
                  ),
                ),
                if (error.questionImageUrl != null &&
                    error.questionImageUrl!.trim().isNotEmpty) ...[
                  const SizedBox(height: DS.spacing16),
                  ErrorQuestionImage(
                    imageReference: error.questionImageUrl!,
                    height: 220,
                    borderRadius: BorderRadius.circular(12),
                  ),
                ],
              ],
            ),
          ),

          // 显示答案和分析
          if (_showAnswer) ...[
            const SizedBox(height: DS.spacing16),
            _buildAnswerSection(context, error),
            if (_showAnalysis && error.latestAnalysis != null) ...[
              const SizedBox(height: DS.spacing16),
              _buildAnalysisSection(context, error),
            ],
          ],
        ],
      ),
    );
  }

  Widget _buildAnswerSection(BuildContext context, ErrorRecord error) {
    final theme = Theme.of(context);

    return Column(
      children: [
        // 你的答案
        Container(
          padding: const EdgeInsets.all(DS.spacing16),
          decoration: BoxDecoration(
            color: theme.colorScheme.errorContainer.withValues(alpha: 0.3),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: theme.colorScheme.error.withValues(alpha: 0.3),
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    Icons.close,
                    size: 18,
                    color: theme.colorScheme.error,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    context.l10n.ebYourAnswer,
                    style: theme.textTheme.titleSmall?.copyWith(
                      color: theme.colorScheme.error,
                      fontWeight: DS.fontWeightSemibold,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: DS.spacing8),
              SelectableText(
                error.userAnswer,
                style: theme.textTheme.bodyMedium,
              ),
            ],
          ),
        ),
        const SizedBox(height: DS.spacing12),

        // 正确答案
        Container(
          padding: const EdgeInsets.all(DS.spacing16),
          decoration: BoxDecoration(
            color: DS.success.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: DS.success.withValues(alpha: 0.3),
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    Icons.check_circle,
                    size: 18,
                    color: DS.success,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    context.l10n.ebCorrectAnswer,
                    style: theme.textTheme.titleSmall?.copyWith(
                      color: DS.success,
                      fontWeight: DS.fontWeightSemibold,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: DS.spacing8),
              SelectableText(
                error.correctAnswer,
                style: theme.textTheme.bodyMedium,
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildAnalysisSection(BuildContext context, ErrorRecord error) =>
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                context.l10n.ebAiAnalysis,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: DS.fontWeightSemibold,
                    ),
              ),
              TextButton.icon(
                onPressed: () {
                  setState(() {
                    _showAnalysis = false;
                  });
                },
                icon: const Icon(Icons.visibility_off, size: 16),
                label: Text(context.l10n.ebHide),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          AnalysisCard(analysis: error.latestAnalysis!),
        ],
      );

  Widget _buildRevealButton(BuildContext context) => SafeArea(
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
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              FilledButton.icon(
                onPressed: () {
                  setState(() {
                    _showAnswer = true;
                  });
                },
                icon: const Icon(Icons.visibility),
                label: Text(context.l10n.ebViewAnswer),
                style: FilledButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: DS.spacing16),
                  minimumSize: const Size(double.infinity, 0),
                  textStyle: const TextStyle(
                    fontSize: 16,
                    fontWeight: DS.fontWeightSemibold,
                  ),
                ),
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                context.l10n.ebThinkFirstHint,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
              ),
            ],
          ),
        ),
      );

  Widget _buildActionBar(
    BuildContext context,
    ErrorRecord error,
    int totalCount,
  ) {
    final theme = Theme.of(context);

    return SafeArea(
      child: Container(
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          color: theme.colorScheme.surface,
          boxShadow: [
            BoxShadow(
              color: DS.textPrimary.withValues(alpha: 0.05),
              blurRadius: 10,
              offset: const Offset(0, -2),
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // AI 分析切换
            if (error.latestAnalysis != null && !_showAnalysis)
              TextButton.icon(
                onPressed: () {
                  setState(() {
                    _showAnalysis = true;
                  });
                },
                icon: const Icon(Icons.psychology_outlined, size: 18),
                label: Text(context.l10n.ebViewAnalysis),
              ),
            if (_showAnalysis) const SizedBox(height: DS.spacing12),

            // 评价按钮
            ReviewPerformanceButtons(
              onPerformanceSelected: (performance) =>
                  _handleReview(context, error, performance),
              isLoading: _isSubmitting,
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _handleReview(
    BuildContext context,
    ErrorRecord error,
    String performance,
  ) async {
    setState(() {
      _isSubmitting = true;
    });

    try {
      await ref.read(errorOperationsProvider.notifier).submitReview(
            errorId: error.id,
            performance: performance,
            timeSpentSeconds: _currentQuestionTimeSpentSeconds(),
          );

      if (!mounted) return;

      // 记录结果
      _reviewResults[error.id] = performance;

      // 重置状态并移动到下一题
      setState(() {
        _currentIndex++;
        _showAnswer = false;
        _showAnalysis = false;
        _isSubmitting = false;
        _questionStartedAt = null;
        _trackedErrorId = null;
      });
    } catch (e) {
      setState(() {
        _isSubmitting = false;
      });

      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SparkleSnackBar.error(context.l10n.ebReviewFailed),
      );
    }
  }

  Widget _buildEmptyState(BuildContext context, {String? customMessage}) =>
      Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.check_circle_outline,
              size: 80,
              color: DS.successLight,
            ),
            const SizedBox(height: DS.spacing16),
            Text(
              customMessage ?? context.l10n.ebNoReviewNeeded,
              style: TextStyle(
                fontSize: 18,
                fontWeight: DS.fontWeightMedium,
                color: DS.textSecondary,
              ),
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              context.l10n.ebNoReviewKeepUp,
              style: TextStyle(
                fontSize: 14,
                color: DS.textSecondary,
              ),
            ),
            const SizedBox(height: DS.spacing24),
            FilledButton.icon(
              onPressed: () => Navigator.of(context).pop(),
              icon: const Icon(Icons.arrow_back),
              label: Text(context.l10n.ebBack),
            ),
          ],
        ),
      );

  Widget _buildCompletionState(BuildContext context, List<ErrorRecord> errors) {
    final theme = Theme.of(context);
    final totalReviewed = _reviewResults.length;
    final remembered =
        _reviewResults.values.where((p) => p == 'remembered').length;
    final fuzzy = _reviewResults.values.where((p) => p == 'fuzzy').length;
    final forgotten =
        _reviewResults.values.where((p) => p == 'forgotten').length;

    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(DS.spacing24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // 完成图标
            Container(
              width: 100,
              height: 100,
              decoration: BoxDecoration(
                color: DS.success.withValues(alpha: 0.1),
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.celebration,
                size: 50,
                color: DS.success,
              ),
            ),
            const SizedBox(height: DS.spacing24),

            Text(
              context.l10n.ebReviewComplete,
              style: theme.textTheme.headlineSmall?.copyWith(
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              context.l10n.ebReviewSummary(totalReviewed),
              style: theme.textTheme.bodyLarge?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: DS.spacing32),

            // 统计卡片
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: theme.colorScheme.surfaceContainerHighest
                    .withValues(alpha: 0.5),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Column(
                children: [
                  Text(
                    context.l10n.ebReviewResults,
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: DS.fontWeightSemibold,
                    ),
                  ),
                  const SizedBox(height: 20),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      _buildStatColumn(
                        context,
                        context.l10n.ebStatusRemembered,
                        remembered.toString(),
                        DS.success,
                        Icons.check_circle,
                      ),
                      _buildStatColumn(
                        context,
                        context.l10n.ebStatusFuzzy,
                        fuzzy.toString(),
                        DS.warningLight,
                        Icons.help_outline,
                      ),
                      _buildStatColumn(
                        context,
                        context.l10n.ebStatusForgot,
                        forgotten.toString(),
                        DS.error,
                        Icons.cancel_outlined,
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: DS.spacing32),

            // 鼓励语
            Text(
              _getEncouragementText(context.l10n, remembered, totalReviewed),
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.primary,
                fontStyle: FontStyle.italic,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: DS.spacing32),

            // 操作按钮
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.arrow_back),
                    label: Text(context.l10n.ebBackToList),
                    style: OutlinedButton.styleFrom(
                      padding:
                          const EdgeInsets.symmetric(vertical: DS.spacing16),
                    ),
                  ),
                ),
                const SizedBox(width: DS.spacing12),
                Expanded(
                  child: FilledButton.icon(
                    onPressed: () {
                      // 重置状态，重新开始
                      setState(() {
                        _currentIndex = 0;
                        _showAnswer = false;
                        _showAnalysis = false;
                        _reviewResults.clear();
                        _questionStartedAt = null;
                        _trackedErrorId = null;
                      });
                      ref.invalidate(todayReviewListProvider);
                    },
                    icon: const Icon(Icons.replay),
                    label: Text(context.l10n.ebAnotherRound),
                    style: FilledButton.styleFrom(
                      padding:
                          const EdgeInsets.symmetric(vertical: DS.spacing16),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatColumn(
    BuildContext context,
    String label,
    String value,
    Color color,
    IconData icon,
  ) {
    final theme = Theme.of(context);

    return Column(
      children: [
        Icon(icon, color: color, size: 32),
        const SizedBox(height: DS.spacing8),
        Text(
          value,
          style: theme.textTheme.headlineMedium?.copyWith(
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
    );
  }

  String _getEncouragementText(AppLocalizations l10n, int remembered, int total) {
    if (total == 0) return l10n.ebEncourageKeepGoing;

    final ratio = remembered / total;
    if (ratio >= 0.9) {
      return l10n.ebEncourageExcellent;
    } else if (ratio >= 0.7) {
      return l10n.ebEncourageGreat;
    } else if (ratio >= 0.5) {
      return l10n.ebEncourageGood;
    } else {
      return l10n.ebEncourageTryAgain;
    }
  }

  Widget _buildErrorState(BuildContext context, String error) => Center(
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
              context.l10n.ebLoadReviewFailed,
              style: TextStyle(
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
                ref.invalidate(todayReviewListProvider);
              },
              icon: const Icon(Icons.refresh),
              label: Text(context.l10n.ebRetry),
            ),
          ],
        ),
      );

  Future<void> _confirmExit(BuildContext context) async {
    if (_reviewResults.isEmpty) {
      Navigator.of(context).pop();
      return;
    }

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(context.l10n.ebConfirmExit),
        content: Text(context.l10n.ebConfirmExitDesc),
        actions: [
          SparkleButton.ghost(
            onPressed: () => Navigator.of(context).pop(false),
            label: context.l10n.ebContinueReview,
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: Text(context.l10n.ebExit),
          ),
        ],
      ),
    );

    if ((confirmed ?? false) && context.mounted) {
      Navigator.of(context).pop();
    }
  }
}
