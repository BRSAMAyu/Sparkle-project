import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/seed_library/presentation/marketplace/marketplace_provider.dart';
import 'package:sparkle/features/seed_library/presentation/marketplace/marketplace_repository.dart';
import 'package:sparkle/features/seed_library/presentation/marketplace/marketplace_screen.dart';

import '../../../../shared/i18n_test_helper.dart';

class _NoopApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _ThrowingMarketplaceRepository extends MarketplaceRepository {
  _ThrowingMarketplaceRepository() : super(_NoopApiClient());

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw Exception('marketplace blew up');
}

/// A-SPEC3 改造 #2（N15/EE-G1）：marketplace_screen.dart:62 直出靶——
/// owner 面板（CustomErrorWidget.page）不豁免内容契约：
/// message 经唯一映射 owner（UserFacingError.from）人话化。
void main() {
  setUp(setUpI18nForTesting);

  testWidgets(
      'owner error panel humanizes provider error — no raw exception text',
      (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          marketplaceProvider.overrideWith(
            (ref) => MarketplaceNotifier(_ThrowingMarketplaceRepository()),
          ),
        ],
        child: testMaterialApp(home: const MarketplaceScreen()),
      ),
    );
    await tester.pump();
    await tester.pump();
    await tester.pump();

    expect(find.byType(CustomErrorWidget), findsOneWidget);
    expect(find.textContaining('marketplace blew up'), findsNothing);
    expect(find.textContaining('Exception'), findsNothing);
    // 默认映射桶：人话 + 稳定追溯码（owner 面板默认标题与 message 双处出现）。
    expect(find.textContaining('哎呀，出错了'), findsWidgets);
    expect(find.textContaining('[ERR-UNKNOWN]'), findsOneWidget);
  });
}
