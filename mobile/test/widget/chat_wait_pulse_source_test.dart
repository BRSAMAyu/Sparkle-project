import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/chat/chat.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_state.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_run_phase_indicator.dart';
import '../shared/i18n_test_helper.dart';

/// SPEC-C #6（N3 呼吸禁令，实现无关口径）验收：
/// 等待窗（runPhase active + streaming 空）内「活跃持续动画源」必须恰好 1 个
/// ——阶段胶囊 700ms 脉冲；呼吸层改单次入场脉冲（320ms forward 后静止），
/// 不得再有常驻 repeat。reduce-motion 行为不回退（呼吸层直接缺席）。
final overlayFinder = find.byWidgetPredicate(
  (widget) => widget.runtimeType.toString() == '_ReasoningBreathOverlay',
  description: 'reasoning breath overlay',
);

/// 采样呼吸层当前渲染的渐变首色 alpha（= 驱动透明度），用于静止定帧断言。
double _sampleBreathOverlayOpacity(WidgetTester tester) {
  final decoratedBox = tester.widget<DecoratedBox>(
    find.descendant(of: overlayFinder, matching: find.byType(DecoratedBox)),
  );
  final gradient = (decoratedBox.decoration as BoxDecoration).gradient!;
  return (gradient as RadialGradient).colors.first.a;
}

class _FakeChatRepository extends Fake implements ChatRepository {
  @override
  Stream<WsConnectionState> get connectionStateStream => const Stream.empty();
  @override
  WsConnectionState get connectionState => WsConnectionState.disconnected;
  @override
  void dispose() {}
  @override
  Future<List<Map<String, dynamic>>> getRecentConversations() async => [];
}

/// 直接把 ChatState 置入等待窗：run 活跃（sending + THINKING）、流内容为空。
/// _shouldShowReasoningAtmosphere == true 且阶段胶囊（index 0）在。
///
/// 注意：ChatScreen 首帧后 post-frame 会调 switchPlanSession →
/// cancelActiveRun（复位 runPhase），因此测试须在 init settle 后调
/// [enterWaitWindow] 重新进入等待窗。
class _WaitWindowChatNotifier extends ChatNotifier {
  _WaitWindowChatNotifier(super.chatRepository, super.ref);

  void enterWaitWindow() {
    state = state.copyWith(
      activeRunId: 'pulse-test-run-1',
      runPhase: ChatRunPhase.sending,
      aiStatus: 'THINKING',
    );
  }

  /// 退出等待窗：run 全清（胶囊卸载、ticker 释放）+ 落一条种子消息
  /// （退出快捷建议页，屏内不再有 per-frame 动画源），供测试收工清 timer。
  void resetIdle() {
    state = ChatState(
      messages: [
        ChatMessageModel(
          id: 'seed-end',
          conversationId: 'pulse-test-session',
          content: 'seed',
          role: MessageRole.user,
          createdAt: DateTime.now(),
        ),
      ],
    );
  }

  @override
  Future<void> warmUpConnection() async {}
}

void main() {
  setUp(setUpI18nForTesting);

  Future<_WaitWindowChatNotifier> pumpWaitingChat(WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({});
    final preferences = await SharedPreferences.getInstance();
    await ViewStorageService.ensureInitialized();

    // 用 ProviderScope（而非手动 ProviderContainer + addTearDown(dispose)）：
    // 后者在 teardown 阶段 dispose 会额外落 Timer，触发 timersPending
    // 不变量；ProviderScope 的容器随树释放，ChatScreen 现有绿色测试同款。
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(preferences),
          chatProvider.overrideWith(
            (ref) => _WaitWindowChatNotifier(_FakeChatRepository(), ref),
          ),
        ],
        child: testMaterialApp(home: const ChatScreen()),
      ),
    );

    // 初始化 settle（禁 pumpAndSettle：常驻 repeat 源永不 settle），
    // 含首帧 post-frame 的 switchPlanSession / hydrate 异步链。
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }
    return tester.state<ConsumerState>(find.byType(ChatScreen))
        .ref
        .read(chatProvider.notifier) as _WaitWindowChatNotifier;
  }

  testWidgets(
    '等待态活跃持续动画源净增=1（阶段胶囊唯一），呼吸层单次入场后静止定帧 '
    '(SPEC-C #6 / N3)',
    (tester) async {
      final notifier = await pumpWaitingChat(tester);

      // init 链会 cancelActiveRun 复位 runPhase——重新进入等待窗。
      notifier.enterWaitWindow();
      await tester.pump();

      // 等待窗已建立：呼吸层挂载 + 阶段胶囊在。
      expect(overlayFinder, findsOneWidget);
      expect(find.byType(ChatRunPhaseIndicator), findsOneWidget);

      // 入场脉冲窗口内（320ms）：呼吸层 ticker 仍活跃。
      // 说明：chat 层存在与等待窗无关的既有氛围 ticker（如 _BlinkingCursor，
      // 本卡不触碰），绝对计数不稳，故用「入场终止性」+「静止定帧」两个
      // 噪声免疫断言裁决唯一持续源，而不用裸总数。
      await tester.pump(const Duration(milliseconds: 100));
      final tickersDuringEntrance = tester.binding.transientCallbackCount;

      // 越过 320ms 入场脉冲：呼吸层 controller complete、ticker 终止。
      // 旧实现（3s repeat(reverse)）的 ticker 永不终止——本断言必失败，
      // 是新旧实现的可判别点。
      await tester.pump(const Duration(milliseconds: 500));
      final tickersAfterEntrance = tester.binding.transientCallbackCount;
      expect(
        tickersAfterEntrance,
        lessThan(tickersDuringEntrance),
        reason: '入场脉冲结束后活跃 frame 源必须减少（呼吸层 ticker 终止）；'
            '旧 repeat 实现此处不会减少',
      );

      // 呼吸层静止定帧：间隔 800ms 两次采样，渐变透明度零变化
      //（旧 3s repeat 会持续在 0.03–0.08 间摆动，必失败）。
      final opacityAtT1 = _sampleBreathOverlayOpacity(tester);
      await tester.pump(const Duration(milliseconds: 800));
      final opacityAtT2 = _sampleBreathOverlayOpacity(tester);
      expect(opacityAtT2, opacityAtT1, reason: '呼吸层入场后必须静止定帧');

      // 唯一持续源：等待窗内仍有 frame 在被调度（阶段胶囊 700ms repeat
      // 在跑），而呼吸层已被上面两条证明静止——持续源恰为胶囊一个。
      expect(tester.binding.hasScheduledFrame, isTrue);
      expect(find.byType(ChatRunPhaseIndicator), findsOneWidget);
      expect(overlayFinder, findsOneWidget);

      // 收工：退出等待窗（胶囊 ticker 释放、会话存档链停摆），
      // 大步 pump 清掉 init 链与会话存档 debounce 的 pending Timer，
      // 避免 teardown 的 timersPending 不变量误伤。
      notifier.resetIdle();
      await tester.pump(const Duration(seconds: 30));
    },
  );

  testWidgets('reduce-motion 下呼吸层直接缺席（行为不回退）(SPEC-C #6 / N3)',
      (tester) async {
    tester.platformDispatcher.accessibilityFeaturesTestValue =
        const FakeAccessibilityFeatures(disableAnimations: true);
    addTearDown(tester.platformDispatcher.clearAccessibilityFeaturesTestValue);

    // 已知存量测试环境怪癖（与本卡改动无关的预存行为）：系统级
    // disableAnimations 下，屏幕里某些 AnimatedSize 零时长完成时会在
    // performLayout 内触发 markNeedsLayout 断言。在框架收集层吸收该类
    // 异常（其余异常照常转发，不会被吞）。
    final bindingOnError = FlutterError.onError;
    FlutterError.onError = (details) {
      if (details.exception.toString().contains('RenderAnimatedSize')) {
        return;
      }
      bindingOnError?.call(details);
    };
    addTearDown(() {
      FlutterError.onError = bindingOnError;
    });

    final notifier = await pumpWaitingChat(tester);

    notifier.enterWaitWindow();
    await tester.pump();
    for (var i = 0; i < 4; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }

    // reduce-motion：呼吸层构建为 SizedBox.shrink——挂载点保留但无渐变
    // 装饰、无 AnimatedBuilder 动画消费（旧行为逐字保留）。
    expect(overlayFinder, findsOneWidget);
    expect(
      find.descendant(of: overlayFinder, matching: find.byType(AnimatedBuilder)),
      findsNothing,
    );
    expect(
      find.descendant(of: overlayFinder, matching: find.byType(DecoratedBox)),
      findsNothing,
    );
    // 阶段胶囊照常在（reduce-motion 下其脉冲对点静止，见
    // chat_run_phase_indicator _StageDot 门控——本卡不触碰该行为）。
    expect(find.byType(ChatRunPhaseIndicator), findsOneWidget);

    // 收工：退出等待窗并清残留 pending Timer。
    notifier.resetIdle();
    await tester.pump(const Duration(seconds: 30));
  });
}
