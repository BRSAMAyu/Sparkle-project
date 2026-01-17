import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/utils/hash_utils.dart';

void main() {
  group('HashUtils - Translation Fingerprint', () {
    test('Should generate stable SHA-256 hash for identical input', () {
      const text = 'hello';
      const contextBefore = 'start';
      const contextAfter = 'end';
      const pageNo = 1;

      final hash1 = HashUtils.generateTranslationFingerprint(
        text: text,
        contextBefore: contextBefore,
        contextAfter: contextAfter,
        pageNo: pageNo,
      );

      final hash2 = HashUtils.generateTranslationFingerprint(
        text: text,
        contextBefore: contextBefore,
        contextAfter: contextAfter,
        pageNo: pageNo,
      );

      expect(hash1, equals(hash2));
      expect(hash1.length, equals(64)); // SHA-256 hex string length
    });

    test('Should generate different hash for different inputs', () {
      final hash1 = HashUtils.generateTranslationFingerprint(text: 'word1');
      final hash2 = HashUtils.generateTranslationFingerprint(text: 'word2');

      expect(hash1, isNot(equals(hash2)));
    });

    test('Should handle null contexts gracefully', () {
      final hashWithNull = HashUtils.generateTranslationFingerprint(
        text: 'hello',
        contextBefore: null,
        contextAfter: null,
        pageNo: null,
      );

      final hashWithEmpty = HashUtils.generateTranslationFingerprint(
        text: 'hello',
        contextBefore: '',
        contextAfter: '',
        pageNo: null,
      );

      expect(hashWithNull, equals(hashWithEmpty));
    });

    test('Should trim whitespace before hashing', () {
      final hash1 = HashUtils.generateTranslationFingerprint(text: 'hello');
      final hash2 = HashUtils.generateTranslationFingerprint(text: ' hello ');

      expect(hash1, equals(hash2));
    });
  });
}
