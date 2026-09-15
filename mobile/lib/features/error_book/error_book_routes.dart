import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/scene_audio_policy.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/error_book/error_book.dart';
import 'package:sparkle/shared/entities/cognitive_analysis.dart';

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
              } catch (error, stackTrace) {
                debugPrint(
                  'ErrorBookRoutes invalid dimension "$dimensionCode": $error',
                );
                debugPrintStack(stackTrace: stackTrace);
              }
            }
            return buildSparkleTransitionPage(
              state: state,
              child: SceneAudioScope(
                policy: const SceneAudioPolicy(track: BgmTrack.task),
                child: ErrorListScreen(
                  filterByDimension: dimension,
                  filterByNodeId: state.uri.queryParameters['node_id'],
                  filterByNodeLabel: state.uri.queryParameters['node_label'],
                ),
              ),
            );
          },
        ),
        GoRoute(
          path: '/errors/new',
          name: 'addError',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: const SceneAudioScope(
              policy: SceneAudioPolicy(track: BgmTrack.task),
              child: AddErrorScreen(),
            ),
            type: SharedAxisTransitionType.scaled,
          ),
        ),
        GoRoute(
          path: '/errors/:id/edit',
          name: 'editError',
          pageBuilder: (context, state) {
            final errorId = state.pathParameters['id']!;
            final initialError =
                state.extra is ErrorRecord ? state.extra! as ErrorRecord : null;
            return buildSparkleTransitionPage(
              state: state,
              child: SceneAudioScope(
                policy: const SceneAudioPolicy(track: BgmTrack.task),
                child: AddErrorScreen(
                  errorId: errorId,
                  initialError: initialError,
                ),
              ),
              type: SharedAxisTransitionType.scaled,
            );
          },
        ),
        GoRoute(
          path: '/errors/:id',
          name: 'errorDetail',
          pageBuilder: (context, state) {
            final errorId = state.pathParameters['id']!;
            return buildSparkleTransitionPage(
              state: state,
              child: SceneAudioScope(
                policy: const SceneAudioPolicy(track: BgmTrack.task),
                child: ErrorDetailScreen(errorId: errorId),
              ),
            );
          },
        ),
      ];
}
