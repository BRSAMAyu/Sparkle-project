import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_state.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_run_phase_indicator.dart';
import '../../../../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);

  group('resolveChatRunStage（S18 三态映射）', () {
    test('sending + 无状态/检索类状态 → 检索', () {
      expect(
        resolveChatRunStage(ChatRunPhase.sending, null),
        ChatRunStage.retrieve,
      );
      expect(
        resolveChatRunStage(ChatRunPhase.sending, 'SEARCHING'),
        ChatRunStage.retrieve,
      );
      expect(
        resolveChatRunStage(ChatRunPhase.sending, 'searching'),
        ChatRunStage.retrieve,
      );
    });

    test('sending + 思考类状态 → 思考', () {
      expect(
        resolveChatRunStage(ChatRunPhase.sending, 'THINKING'),
        ChatRunStage.think,
      );
      expect(
        resolveChatRunStage(ChatRunPhase.sending, 'ANALYZING'),
        ChatRunStage.think,
      );
      expect(
        resolveChatRunStage(ChatRunPhase.sending, 'PLANNING'),
        ChatRunStage.think,
      );
      expect(
        resolveChatRunStage(ChatRunPhase.sending, 'REVIEWING'),
        ChatRunStage.think,
      );
    });

    test('streaming / finalizing → 生成', () {
      expect(
        resolveChatRunStage(ChatRunPhase.streaming, 'THINKING'),
        ChatRunStage.generate,
      );
      expect(
        resolveChatRunStage(ChatRunPhase.finalizing, null),
        ChatRunStage.generate,
      );
    });

    test('终态相位不再进入等待（映射回退检索不渲染，由调用方门控）', () {
      // 终态时胶囊不应挂载；映射函数本身保持全相位可 total 化。
      expect(
        resolveChatRunStage(ChatRunPhase.completed, null),
        ChatRunStage.retrieve,
      );
      expect(
        resolveChatRunStage(ChatRunPhase.failed, null),
        ChatRunStage.retrieve,
      );
    });
  });

  group('ChatRunPhaseIndicator 三态渲染 + 可取消', () {
    Widget host(WidgetTester tester, ChatRunPhase phase, String? aiStatus,
        {required ValueChanged<String> onCancel}) {
      return ProviderScope(
        child: testMaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) => Center(
                child: ChatRunPhaseIndicator(
                  phase: phase,
                  aiStatus: aiStatus,
                  onCancel: () => onCancel(context.l10n.chatRunPhaseCancelButton),
                ),
              ),
            ),
          ),
        ),
      );
    }

    testWidgets('检索阶段高亮检索段并展示预期时长', (tester) async {
      final semantics = tester.ensureSemantics();
      await tester.pumpWidget(host(
        tester,
        ChatRunPhase.sending,
        null,
        onCancel: (_) {},
      ));
      await tester.pump();

      expect(find.text('检索资料'), findsOneWidget);
      expect(find.text('思考中'), findsOneWidget);
      expect(find.text('生成回答'), findsOneWidget);
      expect(find.text('通常几秒到十几秒'), findsOneWidget);
      // 激活段以加粗语义呈现（info 色），此处校验激活段存在语义标签。
      expect(
        find.bySemanticsLabel('正在检索资料，可取消'),
        findsOneWidget,
      );
      semantics.dispose();
    });

    testWidgets('思考阶段映射（aiStatus=THINKING）', (tester) async {
      final semantics = tester.ensureSemantics();
      await tester.pumpWidget(host(
        tester,
        ChatRunPhase.sending,
        'THINKING',
        onCancel: (_) {},
      ));
      await tester.pump();
      expect(find.bySemanticsLabel('正在思考中，可取消'), findsOneWidget);
      semantics.dispose();
    });

    testWidgets('生成阶段映射（streaming）', (tester) async {
      final semantics = tester.ensureSemantics();
      await tester.pumpWidget(host(
        tester,
        ChatRunPhase.streaming,
        null,
        onCancel: (_) {},
      ));
      await tester.pump();
      expect(find.bySemanticsLabel('正在生成回答，可取消'), findsOneWidget);
      semantics.dispose();
    });

    testWidgets('点取消回调触发（接线 cancelActiveRun）', (tester) async {
      final semantics = tester.ensureSemantics();
      var cancelled = false;
      await tester.pumpWidget(
        ProviderScope(
          child: testMaterialApp(
            home: Scaffold(
              body: Center(
                child: ChatRunPhaseIndicator(
                  phase: ChatRunPhase.sending,
                  aiStatus: null,
                  onCancel: () => cancelled = true,
                ),
              ),
            ),
          ),
        ),
      );
      await tester.pump();

      await tester.tap(find.byIcon(Icons.close_rounded));
      await tester.pump();

      expect(cancelled, isTrue);
      // 取消钮带语义标签（≥44 热区由 IconButton visualDensity 保证语义）。
      expect(find.bySemanticsLabel('取消'), findsOneWidget);
      semantics.dispose();
    });
    
    testWidgets('阶段切换语义随 aiStatus 更新（reduced 无关静态段可查）', (tester) async {
      final semantics = tester.ensureSemantics();
      await tester.pumpWidget(host(
        tester,
        ChatRunPhase.sending,
        'REVIEWING',
        onCancel: (_) {},
      ));
      await tester.pump();
      expect(find.bySemanticsLabel('正在思考中，可取消'), findsOneWidget);
      semantics.dispose();
    });
  });

  group('V13-RETEST：阶段胶囊行窄屏收敛（debug overflow 14px 修复钉）', () {
    // 复测环境 Medium_Phone_API_36.1（412dp）：列表左右 padding 16×2 后
    // 胶囊可用宽 ≈380px，原布局（三段 Flexible + 提示 Text 非弹性）恰超
    // 14px 触发 OVERFLOWED BY 14 PIXELS 条纹（复测截图 07/09b/11）。
    Widget narrowHost(WidgetTester tester, double width,
        {required VoidCallback onCancel}) {
      return ProviderScope(
        child: testMaterialApp(
          home: Scaffold(
            body: Center(
              child: SizedBox(
                width: width,
                child: ChatRunPhaseIndicator(
                  phase: ChatRunPhase.streaming,
                  aiStatus: null,
                  onCancel: onCancel,
                ),
              ),
            ),
          ),
        ),
      );
    }

    testWidgets('380px（V13 实测溢出面）不再产生 overflow 异常', (tester) async {
      var cancelled = false;
      await tester.pumpWidget(
        narrowHost(tester, 380, onCancel: () => cancelled = true),
      );
      await tester.pump();
      await tester.pump();

      // 溢出在 debug 测试环境以 FlutterError 形式浮出；无异常即收敛。
      expect(tester.takeException(), isNull);
      // 三段与取消钮仍然完整在场（收敛不牺牲功能）。
      expect(find.text('检索资料'), findsOneWidget);
      expect(find.text('思考中'), findsOneWidget);
      expect(find.text('生成回答'), findsOneWidget);
      expect(find.byIcon(Icons.close_rounded), findsOneWidget);
      await tester.tap(find.byIcon(Icons.close_rounded));
      await tester.pump();
      expect(cancelled, isTrue);
    });

    testWidgets('320px（最小支持宽）仍收敛且时长提示可截断', (tester) async {
      await tester.pumpWidget(narrowHost(tester, 320, onCancel: () {}));
      await tester.pump();
      await tester.pump();

      expect(tester.takeException(), isNull);
      // 时长提示挂 Flexible：被截断时以省略号收敛，Text 本体（全串）在场。
      expect(find.text('通常几秒到十几秒'), findsOneWidget);
    });

    testWidgets('宽屏（600px）时长提示完整不截断', (tester) async {
      await tester.pumpWidget(narrowHost(tester, 600, onCancel: () {}));
      await tester.pump();

      expect(tester.takeException(), isNull);
      final hintRect = tester.getRect(find.text('通常几秒到十几秒'));
      // 宽屏下提示应有完整固有宽度（8 个全角字符 @fontSizeXs 远大于省略态）。
      expect(hintRect.width, greaterThan(70));
    });
  });
}
