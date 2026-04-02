import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';

typedef OpenClawBackendStatusLoader = Future<Map<String, dynamic>?> Function();
typedef OpenClawBackendProfileLoader = Future<Map<String, dynamic>?> Function();
typedef OpenClawBackendProfileSaver = Future<Map<String, dynamic>?> Function(
  Map<String, dynamic> payload,
);
typedef OpenClawBackendProfileDeleter = Future<void> Function();

enum OpenClawConnectionStatus {
  disconnected,
  connecting,
  connected,
  error,
}

class OpenClawConnectionConfig {
  const OpenClawConnectionConfig({
    required this.gatewayUrl,
    this.authToken,
    this.deviceToken,
    this.transport = 'responses_http',
    this.wsUrl,
    this.pairedAt,
  });

  factory OpenClawConnectionConfig.fromJson(Map<String, dynamic> json) =>
      OpenClawConnectionConfig(
        gatewayUrl: json['gateway_url'] as String? ?? '',
        authToken: json['auth_token'] as String?,
        deviceToken: json['device_token'] as String?,
        transport: json['transport'] as String? ?? 'responses_http',
        wsUrl: json['ws_url'] as String?,
        pairedAt: json['paired_at'] != null
            ? DateTime.tryParse(json['paired_at'] as String)
            : null,
      );

  static const empty = OpenClawConnectionConfig(gatewayUrl: '');

  final String gatewayUrl;
  final String? authToken;
  final String? deviceToken;
  final String transport;
  final String? wsUrl;
  final DateTime? pairedAt;

  bool get isConfigured =>
      normalizedGatewayUrl.isNotEmpty || normalizedWsUrl.isNotEmpty;
  bool get isPaired => (deviceToken ?? '').trim().isNotEmpty;
  String get normalizedGatewayUrl =>
      gatewayUrl.trim().replaceAll(RegExp(r'/+$'), '');
  String get normalizedWsUrl =>
      (wsUrl ?? '').trim().replaceAll(RegExp(r'/+$'), '');

  String get httpGatewayUrl {
    final source = normalizedGatewayUrl.isNotEmpty
        ? normalizedGatewayUrl
        : normalizedWsUrl;
    if (source.isEmpty) return '';
    final uri = Uri.tryParse(source);
    if (uri == null) return source;
    final scheme = uri.scheme.toLowerCase();
    if (scheme == 'ws') {
      return uri.replace(scheme: 'http').toString();
    }
    if (scheme == 'wss') {
      return uri.replace(scheme: 'https').toString();
    }
    return source;
  }

  String get resolvedWsUrl {
    if (normalizedWsUrl.isNotEmpty) {
      return normalizedWsUrl;
    }
    final source = normalizedGatewayUrl;
    if (source.isEmpty) return '';
    final uri = Uri.tryParse(source);
    if (uri == null) return '';
    final scheme = uri.scheme.toLowerCase();
    if (scheme == 'http') {
      return uri.replace(scheme: 'ws').toString();
    }
    if (scheme == 'https') {
      return uri.replace(scheme: 'wss').toString();
    }
    return source;
  }

  Map<String, dynamic> toJson() => {
        'gateway_url': httpGatewayUrl,
        'auth_token': authToken,
        'device_token': deviceToken,
        'transport': transport,
        'ws_url': resolvedWsUrl.isEmpty ? null : resolvedWsUrl,
        'paired_at': pairedAt?.toIso8601String(),
      };

  OpenClawConnectionConfig copyWith({
    String? gatewayUrl,
    String? authToken,
    String? deviceToken,
    String? transport,
    String? wsUrl,
    DateTime? pairedAt,
  }) =>
      OpenClawConnectionConfig(
        gatewayUrl: gatewayUrl ?? this.gatewayUrl,
        authToken: authToken ?? this.authToken,
        deviceToken: deviceToken ?? this.deviceToken,
        transport: transport ?? this.transport,
        wsUrl: wsUrl ?? this.wsUrl,
        pairedAt: pairedAt ?? this.pairedAt,
      );
}

class OpenClawConnectionInfo {
  const OpenClawConnectionInfo({
    this.status = OpenClawConnectionStatus.disconnected,
    this.latencyMs,
    this.nodeCount,
    this.capabilities,
    this.errorMessage,
    this.lastCheckedAt,
  });

  final OpenClawConnectionStatus status;
  final int? latencyMs;
  final int? nodeCount;
  final List<String>? capabilities;
  final String? errorMessage;
  final DateTime? lastCheckedAt;

  OpenClawConnectionInfo copyWith({
    OpenClawConnectionStatus? status,
    int? latencyMs,
    int? nodeCount,
    List<String>? capabilities,
    String? errorMessage,
    DateTime? lastCheckedAt,
  }) =>
      OpenClawConnectionInfo(
        status: status ?? this.status,
        latencyMs: latencyMs ?? this.latencyMs,
        nodeCount: nodeCount ?? this.nodeCount,
        capabilities: capabilities ?? this.capabilities,
        errorMessage: errorMessage ?? this.errorMessage,
        lastCheckedAt: lastCheckedAt ?? this.lastCheckedAt,
      );
}

class OpenClawPairingSession {
  const OpenClawPairingSession({
    required this.code,
    required this.createdAt,
    required this.expiresAt,
  });

  factory OpenClawPairingSession.fromJson(Map<String, dynamic> json) =>
      OpenClawPairingSession(
        code: json['code']?.toString() ?? '',
        createdAt: DateTime.tryParse(json['created_at']?.toString() ?? '') ??
            DateTime.now(),
        expiresAt: DateTime.tryParse(json['expires_at']?.toString() ?? '') ??
            DateTime.now().add(const Duration(minutes: 10)),
      );

  final String code;
  final DateTime createdAt;
  final DateTime expiresAt;

  bool get isExpired => DateTime.now().isAfter(expiresAt);

  Map<String, dynamic> toJson() => {
        'code': code,
        'created_at': createdAt.toIso8601String(),
        'expires_at': expiresAt.toIso8601String(),
      };
}

class OpenClawQueuedRequest {
  const OpenClawQueuedRequest({
    required this.id,
    required this.taskId,
    required this.enqueuedAt,
    this.goal,
    this.templateId,
    this.source = 'task_execution',
    this.priority = 0,
  });

  factory OpenClawQueuedRequest.fromJson(Map<String, dynamic> json) =>
      OpenClawQueuedRequest(
        id: json['id']?.toString() ?? '',
        taskId: json['task_id']?.toString() ?? '',
        goal: json['goal']?.toString(),
        templateId: json['template_id']?.toString(),
        source: json['source']?.toString() ?? 'task_execution',
        priority: (json['priority'] as num?)?.toInt() ?? 0,
        enqueuedAt: DateTime.tryParse(json['enqueued_at']?.toString() ?? '') ??
            DateTime.now(),
      );

  final String id;
  final String taskId;
  final String? goal;
  final String? templateId;
  final String source;
  final int priority;
  final DateTime enqueuedAt;

  Map<String, dynamic> toJson() => {
        'id': id,
        'task_id': taskId,
        'goal': goal,
        'template_id': templateId,
        'source': source,
        'priority': priority,
        'enqueued_at': enqueuedAt.toIso8601String(),
      };
}

class OpenClawConnectionService extends ChangeNotifier {
  OpenClawConnectionService({
    OpenClawBackendStatusLoader? backendStatusLoader,
    OpenClawBackendProfileLoader? backendProfileLoader,
    OpenClawBackendProfileSaver? backendProfileSaver,
    OpenClawBackendProfileDeleter? backendProfileDeleter,
  })  : _backendStatusLoader = backendStatusLoader,
        _backendProfileLoader = backendProfileLoader,
        _backendProfileSaver = backendProfileSaver,
        _backendProfileDeleter = backendProfileDeleter;

  static const _configKey = 'openclaw_connection_config';
  static const _pairingKey = 'openclaw_pairing_session';
  static const _queueKey = 'openclaw_execution_queue';
  static const _healthCheckInterval = Duration(seconds: 30);

  final OpenClawBackendStatusLoader? _backendStatusLoader;
  final OpenClawBackendProfileLoader? _backendProfileLoader;
  final OpenClawBackendProfileSaver? _backendProfileSaver;
  final OpenClawBackendProfileDeleter? _backendProfileDeleter;
  OpenClawConnectionConfig _config = OpenClawConnectionConfig.empty;
  OpenClawConnectionInfo _info = const OpenClawConnectionInfo();
  OpenClawPairingSession? _pairingSession;
  List<OpenClawQueuedRequest> _queuedRequests = const [];
  Timer? _healthTimer;

  OpenClawConnectionConfig get config => _config;
  OpenClawConnectionInfo get info => _info;
  OpenClawPairingSession? get pairingSession =>
      (_pairingSession?.isExpired ?? false) ? null : _pairingSession;
  List<OpenClawQueuedRequest> get queuedRequests =>
      List.unmodifiable(_queuedRequests);
  int get queuedRequestCount => _queuedRequests.length;
  bool get isConnected => _info.status == OpenClawConnectionStatus.connected;
  bool get hasExecutionPermissionIssue {
    final normalized = (_info.errorMessage ?? '').toLowerCase();
    return normalized.contains('operator.write') ||
        normalized.contains('scope') ||
        (normalized.contains('权限'));
  }

  bool get hasExecutionEndpointIssue =>
      (_info.errorMessage ?? '').contains('/v1/responses');

  bool get isGatewayReachable =>
      isConnected || hasExecutionPermissionIssue || hasExecutionEndpointIssue;

  void markExecutionUnavailable(String message) {
    final normalized = message.trim();
    _info = _info.copyWith(
      status: OpenClawConnectionStatus.error,
      errorMessage: normalized.isEmpty ? 'OpenClaw 执行当前不可用' : normalized,
      lastCheckedAt: DateTime.now(),
    );
    notifyListeners();
  }

  void markExecutionAvailable({String? message}) {
    _info = _info.copyWith(
      status: OpenClawConnectionStatus.connected,
      errorMessage: message,
      lastCheckedAt: DateTime.now(),
    );
    notifyListeners();
  }

  Future<void> initialize() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_configKey);
    final rawPairing = prefs.getString(_pairingKey);
    final rawQueue = prefs.getString(_queueKey);

    try {
      if (raw != null && raw.isNotEmpty) {
        _config = OpenClawConnectionConfig.fromJson(
          jsonDecode(raw) as Map<String, dynamic>,
        );
      }
      if (rawPairing != null && rawPairing.isNotEmpty) {
        _pairingSession = OpenClawPairingSession.fromJson(
          jsonDecode(rawPairing) as Map<String, dynamic>,
        );
        if (_pairingSession?.isExpired ?? false) {
          _pairingSession = null;
          await prefs.remove(_pairingKey);
        }
      }
      if (rawQueue != null && rawQueue.isNotEmpty) {
        final decoded = jsonDecode(rawQueue);
        if (decoded is List) {
          _queuedRequests = decoded
              .whereType<Map<dynamic, dynamic>>()
              .map(
                (item) => OpenClawQueuedRequest.fromJson(
                  Map<String, dynamic>.from(item),
                ),
              )
              .toList()
            ..sort((a, b) {
              final byPriority = b.priority.compareTo(a.priority);
              if (byPriority != 0) return byPriority;
              return a.enqueuedAt.compareTo(b.enqueuedAt);
            });
        }
      }
      await _syncConfigFromBackend(prefs);
      notifyListeners();
      if (_config.isConfigured) {
        unawaited(checkHealth());
        _startHealthMonitor();
      }
    } catch (_) {
      _config = OpenClawConnectionConfig.empty;
      _info = const OpenClawConnectionInfo();
    }
  }

  Future<void> queueExecutionRequest({
    required String taskId,
    String? goal,
    String? templateId,
    String source = 'task_execution',
    int priority = 0,
  }) async {
    final existingIndex = _queuedRequests.indexWhere(
      (item) =>
          item.taskId == taskId &&
          item.goal == goal &&
          item.templateId == templateId,
    );
    if (existingIndex != -1) {
      return;
    }

    _queuedRequests = [
      ..._queuedRequests,
      OpenClawQueuedRequest(
        id: '${taskId}_${DateTime.now().millisecondsSinceEpoch}',
        taskId: taskId,
        goal: goal,
        templateId: templateId,
        source: source,
        priority: priority,
        enqueuedAt: DateTime.now(),
      ),
    ]..sort((a, b) {
        final byPriority = b.priority.compareTo(a.priority);
        if (byPriority != 0) return byPriority;
        return a.enqueuedAt.compareTo(b.enqueuedAt);
      });
    await _persistQueue();
    notifyListeners();
  }

  Future<void> removeQueuedRequest(String id) async {
    _queuedRequests =
        _queuedRequests.where((request) => request.id != id).toList();
    await _persistQueue();
    notifyListeners();
  }

  Future<void> clearQueuedRequests() async {
    _queuedRequests = const [];
    await _persistQueue();
    notifyListeners();
  }

  Future<OpenClawPairingSession> startPairing() async {
    final random = Random.secure();
    final code = List.generate(6, (_) => random.nextInt(10)).join();
    final session = OpenClawPairingSession(
      code: code,
      createdAt: DateTime.now(),
      expiresAt: DateTime.now().add(const Duration(minutes: 10)),
    );
    _pairingSession = session;
    await _persistPairing();
    notifyListeners();
    return session;
  }

  Future<void> completePairing(String deviceToken) async {
    final trimmed = deviceToken.trim();
    if (trimmed.isEmpty) return;
    _config = _config.copyWith(
      deviceToken: trimmed,
      pairedAt: DateTime.now(),
    );
    _pairingSession = null;
    final prefs = await SharedPreferences.getInstance();
    final syncedConfig = await _syncConfigToBackend(_config) ?? _config;
    _config = syncedConfig;
    await prefs.setString(_configKey, jsonEncode(_config.toJson()));
    await prefs.remove(_pairingKey);
    notifyListeners();
  }

  Future<void> cancelPairing() async {
    _pairingSession = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_pairingKey);
    notifyListeners();
  }

  Future<bool> configure(OpenClawConnectionConfig newConfig) async {
    _config = newConfig.copyWith(gatewayUrl: newConfig.httpGatewayUrl);
    final prefs = await SharedPreferences.getInstance();
    final syncedConfig = await _syncConfigToBackend(_config);
    if (syncedConfig == null && _backendProfileSaver != null) {
      _info = OpenClawConnectionInfo(
        status: OpenClawConnectionStatus.error,
        errorMessage: 'Sparkle 后端未能保存当前 OpenClaw 远程连接配置',
        lastCheckedAt: DateTime.now(),
      );
      notifyListeners();
      return false;
    }
    _config = syncedConfig ?? _config;
    await prefs.setString(_configKey, jsonEncode(_config.toJson()));
    final ok = await checkHealth();
    if (ok) {
      _startHealthMonitor();
    }
    notifyListeners();
    return ok;
  }

  Future<bool> testConnection(OpenClawConnectionConfig config) async {
    _info = OpenClawConnectionInfo(
      status: OpenClawConnectionStatus.connecting,
      lastCheckedAt: DateTime.now(),
    );
    notifyListeners();
    final probe = await _probe(config);
    _info = probe;
    notifyListeners();
    return probe.status == OpenClawConnectionStatus.connected;
  }

  Future<bool> checkHealth() async {
    if (!_config.isConfigured) {
      _info = const OpenClawConnectionInfo();
      notifyListeners();
      return false;
    }

    _info = OpenClawConnectionInfo(
      status: OpenClawConnectionStatus.connecting,
      lastCheckedAt: DateTime.now(),
    );
    notifyListeners();

    final probe = await _probe(_config);
    _info = probe;
    notifyListeners();
    return probe.status == OpenClawConnectionStatus.connected;
  }

  Future<void> disconnect() async {
    _healthTimer?.cancel();
    _healthTimer = null;
    _config = OpenClawConnectionConfig.empty;
    _info = const OpenClawConnectionInfo();
    _pairingSession = null;

    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_configKey);
    await prefs.remove(_pairingKey);
    final deleteProfile = _backendProfileDeleter;
    if (deleteProfile != null) {
      try {
        await deleteProfile();
      } catch (_) {}
    }
    notifyListeners();
  }

  Future<OpenClawConnectionInfo> _probe(
    OpenClawConnectionConfig config,
  ) async {
    if (!config.isConfigured) {
      return await _preferBackendAvailability(
        const OpenClawConnectionInfo(),
      );
    }

    try {
      final stopwatch = Stopwatch()..start();
      final response = await http
          .get(
            Uri.parse('${config.httpGatewayUrl}/health'),
            headers: _buildHeaders(config),
          )
          .timeout(const Duration(seconds: 8));
      stopwatch.stop();

      Map<String, dynamic>? body;
      try {
        body = jsonDecode(response.body) as Map<String, dynamic>?;
      } catch (_) {}

      if (response.statusCode == 200) {
        final executionProbe = config.transport == 'responses_http'
            ? await _probeExecutionCapability(config)
            : null;
        if (executionProbe != null &&
            executionProbe.status != OpenClawConnectionStatus.connected) {
          return await _preferBackendAvailability(executionProbe);
        }
        return OpenClawConnectionInfo(
          status: OpenClawConnectionStatus.connected,
          latencyMs: stopwatch.elapsedMilliseconds,
          nodeCount: (body?['node_count'] as num?)?.toInt() ??
              (body?['connected_nodes'] as num?)?.toInt(),
          capabilities: <String>[
            ..._extractCapabilities(body),
            if (config.transport == 'responses_http') '执行写权限',
          ].toSet().toList(),
          lastCheckedAt: DateTime.now(),
        );
      }

      return await _preferBackendAvailability(
        OpenClawConnectionInfo(
          status: OpenClawConnectionStatus.error,
          latencyMs: stopwatch.elapsedMilliseconds,
          errorMessage: 'HTTP ${response.statusCode}',
          lastCheckedAt: DateTime.now(),
        ),
      );
    } catch (e) {
      return await _preferBackendAvailability(
        OpenClawConnectionInfo(
          status: OpenClawConnectionStatus.error,
          errorMessage: e.toString(),
          lastCheckedAt: DateTime.now(),
        ),
      );
    }
  }

  Future<OpenClawConnectionInfo> _preferBackendAvailability(
    OpenClawConnectionInfo localInfo,
  ) async {
    if (localInfo.status == OpenClawConnectionStatus.connected) {
      return localInfo;
    }
    final backendInfo = await _probeBackendExecutionAvailability();
    return backendInfo ?? localInfo;
  }

  Future<OpenClawConnectionInfo?> _probeBackendExecutionAvailability() async {
    final loader = _backendStatusLoader;
    if (loader == null) {
      return null;
    }

    try {
      final payload = await loader();
      if (payload == null || payload['reachable'] != true) {
        return null;
      }
      final capabilities = <String>[
        ..._extractCapabilities(payload),
        'Sparkle 后端代连',
      ].toSet().toList();
      return OpenClawConnectionInfo(
        status: OpenClawConnectionStatus.connected,
        latencyMs: (payload['latency_ms'] as num?)?.toInt(),
        nodeCount: (payload['connected_nodes'] as num?)?.toInt(),
        capabilities: capabilities,
        lastCheckedAt: DateTime.now(),
      );
    } catch (_) {
      return null;
    }
  }

  Future<OpenClawConnectionInfo> _probeExecutionCapability(
    OpenClawConnectionConfig config,
  ) async {
    try {
      final response = await http
          .post(
            Uri.parse('${config.httpGatewayUrl}/v1/responses'),
            headers: <String, String>{
              ..._buildHeaders(config),
              'Content-Type': 'application/json',
            },
            body: '{}',
          )
          .timeout(const Duration(seconds: 8));

      if (response.statusCode == 400 || response.statusCode == 422) {
        return OpenClawConnectionInfo(
          status: OpenClawConnectionStatus.connected,
          lastCheckedAt: DateTime.now(),
        );
      }

      if (response.statusCode == 401 || response.statusCode == 403) {
        return OpenClawConnectionInfo(
          status: OpenClawConnectionStatus.error,
          errorMessage: _extractErrorMessage(response.body) ??
              '缺少 OpenClaw 执行权限，请检查令牌 scope',
          lastCheckedAt: DateTime.now(),
        );
      }

      if (response.statusCode == 404) {
        return OpenClawConnectionInfo(
          status: OpenClawConnectionStatus.error,
          errorMessage: 'OpenClaw 执行接口不可用（/v1/responses 未找到）',
          lastCheckedAt: DateTime.now(),
        );
      }

      return OpenClawConnectionInfo(
        status: response.statusCode < 500
            ? OpenClawConnectionStatus.connected
            : OpenClawConnectionStatus.error,
        errorMessage: response.statusCode < 500
            ? null
            : 'OpenClaw 执行接口异常（HTTP ${response.statusCode}）',
        lastCheckedAt: DateTime.now(),
      );
    } catch (e) {
      return OpenClawConnectionInfo(
        status: OpenClawConnectionStatus.error,
        errorMessage: e.toString(),
        lastCheckedAt: DateTime.now(),
      );
    }
  }

  Future<void> _syncConfigFromBackend(SharedPreferences prefs) async {
    final loader = _backendProfileLoader;
    if (loader == null) {
      return;
    }
    try {
      final payload = await loader();
      if (payload == null) {
        return;
      }
      if (payload['configured'] != true) {
        _config = OpenClawConnectionConfig.empty;
        await prefs.remove(_configKey);
        return;
      }
      _config = OpenClawConnectionConfig.fromJson(payload);
      await prefs.setString(_configKey, jsonEncode(_config.toJson()));
    } catch (_) {}
  }

  Future<OpenClawConnectionConfig?> _syncConfigToBackend(
    OpenClawConnectionConfig config,
  ) async {
    final saver = _backendProfileSaver;
    if (saver == null) {
      return config;
    }
    try {
      final payload = await saver(config.toJson());
      if (payload == null) {
        return null;
      }
      return OpenClawConnectionConfig.fromJson(payload);
    } catch (_) {
      return null;
    }
  }

  Map<String, String> _buildHeaders(OpenClawConnectionConfig config) {
    final headers = <String, String>{};
    final authToken = config.authToken?.trim();
    final deviceToken = config.deviceToken?.trim();
    if ((authToken ?? '').isNotEmpty) {
      headers['Authorization'] = 'Bearer $authToken';
    }
    if ((deviceToken ?? '').isNotEmpty) {
      headers['X-Device-Token'] = deviceToken!;
    }
    return headers;
  }

  List<String> _extractCapabilities(Map<String, dynamic>? body) {
    if (body == null) return const [];
    final capabilities = <String>[];
    final rawCaps = body['capabilities'];
    if (rawCaps is List) {
      capabilities.addAll(
          rawCaps.map((item) => '$item').where((item) => item.isNotEmpty));
    }
    if (body['supports_nodes'] == true) {
      capabilities.add('节点发现');
    }
    if (body['supports_templates'] == true) {
      capabilities.add('模板执行');
    }
    if (body['supports_quality_loop'] == true) {
      capabilities.add('质量闭环');
    }
    return capabilities.toSet().toList();
  }

  String? _extractErrorMessage(String body) {
    try {
      final decoded = jsonDecode(body);
      if (decoded is Map<String, dynamic>) {
        final error = decoded['error'];
        if (error is Map<String, dynamic>) {
          final message = error['message']?.toString().trim();
          if ((message ?? '').isNotEmpty) {
            return message;
          }
        }
        final message = decoded['message']?.toString().trim();
        if ((message ?? '').isNotEmpty) {
          return message;
        }
      }
    } catch (_) {}
    final trimmed = body.trim();
    return trimmed.isEmpty ? null : trimmed;
  }

  Future<void> _persistQueue() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      _queueKey,
      jsonEncode(_queuedRequests.map((item) => item.toJson()).toList()),
    );
  }

  Future<void> _persistPairing() async {
    final prefs = await SharedPreferences.getInstance();
    if (_pairingSession == null) {
      await prefs.remove(_pairingKey);
      return;
    }
    await prefs.setString(
      _pairingKey,
      jsonEncode(_pairingSession!.toJson()),
    );
  }

  void _startHealthMonitor() {
    _healthTimer?.cancel();
    _healthTimer = Timer.periodic(_healthCheckInterval, (_) {
      unawaited(checkHealth());
    });
  }

  @override
  void dispose() {
    _healthTimer?.cancel();
    super.dispose();
  }
}

final openClawConnectionProvider =
    ChangeNotifierProvider<OpenClawConnectionService>((ref) {
  final apiClient = ref.read(apiClientProvider);
  final service = OpenClawConnectionService(
    backendStatusLoader: () async {
      final response = await apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.executionConnectionStatus,
      );
      return ApiResponseParser.unwrapMap(
        response.data,
        action: 'executionConnectionStatus',
      );
    },
    backendProfileLoader: () async {
      final response = await apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.executionConnectionProfile,
      );
      return ApiResponseParser.unwrapMap(
        response.data,
        action: 'executionConnectionProfile',
      );
    },
    backendProfileSaver: (payload) async {
      final response = await apiClient.put<Map<String, dynamic>>(
        ApiEndpoints.executionConnectionProfile,
        data: payload,
      );
      return ApiResponseParser.unwrapMap(
        response.data,
        action: 'saveExecutionConnectionProfile',
      );
    },
    backendProfileDeleter: () async {
      await apiClient.delete<Map<String, dynamic>>(
        ApiEndpoints.executionConnectionProfile,
      );
    },
  );
  unawaited(service.initialize());
  return service;
});
