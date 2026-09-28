import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'shell_test_harness.dart';

/// V4-F04 验收面：「360宽 / 800×600 / 1280×720 下主操作和错误可见」。
///
/// - 主操作 = 五个 Tab 目的地（真 route ID 合同的呈现面）+ 分支切换可达；
/// - 错误 = home 分支内容顶部的错误探针（shell 级错误面代理，ERROR_PROBE）
///   ——shell 布局不得在任何档位把它裁出视口；
/// - 每个尺寸一正一反：正例钉应得呈现面与可见性，反例钉错误档位不得
///   出现（映射回归必红）。
void main() {
  setUp(setUpI18nForTesting);

  Future<void> expectProbeVisible(WidgetTester tester) async {
    final view = tester.view;
    final logicalWidth = view.physicalSize.width / view.devicePixelRatio;
    final logicalHeight = view.physicalSize.height / view.devicePixelRatio;
    final probeRect = tester.getRect(
      find.byKey(const ValueKey('shell_error_probe')),
    );
    // 探针在视口内（不被裁剪/推出屏外）。
    expect(probeRect.left, greaterThanOrEqualTo(0));
    expect(probeRect.top, greaterThanOrEqualTo(0));
    expect(probeRect.right, lessThanOrEqualTo(logicalWidth));
    expect(probeRect.bottom, lessThanOrEqualTo(logicalHeight));
    expect(
      find.text('ERROR_PROBE'),
      findsOneWidget,
      reason: '错误面在当前档位必须可见',
    );
  }

  testWidgets('360宽（手机）：底栏五目的地可见可点，错误探针可见，切 Tab 可达',
      (tester) async {
    await pumpShellHarness(tester);

    // 正例：底栏承载五 Tab。
    expect(find.byType(NavigationBar), findsOneWidget);
    expect(find.byType(NavigationRail), findsNothing);
    final destinations = tester.widgetList<NavigationDestination>(
      find.byType(NavigationDestination),
    );
    expect(destinations, hasLength(5));
    for (final d in destinations) {
      final rect = tester.getRect(find.byWidget(d));
      expect(rect.right, lessThanOrEqualTo(360), reason: '${d.label} 越界');
      expect(rect.top, greaterThanOrEqualTo(0));
      expect(rect.bottom, lessThanOrEqualTo(800));
    }

    // 主操作可达：点第 3 个目的地（chat）→ 分支切换。
    await tester.tap(find.byType(NavigationDestination).at(2));
    await tester.pumpAndSettle();
    expect(find.text('CHAT_PLACEHOLDER'), findsOneWidget);

    // 错误可见：回到 home 分支，探针仍在视口内。
    await tester.tap(find.byType(NavigationDestination).at(0));
    await tester.pumpAndSettle();
    await expectProbeVisible(tester);

    expect(tester.takeException(), isNull);
  });

  testWidgets('800×600：底栏档不变（反例：不得误升 rail），探针可见',
      (tester) async {
    await pumpShellHarness(tester, size: const Size(800, 600));

    // 正例：底栏仍在（该尺寸与升级前同档，零档位差量）。
    expect(find.byType(NavigationBar), findsOneWidget);
    expect(
      tester.widgetList<NavigationDestination>(
        find.byType(NavigationDestination),
      ),
      hasLength(5),
    );
    // 反例：窄短边小窗不得出现 rail（映射回归即红）。
    expect(find.byType(NavigationRail), findsNothing);

    await expectProbeVisible(tester);
    expect(tester.takeException(), isNull);
  });

  testWidgets('1280×720（桌面窗口）：常驻侧栏五目的地，错误探针在内容侧可见',
      (tester) async {
    await pumpShellHarness(tester, size: const Size(1280, 720));

    // 正例：桌面档升级为常驻侧栏（extended rail + 品牌头）。
    expect(
      find.byType(NavigationBar),
      findsNothing,
      reason: '桌面窗口不得再停在手机底栏（F04 升级点）',
    );
    final rails = tester.widgetList<NavigationRail>(
      find.byType(NavigationRail),
    );
    expect(rails, hasLength(1));
    expect(rails.single.extended, isTrue);
    expect(find.byIcon(Icons.local_fire_department), findsOneWidget);
    expect(
      rails.single.destinations,
      hasLength(5),
      reason: '桌面侧栏五目的地（rail destinations 配置数）',
    );

    // 主操作可达：点 rail 的 galaxy 图标（rail destinations 非_WIDGET，
    // 以目的地图标定位）→ 分支切换。
    await tester.tap(find.byIcon(Icons.auto_awesome_outlined));
    await tester.pumpAndSettle();
    expect(find.text('GALAXY_PLACEHOLDER'), findsOneWidget);

    // 错误可见：回 home 分支，探针在内容侧视口内。
    await tester.tap(find.byIcon(Icons.home_outlined));
    await tester.pumpAndSettle();
    await expectProbeVisible(tester);

    expect(tester.takeException(), isNull);
  });

  testWidgets('768×1024（平板）：rail 档（正例钉既有平板档不因升级回退）',
      (tester) async {
    await pumpShellHarness(tester, size: const Size(768, 1024));

    expect(find.byType(NavigationBar), findsNothing);
    final rails = tester.widgetList<NavigationRail>(
      find.byType(NavigationRail),
    );
    expect(rails, hasLength(1));
    expect(rails.single.extended, isFalse, reason: '平板档是 labelType all，非 extended 侧栏');
    expect(
      rails.single.destinations,
      hasLength(5),
      reason: '平板 rail 五目的地',
    );
    await expectProbeVisible(tester);
    expect(tester.takeException(), isNull);
  });
}
