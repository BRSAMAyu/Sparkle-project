import 'package:animations/animations.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/scene_audio_policy.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/seed_library/presentation/screens/create_library_screen.dart';
import 'package:sparkle/features/seed_library/presentation/screens/seed_library_detail_screen.dart';
import 'package:sparkle/features/seed_library/presentation/screens/seed_library_list_screen.dart';

class SeedLibraryRoutes {
  static const String libraries = '/seed-libraries';
  static const String createLibrary = '/seed-libraries/new';

  static String detail(String id) => '/seed-libraries/$id';

  static List<RouteBase> get routes => [
        GoRoute(
          path: libraries,
          name: 'seedLibraries',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            motionToken: SparkleMotionToken.scene,
            child: const SceneAudioScope(
              policy: SceneAudioPolicy(
                track: BgmTrack.seeds,
                atmosphere: ExperienceAtmosphere.seedsOrganic,
              ),
              child: SeedLibraryListScreen(),
            ),
          ),
        ),
        GoRoute(
          path: createLibrary,
          name: 'createSeedLibrary',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            motionToken: SparkleMotionToken.scene,
            child: const SceneAudioScope(
              policy: SceneAudioPolicy(
                track: BgmTrack.seeds,
                atmosphere: ExperienceAtmosphere.seedsOrganic,
              ),
              child: CreateLibraryScreen(),
            ),
            type: SharedAxisTransitionType.scaled,
          ),
        ),
        GoRoute(
          path: '/seed-libraries/:id',
          name: 'seedLibraryDetail',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            motionToken: SparkleMotionToken.scene,
            child: SceneAudioScope(
              policy: const SceneAudioPolicy(
                track: BgmTrack.seeds,
                atmosphere: ExperienceAtmosphere.seedsOrganic,
              ),
              child: SeedLibraryDetailScreen(
                libraryId: state.pathParameters['id']!,
              ),
            ),
          ),
        ),
      ];
}
