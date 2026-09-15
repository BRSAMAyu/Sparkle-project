import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class PartnerObservationControl extends StatelessWidget {
  const PartnerObservationControl({
    required this.onAccept,
    required this.onDecline,
    required this.onLater,
    required this.onTooFrequent,
    super.key,
  });

  final VoidCallback onAccept;
  final VoidCallback onDecline;
  final VoidCallback onLater;
  final VoidCallback onTooFrequent;

  @override
  Widget build(BuildContext context) => Wrap(
        spacing: 8,
        runSpacing: 8,
        children: [
          _ActionChipButton(
            icon: Icons.notifications_active_outlined,
            label: context.l10n.cahAcceptReminder,
            onPressed: onAccept,
          ),
          _ActionChipButton(
            icon: Icons.close_rounded,
            label: context.l10n.cahDeclineReminder,
            onPressed: onDecline,
          ),
          _ActionChipButton(
            icon: Icons.schedule_rounded,
            label: context.l10n.cahLaterReminder,
            onPressed: onLater,
          ),
          _ActionChipButton(
            icon: Icons.tune_rounded,
            label: context.l10n.cahTooFrequentReminder,
            onPressed: onTooFrequent,
          ),
        ],
      );
}

class _ActionChipButton extends StatelessWidget {
  const _ActionChipButton({
    required this.icon,
    required this.label,
    required this.onPressed,
  });

  final IconData icon;
  final String label;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Semantics(
      button: true,
      label: label,
      child: ActionChip(
        avatar: Icon(icon, size: 18, color: colorScheme.primary),
        label: Text(label),
        onPressed: onPressed,
      ),
    );
  }
}
