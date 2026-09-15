import 'package:go_router/go_router.dart';
import 'package:sparkle/core/experience/experience_profile.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
import 'package:sparkle/features/tools/presentation/screens/tool_host_screen.dart';
import 'package:sparkle/features/tools/presentation/screens/tool_library_screen.dart';
import 'package:sparkle/features/tools/tool_registry.dart';

class ToolsRoutes {
  static const String library = '/tools/library';
  static const String toolHost = '/tools/:toolId';

  static List<RouteBase> get routes => [
        GoRoute(
          path: library,
          name: 'toolLibrary',
          pageBuilder: (context, state) {
            final initialTab =
                state.uri.queryParameters['tab'] == 'manage' ? 1 : 0;
            return buildSparkleTransitionPage(
              state: state,
              child: SceneAudioScope(
                policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                  trackOverride: BgmTrack.tools,
                ),
                child: ToolLibraryScreen(initialTab: initialTab),
              ),
            );
          },
        ),
        GoRoute(
          path: toolHost,
          name: 'toolHost',
          redirect: (context, state) {
            final toolId = state.pathParameters['toolId']!;
            final tool = ToolRegistry.tryGetById(toolId);
            if (tool == null) {
              return '/home';
            }
            if (tool.isRouteBased) {
              final launchContext = ToolLaunchContext.values.firstWhere(
                (value) => value.name == state.uri.queryParameters['context'],
                orElse: () => ToolLaunchContext.toolLibrary,
              );
              return tool.routeBuilder!(
                ToolLaunchRequest(
                  context: launchContext,
                  surface: ToolSurface.page,
                  taskId: state.uri.queryParameters['taskId'],
                ),
              );
            }
            return null;
          },
          pageBuilder: (context, state) {
            final launchContext = ToolLaunchContext.values.firstWhere(
              (value) => value.name == state.uri.queryParameters['context'],
              orElse: () => ToolLaunchContext.toolLibrary,
            );
            return buildSparkleTransitionPage(
              state: state,
              child: SceneAudioScope(
                policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                  trackOverride: BgmTrack.tools,
                ),
                child: ToolHostScreen(
                  toolId: state.pathParameters['toolId']!,
                  launchContext: launchContext,
                  taskId: state.uri.queryParameters['taskId'],
                ),
              ),
            );
          },
        ),
      ];
}
