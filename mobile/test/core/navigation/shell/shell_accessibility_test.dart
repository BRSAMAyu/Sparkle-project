import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'shell_test_harness.dart';

/// V4-F04 验收面：「系统返回、文本200%、键盘打开不越界」。
///
/// - 文本 200%：360 宽下无 RenderFlex 越界异常，五目的地与错误探针仍在；
/// - 键盘：置底输入框聚焦 + 286dp 键盘 inset——Scaffold 消费 viewInsets，
///   输入框不进键盘遮蔽区、底栏不越界（反例钉死：若 Shell 键盘契约
///   （resizeToAvoidBottomInset）回退为 false，输入框 bottom 仍会等于
///   屏高，本测试即红）；
/// - 系统返回：分支根上 popRoute 不被误吞（返回 false 由系统决定退出，
///   shell 保持原状）。
void main() {
  setUp(setUpI18nForTesting);

  testWidgets('文本 200%：360 宽无越界异常，五目的地与错误探针可见',
      (tester) async {
    await pumpShellHarness(tester, textScale: 2.0);

    expect(tester.takeException(), isNull, reason: '200% 文本不得产生布局越界');
    expect(find.byType(NavigationBar), findsOneWidget);
    expect(
      tester
          .widgetList<NavigationDestination>(find.byType(NavigationDestination))
          .length,
      5,
    );
    final probeRect = tester.getRect(
      find.byKey(const ValueKey('shell_error_probe')),
    );
    expect(probeRect.bottom, lessThanOrEqualTo(800));
    expect(find.text('ERROR_PROBE'), findsOneWidget);
  });

  testWidgets('键盘打开：置底输入框在键盘上方，底栏不越界', (tester) async {
    const keyboardInset = 286.0;
    await pumpShellHarness(
      tester,
      homeBottomWidget: const TextField(
        key: ValueKey('shell_bottom_field'),
        decoration: InputDecoration(hintText: 'SHELL_FIELD'),
      ),
    );

    // 聚焦输入框并注入键盘 inset（TestFlutterView.viewInsets）。
    await tester.showKeyboard(find.byKey(const ValueKey('shell_bottom_field')));
    tester.view.viewInsets = const FakeViewPadding(bottom: keyboardInset);
    addTearDown(tester.view.reset);
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull, reason: '键盘打开不得产生越界异常');

    // 反例钉死：inset 被消费 → 置底输入框 bottom ≤ 键盘顶（800-286）。
    final fieldBottom = tester
        .getRect(find.byKey(const ValueKey('shell_bottom_field')))
        .bottom;
    expect(
      fieldBottom,
      lessThanOrEqualTo(800 - keyboardInset + 0.5),
      reason: '置底输入框必须停在键盘上方（Scaffold inset 消费契约）',
    );

    // 底栏不越界：仍在视口内（键盘上方可见）。
    final barRect = tester.getRect(find.byType(NavigationBar));
    expect(barRect.bottom, lessThanOrEqualTo(800));
    expect(barRect.height, greaterThan(0));

    tester.view.viewInsets = FakeViewPadding.zero;
    await tester.pumpAndSettle();
  });

  testWidgets('系统返回：分支根上返回不被 shell 误吞（无弹出即交还系统）',
      (tester) async {
    final router = buildShellTestRouter();
    await pumpShellHarness(tester, router: router);

    final popped = await router.routerDelegate.popRoute();
    expect(popped, isFalse, reason: '分支根无嵌套页可弹，返回应交还系统');
    await tester.pumpAndSettle();
    expect(find.text('HOME_ROOT_MARKER'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
