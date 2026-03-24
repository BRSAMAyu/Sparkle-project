import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/utils/grapheme_utils.dart';

void main() {
  group('GraphemeUtils', () {
    group('graphemeCount', () {
      test('counts simple ASCII characters correctly', () {
        expect(GraphemeUtils.graphemeCount('Hello'), 5);
        expect(GraphemeUtils.graphemeCount(''), 0);
        expect(GraphemeUtils.graphemeCount('A'), 1);
      });

      test('counts Chinese characters correctly', () {
        expect(GraphemeUtils.graphemeCount('你好世界'), 4);
        expect(GraphemeUtils.graphemeCount('中文测试'), 4);
      });

      test('counts simple emoji correctly', () {
        // Simple emoji like 👋 is 1 grapheme cluster
        expect(GraphemeUtils.graphemeCount('👋'), 1);
        expect(GraphemeUtils.graphemeCount('🎉'), 1);
        expect(GraphemeUtils.graphemeCount('❤️'), 1);
      });

      test('counts complex emoji (ZWJ sequences) correctly', () {
        // Family emoji: 👨‍👩‍👧‍👦 is 1 grapheme cluster (7 code points, 11 UTF-16 code units)
        expect(GraphemeUtils.graphemeCount('👨‍👩‍👧‍👦'), 1);
        // Flag emoji: 🏴󠁧󠁢󠁳󠁣󠁴󠁿 is 1 grapheme cluster
        expect(GraphemeUtils.graphemeCount('🏴󠁧󠁢󠁳󠁣󠁴󠁿'), 1);
      });

      test('counts skin tone modified emoji correctly', () {
        // Thumbs up with light skin tone
        expect(GraphemeUtils.graphemeCount('👍🏻'), 1);
        // Thumbs up with dark skin tone
        expect(GraphemeUtils.graphemeCount('👍🏿'), 1);
        // Multiple skin tone emoji
        expect(GraphemeUtils.graphemeCount('👍🏻👍🏿'), 2);
      });

      test('counts mixed content correctly', () {
        // Hello + space + 👋 = 7 graphemes
        expect(GraphemeUtils.graphemeCount('Hello 👋'), 7);
        // 你好 + space + 👋 + space + 世界 + space + 🌍 = 9 graphemes
        expect(GraphemeUtils.graphemeCount('你好 👋 世界 🌍'), 9);
        // Test + space + 👨‍👩‍👧‍👦 + space + Done = 11 graphemes (but wait, let's verify)
        // Actually: T e s t (4) + space (1) + family emoji (1) + space (1) + D o n e (4) = 11
        expect(GraphemeUtils.graphemeCount('Test 👨‍👩‍👧‍👦 Done'), 11);
      });
    });

    group('takeGraphemes', () {
      test('takes simple ASCII characters correctly', () {
        expect(GraphemeUtils.takeGraphemes('Hello World', 5), 'Hello');
        expect(GraphemeUtils.takeGraphemes('Hello', 10), 'Hello');
        expect(GraphemeUtils.takeGraphemes('Hello', 0), '');
      });

      test('takes Chinese characters correctly', () {
        expect(GraphemeUtils.takeGraphemes('你好世界', 2), '你好');
        expect(GraphemeUtils.takeGraphemes('中文测试', 3), '中文测');
      });

      test('takes simple emoji without splitting', () {
        // 'Hello 👋' has 7 graphemes: H-e-l-l-o- -👋
        // Taking 7 should give the whole string
        expect(GraphemeUtils.takeGraphemes('Hello 👋', 7), 'Hello 👋');
        expect(GraphemeUtils.takeGraphemes('👋 World', 1), '👋');
        expect(GraphemeUtils.takeGraphemes('🎉🎊🎈', 2), '🎉🎊');
      });

      test('takes complex emoji without splitting', () {
        // Family emoji should not be split
        expect(GraphemeUtils.takeGraphemes('👨‍👩‍👧‍👦 World', 1), '👨‍👩‍👧‍👦');
        // 'Hi 👨‍👩‍👧‍👦!' has 5 graphemes: H-i- -👨‍👩‍👧‍👦-!
        // Taking 4 should give 'Hi 👨‍👩‍👧‍👦'
        expect(GraphemeUtils.takeGraphemes('Hi 👨‍👩‍👧‍👦!', 4), 'Hi 👨‍👩‍👧‍👦');
      });

      test('takes skin tone modified emoji correctly', () {
        expect(GraphemeUtils.takeGraphemes('👍🏻👍🏿', 1), '👍🏻');
        expect(GraphemeUtils.takeGraphemes('Test 👍🏻 done', 6), 'Test 👍🏻');
      });

      test('handles edge cases', () {
        expect(GraphemeUtils.takeGraphemes('', 5), '');
        expect(GraphemeUtils.takeGraphemes('Test', -1), '');
        expect(GraphemeUtils.takeGraphemes('Test', 0), '');
      });
    });

    group('sliceGraphemes', () {
      test('slices simple text correctly', () {
        expect(GraphemeUtils.sliceGraphemes('Hello World', 0, 5), 'Hello');
        expect(GraphemeUtils.sliceGraphemes('Hello World', 6), 'World');
        expect(GraphemeUtils.sliceGraphemes('Hello World', 6, 11), 'World');
      });

      test('slices with emoji correctly', () {
        expect(GraphemeUtils.sliceGraphemes('Hello 👋 World', 0, 7), 'Hello 👋');
        expect(GraphemeUtils.sliceGraphemes('Hello 👋 World', 7), ' World');
      });

      test('handles out of bounds gracefully', () {
        expect(GraphemeUtils.sliceGraphemes('Hi', 10), '');
        expect(GraphemeUtils.sliceGraphemes('Hi', 0, 10), 'Hi');
        expect(GraphemeUtils.sliceGraphemes('Hi', -1, 5), 'Hi');
      });
    });

    group('graphemeAt', () {
      test('returns correct grapheme at index', () {
        expect(GraphemeUtils.graphemeAt('Hello', 0), 'H');
        expect(GraphemeUtils.graphemeAt('Hello', 4), 'o');
      });

      test('returns emoji as single grapheme', () {
        expect(GraphemeUtils.graphemeAt('👋 World', 0), '👋');
        // 'Hi 👨‍👩‍👧‍👦!' - index 2 is space, index 3 is family emoji
        expect(GraphemeUtils.graphemeAt('Hi 👨‍👩‍👧‍👦!', 3), '👨‍👩‍👧‍👦');
      });

      test('returns null for out of bounds', () {
        expect(GraphemeUtils.graphemeAt('Hi', 10), null);
        expect(GraphemeUtils.graphemeAt('Hi', -1), null);
      });
    });

    group('truncate', () {
      test('truncates long text with ellipsis', () {
        expect(GraphemeUtils.truncate('Hello World', 5), 'Hello…');
        expect(GraphemeUtils.truncate('Hello World', 5, ellipsis: '...'), 'Hello...');
      });

      test('does not truncate short text', () {
        expect(GraphemeUtils.truncate('Hi', 5), 'Hi');
        expect(GraphemeUtils.truncate('', 5), '');
      });

      test('truncates with emoji correctly', () {
        expect(GraphemeUtils.truncate('Hello 👋 World', 7), 'Hello 👋…');
        // Complex emoji should remain intact
        // '👨‍👩‍👧‍👦 Family' has 8 graphemes: family emoji + space + F-a-m-i-l-y
        // Taking 2 should give family emoji + space, then ellipsis
        expect(GraphemeUtils.truncate('👨‍👩‍👧‍👦 Family', 2), '👨‍👩‍👧‍👦 …');
      });
    });

    group('GraphemeStringExtension', () {
      test('provides convenient extension methods', () {
        // 'Hello 👋' has 7 graphemes
        expect('Hello 👋'.graphemeCount, 7);
        // Taking 7 gives the whole string
        expect('Hello 👋'.takeGraphemes(7), 'Hello 👋');
        expect('Hello 👋'.sliceGraphemes(0, 7), 'Hello 👋');
        expect('Hello 👋 World'.truncateGraphemes(7), 'Hello 👋…');
      });
    });
  });
}
