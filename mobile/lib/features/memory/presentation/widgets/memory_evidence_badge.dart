import 'package:flutter/material.dart';
import 'package:sparkle/core/design/components/atoms/semantic_pill.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';


enum MemoryEvidenceStatus {
  ok,
  missing,
  redacted,
}

class MemoryEvidenceBadge extends StatelessWidget {
  const MemoryEvidenceBadge({
    required this.status,
    super.key,
    this.evidenceCount,
    this.onTap,
    this.onLongPress,
    this.quickPeekSummaries,
  });

  final MemoryEvidenceStatus status;
  final int? evidenceCount;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;
  final List<String>? quickPeekSummaries;

  @override
  Widget build(BuildContext context) {
    final zh = I18nService.instance.isChinese;
    final label = switch (status) {
      MemoryEvidenceStatus.ok => 'OK',
      MemoryEvidenceStatus.redacted => zh ? '已隐藏' : 'Redacted',
      MemoryEvidenceStatus.missing => zh ? '缺失' : 'Missing',
    };
    final count = evidenceCount;

    final tone = switch (status) {
      MemoryEvidenceStatus.ok => PillTone.success,
      MemoryEvidenceStatus.redacted => PillTone.warning,
      MemoryEvidenceStatus.missing => PillTone.danger,
    };
    final pillLabel =
        (count != null && count > 0) ? '$count $label' : label;
    // 点击/长按仍由外层 GestureDetector 承担，pill 本体保持非交互（与原等价）。
    final chip = SemanticPill(label: pillLabel, tone: tone, dense: true);

    if (onTap == null && onLongPress == null) return chip;

    return GestureDetector(
      onTap: onTap,
      onLongPress: onLongPress,
      child: chip,
    );
  }
}

class EvidenceQuickPeek extends StatelessWidget {
  const EvidenceQuickPeek({
    required this.summaries,
    required this.status,
    super.key,
  });

  final List<String> summaries;
  final MemoryEvidenceStatus status;

  static void show(
    BuildContext context, {
    required List<String> summaries,
    required MemoryEvidenceStatus status,
  }) {
    final overlay = Overlay.of(context);
    late OverlayEntry entry;
    entry = OverlayEntry(
      builder: (ctx) => GestureDetector(
        onTap: () => entry.remove(),
        behavior: HitTestBehavior.translucent,
        child: Material(
          color: Colors.transparent,
          child: Stack(
            children: [
              Positioned(
                top: MediaQuery.of(context).size.height * 0.18,
                left: DS.md,
                right: DS.md,
                child: EvidenceQuickPeek(
                  summaries: summaries,
                  status: status,
                ),
              ),
            ],
          ),
        ),
      ),
    );
    overlay.insert(entry);
    Future.delayed(const Duration(seconds: 4), () {
      if (entry.mounted) entry.remove();
    });
  }

  @override
  Widget build(BuildContext context) {
    final color = switch (status) {
      MemoryEvidenceStatus.ok => DS.semanticSuccess,
      MemoryEvidenceStatus.redacted => DS.semanticWarning,
      MemoryEvidenceStatus.missing => DS.semanticError,
    };

    return Container(
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        color: DS.surfacePanel,
        borderRadius: DS.borderRadius12,
        border: Border.all(color: DS.borderSubtle),
        boxShadow: DS.shadowSm,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  color: color,
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: DS.spacing8),
              Text(
                '${summaries.length} ${context.l10n.auto_sources}',
                style: DS.bodySmall.copyWith(
                  color: DS.textPrimary,
                  fontWeight: DS.fontWeightSemibold,
                ),
              ),
              const Spacer(),
              Text(
                context.l10n.auto_longpressforall,
                style: DS.labelSmall.copyWith(color: DS.textSecondary),
              ),
            ],
          ),
          if (summaries.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            ...summaries.take(3).map(
                  (s) => Padding(
                    padding: const EdgeInsets.only(bottom: DS.spacing4),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(Icons.circle, size: 5, color: DS.textSecondary),
                        const SizedBox(width: DS.spacing6),
                        Expanded(
                          child: Text(
                            s,
                            style: DS.bodySmall.copyWith(color: DS.textSecondary),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
          ],
        ],
      ),
    );
  }
}
