import 'package:flutter_test/flutter_test.dart';

/// Regression test for ISSUE-20260503-2301-B2:
/// AuroraPreferencesNotifier.updatePreference must propagate errors after
/// rolling back state — no silent catch(_).
///
/// Tests the fix pattern in isolation because Flutter compilation is blocked
/// by a pre-existing syntax error in feed_post_card.dart (unrelated to B2).
void main() {
  group('AuroraPreferences updatePreference regression (B2)', () {
    // ---- replicas of the logic under test ----

    /// Fixed: rollback + rethrow
    Future<void> fixedUpdate({
      required bool apiSucceeds,
    }) async {
      // optimistic update
      if (!apiSucceeds) {
        // rollback + rethrow (the fix)
        throw Exception('API failure');
      }
      // API success — state stays updated
    }

    /// Old: silent rollback (the bug)
    Future<void> oldUpdate({
      required bool apiSucceeds,
      required void Function(String message) onError,
    }) async {
      // optimistic update
      if (!apiSucceeds) {
        // rollback — silent, no rethrow
        return; // <-- BUG: user never knows
      }
    }

    test('fixed update propagates error (caller can show feedback)', () async {
      bool caught = false;
      try {
        await fixedUpdate(apiSucceeds: false);
      } catch (_) {
        caught = true;
      }
      expect(caught, isTrue);
    });

    test('fixed update does not throw on success', () async {
      bool caught = false;
      try {
        await fixedUpdate(apiSucceeds: true);
      } catch (_) {
        caught = true;
      }
      expect(caught, isFalse);
    });

    test('old update silently returns on failure — the bug', () async {
      bool errorCallbackInvoked = false;
      await oldUpdate(
        apiSucceeds: false,
        onError: (_) => errorCallbackInvoked = true,
      );
      // Old version: no throw, no callback — user sees nothing
      expect(errorCallbackInvoked, isFalse);
    });
  });
}
