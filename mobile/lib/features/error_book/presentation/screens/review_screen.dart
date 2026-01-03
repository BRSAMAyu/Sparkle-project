import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/error_book/presentation/widgets/error_card.dart';
import 'package:sparkle/features/error_book/presentation/widgets/subject_chips.dart';
import 'package:sparkle/features/error_book/presentation/widgets/analysis_card.dart';
import 'package:sparkle/features/error_book/presentation/widgets/review_performance_buttons.dart';
import 'package:sparkle/features/error_book/data/providers/error_book_provider.dart';
import 'package:sparkle/features/error_book/data/models/error_record.dart';

/// 复习模式枚举
enum ReviewMode {
  today('today', '今日复习', '完成今天到期的所有错题'),
  bySubject('subject', '按科目', '选择一个科目进行专项复习'),
  weakest('weakest', '薄弱专攻', '优先复习掌握度最低的错题'),
  random('random', '随机抽查', '随机抽取错题进行复习');

  const ReviewMode(this.code, this.label, this.description);

  final String code;
  final String label;
  final String description;
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
  final Map<String, String> _reviewResults = {}; // errorId -> performance (remembered/fuzzy/forgotten)
  bool _isSubmitting = false;

  @override
  Widget build(BuildContext context) {
    final reviewListAsync = ref.watch(todayReviewListProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.mode.label),
        actions: [
          IconButton(
            icon: const Icon(Icons.close),
            tooltip: '退出复习',
            onPressed: () => _confirmExit(context),
          ),
        ],
      ),
      body: reviewListAsync.when(
        data: (errors) {
          if (errors.isEmpty) {
            return _buildEmptyState(context);
          }

          // 根据模式筛选错题
          final filteredErrors = _filterErrors(errors);

          if (filteredErrors.isEmpty) {
            return _buildEmptyState(context, customMessage: '没有符合条件的错题');
          }

          // 复习完成
          if (_currentIndex >= filteredErrors.length) {
            return _buildCompletionState(context, filteredErrors);
          }

          final currentError = filteredErrors[_currentIndex];

          return Column(
            children: [
              // 进度条
              _buildProgressBar(context, _currentIndex, filteredErrors.length),

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
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
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
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '进度: $current/$total',
                style: theme.textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
              Text(
                '${(progress * 100).toInt()}%',
                style: theme.textTheme.titleSmall?.copyWith(
                  color: theme.colorScheme.primary,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
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
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // 科目和章节
          Row(
            children: [
              SubjectChip(subjectCode: error.subject),
              if (error.chapter != null) ...[
                const SizedBox(width: 8),
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
              color: theme.colorScheme.surfaceContainerHighest.withOpacity(0.3),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: theme.colorScheme.outline.withOpacity(0.2),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '题目',
                  style: theme.textTheme.labelLarge?.copyWith(
                    color: theme.colorScheme.primary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 12),
                SelectableText(
                  error.questionText,
                  style: theme.textTheme.bodyLarge?.copyWith(
                    height: 1.6,
                    fontSize: 16,
                  ),
                ),
                if (error.questionImageUrl != null) ...[
                  const SizedBox(height: 16),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: Image.network(
                      error.questionImageUrl!,
                      fit: BoxFit.cover,
                    ),
                  ),
                ],
              ],
            ),
          ),

          // 显示答案和分析
          if (_showAnswer) ...[
            const SizedBox(height: 16),
            _buildAnswerSection(context, error),

            if (_showAnalysis && error.latestAnalysis != null) ...[
              const SizedBox(height: 16),
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
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: theme.colorScheme.errorContainer.withOpacity(0.3),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: theme.colorScheme.error.withOpacity(0.3),
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
                    '你的答案',
                    style: theme.textTheme.titleSmall?.copyWith(
                      color: theme.colorScheme.error,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              SelectableText(
                error.userAnswer,
                style: theme.textTheme.bodyMedium,
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),

        // 正确答案
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.green.withOpacity(0.1),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: Colors.green.withOpacity(0.3),
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(
                    Icons.check_circle,
                    size: 18,
                    color: Colors.green,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    '正确答案',
                    style: theme.textTheme.titleSmall?.copyWith(
                      color: Colors.green,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
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

  Widget _buildAnalysisSection(BuildContext context, ErrorRecord error) => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'AI 分析',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
            ),
            TextButton.icon(
              onPressed: () {
                setState(() {
                  _showAnalysis = false;
                });
              },
              icon: const Icon(Icons.visibility_off, size: 16),
              label: const Text('隐藏'),
            ),
          ],
        ),
        const SizedBox(height: 8),
        AnalysisCard(analysis: error.latestAnalysis!),
      ],
    );

  Widget _buildRevealButton(BuildContext context) => SafeArea(
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.05),
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
              label: const Text('查看答案'),
              style: FilledButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
                minimumSize: const Size(double.infinity, 0),
                textStyle: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              '先思考答案，再点击查看',
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
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: theme.colorScheme.surface,
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.05),
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
                label: const Text('查看 AI 分析'),
              ),
            if (_showAnalysis) const SizedBox(height: 12),

            // 评价按钮
            ReviewPerformanceButtons(
              onPerformanceSelected: (performance) => _handleReview(context, error, performance),
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
          );

      // 记录结果
      _reviewResults[error.id] = performance;

      // 重置状态并移动到下一题
      setState(() {
        _currentIndex++;
        _showAnswer = false;
        _showAnalysis = false;
        _isSubmitting = false;
      });
    } catch (e) {
      setState(() {
        _isSubmitting = false;
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('提交失败: ${e}'),
            backgroundColor: Colors.red,
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    }
  }

  Widget _buildEmptyState(BuildContext context, {String? customMessage}) => Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.check_circle_outline,
            size: 80,
            color: Colors.green.shade300,
          ),
          const SizedBox(height: 16),
          Text(
            customMessage ?? '暂无需要复习的错题',
            style: const TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w500,
              color: Colors.grey,
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            '做得很好！继续保持',
            style: TextStyle(
              fontSize: 14,
              color: Colors.grey,
            ),
          ),
          const SizedBox(height: 24),
          FilledButton.icon(
            onPressed: () => Navigator.of(context).pop(),
            icon: const Icon(Icons.arrow_back),
            label: const Text('返回'),
          ),
        ],
      ),
    );

  Widget _buildCompletionState(BuildContext context, List<ErrorRecord> errors) {
    final theme = Theme.of(context);
    final totalReviewed = _reviewResults.length;
    final remembered = _reviewResults.values.where((p) => p == 'remembered').length;
    final fuzzy = _reviewResults.values.where((p) => p == 'fuzzy').length;
    final forgotten = _reviewResults.values.where((p) => p == 'forgotten').length;

    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // 完成图标
            Container(
              width: 100,
              height: 100,
              decoration: BoxDecoration(
                color: Colors.green.withOpacity(0.1),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.celebration,
                size: 50,
                color: Colors.green,
              ),
            ),
            const SizedBox(height: 24),

            Text(
              '复习完成！',
              style: theme.textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              '本次共复习 $totalReviewed 道题',
              style: theme.textTheme.bodyLarge?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 32),

            // 统计卡片
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: theme.colorScheme.surfaceContainerHighest.withOpacity(0.5),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Column(
                children: [
                  Text(
                    '复习成果',
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 20),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      _buildStatColumn(
                        context,
                        '记住了',
                        remembered.toString(),
                        Colors.green,
                        Icons.check_circle,
                      ),
                      _buildStatColumn(
                        context,
                        '模糊',
                        fuzzy.toString(),
                        Colors.orange,
                        Icons.help_outline,
                      ),
                      _buildStatColumn(
                        context,
                        '忘记了',
                        forgotten.toString(),
                        Colors.red,
                        Icons.cancel_outlined,
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 32),

            // 鼓励语
            Text(
              _getEncouragementText(remembered, totalReviewed),
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.primary,
                fontStyle: FontStyle.italic,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 32),

            // 操作按钮
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => Navigator.of(context).pop(),
                    icon: const Icon(Icons.arrow_back),
                    label: const Text('返回列表'),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 16),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: FilledButton.icon(
                    onPressed: () {
                      // 重置状态，重新开始
                      setState(() {
                        _currentIndex = 0;
                        _showAnswer = false;
                        _showAnalysis = false;
                        _reviewResults.clear();
                      });
                      ref.invalidate(todayReviewListProvider);
                    },
                    icon: const Icon(Icons.replay),
                    label: const Text('再来一轮'),
                    style: FilledButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 16),
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
        const SizedBox(height: 8),
        Text(
          value,
          style: theme.textTheme.headlineMedium?.copyWith(
            color: color,
            fontWeight: FontWeight.bold,
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

  String _getEncouragementText(int remembered, int total) {
    if (total == 0) return '继续加油！';

    final ratio = remembered / total;
    if (ratio >= 0.9) {
      return '太棒了！掌握得非常扎实 🎉';
    } else if (ratio >= 0.7) {
      return '很好！继续保持这个势头 💪';
    } else if (ratio >= 0.5) {
      return '不错！再多复习几次会更好 📚';
    } else {
      return '加油！多复习几次就能记住了 🌟';
    }
  }

  Widget _buildErrorState(BuildContext context, String error) => Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(
            Icons.error_outline,
            size: 80,
            color: Colors.red,
          ),
          const SizedBox(height: 16),
          const Text(
            '加载失败',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            error,
            style: const TextStyle(
              fontSize: 14,
              color: Colors.grey,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
          FilledButton.icon(
            onPressed: () {
              ref.invalidate(todayReviewListProvider);
            },
            icon: const Icon(Icons.refresh),
            label: const Text('重试'),
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
        title: const Text('确认退出'),
        content: const Text('复习还未完成，确定要退出吗？'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('继续复习'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('退出'),
          ),
        ],
      ),
    );

    if ((confirmed ?? false) && context.mounted) {
      Navigator.of(context).pop();
    }
  }
}
