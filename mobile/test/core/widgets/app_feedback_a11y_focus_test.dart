// V4-F06 · toast 不抢持续输入（验收②的 chat 反馈通道面）。
//
// 背景：chat 模块的即时反馈统一走 AppFeedback → SparkleSnackBar
// （floating SnackBar）。验收口径：toast 出现时**不得移动输入焦点**——
// 用户正在输入框持续打字（chat composer），toast 只经 live region 播报，
// 不夺走 primary focus。
//
// 正例 F+：输入框持焦 → AppFeedback.success → SnackBar 在屏 + 输入框
//   primary focus 保持 + SnackBar 语义为 liveRegion（播报不抢焦）；
// 反例 F-（探针活性）：模态对话框路由同法入栈 → primary focus 被对话框
//   夺走（同探针能看见焦点被抢，证明 F+ 的「焦点保持」断言非恒真）。
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('验收② · toast 不抢持续输入（AppFeedback → SnackBar 通道）', () {
    testWidgets('F+：输入框持焦时 toast 在屏，输入焦点不被夺走',
        (tester) async {
      final semantics = tester.ensureSemantics();
      const fieldKey = ValueKey('composer_field');
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Column(
              children: [
                const TextField(
                  key: fieldKey,
                  decoration: InputDecoration(hintText: 'COMPOSER'),
                ),
                Builder(
                  builder: (context) => TextButton(
                    onPressed: () =>
                        AppFeedback.success(context, '已保存到记忆'),
                    child: const Text('TRIGGER_TOAST'),
                  ),
                ),
              ],
            ),
          ),
        ),
      );

      // 模拟持续输入：聚焦 composer（primary focus 在输入框子树；
      // EditableText 内部节点持焦，用祖先链判属）。
      await tester.tap(find.byKey(fieldKey));
      await tester.pumpAndSettle();
      bool primaryFocusInsideComposer() {
        final ctx = FocusManager.instance.primaryFocus?.context;
        if (ctx is! Element) return false;
        final fieldElement = find.byKey(fieldKey).evaluate().single;
        var found = identical(ctx, fieldElement);
        ctx.visitAncestorElements((ancestor) {
          if (identical(ancestor, fieldElement)) {
            found = true;
            return false;
          }
          return true;
        });
        return found;
      }

      expect(
        primaryFocusInsideComposer(),
        isTrue,
        reason: '前置：composer 必须持 primary focus',
      );
      final focusBefore = FocusManager.instance.primaryFocus;

      // toast 出现（chat 的 lastActionStatus 反馈同通道）。
      await tester.tap(find.text('TRIGGER_TOAST'));
      await tester.pumpAndSettle();
      expect(find.text('已保存到记忆'), findsOneWidget);

      // 焦点仍在 composer：toast 未夺走 primary focus。
      expect(
        FocusManager.instance.primaryFocus,
        same(focusBefore),
        reason: 'toast 出现后输入框必须保持 primary focus（不抢持续输入）',
      );

      // toast 经 live region 播报（读屏感知）而不是靠焦点转移。
      final snackBarSemantics =
          tester.getSemantics(find.text('已保存到记忆'));
      expect(
        snackBarSemantics.getSemanticsData().flagsCollection.isLiveRegion,
        isTrue,
        reason: 'SnackBar 须为 liveRegion（播报不抢焦）',
      );
      semantics.dispose();
    });

    testWidgets('F-：模态对话框同法入栈会夺走焦点（探针活性）',
        (tester) async {
      const fieldKey = ValueKey('composer_field_dialog');
      BuildContext? capturedContext;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) {
                capturedContext = context;
                return Column(
                  children: [
                    const TextField(
                      key: fieldKey,
                      decoration: InputDecoration(hintText: 'COMPOSER'),
                    ),
                    TextButton(
                      onPressed: () => showDialog<void>(
                        context: context,
                        builder: (_) => const AlertDialog(
                          title: Text('MODAL_PROBE'),
                        ),
                      ),
                      child: const Text('TRIGGER_MODAL'),
                    ),
                  ],
                );
              },
            ),
          ),
        ),
      );
      expect(capturedContext, isNotNull);

      await tester.tap(find.byKey(fieldKey));
      await tester.pumpAndSettle();
      bool primaryFocusInsideComposer() {
        final ctx = FocusManager.instance.primaryFocus?.context;
        if (ctx is! Element) return false;
        final fieldElement = find.byKey(fieldKey).evaluate().single;
        var found = identical(ctx, fieldElement);
        ctx.visitAncestorElements((ancestor) {
          if (identical(ancestor, fieldElement)) {
            found = true;
            return false;
          }
          return true;
        });
        return found;
      }

      expect(
        primaryFocusInsideComposer(),
        isTrue,
        reason: '前置：composer 必须持 primary focus',
      );
      final focusBefore = FocusManager.instance.primaryFocus;

      // 控制组：模态路由把 primary focus 移出输入框（对话框入栈默认
      // 聚焦自身 scope）——同一探针能看见焦点被抢。
      await tester.tap(find.text('TRIGGER_MODAL'));
      await tester.pumpAndSettle();
      expect(find.text('MODAL_PROBE'), findsOneWidget);
      expect(
        FocusManager.instance.primaryFocus,
        isNot(same(focusBefore)),
        reason: '模态控制组必须被焦点探针判负（否则 F+ 无判别力）',
      );
    });
  });
}
