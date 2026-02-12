// ignore_for_file: avoid_print, prefer_single_quotes, require_trailing_commas

import 'package:sparkle/shared/entities/user_model.dart';

void main() {
  final json = <String, Object?>{
    'id': '652a2a54-cb21-4791-bdb8-7421b460239c',
    'username': 'testuser',
    'email': 'test@example.com',
    'avatar_status': 'approved',
    'flame_level': 5,
    'flame_brightness': 0.8,
    'depth_preference': 0.7,
    'curiosity_preference': 0.6,
    'is_active': true,
    'status': 'online',
    'created_at': '2024-01-01T00:00:00',
    'updated_at': '2024-01-01T00:00:00',
    'photon_balance': 100,
    'push_preferences': <String, Object?>{
      'enable_curiosity': true,
      'persona_type': 'coach',
      'daily_cap': 5,
      'active_slots': <Object?>[],
      'timezone': 'Asia/Shanghai',
    },
  };

  final user = UserModel.fromJson(json);
  print('✅ Success! pushPreferences: ${user.pushPreferences?.enableCuriosity}');
}
