import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/offline/models/vocab_word.dart';

void main() {
  test('calculateNextReview caps long intervals at 180 days', () {
    final word = VocabWord()
      ..importance = 1
      ..consecutiveCorrect = 10;

    final now = DateTime.now();
    final nextReviewAt = word.calculateNextReview(true);
    final days = nextReviewAt.difference(now).inDays;

    expect(days, inInclusiveRange(179, 180));
  });
}
