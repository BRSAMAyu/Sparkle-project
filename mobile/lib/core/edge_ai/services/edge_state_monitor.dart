import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/edge_ai/models/edge_state_schema.dart';
import 'package:sparkle/core/edge_ai/models/user_edge_state.dart';
import 'package:sparkle/core/edge_ai/services/edge_inference_service.dart';
import 'package:sparkle/core/services/passive_signal_service.dart';

class EdgeStateMonitor {
  EdgeStateMonitor(this._signalService, this._edgeInference);

  static const _switchingWindow = Duration(minutes: 2);
  static const _recentInteractionWindow = Duration(seconds: 10);

  final PassiveSignalService _signalService;
  final EdgeInferenceService _edgeInference;
  final StreamController<UserEdgeState> _stateController =
      StreamController<UserEdgeState>.broadcast();

  StreamSubscription<PassiveSignal>? _subscription;
  Timer? _analysisTimer;
  final List<DateTime> _switchEvents = [];

  bool _isForeground = true;
  DateTime? _sessionStartAt;
  DateTime? _lastInteractionAt;
  UserEdgeState? _latest;

  Stream<UserEdgeState> get states => _stateController.stream;
  UserEdgeState? get latestState => _latest;

  void start() {
    _signalService.start();
    _subscription = _signalService.signals.listen(_handleSignal);
    _analysisTimer?.cancel();
    _analysisTimer = Timer.periodic(
      const Duration(minutes: 5),
      (_) => _runInference(),
    );
  }

  void stop() {
    _subscription?.cancel();
    _signalService.stop();
    _analysisTimer?.cancel();
  }

  void _handleSignal(PassiveSignal signal) {
    switch (signal.type) {
      case PassiveSignalType.appForeground:
        _isForeground = true;
        _sessionStartAt ??= signal.timestamp;
        _switchEvents.add(signal.timestamp);
        break;
      case PassiveSignalType.appBackground:
        _isForeground = false;
        _switchEvents.add(signal.timestamp);
        break;
      case PassiveSignalType.userInteraction:
        _lastInteractionAt = signal.timestamp;
        break;
      case PassiveSignalType.idle:
        break;
      case PassiveSignalType.sessionStart:
        _sessionStartAt ??= signal.timestamp;
        break;
      case PassiveSignalType.sessionEnd:
        _sessionStartAt = null;
        break;
    }

    _emitState(signal.timestamp);
  }

  void _emitState(DateTime now) {
    _switchEvents.removeWhere(
      (event) => now.difference(event) > _switchingWindow,
    );

    final sessionDuration = _sessionStartAt == null
        ? Duration.zero
        : now.difference(_sessionStartAt!);

    final lastInteractionGap = _lastInteractionAt == null
        ? Duration(days: 1)
        : now.difference(_lastInteractionAt!);

    final focusScore = _calculateFocusScore(lastInteractionGap);
    final switchingRate = (_switchEvents.length / 5).clamp(0.0, 1.0);

    _latest = UserEdgeState(
      isForeground: _isForeground,
      sessionDuration: sessionDuration,
      focusScore: focusScore,
      switchingRate: switchingRate,
      updatedAt: now,
      source: EdgeStateSource.passiveSignals,
      debug: {
        'last_interaction_s': lastInteractionGap.inSeconds,
        'switch_events': _switchEvents.length,
      },
    );

    _stateController.add(_latest!);
  }

  Future<void> _runInference() async {
    try {
      final edgeState = await _edgeInference.runAnalysis();
      if (edgeState == null || _latest == null) return;
      final updated = _latest!.copyWith(
        debug: {
          ..._latest!.debug,
          'edge_inference': _serializeEdge(edgeState),
        },
      );
      _latest = updated;
      _stateController.add(updated);
    } catch (_) {}
  }

  Map<String, dynamic> _serializeEdge(EdgeState state) {
    return {
      'attention_score': state.attentionScore,
      'fatigue_score': state.fatigueScore,
      'stress_score': state.stressScore,
      'should_interrupt': state.shouldInterrupt,
      'nudge_tone': state.nudgeTone,
      'window_minutes': state.bestWindow.inMinutes,
      'timestamp': state.timestamp,
    };
  }

  double _calculateFocusScore(Duration gap) {
    if (!_isForeground) return 0.0;
    if (gap <= _recentInteractionWindow) return 0.9;
    if (gap > const Duration(seconds: 20)) return 0.2;
    return 0.5;
  }

  void dispose() {
    stop();
    _stateController.close();
  }
}

final edgeStateMonitorProvider = Provider<EdgeStateMonitor>((ref) {
  final signalService = ref.watch(passiveSignalServiceProvider);
  final edgeInference = ref.watch(edgeInferenceServiceProvider);
  final monitor = EdgeStateMonitor(signalService, edgeInference);
  ref.onDispose(monitor.dispose);
  return monitor;
});
