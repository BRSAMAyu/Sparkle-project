import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/services/user_preferences_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('UserPreferencesService', () {
    test('returns sensible defaults for first-time users', () async {
      SharedPreferences.setMockInitialValues({});
      final prefs = await SharedPreferences.getInstance();
      final service = UserPreferencesService(prefs);

      final values = await service.getPreferences();

      expect(values['theme_mode'], 'system');
      expect(values['notifications_enabled'], isTrue);
      expect(values['haptics_enabled'], isTrue);
      expect(values['sound_enabled'], isTrue);
      expect(values['memory_strategy'], 'balanced');
      expect(values['default_focus_minutes'], 25);
      expect(values['default_break_minutes'], 5);
      expect(values['pomodoro_enabled'], isTrue);
      expect(values['ambient_scene'], 'rain');
    });

    test('merges saved values with defaults', () async {
      SharedPreferences.setMockInitialValues({
        'user_preferences':
            '{"theme_mode":"light","default_focus_minutes":45,"ambient_scene":"forest"}',
      });
      final prefs = await SharedPreferences.getInstance();
      final service = UserPreferencesService(prefs);

      final values = await service.getPreferences();

      expect(values['theme_mode'], 'light');
      expect(values['default_focus_minutes'], 45);
      expect(values['ambient_scene'], 'forest');
      expect(values['memory_strategy'], 'balanced');
      expect(values['notifications_enabled'], isTrue);
    });
  });
}
