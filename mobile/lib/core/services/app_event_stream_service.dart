import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';

final appEventStreamServiceProvider = Provider<AppEventStreamService>(
  (ref) => AppEventStreamService(ref.read(apiClientProvider)),
);

class AppEventStreamService {
  AppEventStreamService(this._apiClient);

  final ApiClient _apiClient;

  Future<void> ingestEvents(List<Map<String, dynamic>> events) async {
    if (events.isEmpty) {
      return;
    }
    try {
      await _apiClient.post<dynamic>(
        ApiEndpoints.eventsIngest,
        data: {'events': events},
      );
    } catch (error) {
      debugPrint('Failed to ingest app events: $error');
    }
  }

  Future<void> recordPredictionFeedback({
    required String predictionId,
    required String feedbackType,
    required String actionType,
    required String surface,
    String? suggestedPrompt,
    String? entityType,
    String? entityId,
    Map<String, dynamic>? extraPayload,
  }) => ingestEvents([
      _buildEvent(
        eventType: 'prediction_$feedbackType',
        source: 'prediction_surface',
        entities: {
          'prediction_id': predictionId,
          if (entityType != null) 'entity_type': entityType,
          if (entityId != null) 'entity_id': entityId,
        },
        payload: {
          'action_type': actionType,
          'surface': surface,
          if (suggestedPrompt != null && suggestedPrompt.isNotEmpty)
            'suggested_prompt': suggestedPrompt,
          ...?extraPayload,
        },
      ),
    ]);

  Future<void> recordLearningPathGenerated({
    required String targetNodeId,
    String? planId,
    List<String> taskIds = const <String>[],
  }) => ingestEvents([
      _buildEvent(
        eventType: 'learning_path_generated',
        source: 'learning_path',
        entities: {
          'target_node_id': targetNodeId,
          if (planId != null && planId.isNotEmpty) 'plan_id': planId,
          if (taskIds.isNotEmpty) 'task_ids': taskIds,
        },
        payload: {
          'task_count': taskIds.length,
        },
      ),
    ]);

  Future<void> recordSharedResourceAction({
    required String action,
    required String sharedResourceId,
    required String resourceType,
    String? resourceId,
    String? adoptedEntityId,
  }) => ingestEvents([
      _buildEvent(
        eventType: 'shared_resource_$action',
        source: 'community_share',
        entities: {
          'shared_resource_id': sharedResourceId,
          'resource_type': resourceType,
          if (resourceId != null) 'resource_id': resourceId,
          if (adoptedEntityId != null) 'adopted_entity_id': adoptedEntityId,
        },
      ),
    ]);

  Future<void> recordEntityExecution({
    required String entityType,
    required String entityId,
    required String actionType,
    required String source,
    Map<String, dynamic>? payload,
  }) => ingestEvents([
      _buildEvent(
        eventType: 'entity_execution',
        source: source,
        entities: {
          'entity_type': entityType,
          'entity_id': entityId,
        },
        payload: {
          'action_type': actionType,
          ...?payload,
        },
      ),
    ]);

  Map<String, dynamic> _buildEvent({
    required String eventType,
    required String source,
    Map<String, dynamic>? entities,
    Map<String, dynamic>? payload,
  }) {
    final tsMs = DateTime.now().millisecondsSinceEpoch;
    return {
      'event_id': '$eventType:$tsMs:${identityHashCode(this)}',
      'event_type': eventType,
      'schema_version': 'event.v1',
      'source': source,
      'ts_ms': tsMs,
      if (entities != null && entities.isNotEmpty) 'entities': entities,
      if (payload != null && payload.isNotEmpty) 'payload': payload,
    };
  }
}
