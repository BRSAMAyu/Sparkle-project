import 'package:grpc/grpc.dart';
import 'package:sparkle/core/constants/api_constants.dart';
import 'package:sparkle/gen/agent_service.pbgrpc.dart'
    as proto;

/// Plan review decision enum matching the proto definition
enum UserReviewDecision {
  approve,
  reject,
  modify,
  acknowledge,
}

/// Extension to convert app enum to proto enum
extension UserReviewDecisionX on UserReviewDecision {
  proto.PlanReviewDecision toProto() {
    switch (this) {
      case UserReviewDecision.approve:
        return proto.PlanReviewDecision.APPROVE;
      case UserReviewDecision.reject:
        return proto.PlanReviewDecision.REJECT;
      case UserReviewDecision.modify:
        return proto.PlanReviewDecision.MODIFY;
      case UserReviewDecision.acknowledge:
        return proto.PlanReviewDecision.ACKNOWLEDGE;
    }
  }
}

/// Result of a plan review submission
class PlanReviewSubmitResult {
  const PlanReviewSubmitResult({
    required this.success,
    this.message,
    this.reviewId,
    this.updatedPlanId,
  });

  final bool success;
  final String? message;
  final String? reviewId;
  final String? updatedPlanId;
}

/// Plan Review gRPC Service
///
/// Handles submission of user feedback on plan reviews via gRPC.
/// This service communicates directly with the Python backend gRPC server.
class PlanReviewGrpcService {
  proto.AgentServiceClient? _client;
  ClientChannel? _channel;

  /// Get or create the gRPC client
  proto.AgentServiceClient _getClient() {
    _channel ??= ClientChannel(
      ApiConstants.grpcHost,
      port: ApiConstants.grpcPort,
      options: const ChannelOptions(
        credentials: ChannelCredentials.insecure(),
        // Add timeout and keep-alive settings
        idleTimeout: Duration(minutes: 5),
      ),
    );

    _client ??= proto.AgentServiceClient(_channel!);

    return _client!;
  }

  /// Submit user feedback for a plan review
  ///
  /// Parameters:
  /// - [userId]: The user ID
  /// - [planId]: The plan ID being reviewed
  /// - [reviewId]: The review ID
  /// - [decision]: User's decision on the review
  /// - [userComment]: Optional comment from the user
  /// - [authToken]: Optional authorization token
  /// - [meta]: Optional metadata
  ///
  /// Returns a [PlanReviewSubmitResult] with the outcome
  Future<PlanReviewSubmitResult> submitReview({
    required String userId,
    required String planId,
    required String reviewId,
    required UserReviewDecision decision,
    String? userComment,
    String? authToken,
    Map<String, String>? meta,
  }) async {
    try {
      // Create the request
      final request = proto.PlanReviewRequest()
        ..userId = userId
        ..planId = planId
        ..reviewId = reviewId
        ..decision = decision.toProto()
        ..userComment = userComment ?? ''
        ..traceId = _generateTraceId();

      // Add metadata if provided
      if (meta != null) {
        request.meta.addAll(meta);
      }

      // Build call options with metadata
      final metadata = <String, String>{
        'user-id': userId,
      };
      if (authToken != null) {
        metadata['authorization'] = authToken;
      }

      // Make the gRPC call
      final client = _getClient();
      final response = await client.submitPlanReview(
        request,
        options: CallOptions(
          metadata: metadata,
          timeout: const Duration(seconds: 30),
        ),
      );

      return PlanReviewSubmitResult(
        success: response.success,
        message: response.message.isEmpty ? null : response.message,
        reviewId: response.reviewId.isEmpty ? null : response.reviewId,
        updatedPlanId:
            response.updatedPlanId.isEmpty ? null : response.updatedPlanId,
      );
    } on GrpcError catch (e) {
      return PlanReviewSubmitResult(
        success: false,
        message: 'gRPC error: ${e.message ?? e.toString()}',
      );
    } catch (e) {
      return PlanReviewSubmitResult(
        success: false,
        message: 'Error: ${e.toString()}',
      );
    }
  }

  /// Close the gRPC connection
  Future<void> close() async {
    await _channel?.terminate();
    _channel = null;
    _client = null;
  }

  String _generateTraceId() {
    final timestamp = DateTime.now().millisecondsSinceEpoch;
    final random = (timestamp * 1000 + (timestamp % 1000)).toRadixString(16);
    return 'trace-$random';
  }
}
