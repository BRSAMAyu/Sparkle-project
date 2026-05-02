import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/tools/data/repositories/tool_history_repository.dart';

class ToolContextEffectFeedback {
  const ToolContextEffectFeedback._();

  static void show({
    required BuildContext context,
    required WidgetRef ref,
    required String toolLabel,
    required int? eventId,
  }) {
    if (eventId == null || !context.mounted) {
      return;
    }

    AppFeedback.undoable(
      context: context,
      message: context.l10n.toolsContextEffectMessage(toolLabel),
      actionLabel: context.l10n.toolsContextEffectUndo,
      onAction: () {
        unawaited(_forget(context: context, ref: ref, eventId: eventId));
      },
    );
  }

  static Future<void> _forget({
    required BuildContext context,
    required WidgetRef ref,
    required int eventId,
  }) async {
    final deleted =
        await ref.read(toolHistoryRepositoryProvider).forgetToolEvent(eventId);
    if (!context.mounted) {
      return;
    }
    if (deleted) {
      AppFeedback.info(context, context.l10n.toolsContextEffectUndone);
    } else {
      AppFeedback.warning(context, context.l10n.toolsContextEffectUndoFailed);
    }
  }
}
