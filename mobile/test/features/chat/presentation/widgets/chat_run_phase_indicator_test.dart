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
}
