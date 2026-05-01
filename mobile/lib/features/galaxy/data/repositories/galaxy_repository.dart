import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/galaxy/data/models/node_expansion_models.dart';
import 'package:sparkle/features/knowledge/data/models/knowledge_detail_model.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

final galaxyRepositoryProvider = Provider<GalaxyRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return GalaxyRepository(apiClient);
});

class GalaxyRepository {
  GalaxyRepository(this._apiClient);
  final ApiClient _apiClient;

  Future<GalaxyGraphResponse> getGraph({double zoomLevel = 1.0}) async {
    if (DemoDataService.isDemoMode) {
      return DemoDataService().demoGalaxy;
    }
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.galaxyGraph,
        queryParameters: {'zoom_level': zoomLevel},
      );
      final payload = response.data;
      if (payload == null) {
        throw Exception('Galaxy graph payload is missing');
      }
      return GalaxyGraphResponse.fromJson(payload);
    } on DioException catch (e) {
      throw Exception(
        _extractDetail(
          e,
          defaultMessage: 'Failed to load galaxy graph',
        ),
      );
    } catch (e) {
      debugPrint('GalaxyRepository.getGraph unexpected error: $e');
      throw Exception('An unexpected error occurred');
    }
  }

  Future<void> sparkNode(String id) async {
    if (DemoDataService.isDemoMode) {
      // Simulate success
      return;
    }
    try {
      await _apiClient.post<void>(ApiEndpoints.sparkNode(id));
    } on DioException catch (e) {
      throw Exception(
        _extractDetail(
          e,
          defaultMessage: 'Failed to spark node',
        ),
      );
    }
  }

  Stream<SSEEvent> getGalaxyEventsStream() {
    if (DemoDataService.isDemoMode) {
      return const Stream.empty();
    }
    return _connectSSE();
  }

  Stream<SSEEvent> _connectSSE() async* {
    try {
      final dio = Dio();
      final response = await dio.get<ResponseBody>(
        ApiEndpoints.galaxyEvents,
        options: Options(
          responseType: ResponseType.stream,
          headers: {'Accept': 'text/event-stream'},
        ),
      );
      final stream = response.data;
      if (stream == null) return;
      final buffer = StringBuffer();
      await for (final chunk
          in stream.stream.cast<List<int>>().transform(utf8.decoder)) {
        buffer.write(chunk);
        while (buffer.toString().contains('\n\n')) {
          final content = buffer.toString();
          final idx = content.indexOf('\n\n');
          final raw = content.substring(0, idx);
          buffer.clear();
          buffer.write(content.substring(idx + 2));
          final event = _parseSSE(raw);
          if (event != null) yield event;
        }
      }
    } catch (e) {
      debugPrint('🌌 Galaxy SSE connection error: $e');
    }
  }

  SSEEvent? _parseSSE(String raw) {
    String? eventType;
    String? data;
    for (final line in raw.split('\n')) {
      if (line.startsWith('event:')) {
        eventType = line.substring(6).trim();
      } else if (line.startsWith('data:')) {
        data = line.substring(5).trim();
      }
    }
    if (eventType == null || data == null) return null;
    return SSEEvent(event: eventType, data: data);
  }

  /// Get detailed information about a specific knowledge node
  Future<KnowledgeDetailResponse> getNodeDetail(String nodeId) async {
    if (DemoDataService.isDemoMode) {
      return DemoDataService().getDemoNodeDetail(nodeId);
    }
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.galaxyNodeDetail(nodeId),
      );
      final payload = response.data;
      if (payload == null) {
        throw Exception('Node detail payload is missing');
      }
      return KnowledgeDetailResponse.fromJson(payload);
    } on DioException catch (e) {
      throw Exception(
        _extractDetail(
          e,
          defaultMessage: 'Failed to load node detail',
        ),
      );
    } catch (e) {
      debugPrint('GalaxyRepository.getNodeDetail unexpected error: $e');
      throw Exception('An unexpected error occurred');
    }
  }

  /// Predict the next best node to learn
  Future<KnowledgeDetailResponse?> predictNextNode() async {
    if (DemoDataService.isDemoMode) {
      // Return a random unlocked node or locked neighbor
      return null;
    }
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.galaxyPredictNext,
      );
      final payload = response.data;
      if (payload == null) return null;
      return KnowledgeDetailResponse.fromJson(payload);
    } catch (e) {
      debugPrint('GalaxyRepository.predictNextNode failed: $e');
      // It's okay if prediction fails, just return null.
      return null;
    }
  }

  Future<List<GalaxySearchResult>> searchNodes(String query) async {
    if (DemoDataService.isDemoMode) {
      return [];
    }
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.galaxySearch,
        data: {'query': query},
      );
      final payload = response.data;
      if (payload == null) return [];
      final searchResponse = GalaxySearchResponse.fromJson(payload);
      return searchResponse.results;
    } on DioException catch (e) {
      debugPrint('GalaxyRepository.searchNodes request failed: $e');
      return [];
    } catch (e) {
      debugPrint('GalaxyRepository.searchNodes unexpected error: $e');
      return [];
    }
  }

  /// Toggle favorite status for a knowledge node
  Future<void> toggleFavorite(String nodeId) async {
    if (DemoDataService.isDemoMode) {
      return;
    }
    try {
      await _apiClient.post<void>(ApiEndpoints.galaxyNodeFavorite(nodeId));
    } on DioException catch (e) {
      throw Exception(
        _extractDetail(
          e,
          defaultMessage: 'Failed to toggle favorite',
        ),
      );
    }
  }

  /// Pause or resume decay for a knowledge node
  Future<void> pauseDecay(String nodeId, bool pause) async {
    if (DemoDataService.isDemoMode) {
      return;
    }
    try {
      await _apiClient.post<void>(
        ApiEndpoints.galaxyNodeDecayPause(nodeId),
        data: {'pause': pause},
      );
    } on DioException catch (e) {
      throw Exception(
        _extractDetail(
          e,
          defaultMessage: 'Failed to update decay status',
        ),
      );
    }
  }

  Future<NodeExpansionCandidatesResponse> generateExpansionCandidates(
    String nodeId, {
    int count = 3,
  }) async {
    if (DemoDataService.isDemoMode) {
      return _sanitizeExpansionCandidates(
        NodeExpansionCandidatesResponse(
          triggerNodeId: '',
          promptVersion: 'demo',
          candidates: <NodeExpansionCandidate>[
            NodeExpansionCandidate(
              candidateId: 'demo-1',
              name: S.galaxyBasicConcepts,
              description: S.galaxyBasicConceptsDesc,
              importanceLevel: 3,
              relationToTrigger: 'prerequisite',
              relationStrength: 0.78,
            ),
            NodeExpansionCandidate(
              candidateId: 'demo-2',
              name: S.galaxyAppScenarios,
              description: S.galaxyAppScenariosDesc,
              importanceLevel: 3,
              relationToTrigger: 'application',
              relationStrength: 0.72,
            ),
            NodeExpansionCandidate(
              candidateId: 'demo-3',
              name: S.galaxyAdvancedTopics,
              description: S.galaxyAdvancedTopicsDesc,
              importanceLevel: 4,
              relationToTrigger: 'evolution',
              relationStrength: 0.7,
            ),
          ],
        ),
      );
    }
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.galaxyNodeExpansionCandidates(nodeId),
        data: {'count': count},
      );
      final payload = response.data;
      if (payload == null) {
        throw Exception('Expansion candidates payload is missing');
      }
      return _sanitizeExpansionCandidates(
        NodeExpansionCandidatesResponse.fromJson(payload),
      );
    } on DioException catch (e) {
      throw Exception(
        _extractDetail(
          e,
          defaultMessage: 'Failed to generate node expansion candidates',
        ),
      );
    } catch (e) {
      debugPrint(
        'GalaxyRepository.generateExpansionCandidates unexpected error: $e',
      );
      throw Exception('An unexpected error occurred');
    }
  }

  Future<NodeExpansionApplyResult> applyExpansionCandidates(
    String nodeId, {
    required String promptVersion,
    required List<NodeExpansionCandidate> candidates,
  }) async {
    if (DemoDataService.isDemoMode) {
      return NodeExpansionApplyResult(
        success: true,
        requestedCount: candidates.length,
        appliedCount: candidates.length,
        createdCount: candidates.length,
        reusedCount: 0,
        createdNodes: candidates,
      );
    }
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.galaxyNodeExpansionApply(nodeId),
        data: {
          'prompt_version': promptVersion,
          'candidates': candidates
              .map((candidate) => candidate.toJson())
              .toList(growable: false),
        },
      );
      final payload = response.data;
      if (payload == null) {
        return NodeExpansionApplyResult(
          success: true,
          requestedCount: candidates.length,
          appliedCount: candidates.length,
          createdCount: candidates.length,
          reusedCount: 0,
          createdNodes: candidates,
        );
      }
      final created = _sanitizeCreatedCandidates(
        _parseAppliedNodes(payload['created_nodes']),
      );
      final reused = _sanitizeCreatedCandidates(
        _parseAppliedNodes(payload['reused_nodes']),
      );
      final createdCount =
          (payload['created_count'] as num?)?.toInt() ?? created.length;
      final reusedCount =
          (payload['reused_count'] as num?)?.toInt() ?? reused.length;
      final appliedCount = (payload['applied_count'] as num?)?.toInt() ??
          (createdCount + reusedCount);
      final requestedCount =
          (payload['requested_count'] as num?)?.toInt() ?? candidates.length;

      return NodeExpansionApplyResult(
        success: payload['success'] as bool? ?? true,
        requestedCount: requestedCount,
        appliedCount: appliedCount,
        createdCount: createdCount,
        reusedCount: reusedCount,
        createdNodes: created,
        reusedNodes: reused,
      );
    } on DioException catch (e) {
      throw Exception(
        _extractDetail(
          e,
          defaultMessage: 'Failed to apply node expansion candidates',
        ),
      );
    } catch (e) {
      debugPrint(
        'GalaxyRepository.applyExpansionCandidates unexpected error: $e',
      );
      throw Exception('An unexpected error occurred');
    }
  }

  String _extractDetail(
    DioException exception, {
    required String defaultMessage,
  }) {
    if (exception.response?.statusCode == 404) {
      return S.galaxyNodeNotExist;
    }
    final data = exception.response?.data;
    if (data is Map<String, dynamic>) {
      final detail = data['detail'];
      if (detail is String && detail.isNotEmpty) {
        return detail;
      }
    }
    return defaultMessage;
  }

  NodeExpansionCandidatesResponse _sanitizeExpansionCandidates(
    NodeExpansionCandidatesResponse response,
  ) =>
      NodeExpansionCandidatesResponse(
        triggerNodeId: response.triggerNodeId,
        promptVersion: response.promptVersion,
        candidates: _sanitizeCreatedCandidates(response.candidates),
      );

  List<NodeExpansionCandidate> _sanitizeCreatedCandidates(
    List<NodeExpansionCandidate> candidates,
  ) =>
      candidates
          .where(
            (candidate) =>
                _isRenderableNodeName(candidate.name) &&
                candidate.description.trim().isNotEmpty,
          )
          .toList(growable: false);

  List<NodeExpansionCandidate> _parseAppliedNodes(dynamic rawNodes) =>
      (rawNodes as List<dynamic>? ?? const <dynamic>[])
          .whereType<Map<String, dynamic>>()
          .map(
            (item) => NodeExpansionCandidate(
              candidateId: item['id']?.toString() ?? '',
              name: item['name']?.toString() ?? '',
              nameEn: item['name_en']?.toString(),
              description: item['description']?.toString() ?? '',
              importanceLevel: (item['importance_level'] as num?)?.toInt() ?? 3,
              relationToTrigger: 'related',
              relationStrength: 0.7,
              keywords: ((item['tags'] as List<dynamic>?) ?? const <dynamic>[])
                  .map((tag) => tag.toString())
                  .toList(growable: false),
              sectorWeights:
                  ((item['sector_weights'] as Map<String, dynamic>?) ??
                          const <String, dynamic>{})
                      .map(
                (key, value) => MapEntry(
                  key,
                  (value as num?)?.toDouble() ?? 0,
                ),
              ),
            ),
          )
          .toList(growable: false);

  bool _isRenderableNodeName(String name) {
    final trimmed = name.trim();
    if (trimmed.isEmpty || trimmed.contains('�')) {
      return false;
    }
    if (trimmed.length > 36) {
      return false;
    }
    if (RegExp(r'^J\d', caseSensitive: false).hasMatch(trimmed)) {
      return false;
    }
    if (RegExp(r'^[a-zA-Z]\d{2,}$').hasMatch(trimmed)) {
      return false;
    }
    if (trimmed.toLowerCase() == 'null') {
      return false;
    }
    return !RegExp(r'^[?？·•\-_=\s]+$').hasMatch(trimmed);
  }
}
