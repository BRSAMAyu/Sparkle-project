import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/widgets/unsaved_changes_guard.dart';

import '../../shared/i18n_test_helper.dart';

/// N27（A-SPEC5 v1.5）守卫组件语义回归：
/// - 干净表单直接放行 pop，不弹确认；
/// - 脏表单拦截 pop 弹确认，「继续编辑」留下、「放弃更改」放行；
/// - 弹窗文案默认走 formUnsaved* l10n（zh），不再是硬编码英文。
///
/// 双页 Navigator 模拟真实路由栈：被守卫屏不是首路由，
/// maybePop 的放行/拦截语义与真实 push 页面一致。
void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  Future<void> pumpGuarded(
    WidgetTester tester, {
    required bool isDirty,
    bool customLabels = false,
  }) async {
    await tester.pumpWidget(
      testMaterialApp(
        home: Navigator(
          pages: [
            const MaterialPage<void>(child: Scaffold(body: Text('起点'))),
            MaterialPage<void>(
              key: const ValueKey('guarded-page'),
              child: UnsavedChangesGuard(
                isDirty: isDirty,
                discardTitle: customLabels ? '放弃创建社群？' : null,
                discardMessage: customLabels ? '你有未保存的更改，确定放弃？' : null,
                keepEditingLabel: customLabels ? '继续编辑' : null,
                discardLabel: customLabels ? '放弃' : null,
                child: Scaffold(
                  appBar: AppBar(title: const Text('表单')),
                  body: const SizedBox.shrink(),
                ),
              ),
            ),
          ],
          onPopPage: (route, result) => route.didPop(result),
        ),
      ),
    );
    await tester.pump();
  }

  testWidgets('干净表单返回不弹确认，直接放行 pop', (tester) async {
    await pumpGuarded(tester, isDirty: false);

    await tester.tap(find.byIcon(Icons.arrow_back));
    await tester.pumpAndSettle();

    expect(find.text('表单'), findsNothing, reason: '干净表单应直接 pop 回起点');
    expect(find.text('起点'), findsOneWidget);
    expect(find.text('放弃更改？'), findsNothing, reason: '不应出现确认弹窗');
  });

  testWidgets('脏表单返回被拦截并弹出 l10n 确认，「继续编辑」留下', (tester) async {
    await pumpGuarded(tester, isDirty: true);

    await tester.tap(find.byIcon(Icons.arrow_back));
    await tester.pumpAndSettle();

    // 弹窗出现且为中文文案（formUnsaved* 默认键，替代旧硬编码英文）。
    expect(find.text('放弃更改？'), findsOneWidget);
    expect(find.text('你有未保存的输入，离开后将丢失。'), findsOneWidget);

    await tester.tap(find.text('继续编辑'));
    await tester.pumpAndSettle();

    expect(find.text('表单'), findsOneWidget, reason: '继续编辑应留在原屏');
    expect(find.text('起点'), findsNothing);
  });

  testWidgets('脏表单确认「放弃更改」后放行 pop', (tester) async {
    await pumpGuarded(tester, isDirty: true);

    await tester.tap(find.byIcon(Icons.arrow_back));
    await tester.pumpAndSettle();

    await tester.tap(find.text('放弃更改'));
    await tester.pumpAndSettle();

    expect(find.text('表单'), findsNothing, reason: '放弃后应 pop 回起点');
    expect(find.text('起点'), findsOneWidget);
  });

  testWidgets('域内自定义文案覆盖默认键', (tester) async {
    await pumpGuarded(tester, isDirty: true, customLabels: true);

    await tester.tap(find.byIcon(Icons.arrow_back));
    await tester.pumpAndSettle();

    expect(find.text('放弃创建社群？'), findsOneWidget,
        reason: '域内文案（如社群域既有键）应覆盖默认键',);
    expect(find.text('放弃更改？'), findsNothing);
  });
}
