import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/adaptive/emotion_responsive_theme.dart';
import 'package:sparkle/features/chat/chat.dart' show ChatNotifier;
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_bubble.dart';

import '../shared/i18n_test_helper.dart';
import '../shared/u02_core_screens.dart';

/// U-02 F5 回归锁（V3-FIX-374）。
///
/// 根因（wt399 rubric chat/low 实测、wt683 全栈复现定位）：低刺激档
/// `EmotionResponsiveConfig.lowStimulus` → `MediaQuery.disableAnimations` →
/// `context.reduceMotion == true`，ChatBubble 消息正文 `AnimatedSize`
/// （chat_bubble.dart，LayoutBuilder 内）收到 `Duration.zero`；零时长下
/// AnimationController 在 RenderAnimatedSize 自身 performLayout 中同步
/// `notifyListeners()` → `markNeedsLayout(self)` → 框架断言
/// "RenderAnimatedSize was mutated in its own performLayout"。
///
/// 修复：禁动效档直接挂载 child（零时长 AnimatedSize 的语义等价物，
/// 低刺激行为不变），standard 档动画外壳不变。
///
/// 复跑：`flutter test test/widget/chat_bubble_reduced_motion_test.dart`
void main() {
  setUpAll(initializeU02SurfaceEnvironment);

  testWidgets(
      'U-02 F5/V3-FIX-374: 低刺激档真实 ChatScreen 渲染零 RenderAnimatedSize 断言、'
      '渲染树无零时长 AnimatedSize', (tester) async {
    tester.view.physicalSize = Size(
      u02ViewportLogicalSize.width * u02ViewportDpr,
      u02ViewportLogicalSize.height * u02ViewportDpr,
    );
    tester.view.devicePixelRatio = u02ViewportDpr;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final animatedSizeErrors = <String>[];
    final previousOnError = FlutterError.onError;
    FlutterError.onError = (details) {
      final info = details.toString();
      if (info.contains('RenderAnimatedSize')) {
        animatedSizeErrors.add(info);
      } else {
        previousOnError?.call(details);
      }
    };
    try {
      final chatNotifier = <ChatNotifier>[];
      final host = await u02SurfaceHost(
        U02Surface.chat,
        const EmotionResponsiveConfig.lowStimulus(),
        chatNotifierOut: chatNotifier,
      );
      await tester.pumpWidget(host);
      for (var i = 0; i < 20; i++) {
        await tester.pump(const Duration(milliseconds: 100));
      }
      for (var i = 0; i < 20 && chatNotifier.isEmpty; i++) {
        await tester.pump(const Duration(milliseconds: 50));
      }
      seedU02ChatMessages(chatNotifier.single);
      for (var i = 0; i < 10; i++) {
        await tester.pump(const Duration(milliseconds: 50));
      }
    } finally {
      // expect 前恢复 onError：测试失败要经原生链路报告。
      FlutterError.onError = previousOnError;
    }

    expect(
      animatedSizeErrors,
      isEmpty,
      reason: '低刺激档 ChatScreen 仍触发 RenderAnimatedSize 框架断言',
    );

    // 渲染树级钉死：低刺激档不允许存在零时长 AnimatedSize（修复前的
    // 断言源形态）。修后 chat_bubble 禁动效档不装动画外壳。
    var zeroDurationAnimatedSize = 0;
    void visit(RenderObject child) {
      if (child is RenderAnimatedSize && child.duration == Duration.zero) {
        zeroDurationAnimatedSize++;
      }
      child.visitChildren(visit);
    }

    tester.binding.renderViews.first.visitChildren(visit);
    expect(
      zeroDurationAnimatedSize,
      0,
      reason: '低刺激档渲染树仍存在 Duration.zero 的 AnimatedSize（F5 断言源）',
    );
  });

  testWidgets('standard 档 ChatBubble 保留 AnimatedSize 动画外壳', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        child: testMaterialApp(
          home: EmotionResponsiveAppWrapper(
            config: const EmotionResponsiveConfig.normal(),
            child: Scaffold(
              body: ListView(
                children: [
                  ChatBubble(
                    message: ChatMessageModel(
                      id: 'u02-f5-std',
                      conversationId: 'u02-f5',
                      content: '短消息',
                      role: MessageRole.assistant,
                      createdAt: DateTime(2026, 9, 25, 10),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
    // ChatBubble 持循环动画控制器，pumpAndSettle 会超时；有界泵帧。
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.byType(AnimatedSize), findsWidgets);
  });
}
