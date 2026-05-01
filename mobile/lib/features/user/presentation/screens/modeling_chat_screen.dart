import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/navigation/route_resilience.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/home/home_routes.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/presentation/providers/active_plan_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/learning_portfolio_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/user/presentation/providers/profile_context_provider.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';

class ModelingChatScreen extends ConsumerStatefulWidget {
  const ModelingChatScreen({
    this.postOnboardingMessage,
    super.key,
  });

  final String? postOnboardingMessage;

  @override
  ConsumerState<ModelingChatScreen> createState() => _ModelingChatScreenState();
}

class _ModelingChatScreenState extends ConsumerState<ModelingChatScreen> {
  static const String _auroraModelingSurface = 'aurora_modeling';

  final TextEditingController _inputController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final List<_ModelingMessage> _messages = <_ModelingMessage>[];
  final Map<String, StreamSubscription<ChatStreamEvent>> _runSubscriptions =
      <String, StreamSubscription<ChatStreamEvent>>{};
  final Map<String, String> _draftMessageIdsByRequest = <String, String>{};

  String? _conversationId;
  bool _completed = false;
  bool _planningInFlight = false;
  bool _planningStarted = false;
  bool _skipInFlight = false;
  int _requestSequence = 0;
  int _messageSequence = 0;
  Map<String, dynamic>? _modelingOutput;
  String? _planningErrorMessage;

  bool get _hasActiveAuroraRun => _runSubscriptions.isNotEmpty;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(
        _startModelingStream(
          '_onboarding_start_',
          addUserMessage: false,
        ),
      );
    });
  }

  @override
  void dispose() {
    for (final subscription in _runSubscriptions.values) {
      unawaited(subscription.cancel());
    }
    _runSubscriptions.clear();
    _draftMessageIdsByRequest.clear();
    _inputController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => RouteResilienceScope(
        fallbackRoute: HomeRoutes.home,
        child: SparklePageScaffold(
          role: SparklePageRole.content,
          appBar: AppBar(
            title: const Text('让我更了解你（约2分钟）'),
            actions: [
              TextButton(
                onPressed: (_skipInFlight || _planningInFlight)
                    ? null
                    : () => unawaited(_skip()),
                child: const Text('跳过'),
              ),
            ],
          ),
          child: ContentConstraint(
            child: Column(
              children: [
                Expanded(
                  child: ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.symmetric(vertical: DS.spacing16),
                    itemCount: _messages.length,
                    itemBuilder: (context, index) {
                      final message = _messages[index];
                      final isUser = message.isUser;
                      final label = isUser ? '你' : 'Aurora';
                      return Align(
                        alignment: isUser
                            ? Alignment.centerRight
                            : Alignment.centerLeft,
                        child: Column(
                          crossAxisAlignment: isUser
                              ? CrossAxisAlignment.end
                              : CrossAxisAlignment.start,
                          children: [
                            Padding(
                              padding: const EdgeInsets.only(
                                left: DS.spacing4,
                                right: DS.spacing4,
                                bottom: DS.spacing4,
                              ),
                              child: Text(
                                label,
                                style: Theme.of(context)
                                    .textTheme
                                    .labelSmall
                                    ?.copyWith(
                                      color: DS.textSecondary,
                                      fontWeight: DS.fontWeightSemibold,
                                    ),
                              ),
                            ),
                            Container(
                              margin:
                                  const EdgeInsets.only(bottom: DS.spacing12),
                              padding: const EdgeInsets.all(DS.spacing12),
                              constraints: const BoxConstraints(maxWidth: 520),
                              decoration: BoxDecoration(
                                color: isUser
                                    ? DS.primaryBase
                                    : DS.surfaceSecondary,
                                borderRadius: DS.borderRadius16,
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    message.text,
                                    style: Theme.of(context)
                                        .textTheme
                                        .bodyMedium
                                        ?.copyWith(
                                          color: isUser
                                              ? DS.brandPrimaryConst
                                              : DS.textPrimary,
                                          height: 1.45,
                                        ),
                                  ),
                                  if (!isUser && message.isStreaming)
                                    Padding(
                                      padding: const EdgeInsets.only(
                                        top: DS.spacing8,
                                      ),
                                      child: Text(
                                        '输入中…',
                                        style: Theme.of(context)
                                            .textTheme
                                            .labelSmall
                                            ?.copyWith(color: DS.textSecondary),
                                      ),
                                    ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      );
                    },
                  ),
                ),
                if (_completed)
                  Padding(
                    padding: const EdgeInsets.fromLTRB(
                      DS.spacing16,
                      0,
                      DS.spacing16,
                      DS.spacing16,
                    ),
                    child: _PlanningBridgeStatus(
                      isLoading: _planningInFlight || _planningStarted,
                      errorMessage: _planningErrorMessage,
                      onRetry: _planningInFlight
                          ? null
                          : () => unawaited(_autoStartPlanning()),
                      onSkip: _planningInFlight ? null : _finish,
                    ),
                  )
                else
                  SafeArea(
                    top: false,
                    child: Padding(
                      padding: const EdgeInsets.all(DS.spacing16),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          if (_hasActiveAuroraRun)
                            Container(
                              width: double.infinity,
                              margin:
                                  const EdgeInsets.only(bottom: DS.spacing8),
                              padding: const EdgeInsets.symmetric(
                                horizontal: DS.spacing12,
                                vertical: DS.spacing10,
                              ),
                              decoration: BoxDecoration(
                                color: DS.surfaceSecondary,
                                borderRadius: DS.borderRadius12,
                              ),
                              child: Text(
                                'Aurora 可能会连续发几条，你也可以直接插话。',
                                style: Theme.of(context)
                                    .textTheme
                                    .bodySmall
                                    ?.copyWith(color: DS.textSecondary),
                              ),
                            ),
                          Row(
                            children: [
                              Expanded(
                                child: TextField(
                                  controller: _inputController,
                                  enabled: !_skipInFlight,
                                  onSubmitted: (_) => _handleSubmit(),
                                  decoration: const InputDecoration(
                                    hintText: '输入你的回答…',
                                  ),
                                ),
                              ),
                              const SizedBox(width: DS.spacing8),
                              SparkleIconButton(
                                icon: _skipInFlight
                                    ? const SizedBox(
                                        width: 18,
                                        height: 18,
                                        child: CircularProgressIndicator(
                                          strokeWidth: 2,
                                          color: Colors.white,
                                        ),
                                      )
                                    : const Icon(Icons.send_rounded),
                                onPressed: _skipInFlight ? null : _handleSubmit,
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ),
      );

  Future<void> _handleSubmit() async {
    final text = _inputController.text.trim();
    if (text.isEmpty || _skipInFlight) {
      return;
    }
    _inputController.clear();
    await _startModelingStream(text);
  }

  Future<void> _startModelingStream(
    String message, {
    bool addUserMessage = true,
    Map<String, dynamic>? extraContext,
  }) async {
    final trimmed = message.trim();
    if (trimmed.isEmpty || _skipInFlight || _completed) {
      return;
    }

    if (addUserMessage) {
      setState(() {
        _messages.add(
          _ModelingMessage(
            id: _nextMessageId('user'),
            text: trimmed,
            isUser: true,
          ),
        );
      });
      _scheduleScrollToBottom();
    }

    final requestId = _nextRequestId();
    try {
      final authState = ref.read(authProvider);
      final userId = authState.user?.id ??
          await ref.read(guestServiceProvider).getGuestId();
      final token = await ref.read(authRepositoryProvider).getAccessToken();

      if (!mounted) {
        return;
      }

      final stream = ref.read(chatRepositoryProvider).chatStream(
        trimmed,
        _conversationId,
        userId: userId,
        requestId: requestId,
        token: token,
        extraContext: {
          ...?extraContext,
          'mode': 'onboarding_modeling',
          'aurora_surface': _auroraModelingSurface,
          'aurora_runtime_enabled': true,
        },
      );

      final subscription = stream.listen(
        (event) => _handleStreamEvent(requestId, event),
        onError: (Object error, StackTrace stackTrace) {
          _handleStreamError(requestId, error);
        },
        onDone: () {
          _handleStreamClosed(requestId);
        },
        cancelOnError: false,
      );

      if (!mounted) {
        unawaited(subscription.cancel());
        return;
      }

      setState(() {
        _runSubscriptions[requestId] = subscription;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      AppFeedback.error(context, '建模对话暂时失败：$error');
    }
  }

  void _handleStreamEvent(String requestId, ChatStreamEvent event) {
    if (!mounted) {
      return;
    }

    final sessionId = event.sessionId?.trim();
    if (sessionId != null && sessionId.isNotEmpty) {
      _conversationId = sessionId;
    }

    if (event is TextEvent) {
      _applyMetadata(event.metadata);
      _appendAssistantChunk(requestId, event.content);
      return;
    }

    if (event is FullTextEvent) {
      _applyMetadata(event.metadata);
      _replaceAssistantChunk(requestId, event.content);
      return;
    }

    if (event is MetaEvent) {
      _applyMetadata(event.meta);
      return;
    }

    if (event is ContinueEvent) {
      _applyMetadata(event.metadata);
      _finalizeAssistantDraft(requestId);
      return;
    }

    if (event is DoneEvent) {
      _applyMetadata(event.metadata);
      _finalizeAssistantDraft(requestId);
      _cleanupRun(requestId);
      return;
    }

    if (event is ErrorEvent) {
      _handleStreamError(requestId, event.message);
    }
  }

  void _handleStreamClosed(String requestId) {
    if (!mounted) {
      return;
    }
    _finalizeAssistantDraft(requestId);
    _cleanupRun(requestId);
  }

  void _handleStreamError(String requestId, Object error) {
    if (!mounted) {
      return;
    }
    _finalizeAssistantDraft(requestId);
    _cleanupRun(requestId, cancelSubscription: true);
    AppFeedback.error(context, '建模对话暂时失败：$error');
  }

  void _appendAssistantChunk(String requestId, String chunk) {
    if (chunk.isEmpty) {
      return;
    }

    setState(() {
      final messageId = _draftMessageIdsByRequest[requestId];
      if (messageId == null) {
        final newMessageId = _nextMessageId('assistant');
        _draftMessageIdsByRequest[requestId] = newMessageId;
        _messages.add(
          _ModelingMessage(
            id: newMessageId,
            text: chunk,
            isUser: false,
            isStreaming: true,
          ),
        );
        return;
      }

      final index = _messages.indexWhere((message) => message.id == messageId);
      if (index < 0) {
        final newMessageId = _nextMessageId('assistant');
        _draftMessageIdsByRequest[requestId] = newMessageId;
        _messages.add(
          _ModelingMessage(
            id: newMessageId,
            text: chunk,
            isUser: false,
            isStreaming: true,
          ),
        );
        return;
      }

      final message = _messages[index];
      _messages[index] = message.copyWith(
        text: '${message.text}$chunk',
        isStreaming: true,
      );
    });
    _scheduleScrollToBottom();
  }

  void _replaceAssistantChunk(String requestId, String content) {
    if (content.isEmpty) {
      return;
    }

    setState(() {
      final messageId = _draftMessageIdsByRequest[requestId];
      if (messageId == null) {
        final newMessageId = _nextMessageId('assistant');
        _draftMessageIdsByRequest[requestId] = newMessageId;
        _messages.add(
          _ModelingMessage(
            id: newMessageId,
            text: content,
            isUser: false,
            isStreaming: true,
          ),
        );
        return;
      }

      final index = _messages.indexWhere((message) => message.id == messageId);
      if (index < 0) {
        final newMessageId = _nextMessageId('assistant');
        _draftMessageIdsByRequest[requestId] = newMessageId;
        _messages.add(
          _ModelingMessage(
            id: newMessageId,
            text: content,
            isUser: false,
            isStreaming: true,
          ),
        );
        return;
      }

      _messages[index] = _messages[index].copyWith(
        text: content,
        isStreaming: true,
      );
    });
    _scheduleScrollToBottom();
  }

  void _finalizeAssistantDraft(String requestId) {
    final messageId = _draftMessageIdsByRequest.remove(requestId);
    if (messageId == null || !mounted) {
      return;
    }

    final index = _messages.indexWhere((message) => message.id == messageId);
    if (index < 0 || !_messages[index].isStreaming) {
      return;
    }

    setState(() {
      _messages[index] = _messages[index].copyWith(isStreaming: false);
    });
    _scheduleScrollToBottom();
  }

  void _cleanupRun(
    String requestId, {
    bool cancelSubscription = false,
  }) {
    final subscription = _runSubscriptions.remove(requestId);
    _draftMessageIdsByRequest.remove(requestId);
    if (cancelSubscription && subscription != null) {
      unawaited(subscription.cancel());
    }
    if (mounted) {
      setState(() {});
      _scheduleAutoPlanningIfReady();
    }
  }

  void _applyMetadata(Map<String, dynamic>? metadata) {
    if (metadata == null || metadata.isEmpty || !mounted) {
      return;
    }

    final modelingComplete = _isTruthy(metadata['modeling_complete']);
    if (!modelingComplete || !_isModelingSurface(metadata) || _completed) {
      return;
    }

    Map<String, dynamic>? capturedOutput;
    final outputJson = metadata['modeling_output_json'];
    if (outputJson is String && outputJson.isNotEmpty) {
      try {
        capturedOutput = jsonDecode(outputJson) as Map<String, dynamic>?;
      } catch (error) {
        debugPrint('Modeling output parse failed: $error');
      }
    }

    setState(() {
      _completed = true;
      if (capturedOutput != null) {
        _modelingOutput = capturedOutput;
      }
    });
    ref.invalidate(profileContextProvider);
    _scheduleAutoPlanningIfReady();
  }

  Future<void> _skip() async {
    if (_skipInFlight) {
      return;
    }

    setState(() => _skipInFlight = true);

    final activeSubscriptions = List<StreamSubscription<ChatStreamEvent>>.from(
      _runSubscriptions.values,
    );
    _runSubscriptions.clear();
    _draftMessageIdsByRequest.clear();
    for (final subscription in activeSubscriptions) {
      await subscription.cancel();
    }

    try {
      final authState = ref.read(authProvider);
      final userId = authState.user?.id ??
          await ref.read(guestServiceProvider).getGuestId();
      final token = await ref.read(authRepositoryProvider).getAccessToken();

      final stream = ref.read(chatRepositoryProvider).chatStream(
        '_onboarding_skip_',
        _conversationId,
        userId: userId,
        requestId: _nextRequestId(),
        token: token,
        extraContext: const {
          'mode': 'onboarding_modeling',
          'aurora_surface': _auroraModelingSurface,
          'aurora_runtime_enabled': true,
          'skip': true,
        },
      );

      await stream
          .firstWhere(
            (event) => event is DoneEvent || event is ErrorEvent,
          )
          .timeout(const Duration(seconds: 3), onTimeout: DoneEvent.new);

      if (!mounted) {
        return;
      }
      await _finish();
    } catch (error) {
      if (!mounted) {
        return;
      }
      AppFeedback.error(context, '暂时无法跳过：$error');
      setState(() => _skipInFlight = false);
    }
  }

  Future<void> _finish() async {
    await ref.read(onboardingCompletedProvider.notifier).setCompleted(true);
    ref.invalidate(profileContextProvider);
    if (!mounted) return;
    final firstMessage = widget.postOnboardingMessage?.trim();
    if (firstMessage != null && firstMessage.isNotEmpty) {
      context.go('/chat', extra: {'initial_ai_message': firstMessage});
    } else {
      context.go('/home');
    }
  }

  String _nextRequestId() =>
      'aurora_modeling_${DateTime.now().microsecondsSinceEpoch}_${_requestSequence++}';

  String _nextMessageId(String prefix) =>
      '${prefix}_${DateTime.now().microsecondsSinceEpoch}_${_messageSequence++}';

  void _scheduleScrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !_scrollController.hasClients) {
        return;
      }
      final position = _scrollController.position.maxScrollExtent;
      unawaited(
        _scrollController.animateTo(
          position,
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOut,
        ),
      );
    });
  }

  void _scheduleAutoPlanningIfReady() {
    if (!_completed || _planningStarted || _runSubscriptions.isNotEmpty) {
      return;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted ||
          !_completed ||
          _planningStarted ||
          _runSubscriptions.isNotEmpty) {
        return;
      }
      unawaited(_autoStartPlanning());
    });
  }

  Future<void> _autoStartPlanning() async {
    if (!_completed || _planningInFlight) {
      return;
    }

    setState(() {
      _planningStarted = true;
      _planningInFlight = true;
      _planningErrorMessage = null;
    });

    try {
      await ref.read(onboardingCompletedProvider.notifier).setCompleted(true);
      ref.invalidate(profileContextProvider);

      final authState = ref.read(authProvider);
      final userId = authState.user?.id ??
          await ref.read(guestServiceProvider).getGuestId();
      final token = await ref.read(authRepositoryProvider).getAccessToken();

      String? resolvedPlanId;
      String? resolvedPlanRoute;

      final stream = ref.read(chatRepositoryProvider).chatStream(
        '开始规划',
        _conversationId,
        userId: userId,
        requestId: _nextRequestId(),
        token: token,
        extraContext: {
          'from_modeling_complete': true,
          if (_modelingOutput != null) 'modeling_output': _modelingOutput,
        },
      ).timeout(
        const Duration(seconds: 75),
        onTimeout: (sink) {
          sink
            ..add(
              ErrorEvent(
                code: 'PLANNING_TIMEOUT',
                message: '计划生成超时了，请重试一次。',
                retryable: true,
              ),
            )
            ..close();
        },
      );

      await for (final event in stream) {
        if (!mounted) return;

        final sessionId = event.sessionId?.trim();
        if (sessionId != null && sessionId.isNotEmpty) {
          _conversationId = sessionId;
        }

        final launch = _extractPlanningLaunch(event.metadata);
        resolvedPlanId ??= launch.planId;
        resolvedPlanRoute ??= launch.planRoute;

        if (event is ErrorEvent) {
          throw Exception(event.message);
        }
        if (event is DoneEvent &&
            resolvedPlanRoute != null &&
            resolvedPlanRoute.isNotEmpty) {
          break;
        }
      }

      resolvedPlanRoute ??=
          await _resolveFallbackPlanRoute(preferredPlanId: resolvedPlanId);
      if (resolvedPlanRoute == null || resolvedPlanRoute.isEmpty) {
        throw Exception('计划还在准备入口，请稍后重试一次。');
      }

      if (!mounted) return;
      try {
        if (resolvedPlanId != null && resolvedPlanId.isNotEmpty) {
          ref.read(activePlanProvider.notifier).selectPlan(resolvedPlanId);
          ref.invalidate(planDetailProvider(resolvedPlanId));
        }
        ref
          ..invalidate(planListProvider)
          ..invalidate(learningPortfolioProvider);
      } catch (error) {
        debugPrint('Planning cache refresh failed: $error');
      }
      context.go(resolvedPlanRoute);
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _planningInFlight = false;
        _planningStarted = false;
        _planningErrorMessage = '计划生成遇到问题：$error';
      });
    }
  }

  _PlanningLaunchTarget _extractPlanningLaunch(Map<String, dynamic>? metadata) {
    if (metadata == null || metadata.isEmpty) {
      return const _PlanningLaunchTarget();
    }

    var planId = _readNonEmptyString(metadata['plan_id']);
    var planRoute = _readNonEmptyString(metadata['plan_route']);

    final widgetsJson = _readNonEmptyString(metadata['planning_widgets_json']);
    if ((planId == null || planRoute == null) &&
        widgetsJson != null &&
        widgetsJson.isNotEmpty) {
      try {
        final decoded = jsonDecode(widgetsJson);
        if (decoded is List) {
          for (final item in decoded) {
            if (item is! Map) continue;
            final widget = Map<String, dynamic>.from(item);
            final widgetType = widget['type']?.toString().trim();
            final data = widget['data'];
            if (data is! Map) continue;
            final payload = Map<String, dynamic>.from(data);
            if (widgetType == 'plan_card') {
              planId ??= _readNonEmptyString(payload['plan_id']) ??
                  _readNonEmptyString(payload['id']);
              planRoute ??=
                  planId != null && planId.isNotEmpty ? '/plans/$planId' : null;
            }
            if (widgetType == 'task_list') {
              final tasks = payload['tasks'];
              if (tasks is! List || tasks.isEmpty) continue;
              for (final task in tasks) {
                if (task is! Map) continue;
                final taskPayload = Map<String, dynamic>.from(task);
                planId ??= _readNonEmptyString(taskPayload['plan_id']);
                if (planId != null && planId.isNotEmpty) {
                  planRoute ??= '/plans/$planId';
                  break;
                }
              }
            }
          }
        }
      } catch (_) {}
    }

    if (planRoute == null && planId != null && planId.isNotEmpty) {
      planRoute = '/plans/$planId';
    }

    return _PlanningLaunchTarget(
      planId: planId,
      planRoute: planRoute,
    );
  }

  Future<String?> _resolveFallbackPlanRoute({String? preferredPlanId}) async {
    if (preferredPlanId != null && preferredPlanId.trim().isNotEmpty) {
      return '/plans/${preferredPlanId.trim()}';
    }

    await ref.read(planListProvider.notifier).refresh();
    final sprint = ref
        .read(planListProvider)
        .activePlans
        .where((plan) => plan.type == PlanType.sprint)
        .firstOrNull;
    if (sprint == null) {
      return null;
    }
    ref.read(activePlanProvider.notifier).selectPlan(sprint.id);
    return '/plans/${sprint.id}';
  }

  String? _readNonEmptyString(dynamic value) {
    final text = value?.toString().trim();
    if (text == null || text.isEmpty) {
      return null;
    }
    return text;
  }

  bool _isTruthy(dynamic value) {
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

  bool _isModelingSurface(Map<String, dynamic> metadata) {
    final surface = metadata['aurora_surface']?.toString().trim();
    if (surface == null || surface.isEmpty) {
      return true;
    }
    return surface == _auroraModelingSurface || surface == 'modeling';
  }
}

class _PlanningBridgeStatus extends StatelessWidget {
  const _PlanningBridgeStatus({
    required this.isLoading,
    required this.errorMessage,
    required this.onRetry,
    required this.onSkip,
  });

  final bool isLoading;
  final String? errorMessage;
  final VoidCallback? onRetry;
  final VoidCallback? onSkip;

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        child: Row(
          children: [
            const SizedBox(
              width: 20,
              height: 20,
              child: CircularProgressIndicator(strokeWidth: 2.2),
            ),
            const SizedBox(width: DS.spacing12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    '正在生成你的第一份冲刺计划',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: DS.fontWeightBold,
                        ),
                  ),
                  const SizedBox(height: DS.spacing4),
                  Text(
                    '马上就会带你进入任务页，不需要再点下一步。',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.textSecondary,
                        ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
    }

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '计划生成没成功',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            errorMessage ?? '暂时没能把计划拉起来，请再试一次。',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: DS.textSecondary,
                  height: 1.45,
                ),
          ),
          const SizedBox(height: DS.spacing16),
          SparkleButton(
            label: '重试生成计划',
            onPressed: onRetry,
          ),
          const SizedBox(height: DS.spacing8),
          TextButton(
            onPressed: onSkip,
            child: Text(
              '稍后再说',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: DS.textSecondary,
                  ),
            ),
          ),
        ],
      ),
    );
  }
}

class _PlanningLaunchTarget {
  const _PlanningLaunchTarget({
    this.planId,
    this.planRoute,
  });

  final String? planId;
  final String? planRoute;
}

class _ModelingMessage {
  const _ModelingMessage({
    required this.id,
    required this.text,
    required this.isUser,
    this.isStreaming = false,
  });

  final String id;
  final String text;
  final bool isUser;
  final bool isStreaming;

  _ModelingMessage copyWith({
    String? id,
    String? text,
    bool? isUser,
    bool? isStreaming,
  }) =>
      _ModelingMessage(
        id: id ?? this.id,
        text: text ?? this.text,
        isUser: isUser ?? this.isUser,
        isStreaming: isStreaming ?? this.isStreaming,
      );
}
