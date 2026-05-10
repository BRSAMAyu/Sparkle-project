import 'dart:async';
import 'dart:convert';

import 'package:async/async.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/errors/failures.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/providers/experience_envelope_provider.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/intervention_action_service.dart';
import 'package:sparkle/core/utils/error_messages.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/achievement/presentation/providers/close_to_unlock_provider.dart';
import 'package:sparkle/features/achievement/presentation/providers/home_close_to_unlock_provider.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';
import 'package:sparkle/features/chat/data/models/reasoning_step_model.dart';
import 'package:sparkle/features/chat/presentation/widgets/causal_timeline_panel.dart';
import 'package:sparkle/features/chat/data/repositories/chat_repository.dart';
import 'package:sparkle/features/chat/data/services/agent_session_store.dart';
import 'package:sparkle/features/chat/data/services/plan_review_grpc_service.dart';
import 'package:sparkle/features/chat/data/services/review_grpc_service.dart';
import 'package:sparkle/features/chat/data/services/websocket_chat_service_v2.dart';
import 'package:sparkle/features/chat/presentation/providers/agent_session_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_mode_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_state.dart';
import 'package:sparkle/features/chat/presentation/providers/guidance_mode_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/low_yield_block_provider.dart';
import 'package:sparkle/features/chat/presentation/widgets/content_review_card.dart';
import 'package:sparkle/features/chat/presentation/widgets/plan_review_card.dart';
import 'package:sparkle/features/chat/presentation/widgets/plan_switch_confirmation_dialog.dart';
import 'package:sparkle/features/file/file.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/task_board_provider.dart';
import 'package:sparkle/features/notification_center/notification_center.dart';
import 'package:sparkle/features/plan/presentation/providers/active_plan_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/reviews/presentation/providers/nightly_review_provider.dart';
import 'package:sparkle/features/seed_library/presentation/providers/seed_library_provider.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/features/task/task_routes.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/shared/utils/entity_card_payloads.dart';

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

  static const int historyPageSize = 20;

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

  // P0修复: 跟踪当前正在加载历史的会话ID，防止并发加载和计划切换竞态
  String? loadingConversationId;

  // P0修复: 可取消的历史加载操作，用于切换会话时取消之前的加载请求
  CancelableOperation<List<ChatMessageModel>>? _historyLoadOperation;

  // P0修复: 计划切换进行中标志，阻止切换期间发送消息防止消息发送到错误上下文
  bool isSwitchingPlan = false;
  _PendingChatRequest? _retryableRequest;

  // Any response stream created before the latest generation value becomes
  // stale and must not mutate the current chat UI.
  int _streamGeneration = 0;
  int _runSequence = 0;

  /// Clear the current error state
  void clearError() {
    state = state.copyWith(clearError: true);
  }

  /// 手动触发重连
  Future<void> reconnect() async {
    await _chatRepository.reconnect();
  }

  Future<void> warmUpConnection() async {
    try {
      final authState = _ref.read(authProvider);
      final userId = authState.user?.id ??
          await _ref.read(guestServiceProvider).getGuestId();
      if (userId.isEmpty) {
        return;
      }
      final token = await _ref.read(authRepositoryProvider).getAccessToken();
      await _chatRepository.ensureConnected(userId: userId, token: token);
    } catch (error, stackTrace) {
      debugPrint('[ChatProvider] warmUpConnection failed: $error');
      debugPrintStack(stackTrace: stackTrace);
    }
  }

  String _nextClientRunId() =>
      'run_${DateTime.now().microsecondsSinceEpoch}_${_runSequence++}';

  ActiveRunSummary _buildRunSummary({
    String? status,
    String? details,
    String? agentName,
    int? currentStepIndex,
    int? totalSteps,
    List<String>? activeTools,
    int? startedAtEpochMs,
  }) =>
      ActiveRunSummary(
        status: status ?? state.aiStatus,
        details: details ?? state.aiStatusDetails,
        agentName: agentName ?? state.currentAgentName,
        toolCount: activeTools?.length ?? state.activeTools.length,
        currentStepIndex: currentStepIndex ?? state.currentStepIndex,
        totalSteps: totalSteps ??
            state.transparencyData?.steps.length ??
            state.activeRunSummary?.totalSteps,
        startedAtEpochMs:
            startedAtEpochMs ?? state.activeRunSummary?.startedAtEpochMs,
      );

  void _invalidateActiveStreamState({
    ChatRunPhase phase = ChatRunPhase.cancelled,
    String? completedLabel,
    bool clearCompletedLabel = false,
  }) {
    _streamGeneration++;
    state = state.copyWith(
      isSending: false,
      streamingContent: '',
      clearAiStatus: true,
      clearReasoning: true,
      clearDagExecution: true,
      clearTransparency: true,
      clearRoundtable: true,
      agentActivities: const [],
      activeTools: const [],
      clearActiveRunId: true,
      runPhase: phase,
      clearActiveRunSummary: true,
      transparencyPresentationState:
          state.transparencyPresentationState.copyWith(
        isExpanded: false,
        isDismissed: false,
        lastCompletedLabel: completedLabel,
        clearLastCompletedLabel: clearCompletedLabel,
      ),
    );
  }

  void _beginRun({
    required String runId,
    ChatMessageModel? userMessage,
  }) {
    final nowMs = DateTime.now().millisecondsSinceEpoch;
    state = state.copyWith(
      messages: userMessage == null
          ? state.messages
          : [...state.messages, userMessage],
      isSending: true,
      hasMoreMessages: false,
      streamingContent: '',
      activeTools: const [],
      agentActivities: const [],
      clearRoundtable: true,
      clearDagExecution: true,
      clearTransparency: true,
      clearError: true,
      activeRunId: runId,
      runPhase: ChatRunPhase.sending,
      activeRunSummary: ActiveRunSummary(startedAtEpochMs: nowMs),
      transparencyPresentationState:
          state.transparencyPresentationState.copyWith(
        isExpanded: false,
        isDismissed: false,
        clearLastCompletedLabel: true,
      ),
    );
  }

  void cancelActiveRun({String reason = 'superseded'}) {
    if (!state.isSending && state.activeRunId == null) {
      return;
    }
    debugPrint('[Chat] cancelActiveRun: $reason');
    _streamDebouncer.cancel();
    _invalidateActiveStreamState();
  }

  @override
  void dispose() {
    _streamDebouncer.cancel();
    _chatRepository.dispose();
    _planReviewService?.close();
    _reviewService?.close();
    _isDisposed = true;
    unawaited(_historyLoadOperation?.cancel());
    _historyLoadOperation = null;
    unawaited(_connectionStateSubscription?.cancel());
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

  Map<String, dynamic>? _parseJsonMap(dynamic raw) {
    if (raw is Map<String, dynamic>) {
      return raw;
    }
    if (raw is Map) {
      return Map<String, dynamic>.from(raw);
    }
    if (raw is String && raw.isNotEmpty) {
      try {
        final decoded = jsonDecode(raw);
        if (decoded is Map<String, dynamic>) {
          return decoded;
        }
        if (decoded is Map) {
          return Map<String, dynamic>.from(decoded);
        }
      } catch (_) {}
    }
    return null;
  }

  List<String> _parseStringList(dynamic raw) {
    if (raw is List) {
      return raw
          .map((item) => item.toString().trim())
          .where((item) => item.isNotEmpty)
          .toList();
    }
    if (raw is String && raw.isNotEmpty) {
      return raw
          .split('\n')
          .map((item) => item.trim())
          .where((item) => item.isNotEmpty)
          .toList();
    }
    return const [];
  }

  String? _buildExecutionProgressDetails(dynamic raw) {
    final progress = _parseJsonMap(raw);
    if (progress == null || progress.isEmpty) {
      return null;
    }
    final currentStep = progress['current_step']?.toString().trim();
    final recentOutput = _parseStringList(progress['recent_output']);
    final lines = <String>[
      if (currentStep != null && currentStep.isNotEmpty) currentStep,
      ...recentOutput.take(3),
    ];
    if (lines.isEmpty) {
      return null;
    }
    return lines.join('\n');
  }

  List<Map<String, dynamic>> _parseJsonMapList(dynamic raw) {
    if (raw is List) {
      return raw
          .whereType<Map<dynamic, dynamic>>()
          .map(Map<String, dynamic>.from)
          .toList();
    }
    if (raw is String && raw.isNotEmpty) {
      try {
        final decoded = jsonDecode(raw);
        if (decoded is List) {
          return decoded
              .whereType<Map<dynamic, dynamic>>()
              .map(Map<String, dynamic>.from)
              .toList();
        }
      } catch (_) {}
    }
    return const [];
  }

  bool _parseMetadataFlag(dynamic raw) {
    if (raw is bool) {
      return raw;
    }
    final value = raw?.toString().trim().toLowerCase();
    return value == 'true' || value == '1' || value == 'yes';
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
      final label = item['label']?.toString() ??
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
      'adaptation_summary',
      'continuity_banner',
      'mode_explanation',
      'collaboration_summary',
    ]) {
      final value = metadata[key];
      if (value is Map<String, dynamic> && value.isNotEmpty) {
        envelope[key] = value;
      }
    }
    final structuredAdjustments =
        _parseJsonMapList(metadata['structured_cognitive_adjustments']);
    if (structuredAdjustments.isNotEmpty) {
      envelope['structured_cognitive_adjustments'] = structuredAdjustments;
      final uxTurn =
          Map<String, dynamic>.from(envelope['ux_turn'] as Map? ?? const {});
      envelope['ux_turn'] = {
        ...uxTurn,
        'structured_cognitive_adjustments': structuredAdjustments,
      };
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

    final adaptationSummary = uxEnvelope['adaptation_summary'];
    if (adaptationSummary is Map<String, dynamic>) {
      addWidget('adaptation_summary', adaptationSummary);
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
        'title': followthrough['next_actions_title']?.toString() ??
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
          'title': result['headline']?.toString() ?? l10n.chatBlockedInputTitle,
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

  void _upsertWidget(
    List<WidgetPayload> target,
    String type,
    Map<String, dynamic> data,
  ) {
    if (data.isEmpty) return;
    final index = target.indexWhere((widget) => widget.type == type);
    final payload = WidgetPayload(type: type, data: data);
    if (index >= 0) {
      target[index] = payload;
    } else {
      target.add(payload);
    }
  }

  void _appendExecutionWidgets(
    List<WidgetPayload> target,
    Map<String, dynamic>? metadata,
  ) {
    if (metadata == null || metadata.isEmpty) return;

    final taskStuck = _parseJsonMap(metadata['task_stuck_intervention']);
    if (taskStuck != null && taskStuck.isNotEmpty) {
      _upsertWidget(target, 'task_stuck_card', taskStuck);
    }

    final suggestion = _parseJsonMap(metadata['execution_suggestion']);
    if (suggestion != null && suggestion['task_id'] != null) {
      final taskId = suggestion['task_id'].toString();
      final targetEnv = suggestion['target_env']?.toString() ?? 'general';
      final executionMode = suggestion['execution_mode']?.toString() ?? 'agent';
      final tone = suggestion['tone']?.toString() ?? 'brief_handoff';
      final reason = suggestion['reason']?.toString() ?? '';
      _upsertWidget(target, 'execution_suggestion', {
        'task_id': taskId,
        'target_env': targetEnv,
        'execution_mode': executionMode,
        'tone': tone,
        'reason': reason,
        'source': suggestion['source']?.toString() ?? 'execution_suggestion',
        'delegate_preference': suggestion['delegate_preference'],
        'title': tone == 'detailed_guidance'
            ? S.chatAiExecutionSuitable
            : S.chatAiExecutionDirect,
        'summary': reason.isNotEmpty ? reason : S.chatExecutionDelegatable,
        'route': '${TaskRoutes.home}/$taskId/execute?origin=chat',
      });
    }

    final validation = _parseJsonMap(metadata['execution_validation']);
    if (validation == null) return;
    final toolsTotal = (validation['tools_total'] as num?)?.toInt() ?? 0;
    final toolsSuccessful =
        (validation['tools_successful'] as num?)?.toInt() ?? 0;
    final stepsTotal = (validation['steps_total'] as num?)?.toInt() ?? 0;
    final stepsPassed = (validation['steps_passed'] as num?)?.toInt() ?? 0;
    final qualityScore = (validation['quality_score'] as num?)?.toDouble();
    final validationStatus = validation['validation_status']?.toString() ?? '';
    final aborted = validation['aborted'] == true;
    final hasMeaningfulValidation =
        toolsTotal > 0 || stepsTotal > 0 || qualityScore != null;
    if (!hasMeaningfulValidation) return;

    final failedTools = toolsTotal > 0 ? toolsTotal - toolsSuccessful : 0;
    final failedSteps = stepsTotal > 0 ? stepsTotal - stepsPassed : 0;
    final status = aborted || validationStatus == 'failed'
        ? 'failed'
        : (failedTools > 0 || failedSteps > 0)
            ? 'partial'
            : 'success';

    final affectedObjects = <String>[
      if (stepsTotal > 0) S.chatValidationSteps(stepsPassed, stepsTotal),
      if (toolsTotal > 0) S.chatValidationTools(toolsSuccessful, toolsTotal),
      if (qualityScore != null)
        S.chatValidationQuality((qualityScore * 100).toStringAsFixed(0)),
    ];

    _upsertWidget(target, 'execution_summary', {
      'status': status,
      'impact_summary': status == 'success'
          ? S.chatExecutionSuccessSummary
          : status == 'partial'
              ? S.chatExecutionPartialSummary
              : S.chatExecutionFailedSummary,
      'next_action':
          status == 'success' ? S.chatViewResults : S.chatManualReview,
      'affected_objects': affectedObjects,
      if (_parseJsonMap(validation['result_preview']) != null)
        'result_preview': _parseJsonMap(validation['result_preview']),
      if (_parseJsonMapList(validation['replay_steps']).isNotEmpty)
        'replay_steps': _parseJsonMapList(validation['replay_steps']),
      if (_parseJsonMapList(validation['quality_warnings']).isNotEmpty)
        'quality_warnings': _parseJsonMapList(validation['quality_warnings']),
      if ((validation['validation_issues'] as List?)?.isNotEmpty ?? false)
        'validation_issues': List<String>.from(
          (validation['validation_issues'] as List<dynamic>)
              .map((item) => '$item')
              .where((item) => item.isNotEmpty),
        ),
      if ((validation['comparison_summary']?.toString() ?? '').isNotEmpty)
        'comparison_summary': validation['comparison_summary'],
      if (_parseJsonMap(validation['self_verification']) != null)
        'self_verification': _parseJsonMap(validation['self_verification']),
      if (qualityScore != null) 'quality_score': qualityScore,
      if (stepsTotal > 0) 'validation_passed': stepsPassed,
      if (stepsTotal > 0) 'validation_total': stepsTotal,
    });
  }

  WidgetPayload _normalizeWidgetPayload(
    String type,
    Map<String, dynamic> data,
  ) {
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
            if (metadata['confidence'] != null)
              'confidence': metadata['confidence'],
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

  /// Prepend a local AI welcome message (no backend call).
  /// Used after onboarding to show the AI's personalized opener immediately.
  void prependWelcomeMessage(String content) {
    if (content.trim().isEmpty) return;
    // Don't inject if there are already messages (e.g., returning to chat tab)
    if (state.messages.isNotEmpty) return;
    final welcome = ChatMessageModel(
      id: 'welcome_${DateTime.now().millisecondsSinceEpoch}',
      conversationId: state.conversationId ?? 'onboarding',
      role: MessageRole.assistant,
      content: content.trim(),
      createdAt: DateTime.now(),
    );
    state = state.copyWith(messages: [welcome]);
  }

  void showDailyStartupMessage(
    String content, {
    required String planId,
    required String dateKey,
  }) {
    final trimmed = content.trim();
    if (trimmed.isEmpty) return;
    if (state.messages.any((message) => message.role == MessageRole.user)) {
      return;
    }

    final safePlanId = planId.replaceAll(RegExp('[^a-zA-Z0-9_-]'), '_');
    final messageId = 'daily_startup_${safePlanId}_$dateKey';
    if (state.messages.any((message) => message.id == messageId)) {
      return;
    }

    final retainedMessages = state.messages
        .where(
          (message) =>
              !message.id.startsWith('daily_startup_') &&
              !message.id.startsWith('welcome_'),
        )
        .toList(growable: false);
    final startup = ChatMessageModel(
      id: messageId,
      conversationId: state.conversationId ?? 'daily_startup',
      role: MessageRole.assistant,
      content: trimmed,
      createdAt: DateTime.now(),
    );
    state = state.copyWith(messages: [...retainedMessages, startup]);
  }

  void showComebackMessage(
    String content, {
    required String planId,
    required int daysAway,
  }) {
    final trimmed = content.trim();
    if (trimmed.isEmpty) return;
    if (state.messages.any((message) => message.role == MessageRole.user)) {
      return;
    }

    final safePlanId = planId.replaceAll(RegExp('[^a-zA-Z0-9_-]'), '_');
    final messageId = 'comeback_${safePlanId}_$daysAway';
    if (state.messages.any((message) => message.id == messageId)) {
      return;
    }

    final retainedMessages = state.messages
        .where(
          (message) =>
              !message.id.startsWith('comeback_') &&
              !message.id.startsWith('daily_startup_') &&
              !message.id.startsWith('welcome_'),
        )
        .toList(growable: false);
    final comeback = ChatMessageModel(
      id: messageId,
      conversationId: state.conversationId ?? 'comeback',
      role: MessageRole.assistant,
      content: trimmed,
      createdAt: DateTime.now(),
    );
    state = state.copyWith(messages: [...retainedMessages, comeback]);
  }

  /// 发送消息 (使用 SSE/WebSocket 流式响应)
  Future<void> sendMessage(
    String content, {
    String? taskId,
    Map<String, dynamic>? extraContextOverrides,
    bool reuseLastUserMessage = false,
  }) async {
    // P0修复: 计划切换期间禁止发送，防止消息关联到错误的计划上下文
    if (isSwitchingPlan) {
      debugPrint('[Chat] sendMessage blocked: plan switch in progress');
      return;
    }

    if (state.isSending) {
      cancelActiveRun(reason: 'new_message');
    }

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

    final runId = _nextClientRunId();
    final request = _PendingChatRequest(
      content: content,
      taskId: taskId,
      extraContextOverrides: extraContextOverrides == null
          ? null
          : Map<String, dynamic>.from(extraContextOverrides),
    );
    _retryableRequest = request;
    final requestGeneration = ++_streamGeneration;
    bool isCurrentRequest() => requestGeneration == _streamGeneration;
    final queuedAttachments = List<StoredFile>.from(state.attachedFiles);
    final hasQueuedAttachments = queuedAttachments.isNotEmpty;

    final canReuseLastUserMessage = reuseLastUserMessage &&
        state.messages.isNotEmpty &&
        state.messages.last.role == MessageRole.user &&
        state.messages.last.content == content &&
        state.messages.last.taskId == taskId;

    if (canReuseLastUserMessage) {
      _beginRun(runId: runId);
    } else {
      final userMessage = ChatMessageModel(
        id: 'temp_user_${DateTime.now().millisecondsSinceEpoch}',
        userId: userId,
        conversationId: state.conversationId ?? 'temp_conversation',
        role: MessageRole.user,
        content: content,
        taskId: taskId,
        createdAt: DateTime.now(),
      );
      _beginRun(runId: runId, userMessage: userMessage);
    }

    var accumulatedContent = '';
    String? responseId;
    String? traceId;
    String? workflowId;
    String? promptVersion;
    String? lastAiStatus;
    final accumulatedWidgets = <WidgetPayload>[];
    Map<String, dynamic>? accumulatedCollaboration;
    Map<String, dynamic>? accumulatedUxEnvelope;
    final accumulatedRawMetadata = <String, dynamic>{};
    List<Map<String, dynamic>>? accumulatedStructuredAdjustments;
    Map<String, dynamic>? accumulatedOrchestrationTrace;
    Map<String, dynamic>? accumulatedModeSuggestion;
    Map<String, dynamic>? accumulatedRoutingPreview;
    String? accumulatedCollaborationNarrative;
    String? accumulatedCollaborationMode;
    List<String>? accumulatedAgentsInvolved;
    final accumulatedRoundtableTurns = <Map<String, dynamic>>[];
    final accumulatedMeta = <String, dynamic>{};
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
    var sawTerminalEvent = false;
    var shouldResetSending = true;

    void upsertSourceSummaryCitations(List<Map<String, dynamic>> citations) {
      accumulatedRawMetadata['citations'] =
          List<Map<String, dynamic>>.from(citations);
      final data = {
        'citations_available': citations.isNotEmpty,
        'reference_scope': citations.every(
          (citation) => (citation['file_id']?.toString() ?? '').isNotEmpty,
        )
            ? 'file_only'
            : 'mixed',
        'evidence_summary': citations.isNotEmpty
            ? I18nService.instance.l10n.chatSourcesAvailable
            : I18nService.instance.l10n.chatSourcesUnavailable,
        'citations': citations,
      };
      final existingIndex = accumulatedWidgets.indexWhere(
        (widget) => widget.type == 'source_summary',
      );
      if (existingIndex >= 0) {
        accumulatedWidgets[existingIndex] = WidgetPayload(
          type: 'source_summary',
          data: data,
        );
      } else {
        accumulatedWidgets.add(
          WidgetPayload(
            type: 'source_summary',
            data: data,
          ),
        );
      }
    }

    void captureCitationMetadata(dynamic rawCitations) {
      if (rawCitations is! List || rawCitations.isEmpty) {
        return;
      }
      final citations = rawCitations
          .whereType<Map<dynamic, dynamic>>()
          .map(Map<String, dynamic>.from)
          .toList();
      if (citations.isEmpty) {
        return;
      }
      upsertSourceSummaryCitations(citations);
    }

    void captureStructuredAdjustments(Map<String, dynamic>? metadata) {
      if (metadata == null) {
        return;
      }
      final adjustments =
          _parseJsonMapList(metadata['structured_cognitive_adjustments']);
      if (adjustments.isEmpty) {
        return;
      }
      accumulatedStructuredAdjustments = adjustments;
      accumulatedRawMetadata['structured_cognitive_adjustments'] = adjustments;
    }

    Map<String, dynamic>? extractLowYieldPayload(
      Map<String, dynamic>? metadata,
    ) {
      if (metadata == null || metadata.isEmpty) {
        return null;
      }
      const keys = [
        'low_yield_gentle_block',
        'low_yield_block',
        'low_yield_guard',
        'yield_check',
      ];
      for (final key in keys) {
        final value = metadata[key];
        if (value is Map<String, dynamic>) {
          return value;
        }
        if (value is Map) {
          return Map<String, dynamic>.from(value);
        }
      }
      if (metadata['event_type'] == 'low_yield_block') {
        final payload = metadata['event_payload'];
        if (payload is Map<String, dynamic>) {
          return payload;
        }
        if (payload is Map) {
          return Map<String, dynamic>.from(payload);
        }
        return metadata;
      }
      return null;
    }

    void captureLowYieldBlock(Map<String, dynamic>? metadata) {
      final payload = extractLowYieldPayload(metadata);
      if (payload == null || payload.isEmpty) {
        return;
      }
      _ref.read(lowYieldBlockProvider.notifier).ingestPayload(payload);
      final blockId = payload['id']?.toString() ??
          payload['block_id']?.toString() ??
          payload['intervention_id']?.toString();
      final alreadyAdded = accumulatedWidgets.any(
        (widget) =>
            widget.type == 'low_yield_gentle_block' &&
            (blockId == null ||
                widget.data['id']?.toString() == blockId ||
                widget.data['block_id']?.toString() == blockId ||
                widget.data['intervention_id']?.toString() == blockId),
      );
      if (!alreadyAdded) {
        accumulatedWidgets.add(
          WidgetPayload(type: 'low_yield_gentle_block', data: payload),
        );
      }
    }

    void flushPending({bool immediate = false}) {
      void applyPending() {
        if (_isDisposed || !isCurrentRequest()) return;
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
          runPhase: (pendingStreamingContent?.isNotEmpty ?? false) ||
                  (pendingReasoningActive ?? false) ||
                  (pendingAiStatus?.isNotEmpty ?? false)
              ? ChatRunPhase.streaming
              : state.runPhase,
          activeRunSummary: _buildRunSummary(
            status: pendingAiStatus,
            details: pendingAiStatusDetails,
          ),
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

    void finalizeRun({
      required ChatRunPhase phase,
      String? errorMessage,
      String? errorCode,
      bool isRetryable = false,
      bool restoreAttachments = false,
    }) {
      if (!isCurrentRequest() || sawTerminalEvent) {
        return;
      }
      sawTerminalEvent = true;
      _streamDebouncer.cancel();
      unawaited(BgmService.setThinkingActivity(false));
      _appendUxWidgets(accumulatedWidgets, accumulatedUxEnvelope);

      final hasRenderableMessage = accumulatedContent.trim().isNotEmpty ||
          accumulatedWidgets.isNotEmpty ||
          accumulatedCollaboration != null ||
          accumulatedUxEnvelope != null;

      // For failed streams, only preserve as a message if there's meaningful
      // structured content (widgets/envelope). Bare partial text from a
      // disrupted stream should not be rendered — the user will retry and
      // get the full response, avoiding duplicate partial+full messages.
      final shouldPreserveMessage = phase == ChatRunPhase.completed ||
          accumulatedWidgets.isNotEmpty ||
          accumulatedUxEnvelope != null ||
          accumulatedCollaboration != null;

      if (hasRenderableMessage && shouldPreserveMessage) {
        var resolvedContent = accumulatedContent;
        if (resolvedContent.trim().isEmpty && phase == ChatRunPhase.completed) {
          if (accumulatedWidgets.isNotEmpty || accumulatedUxEnvelope != null) {
            resolvedContent = S.chatNextStepsReady;
          } else if (accumulatedCollaboration != null) {
            resolvedContent = S.chatCollaborationResultReady;
          }
        }
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

        final messageMeta = accumulatedMeta.isNotEmpty
            ? MessageMeta.fromLooseJson(accumulatedMeta)
            : null;

        final aiMessage = ChatMessageModel(
          id: 'ai_${DateTime.now().millisecondsSinceEpoch}',
          userId: 'ai_assistant',
          conversationId: state.conversationId ?? 'temp_conversation',
          role: MessageRole.assistant,
          content: resolvedContent,
          createdAt: DateTime.now(),
          widgets: accumulatedWidgets.isNotEmpty ? accumulatedWidgets : null,
          agentCollaboration: accumulatedCollaboration,
          orchestrationTrace: accumulatedOrchestrationTrace,
          modeSuggestion: accumulatedModeSuggestion,
          collaborationNarrative: accumulatedCollaborationNarrative,
          collaborationMode: accumulatedCollaborationMode,
          agentsInvolved: accumulatedAgentsInvolved ?? const [],
          aiStatus: lastAiStatus,
          agentActivities: snapshotAgentActivities ?? const [],
          reasoningSteps: accumulatedReasoningSteps.isNotEmpty
              ? accumulatedReasoningSteps
              : null,
          reasoningSummary: reasoningSummary,
          isReasoningComplete: accumulatedReasoningSteps.isNotEmpty,
          meta: messageMeta,
          responseId: responseId,
          traceId: traceId,
          workflowId: workflowId,
          promptVersion: promptVersion,
          uxEnvelope: accumulatedUxEnvelope,
          rawMetadata:
              accumulatedRawMetadata.isNotEmpty ? accumulatedRawMetadata : null,
          structuredCognitiveAdjustments:
              accumulatedStructuredAdjustments ?? const [],
        );

        state = state.copyWith(
          messages: [...state.messages, aiMessage],
        );
      }

      state = state.copyWith(
        isSending: false,
        streamingContent: '',
        clearDagExecution: true,
        clearAiStatus: true,
        clearReasoning: true,
        clearTransparency: true,
        clearRoundtable: true,
        agentActivities: const [],
        activeTools: const [],
        clearActiveRunId: true,
        runPhase: phase,
        clearActiveRunSummary: true,
        transparencyPresentationState:
            state.transparencyPresentationState.copyWith(
          isExpanded: false,
          isDismissed: false,
          lastCompletedLabel:
              phase == ChatRunPhase.completed ? S.chatCompleted : null,
          clearLastCompletedLabel: phase != ChatRunPhase.completed,
        ),
        error: errorMessage,
        errorCode: errorCode,
        isErrorRetryable: errorMessage == null ? false : isRetryable,
        attachedFiles: restoreAttachments ? queuedAttachments : const [],
      );
      if (phase == ChatRunPhase.completed) {
        _retryableRequest = null;
      }
      shouldResetSending = false;
    }

    try {
      final token = await _ref.read(authRepositoryProvider).getAccessToken();
      final fileIds = state.attachedFiles.map((file) => file.id).toList();
      final useDocumentContext = state.documentRetrievalEnabled;
      state = state.copyWith(clearAttachments: true);

      // Get selected plan for chat context
      final selectedPlanId = _ref.read(activePlanProvider);
      final reasoningMode = _ref.read(aiReasoningModeProvider);
      final seedLibraryEnabled = _ref.read(chatSeedLibraryEnabledProvider);
      final activeSeedSubscriptions = _ref
          .read(subscriptionsProvider)
          .subscriptions
          .where((subscription) => subscription.isEnabled)
          .toList()
        ..sort((a, b) => b.priority.compareTo(a.priority));
      final extraContext = <String, dynamic>{
        if (selectedPlanId != null) 'plan_id': selectedPlanId,
        'reasoning_mode': reasoningMode,
        'guidance_mode': _ref.read(guidanceModeProvider).name,
        'use_document_context': useDocumentContext,
        'document_context_scope': state.documentContextMode.name,
        'seed_library_enabled': seedLibraryEnabled,
        if (seedLibraryEnabled) ...{
          'active_seed_library_ids':
              activeSeedSubscriptions.map((sub) => sub.libraryId).toList(),
          'active_seed_libraries': activeSeedSubscriptions
              .map(
                (sub) => {
                  'library_id': sub.libraryId,
                  'priority': sub.priority,
                  'name': sub.library?.name,
                },
              )
              .toList(),
        },
        ...?extraContextOverrides,
      };

      // Get selected chat mode
      final chatMode = _ref.read(chatModeProvider);
      final chatModeValue = chatMode.apiValue;

      // Long-running expert and study-plan flows can stay silent for minutes
      // before the first token arrives. Keep a hard inactivity guard, but do
      // not abort healthy generations too early.
      const streamTimeout = Duration(minutes: 8);

      // Create a timeout wrapper for the stream
      final rawStream = _chatRepository.chatStream(
        content,
        state.conversationId,
        userId: userId,
        nickname: nickname,
        token: token,
        fileIds: fileIds,
        includeReferences: useDocumentContext || fileIds.isNotEmpty,
        extraContext: extraContext,
        chatMode: chatModeValue,
        requestId: runId,
        useDocumentContext: useDocumentContext,
      );

      // Wrap with timeout check
      final timedStream = rawStream.timeout(
        streamTimeout,
        onTimeout: (sink) {
          debugPrint('[ChatProvider] Stream timeout after $streamTimeout');
          sink
            ..add(
              ErrorEvent(
                code: 'STREAM_TIMEOUT',
                message:
                    'Stream timed out after ${streamTimeout.inSeconds} seconds of inactivity',
                retryable: true,
              ),
            )
            ..close();
        },
      );

      await for (final event in timedStream) {
        if (!isCurrentRequest()) {
          break;
        }
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
        // Capture sessionId from backend response to maintain conversation continuity
        if (event.sessionId != null && event.sessionId!.isNotEmpty) {
          state = state.copyWith(conversationId: event.sessionId);
        }

        if (event is TextEvent) {
          unawaited(BgmService.setThinkingActivity(true));
          final metadata = event.metadata;
          if (metadata != null) {
            accumulatedMeta.addAll(metadata);
            accumulatedRawMetadata.addAll(metadata);
            _appendExecutionWidgets(accumulatedWidgets, metadata);
            captureCitationMetadata(metadata['citations']);
            captureStructuredAdjustments(metadata);
            captureLowYieldBlock(metadata);
            _ref.read(experienceEnvelopeProvider.notifier).updateFromMetadata(accumulatedRawMetadata);
          }
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
            final answerExpertsRaw = metadata['answer_experts'];
            final routingStrategy = metadata['routing_strategy'];
            final fallbackReason = metadata['fallback_reason'];
            final routeConfidence = metadata['route_confidence'];
            final expertEntrySource = metadata['expert_entry_source'];
            final routingPreview = _parseJsonMap(metadata['routing_preview']);
            final roundtableTurns =
                _parseJsonMapList(metadata['roundtable_turns']);
            final primaryAgent = metadata['primary_agent']?.toString();
            final collaborationNarrative =
                metadata['collaboration_narrative']?.toString();
            final collaborationMode =
                metadata['collaboration_mode']?.toString();
            final predictionPreview =
                _parseJsonMap(metadata['prediction_preview']);
            final simulationPreview =
                _parseJsonMap(metadata['simulation_preview']);
            final reportPreview = _parseJsonMap(metadata['report_preview']);
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
                'answer_experts': _parseSelectedExperts(answerExpertsRaw),
                'routing_strategy': routingStrategy,
                'fallback_reason': fallbackReason,
                'route_confidence': routeConfidence,
                'expert_entry_source': expertEntrySource,
              };
            }
            if (routingPreview != null && routingPreview.isNotEmpty) {
              accumulatedRoutingPreview = routingPreview;
              accumulatedCollaboration = {
                ...(accumulatedCollaboration ?? const <String, dynamic>{}),
                'routing_preview': routingPreview,
              };
              state = state.copyWith(routingPreview: routingPreview);
            }
            if (roundtableTurns.isNotEmpty) {
              accumulatedRoundtableTurns
                ..clear()
                ..addAll(roundtableTurns);
              accumulatedCollaboration = {
                ...(accumulatedCollaboration ?? const <String, dynamic>{}),
                'roundtable_turns':
                    List<Map<String, dynamic>>.from(accumulatedRoundtableTurns),
              };
              state = state.copyWith(
                roundtableTurns:
                    List<Map<String, dynamic>>.from(accumulatedRoundtableTurns),
              );
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
            } else if (primaryAgent != null && primaryAgent.isNotEmpty) {
              accumulatedAgentsInvolved = [primaryAgent];
            }
            if (_parseMetadataFlag(metadata['open_theater']) &&
                predictionPreview != null) {
              accumulatedCollaboration = {
                ...(accumulatedCollaboration ?? const <String, dynamic>{}),
                'open_theater': true,
                'deep_link': metadata['deep_link']?.toString(),
                'prediction_preview': predictionPreview,
                'source_chat_session_id':
                    metadata['source_chat_session_id']?.toString(),
              };
            }
            if (_parseMetadataFlag(metadata['open_simulation']) &&
                simulationPreview != null) {
              accumulatedCollaboration = {
                ...(accumulatedCollaboration ?? const <String, dynamic>{}),
                'open_simulation': true,
                'simulation_deep_link':
                    metadata['simulation_deep_link']?.toString(),
                'simulation_preview': simulationPreview,
                'source_chat_session_id':
                    metadata['source_chat_session_id']?.toString(),
              };
            }
            if (_parseMetadataFlag(metadata['open_report']) &&
                reportPreview != null) {
              accumulatedCollaboration = {
                ...(accumulatedCollaboration ?? const <String, dynamic>{}),
                'open_report': true,
                'report_deep_link': metadata['report_deep_link']?.toString(),
                'report_preview': reportPreview,
                'source_chat_session_id':
                    metadata['source_chat_session_id']?.toString(),
              };
            }
          }
          // 流式文本片段（delta）
          accumulatedContent += event.content;
          pendingStreamingContent = accumulatedContent;
          flushPending();
        } else if (event is StatusUpdateEvent) {
          // AI 状态更新（THINKING, GENERATING 等）
          if (event.state == 'THINKING' || event.state == 'GENERATING') {
            unawaited(BgmService.setThinkingActivity(true));
          } else {
            unawaited(BgmService.setThinkingActivity(false));
          }
          final uxProgress = event.metadata?['ux_progress'];
          final executionProgress = _buildExecutionProgressDetails(
            event.metadata?['execution_progress'],
          );
          lastAiStatus = event.state;
          pendingAiStatus = event.state;
          if (executionProgress != null && executionProgress.isNotEmpty) {
            pendingAiStatusDetails = executionProgress;
          } else if (uxProgress is Map<String, dynamic>) {
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
            activeRunSummary: _buildRunSummary(
              status: event.state,
              details: pendingAiStatusDetails,
              agentName: event.currentAgentName,
            ),
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
            accumulatedMeta.addAll(metadata);
            accumulatedRawMetadata.addAll(metadata);
            _appendExecutionWidgets(accumulatedWidgets, metadata);
            captureCitationMetadata(metadata['citations']);
            captureStructuredAdjustments(metadata);
            captureLowYieldBlock(metadata);
            _ref.read(experienceEnvelopeProvider.notifier).updateFromMetadata(accumulatedRawMetadata);
          }
          final uxEnvelope = _extractUxEnvelope(metadata);
          if (uxEnvelope.isNotEmpty) {
            accumulatedUxEnvelope = {
              ...(accumulatedUxEnvelope ?? const <String, dynamic>{}),
              ...uxEnvelope,
            };
          }
          // Extract dual_core_mode from ux_turn (lives in full_text event metadata)
          final uxTurnMap =
              accumulatedUxEnvelope?['ux_turn'] as Map<String, dynamic>?;
          final newDualCoreMode = uxTurnMap?['dual_core_mode'] as String?;
          if (newDualCoreMode != null) {
            state = state.copyWith(dualCoreMode: newDualCoreMode);
          }
          if (metadata != null) {
            final selectedExpertsRaw = metadata['selected_experts'];
            final answerExpertsRaw = metadata['answer_experts'];
            final routingStrategy = metadata['routing_strategy'];
            final fallbackReason = metadata['fallback_reason'];
            final routeConfidence = metadata['route_confidence'];
            final expertEntrySource = metadata['expert_entry_source'];
            final routingPreview = _parseJsonMap(metadata['routing_preview']);
            final roundtableTurns =
                _parseJsonMapList(metadata['roundtable_turns']);
            final primaryAgent = metadata['primary_agent']?.toString();
            final collaborationNarrative =
                metadata['collaboration_narrative']?.toString();
            final collaborationMode =
                metadata['collaboration_mode']?.toString();
            final predictionPreview =
                _parseJsonMap(metadata['prediction_preview']);
            final simulationPreview =
                _parseJsonMap(metadata['simulation_preview']);
            final reportPreview = _parseJsonMap(metadata['report_preview']);
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
                'answer_experts': _parseSelectedExperts(answerExpertsRaw),
                'routing_strategy': routingStrategy,
                'fallback_reason': fallbackReason,
                'route_confidence': routeConfidence,
                'expert_entry_source': expertEntrySource,
              };
            }
            if (routingPreview != null && routingPreview.isNotEmpty) {
              accumulatedRoutingPreview = routingPreview;
              accumulatedCollaboration = {
                ...(accumulatedCollaboration ?? const <String, dynamic>{}),
                'routing_preview': routingPreview,
              };
              state = state.copyWith(routingPreview: routingPreview);
            }
            if (roundtableTurns.isNotEmpty) {
              accumulatedRoundtableTurns
                ..clear()
                ..addAll(roundtableTurns);
              accumulatedCollaboration = {
                ...(accumulatedCollaboration ?? const <String, dynamic>{}),
                'roundtable_turns':
                    List<Map<String, dynamic>>.from(accumulatedRoundtableTurns),
              };
              state = state.copyWith(
                roundtableTurns:
                    List<Map<String, dynamic>>.from(accumulatedRoundtableTurns),
              );
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
            } else if (primaryAgent != null && primaryAgent.isNotEmpty) {
              accumulatedAgentsInvolved = [primaryAgent];
            }
            if (_parseMetadataFlag(metadata['open_theater']) &&
                predictionPreview != null) {
              accumulatedCollaboration = {
                ...(accumulatedCollaboration ?? const <String, dynamic>{}),
                'open_theater': true,
                'deep_link': metadata['deep_link']?.toString(),
                'prediction_preview': predictionPreview,
                'source_chat_session_id':
                    metadata['source_chat_session_id']?.toString(),
              };
            }
            if (_parseMetadataFlag(metadata['open_simulation']) &&
                simulationPreview != null) {
              accumulatedCollaboration = {
                ...(accumulatedCollaboration ?? const <String, dynamic>{}),
                'open_simulation': true,
                'simulation_deep_link':
                    metadata['simulation_deep_link']?.toString(),
                'simulation_preview': simulationPreview,
                'source_chat_session_id':
                    metadata['source_chat_session_id']?.toString(),
              };
            }
            if (_parseMetadataFlag(metadata['open_report']) &&
                reportPreview != null) {
              accumulatedCollaboration = {
                ...(accumulatedCollaboration ?? const <String, dynamic>{}),
                'open_report': true,
                'report_deep_link': metadata['report_deep_link']?.toString(),
                'report_preview': reportPreview,
                'source_chat_session_id':
                    metadata['source_chat_session_id']?.toString(),
              };
            }
          }
          accumulatedContent = event.content;
          pendingStreamingContent = accumulatedContent;
          flushPending(immediate: true);
        } else if (event is ErrorEvent) {
          final userFriendlyMessage = ErrorMessages.getUserFriendlyMessage(
            event.code,
            event.message,
          );
          final actionSuggestion =
              ErrorMessages.getActionSuggestion(event.code);
          final isRetryable = ErrorMessages.isRetryable(event.code);

          state = state.copyWith(
            activeRunSummary: _buildRunSummary(
              status: lastAiStatus,
              details: event.message,
            ),
          );
          finalizeRun(
            phase: ChatRunPhase.failed,
            errorMessage: actionSuggestion.isEmpty
                ? userFriendlyMessage
                : I18nService.instance.l10n.chatErrorWithSuggestion(
                    userFriendlyMessage,
                    actionSuggestion,
                  ),
            errorCode: event.code,
            isRetryable: isRetryable,
            restoreAttachments: hasQueuedAttachments,
          );
          return; // 提前退出
        } else if (event is NackEvent) {
          final userFriendlyMessage = ErrorMessages.getUserFriendlyMessage(
            event.errorCode,
            event.errorMessage,
          );
          final actionSuggestion =
              ErrorMessages.getActionSuggestion(event.errorCode);
          final isRetryable = ErrorMessages.isRetryable(event.errorCode);

          state = state.copyWith(
            activeRunSummary: _buildRunSummary(
              status: lastAiStatus,
              details: event.errorMessage,
            ),
          );
          finalizeRun(
            phase: ChatRunPhase.failed,
            errorMessage: actionSuggestion.isEmpty
                ? userFriendlyMessage
                : I18nService.instance.l10n.chatErrorWithSuggestion(
                    userFriendlyMessage,
                    actionSuggestion,
                  ),
            errorCode: event.errorCode,
            isRetryable: isRetryable,
            restoreAttachments: hasQueuedAttachments,
          );
          return; // 提前退出
        } else if (event is WidgetEvent) {
          if (event.widgetType == 'system_update' &&
              !_shouldIncludeSystemUpdate(event.widgetData)) {
            continue;
          }
          accumulatedWidgets.add(
            _normalizeWidgetPayload(event.widgetType, event.widgetData),
          );
          if (event.widgetType == 'low_yield_gentle_block') {
            _ref
                .read(lowYieldBlockProvider.notifier)
                .ingestPayload(event.widgetData);
          }
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
            accumulatedWidgets
                .add(_normalizeWidgetPayload(widgetType, widgetData));
            if (widgetType == 'low_yield_gentle_block') {
              _ref
                  .read(lowYieldBlockProvider.notifier)
                  .ingestPayload(widgetData);
            }
          }
        } else if (event is CitationEvent) {
          upsertSourceSummaryCitations(event.citations);
        } else if (event is UsageEvent) {
          state = state.copyWith(
            lastPromptTokens: event.promptTokens,
            lastCompletionTokens: event.completionTokens,
            lastTotalTokens: event.totalTokens,
          );
          await _updateDailyUsage(event);
        } else if (event is MetaEvent) {
          accumulatedMeta.addAll(event.meta);
          accumulatedRawMetadata.addAll(event.meta);
          captureCitationMetadata(event.meta['citations']);
          captureLowYieldBlock(event.meta);
          captureStructuredAdjustments(event.meta);
          flushPending();
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
          unawaited(_ref.read(closeToUnlockProvider.notifier).triggerCheck());
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
            activeRunSummary: _buildRunSummary(
              currentStepIndex: event.stepIndex,
              totalSteps: event.totalSteps > 0 ? event.totalSteps : null,
            ),
          );
          flushPending();
        } else if (event is TransparencyCompleteEvent) {
          // Transparency Complete Event
          state = state.copyWith(
            transparencyData: event.transparencyData,
            activeRunSummary: _buildRunSummary(
              totalSteps: event.transparencyData?.steps.length,
            ),
          );
          flushPending();
        } else if (event is RunLedgerSnapshotEvent) {
          state = state.copyWith(
            runLedgerSummary: event.summary,
          );
          flushPending();
        } else if (event is OrchestrationTraceEvent) {
          accumulatedOrchestrationTrace = event.traceData;
          flushPending();
        } else if (event is ModeSuggestionEvent) {
          accumulatedModeSuggestion = event.suggestion;
          flushPending();
        } else if (event is RoutingPreviewEvent) {
          accumulatedRoutingPreview = event.preview;
          accumulatedCollaboration = {
            ...(accumulatedCollaboration ?? const <String, dynamic>{}),
            'routing_preview': event.preview,
          };
          state = state.copyWith(routingPreview: event.preview);
          flushPending();
        } else if (event is AgentTurnEvent) {
          final turns = [...state.roundtableTurns];
          final incoming = Map<String, dynamic>.from(event.turn);
          final incomingAgent = incoming['agent_id']?.toString();
          final incomingIndex = incoming['turn_index'];
          final existingIndex = turns.indexWhere(
            (item) =>
                item['agent_id']?.toString() == incomingAgent &&
                item['turn_index'] == incomingIndex,
          );
          if (existingIndex >= 0) {
            turns[existingIndex] = incoming;
          } else {
            turns.add(incoming);
          }
          accumulatedRoundtableTurns
            ..clear()
            ..addAll(turns);
          accumulatedCollaboration = {
            ...(accumulatedCollaboration ?? const <String, dynamic>{}),
            if (accumulatedRoutingPreview != null)
              'routing_preview': accumulatedRoutingPreview,
            'roundtable_turns': List<Map<String, dynamic>>.from(turns),
          };
          state = state.copyWith(roundtableTurns: turns);
          flushPending();
        } else if (event is AgentActivityEvent) {
          final activities = [...state.agentActivities];
          final idx =
              activities.indexWhere((item) => item.agentId == event.agentId);
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
        } else if (event is StaleRecoveryEvent) {
          // Spine: StaleStateGuard recovery card
          state = state.copyWith(pendingStaleCard: event);
          flushPending();
        } else if (event is SpineReceiptEvent) {
          // Spine: UserVisibleReceipt card
          state = state.copyWith(pendingSpineReceipt: event);
          flushPending();
        } else if (event is CommunityHintEvent) {
          // Spine: community insight card (divine moment #6 社群经验转策略)
          state = state.copyWith(pendingCommunityHint: event);
          flushPending();
        } else if (event is UXWarningEvent) {
          // Spine: proactive risk warning (divine moment #5 阻止低收益)
          state = state.copyWith(pendingUXWarning: event);
          flushPending();
        } else if (event is GrowthCardEvent) {
          // Spine: growth milestone card (divine moment #1 看见坚持)
          state = state.copyWith(pendingGrowthCard: event);
          flushPending();
        } else if (event is GoalArbitrationEvent) {
          // Spine: multi-goal conflict surface
          state = state.copyWith(pendingGoalArbitration: event);
          flushPending();
        } else if (event is DivineMomentEvent) {
          // Spine: divine moment card (MAGIC-002 through MAGIC-006)
          state = state.copyWith(pendingDivineMoment: event);
          flushPending();
        } else if (event is SpineDegradedEvent) {
          // STAB-012: Spine pipeline degraded — show subtle indicator
          state = state.copyWith(spineDegraded: true);
          flushPending();
        } else if (event is CausalTraceEvent) {
          // GAP-P2-2: Causal trace created — refresh timeline & show indicator
          state = state.copyWith(
            pendingCausalTraceId: event.traceIdValue,
            causalTraceCount: state.causalTraceCount + 1,
          );
          _refreshCausalTimeline();
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
          state = state.copyWith(runPhase: ChatRunPhase.finalizing);
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
          finalizeRun(phase: ChatRunPhase.completed);
          break;
        }
      }

      if (!isCurrentRequest() || sawTerminalEvent) {
        return;
      }
      finalizeRun(phase: ChatRunPhase.completed);
    } catch (e) {
      if (!isCurrentRequest()) {
        return;
      }
      _streamDebouncer.cancel();
      // 捕获未处理的异常，提供友好的错误提示
      final failure = AppFailureMapper.from(
        e,
        fallbackMessage: 'Could not send this message.',
      );

      finalizeRun(
        phase: ChatRunPhase.failed,
        errorMessage: failure.userMessage,
        errorCode: failure.errorCode,
        isRetryable: failure.isRetryable,
        restoreAttachments: hasQueuedAttachments,
      );
    } finally {
      // 🔧 P1-1: 确保 isSending 总是被重置（如果还没被重置）
      if (isCurrentRequest() &&
          shouldResetSending &&
          mounted &&
          state.isSending) {
        state = state.copyWith(
          isSending: false,
          runPhase: state.runPhase == ChatRunPhase.idle
              ? ChatRunPhase.completed
              : state.runPhase,
          clearTransparency: true,
          clearActiveRunId: true,
          clearActiveRunSummary: true,
        );
      }
    }
  }

  Future<void> retryLastMessage() async {
    final request = _retryableRequest;
    if (request == null) {
      if (state.wsConnectionState == WsConnectionState.failed ||
          state.wsConnectionState == WsConnectionState.disconnected) {
        await reconnect();
      }
      return;
    }

    state = state.copyWith(clearError: true);
    await sendMessage(
      request.content,
      taskId: request.taskId,
      extraContextOverrides: request.extraContextOverrides,
      reuseLastUserMessage: true,
    );
  }
}

class _PendingChatRequest {
  const _PendingChatRequest({
    required this.content,
    this.taskId,
    this.extraContextOverrides,
  });

  final String content;
  final String? taskId;
  final Map<String, dynamic>? extraContextOverrides;
}
