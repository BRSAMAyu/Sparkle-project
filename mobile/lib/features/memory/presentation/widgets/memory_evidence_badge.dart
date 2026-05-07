import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
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
    final color = switch (status) {
      MemoryEvidenceStatus.ok => DS.semanticSuccess,
      MemoryEvidenceStatus.redacted => DS.semanticWarning,
      MemoryEvidenceStatus.missing => DS.semanticError,
    };
    final count = evidenceCount;

    final chip = Chip(
      label: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (count != null && count > 0) ...[
            Text('$count ', style: TextStyle(color: color, fontWeight: DS.fontWeightSemibold)),
          ],
          Text(label, style: TextStyle(color: color)),
        ],
      ),
      backgroundColor: color.withValues(alpha: 0.12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: BorderSide(color: color.withValues(alpha: 0.4)),
      ),
    );

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
                '${summaries.length} ${I18nService.instance.isChinese ? '条证据' : 'sources'}',
                style: DS.bodySmall.copyWith(
                  color: DS.textPrimary,
                  fontWeight: DS.fontWeightSemibold,
                ),
              ),
              const Spacer(),
              Text(
                I18nService.instance.isChinese ? '长按查看全部' : 'Long-press for all',
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
