import 'package:animations/animations.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/experience/experience_profile.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/calendar/calendar.dart';

class CalendarRoutes {
  static const String calendar = '/calendar';
  static const String calendarStats = '/calendar-stats';
  static const String dailyDetail = '/calendar/day';

  static List<RouteBase> get routes => [
        GoRoute(
          path: calendar,
          name: 'calendar',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            motionToken: SparkleMotionToken.scene,
            child: SceneAudioScope(
              policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                trackOverride: BgmTrack.calendar,
              ),
              child: CalendarStatsScreen(
                initialDate: _parseInitialDate(
                  state.uri.queryParameters['date'],
                ),
              ),
            ),
            type: SharedAxisTransitionType.scaled,
          ),
        ),
        GoRoute(
          path: calendarStats,
          name: 'calendarStats',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            motionToken: SparkleMotionToken.scene,
            child: SceneAudioScope(
              policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                trackOverride: BgmTrack.calendar,
              ),
              child: CalendarStatsScreen(
                initialDate: _parseInitialDate(
                  state.uri.queryParameters['date'],
                ),
              ),
            ),
            type: SharedAxisTransitionType.scaled,
          ),
        ),
        GoRoute(
          path: dailyDetail,
          name: 'calendarDailyDetail',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            motionToken: SparkleMotionToken.scene,
            child: SceneAudioScope(
              policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                trackOverride: BgmTrack.calendar,
              ),
              child: DailyDetailScreen(
                date: _parseInitialDate(state.uri.queryParameters['date']) ??
                    DateTime.now(),
              ),
            ),
            type: SharedAxisTransitionType.scaled,
          ),
        ),
      ];

  static DateTime? _parseInitialDate(String? raw) {
    if (raw == null || raw.isEmpty) {
      return null;
    }
    return DateTime.tryParse(raw);
  }
}
