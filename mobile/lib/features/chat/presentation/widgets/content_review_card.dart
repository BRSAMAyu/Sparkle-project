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

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/motion.dart';
import 'package:sparkle/core/design/widgets/custom_button.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/l10n/app_localizations.dart';

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

  final String name; // 指标名称
  final double score; // 0-1分数
  final double weight; // 权重
  final double? threshold; // 通过阈值
  final bool? passed; // 是否通过

  static ReviewMetric fromJson(Map<String, dynamic> json) => ReviewMetric(
        name: json['metric'] as String? ?? 'unknown',
        score: (json['score'] as num?)?.toDouble() ?? 0.0,
        weight: json['weight'] as double? ?? 1.0,
        threshold: (json['threshold'] as num?)?.toDouble(),
        passed: json['passed'] as bool?,
      );

  /// 获取本地化名称
  String getDisplayName(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    if (l10n == null) return name;
    final names = {
      'accuracy': l10n.contentReviewMetricAccuracy,
      'completeness': l10n.contentReviewMetricCompleteness,
      'relevance': l10n.contentReviewMetricRelevance,
      'clarity': l10n.contentReviewMetricClarity,
      'safety': l10n.contentReviewMetricSafety,
      'feasibility': l10n.contentReviewMetricFeasibility,
      'efficiency': l10n.contentReviewMetricEfficiency,
      'helpfulness': l10n.contentReviewMetricHelpfulness,
      'tone': l10n.contentReviewMetricTone,
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

  final String category; // 问题类别
  final String severity; // critical/warning/info
  final String description; // 问题描述
  final String? suggestedFix; // 修复建议
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
  String getSeverityLabel(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    if (l10n == null) return severity;
    switch (severity) {
      case 'critical':
        return l10n.contentReviewSeverityCritical;
      case 'warning':
        return l10n.contentReviewSeverityWarning;
      case 'info':
        return l10n.contentReviewSeverityInfo;
      default:
        return severity;
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
  final String?
      reflectionStatus; // "pending", "in_progress", "completed", "failed"
  final String? scoreLabel; // "优秀", "良好", "及格", context.l10n.chatReviewNeedsImprove

  static ContentReviewResult fromJson(Map<String, dynamic> json) =>
      ContentReviewResult(
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

/// 用户覆盖回调参数
typedef OnOverrideCallback = Future<bool> Function(
  String newDecision,
  String reason,
);

/// 申诉回调参数
typedef OnAppealCallback = Future<bool> Function(
  String reason,
  List<String> issues,
);

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
    this.onOverride,
    this.onAppeal,
    this.collapsed = false,
  });

  final ContentReviewResult review;
  final VoidCallback? onAccept;
  final VoidCallback? onReject;
  final VoidCallback? onRequestReview; // 请求人工审查
  final OnOverrideCallback? onOverride; // Phase 2e: 用户覆盖审查决策
  final OnAppealCallback? onAppeal; // Phase 2e: 用户申诉审查结果
  final bool collapsed; // 是否折叠显示

  @override
  State<ContentReviewCard> createState() => _ContentReviewCardState();
}

class _ContentReviewCardState extends State<ContentReviewCard>
    with TickerProviderStateMixin {
  late AnimationController _slideInController;
  late Animation<Offset> _slideInAnimation;

  bool _isExpanded = true;

  @override
  void initState() {
    super.initState();
    _slideInController = AnimationController(
      vsync: this,
      duration: SparkleMotion.normal,
    );
    _slideInAnimation = Tween<Offset>(
      begin: const Offset(0, -0.1),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(parent: _slideInController, curve: Curves.easeOut),
    );
    _slideInController.forward();
  }

  @override
  void dispose() {
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

  String _getDecisionTitle(AppLocalizations l10n) {
    switch (widget.review.decision) {
      case ContentReviewDecision.passed:
        return l10n.contentReviewPassed;
      case ContentReviewDecision.failed:
        return l10n.contentReviewFailed;
      case ContentReviewDecision.needsRefinement:
        return l10n.contentReviewNeedsRefinement;
    }
  }

  String _getScoreLabel(AppLocalizations l10n) =>
      widget.review.scoreLabel ??
      (widget.review.overallScore >= 0.9
          ? l10n.contentReviewScoreExcellent
          : widget.review.overallScore >= 0.7
              ? l10n.contentReviewScoreGood
              : widget.review.overallScore >= 0.5
                  ? l10n.contentReviewScorePass
                  : l10n.contentReviewScoreNeedsWork);

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final color = _getDecisionColor();
    final gradient = _getDecisionGradient();

    // 如果已通过且折叠，显示简化版本
    if (widget.collapsed && widget.review.passed) {
      return _buildCollapsedCard(context, color, gradient, l10n);
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
                    _buildHeader(context, color, gradient, l10n),

                    const SizedBox(height: DS.spacing12),

                    // Score bar
                    _buildScoreBar(context, color, l10n),

                    // Metrics
                    if (widget.review.metrics.isNotEmpty) ...[
                      const SizedBox(height: DS.spacing12),
                      _buildMetricsSection(context, l10n),
                    ],

                    // Issues
                    if (widget.review.issues.isNotEmpty) ...[
                      const SizedBox(height: DS.spacing12),
                      _buildIssuesSection(context, l10n),
                    ],

                    // Suggestions
                    if (widget.review.suggestions.isNotEmpty) ...[
                      const SizedBox(height: DS.spacing12),
                      _buildSuggestionsSection(context, l10n),
                    ],

                    // Reflection status
                    if (widget.review.requiresReflection) ...[
                      const SizedBox(height: DS.spacing12),
                      _buildReflectionStatus(context, l10n),
                    ],

                    // Action buttons
                    if (!widget.review.passed) ...[
                      const SizedBox(height: DS.spacing16),
                      _buildActionButtons(context, color, gradient, l10n),
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
    AppLocalizations l10n,
  ) =>
      Container(
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
              l10n.contentReviewPassed,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.neutral900,
                    fontWeight: DS.fontWeightMedium,
                  ),
            ),
            const Spacer(),
            Text(
              _getScoreLabel(l10n),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: color,
                    fontWeight: DS.fontWeightSemibold,
                  ),
            ),
          ],
        ),
      );

  Widget _buildHeader(
    BuildContext context,
    Color color,
    LinearGradient gradient,
    AppLocalizations l10n,
  ) =>
      Row(
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
              color: DS.textOnPrimary,
              size: 20,
            ),
          ),
          const SizedBox(width: DS.spacing12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _getDecisionTitle(l10n),
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: DS.fontWeightBold,
                        color: DS.neutral900,
                      ),
                ),
                Row(
                  children: [
                    Text(
                      _getScoreLabel(l10n),
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
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
                          _getReflectionStatusLabel(l10n),
                          style:
                              Theme.of(context).textTheme.labelSmall?.copyWith(
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

  Widget _buildScoreBar(
      BuildContext context, Color color, AppLocalizations l10n,) {
    final score = widget.review.overallScore;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              l10n.contentReviewOverallScore,
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

  Widget _buildMetricsSection(BuildContext context, AppLocalizations l10n) {
    final metrics = widget.review.metrics;
    if (metrics.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.contentReviewMetrics,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: DS.neutral600,
                fontWeight: DS.fontWeightMedium,
              ),
        ),
        const SizedBox(height: DS.spacing8),
        Wrap(
          spacing: DS.spacing8,
          runSpacing: DS.spacing8,
          children: metrics
              .take(5)
              .map((metric) => _buildMetricChip(context, metric))
              .toList(),
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

  Widget _buildIssuesSection(BuildContext context, AppLocalizations l10n) {
    final criticalIssues = widget.review.criticalIssues;
    final warningIssues = widget.review.warningIssues;
    final infoIssues = widget.review.infoIssues;

    if (criticalIssues.isEmpty && warningIssues.isEmpty && infoIssues.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (criticalIssues.isNotEmpty) ...[
          _buildIssueGroup(context, l10n.contentReviewCriticalIssues,
              criticalIssues, DS.error,),
          if (warningIssues.isNotEmpty || infoIssues.isNotEmpty)
            const SizedBox(height: DS.spacing8),
        ],
        if (warningIssues.isNotEmpty) ...[
          _buildIssueGroup(
              context, l10n.contentReviewWarnings, warningIssues, DS.warning,),
          if (infoIssues.isNotEmpty) const SizedBox(height: DS.spacing8),
        ],
        if (infoIssues.isNotEmpty &&
            widget.review.decision != ContentReviewDecision.passed)
          _buildIssueGroup(
              context, l10n.contentReviewHints, infoIssues, DS.info,),
      ],
    );
  }

  Widget _buildIssueGroup(
    BuildContext context,
    String title,
    List<ReviewIssue> issues,
    Color color,
  ) {
    final l10n = context.l10n;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(
              _getSeverityIcon(title, l10n),
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
        ...issues
            .take(3)
            .map((issue) => _buildIssueItem(context, issue, color, l10n)),
      ],
    );
  }

  IconData _getSeverityIcon(String title, AppLocalizations l10n) {
    if (title == l10n.contentReviewCriticalIssues) {
      return Icons.error;
    } else if (title == l10n.contentReviewWarnings) {
      return Icons.warning;
    } else if (title == l10n.contentReviewHints) {
      return Icons.info;
    }
    return Icons.circle;
  }

  Widget _buildIssueItem(
    BuildContext context,
    ReviewIssue issue,
    Color color,
    AppLocalizations l10n,
  ) =>
      Container(
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
                      l10n.contentReviewSuggestion(issue.suggestedFix!),
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

  Widget _buildSuggestionsSection(BuildContext context, AppLocalizations l10n) {
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
              l10n.contentReviewSuggestions,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.neutral600,
                    fontWeight: DS.fontWeightMedium,
                  ),
            ),
          ],
        ),
        const SizedBox(height: DS.spacing8),
        ...suggestions.take(3).map(
              (suggestion) => Padding(
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
              ),
            ),
      ],
    );
  }

  Widget _buildReflectionStatus(BuildContext context, AppLocalizations l10n) {
    final status = widget.review.reflectionStatus ?? 'unknown';
    final statusInfo = _getReflectionStatusInfo(status, l10n);

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

  _ReflectionStatusInfo _getReflectionStatusInfo(
      String status, AppLocalizations l10n,) {
    switch (status) {
      case 'pending':
        return _ReflectionStatusInfo(
          label: l10n.contentReviewReflectionPending,
          icon: Icons.schedule_rounded,
          color: DS.info,
          isInProgress: false,
        );
      case 'in_progress':
        return _ReflectionStatusInfo(
          label: l10n.contentReviewReflectionInProgress,
          icon: Icons.autorenew_rounded,
          color: DS.primaryBase,
          isInProgress: true,
        );
      case 'completed':
        return _ReflectionStatusInfo(
          label: l10n.contentReviewReflectionCompleted,
          icon: Icons.check_circle_rounded,
          color: DS.success,
          isInProgress: false,
        );
      case 'failed':
        return _ReflectionStatusInfo(
          label: l10n.contentReviewReflectionFailed,
          icon: Icons.error_rounded,
          color: DS.error,
          isInProgress: false,
        );
      default:
        return _ReflectionStatusInfo(
          label: l10n.contentReviewReflectionProcessing,
          icon: Icons.sync_rounded,
          color: DS.neutral600,
          isInProgress: true,
        );
    }
  }

  String _getReflectionStatusLabel(AppLocalizations l10n) {
    final status = widget.review.reflectionStatus ?? 'unknown';
    switch (status) {
      case 'pending':
        return l10n.contentReviewReflectionPendingShort;
      case 'in_progress':
        return l10n.contentReviewReflectionInProgressShort;
      case 'completed':
        return l10n.contentReviewReflectionCompletedShort;
      case 'failed':
        return l10n.contentReviewReflectionFailedShort;
      default:
        return l10n.contentReviewReflectionProcessingShort;
    }
  }

  Widget _buildActionButtons(
    BuildContext context,
    Color color,
    LinearGradient gradient,
    AppLocalizations l10n,
  ) {
    // 已审查通过的场景
    if (widget.review.decision == ContentReviewDecision.passed) {
      return Row(
        children: [
          CustomButton.text(
            text: l10n.contentReviewAccept,
            onPressed: widget.onAccept,
            size: CustomButtonSize.small,
          ),
          // Phase 2e: 即使通过，用户仍可以反对
          if (widget.onOverride != null) ...[
            const SizedBox(width: DS.spacing4),
            _buildMoreActionsMenu(context, color, l10n),
          ],
        ],
      );
    }

    return Row(
      children: [
        // 拒绝/重新生成
        if (widget.onReject != null)
          CustomButton.text(
            text: l10n.contentReviewRegenerate,
            icon: Icons.refresh_rounded,
            onPressed: widget.onReject,
            size: CustomButtonSize.small,
          ),
        // 请求人工审查
        if (widget.onRequestReview != null)
          CustomButton.text(
            text: l10n.contentReviewManualReview,
            icon: Icons.support_agent_rounded,
            onPressed: widget.onRequestReview,
            size: CustomButtonSize.small,
          ),
        // Phase 2e: 更多操作菜单（覆盖/申诉）
        if (widget.onOverride != null || widget.onAppeal != null)
          _buildMoreActionsMenu(context, color, l10n),
        // 接受当前内容
        if (widget.onAccept != null)
          CustomButton.primary(
            text: l10n.contentReviewAccept,
            icon: Icons.check_rounded,
            onPressed: widget.onAccept,
            size: CustomButtonSize.small,
            customGradient: gradient,
          ),
      ],
    );
  }

  /// Phase 2e: 更多操作菜单
  Widget _buildMoreActionsMenu(
          BuildContext context, Color color, AppLocalizations l10n,) =>
      PopupMenuButton<String>(
        icon: Icon(
          Icons.more_horiz_rounded,
          color: DS.neutral500,
          size: 20,
        ),
        padding: EdgeInsets.zero,
        onSelected: (value) => _handleMenuAction(context, value, l10n),
        itemBuilder: (context) => [
          if (widget.onOverride != null)
            PopupMenuItem(
              value: 'override',
              child: Row(
                children: [
                  Icon(
                    widget.review.passed
                        ? Icons.thumb_down_rounded
                        : Icons.thumb_up_rounded,
                    size: 16,
                    color: DS.neutral700,
                  ),
                  const SizedBox(width: DS.spacing8),
                  Text(
                    widget.review.passed
                        ? l10n.contentReviewDisagreePass
                        : l10n.contentReviewAgreePass,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            ),
          if (widget.onAppeal != null)
            PopupMenuItem(
              value: 'appeal',
              child: Row(
                children: [
                  Icon(
                    Icons.report_problem_rounded,
                    size: 16,
                    color: DS.warning,
                  ),
                  const SizedBox(width: DS.spacing8),
                  Text(
                    l10n.contentReviewReportIssue,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            ),
        ],
      );

  void _handleMenuAction(
      BuildContext context, String action, AppLocalizations l10n,) {
    if (action == 'override') {
      _showOverrideDialog(context, l10n);
    } else if (action == 'appeal') {
      _showAppealDialog(context, l10n);
    }
  }

  /// 显示覆盖决策对话框
  void _showOverrideDialog(BuildContext context, AppLocalizations l10n) {
    final reasonController = TextEditingController();
    final currentDecision =
        widget.review.decision == ContentReviewDecision.passed
            ? 'passed'
            : 'failed';
    final newDecision = currentDecision == 'passed' ? 'failed' : 'passed';

    unawaited(showSensoryModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
      builder: (context) => Container(
        margin: const EdgeInsets.all(DS.spacing16),
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: DS.borderRadius16,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              currentDecision == 'passed'
                  ? l10n.contentReviewDisagreePassTitle
                  : l10n.contentReviewAgreePassTitle,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            const SizedBox(height: DS.spacing12),
            Text(
              l10n.contentReviewReasonPrompt,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.neutral600,
                  ),
            ),
            const SizedBox(height: DS.spacing8),
            TextField(
              controller: reasonController,
              maxLines: 3,
              decoration: InputDecoration(
                hintText: l10n.contentReviewReasonHint,
                filled: true,
                fillColor: DS.neutral100,
                border: const OutlineInputBorder(
                  borderRadius: DS.borderRadius8,
                  borderSide: BorderSide.none,
                ),
              ),
            ),
            const SizedBox(height: DS.spacing16),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                SparkleButton.ghost(
                  label: l10n.contentReviewCancel,
                  onPressed: () => Navigator.pop(context),
                ),
                const SizedBox(width: DS.spacing8),
                SparkleButton.primary(
                  label: l10n.contentReviewConfirm,
                  onPressed: () async {
                    final reason = reasonController.text.trim();
                    if (reason.isEmpty) {
                      AppFeedback.error(
                          context, l10n.contentReviewReasonRequired,);
                      return;
                    }
                    Navigator.pop(context);
                    await widget.onOverride?.call(newDecision, reason);
                  },
                ),
              ],
            ),
          ],
        ),
      ),
    ),);
  }

  /// 显示申诉对话框
  void _showAppealDialog(BuildContext context, AppLocalizations l10n) {
    final reasonController = TextEditingController();
    final selectedIssues = <String>[];
    final issueOptions = [
      l10n.contentReviewAppealUnreasonableStandard,
      l10n.contentReviewAppealScoreError,
      l10n.contentReviewAppealContextIgnored,
      l10n.contentReviewAppealDescriptionInaccurate,
      l10n.contentReviewAppealSuggestionNotFeasible,
    ];

    unawaited(showSensoryModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => Container(
          margin: const EdgeInsets.all(DS.spacing16),
          padding: const EdgeInsets.all(DS.spacing16),
          decoration: BoxDecoration(
            color: DS.surfaceSecondary,
            borderRadius: DS.borderRadius16,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                l10n.contentReviewReportIssue,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: DS.fontWeightBold,
                    ),
              ),
              const SizedBox(height: DS.spacing12),
              Text(
                l10n.contentReviewAppealSelectType,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.neutral600,
                    ),
              ),
              const SizedBox(height: DS.spacing8),
              Wrap(
                spacing: DS.spacing8,
                runSpacing: DS.spacing8,
                children: issueOptions.map((issue) {
                  final isSelected = selectedIssues.contains(issue);
                  return GestureDetector(
                    onTap: () {
                      setDialogState(() {
                        if (isSelected) {
                          selectedIssues.remove(issue);
                        } else {
                          selectedIssues.add(issue);
                        }
                      });
                    },
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: DS.spacing10,
                        vertical: DS.spacing6,
                      ),
                      decoration: BoxDecoration(
                        color: isSelected
                            ? DS.warning.withValues(alpha: 0.15)
                            : DS.neutral100,
                        borderRadius: DS.borderRadius20,
                        border: Border.all(
                          color: isSelected
                              ? DS.warning.withValues(alpha: 0.5)
                              : DS.neutral300,
                        ),
                      ),
                      child: Text(
                        issue,
                        style: Theme.of(context).textTheme.labelSmall?.copyWith(
                              color: isSelected ? DS.warning : DS.neutral700,
                            ),
                      ),
                    ),
                  );
                }).toList(),
              ),
              const SizedBox(height: DS.spacing12),
              Text(
                l10n.contentReviewAppealDetail,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.neutral600,
                    ),
              ),
              const SizedBox(height: DS.spacing8),
              TextField(
                controller: reasonController,
                maxLines: 3,
                decoration: InputDecoration(
                  hintText: l10n.contentReviewAppealDetailHint,
                  filled: true,
                  fillColor: DS.neutral100,
                  border: const OutlineInputBorder(
                    borderRadius: DS.borderRadius8,
                    borderSide: BorderSide.none,
                  ),
                ),
              ),
              const SizedBox(height: DS.spacing16),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  SparkleButton.ghost(
                    label: l10n.contentReviewCancel,
                    onPressed: () => Navigator.pop(context),
                  ),
                  const SizedBox(width: DS.spacing8),
                  SparkleButton.primary(
                    label: l10n.contentReviewAppealSubmit,
                    onPressed: () async {
                      final reason = reasonController.text.trim();
                      if (reason.isEmpty) {
                        AppFeedback.error(
                            context, l10n.contentReviewAppealDetailRequired,);
                        return;
                      }
                      if (selectedIssues.isEmpty) {
                        AppFeedback.error(
                            context, l10n.contentReviewAppealTypeRequired,);
                        return;
                      }
                      Navigator.pop(context);
                      await widget.onAppeal?.call(reason, selectedIssues);
                    },
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    ),);
  }
}

class _ReflectionStatusInfo {
  _ReflectionStatusInfo({
    required this.label,
    required this.icon,
    required this.color,
    required this.isInProgress,
  });

  final String label;
  final IconData icon;
  final Color color;
  final bool isInProgress;
}
