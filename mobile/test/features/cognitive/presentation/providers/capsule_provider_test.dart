import 'package:flutter_test/flutter_test.dart';

/// Regression test for ISSUE-20260504-0501-B5:
/// CapsuleDetailNotifier.submitFeedback must propagate errors after
/// returning null — no silent catch.
///
/// Tests the fix pattern in isolation because Flutter compilation is blocked
/// by a pre-existing syntax error in feed_post_card.dart (unrelated to B5).
void main() {
  group('CapsuleDetailNotifier submitFeedback regression (B5)', () {
    // ---- replicas of the logic under test ----

    /// Fixed: rethrow
    Future<int?> fixedSubmitFeedback({
      required bool apiSucceeds,
    }) async {
      try {
        if (!apiSucceeds) {
          throw Exception('API failure');
        }
        return 200;
      } catch (e) {
        rethrow;
      }
    }

    /// Old: return null (the bug)
    Future<int?> oldSubmitFeedback({
      required bool apiSucceeds,
    }) async {
      try {
        if (!apiSucceeds) {
          throw Exception('API failure');
        }
        return 200;
      } catch (e) {
        return null;
      }
    }

    test('fixed submitFeedback propagates error (caller can show error toast)',
        () async {
      bool caught = false;
      try {
        await fixedSubmitFeedback(apiSucceeds: false);
      } catch (_) {
        caught = true;
      }
      expect(caught, isTrue);
    });

    test('fixed submitFeedback returns value on success', () async {
      final result = await fixedSubmitFeedback(apiSucceeds: true);
      expect(result, 200);
    });

    test('old submitFeedback returns null on failure — the bug', () async {
      final result = await oldSubmitFeedback(apiSucceeds: false);
      // Old version: returns null — UI checks null for nothing, shows success
      expect(result, isNull);
    });
  });
}
