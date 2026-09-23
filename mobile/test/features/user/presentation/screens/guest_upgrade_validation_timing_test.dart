import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/user/presentation/screens/guest_upgrade_screen.dart';

import '../../../../shared/i18n_test_helper.dart';

/// N25（A-SPEC5 v1.5）校验三段制时序断言（guest_upgrade 屏）：
/// ① 未提交不报错；② 提交全量兜底；③ 改对即时消错。
void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  Future<void> pumpUpgrade(WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        child: testMaterialApp(home: const GuestUpgradeScreen()),
      ),
    );
    await tester.pumpAndSettle();
  }

  Future<void> enlargeViewport(WidgetTester tester) async {
    tester.view
      ..physicalSize = const Size(800, 2400)
      ..devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
  }

  testWidgets('未提交输入非法不报错；提交爆出全量错误；修正即时消错', (tester) async {
    await enlargeViewport(tester);
    await pumpUpgrade(tester);

    // ① 未提交：填一个过短用户名与非法邮箱，都不报错。
    await tester.enterText(find.byType(TextFormField).at(0), 'ab');
    await tester.enterText(find.byType(TextFormField).at(1), 'bad-email');
    await tester.pump();
    expect(find.text('用户名至少需要3个字符'), findsNothing,
        reason: '未提交前不得提前报错（三段制第一段）',);
    expect(find.textContaining('邮箱格式'), findsNothing);

    // ② 提交：用户名长度、邮箱格式、密码长度错误一并行内爆出。
    await tester.tap(find.widgetWithText(SparkleButton, '使用邮箱升级'));
    await tester.pump();
    expect(find.text('用户名至少需要3个字符'), findsOneWidget);
    expect(find.textContaining('邮箱格式'), findsOneWidget);
    expect(find.text('密码至少需要8个字符'), findsOneWidget);

    // ③ 修正用户名 → 即时消错；邮箱错误保持。
    await tester.enterText(find.byType(TextFormField).at(0), 'abc');
    await tester.pump();
    expect(find.text('用户名至少需要3个字符'), findsNothing,
        reason: '首提交后改对字段即时消错（三段制第三段）',);
    expect(find.textContaining('邮箱格式'), findsOneWidget,
        reason: '未动字段错误保持',);
  });
}
