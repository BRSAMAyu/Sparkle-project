import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/edge_ai/models/user_edge_state.dart';
import 'package:sparkle/core/services/notification_service.dart';

class GateDecision {
  final bool allow;
  final String reason;
  final DateTime decidedAt;

  GateDecision({
    required this.allow,
    required this.reason,
    DateTime? decidedAt,
  }) : decidedAt = decidedAt ?? DateTime.now();
}

class SceneContext {
  final String? routeName;
  final bool isUserTyping;
  final bool isFullScreen;

  SceneContext({
    required this.routeName,
    required this.isUserTyping,
    required this.isFullScreen,
  });

  bool get isWhitelisted {
    if (routeName == null) return true;
    return routeName!.contains('/chat') || routeName!.contains('/task');
  }

  static SceneContext fromNavigator() {
    final context = navigatorKey.currentContext;
    String? routeName;
    if (context != null) {
      try {
        routeName =
            GoRouter.of(context).routeInformationProvider.value.location;
      } catch (_) {
        routeName = ModalRoute.of(context)?.settings.name;
      }
    }

    final focus = FocusManager.instance.primaryFocus;
    final isUserTyping = focus?.context?.widget is EditableText;

    return SceneContext(
      routeName: routeName,
      isUserTyping: isUserTyping,
      isFullScreen: false,
    );
  }
}

class InterventionGateService {
  InterventionGateService({
    Duration cooldown = const Duration(minutes: 3),
    int dailyCap = 3,
  })  : _cooldown = cooldown,
        _dailyCap = dailyCap;

  final Duration _cooldown;
  final int _dailyCap;

  DateTime? _lastShownAt;
  DateTime _dailyCountDate = DateTime.now();
  int _dailyCount = 0;

  GateDecision evaluate({
    required UserEdgeState state,
    required SceneContext sceneContext,
  }) {
    _resetDailyCountIfNeeded();

    if (!sceneContext.isWhitelisted) {
      return GateDecision(allow: false, reason: 'scene_not_allowed');
    }

    if (sceneContext.isUserTyping && state.focusScore >= 0.7) {
      return GateDecision(allow: false, reason: 'in_focus');
    }

    if (_dailyCount >= _dailyCap) {
      return GateDecision(allow: false, reason: 'daily_cap');
    }

    if (_lastShownAt != null &&
        DateTime.now().difference(_lastShownAt!) < _cooldown) {
      return GateDecision(allow: false, reason: 'cooldown');
    }

    return GateDecision(allow: true, reason: 'allow');
  }

  void markInterventionShown() {
    _resetDailyCountIfNeeded();
    _dailyCount += 1;
    _lastShownAt = DateTime.now();
  }

  void _resetDailyCountIfNeeded() {
    final now = DateTime.now();
    if (now.day != _dailyCountDate.day ||
        now.month != _dailyCountDate.month ||
        now.year != _dailyCountDate.year) {
      _dailyCountDate = now;
      _dailyCount = 0;
    }
  }
}

final interventionGateServiceProvider =
    Provider<InterventionGateService>((ref) {
  return InterventionGateService();
});
