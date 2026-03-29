import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

void main() {
  tearDown(() {
    debugDefaultTargetPlatformOverride = null;
    SensoryFeedbackService.forceNativeDebugSoundFallback = true;
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
}
