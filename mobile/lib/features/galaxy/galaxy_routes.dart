import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/experience/experience_profile.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/scene_audio_policy.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/knowledge/presentation/screens/knowledge_detail_screen.dart';
import 'package:sparkle/features/galaxy/presentation/screens/galaxy_draft_review_screen.dart';

class GalaxyRoutes {
  // Route constants for deep linking and navigation
  static const String home = '/galaxy';
  static const String knowledgeDetail = '/galaxy/node/:id';
  static const String draftReview = '/galaxy/drafts/review';

  static List<RouteBase> get routes => [
        GoRoute(
          path: draftReview,
          name: 'galaxyDraftReview',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) {
            final args = state.extra is GalaxyDraftReviewRouteArgs
                ? state.extra! as GalaxyDraftReviewRouteArgs
                : null;
            return buildSparkleTransitionPage(
              state: state,
              motionToken: SparkleMotionToken.scene,
              type: SharedAxisTransitionType.horizontal,
              child: SceneAudioScope(
                policy: ExperienceProfiles.focusImmersive.audioPolicy(
                  trackOverride: BgmTrack.galaxy,
                  atmosphereOverride: ExperienceAtmosphere.none,
                ),
                child: GalaxyDraftReviewScreen(
                  initialBatchId: args?.batchId,
                ),
              ),
            );
          },
        ),
        // Knowledge detail (full-screen, uses root navigator)
        GoRoute(
          path: knowledgeDetail,
          name: 'knowledgeDetail',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) {
            // P1-12 fix: null-safety for path parameter
            final nodeId = state.pathParameters['id'];
            if (nodeId == null) {
              return buildSparkleTransitionPage(
                state: state,
                child: Scaffold(
                  body: Center(
                    child: Text(
                      context.l10n.galaxyInvalidNodeId,
                      style: Theme.of(context).textTheme.bodyLarge,
                    ),
                  ),
                ),
              );
            }
            return buildSparkleTransitionPage(
              state: state,
              motionToken: SparkleMotionToken.scene,
              type: SharedAxisTransitionType.scaled,
              child: SceneAudioScope(
                policy: ExperienceProfiles.focusImmersive.audioPolicy(
                  trackOverride: BgmTrack.galaxy,
                  atmosphereOverride: ExperienceAtmosphere.none,
                ),
                child: KnowledgeDetailScreen(nodeId: nodeId),
              ),
            );
          },
        ),
      ];
}
