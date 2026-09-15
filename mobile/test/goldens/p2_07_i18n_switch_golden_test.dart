import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:golden_toolkit/golden_toolkit.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/calendar/data/models/calendar_day_aggregate.dart';
import 'package:sparkle/l10n/app_localizations_en.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';

void main() {
  tearDown(I18nService.instance.reset);

  testGoldens('P2-07 calendar summary switches zh/en copy', (tester) async {
    final aggregate = CalendarDayAggregate(
      date: _testDate,
      focusMinutes: 65,
    );

    I18nService.instance.updateLocale(const Locale('zh'), AppLocalizationsZh());
    final zhSummary = aggregate.summaryText;

    I18nService.instance.updateLocale(const Locale('en'), AppLocalizationsEn());
    final enSummary = aggregate.summaryText;

    expect(zhSummary, '1h专注');
    expect(enSummary, '1h focus');

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Center(
            child: _I18nSummaryGoldenHarness(
              zhSummary: zhSummary,
              enSummary: enSummary,
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await expectLater(
      find.byType(_I18nSummaryGoldenHarness),
      matchesGoldenFile('p2_07_calendar_summary_i18n.png'),
    );
  });
}

final _testDate = DateTime(2026, 5, 2);

class _I18nSummaryGoldenHarness extends StatelessWidget {
  const _I18nSummaryGoldenHarness({
    required this.zhSummary,
    required this.enSummary,
  });

  final String zhSummary;
  final String enSummary;

  @override
  Widget build(BuildContext context) => RepaintBoundary(
        child: Container(
          width: 320,
          padding: const EdgeInsets.all(16),
          color: Colors.white,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _SummaryRow(label: 'ZH', value: zhSummary),
              const SizedBox(height: 12),
              _SummaryRow(label: 'EN', value: enSummary),
            ],
          ),
        ),
      );
}

class _SummaryRow extends StatelessWidget {
  const _SummaryRow({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          SizedBox(
            width: 36,
            child: Text(
              label,
              style: const TextStyle(
                color: Color(0xFF525252),
                fontSize: 13,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(
                color: Color(0xFF171717),
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      );
}
