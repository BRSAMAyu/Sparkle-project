// A-7 regression test: the whole CompactErrorCard surface must be tappable.
//
// Field evidence (android-round1.md A-7, screenshots 45-48): after airplane
// mode recovery, tapping "Failed to load · Tap to retry" produced zero
// network requests. The GestureDetector used the default deferToChild hit
// behavior, so taps that did not land exactly on the tiny label glyphs fell
// through — the retry felt like a dead button.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/widgets/compact_error_card.dart';
import 'package:sparkle/l10n/app_localizations.dart';

Future<void> _pumpCard(WidgetTester tester, VoidCallback? onRetry) async {
  await tester.pumpWidget(
    MaterialApp(
      locale: const Locale('en'),
      supportedLocales: const [Locale('en'), Locale('zh')],
      localizationsDelegates: const [AppLocalizations.delegate],
      home: Scaffold(
        body: Align(
          alignment: Alignment.topLeft,
          child: CompactErrorCard(onRetry: onRetry),
        ),
      ),
    ),
  );
  await tester.pump();
}

void main() {
  testWidgets(
      'tapping the card padding (away from the label glyphs) fires onRetry',
      (tester) async {
    var retryCount = 0;
    await _pumpCard(tester, () => retryCount++);

    // The card content Row is min-size; its padded area is much wider than
    // the glyphs. Tap near the right edge of the card — the spot a user
    // naturally aims for on a full-width error card.
    final cardRect = tester.getRect(find.byType(CompactErrorCard));
    expect(
      cardRect.width,
      greaterThan(0),
      reason: 'the card must be laid out before hit-testing',
    );
    await tester.tapAt(
      Offset(cardRect.right - 2, cardRect.center.dy),

    );
    await tester.pump();

    expect(
      retryCount,
      1,
      reason:
          'A tap on the card surface must trigger the retry callback; '
          'retryCount stayed 0, meaning taps on the padding fall through '
          'again (A-7 dead-button regression)',
    );
  });

  testWidgets('tapping the label itself fires onRetry', (tester) async {
    var retryCount = 0;
    await _pumpCard(tester, () => retryCount++);

    await tester.tap(find.text('Tap to retry'), warnIfMissed: false);
    await tester.pump();

    expect(retryCount, 1);
  });

  testWidgets('card without onRetry is inert (no crash on tap)', (tester) async {
    await _pumpCard(tester, null);

    final cardRect = tester.getRect(find.byType(CompactErrorCard));
    await tester.tapAt(
      Offset(cardRect.right - 2, cardRect.center.dy),

    );
    await tester.pump();

    expect(find.byType(CompactErrorCard), findsOneWidget);
  });
}
