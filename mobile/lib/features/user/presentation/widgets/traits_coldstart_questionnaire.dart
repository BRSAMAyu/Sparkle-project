import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class TraitsColdstartQuestionnaire extends StatefulWidget {
  const TraitsColdstartQuestionnaire({
    super.key,
    required this.questions,
    required this.onSubmit,
    required this.onSkip,
  });

  final List<Map<String, dynamic>> questions;
  final Future<void> Function(Map<String, String> answers) onSubmit;
  final Future<void> Function() onSkip;

  @override
  State<TraitsColdstartQuestionnaire> createState() =>
      _TraitsColdstartQuestionnaireState();
}

class _TraitsColdstartQuestionnaireState
    extends State<TraitsColdstartQuestionnaire> {
  final Map<String, String> _answers = <String, String>{};
  bool _submitting = false;

  @override
  Widget build(BuildContext context) {
    return GraphiteCardSurface(
      padding: const EdgeInsets.all(DS.spacing16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.userTraitsColdstart,
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            context.l10n.userTraitsColdstartHint,
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: DS.spacing12),
          ...widget.questions.map(_buildQuestion),
          const SizedBox(height: DS.spacing12),
          Row(
            children: [
              TextButton(
                onPressed: _submitting ? null : () async => widget.onSkip(),
                child: Text(context.l10n.userSkip),
              ),
              const Spacer(),
              FilledButton(
                onPressed: _submitting ? null : _handleSubmit,
                child: Text(_submitting ? context.l10n.userSubmitting : context.l10n.userSave),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildQuestion(Map<String, dynamic> question) {
    final questionId = question['id']?.toString() ?? '';
    final options =
        (question['options'] as List<dynamic>? ?? const <dynamic>[])
            .whereType<Map<String, dynamic>>()
            .toList();
    return Padding(
      padding: const EdgeInsets.only(bottom: DS.spacing16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(question['title']?.toString() ?? ''),
          const SizedBox(height: DS.spacing8),
          ...options.map(
            (option) => RadioListTile<String>(
              contentPadding: EdgeInsets.zero,
              title: Text(option['label']?.toString() ?? ''),
              value: option['id']?.toString() ?? '',
              groupValue: _answers[questionId],
              onChanged: (value) {
                if (value == null) return;
                setState(() {
                  _answers[questionId] = value;
                });
              },
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _handleSubmit() async {
    setState(() {
      _submitting = true;
    });
    try {
      await widget.onSubmit(_answers);
    } finally {
      if (mounted) {
        setState(() {
          _submitting = false;
        });
      }
    }
  }
}
