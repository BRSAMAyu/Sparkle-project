import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/features/community/presentation/widgets/bonfire_widget.dart';
import '../../../../shared/i18n_test_helper.dart';
/// V4-U11「统一火堆呈现」钉（一正一反）：
/// 正——等级徽标走 l10n（zh 文案「火堆等级 {level}」，语言随环境）；
/// 反——原「Crackle/Silent」假开关已移除：任何参数下都不渲染该开关、
/// 不出现 Crackle/Silent 文案（假 affordance = 假成功家族，不留存）。
void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    setUpI18nForTesting();
  });
  tearDown(tearDownI18n);

  Future<void> pumpBonfire(
    WidgetTester tester, {
    required int level,
  }) async {
    await tester.pumpWidget(
      testMaterialApp(
        home: const Scaffold(
          body: Center(child: BonfireWidget(level: 3, size: 80)),
        ),
      ),
    );
    // 火堆呼吸动画是无限 repeat：推进几帧即断言，不 pumpAndSettle。
    await tester.pump(const Duration(milliseconds: 300));
    await tester.pump(const Duration(milliseconds: 300));
  }

  testWidgets('level badge renders localized label for the flame level',
      (tester) async {
    await pumpBonfire(tester, level: 3);

    final badge = tester.widget<Text>(
      find.byKey(const ValueKey('bonfire-level-badge')),
    );
    // 正面：徽标 = l10n 文案（zh），不硬编码「Lv.3」。
    expect(badge.data, '火堆等级 3');
  });

  testWidgets('fake crackle/silent toggle is gone for every configuration',
      (tester) async {
    await pumpBonfire(tester, level: 5);

    // 反面：假声效开关不可再被渲染（假 affordance 移除，不假成功）。
    expect(find.text('Crackle'), findsNothing);
    expect(find.text('Silent'), findsNothing);
    expect(find.byIcon(Icons.graphic_eq_rounded), findsNothing);
    expect(find.byIcon(Icons.volume_mute_outlined), findsNothing);
    // 且徽标仍如实显示等级。
    expect(find.text('火堆等级 3'), findsOneWidget);
  });
}
