import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/features/error_book/error_book.dart';
import 'package:sparkle/shared/entities/cognitive_analysis.dart';

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

class ErrorBookRoutes {
  static List<RouteBase> get routes => [
    GoRoute(
        path: '/errors',
        name: 'errors',
        pageBuilder: (context, state) {
          final dimensionCode = state.uri.queryParameters['dimension'];
          CognitiveDimension? dimension;
          if (dimensionCode != null) {
            try {
              dimension = CognitiveDimension.values.firstWhere(
                (e) => e.code == dimensionCode,
              );
            } catch (_) {}
          }
          return _buildTransitionPage(
            state: state,
            child: ErrorListScreen(filterByDimension: dimension),
          );
        },
      ),
      GoRoute(
        path: '/errors/new',
        name: 'addError',
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const AddErrorScreen(),
          type: SharedAxisTransitionType.scaled,
        ),
      ),
      GoRoute(
        path: '/errors/:id',
        name: 'errorDetail',
        pageBuilder: (context, state) {
          final errorId = state.pathParameters['id'];
          return _buildTransitionPage(
            state: state,
            child: ErrorDetailScreen(errorId: errorId),
          );
        },
      ),
      GoRoute(
        path: '/review',
        name: 'review',
        pageBuilder: (context, state) {
          final modeCode = state.uri.queryParameters['mode'] ?? 'today';
          final subjectCode = state.uri.queryParameters['subject'];

          final mode = ReviewMode.values.firstWhere(
            (m) => m.code == modeCode,
            orElse: () => ReviewMode.today,
          );

          return _buildTransitionPage(
            state: state,
            child: ReviewScreen(mode: mode, subjectCode: subjectCode),
            type: SharedAxisTransitionType.scaled,
          );
        },
      ),
  ];
}
