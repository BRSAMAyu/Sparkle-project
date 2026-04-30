import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/features/user/presentation/screens/ai_ops_analysis_screen.dart';
import '../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  testWidgets('ai ops analysis screen renders utilization chips from export payload', (
    tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          aiOpsExportProvider(14).overrideWith(
            (ref) async => {
              'window_days': 14,
              'overview': {
                'requests_total': 12,
                'success_rate_percent': 91.0,
                'fallback_rate_percent': 10.0,
                'total_cost_usd': 0.0123,
                'avg_first_token_ms': 820.0,
                'avg_total_duration_ms': 4100.0,
                'execution_conversion_rate_percent': 36.0,
                'avg_prompt_utilization_percent': 79.5,
                'avg_inference_utilization_percent': 72.5,
              },
              'items': [
                {
                  'chat_mode': 'standard',
                  'success_rate_percent': 91.0,
                  'fallback_rate_percent': 10.0,
                  'total_cost_usd': 0.0123,
                  'avg_first_token_ms': 820.0,
                  'avg_total_duration_ms': 4100.0,
                  'execution_conversion_rate_percent': 36.0,
                  'avg_prompt_utilization_percent': 79.5,
                  'avg_inference_utilization_percent': 72.5,
                  'prompt_utilization_known_count': 8,
                  'inference_utilization_known_count': 7,
                },
              ],
              'trend_series': const <Map<String, dynamic>>[],
              'generated_at': '2026-04-20T00:00:00Z',
            },
          ),
          predictionAnalyticsByDaysProvider(14).overrideWith(
            (ref) async => {
              'window_days': 14,
              'funnel': {
                'impressions': 10,
                'accepts': 5,
                'executions': 3,
                'ctr_percent': 50.0,
                'accept_to_execution_percent': 60.0,
              },
              'by_surface': const <String, dynamic>{},
              'top_actions': const <Map<String, dynamic>>[],
            },
          ),
        ],
        child: const MaterialApp(
          home: AiOpsAnalysisScreen(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    expect(find.text('prompt 命中'), findsAtLeastNWidgets(1));
    expect(find.text('79.5%'), findsAtLeastNWidgets(1));
    expect(find.text('推理命中'), findsAtLeastNWidgets(1));
    expect(find.text('72.5%'), findsAtLeastNWidgets(1));
    expect(find.textContaining('known 8/7'), findsOneWidget);
  });
}
