import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/openclaw_connection_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/openclaw/presentation/widgets/openclaw_primitives.dart';
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
    label: '访客模式默认引擎',
    description: '为本机演示环境准备好的默认地址与协议；任务委派会优先复用 Sparkle 后端链路，如需直连再补充可执行令牌或设备配对。',
    config: OpenClawConnectionConfig(
      gatewayUrl: 'http://127.0.0.1:18789',
      transport: 'responses_http',
    ),
  ),
];

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
      if ((ref.read(openClawConnectionProvider).pairingSession?.isExpired ??
          true)) {
        _pairingTicker?.cancel();
        _pairingTicker = null;
      }
      setState(() {});
    });
  }

  String _pairingCountdownLabel(OpenClawPairingSession? session) {
    if (session == null) return '';
    final remaining = session.expiresAt.difference(DateTime.now());
    if (remaining.isNegative) return '配对码已过期';
    final minutes = remaining.inMinutes;
    final seconds = remaining.inSeconds % 60;
    if (minutes <= 0) {
      return '请在 $seconds 秒内完成配对';
    }
    return '请在 $minutes 分 ${seconds.toString().padLeft(2, '0')} 秒内完成配对';
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
      _showSnackBar('请输入以 http://、https://、ws:// 或 wss:// 开头的地址', isError: true);
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
      _showSnackBar('请输入有效的 OpenClaw 地址', isError: true);
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
        title: const Text('断开连接'),
        content: const Text('这会清除本地保存的 OpenClaw 连接配置。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('断开'),
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
    _showSnackBar('已断开 OpenClaw 连接');
  }

  Future<void> _startPairing(OpenClawConnectionService service) async {
    final session = await service.startPairing();
    if (!mounted) return;
    _markDirty();
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    _showSnackBar('已生成配对码 ${session.code}');
  }

  Future<void> _completePairing(OpenClawConnectionService service) async {
    final token = _deviceTokenController.text.trim();
    if (token.isEmpty) {
      _showSnackBar('请输入设备令牌后再完成配对', isError: true);
      return;
    }

    await service.completePairing(token);
    if (!mounted) return;
    setState(() {
      _authMode = 'device';
      _syncSavedConfig(service);
    });
    _showSnackBar('设备配对已完成');
  }

  Future<void> _retryQueuedRequests(OpenClawConnectionService service) async {
    if (!service.isConnected) {
      _showSnackBar(
        service.hasExecutionPermissionIssue
            ? '当前网关可访问，但没有执行权限，暂时无法重试队列'
            : service.hasExecutionEndpointIssue
                ? '当前网关可访问，但执行入口不可用，暂时无法重试队列'
                : '执行引擎尚未连接，暂时无法重试队列',
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
      _showSnackBar('已重新提交 $dispatched 个排队任务');
      return;
    }
    _showSnackBar('当前没有可重试的排队任务');
  }

  void _showSnackBar(String message, {bool isError = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isError ? DS.semanticError : DS.semanticSuccess,
      ),
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
        ? '网关在线，但当前令牌没有执行权限'
        : endpointIssue
            ? '网关在线，但执行接口没有准备好'
            : '需要补一层执行链路排查';
    final body = permissionIssue
        ? '当前状态说明健康检查能通过，但真正发起执行会被拒绝。优先更换具备 `operator.write` scope 的令牌，或改用设备配对 + WebSocket。'
        : endpointIssue
            ? '当前地址可访问，但缺少 `/v1/responses` 执行入口。请确认 OpenClaw 网关版本、代理转发和 transport 选择是否一致。'
            : '建议先重新测试连接，再检查网关地址、认证方式和 transport 是否与 OpenClaw 当前实例一致。';

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
      OpenClawConnectionStatus.connected => '已准备好接手任务',
      OpenClawConnectionStatus.connecting => '正在确认连接状态',
      OpenClawConnectionStatus.error when hasPermissionIssue => '网关在线，但没有执行权限',
      OpenClawConnectionStatus.error => '暂时还没连上',
      OpenClawConnectionStatus.disconnected => '还没有接入 OpenClaw',
    };
    final statusSubtitle = switch (service.info.status) {
      OpenClawConnectionStatus.connected =>
        '连接保持正常，你可以直接从任务页或聊天页把工作交给 OpenClaw。',
      OpenClawConnectionStatus.connecting => '我们正在确认引擎状态，保存后的结果会同步显示在这里。',
      OpenClawConnectionStatus.error when hasPermissionIssue =>
        '当前令牌能访问网关，但真正执行会被拒绝。这里需要处理权限，而不是单纯重填地址。',
      OpenClawConnectionStatus.error =>
        service.info.errorMessage ?? '先检查地址、认证方式和传输协议，再重新测试连接。',
      OpenClawConnectionStatus.disconnected =>
        '完成一次连接后，之后的委派、排队和最近活动都会在各入口自动联动。',
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
                  label: '未保存更改',
                  tone: OpenClawVisualTone.attention,
                  emphasized: true,
                ),
              OpenClawMetricPill(
                icon: Icons.route_rounded,
                label: _transport == 'gateway_ws' ? 'WebSocket' : 'HTTP',
                tone: OpenClawVisualTone.active,
              ),
              OpenClawMetricPill(
                icon: _authMode == 'device'
                    ? Icons.devices_rounded
                    : Icons.key_rounded,
                label: _authMode == 'device' ? '设备配对' : '令牌认证',
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
                  label: '${service.queuedRequestCount} 个待处理',
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
            '快速接入',
            style: DS.labelSmall.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing8),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              ChoiceChip(
                label: const Text('自定义配置'),
                selected: _selectedPresetId == 'custom',
                onSelected: (_) {
                  setState(() {
                    _selectedPresetId = 'custom';
                  });
                },
              ),
              ..._openClawGuestPresets.map(
                (preset) => ChoiceChip(
                  label: Text(preset.label),
                  selected: _selectedPresetId == preset.id,
                  onSelected: (_) => _applyPreset(preset),
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            selectedPreset?.description ?? '适合你已经有现成的网关地址和认证方式，想自己掌控连接细节时使用。',
            style: DS.bodySmall.copyWith(
              color: DS.textSecondary,
              height: 1.45,
            ),
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
                labelText: '网关地址',
                hintText: '例如 http://localhost:8080',
              ),
            ),
            SizedBox(height: spacing),
            Text(
              '认证方式',
              style: DS.labelSmall.copyWith(color: DS.textSecondary),
            ),
            const SizedBox(height: DS.spacing8),
            SegmentedButton<String>(
              segments: const [
                ButtonSegment<String>(
                  value: 'token',
                  label: Text('令牌认证'),
                ),
                ButtonSegment<String>(
                  value: 'device',
                  label: Text('设备配对'),
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
                  ? '适合与本机 OpenClaw 配对，一次完成后后续连接会更顺手。'
                  : '适合你已经有现成的网关令牌，需要快速验证或切换环境时使用。',
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
                  labelText: '认证令牌',
                  hintText: '粘贴 OpenClaw 网关令牌',
                ),
              )
            else ...[
              TextField(
                controller: _deviceTokenController,
                onChanged: (_) => _markDirty(),
                decoration: const InputDecoration(
                  labelText: '设备令牌',
                  hintText: '配对完成后粘贴设备令牌',
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
                        '配对码',
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
                              _showSnackBar('配对码已复制');
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
                        '请在 OpenClaw 桌面端输入这 6 位配对码，然后把返回的设备令牌粘贴到上方。',
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
                    child: const Text('生成配对码'),
                  ),
                  TextButton(
                    onPressed: () => unawaited(_completePairing(service)),
                    child: const Text('完成配对'),
                  ),
                  if (pairingSession != null)
                    TextButton(
                      onPressed: () => unawaited(service.cancelPairing()),
                      child: const Text('取消配对'),
                    ),
                ],
              ),
            ],
            SizedBox(height: spacing),
            Text(
              '传输协议',
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
                  ? 'WebSocket 更适合保持持续连接，适合频繁委派和状态回推。'
                  : 'HTTP 更适合手动验证和快速测试连接。',
              style: DS.bodySmall.copyWith(
                color: DS.textSecondary,
                height: 1.45,
              ),
            ),
            SizedBox(height: spacing),
          ] else ...[
            OpenClawMetricPill(
              icon: Icons.login_rounded,
              label: '已为你准备好默认连接细节',
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
                      : const Text('测试连接'),
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
                      : const Text('保存配置'),
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
                        : const Text('重试队列'),
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
                      '断开连接',
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
