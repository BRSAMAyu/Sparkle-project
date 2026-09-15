import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/services/deep_link_service.dart';

void main() {
  test('deep link service accepts direct routes unchanged', () {
    expect(
      DeepLinkService.resolveRoute('/plans/plan-42?source=comeback_nudge'),
      '/plans/plan-42?source=comeback_nudge',
    );
  });

  test('deep link service resolves insights weekly route to real screen', () {
    final route = DeepLinkService.resolveRoute(
      'sparkle://insights/weekly?weekStart=2026-04-20&weekEnd=2026-04-26',
    );

    expect(route, isNotNull);
    final uri = Uri.parse(route!);
    expect(uri.path, '/learning/insights');
    expect(uri.queryParameters['initialPanel'], 'weeklyNarrative');
    expect(uri.queryParameters['weekStart'], '2026-04-20');
    expect(uri.queryParameters['weekEnd'], '2026-04-26');
  });

  test('deep link service preserves node review query parameters', () {
    final route = DeepLinkService.resolveRoute(
      'sparkle://node/node-42?review_mode=spaced_repetition',
    );

    expect(route, isNotNull);
    final uri = Uri.parse(route!);
    expect(uri.path, '/galaxy/node/node-42');
    expect(uri.queryParameters['review_mode'], 'spaced_repetition');
  });
}
