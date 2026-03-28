import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

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
    this.pairedAt,
  });

  factory OpenClawConnectionConfig.fromJson(Map<String, dynamic> json) =>
      OpenClawConnectionConfig(
        gatewayUrl: json['gateway_url'] as String? ?? '',
        authToken: json['auth_token'] as String?,
        deviceToken: json['device_token'] as String?,
        transport: json['transport'] as String? ?? 'responses_http',
        pairedAt: json['paired_at'] != null
            ? DateTime.tryParse(json['paired_at'] as String)
            : null,
      );

  static const empty = OpenClawConnectionConfig(gatewayUrl: '');

  final String gatewayUrl;
  final String? authToken;
  final String? deviceToken;
  final String transport;
  final DateTime? pairedAt;

  bool get isConfigured => normalizedGatewayUrl.isNotEmpty;
  bool get isPaired => (deviceToken ?? '').trim().isNotEmpty;
  String get normalizedGatewayUrl => gatewayUrl.trim().replaceAll(RegExp(r'/+$'), '');

  Map<String, dynamic> toJson() => {
        'gateway_url': normalizedGatewayUrl,
        'auth_token': authToken,
        'device_token': deviceToken,
        'transport': transport,
        'paired_at': pairedAt?.toIso8601String(),
      };

  OpenClawConnectionConfig copyWith({
    String? gatewayUrl,
    String? authToken,
    String? deviceToken,
    String? transport,
    DateTime? pairedAt,
  }) =>
      OpenClawConnectionConfig(
        gatewayUrl: gatewayUrl ?? this.gatewayUrl,
        authToken: authToken ?? this.authToken,
        deviceToken: deviceToken ?? this.deviceToken,
        transport: transport ?? this.transport,
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

class OpenClawConnectionService extends ChangeNotifier {
  static const _configKey = 'openclaw_connection_config';
  static const _healthCheckInterval = Duration(seconds: 30);

  OpenClawConnectionConfig _config = OpenClawConnectionConfig.empty;
  OpenClawConnectionInfo _info = const OpenClawConnectionInfo();
  Timer? _healthTimer;

  OpenClawConnectionConfig get config => _config;
  OpenClawConnectionInfo get info => _info;
  bool get isConnected => _info.status == OpenClawConnectionStatus.connected;

  Future<void> initialize() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_configKey);
    if (raw == null || raw.isEmpty) return;

    try {
      _config = OpenClawConnectionConfig.fromJson(
        jsonDecode(raw) as Map<String, dynamic>,
      );
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

  Future<bool> configure(OpenClawConnectionConfig newConfig) async {
    _config = newConfig.copyWith(gatewayUrl: newConfig.normalizedGatewayUrl);
    final prefs = await SharedPreferences.getInstance();
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

    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_configKey);
    notifyListeners();
  }

  Future<OpenClawConnectionInfo> _probe(
    OpenClawConnectionConfig config,
  ) async {
    if (!config.isConfigured) {
      return const OpenClawConnectionInfo();
    }

    try {
      final stopwatch = Stopwatch()..start();
      final response = await http.get(
        Uri.parse('${config.normalizedGatewayUrl}/health'),
        headers: _buildHeaders(config),
      ).timeout(const Duration(seconds: 8));
      stopwatch.stop();

      Map<String, dynamic>? body;
      try {
        body = jsonDecode(response.body) as Map<String, dynamic>?;
      } catch (_) {}

      if (response.statusCode == 200) {
        return OpenClawConnectionInfo(
          status: OpenClawConnectionStatus.connected,
          latencyMs: stopwatch.elapsedMilliseconds,
          nodeCount: (body?['node_count'] as num?)?.toInt() ??
              (body?['connected_nodes'] as num?)?.toInt(),
          capabilities: _extractCapabilities(body),
          lastCheckedAt: DateTime.now(),
        );
      }

      return OpenClawConnectionInfo(
        status: OpenClawConnectionStatus.error,
        latencyMs: stopwatch.elapsedMilliseconds,
        errorMessage: 'HTTP ${response.statusCode}',
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
      capabilities.addAll(rawCaps.map((item) => '$item').where((item) => item.isNotEmpty));
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
  final service = OpenClawConnectionService();
  unawaited(service.initialize());
  ref.onDispose(service.dispose);
  return service;
});
