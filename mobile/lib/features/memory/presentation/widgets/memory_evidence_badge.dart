import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

enum MemoryEvidenceStatus {
  ok,
  missing,
  redacted,
}

class MemoryEvidenceBadge extends StatelessWidget {
  const MemoryEvidenceBadge({required this.status, super.key});

  final MemoryEvidenceStatus status;

  @override
  Widget build(BuildContext context) {
    final label = switch (status) {
      MemoryEvidenceStatus.ok => 'OK',
      MemoryEvidenceStatus.redacted => '已隐藏',
      MemoryEvidenceStatus.missing => '缺失',
    };
    final color = switch (status) {
      MemoryEvidenceStatus.ok => DS.semanticSuccess,
      MemoryEvidenceStatus.redacted => DS.semanticWarning,
      MemoryEvidenceStatus.missing => DS.semanticError,
    };
    return Chip(
      label: Text(label, style: TextStyle(color: color)),
      backgroundColor: color.withValues(alpha: 0.12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: BorderSide(color: color.withValues(alpha: 0.4)),
      ),
    );
  }
}
