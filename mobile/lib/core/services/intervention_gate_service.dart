import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/edge_ai/models/user_edge_state.dart';
import 'package:sparkle/core/services/notification_service.dart';

class GateDecision {

  GateDecision({
    required this.allow,
    required this.reason,
    DateTime? decidedAt,
  }) : decidedAt = decidedAt ?? DateTime.now();
  final bool allow;
  final String reason;
  final DateTime decidedAt;
}

class SceneContext {

  SceneContext({
    required this.routeName,
    required this.isUserTyping,
    required this.isFullScreen,
  });
  final String? routeName;
  final bool isUserTyping;
  final bool isFullScreen;

  bool get isWhitelisted {
    if (routeName == null) return true;
    return routeName!.contains('/chat') || routeName!.contains('/task');
  }

  static SceneContext fromNavigator() {
    final context = navigatorKey.currentContext;
    String? routeName;
    if (context != null) {
      try {
        routeName = GoRouter.of(context)
            .routeInformationProvider
            .value
            .uri
            .toString();
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
  bool _loaded = false;

  static const _prefsLastShownKey = 'intervention_last_shown_at';
  static const _prefsDailyCountKey = 'intervention_daily_count';
  static const _prefsDailyDateKey = 'intervention_daily_date';

  Future<GateDecision> evaluate({
    required UserEdgeState state,
    required SceneContext sceneContext,
  }) async {
    await _ensureLoaded();
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

  Future<void> markInterventionShown() async {
    await _ensureLoaded();
    _resetDailyCountIfNeeded();
    _dailyCount += 1;
    _lastShownAt = DateTime.now();
    await _persist();
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

  Future<void> _ensureLoaded() async {
    if (_loaded) return;
    final prefs = await SharedPreferences.getInstance();
    final lastShownMillis = prefs.getInt(_prefsLastShownKey);
    final storedDate = prefs.getString(_prefsDailyDateKey);
    _lastShownAt = lastShownMillis == null || lastShownMillis == 0
        ? null
        : DateTime.fromMillisecondsSinceEpoch(lastShownMillis);
    _dailyCount = prefs.getInt(_prefsDailyCountKey) ?? 0;
    _dailyCountDate = storedDate == null
        ? DateTime.now()
        : DateTime.tryParse(storedDate) ?? DateTime.now();
    _loaded = true;
  }

  Future<void> _persist() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(
      _prefsLastShownKey,
      _lastShownAt?.millisecondsSinceEpoch ?? 0,
    );
    await prefs.setInt(_prefsDailyCountKey, _dailyCount);
    await prefs.setString(_prefsDailyDateKey, _formatDate(_dailyCountDate));
  }

  String _formatDate(DateTime date) {
    final month = date.month.toString().padLeft(2, '0');
    final day = date.day.toString().padLeft(2, '0');
    return '${date.year}-$month-$day';
  }
}

final interventionGateServiceProvider =
    Provider<InterventionGateService>((ref) => InterventionGateService());
