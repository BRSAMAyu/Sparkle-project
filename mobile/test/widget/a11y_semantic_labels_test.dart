import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sparkle_avatar.dart';
import 'package:sparkle/core/design/widgets/sparkle_network_image.dart';
import 'package:sparkle/shared/entities/user_model.dart';
import 'package:sparkle/features/community/data/models/community_models.dart';
import 'package:sparkle/features/community/presentation/widgets/feed_post_card.dart';

import '../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);

  group('SparkleAvatar', () {
    testWidgets('builds with semanticLabel parameter', (tester) async {
      await tester.pumpWidget(
        testMaterialApp(
          theme: AppThemes.lightTheme,
          home: const Scaffold(
            body: SparkleAvatar(
              fallbackText: 'User',
              semanticLabel: 'User avatar',
            ),
          ),
        ),
      );
      // Renders CircleAvatar without error
      expect(find.byType(CircleAvatar), findsOneWidget);
    });

    testWidgets('builds with default fallback text', (tester) async {
      await tester.pumpWidget(
        testMaterialApp(
          theme: AppThemes.lightTheme,
          home: const Scaffold(
            body: SparkleAvatar(fallbackText: 'Test'),
          ),
        ),
      );
      // Renders default avatar with fallback text initial
      expect(find.text('T'), findsOneWidget);
    });

    testWidgets('builds pending avatar with overlay', (tester) async {
      await tester.pumpWidget(
        testMaterialApp(
          theme: AppThemes.lightTheme,
          home: Scaffold(
            body: SparkleAvatar(
              fallbackText: 'Li',
              radius: 30,
              status: AvatarStatus.pending,
              semanticLabel: 'Li avatar',
            ),
          ),
        ),
      );
      // Pending avatar renders with progress indicator overlay
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });
  });

  group('SparkleNetworkImage', () {
    testWidgets('exposes semantic label when provided', (tester) async {
      await _withSemantics(tester, () async {
        await tester.pumpWidget(
          testMaterialApp(
            theme: AppThemes.lightTheme,
            home: const Scaffold(
              body: SparkleNetworkImage(
                imageUrl: 'https://example.com/test.png',
                width: 48,
                height: 48,
                semanticLabel: 'Test image',
              ),
            ),
          ),
        );

        expect(find.bySemanticsLabel('Test image'), findsOneWidget);
      });
    });

    testWidgets('no semantics when label is omitted', (tester) async {
      await _withSemantics(tester, () async {
        await tester.pumpWidget(
          testMaterialApp(
            theme: AppThemes.lightTheme,
            home: const Scaffold(
              body: SparkleNetworkImage(
                imageUrl: 'https://example.com/test.png',
                width: 48,
                height: 48,
              ),
            ),
          ),
        );

        expect(find.bySemanticsLabel('Test image'), findsNothing);
      });
    });
  });

  group('FeedPostCard', () {
    testWidgets('renders with user content semantics', (tester) async {
      await _withSemantics(tester, () async {
        await tester.pumpWidget(
          testMaterialApp(
            theme: AppThemes.lightTheme,
            home: Scaffold(
              body: FeedPostCard(
                post: Post(
                  id: 'post-1',
                  userId: 'user-1',
                  content: '今日学习内容',
                  createdAt: DateTime(2026, 5),
                  user: const PostUser(id: 'user-1', username: '小星'),
                ),
                onLike: () {},
              ),
            ),
          ),
        );

        // FeedPostCard should render the post content and user info
        expect(find.text('今日学习内容'), findsOneWidget);
        expect(find.text('小星'), findsOneWidget);
      });
    });
  });
}

Future<void> _withSemantics(
  WidgetTester tester,
  Future<void> Function() body,
) async {
  final semantics = tester.ensureSemantics();
  try {
    await body();
  } finally {
    semantics.dispose();
  }
}
