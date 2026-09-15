import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

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

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Column(
      key: const ValueKey('goal-intent-input'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.goalIntentTitle,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w700,
              ),
        ),
        const SizedBox(height: 6),
        Text(
          l10n.goalIntentHint,
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
            hintText: l10n.goalIntentInputHint,
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
            analyzing ? l10n.goalIntentUnderstanding : l10n.goalIntentAnalyze,
          ),
        ),
      ],
    );
  }
}
