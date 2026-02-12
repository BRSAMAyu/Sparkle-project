// This is a generated file - do not edit.
//
// Generated from agent_service.proto.

// @dart = 3.3

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names
// ignore_for_file: curly_braces_in_flow_control_structures
// ignore_for_file: deprecated_member_use_from_same_package, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_relative_imports

import 'dart:async' as $async;
import 'dart:core' as $core;

import 'package:grpc/service_api.dart' as $grpc;
import 'package:protobuf/protobuf.dart' as $pb;

import 'agent_service.pb.dart' as $0;

export 'agent_service.pb.dart';

/// AgentService defines the interface for the AI Agent Engine.
/// It handles complex reasoning, long-term memory retrieval, and tool orchestration.
@$pb.GrpcServiceName('agent.v1.AgentService')
class AgentServiceClient extends $grpc.Client {
  /// The hostname for this service.
  static const $core.String defaultHost = '';

  /// OAuth scopes needed for the client.
  static const $core.List<$core.String> oauthScopes = [
    '',
  ];

  AgentServiceClient(super.channel, {super.options, super.interceptors});

  /// StreamChat handles the bi-directional communication for AI chat.
  /// It supports streaming responses for a "typewriter" effect and tool execution flows.
  $grpc.ResponseStream<$0.ChatResponse> streamChat(
    $0.ChatRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createStreamingCall(
        _$streamChat, $async.Stream.fromIterable([request]),
        options: options);
  }

  /// RetrieveMemory allows the gateway (or other services) to query the AI's long-term memory store (Vector DB).
  /// This is used for RAG (Retrieval-Augmented Generation) or context building.
  $grpc.ResponseFuture<$0.MemoryResult> retrieveMemory(
    $0.MemoryQuery request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$retrieveMemory, request, options: options);
  }

  /// GetUserProfile retrieves the user's profile data.
  $grpc.ResponseFuture<$0.UserProfile> getUserProfile(
    $0.ProfileRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$getUserProfile, request, options: options);
  }

  /// GetWeeklyReport generates or retrieves a weekly summary for the user.
  $grpc.ResponseFuture<$0.WeeklyReport> getWeeklyReport(
    $0.WeeklyReportRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$getWeeklyReport, request, options: options);
  }

  /// SubmitResponseFeedback records user feedback for an AI response.
  $grpc.ResponseFuture<$0.ResponseFeedbackResponse> submitResponseFeedback(
    $0.ResponseFeedbackRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$submitResponseFeedback, request,
        options: options);
  }

  /// SubmitPlanReview submits user feedback for a plan review.
  $grpc.ResponseFuture<$0.PlanReviewResponse> submitPlanReview(
    $0.PlanReviewRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$submitPlanReview, request, options: options);
  }

  /// SubmitContentReviewFeedback submits user feedback for a content review (Phase 2c).
  $grpc.ResponseFuture<$0.ContentReviewFeedbackResponse>
      submitContentReviewFeedback(
    $0.ContentReviewFeedbackRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$submitContentReviewFeedback, request,
        options: options);
  }

  /// Phase 2e: Review Override & Appeal
  /// SubmitReviewOverride allows user to override a review decision
  $grpc.ResponseFuture<$0.ReviewOverrideResponse> submitReviewOverride(
    $0.ReviewOverrideRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$submitReviewOverride, request, options: options);
  }

  /// SubmitReviewAppeal submits an appeal against a review
  $grpc.ResponseFuture<$0.ReviewAppealResponse> submitReviewAppeal(
    $0.ReviewAppealRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$submitReviewAppeal, request, options: options);
  }

  /// GetAppealStatus retrieves the status of an appeal
  $grpc.ResponseFuture<$0.AppealStatusResponse> getAppealStatus(
    $0.AppealStatusRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$getAppealStatus, request, options: options);
  }

  /// Phase 2f: Review Feedback & Regeneration
  /// SubmitReviewFeedback allows user to rate and provide feedback on reviews
  $grpc.ResponseFuture<$0.ReviewFeedbackResponse> submitReviewFeedback(
    $0.ReviewFeedbackRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$submitReviewFeedback, request, options: options);
  }

  /// RequestRegeneration requests content regeneration based on feedback
  $grpc.ResponseFuture<$0.RegenerationResponse> requestRegeneration(
    $0.RegenerationRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$requestRegeneration, request, options: options);
  }

  /// GetFeedbackStatistics retrieves feedback statistics
  $grpc.ResponseFuture<$0.FeedbackStatisticsResponse> getFeedbackStatistics(
    $0.FeedbackStatisticsRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$getFeedbackStatistics, request, options: options);
  }

  /// Phase 2g: Arbitration System
  /// GetArbitrationQueue retrieves pending arbitration cases for admins
  $grpc.ResponseFuture<$0.GetArbitrationQueueResponse> getArbitrationQueue(
    $0.GetArbitrationQueueRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$getArbitrationQueue, request, options: options);
  }

  /// AssignArbitrationCase assigns a case to an arbitrator
  $grpc.ResponseFuture<$0.AssignArbitrationCaseResponse> assignArbitrationCase(
    $0.AssignArbitrationCaseRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$assignArbitrationCase, request, options: options);
  }

  /// SubmitArbitrationDecision submits an arbitrator's decision
  $grpc.ResponseFuture<$0.SubmitArbitrationDecisionResponse>
      submitArbitrationDecision(
    $0.SubmitArbitrationDecisionRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$submitArbitrationDecision, request,
        options: options);
  }

  /// GetArbitrationQueueStats retrieves queue statistics
  $grpc.ResponseFuture<$0.GetArbitrationQueueStatsResponse>
      getArbitrationQueueStats(
    $0.GetArbitrationQueueStatsRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$getArbitrationQueueStats, request,
        options: options);
  }

  // method descriptors

  static final _$streamChat =
      $grpc.ClientMethod<$0.ChatRequest, $0.ChatResponse>(
          '/agent.v1.AgentService/StreamChat',
          ($0.ChatRequest value) => value.writeToBuffer(),
          $0.ChatResponse.fromBuffer);
  static final _$retrieveMemory =
      $grpc.ClientMethod<$0.MemoryQuery, $0.MemoryResult>(
          '/agent.v1.AgentService/RetrieveMemory',
          ($0.MemoryQuery value) => value.writeToBuffer(),
          $0.MemoryResult.fromBuffer);
  static final _$getUserProfile =
      $grpc.ClientMethod<$0.ProfileRequest, $0.UserProfile>(
          '/agent.v1.AgentService/GetUserProfile',
          ($0.ProfileRequest value) => value.writeToBuffer(),
          $0.UserProfile.fromBuffer);
  static final _$getWeeklyReport =
      $grpc.ClientMethod<$0.WeeklyReportRequest, $0.WeeklyReport>(
          '/agent.v1.AgentService/GetWeeklyReport',
          ($0.WeeklyReportRequest value) => value.writeToBuffer(),
          $0.WeeklyReport.fromBuffer);
  static final _$submitResponseFeedback = $grpc.ClientMethod<
          $0.ResponseFeedbackRequest, $0.ResponseFeedbackResponse>(
      '/agent.v1.AgentService/SubmitResponseFeedback',
      ($0.ResponseFeedbackRequest value) => value.writeToBuffer(),
      $0.ResponseFeedbackResponse.fromBuffer);
  static final _$submitPlanReview =
      $grpc.ClientMethod<$0.PlanReviewRequest, $0.PlanReviewResponse>(
          '/agent.v1.AgentService/SubmitPlanReview',
          ($0.PlanReviewRequest value) => value.writeToBuffer(),
          $0.PlanReviewResponse.fromBuffer);
  static final _$submitContentReviewFeedback = $grpc.ClientMethod<
          $0.ContentReviewFeedbackRequest, $0.ContentReviewFeedbackResponse>(
      '/agent.v1.AgentService/SubmitContentReviewFeedback',
      ($0.ContentReviewFeedbackRequest value) => value.writeToBuffer(),
      $0.ContentReviewFeedbackResponse.fromBuffer);
  static final _$submitReviewOverride =
      $grpc.ClientMethod<$0.ReviewOverrideRequest, $0.ReviewOverrideResponse>(
          '/agent.v1.AgentService/SubmitReviewOverride',
          ($0.ReviewOverrideRequest value) => value.writeToBuffer(),
          $0.ReviewOverrideResponse.fromBuffer);
  static final _$submitReviewAppeal =
      $grpc.ClientMethod<$0.ReviewAppealRequest, $0.ReviewAppealResponse>(
          '/agent.v1.AgentService/SubmitReviewAppeal',
          ($0.ReviewAppealRequest value) => value.writeToBuffer(),
          $0.ReviewAppealResponse.fromBuffer);
  static final _$getAppealStatus =
      $grpc.ClientMethod<$0.AppealStatusRequest, $0.AppealStatusResponse>(
          '/agent.v1.AgentService/GetAppealStatus',
          ($0.AppealStatusRequest value) => value.writeToBuffer(),
          $0.AppealStatusResponse.fromBuffer);
  static final _$submitReviewFeedback =
      $grpc.ClientMethod<$0.ReviewFeedbackRequest, $0.ReviewFeedbackResponse>(
          '/agent.v1.AgentService/SubmitReviewFeedback',
          ($0.ReviewFeedbackRequest value) => value.writeToBuffer(),
          $0.ReviewFeedbackResponse.fromBuffer);
  static final _$requestRegeneration =
      $grpc.ClientMethod<$0.RegenerationRequest, $0.RegenerationResponse>(
          '/agent.v1.AgentService/RequestRegeneration',
          ($0.RegenerationRequest value) => value.writeToBuffer(),
          $0.RegenerationResponse.fromBuffer);
  static final _$getFeedbackStatistics = $grpc.ClientMethod<
          $0.FeedbackStatisticsRequest, $0.FeedbackStatisticsResponse>(
      '/agent.v1.AgentService/GetFeedbackStatistics',
      ($0.FeedbackStatisticsRequest value) => value.writeToBuffer(),
      $0.FeedbackStatisticsResponse.fromBuffer);
  static final _$getArbitrationQueue = $grpc.ClientMethod<
          $0.GetArbitrationQueueRequest, $0.GetArbitrationQueueResponse>(
      '/agent.v1.AgentService/GetArbitrationQueue',
      ($0.GetArbitrationQueueRequest value) => value.writeToBuffer(),
      $0.GetArbitrationQueueResponse.fromBuffer);
  static final _$assignArbitrationCase = $grpc.ClientMethod<
          $0.AssignArbitrationCaseRequest, $0.AssignArbitrationCaseResponse>(
      '/agent.v1.AgentService/AssignArbitrationCase',
      ($0.AssignArbitrationCaseRequest value) => value.writeToBuffer(),
      $0.AssignArbitrationCaseResponse.fromBuffer);
  static final _$submitArbitrationDecision = $grpc.ClientMethod<
          $0.SubmitArbitrationDecisionRequest,
          $0.SubmitArbitrationDecisionResponse>(
      '/agent.v1.AgentService/SubmitArbitrationDecision',
      ($0.SubmitArbitrationDecisionRequest value) => value.writeToBuffer(),
      $0.SubmitArbitrationDecisionResponse.fromBuffer);
  static final _$getArbitrationQueueStats = $grpc.ClientMethod<
          $0.GetArbitrationQueueStatsRequest,
          $0.GetArbitrationQueueStatsResponse>(
      '/agent.v1.AgentService/GetArbitrationQueueStats',
      ($0.GetArbitrationQueueStatsRequest value) => value.writeToBuffer(),
      $0.GetArbitrationQueueStatsResponse.fromBuffer);
}

@$pb.GrpcServiceName('agent.v1.AgentService')
abstract class AgentServiceBase extends $grpc.Service {
  $core.String get $name => 'agent.v1.AgentService';

  AgentServiceBase() {
    $addMethod($grpc.ServiceMethod<$0.ChatRequest, $0.ChatResponse>(
        'StreamChat',
        streamChat_Pre,
        false,
        true,
        ($core.List<$core.int> value) => $0.ChatRequest.fromBuffer(value),
        ($0.ChatResponse value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.MemoryQuery, $0.MemoryResult>(
        'RetrieveMemory',
        retrieveMemory_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $0.MemoryQuery.fromBuffer(value),
        ($0.MemoryResult value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.ProfileRequest, $0.UserProfile>(
        'GetUserProfile',
        getUserProfile_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $0.ProfileRequest.fromBuffer(value),
        ($0.UserProfile value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.WeeklyReportRequest, $0.WeeklyReport>(
        'GetWeeklyReport',
        getWeeklyReport_Pre,
        false,
        false,
        ($core.List<$core.int> value) =>
            $0.WeeklyReportRequest.fromBuffer(value),
        ($0.WeeklyReport value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.ResponseFeedbackRequest,
            $0.ResponseFeedbackResponse>(
        'SubmitResponseFeedback',
        submitResponseFeedback_Pre,
        false,
        false,
        ($core.List<$core.int> value) =>
            $0.ResponseFeedbackRequest.fromBuffer(value),
        ($0.ResponseFeedbackResponse value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.PlanReviewRequest, $0.PlanReviewResponse>(
        'SubmitPlanReview',
        submitPlanReview_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $0.PlanReviewRequest.fromBuffer(value),
        ($0.PlanReviewResponse value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.ContentReviewFeedbackRequest,
            $0.ContentReviewFeedbackResponse>(
        'SubmitContentReviewFeedback',
        submitContentReviewFeedback_Pre,
        false,
        false,
        ($core.List<$core.int> value) =>
            $0.ContentReviewFeedbackRequest.fromBuffer(value),
        ($0.ContentReviewFeedbackResponse value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.ReviewOverrideRequest,
            $0.ReviewOverrideResponse>(
        'SubmitReviewOverride',
        submitReviewOverride_Pre,
        false,
        false,
        ($core.List<$core.int> value) =>
            $0.ReviewOverrideRequest.fromBuffer(value),
        ($0.ReviewOverrideResponse value) => value.writeToBuffer()));
    $addMethod(
        $grpc.ServiceMethod<$0.ReviewAppealRequest, $0.ReviewAppealResponse>(
            'SubmitReviewAppeal',
            submitReviewAppeal_Pre,
            false,
            false,
            ($core.List<$core.int> value) =>
                $0.ReviewAppealRequest.fromBuffer(value),
            ($0.ReviewAppealResponse value) => value.writeToBuffer()));
    $addMethod(
        $grpc.ServiceMethod<$0.AppealStatusRequest, $0.AppealStatusResponse>(
            'GetAppealStatus',
            getAppealStatus_Pre,
            false,
            false,
            ($core.List<$core.int> value) =>
                $0.AppealStatusRequest.fromBuffer(value),
            ($0.AppealStatusResponse value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.ReviewFeedbackRequest,
            $0.ReviewFeedbackResponse>(
        'SubmitReviewFeedback',
        submitReviewFeedback_Pre,
        false,
        false,
        ($core.List<$core.int> value) =>
            $0.ReviewFeedbackRequest.fromBuffer(value),
        ($0.ReviewFeedbackResponse value) => value.writeToBuffer()));
    $addMethod(
        $grpc.ServiceMethod<$0.RegenerationRequest, $0.RegenerationResponse>(
            'RequestRegeneration',
            requestRegeneration_Pre,
            false,
            false,
            ($core.List<$core.int> value) =>
                $0.RegenerationRequest.fromBuffer(value),
            ($0.RegenerationResponse value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.FeedbackStatisticsRequest,
            $0.FeedbackStatisticsResponse>(
        'GetFeedbackStatistics',
        getFeedbackStatistics_Pre,
        false,
        false,
        ($core.List<$core.int> value) =>
            $0.FeedbackStatisticsRequest.fromBuffer(value),
        ($0.FeedbackStatisticsResponse value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.GetArbitrationQueueRequest,
            $0.GetArbitrationQueueResponse>(
        'GetArbitrationQueue',
        getArbitrationQueue_Pre,
        false,
        false,
        ($core.List<$core.int> value) =>
            $0.GetArbitrationQueueRequest.fromBuffer(value),
        ($0.GetArbitrationQueueResponse value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.AssignArbitrationCaseRequest,
            $0.AssignArbitrationCaseResponse>(
        'AssignArbitrationCase',
        assignArbitrationCase_Pre,
        false,
        false,
        ($core.List<$core.int> value) =>
            $0.AssignArbitrationCaseRequest.fromBuffer(value),
        ($0.AssignArbitrationCaseResponse value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.SubmitArbitrationDecisionRequest,
            $0.SubmitArbitrationDecisionResponse>(
        'SubmitArbitrationDecision',
        submitArbitrationDecision_Pre,
        false,
        false,
        ($core.List<$core.int> value) =>
            $0.SubmitArbitrationDecisionRequest.fromBuffer(value),
        ($0.SubmitArbitrationDecisionResponse value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.GetArbitrationQueueStatsRequest,
            $0.GetArbitrationQueueStatsResponse>(
        'GetArbitrationQueueStats',
        getArbitrationQueueStats_Pre,
        false,
        false,
        ($core.List<$core.int> value) =>
            $0.GetArbitrationQueueStatsRequest.fromBuffer(value),
        ($0.GetArbitrationQueueStatsResponse value) => value.writeToBuffer()));
  }

  $async.Stream<$0.ChatResponse> streamChat_Pre(
      $grpc.ServiceCall $call, $async.Future<$0.ChatRequest> $request) async* {
    yield* streamChat($call, await $request);
  }

  $async.Stream<$0.ChatResponse> streamChat(
      $grpc.ServiceCall call, $0.ChatRequest request);

  $async.Future<$0.MemoryResult> retrieveMemory_Pre(
      $grpc.ServiceCall $call, $async.Future<$0.MemoryQuery> $request) async {
    return retrieveMemory($call, await $request);
  }

  $async.Future<$0.MemoryResult> retrieveMemory(
      $grpc.ServiceCall call, $0.MemoryQuery request);

  $async.Future<$0.UserProfile> getUserProfile_Pre($grpc.ServiceCall $call,
      $async.Future<$0.ProfileRequest> $request) async {
    return getUserProfile($call, await $request);
  }

  $async.Future<$0.UserProfile> getUserProfile(
      $grpc.ServiceCall call, $0.ProfileRequest request);

  $async.Future<$0.WeeklyReport> getWeeklyReport_Pre($grpc.ServiceCall $call,
      $async.Future<$0.WeeklyReportRequest> $request) async {
    return getWeeklyReport($call, await $request);
  }

  $async.Future<$0.WeeklyReport> getWeeklyReport(
      $grpc.ServiceCall call, $0.WeeklyReportRequest request);

  $async.Future<$0.ResponseFeedbackResponse> submitResponseFeedback_Pre(
      $grpc.ServiceCall $call,
      $async.Future<$0.ResponseFeedbackRequest> $request) async {
    return submitResponseFeedback($call, await $request);
  }

  $async.Future<$0.ResponseFeedbackResponse> submitResponseFeedback(
      $grpc.ServiceCall call, $0.ResponseFeedbackRequest request);

  $async.Future<$0.PlanReviewResponse> submitPlanReview_Pre(
      $grpc.ServiceCall $call,
      $async.Future<$0.PlanReviewRequest> $request) async {
    return submitPlanReview($call, await $request);
  }

  $async.Future<$0.PlanReviewResponse> submitPlanReview(
      $grpc.ServiceCall call, $0.PlanReviewRequest request);

  $async.Future<$0.ContentReviewFeedbackResponse>
      submitContentReviewFeedback_Pre($grpc.ServiceCall $call,
          $async.Future<$0.ContentReviewFeedbackRequest> $request) async {
    return submitContentReviewFeedback($call, await $request);
  }

  $async.Future<$0.ContentReviewFeedbackResponse> submitContentReviewFeedback(
      $grpc.ServiceCall call, $0.ContentReviewFeedbackRequest request);

  $async.Future<$0.ReviewOverrideResponse> submitReviewOverride_Pre(
      $grpc.ServiceCall $call,
      $async.Future<$0.ReviewOverrideRequest> $request) async {
    return submitReviewOverride($call, await $request);
  }

  $async.Future<$0.ReviewOverrideResponse> submitReviewOverride(
      $grpc.ServiceCall call, $0.ReviewOverrideRequest request);

  $async.Future<$0.ReviewAppealResponse> submitReviewAppeal_Pre(
      $grpc.ServiceCall $call,
      $async.Future<$0.ReviewAppealRequest> $request) async {
    return submitReviewAppeal($call, await $request);
  }

  $async.Future<$0.ReviewAppealResponse> submitReviewAppeal(
      $grpc.ServiceCall call, $0.ReviewAppealRequest request);

  $async.Future<$0.AppealStatusResponse> getAppealStatus_Pre(
      $grpc.ServiceCall $call,
      $async.Future<$0.AppealStatusRequest> $request) async {
    return getAppealStatus($call, await $request);
  }

  $async.Future<$0.AppealStatusResponse> getAppealStatus(
      $grpc.ServiceCall call, $0.AppealStatusRequest request);

  $async.Future<$0.ReviewFeedbackResponse> submitReviewFeedback_Pre(
      $grpc.ServiceCall $call,
      $async.Future<$0.ReviewFeedbackRequest> $request) async {
    return submitReviewFeedback($call, await $request);
  }

  $async.Future<$0.ReviewFeedbackResponse> submitReviewFeedback(
      $grpc.ServiceCall call, $0.ReviewFeedbackRequest request);

  $async.Future<$0.RegenerationResponse> requestRegeneration_Pre(
      $grpc.ServiceCall $call,
      $async.Future<$0.RegenerationRequest> $request) async {
    return requestRegeneration($call, await $request);
  }

  $async.Future<$0.RegenerationResponse> requestRegeneration(
      $grpc.ServiceCall call, $0.RegenerationRequest request);

  $async.Future<$0.FeedbackStatisticsResponse> getFeedbackStatistics_Pre(
      $grpc.ServiceCall $call,
      $async.Future<$0.FeedbackStatisticsRequest> $request) async {
    return getFeedbackStatistics($call, await $request);
  }

  $async.Future<$0.FeedbackStatisticsResponse> getFeedbackStatistics(
      $grpc.ServiceCall call, $0.FeedbackStatisticsRequest request);

  $async.Future<$0.GetArbitrationQueueResponse> getArbitrationQueue_Pre(
      $grpc.ServiceCall $call,
      $async.Future<$0.GetArbitrationQueueRequest> $request) async {
    return getArbitrationQueue($call, await $request);
  }

  $async.Future<$0.GetArbitrationQueueResponse> getArbitrationQueue(
      $grpc.ServiceCall call, $0.GetArbitrationQueueRequest request);

  $async.Future<$0.AssignArbitrationCaseResponse> assignArbitrationCase_Pre(
      $grpc.ServiceCall $call,
      $async.Future<$0.AssignArbitrationCaseRequest> $request) async {
    return assignArbitrationCase($call, await $request);
  }

  $async.Future<$0.AssignArbitrationCaseResponse> assignArbitrationCase(
      $grpc.ServiceCall call, $0.AssignArbitrationCaseRequest request);

  $async.Future<$0.SubmitArbitrationDecisionResponse>
      submitArbitrationDecision_Pre($grpc.ServiceCall $call,
          $async.Future<$0.SubmitArbitrationDecisionRequest> $request) async {
    return submitArbitrationDecision($call, await $request);
  }

  $async.Future<$0.SubmitArbitrationDecisionResponse> submitArbitrationDecision(
      $grpc.ServiceCall call, $0.SubmitArbitrationDecisionRequest request);

  $async.Future<$0.GetArbitrationQueueStatsResponse>
      getArbitrationQueueStats_Pre($grpc.ServiceCall $call,
          $async.Future<$0.GetArbitrationQueueStatsRequest> $request) async {
    return getArbitrationQueueStats($call, await $request);
  }

  $async.Future<$0.GetArbitrationQueueStatsResponse> getArbitrationQueueStats(
      $grpc.ServiceCall call, $0.GetArbitrationQueueStatsRequest request);
}
