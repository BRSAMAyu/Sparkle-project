import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/edge_ai/models/user_edge_state.dart';
import 'package:sparkle/core/services/intervention_gate_service.dart';

UserEdgeState _state({
  required bool isForeground,
  required double focusScore,
}) {
  return UserEdgeState(
    isForeground: isForeground,
    sessionDuration: const Duration(seconds: 30),
    focusScore: focusScore,
    switchingRate: 0.2,
    updatedAt: DateTime.now(),
    source: EdgeStateSource.passiveSignals,
  );
}

void main() {
  test('Gate denies when scene is not whitelisted', () {
    final gate = InterventionGateService(cooldown: Duration.zero);
    final decision = gate.evaluate(
      state: _state(isForeground: true, focusScore: 0.3),
      sceneContext: SceneContext(
        routeName: '/home',
        isUserTyping: false,
        isFullScreen: false,
      ),
    );

    expect(decision.allow, isFalse);
    expect(decision.reason, 'scene_not_allowed');
  });

  test('Gate denies when typing and focus is high', () {
    final gate = InterventionGateService(cooldown: Duration.zero);
    final decision = gate.evaluate(
      state: _state(isForeground: true, focusScore: 0.9),
      sceneContext: SceneContext(
        routeName: '/chat',
        isUserTyping: true,
        isFullScreen: false,
      ),
    );

    expect(decision.allow, isFalse);
    expect(decision.reason, 'in_focus');
  });

  test('Gate enforces daily cap', () {
    final gate = InterventionGateService(cooldown: Duration.zero, dailyCap: 1);
    gate.markInterventionShown();
    final decision = gate.evaluate(
      state: _state(isForeground: true, focusScore: 0.2),
      sceneContext: SceneContext(
        routeName: '/chat',
        isUserTyping: false,
        isFullScreen: false,
      ),
    );

    expect(decision.allow, isFalse);
    expect(decision.reason, 'daily_cap');
  });

  test('Gate allows when idle and scene is whitelisted', () {
    final gate = InterventionGateService(cooldown: Duration.zero);
    final decision = gate.evaluate(
      state: _state(isForeground: true, focusScore: 0.2),
      sceneContext: SceneContext(
        routeName: '/chat',
        isUserTyping: false,
        isFullScreen: false,
      ),
    );

    expect(decision.allow, isTrue);
  });
}
