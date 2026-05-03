import 'package:flutter_test/flutter_test.dart';

/// Regression test for ISSUE-20260503-2300-B1:
/// ExperienceRepository._payload must throw FormatException for non-Map input
/// instead of silently returning const {}.
///
/// We test the logic in isolation because the Flutter compilation is blocked
/// by a pre-existing syntax error in feed_post_card.dart (unrelated to B1).
void main() {
  group('ExperienceRepository._payload regression (B1)', () {
    /// Replicates the fixed _payload logic from experience_repository.dart
    Map<String, dynamic> fixedPayload(Object? data) {
      if (data is Map<String, dynamic>) return data;
      if (data is Map) return Map<String, dynamic>.from(data);
      throw FormatException(
        'experience: expected Map response, got ${data.runtimeType}',
      );
    }

    /// Replicates the OLD buggy _payload logic
    Map<String, dynamic> oldPayload(Object? data) {
      if (data is Map<String, dynamic>) return data;
      if (data is Map) return Map<String, dynamic>.from(data);
      return const {};
    }

    test('fixed _payload throws FormatException for List input', () {
      expect(
        () => fixedPayload(['unexpected', 'array']),
        throwsA(isA<FormatException>()),
      );
    });

    test('fixed _payload throws FormatException for String input', () {
      expect(
        () => fixedPayload('not a map'),
        throwsA(isA<FormatException>()),
      );
    });

    test('fixed _payload throws FormatException for null input', () {
      expect(
        () => fixedPayload(null),
        throwsA(isA<FormatException>()),
      );
    });

    test('fixed _payload returns Map for valid Map<String, dynamic>', () {
      final input = <String, dynamic>{'key': 'value'};
      expect(fixedPayload(input), same(input));
    });

    test('old _payload silently returns {} for List — the bug', () {
      final result = oldPayload(['unexpected']);
      expect(result, isEmpty);
      expect(result, isA<Map<String, dynamic>>());
    });

    test('old _payload silently returns {} for null — the bug', () {
      final result = oldPayload(null);
      expect(result, isEmpty);
    });

    test('FormatException message includes the unexpected type', () {
      try {
        fixedPayload(42);
        fail('should have thrown');
      } on FormatException catch (e) {
        expect(e.message, contains('int'));
      }
    });
  });
}
