import 'package:animations/animations.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/features/documents/presentation/screens/document_library_screen.dart';

class DocumentLibraryRoutes {
  static const String library = '/library';
  static const String documents = '/documents';

  static List<RouteBase> get routes => [
        GoRoute(
          path: library,
          name: 'studyMaterialsLibrary',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            type: SharedAxisTransitionType.scaled,
            child: const DocumentLibraryScreen(),
          ),
        ),
        GoRoute(
          path: documents,
          redirect: (_, __) => library,
        ),
      ];
}
