import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/user/presentation/screens/unified_settings_screen.dart';
import '../shared/i18n_test_helper.dart';

/// V4-U14 · 统一设置面：背景声独立开关 + 音频诚实降级提示行。
///
/// 一正一反：
/// - 正：展开「感官反馈」→ 背景声开关可见，关闭后持久层落位（重开保持）；
/// - 反：系统拒绝播放（降级位）→ 设置页如实呈现降级提示行，而非假成功。
void main() {
  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() async {
    SharedPreferences.setMockInitialValues(<String, Object>{
      'sensory_feedback.sound_enabled': true,
      'sensory_feedback.haptic_enabled': true,
      'sensory_feedback.aurora_linkage_enabled': true,
    });
    await SensoryFeedbackService.dispose();
  });

  tearDown(() async {
    await SensoryFeedbackService.dispose();
    SensoryFeedbackService.debugSetAudioPlaybackDegraded(false);
  });

  Future<void> expandSensorySection(WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        child: testMaterialApp(
          theme: AppThemes.lightTheme,
          home: const UnifiedSettingsScreen(),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));

    await tester.tap(find.text('感官反馈').first);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
  }

  testWidgets('正·背景声独立开关可见；关闭后持久层落位', (tester) async {
    tester.view.physicalSize = const Size(1200, 2600);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await expandSensorySection(tester);

    final toggle = find.byKey(const ValueKey('sensory-ambient-toggle'));
    expect(toggle, findsOneWidget);
    expect(await SensoryFeedbackService.isAmbientEnabled(), isTrue);

    await tester.tap(find.widgetWithText(SwitchListTile, '背景声'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(await SensoryFeedbackService.isAmbientEnabled(), isFalse);
    // 提示音开关独立性：背景声关闭不连带提示音。
    expect(await SensoryFeedbackService.isSoundEnabled(), isTrue);
  });

  testWidgets('反·音频降级位呈现诚实提示行（不假成功）', (tester) async {
    SensoryFeedbackService.debugSetAudioPlaybackDegraded(true);

    await expandSensorySection(tester);

    expect(
      find.byKey(const ValueKey('sensory-audio-degraded-notice')),
      findsOneWidget,
    );
    expect(find.text('系统拒绝了音频播放，提示音已静音降级；任务与提醒不受影响'), findsOneWidget);
  });
}
