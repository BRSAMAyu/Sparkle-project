part of 'chat_provider.dart';

extension ChatNotifierActions on ChatNotifier {
  void setTransparencyExpanded(bool expanded) {
    state = state.copyWith(
      transparencyPresentationState:
          state.transparencyPresentationState.copyWith(isExpanded: expanded),
    );
  }

  void dismissTransparencyForCurrentRun() {
    state = state.copyWith(
      transparencyPresentationState:
          state.transparencyPresentationState.copyWith(
        isDismissed: true,
        isExpanded: false,
      ),
    );
  }

  Map<String, dynamic> _actionPayload(Map<String, dynamic> payload) {
    final nested = payload['payload'];
    if (nested is Map<String, dynamic>) {
      return nested;
    }
    if (nested is Map) {
      return Map<String, dynamic>.from(nested);
    }
    return const <String, dynamic>{};
  }

  String _actionString(
    Map<String, dynamic> payload,
    String key,
  ) {
    final nested = _actionPayload(payload);
    final value = nested[key] ?? payload[key];
    return value?.toString() ?? '';
  }

  void _queueNavigation(String route, {String? successMessage}) {
    if (route.isEmpty) {
      return;
    }
    state = state.copyWith(
      lastActionStatus: 'navigation_ready',
      lastActionMessage: route,
    );
    if (successMessage != null && successMessage.isNotEmpty) {
      debugPrint('➡️ $successMessage -> $route');
    }
  }

  Future<void> handleWidgetAction(
    String actionType,
    Map<String, dynamic> payload,
  ) async {
    final l10n = I18nService.instance.l10n;
    switch (actionType) {
      case 'prompt':
        final prompt = _actionString(payload, 'prompt').isNotEmpty
            ? _actionString(payload, 'prompt')
            : payload['label']?.toString() ?? '';
        if (prompt.isNotEmpty) {
          await sendMessage(prompt);
        }
        return;
      case 'route':
        final route = _actionString(payload, 'route');
        if (route.isNotEmpty) {
          _queueNavigation(route);
        }
        return;
      case 'switch_plan':
        final planId = _actionString(payload, 'plan_id');
        if (planId.isEmpty) {
          return;
        }
        _ref.read(activePlanProvider.notifier).selectPlan(planId);
        await switchPlanSession(planId);
        state = state.copyWith(
          lastActionStatus: 'plan_switched',
          lastActionMessage: l10n.chatPlanContextSwitched,
        );
        return;
      case 'open_task':
        final taskId = _actionString(payload, 'task_id');
        final route = _actionString(payload, 'route').isNotEmpty
            ? _actionString(payload, 'route')
            : (taskId.isNotEmpty ? '/tasks/$taskId/execute' : '');
        _queueNavigation(route);
        return;
      case 'handoff_task':
        final taskId = _actionString(payload, 'task_id');
        if (taskId.isEmpty) {
          return;
        }
        final templateId = _actionString(payload, 'template_id');
        if (templateId.isNotEmpty) {
          _ref
              .read(taskListProvider.notifier)
              .selectExecutionTemplate(taskId, templateId);
        }
        final intent =
            await _ref.read(taskListProvider.notifier).handoffTaskToAi(
                  taskId,
                  goal: _actionString(payload, 'goal').isNotEmpty
                      ? _actionString(payload, 'goal')
                      : null,
                );
        if (intent == null) {
          final message = _ref.read(taskListProvider).error ?? 'AI 执行发起失败';
          if (message.contains('等待队列')) {
            state = state.copyWith(
              lastActionStatus: 'queued',
              lastActionMessage: message,
            );
            _queueNavigation(
              _actionString(payload, 'route').isNotEmpty
                  ? _actionString(payload, 'route')
                  : '${TaskRoutes.home}/$taskId/execute?origin=chat',
            );
            return;
          }
          state = state.copyWith(
            lastActionStatus: 'failed',
            lastActionMessage: message,
          );
          return;
        }
        _queueNavigation(
          _actionString(payload, 'route').isNotEmpty
              ? _actionString(payload, 'route')
              : '${TaskRoutes.home}/$taskId/execute?origin=chat',
          successMessage: '已开始委派执行',
        );
        return;
      case 'open_task_execution':
        final taskId = _actionString(payload, 'task_id');
        if (taskId.isEmpty) {
          return;
        }
        _queueNavigation(
          _actionString(payload, 'route').isNotEmpty
              ? _actionString(payload, 'route')
              : '${TaskRoutes.home}/$taskId/execute?origin=chat',
        );
        return;
      case 'start_focus':
        final taskId = _actionString(payload, 'task_id');
        final route = _actionString(payload, 'route').isNotEmpty
            ? _actionString(payload, 'route')
            : (taskId.isNotEmpty ? '/focus/mindfulness/$taskId' : '/focus');
        _queueNavigation(route);
        return;
      case 'create_task_draft':
        final title = _actionString(payload, 'title');
        final route = _actionString(payload, 'route').isNotEmpty
            ? _actionString(payload, 'route')
            : (title.isNotEmpty
                ? '/tasks/new?title=${Uri.encodeComponent(title)}'
                : '/tasks/new');
        _queueNavigation(route);
        return;
      case 'reflection_submit':
        final feedbackId = _actionString(payload, 'feedback_id');
        if (feedbackId.isEmpty) {
          return;
        }
        await _ref.read(taskRepositoryProvider).submitReflectionAnswer(
              feedbackId,
              selectedOption: _actionString(payload, 'selected_option'),
              freeText: _actionString(payload, 'free_text'),
            );
        state = state.copyWith(
          lastActionStatus: 'reflection_submitted',
          lastActionMessage: l10n.chatFeedbackThanks,
        );
        return;
      default:
        debugPrint('ℹ️ Unsupported widget action: $actionType');
    }
  }

  void startNewSession() {
    cancelActiveRun(reason: 'new_session');
    state = state.copyWith(
      clearConversation: true,
      messages: [],
      hasMoreMessages: false,
      clearError: true,
      agentActivities: const [],
    );
    if (DemoDataService.isDemoMode) {
      // Keep demo history? Or clear?
      // Usually "Start New Session" means clear.
    }
  }

  Future<void> switchPlanSession(
    String? planId, {
    BuildContext? context,
  }) async {
    cancelActiveRun(reason: 'switch_plan');
    if (planId == null) {
      // 🔧 修复：即使没有活跃计划，也尝试加载当前会话历史
      final currentSessionId = state.conversationId;
      if (currentSessionId != null && currentSessionId.isNotEmpty) {
        await loadConversationHistory(currentSessionId);
      } else {
        state = state.copyWith(
          clearConversation: true,
          messages: [],
          clearError: true,
          agentActivities: const [],
        );
      }
      return;
    }

    final authState = _ref.read(authProvider);
    final user = authState.user;
    final userId =
        user?.id ?? await _ref.read(guestServiceProvider).getGuestId();
    final sessionId = _ref.read(agentSessionStoreProvider).getOrCreateSessionId(
          AgentSessionScope.plan,
          planId,
          userId,
        );

    if (state.conversationId == sessionId) {
      return;
    }

    // Check if there are unsaved/temporary messages in current conversation
    final hasUnsavedMessages = state.messages.isNotEmpty &&
        state.messages.any((m) => m.id.startsWith('temp_') || m.id.isEmpty);

    if (hasUnsavedMessages && context != null) {
      // Show confirmation dialog
      final targetPlanName = await _getPlanName(planId);
      if (!context.mounted) return;

      final confirmed = await showSensoryDialog<bool>(
        context: context,
        barrierColor: Colors.black54,
        builder: (ctx) => PlanSwitchConfirmationDialog(
          targetPlanName: targetPlanName,
          unsavedMessageCount: state.messages.length,
          onConfirm: () => Navigator.pop(ctx, true),
          onCancel: () => Navigator.pop(ctx, false),
        ),
      );

      if (confirmed != true) return;
    }

    // P0修复: 设置切换标志，阻止此期间的消息发送
    isSwitchingPlan = true;
    try {
      state = state.copyWith(
        conversationId: sessionId,
        messages: [],
        hasMoreMessages: false,
        isSending: false,
        clearError: true,
        streamingContent: '',
        clearAiStatus: true,
        clearReasoning: true,
        agentActivities: const [],
      );

      await loadConversationHistory(sessionId);
    } finally {
      isSwitchingPlan = false;
    }

    // Show feedback after successful switch
    if (context != null && context.mounted) {
      AppFeedback.success(
        context,
        I18nService.instance.l10n.chatPlanContextSwitched,
      );
    }
  }

  /// Helper to get plan name from provider
  Future<String> _getPlanName(String planId) async {
    try {
      final planListState = _ref.read(planListProvider);
      final plans = planListState.plans;
      final plan = plans.firstWhere(
        (p) => p.id == planId,
        orElse: () => throw StateError('Plan not found'),
      );
      return plan.name;
    } catch (_) {
      return I18nService.instance.l10n.chatNewChat;
    }
  }

  /// 确认 ActionCard
  void confirmAction(WidgetPayload action) {
    final entity = EntityCardPayload.fromRaw(
      action.data,
      fallbackType: action.type,
    );
    if (action.type == 'nightly_review') {
      final reviewId = action.data['review_id']?.toString() ?? '';
      if (reviewId.isNotEmpty) {
        unawaited(_markNightlyReviewed(reviewId));
        return;
      }
    }

    final interventionId = action.data['intervention_id']?.toString() ??
        action.data['request_id']?.toString() ??
        '';
    if (interventionId.isNotEmpty) {
      _chatRepository.sendInterventionFeedback(
        requestId: interventionId,
        feedbackType: 'accept',
        extraData: {'widget_type': action.type},
      );
      debugPrint('✅ Intervention accepted: $interventionId');
      return;
    }

    // 从 WidgetPayload 中提取 tool_result_id
    final toolResultId = action.data['id']?.toString() ??
        entity.toolResultId ??
        action.data['tool_result_id']?.toString() ??
        '';

    if (toolResultId.isEmpty) {
      debugPrint('⚠️ Warning: Cannot confirm action - missing tool_result_id');
      return;
    }

    // 发送确认反馈到后端
    _chatRepository.sendActionFeedback(
      action: 'confirm',
      toolResultId: toolResultId,
      widgetType: action.type,
    );

    debugPrint(
      '✅ Action confirmed: ${action.type} (tool_result_id: $toolResultId)',
    );

    // TRACKED(TD-001): 可以添加乐观更新 - 立即在 UI 中标记为已确认
    // state = state.copyWith(messages: _updateActionStatus(toolResultId, confirmed: true));
  }

  /// 忽略 ActionCard
  void dismissAction(WidgetPayload action) {
    final entity = EntityCardPayload.fromRaw(
      action.data,
      fallbackType: action.type,
    );
    if (action.type == 'nightly_review') {
      debugPrint('ℹ️ Nightly review dismissed');
      return;
    }

    final interventionId = action.data['intervention_id']?.toString() ??
        action.data['request_id']?.toString() ??
        '';
    if (interventionId.isNotEmpty) {
      _chatRepository.sendInterventionFeedback(
        requestId: interventionId,
        feedbackType: 'reject',
        extraData: {'widget_type': action.type},
      );
      debugPrint('❌ Intervention dismissed: $interventionId');
      return;
    }

    final toolResultId = action.data['id']?.toString() ??
        entity.toolResultId ??
        action.data['tool_result_id']?.toString() ??
        '';

    if (toolResultId.isEmpty) {
      debugPrint('⚠️ Warning: Cannot dismiss action - missing tool_result_id');
      return;
    }

    // 发送忽略反馈到后端
    _chatRepository.sendActionFeedback(
      action: 'dismiss',
      toolResultId: toolResultId,
      widgetType: action.type,
    );

    debugPrint(
      '❌ Action dismissed: ${action.type} (tool_result_id: $toolResultId)',
    );

    // TRACKED(TD-001): 可以添加乐观更新 - 从 UI 中移除或标记为已忽略
    // state = state.copyWith(messages: _updateActionStatus(toolResultId, confirmed: false));
  }

  void sendResponseFeedback(ChatMessageModel message, String feedbackType) {
    final responseId = message.responseId ?? '';
    if (responseId.isEmpty) {
      debugPrint('⚠️ Missing response_id for feedback');
      return;
    }

    final selectedExpertsRaw = message.agentCollaboration?['selected_experts'];
    String? selectedExpertsMeta;
    if (selectedExpertsRaw is List) {
      selectedExpertsMeta = selectedExpertsRaw.map((e) => '$e').join(',');
    } else if (selectedExpertsRaw is String && selectedExpertsRaw.isNotEmpty) {
      selectedExpertsMeta = selectedExpertsRaw;
    }

    _chatRepository.sendResponseFeedback(
      responseId: responseId,
      feedbackType: feedbackType,
      workflowId: message.workflowId,
      promptVersion: message.promptVersion,
      traceId: message.traceId,
      meta: {
        'message_id': message.id,
        if ((message.meta?.chatMode?.isNotEmpty ?? false))
          'chat_mode': message.meta!.chatMode!,
        if ((message.meta?.reasoningMode?.isNotEmpty ?? false))
          'reasoning_mode': message.meta!.reasoningMode!,
        if (selectedExpertsMeta != null)
          'selected_experts': selectedExpertsMeta,
      },
    );
    debugPrint('📤 Response feedback sent: $feedbackType for $responseId');
    state = state.copyWith(
      lastActionStatus: 'response_feedback_sent',
      lastActionMessage:
          feedbackType == 'up' ? '已收到你的反馈，这条回复已标记为有帮助' : '已收到你的反馈，我们会继续改进这类回复',
    );
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) {
        state = state.copyWith(clearActionFeedback: true);
      }
    });
  }

  /// 发送计划审查反馈
  void sendPlanReviewFeedback({
    required String reviewId,
    required String userDecision,
    String? planId,
    String? userComment,
  }) {
    _chatRepository.sendPlanReviewFeedback(
      reviewId: reviewId,
      userDecision: userDecision,
      planId: planId,
      userComment: userComment,
    );
    debugPrint('📤 Plan review feedback sent: $userDecision for $reviewId');

    // Clear the pending review after sending feedback
    state = state.copyWith(clearPendingReview: true);
  }

  Future<void> _markNightlyReviewed(String reviewId) async {
    try {
      await _ref.read(nightlyReviewActionsProvider).markReviewed(reviewId);
      debugPrint('✅ Nightly review marked as reviewed: $reviewId');
    } catch (e) {
      debugPrint('❌ Nightly review feedback failed: $e');
    }
  }

  /// 处理成就解锁事件
  void _handleAchievementUnlock(AchievementUnlockEvent event) {
    debugPrint('🏆 Achievement unlocked: ${event.name}');

    // Delegate to achievement_provider for combo queue management
    final result =
        _ref.read(achievementProvider.notifier).handleAchievementUnlock(event);

    if (result != null) {
      // Write to global provider so any screen can show the dialog
      _ref.read(pendingAchievementUnlockProvider.notifier).setPending(
            event: result.event,
            comboCount: result.comboCount,
          );

      // Show toast feedback
      state = state.copyWith(
        lastActionStatus: 'achievement_unlocked',
        lastActionMessage:
            I18nService.instance.l10n.chatAchievementUnlocked(event.name),
      );
      Future.delayed(const Duration(seconds: 3), () {
        if (mounted) state = state.copyWith(clearActionFeedback: true);
      });
    } else {
      debugPrint('🏆 Achievement queued for combo: ${event.name}');
    }
  }

  /// 处理成就里程碑事件
  void _handleAchievementMilestone(AchievementMilestoneEvent event) {
    debugPrint(
      '📊 Achievement milestone: ${event.achievementName} - ${event.milestonePercent}%',
    );

    // 显示里程碑通知（可以作为轻量级提示）
    state = state.copyWith(
      lastActionStatus: 'milestone_reached',
      lastActionMessage: event.message,
    );

    // Phase 1B: Trigger close-to-unlock check
    _ref.read(closeToUnlockProvider.notifier).triggerCheck();
    unawaited(
      _ref.read(homeCloseToUnlockProvider.notifier).fetch(forceRefresh: true),
    );

    // Clear after delay
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) {
        state = state.copyWith(
          clearActionFeedback: true,
        );
      }
    });
  }

  void _handleSprintModeSwitch(SprintModeSwitchEvent event) {
    debugPrint('🔄 Sprint mode switch event received');

    // Switch to Sprint View
    _ref.read(taskBoardProvider.notifier).switchView(TaskViewMode.sprint);
  }

  /// 处理 Notification Event (实时通知推送)
  void _handleNotificationEvent(NotificationEvent event) {
    debugPrint(
      '🔔 Notification event received: ${event.title} (type: ${event.notificationType})',
    );

    // 直接将通知添加到通知中心
    try {
      final notificationCenter = _ref.read(notificationCenterProvider.notifier);
      notificationCenter.handleNewNotification(
        notificationData: event.fullNotificationData,
        notificationType: event.notificationType,
      );
      debugPrint(
        '✅ Notification added to notification center: ${event.notificationId}',
      );
    } catch (e) {
      debugPrint('⚠️ Failed to add notification to center: $e');
    }

    // 显示 toast 提示
    final title = event.title.isNotEmpty ? event.title : event.content;
    if (title.isNotEmpty) {
      state = state.copyWith(
        lastActionStatus: 'notification_received',
        lastActionMessage: title,
      );

      // 延迟清除反馈状态
      Future.delayed(const Duration(seconds: 3), () {
        if (mounted) {
          state = state.copyWith(clearActionFeedback: true);
        }
      });
    }
  }

  /// 处理 ActionCard 状态更新
  void _handleActionStatus(ActionStatusEvent event) {
    debugPrint(
      '📥 Action status received: ${event.status} for ${event.actionId}',
    );

    // 显示用户友好的提示消息
    final message = event.message ?? _getDefaultStatusMessage(event.status);

    // 更新状态以触发 UI 反馈
    state = state.copyWith(
      lastActionStatus: event.status,
      lastActionMessage: message,
    );

    // 延迟清除反馈状态
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) {
        state = state.copyWith(clearActionFeedback: true);
      }
    });

    debugPrint('💬 Status message: $message');

    // TRACKED(TD-001): 更新 UI 中对应 ActionCard 的状态
    // 例如：标记为已确认、已忽略，或者从列表中移除
    // state = state.copyWith(messages: _updateMessageActionStatus(event.actionId, event.status));
  }

  String _getDefaultStatusMessage(String status) {
    final l10n = I18nService.instance.l10n;
    switch (status) {
      case 'confirmed':
        return l10n.chatActionStatusConfirmed;
      case 'dismissed':
        return l10n.chatActionStatusDismissed;
      case 'processing':
        return l10n.chatActionStatusProcessing;
      case 'completed':
        return l10n.chatActionStatusCompleted;
      case 'failed':
        return l10n.chatActionStatusFailed;
      default:
        return l10n.chatActionStatusUpdate(status);
    }
  }

  /// 处理 Plan Review Widget Event
  void _handlePlanReviewWidget(PlanReviewWidgetEvent event) {
    debugPrint('📥 Plan review widget received');

    // Parse review data
    final reviewData = event.reviewData;
    final review = PlanReviewResult.fromJson(reviewData);

    // Update state with pending review
    state = state.copyWith(
      pendingPlanReview: review,
      pendingReviewActionId: review.actionId,
    );

    debugPrint(
      '📋 Plan review ready: ${review.decision} (review_id: ${review.reviewId})',
    );
  }

  /// 处理 State Change Event (计划归档/恢复/删除、设置更新等重大状态变更)
  void _handleStateChangeEvent(StateChangeEvent event) {
    debugPrint('🔄 State change event received: ${event.changeType}');

    // Convert to intervention message
    final intervention = event.toInterventionMessage();

    // Add to pending interventions
    state = state.copyWith(
      pendingInterventions: [...state.pendingInterventions, intervention],
    );

    debugPrint(
      '📢 State change notification added: ${event.changeType} (${event.interventionLevel})',
    );

    if (event.changeType.startsWith('plan_')) {
      _refreshPlanRelatedState(reason: event.changeType);
    }

    // Refresh notification center when receiving state change events
    _refreshNotificationCenter();
  }

  void _refreshPlanRelatedState({required String reason}) {
    unawaited(
      _ref.read(planListProvider.notifier).refresh().catchError((Object error) {
        debugPrint('⚠️ Failed to refresh plan list after $reason: $error');
      }),
    );
    unawaited(
      _ref.read(taskListProvider.notifier).refreshTasks().catchError((
        Object error,
      ) {
        debugPrint('⚠️ Failed to refresh task list after $reason: $error');
      }),
    );
    unawaited(
      _ref.read(dashboardProvider.notifier).refresh().catchError((
        Object error,
      ) {
        debugPrint('⚠️ Failed to refresh dashboard after $reason: $error');
      }),
    );
  }

  /// 刷新通知中心
  void _refreshNotificationCenter() {
    final notificationCenter = _ref.read(notificationCenterProvider.notifier);
    unawaited(
      notificationCenter.refresh().catchError((Object error) {
        debugPrint('⚠️ Failed to refresh notification center: $error');
      }),
    );
    debugPrint('🔔 Notification center refreshed due to state change');
  }

  /// 处理 Plan Review Status Event
  void _handlePlanReviewStatus(PlanReviewStatusEvent event) {
    debugPrint(
      '📥 Plan review status received: ${event.status} for ${event.reviewId}',
    );

    // Show user-friendly message
    final message = event.message ?? _getPlanReviewStatusMessage(event.status);

    // Update state to trigger UI feedback
    state = state.copyWith(
      lastActionStatus: event.status,
      lastActionMessage: message,
    );

    // Clear pending review if status indicates completion
    if (event.status == 'approved' || event.status == 'rejected') {
      state = state.copyWith(clearPendingReview: true);
      _refreshPlanRelatedState(reason: 'plan_review_${event.status}');
    }

    // Delay clearing feedback state
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) {
        state = state.copyWith(clearActionFeedback: true);
      }
    });

    debugPrint('💬 Plan review status message: $message');
  }

  String _getPlanReviewStatusMessage(String status) {
    final l10n = I18nService.instance.l10n;
    switch (status) {
      case 'approved':
        return l10n.chatPlanReviewApproved;
      case 'rejected':
        return l10n.chatPlanReviewRejected;
      case 'modify_requested':
        return l10n.chatPlanReviewModifyRequested;
      case 'acknowledged':
        return l10n.chatPlanReviewAcknowledged;
      default:
        return l10n.chatPlanReviewStatusUpdate(status);
    }
  }

  // ============================================
  // Phase 2b: Content Review Handlers
  // ============================================

  /// 处理 Content Review Widget Event
  void _handleContentReviewWidget(ContentReviewWidgetEvent event) {
    debugPrint('📥 Content review widget received');

    // Parse review data
    final reviewData = event.reviewData;
    final review = ContentReviewResult.fromJson(reviewData);

    // Update state with pending content review
    state = state.copyWith(pendingContentReview: review);

    debugPrint(
      '📋 Content review ready: ${review.decision} (review_id: ${review.reviewId})',
    );
  }

  /// 处理 Content Reflection Result Event
  void _handleContentReflectionResult(ContentReflectionResultEvent event) {
    debugPrint('📥 Content reflection result received');

    final reflectionData = event.reflectionData;
    final outcome = reflectionData['outcome'] as String? ?? 'unknown';
    final scoreDelta =
        (reflectionData['score_delta'] as num?)?.toDouble() ?? 0.0;
    final rounds = reflectionData['rounds'] as int? ?? 0;

    // Show user-friendly message about reflection result
    final message = _getReflectionResultMessage(outcome, scoreDelta, rounds);

    state = state.copyWith(
      lastActionStatus: outcome,
      lastActionMessage: message,
    );

    // Update pending content review with reflection status
    final currentReview = state.pendingContentReview;
    if (currentReview != null) {
      // Create updated review with reflection status
      final updatedReview = ContentReviewResult(
        reviewId: currentReview.reviewId,
        decision: currentReview.decision,
        overallScore: currentReview.overallScore + scoreDelta,
        metrics: currentReview.metrics,
        issues: currentReview.issues,
        suggestions: currentReview.suggestions,
        reviewedAt: currentReview.reviewedAt,
        reflectionStatus: outcome == 'fixed' || outcome == 'improved'
            ? 'completed'
            : 'failed',
        scoreLabel:
            _getScoreLabelForScore(currentReview.overallScore + scoreDelta),
      );

      state = state.copyWith(pendingContentReview: updatedReview);
    }

    // Delay clearing feedback state
    Future.delayed(const Duration(seconds: 3), () {
      if (mounted) {
        state = state.copyWith(clearActionFeedback: true);
      }
    });

    debugPrint('💬 Reflection result: $message');
  }

  /// Get user-friendly reflection result message
  String _getReflectionResultMessage(
    String outcome,
    double scoreDelta,
    int rounds,
  ) {
    final l10n = I18nService.instance.l10n;
    final roundsInfo = rounds > 1 ? l10n.chatRoundsInfo(rounds) : '';
    final scoreDeltaPct = (scoreDelta * 100).toInt();
    switch (outcome) {
      case 'fixed':
        return l10n.chatReflectionFixed(roundsInfo, scoreDeltaPct);
      case 'improved':
        return l10n.chatReflectionImproved(roundsInfo, scoreDeltaPct);
      case 'no_change':
        return l10n.chatReflectionNoChange;
      case 'degraded':
        return l10n.chatReflectionDegraded;
      case 'failed':
        return l10n.chatReflectionFailed;
      default:
        return l10n.chatReflectionStatusUpdate(outcome);
    }
  }

  /// Get score label for a given score
  String _getScoreLabelForScore(double score) {
    final l10n = I18nService.instance.l10n;
    if (score >= 0.9) return l10n.contentReviewScoreExcellent;
    if (score >= 0.7) return l10n.contentReviewScoreGood;
    if (score >= 0.5) return l10n.contentReviewScorePass;
    return l10n.contentReviewScoreNeedsWork;
  }
}
