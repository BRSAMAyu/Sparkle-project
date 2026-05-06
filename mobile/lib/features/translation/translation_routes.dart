import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/features/translation/presentation/screens/translation_history_screen.dart';

class TranslationRoutes {
  static const String history = '/translations/history';

  static List<RouteBase> get routes => [
        GoRoute(
          path: history,
          name: 'translationHistory',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: const TranslationHistoryScreen(),
          ),
        ),
      ];
}
