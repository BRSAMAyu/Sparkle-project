// V3-FIX-259：StreakDayStatus wire 解析四层断链之端上消费面（台账 259）。
//
// 后端 StreakDayStatus 为 4 值（active/weak/frozen/missed），mobile 旧值集仅
// 3 值缺 weak，且 json_serializable $enumDecode 硬失败无兜底：
// - 迁移库修复后（或 create_all 库）weak 经 GET /achievements/streak/history
//   下发，端上解析当场 ArgumentError 崩（消费点 achievement_repository）；
// - 未来后端再增值（enum 被污染/演进）同样崩。
//
// 修复范式：execution_intent_model 的 unknown 哨兵 + 手写解析函数——
// 未知值不崩、降级 unknown 并记 log；weak 与后端值串精确对齐。
//
// 修复前实录（红）：weak/未知值解析抛 ArgumentError。
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

void main() {
  group('V3-FIX-259 StreakDayStatus wire decode', () {
    test('后端 weak 值串精确对齐可解析', () {
      final record = StreakDayRecord.fromJson(<String, dynamic>{
        'day': '2026-09-25',
        'status': 'weak',
        'used_freeze': false,
        'source_event': 'daily_checkin',
      });

      expect(record.status, StreakDayStatus.weak);
      expect(record.usedFreeze, isFalse);
      expect(record.sourceEvent, 'daily_checkin');
    });

    test('未知状态值降级 unknown 哨兵不崩（execution_intent 范式）', () {
      final record = StreakDayRecord.fromJson(<String, dynamic>{
        'day': '2026-09-25',
        'status': 'supercharged',
      });

      expect(record.status, StreakDayStatus.unknown);
    });

    test('status 缺失时同样降级 unknown 不崩', () {
      final record = StreakDayRecord.fromJson(<String, dynamic>{
        'day': '2026-09-25',
      });

      expect(record.status, StreakDayStatus.unknown);
    });

    test('既有三值解析行为保持不变', () {
      expect(
        StreakDayRecord.fromJson(<String, dynamic>{'day': '2026-09-25', 'status': 'active'}).status,
        StreakDayStatus.active,
      );
      expect(
        StreakDayRecord.fromJson(<String, dynamic>{'day': '2026-09-25', 'status': 'frozen'}).status,
        StreakDayStatus.frozen,
      );
      expect(
        StreakDayRecord.fromJson(<String, dynamic>{'day': '2026-09-25', 'status': 'missed'}).status,
        StreakDayStatus.missed,
      );
    });

    test('toJson 往返保持 wire 值串', () {
      final record = StreakDayRecord.fromJson(<String, dynamic>{
        'day': '2026-09-25',
        'status': 'weak',
      });

      expect(record.toJson()['status'], 'weak');
    });

    test('日历列表面：StreakHistoryResponse 含 weak 与未知行整表可解析', () {
      final response = StreakHistoryResponse.fromJson(<String, dynamic>{
        'days': [
          {'day': '2026-09-24', 'status': 'weak'},
          {'day': '2026-09-25', 'status': 'active'},
          {'day': '2026-09-26', 'status': 'brand_new_future_value'},
        ],
      });

      expect(response.days, hasLength(3));
      expect(response.days[0].status, StreakDayStatus.weak);
      expect(response.days[1].status, StreakDayStatus.active);
      expect(response.days[2].status, StreakDayStatus.unknown);
    });
  });
}
