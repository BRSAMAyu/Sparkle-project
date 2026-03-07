part of 'chat_provider.dart';

extension ChatNotifierActions on ChatNotifier {
  Future<void> handleWidgetAction(
    String actionType,
    Map<String, dynamic> payload,
  ) async {
    switch (actionType) {
      case 'prompt':
        final prompt =
            payload['prompt']?.toString() ?? payload['label']?.toString() ?? '';
        if (prompt.isNotEmpty) {
          await sendMessage(prompt);
        }
        return;
      case 'route':
        final route = payload['route']?.toString() ?? '';
        if (route.isNotEmpty) {
          state = state.copyWith(
            lastActionStatus: 'navigation_ready',
            lastActionMessage: route,
          );
        }
        return;
      default:
        debugPrint('ℹ️ Unsupported widget action: $actionType');
    }
  }

  void startNewSession() {
    state = state.copyWith(clearConversation: true, messages: []);
    if (DemoDataService.isDemoMode) {
      // Keep demo history? Or clear?
      // Usually "Start New Session" means clear.
    }
  }

  Future<void> switchPlanSession(String? planId) async {
    if (planId == null) {
      state = state.copyWith(clearConversation: true, messages: []);
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

    state = state.copyWith(
      conversationId: sessionId,
      messages: [],
      clearError: true,
      streamingContent: '',
      clearAiStatus: true,
      clearReasoning: true,
    );

    await loadConversationHistory(sessionId);
  }

  /// 确认 ActionCard
  void confirmAction(WidgetPayload action) {
    if (action.type == 'nightly_review') {
      final reviewId = action.data['review_id']?.toString() ?? '';
      if (reviewId.isNotEmpty) {
        _markNightlyReviewed(reviewId);
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

    // TODO: 可以添加乐观更新 - 立即在 UI 中标记为已确认
    // state = state.copyWith(messages: _updateActionStatus(toolResultId, confirmed: true));
  }

  /// 忽略 ActionCard
  void dismissAction(WidgetPayload action) {
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

    // TODO: 可以添加乐观更新 - 从 UI 中移除或标记为已忽略
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
        if (selectedExpertsMeta != null)
          'selected_experts': selectedExpertsMeta,
      },
    );
    debugPrint('📤 Response feedback sent: $feedbackType for $responseId');
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

    state = state.copyWith(
      pendingAchievementUnlock: event,
      lastActionStatus: 'achievement_unlocked',
      lastActionMessage: '${event.name} 解锁！',
    );

    // Clear after delay
    Future.delayed(const Duration(seconds: 3), () {
      if (mounted) {
        state = state.copyWith(
          clearActionFeedback: true,
        );
      }
    });
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

    // TODO: 更新 UI 中对应 ActionCard 的状态
    // 例如：标记为已确认、已忽略，或者从列表中移除
    // state = state.copyWith(messages: _updateMessageActionStatus(event.actionId, event.status));
  }

  String _getDefaultStatusMessage(String status) {
    switch (status) {
      case 'confirmed':
        return '✅ 已确认';
      case 'dismissed':
        return '❌ 已忽略';
      case 'processing':
        return '⏳ 处理中...';
      case 'completed':
        return '✅ 已完成';
      case 'failed':
        return '❌ 操作失败';
      default:
        return '📝 状态更新: $status';
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
    switch (status) {
      case 'approved':
        return '✅ 计划已批准';
      case 'rejected':
        return '❌ 计划已取消';
      case 'modify_requested':
        return '📝 请提供修改要求...';
      case 'acknowledged':
        return '✅ 反馈已收到';
      default:
        return '📋 计划状态更新: $status';
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
      String outcome, double scoreDelta, int rounds) {
    final roundsInfo = rounds > 1 ? ' ($rounds轮)' : '';
    switch (outcome) {
      case 'fixed':
        return '✅ 内容已优化$roundsInfo，分数提升 +${(scoreDelta * 100).toInt()}%';
      case 'improved':
        return '📈 内容有所改善$roundsInfo，分数提升 +${(scoreDelta * 100).toInt()}%';
      case 'no_change':
        return 'ℹ️ 优化尝试完成，内容无明显变化';
      case 'degraded':
        return '⚠️ 优化尝试未达预期，保留原内容';
      case 'failed':
        return '❌ 优化失败，请稍后重试';
      default:
        return '🔄 反思处理完成: $outcome';
    }
  }

  /// Get score label for a given score
  String _getScoreLabelForScore(double score) {
    if (score >= 0.9) return '优秀';
    if (score >= 0.7) return '良好';
    if (score >= 0.5) return '及格';
    return '需改进';
  }
}
