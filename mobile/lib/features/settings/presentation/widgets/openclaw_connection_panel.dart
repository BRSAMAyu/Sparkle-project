import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/services/openclaw_connection_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/openclaw/presentation/widgets/openclaw_primitives.dart';
import 'package:sparkle/features/settings/presentation/widgets/openclaw_pairing_scanner_sheet.dart';
import 'package:sparkle/features/task/presentation/execution_copy.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';

class _OpenClawConnectionPreset {
  const _OpenClawConnectionPreset({
    required this.id,
    required this.label,
    required this.description,
    required this.config,
  });

  final String id;
  final String label;
  final String description;
  final OpenClawConnectionConfig config;
}

const _openClawGuestPresets = <_OpenClawConnectionPreset>[
  _OpenClawConnectionPreset(
    id: 'guest_local_main',
    label: '',
    description: '',
    config: OpenClawConnectionConfig(
      gatewayUrl: 'http://127.0.0.1:18789',
    ),
  ),
];

String _presetLabel(String id, BuildContext context) {
  switch (id) {
    case 'guest_local_main':
      return context.l10n.openclawGuestMainLabel;
    default:
      return context.l10n.openclawCustomConfig;
  }
}

String _presetDescription(String id, BuildContext context) {
  switch (id) {
    case 'guest_local_main':
      return context.l10n.openclawGuestMainDesc;
    default:
      return context.l10n.openclawCustomConfigDesc;
  }
}

class OpenClawConnectionPanel extends ConsumerStatefulWidget {
  const OpenClawConnectionPanel({
    super.key,
    this.compact = false,
  });

  final bool compact;

  @override
  ConsumerState<OpenClawConnectionPanel> createState() =>
      _OpenClawConnectionPanelState();
}

class _OpenClawConnectionPanelState
    extends ConsumerState<OpenClawConnectionPanel> {
  late final TextEditingController _gatewayController;
  late final TextEditingController _tokenController;
  late final TextEditingController _deviceTokenController;
  bool _hydrated = false;
  bool _formDirty = false;
  String? _lastHydratedSignature;
  bool _testing = false;
  bool _saving = false;
  bool _retryingQueue = false;
  bool _showSaveHighlight = false;
  String _authMode = 'token';
  String _transport = 'responses_http';
  String _selectedPresetId = 'custom';
  Timer? _pairingTicker;
  Timer? _saveHighlightTimer;

  @override
  void initState() {
    super.initState();
    _gatewayController = TextEditingController();
    _tokenController = TextEditingController();
    _deviceTokenController = TextEditingController();
  }

  @override
  void dispose() {
    _pairingTicker?.cancel();
    _saveHighlightTimer?.cancel();
    _gatewayController.dispose();
    _tokenController.dispose();
    _deviceTokenController.dispose();
    super.dispose();
  }

  String _configSignature(OpenClawConnectionConfig config) => [
        config.normalizedGatewayUrl,
        config.authToken ?? '',
        config.deviceToken ?? '',
        config.transport,
        config.wsUrl ?? '',
        config.pairedAt?.toIso8601String() ?? '',
      ].join('|');

  void _markDirty() {
    if (_formDirty) return;
    setState(() => _formDirty = true);
  }

  void _hydrateFromService(OpenClawConnectionService service) {
    final signature = _configSignature(service.config);
    if (_formDirty || (_hydrated && signature == _lastHydratedSignature)) {
      return;
    }

    final config = service.config;
    _gatewayController.text = config.gatewayUrl;
    _tokenController.text = config.authToken ?? '';
    _deviceTokenController.text = config.deviceToken ?? '';
    _authMode = config.isPaired ? 'device' : 'token';
    _transport = config.transport;
    _selectedPresetId = _matchingPreset(config)?.id ?? 'custom';
    _hydrated = true;
    _lastHydratedSignature = signature;
  }

  void _syncSavedConfig(OpenClawConnectionService service) {
    _formDirty = false;
    _hydrated = true;
    _lastHydratedSignature = _configSignature(service.config);
    _selectedPresetId = _matchingPreset(service.config)?.id ?? 'custom';
  }

  _OpenClawConnectionPreset? _matchingPreset(OpenClawConnectionConfig config) {
    for (final preset in _openClawGuestPresets) {
      if (preset.config.normalizedGatewayUrl == config.normalizedGatewayUrl &&
          (preset.config.authToken ?? '') == (config.authToken ?? '') &&
          preset.config.transport == config.transport &&
          !config.isPaired) {
        return preset;
      }
    }
    return null;
  }

  void _applyPreset(_OpenClawConnectionPreset preset) {
    _gatewayController.text = preset.config.gatewayUrl;
    _tokenController.text = preset.config.authToken ?? '';
    _deviceTokenController.clear();
    setState(() {
      _selectedPresetId = preset.id;
      _authMode = 'token';
      _transport = preset.config.transport;
      _formDirty = true;
    });
  }

  void _applyConfigDraft(
    OpenClawConnectionConfig config, {
    bool markDirty = true,
  }) {
    _gatewayController.text = config.transport == 'gateway_ws' &&
            (config.wsUrl ?? '').trim().isNotEmpty
        ? config.wsUrl!
        : config.gatewayUrl;
    _tokenController.text = config.authToken ?? '';
    _deviceTokenController.text = config.deviceToken ?? '';
    setState(() {
      _selectedPresetId = 'custom';
      _authMode = config.isPaired ? 'device' : 'token';
      _transport = config.transport;
      _formDirty = markDirty;
    });
  }

  Future<void> _saveImportedConfig(
    OpenClawConnectionService service,
    OpenClawConnectionConfig config, {
    String? successLabel,
  }) async {
    setState(() => _saving = true);
    final ok = await service.configure(config);
    if (!mounted) return;
    setState(() => _saving = false);
    _syncSavedConfig(service);
    if (ok) {
      _flashSavedState();
    }
    unawaited(
      SensoryFeedbackService.emit(
        ok ? SensoryFeedbackEvent.success : SensoryFeedbackEvent.warning,
      ),
    );
    _showSnackBar(
      ok
          ? (successLabel ?? context.l10n.openclawPairImportedSaved)
          : (service.info.errorMessage ?? context.l10n.openclawPairImportedVerifyFailed),
      isError: !ok,
    );
  }

  Future<void> _importPairingPayloadFromClipboard(
    OpenClawConnectionService service,
  ) async {
    final clipboard = await Clipboard.getData('text/plain');
    final raw = clipboard?.text?.trim() ?? '';
    final payload = OpenClawConnectionService.parsePairingPayload(raw);
    if (payload == null) {
      _showSnackBar(
        context.l10n.openclawClipboardNoPairingPayload,
        isError: true,
      );
      return;
    }

    final config = payload.toConfig();
    _applyConfigDraft(config);
    await _saveImportedConfig(
      service,
      config,
      successLabel: payload.deviceName == null
          ? context.l10n.openclawImportedFromClipboard
          : context.l10n.openclawConnectedToDevice(payload.deviceName!),
    );
  }

  Future<void> _showPairingImportDialog(
    OpenClawConnectionService service,
  ) async {
    final controller = TextEditingController();
    final raw = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text(context.l10n.openclawImportPairingString),
        content: SizedBox(
          width: 520,
          child: TextField(
            controller: controller,
            maxLines: 8,
            autofocus: true,
            decoration: const InputDecoration(
              labelText: context.l10n.openclawPairingOrQrLabel,
              hintText:
                  context.l10n.openclawPairingPasteHint,
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text(context.l10n.cancel),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(controller.text),
            child: const Text(context.l10n.openclawImportAndSave),
          ),
        ],
      ),
    );
    controller.dispose();
    if (raw == null || raw.trim().isEmpty || !mounted) return;

    final payload = OpenClawConnectionService.parsePairingPayload(raw);
    if (payload == null) {
      _showSnackBar(context.l10n.openclawUnrecognizedContent, isError: true);
      return;
    }

    final config = payload.toConfig();
    _applyConfigDraft(config);
    await _saveImportedConfig(
      service,
      config,
      successLabel: payload.deviceName == null
          ? context.l10n.openclawImportedPairing
          : context.l10n.openclawImportedDevicePairing(payload.deviceName!),
    );
  }

  Future<void> _scanPairingPayload(
    OpenClawConnectionService service,
  ) async {
    final status = await Permission.camera.request();
    if (!mounted) return;
    if (!status.isGranted) {
      _showSnackBar(
        context.l10n.openclawCameraPermissionNeeded,
        isError: true,
      );
      return;
    }

    final raw = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Theme.of(context).colorScheme.surface,
      builder: (context) => const OpenClawPairingScannerSheet(),
    );
    if (!mounted || raw == null || raw.trim().isEmpty) return;

    final payload = OpenClawConnectionService.parsePairingPayload(raw);
    if (payload == null) {
      _showSnackBar(context.l10n.openclawQrNotPairingContent, isError: true);
      return;
    }

    final config = payload.toConfig();
    _applyConfigDraft(config);
    await _saveImportedConfig(
      service,
      config,
      successLabel: payload.deviceName == null
          ? context.l10n.openclawScannedPairingImported
          : context.l10n.openclawScannedConnectedToDevice(payload.deviceName!),
    );
  }

  Future<void> _showRemotePresetDialog({
    required String title,
    required String labelText,
    required String hintText,
    required String helperText,
    required String Function(String rawValue) buildUrl,
    String transport = 'gateway_ws',
  }) async {
    final controller = TextEditingController();
    final rawValue = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: SizedBox(
          width: 420,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                helperText,
                style: DS.bodySmall.copyWith(
                  color: DS.textSecondary,
                  height: 1.45,
                ),
              ),
              const SizedBox(height: DS.spacing12),
              TextField(
                controller: controller,
                autofocus: true,
                decoration: InputDecoration(
                  labelText: labelText,
                  hintText: hintText,
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text(context.l10n.cancel),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(controller.text),
            child: const Text(context.l10n.openclawApplyWizard),
          ),
        ],
      ),
    );
    controller.dispose();
    if (rawValue == null || rawValue.trim().isEmpty) return;

    final gatewayUrl = buildUrl(rawValue.trim());
    _applyConfigDraft(
      OpenClawConnectionConfig(
        gatewayUrl: gatewayUrl,
        transport: transport,
      ),
    );
    _showSnackBar(context.l10n.openclawRemoteTemplateFilled);
  }

  void _flashSavedState() {
    _saveHighlightTimer?.cancel();
    setState(() => _showSaveHighlight = true);
    _saveHighlightTimer = Timer(const Duration(seconds: 2), () {
      if (!mounted) return;
      setState(() => _showSaveHighlight = false);
    });
  }

  void _syncPairingTicker(OpenClawPairingSession? session) {
    if (session == null || session.isExpired) {
      _pairingTicker?.cancel();
      _pairingTicker = null;
      return;
    }
    if (_pairingTicker != null) return;
    _pairingTicker = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      if (ref.read(openClawConnectionProvider).pairingSession?.isExpired ??
          true) {
        _pairingTicker?.cancel();
        _pairingTicker = null;
      }
      setState(() {});
    });
  }

  String _pairingCountdownLabel(OpenClawPairingSession? session) {
    if (session == null) return '';
    final remaining = session.expiresAt.difference(DateTime.now());
    if (remaining.isNegative) return context.l10n.openclawPairingCodeExpired;
    final minutes = remaining.inMinutes;
    final seconds = remaining.inSeconds % 60;
    if (minutes <= 0) {
      return context.l10n.openclawPairingExpiresSeconds(seconds);
    }
    return context.l10n.openclawPairingExpiresMinutes(minutes, seconds.toString().padLeft(2, '0'));
  }

  OpenClawConnectionConfig? _buildConfig() {
    final rawUrl = _gatewayController.text.trim();
    final isHttpLike =
        rawUrl.startsWith('http://') || rawUrl.startsWith('https://');
    final isWsLike = rawUrl.startsWith('ws://') || rawUrl.startsWith('wss://');
    if (rawUrl.isEmpty || (!isHttpLike && !isWsLike)) {
      return null;
    }

    return OpenClawConnectionConfig(
      gatewayUrl: rawUrl,
      authToken: _authMode == 'token' && _tokenController.text.trim().isNotEmpty
          ? _tokenController.text.trim()
          : null,
      deviceToken:
          _authMode == 'device' && _deviceTokenController.text.trim().isNotEmpty
              ? _deviceTokenController.text.trim()
              : null,
      transport: _transport,
      wsUrl: _transport == 'gateway_ws' && isWsLike ? rawUrl : null,
      pairedAt: _authMode == 'device' ? DateTime.now() : null,
    );
  }

  Future<void> _testConnection(OpenClawConnectionService service) async {
    final copy = ExecutionCopy.of(context);
    final config = _buildConfig();
    if (config == null) {
      _showSnackBar(
        context.l10n.openclawInvalidUrlFormat,
        isError: true,
      );
      return;
    }

    setState(() => _testing = true);
    final ok = await service.testConnection(config);
    if (!mounted) return;
    setState(() => _testing = false);
    unawaited(
      SensoryFeedbackService.emit(
        ok ? SensoryFeedbackEvent.success : SensoryFeedbackEvent.error,
      ),
    );
    _showSnackBar(
      ok
          ? copy.connectionSuccess
          : (service.info.errorMessage ?? copy.connectionFailure),
      isError: !ok,
    );
  }

  Future<void> _saveConnection(OpenClawConnectionService service) async {
    final copy = ExecutionCopy.of(context);
    final config = _buildConfig();
    if (config == null) {
      _showSnackBar(context.l10n.openclawValidAddressRequired, isError: true);
      return;
    }

    setState(() => _saving = true);
    final ok = await service.configure(config);
    if (!mounted) return;
    setState(() => _saving = false);
    _syncSavedConfig(service);
    unawaited(
      SensoryFeedbackService.emit(
        ok ? SensoryFeedbackEvent.success : SensoryFeedbackEvent.warning,
      ),
    );
    if (ok && service.queuedRequests.isNotEmpty) {
      unawaited(_retryQueuedRequests(service));
    }
    if (ok) {
      _flashSavedState();
    }
    _showSnackBar(
      ok
          ? copy.configurationSavedAndConnected
          : copy.configurationSavedButUnavailable,
      isError: !ok,
    );
  }

  Future<void> _disconnect(OpenClawConnectionService service) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text(context.l10n.openclawDisconnect),
        content: const Text(context.l10n.openclawDisconnectConfirmBody),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text(context.l10n.cancel),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text(context.l10n.openclawDisconnectAction),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    await service.disconnect();
    if (!mounted) return;
    _gatewayController.clear();
    _tokenController.clear();
    _deviceTokenController.clear();
    setState(() {
      _hydrated = true;
      _formDirty = false;
      _lastHydratedSignature = _configSignature(service.config);
      _authMode = 'token';
      _transport = 'responses_http';
    });
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    _showSnackBar(context.l10n.openclawDisconnected);
  }

  Future<void> _startPairing(OpenClawConnectionService service) async {
    final session = await service.startPairing();
    if (!mounted) return;
    _markDirty();
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    _showSnackBar(context.l10n.openclawPairingCodeGenerated(session.code));
  }

  Future<void> _completePairing(OpenClawConnectionService service) async {
    final token = _deviceTokenController.text.trim();
    if (token.isEmpty) {
      _showSnackBar(context.l10n.openclawDeviceTokenRequired, isError: true);
      return;
    }

    await service.completePairing(token);
    if (!mounted) return;
    setState(() {
      _authMode = 'device';
      _syncSavedConfig(service);
    });
    _showSnackBar(context.l10n.openclawDevicePairingComplete);
  }

  Future<void> _retryQueuedRequests(OpenClawConnectionService service) async {
    if (!service.isConnected) {
      _showSnackBar(
        service.hasExecutionPermissionIssue
            ? context.l10n.openclawNoExecutionPermission
            : service.hasExecutionEndpointIssue
                ? context.l10n.openclawExecutionEndpointUnavailable
                : context.l10n.openclawExecutionEngineNotConnected,
        isError: true,
      );
      return;
    }

    setState(() => _retryingQueue = true);
    final dispatched =
        await ref.read(taskListProvider.notifier).drainQueuedAiHandoffs();
    if (!mounted) return;
    setState(() => _retryingQueue = false);
    if (dispatched > 0) {
      _showSnackBar(context.l10n.openclawQueuedTasksResubmitted(dispatched));
      return;
    }
    _showSnackBar(context.l10n.openclawNoRetryableTasks);
  }

  void _showSnackBar(String message, {bool isError = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      isError
          ? SparkleSnackBar.error(message)
          : SparkleSnackBar.success(message),
    );
  }

  bool _hasExecutionPermissionIssue(String? message) {
    final normalized = (message ?? '').toLowerCase();
    return normalized.contains('operator.write') ||
        normalized.contains('scope') ||
        normalized.contains('权限');
  }

  bool _hasExecutionEndpointIssue(String? message) =>
      (message ?? '').contains('/v1/responses');

  Widget _buildTroubleshootingCard(String message) {
    final permissionIssue = _hasExecutionPermissionIssue(message);
    final endpointIssue = _hasExecutionEndpointIssue(message);
    final title = permissionIssue
        ? context.l10n.openclawGatewayOnlineNoExecPermission
        : endpointIssue
            ? context.l10n.openclawGatewayOnlineExecNotReady
            : context.l10n.openclawNeedExecutionChainCheck;
    final body = permissionIssue
        ? context.l10n.openclawTroubleshootNoPermissionBody
        : endpointIssue
            ? context.l10n.openclawTroubleshootMissingEndpointBody
            : context.l10n.openclawTroubleshootGenericBody;

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(top: DS.spacing10),
      padding: const EdgeInsets.all(DS.spacing12),
      decoration: BoxDecoration(
        color: DS.warning.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: DS.warning.withValues(alpha: 0.18)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: DS.bodyMedium.copyWith(
              color: DS.warning,
              fontWeight: DS.fontWeightBold,
            ),
          ),
          const SizedBox(height: DS.spacing6),
          Text(
            body,
            style: DS.bodySmall.copyWith(
              color: DS.textSecondary,
              height: 1.45,
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final service = ref.watch(openClawConnectionProvider);
    final pairingSession = service.pairingSession;
    _syncPairingTicker(pairingSession);
    _hydrateFromService(service);

    final spacing = widget.compact ? DS.spacing12 : DS.spacing16;
    final copy = ExecutionCopy.of(context);
    final selectedPreset = _openClawGuestPresets
        .where((preset) => preset.id == _selectedPresetId)
        .cast<_OpenClawConnectionPreset?>()
        .firstWhere(
          (preset) => preset != null,
          orElse: () => null,
        );
    final hasPermissionIssue =
        _hasExecutionPermissionIssue(service.info.errorMessage);
    final statusTone = switch (service.info.status) {
      OpenClawConnectionStatus.connected => OpenClawVisualTone.connected,
      OpenClawConnectionStatus.connecting => OpenClawVisualTone.active,
      OpenClawConnectionStatus.error when hasPermissionIssue =>
        OpenClawVisualTone.attention,
      OpenClawConnectionStatus.error => OpenClawVisualTone.offline,
      OpenClawConnectionStatus.disconnected => OpenClawVisualTone.offline,
    };
    final statusTitle = switch (service.info.status) {
      OpenClawConnectionStatus.connected => context.l10n.openclawStatusReadyForTasks,
      OpenClawConnectionStatus.connecting => context.l10n.openclawStatusConfirmingConnection,
      OpenClawConnectionStatus.error when hasPermissionIssue => context.l10n.openclawStatusOnlineNoPermission,
      OpenClawConnectionStatus.error => context.l10n.openclawStatusNotConnected,
      OpenClawConnectionStatus.disconnected => context.l10n.openclawStatusNotConfigured,
    };
    final statusSubtitle = switch (service.info.status) {
      OpenClawConnectionStatus.connected =>
        context.l10n.openclawStatusConnectedSubtitle,
      OpenClawConnectionStatus.connecting => context.l10n.openclawStatusConnectingSubtitle,
      OpenClawConnectionStatus.error when hasPermissionIssue =>
        context.l10n.openclawStatusNoPermissionSubtitle,
      OpenClawConnectionStatus.error =>
        service.info.errorMessage ?? context.l10n.openclawStatusErrorSubtitleFallback,
      OpenClawConnectionStatus.disconnected =>
        context.l10n.openclawStatusDisconnectedSubtitle,
    };

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          OpenClawStatusCapsule(
            title: statusTitle,
            subtitle: statusSubtitle,
            tone: statusTone,
            icon: _showSaveHighlight
                ? Icons.check_circle_rounded
                : Icons.cloud_sync_rounded,
            showToggle: false,
            metrics: [
              if (_formDirty)
                const OpenClawMetricPill(
                  icon: Icons.edit_rounded,
                  label: context.l10n.openclawUnsavedChanges,
                  tone: OpenClawVisualTone.attention,
                  emphasized: true,
                ),
              OpenClawMetricPill(
                icon: Icons.route_rounded,
                label: _transport == 'gateway_ws' ? 'WebSocket' : 'HTTP',
              ),
              OpenClawMetricPill(
                icon: _authMode == 'device'
                    ? Icons.devices_rounded
                    : Icons.key_rounded,
                label: _authMode == 'device' ? context.l10n.openclawDevicePairing : context.l10n.openclawTokenAuth,
                tone: _authMode == 'device'
                    ? OpenClawVisualTone.attention
                    : OpenClawVisualTone.active,
              ),
              if (service.info.latencyMs != null)
                OpenClawMetricPill(
                  icon: Icons.speed_rounded,
                  label: '${service.info.latencyMs}ms',
                  tone: OpenClawVisualTone.connected,
                ),
              if (service.queuedRequests.isNotEmpty)
                OpenClawMetricPill(
                  icon: Icons.schedule_rounded,
                  label: context.l10n.openclawQueuedRequestCount(service.queuedRequestCount),
                  tone: OpenClawVisualTone.offline,
                  emphasized: true,
                ),
            ],
          ),
          if (service.info.status == OpenClawConnectionStatus.error &&
              (service.info.errorMessage ?? '').isNotEmpty)
            _buildTroubleshootingCard(service.info.errorMessage!),
          SizedBox(height: spacing),
          Text(
            context.l10n.openclawQuickConnect,
            style: DS.labelSmall.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing8),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              ChoiceChip(
                label: const Text(context.l10n.openclawCustomConfig),
                selected: _selectedPresetId == 'custom',
                onSelected: (_) {
                  setState(() {
                    _selectedPresetId = 'custom';
                  });
                },
              ),
              ..._openClawGuestPresets.map(
                (preset) => ChoiceChip(
                  label: Text(_presetLabel(preset.id, context)),
                  selected: _selectedPresetId == preset.id,
                  onSelected: (_) => _applyPreset(preset),
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            selectedPreset != null
                ? _presetDescription(selectedPreset.id, context)
                : context.l10n.openclawCustomConfigDesc,
            style: DS.bodySmall.copyWith(
              color: DS.textSecondary,
              height: 1.45,
            ),
          ),
          const SizedBox(height: DS.spacing10),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              OutlinedButton.icon(
                onPressed: () =>
                    unawaited(_importPairingPayloadFromClipboard(service)),
                icon: const Icon(Icons.content_paste_go_rounded),
                label: const Text(context.l10n.openclawImportFromClipboard),
              ),
              OutlinedButton.icon(
                onPressed: () => unawaited(_showPairingImportDialog(service)),
                icon: const Icon(Icons.qr_code_2_rounded),
                label: const Text(context.l10n.openclawPastePairingString),
              ),
              OutlinedButton.icon(
                onPressed: () => unawaited(_scanPairingPayload(service)),
                icon: const Icon(Icons.qr_code_scanner_rounded),
                label: const Text(context.l10n.openclawScanToPair),
              ),
              OutlinedButton.icon(
                onPressed: () => unawaited(
                  _showRemotePresetDialog(
                    title: context.l10n.openclawTailscaleRemoteNode,
                    labelText: context.l10n.openclawTailscaleIpOrDomain,
                    hintText: context.l10n.openclawTailscaleHint,
                    helperText:
                        context.l10n.openclawTailscaleHelperText,
                    buildUrl: (raw) {
                      if (raw.startsWith('http://') ||
                          raw.startsWith('https://') ||
                          raw.startsWith('ws://') ||
                          raw.startsWith('wss://')) {
                        return raw;
                      }
                      return 'http://$raw:18789';
                    },
                  ),
                ),
                icon: const Icon(Icons.hub_rounded),
                label: const Text(context.l10n.openclawTailscaleLabel),
              ),
              OutlinedButton.icon(
                onPressed: () => unawaited(
                  _showRemotePresetDialog(
                    title: context.l10n.openclawCloudflareTunnel,
                    labelText: context.l10n.openclawTunnelDomain,
                    hintText: context.l10n.openclawCloudflareHint,
                    helperText:
                        context.l10n.openclawCloudflareHelperText,
                    buildUrl: (raw) {
                      if (raw.startsWith('http://') ||
                          raw.startsWith('https://')) {
                        return raw;
                      }
                      return 'https://$raw';
                    },
                  ),
                ),
                icon: const Icon(Icons.cloud_rounded),
                label: const Text(context.l10n.openclawCloudflareLabel),
              ),
            ],
          ),
          if (selectedPreset != null) ...[
            const SizedBox(height: DS.spacing10),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(DS.spacing12),
              decoration: BoxDecoration(
                color: DS.info.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: DS.info.withValues(alpha: 0.16)),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(
                    Icons.auto_awesome_rounded,
                    color: DS.info,
                    size: 18,
                  ),
                  const SizedBox(width: DS.spacing8),
                  Expanded(
                    child: Text(
                      '已选中“${selectedPreset.label}”。连接细节会自动填入；如果随后提示缺执行权限，优先更换具备 `operator.write` scope 的令牌，或改用设备配对。',
                      style: DS.bodySmall.copyWith(
                        color: DS.textSecondary,
                        height: 1.45,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
          SizedBox(height: spacing),
          if (_selectedPresetId == 'custom') ...[
            TextField(
              controller: _gatewayController,
              onChanged: (_) => _markDirty(),
              decoration: const InputDecoration(
                labelText: context.l10n.openclawGatewayAddress,
                hintText: context.l10n.openclawGatewayHint,
              ),
            ),
            SizedBox(height: spacing),
            Text(
              context.l10n.openclawAuthMode,
              style: DS.labelSmall.copyWith(color: DS.textSecondary),
            ),
            const SizedBox(height: DS.spacing8),
            SegmentedButton<String>(
              segments: const [
                ButtonSegment<String>(
                  value: 'token',
                  label: Text(context.l10n.openclawTokenAuth),
                ),
                ButtonSegment<String>(
                  value: 'device',
                  label: Text(context.l10n.openclawDevicePairing),
                ),
              ],
              selected: {_authMode},
              onSelectionChanged: (selection) {
                setState(() {
                  _authMode = selection.first;
                  _formDirty = true;
                });
              },
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              _authMode == 'device'
                  ? context.l10n.openclawDeviceAuthDesc
                  : context.l10n.openclawTokenAuthDesc,
              style: DS.bodySmall.copyWith(
                color: DS.textSecondary,
                height: 1.45,
              ),
            ),
            SizedBox(height: spacing),
            if (_authMode == 'token')
              TextField(
                controller: _tokenController,
                onChanged: (_) => _markDirty(),
                obscureText: true,
                decoration: const InputDecoration(
                  labelText: context.l10n.openclawAuthToken,
                  hintText: context.l10n.openclawAuthTokenHint,
                ),
              )
            else ...[
              TextField(
                controller: _deviceTokenController,
                onChanged: (_) => _markDirty(),
                decoration: const InputDecoration(
                  labelText: context.l10n.openclawDeviceToken,
                  hintText: context.l10n.openclawDeviceTokenHint,
                ),
              ),
              if (pairingSession != null) ...[
                const SizedBox(height: DS.spacing12),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(DS.spacing12),
                  decoration: BoxDecoration(
                    color: DS.info.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: DS.info.withValues(alpha: 0.18),
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        context.l10n.openclawPairingCode,
                        style: DS.bodySmall.copyWith(
                          fontWeight: DS.fontWeightBold,
                          color: DS.info,
                        ),
                      ),
                      const SizedBox(height: DS.spacing6),
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              pairingSession.code,
                              style: Theme.of(context)
                                  .textTheme
                                  .headlineSmall
                                  ?.copyWith(
                                    letterSpacing: 6,
                                    fontWeight: DS.fontWeightBold,
                                  ),
                            ),
                          ),
                          IconButton(
                            onPressed: () async {
                              await Clipboard.setData(
                                ClipboardData(text: pairingSession.code),
                              );
                              if (!mounted) return;
                              _showSnackBar(context.l10n.openclawPairingCodeCopied);
                            },
                            icon: const Icon(Icons.copy_rounded),
                          ),
                        ],
                      ),
                      Text(
                        _pairingCountdownLabel(pairingSession),
                        style: DS.bodySmall.copyWith(
                          color: DS.info,
                          fontWeight: DS.fontWeightSemiBold,
                        ),
                      ),
                      const SizedBox(height: DS.spacing4),
                      Text(
                        context.l10n.openclawPairingCodeInstructions,
                        style: DS.bodySmall.copyWith(
                          color: DS.textSecondary,
                          height: 1.45,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: DS.spacing8),
              Wrap(
                spacing: DS.spacing8,
                runSpacing: DS.spacing8,
                children: [
                  TextButton(
                    onPressed: () => unawaited(_startPairing(service)),
                    child: const Text(context.l10n.openclawGeneratePairingCode),
                  ),
                  TextButton(
                    onPressed: () => unawaited(_completePairing(service)),
                    child: const Text(context.l10n.openclawCompletePairing),
                  ),
                  if (pairingSession != null)
                    TextButton(
                      onPressed: () => unawaited(service.cancelPairing()),
                      child: const Text(context.l10n.openclawCancelPairing),
                    ),
                ],
              ),
            ],
            SizedBox(height: spacing),
            Text(
              context.l10n.openclawTransportProtocol,
              style: DS.labelSmall.copyWith(color: DS.textSecondary),
            ),
            const SizedBox(height: DS.spacing8),
            SegmentedButton<String>(
              segments: const [
                ButtonSegment<String>(
                  value: 'responses_http',
                  label: Text('HTTP'),
                ),
                ButtonSegment<String>(
                  value: 'gateway_ws',
                  label: Text('WebSocket'),
                ),
              ],
              selected: {_transport},
              onSelectionChanged: (selection) {
                setState(() {
                  _transport = selection.first;
                  _formDirty = true;
                });
              },
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              _transport == 'gateway_ws'
                  ? context.l10n.openclawWebSocketTransportDesc
                  : context.l10n.openclawHttpTransportDesc,
              style: DS.bodySmall.copyWith(
                color: DS.textSecondary,
                height: 1.45,
              ),
            ),
            SizedBox(height: spacing),
          ] else ...[
            const OpenClawMetricPill(
              icon: Icons.login_rounded,
              label: context.l10n.openclawDefaultConnectionReady,
              tone: OpenClawVisualTone.connected,
              emphasized: true,
            ),
            SizedBox(height: spacing),
          ],
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: _testing
                      ? null
                      : () => unawaited(_testConnection(service)),
                  child: _testing
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text(context.l10n.openclawTestConnection),
                ),
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: FilledButton(
                  onPressed: _saving
                      ? null
                      : () => unawaited(_saveConnection(service)),
                  child: _saving
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            valueColor: AlwaysStoppedAnimation<Color>(
                              Colors.white,
                            ),
                          ),
                        )
                      : const Text(context.l10n.openclawSaveConfig),
                ),
              ),
            ],
          ),
          if (_showSaveHighlight) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              service.isConnected
                  ? copy.configurationSavedAndConnected
                  : copy.configurationSavedButUnavailable,
              style: DS.bodySmall.copyWith(
                color: service.isConnected ? DS.semanticSuccess : DS.warning,
                fontWeight: DS.fontWeightSemiBold,
              ),
            ),
          ],
          const SizedBox(height: DS.spacing8),
          Row(
            children: [
              if (service.queuedRequests.isNotEmpty)
                Expanded(
                  child: OutlinedButton(
                    onPressed: _retryingQueue
                        ? null
                        : () => unawaited(_retryQueuedRequests(service)),
                    child: _retryingQueue
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Text(context.l10n.openclawRetryQueue),
                  ),
                ),
              if (service.queuedRequests.isNotEmpty &&
                  service.config.isConfigured) ...[
                const SizedBox(width: DS.spacing12),
              ],
              if (service.config.isConfigured)
                Expanded(
                  child: TextButton(
                    onPressed: () => unawaited(_disconnect(service)),
                    child: Text(
                      context.l10n.openclawDisconnect,
                      style: DS.bodyMedium.copyWith(color: DS.semanticError),
                    ),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
