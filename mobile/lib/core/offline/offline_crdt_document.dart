import 'dart:convert';
import 'dart:math';

import 'package:crypto/crypto.dart';

const String offlineCrdtProtocol = 'sparkle-crdt-v1';

class OfflineCrdtOperation {
  OfflineCrdtOperation({
    required this.opId,
    required this.actorId,
    required this.objectType,
    required this.objectId,
    required this.opType,
    required this.lamport,
    required this.createdAt,
    required this.value,
  });

  factory OfflineCrdtOperation.fromJson(Map<String, dynamic> json) =>
      OfflineCrdtOperation(
        opId: json['opId']?.toString() ?? '',
        actorId: json['actorId']?.toString() ?? '',
        objectType: json['objectType']?.toString() ?? '',
        objectId: json['objectId']?.toString() ?? '',
        opType: json['opType']?.toString() ?? '',
        lamport: _asInt(json['lamport']),
        createdAt: DateTime.tryParse(json['createdAt']?.toString() ?? '') ??
            DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
        value: (json['value'] as Map?)?.cast<String, dynamic>() ??
            const <String, dynamic>{},
      );

  final String opId;
  final String actorId;
  final String objectType;
  final String objectId;
  final String opType;
  final int lamport;
  final DateTime createdAt;
  final Map<String, dynamic> value;

  Map<String, dynamic> toJson() => {
        'opId': opId,
        'actorId': actorId,
        'objectType': objectType,
        'objectId': objectId,
        'opType': opType,
        'lamport': lamport,
        'createdAt': createdAt.toUtc().toIso8601String(),
        'value': value,
      };
}

class OfflineCrdtDocument {
  OfflineCrdtDocument._({
    required Map<String, OfflineCrdtOperation> operations,
    required Map<String, int> vectorClock,
  })  : _operations = operations,
        _vectorClock = vectorClock;

  factory OfflineCrdtDocument.empty() => OfflineCrdtDocument._(
        operations: <String, OfflineCrdtOperation>{},
        vectorClock: <String, int>{},
      );

  factory OfflineCrdtDocument.fromBytes(List<int> bytes) {
    final decoded = jsonDecode(utf8.decode(bytes));
    if (decoded is! Map) return OfflineCrdtDocument.empty();
    return OfflineCrdtDocument.fromJson(decoded.cast<String, dynamic>());
  }

  factory OfflineCrdtDocument.fromJson(Map<String, dynamic> json) {
    if (json['protocol'] != offlineCrdtProtocol) {
      return OfflineCrdtDocument.empty();
    }
    final operations = <String, OfflineCrdtOperation>{};
    final rawOperations = json['operations'];
    if (rawOperations is Iterable) {
      for (final raw in rawOperations) {
        if (raw is! Map) continue;
        final operation =
            OfflineCrdtOperation.fromJson(raw.cast<String, dynamic>());
        if (operation.opId.isNotEmpty) {
          operations[operation.opId] = operation;
        }
      }
    }

    return OfflineCrdtDocument._(
      operations: operations,
      vectorClock: _readVectorClock(json['vectorClock']),
    ).._rebuildVectorClock();
  }

  final Map<String, OfflineCrdtOperation> _operations;
  final Map<String, int> _vectorClock;

  List<OfflineCrdtOperation> get operations {
    final values = _operations.values.toList()..sort(_compareOperations);
    return List.unmodifiable(values);
  }

  Map<String, int> get vectorClock => Map.unmodifiable(_vectorClock);

  int nextLamport(String actorId) => (_vectorClock[actorId] ?? 0) + 1;

  bool apply(OfflineCrdtOperation operation) {
    if (operation.opId.isEmpty || _operations.containsKey(operation.opId)) {
      return false;
    }
    _operations[operation.opId] = operation;
    _vectorClock.update(
      operation.actorId,
      (current) => max(current, operation.lamport),
      ifAbsent: () => operation.lamport,
    );
    return true;
  }

  int applyAll(Iterable<OfflineCrdtOperation> operations) {
    var applied = 0;
    for (final operation in operations) {
      if (apply(operation)) applied++;
    }
    return applied;
  }

  OfflineCrdtDocument merged(OfflineCrdtDocument other) {
    final merged = OfflineCrdtDocument.empty()
      ..applyAll(operations)
      ..applyAll(other.operations);
    return merged;
  }

  int knowledgeMastery(String nodeId, {int initial = 0}) {
    final total = operations
        .where(
          (operation) =>
              operation.objectType == 'knowledge_mastery' &&
              operation.objectId == nodeId &&
              operation.opType == 'mastery_delta',
        )
        .fold<int>(
          initial,
          (sum, operation) => sum + _asInt(operation.value['delta']),
        );
    return total.clamp(0, 100);
  }

  Map<String, dynamic> taskState(String taskId) {
    final taskOperations = operations
        .where(
          (operation) =>
              operation.objectType == 'task_state' &&
              operation.objectId == taskId,
        )
        .toList();
    if (taskOperations.isEmpty) return const <String, dynamic>{};

    String? status;
    var statusRank = -1;
    final fields = <String, dynamic>{};
    for (final operation in taskOperations) {
      if (operation.opType == 'task_status') {
        final candidate = operation.value['status']?.toString();
        final candidateRank = _taskStatusRank(candidate);
        if (candidate != null && candidateRank > statusRank) {
          status = candidate;
          statusRank = candidateRank;
        }
      }
      if (operation.opType == 'task_field') {
        final key = operation.value['key']?.toString();
        if (key != null && key.isNotEmpty) {
          fields[key] = operation.value['value'];
        }
      }
    }

    return <String, dynamic>{
      if (status != null) 'status': status,
      ...fields,
    };
  }

  List<Map<String, dynamic>> chatMessages(String sessionId) {
    final tombstones = operations
        .where(
          (operation) =>
              operation.objectType == 'chat_message' &&
              operation.opType == 'chat_delete' &&
              operation.value['sessionId'] == sessionId,
        )
        .map((operation) => operation.objectId)
        .toSet();

    final messages = operations
        .where(
          (operation) =>
              operation.objectType == 'chat_message' &&
              operation.opType == 'chat_add' &&
              operation.value['sessionId'] == sessionId &&
              !tombstones.contains(operation.objectId),
        )
        .map(
          (operation) => <String, dynamic>{
            'messageId': operation.objectId,
            ...operation.value,
            'opId': operation.opId,
          },
        )
        .toList()
      ..sort((a, b) {
        final aTime = a['createdAt']?.toString() ?? '';
        final bTime = b['createdAt']?.toString() ?? '';
        final timeCompare = aTime.compareTo(bTime);
        if (timeCompare != 0) return timeCompare;
        return (a['opId'] as String).compareTo(b['opId'] as String);
      });
    return List.unmodifiable(messages);
  }

  Map<String, dynamic> toJson() => {
        'protocol': offlineCrdtProtocol,
        'vectorClock': vectorClock,
        'operations':
            operations.map((operation) => operation.toJson()).toList(),
        'hash': hash,
      };

  List<int> toBytes() => utf8.encode(jsonEncode(toJson()));

  String get hash {
    final withoutHash = {
      'protocol': offlineCrdtProtocol,
      'vectorClock': vectorClock,
      'operations': operations.map((operation) => operation.toJson()).toList(),
    };
    return sha256.convert(utf8.encode(jsonEncode(withoutHash))).toString();
  }

  void _rebuildVectorClock() {
    _vectorClock.clear();
    for (final operation in _operations.values) {
      _vectorClock.update(
        operation.actorId,
        (current) => max(current, operation.lamport),
        ifAbsent: () => operation.lamport,
      );
    }
  }
}

OfflineCrdtOperation makeKnowledgeMasteryDelta({
  required String opId,
  required String actorId,
  required String nodeId,
  required int delta,
  required int lamport,
  required DateTime createdAt,
}) =>
    OfflineCrdtOperation(
      opId: opId,
      actorId: actorId,
      objectType: 'knowledge_mastery',
      objectId: nodeId,
      opType: 'mastery_delta',
      lamport: lamport,
      createdAt: createdAt,
      value: {'delta': delta},
    );

OfflineCrdtOperation makeTaskStatusOperation({
  required String opId,
  required String actorId,
  required String taskId,
  required String status,
  required int lamport,
  required DateTime createdAt,
  Map<String, dynamic> metadata = const <String, dynamic>{},
}) =>
    OfflineCrdtOperation(
      opId: opId,
      actorId: actorId,
      objectType: 'task_state',
      objectId: taskId,
      opType: 'task_status',
      lamport: lamport,
      createdAt: createdAt,
      value: {'status': status, if (metadata.isNotEmpty) 'metadata': metadata},
    );

OfflineCrdtOperation makeChatAddOperation({
  required String opId,
  required String actorId,
  required String sessionId,
  required String messageId,
  required String content,
  required String role,
  required int lamport,
  required DateTime createdAt,
  Map<String, dynamic> metadata = const <String, dynamic>{},
}) =>
    OfflineCrdtOperation(
      opId: opId,
      actorId: actorId,
      objectType: 'chat_message',
      objectId: messageId,
      opType: 'chat_add',
      lamport: lamport,
      createdAt: createdAt,
      value: {
        'sessionId': sessionId,
        'content': content,
        'role': role,
        'createdAt': createdAt.toUtc().toIso8601String(),
        if (metadata.isNotEmpty) 'metadata': metadata,
      },
    );

List<OfflineCrdtOperation> operationsFromPayload(Map<String, dynamic> payload) {
  final rawOperations = payload['operations'];
  if (rawOperations is! Iterable) return const <OfflineCrdtOperation>[];
  return rawOperations
      .whereType<Map<dynamic, dynamic>>()
      .map((raw) => OfflineCrdtOperation.fromJson(raw.cast<String, dynamic>()))
      .where((operation) => operation.opId.isNotEmpty)
      .toList(growable: false);
}

Map<String, dynamic> operationsPayload({
  required String galaxyId,
  required String actorId,
  required Iterable<OfflineCrdtOperation> operations,
  required OfflineCrdtDocument document,
}) =>
    {
      'protocol': offlineCrdtProtocol,
      'galaxyId': galaxyId,
      'actorId': actorId,
      'operations': operations.map((operation) => operation.toJson()).toList(),
      'vectorClock': document.vectorClock,
      'snapshotHash': document.hash,
    };

int _compareOperations(OfflineCrdtOperation a, OfflineCrdtOperation b) {
  final lamportCompare = a.lamport.compareTo(b.lamport);
  if (lamportCompare != 0) return lamportCompare;
  final actorCompare = a.actorId.compareTo(b.actorId);
  if (actorCompare != 0) return actorCompare;
  return a.opId.compareTo(b.opId);
}

Map<String, int> _readVectorClock(dynamic raw) {
  if (raw is! Map) return <String, int>{};
  return raw.map(
    (key, value) => MapEntry(key.toString(), _asInt(value)),
  );
}

int _asInt(dynamic value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  return int.tryParse(value?.toString() ?? '') ?? 0;
}

int _taskStatusRank(String? status) {
  switch (status) {
    case 'pending':
    case 'todo':
      return 0;
    case 'in_progress':
    case 'active':
      return 1;
    case 'paused':
      return 2;
    case 'blocked':
      return 3;
    case 'failed':
      return 4;
    case 'completed':
    case 'done':
      return 5;
    default:
      return -1;
  }
}
