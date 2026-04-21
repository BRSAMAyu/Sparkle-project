import 'package:flutter/material.dart';

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
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '初始画像',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(
              '只会作为弱先验，后续会被真实互动修正。',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 12),
            ...widget.questions.map(_buildQuestion),
            const SizedBox(height: 12),
            Row(
              children: [
                TextButton(
                  onPressed: _submitting ? null : () async => widget.onSkip(),
                  child: const Text('跳过'),
                ),
                const Spacer(),
                FilledButton(
                  onPressed: _submitting ? null : _handleSubmit,
                  child: Text(_submitting ? '提交中...' : '保存'),
                ),
              ],
            ),
          ],
        ),
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
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(question['title']?.toString() ?? ''),
          const SizedBox(height: 8),
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
