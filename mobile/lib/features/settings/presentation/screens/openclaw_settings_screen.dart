import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/openclaw_connection_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

class OpenClawSettingsScreen extends ConsumerStatefulWidget {
  const OpenClawSettingsScreen({super.key});

  @override
  ConsumerState<OpenClawSettingsScreen> createState() =>
      _OpenClawSettingsScreenState();
}

class _OpenClawSettingsScreenState
    extends ConsumerState<OpenClawSettingsScreen> {
  late final TextEditingController _gatewayController;
  late final TextEditingController _tokenController;
  late final TextEditingController _deviceTokenController;
  bool _hydrated = false;
  bool _testing = false;
  bool _saving = false;
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

  void _hydrateFromService(OpenClawConnectionService service) {
    if (_hydrated && _gatewayController.text.isNotEmpty) return;
    final config = service.config;
    _gatewayController.text = config.gatewayUrl;
    _tokenController.text = config.authToken ?? '';
    _deviceTokenController.text = config.deviceToken ?? '';
    _authMode = config.isPaired ? 'device' : 'token';
    _transport = config.transport;
    _hydrated = true;
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
      ok ? '连接成功' : (service.info.errorMessage ?? '连接失败'),
      isError: !ok,
    );
  }

  Future<void> _saveConnection(OpenClawConnectionService service) async {
    final config = _buildConfig();
    if (config == null) {
      _showSnackBar('请输入有效的网关地址', isError: true);
      return;
    }
    setState(() => _saving = true);
    final ok = await service.configure(config);
    if (!mounted) return;
    setState(() => _saving = false);
    unawaited(
      SensoryFeedbackService.emit(
        ok ? SensoryFeedbackEvent.success : SensoryFeedbackEvent.warning,
      ),
    );
    _showSnackBar(
      ok ? '配置已保存并连接成功' : '配置已保存，但当前引擎不可达',
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
      _authMode = 'token';
      _transport = 'responses_http';
    });
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    _showSnackBar('已断开 OpenClaw 连接');
  }

  void _showSnackBar(String message, {bool isError = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isError ? DS.semanticError : DS.semanticSuccess,
      ),
    );
  }

  String _statusLabel(OpenClawConnectionInfo info) {
    switch (info.status) {
      case OpenClawConnectionStatus.connected:
        return '已连接';
      case OpenClawConnectionStatus.connecting:
        return '连接中...';
      case OpenClawConnectionStatus.error:
        return '连接失败';
      case OpenClawConnectionStatus.disconnected:
        return '未连接';
    }
  }

  Color _statusColor(OpenClawConnectionInfo info) {
    switch (info.status) {
      case OpenClawConnectionStatus.connected:
        return DS.semanticSuccess;
      case OpenClawConnectionStatus.connecting:
        return DS.info;
      case OpenClawConnectionStatus.error:
        return DS.semanticError;
      case OpenClawConnectionStatus.disconnected:
        return DS.textTertiary;
    }
  }

  String? _lastCheckedLabel(OpenClawConnectionInfo info) {
    final checkedAt = info.lastCheckedAt;
    if (checkedAt == null) return null;
    final seconds = DateTime.now().difference(checkedAt).inSeconds;
    if (seconds < 60) return '${seconds}s 前检查';
    final minutes = DateTime.now().difference(checkedAt).inMinutes;
    return '${minutes}m 前检查';
  }

  @override
  Widget build(BuildContext context) {
    final service = ref.watch(openClawConnectionProvider);
    _hydrateFromService(service);
    final info = service.info;
    final statusColor = _statusColor(info);
    final lastCheckedLabel = _lastCheckedLabel(info);

    return SparklePageScaffold(
      role: SparklePageRole.settings,
      appBar: AppBar(
        title: const Text('AI执行引擎'),
      ),
      child: ContentConstraint(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(DS.spacing16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              GraphiteCardSurface(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          width: 12,
                          height: 12,
                          decoration: BoxDecoration(
                            color: statusColor,
                            borderRadius: BorderRadius.circular(99),
                          ),
                        ),
                        const SizedBox(width: DS.spacing8),
                        Text(
                          _statusLabel(info),
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                fontWeight: DS.fontWeightBold,
                              ),
                        ),
                        const Spacer(),
                        if (info.latencyMs != null)
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: DS.spacing8,
                              vertical: DS.spacing4,
                            ),
                            decoration: BoxDecoration(
                              color: statusColor.withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(999),
                            ),
                            child: Text(
                              '${info.latencyMs}ms',
                              style: DS.bodySmall.copyWith(color: statusColor),
                            ),
                          ),
                      ],
                    ),
                    if ((info.errorMessage ?? '').isNotEmpty) ...[
                      const SizedBox(height: DS.spacing8),
                      Text(
                        info.errorMessage!,
                        style: DS.bodySmall.copyWith(color: DS.semanticError),
                      ),
                    ],
                    if ((info.nodeCount ?? 0) > 0 || (info.capabilities ?? const []).isNotEmpty) ...[
                      const SizedBox(height: DS.spacing12),
                      Text(
                        '节点数：${info.nodeCount ?? 0}',
                        style: DS.bodyMedium.copyWith(
                          fontWeight: DS.fontWeightMedium,
                        ),
                      ),
                      if ((info.capabilities ?? const []).isNotEmpty) ...[
                        const SizedBox(height: DS.spacing8),
                        Wrap(
                          spacing: DS.spacing8,
                          runSpacing: DS.spacing8,
                          children: (info.capabilities ?? const [])
                              .map(
                                (capability) => Chip(
                                  label: Text(capability),
                                  side: BorderSide.none,
                                  backgroundColor: DS.surfaceSecondary,
                                ),
                              )
                              .toList(),
                        ),
                      ],
                    ],
                    if (lastCheckedLabel != null) ...[
                      const SizedBox(height: DS.spacing12),
                      Text(
                        lastCheckedLabel,
                        style: DS.bodySmall.copyWith(color: DS.textSecondary),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: DS.spacing16),
              GraphiteCardSurface(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '连接配置',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: DS.fontWeightBold,
                          ),
                    ),
                    const SizedBox(height: DS.spacing12),
                    TextField(
                      controller: _gatewayController,
                      decoration: const InputDecoration(
                        labelText: '网关地址',
                        hintText: 'http://localhost:8080',
                      ),
                    ),
                    const SizedBox(height: DS.spacing12),
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
                        setState(() => _authMode = selection.first);
                      },
                    ),
                    const SizedBox(height: DS.spacing12),
                    if (_authMode == 'token')
                      TextField(
                        controller: _tokenController,
                        obscureText: true,
                        decoration: const InputDecoration(
                          labelText: '认证令牌',
                          hintText: '输入认证令牌',
                        ),
                      )
                    else ...[
                      TextField(
                        controller: _deviceTokenController,
                        decoration: const InputDecoration(
                          labelText: '设备令牌',
                          hintText: '输入设备令牌',
                        ),
                      ),
                      const SizedBox(height: DS.spacing8),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: TextButton(
                          onPressed: () {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text('扫码配对即将推出')),
                            );
                          },
                          child: const Text('扫码配对'),
                        ),
                      ),
                    ],
                    const SizedBox(height: DS.spacing12),
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
                        setState(() => _transport = selection.first);
                      },
                    ),
                    const SizedBox(height: DS.spacing16),
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
                    if (service.config.isConfigured) ...[
                      const SizedBox(height: DS.spacing8),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: TextButton(
                          onPressed: () => unawaited(_disconnect(service)),
                          child: Text(
                            '断开连接',
                            style: DS.bodyMedium.copyWith(
                              color: DS.semanticError,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              if (!service.config.isConfigured) ...[
                const SizedBox(height: DS.spacing16),
                GraphiteCardSurface(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '什么是AI执行引擎？',
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontWeight: DS.fontWeightBold,
                            ),
                      ),
                      const SizedBox(height: DS.spacing8),
                      Text(
                        'AI执行引擎（OpenClaw）可以自动完成网页调研、文档整理等任务。你可以在自己的电脑上运行 OpenClaw，然后在这里连接它。',
                        style: DS.bodySmall.copyWith(
                          color: DS.textSecondary,
                          height: 1.5,
                        ),
                      ),
                      const SizedBox(height: DS.spacing8),
                      TextButton(
                        onPressed: () {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('更多连接引导即将推出')),
                          );
                        },
                        child: const Text('了解更多'),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
