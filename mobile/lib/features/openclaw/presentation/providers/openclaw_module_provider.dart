import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/services/openclaw_automation_service.dart';
import 'package:sparkle/core/services/openclaw_connection_service.dart';

enum OpenClawModulePhase {
  setup,
  loading,
  ready,
  attention,
}

class OpenClawModuleState {
  const OpenClawModuleState({
    required this.phase,
    required this.isGatewayReachable,
    required this.isExecutionReady,
    required this.queuedRequestCount,
    required this.automationCount,
    required this.setupGuideUrl,
    this.errorMessage,
  });

  factory OpenClawModuleState.fromServices({
    required OpenClawConnectionService connection,
    required OpenClawAutomationService automation,
  }) {
    final isLoading =
        connection.info.status == OpenClawConnectionStatus.connecting ||
            automation.isLoading;
    final hasSetupSignal = connection.config.isConfigured ||
        connection.queuedRequestCount > 0 ||
        connection.hasExecutionPermissionIssue ||
        connection.hasExecutionEndpointIssue ||
        automation.error != null;
    final phase = isLoading
        ? OpenClawModulePhase.loading
        : connection.isConnected
            ? OpenClawModulePhase.ready
            : hasSetupSignal
                ? OpenClawModulePhase.attention
                : OpenClawModulePhase.setup;

    return OpenClawModuleState(
      phase: phase,
      isGatewayReachable: connection.isGatewayReachable,
      isExecutionReady: connection.isConnected,
      queuedRequestCount: connection.queuedRequestCount,
      automationCount: automation.schedules.length,
      errorMessage: automation.error ?? connection.info.errorMessage,
      setupGuideUrl: Uri.parse(
        'https://github.com/BRSAMAyu/Sparkle-project/blob/main/docs/openclaw/OPENCLAW_CONNECTION_GUIDE.md',
      ),
    );
  }

  final OpenClawModulePhase phase;
  final bool isGatewayReachable;
  final bool isExecutionReady;
  final int queuedRequestCount;
  final int automationCount;
  final String? errorMessage;
  final Uri setupGuideUrl;

  bool get needsSetup => phase == OpenClawModulePhase.setup;
  bool get isLoading => phase == OpenClawModulePhase.loading;
  bool get needsAttention => phase == OpenClawModulePhase.attention;
}

final openClawModuleProvider = Provider<OpenClawModuleState>((ref) {
  final connection = ref.watch(openClawConnectionProvider);
  final automation = ref.watch(openClawAutomationProvider);
  return OpenClawModuleState.fromServices(
    connection: connection,
    automation: automation,
  );
});
