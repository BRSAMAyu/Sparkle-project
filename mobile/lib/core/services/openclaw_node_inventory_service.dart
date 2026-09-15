import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';

class OpenClawNodeSummary {
  const OpenClawNodeSummary({
    required this.nodeId,
    required this.name,
    required this.platform,
    required this.connected,
    this.status = 'unknown',
    this.activeRuns = 0,
    this.lastSeen,
    this.commands = const <String>[],
    this.caps = const <String>[],
  });

  factory OpenClawNodeSummary.fromJson(Map<String, dynamic> json) {
    List<String> parseList(dynamic raw) {
      if (raw is! List) return const <String>[];
      return raw
          .map((item) => item.toString())
          .where((item) => item.isNotEmpty)
          .toList();
    }

    return OpenClawNodeSummary(
      nodeId: json['node_id']?.toString() ?? '',
      name: json['name']?.toString() ?? 'Unknown Node',
      platform: json['platform']?.toString() ?? 'unknown',
      connected: json['connected'] as bool? ?? false,
      status: json['status']?.toString() ?? 'unknown',
      activeRuns: (json['active_runs'] as num?)?.toInt() ?? 0,
      lastSeen: json['last_seen']?.toString(),
      commands: parseList(json['commands']),
      caps: parseList(json['caps']),
    );
  }

  final String nodeId;
  final String name;
  final String platform;
  final bool connected;
  final String status;
  final int activeRuns;
  final String? lastSeen;
  final List<String> commands;
  final List<String> caps;
}

class OpenClawNodeInventoryService extends ChangeNotifier {
  OpenClawNodeInventoryService({
    required Future<List<Map<String, dynamic>>> Function({bool connectedOnly})
        loader,
  }) : _loader = loader;

  final Future<List<Map<String, dynamic>>> Function({bool connectedOnly})
      _loader;

  List<OpenClawNodeSummary> _nodes = const <OpenClawNodeSummary>[];
  bool _isLoading = false;
  String? _error;

  List<OpenClawNodeSummary> get nodes => List.unmodifiable(_nodes);
  bool get isLoading => _isLoading;
  String? get error => _error;
  int get connectedCount => _nodes.where((node) => node.connected).length;

  Future<void> initialize() => refresh();

  Future<void> refresh({bool connectedOnly = false}) async {
    if (_isLoading) return;
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      final payload = await _loader(connectedOnly: connectedOnly);
      _nodes = payload
          .map(OpenClawNodeSummary.fromJson)
          .where((node) => node.nodeId.isNotEmpty)
          .toList(growable: false);
    } catch (error) {
      _error = error.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}

final openClawNodeInventoryProvider =
    ChangeNotifierProvider<OpenClawNodeInventoryService>((ref) {
  final apiClient = ref.read(apiClientProvider);
  final service = OpenClawNodeInventoryService(
    loader: ({connectedOnly = false}) async {
      final response = await apiClient.get<List<dynamic>>(
        ApiEndpoints.executionNodes,
        queryParameters: <String, dynamic>{
          if (connectedOnly) 'connected_only': true,
        },
      );
      return ApiResponseParser.unwrapList(
        response.data,
        action: 'executionNodes',
      )
          .whereType<Map<dynamic, dynamic>>()
          .map(Map<String, dynamic>.from)
          .toList();
    },
  );
  unawaited(service.initialize());
  return service;
});
