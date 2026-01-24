import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:sparkle/core/models/intervention.dart';
import 'package:sparkle/core/widgets/card_intervention.dart';
import 'package:sparkle/core/widgets/modal_intervention.dart';
import 'package:sparkle/core/widgets/toast_intervention.dart';

class InterventionOverlay extends StatelessWidget {

  const InterventionOverlay({
    required this.intervention, required this.onAction, required this.onDismiss, super.key,
  });
  final InterventionPushMessage intervention;
  final ValueChanged<String> onAction;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) {
    if (intervention.level == InterventionLevel.silent) {
      return const SizedBox.shrink();
    }

    Widget content;
    switch (intervention.level) {
      case InterventionLevel.toast:
        content = ToastIntervention(
          intervention: intervention,
          onAction: onAction,
          onDismiss: onDismiss,
        );
      case InterventionLevel.card:
        content = CardIntervention(
          intervention: intervention,
          onAction: onAction,
          onDismiss: onDismiss,
        );
      case InterventionLevel.modal:
        content = ModalIntervention(
          intervention: intervention,
          onAction: onAction,
          onDismiss: onDismiss,
        );
      case InterventionLevel.silent:
        content = const SizedBox.shrink();
    }

    return GestureDetector(
      onTap: onDismiss,
      child: ColoredBox(
        color: Colors.black.withValues(alpha: 0.35),
        child: Stack(
          children: [
            Positioned.fill(
              child: ClipRect(
                child: BackdropFilter(
                  filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
                  child: const SizedBox.expand(),
                ),
              ),
            ),
            content,
          ],
        ),
      ),
    );
  }
}
