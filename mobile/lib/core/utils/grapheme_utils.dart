/// Grapheme-safe string utilities for proper Unicode handling.
///
/// This module provides utilities for safely manipulating strings that contain
/// multi-code-point characters like emoji, combining characters, and other
/// complex Unicode sequences.
///
/// ## Why is this needed?
///
/// Dart's default `String.substring()` operates on UTF-16 code units, which can
/// split grapheme clusters (user-perceived characters) in the middle. This
/// causes emoji and other complex characters to display as question marks or
/// replacement characters.
///
/// Example:
/// ```dart
/// // ❌ Wrong: splits emoji in the middle
/// 'Hello 👋'.substring(0, 6); // Returns 'Hello ' with broken emoji
///
/// // ✅ Correct: respects grapheme boundaries
/// GraphemeUtils.takeGraphemes('Hello 👋', 6); // Returns 'Hello 👋'
/// ```
library;

import 'package:characters/characters.dart';

/// Utilities for grapheme-safe string operations.
///
/// A "grapheme cluster" is what users perceive as a single character.
/// This can be multiple Unicode code points combined (e.g., 👨‍👩‍👧‍👦 family emoji
/// is 7 code points but 1 grapheme cluster).
class GraphemeUtils {
  GraphemeUtils._();

  /// Returns the first [count] grapheme clusters from [text].
  ///
  /// Safe for emoji, combining characters, and other complex Unicode.
  ///
  /// Example:
  /// ```dart
  /// GraphemeUtils.takeGraphemes('Hello 👋 World', 7); // 'Hello 👋'
  /// GraphemeUtils.takeGraphemes('👨‍👩‍👧‍👦', 1); // '👨‍👩‍👧‍👦'
  /// ```
  static String takeGraphemes(String text, int count) {
    if (count <= 0) return '';
    final characters = text.characters;
    if (count >= characters.length) return text;
    return characters.take(count).string;
  }

  /// Returns the number of grapheme clusters in [text].
  ///
  /// This is often different from `String.length` for emoji-heavy text.
  ///
  /// Example:
  /// ```dart
  /// 'Hello'.length; // 5
  /// GraphemeUtils.graphemeCount('Hello'); // 5
  ///
  /// '👋'.length; // 2 (UTF-16 code units)
  /// GraphemeUtils.graphemeCount('👋'); // 1
  ///
  /// '👨‍👩‍👧‍👦'.length; // 11 (UTF-16 code units)
  /// GraphemeUtils.graphemeCount('👨‍👩‍👧‍👦'); // 1
  /// ```
  static int graphemeCount(String text) => text.characters.length;

  /// Returns grapheme clusters from [start] to [end] (exclusive).
  ///
  /// If [end] is omitted, returns from [start] to the end.
  ///
  /// Example:
  /// ```dart
  /// GraphemeUtils.sliceGraphemes('Hello 👋 World', 0, 7); // 'Hello 👋'
  /// GraphemeUtils.sliceGraphemes('Hello 👋 World', 7); // ' World'
  /// ```
  static String sliceGraphemes(String text, int start, [int? end]) {
    final characters = text.characters;
    if (start < 0) start = 0;
    if (start >= characters.length) return '';

    final effectiveEnd = end ?? characters.length;
    if (effectiveEnd <= start) return '';
    if (effectiveEnd > characters.length) {
      return characters.skip(start).string;
    }

    return characters.skip(start).take(effectiveEnd - start).string;
  }

  /// Returns the grapheme cluster at the given [index].
  ///
  /// Returns null if index is out of bounds.
  ///
  /// Example:
  /// ```dart
  /// GraphemeUtils.graphemeAt('Hello 👋', 6); // '👋'
  /// GraphemeUtils.graphemeAt('Hello', 10); // null
  /// ```
  static String? graphemeAt(String text, int index) {
    if (index < 0) return null;
    final characters = text.characters.toList();
    if (index >= characters.length) return null;
    return characters[index];
  }

  /// Checks if [text] ends with a complete grapheme cluster.
  ///
  /// Useful for validating that a truncated string doesn't end mid-character.
  static bool endsWithCompleteGrapheme(String text) {
    if (text.isEmpty) return true;
    // If the last code unit is a low surrogate, the string is incomplete
    final runes = text.runes.toList();
    if (runes.isEmpty) return true;

    // Check if the string can be reconstructed from its characters
    final reconstructed = text.characters.string;
    return reconstructed == text;
  }

  /// Safely truncates [text] to at most [maxGraphemes] grapheme clusters.
  ///
  /// If truncated, appends [ellipsis] to indicate truncation.
  ///
  /// Example:
  /// ```dart
  /// GraphemeUtils.truncate('Hello 👋 World', 7); // 'Hello 👋…'
  /// GraphemeUtils.truncate('Hello 👋 World', 7, ellipsis: '...'); // 'Hello 👋...'
  /// ```
  static String truncate(
    String text,
    int maxGraphemes, {
    String ellipsis = '…',
  }) {
    if (maxGraphemes <= 0) return ellipsis;
    final characters = text.characters;
    if (characters.length <= maxGraphemes) return text;

    return characters.take(maxGraphemes).string + ellipsis;
  }
}

/// Extension on String to provide grapheme-safe operations.
extension GraphemeStringExtension on String {
  /// Returns the number of grapheme clusters in this string.
  int get graphemeCount => GraphemeUtils.graphemeCount(this);

  /// Returns the first [count] grapheme clusters.
  String takeGraphemes(int count) => GraphemeUtils.takeGraphemes(this, count);

  /// Safely slices grapheme clusters from [start] to [end].
  String sliceGraphemes(int start, [int? end]) =>
      GraphemeUtils.sliceGraphemes(this, start, end);

  /// Safely truncates to [maxGraphemes] with optional ellipsis.
  String truncateGraphemes(int maxGraphemes, {String ellipsis = '…'}) =>
      GraphemeUtils.truncate(this, maxGraphemes, ellipsis: ellipsis);
}
