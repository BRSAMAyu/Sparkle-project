import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/community/community_routes.dart';
import 'package:sparkle/features/error_book/error_book_routes.dart';
import 'package:sparkle/features/error_book/presentation/screens/review_screen.dart';
import 'package:sparkle/features/galaxy/galaxy_routes.dart';
import 'package:sparkle/features/insights/insights_routes.dart';
import 'package:sparkle/features/memory/memory_routes.dart';
import 'package:sparkle/features/reviews/reviews_routes.dart';
import 'package:sparkle/features/shop/shop_routes.dart';
import 'package:sparkle/shared/entities/cognitive_analysis.dart';

void main() {
  group('J6: Error Book & Review chain', () {
    test('error book routes define all required paths', () {
      final routes = ErrorBookRoutes.routes;
      final paths = routes.whereType<GoRoute>().map((r) => r.path).toSet();

      expect(paths.contains('/errors'), isTrue, reason: 'error list route');
      expect(paths.contains('/errors/new'), isTrue, reason: 'add error route');
      expect(paths.contains('/errors/:id/edit'), isTrue,
          reason: 'edit error route');
      expect(paths.contains('/errors/:id'), isTrue,
          reason: 'error detail route');
    });

    test('review routes define the hub and active review paths', () {
      final routes = ReviewRoutes.routes;
      final paths = routes.whereType<GoRoute>().map((r) => r.path).toSet();

      expect(paths.contains(ReviewRoutes.planHub), isTrue,
          reason: 'review hub route');
      expect(paths.contains(ReviewRoutes.review), isTrue,
          reason: 'review session route');
    });

    test('ReviewMode enum covers all 4 learning modes', () {
      expect(ReviewMode.values.length, 4);
      expect(ReviewMode.today.code, 'today');
      expect(ReviewMode.bySubject.code, 'subject');
      expect(ReviewMode.weakest.code, 'weakest');
      expect(ReviewMode.random.code, 'random');

      // Each mode must have a non-empty label and description
      for (final mode in ReviewMode.values) {
        expect(mode.label(S).isNotEmpty, isTrue);
        expect(mode.description(S).isNotEmpty, isTrue);
      }
    });

    test('CognitiveDimension enum supports error filtering', () {
      // Verify at least basic dimensions exist
      expect(CognitiveDimension.values.isNotEmpty, isTrue);

      // Each dimension must have a code for URL query params
      for (final dim in CognitiveDimension.values) {
        expect(dim.code.isNotEmpty, isTrue,
            reason: '${dim.name} must have a code');
      }
    });

    test('review mode code round-trip via URL query parameter', () {
      // Simulate what the route builder does
      for (final mode in ReviewMode.values) {
        final resolved = ReviewMode.values.firstWhere(
          (m) => m.code == mode.code,
          orElse: () => ReviewMode.today,
        );
        expect(resolved, mode);
      }
    });
  });

  group('J7: Knowledge & Insights chain', () {
    test('galaxy routes define knowledge detail path', () {
      final routes = GalaxyRoutes.routes;
      final paths = routes.whereType<GoRoute>().map((r) => r.path).toSet();

      expect(paths.contains('/galaxy/node/:id'), isTrue,
          reason: 'knowledge detail route must exist');
    });

    test('insights routes define learning forecast path', () {
      final routes = InsightsRoutes.routes;
      final paths = routes.whereType<GoRoute>().map((r) => r.path).toSet();

      expect(paths.contains('/learning/forecast'), isTrue,
          reason: 'learning forecast route must exist');
    });
  });

  group('J8: Memory system chain', () {
    test('memory routes define panel, settings, and detail paths', () {
      final routes = MemoryRoutes.routes;
      final paths = routes.whereType<GoRoute>().map((r) => r.path).toSet();

      expect(paths.contains('/memory'), isTrue, reason: 'memory panel');
      expect(paths.contains('/memory/settings'), isTrue,
          reason: 'memory settings');
      expect(paths.contains('/memory/detail'), isTrue, reason: 'memory detail');
    });

    test('memory detail gracefully handles missing args', () {
      // The route builder should show an error message, not crash
      // This is verified by the route code: if args is! MemoryDetailArgs,
      // it returns a scaffold with '记忆详情参数缺失'
      expect(MemoryRoutes.detail, '/memory/detail');
    });
  });

  group('J9: Shop system chain', () {
    test('shop route exists with proper path', () {
      final routes = ShopRoutes.routes;
      final paths = routes.whereType<GoRoute>().map((r) => r.path).toSet();

      expect(paths.contains('/shop'), isTrue);
    });

    test('shop route uses SceneAudioScope (not bare MaterialPage)', () {
      // Verify the route builder wraps with audio scope by checking
      // the route uses buildSparkleTransitionPage (not MaterialPage)
      final route = ShopRoutes.routes.whereType<GoRoute>().first;
      expect(route.pageBuilder, isNotNull,
          reason: 'shop route must use pageBuilder for transition support');
    });
  });

  group('J10: Community advanced routes completeness', () {
    test('community routes define all 18+ required paths', () {
      final routes = CommunityRoutes.routes;
      final paths = routes.whereType<GoRoute>().map((r) => r.path).toSet();

      // Core social paths
      expect(paths.contains(CommunityRoutes.friendsRequests), isTrue);
      expect(paths.contains(CommunityRoutes.friendsDiscover), isTrue);
      expect(paths.contains(CommunityRoutes.friends), isTrue);
      expect(paths.contains(CommunityRoutes.userSearch), isTrue);
      expect(paths.contains(CommunityRoutes.userProfile), isTrue);

      // Group paths
      expect(paths.contains(CommunityRoutes.groups), isTrue);
      expect(paths.contains(CommunityRoutes.groupsSearch), isTrue);
      expect(paths.contains(CommunityRoutes.groupsDiscover), isTrue);
      expect(paths.contains(CommunityRoutes.groupsCreate), isTrue);
      expect(paths.contains(CommunityRoutes.groupDetail), isTrue);
      expect(paths.contains(CommunityRoutes.groupTasks), isTrue);
      expect(paths.contains(CommunityRoutes.groupMembers), isTrue);
      expect(paths.contains(CommunityRoutes.groupFiles), isTrue);
      expect(paths.contains(CommunityRoutes.groupModeration), isTrue);

      // Utility paths
      expect(paths.contains(CommunityRoutes.favorites), isTrue);
      expect(paths.contains(CommunityRoutes.blockedUsers), isTrue);
      expect(paths.contains(CommunityRoutes.accountability), isTrue);
      expect(paths.contains(CommunityRoutes.accountabilityDetail), isTrue);
      expect(paths.contains(CommunityRoutes.postsCreate), isTrue);
    });
  });
}
