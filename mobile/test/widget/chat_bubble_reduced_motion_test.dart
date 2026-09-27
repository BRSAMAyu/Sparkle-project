import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/adaptive/emotion_responsive_theme.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/aurora/data/models/aurora_calibration_card.dart';
import 'package:sparkle/features/aurora/presentation/providers/aurora_calibration_provider.dart';
import 'package:sparkle/features/aurora/presentation/widgets/aurora_calibration_strip.dart';
import 'package:sparkle/features/chat/chat.dart' show ChatNotifier;
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_bubble.dart';

import '../features/home/dashboard_test_harness.dart';
import '../shared/i18n_test_helper.dart';
import '../shared/u02_core_screens.dart';

/// U-02 F5 回归锁（V3-FIX-374）+ dashboard 漏修面扩展（V3-FIX-384）。
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
  // V3-FIX-384 dashboard 面：存量 dashboard harness 环境初始化（Hive/
  // prefs/ViewStorage，真异步区），幂等。
  setUpAll(initializeDashboardTestEnvironment);

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

  // ---- V3-FIX-384：dashboard 低层渲染宿主面（AuroraCalibrationStrip）----

  testWidgets(
      'V3-FIX-384: dashboard 低刺激档 AuroraCalibrationStrip 展开零 RenderAnimatedSize 断言、'
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
    var stripRendered = false;
    try {
      await tester.pumpWidget(
        _calibrationStripHost(const EmotionResponsiveConfig.lowStimulus()),
      );
      for (var i = 0; i < 10; i++) {
        await tester.pump(const Duration(milliseconds: 50));
      }
      stripRendered = find.text(_kFix384SurfaceLabel).evaluate().isNotEmpty;
      if (stripRendered) {
        await tester.tap(
          find
              .ancestor(
                of: find.text(_kFix384SurfaceLabel),
                matching: find.byType(InkWell),
              )
              .first,
        );
        for (var i = 0; i < 10; i++) {
          await tester.pump(const Duration(milliseconds: 50));
        }
      }
    } finally {
      // expect 前恢复 onError：测试失败要经原生链路报告。
      FlutterError.onError = previousOnError;
    }

    // 条面必须真实渲染（fixture 有 items），否则本锁空转。
    expect(stripRendered, isTrue, reason: '校准条未渲染，回归锁空转');
    // 展开后卡片内容可见（禁动效档直接挂载，无动画外壳）。
    expect(find.text(_kFix384CardStatement), findsOneWidget);
    expect(
      animatedSizeErrors,
      isEmpty,
      reason: '低刺激档校准条展开仍触发 RenderAnimatedSize 框架断言',
    );
    expect(
      _countZeroDurationAnimatedSize(tester),
      0,
      reason:
          '低刺激档渲染树仍存在 Duration.zero 的 AnimatedSize（V3-FIX-384 断言源）',
    );
  });

  testWidgets('V3-FIX-384 对照: standard 档 AuroraCalibrationStrip 保留 AnimatedSize 动画外壳',
      (tester) async {
    tester.view.physicalSize = Size(
      u02ViewportLogicalSize.width * u02ViewportDpr,
      u02ViewportLogicalSize.height * u02ViewportDpr,
    );
    tester.view.devicePixelRatio = u02ViewportDpr;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      _calibrationStripHost(const EmotionResponsiveConfig.normal()),
    );
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }
    await tester.tap(
      find
          .ancestor(
            of: find.text(_kFix384SurfaceLabel),
            matching: find.byType(InkWell),
          )
          .first,
    );
    // standard 档 SparkleMotionToken.standard 动画（300ms 档）有界泵帧落定。
    for (var i = 0; i < 6; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }

    expect(find.text(_kFix384CardStatement), findsOneWidget);
    expect(find.byType(AnimatedSize), findsWidgets);
  });
}

const String _kFix384SurfaceLabel = 'Aurora · 校准待你确认';
const String _kFix384CardStatement = 'V3-FIX-384 回归锁校准卡陈述';

AuroraCalibrationSurface _fix384CalibrationSurface() =>
    const AuroraCalibrationSurface(
      items: [
        AuroraCalibrationCard(
          id: 'fix384-card-1',
          title: '校准卡',
          statement: _kFix384CardStatement,
          confidence: 0.82,
          confidenceLabel: '82%',
          needsConfirmation: true,
          evidence: ['证据 A', '证据 B'],
        ),
      ],
      state: 'needs_confirmation',
      label: _kFix384SurfaceLabel,
    );

/// V3-FIX-384 宿主：真实 dashboard provider 管道（存量 harness）+ 真实
/// AuroraCalibrationStrip（dashboard_screen.dart:1298 低层渲染宿主同一
/// widget），校准面数据钉为确定性 fixture（渲染/主题层全部真实）。
Widget _calibrationStripHost(EmotionResponsiveConfig config) =>
    buildDashboardWidgetHarness(
      child: const AuroraCalibrationStrip(),
      theme: AppThemes.lightTheme,
      locale: const Locale('zh'),
      size: u02ViewportLogicalSize,
      emotionConfig: config,
      extraOverrides: [
        auroraCalibrationSurfaceProvider.overrideWith(
          (ref, planId) async => _fix384CalibrationSurface(),
        ),
      ],
    );

/// 渲染树级枚举：当前渲染树中 Duration.zero 的 RenderAnimatedSize 数量
/// （374 锁同款判据）。
int _countZeroDurationAnimatedSize(WidgetTester tester) {
  var count = 0;
  void visit(RenderObject child) {
    if (child is RenderAnimatedSize && child.duration == Duration.zero) {
      count++;
    }
    child.visitChildren(visit);
  }

  tester.binding.renderViews.first.visitChildren(visit);
  return count;
}
