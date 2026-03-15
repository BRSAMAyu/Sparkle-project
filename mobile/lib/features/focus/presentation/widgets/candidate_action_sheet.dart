import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/network/dio_provider.dart';
import 'package:sparkle/features/focus/data/models/candidate_action_model.dart';
import 'package:sparkle/features/focus/data/services/candidate_feedback_service.dart';

/// Bottom sheet displaying predicted candidate actions
///
/// Shows 1-3 candidate actions with:
/// - Action type icon and title
/// - Confidence indicator
/// - Reason for suggestion
/// - Accept/Dismiss buttons
class CandidateActionSheet extends ConsumerStatefulWidget {
  const CandidateActionSheet({
    required this.candidates,
    this.onAccept,
    this.onDismiss,
    super.key,
  });

  final List<CandidateActionModel> candidates;
  final void Function(CandidateActionModel)? onAccept;
  final void Function(CandidateActionModel)? onDismiss;

  @override
  ConsumerState<CandidateActionSheet> createState() =>
      _CandidateActionSheetState();
}

class _CandidateActionSheetState extends ConsumerState<CandidateActionSheet> {
  late final CandidateFeedbackService _feedbackService;
  final Set<String> _dismissedCandidates = {};

  @override
  void initState() {
    super.initState();
    _feedbackService = CandidateFeedbackService(ref.read(dioProvider));
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    // Filter out dismissed candidates
    final visibleCandidates = widget.candidates
        .where((c) => !_dismissedCandidates.contains(c.id))
        .toList();

    if (visibleCandidates.isEmpty) {
      // Auto-close if all dismissed
      Navigator.of(context).pop();
      return const SizedBox.shrink();
    }

    return Container(
      padding: const EdgeInsets.fromLTRB(DS.lg, DS.md, DS.lg, DS.lg),
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Handle bar
          Container(
            width: 40,
            height: 4,
            margin: const EdgeInsets.only(bottom: DS.lg),
            decoration: BoxDecoration(
              color: DS.neutral300,
              borderRadius: BorderRadius.circular(2),
            ),
          ),

          // Header
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(DS.sm),
                decoration: BoxDecoration(
                  gradient: DS.secondaryGradient,
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  Icons.lightbulb_outline,
                  color: DS.brandPrimaryConst,
                  size: 18,
                ),
              ),
              const SizedBox(width: DS.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      l10n.focusCandidateTitle,
                      style: const TextStyle(
                        fontWeight: DS.fontWeightBold,
                        fontSize: 16,
                      ),
                    ),
                    Text(
                      l10n.focusCandidateSubtitle,
                      style: TextStyle(color: DS.neutral500, fontSize: 12),
                    ),
                  ],
                ),
              ),
              SparkleIconButton(
                variant: ButtonVariant.ghost,
                size: 36,
                icon: const Icon(Icons.close, size: 20),
                onPressed: () {
                  // Record implicit ignore for all visible candidates
                  for (final candidate in visibleCandidates) {
                    _recordFeedback(candidate, 'ignore');
                  }
                  Navigator.of(context).pop();
                },
              ),
            ],
          ),

          const SizedBox(height: DS.md),

          // Candidate cards
          ...visibleCandidates.map(
            (candidate) => _CandidateCard(
              candidate: candidate,
              onAccept: () => _handleAccept(candidate),
              onDismiss: () => _handleDismiss(candidate),
            ),
          ),

          const SizedBox(height: DS.sm),

          // Footer hint
          Text(
            l10n.focusCandidateFooterHint,
            style: TextStyle(
              color: DS.neutral400,
              fontSize: 11,
            ),
          ),
        ],
      ),
    );
  }

  void _handleAccept(CandidateActionModel candidate) {
    _recordFeedback(candidate, 'accept');
    widget.onAccept?.call(candidate);
    Navigator.of(context).pop();
  }

  void _handleDismiss(CandidateActionModel candidate) {
    setState(() {
      _dismissedCandidates.add(candidate.id);
    });
    _recordFeedback(candidate, 'dismiss');
    widget.onDismiss?.call(candidate);
  }

  void _recordFeedback(CandidateActionModel candidate, String feedbackType) {
    _feedbackService.recordFeedback(
      candidateId: candidate.id,
      actionType: candidate.actionType,
      feedbackType: feedbackType,
    );
  }
}

/// Individual candidate action card
class _CandidateCard extends StatelessWidget {
  const _CandidateCard({
    required this.candidate,
    required this.onAccept,
    required this.onDismiss,
  });

  final CandidateActionModel candidate;
  final VoidCallback onAccept;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) {
    final color = Color(candidate.getColorValue());
    final l10n = context.l10n;

    return Container(
      margin: const EdgeInsets.only(bottom: DS.md),
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Action type and confidence
          Row(
            children: [
              Text(
                candidate.getIcon(),
                style: const TextStyle(fontSize: 20),
              ),
              const SizedBox(width: DS.sm),
              Expanded(
                child: Text(
                  candidate.title,
                  style: TextStyle(
                    fontWeight: DS.fontWeightBold,
                    fontSize: 15,
                    color: color,
                  ),
                ),
              ),
              _ConfidenceBadge(confidence: candidate.confidence),
            ],
          ),

          const SizedBox(height: DS.xs),

          // Reason
          Text(
            candidate.reason,
            style: TextStyle(
              fontSize: 13,
              color: DS.neutral700,
              height: 1.4,
            ),
          ),

          const SizedBox(height: DS.md),

          // Action buttons
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              SparkleButton(
                label: l10n.focusCandidateDismiss,
                variant: ButtonVariant.ghost,
                onPressed: onDismiss,
              ),
              const SizedBox(width: DS.sm),
              SparkleButton(
                label: l10n.focusCandidateAccept,
                onPressed: onAccept,
                icon: Icon(Icons.play_arrow_rounded, color: color),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// Confidence indicator badge
class _ConfidenceBadge extends StatelessWidget {
  const _ConfidenceBadge({required this.confidence});

  final double confidence;

  @override
  Widget build(BuildContext context) {
    final percentage = (confidence * 100).round();
    final color = _getConfidenceColor(confidence);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: DS.sm, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.2),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        '$percentage%',
        style: TextStyle(
          fontSize: 11,
          fontWeight: DS.fontWeightBold,
          color: color,
        ),
      ),
    );
  }

  Color _getConfidenceColor(double confidence) {
    if (confidence >= 0.75) {
      return DS.success;
    } else if (confidence >= 0.65) {
      return DS.warning;
    } else {
      return DS.textSecondary;
    }
  }
}
