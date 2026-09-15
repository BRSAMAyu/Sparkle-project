import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/shared/entities/user_model.dart';

void main() {
  test('UserModel parses push preferences and equipment sources', () {
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
      'equipped_skin': 'legendary_anniversary',
      'equipped_skin_source': 'achievement',
      'equipped_title': 'title_legend_scholar_001',
      'equipped_title_source': 'shop',
      'push_preferences': <String, Object?>{
        'enable_curiosity': true,
        'persona_type': 'coach',
        'daily_cap': 5,
        'active_slots': <Object?>[],
        'timezone': 'Asia/Shanghai',
      },
    };

    final user = UserModel.fromJson(json);

    expect(user.pushPreferences?.enableCuriosity, isTrue);
    expect(user.equippedSkin, 'legendary_anniversary');
    expect(user.equippedSkinSource, 'achievement');
    expect(user.equippedTitle, 'title_legend_scholar_001');
    expect(user.equippedTitleSource, 'shop');
  });
}
