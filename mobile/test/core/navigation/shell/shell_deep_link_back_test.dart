import 'dart:async' show unawaited;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'shell_test_harness.dart';

/// V4-F04 验收面：「全部旧深链能到同一对象、Back 不丢上下文」。
///
/// Shell 升级不改 app/routes.dart（五分支合同零触碰）；本组测试以镜像
/// 真实 route ID 的测试路由钉住 Shell 呈现层升级不得破坏的既有语义：
/// - 嵌套深链（/plans/:id，镜像 PlanRoutes.shellRoutes）直达同一对象；
/// - StatefulShellRoute.indexedStack 分支切换保留各分支栈（切回不丢）；
/// - 系统返回（popRoute）弹嵌套页回到分支根，分支上下文保留。
void main() {
  setUp(setUpI18nForTesting);

  testWidgets('旧深链 /plans/plan-42 直达同一对象（分支索引 0）', (tester) async {
    await pumpShellHarness(tester, initialLocation: '/plans/plan-42');

    // 同一对象 = 与站内导航同一占位屏（类型+ID 文本），不是降级错误页。
    expect(find.text('PLAN_PLACEHOLDER:plan-42'), findsOneWidget);
    expect(find.text('ERROR_PROBE'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('切 Tab 再切回：嵌套深链上下文不丢（分支栈保留）', (tester) async {
    await pumpShellHarness(tester, initialLocation: '/plans/plan-42');

    // 切到 chat 分支（底栏第 3 个目的地）再切回 home 分支。
    await tester.tap(find.byType(NavigationDestination).at(2));
    await tester.pumpAndSettle();
    expect(find.text('CHAT_PLACEHOLDER'), findsOneWidget);

    await tester.tap(find.byType(NavigationDestination).at(0));
    await tester.pumpAndSettle();
    // 反例钉死：若 shell/路由层重置了分支栈，这里会是分支根 HOME 而非嵌套对象。
    expect(
      find.text('PLAN_PLACEHOLDER:plan-42'),
      findsOneWidget,
      reason: '切回 home 分支必须还在嵌套深链对象上（Back 不丢上下文）',
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets('系统返回：站内入栈嵌套页后 Back 弹回分支根，再深链仍直达同一对象',
      (tester) async {
    final router = buildShellTestRouter();
    await pumpShellHarness(tester, router: router);

    // 站内导航压入嵌套对象（push 语义：分支栈 /home → /plans/plan-42；
    // go 是替换语义，不产生可弹栈，见首两条用例的深链口径）。
    unawaited(router.push('/plans/plan-42'));
    await tester.pumpAndSettle();
    expect(find.text('PLAN_PLACEHOLDER:plan-42'), findsOneWidget);

    // 系统返回语义代理：routerDelegate.popRoute()（SystemNavigator 同路）。
    final popped = await router.routerDelegate.popRoute();
    expect(popped, isTrue, reason: '嵌套页上系统返回应当被消费');
    await tester.pumpAndSettle();
    expect(find.text('HOME_ROOT_MARKER'), findsOneWidget);
    expect(find.text('PLAN_PLACEHOLDER:plan-42'), findsNothing);

    // 再入同一旧深链：仍直达同一对象（幂等）。
    router.go('/plans/plan-42');
    await tester.pumpAndSettle();
    expect(find.text('PLAN_PLACEHOLDER:plan-42'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
