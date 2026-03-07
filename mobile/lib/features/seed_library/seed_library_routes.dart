import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/features/seed_library/presentation/screens/create_library_screen.dart';
import 'package:sparkle/features/seed_library/presentation/screens/seed_library_detail_screen.dart';
import 'package:sparkle/features/seed_library/presentation/screens/seed_library_list_screen.dart';

Page<dynamic> _buildTransitionPage({
  required GoRouterState state,
  required Widget child,
  SharedAxisTransitionType type = SharedAxisTransitionType.horizontal,
}) =>
    CustomTransitionPage<void>(
      key: state.pageKey,
      child: child,
      transitionsBuilder: (context, animation, secondaryAnimation, child) =>
          SharedAxisTransition(
        animation: animation,
        secondaryAnimation: secondaryAnimation,
        transitionType: type,
        child: child,
      ),
    );

class SeedLibraryRoutes {
  static const String libraries = '/seed-libraries';
  static const String createLibrary = '/seed-libraries/new';

  static String detail(String id) => '/seed-libraries/$id';

  static List<RouteBase> get routes => [
        GoRoute(
          path: libraries,
          name: 'seedLibraries',
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: const SeedLibraryListScreen(),
          ),
        ),
        GoRoute(
          path: createLibrary,
          name: 'createSeedLibrary',
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: const CreateLibraryScreen(),
            type: SharedAxisTransitionType.scaled,
          ),
        ),
        GoRoute(
          path: '/seed-libraries/:id',
          name: 'seedLibraryDetail',
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: SeedLibraryDetailScreen(
              libraryId: state.pathParameters['id']!,
            ),
          ),
        ),
      ];
}
