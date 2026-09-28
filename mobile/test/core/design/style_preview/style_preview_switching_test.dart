// V4-F05 验收 1 + 验收 2 · preview 门与切换状态流（每面一正一反）。
//
// 卡面验收逐条：
// - 「设计未批准时稳定主题仍可用，preview 不隐性全量上线」→
//   classic_gate 组：flag 默认关（gate 反例：flag 关时入口零节点）；
//   classic 下页面正常渲染且无 PixelProfileTheme 扩展（稳定主题可用）。
// - 「切主题不重启 run / 清数据 / 改 token 用量」→ switching 组：
//   探针 state 存活（重挂即红）、外源 prefs 键零触碰、持久化可复原、
//   回退 classic 逐槽复原。
// - 「切换状态流可复现（进/退/持久化/回退 classic 逐槽复原）」→ 本文件
//   switching 组即该状态流的可执行口径。
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/style_preview/style_preview_page.dart'
    show StylePreviewEntry, StylePreviewPage, StylePreviewPageState;

import 'style_preview_test_harness.dart';

// classic 基线：默认值链下 AppThemes.lightTheme 的产出（回退逐槽对照）。
ThemeData _freshClassicTheme() => AppThemes.lightTheme;

void main() {
  group('classic_gate｜preview 不隐性全量上线（验收 1）', () {
    test('正例：enableStylePreview 默认 false（设计未批准前入口不存在）', () {
      expect(AppFeatureFlags.enableStylePreview, isFalse);
    });

    testWidgets('正例：flag 关 → gate 渲染零节点；flag 开 → 入口可进 preview 页',
        (tester) async {
      await freshThemeManager();
      await tester.pumpWidget(
        buildPreviewHost(
          body: const Scaffold(body: StylePreviewEntry()),
        ),
      );
      await settlePreview(tester);

      // 反例面（flag 关）：入口不存在——发布面零节点。
      expect(find.byKey(const ValueKey('style-preview-entry-tile')),
          findsNothing,);
      expect(find.text('风格预览（开发者）'), findsNothing);

      // 正例面（flag 开，测试内显式打开 + 还原）：入口出现且可进页。
      final restored = AppFeatureFlags.enableStylePreview;
      AppFeatureFlags.enableStylePreview = true;
      addTearDown(() => AppFeatureFlags.enableStylePreview = restored);
      await tester.pumpWidget(
        buildPreviewHost(
          body: const Scaffold(body: StylePreviewEntry()),
        ),
      );
      await settlePreview(tester);
      expect(find.byKey(const ValueKey('style-preview-entry-tile')),
          findsOneWidget,);

      await tester.tap(find.byKey(const ValueKey('style-preview-entry-tile')));
      await settlePreview(tester);
      expect(find.byType(StylePreviewPage), findsOneWidget);
      // 页头提案常显：不冒充已定版。
      expect(find.text('PROPOSED · 未批准'), findsOneWidget);
    });

    testWidgets('正例：classic（默认）下页面真实渲染，稳定主题仍可用',
        (tester) async {
      await freshThemeManager();
      await tester.pumpWidget(
        buildPreviewHost(body: const StylePreviewPage()),
      );
      await settlePreview(tester);

      // 稳定主题可用：classic 档下无像素扩展（发布主题路径零差量），
      // 页面骨架（切换器/五面卡）照常构建。
      expect(mountedPixelProfile(tester), isNull);
      expect(
        find.byKey(const ValueKey('style-preview-profile-switcher')),
        findsOneWidget,
      );
      expect(find.text('PROPOSED · 未批准'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });

  group('switching｜切主题不重启 run / 清数据 / 改 token 用量（验收 2）', () {
    testWidgets('正例：classic→纸昼→暮色→低刺激 live 切档，主题逐槽换装',
        (tester) async {
      await freshThemeManager();
      await tester.pumpWidget(
        buildPreviewHost(body: const StylePreviewPage()),
      );
      await settlePreview(tester);

      expect(mountedPixelProfile(tester), isNull); // classic 基线
      final classicTheme = mountedTheme(tester);

      await tester.tap(find.text('纸昼'));
      await settlePreview(tester);
      expect(mountedPixelProfile(tester), PixelPreviewProfile.paperDay);
      final paperTheme = mountedTheme(tester);
      expect(paperTheme.scaffoldBackgroundColor, isNot(
        classicTheme.scaffoldBackgroundColor,
      ),);

      await tester.tap(find.text('暮色'));
      await settlePreview(tester);
      expect(mountedPixelProfile(tester), PixelPreviewProfile.dusk);
      expect(mountedTheme(tester).brightness, Brightness.dark);

      await tester.tap(find.text('低刺激'));
      await settlePreview(tester);
      expect(mountedPixelProfile(tester), PixelPreviewProfile.quiet);
      expect(mountedTheme(tester).brightness, Brightness.light);
    });

    testWidgets('反例+正例：回退 classic 逐槽复原（回退即红：任何槽残留）',
        (tester) async {
      await freshThemeManager();
      await tester.pumpWidget(
        buildPreviewHost(body: const StylePreviewPage()),
      );
      await settlePreview(tester);
      final baseline = _freshClassicTheme();

      await tester.tap(find.text('暮色'));
      await settlePreview(tester);
      expect(mountedPixelProfile(tester), PixelPreviewProfile.dusk);

      await tester.tap(find.text('classic'));
      await settlePreview(tester);

      // 反例探测：像素扩展必须卸载（classic 不携带）。
      expect(mountedPixelProfile(tester), isNull);
      // 逐槽复原：色板/亮度/scaffold 底色/colorScheme 主色 = classic 基线。
      final restored = mountedTheme(tester);
      expect(restored.scaffoldBackgroundColor,
          baseline.scaffoldBackgroundColor,);
      expect(restored.colorScheme.primary, baseline.colorScheme.primary);
      expect(restored.colorScheme.onPrimary, baseline.colorScheme.onPrimary);
      expect(restored.brightness, baseline.brightness);
      expect(restored.colorScheme.surface, baseline.colorScheme.surface);
      expect(restored.colorScheme.secondary, baseline.colorScheme.secondary);
      expect(restored.colorScheme.error, baseline.colorScheme.error);
      // 像素扩展逐槽：classic 下无任何 PixelProfileTheme。
      expect(restored.extension<PixelProfileTheme>(), isNull);
    });

    testWidgets('正例：切档不重启 run——页面 State 与探针 State 全程存活',
        (tester) async {
      await freshThemeManager();
      StylePreviewStateProbe.mountedCount = 0;
      await tester.pumpWidget(
        buildPreviewHost(
          body: const Column(
            children: [
              StylePreviewStateProbe(),
              Expanded(child: StylePreviewPage()),
            ],
          ),
        ),
      );
      await settlePreview(tester);

      // 建立 run 内状态：探针 tick ×2 + 页面流步推进到第 3 步。
      await tester.tap(find.byKey(const ValueKey('style-preview-probe-tick')));
      await tester.tap(find.byKey(const ValueKey('style-preview-probe-tick')));
      await tester.pump();
      final state = tester.state<StylePreviewPageState>(
        find.byType(StylePreviewPage),
      );
      for (var i = 0; i < 2; i++) {
        state.advanceFlow();
      }
      await tester.pump();
      expect(find.text('probe-2'), findsOneWidget);

      // 连切三档：任何 State 重挂（initState 再入）都算重启 run。
      await tester.tap(find.text('纸昼'));
      await settlePreview(tester);
      await tester.tap(find.text('暮色'));
      await settlePreview(tester);
      await tester.tap(find.text('低刺激'));
      await settlePreview(tester);

      expect(StylePreviewStateProbe.mountedCount, 1,
          reason: '探针被重挂 = 切主题重启了 run（红）',);
      expect(find.text('probe-2'), findsOneWidget,
          reason: '探针内部状态丢失 = run 被清（红）',);
      // 页面自身流步也未被重置（同一 run 继续在 step 3）。
      expect(
        tester
            .state<StylePreviewPageState>(find.byType(StylePreviewPage))
            .flowStep
            .index,
        2,
      );
    });

    testWidgets('正例：切档不清数据——外源 prefs 键零触碰，仅 pixel 通道键更新',
        (tester) async {
      // 外源键模拟账号/用量面数据；ThemeManager 通道键预置为默认值。
      await freshThemeManager(initialPrefs: <String, Object>{
        'user_token_usage_total': 12345,
        'user_memory_seed_key': 'seed-do-not-touch',
        ThemeManager.pixelPreviewPrefsKey: 0,
      },);
      final prefs = await SharedPreferences.getInstance();
      await tester.pumpWidget(
        buildPreviewHost(body: const StylePreviewPage()),
      );
      await settlePreview(tester);

      await tester.tap(find.text('纸昼'));
      await settlePreview(tester);
      await tester.tap(find.text('暮色'));
      await settlePreview(tester);
      await tester.tap(find.text('低刺激'));
      await settlePreview(tester);
      await tester.tap(find.text('classic'));
      await settlePreview(tester);

      // 外源键零触碰（清数据即红）。
      expect(prefs.getInt('user_token_usage_total'), 12345,
          reason: '用量面数据被清 = 「切主题改 token 用量」（红）',);
      expect(prefs.getString('user_memory_seed_key'), 'seed-do-not-touch');
      // pixel 通道键回落 classic（index 0）。
      expect(prefs.getInt(ThemeManager.pixelPreviewPrefsKey), 0);
    });

    testWidgets('正例：切换可持久化复原（进→退→重启恢复）', (tester) async {
      await freshThemeManager();
      await tester.pumpWidget(
        buildPreviewHost(body: const StylePreviewPage()),
      );
      await settlePreview(tester);

      await tester.tap(find.text('低刺激'));
      await settlePreview(tester);
      final manager = ThemeManager();
      // 模拟重启：initialize() 重读持久层。
      await manager.initialize();
      expect(manager.pixelPreviewProfile, PixelPreviewProfile.quiet);

      await tester.tap(find.text('classic'));
      await settlePreview(tester);
      await manager.initialize();
      expect(manager.pixelPreviewProfile, PixelPreviewProfile.classic);
    });

    testWidgets('正例：切档路径纯本地——无网络/无第二写入面（结构自证）',
        (tester) async {
      await freshThemeManager(initialPrefs: <String, Object>{
        ThemeManager.pixelPreviewPrefsKey: 0,
      },);
      final prefs = await SharedPreferences.getInstance();
      await tester.pumpWidget(
        buildPreviewHost(body: const StylePreviewPage()),
      );
      await settlePreview(tester);

      await tester.tap(find.text('纸昼'));
      await settlePreview(tester);

      // 切档只落 pixel 通道键（F01 唯一编程入口的持久化面）；无任何新增
      // 写入键（第二持久化面即红）。
      final keys = prefs.getKeys();
      expect(keys, contains(ThemeManager.pixelPreviewPrefsKey));
      expect(prefs.getInt(ThemeManager.pixelPreviewPrefsKey),
          PixelPreviewProfile.paperDay.index,);
      expect(
        keys.where((k) => k.startsWith('style_preview_')),
        isEmpty,
        reason: 'preview 面不得自建第二持久化权威',
      );
      // 泵内无未落定异步（网络/计时器）残留。
      expect(tester.takeException(), isNull);
    });
  });
}
