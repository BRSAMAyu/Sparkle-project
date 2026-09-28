import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    await SensoryFeedbackService.dispose();
    SensoryFeedbackService.forceNativeDebugSoundFallback = true;
    debugDefaultTargetPlatformOverride = TargetPlatform.android;
  });

  tearDown(() async {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(SystemChannels.platform, null);
    debugDefaultTargetPlatformOverride = null;
    SensoryFeedbackService.forceNativeDebugSoundFallback = true;
    await SensoryFeedbackService.dispose();
  });

  // V4-S02 行为差量：提示音默认关闭（MOTION「默认环境声与提示音关闭」/
  // 卡验收1「未明确点播无声音」）。原断言「defaults on」按 V4 规格显式
  // 变更为 defaults off——非删断言凑绿，反例面（显式开启后发声）由
  // sensory_feedback_service_s02_test.dart 钉死。
  test('sound preference defaults off (V4-S02) and persists toggles',
      () async {
    expect(await SensoryFeedbackService.isSoundEnabled(), isFalse);

    await SensoryFeedbackService.setSoundEnabled(true);

    expect(await SensoryFeedbackService.isSoundEnabled(), isTrue);
    await SensoryFeedbackService.setSoundEnabled(false);
    expect(await SensoryFeedbackService.isSoundEnabled(), isFalse);
  });

  test('haptic preference defaults on and persists toggles', () async {
    expect(await SensoryFeedbackService.isHapticEnabled(), isTrue);

    await SensoryFeedbackService.setHapticEnabled(false);

    expect(await SensoryFeedbackService.isHapticEnabled(), isFalse);
  });

  test('ambient volume and scene are saved without autoplay side effects',
      () async {
    await SensoryFeedbackService.setAmbientVolume(0.72);
    await SensoryFeedbackService.setAmbientScene(AmbientScene.ocean);

    expect(await SensoryFeedbackService.getAmbientVolume(), 0.72);
    expect(
      await SensoryFeedbackService.getSavedAmbientScene(),
      AmbientScene.ocean,
    );
    expect(SensoryFeedbackService.currentScene, AmbientScene.none);
    expect(AmbientScene.ocean.assetPath, 'audio/ambient/ocean_waves.ogg');
  });

  test('sound budget limits rapid distinct events to five emissions',
      () async {
    // V4-S02：默认关闭后，预算语义以「已点播」为前提——显式开启再计。
    await SensoryFeedbackService.setSoundEnabled(true);
    var soundCalls = 0;
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(SystemChannels.platform, (call) async {
      if (call.method == 'SystemSound.play') {
        soundCalls++;
      }
      return null;
    });

    for (final event in const <SensoryFeedbackEvent>[
      SensoryFeedbackEvent.tap,
      SensoryFeedbackEvent.toggle,
      SensoryFeedbackEvent.selection,
      SensoryFeedbackEvent.navigation,
      SensoryFeedbackEvent.sheetOpen,
      SensoryFeedbackEvent.dialogOpen,
      SensoryFeedbackEvent.confirm,
    ]) {
      await SensoryFeedbackService.emit(event, enableHaptic: false);
    }
    await Future<void>.delayed(const Duration(milliseconds: 10));

    expect(soundCalls, 5);
  });

  test('haptic budget limits rapid distinct events to three emissions',
      () async {
    var hapticCalls = 0;
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(SystemChannels.platform, (call) async {
      if (call.method.startsWith('HapticFeedback.')) {
        hapticCalls++;
      }
      return null;
    });

    for (final event in const <SensoryFeedbackEvent>[
      SensoryFeedbackEvent.tap,
      SensoryFeedbackEvent.toggle,
      SensoryFeedbackEvent.selection,
      SensoryFeedbackEvent.navigation,
      SensoryFeedbackEvent.sheetOpen,
    ]) {
      await SensoryFeedbackService.emit(
        event,
        enableSound: false,
      );
    }
    await Future<void>.delayed(const Duration(milliseconds: 10));

    expect(hapticCalls, 3);
  });

  test('Aurora linkage disabled prevents mapped feedback emission', () async {
    var platformCalls = 0;
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(SystemChannels.platform, (call) async {
      platformCalls++;
      return null;
    });

    await SensoryFeedbackService.setAuroraLinkageEnabled(false);
    await SensoryFeedbackService.emitAuroraEvent(
      AuroraSensoryEvent.achievementUnlocked,
    );
    await Future<void>.delayed(const Duration(milliseconds: 10));

    expect(platformCalls, 0);
  });
}
