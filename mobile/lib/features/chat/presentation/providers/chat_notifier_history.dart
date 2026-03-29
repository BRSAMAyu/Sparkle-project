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

  String _dateKey(DateTime date) => '${date.year.toString().padLeft(4, '0')}-'
      '${date.month.toString().padLeft(2, '0')}-'
      '${date.day.toString().padLeft(2, '0')}';

  Future<void> loadConversationHistory(String conversationId) async {
    final previousMessages = state.messages;
    final previousConversationId = state.conversationId;

    // P0修复: 取消之前的加载请求，防止快速切换会话时竞态条件
    unawaited(_historyLoadOperation?.cancel());
    _historyLoadOperation = null;

    // P0修复: 防止重复加载同一会话
    if (loadingConversationId == conversationId) {
      return;
    }
    loadingConversationId = conversationId;

    state = state.copyWith(
      isLoading: true,
      isSending: false,
      isLoadingMore: false,
      hasMoreMessages: false,
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

    // P0修复: 使用CancelableOperation包装异步请求，支持取消
    _historyLoadOperation = CancelableOperation.fromFuture(
      _chatRepository
          .getConversationHistory(
        conversationId,
        limit: ChatNotifier.historyPageSize,
      )
          .timeout(
        const Duration(seconds: 10),
        onTimeout: () {
          throw TimeoutException('[ChatHistory] Load timeout for $conversationId');
        },
      ),
      onCancel: () {
        debugPrint('[ChatHistory] Load cancelled for $conversationId');
      },
    );

    try {
      final history = await _historyLoadOperation!.value;

      // P0修复: 若等待期间会话已切换（计划切换竞态），放弃此次更新
      if (loadingConversationId != conversationId) {
        return;
      }

      state = state.copyWith(
        isLoading: false,
        messages: history,
        conversationId: conversationId,
        hasMoreMessages: history.length >= ChatNotifier.historyPageSize,
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
        messages: previousMessages,
        conversationId: previousConversationId,
        error: errorMessage,
        errorCode: 'UNKNOWN',
        isErrorRetryable: true,
      );
    } finally {
      if (loadingConversationId == conversationId) {
        loadingConversationId = null;
      }
      _historyLoadOperation = null;
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
      final currentCount = state.messages.length;

      final moreMessages = await _chatRepository.getConversationHistory(
        state.conversationId!,
        limit: ChatNotifier.historyPageSize,
        offset: currentCount,
      );

      // 如果返回的消息少于 pageSize，说明没有更多消息了
      final hasMore = moreMessages.length >= ChatNotifier.historyPageSize;

      state = state.copyWith(
        isLoadingMore: false,
        messages: [...moreMessages, ...state.messages],
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
