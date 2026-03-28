import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/openclaw_connection_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/task/presentation/execution_copy.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';

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
  String _authMode = 'token';
  String _transport = 'responses_http';

  @override
  void initState() {
    super.initState();
    _gatewayController = TextEditingController();
    _tokenController = TextEditingController();
    _deviceTokenController = TextEditingController();
  }

  @override
  void dispose() {
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
    _hydrated = true;
    _lastHydratedSignature = signature;
  }

  void _syncSavedConfig(OpenClawConnectionService service) {
    _formDirty = false;
    _hydrated = true;
    _lastHydratedSignature = _configSignature(service.config);
  }

  OpenClawConnectionConfig? _buildConfig() {
    final gatewayUrl = _gatewayController.text.trim();
    if (gatewayUrl.isEmpty ||
        (!gatewayUrl.startsWith('http://') &&
            !gatewayUrl.startsWith('https://'))) {
      return null;
    }

    return OpenClawConnectionConfig(
      gatewayUrl: gatewayUrl,
      authToken: _authMode == 'token' && _tokenController.text.trim().isNotEmpty
          ? _tokenController.text.trim()
          : null,
      deviceToken:
          _authMode == 'device' && _deviceTokenController.text.trim().isNotEmpty
              ? _deviceTokenController.text.trim()
              : null,
      transport: _transport,
      pairedAt: _authMode == 'device' ? DateTime.now() : null,
    );
  }

  Future<void> _testConnection(OpenClawConnectionService service) async {
    final copy = ExecutionCopy.of(context);
    final config = _buildConfig();
    if (config == null) {
      _showSnackBar('请输入以 http:// 或 https:// 开头的网关地址', isError: true);
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
      _showSnackBar('请输入有效的网关地址', isError: true);
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
      _showSnackBar('执行引擎尚未连接，暂时无法重试队列', isError: true);
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

  @override
  Widget build(BuildContext context) {
    final service = ref.watch(openClawConnectionProvider);
    final pairingSession = service.pairingSession;
    _hydrateFromService(service);

    final spacing = widget.compact ? DS.spacing12 : DS.spacing16;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextField(
          controller: _gatewayController,
          onChanged: (_) => _markDirty(),
          decoration: const InputDecoration(
            labelText: '网关地址',
            hintText: 'http://localhost:8080',
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
              hintText: '输入认证令牌',
            ),
          )
        else ...[
          TextField(
            controller: _deviceTokenController,
            onChanged: (_) => _markDirty(),
            decoration: const InputDecoration(
              labelText: '设备令牌',
              hintText: '输入设备令牌',
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
        Row(
          children: [
            Expanded(
              child: OutlinedButton(
                onPressed:
                    _testing ? null : () => unawaited(_testConnection(service)),
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
                onPressed:
                    _saving ? null : () => unawaited(_saveConnection(service)),
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
    );
  }
}
