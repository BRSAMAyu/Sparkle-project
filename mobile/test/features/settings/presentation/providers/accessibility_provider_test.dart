import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/settings/presentation/providers/accessibility_provider.dart';

void main() {
  group('AccessibilitySettings', () {
    test('normalizes payload values and clamps font scale', () {
      final settings = AccessibilitySettings.fromJson({
        'font_scale': 2.0,
        'high_contrast': 'yes',
        'screen_reader_optimized': 'true',
        'touch_target_size': 'extra_large',
        'reduce_motion': 1,
        'color_blind_friendly': 'on',
        'tts_enabled': 'false',
        'haptic_feedback': 'no',
        'low_load_mode': true,
      });

      expect(settings.fontScale, 1.4);
      expect(settings.highContrast, isTrue);
      expect(settings.screenReaderOptimized, isTrue);
      expect(settings.touchTargetSize, TouchTargetSize.extraLarge);
      expect(settings.reduceMotion, isTrue);
      expect(settings.colorBlindFriendly, isTrue);
      expect(settings.ttsEnabled, isFalse);
      expect(settings.hapticFeedback, isFalse);
      expect(settings.lowLoadMode, isTrue);
    });

    test('serializes into user_settings accessibility payload', () {
      const settings = AccessibilitySettings(
        fontScale: 1.15,
        highContrast: true,
        touchTargetSize: TouchTargetSize.large,
        reduceMotion: true,
      );

      expect(settings.toUserSettingsPayload(), {
        'accessibility_settings': {
          'font_scale': 1.15,
          'high_contrast': true,
          'screen_reader_optimized': false,
          'touch_target_size': 'large',
          'reduce_motion': true,
          'color_blind_friendly': false,
          'tts_enabled': false,
          'haptic_feedback': true,
          'low_load_mode': false,
        },
        'haptics_enabled': true,
        'galaxy_accessibility_defaults': {
          'screen_reader_enabled': false,
          'reduce_motion': true,
          'high_contrast': true,
          'haptic_enabled': true,
        },
      });
    });

    test('low-load mode applies calmer defaults without shrinking font', () {
      const settings = AccessibilitySettings(fontScale: 1.2);

      final lowLoad = settings.asLowLoadDefaults(true);

      expect(lowLoad.lowLoadMode, isTrue);
      expect(lowLoad.reduceMotion, isTrue);
      expect(lowLoad.screenReaderOptimized, isTrue);
      expect(lowLoad.touchTargetSize, TouchTargetSize.large);
      expect(lowLoad.fontScale, 1.2);
    });
  });
}
