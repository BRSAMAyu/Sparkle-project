import 'package:go_router/go_router.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
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
                : const LearningReport(
                    reportId: 'empty',
                    markdown: '暂无学习报告数据。',
                    sections: <String>[],
                    mastery: <LearningMasteryDatum>[],
                  );
            return buildSparkleTransitionPage(
              state: state,
              child: LearningReportScreen(report: report),
            );
          },
        ),
      ];
}
