import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/utils/error_messages.dart';
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
import 'package:sparkle/features/file/file.dart';
import 'package:sparkle/features/home/presentation/providers/task_board_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/active_plan_provider.dart';
import 'package:sparkle/features/reviews/presentation/providers/nightly_review_provider.dart';
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
    final accumulatedReasoningSteps = <ReasoningStep>[];
    int? reasoningStartTime;
    String? pendingStreamingContent;
    String? pendingAiStatus;
    String? pendingAiStatusDetails;
    List<ReasoningStep>? pendingReasoningSteps;
    bool? pendingReasoningActive;
    int? pendingReasoningStartTime;
    var planContextInjected = false;

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
            if (selectedExpertsRaw != null ||
                routingStrategy != null ||
                fallbackReason != null ||
                routeConfidence != null ||
                expertEntrySource != null) {
              List<String> selectedExperts = const [];
              if (selectedExpertsRaw is List) {
                selectedExperts = selectedExpertsRaw.map((e) => '$e').toList();
              } else if (selectedExpertsRaw is String &&
                  selectedExpertsRaw.isNotEmpty) {
                if (selectedExpertsRaw.trim().startsWith('[')) {
                  try {
                    final decoded = jsonDecode(selectedExpertsRaw);
                    if (decoded is List) {
                      selectedExperts = decoded.map((e) => '$e').toList();
                    }
                  } catch (_) {}
                }
                if (selectedExperts.isEmpty) {
                  selectedExperts = selectedExpertsRaw
                      .split(',')
                      .map((e) => e.trim())
                      .where((e) => e.isNotEmpty)
                      .toList();
                }
              }
              accumulatedCollaboration = {
                ...(accumulatedCollaboration ?? const <String, dynamic>{}),
                'selected_experts': selectedExperts,
                'routing_strategy': routingStrategy,
                'fallback_reason': fallbackReason,
                'route_confidence': routeConfidence,
                'expert_entry_source': expertEntrySource,
              };
            }
          }
          // 流式文本片段（delta）
          accumulatedContent += event.content;
          pendingStreamingContent = accumulatedContent;
          flushPending();
        } else if (event is StatusUpdateEvent) {
          // AI 状态更新（THINKING, GENERATING 等）
          lastAiStatus = event.state;
          pendingAiStatus = event.state;
          pendingAiStatusDetails = event.details;
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
          if (metadata != null) {
            final selectedExpertsRaw = metadata['selected_experts'];
            final routingStrategy = metadata['routing_strategy'];
            final fallbackReason = metadata['fallback_reason'];
            final routeConfidence = metadata['route_confidence'];
            final expertEntrySource = metadata['expert_entry_source'];
            if (selectedExpertsRaw != null ||
                routingStrategy != null ||
                fallbackReason != null ||
                routeConfidence != null ||
                expertEntrySource != null) {
              List<String> selectedExperts = const [];
              if (selectedExpertsRaw is List) {
                selectedExperts = selectedExpertsRaw.map((e) => '$e').toList();
              } else if (selectedExpertsRaw is String &&
                  selectedExpertsRaw.isNotEmpty) {
                if (selectedExpertsRaw.trim().startsWith('[')) {
                  try {
                    final decoded = jsonDecode(selectedExpertsRaw);
                    if (decoded is List) {
                      selectedExperts = decoded.map((e) => '$e').toList();
                    }
                  } catch (_) {}
                }
                if (selectedExperts.isEmpty) {
                  selectedExperts = selectedExpertsRaw
                      .split(',')
                      .map((e) => e.trim())
                      .where((e) => e.isNotEmpty)
                      .toList();
                }
              }
              accumulatedCollaboration = {
                ...(accumulatedCollaboration ?? const <String, dynamic>{}),
                'selected_experts': selectedExperts,
                'routing_strategy': routingStrategy,
                'fallback_reason': fallbackReason,
                'route_confidence': routeConfidence,
                'expert_entry_source': expertEntrySource,
              };
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
          final isRetryable = ErrorMessages.isRetryable(event.code);

          state = state.copyWith(
            error: userFriendlyMessage,
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
            WidgetPayload(
              type: event.widgetType,
              data: event.widgetData,
            ),
          );
        } else if (event is ToolStartEvent) {
          // 显示"正在使用工具: xxx"
          lastAiStatus = 'EXECUTING_TOOL';
          pendingAiStatus = 'EXECUTING_TOOL';
          pendingAiStatusDetails = '正在使用 ${event.toolName}...';
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
            accumulatedWidgets.add(
              WidgetPayload(
                type: widgetType,
                data: widgetData,
              ),
            );
          }
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
        } else if (event is SprintModeSwitchEvent) {
          // Sprint Mode Switch Event
          _handleSprintModeSwitch(event);
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
      // 流结束后，将累积的内容转为正式消息
      if (accumulatedContent.isNotEmpty ||
          accumulatedWidgets.isNotEmpty ||
          accumulatedCollaboration != null) {
        // Calculate total duration if reasoning steps exist
        String? reasoningSummary;
        if (accumulatedReasoningSteps.isNotEmpty &&
            reasoningStartTime != null) {
          final durationMs =
              DateTime.now().millisecondsSinceEpoch - reasoningStartTime;
          reasoningSummary =
              '完成于 ${(durationMs / 1000).toStringAsFixed(1)}s，${accumulatedReasoningSteps.length}个步骤';
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
          aiStatus: lastAiStatus, // 持久化最后的 AI 状态（如：EXECUTING_TOOL）
          reasoningSteps: accumulatedReasoningSteps.isNotEmpty
              ? accumulatedReasoningSteps
              : null,
          reasoningSummary: reasoningSummary,
          isReasoningComplete: accumulatedReasoningSteps.isNotEmpty,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
        );

        state = state.copyWith(
          isSending: false,
          messages: [...state.messages, aiMessage],
          streamingContent: '',
          clearDagExecution: true,
          clearAiStatus: true,
          clearReasoning: true, // Clear real-time reasoning state
        );
      } else {
        state = state.copyWith(
          isSending: false,
          streamingContent: '',
          clearDagExecution: true,
          clearAiStatus: true,
          clearReasoning: true,
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
