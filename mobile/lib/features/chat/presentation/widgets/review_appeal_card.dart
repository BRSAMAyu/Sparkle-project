// Review Appeal Card Widget - Phase 2e
//
// 显示审查申诉状态和提交申诉表单：
// - 申诉状态追踪
// - 申诉表单（理由输入）
// - 申诉进度时间线
// - 最终决策展示
//
// 作者: Claude Code (Opus 4.5)
// 创建时间: 2026-01-25

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/custom_button.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/utils/formatters.dart';

/// 申诉状态枚举
enum AppealStatus {
  pending,
  inReview,
  resolved,
  rejected,
  escalated,
}

/// 申诉数据模型
class ReviewAppealData {
  const ReviewAppealData({
    required this.appealId,
    required this.reviewId,
    required this.status,
    required this.submittedAt,
    this.appealReason,
    this.resolution,
    this.resolvedBy,
    this.resolvedAt,
    this.secondaryDecision,
    this.secondaryScore,
  });

  final String appealId;
  final String reviewId;
  final AppealStatus status;
  final String submittedAt;
  final String? appealReason;
  final String? resolution;
  final String? resolvedBy;
  final String? resolvedAt;
  final String? secondaryDecision;
  final double? secondaryScore;

  static ReviewAppealData fromJson(Map<String, dynamic> json) =>
      ReviewAppealData(
        appealId: json['appeal_id'] as String? ?? '',
        reviewId: json['review_id'] as String? ?? '',
        status: _parseStatus(json['status'] as String? ?? 'pending'),
        submittedAt: json['submitted_at'] as String? ?? '',
        appealReason: json['appeal_reason'] as String?,
        resolution: json['resolution'] as String?,
        resolvedBy: json['resolved_by'] as String?,
        resolvedAt: json['resolved_at'] as String?,
        secondaryDecision: json['secondary_decision'] as String?,
        secondaryScore: (json['secondary_score'] as num?)?.toDouble(),
      );

  static AppealStatus _parseStatus(String value) {
    switch (value) {
      case 'pending':
        return AppealStatus.pending;
      case 'in_review':
        return AppealStatus.inReview;
      case 'resolved':
        return AppealStatus.resolved;
      case 'rejected':
        return AppealStatus.rejected;
      case 'escalated':
        return AppealStatus.escalated;
      default:
        return AppealStatus.pending;
    }
  }

  bool get isResolved =>
      status == AppealStatus.resolved || status == AppealStatus.rejected;
  bool get isApproved => status == AppealStatus.resolved;
  bool get isRejected => status == AppealStatus.rejected;
  bool get isPending =>
      status == AppealStatus.pending || status == AppealStatus.inReview;
  bool get isEscalated => status == AppealStatus.escalated;
}

/// Review Appeal Card Widget
///
/// 显示审查申诉状态或提交申诉表单
class ReviewAppealCard extends StatefulWidget {
  const ReviewAppealCard({
    super.key,
    this.appealData,
    this.reviewId,
    this.onSubmitAppeal,
    this.onCancelAppeal,
    this.isSubmitting = false,
  });

  /// 已有申诉数据（用于显示状态）
  final ReviewAppealData? appealData;

  /// 审查ID（用于提交新申诉）
  final String? reviewId;

  /// 提交申诉回调
  final Future<bool> Function(String reason, List<String> issues)?
      onSubmitAppeal;

  /// 取消申诉回调
  final VoidCallback? onCancelAppeal;

  /// 是否正在提交
  final bool isSubmitting;

  @override
  State<ReviewAppealCard> createState() => _ReviewAppealCardState();
}

class _ReviewAppealCardState extends State<ReviewAppealCard>
    with SingleTickerProviderStateMixin {
  late AnimationController _pulseController;
  final _reasonController = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  final List<String> _selectedIssues = [];

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );

    if (widget.appealData?.isPending ?? false) {
      unawaited(_pulseController.repeat(reverse: true));
    }
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _reasonController.dispose();
    super.dispose();
  }

  Color _getStatusColor() {
    final status = widget.appealData?.status ?? AppealStatus.pending;
    switch (status) {
      case AppealStatus.pending:
        return DS.info;
      case AppealStatus.inReview:
        return DS.primaryBase;
      case AppealStatus.resolved:
        return DS.success;
      case AppealStatus.rejected:
        return DS.error;
      case AppealStatus.escalated:
        return DS.warning;
    }
  }

  IconData _getStatusIcon() {
    final status = widget.appealData?.status ?? AppealStatus.pending;
    switch (status) {
      case AppealStatus.pending:
        return Icons.schedule_rounded;
      case AppealStatus.inReview:
        return Icons.rate_review_rounded;
      case AppealStatus.resolved:
        return Icons.check_circle_rounded;
      case AppealStatus.rejected:
        return Icons.cancel_rounded;
      case AppealStatus.escalated:
        return Icons.support_agent_rounded;
    }
  }

  String _getStatusTitle(BuildContext context) {
    final status = widget.appealData?.status ?? AppealStatus.pending;
    switch (status) {
      case AppealStatus.pending:
        return context.l10n.reviewAppealPendingTitle;
      case AppealStatus.inReview:
        return context.l10n.reviewAppealInReviewTitle;
      case AppealStatus.resolved:
        return context.l10n.reviewAppealResolvedTitle;
      case AppealStatus.rejected:
        return context.l10n.reviewAppealRejectedTitle;
      case AppealStatus.escalated:
        return context.l10n.reviewAppealEscalatedTitle;
    }
  }

  String _getStatusDescription(BuildContext context) {
    final status = widget.appealData?.status ?? AppealStatus.pending;
    switch (status) {
      case AppealStatus.pending:
        return context.l10n.reviewAppealPendingDesc;
      case AppealStatus.inReview:
        return context.l10n.reviewAppealInReviewDesc;
      case AppealStatus.resolved:
        return widget.appealData?.resolution ??
            context.l10n.reviewAppealResolvedDesc;
      case AppealStatus.rejected:
        return widget.appealData?.resolution ??
            context.l10n.reviewAppealRejectedDesc;
      case AppealStatus.escalated:
        return context.l10n.reviewAppealEscalatedDesc;
    }
  }

  @override
  Widget build(BuildContext context) {
    // 如果有申诉数据，显示状态
    if (widget.appealData != null) {
      return _buildStatusCard(context);
    }

    // 否则显示申诉表单
    return _buildAppealForm(context);
  }

  Widget _buildStatusCard(BuildContext context) {
    final color = _getStatusColor();
    final isPending = widget.appealData?.isPending ?? false;

    return Container(
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
            // Status stripe
            Positioned(
              left: 0,
              top: 0,
              bottom: 0,
              width: 4,
              child: Container(color: color),
            ),

            Padding(
              padding: const EdgeInsets.all(DS.spacing16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Header
                  Row(
                    children: [
                      AnimatedBuilder(
                        animation: _pulseController,
                        builder: (context, child) => Container(
                          padding: const EdgeInsets.all(DS.spacing10),
                          decoration: BoxDecoration(
                            color: color.withValues(
                              alpha: isPending
                                  ? 0.15 + _pulseController.value * 0.1
                                  : 0.15,
                            ),
                            shape: BoxShape.circle,
                          ),
                          child: Icon(
                            _getStatusIcon(),
                            color: color,
                            size: 20,
                          ),
                        ),
                      ),
                      const SizedBox(width: DS.spacing12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              _getStatusTitle(context),
                              style: Theme.of(context)
                                  .textTheme
                                  .titleSmall
                                  ?.copyWith(
                                    fontWeight: DS.fontWeightBold,
                                    color: DS.neutral900,
                                  ),
                            ),
                            Text(
                              context.l10n.reviewAppealId(
                                widget.appealData!.appealId.substring(0, 8),
                              ),
                              style: Theme.of(context)
                                  .textTheme
                                  .bodySmall
                                  ?.copyWith(
                                    color: DS.neutral500,
                                    fontSize: 11,
                                  ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),

                  const SizedBox(height: DS.spacing12),

                  // Description
                  Text(
                    _getStatusDescription(context),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.neutral700,
                        ),
                  ),

                  // Timeline (if resolved)
                  if (widget.appealData!.isResolved) ...[
                    const SizedBox(height: DS.spacing12),
                    _buildTimeline(context),
                  ],

                  // Secondary review result (if available)
                  if (widget.appealData!.secondaryScore != null) ...[
                    const SizedBox(height: DS.spacing12),
                    _buildSecondaryReviewResult(context),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTimeline(BuildContext context) {
    final data = widget.appealData!;
    return Container(
      padding: const EdgeInsets.all(DS.spacing10),
      decoration: BoxDecoration(
        color: DS.neutral100,
        borderRadius: DS.borderRadius8,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildTimelineItem(
            context,
            icon: Icons.send_rounded,
            title: context.l10n.reviewAppealTimelineSubmitted,
            subtitle: _formatTime(data.submittedAt),
            isFirst: true,
          ),
          if (data.secondaryScore != null)
            _buildTimelineItem(
              context,
              icon: Icons.rate_review_rounded,
              title: context.l10n.reviewAppealTimelineReviewed,
              subtitle: context.l10n.reviewAppealScore(
                (data.secondaryScore! * 100).toInt(),
              ),
            ),
          if (data.resolvedAt != null)
            _buildTimelineItem(
              context,
              icon: data.isApproved
                  ? Icons.check_circle_rounded
                  : Icons.cancel_rounded,
              title: data.isApproved
                  ? context.l10n.reviewAppealTimelineApproved
                  : context.l10n.reviewAppealTimelineRejected,
              subtitle: _formatTime(data.resolvedAt!),
              isLast: true,
              color: data.isApproved ? DS.success : DS.error,
            ),
        ],
      ),
    );
  }

  Widget _buildTimelineItem(
    BuildContext context, {
    required IconData icon,
    required String title,
    required String subtitle,
    bool isFirst = false,
    bool isLast = false,
    Color? color,
  }) {
    final itemColor = color ?? DS.neutral600;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Column(
          children: [
            if (!isFirst)
              Container(
                width: 1,
                height: 8,
                color: DS.neutral300,
              ),
            Icon(icon, size: 16, color: itemColor),
            if (!isLast)
              Container(
                width: 1,
                height: 8,
                color: DS.neutral300,
              ),
          ],
        ),
        const SizedBox(width: DS.spacing8),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      fontWeight: DS.fontWeightMedium,
                      color: DS.neutral800,
                    ),
              ),
              Text(
                subtitle,
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: DS.neutral500,
                      fontSize: 10,
                    ),
              ),
              if (!isLast) const SizedBox(height: DS.spacing4),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildSecondaryReviewResult(BuildContext context) {
    final score = widget.appealData!.secondaryScore!;
    final decision = widget.appealData!.secondaryDecision ?? '';
    final passed = decision == 'passed' || score >= 0.7;

    return Container(
      padding: const EdgeInsets.all(DS.spacing10),
      decoration: BoxDecoration(
        color: (passed ? DS.success : DS.warning).withValues(alpha: 0.1),
        borderRadius: DS.borderRadius8,
        border: Border.all(
          color: (passed ? DS.success : DS.warning).withValues(alpha: 0.3),
        ),
      ),
      child: Row(
        children: [
          Icon(
            Icons.analytics_rounded,
            size: 16,
            color: passed ? DS.success : DS.warning,
          ),
          const SizedBox(width: DS.spacing8),
          Text(
            context.l10n.reviewAppealSecondaryScore((score * 100).toInt()),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: DS.neutral800,
                  fontWeight: DS.fontWeightMedium,
                ),
          ),
        ],
      ),
    );
  }

  Widget _buildAppealForm(BuildContext context) => Container(
        margin: const EdgeInsets.symmetric(vertical: DS.spacing8),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: DS.borderRadius16,
          boxShadow: DS.shadowMd,
          border: Border.all(
            color: DS.warning.withValues(alpha: 0.3),
            width: 1.5,
          ),
        ),
        child: ClipRRect(
          borderRadius: DS.borderRadius16,
          child: Stack(
            children: [
              // Warning stripe
              Positioned(
                left: 0,
                top: 0,
                bottom: 0,
                width: 4,
                child: Container(color: DS.warning),
              ),

              Padding(
                padding: const EdgeInsets.all(DS.spacing16),
                child: Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Header
                      Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(DS.spacing10),
                            decoration: BoxDecoration(
                              color: DS.warning.withValues(alpha: 0.15),
                              shape: BoxShape.circle,
                            ),
                            child: Icon(
                              Icons.report_problem_rounded,
                              color: DS.warning,
                              size: 20,
                            ),
                          ),
                          const SizedBox(width: DS.spacing12),
                          Expanded(
                            child: Text(
                              context.l10n.contentReviewAppealDialogTitle,
                              style: Theme.of(context)
                                  .textTheme
                                  .titleSmall
                                  ?.copyWith(
                                    fontWeight: DS.fontWeightBold,
                                    color: DS.neutral900,
                                  ),
                            ),
                          ),
                          InkWell(
                            onTap: widget.onCancelAppeal,
                            borderRadius: DS.borderRadiusFull,
                            child: Icon(
                              Icons.close_rounded,
                              color: DS.neutral400,
                              size: DS.iconSizeSm,
                            ),
                          ),
                        ],
                      ),

                      const SizedBox(height: DS.spacing12),

                      // Issue chips
                      Text(
                        context.l10n.contentReviewAppealSelectType,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: DS.neutral600,
                              fontWeight: DS.fontWeightMedium,
                            ),
                      ),
                      const SizedBox(height: DS.spacing8),
                      Wrap(
                        spacing: DS.spacing8,
                        runSpacing: DS.spacing8,
                        children: _issueOptions(context).map((issue) {
                          final isSelected = _selectedIssues.contains(issue);
                          return GestureDetector(
                            onTap: () {
                              unawaited(
                                SensoryFeedbackService.emit(
                                  SensoryFeedbackEvent.selection,
                                ),
                              );
                              setState(() {
                                if (isSelected) {
                                  _selectedIssues.remove(issue);
                                } else {
                                  _selectedIssues.add(issue);
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
                                style: Theme.of(context)
                                    .textTheme
                                    .labelSmall
                                    ?.copyWith(
                                      color: isSelected
                                          ? DS.warning
                                          : DS.neutral700,
                                      fontWeight: isSelected
                                          ? DS.fontWeightSemibold
                                          : DS.fontWeightMedium,
                                    ),
                              ),
                            ),
                          );
                        }).toList(),
                      ),

                      const SizedBox(height: DS.spacing12),

                      // Reason input
                      Text(
                        context.l10n.contentReviewAppealDetail,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: DS.neutral600,
                              fontWeight: DS.fontWeightMedium,
                            ),
                      ),
                      const SizedBox(height: DS.spacing6),
                      TextFormField(
                        controller: _reasonController,
                        maxLines: 3,
                        decoration: InputDecoration(
                          hintText: context.l10n.contentReviewAppealDetailHint,
                          hintStyle: Theme.of(context)
                              .textTheme
                              .bodySmall
                              ?.copyWith(color: DS.neutral400),
                          filled: true,
                          fillColor: DS.neutral100,
                          border: const OutlineInputBorder(
                            borderRadius: DS.borderRadius8,
                            borderSide: BorderSide.none,
                          ),
                          contentPadding: const EdgeInsets.all(DS.spacing10),
                        ),
                        validator: (value) {
                          if (value == null || value.trim().isEmpty) {
                            return context
                                .l10n.contentReviewAppealDetailRequired;
                          }
                          if (value.trim().length < 10) {
                            return context.l10n.reviewAppealMinReason;
                          }
                          return null;
                        },
                      ),

                      const SizedBox(height: DS.spacing16),

                      // Submit button
                      Row(
                        mainAxisAlignment: MainAxisAlignment.end,
                        children: [
                          CustomButton.text(
                            text: context.l10n.contentReviewCancel,
                            onPressed: widget.onCancelAppeal,
                            size: CustomButtonSize.small,
                          ),
                          const SizedBox(width: DS.spacing8),
                          CustomButton.primary(
                            text: widget.isSubmitting
                                ? context.l10n.commonSubmitting
                                : context.l10n.contentReviewAppealSubmit,
                            icon: Icons.send_rounded,
                            onPressed:
                                widget.isSubmitting ? null : _handleSubmit,
                            size: CustomButtonSize.small,
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      );

  Future<void> _handleSubmit() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    if (_selectedIssues.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(context.l10n.contentReviewAppealTypeRequired)),
      );
      return;
    }

    await SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm);

    final success = await widget.onSubmitAppeal?.call(
      _reasonController.text.trim(),
      _selectedIssues,
    );

    if (success ?? false) {
      _reasonController.clear();
      _selectedIssues.clear();
      setState(() {});
    }
  }

  String _formatTime(String isoTime) {
    try {
      return Formatters.formatRelativeTime(DateTime.parse(isoTime));
    } catch (_) {
      return isoTime;
    }
  }

  List<String> _issueOptions(BuildContext context) => [
        context.l10n.contentReviewAppealUnreasonableStandard,
        context.l10n.contentReviewAppealScoreError,
        context.l10n.contentReviewAppealContextIgnored,
        context.l10n.contentReviewAppealDescriptionInaccurate,
        context.l10n.contentReviewAppealSuggestionNotFeasible,
        context.l10n.reviewAppealOtherIssue,
      ];
}
