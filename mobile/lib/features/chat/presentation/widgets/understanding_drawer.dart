import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/home/presentation/providers/understanding_snapshot_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/understanding_panel.dart';
import 'package:sparkle/features/memory/memory_routes.dart';

class ChatUnderstandingDrawerButton extends ConsumerWidget {
  const ChatUnderstandingDrawerButton({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final snapshot = ref.watch(understandingSnapshotProvider).valueOrNull;
    final scheme = Theme.of(context).colorScheme;
    // U-03 黑话移除：不再用「N 条可纠正判断」计数做主呈现。
    final subtitle = snapshot == null || snapshot.claims.isEmpty
        ? context.l10n.understandingChatDrawerSubtitleEmpty
        : context.l10n.understandingChatDrawerSubtitle;
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
      showSensoryModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        builder: (sheetContext) => SafeArea(
          child: Padding(
            padding: EdgeInsets.only(
              left: 16,
              right: 16,
              bottom: MediaQuery.viewInsetsOf(sheetContext).bottom + 16,
            ),
            child: SingleChildScrollView(
              // M-10 深链：chat 内的理解面板同样可以进入完整理解视图；
              // 面板嵌在模态 sheet 里，先关 sheet 再走根路由导航。
              child: UnderstandingPanel(
                compact: true,
                initiallyExpanded: true,
                surface: 'chat',
                onOpenFullUnderstanding: () {
                  final navigator = Navigator.of(sheetContext);
                  if (navigator.canPop()) {
                    navigator.pop();
                  }
                  unawaited(context.push(MemoryRoutes.understanding));
                },
              ),
            ),
          ),
        ),
      ),
    );
  }
}
