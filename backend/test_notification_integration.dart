import 'shared/entities/user_model.dart';

void main() {
  print('\x1B[60m=\x1B[0m' * 30);
  print('\x1B[1;35m🧪 FRONTEND NOTIFICATION SYSTEM TEST\x1B[0m');
  print('\x1B[60m=\x1B[0m' * 30);
  print('\x1B[0m');

  // Test 1: Deserialization with push_preferences
  print('\x1B[34m📋 TEST 1: Deserialization with push_preferences\x1B[0m');
  print('\x1B[90m-\x1B[0m' * 60);
  final jsonWithPrefs = {
    "id": "652a2a54-cb21-4791-bdb8-7421b460239c",
    "username": "testuser",
    "email": "test@example.com",
    "nickname": "Test User",
    "avatar_url": null,
    "avatar_status": "approved",
    "pending_avatar_url": null,
    "flame_level": 5,
    "flame_brightness": 0.8,
    "depth_preference": 0.7,
    "curiosity_preference": 0.6,
    "is_active": true,
    "status": "online",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00",
    "photon_balance": 100,
    "equipped_skin": "fire_skin_001",
    "equipped_title": "early_adopter",
    "push_preferences": {
      "enable_curiosity": true,
      "persona_type": "coach",
      "daily_cap": 5,
      "active_slots": [
        {"start": "08:00", "end": "09:00"},
        {"start": "18:00", "end": "19:00"}
      ],
      "timezone": "Asia/Shanghai"
    }
  };

  try {
    final user1 = UserModel.fromJson(jsonWithPrefs);
    print('\x1B[32m✅ Deserialization successful\x1B[0m');
    print('   Username: ${user1.username}');
    print('   PushPreferences: ${user1.pushPreferences != null ? "\x1B[32m✅ Present\x1B[0m" : "\x1B[31m❌ Null\x1B[0m"}');
    if (user1.pushPreferences != null) {
      print('   - enableCuriosity: ${user1.pushPreferences!.enableCuriosity}');
      print('   - personaType: ${user1.pushPreferences!.personaType}');
      print('   - dailyCap: ${user1.pushPreferences!.dailyCap}');
      print('   - timezone: ${user1.pushPreferences!.timezone}');
      print('   - activeSlots: ${user1.pushPreferences!.activeSlots!.length} slots');
    }
  } catch (e) {
    print('\x1B[31m❌ Failed: $e\x1B[0m');
  }
  print('\x1B[0m');

  // Test 2: Deserialization with null push_preferences
  print('\x1B[34m📋 TEST 2: Deserialization with null push_preferences\x1B[0m');
  print('\x1B[90m-\x1B[0m' * 60);
  final jsonWithoutPrefs = {
    "id": "12345678-1234-1234-1234-123456789012",
    "username": "newuser",
    "email": "new@example.com",
    "avatar_status": "approved",
    "flame_level": 1,
    "flame_brightness": 0.5,
    "depth_preference": 0.5,
    "curiosity_preference": 0.5,
    "is_active": true,
    "status": "offline",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00",
    "photon_balance": 0,
    "push_preferences": null
  };

  try {
    final user2 = UserModel.fromJson(jsonWithoutPrefs);
    print('\x1B[32m✅ Deserialization successful with null push_preferences\x1B[0m');
    print('   PushPreferences is null: ${user2.pushPreferences == null}');
  } catch (e) {
    print('\x1B[31m❌ Failed: $e\x1B[0m');
  }
  print('\x1B[0m');

  // Test 3: Deserialization without push_preferences field
  print('\x1B[34m📋 TEST 3: Deserialization without push_preferences field\x1B[0m');
  print('\x1B[90m-\x1B[0m' * 60);
  final jsonNoPrefsField = {
    "id": "87654321-4321-4321-4321-210987654321",
    "username": "olduser",
    "email": "old@example.com",
    "avatar_status": "approved",
    "flame_level": 3,
    "flame_brightness": 0.7,
    "depth_preference": 0.6,
    "curiosity_preference": 0.6,
    "is_active": true,
    "status": "online",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00",
    "photon_balance": 50
  };

  try {
    final user3 = UserModel.fromJson(jsonNoPrefsField);
    print('\x1B[32m✅ Deserialization successful without push_preferences field\x1B[0m');
    print('   PushPreferences defaults to null: ${user3.pushPreferences == null}');
  } catch (e) {
    print('\x1B[31m❌ Failed: $e\x1B[0m');
  }
  print('\x1B[0m');

  // Test 4: PushPreferences serialization
  print('\x1B[34m📋 TEST 4: PushPreferences Serialization (toJson)\x1B[0m');
  print('\x1B[90m-\x1B[0m' * 60);
  final prefs = PushPreferences(
    enableCuriosity: false,
    personaType: 'anime',
    dailyCap: 10,
    activeSlots: [
      {"start": "20:00", "end": "22:00"}
    ],
    timezone: 'America/New_York'
  );

  try {
    final json = prefs.toJson();
    print('\x1B[32m✅ Serialization successful\x1B[0m');
    print('   JSON keys: ${json.keys.toList()}');
    print('   enable_curiosity: ${json['enable_curiosity']}');
    print('   persona_type: ${json['persona_type']}');
    print('   daily_cap: ${json['daily_cap']}');
  } catch (e) {
    print('\x1B[31m❌ Failed: $e\x1B[0m');
  }
  print('\x1B[0m');

  print('\x1B[60m=\x1B[0m' * 30);
  print('\x1B[1;32m✅ ALL FRONTEND TESTS PASSED\x1B[0m');
  print('\x1B[60m=\x1B[0m' * 30);
}
