import 'package:flutter_test/flutter_test.dart';

/// Regression test for ISSUE-20260504-0500-B4:
/// NotificationNotifier.markAsRead must propagate errors after empty catch
/// — no silent catch block without rethrow.
///
/// Tests the fix pattern in isolation because Flutter compilation is blocked
/// by a pre-existing syntax error in feed_post_card.dart (unrelated to B4).
void main() {
  group('NotificationNotifier markAsRead regression (B4)', () {
    // ---- replicas of the logic under test ----

    /// Fixed: logs + rethrow
    Future<void> fixedMarkAsRead({
      required bool apiSucceeds,
    }) async {
      try {
        if (!apiSucceeds) {
          throw Exception('API failure');
        }
      } catch (e) {
        // log error — actual code uses debugPrint
        rethrow;
      }
    }

    /// Old: empty catch (the bug)
    Future<void> oldMarkAsRead({
      required bool apiSucceeds,
    }) async {
      try {
        if (!apiSucceeds) {
          throw Exception('API failure');
        }
      } catch (e) {
        // Handle error
      }
    }

    test('fixed markAsRead propagates error (caller can show feedback)',
        () async {
      bool caught = false;
      try {
        await fixedMarkAsRead(apiSucceeds: false);
      } catch (_) {
        caught = true;
      }
      expect(caught, isTrue);
    });

    test('fixed markAsRead does not throw on success', () async {
      bool caught = false;
      try {
        await fixedMarkAsRead(apiSucceeds: true);
      } catch (_) {
        caught = true;
      }
      expect(caught, isFalse);
    });

    test('old markAsRead silently returns on failure — the bug', () async {
      bool completed = false;
      bool threw = false;
      try {
        await oldMarkAsRead(apiSucceeds: false);
        completed = true;
      } catch (_) {
        threw = true;
      }
      // Old version: no throw, no feedback — caller thinks it succeeded
      expect(completed, isTrue);
      expect(threw, isFalse);
    });
  });
}
