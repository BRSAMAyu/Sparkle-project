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

  static PlanReviewResult fromJson(Map<String, dynamic> json) => PlanReviewResult(
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
  });

  final PlanReviewResult review;
  final VoidCallback? onApprove;
  final VoidCallback? onReject;
  final VoidCallback? onModify;

  @override
  State<PlanReviewCard> createState() => _PlanReviewCardState();
}

class _PlanReviewCardState extends State<PlanReviewCard>
    with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late Animation<double> _iconScaleAnimation;
  late AnimationController _pressController;
  late AnimationController _slideInController;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);

    _iconScaleAnimation = Tween<double>(begin: 1.0, end: 1.08).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
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
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _pressController.dispose();
    _slideInController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final decision = widget.review.decision;
    final gradient = _getDecisionGradient(decision);
    final color = _getDecisionColor(decision);
    final icon = _getDecisionIcon(decision);
    final title = _getDecisionTitle(decision);

    // For approved plans, don't show action buttons (auto-approved)
    final showActions = !widget.review.autoApproved &&
        decision != ReviewDecision.approved &&
        (widget.onApprove != null ||
            widget.onReject != null ||
            widget.onModify != null);

    return SlideTransition(
      position: Tween<Offset>(
        begin: const Offset(0, -0.1),
        end: Offset.zero,
      ).animate(CurvedAnimation(
        parent: _slideInController,
        curve: Curves.easeOut,
      ),),
      child: GestureDetector(
        onTapDown: showActions ? (_) => _pressController.forward() : null,
        onTapUp: showActions ? (_) => _pressController.reverse() : null,
        onTapCancel: showActions ? () => _pressController.reverse() : null,
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
                  // Gradient stripe
                  Positioned(
                    left: 0,
                    top: 0,
                    bottom: 0,
                    width: 5,
                    child: Container(
                      decoration: BoxDecoration(
                        gradient: gradient,
                      ),
                    ),
                  ),

                  // Shimmer overlay for pending reviews
                  if (showActions)
                    Positioned.fill(
                      child: TweenAnimationBuilder<double>(
                        tween: Tween(begin: -2.0, end: 2.0),
                        duration: const Duration(seconds: 3),
                        builder: (context, value, child) => Container(
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                              colors: [
                                Colors.transparent,
                                color.withValues(alpha: 0.08),
                                Colors.transparent,
                              ],
                              stops: [
                                (value - 0.3).clamp(0.0, 1.0),
                                value.clamp(0.0, 1.0),
                                (value + 0.3).clamp(0.0, 1.0),
                              ],
                            ),
                          ),
                        ),
                        onEnd: () {
                          if (mounted) setState(() {});
                        },
                      ),
                    ),

                  Padding(
                    padding: const EdgeInsets.all(DS.spacing16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Header with icon and title
                        Row(
                          children: [
                            AnimatedBuilder(
                              animation: _iconScaleAnimation,
                              builder: (context, child) => Transform.scale(
                                scale: showActions ? _iconScaleAnimation.value : 1.0,
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
                                    color: Colors.white,
                                    size: DS.iconSizeBase,
                                  ),
                                ),
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
                            // Decision badge
                            _buildDecisionBadge(decision),
                          ],
                        ),

                        // Comments section
                        if (widget.review.comments.isNotEmpty) ...[
                          const SizedBox(height: DS.spacing16),
                          _buildCommentsSection(),
                        ],

                        // Confidence bar
                        if (widget.review.confidence > 0 && !widget.review.autoApproved) ...[
                          const SizedBox(height: DS.spacing12),
                          _buildConfidenceBar(),
                        ],

                        // Action buttons
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
    );
  }

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
          if (infoComments.isNotEmpty)
              const SizedBox(height: DS.spacing8),
        ],
        if (infoComments.isNotEmpty &&
            widget.review.decision != ReviewDecision.rejected)
          _buildCommentGroup('建议', infoComments, DS.info),
      ],
    );
  }

  Widget _buildCommentGroup(String title, List<ReviewComment> comments, Color color) => Column(
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
        ...comments.take(3).map((comment) => Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing6),
              child: _buildCommentItem(comment, color),
            )),
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
            text: '重新描述',
            icon: Icons.refresh_rounded,
            onPressed: widget.onReject,
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
          if (widget.onReject != null)
            CustomButton.text(
              text: '取消',
              onPressed: widget.onReject,
              size: CustomButtonSize.small,
            ),
          const SizedBox(width: DS.spacing8),
          if (widget.onModify != null)
            CustomButton.primary(
              text: '修改计划',
              icon: Icons.edit_rounded,
              onPressed: widget.onModify,
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
        if (widget.onReject != null)
          CustomButton.text(
            text: '取消',
            onPressed: widget.onReject,
            size: CustomButtonSize.small,
          ),
        const SizedBox(width: DS.spacing8),
        if (widget.onApprove != null)
          CustomButton.primary(
            text: '批准执行',
            icon: Icons.check_rounded,
            onPressed: () {
              HapticFeedback.mediumImpact();
              widget.onApprove?.call();
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
