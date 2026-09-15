import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// Degraded notice for dialogs (v2.1)
class ParseDegradedNotice extends StatelessWidget {
  const ParseDegradedNotice({super.key, this.reason});

  final String? reason;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        color: DS.brandPrimary.shade50,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: DS.brandPrimary.shade200),
        ),
        child: Row(
          children: [
            Icon(Icons.warning_amber_rounded, color: DS.brandPrimary.shade700),
            const SizedBox(width: DS.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    l10n.commonOperationWarning,
                    style: TextStyle(
                      fontWeight: DS.fontWeightBold,
                      color: DS.brandPrimary.shade900,
                    ),
                  ),
                  if (reason != null) ...[
                    const SizedBox(height: DS.xs),
                    Text(
                      reason!,
                      style: TextStyle(
                        fontSize: 13,
                        color: DS.brandPrimary.shade800,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      );
  }
}
