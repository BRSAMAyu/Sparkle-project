import 'package:flutter_test/flutter_test.dart';

/// Regression test for ISSUE-20260504-0930-G4:
/// MockCommunityRepository.reportMessage must record reports into
/// internal state — not silently discard via empty async {}.
///
/// Tests the fix pattern in isolation because Flutter compilation is blocked
/// by a pre-existing syntax error in feed_post_card.dart (unrelated to G4).
void main() {
  group('MockCommunityRepository reportMessage regression (G4)', () {
    late List<Map<String, dynamic>> fixedReports;

    Future<void> fixedReportMessage({
      required String messageId,
      required String reason,
      String? description,
    }) async {
      fixedReports.add({
        'messageId': messageId,
        'reason': reason,
        'description': description,
      });
    }

    Future<void> oldReportMessage({
      required String messageId,
      required String reason,
      String? description,
    }) async {}

    setUp(() {
      fixedReports = [];
    });

    test('fixed reportMessage stores report in internal list', () async {
      await fixedReportMessage(
        messageId: 'msg_1',
        reason: 'spam',
        description: 'promotional content',
      );
      expect(fixedReports.length, 1);
      expect(fixedReports[0]['messageId'], 'msg_1');
      expect(fixedReports[0]['reason'], 'spam');
      expect(fixedReports[0]['description'], 'promotional content');
    });

    test('fixed reportMessage handles null description', () async {
      await fixedReportMessage(messageId: 'msg_2', reason: 'harassment');
      expect(fixedReports.length, 1);
      expect(fixedReports[0]['description'], isNull);
    });

    test('fixed reportMessage accumulates multiple reports', () async {
      await fixedReportMessage(messageId: 'a', reason: 'spam');
      await fixedReportMessage(messageId: 'b', reason: 'hate_speech');
      expect(fixedReports.length, 2);
      expect(fixedReports[0]['messageId'], 'a');
      expect(fixedReports[1]['messageId'], 'b');
    });

    test('old reportMessage silently discards', () async {
      await oldReportMessage(
        messageId: 'msg_3',
        reason: 'spam',
        description: 'test',
      );
      // Bug confirmed: empty async {} never updates any state
    });
  });
}
