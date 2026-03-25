import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/scene_audio_policy.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/shop/presentation/screens/shop_screen.dart';

/// Shop routes
class ShopRoutes {
  ShopRoutes._();

  static const String basePath = '/shop';

  static List<RouteBase> routes = [
    GoRoute(
      path: basePath,
      pageBuilder: (context, state) => buildSparkleTransitionPage(
        state: state,
        child: const SceneAudioScope(
          policy: SceneAudioPolicy(track: BgmTrack.community),
          child: ShopScreen(),
        ),
      ),
    ),
  ];
}
