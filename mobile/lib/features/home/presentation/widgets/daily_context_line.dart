import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/core/services/i18n_service.dart';

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
    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing20,
          DS.spacing12,
          DS.spacing20,
          DS.spacing4,
        ),
        child: AnimatedSwitcher(
          duration: DS.quick,
          child: isLoading && (line == null || line.isEmpty)
              ? const _DailyContextLineSkeleton()
              : Text(
                  line == null || line.isEmpty
                      ? (I18nService.instance.isChinese
                          ? '早上好，今天先从一小步开始，把节奏找回来就很好。'
                          : 'Good morning. Start with one small step today—finding your rhythm is enough.')
                      : line,
                  key: ValueKey(line),
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                  style: context.sparkleTypography.titleLarge.copyWith(
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
