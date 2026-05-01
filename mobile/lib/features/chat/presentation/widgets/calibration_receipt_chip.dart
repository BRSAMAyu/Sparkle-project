import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

const kCalibrationReceiptType = 'calibration_receipt';

class CalibrationReceiptChip extends StatefulWidget {
  const CalibrationReceiptChip({
    required this.receipt,
    super.key,
  });

  final Map<String, dynamic> receipt;

  @override
  State<CalibrationReceiptChip> createState() => _CalibrationReceiptChipState();
}

class _CalibrationReceiptChipState extends State<CalibrationReceiptChip> {
  bool _expanded = false;
  bool _dismissed = false;
  bool _visible = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        setState(() => _visible = true);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_dismissed) return const SizedBox.shrink();

    final receipt = CalibrationReceiptViewData.fromReceipt(widget.receipt);
    if (!receipt.hasVisibleText) return const SizedBox.shrink();

    final summary = receipt.summary.isNotEmpty ? receipt.summary : receipt.what;
    final semanticLabel = _expanded
        ? context.l10n.calibrationReceiptCollapse
        : context.l10n.calibrationReceiptExpand;

    return AnimatedOpacity(
      opacity: _visible ? 1 : 0,
      duration: const Duration(milliseconds: 220),
      curve: Curves.easeOutCubic,
      child: AnimatedSize(
        duration: const Duration(milliseconds: 180),
        curve: Curves.easeOutCubic,
        alignment: Alignment.topCenter,
        child: Container(
          margin: const EdgeInsets.only(top: 6, bottom: 2),
          child: Semantics(
            button: true,
            label: '$summary. $semanticLabel',
            child: ExcludeSemantics(
              child: Material(
                color: Colors.transparent,
                child: InkWell(
                  borderRadius: BorderRadius.circular(8),
                  onTap: () {
                    unawaited(
                      SensoryFeedbackService.emit(SensoryFeedbackEvent.tap),
                    );
                    setState(() => _expanded = !_expanded);
                  },
                  child: Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: DS.surfaceHigh.withValues(alpha: 0.62),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: DS.brandPrimary.withValues(alpha: 0.22),
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(
                              Icons.tune_rounded,
                              size: 14,
                              color: DS.brandPrimary,
                            ),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                summary,
                                style: DS.labelSmall.copyWith(
                                  color: DS.textSecondary,
                                  fontWeight: FontWeight.w600,
                                ),
                                maxLines: _expanded ? 3 : 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            const SizedBox(width: 4),
                            Icon(
                              _expanded
                                  ? Icons.keyboard_arrow_up_rounded
                                  : Icons.keyboard_arrow_down_rounded,
                              size: 16,
                              color: DS.textTertiary,
                            ),
                            Semantics(
                              button: true,
                              label: context.l10n.calibrationReceiptDismiss,
                              child: IconButton(
                                visualDensity: VisualDensity.compact,
                                constraints: const BoxConstraints(
                                  minWidth: 32,
                                  minHeight: 32,
                                ),
                                padding: EdgeInsets.zero,
                                tooltip: context.l10n.calibrationReceiptDismiss,
                                icon: Icon(
                                  Icons.close_rounded,
                                  size: 14,
                                  color: DS.textTertiary,
                                ),
                                onPressed: () {
                                  unawaited(
                                    SensoryFeedbackService.emit(
                                      SensoryFeedbackEvent.selection,
                                    ),
                                  );
                                  setState(() => _dismissed = true);
                                },
                              ),
                            ),
                          ],
                        ),
                        if (_expanded) ...[
                          const SizedBox(height: 10),
                          _ReceiptDetailLine(
                            icon: Icons.auto_fix_high_outlined,
                            label: context.l10n.calibrationReceiptWhatChanged,
                            value: receipt.what,
                          ),
                          _ReceiptDetailLine(
                            icon: Icons.feedback_outlined,
                            label: context.l10n.calibrationReceiptWhyChanged,
                            value: receipt.why,
                          ),
                          _ReceiptDetailLine(
                            icon: Icons.update_outlined,
                            label: context.l10n.calibrationReceiptNextTime,
                            value: receipt.nextTime,
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _ReceiptDetailLine extends StatelessWidget {
  const _ReceiptDetailLine({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final cleanValue = value.trim();
    if (cleanValue.isEmpty) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 14, color: DS.brandPrimary),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: DS.labelSmall.copyWith(color: DS.textTertiary),
                ),
                const SizedBox(height: 2),
                Text(
                  cleanValue,
                  style: DS.bodySmall.copyWith(color: DS.textPrimary),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class CalibrationReceiptViewData {
  const CalibrationReceiptViewData({
    required this.summary,
    required this.what,
    required this.why,
    required this.nextTime,
  });

  factory CalibrationReceiptViewData.fromReceipt(
    Map<String, dynamic> receipt,
  ) =>
      CalibrationReceiptViewData(
        summary: _localizedText(
          receipt,
          const ['summary', 'receipt_summary', 'title'],
        ),
        what: _localizedText(
          receipt,
          const ['what_changed', 'what'],
          allowList: true,
        ),
        why: _localizedText(receipt, const ['why_changed', 'why']),
        nextTime: _localizedText(
          receipt,
          const ['next_time', 'next_time_effect', 'future_behavior'],
        ),
      );

  final String summary;
  final String what;
  final String why;
  final String nextTime;

  bool get hasVisibleText =>
      summary.isNotEmpty ||
      what.isNotEmpty ||
      why.isNotEmpty ||
      nextTime.isNotEmpty;

  static String _localizedText(
    Map<String, dynamic> receipt,
    List<String> keys, {
    bool allowList = false,
  }) {
    for (final key in keys) {
      final explicit = _pickLocalized(receipt[key]);
      if (explicit.isNotEmpty) return explicit;

      final suffix = I18nService.instance.isChinese ? '_zh' : '_en';
      final suffixed = _pickLocalized(receipt['$key$suffix']);
      if (suffixed.isNotEmpty) return suffixed;

      final i18n = _pickLocalized(receipt['${key}_i18n']);
      if (i18n.isNotEmpty) return i18n;

      if (allowList && receipt[key] is List) {
        final items = (receipt[key] as List)
            .map(_pickLocalized)
            .where((item) => item.isNotEmpty)
            .toList(growable: false);
        if (items.isNotEmpty) return items.join(' · ');
      }
    }
    return '';
  }

  static String _pickLocalized(dynamic raw) {
    if (raw == null) return '';
    if (raw is String) return raw.trim();
    if (raw is List) {
      return raw
          .map(_pickLocalized)
          .where((item) => item.isNotEmpty)
          .join(' · ');
    }
    if (raw is Map) {
      final map = Map<String, dynamic>.from(raw);
      final preferredKeys = I18nService.instance.isChinese
          ? const ['zh', 'zh_CN', 'zh-Hans', 'cn', 'default']
          : const ['en', 'en_US', 'en-US', 'default'];
      for (final key in preferredKeys) {
        final value = _pickLocalized(map[key]);
        if (value.isNotEmpty) return value;
      }
      for (final value in map.values) {
        final text = _pickLocalized(value);
        if (text.isNotEmpty) return text;
      }
    }
    return '';
  }
}

bool isCalibrationReceipt(Map<String, dynamic> receipt) {
  final rawType = (receipt['receipt_type'] ?? receipt['type'] ?? '')
      .toString()
      .trim()
      .toLowerCase();
  final hasCalibrationShape = receipt.containsKey('what_changed') &&
      (receipt.containsKey('why_changed') || receipt.containsKey('next_time'));
  return rawType == kCalibrationReceiptType ||
      rawType == 'aurora_calibration_receipt' ||
      hasCalibrationShape ||
      receipt.containsKey('calibration_receipt');
}
