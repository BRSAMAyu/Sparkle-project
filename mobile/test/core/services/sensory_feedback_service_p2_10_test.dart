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

  test('sound preference defaults on and persists toggles', () async {
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

  test('sound budget limits rapid distinct events to five emissions', () async {
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
