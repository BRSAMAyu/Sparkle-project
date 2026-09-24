import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/plan/presentation/screens/exam_sprint_setup_screen.dart';

import '../../../../shared/i18n_test_helper.dart';

/// N27（A-SPEC5 v1.5）脏态保护回归（exam_sprint_setup 屏）：
/// 科目输入/上传材料/薄弱章节都是用户劳动；考试日期出厂有默认值不算脏。
/// 原返回键 context.pop() 硬 pop 绕过守卫，已改 maybePop。
void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  Future<void> pumpSetup(WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        child: testMaterialApp(
          home: Navigator(
            pages: const [
              MaterialPage<void>(child: Scaffold(body: Text('起点'))),
              MaterialPage<void>(
                key: ValueKey('sprint-setup-page'),
                child: ExamSprintSetupScreen(),
              ),
            ],
            onPopPage: (route, result) => route.didPop(result),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('出厂默认（考试日期已预置）返回不弹确认，直接放行', (tester) async {
    await pumpSetup(tester);

    await tester.tap(find.byIcon(Icons.arrow_back));
    await tester.pumpAndSettle();

    expect(find.byType(ExamSprintSetupScreen), findsNothing,
        reason: '默认值不算用户劳动，返回直接放行',);
    expect(find.text('起点'), findsOneWidget);
    expect(find.text('放弃更改？'), findsNothing);
  });

  testWidgets('输入科目后返回必确认，「继续编辑」留下、「放弃更改」放行', (tester) async {
    await pumpSetup(tester);

    await tester.enterText(find.byType(TextFormField).first, '计算机网络');
    await tester.pump();

    await tester.tap(find.byIcon(Icons.arrow_back));
    await tester.pumpAndSettle();

    expect(find.text('放弃更改？'), findsOneWidget,
        reason: '科目输入是用户劳动，返回必须确认',);

    await tester.tap(find.text('继续编辑'));
    await tester.pumpAndSettle();
    expect(find.byType(ExamSprintSetupScreen), findsOneWidget);

    await tester.tap(find.byIcon(Icons.arrow_back));
    await tester.pumpAndSettle();
    await tester.tap(find.text('放弃更改'));
    await tester.pumpAndSettle();

    expect(find.byType(ExamSprintSetupScreen), findsNothing);
    expect(find.text('起点'), findsOneWidget);
  });
}
