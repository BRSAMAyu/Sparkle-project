import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/presentation/widgets/shared_resource_card.dart';
import '../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);

  SharedResourceInfo makeResource({
    double? qualityScore,
    bool? qualityHidden,
    int? adoptionCount,
    double? avgRating,
    String? title,
    String? summary,
    int feedbackCount = 0,
    int unadoptedFeedbackCount = 0,
    bool isOwn = false,
  }) =>
      SharedResourceInfo(
        id: 'test-id',
        resourceType: SharedResourceType.plan,
        createdAt: DateTime.utc(2026, 5),
        qualityScore: qualityScore,
        qualityHidden: qualityHidden,
        adoptionCount: adoptionCount,
        avgRating: avgRating,
        resourceTitle: title ?? 'Test Resource',
        resourceSummary: summary,
        feedbackCount: feedbackCount,
        unadoptedFeedbackCount: unadoptedFeedbackCount,
        isOwn: isOwn,
      );

  testWidgets('SharedResourceCard renders gold badge for score >= 0.8',
      (tester) async {
    final resource = makeResource(qualityScore: 0.9);

    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: SharedResourceCard(resource: resource),
        ),
      ),
    );

    expect(find.text('精选'), findsOneWidget);
    expect(find.text('Test Resource'), findsOneWidget);
  });

  testWidgets('SharedResourceCard renders silver badge for score 0.6-0.8',
      (tester) async {
    final resource = makeResource(qualityScore: 0.7);

    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: SharedResourceCard(resource: resource),
        ),
      ),
    );

    expect(find.text('推荐'), findsOneWidget);
  });

  testWidgets('SharedResourceCard renders no badge for score 0.4-0.6',
      (tester) async {
    final resource = makeResource(qualityScore: 0.5);

    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: SharedResourceCard(resource: resource),
        ),
      ),
    );

    // Should NOT have any badge labels
    expect(find.text('精选'), findsNothing);
    expect(find.text('推荐'), findsNothing);
  });

  testWidgets('SharedResourceCard renders beginner badge for score < 0.4',
      (tester) async {
    final resource = makeResource(qualityScore: 0.2);

    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: SharedResourceCard(resource: resource),
        ),
      ),
    );

    expect(find.text('新手友好'), findsOneWidget);
  });

  testWidgets('SharedResourceCard shows adoption count in stats',
      (tester) async {
    final resource =
        makeResource(qualityScore: 0.8, adoptionCount: 5, avgRating: 4.6);

    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: SharedResourceCard(resource: resource),
        ),
      ),
    );

    expect(find.textContaining('采纳'), findsOneWidget);
    expect(find.textContaining('平均评分 4.6'), findsOneWidget);
  });

  testWidgets('SharedResourceCard onTap callback fires', (tester) async {
    var tapped = false;
    final resource = makeResource();

    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: SharedResourceCard(
            resource: resource,
            onTap: () => tapped = true,
          ),
        ),
      ),
    );

    await tester.tap(find.byType(SharedResourceCard));
    expect(tapped, isTrue);
  });

  group('SharedResourceCard S-04 feedback → evidence surface', () {
    testWidgets('shows feedback count chip and fires feedback callback',
        (tester) async {
      final resource = makeResource(feedbackCount: 3);
      var feedbackTapped = false;

      await tester.pumpWidget(
        testMaterialApp(
          home: Scaffold(
            body: SharedResourceCard(
              resource: resource,
              onFeedback: () => feedbackTapped = true,
            ),
          ),
        ),
      );

      expect(find.text('3 条反馈'), findsOneWidget);
      await tester
          .tap(find.byKey(const ValueKey('shared-resource-feedback-button')));
      expect(feedbackTapped, isTrue);
    });

    testWidgets('own resource with unadopted feedback offers adopt entry',
        (tester) async {
      final resource =
          makeResource(feedbackCount: 2, unadoptedFeedbackCount: 2, isOwn: true);

      await tester.pumpWidget(
        testMaterialApp(
          home: Scaffold(
            body: SharedResourceCard(
              resource: resource,
              onAdoptFeedback: () {},
            ),
          ),
        ),
      );

      expect(
        find.byKey(const ValueKey('shared-resource-adopt-evidence')),
        findsOneWidget,
      );
    });

    testWidgets('hides adopt entry when hub withholds the callback',
        (tester) async {
      // 卡片契约：入口显隐由调用方按「未采纳反馈 > 0」决定，卡片只管回传。
      final resource = makeResource(isOwn: true);

      await tester.pumpWidget(
        testMaterialApp(
          home: Scaffold(
            body: SharedResourceCard(
              resource: resource,
            ),
          ),
        ),
      );

      expect(
        find.byKey(const ValueKey('shared-resource-adopt-evidence')),
        findsNothing,
      );
    });
  });
}
