import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/chat/data/models/chat_mode.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_mode_provider.dart';

class ModeSuggestionCard extends ConsumerStatefulWidget {
  const ModeSuggestionCard({
    required this.suggestion,
    super.key,
  });

  final Map<String, dynamic> suggestion;

  @override
  ConsumerState<ModeSuggestionCard> createState() => _ModeSuggestionCardState();
}

class _ModeSuggestionCardState extends ConsumerState<ModeSuggestionCard> {
  bool _dismissed = false;

  @override
  Widget build(BuildContext context) {
    if (_dismissed) return const SizedBox.shrink();
    final suggestedMode = widget.suggestion['suggested_mode']?.toString() ?? '';
    final reason = widget.suggestion['reason']?.toString() ?? '';
    if (suggestedMode.isEmpty) return const SizedBox.shrink();

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 8),
      color: Theme.of(context).colorScheme.tertiaryContainer,
      child: Padding(
        padding: const EdgeInsets.all(DS.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.l10n.chatModeSuggestionTitle,
              style: Theme.of(context).textTheme.titleSmall,
            ),
            if (reason.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text(
                  reason,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
            const SizedBox(height: DS.md),
            Row(
              children: [
                SparkleButton.primary(
                  label: context.l10n.chatModeSwitch,
                  onPressed: () {
                    final mode = ChatMode.fromApiValue(suggestedMode);
                    ref.read(chatModeProvider.notifier).setMode(mode);
                    ref.read(lastMultiAgentModeProvider.notifier).setMode(mode);
                    setState(() => _dismissed = true);
                  },
                ),
                const SizedBox(width: DS.sm),
                SparkleButton.ghost(
                  label: context.l10n.chatModeKeepCurrent,
                  onPressed: () => setState(() => _dismissed = true),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
