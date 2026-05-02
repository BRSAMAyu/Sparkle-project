import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/home/presentation/providers/understanding_snapshot_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/understanding_panel.dart';

class ChatUnderstandingDrawerButton extends ConsumerWidget {
  const ChatUnderstandingDrawerButton({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final snapshot = ref.watch(understandingSnapshotProvider).valueOrNull;
    final scheme = Theme.of(context).colorScheme;
    final subtitle = snapshot == null || snapshot.claims.isEmpty
        ? context.l10n.understandingChatDrawerSubtitleEmpty
        : context.l10n.understandingChatDrawerSubtitle(snapshot.claims.length);
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 6),
      child: Semantics(
        button: true,
        label: context.l10n.understandingChatDrawerOpen,
        child: Material(
          color: scheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(8),
          child: InkWell(
            borderRadius: BorderRadius.circular(8),
            onTap: () => _openUnderstandingSheet(context),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              child: Row(
                children: [
                  Icon(Icons.psychology_alt_outlined, color: scheme.primary),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          context.l10n.understandingChatDrawerTitle,
                          style:
                              Theme.of(context).textTheme.labelLarge?.copyWith(
                                    color: scheme.onSurface,
                                    fontWeight: FontWeight.w700,
                                  ),
                        ),
                        Text(
                          subtitle,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style:
                              Theme.of(context).textTheme.bodySmall?.copyWith(
                                    color: scheme.onSurfaceVariant,
                                  ),
                        ),
                      ],
                    ),
                  ),
                  Icon(
                    Icons.keyboard_arrow_down_rounded,
                    color: scheme.onSurfaceVariant,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  void _openUnderstandingSheet(BuildContext context) {
    unawaited(
      showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        showDragHandle: true,
        builder: (sheetContext) => SafeArea(
          child: Padding(
            padding: EdgeInsets.only(
              left: 16,
              right: 16,
              bottom: MediaQuery.viewInsetsOf(sheetContext).bottom + 16,
            ),
            child: const SingleChildScrollView(
              child: UnderstandingPanel(
                compact: true,
                initiallyExpanded: true,
                surface: 'chat',
              ),
            ),
          ),
        ),
      ),
    );
  }
}
