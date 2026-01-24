//
//  Generated code. Do not modify.
//  source: agent_service.proto
//
// @dart = 2.12

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_final_fields
// ignore_for_file: unnecessary_import, unnecessary_this, unused_import

import 'dart:async' as $async;
import 'dart:core' as $core;

import 'package:grpc/service_api.dart' as $grpc;
import 'package:protobuf/protobuf.dart' as $pb;

import 'package:sparkle/gen/agent_service.pb.dart' as $0;

export 'agent_service.pb.dart';

@$pb.GrpcServiceName('agent.v1.AgentService')
class AgentServiceClient extends $grpc.Client {

  AgentServiceClient($grpc.ClientChannel channel,
      {$grpc.CallOptions? options,
      $core.Iterable<$grpc.ClientInterceptor>? interceptors})
      : super(channel, options: options,
        interceptors: interceptors);
  static final _$streamChat = $grpc.ClientMethod<$0.ChatRequest, $0.ChatResponse>(
      '/agent.v1.AgentService/StreamChat',
      ($0.ChatRequest value) => value.writeToBuffer(),
      ($core.List<$core.int> value) => $0.ChatResponse.fromBuffer(value),);
  static final _$retrieveMemory = $grpc.ClientMethod<$0.MemoryQuery, $0.MemoryResult>(
      '/agent.v1.AgentService/RetrieveMemory',
      ($0.MemoryQuery value) => value.writeToBuffer(),
      ($core.List<$core.int> value) => $0.MemoryResult.fromBuffer(value),);
  static final _$getUserProfile = $grpc.ClientMethod<$0.ProfileRequest, $0.UserProfile>(
      '/agent.v1.AgentService/GetUserProfile',
      ($0.ProfileRequest value) => value.writeToBuffer(),
      ($core.List<$core.int> value) => $0.UserProfile.fromBuffer(value),);
  static final _$getWeeklyReport = $grpc.ClientMethod<$0.WeeklyReportRequest, $0.WeeklyReport>(
      '/agent.v1.AgentService/GetWeeklyReport',
      ($0.WeeklyReportRequest value) => value.writeToBuffer(),
      ($core.List<$core.int> value) => $0.WeeklyReport.fromBuffer(value),);
  static final _$submitResponseFeedback = $grpc.ClientMethod<$0.ResponseFeedbackRequest, $0.ResponseFeedbackResponse>(
      '/agent.v1.AgentService/SubmitResponseFeedback',
      ($0.ResponseFeedbackRequest value) => value.writeToBuffer(),
      ($core.List<$core.int> value) => $0.ResponseFeedbackResponse.fromBuffer(value),);

  $grpc.ResponseStream<$0.ChatResponse> streamChat($0.ChatRequest request, {$grpc.CallOptions? options}) => $createStreamingCall(_$streamChat, $async.Stream.fromIterable([request]), options: options);

  $grpc.ResponseFuture<$0.MemoryResult> retrieveMemory($0.MemoryQuery request, {$grpc.CallOptions? options}) => $createUnaryCall(_$retrieveMemory, request, options: options);

  $grpc.ResponseFuture<$0.UserProfile> getUserProfile($0.ProfileRequest request, {$grpc.CallOptions? options}) => $createUnaryCall(_$getUserProfile, request, options: options);

  $grpc.ResponseFuture<$0.WeeklyReport> getWeeklyReport($0.WeeklyReportRequest request, {$grpc.CallOptions? options}) => $createUnaryCall(_$getWeeklyReport, request, options: options);

  $grpc.ResponseFuture<$0.ResponseFeedbackResponse> submitResponseFeedback($0.ResponseFeedbackRequest request, {$grpc.CallOptions? options}) => $createUnaryCall(_$submitResponseFeedback, request, options: options);
}

@$pb.GrpcServiceName('agent.v1.AgentService')
abstract class AgentServiceBase extends $grpc.Service {

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
        ($core.List<$core.int> value) => $0.WeeklyReportRequest.fromBuffer(value),
        ($0.WeeklyReport value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.ResponseFeedbackRequest, $0.ResponseFeedbackResponse>(
        'SubmitResponseFeedback',
        submitResponseFeedback_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $0.ResponseFeedbackRequest.fromBuffer(value),
        ($0.ResponseFeedbackResponse value) => value.writeToBuffer()));
  }
  $core.String get $name => 'agent.v1.AgentService';

  $async.Stream<$0.ChatResponse> streamChat_Pre($grpc.ServiceCall call, $async.Future<$0.ChatRequest> request) async* {
    yield* streamChat(call, await request);
  }

  $async.Future<$0.MemoryResult> retrieveMemory_Pre($grpc.ServiceCall call, $async.Future<$0.MemoryQuery> request) async => retrieveMemory(call, await request);

  $async.Future<$0.UserProfile> getUserProfile_Pre($grpc.ServiceCall call, $async.Future<$0.ProfileRequest> request) async => getUserProfile(call, await request);

  $async.Future<$0.WeeklyReport> getWeeklyReport_Pre($grpc.ServiceCall call, $async.Future<$0.WeeklyReportRequest> request) async => getWeeklyReport(call, await request);

  $async.Future<$0.ResponseFeedbackResponse> submitResponseFeedback_Pre($grpc.ServiceCall call, $async.Future<$0.ResponseFeedbackRequest> request) async => submitResponseFeedback(call, await request);

  $async.Stream<$0.ChatResponse> streamChat($grpc.ServiceCall call, $0.ChatRequest request);
  $async.Future<$0.MemoryResult> retrieveMemory($grpc.ServiceCall call, $0.MemoryQuery request);
  $async.Future<$0.UserProfile> getUserProfile($grpc.ServiceCall call, $0.ProfileRequest request);
  $async.Future<$0.WeeklyReport> getWeeklyReport($grpc.ServiceCall call, $0.WeeklyReportRequest request);
  $async.Future<$0.ResponseFeedbackResponse> submitResponseFeedback($grpc.ServiceCall call, $0.ResponseFeedbackRequest request);
}
