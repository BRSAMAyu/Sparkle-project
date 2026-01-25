// Content Review Card Widget - Phase 2b
//
// 显示AI生成内容的审查结果：
// - 审查评分展示
// - 指标细分（accuracy, completeness, relevance等）
// - 问题列表（按严重程度分类）
// - 改进建议
// - 反思状态指示
// - 用户交互按钮
//
// 作者: Claude Code (Opus 4.5)
// 创建时间: 2026-01-25

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/motion.dart';
import 'package:sparkle/core/design/widgets/custom_button.dart';

/// 内容审查决策类型
enum ContentReviewDecision {
  passed,
  failed,
  needsRefinement,
}

/// 审查指标模型
class ReviewMetric {
  const ReviewMetric({
    required this.name,
    required this.score,
    required this.weight,
    this.threshold,
    this.passed,
  });

  final String name;           // 指标名称
  final double score;          // 0-1分数
  final double weight;         // 权重
  final double? threshold;     // 通过阈值
  final bool? passed;          // 是否通过

  static ReviewMetric fromJson(Map<String, dynamic> json) => ReviewMetric(
    name: json['metric'] as String? ?? 'unknown',
    score: (json['score'] as num?)?.toDouble() ?? 0.0,
    weight: json['weight'] as double? ?? 1.0,
    threshold: (json['threshold'] as num?)?.toDouble(),
    passed: json['passed'] as bool?,
  );

  /// 获取本地化名称
  String getDisplayName(BuildContext context) {
    final names = {
      'accuracy': '准确性',
      'completeness': '完整性',
      'relevance': '相关性',
      'clarity': '清晰度',
      'safety': '安全性',
      'feasibility': '可行性',
      'efficiency': '效率性',
      'helpfulness': '有用性',
      'tone': '语气适当性',
    };
    return names[name] ?? name;
  }

  /// 获取颜色
  Color getColor(BuildContext context) {
    final thresholdValue = threshold ?? 0.7;
    final passedValue = passed ?? (score >= thresholdValue);

    if (passedValue == true) return DS.success;
    if (passedValue == false) return DS.error;
    if (score >= thresholdValue) return DS.success;
    if (score >= 0.5) return DS.warning;
    return DS.error;
  }
}

/// 审查问题模型
class ReviewIssue {
  const ReviewIssue({
    required this.category,
    required this.severity,
    required this.description,
    this.suggestedFix,
    this.affectedContent,
  });

  final String category;        // 问题类别
  final String severity;        // critical/warning/info
  final String description;     // 问题描述
  final String? suggestedFix;   // 修复建议
  final String? affectedContent; // 受影响的内容

  static ReviewIssue fromJson(Map<String, dynamic> json) => ReviewIssue(
    category: json['category'] as String? ?? 'general',
    severity: json['severity'] as String? ?? 'info',
    description: json['description'] as String? ?? '',
    suggestedFix: json['suggested_fix'] as String?,
    affectedContent: json['affected_content'] as String?,
  );

  /// 获取严重程度颜色
  Color getColor(BuildContext context) {
    switch (severity) {
      case 'critical':
        return DS.error;
      case 'warning':
        return DS.warning;
      case 'info':
        return DS.info;
      default:
        return DS.neutral600;
    }
  }

  /// 获取严重程度图标
  IconData getIcon(BuildContext context) {
    switch (severity) {
      case 'critical':
        return Icons.error_outline_rounded;
      case 'warning':
        return Icons.warning_amber_rounded;
      case 'info':
        return Icons.info_outline_rounded;
      default:
        return Icons.help_outline_rounded;
    }
  }

  /// 获取严重程度标签
  String getSeverityLabel() {
    switch (severity) {
      case 'critical':
        return '严重';
      case 'warning':
        return '警告';
      case 'info':
        return '提示';
      default:
        return '';
    }
  }
}

/// 内容审查结果模型
class ContentReviewResult {
  const ContentReviewResult({
    required this.reviewId,
    required this.decision,
    required this.overallScore,
    required this.metrics,
    required this.issues,
    required this.suggestions,
    required this.reviewedAt,
    this.requiresReflection = false,
    this.reflectionStatus,
    this.scoreLabel,
  });

  final String reviewId;
  final ContentReviewDecision decision;
  final double overallScore;
  final List<ReviewMetric> metrics;
  final List<ReviewIssue> issues;
  final List<String> suggestions;
  final String reviewedAt;
  final bool requiresReflection;
  final String? reflectionStatus;  // "pending", "in_progress", "completed", "failed"
  final String? scoreLabel;       // "优秀", "良好", "及格", "需改进"

  static ContentReviewResult fromJson(Map<String, dynamic> json) => ContentReviewResult(
    reviewId: json['review_id'] as String? ?? '',
    decision: _parseDecision(json['decision'] as String? ?? ''),
    overallScore: (json['overall_score'] as num?)?.toDouble() ?? 0.0,
    metrics: (json['metrics'] as List<dynamic>?)
            ?.map((e) => ReviewMetric.fromJson(e as Map<String, dynamic>))
            .toList() ??
        [],
    issues: (json['issues'] as List<dynamic>?)
            ?.map((e) => ReviewIssue.fromJson(e as Map<String, dynamic>))
            .toList() ??
        [],
    suggestions: (json['suggestions'] as List<dynamic>?)
            ?.map((e) => e.toString())
            .toList() ??
        [],
    reviewedAt: json['reviewed_at'] as String? ?? '',
    requiresReflection: json['requires_reflection'] as bool? ?? false,
    reflectionStatus: json['reflection_status'] as String?,
    scoreLabel: json['score_label'] as String?,
  );

  static ContentReviewDecision _parseDecision(String value) {
    switch (value) {
      case 'passed':
        return ContentReviewDecision.passed;
      case 'failed':
        return ContentReviewDecision.failed;
      case 'needs_refinement':
        return ContentReviewDecision.needsRefinement;
      default:
        return ContentReviewDecision.needsRefinement;
    }
  }

  /// 是否通过
  bool get passed => decision == ContentReviewDecision.passed;

  /// 严重问题列表
  List<ReviewIssue> get criticalIssues =>
      issues.where((i) => i.severity == 'critical').toList();

  /// 警告问题列表
  List<ReviewIssue> get warningIssues =>
      issues.where((i) => i.severity == 'warning').toList();

  /// 信息提示列表
  List<ReviewIssue> get infoIssues =>
      issues.where((i) => i.severity == 'info').toList();
}

/// Content Review Card Widget
///
/// 显示AI生成内容的审查结果
class ContentReviewCard extends StatefulWidget {
  const ContentReviewCard({
    required this.review,
    super.key,
    this.onAccept,
    this.onReject,
    this.onRequestReview,
    this.collapsed = false,
  });

  final ContentReviewResult review;
  final VoidCallback? onAccept;
  final VoidCallback? onReject;
  final VoidCallback? onRequestReview;  // 请求人工审查
  final bool collapsed;  // 是否折叠显示

  @override
  State<ContentReviewCard> createState() => _ContentReviewCardState();
}

class _ContentReviewCardState extends State<ContentReviewCard>
    with TickerProviderStateMixin {
  late AnimationController _shimmerController;
  late AnimationController _slideInController;
  late Animation<double> _shimmerAnimation;
  late Animation<Offset> _slideInAnimation;

  bool _isExpanded = true;

  @override
  void initState() {
    super.initState();
    _shimmerController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat();
    _shimmerAnimation = Tween<double>(begin: -2.0, end: 2.0).animate(
      CurvedAnimation(parent: _shimmerController, curve: Curves.easeInOut),
    );

    _slideInController = AnimationController(
      vsync: this,
      duration: SparkleMotion.normal,
    );
    _slideInAnimation = Tween<Offset>(
      begin: const Offset(0, -0.1),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _slideInController, curve: Curves.easeOut));
    _slideInController.forward();
  }

  @override
  void dispose() {
    _shimmerController.dispose();
    _slideInController.dispose();
    super.dispose();
  }

  Color _getDecisionColor() {
    switch (widget.review.decision) {
      case ContentReviewDecision.passed:
        return DS.success;
      case ContentReviewDecision.failed:
        return DS.error;
      case ContentReviewDecision.needsRefinement:
        return DS.warning;
    }
  }

  LinearGradient _getDecisionGradient() {
    switch (widget.review.decision) {
      case ContentReviewDecision.passed:
        return DS.successGradient;
      case ContentReviewDecision.failed:
        return DS.errorGradient;
      case ContentReviewDecision.needsRefinement:
        return DS.warningGradient;
    }
  }

  IconData _getDecisionIcon() {
    switch (widget.review.decision) {
      case ContentReviewDecision.passed:
        return Icons.verified_rounded;
      case ContentReviewDecision.failed:
        return Icons.cancel_rounded;
      case ContentReviewDecision.needsRefinement:
        return Icons.edit_note_rounded;
    }
  }

  String _getDecisionTitle() {
    switch (widget.review.decision) {
      case ContentReviewDecision.passed:
        return '内容已通过审查';
      case ContentReviewDecision.failed:
        return '内容未通过审查';
      case ContentReviewDecision.needsRefinement:
        return '内容需要优化';
    }
  }

  String _getScoreLabel() {
    return widget.review.scoreLabel ??
        (widget.review.overallScore >= 0.9
            ? '优秀'
            : widget.review.overallScore >= 0.7
                ? '良好'
                : widget.review.overallScore >= 0.5
                    ? '及格'
                    : '需改进');
  }

  @override
  Widget build(BuildContext context) {
    final color = _getDecisionColor();
    final gradient = _getDecisionGradient();
    final isDark = Theme.of(context).brightness == Brightness.dark;

    // 如果已通过且折叠，显示简化版本
    if (widget.collapsed && widget.review.passed) {
      return _buildCollapsedCard(context, color, gradient);
    }

    return SlideTransition(
      position: _slideInAnimation,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: DS.spacing8),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: DS.borderRadius16,
          boxShadow: DS.shadowMd,
          border: Border.all(
            color: color.withValues(alpha: 0.3),
            width: 1.5,
          ),
        ),
        child: ClipRRect(
          borderRadius: DS.borderRadius16,
          child: Stack(
            children: [
              // Gradient stripe
              Positioned(
                left: 0,
                top: 0,
                bottom: 0,
                width: 4,
                child: Container(
                  decoration: BoxDecoration(gradient: gradient),
                ),
              ),

              // Content
              Padding(
                padding: const EdgeInsets.all(DS.spacing16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Header
                    _buildHeader(context, color, gradient),

                    const SizedBox(height: DS.spacing12),

                    // Score bar
                    _buildScoreBar(context, color),

                    // Metrics
                    if (widget.review.metrics.isNotEmpty) ...[
                      const SizedBox(height: DS.spacing12),
                      _buildMetricsSection(context),
                    ],

                    // Issues
                    if (widget.review.issues.isNotEmpty) ...[
                      const SizedBox(height: DS.spacing12),
                      _buildIssuesSection(context),
                    ],

                    // Suggestions
                    if (widget.review.suggestions.isNotEmpty) ...[
                      const SizedBox(height: DS.spacing12),
                      _buildSuggestionsSection(context),
                    ],

                    // Reflection status
                    if (widget.review.requiresReflection) ...[
                      const SizedBox(height: DS.spacing12),
                      _buildReflectionStatus(context),
                    ],

                    // Action buttons
                    if (!widget.review.passed) ...[
                      const SizedBox(height: DS.spacing16),
                      _buildActionButtons(context, color, gradient),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCollapsedCard(
    BuildContext context,
    Color color,
    LinearGradient gradient,
  ) {
    return Container(
      margin: const EdgeInsets.symmetric(vertical: DS.spacing4),
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing12,
        vertical: DS.spacing8,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: DS.borderRadius12,
        border: Border.all(
          color: color.withValues(alpha: 0.3),
          width: 1,
        ),
      ),
      child: Row(
        children: [
          Icon(
            _getDecisionIcon(),
            color: color,
            size: 16,
          ),
          const SizedBox(width: DS.spacing8),
          Text(
            '内容已通过审查',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.neutral900,
                  fontWeight: DS.fontWeightMedium,
                ),
          ),
          const Spacer(),
          Text(
            '$_getScoreLabel()',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: color,
                  fontWeight: DS.fontWeightSemibold,
                ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader(
    BuildContext context,
    Color color,
    LinearGradient gradient,
  ) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(DS.spacing10),
          decoration: BoxDecoration(
            gradient: gradient,
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: color.withValues(alpha: 0.3),
                blurRadius: 8,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Icon(
            _getDecisionIcon(),
            color: Colors.white,
            size: 20,
          ),
        ),
        const SizedBox(width: DS.spacing12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                _getDecisionTitle(),
                style: Theme.of(context)
                    .textTheme
                    .titleSmall
                    ?.copyWith(
                      fontWeight: DS.fontWeightBold,
                      color: DS.neutral900,
                    ),
              ),
              Row(
                children: [
                  Text(
                    '$_getScoreLabel()',
                    style: Theme.of(context)
                        .textTheme
                        .bodySmall
                        ?.copyWith(
                          color: color,
                          fontWeight: DS.fontWeightSemibold,
                        ),
                  ),
                  if (widget.review.reflectionStatus != null) ...[
                    const SizedBox(width: DS.spacing8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: DS.spacing6,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: color.withValues(alpha: 0.1),
                        borderRadius: DS.borderRadius8,
                      ),
                      child: Text(
                        _getReflectionStatusLabel(),
                        style: Theme.of(context)
                            .textTheme
                            .labelSmall
                            ?.copyWith(
                              color: color,
                              fontSize: 10,
                            ),
                      ),
                    ),
                  ],
                ],
              ),
            ],
          ),
        ),
        // Expand/collapse button
        InkWell(
          onTap: () => setState(() => _isExpanded = !_isExpanded),
          child: Icon(
            _isExpanded
                ? Icons.expand_less_rounded
                : Icons.expand_more_rounded,
            size: 20,
            color: DS.neutral400,
          ),
        ),
      ],
    );
  }

  Widget _buildScoreBar(BuildContext context, Color color) {
    final score = widget.review.overallScore;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              '综合评分',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.neutral600,
                  ),
            ),
            Text(
              '${(score * 100).toInt()}%',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.neutral900,
                    fontWeight: DS.fontWeightSemibold,
                  ),
            ),
          ],
        ),
        const SizedBox(height: DS.spacing6),
        ClipRRect(
          borderRadius: DS.borderRadius4,
          child: LinearProgressIndicator(
            value: score,
            backgroundColor: DS.neutral200,
            valueColor: AlwaysStoppedAnimation<Color>(
              score >= 0.8
                  ? DS.success
                  : score >= 0.5
                      ? DS.warning
                      : DS.error,
            ),
            minHeight: 6,
          ),
        ),
      ],
    );
  }

  Widget _buildMetricsSection(BuildContext context) {
    final metrics = widget.review.metrics;
    if (metrics.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '评估指标',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: DS.neutral600,
                fontWeight: DS.fontWeightMedium,
              ),
        ),
        const SizedBox(height: DS.spacing8),
        Wrap(
          spacing: DS.spacing8,
          runSpacing: DS.spacing8,
          children: metrics.take(5).map((metric) {
            return _buildMetricChip(context, metric);
          }).toList(),
        ),
      ],
    );
  }

  Widget _buildMetricChip(BuildContext context, ReviewMetric metric) {
    final metricColor = metric.getColor(context);
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing10,
        vertical: DS.spacing6,
      ),
      decoration: BoxDecoration(
        color: metricColor.withValues(alpha: 0.1),
        borderRadius: DS.borderRadius20,
        border: Border.all(
          color: metricColor.withValues(alpha: 0.3),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            metric.getDisplayName(context),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.neutral800,
                  fontWeight: DS.fontWeightMedium,
                ),
          ),
          const SizedBox(width: DS.spacing4),
          Text(
            '${(metric.score * 100).toInt()}%',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: metricColor,
                  fontWeight: DS.fontWeightSemibold,
                ),
          ),
        ],
      ),
    );
  }

  Widget _buildIssuesSection(BuildContext context) {
    final criticalIssues = widget.review.criticalIssues;
    final warningIssues = widget.review.warningIssues;
    final infoIssues = widget.review.infoIssues;

    if (criticalIssues.isEmpty &&
        warningIssues.isEmpty &&
        infoIssues.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (criticalIssues.isNotEmpty) ...[
          _buildIssueGroup(context, '严重问题', criticalIssues, DS.error),
          if (warningIssues.isNotEmpty || infoIssues.isNotEmpty)
              const SizedBox(height: DS.spacing8),
        ],
        if (warningIssues.isNotEmpty) ...[
          _buildIssueGroup(context, '警告', warningIssues, DS.warning),
          if (infoIssues.isNotEmpty)
              const SizedBox(height: DS.spacing8),
        ],
        if (infoIssues.isNotEmpty && widget.review.decision != ContentReviewDecision.passed)
          _buildIssueGroup(context, '提示', infoIssues, DS.info),
      ],
    );
  }

  Widget _buildIssueGroup(
    BuildContext context,
    String title,
    List<ReviewIssue> issues,
    Color color,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(
              _getSeverityIcon(title),
              size: 14,
              color: color,
            ),
            const SizedBox(width: DS.spacing4),
            Text(
              title,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: color,
                    fontWeight: DS.fontWeightSemibold,
                  ),
            ),
          ],
        ),
        const SizedBox(height: DS.spacing6),
        ...issues.take(3).map((issue) => _buildIssueItem(context, issue, color)),
      ],
    );
  }

  IconData _getSeverityIcon(String title) {
    switch (title) {
      case '严重问题':
        return Icons.error;
      case '警告':
        return Icons.warning;
      case '提示':
        return Icons.info;
      default:
        return Icons.circle;
    }
  }

  Widget _buildIssueItem(
    BuildContext context,
    ReviewIssue issue,
    Color color,
  ) {
    return Container(
      padding: const EdgeInsets.all(DS.spacing10),
      margin: const EdgeInsets.only(bottom: DS.spacing4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.06),
        borderRadius: DS.borderRadius8,
        border: Border.all(
          color: color.withValues(alpha: 0.2),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(
                issue.getIcon(context),
                size: 14,
                color: color,
              ),
              const SizedBox(width: DS.spacing6),
              Expanded(
                child: Text(
                  issue.description,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.neutral800,
                      ),
                ),
              ),
            ],
          ),
          if (issue.suggestedFix != null) ...[
            const SizedBox(height: DS.spacing4),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  Icons.lightbulb_outline_rounded,
                  size: 12,
                  color: DS.neutral500,
                ),
                const SizedBox(width: DS.spacing4),
                Expanded(
                  child: Text(
                    '建议: ${issue.suggestedFix}',
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: DS.neutral600,
                          fontStyle: FontStyle.italic,
                          fontSize: 11,
                        ),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildSuggestionsSection(BuildContext context) {
    final suggestions = widget.review.suggestions;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(
              Icons.tips_and_updates_outlined,
              size: 16,
              color: DS.primaryBase,
            ),
            const SizedBox(width: DS.spacing6),
            Text(
              '改进建议',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.neutral600,
                    fontWeight: DS.fontWeightMedium,
                  ),
            ),
          ],
        ),
        const SizedBox(height: DS.spacing8),
        ...suggestions.take(3).map((suggestion) => Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing4),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '•',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.primaryBase,
                        ),
                  ),
                  const SizedBox(width: DS.spacing6),
                  Expanded(
                    child: Text(
                      suggestion,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: DS.neutral800,
                          ),
                    ),
                  ),
                ],
              ),
            )),
      ],
    );
  }

  Widget _buildReflectionStatus(BuildContext context) {
    final status = widget.review.reflectionStatus ?? 'unknown';
    final statusInfo = _getReflectionStatusInfo(status);

    return Container(
      padding: const EdgeInsets.all(DS.spacing10),
      decoration: BoxDecoration(
        color: statusInfo.color.withValues(alpha: 0.1),
        borderRadius: DS.borderRadius8,
        border: Border.all(
          color: statusInfo.color.withValues(alpha: 0.3),
        ),
      ),
      child: Row(
        children: [
          if (statusInfo.isInProgress)
            SizedBox(
              width: 14,
              height: 14,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                valueColor: AlwaysStoppedAnimation<Color>(statusInfo.color),
              ),
            )
          else
            Icon(
              statusInfo.icon,
              size: 16,
              color: statusInfo.color,
            ),
          const SizedBox(width: DS.spacing8),
          Expanded(
            child: Text(
              statusInfo.label,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: statusInfo.color,
                  ),
            ),
          ),
        ],
      ),
    );
  }

  _ReflectionStatusInfo _getReflectionStatusInfo(String status) {
    switch (status) {
      case 'pending':
        return _ReflectionStatusInfo(
          label: '等待优化...',
          icon: Icons.schedule_rounded,
          color: DS.info,
          isInProgress: false,
        );
      case 'in_progress':
        return _ReflectionStatusInfo(
          label: '正在优化内容...',
          icon: Icons.autorenew_rounded,
          color: DS.primaryBase,
          isInProgress: true,
        );
      case 'completed':
        return _ReflectionStatusInfo(
          label: '优化完成',
          icon: Icons.check_circle_rounded,
          color: DS.success,
          isInProgress: false,
        );
      case 'failed':
        return _ReflectionStatusInfo(
          label: '优化失败',
          icon: Icons.error_rounded,
          color: DS.error,
          isInProgress: false,
        );
      default:
        return _ReflectionStatusInfo(
          label: '反思处理中...',
          icon: Icons.sync_rounded,
          color: DS.neutral600,
          isInProgress: true,
        );
    }
  }

  String _getReflectionStatusLabel() {
    final status = widget.review.reflectionStatus ?? 'unknown';
    switch (status) {
      case 'pending':
        return '等待优化';
      case 'in_progress':
        return '优化中...';
      case 'completed':
        return '已优化';
      case 'failed':
        return '优化失败';
      default:
        return '处理中';
    }
  }

  Widget _buildActionButtons(
    BuildContext context,
    Color color,
    LinearGradient gradient,
  ) {
    // 已审查通过的场景不需要操作按钮
    if (widget.review.decision == ContentReviewDecision.passed) {
      return Row(
        children: [
          CustomButton.text(
            text: '接受',
            onPressed: widget.onAccept,
            size: CustomButtonSize.small,
          ),
        ],
      );
    }

    return Row(
      children: [
        // 拒绝/重新生成
        if (widget.onReject != null)
          CustomButton.text(
            text: '重新生成',
            icon: Icons.refresh_rounded,
            onPressed: widget.onReject,
            size: CustomButtonSize.small,
          ),
        // 请求人工审查
        if (widget.onRequestReview != null)
          CustomButton.text(
            text: '人工审查',
            icon: Icons.support_agent_rounded,
            onPressed: widget.onRequestReview,
            size: CustomButtonSize.small,
          ),
        // 接受当前内容
        if (widget.onAccept != null)
          CustomButton.primary(
            text: '接受',
            icon: Icons.check_rounded,
            onPressed: widget.onAccept,
            size: CustomButtonSize.small,
            customGradient: gradient,
          ),
      ],
    );
  }
}

class _ReflectionStatusInfo {
  final String label;
  final IconData icon;
  final Color color;
  final bool isInProgress;

  _ReflectionStatusInfo({
    required this.label,
    required this.icon,
    required this.color,
    required this.isInProgress,
  });
}
