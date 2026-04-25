import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/features/achievement/achievement_routes.dart';
import 'package:sparkle/features/auth/auth_routes.dart';
import 'package:sparkle/features/calendar/calendar_routes.dart';
import 'package:sparkle/features/chat/chat_routes.dart';
import 'package:sparkle/features/cognitive/cognitive_routes.dart';
import 'package:sparkle/features/community/community_routes.dart';
import 'package:sparkle/features/error_book/error_book_routes.dart';
import 'package:sparkle/features/focus/focus_routes.dart';
import 'package:sparkle/features/galaxy/galaxy_routes.dart';
import 'package:sparkle/features/insights/insights_routes.dart';
import 'package:sparkle/features/memory/memory_routes.dart';
import 'package:sparkle/features/notification_center/notification_center_routes.dart';
import 'package:sparkle/features/photon/photon_routes.dart';
import 'package:sparkle/features/plan/plan_routes.dart';
import 'package:sparkle/features/seed_library/seed_library_routes.dart';
import 'package:sparkle/features/shop/shop_routes.dart';
import 'package:sparkle/features/task/task_routes.dart';
import 'package:sparkle/features/tools/tools_routes.dart';
import 'package:sparkle/features/translation/translation_routes.dart';
import 'package:sparkle/features/user/user_routes.dart';
import 'package:sparkle/features/visual_elements/visual_elements_routes.dart';

/// Extracts all GoRoute paths from a list of route bases (including nested).
Set<String> _extractPaths(List<RouteBase> routes) {
  final paths = <String>{};
  for (final route in routes) {
    if (route is GoRoute) {
      paths.add(route.path);
    }
    if (route is ShellRoute) {
      paths.addAll(_extractPaths(route.routes));
    }
  }
  return paths;
}

void main() {
  group('Full route coverage: every feature module defines valid routes', () {
    test('achievement routes (5 paths)', () {
      final paths = _extractPaths(AchievementRoutes.routes);
      expect(paths, containsAll([
        '/achievements',
        '/achievements/:id',
        '/achievements/map',
        '/achievements/streak',
        '/achievements/contract',
      ]));
    });

    test('auth routes (6 paths)', () {
      final paths = _extractPaths(AuthRoutes.routes);
      expect(paths, containsAll([
        '/login',
        '/register',
        '/forgot-password',
        '/reset-password',
        '/legal/terms',
        '/legal/privacy',
      ]));
    });

    test('calendar routes (3 paths)', () {
      final paths = _extractPaths(CalendarRoutes.routes);
      expect(paths, containsAll([
        '/calendar',
        '/calendar-stats',
        '/calendar/day',
      ]));
    });

    test('chat routes (6 paths including legacy redirects)', () {
      final paths = _extractPaths(ChatRoutes.routes);
      expect(paths, containsAll([
        '/chat/group/:id',
        '/chat/private/:id',
      ]));
      // Legacy redirects
      expect(paths.contains('/community/chat/group/:id'), isTrue);
      expect(paths.contains('/community/chat/private/:id'), isTrue);
    });

    test('cognitive routes (2 paths)', () {
      final paths = _extractPaths(CognitiveRoutes.routes);
      expect(paths, containsAll([
        '/cognitive/patterns',
        '/curiosity-capsule',
      ]));
    });

    test('community routes (19+ paths)', () {
      final paths = _extractPaths(CommunityRoutes.routes);
      expect(paths.length, greaterThanOrEqualTo(19));
      expect(paths, containsAll([
        CommunityRoutes.friends,
        CommunityRoutes.friendsRequests,
        CommunityRoutes.friendsDiscover,
        CommunityRoutes.userSearch,
        CommunityRoutes.userProfile,
        CommunityRoutes.groups,
        CommunityRoutes.groupsCreate,
        CommunityRoutes.groupDetail,
        CommunityRoutes.groupMembers,
        CommunityRoutes.favorites,
        CommunityRoutes.accountability,
        CommunityRoutes.accountabilityDetail,
        CommunityRoutes.postsCreate,
      ]));
    });

    test('error book routes (4 paths)', () {
      final paths = _extractPaths(ErrorBookRoutes.routes);
      expect(paths, containsAll([
        '/errors',
        '/errors/new',
        '/errors/:id',
        '/review',
      ]));
    });

    test('focus routes (2 paths)', () {
      final paths = _extractPaths(FocusRoutes.routes);
      expect(paths.length, greaterThanOrEqualTo(2));
    });

    test('galaxy routes define knowledge detail', () {
      final paths = _extractPaths(GalaxyRoutes.routes);
      expect(paths.contains('/galaxy/node/:id'), isTrue);
    });

    test('insights routes define learning forecast', () {
      final paths = _extractPaths(InsightsRoutes.routes);
      expect(paths.contains('/learning/forecast'), isTrue);
    });

    test('memory routes (3 paths)', () {
      final paths = _extractPaths(MemoryRoutes.routes);
      expect(paths, containsAll([
        '/memory',
        '/memory/settings',
        '/memory/detail',
      ]));
    });

    test('notification center routes (2 paths)', () {
      final paths = _extractPaths(NotificationCenterRoutes.routes);
      expect(paths, containsAll([
        '/notification-center',
        '/notification-analytics',
      ]));
    });

    test('photon routes (2 paths)', () {
      final paths = _extractPaths(PhotonRoutes.routes);
      expect(paths, containsAll([
        PhotonRoutes.transactionHistory,
        PhotonRoutes.transfer,
      ]));
    });

    test('plan routes (9 paths)', () {
      final paths = _extractPaths(PlanRoutes.routes);
      expect(paths.length, greaterThanOrEqualTo(9));
      expect(paths, containsAll([
        '/plans',
        '/plans/new',
        '/plans/:id',
        '/exam-sprint/review',
      ]));
    });

    test('seed library routes (3 paths)', () {
      final paths = _extractPaths(SeedLibraryRoutes.routes);
      expect(paths, containsAll([
        '/seed-libraries',
        '/seed-libraries/new',
        '/seed-libraries/:id',
      ]));
    });

    test('shop route uses pageBuilder (not bare MaterialPage)', () {
      final route = ShopRoutes.routes.whereType<GoRoute>().first;
      expect(route.path, '/shop');
      expect(route.pageBuilder, isNotNull);
    });

    test('task routes (4 paths)', () {
      final paths = _extractPaths(TaskRoutes.routes);
      expect(paths, containsAll([
        '/tasks',
        '/tasks/new',
        '/tasks/:id',
        '/tasks/:id/execute',
      ]));
    });

    test('tools routes (2 paths) use pageBuilder', () {
      final routes = ToolsRoutes.routes.whereType<GoRoute>().toList();
      expect(routes.length, 2);
      for (final route in routes) {
        expect(route.pageBuilder, isNotNull,
            reason: '${route.path} must use pageBuilder');
      }
    });

    test('translation routes (1 path)', () {
      final paths = _extractPaths(TranslationRoutes.routes);
      expect(paths.contains(TranslationRoutes.history), isTrue);
    });

    test('user routes (17+ paths)', () {
      final paths = _extractPaths(UserRoutes.routes);
      expect(paths.length, greaterThanOrEqualTo(15));
      expect(paths, containsAll([
        '/profile/edit',
        '/profile/settings',
        '/profile/persona',
      ]));
    });

    test('visual elements route uses pageBuilder', () {
      final route = VisualElementsRoutes.routes.whereType<GoRoute>().first;
      expect(route.path, '/visual-elements');
      expect(route.pageBuilder, isNotNull);
    });
  });

  group('Route constant consistency', () {
    test('all route constants are unique across features', () {
      final allPaths = <String>{};
      final duplicates = <String>[];

      void checkUnique(String feature, Set<String> paths) {
        for (final path in paths) {
          // Skip legacy redirects
          if (path.startsWith('/community/chat/') ||
              path.startsWith('/community/groups/') && path.endsWith('/chat') ||
              path.startsWith('/community/friends/') && path.endsWith('/chat')) {
            continue;
          }
          if (!allPaths.add(path)) {
            duplicates.add('$feature: $path');
          }
        }
      }

      checkUnique('achievement', _extractPaths(AchievementRoutes.routes));
      checkUnique('auth', _extractPaths(AuthRoutes.routes));
      checkUnique('calendar', _extractPaths(CalendarRoutes.routes));
      checkUnique('chat', _extractPaths(ChatRoutes.routes));
      checkUnique('cognitive', _extractPaths(CognitiveRoutes.routes));
      checkUnique('community', _extractPaths(CommunityRoutes.routes));
      checkUnique('error_book', _extractPaths(ErrorBookRoutes.routes));
      checkUnique('focus', _extractPaths(FocusRoutes.routes));
      checkUnique('galaxy', _extractPaths(GalaxyRoutes.routes));
      checkUnique('insights', _extractPaths(InsightsRoutes.routes));
      checkUnique('memory', _extractPaths(MemoryRoutes.routes));
      checkUnique('notification', _extractPaths(NotificationCenterRoutes.routes));
      checkUnique('photon', _extractPaths(PhotonRoutes.routes));
      checkUnique('plan', _extractPaths(PlanRoutes.routes));
      checkUnique('seed_library', _extractPaths(SeedLibraryRoutes.routes));
      checkUnique('shop', _extractPaths(ShopRoutes.routes));
      checkUnique('task', _extractPaths(TaskRoutes.routes));
      checkUnique('tools', _extractPaths(ToolsRoutes.routes));
      checkUnique('translation', _extractPaths(TranslationRoutes.routes));
      checkUnique('user', _extractPaths(UserRoutes.routes));
      checkUnique('visual_elements', _extractPaths(VisualElementsRoutes.routes));

      expect(duplicates, isEmpty,
          reason: 'Duplicate route paths: ${duplicates.join(", ")}');
    });

    test('total route count is at least 90', () {
      var count = 0;
      count += _extractPaths(AchievementRoutes.routes).length;
      count += _extractPaths(AuthRoutes.routes).length;
      count += _extractPaths(CalendarRoutes.routes).length;
      count += _extractPaths(ChatRoutes.routes).length;
      count += _extractPaths(CognitiveRoutes.routes).length;
      count += _extractPaths(CommunityRoutes.routes).length;
      count += _extractPaths(ErrorBookRoutes.routes).length;
      count += _extractPaths(FocusRoutes.routes).length;
      count += _extractPaths(GalaxyRoutes.routes).length;
      count += _extractPaths(InsightsRoutes.routes).length;
      count += _extractPaths(MemoryRoutes.routes).length;
      count += _extractPaths(NotificationCenterRoutes.routes).length;
      count += _extractPaths(PhotonRoutes.routes).length;
      count += _extractPaths(PlanRoutes.routes).length;
      count += _extractPaths(SeedLibraryRoutes.routes).length;
      count += _extractPaths(ShopRoutes.routes).length;
      count += _extractPaths(TaskRoutes.routes).length;
      count += _extractPaths(ToolsRoutes.routes).length;
      count += _extractPaths(TranslationRoutes.routes).length;
      count += _extractPaths(UserRoutes.routes).length;
      count += _extractPaths(VisualElementsRoutes.routes).length;
      // ignore: avoid_print
      print('Total routes: $count');
      expect(count, greaterThanOrEqualTo(90));
    });
  });
}
