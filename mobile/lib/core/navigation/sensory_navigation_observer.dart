import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/client_observability_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

/// Navigator observer that keeps route changes aligned with the shared
/// sensory language without adding noise on first paint.
class SensoryNavigationObserver extends NavigatorObserver {
  bool _hasSeenInitialRoute = false;
  DateTime? _lastFeedbackAt;

  void _emitFeedback(SensoryFeedbackEvent event) {
    if (!_hasSeenInitialRoute) {
      _hasSeenInitialRoute = true;
      return;
    }
    final now = DateTime.now();
    if (_lastFeedbackAt != null &&
        now.difference(_lastFeedbackAt!) < const Duration(milliseconds: 160)) {
      return;
    }
    _lastFeedbackAt = now;
    unawaited(
      BgmService.duckForNavigation(
        isBackNavigation: event == SensoryFeedbackEvent.selection,
      ),
    );
    unawaited(SensoryFeedbackService.emit(event));
  }

  void _trackScreen(Route<dynamic> route) {
    final routeName = route.settings.name ??
        route.settings.arguments?.toString() ??
        route.runtimeType.toString();
    unawaited(ClientObservabilityService.instance.trackScreenView(routeName));
  }

  @override
  void didPush(Route<dynamic> route, Route<dynamic>? previousRoute) {
    super.didPush(route, previousRoute);
    _emitFeedback(SensoryFeedbackEvent.navigation);
    _trackScreen(route);
  }

  @override
  void didPop(Route<dynamic> route, Route<dynamic>? previousRoute) {
    super.didPop(route, previousRoute);
    _emitFeedback(SensoryFeedbackEvent.selection);
    if (previousRoute != null) {
      _trackScreen(previousRoute);
    }
  }

  @override
  void didReplace({Route<dynamic>? newRoute, Route<dynamic>? oldRoute}) {
    super.didReplace(newRoute: newRoute, oldRoute: oldRoute);
    _emitFeedback(SensoryFeedbackEvent.navigation);
    if (newRoute != null) {
      _trackScreen(newRoute);
    }
  }
}
