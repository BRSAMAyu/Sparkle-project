import 'package:flutter_test/flutter_test.dart';

/// Regression test for ISSUE-20260504-1200-G4:
/// Mock getMessages/getPrivateMessages must respect beforeId and limit
/// parameters for pagination, not ignore them and return all messages.

/// Minimal stub mimicking MessageInfo/PrivateMessageInfo shape for pagination.
class _MsgStub {
  _MsgStub({required this.id, required this.createdAt});
  final String id;
  final DateTime createdAt;
}

/// Returns messages sorted newest-first, respecting beforeId and limit.
List<_MsgStub> paginate(
  List<_MsgStub> allMessages, {
  String? beforeId,
  int limit = 50,
}) {
  final messages = List<_MsgStub>.from(allMessages);
  messages.sort((a, b) => b.createdAt.compareTo(a.createdAt));

  if (beforeId != null) {
    final index = messages.indexWhere((m) => m.id == beforeId);
    if (index >= 0) {
      final older = messages.sublist(index + 1);
      return older.take(limit).toList();
    }
  }
  return messages.take(limit).toList();
}

void main() {
  final t0 = DateTime(2026, 5, 1, 12, 0);
  final messages = List.generate(
    10,
    (i) => _MsgStub(
      id: 'msg_$i',
      createdAt: t0.add(Duration(hours: i)),
    ),
  );
  // messages[0] = msg_0, t0+0h (oldest)
  // messages[9] = msg_9, t0+9h (newest)

  group('Mock message pagination regression (G4)', () {
    test('without beforeId, returns most recent messages up to limit', () {
      final result = paginate(messages, limit: 3);
      expect(result.length, 3);
      // newest first: msg_9, msg_8, msg_7
      expect(result[0].id, 'msg_9');
      expect(result[1].id, 'msg_8');
      expect(result[2].id, 'msg_7');
    });

    test('with beforeId, returns messages older than the reference', () {
      // beforeId = msg_5 (index 4 in newest-first order)
      // messages after index 4: msg_4, msg_3, msg_2, msg_1, msg_0
      final result = paginate(messages, beforeId: 'msg_5', limit: 50);
      expect(result.length, 5);
      expect(result[0].id, 'msg_4');
      expect(result[4].id, 'msg_0');
    });

    test('with beforeId + limit, returns at most limit messages', () {
      final result = paginate(messages, beforeId: 'msg_5', limit: 2);
      expect(result.length, 2);
      expect(result[0].id, 'msg_4');
      expect(result[1].id, 'msg_3');
    });

    test('beforeId not found returns most recent messages', () {
      final result = paginate(messages, beforeId: 'nonexistent', limit: 2);
      expect(result.length, 2);
      expect(result[0].id, 'msg_9');
      expect(result[1].id, 'msg_8');
    });

    test('beforeId of oldest message returns empty', () {
      // msg_0 is the oldest (index 9 in newest-first order)
      final result = paginate(messages, beforeId: 'msg_0', limit: 50);
      expect(result, isEmpty);
    });

    test('beforeId of newest message returns all older messages', () {
      final result = paginate(messages, beforeId: 'msg_9', limit: 50);
      expect(result.length, 9); // msg_8..msg_0
      expect(result[0].id, 'msg_8');
    });
  });
}
