part of 'chat_provider.dart';

extension ChatNotifierHistory on ChatNotifier {
  Future<void> _updateDailyUsage(UsageEvent event) async {
    final prefs = await SharedPreferences.getInstance();
    final today = _dateKey(DateTime.now());
    final storedDate = prefs.getString(ChatNotifier._dailyUsageDateKey);

    var totalTokens = prefs.getInt(ChatNotifier._dailyUsageTokensKey) ?? 0;
    var totalCost = prefs.getInt(ChatNotifier._dailyUsageCostKey) ?? 0;

    if (storedDate != today) {
      totalTokens = 0;
      totalCost = 0;
      await prefs.setString(ChatNotifier._dailyUsageDateKey, today);
    }

    totalTokens += event.totalTokens;
    if (event.costMicroUsd != null) {
      totalCost += event.costMicroUsd!;
      await prefs.setInt(ChatNotifier._dailyUsageCostKey, totalCost);
    }
    await prefs.setInt(ChatNotifier._dailyUsageTokensKey, totalTokens);

    state = state.copyWith(
      dailyTokens: totalTokens,
      dailyTokenLimit: ChatNotifier._dailyTokenLimitDefault,
      dailyCostMicroUsd: totalCost,
    );
  }

  String _dateKey(DateTime date) =>
      '${date.year.toString().padLeft(4, '0')}-'
      '${date.month.toString().padLeft(2, '0')}-'
      '${date.day.toString().padLeft(2, '0')}';

  Future<void> loadConversationHistory(String conversationId) async {
    // P0修复: 防止重复加载同一会话
    if (loadingConversationId == conversationId) {
      return;
    }
    loadingConversationId = conversationId;

    state = state.copyWith(
      isLoading: true,
      isSending: false,
      isLoadingMore: false,
      hasMoreMessages: true,
      streamingContent: '',
      clearError: true,
      clearAiStatus: true,
      clearReasoning: true,
      clearDagExecution: true,
      clearActionFeedback: true,
      clearPendingReview: true,
      clearPendingContentReview: true,
      clearTransparency: true,
      activeTools: const [],
      agentActivities: const [],
      reasoningSteps: const [],
      pendingInterventions: const [],
    );
    try {
      // P0修复: 10s超时防止DB慢查询导致UI无限冻结，超时后降级为空历史
      final history = await _chatRepository
          .getConversationHistory(conversationId)
          .timeout(
            const Duration(seconds: 10),
            onTimeout: () {
              debugPrint('[ChatHistory] Load timeout for $conversationId, falling back to empty history');
              return <ChatMessageModel>[];
            },
          );

      // P0修复: 若等待期间会话已切换（计划切换竞态），放弃此次更新
      if (loadingConversationId != conversationId) {
        return;
      }

      state = state.copyWith(
        isLoading: false,
        messages: history,
        conversationId: conversationId,
      );
    } catch (e) {
      if (loadingConversationId != conversationId) {
        return;
      }
      final l10n = I18nService.instance.l10n;
      final errorMessage = ErrorMessages.getUserFriendlyMessage(
        'UNKNOWN',
        l10n.chatHistoryLoadFailed('$e'),
      );

      state = state.copyWith(
        isLoading: false,
        error: errorMessage,
        errorCode: 'UNKNOWN',
        isErrorRetryable: true,
      );
    } finally {
      if (loadingConversationId == conversationId) {
        loadingConversationId = null;
      }
    }
  }

  void addAttachment(StoredFile file) {
    if (state.attachedFiles.any((item) => item.id == file.id)) {
      return;
    }
    state = state.copyWith(attachedFiles: [...state.attachedFiles, file]);
  }

  void removeAttachment(String fileId) {
    state = state.copyWith(
      attachedFiles:
          state.attachedFiles.where((file) => file.id != fileId).toList(),
    );
  }

  void clearAttachments() {
    state = state.copyWith(clearAttachments: true);
  }

  Future<List<Map<String, dynamic>>> getRecentConversations() async =>
      _chatRepository.getRecentConversations();

  Future<void> loadMoreHistory() async {
    // 如果没有对话 ID 或正在加载或没有更多消息，则不加载
    if (state.conversationId == null ||
        state.isLoadingMore ||
        !state.hasMoreMessages) {
      return;
    }

    state = state.copyWith(isLoadingMore: true);

    try {
      const pageSize = 20;
      final currentCount = state.messages.length;

      final moreMessages = await _chatRepository.getConversationHistory(
        state.conversationId!,
        limit: pageSize,
        offset: currentCount,
      );

      // 如果返回的消息少于 pageSize，说明没有更多消息了
      final hasMore = moreMessages.length >= pageSize;

      state = state.copyWith(
        isLoadingMore: false,
        messages: [...state.messages, ...moreMessages],
        hasMoreMessages: hasMore,
      );
    } catch (e) {
      final l10n = I18nService.instance.l10n;
      final errorMessage = ErrorMessages.getUserFriendlyMessage(
        'UNKNOWN',
        l10n.chatHistoryLoadMoreFailed('$e'),
      );

      state = state.copyWith(
        isLoadingMore: false,
        error: errorMessage,
        errorCode: 'UNKNOWN',
        isErrorRetryable: true,
      );
    }
  }
}
