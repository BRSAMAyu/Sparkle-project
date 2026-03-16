import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/utils/error_messages.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/achievement/presentation/providers/close_to_unlock_provider.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';
import 'package:sparkle/features/chat/data/models/reasoning_step_model.dart';
import 'package:sparkle/features/chat/data/repositories/chat_repository.dart';
import 'package:sparkle/features/chat/data/services/agent_session_store.dart';
import 'package:sparkle/features/chat/data/services/plan_review_grpc_service.dart';
import 'package:sparkle/features/chat/data/services/review_grpc_service.dart';
import 'package:sparkle/features/chat/data/services/websocket_chat_service_v2.dart';
import 'package:sparkle/features/chat/presentation/providers/agent_session_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_mode_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_state.dart';
import 'package:sparkle/features/chat/presentation/widgets/content_review_card.dart';
import 'package:sparkle/features/chat/presentation/widgets/plan_review_card.dart';
import 'package:sparkle/features/chat/presentation/widgets/plan_switch_confirmation_dialog.dart';
import 'package:sparkle/features/file/file.dart';
import 'package:sparkle/features/home/presentation/providers/task_board_provider.dart';
import 'package:sparkle/features/notification_center/notification_center.dart';
import 'package:sparkle/features/plan/presentation/providers/active_plan_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/reviews/presentation/providers/nightly_review_provider.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';

part 'chat_notifier_reviews.dart';
part 'chat_notifier_history.dart';
part 'chat_notifier_actions.dart';
part 'chat_provider_wiring.dart';

// 2. ChatNotifier Class
class ChatNotifier extends StateNotifier<ChatState> {
  ChatNotifier(this._chatRepository, this._ref) : super(ChatState()) {
    if (DemoDataService.isDemoMode) {
      // Load demo history
      state = state.copyWith(
        messages: DemoDataService().demoChatHistory,
        conversationId: 'demo_conv_1',
      );
    }

    // 监听 WebSocket 连接状态
    _connectionStateSubscription =
        _chatRepository.connectionStateStream.listen((connectionState) {
      if (_isDisposed) return;
      state = state.copyWith(wsConnectionState: connectionState);
    });
  }
  final ChatRepository _chatRepository;
  final Ref _ref;
  StreamSubscription<WsConnectionState>? _connectionStateSubscription;
  final _Debouncer _streamDebouncer =
      _Debouncer(const Duration(milliseconds: 50));
  bool _isDisposed = false;
  static const String _dailyUsageDateKey = 'chat_daily_usage_date';
  static const String _dailyUsageTokensKey = 'chat_daily_usage_tokens';
  static const String _dailyUsageCostKey = 'chat_daily_usage_cost_micro_usd';
  static const int _dailyTokenLimitDefault = 50000;

  // Plan review service (lazy initialized)
  PlanReviewGrpcService? _planReviewService;

  // Review service (lazy initialized)
  ReviewGrpcService? _reviewService;

  /// 手动触发重连
  Future<void> reconnect() async {
    await _chatRepository.reconnect();
  }

  @override
  void dispose() {
    _isDisposed = true;
    unawaited(_connectionStateSubscription?.cancel());
    _streamDebouncer.cancel();
    _chatRepository.dispose();
    super.dispose();
  }

  bool _shouldIncludeSystemUpdate(Map<String, dynamic> data) {
    final level = _ref.read(systemUpdateLevelProvider);
    if (level <= 0) {
      return false;
    }
    if (level == 1) {
      final priority = data['priority']?.toString().toLowerCase() ?? 'low';
      return priority != 'low';
    }
    return true;
  }

  List<String> _parseSelectedExperts(dynamic raw) {
    if (raw is List) {
      return raw.map((e) => '$e').toList();
    }
    if (raw is String && raw.isNotEmpty) {
      if (raw.trim().startsWith('[')) {
        try {
          final decoded = jsonDecode(raw);
          if (decoded is List) {
            return decoded.map((e) => '$e').toList();
          }
        } catch (_) {}
      }
      return raw
          .split(',')
          .map((e) => e.trim())
          .where((e) => e.isNotEmpty)
          .toList();
    }
    return const [];
  }

  Map<String, dynamic> _normalizeUxActionItem(
    dynamic raw, {
    String defaultType = 'prompt',
  }) {
    if (raw is Map) {
      final item = Map<String, dynamic>.from(raw);
      final payload = item['payload'] is Map
          ? Map<String, dynamic>.from(item['payload'] as Map)
          : <String, dynamic>{};
      final type = item['type']?.toString() ?? defaultType;
      final label =
          item['label']?.toString() ??
          payload['label']?.toString() ??
          item['prompt']?.toString() ??
          payload['prompt']?.toString() ??
          item['route']?.toString() ??
          payload['route']?.toString() ??
          '';
      if (label.isEmpty) {
        return const {};
      }
      if (type == 'prompt' && !payload.containsKey('prompt')) {
        payload['prompt'] = item['prompt']?.toString() ?? label;
      }
      if (!payload.containsKey('route') && item['route'] != null) {
        payload['route'] = item['route'];
      }
      if (!payload.containsKey('task_id') && item['task_id'] != null) {
        payload['task_id'] = item['task_id'];
      }
      if (!payload.containsKey('plan_id') && item['plan_id'] != null) {
        payload['plan_id'] = item['plan_id'];
      }
      if (!payload.containsKey('title') && item['title'] != null) {
        payload['title'] = item['title'];
      }
      return {
        'label': label,
        'type': type,
        'payload': payload,
        if (item['style'] != null) 'style': item['style'],
        if (item['stage'] != null) 'stage': item['stage'],
        if (item['reason_key'] != null) 'reason_key': item['reason_key'],
        if (payload['prompt'] != null) 'prompt': payload['prompt'],
        if (payload['route'] != null) 'route': payload['route'],
      };
    }

    final label = '$raw'.trim();
    if (label.isEmpty) {
      return const {};
    }
    return {
      'label': label,
      'type': defaultType,
      'payload': {'prompt': label},
      'prompt': label,
    };
  }

  List<Map<String, dynamic>> _normalizeUxActionList(dynamic raw) {
    if (raw is! List) {
      return const [];
    }
    return raw
        .map(_normalizeUxActionItem)
        .where((item) => item.isNotEmpty)
        .toList();
  }

  Map<String, dynamic> _extractUxEnvelope(Map<String, dynamic>? metadata) {
    if (metadata == null) return const {};
    final envelope = <String, dynamic>{};
    for (final key in const [
      'ux_turn',
      'ux_progress',
      'ux_result',
      'ux_followthrough',
      'ux_sources',
      'ux_evolution',
      'continuity_banner',
      'mode_explanation',
      'collaboration_summary',
    ]) {
      final value = metadata[key];
      if (value is Map<String, dynamic> && value.isNotEmpty) {
        envelope[key] = value;
      }
    }
    return envelope;
  }

  void _appendUxWidgets(
    List<WidgetPayload> target,
    Map<String, dynamic>? uxEnvelope,
  ) {
    if (uxEnvelope == null || uxEnvelope.isEmpty) return;
    final l10n = I18nService.instance.l10n;

    void addWidget(String type, Map<String, dynamic>? data) {
      if (data == null || data.isEmpty) return;
      final exists = target.any((widget) => widget.type == type);
      if (!exists) {
        target.add(WidgetPayload(type: type, data: data));
      }
    }

    final continuity = uxEnvelope['continuity_banner'];
    if (continuity is Map<String, dynamic>) {
      addWidget('continuity_banner', continuity);
    }

    final modeExplanation = uxEnvelope['mode_explanation'];
    if (modeExplanation is Map<String, dynamic>) {
      addWidget('mode_explanation', modeExplanation);
    }

    final sources = uxEnvelope['ux_sources'];
    if (sources is Map<String, dynamic>) {
      final result = uxEnvelope['ux_result'];
      addWidget('source_summary', {
        ...sources,
        if (result is Map<String, dynamic>) ...{
          'headline': result['headline'],
          'first_screen_focus': result['first_screen_focus'],
        },
      });
    }

    final followthrough = uxEnvelope['ux_followthrough'];
    if (followthrough is Map<String, dynamic>) {
      final nextActionsRaw = followthrough['next_actions'];
      final retryOptionsRaw = followthrough['retry_options'];
      final nextActions = _normalizeUxActionList(nextActionsRaw);
      final retryOptions = _normalizeUxActionList(retryOptionsRaw);
      addWidget('next_actions', {
        'title':
            followthrough['next_actions_title']?.toString() ??
                l10n.chatNextActionsTitle,
        'actions': nextActions,
        'retry_options': retryOptions,
        'recovery_message': followthrough['recovery_message'],
        'memory_updates': followthrough['memory_updates'],
        if (followthrough['stage'] != null) 'stage': followthrough['stage'],
        if (followthrough['next_actions_strategy'] != null)
          'next_actions_strategy': followthrough['next_actions_strategy'],
      });
    }

    final evolution = uxEnvelope['ux_evolution'];
    if (evolution is Map<String, dynamic>) {
      addWidget('evolution_card', evolution);
      final progressSnapshot = evolution['progress_snapshot'];
      if (progressSnapshot is Map<String, dynamic>) {
        addWidget('progress_card', progressSnapshot);
      }
    }

    final result = uxEnvelope['ux_result'];
    if (result is Map<String, dynamic>) {
      final completionState = result['completion_state']?.toString();
      if (completionState == 'needs_input' || completionState == 'blocked') {
        addWidget('blocked_input_request', {
          'title': result['headline']?.toString() ??
              l10n.chatBlockedInputTitle,
          'reason': result['why_this_answer'],
          'failure_kind': result['failure_kind'],
          'recovery_message': followthrough is Map<String, dynamic>
              ? followthrough['recovery_message']
              : null,
          'completion_state': completionState,
          if (result['blocked_temperature'] != null)
            'blocked_temperature': result['blocked_temperature'],
          if (result['blocked_repeat_count'] != null)
            'blocked_repeat_count': result['blocked_repeat_count'],
          'retry_options': followthrough is Map<String, dynamic>
              ? _normalizeUxActionList(followthrough['retry_options'])
              : const <Map<String, dynamic>>[],
        });
      }
    }
  }

  WidgetPayload _normalizeWidgetPayload(String type, Map<String, dynamic> data) {
    if (type == 'system_update') {
      final category = data['category']?.toString();
      final metadata = data['metadata'];
      if (category == 'evolution' && metadata is Map<String, dynamic>) {
        final evolutionKind = metadata['evolution_kind']?.toString() ?? '';
        final adaptation = metadata['adaptation_record'];
        final preferenceLearning = metadata['preference_learning'];
        final progressSnapshot = metadata['progress_snapshot'];
        if (metadata['evolution_kind'] == 'progress_snapshot' &&
            progressSnapshot is Map<String, dynamic>) {
          return WidgetPayload(type: 'progress_card', data: progressSnapshot);
        }
        return WidgetPayload(
          type: 'evolution_card',
          data: {
            'evolution_kind': evolutionKind,
            'headline': data['title']?.toString() ??
                I18nService.instance.l10n.chatEvolutionHeadlineDefault,
            'summary': data['description']?.toString() ?? '',
            if (metadata['insight_text'] != null)
              'insight_text': metadata['insight_text'],
            if (metadata['evidence_summary'] != null)
              'evidence_summary': metadata['evidence_summary'],
            if (metadata['recommended_action'] is Map)
              'recommended_action': Map<String, dynamic>.from(
                metadata['recommended_action'] as Map,
              ),
            if (metadata['confidence'] != null) 'confidence': metadata['confidence'],
            if (metadata['weekly_summary'] != null)
              'weekly_summary': metadata['weekly_summary'],
            if (metadata['top_learnings'] is List<dynamic>)
              'top_learnings': metadata['top_learnings'],
            if (metadata['one_key_adjustment'] != null)
              'one_key_adjustment': metadata['one_key_adjustment'],
            if (metadata['comparison_highlight'] != null)
              'comparison_highlight': metadata['comparison_highlight'],
            if (metadata['period_range'] != null)
              'period_range': metadata['period_range'],
            if (metadata['reasoning_summary'] != null)
              'reasoning_summary': metadata['reasoning_summary'],
            if (metadata['reasoning_details'] is List<dynamic>)
              'reasoning_details': metadata['reasoning_details'],
            if (metadata['comparison'] is Map)
              'comparison': Map<String, dynamic>.from(
                metadata['comparison'] as Map,
              ),
            if (adaptation is Map<String, dynamic>)
              'adaptation_records': [adaptation],
            if (preferenceLearning is Map<String, dynamic>)
              'preference_learnings': [preferenceLearning],
            if (progressSnapshot is Map<String, dynamic>)
              'progress_snapshot': progressSnapshot,
            'highlights': <String>[
              if ((data['description']?.toString() ?? '').isNotEmpty)
                data['description'].toString(),
            ],
          },
        );
      }
      if (category == 'reflection' && metadata is Map<String, dynamic>) {
        final prompt = metadata['reflection_prompt'];
        if (prompt is Map<String, dynamic>) {
          return WidgetPayload(type: 'reflection_card', data: prompt);
        }
      }
    }
    return WidgetPayload(type: type, data: data);
  }

  /// 发送消息 (使用 SSE/WebSocket 流式响应)
  Future<void> sendMessage(String content, {String? taskId}) async {
    // 获取当前用户信息
    final authState = _ref.read(authProvider);
    final user = authState.user;

    // 如果未登录，使用持久化的访客 ID
    String userId;
    String nickname;
    if (user != null) {
      userId = user.id;
      nickname = (user.nickname != null && user.nickname!.isNotEmpty)
          ? user.nickname!
          : user.username;
    } else {
      final guestService = _ref.read(guestServiceProvider);
      userId = await guestService.getGuestId();
      nickname = guestService.getGuestNickname();
    }

    // 1. 立即添加用户消息到 UI
    final userMessage = ChatMessageModel(
      id: 'temp_user_${DateTime.now().millisecondsSinceEpoch}',
      userId: userId,
      conversationId: state.conversationId ?? 'temp_conversation',
      role: MessageRole.user,
      content: content,
      taskId: taskId,
      createdAt: DateTime.now(),
    );

    state = state.copyWith(
      messages: [...state.messages, userMessage],
      isSending: true,
      streamingContent: '',
      activeTools: const [],
      agentActivities: const [],
      clearDagExecution: true,
      clearError: true,
    );

    var accumulatedContent = '';
    String? responseId;
    String? traceId;
    String? workflowId;
    String? promptVersion;
    String? lastAiStatus;
    final accumulatedWidgets = <WidgetPayload>[];
    Map<String, dynamic>? accumulatedCollaboration;
    Map<String, dynamic>? accumulatedUxEnvelope;
    Map<String, dynamic>? accumulatedOrchestrationTrace;
    Map<String, dynamic>? accumulatedModeSuggestion;
    String? accumulatedCollaborationNarrative;
    String? accumulatedCollaborationMode;
    List<String>? accumulatedAgentsInvolved;
    final accumulatedReasoningSteps = <ReasoningStep>[];
    int? reasoningStartTime;
    String? pendingStreamingContent;
    String? pendingAiStatus;
    String? pendingAiStatusDetails;
    List<ReasoningStep>? pendingReasoningSteps;
    bool? pendingReasoningActive;
    int? pendingReasoningStartTime;
    var planContextInjected = false;
    List<Map<String, dynamic>>? snapshotAgentActivities;

    void flushPending({bool immediate = false}) {
      void applyPending() {
        if (_isDisposed) return;
        if (pendingStreamingContent == null &&
            pendingAiStatus == null &&
            pendingAiStatusDetails == null &&
            pendingReasoningSteps == null &&
            pendingReasoningActive == null &&
            pendingReasoningStartTime == null) {
          return;
        }
        state = state.copyWith(
          streamingContent: pendingStreamingContent,
          aiStatus: pendingAiStatus,
          aiStatusDetails: pendingAiStatusDetails,
          reasoningSteps: pendingReasoningSteps,
          isReasoningActive: pendingReasoningActive,
          reasoningStartTime: pendingReasoningStartTime,
        );
        pendingStreamingContent = null;
        pendingAiStatus = null;
        pendingAiStatusDetails = null;
        pendingReasoningSteps = null;
        pendingReasoningActive = null;
        pendingReasoningStartTime = null;
      }

      if (immediate) {
        _streamDebouncer.flush(applyPending);
      } else {
        _streamDebouncer.run(applyPending);
      }
    }

    // 🔧 P1-1: 使用 finally 确保 isSending 总是被重置
    var shouldResetSending = true;
    try {
      final token = await _ref.read(authRepositoryProvider).getAccessToken();
      final fileIds = state.attachedFiles.map((file) => file.id).toList();
      state = state.copyWith(clearAttachments: true);

      // Get selected plan for chat context
      final selectedPlanId = _ref.read(activePlanProvider);
      final extraContext =
          selectedPlanId != null ? {'plan_id': selectedPlanId} : null;

      // Get selected chat mode
      final chatMode = _ref.read(chatModeProvider);
      final chatModeValue = chatMode.apiValue;

      await for (final event in _chatRepository.chatStream(
        content,
        state.conversationId,
        userId: userId,
        nickname: nickname,
        token: token,
        fileIds: fileIds,
        includeReferences: fileIds.isNotEmpty,
        extraContext: extraContext,
        chatMode: chatModeValue,
      )) {
        if (event.responseId != null && event.responseId!.isNotEmpty) {
          responseId = event.responseId;
        }
        if (event.traceId != null && event.traceId!.isNotEmpty) {
          traceId = event.traceId;
        }
        if (event.workflowId != null && event.workflowId!.isNotEmpty) {
          workflowId = event.workflowId;
        }
        if (event.promptVersion != null && event.promptVersion!.isNotEmpty) {
          promptVersion = event.promptVersion;
        }

        if (event is TextEvent) {
          final metadata = event.metadata;
          final uxEnvelope = _extractUxEnvelope(metadata);
          if (uxEnvelope.isNotEmpty) {
            accumulatedUxEnvelope = {
              ...(accumulatedUxEnvelope ?? const <String, dynamic>{}),
              ...uxEnvelope,
            };
          }
          final planContext = metadata?['plan_context'];
          final showPlanContext = metadata?['show_plan_context'] == true;
          if (!planContextInjected &&
              (planContext is Map<String, dynamic> || showPlanContext)) {
            final data = planContext is Map<String, dynamic>
                ? planContext
                : {
                    if (metadata?['plan_id'] is String)
                      'plan_id': metadata?['plan_id'],
                  };
            if (data.isNotEmpty) {
              accumulatedWidgets.add(
                WidgetPayload(
                  type: 'plan_context_summary',
                  data: data,
                ),
              );
              planContextInjected = true;
            }
          }
          if (metadata != null) {
            final selectedExpertsRaw = metadata['selected_experts'];
            final routingStrategy = metadata['routing_strategy'];
            final fallbackReason = metadata['fallback_reason'];
            final routeConfidence = metadata['route_confidence'];
            final expertEntrySource = metadata['expert_entry_source'];
            final collaborationNarrative =
                metadata['collaboration_narrative']?.toString();
            final collaborationMode =
                metadata['collaboration_mode']?.toString();
            final agentsInvolved = _parseSelectedExperts(
              metadata['agents_involved'],
            );
            if (selectedExpertsRaw != null ||
                routingStrategy != null ||
                fallbackReason != null ||
                routeConfidence != null ||
                expertEntrySource != null) {
              final selectedExperts = _parseSelectedExperts(selectedExpertsRaw);
              accumulatedCollaboration = {
                ...(accumulatedCollaboration ?? const <String, dynamic>{}),
                'selected_experts': selectedExperts,
                'routing_strategy': routingStrategy,
                'fallback_reason': fallbackReason,
                'route_confidence': routeConfidence,
                'expert_entry_source': expertEntrySource,
              };
            }
            if (collaborationNarrative != null &&
                collaborationNarrative.trim().isNotEmpty) {
              accumulatedCollaborationNarrative = collaborationNarrative.trim();
            }
            if (collaborationMode != null &&
                collaborationMode.trim().isNotEmpty) {
              accumulatedCollaborationMode = collaborationMode.trim();
            }
            if (agentsInvolved.isNotEmpty) {
              accumulatedAgentsInvolved = agentsInvolved;
            }
          }
          // 流式文本片段（delta）
          accumulatedContent += event.content;
          pendingStreamingContent = accumulatedContent;
          flushPending();
        } else if (event is StatusUpdateEvent) {
          // AI 状态更新（THINKING, GENERATING 等）
          final uxProgress = event.metadata?['ux_progress'];
          lastAiStatus = event.state;
          pendingAiStatus = event.state;
          if (uxProgress is Map<String, dynamic>) {
            final headline = uxProgress['headline']?.toString();
            final detail = uxProgress['detail']?.toString();
            pendingAiStatusDetails = [headline, detail]
                .whereType<String>()
                .where((item) => item.trim().isNotEmpty)
                .join(' · ');
          } else {
            pendingAiStatusDetails = event.details;
          }
          state = state.copyWith(
            currentAgentName: event.currentAgentName,
            activeAgentType: event.activeAgentType,
          );
          flushPending();
        } else if (event is DagExecutionEvent) {
          state = state.copyWith(dagExecutionSignal: event.signal);
          final dagDetails = event.signal.statusDetails;
          if (dagDetails != null && dagDetails.isNotEmpty) {
            lastAiStatus = 'EXECUTING_TOOL';
            pendingAiStatus = 'EXECUTING_TOOL';
            pendingAiStatusDetails = dagDetails;
          }
          flushPending();
        } else if (event is FullTextEvent) {
          // 完整文本（通常在流结束时）
          final metadata = event.metadata;
          final uxEnvelope = _extractUxEnvelope(metadata);
          if (uxEnvelope.isNotEmpty) {
            accumulatedUxEnvelope = {
              ...(accumulatedUxEnvelope ?? const <String, dynamic>{}),
              ...uxEnvelope,
            };
          }
          if (metadata != null) {
            final selectedExpertsRaw = metadata['selected_experts'];
            final routingStrategy = metadata['routing_strategy'];
            final fallbackReason = metadata['fallback_reason'];
            final routeConfidence = metadata['route_confidence'];
            final expertEntrySource = metadata['expert_entry_source'];
            final collaborationNarrative =
                metadata['collaboration_narrative']?.toString();
            final collaborationMode =
                metadata['collaboration_mode']?.toString();
            final agentsInvolved = _parseSelectedExperts(
              metadata['agents_involved'],
            );
            if (selectedExpertsRaw != null ||
                routingStrategy != null ||
                fallbackReason != null ||
                routeConfidence != null ||
                expertEntrySource != null) {
              final selectedExperts = _parseSelectedExperts(selectedExpertsRaw);
              accumulatedCollaboration = {
                ...(accumulatedCollaboration ?? const <String, dynamic>{}),
                'selected_experts': selectedExperts,
                'routing_strategy': routingStrategy,
                'fallback_reason': fallbackReason,
                'route_confidence': routeConfidence,
                'expert_entry_source': expertEntrySource,
              };
            }
            if (collaborationNarrative != null &&
                collaborationNarrative.trim().isNotEmpty) {
              accumulatedCollaborationNarrative = collaborationNarrative.trim();
            }
            if (collaborationMode != null &&
                collaborationMode.trim().isNotEmpty) {
              accumulatedCollaborationMode = collaborationMode.trim();
            }
            if (agentsInvolved.isNotEmpty) {
              accumulatedAgentsInvolved = agentsInvolved;
            }
          }
          accumulatedContent = event.content;
          pendingStreamingContent = accumulatedContent;
          flushPending(immediate: true);
        } else if (event is ErrorEvent) {
          // 错误事件 - 使用用户友好的错误消息
          _streamDebouncer.cancel();
          final userFriendlyMessage = ErrorMessages.getUserFriendlyMessage(
            event.code,
            event.message,
          );
          final actionSuggestion =
              ErrorMessages.getActionSuggestion(event.code);
          final isRetryable = ErrorMessages.isRetryable(event.code);

          state = state.copyWith(
            error: actionSuggestion.isEmpty
                ? userFriendlyMessage
                : I18nService.instance.l10n.chatErrorWithSuggestion(
                    userFriendlyMessage,
                    actionSuggestion,
                  ),
            errorCode: event.code,
            isErrorRetryable: isRetryable,
            isSending: false,
            streamingContent: '',
            clearDagExecution: true,
            clearAiStatus: true,
            clearReasoning: true,
          );
          shouldResetSending = false; // 已经重置过了
          return; // 提前退出
        } else if (event is WidgetEvent) {
          if (event.widgetType == 'system_update' &&
              !_shouldIncludeSystemUpdate(event.widgetData)) {
            continue;
          }
          accumulatedWidgets.add(
            _normalizeWidgetPayload(event.widgetType, event.widgetData),
          );
        } else if (event is ToolStartEvent) {
          // 显示"正在使用工具: xxx"
          lastAiStatus = 'EXECUTING_TOOL';
          pendingAiStatus = 'EXECUTING_TOOL';
          pendingAiStatusDetails =
              I18nService.instance.l10n.chatUsingTool(event.toolName);
          final nextTools = List<String>.from(state.activeTools);
          if (!nextTools.contains(event.toolName)) {
            nextTools.add(event.toolName);
          }
          state = state.copyWith(activeTools: nextTools);
          flushPending();
        } else if (event is ToolResultEvent) {
          final widgetType = event.result.widgetType;
          final widgetData = event.result.widgetData;
          final toolName = event.result.toolName;
          if (toolName.isNotEmpty) {
            final nextTools = List<String>.from(state.activeTools)
              ..removeWhere((tool) => tool == toolName);
            state = state.copyWith(activeTools: nextTools);
          }
          if (widgetType != null && widgetData != null) {
            if (widgetType == 'system_update' &&
                !_shouldIncludeSystemUpdate(widgetData)) {
              continue;
            }
            accumulatedWidgets.add(_normalizeWidgetPayload(widgetType, widgetData));
          }
        } else if (event is CitationEvent) {
          accumulatedWidgets.add(
            WidgetPayload(
              type: 'source_summary',
              data: {
                'citations_available': event.citations.isNotEmpty,
                'reference_scope': event.citations.every(
                  (citation) =>
                      (citation['file_id']?.toString() ?? '').isNotEmpty,
                )
                    ? 'file_only'
                    : 'mixed',
                'evidence_summary': event.citations.isNotEmpty
                    ? I18nService.instance.l10n.chatSourcesAvailable
                    : I18nService.instance.l10n.chatSourcesUnavailable,
                'citations': event.citations,
              },
            ),
          );
        } else if (event is UsageEvent) {
          state = state.copyWith(
            lastPromptTokens: event.promptTokens,
            lastCompletionTokens: event.completionTokens,
            lastTotalTokens: event.totalTokens,
          );
          await _updateDailyUsage(event);
        } else if (event is ReasoningStepEvent) {
          // 🆕 推理步骤事件 - Chain of Thought Visualization
          reasoningStartTime ??= DateTime.now().millisecondsSinceEpoch;

          // Add timestamp to step
          final stepWithTime = event.step.copyWith(
            createdAt: event.step.createdAt ?? DateTime.now(),
          );

          accumulatedReasoningSteps.add(stepWithTime);

          pendingReasoningSteps = List.from(accumulatedReasoningSteps);
          pendingReasoningActive = true;
          pendingReasoningStartTime = reasoningStartTime;
          flushPending();
        } else if (event is ActionStatusEvent) {
          // ActionCard 状态更新事件
          _handleActionStatus(event);
          flushPending();
        } else if (event is PlanReviewWidgetEvent) {
          // Plan Review Widget Event
          _handlePlanReviewWidget(event);
          flushPending();
        } else if (event is StateChangeEvent) {
          // State Change Event (plan archived/restored/deleted, settings updated)
          _handleStateChangeEvent(event);
          flushPending();
        } else if (event is PlanReviewStatusEvent) {
          // Plan Review Status Event
          _handlePlanReviewStatus(event);
          flushPending();
        } else if (event is ContentReviewWidgetEvent) {
          // Content Review Widget Event (Phase 2b)
          _handleContentReviewWidget(event);
          flushPending();
        } else if (event is ContentReflectionResultEvent) {
          // Content Reflection Result Event (Phase 2b)
          _handleContentReflectionResult(event);
          flushPending();
        } else if (event is AchievementUnlockEvent) {
          // Achievement Unlock Event
          _handleAchievementUnlock(event);
          _ref.read(closeToUnlockProvider.notifier).triggerCheck();
          flushPending();
        } else if (event is AchievementMilestoneEvent) {
          // Achievement Milestone Event
          _handleAchievementMilestone(event);
          flushPending();
        } else if (event is TransparencyStepEvent) {
          // Transparency Step Event
          state = state.copyWith(
            currentStepId: event.currentStep,
            currentStepIndex: event.stepIndex,
          );
          flushPending();
        } else if (event is TransparencyCompleteEvent) {
          // Transparency Complete Event
          state = state.copyWith(
            transparencyData: event.transparencyData,
          );
          flushPending();
        } else if (event is OrchestrationTraceEvent) {
          accumulatedOrchestrationTrace = event.traceData;
          flushPending();
        } else if (event is ModeSuggestionEvent) {
          accumulatedModeSuggestion = event.suggestion;
          flushPending();
        } else if (event is AgentActivityEvent) {
          final activities = [...state.agentActivities];
          final idx = activities.indexWhere((item) => item.agentId == event.agentId);
          if (idx >= 0) {
            activities[idx] = event;
          } else {
            activities.add(event);
          }
          state = state.copyWith(agentActivities: activities);
          flushPending();
        } else if (event is SprintModeSwitchEvent) {
          // Sprint Mode Switch Event
          _handleSprintModeSwitch(event);
          flushPending();
        } else if (event is NotificationEvent) {
          // Notification Event - 实时通知推送
          _handleNotificationEvent(event);
          flushPending();
        } else if (event is CollaborationTimelineEvent) {
          accumulatedCollaboration = event.collaborationData;
          flushPending();
        } else if (event is DoneEvent) {
          // 流结束
          // finishReason: event.finishReason
          flushPending(immediate: true);
          if (state.activeTools.isNotEmpty) {
            state = state.copyWith(activeTools: []);
          }
          if (state.agentActivities.isNotEmpty) {
            snapshotAgentActivities = state.agentActivities
                .map(
                  (item) => {
                    'agent_id': item.agentId,
                    'status': item.status,
                    'display_name': item.displayName,
                    'icon': item.icon,
                    'color': item.color,
                    'description': item.description,
                    if (item.durationMs != null) 'duration_ms': item.durationMs,
                    if (item.resultSummary != null)
                      'result_summary': item.resultSummary,
                    if (item.collaborationMode != null)
                      'collaboration_mode': item.collaborationMode,
                    if (item.phase != null) 'phase': item.phase,
                  },
                )
                .toList();
          }
          // 🔧 修复：清除状态指示器（"思考中"/"生成中"等）
          state = state.copyWith(
            clearAiStatus: true,
            clearDagExecution: true,
            streamingContent: '',
          );
          // 🔧 修复：立即退出流循环，确保执行清理代码（设置 isSending: false）
          break;
        }
      }

      _streamDebouncer.cancel();
      _appendUxWidgets(accumulatedWidgets, accumulatedUxEnvelope);
      // 流结束后，将累积的内容转为正式消息
      if (accumulatedContent.isNotEmpty ||
          accumulatedWidgets.isNotEmpty ||
          accumulatedCollaboration != null ||
          accumulatedUxEnvelope != null) {
        // Calculate total duration if reasoning steps exist
        String? reasoningSummary;
        if (accumulatedReasoningSteps.isNotEmpty &&
            reasoningStartTime != null) {
          final durationMs =
              DateTime.now().millisecondsSinceEpoch - reasoningStartTime;
          reasoningSummary = I18nService.instance.l10n.chatReasoningSummary(
            (durationMs / 1000).toStringAsFixed(1),
            accumulatedReasoningSteps.length,
          );
        }

        final aiMessage = ChatMessageModel(
          id: 'ai_${DateTime.now().millisecondsSinceEpoch}',
          userId: 'ai_assistant',
          conversationId: state.conversationId ?? 'temp_conversation',
          role: MessageRole.assistant,
          content: accumulatedContent,
          createdAt: DateTime.now(),
          widgets: accumulatedWidgets.isNotEmpty ? accumulatedWidgets : null,
          agentCollaboration: accumulatedCollaboration,
          orchestrationTrace: accumulatedOrchestrationTrace,
          modeSuggestion: accumulatedModeSuggestion,
          collaborationNarrative: accumulatedCollaborationNarrative,
          collaborationMode: accumulatedCollaborationMode,
          agentsInvolved: accumulatedAgentsInvolved ?? const [],
          aiStatus: lastAiStatus, // 持久化最后的 AI 状态（如：EXECUTING_TOOL）
          agentActivities: snapshotAgentActivities ?? const [],
          reasoningSteps: accumulatedReasoningSteps.isNotEmpty
              ? accumulatedReasoningSteps
              : null,
          reasoningSummary: reasoningSummary,
          isReasoningComplete: accumulatedReasoningSteps.isNotEmpty,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
          uxEnvelope: accumulatedUxEnvelope,
        );

        state = state.copyWith(
          isSending: false,
          messages: [...state.messages, aiMessage],
          streamingContent: '',
          clearDagExecution: true,
          clearAiStatus: true,
          clearReasoning: true, // Clear real-time reasoning state
          agentActivities: const [],
        );
      } else {
        state = state.copyWith(
          isSending: false,
          streamingContent: '',
          clearDagExecution: true,
          clearAiStatus: true,
          clearReasoning: true,
          agentActivities: const [],
        );
      }
    } catch (e) {
      _streamDebouncer.cancel();
      // 捕获未处理的异常，提供友好的错误提示
      final errorMessage = ErrorMessages.getUserFriendlyMessage(
        'UNKNOWN',
        e.toString(),
      );

      state = state.copyWith(
        isSending: false,
        streamingContent: '',
        clearDagExecution: true,
        agentActivities: const [],
        error: errorMessage,
        errorCode: 'UNKNOWN',
        isErrorRetryable: true, // 未知错误默认可重试
      );
      shouldResetSending = false; // 已经重置过了
    } finally {
      // 🔧 P1-1: 确保 isSending 总是被重置（如果还没被重置）
      if (shouldResetSending && mounted && state.isSending) {
        state = state.copyWith(isSending: false);
      }
    }
  }
}
