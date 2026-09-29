import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/user/presentation/screens/unified_settings_screen.dart';
import '../shared/i18n_test_helper.dart';

/// V4-S02 · 统一设置面：提示音独立音量（环境/提示音两独立音量的 UI 面）。
///
/// 一正一反：
/// - 正：展开「感官反馈」→ 提示音音量滑杆可见可调，落位持久层，
///   且不连带环境音量（两独立音量）；
/// - 反：提示音开关关闭 → 提示音音量滑杆置灰（关了提示音还能调音量是
///   不诚实的中间态）。
void main() {
  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() async {
    SharedPreferences.setMockInitialValues(<String, Object>{
      'sensory_feedback.sound_enabled': true,
      'sensory_feedback.haptic_enabled': true,
      'sensory_feedback.aurora_linkage_enabled': true,
      'sensory_feedback.ambient_volume': 0.6,
    });
    await SensoryFeedbackService.dispose();
  });

  tearDown(() async {
    await SensoryFeedbackService.dispose();
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

  testWidgets('正·提示音音量滑杆可见；调整落持久层且不连带环境音量', (tester) async {
    tester.view.physicalSize = const Size(1200, 2800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await expandSensorySection(tester);

    expect(
      find.byKey(const ValueKey('sensory-sfx-volume-title')),
      findsOneWidget,
    );
    final slider = find.byKey(const ValueKey('sensory-sfx-volume'));
    expect(slider, findsOneWidget);

    // 滑到最左（0.0）→ onChangeEnd 落持久层。
    final rect = tester.getRect(slider);
    await tester.tapAt(Offset(rect.left + 1, rect.center.dy));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(await SensoryFeedbackService.getSfxVolume(), closeTo(0.0, 0.001));
    // 两独立音量：提示音调整不连带环境音量。
    expect(await SensoryFeedbackService.getAmbientVolume(), closeTo(0.6, 0.001));
  });

  testWidgets('反·提示音开关关闭后滑杆置灰（不提供无声可调的假中间态）',
      (tester) async {
    tester.view.physicalSize = const Size(1200, 2800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await expandSensorySection(tester);
    expect(
      tester.widget<Slider>(
        find.byKey(const ValueKey('sensory-sfx-volume')),
      ).onChanged,
      isNotNull,
    );

    await tester.tap(find.widgetWithText(SwitchListTile, '音效反馈'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(await SensoryFeedbackService.isSoundEnabled(), isFalse);
    expect(
      tester.widget<Slider>(
        find.byKey(const ValueKey('sensory-sfx-volume')),
      ).onChanged,
      isNull,
    );
  });
}
