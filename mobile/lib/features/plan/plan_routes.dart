import 'package:animations/animations.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/experience/experience_profile.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/plan/data/models/exam_sprint_models.dart';
import 'package:sparkle/features/plan/presentation/screens/exam_sprint_setup_screen.dart';
import 'package:sparkle/features/plan/presentation/screens/growth_screen.dart';
import 'package:sparkle/features/plan/presentation/screens/learning_portfolio_screen.dart';
import 'package:sparkle/features/plan/presentation/screens/plan_create_screen.dart';
import 'package:sparkle/features/plan/presentation/screens/plan_detail_screen.dart';
import 'package:sparkle/features/plan/presentation/screens/plan_edit_screen.dart';
import 'package:sparkle/features/plan/presentation/screens/plan_history_screen.dart';
import 'package:sparkle/features/plan/presentation/screens/post_exam_review_screen.dart';
import 'package:sparkle/features/plan/presentation/screens/sprint_completion_screen.dart';
import 'package:sparkle/features/plan/presentation/screens/sprint_history_screen.dart';
import 'package:sparkle/features/plan/presentation/screens/sprint_screen.dart';

class PlanRoutes {
  // Route constants for deep linking and navigation
  static const String home = '/plans';
  static const String planCreate = '/plans/new';
  static const String planDetail = '/plans/:id';
  static const String planEdit = '/plans/:id/edit';
  static const String planHistory = '/plans/history';
  static const String sprint = '/sprint';
  static const String sprintHistory = '/sprint/history';
  static const String growth = '/growth';
  static const String examSprintSetup = '/exam-sprint/setup';
  static const String examSprintReview = '/exam-sprint/review';
  static const String examSprintCompletion = '/exam-sprint/completion';
  static const String learningPortfolio = '/exam-sprint/portfolio';

  static List<RouteBase> get shellRoutes => [
        _planDetailRoute(),
      ];

  static List<RouteBase> get routes => [
        GoRoute(
          path: learningPortfolio,
          name: 'learningPortfolio',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            motionToken: SparkleMotionToken.scene,
            child: SceneAudioScope(
              policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                trackOverride: BgmTrack.plan,
              ),
              child: const LearningPortfolioScreen(),
            ),
            type: SharedAxisTransitionType.scaled,
          ),
        ),
        GoRoute(
          path: examSprintCompletion,
          name: 'examSprintCompletion',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) {
            final extra = state.extra;
            final extraMap = extra is Map ? extra : null;
            final summary = extraMap?['summary'];
            final planId = state.uri.queryParameters['plan_id'] ??
                state.uri.queryParameters['planId'] ??
                extraMap?['plan_id']?.toString() ??
                extraMap?['planId']?.toString() ??
                '';
            final subjectName = state.uri.queryParameters['subject'] ??
                state.uri.queryParameters['subject_name'] ??
                extraMap?['subject']?.toString() ??
                extraMap?['subjectName']?.toString() ??
                '';
            return buildSparkleTransitionPage(
              state: state,
              motionToken: SparkleMotionToken.scene,
              child: SceneAudioScope(
                policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                  trackOverride: BgmTrack.plan,
                ),
                child: SprintCompletionScreen(
                  planId: planId,
                  subjectName: subjectName,
                  initialSummary:
                      summary is SprintCompletionSummary ? summary : null,
                ),
              ),
              type: SharedAxisTransitionType.scaled,
            );
          },
        ),
        GoRoute(
          path: examSprintReview,
          name: 'examSprintReview',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) {
            final extra = state.extra;
            final extraMap = extra is Map ? extra : null;
            final planId = state.uri.queryParameters['plan_id'] ??
                state.uri.queryParameters['planId'] ??
                extraMap?['plan_id']?.toString() ??
                extraMap?['planId']?.toString() ??
                '';
            final subjectName = state.uri.queryParameters['subject'] ??
                state.uri.queryParameters['subject_name'] ??
                extraMap?['subject']?.toString() ??
                extraMap?['subjectName']?.toString() ??
                '';
            return buildSparkleTransitionPage(
              state: state,
              motionToken: SparkleMotionToken.scene,
              child: SceneAudioScope(
                policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                  trackOverride: BgmTrack.plan,
                ),
                child: PostExamReviewScreen(
                  planId: planId,
                  subjectName: subjectName,
                ),
              ),
              type: SharedAxisTransitionType.scaled,
            );
          },
        ),
        GoRoute(
          path: examSprintSetup,
          name: 'examSprintSetup',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            motionToken: SparkleMotionToken.scene,
            child: SceneAudioScope(
              policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                trackOverride: BgmTrack.plan,
              ),
              child: const ExamSprintSetupScreen(),
            ),
            type: SharedAxisTransitionType.scaled,
          ),
        ),
        // Plan create (modal-like, full-screen)
        GoRoute(
          path: planCreate,
          name: 'createPlan',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) {
            final planType = state.uri.queryParameters['type'];
            return buildSparkleTransitionPage(
              state: state,
              motionToken: SparkleMotionToken.scene,
              child: SceneAudioScope(
                policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                  trackOverride: BgmTrack.plan,
                ),
                child: PlanCreateScreen(planType: planType),
              ),
              type: SharedAxisTransitionType.scaled,
            );
          },
        ),
        // Plan detail
        _planDetailRoute(name: null),
        // Plan edit (modal-like, full-screen)
        GoRoute(
          path: planEdit,
          name: 'editPlan',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) {
            // id is a required path parameter, so it won't be null
            final planId = state.pathParameters['id']!;
            return buildSparkleTransitionPage(
              state: state,
              motionToken: SparkleMotionToken.scene,
              child: SceneAudioScope(
                policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                  trackOverride: BgmTrack.plan,
                ),
                child: PlanEditScreen(planId: planId),
              ),
              type: SharedAxisTransitionType.scaled,
            );
          },
        ),
        GoRoute(
          path: planHistory,
          name: 'planHistory',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: SceneAudioScope(
              policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                trackOverride: BgmTrack.plan,
              ),
              child: const PlanHistoryScreen(),
            ),
          ),
        ),
        // Plans list / Sprint screen (detail page, full-screen)
        GoRoute(
          path: home,
          name: 'plans',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: SceneAudioScope(
              policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                trackOverride: BgmTrack.plan,
              ),
              child: const SprintScreen(),
            ),
          ),
        ),
        // Sprint alias (detail page, full-screen)
        GoRoute(
          path: sprint,
          name: 'sprint',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: SceneAudioScope(
              policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                trackOverride: BgmTrack.plan,
              ),
              child: const SprintScreen(),
            ),
          ),
        ),
        // Sprint history (detail page, full-screen)
        GoRoute(
          path: sprintHistory,
          name: 'sprintHistory',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: SceneAudioScope(
              policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                trackOverride: BgmTrack.plan,
              ),
              child: const SprintHistoryScreen(),
            ),
          ),
        ),
        // Growth screen (detail page, full-screen)
        GoRoute(
          path: growth,
          name: 'growth',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: SceneAudioScope(
              policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                trackOverride: BgmTrack.plan,
              ),
              child: const GrowthScreen(),
            ),
          ),
        ),
      ];

  static GoRoute _planDetailRoute({String? name = 'planDetail'}) => GoRoute(
        path: planDetail,
        name: name,
        pageBuilder: (context, state) {
          // id is a required path parameter, so it won't be null
          final planId = state.pathParameters['id']!;
          return buildSparkleTransitionPage(
            state: state,
            child: SceneAudioScope(
              policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                trackOverride: BgmTrack.plan,
              ),
              child: PlanDetailScreen(planId: planId),
            ),
          );
        },
      );
}
