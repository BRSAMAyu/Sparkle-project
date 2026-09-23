import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_button_v2.dart';
import 'package:sparkle/features/settings/presentation/providers/accessibility_provider.dart';

import '../../shared/i18n_test_helper.dart';

/// SparkleIconButton watch accessibilitySettingsProvider，真实 notifier
/// 构造即发起服务端同步（Dio）——widget 测试里 stub 掉（照
/// sparkle_button_test 先例），保持纯语义断言。
class _StubAccessibilitySettingsNotifier extends AccessibilitySettingsNotifier {
  _StubAccessibilitySettingsNotifier(super.ref);

  @override
  Future<void> load() async {}
}

/// A11Y-ICONS（N31 图标钮必有名 · 组件层防御）：
///
/// SparkleIconButton 语义名解析顺序——
/// 1. 显式 semanticLabel（l10n）；
/// 2. 反推：icon 为 Flutter `Icon` 且自带 semanticLabel 时上提为按钮语义名；
/// 3. 皆无 → debug 登记诊断（登记制，不致命），语义树上无名（诚实缺口）。
///
/// 验收（卡面）：首批面读屏可念出每个钮的用途 → semantics label 存在断言。
void main() {
  setUp(setUpI18nForTesting);

  Future<void> pumpButton(
    WidgetTester tester,
    SparkleIconButton button,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          accessibilitySettingsProvider
              .overrideWith(_StubAccessibilitySettingsNotifier.new),
        ],
        child: MaterialApp(
          home: Scaffold(body: Center(child: button)),
        ),
      ),
    );
    await tester.pump();
  }

  group('SparkleIconButton 语义名（N31）', () {
    testWidgets('显式 semanticLabel → 语义树可按名定位且带按钮角色', (tester) async {
      final semantics = tester.ensureSemantics();
      await pumpButton(
        tester,
        SparkleIconButton(
          icon: const Icon(Icons.close),
          semanticLabel: '关闭',
          onPressed: () {},
        ),
      );

      final handle = find.bySemanticsLabel('关闭');
      expect(handle, findsOneWidget);
      final node = tester.getSemantics(handle);
      expect(node.flagsCollection.isButton, isTrue);
      semantics.dispose();
    });

    testWidgets('反推：icon 自带 semanticLabel 时上提为按钮语义名', (tester) async {
      final semantics = tester.ensureSemantics();
      await pumpButton(
        tester,
        SparkleIconButton(
          icon: const Icon(Icons.arrow_back, semanticLabel: '返回'),
          onPressed: () {},
        ),
      );

      // 上提成功：语义树上按「返回」可定位（与按钮角色合并播报）。
      expect(find.bySemanticsLabel('返回'), findsOneWidget);
      final node = tester.getSemantics(find.bySemanticsLabel('返回'));
      expect(node.flagsCollection.isButton, isTrue);
      semantics.dispose();
    });

    testWidgets('显式 semanticLabel 优先于 icon 自带标签', (tester) async {
      final semantics = tester.ensureSemantics();
      await pumpButton(
        tester,
        SparkleIconButton(
          icon: const Icon(Icons.search, semanticLabel: '图标级标签'),
          semanticLabel: '搜索',
          onPressed: () {},
        ),
      );

      expect(find.bySemanticsLabel('搜索'), findsOneWidget);
      expect(find.bySemanticsLabel('图标级标签'), findsNothing);
      semantics.dispose();
    });

    testWidgets('两者皆无 → 不致命（构建成功），登记制走 debug 诊断', (tester) async {
      // 存量无名钮是登记制债务（ratchet 只降不升）：本断言钉住「不因
      // 无名而崩溃」的底线；debug 期诊断由组件内 assert+debugPrint 输出。
      await pumpButton(
        tester,
        SparkleIconButton(
          icon: const Icon(Icons.help_outline),
          onPressed: () {},
        ),
      );
      expect(tester.takeException(), isNull);
    });
  });
}
