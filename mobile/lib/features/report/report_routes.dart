import 'package:go_router/go_router.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/scene_audio_policy.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/report/data/models/learning_report.dart';
import 'package:sparkle/features/report/presentation/screens/learning_report_screen.dart';

class ReportRoutes {
  static const String learningReport = '/learning-report';

  static List<RouteBase> get routes => <RouteBase>[
        GoRoute(
          path: learningReport,
          name: 'learning-report',
          pageBuilder: (context, state) {
            final report = state.extra is LearningReport
                ? state.extra as LearningReport
                : LearningReport(
                    reportId: 'empty',
                    markdown: context.l10n.noLearningReportData,
                    sections: const <String>[],
                    mastery: const <LearningMasteryDatum>[],
                  );
            return buildSparkleTransitionPage(
              state: state,
              child: SceneAudioScope(
                policy: const SceneAudioPolicy(track: BgmTrack.insights),
                child: LearningReportScreen(
                  report: report,
                  initialSourceChatSessionId:
                      state.uri.queryParameters['source_chat_session_id'],
                ),
              ),
            );
          },
        ),
      ];
}
