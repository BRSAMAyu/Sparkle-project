import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:sparkle/core/services/client_observability_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

/// Navigator observer that keeps route changes aligned with the shared
/// sensory language without adding noise on first paint.
class SensoryNavigationObserver extends NavigatorObserver {
  bool _hasSeenInitialRoute = false;

  void _emitNavigationFeedback() {
    if (!_hasSeenInitialRoute) {
      _hasSeenInitialRoute = true;
      return;
    }
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.navigation));
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
    _emitNavigationFeedback();
    _trackScreen(route);
  }

  @override
  void didPop(Route<dynamic> route, Route<dynamic>? previousRoute) {
    super.didPop(route, previousRoute);
    _emitNavigationFeedback();
    if (previousRoute != null) {
      _trackScreen(previousRoute);
    }
  }

  @override
  void didReplace({Route<dynamic>? newRoute, Route<dynamic>? oldRoute}) {
    super.didReplace(newRoute: newRoute, oldRoute: oldRoute);
    _emitNavigationFeedback();
    if (newRoute != null) {
      _trackScreen(newRoute);
    }
  }
}
