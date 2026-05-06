import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';

/// Phase-1 Entry Wire — single natural-language input that replaces step 0
/// of the legacy 5-step wizard.
///
/// Stays a dumb stateless widget; the wizard owns the controller and the
/// "Analyze" call so this widget can be reused (or A/B'd) without change.
class GoalIntentInput extends StatelessWidget {
  const GoalIntentInput({
    required this.controller,
    required this.onSubmit,
    required this.analyzing,
    super.key,
  });

  final TextEditingController controller;
  final Future<void> Function() onSubmit;
  final bool analyzing;

  static String _t(String zh, String en) =>
      I18nService.instance.isChinese ? zh : en;

  @override
  Widget build(BuildContext context) {
    return Column(
      key: const ValueKey('goal-intent-input'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          _t('告诉我你想达成什么', 'Tell me what you want to achieve'),
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w700,
              ),
        ),
        const SizedBox(height: 6),
        Text(
          _t(
            '一句话就好，比如「7天后计网考试基本没学想先别挂」',
            'One sentence works, e.g. "Computer Networks final in 7 days, barely studied"',
          ),
          style: TextStyle(color: DS.textSecondary, fontSize: 13),
        ),
        const SizedBox(height: 14),
        TextField(
          controller: controller,
          minLines: 2,
          maxLines: 5,
          enabled: !analyzing,
          textInputAction: TextInputAction.send,
          onSubmitted: (_) => onSubmit(),
          decoration: InputDecoration(
            hintText: _t('在这里输入', 'Type here'),
            prefixIcon: const Icon(Icons.flag_outlined),
          ),
        ),
        const SizedBox(height: 12),
        FilledButton.icon(
          onPressed: analyzing ? null : onSubmit,
          icon: analyzing
              ? const SizedBox(
                  height: 16,
                  width: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.auto_awesome_rounded),
          label: Text(
            analyzing
                ? _t('正在理解…', 'Understanding…')
                : _t('让我先看看你的情况', 'Let me read your situation'),
          ),
        ),
      ],
    );
  }
}
