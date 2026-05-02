import 'package:animations/animations.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/scene_audio_policy.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/error_book/presentation/screens/review_screen.dart';
import 'package:sparkle/features/reviews/presentation/screens/review_plan_hub_screen.dart';

class ReviewRoutes {
  static const String planHub = '/review-plan';
  static const String review = '/review';

  static String todayReviewLocation({String? subjectCode}) {
    final query = <String, String>{
      'mode': ReviewMode.today.code,
      if (subjectCode != null && subjectCode.isNotEmpty) 'subject': subjectCode,
    };
    return Uri(path: review, queryParameters: query).toString();
  }

  static List<RouteBase> get routes => [
        GoRoute(
          path: planHub,
          name: 'reviewPlanHub',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: const SceneAudioScope(
              policy: SceneAudioPolicy(track: BgmTrack.task),
              child: ReviewPlanHubScreen(),
            ),
            type: SharedAxisTransitionType.scaled,
          ),
        ),
        GoRoute(
          path: review,
          name: 'review',
          pageBuilder: (context, state) {
            final modeCode = state.uri.queryParameters['mode'] ?? 'today';
            final subjectCode = state.uri.queryParameters['subject'];

            final mode = ReviewMode.values.firstWhere(
              (m) => m.code == modeCode,
              orElse: () => ReviewMode.today,
            );

            return buildSparkleTransitionPage(
              state: state,
              child: SceneAudioScope(
                policy: const SceneAudioPolicy(track: BgmTrack.task),
                child: ReviewScreen(mode: mode, subjectCode: subjectCode),
              ),
              type: SharedAxisTransitionType.scaled,
            );
          },
        ),
      ];
}
