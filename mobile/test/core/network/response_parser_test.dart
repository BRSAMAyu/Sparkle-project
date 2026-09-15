import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/response_parser.dart';

void main() {
  group('ApiResponseParser.unwrapMap', () {
    test('returns direct payload map when success key is present', () {
      final payload = <String, dynamic>{
        'success': true,
        'resource_type': 'plan',
        'new_resource_id': 'plan-123',
      };

      final result = ApiResponseParser.unwrapMap(payload, action: 'adopt');

      expect(result, payload);
      expect(result['resource_type'], 'plan');
    });

    test('returns nested data map when present', () {
      final payload = <String, dynamic>{
        'success': true,
        'data': <String, dynamic>{'message': 'ok'},
      };

      final result = ApiResponseParser.unwrapMap(payload, action: 'nudge');

      expect(result, <String, dynamic>{'message': 'ok'});
    });
  });
}
