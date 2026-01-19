import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/edge_ai/models/user_edge_state.dart';
import 'package:sparkle/core/edge_ai/services/edge_state_monitor.dart';
import 'package:sparkle/core/models/intervention.dart';
import 'package:sparkle/core/offline/offline_providers.dart';
import 'package:sparkle/core/offline/sync_engine.dart';
import 'package:sparkle/core/analytics/services/local_feature_service.dart';
import 'package:sparkle/core/services/intervention_event_service.dart';
import 'package:sparkle/core/services/intervention_gate_service.dart';
import 'package:sparkle/core/services/intervention_overlay_manager.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/passive_signal_service.dart';
import 'package:sparkle/core/services/websocket_service.dart';

class InterventionHandlerService {
  InterventionHandlerService({
    required PassiveSignalService signalService,
    required EdgeStateMonitor monitor,
    required InterventionGateService gate,
    required InterventionOverlayManager overlayManager,
    required InterventionEventService events,
    required WebSocketService webSocketService,
    required SyncEngine syncEngine,
    required NotificationService notifications,
    required LocalFeatureService localFeatures,
  })  : _signalService = signalService,
        _monitor = monitor,
        _gate = gate,
        _overlayManager = overlayManager,
        _events = events,
        _webSocketService = webSocketService,
        _syncEngine = syncEngine,
        _notifications = notifications,
        _localFeatures = localFeatures;

  static const _backgroundTriggerThreshold = Duration(seconds: 20);

  final PassiveSignalService _signalService;
  final EdgeStateMonitor _monitor;
  final InterventionGateService _gate;
  final InterventionOverlayManager _overlayManager;
  final InterventionEventService _events;
  final WebSocketService _webSocketService;
  final SyncEngine _syncEngine;
  final NotificationService _notifications;
  final LocalFeatureService _localFeatures;

  StreamSubscription<PassiveSignal>? _subscription;
  StreamSubscription<dynamic>? _wsSubscription;
  DateTime? _backgroundAt;
  String? _currentInterventionId;

  void start() {
    _monitor.start();
    _subscription?.cancel();
    _subscription = _signalService.signals.listen(_handleSignal);
    _wsSubscription?.cancel();
    _wsSubscription = _webSocketService.stream.listen(_handleSocketMessage);
    _localFeatures.startInterventionTriggers(
      onTrigger: (trigger, context) {
        unawaited(_attemptIntervention(trigger, context: context));
      },
    );
  }

  void stop() {
    _subscription?.cancel();
    _wsSubscription?.cancel();
    _monitor.stop();
  }

  void debugTrigger() {
    final fallback = buildLocalFallback(
      title: '需要来点休息吗?',
      body: '给自己一个短暂的暂停,再继续也可以。',
    );
    _currentInterventionId = fallback.interventionId;
    _overlayManager.show(fallback, onAction: _handleAction);
  }

  void _handleSignal(PassiveSignal signal) {
    _enqueuePassiveSignal(signal);
    switch (signal.type) {
      case PassiveSignalType.appBackground:
        _backgroundAt = signal.timestamp;
      case PassiveSignalType.appForeground:
        final backgroundDuration = _backgroundAt == null
            ? Duration.zero
            : signal.timestamp.difference(_backgroundAt!);
        _backgroundAt = null;
        if (backgroundDuration >= _backgroundTriggerThreshold) {
          unawaited(_attemptIntervention('resume_after_background'));
        }
      case PassiveSignalType.idle:
        unawaited(_attemptIntervention('idle_trigger'));
      case PassiveSignalType.userInteraction:
      case PassiveSignalType.sessionStart:
      case PassiveSignalType.sessionEnd:
        break;
    }
  }

  void _enqueuePassiveSignal(PassiveSignal signal) {
    _syncEngine.enqueue(
      topic: 'intervention_passive_signals',
      opType: 'record',
      payload: {
        'signal_type': signal.type.name,
        'context': signal.data,
        'timestamp': signal.timestamp.toIso8601String(),
      },
    );
  }

  Future<void> _attemptIntervention(
    String trigger, {
    Map<String, dynamic>? context,
  }) async {
    if (_overlayManager.isShowing) {
      _events.record(
        InterventionEvent(
          type: InterventionEventType.gateDenied,
          data: {
            'reason': 'already_showing',
            'trigger': trigger,
          },
        ),
      );
      return;
    }
    final state = _monitor.latestState;
    if (state == null) return;
    final scene = SceneContext.fromNavigator();
    final decision = await _gate.evaluate(state: state, sceneContext: scene);

    if (!decision.allow) {
      _events.record(
        InterventionEvent(
          type: InterventionEventType.gateDenied,
          data: {
            'reason': decision.reason,
            'trigger': trigger,
            'route': scene.routeName,
            'edge_state': _edgeSnapshot(state),
          },
        ),
      );
      return;
    }

    await _enqueueRequest(state, trigger, decision, context: context);
    await _gate.markInterventionShown();

    debugPrint(
      '[InterventionHandler] allow trigger=$trigger focus=${state.focusScore.toStringAsFixed(2)}',
    );
  }

  Future<void> _enqueueRequest(
    UserEdgeState state,
    String trigger,
    GateDecision decision, {
    Map<String, dynamic>? context,
  }) async {
    await _syncEngine.enqueue(
      topic: 'intervention_requests',
      opType: 'create',
      payload: {
        'type': trigger,
        'urgency': _mapUrgency(state),
        'context': {
          'trigger': trigger,
          if (context != null) ...context,
        },
        'edge_state': _edgeSnapshot(state),
        'gate_decision': {
          'allow': decision.allow,
          'reason': decision.reason,
        },
      },
    );

    if (!_webSocketService.isConnected) {
      final fallback = buildLocalFallback(
        title: '需要来点休息吗?',
        body: '系统离线中,先给你一个本地提醒。',
      );
      _currentInterventionId = fallback.interventionId;
      _overlayManager.show(fallback, onAction: _handleAction);
      await _notifications.showSmartPush(
        title: 'Sparkle 提醒',
        body: fallback.content.renderedMessage,
        payload: {'intervention_id': fallback.interventionId},
      );
    }
  }

  Map<String, dynamic> _edgeSnapshot(UserEdgeState state) => {
      'focus_score': state.focusScore,
      'switching_rate': state.switchingRate,
      'is_foreground': state.isForeground,
      'session_seconds': state.sessionDuration.inSeconds,
      'last_interaction_s': state.debug['last_interaction_s'],
    };

  double _mapUrgency(UserEdgeState state) {
    final score = 1 - state.focusScore;
    return score.clamp(0.1, 0.9);
  }

  void _handleSocketMessage(dynamic message) {
    if (message is Map<String, dynamic>) {
      final type = message['type'];
      if (type == 'intervention_push') {
        final intervention = InterventionPushMessage.fromJson(message);
        if (intervention.isExpired) return;
        _currentInterventionId = intervention.interventionId;
        _overlayManager.show(intervention, onAction: _handleAction);
      }
    }
  }

  void _handleAction(String actionId) {
    final current = _overlayManager.isShowing;
    final interventionId = _currentInterventionId;
    final feedbackType = _mapFeedbackType(actionId);
    _events.record(
      InterventionEvent(
        type: InterventionEventType.overlayAction,
        data: {'action': actionId, 'has_overlay': current},
      ),
    );
    _syncEngine.enqueue(
      topic: 'intervention_feedback',
      opType: 'record',
      payload: {
        'intervention_id': interventionId,
        'feedback_type': feedbackType,
        'action_taken': actionId,
        'timestamp': DateTime.now().toIso8601String(),
      },
    );
    _currentInterventionId = null;
  }

  String _mapFeedbackType(String actionId) {
    switch (actionId) {
      case 'start_now':
      case 'primary':
        return 'accept';
      case 'snooze':
        return 'snooze';
      case 'dismiss':
      case 'dismissed':
      case 'secondary':
        return 'reject';
      default:
        return 'ignore';
    }
  }

  void dispose() {
    stop();
  }
}

final interventionHandlerServiceProvider =
    Provider<InterventionHandlerService>((ref) {
  final signalService = ref.watch(passiveSignalServiceProvider);
  final monitor = ref.watch(edgeStateMonitorProvider);
  final gate = ref.watch(interventionGateServiceProvider);
  final overlayManager = ref.watch(interventionOverlayManagerProvider);
  final events = ref.watch(interventionEventServiceProvider);
  final wsService = ref.watch(webSocketServiceProvider);
  final syncEngine = ref.watch(syncEngineProvider);
  final notifications = ref.watch(notificationServiceProvider);
  final localFeatures = ref.watch(localFeatureServiceProvider);

  final service = InterventionHandlerService(
    signalService: signalService,
    monitor: monitor,
    gate: gate,
    overlayManager: overlayManager,
    events: events,
    webSocketService: wsService,
    syncEngine: syncEngine,
    notifications: notifications,
    localFeatures: localFeatures,
  );

  service.start();
  ref.onDispose(service.dispose);
  return service;
});
