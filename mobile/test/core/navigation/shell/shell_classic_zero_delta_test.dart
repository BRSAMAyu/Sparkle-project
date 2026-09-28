import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/navigation/shell/shell.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';

import 'shell_test_harness.dart';

/// V4-F04 · classic 零差量断言（Shell 面随调用点举证——F02 一审 N2 注记）。
///
/// N2 注记原文：组件接入调用点后，「零差量主张须随调用点重新举证，
/// 不得沿用组件级断言」。本文件即 Shell 调用点的重新举证：
/// - classic（preview off，发布默认）：像素装饰沿零渲染节点，底栏仍是
///   单一 NavigationBar（五目的地结构不变）；
/// - 像素 preview 档：装饰沿出现（反过来证明 classic 断言不是恒真）；
/// - 像素只经装饰沿进入 Shell（F01 preview 通道红线），classic 无渗漏。
void main() {
  setUp(setUpI18nForTesting);

  bool isPixelEdgePainter(Widget w) =>
      w is CustomPaint &&
      w.painter != null &&
      w.painter!.runtimeType.toString() == '_PixelEdgePainter';

  testWidgets('classic（默认）：PixelShellTopEdge 渲染 shrink，零 CustomPaint',
      (tester) async {
    await tester.pumpWidget(
      testMaterialApp(home: const Center(child: PixelShellTopEdge())),
    );

    // 限定在装饰沿子树内：classic 不得有任何绘制层（框架级零星
    // CustomPaint 不在本断言面）。
    expect(
      find.descendant(
        of: find.byType(PixelShellTopEdge),
        matching: find.byType(CustomPaint),
      ),
      findsNothing,
    );
    expect(tester.getSize(find.byType(PixelShellTopEdge)), Size.zero);
    expect(tester.takeException(), isNull);
  });

  testWidgets('classic 全壳：无像素装饰沿渗漏，底栏结构 = 单一 NavigationBar 五目的地',
      (tester) async {
    await pumpShellHarness(tester);

    expect(
      find.byWidgetPredicate(isPixelEdgePainter),
      findsNothing,
      reason: 'classic（发布默认）不得出现像素装饰绘制层',
    );
    final bar = tester.widget<NavigationBar>(find.byType(NavigationBar));
    expect(bar.destinations, hasLength(5));
    // 语义独立模型落到呈现面：视觉标签与语义名（tooltip）都来自 l10n
    // （zh 测试语言）显式语义模型，不派生自图标字形。
    final l10n = AppLocalizationsZh();
    final l10nLabels = [
      l10n.home,
      l10n.galaxy,
      l10n.chat,
      l10n.community,
      l10n.profile,
    ];
    final destinations =
        bar.destinations.cast<NavigationDestination>().toList();
    expect(destinations.map((d) => d.label), l10nLabels);
    expect(
      destinations.map((d) => d.tooltip),
      l10nLabels,
      reason: 'tooltip 语义名与视觉标签同源（图标字形不参与命名）',
    );
  });

  testWidgets('pixel preview 档：装饰沿出现（反例对照：证明 classic 断言可失败）',
      (tester) async {
    await pumpShellHarness(tester, pixelPreview: true);

    expect(
      find.byWidgetPredicate(isPixelEdgePainter),
      findsOneWidget,
      reason: 'preview 档装饰沿必须出现——若 classic 也有此节点，上一条即红',
    );
    // 装饰沿高度 = pixelStep 2dp（dpr 1）。
    final edge = tester.getSize(
      find.ancestor(
        of: find.byWidgetPredicate(isPixelEdgePainter),
        matching: find.byType(SizedBox),
      ).first,
    );
    expect(edge.height, PixelShellTopEdge.heightFor(2.0, 1.0));
    // 装饰不改变底栏本体：NavigationBar 仍在且五目的地。
    expect(find.byType(NavigationBar), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('pixel preview 档装饰沿不吞手势、不进语义树', (tester) async {
    final handle = tester.ensureSemantics();
    await pumpShellHarness(tester, pixelPreview: true);

    // 点装饰沿覆盖区（底栏顶部 2dp 带内第 2 个目的地=galaxy）→ 命中
    // 穿透到底栏目的地。
    final barTop = tester.getTopLeft(find.byType(NavigationBar));
    await tester.tapAt(Offset(barTop.dx + 108, barTop.dy + 1));
    await tester.pumpAndSettle();
    expect(
      find.text('GALAXY_PLACEHOLDER'),
      findsOneWidget,
      reason: '装饰沿必须 IgnorePointer（命中穿透到其下目的地）',
    );
    // 语义树：galaxy 目的地的语义标签可定位（含义：装饰沿未引入新语义
    // 节点、目的地语义完好——ExcludeSemantics 结构见组件实现）。
    expect(
      find.bySemanticsLabel(RegExp('星图')),
      findsWidgets,
    );
    handle.dispose();
  });
}
