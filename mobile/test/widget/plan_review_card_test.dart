import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/presentation/widgets/plan_review_card.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  testWidgets('plan review card submits delegate toggle through meta', (
    tester,
  ) async {
    ReviewDecision? capturedDecision;
    Map<String, String>? capturedMeta;

    const review = PlanReviewResult(
      reviewId: 'review-1',
      planId: 'plan-1',
      decision: ReviewDecision.requiresConfirmation,
      confidence: 0.82,
      comments: <ReviewComment>[],
      reviewedAt: '2026-04-02T12:00:00Z',
    );

    await tester.pumpWidget(
      MaterialApp(
        locale: const Locale('zh'),
        supportedLocales: AppLocalizations.supportedLocales,
        localizationsDelegates: const <LocalizationsDelegate<dynamic>>[
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        home: Scaffold(
          body: Center(
            child: SizedBox(
              width: 420,
              child: PlanReviewCard(
                review: review,
                onDecision: (decision, {userComment, meta}) async {
                  capturedDecision = decision;
                  capturedMeta = meta;
                  return true;
                },
              ),
            ),
          ),
        ),
      ),
    );

    await tester.pump(const Duration(milliseconds: 50));

    expect(find.text('批准后自动交给 Agent 执行'), findsOneWidget);

    await tester.tap(find.byType(Switch));
    await tester.pump(const Duration(milliseconds: 50));
    await tester.tap(find.byIcon(Icons.check_rounded));
    await tester.pump(const Duration(milliseconds: 50));

    expect(capturedDecision, ReviewDecision.approved);
    expect(capturedMeta?['delegate_approved_tasks'], 'true');
    expect(capturedMeta?['execution_mode'], 'agent');
  });
}
