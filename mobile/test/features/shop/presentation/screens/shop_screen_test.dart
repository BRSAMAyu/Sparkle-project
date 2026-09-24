import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/shop/data/repositories/shop_repository.dart';
import 'package:sparkle/features/shop/presentation/providers/shop_provider.dart';
import 'package:sparkle/features/shop/presentation/screens/shop_screen.dart';

import '../../../../shared/i18n_test_helper.dart';

class _NoopApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

/// 抛错仓储：loadShopItems 的 catch 会把异常洗进 state.error
/// （provider 通道存量 ratchet 项），UI 侧必须经 owner 人话化后渲染。
class _ThrowingShopRepository extends ShopRepository {
  _ThrowingShopRepository() : super(_NoopApiClient());

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw Exception('shop feed blew up');
}

/// A-SPEC3 改造 #2（N15/EE-G6）：shop_screen.dart:112-131 直出靶——
/// 空态与错误态拆为互斥分支：空态不再混排原始异常红字；
/// 错误态走 owner（CustomErrorWidget.page）+ 人话化文案。
void main() {
  setUp(setUpI18nForTesting);

  testWidgets(
      'empty+error renders owner error page with humanized copy — '
      'no raw exception in the empty state', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          shopItemsProvider.overrideWith(
            (ref) => ShopItemsNotifier(_ThrowingShopRepository(), ref),
          ),
        ],
        child: testMaterialApp(home: const ShopScreen()),
      ),
    );
    await tester.pump();
    await tester.pump();
    await tester.pump();

    // 空态插画与「暂无物品」不得与错误混排。
    expect(find.text('暂无物品'), findsNothing);
    // 原始异常不入 UI；错误经 owner 面板人话化（默认标题与 message 双处出现）。
    expect(find.textContaining('shop feed blew up'), findsNothing);
    expect(find.textContaining('Exception'), findsNothing);
    expect(find.textContaining('哎呀，出错了'), findsWidgets);
    expect(find.textContaining('[ERR-UNKNOWN]'), findsOneWidget);
    expect(find.byType(CustomErrorWidget), findsOneWidget);
  });

  testWidgets(
      'plain empty (no error) shows the guided empty state with no error copy',
      (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          shopItemsProvider.overrideWith((ref) {
            final notifier = ShopItemsNotifier(_ThrowingShopRepository(), ref);
            // 加载完成后清错误、保持空列表：纯空态。
            Future<void>.delayed(Duration.zero, () {
              notifier.state = ShopItemsState();
            });
            return notifier;
          }),
        ],
        child: testMaterialApp(home: const ShopScreen()),
      ),
    );
    await tester.pump();
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));
    await tester.pump();

    expect(find.text('暂无物品'), findsOneWidget);
    expect(find.textContaining('[ERR-'), findsNothing);
    expect(find.textContaining('Exception'), findsNothing);
    expect(find.byType(CustomErrorWidget), findsNothing);
  });
}
