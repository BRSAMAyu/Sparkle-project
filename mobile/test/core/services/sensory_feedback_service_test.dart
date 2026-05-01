import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    SensoryFeedbackService.debugSetAuroraLinkageEnabledCache(true);
  });

  tearDown(() {
    debugDefaultTargetPlatformOverride = null;
    SensoryFeedbackService.forceNativeDebugSoundFallback = true;
    SensoryFeedbackService.debugSetAuroraLinkageEnabledCache(true);
  });

  test('uses native debug sound fallback on mobile debug targets', () {
    debugDefaultTargetPlatformOverride = TargetPlatform.android;
    expect(SensoryFeedbackService.shouldUseNativeDebugSoundFallback, isTrue);

    debugDefaultTargetPlatformOverride = TargetPlatform.iOS;
    expect(SensoryFeedbackService.shouldUseNativeDebugSoundFallback, isTrue);
  });

  test('does not force native debug sound fallback on desktop targets', () {
    debugDefaultTargetPlatformOverride = TargetPlatform.macOS;
    expect(SensoryFeedbackService.shouldUseNativeDebugSoundFallback, isFalse);
  });

  test('Aurora sensory linkage preference can be disabled', () async {
    expect(await SensoryFeedbackService.isAuroraLinkageEnabled(), isTrue);

    await SensoryFeedbackService.setAuroraLinkageEnabled(false);

    expect(await SensoryFeedbackService.isAuroraLinkageEnabled(), isFalse);
  });

  test('Aurora sensory events map to budgeted feedback events', () {
    expect(
      SensoryFeedbackService.debugFeedbackEventForAurora(
        AuroraSensoryEvent.coreSessionOpen,
      ),
      SensoryFeedbackEvent.sheetOpen,
    );
    expect(
      SensoryFeedbackService.debugFeedbackEventForAurora(
        AuroraSensoryEvent.correctionCompleted,
      ),
      SensoryFeedbackEvent.confirm,
    );
    expect(
      SensoryFeedbackService.debugFeedbackEventForAurora(
        AuroraSensoryEvent.achievementUnlocked,
      ),
      SensoryFeedbackEvent.achievementRare,
    );
    expect(
      SensoryFeedbackService.debugFeedbackEventForAurora(
        AuroraSensoryEvent.streakContinued,
      ),
      SensoryFeedbackEvent.checkin,
    );
  });
}
