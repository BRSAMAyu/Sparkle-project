import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/scene_audio_policy.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/memory/memory.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class MemoryRoutes {
  static const String panel = '/memory';
  static const String settings = '/memory/settings';
  static const String detail = '/memory/detail';

  static void popOrGoPanel(BuildContext context, {String fallback = panel}) {
    final navigator = Navigator.of(context);
    if (navigator.canPop()) {
      context.pop();
      return;
    }
    context.go(fallback);
  }

  static List<RouteBase> get routes => [
        GoRoute(
          path: panel,
          name: 'memoryPanel',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            motionToken: SparkleMotionToken.scene,
            child: const SceneAudioScope(
              policy: SceneAudioPolicy(
                track: BgmTrack.insights,
                atmosphere: ExperienceAtmosphere.insightsMist,
              ),
              child: MemoryPanelScreen(),
            ),
            type: SharedAxisTransitionType.scaled,
          ),
        ),
        GoRoute(
          path: settings,
          name: 'memorySettings',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            motionToken: SparkleMotionToken.scene,
            child: const SceneAudioScope(
              policy: SceneAudioPolicy(
                track: BgmTrack.insights,
                atmosphere: ExperienceAtmosphere.insightsMist,
              ),
              child: MemorySettingsScreen(),
            ),
          ),
        ),
        GoRoute(
          path: detail,
          name: 'memoryDetail',
          pageBuilder: (context, state) {
            final args = state.extra;
            if (args is! MemoryDetailArgs) {
              return buildSparkleTransitionPage(
                state: state,
                motionToken: SparkleMotionToken.scene,
                child: const Scaffold(
                  body: Center(child: Text(context.l10n.memDetailMissing)),
                ),
              );
            }
            return buildSparkleTransitionPage(
              state: state,
              motionToken: SparkleMotionToken.scene,
              child: SceneAudioScope(
                policy: const SceneAudioPolicy(
                  track: BgmTrack.insights,
                  atmosphere: ExperienceAtmosphere.insightsMist,
                ),
                child: MemoryDetailScreen(args: args),
              ),
            );
          },
        ),
      ];
}
