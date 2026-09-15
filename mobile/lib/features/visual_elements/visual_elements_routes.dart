import 'package:go_router/go_router.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/scene_audio_policy.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/visual_elements/presentation/screens/visual_elements_screen.dart';

/// 视觉元素系统路由配置
class VisualElementsRoutes {
  VisualElementsRoutes._();

  static const String basePath = '/visual-elements';

  static List<RouteBase> routes = [
    GoRoute(
      path: basePath,
      pageBuilder: (context, state) => buildSparkleTransitionPage(
        state: state,
        child: const SceneAudioScope(
          policy: SceneAudioPolicy(track: BgmTrack.profile),
          child: VisualElementsScreen(),
        ),
      ),
    ),
  ];
}
