import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/utils/text_rendering.dart';

class DailyContextLine extends StatelessWidget {
  const DailyContextLine({
    super.key,
    this.text,
    this.isLoading = false,
  });

  final String? text;
  final bool isLoading;

  @override
  Widget build(BuildContext context) {
    final line = text?.trim();
    // The sentence is composed server-side (rule or AI) and frequently glues a
    // Latin task title directly onto CJK prose; space it at the display layer.
    final displayLine =
        line == null || line.isEmpty ? '' : autoSpaceCjkLatin(line);
    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing20,
          DS.spacing12,
          DS.spacing20,
          DS.spacing4,
        ),
        child: AnimatedSwitcher(
          duration: context.reduceMotion ? Duration.zero : DS.quick,
          child: isLoading && (line == null || line.isEmpty)
              ? const _DailyContextLineSkeleton()
              : Text(
                  displayLine.isEmpty
                      ? context.l10n.dailyContextDefault
                      : displayLine,
                  key: ValueKey(line),
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                  style: context.typo.titleLarge.copyWith(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightBold,
                    height: 1.28,
                  ),
                ),
        ),
      ),
    );
  }
}

class _DailyContextLineSkeleton extends StatelessWidget {
  const _DailyContextLineSkeleton();

  @override
  Widget build(BuildContext context) => const Column(
        key: ValueKey('daily-context-line-skeleton'),
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SparkleSkeleton(width: 260, height: 24, borderRadius: 12),
          SizedBox(height: DS.spacing8),
          SparkleSkeleton(width: 190, height: 20, borderRadius: 10),
        ],
      );
}
