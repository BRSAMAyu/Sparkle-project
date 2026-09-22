// S13 回归 · 设置页不得出现假「确定」保存按钮（批1-A 信任地基）。
//
// AUDIT S13 / D9：unified_settings_screen 为即时生效模型（每项开关拨动
// 即写 provider，无脏状态）。此前 AppBar 右上角有一颗 ghost「确定」，
// onPressed 只做 context.pop()——伪装手动保存语义，误导用户
// 「不按确定不生效」且零收益。修复后 AppBar 仅保留返回箭头。
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/features/user/presentation/screens/unified_settings_screen.dart';
import '../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() async {
    SharedPreferences.setMockInitialValues(<String, Object>{
      'bgm.enabled': false,
      'bgm.palette': 'adaptive',
      'bgm.mode': 'adaptive',
      'bgm.intensity': 'gentle',
      'bgm.variety': 'balanced',
      'bgm.reading_protection': true,
      'bgm.focus_priority': true,
      'bgm.lock_current_style': false,
      'sensory_feedback.aurora_linkage_enabled': true,
    });
    await BgmService.debugResetState();
  });

  tearDown(() async {
    await BgmService.debugResetState();
  });

  testWidgets('AppBar 不再渲染「确定」按钮，仅保留返回箭头与标题', (tester) async {
    tester.view.physicalSize = const Size(1200, 2200);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      ProviderScope(
        child: testMaterialApp(
          theme: AppThemes.lightTheme,
          home: const UnifiedSettingsScreen(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));

    final appBar = find.byType(AppBar);
    expect(appBar, findsOneWidget);
    expect(
      find.descendant(of: appBar, matching: find.text('确定')),
      findsNothing,
      reason: '即时生效设置页没有可「确定」的脏状态，假保存按钮已按 S13/D9 移除',
    );
    expect(
      find.descendant(of: appBar, matching: find.text('个人偏好')),
      findsOneWidget,
      reason: '页面标题必须保留',
    );
    expect(
      find.descendant(of: appBar, matching: find.byIcon(Icons.arrow_back)),
      findsOneWidget,
      reason: '返回入口由返回箭头承担',
    );
  });
}
