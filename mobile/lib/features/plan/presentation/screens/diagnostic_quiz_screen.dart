import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/errors/user_facing_error.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/plan/data/models/exam_sprint_models.dart';
import 'package:sparkle/features/plan/data/repositories/exam_sprint_repository.dart';

/// P1-E5: minimal entry to the diagnostic mini-quiz.
///
/// Loads questions from POST /exam-sprint/diagnose/generate (answer keys stay
/// server-side), collects answers locally and submits them through
/// POST /exam-sprint/diagnose/grade using the returned diagnostic_id.
class DiagnosticQuizScreen extends ConsumerStatefulWidget {
  const DiagnosticQuizScreen({super.key, this.subject = '计算机网络'});

  final String subject;

  @override
  ConsumerState<DiagnosticQuizScreen> createState() =>
      _DiagnosticQuizScreenState();
}

class _DiagnosticQuizScreenState extends ConsumerState<DiagnosticQuizScreen> {
  DiagnosticGenerateResult? _generated;
  String? _error;
  bool _loading = true;
  bool _submitting = false;
  DiagnosticGradeResult? _result;

  final Map<String, String> _answers = <String, String>{};
  final Map<String, String> _confidences = <String, String>{};

  @override
  void initState() {
    super.initState();
    unawaited(_load());
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
      _result = null;
      _answers.clear();
      _confidences.clear();
    });
    try {
      final result = await ref.read(examSprintRepositoryProvider)
          .generateDiagnostic(subject: widget.subject);
      if (!mounted) {
        return;
      }
      setState(() {
        _generated = result;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = context.l10n.examDiagnosticLoadFailed;
        _loading = false;
      });
    }
  }

  Future<void> _submit() async {
    final generated = _generated;
    if (generated == null || _submitting) {
      return;
    }
    setState(() {
      _submitting = true;
    });
    try {
      final answers = <DiagnosticAnswerInput>[
        for (final question in generated.questions)
          DiagnosticAnswerInput(
            questionId: question.questionId,
            answer: _answers[question.questionId] ?? '',
            confidence: _confidences[question.questionId] ?? 'fuzzy',
          ),
      ];
      final result =
          await ref.read(examSprintRepositoryProvider).gradeDiagnostic(
                subject: widget.subject,
                diagnosticId: generated.diagnosticId,
                answers: answers,
              );
      if (!mounted) {
        return;
      }
      setState(() {
        _result = result;
        _submitting = false;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _submitting = false;
      });
      // N15（A-SPEC3 EE-G1）：裸 SnackBar 直出 toString → owner SnackBar + 人话文案
      ScaffoldMessenger.of(context).showSnackBar(
        SparkleSnackBar.error(UserFacingError.from(error)),
      );
    }
  }

  bool get _allAnswered {
    final generated = _generated;
    if (generated == null) return false;
    return generated.questions.every(
      (DiagnosticQuestion q) =>
          (_answers[q.questionId] ?? '').trim().isNotEmpty,
    );
  }

  @override
  Widget build(BuildContext context) => SparklePageScaffold(
        role: SparklePageRole.content,
        appBar: AppBar(
          // 甲式（A11Y-BATCH6B）：SparkleIconButton semanticLabel 单节点。
          leading: SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: const Icon(Icons.arrow_back),
            semanticLabel: context.l10n.back,
            onPressed: () => context.pop(),
          ),
          title: Text(context.l10n.examDiagnosticTitle),
        ),
        child: ContentConstraint(
          child: _buildBody(context),
        ),
      );

  Widget _buildBody(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              _error!,
              style: context.typo.bodyMedium.copyWith(color: DS.textSecondary),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: DS.spacing12),
            FilledButton.tonal(
              onPressed: () => unawaited(_load()),
              child: Text(context.l10n.examDiagnosticRetry),
            ),
          ],
        ),
      );
    }
    final result = _result;
    if (result != null) {
      return _ResultView(
        result: result,
        onRetry: () => unawaited(_load()),
      );
    }
    return _QuizForm(
      generated: _generated!,
      answers: _answers,
      confidences: _confidences,
      submitting: _submitting,
      allAnswered: _allAnswered,
      onAnswerChanged: (String questionId, String value) =>
          setState(() => _answers[questionId] = value),
      onConfidenceChanged: (String questionId, String value) =>
          setState(() => _confidences[questionId] = value),
      onSubmit: () => unawaited(_submit()),
    );
  }
}

class _QuizForm extends StatelessWidget {
  const _QuizForm({
    required this.generated,
    required this.answers,
    required this.confidences,
    required this.submitting,
    required this.allAnswered,
    required this.onAnswerChanged,
    required this.onConfidenceChanged,
    required this.onSubmit,
  });

  final DiagnosticGenerateResult generated;
  final Map<String, String> answers;
  final Map<String, String> confidences;
  final bool submitting;
  final bool allAnswered;
  final void Function(String questionId, String value) onAnswerChanged;
  final void Function(String questionId, String value) onConfidenceChanged;
  final VoidCallback onSubmit;

  @override
  Widget build(BuildContext context) {
    final l = context.l10n;
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(DS.spacing16),
      children: [
        Text(
          l.examDiagnosticIntro(
            generated.questionCount,
            generated.estimatedMinutes,
          ),
          style: context.typo.bodyMedium.copyWith(color: DS.textSecondary),
        ),
        const SizedBox(height: DS.spacing16),
        for (final DiagnosticQuestion question in generated.questions) ...[
          _QuestionCard(
            question: question,
            index: generated.questions.indexOf(question) + 1,
            total: generated.questions.length,
            answer: answers[question.questionId] ?? '',
            confidence: confidences[question.questionId] ?? 'fuzzy',
            onAnswerChanged: (String value) =>
                onAnswerChanged(question.questionId, value),
            onConfidenceChanged: (String value) =>
                onConfidenceChanged(question.questionId, value),
          ),
          const SizedBox(height: DS.spacing12),
        ],
        const SizedBox(height: DS.spacing4),
        FilledButton(
          onPressed: allAnswered && !submitting ? onSubmit : null,
          style: FilledButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: DS.spacing12),
          ),
          child: Text(
            submitting ? '...' : l.examDiagnosticSubmit,
            style: context.typo.labelLarge.copyWith(
              fontWeight: DS.fontWeightBold,
            ),
          ),
        ),
      ],
    );
  }
}

class _QuestionCard extends StatelessWidget {
  const _QuestionCard({
    required this.question,
    required this.index,
    required this.total,
    required this.answer,
    required this.confidence,
    required this.onAnswerChanged,
    required this.onConfidenceChanged,
  });

  final DiagnosticQuestion question;
  final int index;
  final int total;
  final String answer;
  final String confidence;
  final void Function(String value) onAnswerChanged;
  final void Function(String value) onConfidenceChanged;

  @override
  Widget build(BuildContext context) {
    final l = context.l10n;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary.withValues(alpha: 0.9),
        borderRadius: DS.borderRadius16,
        border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.12)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  l.examDiagnosticQuestionCounter(index, total),
                  style: context.typo.labelSmall.copyWith(
                    color: DS.textSecondary,
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
              ),
              _DomainChip(label: question.domain),
            ],
          ),
          const SizedBox(height: DS.spacing10),
          Text(
            question.stem,
            style: context.typo.bodyMedium.copyWith(
              color: DS.textPrimary,
              height: 1.4,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
          const SizedBox(height: DS.spacing12),
          if (question.isSingleChoice)
            RadioGroup<String>(
              groupValue: answer,
              onChanged: (String? value) {
                if (value != null) {
                  onAnswerChanged(value);
                }
              },
              child: Column(
                children: [
                  for (int i = 0; i < question.choices.length; i++)
                    RadioListTile<String>(
                      value: question.choices[i],
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                      activeColor: DS.brandPrimary,
                      title: Text(
                        question.choices[i],
                        style: context.typo.bodyMedium.copyWith(
                          color: DS.textPrimary,
                        ),
                      ),
                    ),
                ],
              ),
            )
          else
            _ShortAnswerField(
              initialAnswer: answer,
              hint: l.examDiagnosticShortAnswerHint,
              onChanged: onAnswerChanged,
            ),
          const SizedBox(height: DS.spacing8),
          Text(
            l.examDiagnosticConfidenceLabel,
            style: context.typo.labelSmall.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing6),
          Wrap(
            spacing: DS.spacing8,
            children: [
              _ConfidenceChip(
                label: l.examConfidenceCertain,
                value: 'certain',
                groupValue: confidence,
                onSelected: onConfidenceChanged,
              ),
              _ConfidenceChip(
                label: l.examConfidenceFuzzy,
                value: 'fuzzy',
                groupValue: confidence,
                onSelected: onConfidenceChanged,
              ),
              _ConfidenceChip(
                label: l.examConfidenceGuess,
                value: 'guess',
                groupValue: confidence,
                onSelected: onConfidenceChanged,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ShortAnswerField extends StatefulWidget {
  const _ShortAnswerField({
    required this.initialAnswer,
    required this.hint,
    required this.onChanged,
  });

  final String initialAnswer;
  final String hint;
  final void Function(String value) onChanged;

  @override
  State<_ShortAnswerField> createState() => _ShortAnswerFieldState();
}

class _ShortAnswerFieldState extends State<_ShortAnswerField> {
  late final TextEditingController _controller =
      TextEditingController(text: widget.initialAnswer);

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => TextField(
        controller: _controller,
        onChanged: widget.onChanged,
        maxLines: 2,
        decoration: InputDecoration(hintText: widget.hint),
      );
}

class _DomainChip extends StatelessWidget {
  const _DomainChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: DS.brandPrimary.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.16)),
        ),
        child: Text(
          label,
          style: context.typo.labelSmall.copyWith(color: DS.brandPrimary),
        ),
      );
}

class _ConfidenceChip extends StatelessWidget {
  const _ConfidenceChip({
    required this.label,
    required this.value,
    required this.groupValue,
    required this.onSelected,
  });

  final String label;
  final String value;
  final String groupValue;
  final void Function(String value) onSelected;

  @override
  Widget build(BuildContext context) {
    final selected = value == groupValue;
    return ChoiceChip(
      label: Text(label),
      selected: selected,
      onSelected: (_) => onSelected(value),
    );
  }
}

class _ResultView extends StatelessWidget {
  const _ResultView({required this.result, required this.onRetry});

  final DiagnosticGradeResult result;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final l = context.l10n;
    final pathLabel = result.recommendedPath == 'score_max'
        ? l.examDiagnosticPathScoreMax
        : l.examDiagnosticPathMinimumPass;
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(DS.spacing16),
      children: [
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(DS.spacing20),
          decoration: BoxDecoration(
            color: DS.brandPrimary.withValues(alpha: 0.06),
            borderRadius: DS.borderRadius16,
            border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.14)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                l.examDiagnosticScore(result.estimatedScoreNow),
                style: context.typo.headingLarge.copyWith(
                  color: DS.textPrimary,
                  fontWeight: DS.fontWeightBold,
                ),
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                l.examDiagnosticPassProbability(
                  '${(result.passProbability.clamp(0.0, 1.0) * 100).round()}%',
                ),
                style: context.typo.bodyMedium.copyWith(
                  color: DS.textSecondary,
                ),
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                pathLabel,
                style: context.typo.labelLarge.copyWith(
                  color: DS.brandPrimary,
                  fontWeight: DS.fontWeightBold,
                ),
              ),
            ],
          ),
        ),
        if (result.topBottlenecks.isNotEmpty) ...[
          const SizedBox(height: DS.spacing16),
          Text(
            l.examDiagnosticBottlenecks,
            style: context.typo.titleLarge.copyWith(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightBold,
            ),
          ),
          const SizedBox(height: DS.spacing8),
          for (final bottleneck in result.topBottlenecks) ...[
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(DS.spacing12),
              decoration: BoxDecoration(
                color: DS.surfaceSecondary.withValues(alpha: 0.9),
                borderRadius: DS.borderRadius16,
                border: Border.all(color: DS.warning.withValues(alpha: 0.2)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          bottleneck.nodeName,
                          style: context.typo.labelLarge.copyWith(
                            color: DS.textPrimary,
                            fontWeight: DS.fontWeightBold,
                          ),
                        ),
                      ),
                      Text(
                        '${bottleneck.mastery.round()}',
                        style: context.typo.labelLarge.copyWith(
                          color: DS.warning,
                          fontWeight: DS.fontWeightBold,
                        ),
                      ),
                    ],
                  ),
                  if (bottleneck.reason != null &&
                      bottleneck.reason!.isNotEmpty) ...[
                    const SizedBox(height: DS.spacing4),
                    Text(
                      bottleneck.reason!,
                      style: context.typo.bodySmall.copyWith(
                        color: DS.textSecondary,
                        height: 1.35,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: DS.spacing8),
          ],
        ],
        const SizedBox(height: DS.spacing8),
        FilledButton.tonal(
          onPressed: onRetry,
          child: Text(l.examDiagnosticRetry),
        ),
      ],
    );
  }
}
