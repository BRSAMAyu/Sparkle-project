// V3-FIX-269/270：community 双族枚举漂移端上消费面（台账 269/270）。
//
// 后端真源 app/models/community.py：
// - GroupType 三值 squad/sprint/official（OFFICIAL="official"），mobile 旧镜像仅
//   squad/sprint 二值。API 面 schemas/community.py GroupTypeEnum 现仅下发
//   squad/sprint（official 为模型单面潜伏），一旦 schema 放开 GroupListItem/
//   GroupInfo $enumDecode 即 ArgumentError 崩（V3-FIX-259/260 同型断链）。
// - MessageType 十二值含 BROADCAST="broadcast"，community_advanced_service.py:751
//   真实落库且 wt297 已修 schema 侧缺成员——广播值现经群消息列表 API 原样下发，
//   mobile $enumDecode 遇 broadcast 即 ArgumentError，群聊页整体解析崩（活体面）。
//
// 修复范式（V3-FIX-260 判例）：补缺失值 + @JsonValue('unknown') 哨兵 +
// @JsonKey(unknownEnumValue) 兜底——未知值不崩、降级 unknown。
//
// 修复前实录（红）：'official'/'broadcast'/未知值解析抛 ArgumentError。
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';

Map<String, dynamic> _groupListJson(String type) => <String, dynamic>{
      'id': 'g1',
      'name': '测试群',
      'type': type,
      'member_count': 10,
      'total_flame_power': 100,
      'today_checkin_count': 3,
      'focus_tags': <String>['math'],
    };

Map<String, dynamic> _messageJson(String messageType) => <String, dynamic>{
      'id': 'm1',
      'message_type': messageType,
      'content': 'hello',
      'created_at': '2026-09-25T10:00:00Z',
      'updated_at': '2026-09-25T10:00:00Z',
    };

void main() {
  group('V3-FIX-269 GroupType wire decode', () {
    test('official 值串精确对齐可解析（schema 放开前潜伏面拆除）', () {
      final group = GroupListItem.fromJson(_groupListJson('official'));
      expect(group.type, GroupType.official);
    });

    test('未知群组类型降级 unknown 哨兵不崩', () {
      final group = GroupListItem.fromJson(_groupListJson('guild'));
      expect(group.type, GroupType.unknown);
    });

    test('既有 squad/sprint 解析行为保持不变', () {
      expect(
        GroupListItem.fromJson(_groupListJson('squad')).type,
        GroupType.squad,
      );
      expect(
        GroupListItem.fromJson(_groupListJson('sprint')).type,
        GroupType.sprint,
      );
    });

    test('GroupInfo 详表面对 official 同样可解析', () {
      final info = GroupInfo.fromJson(<String, dynamic>{
        ..._groupListJson('official'),
        'total_tasks_completed': 5,
        'max_members': 50,
        'is_public': true,
        'join_requires_approval': false,
        'created_at': '2026-09-25T10:00:00Z',
        'updated_at': '2026-09-25T10:00:00Z',
      });
      expect(info.type, GroupType.official);
    });
  });

  group('V3-FIX-270 MessageType wire decode', () {
    test('broadcast 值串精确对齐可解析（wt297 实录活体崩溃面）', () {
      final message = MessageInfo.fromJson(_messageJson('broadcast'));
      expect(message.messageType, MessageType.broadcast);
    });

    test('未知消息类型降级 unknown 哨兵不崩', () {
      final message = MessageInfo.fromJson(_messageJson('hologram'));
      expect(message.messageType, MessageType.unknown);
    });

    test('既有 11 值解析行为保持不变', () {
      expect(
        MessageInfo.fromJson(_messageJson('text')).messageType,
        MessageType.text,
      );
      expect(
        MessageInfo.fromJson(_messageJson('task_share')).messageType,
        MessageType.taskShare,
      );
      expect(
        MessageInfo.fromJson(_messageJson('system')).messageType,
        MessageType.system,
      );
    });

    test('私聊表面对未知类型同样降级 unknown 不崩', () {
      final message = PrivateMessageInfo.fromJson(<String, dynamic>{
        'id': 'pm1',
        'sender': <String, dynamic>{'id': 'u1', 'username': 'alice'},
        'receiver': <String, dynamic>{'id': 'u2', 'username': 'bob'},
        'message_type': 'broadcast',
        'is_read': false,
        'created_at': '2026-09-25T10:00:00Z',
        'updated_at': '2026-09-25T10:00:00Z',
      });
      expect(message.messageType, MessageType.broadcast);
    });
  });
}
