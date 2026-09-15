import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/services/guest_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('GuestService', () {
    test('generates and persists a device-unique guest id', () async {
      SharedPreferences.setMockInitialValues({});
      final prefs = await SharedPreferences.getInstance();
      final service = GuestService(prefs);

      final firstGuestId = await service.getGuestId();
      final secondGuestId = await service.getGuestId();

      expect(firstGuestId, startsWith('guest_'));
      expect(firstGuestId, isNot('guest_sparkle_demo_visitor'));
      expect(secondGuestId, firstGuestId);
      expect(prefs.getString('guest_id'), firstGuestId);
    });

    test('migrates legacy shared guest id to a device-unique guest id',
        () async {
      SharedPreferences.setMockInitialValues({
        'guest_id': 'guest_sparkle_demo_visitor',
      });
      final prefs = await SharedPreferences.getInstance();
      final service = GuestService(prefs);

      final guestId = await service.getGuestId();

      expect(guestId, startsWith('guest_'));
      expect(guestId, isNot('guest_sparkle_demo_visitor'));
      expect(prefs.getString('guest_id'), guestId);
    });

    test('clearGuestData removes persisted guest state', () async {
      SharedPreferences.setMockInitialValues({
        'guest_id': 'guest_legacy123',
        'guest_nickname': '访客123',
      });
      final prefs = await SharedPreferences.getInstance();
      final service = GuestService(prefs);

      await service.clearGuestData();

      expect(prefs.getString('guest_id'), isNull);
      expect(prefs.getString('guest_nickname'), isNull);
      expect(service.isGuestMode, isFalse);
    });
  });
}
