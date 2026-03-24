import 'dart:ui' show AppExitResponse, ViewFocusEvent;

import 'package:flutter/services.dart' show PredictiveBackEvent;
import 'package:flutter/widgets.dart';

class _LifecycleControllerEntry {
  _LifecycleControllerEntry(this.controller, this.onResume);

  final AnimationController controller;
  final VoidCallback? onResume;
}

/// Pause/resume registered animation controllers on app lifecycle changes.
mixin AnimationLifecycleMixin<T extends StatefulWidget> on State<T>
    implements WidgetsBindingObserver {
  final List<_LifecycleControllerEntry> _controllers = [];
  final Map<AnimationController, bool> _wasAnimating = {};

  void registerController(
    AnimationController controller, {
    VoidCallback? onResume,
  }) {
    _controllers.add(_LifecycleControllerEntry(controller, onResume));
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _controllers.clear();
    _wasAnimating.clear();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    switch (state) {
      case AppLifecycleState.resumed:
        _resumeControllers();
      case AppLifecycleState.inactive:
      case AppLifecycleState.paused:
      case AppLifecycleState.detached:
      case AppLifecycleState.hidden:
        _pauseControllers();
    }
  }

  @override
  Future<bool> didPopRoute() => Future<bool>.value(false);

  @override
  bool handleStartBackGesture(PredictiveBackEvent backEvent) => false;

  @override
  void handleUpdateBackGestureProgress(PredictiveBackEvent backEvent) {}

  @override
  void handleCommitBackGesture() {}

  @override
  void handleCancelBackGesture() {}

  @override
  void handleStatusBarTap() {}

  @override
  Future<bool> didPushRoute(String route) => Future<bool>.value(false);

  @override
  Future<bool> didPushRouteInformation(RouteInformation routeInformation) =>
      Future<bool>.value(false);

  @override
  void didChangeMetrics() {}

  @override
  void didChangeTextScaleFactor() {}

  @override
  void didChangePlatformBrightness() {}

  @override
  void didChangeLocales(List<Locale>? locales) {}

  @override
  void didChangeViewFocus(ViewFocusEvent event) {}

  @override
  Future<AppExitResponse> didRequestAppExit() async => AppExitResponse.exit;

  @override
  void didHaveMemoryPressure() {}

  @override
  void didChangeAccessibilityFeatures() {}

  void _pauseControllers() {
    for (final entry in _controllers) {
      _wasAnimating[entry.controller] = entry.controller.isAnimating;
      if (entry.controller.isAnimating) {
        entry.controller.stop(canceled: false);
      }
    }
  }

  void _resumeControllers() {
    for (final entry in _controllers) {
      final wasAnimating = _wasAnimating[entry.controller] ?? false;
      if (!wasAnimating || entry.controller.isAnimating) {
        continue;
      }
      if (entry.onResume != null) {
        entry.onResume!();
      } else {
        entry.controller.repeat();
      }
    }
    _wasAnimating.clear();
  }
}
