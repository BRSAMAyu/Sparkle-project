import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/edge_ai/models/user_edge_state.dart';
import 'package:sparkle/core/edge_ai/services/edge_state_monitor.dart';
import 'package:sparkle/core/services/intervention_event_service.dart';
import 'package:sparkle/core/services/intervention_gate_service.dart';
import 'package:sparkle/core/services/intervention_overlay_manager.dart';
import 'package:sparkle/core/services/passive_signal_service.dart';
import 'package:sparkle/core/widgets/intervention_overlay.dart';

class InterventionHandlerService {
  InterventionHandlerService({
    required PassiveSignalService signalService,
    required EdgeStateMonitor monitor,
    required InterventionGateService gate,
    required InterventionOverlayManager overlayManager,
    required InterventionEventService events,
  })  : _signalService = signalService,
        _monitor = monitor,
        _gate = gate,
        _overlayManager = overlayManager,
        _events = events;

  static const _backgroundTriggerThreshold = Duration(seconds: 20);

  final PassiveSignalService _signalService;
  final EdgeStateMonitor _monitor;
  final InterventionGateService _gate;
  final InterventionOverlayManager _overlayManager;
  final InterventionEventService _events;

  StreamSubscription<PassiveSignal>? _subscription;
  DateTime? _backgroundAt;

  void start() {
    _monitor.start();
    _subscription?.cancel();
    _subscription = _signalService.signals.listen(_handleSignal);
  }

  void stop() {
    _subscription?.cancel();
    _monitor.stop();
  }

  void debugTrigger() {
    unawaited(_attemptIntervention('debug_trigger'));
  }

  void _handleSignal(PassiveSignal signal) {
    switch (signal.type) {
      case PassiveSignalType.appBackground:
        _backgroundAt = signal.timestamp;
        break;
      case PassiveSignalType.appForeground:
        final backgroundDuration = _backgroundAt == null
            ? Duration.zero
            : signal.timestamp.difference(_backgroundAt!);
        _backgroundAt = null;
        if (backgroundDuration >= _backgroundTriggerThreshold) {
          unawaited(_attemptIntervention('resume_after_background'));
        }
        break;
      case PassiveSignalType.idle:
        unawaited(_attemptIntervention('idle_trigger'));
        break;
      case PassiveSignalType.userInteraction:
      case PassiveSignalType.sessionStart:
      case PassiveSignalType.sessionEnd:
        break;
    }
  }

  Future<void> _attemptIntervention(String trigger) async {
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

    final payload = _buildPayload(state, trigger);
    _overlayManager.show(payload);
    await _gate.markInterventionShown();

    debugPrint(
      '[InterventionHandler] allow trigger=$trigger focus=${state.focusScore.toStringAsFixed(2)}',
    );
  }

  InterventionOverlayPayload _buildPayload(
    UserEdgeState state,
    String trigger,
  ) {
    final title = trigger == 'idle_trigger'
        ? 'Quick reset?'
        : 'Welcome back';
    final body = trigger == 'idle_trigger'
        ? 'Take a 60-second pause to stay sharp.'
        : 'Pick up where you left off with a focused sprint.';

    return InterventionOverlayPayload(
      title: title,
      body: body,
      primaryActionText: 'Start',
      secondaryActionText: 'Later',
    );
  }

  Map<String, dynamic> _edgeSnapshot(UserEdgeState state) {
    return {
      'focus_score': state.focusScore,
      'switching_rate': state.switchingRate,
      'is_foreground': state.isForeground,
      'session_seconds': state.sessionDuration.inSeconds,
      'last_interaction_s': state.debug['last_interaction_s'],
    };
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

  final service = InterventionHandlerService(
    signalService: signalService,
    monitor: monitor,
    gate: gate,
    overlayManager: overlayManager,
    events: events,
  );

  service.start();
  ref.onDispose(service.dispose);
  return service;
});
