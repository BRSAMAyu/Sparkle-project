import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

class ContextReceiptBar extends StatelessWidget {
  const ContextReceiptBar({required this.rawMetadata, super.key});

  final Map<String, dynamic>? rawMetadata;

  @override
  Widget build(BuildContext context) {
    final receipt = _parseReceipt();
    if (receipt == null) return const SizedBox.shrink();

    return _ReceiptChip(receipt: receipt);
  }

  Map<String, dynamic>? _parseReceipt() {
    if (rawMetadata == null) return null;
    final raw = rawMetadata!['context_receipt'];
    if (raw == null) return null;
    if (raw is Map<String, dynamic>) return raw;
    if (raw is String) {
      try {
        return json.decode(raw) as Map<String, dynamic>;
      } catch (_) {
        return null;
      }
    }
    return null;
  }
}

class _ReceiptChip extends StatelessWidget {
  const _ReceiptChip({required this.receipt});

  final Map<String, dynamic> receipt;

  @override
  Widget build(BuildContext context) {
    final usedCount = receipt['used_count'] as int? ?? 0;
    final excludedCount = receipt['excluded_count'] as int? ?? 0;
    final reason = receipt['decision_reason'] as String? ?? '';

    if (usedCount == 0 && reason.isEmpty) return const SizedBox.shrink();

    return Container(
      margin: const EdgeInsets.only(top: 6, bottom: 2),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: DS.surfaceHigh.withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Row(
        children: [
          Icon(Icons.auto_awesome, size: 13, color: DS.brandPrimary),
          const SizedBox(width: 6),
          Expanded(
            child: Text(
              reason.isNotEmpty
                  ? reason
                  : 'Aurora · used $usedCount source${usedCount != 1 ? 's' : ''}${excludedCount > 0 ? ' / skipped $excludedCount' : ''}',
              style: DS.labelSmall.copyWith(color: DS.textSecondary),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          if (usedCount > 0)
            _SourceCountBadge(count: usedCount),
        ],
      ),
    );
  }
}

class _SourceCountBadge extends StatelessWidget {
  const _SourceCountBadge({required this.count});

  final int count;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
        decoration: BoxDecoration(
          color: DS.brandPrimary20,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Text(
          '$count',
          style: DS.labelSmall.copyWith(color: DS.brandPrimary, fontSize: 10),
        ),
      );
}
