// This is a generated file - do not edit.
//
// Generated from agent_service_v2.proto.

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

import 'package:sparkle/gen/agent_service_v2.pb.dart' as $0;

export 'agent_service_v2.pb.dart';

@$pb.GrpcServiceName('sparkle.agent.v2.AgentServiceV2')
class AgentServiceV2Client extends $grpc.Client {

  AgentServiceV2Client(super.channel, {super.options, super.interceptors});
  /// The hostname for this service.
  static const $core.String defaultHost = '';

  /// OAuth scopes needed for the client.
  static const $core.List<$core.String> oauthScopes = [
    '',
  ];

  $grpc.ResponseStream<$0.ChatResponseV2> streamChat(
    $0.ChatRequestV2 request, {
    $grpc.CallOptions? options,
  }) => $createStreamingCall(
        _$streamChat, $async.Stream.fromIterable([request]),
        options: options,);

  $grpc.ResponseFuture<$0.ProfileResponseV2> getUserProfile(
    $0.ProfileRequestV2 request, {
    $grpc.CallOptions? options,
  }) => $createUnaryCall(_$getUserProfile, request, options: options);

  $grpc.ResponseFuture<$0.WeeklyReport> getWeeklyReport(
    $0.WeeklyReportRequest request, {
    $grpc.CallOptions? options,
  }) => $createUnaryCall(_$getWeeklyReport, request, options: options);

  // method descriptors

  static final _$streamChat =
      $grpc.ClientMethod<$0.ChatRequestV2, $0.ChatResponseV2>(
          '/sparkle.agent.v2.AgentServiceV2/StreamChat',
          ($0.ChatRequestV2 value) => value.writeToBuffer(),
          $0.ChatResponseV2.fromBuffer,);
  static final _$getUserProfile =
      $grpc.ClientMethod<$0.ProfileRequestV2, $0.ProfileResponseV2>(
          '/sparkle.agent.v2.AgentServiceV2/GetUserProfile',
          ($0.ProfileRequestV2 value) => value.writeToBuffer(),
          $0.ProfileResponseV2.fromBuffer,);
  static final _$getWeeklyReport =
      $grpc.ClientMethod<$0.WeeklyReportRequest, $0.WeeklyReport>(
          '/sparkle.agent.v2.AgentServiceV2/GetWeeklyReport',
          ($0.WeeklyReportRequest value) => value.writeToBuffer(),
          $0.WeeklyReport.fromBuffer,);
}

@$pb.GrpcServiceName('sparkle.agent.v2.AgentServiceV2')
abstract class AgentServiceV2ServiceBase extends $grpc.Service {

  AgentServiceV2ServiceBase() {
    $addMethod($grpc.ServiceMethod<$0.ChatRequestV2, $0.ChatResponseV2>(
        'StreamChat',
        streamChat_Pre,
        false,
        true,
        $0.ChatRequestV2.fromBuffer,
        ($0.ChatResponseV2 value) => value.writeToBuffer(),),);
    $addMethod($grpc.ServiceMethod<$0.ProfileRequestV2, $0.ProfileResponseV2>(
        'GetUserProfile',
        getUserProfile_Pre,
        false,
        false,
        $0.ProfileRequestV2.fromBuffer,
        ($0.ProfileResponseV2 value) => value.writeToBuffer(),),);
    $addMethod($grpc.ServiceMethod<$0.WeeklyReportRequest, $0.WeeklyReport>(
        'GetWeeklyReport',
        getWeeklyReport_Pre,
        false,
        false,
        $0.WeeklyReportRequest.fromBuffer,
        ($0.WeeklyReport value) => value.writeToBuffer(),),);
  }
  $core.String get $name => 'sparkle.agent.v2.AgentServiceV2';

  $async.Stream<$0.ChatResponseV2> streamChat_Pre($grpc.ServiceCall $call,
      $async.Future<$0.ChatRequestV2> $request,) async* {
    yield* streamChat($call, await $request);
  }

  $async.Stream<$0.ChatResponseV2> streamChat(
      $grpc.ServiceCall call, $0.ChatRequestV2 request,);

  $async.Future<$0.ProfileResponseV2> getUserProfile_Pre(
      $grpc.ServiceCall $call,
      $async.Future<$0.ProfileRequestV2> $request,) async => getUserProfile($call, await $request);

  $async.Future<$0.ProfileResponseV2> getUserProfile(
      $grpc.ServiceCall call, $0.ProfileRequestV2 request,);

  $async.Future<$0.WeeklyReport> getWeeklyReport_Pre($grpc.ServiceCall $call,
      $async.Future<$0.WeeklyReportRequest> $request,) async => getWeeklyReport($call, await $request);

  $async.Future<$0.WeeklyReport> getWeeklyReport(
      $grpc.ServiceCall call, $0.WeeklyReportRequest request,);
}
