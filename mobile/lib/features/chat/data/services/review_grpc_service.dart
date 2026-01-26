import 'package:grpc/grpc.dart';
import 'package:sparkle/core/constants/api_constants.dart';
import 'package:sparkle/gen/agent_service.pbgrpc.dart'
    as proto;

/// Result classes for review gRPC calls
///
/// These classes wrap the response data for easier handling in the UI.

class ReviewOverrideResult {
  const ReviewOverrideResult({
    required this.success,
    this.message,
    this.overrideId,
  });

  final bool success;
  final String? message;
  final String? overrideId;
}

class ReviewAppealResult {
  const ReviewAppealResult({
    required this.success,
    this.message,
    this.appealId,
    this.status,
  });

  final bool success;
  final String? message;
  final String? appealId;
  final String? status;
}

class AppealStatusResult {
  const AppealStatusResult({
    required this.appealId,
    required this.reviewId,
    required this.status,
    required this.submittedAt,
    this.appealReason,
    this.resolution,
    this.resolvedBy,
    this.resolvedAt,
    this.secondaryDecision,
    this.secondaryScore,
  });

  final String appealId;
  final String reviewId;
  final String status;
  final String submittedAt;
  final String? appealReason;
  final String? resolution;
  final String? resolvedBy;
  final String? resolvedAt;
  final String? secondaryDecision;
  final double? secondaryScore;
}

class ReviewFeedbackResult {
  const ReviewFeedbackResult({
    required this.success,
    this.message,
    this.feedbackId,
  });

  final bool success;
  final String? message;
  final String? feedbackId;
}

class RegenerationResult {
  const RegenerationResult({
    required this.success,
    this.message,
    this.requestId,
    this.newContent,
    this.newContentId,
    this.improvementSummary,
    this.changesMade = const [],
    this.scoreImprovement = 0.0,
    this.generationTimeMs = 0,
  });

  final bool success;
  final String? message;
  final String? requestId;
  final String? newContent;
  final String? newContentId;
  final String? improvementSummary;
  final List<String> changesMade;
  final double scoreImprovement;
  final int generationTimeMs;
}

class FeedbackStatisticsResult {
  const FeedbackStatisticsResult({
    required this.success,
    this.totalFeedbacks = 0,
    this.avgRating = 0.0,
    this.helpfulRate = 0.0,
    this.accuracyRate = 0.0,
    this.regenerationRequests = 0,
    this.successfulRegenerations = 0,
    this.periodDays = 30,
  });

  final bool success;
  final int totalFeedbacks;
  final double avgRating;
  final double helpfulRate;
  final double accuracyRate;
  final int regenerationRequests;
  final int successfulRegenerations;
  final int periodDays;
}

class ArbitrationCaseInfo {
  const ArbitrationCaseInfo({
    required this.caseId,
    required this.appealId,
    required this.reviewId,
    required this.userId,
    required this.escalationReason,
    required this.priority,
    required this.createdAt,
    required this.status,
    this.assignedTo,
    this.assignedAt,
    this.originalReviewScore = 0.0,
    this.secondaryReviewScore,
    this.scoreDiscrepancy = 0.0,
    this.resolution,
    this.finalDecision,
    this.resolvedAt,
    this.resolvedBy,
    this.notes = const [],
  });

  factory ArbitrationCaseInfo.fromProto(proto.ArbitrationCaseInfo info) {
    return ArbitrationCaseInfo(
      caseId: info.caseId,
      appealId: info.appealId,
      reviewId: info.reviewId,
      userId: info.userId,
      escalationReason: info.escalationReason,
      priority: info.priority,
      createdAt: info.createdAt,
      status: info.status,
      assignedTo: info.assignedTo.isNotEmpty ? info.assignedTo : null,
      assignedAt: info.assignedAt.isNotEmpty ? info.assignedAt : null,
      originalReviewScore: info.originalReviewScore,
      secondaryReviewScore: info.secondaryReviewScore > 0
          ? info.secondaryReviewScore
          : null,
      scoreDiscrepancy: info.scoreDiscrepancy,
      resolution: info.resolution.isNotEmpty ? info.resolution : null,
      finalDecision: info.finalDecision.isNotEmpty ? info.finalDecision : null,
      resolvedAt: info.resolvedAt.isNotEmpty ? info.resolvedAt : null,
      resolvedBy: info.resolvedBy.isNotEmpty ? info.resolvedBy : null,
      notes: info.notes.toList(),
    );
  }

  final String caseId;
  final String appealId;
  final String reviewId;
  final String userId;
  final String escalationReason;
  final String priority;
  final String createdAt;
  final String status;
  final String? assignedTo;
  final String? assignedAt;
  final double originalReviewScore;
  final double? secondaryReviewScore;
  final double scoreDiscrepancy;
  final String? resolution;
  final String? finalDecision;
  final String? resolvedAt;
  final String? resolvedBy;
  final List<String> notes;
}

class ArbitrationQueueResult {
  const ArbitrationQueueResult({
    required this.success,
    this.cases = const [],
    this.totalCount = 0,
    this.message,
  });

  final bool success;
  final List<ArbitrationCaseInfo> cases;
  final int totalCount;
  final String? message;
}

class AssignCaseResult {
  const AssignCaseResult({
    required this.success,
    this.message,
  });

  final bool success;
  final String? message;
}

class SubmitDecisionResult {
  const SubmitDecisionResult({
    required this.success,
    this.message,
    this.decisionId,
  });

  final bool success;
  final String? message;
  final String? decisionId;
}

class ArbitrationQueueStatsResult {
  const ArbitrationQueueStatsResult({
    required this.success,
    this.totalPending = 0,
    this.totalAssigned = 0,
    this.totalInReview = 0,
    this.totalResolvedToday = 0,
    this.avgResolutionTimeHours = 0.0,
    this.byPriority = const {},
    this.byReason = const {},
  });

  factory ArbitrationQueueStatsResult.fromProto(
    proto.ArbitrationQueueStatsInfo stats,
  ) {
    return ArbitrationQueueStatsResult(
      success: true,
      totalPending: stats.totalPending,
      totalAssigned: stats.totalAssigned,
      totalInReview: stats.totalInReview,
      totalResolvedToday: stats.totalResolvedToday,
      avgResolutionTimeHours: stats.avgResolutionTimeHours,
      byPriority: stats.byPriority.map((k, v) => MapEntry(k, v)),
      byReason: stats.byReason.map((k, v) => MapEntry(k, v)),
    );
  }

  final bool success;
  final int totalPending;
  final int totalAssigned;
  final int totalInReview;
  final int totalResolvedToday;
  final double avgResolutionTimeHours;
  final Map<String, int> byPriority;
  final Map<String, int> byReason;
}

/// Review gRPC Service
///
/// Handles all review-related gRPC calls to the Python backend.
/// This includes review override, appeal, feedback, regeneration, and arbitration.
class ReviewGrpcService {
  proto.AgentServiceClient? _client;
  ClientChannel? _channel;

  /// Get or create the gRPC client
  proto.AgentServiceClient _getClient() {
    _channel ??= ClientChannel(
      ApiConstants.grpcHost,
      port: ApiConstants.grpcPort,
      options: const ChannelOptions(
        credentials: ChannelCredentials.insecure(),
        idleTimeout: Duration(minutes: 5),
      ),
    );

    _client ??= proto.AgentServiceClient(_channel!);

    return _client!;
  }

  // ========================================================================
  // Phase 2e: Review Override & Appeal
  // ========================================================================

  /// Submit user override of a review decision
  ///
  /// Parameters:
  /// - [userId]: The user ID
  /// - [reviewId]: The review ID being overridden
  /// - [originalDecision]: Original review decision (e.g., "failed", "passed")
  /// - [newDecision]: User's new decision
  /// - [reason]: Reason for override
  /// - [authToken]: Optional authorization token
  Future<ReviewOverrideResult> submitReviewOverride({
    required String userId,
    required String reviewId,
    required String originalDecision,
    required String newDecision,
    required String reason,
    String? authToken,
  }) async {
    try {
      final request = proto.ReviewOverrideRequest()
        ..userId = userId
        ..reviewId = reviewId
        ..originalDecision = originalDecision
        ..newDecision = newDecision
        ..reason = reason;

      final metadata = <String, String>{
        'user-id': userId,
      };
      if (authToken != null) {
        metadata['authorization'] = authToken;
      }

      final client = _getClient();
      final response = await client.submitReviewOverride(
        request,
        options: CallOptions(
          metadata: metadata,
          timeout: const Duration(seconds: 30),
        ),
      );

      return ReviewOverrideResult(
        success: response.success,
        message: response.message.isEmpty ? null : response.message,
        overrideId: response.overrideId.isEmpty ? null : response.overrideId,
      );
    } on GrpcError catch (e) {
      return ReviewOverrideResult(
        success: false,
        message: 'gRPC error: ${e.message ?? e.toString()}',
      );
    } catch (e) {
      return ReviewOverrideResult(
        success: false,
        message: 'Error: ${e.toString()}',
      );
    }
  }

  /// Submit an appeal against a review
  ///
  /// Parameters:
  /// - [userId]: The user ID
  /// - [reviewId]: The review ID to appeal
  /// - [appealReason]: Main reason for the appeal
  /// - [issuesWithReview]: Specific issues with the review
  /// - [authToken]: Optional authorization token
  Future<ReviewAppealResult> submitReviewAppeal({
    required String userId,
    required String reviewId,
    required String appealReason,
    List<String>? issuesWithReview,
    String? authToken,
  }) async {
    try {
      final request = proto.ReviewAppealRequest()
        ..userId = userId
        ..reviewId = reviewId
        ..appealReason = appealReason
        ..issuesWithReview.addAll(issuesWithReview ?? []);

      final metadata = <String, String>{
        'user-id': userId,
      };
      if (authToken != null) {
        metadata['authorization'] = authToken;
      }

      final client = _getClient();
      final response = await client.submitReviewAppeal(
        request,
        options: CallOptions(
          metadata: metadata,
          timeout: const Duration(seconds: 30),
        ),
      );

      return ReviewAppealResult(
        success: response.success,
        message: response.message.isEmpty ? null : response.message,
        appealId: response.appealId.isEmpty ? null : response.appealId,
        status: response.status.isEmpty ? null : response.status,
      );
    } on GrpcError catch (e) {
      return ReviewAppealResult(
        success: false,
        message: 'gRPC error: ${e.message ?? e.toString()}',
      );
    } catch (e) {
      return ReviewAppealResult(
        success: false,
        message: 'Error: ${e.toString()}',
      );
    }
  }

  /// Get the status of an appeal
  ///
  /// Parameters:
  /// - [userId]: The user ID
  /// - [appealId]: The appeal ID
  /// - [authToken]: Optional authorization token
  Future<AppealStatusResult?> getAppealStatus({
    required String userId,
    required String appealId,
    String? authToken,
  }) async {
    try {
      final request = proto.AppealStatusRequest()
        ..userId = userId
        ..appealId = appealId;

      final metadata = <String, String>{
        'user-id': userId,
      };
      if (authToken != null) {
        metadata['authorization'] = authToken;
      }

      final client = _getClient();
      final response = await client.getAppealStatus(
        request,
        options: CallOptions(
          metadata: metadata,
          timeout: const Duration(seconds: 30),
        ),
      );

      // Return null if appeal not found (empty response)
      if (response.appealId.isEmpty) {
        return null;
      }

      return AppealStatusResult(
        appealId: response.appealId,
        reviewId: response.reviewId,
        status: response.status,
        submittedAt: response.submittedAt,
        appealReason: response.appealReason.isEmpty
            ? null
            : response.appealReason,
        resolution: response.resolution.isEmpty ? null : response.resolution,
        resolvedBy: response.resolvedBy.isEmpty ? null : response.resolvedBy,
        resolvedAt: response.resolvedAt.isEmpty ? null : response.resolvedAt,
        secondaryDecision: response.secondaryDecision.isEmpty
            ? null
            : response.secondaryDecision,
        secondaryScore: response.secondaryScore > 0
            ? response.secondaryScore
            : null,
      );
    } on GrpcError catch (e) {
      // Return null on not found
      if (e.code == StatusCode.notFound) {
        return null;
      }
      return AppealStatusResult(
        appealId: appealId,
        reviewId: '',
        status: 'error',
        submittedAt: '',
      );
    } catch (e) {
      return AppealStatusResult(
        appealId: appealId,
        reviewId: '',
        status: 'error',
        submittedAt: '',
      );
    }
  }

  // ========================================================================
  // Phase 2f: Review Feedback & Regeneration
  // ========================================================================

  /// Submit feedback on a review
  ///
  /// Parameters:
  /// - [userId]: The user ID
  /// - [reviewId]: The review ID
  /// - [feedbackType]: Type of feedback (rating, quality, accuracy, specificity)
  /// - [rating]: 1-5 rating
  /// - [wasHelpful]: Whether the review was helpful
  /// - [wasAccurate]: Whether the review was accurate
  /// - [inaccuratePoints]: List of inaccurate points
  /// - [specificityLevel]: Specificity level (too_vague, appropriate, too_detailed)
  /// - [comments]: Free-form comments
  /// - [tags]: Optional tags
  /// - [authToken]: Optional authorization token
  Future<ReviewFeedbackResult> submitReviewFeedback({
    required String userId,
    required String reviewId,
    String feedbackType = 'rating',
    int? rating,
    bool? wasHelpful,
    bool? wasAccurate,
    List<String>? inaccuratePoints,
    String? specificityLevel,
    String? comments,
    List<String>? tags,
    String? authToken,
  }) async {
    try {
      final request = proto.ReviewFeedbackRequest()
        ..userId = userId
        ..reviewId = reviewId
        ..feedbackType = feedbackType;

      if (rating != null) {
        request.rating = rating;
      }
      if (wasHelpful != null) {
        request.wasHelpful = wasHelpful;
      }
      if (wasAccurate != null) {
        request.wasAccurate = wasAccurate;
      }
      if (inaccuratePoints != null) {
        request.inaccuratePoints.addAll(inaccuratePoints);
      }
      if (specificityLevel != null) {
        request.specificityLevel = specificityLevel;
      }
      if (comments != null) {
        request.comments = comments;
      }
      if (tags != null) {
        request.tags.addAll(tags);
      }

      final metadata = <String, String>{
        'user-id': userId,
      };
      if (authToken != null) {
        metadata['authorization'] = authToken;
      }

      final client = _getClient();
      final response = await client.submitReviewFeedback(
        request,
        options: CallOptions(
          metadata: metadata,
          timeout: const Duration(seconds: 30),
        ),
      );

      return ReviewFeedbackResult(
        success: response.success,
        message: response.message.isEmpty ? null : response.message,
        feedbackId: response.feedbackId.isEmpty ? null : response.feedbackId,
      );
    } on GrpcError catch (e) {
      return ReviewFeedbackResult(
        success: false,
        message: 'gRPC error: ${e.message ?? e.toString()}',
      );
    } catch (e) {
      return ReviewFeedbackResult(
        success: false,
        message: 'Error: ${e.toString()}',
      );
    }
  }

  /// Request content regeneration based on feedback
  ///
  /// Parameters:
  /// - [userId]: The user ID
  /// - [originalContentId]: Original content ID
  /// - [reviewId]: Associated review ID
  /// - [regenerationType]: Type of regeneration
  /// - [improvementHints]: Hints for improvement
  /// - [focusAreas]: Areas to focus on
  /// - [customInstructions]: Custom instructions
  /// - [authToken]: Optional authorization token
  Future<RegenerationResult> requestRegeneration({
    required String userId,
    required String originalContentId,
    required String reviewId,
    required String regenerationType,
    List<String>? improvementHints,
    List<String>? focusAreas,
    String? customInstructions,
    String? authToken,
  }) async {
    try {
      final request = proto.RegenerationRequest()
        ..userId = userId
        ..originalContentId = originalContentId
        ..reviewId = reviewId
        ..regenerationType = regenerationType;

      if (improvementHints != null) {
        request.improvementHints.addAll(improvementHints);
      }
      if (focusAreas != null) {
        request.focusAreas.addAll(focusAreas);
      }
      if (customInstructions != null) {
        request.customInstructions = customInstructions;
      }

      final metadata = <String, String>{
        'user-id': userId,
      };
      if (authToken != null) {
        metadata['authorization'] = authToken;
      }

      final client = _getClient();
      final response = await client.requestRegeneration(
        request,
        options: CallOptions(
          metadata: metadata,
          timeout: const Duration(seconds: 60), // Longer timeout for generation
        ),
      );

      return RegenerationResult(
        success: response.success,
        requestId: response.requestId.isEmpty ? null : response.requestId,
        newContent: response.newContent.isEmpty ? null : response.newContent,
        newContentId: response.newContentId.isEmpty ? null : response.newContentId,
        improvementSummary: response.improvementSummary.isEmpty
            ? null
            : response.improvementSummary,
        changesMade: response.changesMade.toList(),
        scoreImprovement: response.scoreImprovement,
        generationTimeMs: response.generationTimeMs,
      );
    } on GrpcError catch (e) {
      return RegenerationResult(
        success: false,
        message: 'gRPC error: ${e.message ?? e.toString()}',
      );
    } catch (e) {
      return RegenerationResult(
        success: false,
        message: 'Error: ${e.toString()}',
      );
    }
  }

  /// Get feedback statistics
  ///
  /// Parameters:
  /// - [userId]: The user ID
  /// - [periodDays]: Statistics period in days
  /// - [authToken]: Optional authorization token
  Future<FeedbackStatisticsResult> getFeedbackStatistics({
    required String userId,
    int periodDays = 30,
    String? authToken,
  }) async {
    try {
      final request = proto.FeedbackStatisticsRequest()
        ..userId = userId
        ..periodDays = periodDays;

      final metadata = <String, String>{
        'user-id': userId,
      };
      if (authToken != null) {
        metadata['authorization'] = authToken;
      }

      final client = _getClient();
      final response = await client.getFeedbackStatistics(
        request,
        options: CallOptions(
          metadata: metadata,
          timeout: const Duration(seconds: 30),
        ),
      );

      return FeedbackStatisticsResult(
        success: true,
        totalFeedbacks: response.totalFeedbacks,
        avgRating: response.avgRating,
        helpfulRate: response.helpfulRate,
        accuracyRate: response.accuracyRate,
        regenerationRequests: response.regenerationRequests,
        successfulRegenerations: response.successfulRegenerations,
        periodDays: response.periodDays,
      );
    } on GrpcError catch (e) {
      return FeedbackStatisticsResult(
        success: false,
      );
    } catch (e) {
      return FeedbackStatisticsResult(
        success: false,
      );
    }
  }

  // ========================================================================
  // Phase 2g: Arbitration System
  // ========================================================================

  /// Get arbitration queue for admins
  ///
  /// Parameters:
  /// - [limit]: Maximum number of cases to return
  /// - [priorityFilter]: Filter by priority (low, normal, high, urgent)
  /// - [statusFilter]: Filter by status (pending, assigned, in_review)
  /// - [authToken]: Optional authorization token
  Future<ArbitrationQueueResult> getArbitrationQueue({
    int limit = 50,
    String? priorityFilter,
    String? statusFilter,
    String? authToken,
  }) async {
    try {
      final request = proto.GetArbitrationQueueRequest()
        ..limit = limit;

      if (priorityFilter != null) {
        request.priorityFilter = priorityFilter;
      }
      if (statusFilter != null) {
        request.statusFilter = statusFilter;
      }

      final metadata = <String, String>{};
      if (authToken != null) {
        metadata['authorization'] = authToken;
      }

      final client = _getClient();
      final response = await client.getArbitrationQueue(
        request,
        options: CallOptions(
          metadata: metadata,
          timeout: const Duration(seconds: 30),
        ),
      );

      final cases = response.cases
          .map((info) => ArbitrationCaseInfo.fromProto(info))
          .toList();

      return ArbitrationQueueResult(
        success: true,
        cases: cases,
        totalCount: response.totalCount,
      );
    } on GrpcError catch (e) {
      return ArbitrationQueueResult(
        success: false,
        message: 'gRPC error: ${e.message ?? e.toString()}',
      );
    } catch (e) {
      return ArbitrationQueueResult(
        success: false,
        message: 'Error: ${e.toString()}',
      );
    }
  }

  /// Assign an arbitration case to an arbitrator
  ///
  /// Parameters:
  /// - [caseId]: The case ID to assign
  /// - [arbitratorId]: The arbitrator's ID
  /// - [arbitratorRole]: Role of arbitrator (reviewer, senior, admin)
  /// - [authToken]: Optional authorization token
  Future<AssignCaseResult> assignArbitrationCase({
    required String caseId,
    required String arbitratorId,
    String arbitratorRole = 'reviewer',
    String? authToken,
  }) async {
    try {
      final request = proto.AssignArbitrationCaseRequest()
        ..caseId = caseId
        ..arbitratorId = arbitratorId
        ..arbitratorRole = arbitratorRole;

      final metadata = <String, String>{};
      if (authToken != null) {
        metadata['authorization'] = authToken;
      }

      final client = _getClient();
      final response = await client.assignArbitrationCase(
        request,
        options: CallOptions(
          metadata: metadata,
          timeout: const Duration(seconds: 30),
        ),
      );

      return AssignCaseResult(
        success: response.success,
        message: response.message.isEmpty ? null : response.message,
      );
    } on GrpcError catch (e) {
      return AssignCaseResult(
        success: false,
        message: 'gRPC error: ${e.message ?? e.toString()}',
      );
    } catch (e) {
      return AssignCaseResult(
        success: false,
        message: 'Error: ${e.toString()}',
      );
    }
  }

  /// Submit an arbitration decision
  ///
  /// Parameters:
  /// - [caseId]: The case ID
  /// - [decision]: The decision (approved, rejected, partially_approved, escalated)
  /// - [explanation]: Explanation for the decision
  /// - [arbitratorId]: The arbitrator's ID
  /// - [arbitratorRole]: Role of arbitrator
  /// - [feedbackForModel]: Optional feedback for model learning
  /// - [authToken]: Optional authorization token
  Future<SubmitDecisionResult> submitArbitrationDecision({
    required String caseId,
    required String decision,
    required String explanation,
    required String arbitratorId,
    String arbitratorRole = 'reviewer',
    String? feedbackForModel,
    String? authToken,
  }) async {
    try {
      final request = proto.SubmitArbitrationDecisionRequest()
        ..caseId = caseId
        ..decision = decision
        ..explanation = explanation
        ..arbitratorId = arbitratorId
        ..arbitratorRole = arbitratorRole;

      if (feedbackForModel != null) {
        request.feedbackForModel = feedbackForModel;
      }

      final metadata = <String, String>{};
      if (authToken != null) {
        metadata['authorization'] = authToken;
      }

      final client = _getClient();
      final response = await client.submitArbitrationDecision(
        request,
        options: CallOptions(
          metadata: metadata,
          timeout: const Duration(seconds: 30),
        ),
      );

      return SubmitDecisionResult(
        success: response.success,
        message: response.message.isEmpty ? null : response.message,
        decisionId: response.decisionId.isEmpty ? null : response.decisionId,
      );
    } on GrpcError catch (e) {
      return SubmitDecisionResult(
        success: false,
        message: 'gRPC error: ${e.message ?? e.toString()}',
      );
    } catch (e) {
      return SubmitDecisionResult(
        success: false,
        message: 'Error: ${e.toString()}',
      );
    }
  }

  /// Get arbitration queue statistics
  ///
  /// Parameters:
  /// - [authToken]: Optional authorization token
  Future<ArbitrationQueueStatsResult> getArbitrationQueueStats({
    String? authToken,
  }) async {
    try {
      final request = proto.GetArbitrationQueueStatsRequest();

      final metadata = <String, String>{};
      if (authToken != null) {
        metadata['authorization'] = authToken;
      }

      final client = _getClient();
      final response = await client.getArbitrationQueueStats(
        request,
        options: CallOptions(
          metadata: metadata,
          timeout: const Duration(seconds: 30),
        ),
      );

      return ArbitrationQueueStatsResult.fromProto(response.stats);
    } on GrpcError catch (e) {
      return ArbitrationQueueStatsResult(
        success: false,
      );
    } catch (e) {
      return ArbitrationQueueStatsResult(
        success: false,
      );
    }
  }

  /// Close the gRPC connection
  Future<void> close() async {
    await _channel?.terminate();
    _channel = null;
    _client = null;
  }
}
