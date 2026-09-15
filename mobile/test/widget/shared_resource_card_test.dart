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
}
