import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

/// V3-FIX-260：AchievementType.PLANNING 后端单面新增的 mobile 对齐。
///
/// 后端 AchievementType 11 值（含 PLANNING="planning"，DB 迁移已就位），
/// mobile 若缺 planning 值或 decode 无兜底，成就列表 API 一旦下发 planning
/// 即崩解析。本测试钉住：
/// 1. planning 值可解码（与 backend models/achievement.py 值串精确对齐）；
/// 2. 未知值不崩、降级 unknown 哨兵（execution_intent 范式）；
/// 3. 成就列表嵌套解码路径（AchievementWithProgress）同样存活。
void main() {
  Map<String, dynamic> achievementJson(String type) => <String, dynamic>{
        'id': 'ach-1',
        'name': '规划成就',
        'type': type,
        'rarity': 'rare',
        'created_at': '2026-09-25T00:00:00Z',
        'updated_at': '2026-09-25T00:00:00Z',
      };

  group('AchievementType wire 解码（V3-FIX-260）', () {
    test('planning 值解码为 AchievementType.planning（与后端值串对齐）', () {
      final model = AchievementModel.fromJson(achievementJson('planning'));

      expect(model.type, AchievementType.planning);
    });

    test('planning 值 toJson 往返保持 wire 串', () {
      final model = AchievementModel.fromJson(achievementJson('planning'));

      expect(model.toJson()['type'], 'planning');
    });

    test('未知类型值不崩、降级 unknown 哨兵', () {
      final model = AchievementModel.fromJson(achievementJson('quantum_flip'));

      expect(model.type, AchievementType.unknown);
    });

    test('成就列表嵌套解码遇 planning 不崩', () {
      final payload = <String, dynamic>{
        'achievement': achievementJson('planning'),
        'user_progress': null,
        'is_unlocked': false,
        'progress_percentage': 0,
      };

      final decoded = AchievementWithProgress.fromJson(payload);

      expect(decoded.achievement.type, AchievementType.planning);
      expect(decoded.isUnlocked, isFalse);
    });

    test('值集与后端 AchievementType 11 值精确对齐（另加 unknown 哨兵）', () {
      // 与 backend/app/models/achievement.py AchievementType 逐值对照。
      const backendWireValues = <String>[
        'milestone',
        'streak',
        'mastery',
        'task_complete',
        'hidden',
        'social',
        'contract',
        'study_time',
        'node_explore',
        'sprint',
        'planning',
      ];

      expect(
        AchievementType.values.length,
        backendWireValues.length + 1,
        reason: '11 个后端值 + 1 个 unknown 哨兵',
      );
      expect(
        AchievementType.values.contains(AchievementType.unknown),
        isTrue,
        reason: 'unknown 哨兵必须存在',
      );

      for (final wire in backendWireValues) {
        final model = AchievementModel.fromJson(achievementJson(wire));
        expect(
          model.type,
          isNot(AchievementType.unknown),
          reason: '后端值 "$wire" 应可解码而非降级 unknown',
        );
        expect(
          model.toJson()['type'],
          wire,
          reason: '往返应保持 wire 串 "$wire"',
        );
      }
    });
  });
}
