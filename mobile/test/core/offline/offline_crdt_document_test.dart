import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/offline/offline_crdt_document.dart';

void main() {
  group('OfflineCrdtDocument', () {
    test('merges concurrent knowledge mastery deltas without last-write-wins',
        () {
      final a = OfflineCrdtDocument.empty()
        ..apply(
          makeKnowledgeMasteryDelta(
            opId: 'a1',
            actorId: 'device-a',
            nodeId: 'node-1',
            delta: 12,
            lamport: 1,
            createdAt: DateTime.utc(2026),
          ),
        );
      final b = OfflineCrdtDocument.empty()
        ..apply(
          makeKnowledgeMasteryDelta(
            opId: 'b1',
            actorId: 'device-b',
            nodeId: 'node-1',
            delta: 8,
            lamport: 1,
            createdAt: DateTime.utc(2026),
          ),
        );

      final merged = a.merged(b);

      expect(merged.knowledgeMastery('node-1'), 20);
      expect(merged.operations.map((operation) => operation.opId), [
        'a1',
        'b1',
      ]);
    });

    test('uses a task-state lattice for concurrent task transitions', () {
      final document = OfflineCrdtDocument.empty()
        ..apply(
          makeTaskStatusOperation(
            opId: 'a1',
            actorId: 'device-a',
            taskId: 'task-1',
            status: 'paused',
            lamport: 1,
            createdAt: DateTime.utc(2026),
          ),
        )
        ..apply(
          makeTaskStatusOperation(
            opId: 'b1',
            actorId: 'device-b',
            taskId: 'task-1',
            status: 'completed',
            lamport: 1,
            createdAt: DateTime.utc(2026),
          ),
        );

      expect(document.taskState('task-1'), {'status': 'completed'});
    });

    test('keeps concurrent chat message appends as an ordered OR-set', () {
      final document = OfflineCrdtDocument.empty()
        ..apply(
          makeChatAddOperation(
            opId: 'b1',
            actorId: 'device-b',
            sessionId: 'session-1',
            messageId: 'message-b',
            content: 'second',
            role: 'user',
            lamport: 1,
            createdAt: DateTime.utc(2026, 1, 1, 0, 0, 2),
          ),
        )
        ..apply(
          makeChatAddOperation(
            opId: 'a1',
            actorId: 'device-a',
            sessionId: 'session-1',
            messageId: 'message-a',
            content: 'first',
            role: 'assistant',
            lamport: 1,
            createdAt: DateTime.utc(2026, 1, 1, 0, 0, 1),
          ),
        );

      final messages = document.chatMessages('session-1');

      expect(messages.map((message) => message['messageId']), [
        'message-a',
        'message-b',
      ]);
      expect(
        messages.map((message) => message['content']),
        ['first', 'second'],
      );
    });

    test('serializes operation deltas for server ACK protocol', () {
      final document = OfflineCrdtDocument.empty();
      final operation = makeKnowledgeMasteryDelta(
        opId: 'a1',
        actorId: 'device-a',
        nodeId: 'node-1',
        delta: 5,
        lamport: 1,
        createdAt: DateTime.utc(2026),
      );
      document.apply(operation);

      final payload = operationsPayload(
        galaxyId: 'default',
        actorId: 'device-a',
        operations: [operation],
        document: document,
      );

      expect(payload['protocol'], offlineCrdtProtocol);
      expect(payload['snapshotHash'], document.hash);
      expect(operationsFromPayload(payload).single.opId, 'a1');
      expect(jsonEncode(payload), isNot(contains('data')));
    });

    test('merges 1000 accumulated operations within the mobile budget', () {
      final document = OfflineCrdtDocument.empty();
      final operations = List.generate(
        1000,
        (index) => makeKnowledgeMasteryDelta(
          opId: 'op-$index',
          actorId: 'device-${index % 4}',
          nodeId: 'node-${index % 10}',
          delta: 1,
          lamport: index + 1,
          createdAt: DateTime.utc(2026, 1, 1, 0, 0, index % 60),
        ),
      );

      final stopwatch = Stopwatch()..start();
      document.applyAll(operations);
      final nodeValue = document.knowledgeMastery('node-1');
      stopwatch.stop();

      expect(document.operations.length, 1000);
      expect(nodeValue, 100);
      expect(stopwatch.elapsedMilliseconds, lessThan(200));
    });
  });
}
