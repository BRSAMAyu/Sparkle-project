import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/services/openclaw_automation_service.dart';
import 'package:sparkle/core/services/openclaw_connection_service.dart';
import 'package:sparkle/features/openclaw/presentation/providers/openclaw_module_provider.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test('OpenClaw module starts with setup state and setup guide link', () {
    final connection = OpenClawConnectionService();
    final automation = _automationService();

    final state = OpenClawModuleState.fromServices(
      connection: connection,
      automation: automation,
    );

    expect(state.phase, OpenClawModulePhase.setup);
    expect(state.needsSetup, isTrue);
    expect(state.isExecutionReady, isFalse);
    expect(
      state.setupGuideUrl.toString(),
      contains('docs/openclaw/OPENCLAW_CONNECTION_GUIDE.md'),
    );
  });

  test('OpenClaw module reports ready when execution is connected', () {
    final connection = OpenClawConnectionService()
      ..markExecutionAvailable(message: 'ready');
    final automation = _automationService();

    final state = OpenClawModuleState.fromServices(
      connection: connection,
      automation: automation,
    );

    expect(state.phase, OpenClawModulePhase.ready);
    expect(state.isGatewayReachable, isTrue);
    expect(state.isExecutionReady, isTrue);
  });
}

OpenClawAutomationService _automationService() => OpenClawAutomationService(
      schedulesLoader: () async => const <Map<String, dynamic>>[],
      scheduleCreator: (payload) async => const <String, dynamic>{},
      schedulePauser: (scheduleId) async => const <String, dynamic>{},
      scheduleResumer: (scheduleId) async => const <String, dynamic>{},
      scheduleDeleter: (scheduleId) async {},
      taskBatchHandoff: (taskIds, executionStrategy) async =>
          const <String, dynamic>{},
    );
