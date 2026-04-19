import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/chat/presentation/providers/guidance_mode_provider.dart';

void main() {
  group('GuidanceModeNotifier', () {
    setUp(() async {
      SharedPreferences.setMockInitialValues({});
      await ViewStorageService.ensureInitialized();
    });

    test('defaults to aiGuide', () {
      final mode = GuidanceModeNotifier().state;
      expect(mode, GuidanceMode.aiGuide);
    });

    test('mode setter changes mode', () {
      final notifier = GuidanceModeNotifier();
      notifier.mode = GuidanceMode.selfGuide;
      expect(notifier.state, GuidanceMode.selfGuide);

      notifier.mode = GuidanceMode.aiGuide;
      expect(notifier.state, GuidanceMode.aiGuide);
    });

    test('toggle switches between modes', () {
      final notifier = GuidanceModeNotifier();
      expect(notifier.state, GuidanceMode.aiGuide);

      notifier.toggle();
      expect(notifier.state, GuidanceMode.selfGuide);

      notifier.toggle();
      expect(notifier.state, GuidanceMode.aiGuide);
    });
  });

  group('GuidanceMode', () {
    test('has correct enum values', () {
      expect(GuidanceMode.values, hasLength(2));
      expect(GuidanceMode.values, contains(GuidanceMode.aiGuide));
      expect(GuidanceMode.values, contains(GuidanceMode.selfGuide));
    });

    test('name property returns expected strings', () {
      expect(GuidanceMode.aiGuide.name, 'aiGuide');
      expect(GuidanceMode.selfGuide.name, 'selfGuide');
    });
  });
}
