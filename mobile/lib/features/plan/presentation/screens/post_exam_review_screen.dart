import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/plan/data/models/exam_sprint_models.dart';
import 'package:sparkle/features/plan/data/repositories/exam_sprint_repository.dart';

class PostExamReviewScreen extends ConsumerStatefulWidget {
  const PostExamReviewScreen({
    required this.planId,
    required this.subjectName,
    super.key,
    this.successDelay = const Duration(milliseconds: 1400),
    this.onSuccess,
  });

  final String planId;
  final String subjectName;
  final Duration successDelay;
  final VoidCallback? onSuccess;

  @override
  ConsumerState<PostExamReviewScreen> createState() =>
      _PostExamReviewScreenState();
}

class _PostExamReviewScreenState extends ConsumerState<PostExamReviewScreen> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final TextEditingController _resultDescriptionController =
      TextEditingController();
  final TextEditingController _biggestChallengeController =
      TextEditingController();
  final TextEditingController _strategyFeedbackController =
      TextEditingController();
  final TextEditingController _selfAdviceController = TextEditingController();

  int _resultRating = 0;
  bool _isSubmitting = false;
  bool _showConfetti = false;

  String _titleL10n(AppLocalizations l10n) {
    final subject = widget.subjectName.trim();
    return subject.isEmpty ? l10n.planExamReviewNoSubject : l10n.planExamReviewSubject(subject);
  }

  @override
  void dispose() {
    _resultDescriptionController.dispose();
    _biggestChallengeController.dispose();
    _strategyFeedbackController.dispose();
    _selfAdviceController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => SparklePageScaffold(
        role: SparklePageRole.content,
        appBar: AppBar(
          leading: SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: const Icon(Icons.arrow_back),
            onPressed: () => context.pop(),
          ),
          title: Text(_titleL10n(context.l10n)),
        ),
        child: Stack(
          children: [
            ContentConstraint(
              child: Form(
                key: _formKey,
                child: ListView(
                  padding: const EdgeInsets.all(DS.spacing16),
                  children: [
                    _buildIntroCard(context),
                    const SizedBox(height: DS.spacing16),
                    _buildSection(
                      context,
                      title: context.l10n.planExamResult,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _buildRatingPicker(context),
                          const SizedBox(height: DS.spacing12),
                          TextFormField(
                            key: const ValueKey(
                              'post-exam-review-result-description',
                            ),
                            controller: _resultDescriptionController,
                            textInputAction: TextInputAction.next,
                            decoration: InputDecoration(
                              labelText: context.l10n.planExamScoreLabel,
                              hintText: context.l10n.planExamScoreHint,
                              prefixIcon: Icon(Icons.query_stats_outlined),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: DS.spacing12),
                    _buildSection(
                      context,
                      title: context.l10n.planExamBiggestChallenge,
                      child: TextFormField(
                        key: const ValueKey('post-exam-review-challenge'),
                        controller: _biggestChallengeController,
                        maxLines: 5,
                        minLines: 3,
                        textInputAction: TextInputAction.newline,
                        decoration: InputDecoration(
                          labelText: context.l10n.planExamChallengeLabel,
                          alignLabelWithHint: true,
                        ),
                        validator: _requiredField(context.l10n.planExamChallengeRequired),
                      ),
                    ),
                    const SizedBox(height: DS.spacing12),
                    _buildSection(
                      context,
                      title: context.l10n.planExamStrategyFeel,
                      child: TextFormField(
                        key: const ValueKey('post-exam-review-strategy'),
                        controller: _strategyFeedbackController,
                        maxLines: 5,
                        minLines: 3,
                        textInputAction: TextInputAction.newline,
                        decoration: InputDecoration(
                          labelText: context.l10n.planExamStrategyLabel,
                          alignLabelWithHint: true,
                        ),
                        validator: _requiredField(context.l10n.planExamStrategyRequired),
                      ),
                    ),
                    const SizedBox(height: DS.spacing12),
                    _buildSection(
                      context,
                      title: context.l10n.planExamFutureAdvice,
                      child: TextFormField(
                        key: const ValueKey('post-exam-review-self-advice'),
                        controller: _selfAdviceController,
                        maxLines: 4,
                        minLines: 2,
                        textInputAction: TextInputAction.newline,
                        decoration: InputDecoration(
                          labelText: context.l10n.planExamFutureLabel,
                          hintText: context.l10n.planExamFutureHint,
                          alignLabelWithHint: true,
                        ),
                      ),
                    ),
                    const SizedBox(height: DS.spacing20),
                    SparkleButton(
                      key: const ValueKey('post-exam-review-submit'),
                      label: context.l10n.planExamSubmitReview,
                      icon: const Icon(Icons.auto_awesome_rounded),
                      loading: _isSubmitting,
                      expand: true,
                      onPressed: _isSubmitting ? null : _submit,
                    ),
                    const SizedBox(height: DS.spacing20),
                  ],
                ),
              ),
            ),
            if (_showConfetti) const _SparkleConfettiOverlay(),
          ],
        ),
      );

  Widget _buildIntroCard(BuildContext context) => GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: DS.brandPrimary.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(14),
              ),
              child: const Icon(Icons.school_outlined),
            ),
            const SizedBox(width: DS.spacing12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _titleL10n(context.l10n),
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: DS.spacing4),
                  Text(
                    context.l10n.planExamReviewFeedback,
                    style: Theme.of(context)
                        .textTheme
                        .bodyMedium
                        ?.copyWith(color: DS.textSecondary),
                  ),
                ],
              ),
            ),
          ],
        ),
      );

  Widget _buildSection(
    BuildContext context, {
    required String title,
    required Widget child,
  }) =>
      GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: DS.spacing12),
            child,
          ],
        ),
      );

  Widget _buildRatingPicker(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.planExamStarRating,
            style: Theme.of(context).textTheme.titleSmall,
          ),
          const SizedBox(height: DS.spacing8),
          Row(
            children: List<Widget>.generate(5, (index) {
              final rating = index + 1;
              final selected = rating <= _resultRating;
              return IconButton(
                key: ValueKey('post-exam-review-rating-star-$rating'),
                tooltip: context.l10n.planExamStarTooltip(rating),
                onPressed: () => setState(() => _resultRating = rating),
                icon: Icon(
                  selected ? Icons.star_rounded : Icons.star_border_rounded,
                  color: selected ? Colors.amber.shade600 : DS.textTertiary,
                  size: 34,
                ),
              );
            }),
          ),
        ],
      );

  String? Function(String?) _requiredField(String message) => (String? value) {
        if (value == null || value.trim().isEmpty) {
          return message;
        }
        return null;
      };

  Future<void> _submit() async {
    if (widget.planId.trim().isEmpty) {
      AppFeedback.error(context, context.l10n.planExamMissingPlanId);
      return;
    }
    if (_resultRating == 0) {
      AppFeedback.warning(context, context.l10n.planExamSelectStarFirst);
      return;
    }
    if (!_formKey.currentState!.validate()) {
      return;
    }

    FocusScope.of(context).unfocus();
    setState(() => _isSubmitting = true);
    final request = PostExamReviewRequest(
      planId: widget.planId.trim(),
      resultRating: _resultRating,
      resultDescription: _resultDescriptionController.text.trim(),
      biggestChallenge: _biggestChallengeController.text.trim(),
      strategyFeedback: _strategyFeedbackController.text.trim(),
      selfAdvice: _selfAdviceController.text.trim(),
    );

    try {
      await ref
          .read(examSprintRepositoryProvider)
          .submitPostExamReview(request);
      if (!mounted) {
        return;
      }
      setState(() {
        _isSubmitting = false;
        _showConfetti = true;
      });
      AppFeedback.success(context, context.l10n.planExamReviewSaved);
      await Future<void>.delayed(widget.successDelay);
      if (!mounted) {
        return;
      }
      final onSuccess = widget.onSuccess;
      if (onSuccess != null) {
        onSuccess();
      } else {
        context.go('/home');
      }
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() => _isSubmitting = false);
      AppFeedback.error(context, e.toString());
    }
  }
}

class _SparkleConfettiOverlay extends StatelessWidget {
  const _SparkleConfettiOverlay();

  @override
  Widget build(BuildContext context) => Positioned.fill(
        child: IgnorePointer(
          child: ColoredBox(
            color: Colors.black.withValues(alpha: 0.08),
            child: Stack(
              children: [
                ...List<Widget>.generate(_pieces.length, (index) {
                  final piece = _pieces[index];
                  return TweenAnimationBuilder<double>(
                    tween: Tween<double>(begin: 0, end: 1),
                    duration: Duration(milliseconds: 620 + (index * 70)),
                    curve: Curves.easeOutCubic,
                    builder: (context, value, child) => Positioned(
                      left: MediaQuery.sizeOf(context).width * piece.dx,
                      top: 48 + (value * piece.fall),
                      child: Opacity(
                        opacity: (1 - (value * 0.4)).clamp(0, 1).toDouble(),
                        child: Transform.rotate(
                          angle: value * piece.rotation,
                          child: Icon(
                            Icons.auto_awesome_rounded,
                            color: piece.color,
                            size: piece.size,
                          ),
                        ),
                      ),
                    ),
                  );
                }),
                Center(
                  child: TweenAnimationBuilder<double>(
                    tween: Tween<double>(begin: 0.92, end: 1),
                    duration: const Duration(milliseconds: 360),
                    curve: Curves.easeOutBack,
                    builder: (context, scale, child) =>
                        Transform.scale(scale: scale, child: child),
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        color: DS.surfacePrimary.withValues(alpha: 0.94),
                        borderRadius: BorderRadius.circular(24),
                        border: Border.all(color: DS.borderSubtle),
                        boxShadow: DS.shadowLg,
                      ),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: DS.spacing20,
                          vertical: DS.spacing16,
                        ),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              Icons.auto_awesome_rounded,
                              color: DS.brandPrimary,
                              size: 34,
                            ),
                            const SizedBox(height: DS.spacing8),
                            Text(
                              context.l10n.planExamReviewComplete,
                              style: Theme.of(context).textTheme.titleMedium,
                            ),
                            const SizedBox(height: DS.spacing4),
                            Text(
                              context.l10n.planExamReviewEnterNext,
                              style: Theme.of(context)
                                  .textTheme
                                  .bodySmall
                                  ?.copyWith(color: DS.textSecondary),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
}

class _ConfettiPiece {
  const _ConfettiPiece({
    required this.dx,
    required this.fall,
    required this.rotation,
    required this.size,
    required this.color,
  });

  final double dx;
  final double fall;
  final double rotation;
  final double size;
  final Color color;
}

const List<_ConfettiPiece> _pieces = <_ConfettiPiece>[
  _ConfettiPiece(
    dx: 0.12,
    fall: 170,
    rotation: 3.0,
    size: 22,
    color: Color(0xFF7C3AED),
  ),
  _ConfettiPiece(
    dx: 0.24,
    fall: 230,
    rotation: 4.2,
    size: 18,
    color: Color(0xFF0EA5E9),
  ),
  _ConfettiPiece(
    dx: 0.38,
    fall: 190,
    rotation: 3.6,
    size: 24,
    color: Color(0xFFF59E0B),
  ),
  _ConfettiPiece(
    dx: 0.56,
    fall: 220,
    rotation: 4.8,
    size: 20,
    color: Color(0xFF10B981),
  ),
  _ConfettiPiece(
    dx: 0.72,
    fall: 180,
    rotation: 3.4,
    size: 22,
    color: Color(0xFFEC4899),
  ),
  _ConfettiPiece(
    dx: 0.86,
    fall: 240,
    rotation: 5.0,
    size: 18,
    color: Color(0xFF6366F1),
  ),
];
