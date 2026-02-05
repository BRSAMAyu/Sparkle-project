part of 'chat_provider.dart';

extension ChatNotifierReviews on ChatNotifier {
  /// Submit plan review decision via gRPC
  Future<bool> submitPlanReview({
    required ReviewDecision decision,
    String? userComment,
    Map<String, String>? meta,
  }) async {
    final review = state.pendingPlanReview;
    if (review == null) {
      debugPrint('⚠️ No pending plan review to submit');
      return false;
    }

    // Get current user
    final authState = _ref.read(authProvider);
    final user = authState.user;
    if (user == null) {
      debugPrint('⚠️ User not authenticated');
      state = state.copyWith(
        lastActionStatus: 'error',
        lastActionMessage: '请先登录',
      );
      return false;
    }

    // Get access token
    final authRepository = _ref.read(authRepositoryProvider);
    final authToken = await authRepository.getAccessToken();

    try {
      _planReviewService ??= PlanReviewGrpcService();

      // Map ReviewDecision to UserReviewDecision
      final grpcDecision = _mapReviewDecision(decision);

      final result = await _planReviewService!.submitReview(
        userId: user.id,
        planId: review.planId,
        reviewId: review.reviewId,
        decision: grpcDecision,
        userComment: userComment,
        authToken: authToken,
        meta: meta,
      );

      if (result.success) {
        // Update state with success message
        state = state.copyWith(
          lastActionStatus: 'submitted',
          lastActionMessage: result.message ?? _getSuccessMessageKey(decision),
          clearPendingReview: true,
        );

        // Clear feedback message after delay
        Future.delayed(const Duration(seconds: 2), () {
          if (mounted) {
            state = state.copyWith(clearActionFeedback: true);
          }
        });

        debugPrint('✅ Plan review submitted: ${decision.name}');
        return true;
      } else {
        // Update state with error message
        state = state.copyWith(
          lastActionStatus: 'error',
          lastActionMessage: result.message ?? 'submit_failed',
        );
        debugPrint('❌ Plan review failed: ${result.message}');
        return false;
      }
    } catch (e) {
      debugPrint('❌ Plan review error: $e');
      state = state.copyWith(
        lastActionStatus: 'error',
        lastActionMessage: 'network_error_retry',
      );
      return false;
    }
  }

  /// Map ReviewDecision from UI to UserReviewDecision for gRPC
  UserReviewDecision _mapReviewDecision(ReviewDecision decision) {
    switch (decision) {
      case ReviewDecision.approved:
        return UserReviewDecision.approve;
      case ReviewDecision.rejected:
        return UserReviewDecision.reject;
      case ReviewDecision.needsModification:
        return UserReviewDecision.modify;
      case ReviewDecision.requiresConfirmation:
        return UserReviewDecision.acknowledge;
    }
  }

  /// Get user-friendly success message key (to be localized by UI)
  String _getSuccessMessageKey(ReviewDecision decision) {
    switch (decision) {
      case ReviewDecision.approved:
        return 'review_approved';
      case ReviewDecision.rejected:
        return 'review_rejected';
      case ReviewDecision.needsModification:
        return 'review_modification_requested';
      case ReviewDecision.requiresConfirmation:
        return 'review_confirmed';
    }
  }

  /// 用户接受审查后的内容（不采取行动）
  void acceptContentReview() {
    state = state.copyWith(clearPendingContentReview: true);
    debugPrint('✅ Content review accepted');
  }

  /// 用户拒绝内容，请求重新生成
  void rejectContentReview() {
    final review = state.pendingContentReview;
    if (review == null) return;

    state = state.copyWith(
      clearPendingContentReview: true,
      lastActionStatus: 'rejected',
      lastActionMessage: '已请求重新生成',
    );

    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) {
        state = state.copyWith(clearActionFeedback: true);
      }
    });

    requestRegeneration(
      originalContentId: 'content_from_review_${review.reviewId}',
      reviewId: review.reviewId,
      regenerationType: 'fix_issues',
    ).then((result) {
      if (result == null || result['success'] != true) {
        debugPrint('❌ Regeneration request failed for ${review.reviewId}');
      }
    });

    debugPrint('❌ Content review rejected, requesting regeneration');
  }

  /// 用户请求人工审查
  void requestHumanReview() {
    state = state.copyWith(
      lastActionStatus: 'human_review_requested',
      lastActionMessage: '已提交人工审查请求',
    );

    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) {
        state = state.copyWith(clearActionFeedback: true);
      }
    });

    debugPrint('👤 Human review requested');
  }

  // ============================================
  // Phase 2e: Review Override & Appeal
  // ============================================

  /// 用户覆盖审查决策
  Future<bool> submitReviewOverride({
    required String reviewId,
    required String originalDecision,
    required String newDecision,
    required String reason,
  }) async {
    final authState = _ref.read(authProvider);
    final user = authState.user;
    if (user == null) {
      debugPrint('⚠️ User not authenticated');
      state = state.copyWith(
        lastActionStatus: 'error',
        lastActionMessage: '请先登录',
      );
      return false;
    }

    try {
      // Get access token
      final authRepository = _ref.read(authRepositoryProvider);
      final authToken = await authRepository.getAccessToken();

      _reviewService ??= ReviewGrpcService();

      final result = await _reviewService!.submitReviewOverride(
        userId: user.id,
        reviewId: reviewId,
        originalDecision: originalDecision,
        newDecision: newDecision,
        reason: reason,
        authToken: authToken,
      );

      if (result.success) {
        state = state.copyWith(
          lastActionStatus: 'override_submitted',
          lastActionMessage: result.message ??
              (newDecision == 'passed'
                  ? '已接受内容（尽管未通过审查）'
                  : '已拒绝内容（尽管审查通过）'),
          clearPendingContentReview: true,
        );

        Future.delayed(const Duration(seconds: 2), () {
          if (mounted) {
            state = state.copyWith(clearActionFeedback: true);
          }
        });

        debugPrint('✅ Review override submitted: $originalDecision -> $newDecision');
        return true;
      } else {
        state = state.copyWith(
          lastActionStatus: 'error',
          lastActionMessage: result.message ?? '提交失败，请重试',
        );
        return false;
      }
    } catch (e) {
      debugPrint('❌ Review override error: $e');
      state = state.copyWith(
        lastActionStatus: 'error',
        lastActionMessage: '提交失败，请重试',
      );
      return false;
    }
  }

  /// 用户提交审查申诉
  Future<bool> submitReviewAppeal({
    required String reviewId,
    required String reason,
    required List<String> issues,
  }) async {
    final authState = _ref.read(authProvider);
    final user = authState.user;
    if (user == null) {
      debugPrint('⚠️ User not authenticated');
      state = state.copyWith(
        lastActionStatus: 'error',
        lastActionMessage: '请先登录',
      );
      return false;
    }

    try {
      // Get access token
      final authRepository = _ref.read(authRepositoryProvider);
      final authToken = await authRepository.getAccessToken();

      _reviewService ??= ReviewGrpcService();

      final result = await _reviewService!.submitReviewAppeal(
        userId: user.id,
        reviewId: reviewId,
        appealReason: reason,
        issuesWithReview: issues,
        authToken: authToken,
      );

      if (result.success) {
        state = state.copyWith(
          lastActionStatus: 'appeal_submitted',
          lastActionMessage: result.message ?? '申诉已提交，正在处理...',
        );

        Future.delayed(const Duration(seconds: 2), () {
          if (mounted) {
            state = state.copyWith(clearActionFeedback: true);
          }
        });

        debugPrint('✅ Review appeal submitted for review $reviewId');
        return true;
      } else {
        state = state.copyWith(
          lastActionStatus: 'error',
          lastActionMessage: result.message ?? '提交失败，请重试',
        );
        return false;
      }
    } catch (e) {
      debugPrint('❌ Review appeal error: $e');
      state = state.copyWith(
        lastActionStatus: 'error',
        lastActionMessage: '提交失败，请重试',
      );
      return false;
    }
  }

  /// 获取申诉状态
  Future<Map<String, dynamic>?> getAppealStatus(String appealId) async {
    final authState = _ref.read(authProvider);
    final user = authState.user;
    if (user == null) {
      debugPrint('⚠️ User not authenticated');
      return null;
    }

    try {
      // Get access token
      final authRepository = _ref.read(authRepositoryProvider);
      final authToken = await authRepository.getAccessToken();

      _reviewService ??= ReviewGrpcService();

      final result = await _reviewService!.getAppealStatus(
        userId: user.id,
        appealId: appealId,
        authToken: authToken,
      );

      if (result != null) {
        return {
          'appeal_id': result.appealId,
          'review_id': result.reviewId,
          'status': result.status,
          'submitted_at': result.submittedAt,
          'appeal_reason': result.appealReason,
          'resolution': result.resolution,
          'resolved_by': result.resolvedBy,
          'resolved_at': result.resolvedAt,
          'secondary_decision': result.secondaryDecision,
          'secondary_score': result.secondaryScore,
        };
      }
      return null;
    } catch (e) {
      debugPrint('❌ Get appeal status error: $e');
      return null;
    }
  }

  // ============================================
  // Phase 2f: Feedback Complete Integration
  // ============================================

  /// 提交审查反馈（评分）
  ///
  /// 允许用户对审查结果进行评分和反馈
  Future<bool> submitReviewFeedback({
    required String reviewId,
    int? rating,
    bool? wasHelpful,
    bool? wasAccurate,
    List<String>? inaccuratePoints,
    String? specificityLevel,
    String? comments,
    List<String>? tags,
  }) async {
    final authState = _ref.read(authProvider);
    final user = authState.user;
    if (user == null) {
      debugPrint('⚠️ User not authenticated');
      return false;
    }

    try {
      debugPrint('[ChatProvider] Submitting review feedback for $reviewId');

      // Get access token
      final authRepository = _ref.read(authRepositoryProvider);
      final authToken = await authRepository.getAccessToken();

      _reviewService ??= ReviewGrpcService();

      final result = await _reviewService!.submitReviewFeedback(
        userId: user.id,
        reviewId: reviewId,
        rating: rating,
        wasHelpful: wasHelpful,
        wasAccurate: wasAccurate,
        inaccuratePoints: inaccuratePoints,
        specificityLevel: specificityLevel,
        comments: comments,
        tags: tags,
        authToken: authToken,
      );

      debugPrint('[ChatProvider] Feedback ${result.success ? "submitted" : "failed"}');
      return result.success;
    } catch (e) {
      debugPrint('[ChatProvider] Failed to submit feedback: $e');
      return false;
    }
  }

  /// 为审查评分（简化接口）
  Future<bool> rateReview({
    required String reviewId,
    required int rating,
    String? comments,
  }) async => submitReviewFeedback(
      reviewId: reviewId,
      rating: rating,
      wasHelpful: rating >= 4,
      comments: comments,
    );

  /// 请求内容重新生成
  ///
  /// 基于用户反馈请求AI重新生成内容
  Future<Map<String, dynamic>?> requestRegeneration({
    required String originalContentId,
    required String reviewId,
    required String regenerationType,
    List<String>? improvementHints,
    List<String>? focusAreas,
    String? customInstructions,
  }) async {
    final authState = _ref.read(authProvider);
    final user = authState.user;
    if (user == null) {
      debugPrint('⚠️ User not authenticated');
      return null;
    }

    try {
      debugPrint(
        '[ChatProvider] Requesting regeneration for content $originalContentId',
      );

      // Get access token
      final authRepository = _ref.read(authRepositoryProvider);
      final authToken = await authRepository.getAccessToken();

      _reviewService ??= ReviewGrpcService();

      final result = await _reviewService!.requestRegeneration(
        userId: user.id,
        originalContentId: originalContentId,
        reviewId: reviewId,
        regenerationType: regenerationType,
        improvementHints: improvementHints,
        focusAreas: focusAreas,
        customInstructions: customInstructions,
        authToken: authToken,
      );

      if (result.success) {
        final resultMap = {
          'request_id': result.requestId,
          'success': true,
          'new_content': result.newContent,
          'new_content_id': result.newContentId,
          'improvement_summary': result.improvementSummary,
          'changes_made': result.changesMade,
          'score_improvement': result.scoreImprovement,
          'generation_time_ms': result.generationTimeMs,
        };
        debugPrint('[ChatProvider] Regeneration completed: $resultMap');
        return resultMap;
      } else {
        debugPrint('[ChatProvider] Regeneration failed: ${result.message}');
        return {
          'success': false,
          'message': result.message,
        };
      }
    } catch (e) {
      debugPrint('[ChatProvider] Failed to request regeneration: $e');
      return null;
    }
  }

  /// 获取用户反馈模式
  ///
  /// 返回用户的历史反馈模式，用于个性化审查
  Future<Map<String, dynamic>?> getUserFeedbackPattern() async {
    try {
      // TODO: Implement gRPC call to GetUserFeedbackPattern
      // For now, return null (no pattern yet)
      return null;
    } catch (e) {
      debugPrint('[ChatProvider] Failed to get feedback pattern: $e');
      return null;
    }
  }

  /// 获取反馈统计
  ///
  /// 返回用户反馈的整体统计数据
  Future<Map<String, dynamic>?> getFeedbackStatistics({
    int days = 30,
  }) async {
    final authState = _ref.read(authProvider);
    final user = authState.user;
    if (user == null) {
      debugPrint('⚠️ User not authenticated');
      return null;
    }

    try {
      // Get access token
      final authRepository = _ref.read(authRepositoryProvider);
      final authToken = await authRepository.getAccessToken();

      _reviewService ??= ReviewGrpcService();

      final result = await _reviewService!.getFeedbackStatistics(
        userId: user.id,
        periodDays: days,
        authToken: authToken,
      );

      if (result.success) {
        return {
          'total_feedbacks': result.totalFeedbacks,
          'avg_rating': result.avgRating,
          'helpful_rate': result.helpfulRate,
          'accuracy_rate': result.accuracyRate,
          'regeneration_requests': result.regenerationRequests,
          'successful_regenerations': result.successfulRegenerations,
          'period_days': result.periodDays,
        };
      }
      return null;
    } catch (e) {
      debugPrint('[ChatProvider] Failed to get feedback statistics: $e');
      return null;
    }
  }
}
