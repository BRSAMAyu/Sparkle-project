import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/constants/api_constants.dart';
import 'package:sparkle/core/models/user_state_models.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/tracing/tracing_service.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/models/offline_chat_message.dart';
import 'package:sparkle/core/offline/offline_message_queue_service.dart';
import 'package:sparkle/features/aurora/presentation/providers/emotion_state_provider.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';
import 'package:sparkle/features/chat/data/models/reasoning_step_model.dart';
import 'package:web_socket_channel/io.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

/// Decode a value that may be a Map or a JSON-encoded string into a Map.
/// Backend sometimes sends review_data as a JSON string.
Map<String, dynamic>? _decodeMapOrString(dynamic value) {
  if (value is Map<String, dynamic>) return value;
  if (value is String && value.isNotEmpty) {
    try {
      final decoded = json.decode(value);
      if (decoded is Map<String, dynamic>) return decoded;
    } catch (_) {}
  }
  return null;
}

List<Map<String, dynamic>>? _decodeMapListOrString(dynamic value) {
  dynamic decoded = value;
  if (value is String && value.isNotEmpty) {
    try {
      decoded = json.decode(value);
    } catch (_) {
      return null;
    }
  }
  if (decoded is List) {
    final items = decoded
        .whereType<Map<dynamic, dynamic>>()
        .map(Map<String, dynamic>.from)
        .toList();
    return items.isEmpty ? null : items;
  }
  return null;
}

Map<String, dynamic>? _normalizeMetadata(dynamic raw) {
  final metadata = _decodeMapOrString(raw);
  if (metadata == null) {
    return null;
  }

  final normalized = Map<String, dynamic>.from(metadata);
  final directUserState = _decodeUserStatePayload(normalized['user_state_v1']);
  if (directUserState != null) {
    normalized['user_state_v1'] = directUserState;
  }

  final structuredAdjustments = _decodeMapListOrString(
    normalized['structured_cognitive_adjustments'],
  );
  if (structuredAdjustments != null) {
    normalized['structured_cognitive_adjustments'] = structuredAdjustments;
  }

  final profileContext = _decodeMapOrString(normalized['profile_context']);
  if (profileContext != null) {
    final userState = _decodeUserStatePayload(profileContext['user_state_v1']);
    normalized['profile_context'] = {
      ...profileContext,
      if (userState != null) 'user_state_v1': userState,
    };
  }

  return normalized;
}

Map<String, dynamic>? _decodeUserStatePayload(dynamic value) {
  final payload = _decodeMapOrString(value);
  if (payload == null || payload.isEmpty) {
    return null;
  }

  // Run the Stage 35 typed parser here so REST/WS payloads share one schema path.
  UserStateV1Model.fromJson(payload);
  return payload;
}

bool _isTrue(dynamic value) {
  if (value is bool) {
    return value;
  }
  if (value is String) {
    return value.toLowerCase() == 'true';
  }
  if (value is num) {
    return value != 0;
  }
  return false;
}

String? _normalizeFinishReason(dynamic raw) {
  final finishReason = raw?.toString().trim();
  if (finishReason == null ||
      finishReason.isEmpty ||
      finishReason.toUpperCase() == 'NULL') {
    return null;
  }
  return finishReason;
}

bool _isContinueFinishReason(String? finishReason) =>
    finishReason?.toUpperCase() == 'CONTINUE';

Map<String, dynamic>? _extractDagExecutionMetadata(
  Map<String, dynamic>? metadata,
) {
  if (metadata == null) {
    return null;
  }
  final raw = metadata['dag_execution_event'];
  if (raw is Map<String, dynamic>) {
    return raw;
  }
  if (raw is String && raw.isNotEmpty) {
    try {
      final decoded = json.decode(raw);
      if (decoded is Map<String, dynamic>) {
        return decoded;
      }
    } catch (_) {}
  }
  return null;
}

Map<String, dynamic> _extractAuroraStateBandPayload(
  Map<String, dynamic> data,
) {
  final payload = data['payload'] ?? data['data'] ?? data['state'];
  if (payload is Map<String, dynamic>) {
    return payload;
  }
  if (payload is Map) {
    return Map<String, dynamic>.from(payload);
  }
  return data;
}

/// Parse JSON event in isolate to avoid blocking main thread
ChatStreamEvent _parseChatEvent(String jsonString) {
  try {
    final data = json.decode(jsonString) as Map<String, dynamic>;

    // Basic validation
    if (!data.containsKey('type')) {
      return ErrorEvent(
        code: 'INVALID_FORMAT',
        message: S.chatErrorMissingTypeField,
        retryable: false,
      );
    }

    final type = data['type'] as String?;
    final responseId = data['response_id'] as String?;
    final traceId = data['trace_id'] as String?;
    final workflowId = data['workflow_id'] as String?;
    final promptVersion = data['prompt_version'] as String?;
    final sessionId = data['session_id'] as String?;
    final finishReason = _normalizeFinishReason(data['finish_reason']);

    switch (type) {
      case 'aurora_state_band':
        final metadata = _normalizeMetadata(data['metadata']);
        return AuroraStateBandEvent(
          stateData: _extractAuroraStateBandPayload(data),
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
          metadata: metadata,
          sessionId: sessionId,
        );

      case 'delta':
        final metadata = _normalizeMetadata(data['metadata']);
        final dagData = _extractDagExecutionMetadata(metadata);
        final dagSignal = DagExecutionSignal.fromDynamic(dagData);
        final deltaContent = data['delta'] as String? ?? '';

        if (dagSignal != null && deltaContent.isEmpty) {
          return DagExecutionEvent(
            signal: dagSignal,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
            metadata: metadata,
          );
        }

        // Check for transparency events (透明化与信任构建链路)
        if (metadata != null && metadata['event_type'] == 'transparency') {
          final eventPayload = metadata['event_payload'] as String?;
          if (eventPayload != null && eventPayload.isNotEmpty) {
            try {
              final eventData =
                  json.decode(eventPayload) as Map<String, dynamic>;
              final eventType = eventData['type'] as String?;

              if (eventType == 'transparency_step') {
                final stepData = eventData['data'] as Map<String, dynamic>?;
                return TransparencyStepEvent(
                  stepData: stepData ?? eventData,
                  responseId: responseId,
                  traceId: traceId,
                  workflowId: workflowId,
                  promptVersion: promptVersion,
                );
              } else if (eventType == 'transparency_complete') {
                final transData = eventData['data'] as Map<String, dynamic>?;
                return TransparencyCompleteEvent(
                  transparencyData: transData != null
                      ? TransparencyData.fromJson(transData)
                      : null,
                  responseId: responseId,
                  traceId: traceId,
                  workflowId: workflowId,
                  promptVersion: promptVersion,
                );
              }
            } catch (e) {
              // If parsing fails, fall through to regular text event
              debugPrint('Failed to parse transparency event: $e');
            }
          }
        }

        // Check for orchestration trace events
        if (metadata != null &&
            metadata['event_type'] == 'orchestration_trace') {
          final tracePayload = metadata['trace'] as String?;
          if (tracePayload != null && tracePayload.isNotEmpty) {
            try {
              final traceData =
                  json.decode(tracePayload) as Map<String, dynamic>;
              return OrchestrationTraceEvent(
                traceData: traceData,
                responseId: responseId,
                traceId: traceId,
                workflowId: workflowId,
                promptVersion: promptVersion,
              );
            } catch (e) {
              debugPrint('Failed to parse orchestration trace: $e');
            }
          }
        }

        if (metadata != null && metadata['event_type'] == 'run_ledger') {
          final ledgerPayload = metadata['payload'] as String?;
          if (ledgerPayload != null && ledgerPayload.isNotEmpty) {
            try {
              final decoded =
                  json.decode(ledgerPayload) as Map<String, dynamic>;
              final summaryJson = decoded['summary'] as Map<String, dynamic>?;
              final latestEventJson =
                  decoded['latest_event'] as Map<String, dynamic>?;
              if (summaryJson != null) {
                return RunLedgerSnapshotEvent(
                  summary: RunLedgerSummary.fromJson(summaryJson),
                  latestEvent: latestEventJson != null
                      ? RunLedgerEvent.fromJson(latestEventJson)
                      : null,
                  responseId: responseId,
                  traceId: traceId,
                  workflowId: workflowId,
                  promptVersion: promptVersion,
                );
              }
            } catch (e) {
              debugPrint('Failed to parse run ledger event: $e');
            }
          }
        }

        // Check for mode suggestion events
        if (metadata != null && metadata['event_type'] == 'mode_suggestion') {
          final suggestionPayload = metadata['suggestion'] as String?;
          if (suggestionPayload != null && suggestionPayload.isNotEmpty) {
            try {
              final suggestion =
                  json.decode(suggestionPayload) as Map<String, dynamic>;
              return ModeSuggestionEvent(
                suggestion: suggestion,
                responseId: responseId,
                traceId: traceId,
                workflowId: workflowId,
                promptVersion: promptVersion,
              );
            } catch (e) {
              debugPrint('Failed to parse mode suggestion: $e');
            }
          }
        }

        if (metadata != null && metadata['event_type'] == 'routing_preview') {
          final payload = metadata['payload'] as String?;
          if (payload != null && payload.isNotEmpty) {
            try {
              final preview = json.decode(payload) as Map<String, dynamic>;
              return RoutingPreviewEvent(
                preview: preview,
                responseId: responseId,
                traceId: traceId,
                workflowId: workflowId,
                promptVersion: promptVersion,
              );
            } catch (e) {
              debugPrint('Failed to parse routing preview: $e');
            }
          }
        }

        if (metadata != null && metadata['event_type'] == 'agent_turn') {
          final payload = metadata['payload'] as String?;
          if (payload != null && payload.isNotEmpty) {
            try {
              final turn = json.decode(payload) as Map<String, dynamic>;
              return AgentTurnEvent(
                turn: turn,
                responseId: responseId,
                traceId: traceId,
                workflowId: workflowId,
                promptVersion: promptVersion,
              );
            } catch (e) {
              debugPrint('Failed to parse agent turn: $e');
            }
          }
        }

        // Check for agent activity events
        if (metadata != null && metadata['event_type'] == 'agent_activity') {
          final activityPayload = metadata['payload'] as String?;
          if (activityPayload != null && activityPayload.isNotEmpty) {
            try {
              final activityData =
                  json.decode(activityPayload) as Map<String, dynamic>;
              return AgentActivityEvent.fromJson(activityData);
            } catch (e) {
              debugPrint('Failed to parse agent activity: $e');
            }
          }
        }

        // Check for state change events (计划归档/恢复/删除等重大状态变更)
        if (metadata != null && metadata['state_change_event'] != null) {
          final stateChangeData =
              metadata['state_change_event'] as Map<String, dynamic>;
          return StateChangeEvent(
            changeData: stateChangeData,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }

        // Check for sprint mode switch
        if (metadata != null && _isTrue(metadata['switch_to_sprint'])) {
          return SprintModeSwitchEvent(
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }

        // Phase 2b: Check if this delta contains content review data
        if (metadata != null && _isTrue(metadata['has_review_result'])) {
          final reviewData = _decodeMapOrString(metadata['review_data']);
          return ContentReviewWidgetEvent(
            reviewData: reviewData ?? metadata,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }

        // Check if this delta contains collaboration timeline data
        if (metadata != null) {
          final collaborationData =
              metadata['collaboration_timeline'] as Map<String, dynamic>?;

          if (collaborationData != null) {
            return CollaborationTimelineEvent(
              collaborationData: collaborationData,
              responseId: responseId,
              traceId: traceId,
              workflowId: workflowId,
              promptVersion: promptVersion,
            );
          }

          final visualization =
              metadata['visualization'] as Map<String, dynamic>?;
          final timeline = visualization?['timeline'] as List<dynamic>?;
          if (timeline != null && timeline.isNotEmpty) {
            final workflowType = (metadata['workflow'] as String?) ??
                (visualization?['workflow_type'] as String?) ??
                'unknown';
            final executionTime = metadata['execution_time'];
            final executionTimeMs =
                executionTime is num ? (executionTime * 1000).round() : 0;

            return CollaborationTimelineEvent(
              collaborationData: {
                'workflow_type': workflowType,
                'execution_time_ms': executionTimeMs,
                'steps': timeline,
              },
              responseId: responseId,
              traceId: traceId,
              workflowId: workflowId,
              promptVersion: promptVersion,
            );
          }
        }

        // Check if this delta contains plan review data
        if (metadata != null && _isTrue(metadata['requires_review'])) {
          final reviewData = _decodeMapOrString(metadata['review_data']);
          return PlanReviewWidgetEvent(
            reviewData: reviewData ?? metadata,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }

        // Phase 2b: Check if this delta contains reflection result
        if (metadata != null && _isTrue(metadata['has_reflection_result'])) {
          return ContentReflectionResultEvent(
            reflectionData: metadata,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }

        // Spine: StaleStateGuard recovery card
        if (metadata != null && metadata['spine_stale_card'] != null) {
          final staleData = _decodeMapOrString(metadata['spine_stale_card']);
          if (staleData != null) {
            return StaleRecoveryEvent(
              staleData: staleData,
              responseId: responseId,
              traceId: traceId,
              workflowId: workflowId,
              promptVersion: promptVersion,
            );
          }
        }

        // Spine: UserVisibleReceipt card
        if (metadata != null && metadata['spine_receipt'] != null) {
          final receiptData = _decodeMapOrString(metadata['spine_receipt']);
          if (receiptData != null) {
            return SpineReceiptEvent(
              receiptData: receiptData,
              responseId: responseId,
              traceId: traceId,
              workflowId: workflowId,
              promptVersion: promptVersion,
            );
          }
        }

        // Spine: UX risk warning (divine moment #5 阻止低收益)
        if (metadata != null && metadata['spine_ux_warning'] != null) {
          final warningData = _decodeMapOrString(metadata['spine_ux_warning']);
          if (warningData != null) {
            return UXWarningEvent(
              warningData: warningData,
              responseId: responseId,
              traceId: traceId,
              workflowId: workflowId,
              promptVersion: promptVersion,
            );
          }
        }

        // Spine: Community hint card (divine moment #6 社群经验转策略)
        if (metadata != null && metadata['spine_community_hint'] != null) {
          final hintData = _decodeMapOrString(metadata['spine_community_hint']);
          if (hintData != null) {
            return CommunityHintEvent(
              hintData: hintData,
              responseId: responseId,
              traceId: traceId,
              workflowId: workflowId,
              promptVersion: promptVersion,
            );
          }
        }

        // Spine: Growth card (divine moment #1 看见坚持)
        if (metadata != null && metadata['spine_growth_card'] != null) {
          final growthData = _decodeMapOrString(metadata['spine_growth_card']);
          if (growthData != null) {
            return GrowthCardEvent(
              cardData: growthData,
              responseId: responseId,
              traceId: traceId,
              workflowId: workflowId,
              promptVersion: promptVersion,
            );
          }
        }

        // Spine: Goal Arbitration Card — multi-goal conflict surface
        if (metadata != null && metadata['spine_goal_arbitration'] != null) {
          final arbData =
              _decodeMapOrString(metadata['spine_goal_arbitration']);
          if (arbData != null) {
            return GoalArbitrationEvent(
              arbData: arbData,
              responseId: responseId,
              traceId: traceId,
              workflowId: workflowId,
              promptVersion: promptVersion,
            );
          }
        }

        // Spine: Divine Moment Card — MAGIC-002 through MAGIC-006
        if (metadata != null && metadata['spine_divine_moment'] != null) {
          final divineData = _decodeMapOrString(metadata['spine_divine_moment']);
          if (divineData != null) {
            return DivineMomentEvent(
              cardData: divineData,
              responseId: responseId,
              traceId: traceId,
              workflowId: workflowId,
              promptVersion: promptVersion,
            );
          }
        }

        // Spine: Degraded mode indicator (STAB-012)
        if (metadata != null && metadata['spine_degraded'] == 'true') {
          return SpineDegradedEvent(
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }

        // Spine: Causal trace created — timeline integration (GAP-P2-2)
        if (metadata != null && metadata['spine_causal_trace_id'] != null) {
          final causalId = metadata['spine_causal_trace_id'];
          if (causalId is String && causalId.isNotEmpty) {
            return CausalTraceEvent(
              traceIdValue: causalId,
              responseId: responseId,
              traceId: traceId,
              workflowId: workflowId,
              promptVersion: promptVersion,
            );
          }
        }

        return TextEvent(
          content: deltaContent,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
          metadata: metadata,
        );

      case 'status_update':
        final status = data['status'] as Map<String, dynamic>?;
        final metadata = data['metadata'] as Map<String, dynamic>?;
        final dagData = _extractDagExecutionMetadata(metadata);
        final dagSignal = DagExecutionSignal.fromDynamic(dagData);
        if (status != null) {
          final dagDetails = dagSignal?.statusDetails;
          return StatusUpdateEvent(
            state: status['state'] as String? ?? 'UNKNOWN',
            details: dagDetails ?? status['details'] as String? ?? '',
            currentAgentName: status['current_agent_name'] as String?,
            activeAgentType: status['active_agent'] as String?,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
            metadata: metadata,
          );
        }
        if (dagSignal != null) {
          return DagExecutionEvent(
            signal: dagSignal,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
            metadata: metadata,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'tool_call':
        final toolCall = data['tool_call'] as Map<String, dynamic>?;
        if (toolCall != null) {
          return ToolStartEvent(
            toolName: toolCall['name'] as String? ?? 'unknown',
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'tool_result':
        final toolResult = data['tool_result'] as Map<String, dynamic>?;
        if (toolResult != null) {
          final widgetData = toolResult['widget_data'];
          final toolCallId = toolResult['tool_call_id'] as String?;
          if (widgetData is Map<String, dynamic> &&
              toolCallId != null &&
              (widgetData['tool_result_id'] == null ||
                  widgetData['tool_result_id'].toString().isEmpty)) {
            widgetData['tool_result_id'] = toolCallId;
            toolResult['widget_data'] = widgetData;
          }
          return ToolResultEvent(
            result: ToolResultModel.fromJson(toolResult),
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'intervention':
        final intervention = data['intervention'] as Map<String, dynamic>?;
        if (intervention == null) {
          return UnknownEvent(
            data: data,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        final content = intervention['content'] as Map<String, dynamic>? ?? {};
        final widgetType =
            content['widget_type'] as String? ?? 'intervention_card';
        final widgetData = (content['widget_data'] as Map<String, dynamic>?) ??
            Map<String, dynamic>.from(content);

        widgetData['intervention_id'] ??= intervention['id'];
        widgetData['intervention_topic'] ??= intervention['topic'];
        widgetData['intervention_level'] ??= intervention['level'];

        return WidgetEvent(
          widgetType: widgetType,
          widgetData: widgetData,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'widget':
        final widgetType = data['widget_type'] as String?;
        final widgetData = data['widget_data'] as Map<String, dynamic>?;
        if (widgetType != null && widgetData != null) {
          return WidgetEvent(
            widgetType: widgetType,
            widgetData: widgetData,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'full_text':
        final metadata = _normalizeMetadata(data['metadata']);
        return FullTextEvent(
          content: data['full_text'] as String? ?? '',
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
          metadata: metadata,
        );

      case 'done':
        final metadata = _normalizeMetadata(data['metadata']);
        if (_isContinueFinishReason(finishReason)) {
          return ContinueEvent(
            finishReason: finishReason,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
            metadata: metadata,
            sessionId: sessionId,
          );
        }
        return DoneEvent(
          finishReason: finishReason,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
          metadata: metadata,
          sessionId: sessionId,
        );

      case 'error':
        final error = data['error'] as Map<String, dynamic>?;
        if (error != null) {
          final code = (error['error_code'] as String?) ?? 'UNKNOWN';
          return ErrorEvent(
            code: code,
            message: error['message'] as String? ?? S.chatWsUnknownError,
            retryable: error['retryable'] as bool? ?? false,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        final topLevelCode =
            (data['error_code'] as String?) ?? (data['code'] as String?);
        final topLevelMessage = data['message'] as String?;
        if (topLevelCode != null || topLevelMessage != null) {
          return ErrorEvent(
            code: topLevelCode ?? 'UNKNOWN',
            message: topLevelMessage ?? S.chatWsUnknownError,
            retryable: data['retryable'] as bool? ?? false,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return ErrorEvent(
          code: 'UNKNOWN',
          message: S.chatWsUnknownError,
          retryable: false,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'usage':
        final usage = data['usage'] as Map<String, dynamic>?;
        if (usage != null) {
          return UsageEvent(
            promptTokens: usage['prompt_tokens'] as int? ?? 0,
            completionTokens: usage['completion_tokens'] as int? ?? 0,
            totalTokens: usage['total_tokens'] as int? ?? 0,
            costMicroUsd: usage['cost_micro_usd'] as int?,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'citations':
        final list = data['citations'] as List<dynamic>?;
        if (list != null) {
          return CitationEvent(
            citations: list.map((e) => e as Map<String, dynamic>).toList(),
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'pong':
        // 心跳响应，静默处理
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'message_ack':
      case 'ack':
        final messageId = data['message_id'] as String?;
        final status = data['status'] as String? ?? 'received';
        final timestamp = data['timestamp'] as int? ??
            data['server_ts'] as int? ??
            DateTime.now().millisecondsSinceEpoch;
        if (messageId != null) {
          return AckEvent(
            messageId: messageId,
            status: status,
            timestamp: timestamp,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'message_nack':
      case 'nack':
        final messageId = data['message_id'] as String?;
        final errorCode = data['error_code'] as String? ?? 'unknown';
        final errorMessage =
            data['error_message'] as String? ?? S.chatWsUnknownError;
        final retryAfterMs = data['retry_after_ms'] as int?;
        if (messageId != null) {
          return NackEvent(
            messageId: messageId,
            errorCode: errorCode,
            errorMessage: errorMessage,
            retryAfterMs: retryAfterMs,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'meta':
      case 'metadata':
        return MetaEvent(
          meta: Map<String, dynamic>.from(
            (data['meta'] as Map?)?.cast<String, dynamic>() ?? data,
          ),
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
          sessionId: sessionId,
        );

      case 'reasoning_step':
        final step = data['step'] as Map<String, dynamic>?;
        if (step != null) {
          return ReasoningStepEvent(
            step: ReasoningStep.fromJson(step),
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'action_status':
        final actionId = data['action_id'] as String?;
        final status = data['status'] as String?;
        if (actionId != null && status != null) {
          return ActionStatusEvent(
            actionId: actionId,
            status: status,
            message: data['message'] as String?,
            widgetType: data['widget_type'] as String?,
            timestamp: data['timestamp'] as int?,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'plan_review_status':
        final reviewId = data['review_id'] as String?;
        final status = data['status'] as String?;
        if (reviewId != null && status != null) {
          return PlanReviewStatusEvent(
            reviewId: reviewId,
            status: status,
            message: data['message'] as String?,
            userDecision: data['user_decision'] as String?,
            timestamp: data['timestamp'] as int?,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'plan_review_widget':
        final reviewData = _decodeMapOrString(data['review_data']);
        if (reviewData != null) {
          return PlanReviewWidgetEvent(
            reviewData: reviewData,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'intervention_feedback_ack':
        final requestId = data['request_id'] as String?;
        final status = data['status'] as String?;
        if (requestId != null && status != null) {
          return ActionStatusEvent(
            actionId: requestId,
            status: status,
            message: data['message'] as String?,
            widgetType: 'intervention',
            timestamp: data['timestamp'] as int?,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'response_feedback_ack':
        final responseId = data['response_id'] as String?;
        final status = data['status'] as String?;
        if (responseId != null && status != null) {
          return ActionStatusEvent(
            actionId: responseId,
            status: status,
            message: data['message'] as String?,
            widgetType: 'response_feedback',
            timestamp: data['timestamp'] as int?,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'milestone_proposal':
        final proposalData = data['proposal'] as Map<String, dynamic>?;
        if (proposalData != null) {
          return MilestoneProposalEvent(
            proposalData: proposalData,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'achievement_unlock':
        final achievementData =
            data['achievement_data'] as Map<String, dynamic>?;
        if (achievementData != null) {
          return AchievementUnlockEvent(
            achievementData: achievementData,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'achievement_milestone':
        final milestoneData = data['data'] as Map<String, dynamic>?;
        if (milestoneData != null) {
          return AchievementMilestoneEvent(
            milestoneData: milestoneData,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'transparency_step':
        // 透明度步骤事件
        final stepData = data['step_data'] as Map<String, dynamic>?;
        if (stepData != null) {
          return TransparencyStepEvent(
            stepData: stepData,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'transparency_complete':
        // 透明度完整数据事件
        final transData = data['transparency'] as Map<String, dynamic>?;
        if (transData != null) {
          return TransparencyCompleteEvent(
            transparencyData: TransparencyData.fromJson(transData),
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'run_ledger':
        final ledgerData = data['payload'] as Map<String, dynamic>?;
        final summaryJson = ledgerData?['summary'] as Map<String, dynamic>?;
        final latestEventJson =
            ledgerData?['latest_event'] as Map<String, dynamic>?;
        if (summaryJson != null) {
          return RunLedgerSnapshotEvent(
            summary: RunLedgerSummary.fromJson(summaryJson),
            latestEvent: latestEventJson != null
                ? RunLedgerEvent.fromJson(latestEventJson)
                : null,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

      case 'notification':
        // 实时通知推送事件
        return NotificationEvent.fromJson(data);

      case 'action_feedback':
        return ActionFeedbackAckEvent(
          actionId: data['action_id'] as String? ?? '',
          status: data['status'] as String?,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
          sessionId: sessionId,
        );

      case 'focus_completed':
        return FocusCompletedAckEvent(
          focusSessionId: data['focus_session_id'] as String? ?? '',
          duration: data['duration'] as int?,
          success: data['success'] as bool?,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
          sessionId: sessionId,
        );

      case 'update_node_mastery':
      case 'ack_update_node_mastery':
        return NodeMasteryAckEvent(
          nodeId: data['node_id'] as String? ?? '',
          masteryLevel: (data['mastery_level'] as num?)?.toDouble(),
          delta: (data['delta'] as num?)?.toDouble(),
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
          sessionId: sessionId,
        );

      case 'error_update_node_mastery':
        return NodeMasteryErrorEvent(
          nodeId: data['node_id'] as String? ?? '',
          error: data['error'] as String?,
          retryable: data['retryable'] as bool?,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
          sessionId: sessionId,
        );

      default:
        if (finishReason != null) {
          final metadata = _normalizeMetadata(data['metadata']);
          if (_isContinueFinishReason(finishReason)) {
            return ContinueEvent(
              finishReason: finishReason,
              responseId: responseId,
              traceId: traceId,
              workflowId: workflowId,
              promptVersion: promptVersion,
              metadata: metadata,
              sessionId: sessionId,
            );
          }
          return DoneEvent(
            finishReason: finishReason,
            responseId: responseId,
            traceId: traceId,
            workflowId: workflowId,
            promptVersion: promptVersion,
            metadata: metadata,
            sessionId: sessionId,
          );
        }
        return UnknownEvent(
          data: data,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
          sessionId: sessionId,
        );
    }
  } catch (e) {
    return ErrorEvent(
      code: 'PARSE_ERROR',
      message: e.toString(),
      retryable: false,
    );
  }
}

@visibleForTesting
ChatStreamEvent parseChatEventForTest(String jsonString) =>
    _parseChatEvent(jsonString);

/// WebSocket 连接状态
enum WsConnectionState {
  disconnected,
  connecting,
  connected,
  reconnecting,
  failed,
}

/// 心跳指标
class HeartbeatMetrics {
  const HeartbeatMetrics({
    required this.rtt,
    required this.sentAt,
    this.receivedAt,
    this.consecutiveFailures = 0,
  });

  final Duration rtt;
  final DateTime sentAt;
  final DateTime? receivedAt;
  final int consecutiveFailures;

  bool get isTimeout => receivedAt == null;

  @override
  String toString() =>
      'HeartbeatMetrics(rtt: ${rtt.inMilliseconds}ms, failures: $consecutiveFailures)';
}

/// Factory for creating WebSocket channels (facilitates testing)
typedef WebSocketChannelFactory = WebSocketChannel Function(
  Uri uri, {
  Map<String, dynamic>? headers,
});

/// WebSocket 聊天服务 V2（完整的连接复用和状态管理）
class WebSocketChatServiceV2 with WidgetsBindingObserver {
  WebSocketChatServiceV2({
    required ProviderContainer container,
    String? baseUrl,
    WebSocketChannelFactory? channelFactory,
    bool enableReconnect = true,
    bool autoConnect = true,
    Duration terminalDoneFallbackDelay = const Duration(seconds: 2),
  })  : _container = container,
        baseUrl = baseUrl ?? ApiConstants.wsBaseUrl,
        _channelFactory = channelFactory,
        _enableReconnect = enableReconnect,
        _autoConnect = autoConnect,
        _terminalDoneFallbackDelay = terminalDoneFallbackDelay {
    WidgetsBinding.instance.addObserver(this);
    _offlineQueue = OfflineMessageQueueService(
      _container.read(localDatabaseProvider),
    );
  }

  static const List<Duration> _reconnectSchedule = <Duration>[
    Duration(milliseconds: 800),
    Duration(milliseconds: 1200),
    Duration(milliseconds: 2200),
    Duration(milliseconds: 4200),
    Duration(milliseconds: 8200),
    Duration(milliseconds: 12200),
  ];
  static const int _maxReconnectAttempts = 6;

  // Factory for creating channels
  final WebSocketChannelFactory? _channelFactory;
  final bool _enableReconnect;
  final bool _autoConnect;
  final Duration _terminalDoneFallbackDelay;
  final ProviderContainer _container;

  // WebSocket 连接
  WebSocketChannel? _channel;
  StreamSubscription<dynamic>? _socketSubscription;
  Future<void> _incomingMessageChain = Future<void>.value();
  bool _disposed = false;
  int _connGen = 0;

  // 每个请求独立的消息流，避免不同 run 之间事件串流
  final Map<String, StreamController<ChatStreamEvent>> _requestControllers = {};
  final Map<String, Timer> _terminalFallbackTimers = {};

  // 连接状态流
  final StreamController<WsConnectionState> _connectionStateController =
      StreamController<WsConnectionState>.broadcast();

  final String baseUrl;

  // 当前用户和会话
  String? _currentUserId;
  String? _currentSessionId;
  String? _currentToken;

  // 连接状态
  WsConnectionState _connectionState = WsConnectionState.disconnected;

  // 重连机制
  int _reconnectAttempts = 0;
  Timer? _reconnectTimer;

  // 心跳保活
  Timer? _heartbeatTimer;
  Timer? _heartbeatTimeoutTimer;
  static const Duration _heartbeatInterval = Duration(seconds: 30);
  static const Duration _heartbeatTimeout = Duration(
    seconds: 60,
  ); // 从 90s 降低到 60s
  int _consecutiveHeartbeatFailures = 0;
  static const int _maxConsecutiveHeartbeatFailures = 3;
  DateTime? _lastPongReceivedTime;
  DateTime? _lastPingSentTime;

  // 流式消息活跃标记 — 活跃时抑制心跳超时触发的重连
  bool _isStreamActive = false;
  DateTime? _lastStreamDataTime;

  // 心跳指标
  final _heartbeatMetricsController =
      StreamController<HeartbeatMetrics>.broadcast();
  Stream<HeartbeatMetrics> get heartbeatMetrics =>
      _heartbeatMetricsController.stream;

  // 消息队列（连接断开时暂存）
  final List<Map<String, dynamic>> _pendingMessages = [];

  // Offline persistent queue (R3 O-01: survive app kill)
  late final OfflineMessageQueueService _offlineQueue;

  // 401错误处理和Token刷新
  Completer<String>? _refreshCompleter;
  int _error401Count = 0;
  static const int _max401Retries = 1;

  /// Exposed for testing
  @visibleForTesting
  List<Map<String, dynamic>> get pendingMessages => _pendingMessages;

  /// Exposed for testing
  @visibleForTesting
  int get reconnectAttempts => _reconnectAttempts;

  /// 获取连接状态流
  Stream<WsConnectionState> get connectionStateStream =>
      _connectionStateController.stream;

  /// 当前连接状态
  WsConnectionState get connectionState => _connectionState;

  static const int _pendingMessageLimit = 50;

  /// 是否已连接
  bool get isConnected => _connectionState == WsConnectionState.connected;

  Future<void> ensureConnected({required String userId, String? token}) async {
    if (_disposed) {
      return;
    }
    if (_currentUserId != null && _currentUserId != userId) {
      _resetConnectionState();
    }
    if (_shouldConnect(userId, token)) {
      await _establishConnectionAsync(userId, token);
    }
  }

  /// 发送消息（复用连接）
  Stream<ChatStreamEvent> sendMessage({
    required String message,
    required String userId,
    String? sessionId,
    String? requestId,
    String? nickname,
    Map<String, dynamic>? extraContext,
    String? token,
    List<String>? fileIds,
    bool includeReferences = false,
    String? chatMode,
    bool? useDocumentContext,
  }) {
    // ✅ Fix H1: Reset connection state for new user session
    if (_currentUserId != null && _currentUserId != userId) {
      _resetConnectionState();
    }

    // 更新 session ID
    _currentSessionId = sessionId ?? _currentSessionId ?? _generateSessionId();

    final resolvedRequestId = requestId ?? _generateRequestId();
    late final StreamController<ChatStreamEvent> controller;
    controller = StreamController<ChatStreamEvent>(
      onCancel: () {
        final existing = _requestControllers[resolvedRequestId];
        if (identical(existing, controller)) {
          _requestControllers.remove(resolvedRequestId);
        }
        _cancelTerminalFallback(resolvedRequestId);
      },
    );
    _requestControllers[resolvedRequestId] = controller;

    // 检查是否需要建立连接
    if (_autoConnect && _shouldConnect(userId, token)) {
      _establishConnection(userId, token);
    }

    // 构建消息
    final messagePayload = {
      'message': message,
      'session_id': _currentSessionId,
      'request_id': resolvedRequestId,
      if (nickname != null) 'nickname': nickname,
      if (extraContext != null) 'extra_context': extraContext,
      if (fileIds != null && fileIds.isNotEmpty) 'file_ids': fileIds,
      if (includeReferences) 'include_references': true,
      if (chatMode != null) 'chat_mode': chatMode,
      if (useDocumentContext != null)
        'use_document_context': useDocumentContext,
    };

    // 发送或排队
    if (isConnected) {
      _persistOutgoingMessage(messagePayload);
      _sendMessage(messagePayload);
    } else {
      _log('⏳ Message queued (not connected yet)');
      // TRACKED(TD-001): Pending limit
      _enqueuePendingMessage(messagePayload);
    }

    return controller.stream;
  }

  /// 发送行动反馈（确认/拒绝）
  void sendActionFeedback({
    required String action,
    required String toolResultId,
    required String widgetType,
  }) {
    final feedback = {
      'type': 'action_feedback',
      'action': action, // 'confirm' or 'dismiss'
      'tool_result_id': toolResultId,
      'widget_type': widgetType,
      'timestamp': DateTime.now().toIso8601String(),
    };

    _sendMessage(feedback);
    _log('📤 Action feedback sent: $action for $widgetType');
  }

  /// 发送干预反馈（Intervention）
  void sendInterventionFeedback({
    required String requestId,
    required String feedbackType,
    Map<String, dynamic>? extraData,
  }) {
    final feedback = {
      'type': 'intervention_feedback',
      'request_id': requestId,
      'feedback_type': feedbackType,
      if (extraData != null) 'extra_data': extraData,
      'timestamp': DateTime.now().toIso8601String(),
    };

    _sendMessage(feedback);
    _log('📤 Intervention feedback sent: $feedbackType for $requestId');
  }

  /// 发送回复反馈（Thumbs up/down）
  void sendResponseFeedback({
    required String responseId,
    required String feedbackType,
    List<String>? reasons,
    String? freeText,
    String? workflowId,
    String? promptVersion,
    String? traceId,
    Map<String, dynamic>? meta,
  }) {
    final feedback = {
      'type': 'response_feedback',
      'response_id': responseId,
      'feedback_type': feedbackType,
      if (reasons != null && reasons.isNotEmpty) 'reasons': reasons,
      if (freeText != null && freeText.isNotEmpty) 'free_text': freeText,
      if (workflowId != null) 'workflow_id': workflowId,
      if (promptVersion != null) 'prompt_version': promptVersion,
      if (traceId != null) 'trace_id': traceId,
      if (meta != null) 'meta': meta,
      'timestamp': DateTime.now().toIso8601String(),
    };

    _sendMessage(feedback);
    _log('📤 Response feedback sent: $feedbackType for $responseId');
  }

  /// 发送计划审查反馈（Plan Review Feedback）
  void sendPlanReviewFeedback({
    required String reviewId,
    required String userDecision,
    String? planId,
    String? userComment,
    Map<String, dynamic>? modifications,
  }) {
    final feedback = {
      'type': 'plan_review_feedback',
      'review_id': reviewId,
      'user_decision': userDecision, // 'approve', 'reject', 'modify'
      if (planId != null && planId.isNotEmpty) 'plan_id': planId,
      if (userComment != null && userComment.isNotEmpty)
        'user_comment': userComment,
      if (modifications != null && modifications.isNotEmpty)
        'modifications': modifications,
      'timestamp': DateTime.now().toIso8601String(),
    };

    _sendMessage(feedback);
    _log('📤 Plan review feedback sent: $userDecision for $reviewId');
  }

  /// 发送专注完成事件
  void sendFocusCompleted({
    required String sessionId,
    required int actualDuration,
    List<String> completedTaskIds = const [],
  }) {
    final event = {
      'type': 'focus_completed',
      'session_id': sessionId,
      'actual_duration': actualDuration,
      'tasks_completed': completedTaskIds,
      'timestamp': DateTime.now().toIso8601String(),
    };

    _sendMessage(event);
    _log('📤 Focus completed event sent');
  }

  /// 判断是否需要建立连接
  bool _shouldConnect(String userId, String? token) {
    // 用户切换
    if (_currentUserId != null && _currentUserId != userId) {
      _log('👤 User changed, reconnecting...');
      _closeConnection();
      return true;
    }
    if (token != null && token.isNotEmpty && _currentToken != token) {
      _log('🔐 Token changed, reconnecting...');
      _closeConnection();
      return true;
    }

    // 未连接
    if (_connectionState == WsConnectionState.failed && !_enableReconnect) {
      return false;
    }

    if (_connectionState == WsConnectionState.disconnected ||
        _connectionState == WsConnectionState.failed) {
      return true;
    }

    return false;
  }

  /// 建立 WebSocket 连接
  void _establishConnection(String userId, String? token) {
    unawaited(_establishConnectionAsync(userId, token));
  }

  Future<void> _establishConnectionAsync(String userId, String? token) async {
    if (_connectionState == WsConnectionState.connecting ||
        _connectionState == WsConnectionState.connected) {
      _log('⚠️  Already connecting/connected');
      return;
    }

    final shouldUseRuntimeAuthResolution = _channelFactory == null;
    final effectiveToken = shouldUseRuntimeAuthResolution
        ? await _resolveAuthToken(token) ??
            await _resolveAuthToken(_currentToken)
        : token ?? _currentToken;
    _currentUserId = userId;
    _currentToken = effectiveToken;
    _updateConnectionState(WsConnectionState.connecting);

    try {
      // Web platform: headers not supported - throw explicit error
      if (kIsWeb) {
        throw UnsupportedError(
          'WebSocket header authentication is not supported on Web platform. '
          'Web browsers do not allow custom headers in WebSocket connections. '
          'Please configure the server to accept token via query parameter or use a proxy.',
        );
      }

      // Force secure WebSocket in production
      const isProduction = kReleaseMode;
      _log('📍 Original baseUrl: $baseUrl');
      final effectiveBaseUrl = _applyWebSocketSchemeForEnvironment(
        baseUrl,
        isProduction: isProduction,
      );
      _log('📍 Effective WebSocket URL: $effectiveBaseUrl');

      String? wsTicket;
      if (shouldUseRuntimeAuthResolution &&
          effectiveToken != null &&
          effectiveToken.isNotEmpty) {
        wsTicket = await _issueWsTicket();
      }

      final queryParameters = <String, String>{'user_id': userId};
      // P0-1: Include session_id on reconnect so backend can restore context
      if (_currentSessionId != null && _reconnectAttempts > 0) {
        queryParameters['session_id'] = _currentSessionId!;
      }
      if (wsTicket != null && wsTicket.isNotEmpty) {
        queryParameters['ticket'] = wsTicket;
      } else {
        // SECURITY: Never put JWT in URL query params — it leaks to server
        // logs, proxy logs, and browser history. Rely on Authorization header instead.
        _log('⚠️ WS ticket unavailable, using Authorization header only');
      }

      final wsUri = Uri.parse(
        '$effectiveBaseUrl/ws/chat',
      ).replace(queryParameters: queryParameters);
      _log('🔌 Connecting to: $wsUri');

      // Note: We still send Authorization header for reference, but WS uses query param
      final headers = <String, dynamic>{};
      if (effectiveToken != null && effectiveToken.isNotEmpty) {
        headers['Authorization'] = 'Bearer $effectiveToken';
      }
      // Headers are included but query param token is used as fallback

      if (_channelFactory != null) {
        _channel = _channelFactory!(
          wsUri,
          headers: headers.isEmpty ? null : headers,
        );
      } else {
        _channel = IOWebSocketChannel.connect(
          wsUri,
          headers: headers.isEmpty ? null : headers,
        );
      }

      // 监听 WebSocket 流
      _socketSubscription = _channel!.stream.listen(
        _queueIncomingMessage,
        onError: _handleConnectionError,
        onDone: _handleConnectionClosed,
        cancelOnError: false,
      );

      // 连接成功
      _updateConnectionState(WsConnectionState.connected);
      _reconnectAttempts = 0;

      // 启动心跳
      _startHeartbeat();

      // Restore pending messages from offline DB, then flush all pending
      // (must complete DB restore before flush to avoid message ordering issues)
      _restorePendingFromDb().then((_) => _flushPendingMessages());

      _log('✅ WebSocket connected');
    } catch (e) {
      _log('❌ Connection failed: $e');
      _handleConnectionError(e);
    }
  }

  Future<String?> _resolveAuthToken(String? candidate) async {
    final trimmed = candidate?.trim();
    if (trimmed != null && trimmed.isNotEmpty) {
      return trimmed;
    }

    try {
      final storedToken =
          await _container.read(authRepositoryProvider).getAccessToken();
      if (storedToken != null && storedToken.isNotEmpty) {
        return storedToken;
      }
    } catch (e) {
      _log('⚠️ Failed to resolve auth token from repository: $e');
    }

    return null;
  }

  Future<String?> _issueWsTicket() async {
    try {
      final response =
          await _container.read(apiClientProvider).post<dynamic>('/ws/ticket');
      final data = response.data;
      if (data is Map<String, dynamic>) {
        final ticket = data['ticket']?.toString();
        if (ticket != null && ticket.isNotEmpty) {
          return ticket;
        }
      }
    } catch (e) {
      _log('⚠️ Failed to issue WS ticket, falling back to direct auth: $e');
    }

    return null;
  }

  /// 更新连接状态
  void _updateConnectionState(WsConnectionState newState) {
    if (_connectionState != newState) {
      _connectionState = newState;
      if (!_connectionStateController.isClosed) {
        _connectionStateController.add(newState);
      }
      _log('📡 Connection state: ${newState.name}');
    }
  }

  void _safeAdd<T>(StreamController<T> controller, T event) {
    if (_disposed || controller.isClosed) return;
    controller.add(event);
  }

  void _safeClose<T>(StreamController<T> controller) {
    if (_disposed || controller.isClosed) return;
    unawaited(controller.close());
  }

  void _cancelTerminalFallback(String requestId) {
    final timer = _terminalFallbackTimers.remove(requestId);
    timer?.cancel();
  }

  void _scheduleTerminalFallback(String requestId) {
    if (_terminalDoneFallbackDelay <= Duration.zero) {
      return;
    }
    _cancelTerminalFallback(requestId);
    _terminalFallbackTimers[requestId] = Timer(_terminalDoneFallbackDelay, () {
      final controller = _requestControllers[requestId];
      if (controller == null || controller.isClosed || _disposed) {
        _terminalFallbackTimers.remove(requestId);
        return;
      }
      _safeAdd(controller, DoneEvent(finishReason: 'full_text_idle_fallback'));
      _requestControllers.remove(requestId);
      _terminalFallbackTimers.remove(requestId);
      _safeClose(controller);
      _isStreamActive = false;
    });
  }

  String? _extractRequestIdFromRawMessage(String data) {
    try {
      final jsonData = json.decode(data) as Map<String, dynamic>;
      final requestId = jsonData['request_id'] as String?;
      if (requestId != null && requestId.isNotEmpty) {
        return requestId;
      }
      // Fallback: some error payloads (e.g. message_nack) use message_id
      final messageId = jsonData['message_id'] as String?;
      if (messageId != null && messageId.isNotEmpty) {
        return messageId;
      }
    } catch (_) {}
    return null;
  }

  void _routeEventToRequest(String? requestId, ChatStreamEvent event) {
    var targetRequestId = requestId;
    if ((targetRequestId == null || targetRequestId.isEmpty) &&
        _requestControllers.length == 1) {
      targetRequestId = _requestControllers.keys.first;
    }
    if (targetRequestId == null || targetRequestId.isEmpty) {
      return;
    }
    final controller = _requestControllers[targetRequestId];
    if (controller == null) {
      return;
    }
    _safeAdd(controller, event);

    // Mark message as acked in offline DB (R3 O-01)
    if (event is AckEvent) {
      unawaited(_offlineQueue.markAcked(
        targetRequestId,
        serverMessageId: event.messageId,
      ));
    }

    if (event is FullTextEvent) {
      _scheduleTerminalFallback(targetRequestId);
      return;
    }
    if (event is ContinueEvent) {
      // CONTINUE is the authoritative segment boundary for Aurora multi-turn
      // streams. Keep the request open and avoid synthesizing a false DoneEvent.
      _cancelTerminalFallback(targetRequestId);
      return;
    }
    if (_terminalFallbackTimers.containsKey(targetRequestId) &&
        event is! DoneEvent &&
        event is! ErrorEvent &&
        event is! NackEvent) {
      _scheduleTerminalFallback(targetRequestId);
    }
    if (event is DoneEvent || event is ErrorEvent || event is NackEvent) {
      _cancelTerminalFallback(targetRequestId);
      _requestControllers.remove(targetRequestId);
      _safeClose(controller);
    }
  }

  void _broadcastErrorToActiveRequests(ErrorEvent event) {
    final activeEntries = _requestControllers.entries.toList();
    for (final entry in activeEntries) {
      _cancelTerminalFallback(entry.key);
      _safeAdd(entry.value, event);
      _safeClose(entry.value);
      _requestControllers.remove(entry.key);
    }
  }

  void _enqueuePendingMessage(Map<String, dynamic> payload) {
    if (_pendingMessages.length >= _pendingMessageLimit) {
      final droppedPayload = _pendingMessages.removeAt(0);
      _notifyPendingPayloadFailure(
        droppedPayload,
        ErrorEvent(
          code: 'PENDING_QUEUE_OVERFLOW',
          message: S.chatErrorQueueOverflow,
          retryable: false,
        ),
      );
      // Remove overflowed message from offline DB (R3 O-01)
      final droppedId = droppedPayload['request_id']?.toString();
      if (droppedId != null && droppedId.isNotEmpty) {
        unawaited(_offlineQueue.remove(droppedId));
      }
    }
    _pendingMessages.add(payload);

    _persistOutgoingMessage(payload);
  }

  void _persistOutgoingMessage(Map<String, dynamic> payload) {
    final requestId = payload['request_id']?.toString();
    if (requestId != null && requestId.isNotEmpty) {
      unawaited(_offlineQueue.enqueue(
        requestId: requestId,
        sessionId: (payload['session_id'] ?? '').toString(),
        message: (payload['message'] ?? '').toString(),
        userId: _currentUserId ?? '',
        extraContext: payload['extra_context']?.toString(),
        fileIds: payload['file_ids'] is List
            ? (payload['file_ids'] as List).map((e) => e.toString()).toList()
            : null,
        chatMode: payload['chat_mode']?.toString(),
        nickname: payload['nickname']?.toString(),
      ));
    }
  }

  void _notifyPendingPayloadFailure(
    Map<String, dynamic> payload,
    ErrorEvent event,
  ) {
    final requestId = payload['request_id']?.toString();
    if (requestId == null || requestId.isEmpty) {
      return;
    }
    _routeEventToRequest(requestId, event);
  }

  void _failPendingMessages({required String code, required String message}) {
    if (_pendingMessages.isEmpty) {
      return;
    }
    final pending = List<Map<String, dynamic>>.from(_pendingMessages);
    _pendingMessages.clear();
    for (final payload in pending) {
      _notifyPendingPayloadFailure(
        payload,
        ErrorEvent(code: code, message: message, retryable: false),
      );
      // Keep the failed row so it can be retried after reconnect/manual retry.
      final reqId = payload['request_id']?.toString();
      if (reqId != null && reqId.isNotEmpty) {
        unawaited(_offlineQueue.markFailed(reqId, message));
      }
    }
  }

  void _queueIncomingMessage(dynamic data) {
    _incomingMessageChain = _incomingMessageChain
        .then((_) => _handleIncomingMessage(data))
        .catchError((Object error, StackTrace stackTrace) {
      _log('❌ Incoming message queue error: $error');
      _broadcastErrorToActiveRequests(ErrorEvent(
        code: 'MESSAGE_PARSE_ERROR',
        message: S.chatErrorParseFailed,
        retryable: false,
      ));
    });
  }

  /// 处理接收到的消息
  Future<void> _handleIncomingMessage(dynamic data) async {
    if (_disposed) return;

    try {
      if (data is! String) {
        _log('❌ Invalid data type: ${data.runtimeType}');
        return;
      }

      // Fast pong check without full JSON decode (avoids main-thread overhead for large frames)
      if (data == '{"type":"pong"}' || data == '{"type": "pong"}') {
        _onPongReceived();
        _log('💓 Pong received');
        return;
      }

      // Small control/status frames are latency-sensitive; large text frames
      // still go through an isolate to avoid blocking the UI thread.
      final event = data.length < 12000
          ? _parseChatEvent(data)
          : await compute(_parseChatEvent, data);
      final requestId = _extractRequestIdFromRawMessage(data);

      // 🔧 P0修复：标记流活跃状态，抑制心跳超时触发的假性重连
      _lastStreamDataTime = DateTime.now();
      if (event is! DoneEvent) {
        _isStreamActive = true;
      }
      _routeEventToRequest(requestId, event);
      if (event is AuroraStateBandEvent) {
        _container
            .read(emotionStateProvider.notifier)
            .updateFromAuroraStateBand(event.stateData);
      }

      // DoneEvent 到达时清除流活跃标记
      if (event is DoneEvent) {
        _isStreamActive = false;
      }
    } catch (e) {
      _log('❌ Parse error: $e');
    }
  }

  /// 检测错误是否为401认证失败
  bool _is401Error(dynamic error) => looksLikeAuthFailure(error);

  @visibleForTesting
  static bool looksLikeAuthFailure(dynamic error) {
    final errorStr = error.toString().toLowerCase();
    return errorStr.contains('status code: 401') ||
        errorStr.contains('http 401') ||
        errorStr.contains(' 401 ') ||
        errorStr.startsWith('401') ||
        errorStr.contains('unauthorized') ||
        errorStr.contains('invalid token') ||
        errorStr.contains('token expired') ||
        errorStr.contains('jwt expired') ||
        errorStr.contains('authentication failed') ||
        errorStr.contains('auth failed') ||
        errorStr.contains('4401');
  }

  /// 处理401错误：自动刷新Token并重连
  Future<void> _handle401Error() async {
    final l10n = I18nService.instance.l10n;
    if (_disposed) return;

    // 并发调用者等待正在进行的刷新完成
    if (_refreshCompleter != null) {
      _log('⏳ Token refresh already in progress, awaiting...');
      try {
        await _refreshCompleter!.future;
        _log('✅ Concurrent caller: token refreshed successfully');
      } catch (e) {
        _log('❌ Concurrent caller: token refresh failed: $e');
      }
      return;
    }

    // 检查是否超过最大重试次数
    if (_error401Count >= _max401Retries) {
      _log('❌ Max 401 retry attempts exceeded, logging out...');

      // 发送友好错误提示
      _broadcastErrorToActiveRequests(
        ErrorEvent(
          code: 'AUTH_FAILED',
          message: l10n.chatAuthExpired,
          retryable: false,
        ),
      );

      // 执行登出
      try {
        await _container
            .read(authRepositoryProvider)
            .logout(keepDemoMode: DemoDataService.isDemoMode);
      } catch (e) {
        _log('❌ Logout failed: $e');
      }

      // 更新连接状态，禁用重连
      _updateConnectionState(WsConnectionState.failed);
      _enableReconnectLocal = false;

      // 🔧 P0-2: 通知用户有消息未发送
      if (_pendingMessages.isNotEmpty) {
        final droppedCount = _pendingMessages.length;
        _log(
          '⚠️ Discarding $droppedCount pending messages due to auth failure',
        );
        _failPendingMessages(
          code: 'MESSAGES_LOST',
          message: l10n.chatPendingMessagesFailed(
            '有 $droppedCount 条未发送消息因登录失效被丢弃 / $droppedCount pending messages were dropped because authentication expired.',
          ),
        );
      }
      return;
    }

    _refreshCompleter = Completer<String>();
    _error401Count++;

    _log(
      '🔑 Detected 401 error, refreshing token... ($_error401Count/$_max401Retries)',
    );

    try {
      // 发送刷新中的提示
      _broadcastErrorToActiveRequests(
        ErrorEvent(
          code: 'TOKEN_REFRESHING',
          message: l10n.chatAuthRefreshing,
          retryable: false,
        ),
      );

      // 刷新Token
      final authRepo = _container.read(authRepositoryProvider);
      final newTokenResponse = await authRepo.refreshToken();

      _log('✅ Token refreshed successfully');

      _refreshCompleter!.complete(newTokenResponse.accessToken);

      // ✅ Fix H1: Restore connection state after successful token refresh
      _onTokenRefreshSuccess(newTokenResponse.accessToken);
    } catch (e) {
      _log('❌ Token refresh failed: $e');

      _refreshCompleter!.completeError(e);

      // Token刷新失败，发送友好错误并登出
      _broadcastErrorToActiveRequests(
        ErrorEvent(
          code: 'AUTH_FAILED',
          message: l10n.chatAuthExpired,
          retryable: false,
        ),
      );

      // 执行登出
      try {
        await _container
            .read(authRepositoryProvider)
            .logout(keepDemoMode: DemoDataService.isDemoMode);
      } catch (logoutErr) {
        _log('❌ Logout failed: $logoutErr');
      }

      // 禁用重连
      _updateConnectionState(WsConnectionState.failed);
      _enableReconnectLocal = false;

      // 🔧 P0-2: 通知用户有消息未发送
      if (_pendingMessages.isNotEmpty) {
        final droppedCount = _pendingMessages.length;
        _log(
          '⚠️ Discarding $droppedCount pending messages due to token refresh failure',
        );
        _failPendingMessages(
          code: 'MESSAGES_LOST',
          message: l10n.chatPendingMessagesFailed(
            '有 $droppedCount 条未发送消息因刷新登录失败被丢弃 / $droppedCount pending messages were dropped because token refresh failed.',
          ),
        );
      }
    } finally {
      _refreshCompleter = null;
    }
  }

  /// ✅ Fix H1: Reset connection state to allow reconnection
  void _resetConnectionState() {
    if (_disposed) return;
    _log('🔄 Resetting connection state');
    _enableReconnectLocal = true;
    _reconnectAttempts = 0;
    _error401Count = 0;
    _refreshCompleter = null;
  }

  /// ✅ Fix H1: Handle successful token refresh and restore connection state
  void _onTokenRefreshSuccess(String newToken) {
    if (_disposed) return;
    _log('✅ Token refresh successful, restoring connection state');
    _currentToken = newToken;
    _resetConnectionState();

    // 立即尝试重连
    if (_currentUserId != null) {
      _closeConnection();
      _updateConnectionState(WsConnectionState.disconnected);
      _establishConnection(_currentUserId!, _currentToken);
    }
  }

  /// 本地重连开关（用于401后禁用）
  bool _enableReconnectLocal = true;

  /// 处理连接错误
  void _handleConnectionError(dynamic error) {
    if (_disposed) return;

    _log('❌ Connection error: $error');

    // 检测是否为401认证错误
    if (_is401Error(error)) {
      _log('🔐 401 Authentication error detected');
      // 异步处理401，避免阻塞错误处理流程
      unawaited(Future.microtask(_handle401Error));
      return;
    }

    // 普通连接错误，发送错误事件给消息流
    _broadcastErrorToActiveRequests(
      ErrorEvent(
        code: 'CONNECTION_ERROR',
        message: S.chatErrorConnectionFailed,
        retryable: true,
      ),
    );

    _triggerReconnect();
  }

  /// 处理连接关闭
  void _handleConnectionClosed() {
    _log('🔌 Connection closed');
    _stopHeartbeat();

    if (_requestControllers.isNotEmpty) {
      _broadcastErrorToActiveRequests(
        ErrorEvent(
          code: 'CONNECTION_CLOSED',
          message: S.chatErrorConnectionClosedGenerating,
          retryable: true,
        ),
      );
    }

    // 非主动关闭时尝试重连
    if (_connectionState != WsConnectionState.disconnected) {
      _triggerReconnect();
    }
  }

  /// 触发重连（指数退避）(TRACKED(TD-001))
  void _triggerReconnect() {
    if (_disposed) return; // TRACKED(TD-001): Check disposed
    if (!_enableReconnect || !_enableReconnectLocal) {
      _log('⛔ Reconnect disabled');
      _updateConnectionState(WsConnectionState.failed);
      return;
    }

    if (_reconnectAttempts >= _maxReconnectAttempts) {
      _log('❌ Max reconnect attempts reached');
      _updateConnectionState(WsConnectionState.failed);

      // Notify user about dropped pending messages (consistent with 401/token-refresh paths)
      if (_pendingMessages.isNotEmpty) {
        final droppedCount = _pendingMessages.length;
        final l10n = I18nService.instance.l10n;
        _log(
          '⚠️ Discarding $droppedCount pending messages: max reconnect attempts reached',
        );
        _failPendingMessages(
          code: 'MESSAGES_LOST',
          message: l10n.chatPendingMessagesFailed(
            '有 $droppedCount 条未发送消息因网络连接失败被丢弃 / $droppedCount pending messages were dropped because connection failed after $_maxReconnectAttempts attempts.',
          ),
        );
      }

      _broadcastErrorToActiveRequests(
        ErrorEvent(
          code: 'MAX_RETRIES_EXCEEDED',
          message: S.chatErrorMaxRetriesExceeded(_maxReconnectAttempts),
          retryable: false,
        ),
      );
      return;
    }

    _reconnectAttempts++;
    _updateConnectionState(WsConnectionState.reconnecting);

    final baseDelay = _reconnectSchedule[
        _reconnectAttempts.clamp(1, _maxReconnectAttempts) - 1];
    final jitterMs = math.Random().nextInt(250);
    final delayMs = baseDelay.inMilliseconds + jitterMs;

    _log(
      '🔄 Reconnecting in ${delayMs}ms '
      '(attempt $_reconnectAttempts/$_maxReconnectAttempts)',
    );

    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(Duration(milliseconds: delayMs), () {
      if (_disposed) return; // TRACKED(TD-001): Check disposed inside timer
      if (_currentUserId != null) {
        _establishConnection(_currentUserId!, _currentToken);
      }
    });
  }

  /// 启动心跳
  void _startHeartbeat() {
    _stopHeartbeat();
    _consecutiveHeartbeatFailures = 0;
    _lastPongReceivedTime = DateTime.now();

    _heartbeatTimer = Timer.periodic(_heartbeatInterval, (timer) {
      if (isConnected) {
        _sendPing();
      } else {
        timer.cancel();
      }
    });
  }

  /// 发送Ping并启动超时计时器
  void _sendPing() {
    try {
      _lastPingSentTime = DateTime.now();
      _channel?.sink.add(json.encode({'type': 'ping'}));
      _log('💓 Heartbeat sent');
      _startHeartbeatTimeout();
    } catch (e) {
      _log('❌ Heartbeat failed: $e');
      _handleHeartbeatFailure();
    }
  }

  /// 启动心跳超时计时器
  void _startHeartbeatTimeout() {
    _heartbeatTimeoutTimer?.cancel();
    _heartbeatTimeoutTimer = Timer(_heartbeatTimeout, () {
      _log(
        '⏰ Heartbeat timeout - no pong received in ${_heartbeatTimeout.inSeconds}s',
      );
      _handleHeartbeatFailure();
    });
  }

  /// 处理收到Pong
  void _onPongReceived() {
    _heartbeatTimeoutTimer?.cancel();
    _consecutiveHeartbeatFailures = 0;
    _lastPongReceivedTime = DateTime.now();

    // 计算RTT
    if (_lastPingSentTime != null) {
      final rtt = _lastPongReceivedTime!.difference(_lastPingSentTime!);
      final metrics = HeartbeatMetrics(
        rtt: rtt,
        sentAt: _lastPingSentTime!,
        receivedAt: _lastPongReceivedTime,
      );
      _heartbeatMetricsController.add(metrics);
      _log('💓 Heartbeat OK (RTT: ${rtt.inMilliseconds}ms)');
    }
  }

  /// 处理心跳失败
  void _handleHeartbeatFailure() {
    _heartbeatTimeoutTimer?.cancel();
    _consecutiveHeartbeatFailures++;

    // 发送失败指标
    if (_lastPingSentTime != null) {
      final metrics = HeartbeatMetrics(
        rtt: Duration.zero,
        sentAt: _lastPingSentTime!,
        consecutiveFailures: _consecutiveHeartbeatFailures,
      );
      _heartbeatMetricsController.add(metrics);
    }

    _log(
      '❌ Heartbeat failure #$_consecutiveHeartbeatFailures/$_maxConsecutiveHeartbeatFailures',
    );

    if (_consecutiveHeartbeatFailures >= _maxConsecutiveHeartbeatFailures) {
      // 🔧 P0修复：流式消息活跃期间，如果最近收到过数据则跳过重连
      // 避免心跳pong丢失导致正在接收的AI回复被中断
      if (_isStreamActive && _lastStreamDataTime != null) {
        final sinceLastData = DateTime.now().difference(_lastStreamDataTime!);
        if (sinceLastData.inSeconds < 120) {
          _log(
            '💡 Suppressing heartbeat reconnect: stream active, last data ${sinceLastData.inSeconds}s ago',
          );
          _consecutiveHeartbeatFailures =
              0; // Reset to avoid immediate re-trigger
          return;
        }
      }
      _log('🔌 Too many heartbeat failures, triggering reconnect');
      _handleConnectionClosed();
    }
  }

  /// 停止心跳
  void _stopHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = null;
    _heartbeatTimeoutTimer?.cancel();
    _heartbeatTimeoutTimer = null;
  }

  /// 发送消息 (TRACKED(TD-001))
  void _sendMessage(Map<String, dynamic> payload) {
    _log(
      '📤 Attempting to send message, isConnected: $isConnected, channel: ${_channel != null}',
    );
    if (!isConnected) {
      _log('⚠️  Cannot send: not connected');
      _enqueuePendingMessage(payload);
      return;
    }

    try {
      final span = TracingService.instance.startSpan('ws.chat_send');
      payload.putIfAbsent('trace_id', TracingService.instance.createTraceId);
      if (payload['type'] is String) {
        span.setAttribute('ws.type', payload['type'] as String);
      }
      _channel?.sink.add(json.encode(payload));
      _log('📤 Sent: type=${payload['type']}, id=${payload['id']}');

      // Mark as sent in offline DB (R3 O-01)
      final reqId = payload['request_id']?.toString();
      if (reqId != null && reqId.isNotEmpty) {
        unawaited(_offlineQueue.markSent(reqId));
      }

      span.end();
    } catch (e) {
      _log('❌ Send failed: $e');
      _enqueuePendingMessage(payload);
      // Don't broadcast to all streams — single send failure is not a connection error
    }
  }

  /// 发送待发送的消息
  void _flushPendingMessages() {
    if (_pendingMessages.isEmpty) return;

    _log('📨 Flushing ${_pendingMessages.length} pending messages');
    final messages = List<Map<String, dynamic>>.from(_pendingMessages);
    _pendingMessages.clear();

    messages.forEach(_sendMessage);
  }

  /// Restore pending messages from offline Isar DB into the in-memory queue (R3 O-01).
  Future<void> _restorePendingFromDb() async {
    if (_currentUserId == null) return;
    final pending = await _offlineQueue.loadRetryableForUser(_currentUserId!);
    if (pending.isEmpty) return;

    _log('📨 Restoring ${pending.length} offline messages from DB');
    final queuedIds = _pendingMessages
        .map((payload) => payload['request_id']?.toString())
        .whereType<String>()
        .toSet();
    for (final msg in pending) {
      if (queuedIds.contains(msg.requestId)) {
        continue;
      }
      unawaited(_offlineQueue.prepareForRetry(msg.requestId));
      final payload = <String, dynamic>{
        'message': msg.message,
        'session_id': msg.sessionId,
        'request_id': msg.requestId,
        if (msg.nickname != null) 'nickname': msg.nickname,
        if (msg.extraContext != null) 'extra_context': msg.extraContext,
        if (msg.fileIds != null && msg.fileIds!.isNotEmpty)
          'file_ids': msg.parsedFileIds,
        if (msg.chatMode != null) 'chat_mode': msg.chatMode,
      };
      _pendingMessages.add(payload);
      queuedIds.add(msg.requestId);
    }
  }

  String _applyWebSocketSchemeForEnvironment(
    String rawBaseUrl, {
    required bool isProduction,
  }) {
    final uri = Uri.parse(rawBaseUrl);

    // 确保总是使用WebSocket协议（ws:// 或 wss://）
    final currentScheme = uri.scheme;
    String finalScheme;

    if (currentScheme == 'https' || currentScheme == 'wss') {
      finalScheme = 'wss';
    } else if (currentScheme == 'http' || currentScheme == 'ws') {
      finalScheme = 'ws';
    } else {
      // 未知协议，根据环境决定
      finalScheme = isProduction ? 'wss' : 'ws';
    }

    // 如果需要转换协议
    if (currentScheme != finalScheme) {
      _log('🔄 Converting URL scheme: $currentScheme → $finalScheme');
      return uri.replace(scheme: finalScheme).toString();
    }

    return rawBaseUrl;
  }

  /// 生成 session ID
  String _generateSessionId() =>
      'session_${DateTime.now().millisecondsSinceEpoch}';

  /// 生成 request ID（用于端到端幂等）
  String _generateRequestId() {
    final now = DateTime.now().microsecondsSinceEpoch;
    final rand = math.Random().nextInt(1 << 20);
    return 'req_${now}_$rand';
  }

  /// 手动重连
  Future<void> manualReconnect() async {
    if (_disposed) return;
    if (_currentUserId == null) {
      _log('⚠️  Cannot reconnect: no user ID');
      return;
    }

    _log('🔄 Manual reconnect triggered');
    _reconnectAttempts = 0;

    _connGen++;
    await _teardownSocket(_connGen);
    _updateConnectionState(WsConnectionState.disconnected);

    await Future<void>.delayed(const Duration(milliseconds: 500));
    if (!_disposed) {
      _establishConnection(_currentUserId!, _currentToken);
    }
  }

  /// 销毁 Socket 连接（幂等、异步、安全）
  Future<void> _teardownSocket(int gen) async {
    if (gen != _connGen) {
      _log('⚠️ Ignored teardown for gen $gen (current: $_connGen)');
      return;
    }

    _log('🔌 Teardown socket (Gen: $gen)');

    _stopHeartbeat();

    if (!_disposed) {
      _connectionState = WsConnectionState.disconnected;
      _safeAdd(_connectionStateController, WsConnectionState.disconnected);
    }

    final sub = _socketSubscription;
    _socketSubscription = null;
    try {
      await sub?.cancel();
    } catch (_) {}

    final ch = _channel;
    _channel = null;
    try {
      await ch?.sink.close();
    } catch (_) {}
  }

  /// 关闭连接
  void _closeConnection() {
    _log('🔌 Closing connection');
    _stopHeartbeat();
    _reconnectTimer?.cancel();
    final sink = _channel?.sink;
    if (sink != null) {
      unawaited(sink.close());
    }
    _channel = null;
    _updateConnectionState(WsConnectionState.disconnected);
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (_disposed) return;
    if (state == AppLifecycleState.inactive) {
      _log('📱 App inactive — keeping socket warm');
      _stopHeartbeat();
      return;
    }

    if (state == AppLifecycleState.paused ||
        state == AppLifecycleState.hidden ||
        state == AppLifecycleState.detached) {
      _log('📱 App backgrounded — disconnecting WebSocket');
      _stopHeartbeat();
      _closeConnection();
      _updateConnectionState(WsConnectionState.disconnected);
      return;
    }

    if (state == AppLifecycleState.resumed) {
      _log('📱 App resumed — checking WebSocket');
      if (_connectionState == WsConnectionState.disconnected &&
          _currentUserId != null) {
        _reconnectAttempts = 0;
        _establishConnection(_currentUserId!, _currentToken);
      }
    }
  }

  /// 释放资源
  void dispose() {
    if (_disposed) return;
    _log('🗑️  Disposing WebSocketChatServiceV2');
    _disposed = true;
    WidgetsBinding.instance.removeObserver(this);
    _connGen++; // Invalidate any pending connection attempts

    unawaited(_socketSubscription?.cancel());
    _socketSubscription = null;

    _reconnectTimer?.cancel();
    _reconnectTimer = null;

    _stopHeartbeat();

    _closeConnection();

    for (final timer in _terminalFallbackTimers.values) {
      timer.cancel();
    }
    _terminalFallbackTimers.clear();
    _requestControllers.values.forEach(_safeClose);
    _requestControllers.clear();
    if (!_connectionStateController.isClosed) {
      unawaited(_connectionStateController.close());
    }
    // ✅ Fix C1: Close heartbeat metrics controller to prevent memory leak
    if (!_heartbeatMetricsController.isClosed) {
      unawaited(_heartbeatMetricsController.close());
    }
    _pendingMessages.clear();

    // Cleanup old acked offline messages (R3 O-01)
    unawaited(_offlineQueue.cleanupOldAcked());
  }

  // Helper for TRACKED(TD-001)
  void _log(String message) {
    if (kDebugMode) {
      var masked = message;
      if (message.contains('token=') || message.contains('Authorization')) {
        masked = message.replaceAllMapped(
          RegExp('(token=|Authorization: )([^&]+)'),
          (m) => '${m.group(1)}${_maskSecret(m.group(2))}',
        );
      }
      debugPrint(masked);
    }
  }

  String _maskSecret(String? secret) {
    if (secret == null) return '';
    if (secret.length < 6) return '***';
    return '${secret.substring(0, 3)}...${secret.substring(secret.length - 3)}';
  }
}
