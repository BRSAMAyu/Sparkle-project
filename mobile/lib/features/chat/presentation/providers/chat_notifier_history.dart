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
      reasoningSteps: const [],
      pendingInterventions: const [],
    );
    try {
      final history = await _chatRepository.getConversationHistory(conversationId);
      state = state.copyWith(
        isLoading: false,
        messages: history,
        conversationId: conversationId,
      );
    } catch (e) {
      final errorMessage = ErrorMessages.getUserFriendlyMessage(
        'UNKNOWN',
        '加载历史失败: $e',
      );

      state = state.copyWith(
        isLoading: false,
        error: errorMessage,
        errorCode: 'UNKNOWN',
        isErrorRetryable: true,
      );
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
      final errorMessage = ErrorMessages.getUserFriendlyMessage(
        'UNKNOWN',
        '加载更多消息失败: $e',
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
