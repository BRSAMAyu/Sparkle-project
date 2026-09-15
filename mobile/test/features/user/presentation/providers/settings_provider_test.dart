import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';

void main() {
  group('settings normalization', () {
    test('maps legacy notification levels to supported dropdown values', () {
      expect(normalizeNotificationLevelSetting('focused'), 'minimal');
      expect(normalizeNotificationLevelSetting('standard'), 'standard');
      expect(normalizeNotificationLevelSetting('verbose'), 'verbose');
      expect(normalizeNotificationLevelSetting('unknown'), 'standard');
    });

    test('normalizes transparency levels from strings and bounds numbers', () {
      expect(normalizeTransparencyLevelSetting('basic'), 1);
      expect(normalizeTransparencyLevelSetting('advanced'), 3);
      expect(normalizeTransparencyLevelSetting(99), 3);
      expect(normalizeTransparencyLevelSetting(-1), 0);
    });

    test('normalizes system update levels from legacy labels', () {
      expect(normalizeSystemUpdateLevelSetting('minimal'), 0);
      expect(normalizeSystemUpdateLevelSetting('summary'), 1);
      expect(normalizeSystemUpdateLevelSetting('verbose'), 2);
      expect(normalizeSystemUpdateLevelSetting(10), 2);
    });

    test('normalizes ai reasoning mode aliases', () {
      expect(normalizeAiReasoningModeSetting('quick'), 'fast');
      expect(normalizeAiReasoningModeSetting('standard'), 'balanced');
      expect(normalizeAiReasoningModeSetting('intensive'), 'deep');
      expect(normalizeAiReasoningModeSetting('mystery'), 'balanced');
    });

    test('notification settings model sanitizes payload values', () {
      final settings = NotificationPreferenceSettings.fromJson({
        'notification_level': 'focused',
        'quiet_hours_enabled': true,
      });

      expect(settings.notificationLevel, 'minimal');
      expect(settings.quietHoursEnabled, isTrue);
      expect(settings.isLoaded, isTrue);
    });
  });
}
