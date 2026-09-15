import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';

void main() {
  group('SSEEvent', () {
    test('jsonData parses valid JSON data', () {
      final event = SSEEvent(
        event: 'message',
        data: jsonEncode({'key': 'value', 'count': 42}),
      );
      final json = event.jsonData;
      expect(json, isNotNull);
      expect(json!['key'], 'value');
      expect(json['count'], 42);
    });

    test('jsonData returns null for invalid JSON', () {
      final event = SSEEvent(
        event: 'message',
        data: 'not valid json',
      );
      expect(event.jsonData, isNull);
    });

    test('jsonData returns null for empty string', () {
      final event = SSEEvent(event: 'message', data: '');
      expect(event.jsonData, isNull);
    });

    test('toString includes event and data', () {
      final event = SSEEvent(
        id: '123',
        event: 'delta',
        data: 'hello',
      );
      final str = event.toString();
      expect(str, contains('delta'));
      expect(str, contains('hello'));
    });

    test('id is optional and can be null', () {
      final event = SSEEvent(event: 'message', data: 'test');
      expect(event.id, isNull);
      expect(event.event, 'message');
      expect(event.data, 'test');
    });

    test('jsonData handles nested objects', () {
      final event = SSEEvent(
        event: 'message',
        data: jsonEncode(<String, dynamic>{
          'nested': <String, dynamic>{'a': 1, 'b': [1, 2, 3]},
        }),
      );
      final json = event.jsonData;
      expect(json, isNotNull);
      expect(json!['nested'], isA<Map<String, dynamic>>());
    });
  });
}
