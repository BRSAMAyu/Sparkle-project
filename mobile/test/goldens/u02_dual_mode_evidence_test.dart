import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:golden_toolkit/golden_toolkit.dart';
import 'package:sparkle/core/design/adaptive/emotion_responsive_theme.dart';
import 'package:sparkle/features/chat/chat.dart' show ChatNotifier;

import '../shared/u02_core_screens.dart';
import '../shared/u02_test_fonts.dart';

/// U-02 验收证据：四个核心屏 × standard/low 双刺激档真实渲染截图。
///
/// 运行（真跑出图）：
/// ```
/// flutter test test/goldens/u02_dual_mode_evidence_test.dart \
///   --dart-define=U02_CAPTURE_EVIDENCE=true --update-goldens
/// ```
/// 不带 dart-define 时整组 skip（与存量 golden 套件同一门控惯例），
/// 避免常规 CI 把证据图当回归基线比对。
///
/// 视口：wt390 U-09 矩阵 android 列 1080x2400@3.0（逻辑 360x800）。
/// 输出：v3/09_evidence/u02_rubric/<surface>__demo_data__android__
/// 1080x2400@3.0__<mode>.png（B-04 命名法，mode 位记录刺激档）。
void main() {
  setUpAll(initializeU02SurfaceEnvironment);

  final captureEnabled = const bool.fromEnvironment('U02_CAPTURE_EVIDENCE');

  Future<void> pumpSurface(
    WidgetTester tester,
    U02Surface surface,
    EmotionResponsiveConfig config,
  ) async {
    await tester.runAsync(U02TestFonts.load);
    await initializeU02SurfaceEnvironment();

    final chatNotifier = <ChatNotifier>[];
    final host = await u02SurfaceHost(
      surface,
      config,
      chatNotifierOut: chatNotifier,
    );
    await tester.pumpWidget(host);

    // 等真实屏的异步初始化落定；不用 pumpAndSettle（周期计时器不归零）。
    for (var i = 0; i < 20; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }

    if (surface == U02Surface.chat) {
      // chat_scroll_test 同款时序：初始化落定后再种消息（会话列表加载
      // 会重置早种的消息），随后再泵帧渲染消息列表。
      for (var i = 0; i < 20 && chatNotifier.isEmpty; i++) {
        await tester.pump(const Duration(milliseconds: 50));
      }
      seedU02ChatMessages(chatNotifier.single);
      for (var i = 0; i < 10; i++) {
        await tester.pump(const Duration(milliseconds: 50));
      }
    }
  }

  for (final surface in U02Surface.values) {
    for (final entry in {
      'standard': const EmotionResponsiveConfig.normal(),
      'low': const EmotionResponsiveConfig.lowStimulus(),
    }.entries) {
      testGoldens(
        '${surface.name} __ ${entry.key}',
        (tester) async {
          tester.view.physicalSize = Size(
            u02ViewportLogicalSize.width * u02ViewportDpr,
            u02ViewportLogicalSize.height * u02ViewportDpr,
          );
          tester.view.devicePixelRatio = u02ViewportDpr;
          addTearDown(tester.view.resetPhysicalSize);
          addTearDown(tester.view.resetDevicePixelRatio);

          // 登记棘轮（与 rubric 同真源）：已登记发现不放红（证据照常
          // 出图并在判定表留证）；未登记异常必须红。
          final registered = registeredU02Findings[surface]!;
          final caughtLayoutErrors = <String>[];
          final previousOnError = FlutterError.onError;
          FlutterError.onError = (details) {
            final info = details.toString();
            final location =
                RegExp(r'(?:\w+):file:///\S+/lib/([^\s(]+\.dart):(\d+)')
                    .firstMatch(info);
            if (info.contains('overflowed') && location != null) {
              caughtLayoutErrors
                  .add('layout:${location.group(1)}:${location.group(2)}');
            } else if (info.contains('RenderAnimatedSize')) {
              // F5：低刺激档 disableAnimations × AnimatedSize 交互触发
              // 框架层断言（RenderAnimatedSize 在 performLayout 中自脏）。
              caughtLayoutErrors.add('flutteranim:RenderAnimatedSize');
            } else if (details.exception is FlutterError) {
              caughtLayoutErrors.add(
                  'flutter:${info.substring(0, math.min(120, info.length))}');
            } else {
              previousOnError?.call(details);
            }
          };
          addTearDown(() => FlutterError.onError = previousOnError);

          await pumpSurface(tester, surface, entry.value);

          final unregistered = caughtLayoutErrors
              .where((e) => !registered.contains(e))
              .toSet();
          expect(
            unregistered,
            isEmpty,
            reason: '${surface.name}(${entry.key}) 存在未登记的布局/框架异常：'
                '$unregistered',
          );

          await expectLater(
            find.byType(MaterialApp),
            matchesGoldenFile(
              '../../../v3/09_evidence/u02_rubric/'
              '${surface.name}__demo_data__android__1080x2400@3.0__'
              '${entry.key}.png',
            ),
          );
        },
        skip: !captureEnabled,
      );
    }
  }
}
