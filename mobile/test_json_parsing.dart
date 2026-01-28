import 'dart:convert';
import 'lib/shared/entities/user_model.dart';

void main() {
  final json = {
    "id": "69be26bd-9421-4ad2-a07b-aac2f7994656",
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
    "equipped_skin": null,
    "equipped_title": null,
    "push_preferences": {
      "enable_curiosity": true,
      "persona_type": "coach",
      "daily_cap": 5,
      "active_slots": [],
      "timezone": "Asia/Shanghai"
    }
  };

  try {
    final user = UserModel.fromJson(json);
    print('✅ UserModel deserialization successful!');
    print('User: ${user.username}');
    print('PushPreferences: ${user.pushPreferences}');
    print('  - enableCuriosity: ${user.pushPreferences?.enableCuriosity}');
    print('  - dailyCap: ${user.pushPreferences?.dailyCap}');
    print('  - personaType: ${user.pushPreferences?.personaType}');
  } catch (e) {
    print('❌ Deserialization failed: $e');
  }
}
