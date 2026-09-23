import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/features/community/presentation/screens/create_group_screen.dart';

import '../../../../shared/i18n_test_helper.dart';

/// N27（A-SPEC5 v1.5）脏态保护回归（create_group 屏）。
///
/// 存量缺陷：原屏手写 PopScope 未设 canPop，didPop 恒 true，确认弹窗
/// 从未出现（死 guard），且返回键 context.pop() 硬 pop 绕过守卫。
/// 修复后：干净返回直接放行；有输入返回必确认；确认后放行。
void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  Future<void> pumpGroupForm(WidgetTester tester) async {
    final router = GoRouter(
      initialLocation: '/start',
      routes: [
        GoRoute(
          path: '/start',
          builder: (_, __) => const Scaffold(body: Text('起点')),
        ),
        GoRoute(
          path: '/community/groups/new',
          builder: (_, __) => const CreateGroupScreen(),
        ),
      ],
    );
    await tester.pumpWidget(
      ProviderScope(
        child: testMaterialApp(routerConfig: router),
      ),
    );
    await tester.pumpAndSettle();
    unawaited(router.push('/community/groups/new'));
    await tester.pumpAndSettle();
  }

  testWidgets('空表单返回不弹确认，直接放行', (tester) async {
    await pumpGroupForm(tester);

    await tester.tap(find.byIcon(Icons.arrow_back));
    await tester.pumpAndSettle();

    expect(find.byType(CreateGroupScreen), findsNothing,
        reason: '空表单返回应直接 pop',);
    expect(find.text('起点'), findsOneWidget);
    expect(find.text('放弃创建社群？'), findsNothing);
  });

  testWidgets('填入队名后返回必确认，「继续编辑」留下、「放弃」放行', (tester) async {
    await pumpGroupForm(tester);

    await tester.enterText(find.byType(TextFormField).first, '高数互助小队');
    await tester.pump();

    await tester.tap(find.byIcon(Icons.arrow_back));
    await tester.pumpAndSettle();

    expect(find.text('放弃创建社群？'), findsOneWidget,
        reason: '有输入的表单返回必须弹确认（死 guard 修复点）',);

    await tester.tap(find.text('继续编辑'));
    await tester.pumpAndSettle();

    expect(find.byType(CreateGroupScreen), findsOneWidget,
        reason: '继续编辑应留在原屏',);

    await tester.tap(find.byIcon(Icons.arrow_back));
    await tester.pumpAndSettle();
    await tester.tap(find.text('放弃'));
    await tester.pumpAndSettle();

    expect(find.byType(CreateGroupScreen), findsNothing, reason: '放弃后放行 pop');
    expect(find.text('起点'), findsOneWidget);
  });
}
