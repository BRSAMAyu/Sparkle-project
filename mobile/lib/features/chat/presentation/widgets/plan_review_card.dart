import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/motion.dart';
import 'package:sparkle/core/design/widgets/custom_button.dart';

/// Plan review decision types
enum ReviewDecision {
  approved,
  rejected,
  needsModification,
  requiresConfirmation,
}

/// Review comment model
class ReviewComment {
  const ReviewComment({
    required this.category,
    required this.severity,
    required this.message,
    this.suggestedFix,
    this.affectedToolCalls = const [],
  });

  final String category;
  final String severity; // 'critical', 'warning', 'info'
  final String message;
  final String? suggestedFix;
  final List<String> affectedToolCalls;

  static ReviewComment fromJson(Map<String, dynamic> json) => ReviewComment(
        category: json['category'] as String? ?? 'suggestion',
        severity: json['severity'] as String? ?? 'info',
        message: json['message'] as String? ?? '',
        suggestedFix: json['suggested_fix'] as String?,
        affectedToolCalls: (json['affected_tool_calls'] as List<dynamic>?)
                ?.map((e) => e.toString())
                .toList() ??
            [],
      );
}

class ReviewReasoningDetail {
  const ReviewReasoningDetail({
    required this.label,
    required this.evidence,
    required this.impact,
    this.confidenceTier,
  });

  final String label;
  final String evidence;
  final String impact;
  final String? confidenceTier;

  static ReviewReasoningDetail fromJson(Map<String, dynamic> json) =>
      ReviewReasoningDetail(
        label: json['label'] as String? ?? '',
        evidence: json['evidence'] as String? ?? '',
        impact: json['impact'] as String? ?? '',
        confidenceTier: json['confidence_tier'] as String?,
      );
}

/// Plan review result model
class PlanReviewResult {
  const PlanReviewResult({
    required this.reviewId,
    required this.planId,
    required this.decision,
    required this.confidence,
    required this.comments,
    required this.reviewedAt,
    this.suggestedModifications,
    this.autoApproved = false,
    this.actionId,
    this.userFacingReason,
    this.reasoningSummary,
    this.reasoningDetails = const [],
    this.alignmentSummary,
    this.alignmentScore,
  });

  final String reviewId;
  final String planId;
  final ReviewDecision decision;
  final double confidence;
  final List<ReviewComment> comments;
  final String reviewedAt;
  final Map<String, dynamic>? suggestedModifications;
  final bool autoApproved;
  final String? actionId; // For feedback
  final String? userFacingReason; // User-facing explanation of the decision
  final String? reasoningSummary;
  final List<ReviewReasoningDetail> reasoningDetails;
  final String? alignmentSummary;
  final double? alignmentScore;

  static ReviewDecision _parseDecision(String value) {
    switch (value) {
      case 'approved':
        return ReviewDecision.approved;
      case 'rejected':
        return ReviewDecision.rejected;
      case 'needs_modification':
        return ReviewDecision.needsModification;
      case 'requires_confirmation':
        return ReviewDecision.requiresConfirmation;
      default:
        return ReviewDecision.requiresConfirmation;
    }
  }

  static PlanReviewResult fromJson(Map<String, dynamic> json) =>
      PlanReviewResult(
        reviewId: json['review_id'] as String? ?? '',
        planId: json['plan_id'] as String? ?? '',
        decision: _parseDecision(json['decision'] as String? ?? ''),
        confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
        comments: (json['comments'] as List<dynamic>?)
                ?.map((e) => ReviewComment.fromJson(e as Map<String, dynamic>))
                .toList() ??
            [],
        reviewedAt: json['reviewed_at'] as String? ?? '',
        suggestedModifications:
            json['suggested_modifications'] as Map<String, dynamic>?,
        autoApproved: json['auto_approved'] as bool? ?? false,
        actionId: json['action_id'] as String?,
        userFacingReason: json['user_facing_reason'] as String?,
        reasoningSummary: json['reasoning_summary'] as String?,
        reasoningDetails: (json['reasoning_details'] as List<dynamic>?)
                ?.map(
                  (e) => ReviewReasoningDetail.fromJson(
                    Map<String, dynamic>.from(e as Map),
                  ),
                )
                .toList() ??
            const [],
        alignmentSummary: json['alignment_summary'] as String?,
        alignmentScore: (json['alignment_score'] as num?)?.toDouble(),
      );
}

/// Plan Review Card Widget
///
/// Displays the result of an AI plan review with action buttons.
/// Used in the chat screen to present plan approval/modification options.
class PlanReviewCard extends StatefulWidget {
  const PlanReviewCard({
    required this.review,
    super.key,
    this.onApprove,
    this.onReject,
    this.onModify,
    this.onDecision,
  });

  final PlanReviewResult review;
  final VoidCallback? onApprove;
  final VoidCallback? onReject;
  final VoidCallback? onModify;

  /// Callback for user decision with the decision type
  final Future<bool> Function(
    ReviewDecision decision, {
    String? userComment,
    Map<String, String>? meta,
  })? onDecision;

  @override
  State<PlanReviewCard> createState() => _PlanReviewCardState();
}

class _PlanReviewCardState extends State<PlanReviewCard>
    with TickerProviderStateMixin {
  late AnimationController _highlightController;
  late Animation<double> _iconScaleAnimation;
  late AnimationController _pressController;
  late AnimationController _slideInController;

  // Submission state
  bool _isSubmitting = false;
  bool _isSubmitted = false;

  @override
  void initState() {
    super.initState();
    _highlightController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2200),
    );

    _iconScaleAnimation = Tween<double>(begin: 1.0, end: 1.08).animate(
      CurvedAnimation(parent: _highlightController, curve: Curves.easeInOut),
    );

    _pressController = AnimationController(
      vsync: this,
      duration: SparkleMotion.fast,
    );

    _slideInController = AnimationController(
      vsync: this,
      duration: SparkleMotion.normal,
    );
    _slideInController.forward();
    _syncHighlightAnimation();
  }

  @override
  void didUpdateWidget(covariant PlanReviewCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.review != widget.review || _isSubmitting || _isSubmitted) {
      _syncHighlightAnimation();
    }
  }

  @override
  void dispose() {
    _highlightController.dispose();
    _pressController.dispose();
    _slideInController.dispose();
    super.dispose();
  }

  bool get _showActions =>
      !_isSubmitted &&
      !widget.review.autoApproved &&
      widget.review.decision != ReviewDecision.approved &&
      (widget.onDecision != null ||
          widget.onApprove != null ||
          widget.onReject != null ||
          widget.onModify != null);

  void _syncHighlightAnimation() {
    if (_showActions && !_isSubmitting) {
      if (!_highlightController.isAnimating) {
        _highlightController.repeat(reverse: true);
      }
    } else {
      _highlightController.stop();
      _highlightController.value = 0;
    }
  }

  /// Handle user decision on the plan review
  Future<void> _handleDecision(
    ReviewDecision decision, {
    String? userComment,
    Map<String, String>? meta,
  }) async {
    if (_isSubmitting || _isSubmitted) return;

    setState(() => _isSubmitting = true);

    try {
      // Use new callback if provided
      if (widget.onDecision != null) {
        final success = await widget.onDecision!(
          decision,
          userComment: userComment,
          meta: meta,
        );
        if (success) {
          setState(() => _isSubmitted = true);
        }
      } else {
        // Fall back to legacy callbacks
        switch (decision) {
          case ReviewDecision.approved:
            widget.onApprove?.call();
          case ReviewDecision.rejected:
            widget.onReject?.call();
          case ReviewDecision.needsModification:
            widget.onModify?.call();
          case ReviewDecision.requiresConfirmation:
            widget.onApprove?.call();
        }
        setState(() => _isSubmitted = true);
      }
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
        _syncHighlightAnimation();
      }
    }
  }

  Future<void> _handleRejectionFlow() async {
    final feedback = await _showRejectionFeedbackSheet();
    if (feedback == null) return;

    final trimmedNote = feedback.note?.trim();
    final meta = <String, String>{
      'feedback_category': feedback.category,
      if (trimmedNote != null && trimmedNote.isNotEmpty)
        'feedback_note': trimmedNote,
    };

    await _handleDecision(
      ReviewDecision.rejected,
      userComment: trimmedNote,
      meta: meta,
    );
  }

  @override
  Widget build(BuildContext context) {
    final decision = widget.review.decision;
    final gradient = _getDecisionGradient(decision);
    final color = _getDecisionColor(decision);
    final icon = _getDecisionIcon(decision);
    final title = _getDecisionTitle(decision);
    final showActions = _showActions;

    return SlideTransition(
      position: Tween<Offset>(
        begin: const Offset(0, -0.1),
        end: Offset.zero,
      ).animate(
        CurvedAnimation(
          parent: _slideInController,
          curve: Curves.easeOut,
        ),
      ),
      child: GestureDetector(
        onTapDown: showActions ? (_) => _pressController.forward() : null,
        onTapUp: showActions ? (_) => _pressController.reverse() : null,
        onTapCancel: showActions ? () => _pressController.reverse() : null,
        child: RepaintBoundary(
          child: SparkleMotion.pressScale(
            animation: _pressController,
            child: Container(
              margin: const EdgeInsets.symmetric(vertical: DS.spacing8),
              decoration: BoxDecoration(
                color: context.colors.surfaceCard,
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
                    Positioned(
                      left: 0,
                      top: 0,
                      bottom: 0,
                      width: 5,
                      child: DecoratedBox(
                        decoration: BoxDecoration(gradient: gradient),
                      ),
                    ),
                    if (showActions)
                      Positioned.fill(
                        child: IgnorePointer(
                          child: AnimatedBuilder(
                            animation: _highlightController,
                            builder: (context, child) {
                              final progress = _highlightController.value;
                              return DecoratedBox(
                                decoration: BoxDecoration(
                                  gradient: LinearGradient(
                                    begin: Alignment.topLeft,
                                    end: Alignment.bottomRight,
                                    colors: [
                                      DS.surfacePrimary.withValues(alpha: 0),
                                      color.withValues(
                                          alpha: 0.03 + (progress * 0.05),),
                                      DS.surfacePrimary.withValues(alpha: 0),
                                    ],
                                    stops: const [0.2, 0.5, 0.8],
                                  ),
                                ),
                              );
                            },
                          ),
                        ),
                      ),
                    Padding(
                      padding: const EdgeInsets.all(DS.spacing16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              AnimatedBuilder(
                                animation: _iconScaleAnimation,
                                child: Container(
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
                                    icon,
                                    color: DS.textOnPrimary,
                                    size: DS.iconSizeBase,
                                  ),
                                ),
                                builder: (context, child) => Transform.scale(
                                  scale: showActions
                                      ? _iconScaleAnimation.value
                                      : 1,
                                  child: child,
                                ),
                              ),
                              const SizedBox(width: DS.spacing12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      title,
                                      style: Theme.of(context)
                                          .textTheme
                                          .titleMedium
                                          ?.copyWith(
                                            fontWeight: DS.fontWeightBold,
                                            color: DS.neutral900,
                                          ),
                                    ),
                                    if (widget.review.confidence > 0)
                                      Text(
                                        '置信度: ${(widget.review.confidence * 100).toInt()}%',
                                        style: Theme.of(context)
                                            .textTheme
                                            .bodySmall
                                            ?.copyWith(
                                              color: DS.neutral600,
                                            ),
                                      ),
                                  ],
                                ),
                              ),
                              _buildDecisionBadge(decision),
                            ],
                          ),
                          if (widget.review.userFacingReason != null) ...[
                            const SizedBox(height: DS.spacing12),
                            Container(
                              padding: const EdgeInsets.all(DS.spacing12),
                              decoration: BoxDecoration(
                                color: color.withValues(alpha: 0.08),
                                borderRadius: DS.borderRadius8,
                                border: Border.all(
                                  color: color.withValues(alpha: 0.2),
                                ),
                              ),
                              child: Row(
                                children: [
                                  Icon(
                                    Icons.info_outline_rounded,
                                    size: DS.iconSizeSm,
                                    color: color,
                                  ),
                                  const SizedBox(width: DS.spacing8),
                                  Expanded(
                                    child: Text(
                                      widget.review.userFacingReason!,
                                      style: Theme.of(context)
                                          .textTheme
                                          .bodySmall
                                          ?.copyWith(
                                            color: DS.neutral800,
                                            height: 1.4,
                                          ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                          if ((widget.review.reasoningSummary ?? '').isNotEmpty) ...[
                            const SizedBox(height: DS.spacing12),
                            _buildReasoningSummary(color),
                          ],
                          if ((widget.review.alignmentSummary ?? '').isNotEmpty) ...[
                            const SizedBox(height: DS.spacing12),
                            _buildAlignmentSummary(),
                          ],
                          if (widget.review.reasoningDetails.isNotEmpty) ...[
                            const SizedBox(height: DS.spacing12),
                            _buildReasoningDetails(),
                          ],
                          if (widget.review.comments.isNotEmpty) ...[
                            const SizedBox(height: DS.spacing16),
                            _buildCommentsSection(),
                          ],
                          if (widget.review.confidence > 0 &&
                              !widget.review.autoApproved) ...[
                            const SizedBox(height: DS.spacing12),
                            _buildConfidenceBar(),
                          ],
                          if (showActions) ...[
                            const SizedBox(height: DS.spacing16),
                            _buildActionButtons(decision, gradient),
                          ],
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildReasoningSummary(Color accentColor) => Container(
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: accentColor.withValues(alpha: 0.08),
          borderRadius: DS.borderRadius8,
          border: Border.all(color: accentColor.withValues(alpha: 0.18)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              Icons.lightbulb_outline_rounded,
              size: DS.iconSizeSm,
              color: accentColor,
            ),
            const SizedBox(width: DS.spacing8),
            Expanded(
              child: Text(
                widget.review.reasoningSummary ?? '',
                style: const TextStyle(height: 1.45),
              ),
            ),
          ],
        ),
      );

  Widget _buildReasoningDetails() => ExpansionTile(
        tilePadding: EdgeInsets.zero,
        childrenPadding: EdgeInsets.zero,
        title: const Text(
          '查看规划依据',
          style: TextStyle(fontWeight: DS.fontWeightSemibold),
        ),
        children: widget.review.reasoningDetails.map((detail) => Container(
            margin: const EdgeInsets.only(top: DS.spacing8),
            padding: const EdgeInsets.all(DS.spacing12),
            decoration: BoxDecoration(
              color: DS.neutral100,
              borderRadius: DS.borderRadius12,
              border: Border.all(color: DS.neutral200),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  detail.label,
                  style: const TextStyle(fontWeight: DS.fontWeightSemibold),
                ),
                if (detail.evidence.isNotEmpty) ...[
                  const SizedBox(height: DS.spacing6),
                  Text('依据：${detail.evidence}'),
                ],
                if (detail.impact.isNotEmpty) ...[
                  const SizedBox(height: DS.spacing6),
                  Text('影响：${detail.impact}'),
                ],
                if ((detail.confidenceTier ?? '').isNotEmpty) ...[
                  const SizedBox(height: DS.spacing6),
                  Text('证据层级：${detail.confidenceTier}'),
                ],
              ],
            ),
          )).toList(),
      );

  Widget _buildAlignmentSummary() => Container(
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: DS.info.withValues(alpha: 0.08),
          borderRadius: DS.borderRadius8,
          border: Border.all(color: DS.info.withValues(alpha: 0.18)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              Icons.track_changes_outlined,
              size: DS.iconSizeSm,
              color: DS.info,
            ),
            const SizedBox(width: DS.spacing8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    widget.review.alignmentSummary ?? '',
                    style: const TextStyle(height: 1.45),
                  ),
                  if (widget.review.alignmentScore != null) ...[
                    const SizedBox(height: DS.spacing6),
                    Text(
                      '画像对齐度 ${(widget.review.alignmentScore! * 100).toStringAsFixed(0)}%',
                      style: TextStyle(
                        color: DS.info,
                        fontSize: DS.fontSizeXs,
                        fontWeight: DS.fontWeightSemibold,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      );

  Widget _buildDecisionBadge(ReviewDecision decision) {
    String label;
    Color bgColor;
    Color textColor;

    switch (decision) {
      case ReviewDecision.approved:
        label = '已通过';
        bgColor = DS.success.withValues(alpha: 0.1);
        textColor = DS.success;
      case ReviewDecision.rejected:
        label = '未通过';
        bgColor = DS.error.withValues(alpha: 0.1);
        textColor = DS.error;
      case ReviewDecision.needsModification:
        label = '需修改';
        bgColor = DS.warning.withValues(alpha: 0.1);
        textColor = DS.warning;
      case ReviewDecision.requiresConfirmation:
        label = '待确认';
        bgColor = DS.info.withValues(alpha: 0.1);
        textColor = DS.info;
    }

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing10,
        vertical: DS.spacing4,
      ),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: DS.borderRadius20,
        border: Border.all(color: textColor.withValues(alpha: 0.3)),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: DS.fontSizeXs,
          fontWeight: DS.fontWeightSemibold,
          color: textColor,
        ),
      ),
    );
  }

  Widget _buildCommentsSection() {
    final criticalComments =
        widget.review.comments.where((c) => c.severity == 'critical').toList();
    final warningComments =
        widget.review.comments.where((c) => c.severity == 'warning').toList();
    final infoComments =
        widget.review.comments.where((c) => c.severity == 'info').toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (criticalComments.isNotEmpty) ...[
          _buildCommentGroup('严重问题', criticalComments, DS.error),
          if (warningComments.isNotEmpty || infoComments.isNotEmpty)
            const SizedBox(height: DS.spacing8),
        ],
        if (warningComments.isNotEmpty) ...[
          _buildCommentGroup('警告', warningComments, DS.warning),
          if (infoComments.isNotEmpty) const SizedBox(height: DS.spacing8),
        ],
        if (infoComments.isNotEmpty &&
            widget.review.decision != ReviewDecision.rejected)
          _buildCommentGroup('建议', infoComments, DS.info),
      ],
    );
  }

  Widget _buildCommentGroup(
          String title, List<ReviewComment> comments, Color color,) =>
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  fontWeight: DS.fontWeightSemibold,
                  color: color,
                ),
          ),
          const SizedBox(height: DS.spacing6),
          ...comments.take(3).map(
                (comment) => Padding(
                  padding: const EdgeInsets.only(bottom: DS.spacing6),
                  child: _buildCommentItem(comment, color),
                ),
              ),
        ],
      );

  Widget _buildCommentItem(ReviewComment comment, Color color) => Container(
        padding: const EdgeInsets.all(DS.spacing12),
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
              children: [
                Icon(
                  _getCategoryIcon(comment.category),
                  size: DS.iconSizeXs,
                  color: color,
                ),
                const SizedBox(width: DS.spacing6),
                Expanded(
                  child: Text(
                    comment.message,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.neutral800,
                        ),
                  ),
                ),
              ],
            ),
            if (comment.suggestedFix != null) ...[
              const SizedBox(height: DS.spacing6),
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(
                    Icons.lightbulb_outline_rounded,
                    size: DS.iconSizeXs,
                    color: DS.neutral600,
                  ),
                  const SizedBox(width: DS.spacing6),
                  Expanded(
                    child: Text(
                      '建议: ${comment.suggestedFix}',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: DS.neutral600,
                            fontStyle: FontStyle.italic,
                          ),
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      );

  Widget _buildConfidenceBar() => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '审查置信度',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.neutral600,
                    ),
              ),
              Text(
                '${(widget.review.confidence * 100).toInt()}%',
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
              value: widget.review.confidence,
              backgroundColor: DS.neutral200,
              valueColor: AlwaysStoppedAnimation<Color>(
                widget.review.confidence >= 0.8
                    ? DS.success
                    : widget.review.confidence >= 0.5
                        ? DS.warning
                        : DS.error,
              ),
              minHeight: 6,
            ),
          ),
        ],
      );

  Widget _buildActionButtons(ReviewDecision decision, LinearGradient gradient) {
    // For rejected plans, only show retry option
    if (decision == ReviewDecision.rejected) {
      return Row(
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          CustomButton.primary(
            text: _isSubmitting ? '提交中...' : '拒绝并反馈',
            icon: Icons.refresh_rounded,
            onPressed: _isSubmitting ? null : _handleRejectionFlow,
            size: CustomButtonSize.small,
          ),
        ],
      );
    }

    // For needs_modification, show modify and reject
    if (decision == ReviewDecision.needsModification) {
      return Row(
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          if (widget.onReject != null || widget.onDecision != null)
            CustomButton.text(
              text: '取消',
              onPressed: _isSubmitting
                  ? null
                  : () => _handleDecision(ReviewDecision.rejected),
              size: CustomButtonSize.small,
            ),
          const SizedBox(width: DS.spacing8),
          if (widget.onModify != null || widget.onDecision != null)
            CustomButton.primary(
              text: _isSubmitting ? '提交中...' : '修改计划',
              icon: Icons.edit_rounded,
              onPressed: _isSubmitting ? null : () => _handleDecision(decision),
              size: CustomButtonSize.small,
              customGradient: gradient,
            ),
        ],
      );
    }

    // For requires_confirmation, show approve and reject
    return Row(
      mainAxisAlignment: MainAxisAlignment.end,
      children: [
        if (widget.onReject != null || widget.onDecision != null)
          CustomButton.text(
            text: '取消',
            onPressed: _isSubmitting
                ? null
                : () => _handleDecision(ReviewDecision.rejected),
            size: CustomButtonSize.small,
          ),
        const SizedBox(width: DS.spacing8),
        if (widget.onApprove != null || widget.onDecision != null)
          CustomButton.primary(
            text: _isSubmitting ? '提交中...' : '批准执行',
            icon: Icons.check_rounded,
            onPressed: _isSubmitting
                ? null
                : () {
                    HapticFeedback.mediumImpact();
                    _handleDecision(ReviewDecision.approved);
                  },
            size: CustomButtonSize.small,
            customGradient: gradient,
          ),
      ],
    );
  }

  LinearGradient _getDecisionGradient(ReviewDecision decision) {
    switch (decision) {
      case ReviewDecision.approved:
        return DS.successGradient;
      case ReviewDecision.rejected:
        return DS.errorGradient;
      case ReviewDecision.needsModification:
        return DS.warningGradient;
      case ReviewDecision.requiresConfirmation:
        return DS.infoGradient;
    }
  }

  Color _getDecisionColor(ReviewDecision decision) {
    switch (decision) {
      case ReviewDecision.approved:
        return DS.success;
      case ReviewDecision.rejected:
        return DS.error;
      case ReviewDecision.needsModification:
        return DS.warning;
      case ReviewDecision.requiresConfirmation:
        return DS.info;
    }
  }

  IconData _getDecisionIcon(ReviewDecision decision) {
    switch (decision) {
      case ReviewDecision.approved:
        return Icons.check_circle_rounded;
      case ReviewDecision.rejected:
        return Icons.cancel_rounded;
      case ReviewDecision.needsModification:
        return Icons.edit_note_rounded;
      case ReviewDecision.requiresConfirmation:
        return Icons.help_outline_rounded;
    }
  }

  String _getDecisionTitle(ReviewDecision decision) {
    switch (decision) {
      case ReviewDecision.approved:
        return '计划已通过审查';
      case ReviewDecision.rejected:
        return '计划未通过审查';
      case ReviewDecision.needsModification:
        return '计划需要修改';
      case ReviewDecision.requiresConfirmation:
        return '请确认计划';
    }
  }

  IconData _getCategoryIcon(String category) {
    switch (category.toLowerCase()) {
      case 'safety':
        return Icons.shield_rounded;
      case 'completeness':
        return Icons.checklist_rounded;
      case 'alignment':
        return Icons.align_horizontal_left_rounded;
      case 'quality':
        return Icons.star_rounded;
      case 'suggestion':
      default:
        return Icons.lightbulb_rounded;
    }
  }
}

class _RejectionFeedback {
  const _RejectionFeedback({
    required this.category,
    this.note,
  });

  final String category;
  final String? note;
}

class _FeedbackOption {
  const _FeedbackOption({
    required this.value,
    required this.label,
  });

  final String value;
  final String label;
}

extension on _PlanReviewCardState {
  Future<_RejectionFeedback?> _showRejectionFeedbackSheet() async {
    final controller = TextEditingController();
    const options = [
      _FeedbackOption(value: 'tasks_too_many', label: '任务太多'),
      _FeedbackOption(value: 'tasks_too_few', label: '任务太少'),
      _FeedbackOption(value: 'difficulty_too_high', label: '难度太高'),
      _FeedbackOption(value: 'difficulty_too_low', label: '难度太低'),
      _FeedbackOption(value: 'schedule_unreasonable', label: '时间安排不合理'),
      _FeedbackOption(value: 'missing_key_task', label: '缺少关键任务'),
      _FeedbackOption(value: 'other', label: '其他（自定义）'),
    ];
    String? selected;
    var showError = false;

    try {
      return await showModalBottomSheet<_RejectionFeedback>(
        context: context,
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
        isScrollControlled: true,
        builder: (context) => StatefulBuilder(
          builder: (context, setSheetState) {
            final isDark = Theme.of(context).brightness == Brightness.dark;

            void submit() {
              final note = controller.text.trim();
              final needsNote = selected == 'other';
              if (selected == null || (needsNote && note.isEmpty)) {
                setSheetState(() => showError = true);
                return;
              }
              Navigator.of(context).pop(
                _RejectionFeedback(
                    category: selected!, note: note.isEmpty ? null : note,),
              );
            }

            return Padding(
              padding: EdgeInsets.only(
                bottom: MediaQuery.of(context).viewInsets.bottom,
              ),
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.surface,
                  borderRadius: const BorderRadius.vertical(
                    top: Radius.circular(24),
                  ),
                ),
                child: SafeArea(
                  top: false,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        width: 40,
                        height: 4,
                        margin: const EdgeInsets.symmetric(vertical: 12),
                        decoration: BoxDecoration(
                          color: isDark ? DS.neutral700 : DS.neutral300,
                          borderRadius: BorderRadius.circular(2),
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.symmetric(
                            horizontal: DS.spacing20,),
                        child: Row(
                          children: [
                            Icon(Icons.feedback_outlined,
                                color: DS.primaryBase,),
                            const SizedBox(width: DS.spacing12),
                            Text(
                              '告诉我们拒绝原因',
                              style: TextStyle(
                                fontSize: DS.fontSizeLg,
                                fontWeight: DS.fontWeightBold,
                                color: isDark ? DS.neutral100 : DS.neutral900,
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: DS.spacing12),
                      ...options.map((option) {
                        final isSelected = selected == option.value;
                        return InkWell(
                          onTap: () => setSheetState(() {
                            selected = option.value;
                            showError = false;
                          }),
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: DS.spacing20,
                              vertical: DS.spacing12,
                            ),
                            decoration: BoxDecoration(
                              color: isSelected
                                  ? DS.primaryBase.withValues(alpha: 0.08)
                                  : DS.surfacePrimary.withValues(alpha: 0),
                              border: Border(
                                left: BorderSide(
                                  color: isSelected
                                      ? DS.primaryBase
                                      : DS.surfacePrimary.withValues(alpha: 0),
                                  width: 3,
                                ),
                              ),
                            ),
                            child: Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    option.label,
                                    style: TextStyle(
                                      fontSize: DS.fontSizeBase,
                                      fontWeight: isSelected
                                          ? DS.fontWeightSemibold
                                          : DS.fontWeightRegular,
                                      color: isDark
                                          ? DS.neutral100
                                          : DS.neutral900,
                                    ),
                                  ),
                                ),
                                if (isSelected)
                                  Icon(
                                    Icons.check_circle,
                                    color: DS.primaryBase,
                                    size: DS.iconSizeBase,
                                  ),
                              ],
                            ),
                          ),
                        );
                      }),
                      Padding(
                        padding: const EdgeInsets.fromLTRB(
                          DS.spacing20,
                          DS.spacing8,
                          DS.spacing20,
                          0,
                        ),
                        child: TextField(
                          controller: controller,
                          maxLines: 2,
                          decoration: InputDecoration(
                            hintText: '补充说明（可选）',
                            errorText: showError && selected == 'other'
                                ? '请补充说明'
                                : null,
                          ),
                        ),
                      ),
                      if (showError && selected == null)
                        Padding(
                          padding: const EdgeInsets.only(
                            left: DS.spacing20,
                            right: DS.spacing20,
                            top: DS.spacing8,
                          ),
                          child: Align(
                            alignment: Alignment.centerLeft,
                            child: Text(
                              '请选择一个原因',
                              style: TextStyle(
                                color: DS.error,
                                fontSize: DS.fontSizeSm,
                              ),
                            ),
                          ),
                        ),
                      const SizedBox(height: DS.spacing16),
                      Padding(
                        padding: const EdgeInsets.symmetric(
                            horizontal: DS.spacing20,),
                        child: Row(
                          children: [
                            Expanded(
                              child: CustomButton.text(
                                text: '取消',
                                onPressed: () => Navigator.of(context).pop(),
                                size: CustomButtonSize.small,
                              ),
                            ),
                            const SizedBox(width: DS.spacing12),
                            Expanded(
                              child: CustomButton.primary(
                                text: '提交反馈',
                                onPressed: submit,
                                size: CustomButtonSize.small,
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: DS.spacing16),
                    ],
                  ),
                ),
              ),
            );
          },
        ),
      );
    } finally {
      controller.dispose();
    }
  }
}
