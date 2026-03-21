import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/widgets/bgm_scope.dart';
import 'package:sparkle/features/calendar/calendar.dart';

Page<dynamic> _buildTransitionPage({
  required GoRouterState state,
  required Widget child,
  SharedAxisTransitionType type = SharedAxisTransitionType.horizontal,
}) =>
    CustomTransitionPage<void>(
      key: state.pageKey,
      child: child,
      transitionsBuilder: (context, animation, secondaryAnimation, child) =>
          SharedAxisTransition(
        animation: animation,
        secondaryAnimation: secondaryAnimation,
        transitionType: type,
        child: child,
      ),
    );

class CalendarRoutes {
  static const String calendar = '/calendar';
  static const String calendarStats = '/calendar-stats';
  static const String dailyDetail = '/calendar/day';

  static List<RouteBase> get routes => [
        GoRoute(
          path: calendar,
          name: 'calendar',
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: BgmScope(
              track: BgmTrack.calendar,
              child: CalendarStatsScreen(
                initialDate: _parseInitialDate(state.uri.queryParameters['date']),
              ),
            ),
            type: SharedAxisTransitionType.scaled,
          ),
        ),
        GoRoute(
          path: calendarStats,
          name: 'calendarStats',
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: BgmScope(
              track: BgmTrack.calendar,
              child: CalendarStatsScreen(
                initialDate: _parseInitialDate(state.uri.queryParameters['date']),
              ),
            ),
            type: SharedAxisTransitionType.scaled,
          ),
        ),
        GoRoute(
          path: dailyDetail,
          name: 'calendarDailyDetail',
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: BgmScope(
              track: BgmTrack.calendar,
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
