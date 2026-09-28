import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/widgets/object_unavailable_surface.dart';
import '../../../shared/i18n_test_helper.dart';

/// V4-U14 · 深链空对象统一面（SCREEN_FAMILIES：404/离线/登录失效语义分开，
/// 不全部跳通用错误页；已删对象提示而非空白）。
///
/// 一正一反：
/// - 正：missing 面呈现标题/解释/主动作/恒在回首页出口；回首页真实路由；
/// - 反：未提供主动作时不渲染空按钮位（无主动作 ≠ 空白/假出口）。
void main() {
  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  Widget host({
    required String? primaryLabel,
    required VoidCallback? onPrimary,
  }) {
    final router = GoRouter(
      initialLocation: '/start',
      routes: [
        GoRoute(
          path: '/start',
          builder: (_, __) => ObjectUnavailableSurface(
            kind: ObjectUnavailableKind.missing,
            title: '内容已删除或不存在',
            body: '测试体',
            fallbackRoute: '/landing',
            primaryLabel: primaryLabel,
            onPrimary: onPrimary,
          ),
        ),
        GoRoute(
          path: '/landing',
          builder: (_, __) => const Text('LANDED'),
        ),
      ],
    );
    return testMaterialApp(routerConfig: router);
  }

  testWidgets(
    '正·missing 面呈现标题/解释/主动作/恒在回首页出口；回首页真实路由',
    (tester) async {
      await tester.pumpWidget(
        host(primaryLabel: '查看任务列表', onPrimary: () {}),
      );
      await tester.pump();

      expect(
        find.byKey(const ValueKey('object-unavailable-surface')),
        findsOneWidget,
      );
      expect(find.text('内容已删除或不存在'), findsOneWidget);
      expect(find.text('测试体'), findsOneWidget);
      expect(
        find.byKey(const ValueKey('object-unavailable-primary')),
        findsOneWidget,
      );
      expect(
        find.byKey(const ValueKey('object-unavailable-back-home')),
        findsOneWidget,
      );

      await tester.tap(
        find.byKey(const ValueKey('object-unavailable-back-home')),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));
      expect(find.text('LANDED'), findsOneWidget);
    },
  );

  testWidgets('反·未提供主动作时不渲染空按钮位（恒在出口仍在）', (tester) async {
    await tester.pumpWidget(host(primaryLabel: null, onPrimary: null));
    await tester.pump();

    expect(
      find.byKey(const ValueKey('object-unavailable-primary')),
      findsNothing,
    );
    expect(
      find.byKey(const ValueKey('object-unavailable-back-home')),
      findsOneWidget,
    );
    expect(find.text('内容已删除或不存在'), findsOneWidget);
  });
}
