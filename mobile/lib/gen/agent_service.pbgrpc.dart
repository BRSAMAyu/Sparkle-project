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

import 'package:sparkle/gen/agent_service.pb.dart' as $0;

export 'agent_service.pb.dart';

/// AgentService defines the interface for the AI Agent Engine.
/// It handles complex reasoning, long-term memory retrieval, and tool orchestration.
@$pb.GrpcServiceName('agent.v1.AgentService')
class AgentServiceClient extends $grpc.Client {

  AgentServiceClient(super.channel, {super.options, super.interceptors});
  /// The hostname for this service.
  static const $core.String defaultHost = '';

  /// OAuth scopes needed for the client.
  static const $core.List<$core.String> oauthScopes = [
    '',
  ];

  /// StreamChat handles the bi-directional communication for AI chat.
  /// It supports streaming responses for a "typewriter" effect and tool execution flows.
  $grpc.ResponseStream<$0.ChatResponse> streamChat(
    $0.ChatRequest request, {
    $grpc.CallOptions? options,
  }) => $createStreamingCall(
        _$streamChat, $async.Stream.fromIterable([request]),
        options: options,);

  /// RetrieveMemory allows the gateway (or other services) to query the AI's long-term memory store (Vector DB).
  /// This is used for RAG (Retrieval-Augmented Generation) or context building.
  $grpc.ResponseFuture<$0.MemoryResult> retrieveMemory(
    $0.MemoryQuery request, {
    $grpc.CallOptions? options,
  }) => $createUnaryCall(_$retrieveMemory, request, options: options);

  /// GetUserProfile retrieves the user's profile data.
  $grpc.ResponseFuture<$0.UserProfile> getUserProfile(
    $0.ProfileRequest request, {
    $grpc.CallOptions? options,
  }) => $createUnaryCall(_$getUserProfile, request, options: options);

  /// GetWeeklyReport generates or retrieves a weekly summary for the user.
  $grpc.ResponseFuture<$0.WeeklyReport> getWeeklyReport(
    $0.WeeklyReportRequest request, {
    $grpc.CallOptions? options,
  }) => $createUnaryCall(_$getWeeklyReport, request, options: options);

  // method descriptors

  static final _$streamChat =
      $grpc.ClientMethod<$0.ChatRequest, $0.ChatResponse>(
          '/agent.v1.AgentService/StreamChat',
          ($0.ChatRequest value) => value.writeToBuffer(),
          $0.ChatResponse.fromBuffer,);
  static final _$retrieveMemory =
      $grpc.ClientMethod<$0.MemoryQuery, $0.MemoryResult>(
          '/agent.v1.AgentService/RetrieveMemory',
          ($0.MemoryQuery value) => value.writeToBuffer(),
          $0.MemoryResult.fromBuffer,);
  static final _$getUserProfile =
      $grpc.ClientMethod<$0.ProfileRequest, $0.UserProfile>(
          '/agent.v1.AgentService/GetUserProfile',
          ($0.ProfileRequest value) => value.writeToBuffer(),
          $0.UserProfile.fromBuffer,);
  static final _$getWeeklyReport =
      $grpc.ClientMethod<$0.WeeklyReportRequest, $0.WeeklyReport>(
          '/agent.v1.AgentService/GetWeeklyReport',
          ($0.WeeklyReportRequest value) => value.writeToBuffer(),
          $0.WeeklyReport.fromBuffer,);
}

@$pb.GrpcServiceName('agent.v1.AgentService')
abstract class AgentServiceBase extends $grpc.Service {

  AgentServiceBase() {
    $addMethod($grpc.ServiceMethod<$0.ChatRequest, $0.ChatResponse>(
        'StreamChat',
        streamChat_Pre,
        false,
        true,
        $0.ChatRequest.fromBuffer,
        ($0.ChatResponse value) => value.writeToBuffer(),),);
    $addMethod($grpc.ServiceMethod<$0.MemoryQuery, $0.MemoryResult>(
        'RetrieveMemory',
        retrieveMemory_Pre,
        false,
        false,
        $0.MemoryQuery.fromBuffer,
        ($0.MemoryResult value) => value.writeToBuffer(),),);
    $addMethod($grpc.ServiceMethod<$0.ProfileRequest, $0.UserProfile>(
        'GetUserProfile',
        getUserProfile_Pre,
        false,
        false,
        $0.ProfileRequest.fromBuffer,
        ($0.UserProfile value) => value.writeToBuffer(),),);
    $addMethod($grpc.ServiceMethod<$0.WeeklyReportRequest, $0.WeeklyReport>(
        'GetWeeklyReport',
        getWeeklyReport_Pre,
        false,
        false,
        $0.WeeklyReportRequest.fromBuffer,
        ($0.WeeklyReport value) => value.writeToBuffer(),),);
  }
  $core.String get $name => 'agent.v1.AgentService';

  $async.Stream<$0.ChatResponse> streamChat_Pre(
      $grpc.ServiceCall $call, $async.Future<$0.ChatRequest> $request,) async* {
    yield* streamChat($call, await $request);
  }

  $async.Stream<$0.ChatResponse> streamChat(
      $grpc.ServiceCall call, $0.ChatRequest request,);

  $async.Future<$0.MemoryResult> retrieveMemory_Pre(
      $grpc.ServiceCall $call, $async.Future<$0.MemoryQuery> $request,) async => retrieveMemory($call, await $request);

  $async.Future<$0.MemoryResult> retrieveMemory(
      $grpc.ServiceCall call, $0.MemoryQuery request,);

  $async.Future<$0.UserProfile> getUserProfile_Pre($grpc.ServiceCall $call,
      $async.Future<$0.ProfileRequest> $request,) async => getUserProfile($call, await $request);

  $async.Future<$0.UserProfile> getUserProfile(
      $grpc.ServiceCall call, $0.ProfileRequest request,);

  $async.Future<$0.WeeklyReport> getWeeklyReport_Pre($grpc.ServiceCall $call,
      $async.Future<$0.WeeklyReportRequest> $request,) async => getWeeklyReport($call, await $request);

  $async.Future<$0.WeeklyReport> getWeeklyReport(
      $grpc.ServiceCall call, $0.WeeklyReportRequest request,);
}
