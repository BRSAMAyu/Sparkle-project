//
//  Generated code. Do not modify.
//  source: agent_service_v2.proto
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

import 'agent_service_v2.pb.dart' as $1;

export 'agent_service_v2.pb.dart';

@$pb.GrpcServiceName('sparkle.agent.v2.AgentServiceV2')
class AgentServiceV2Client extends $grpc.Client {
  static final _$streamChat = $grpc.ClientMethod<$1.ChatRequestV2, $1.ChatResponseV2>(
      '/sparkle.agent.v2.AgentServiceV2/StreamChat',
      ($1.ChatRequestV2 value) => value.writeToBuffer(),
      ($core.List<$core.int> value) => $1.ChatResponseV2.fromBuffer(value));
  static final _$getUserProfile = $grpc.ClientMethod<$1.ProfileRequestV2, $1.ProfileResponseV2>(
      '/sparkle.agent.v2.AgentServiceV2/GetUserProfile',
      ($1.ProfileRequestV2 value) => value.writeToBuffer(),
      ($core.List<$core.int> value) => $1.ProfileResponseV2.fromBuffer(value));
  static final _$getWeeklyReport = $grpc.ClientMethod<$1.WeeklyReportRequest, $1.WeeklyReport>(
      '/sparkle.agent.v2.AgentServiceV2/GetWeeklyReport',
      ($1.WeeklyReportRequest value) => value.writeToBuffer(),
      ($core.List<$core.int> value) => $1.WeeklyReport.fromBuffer(value));

  AgentServiceV2Client($grpc.ClientChannel channel,
      {$grpc.CallOptions? options,
      $core.Iterable<$grpc.ClientInterceptor>? interceptors})
      : super(channel, options: options,
        interceptors: interceptors);

  $grpc.ResponseStream<$1.ChatResponseV2> streamChat($1.ChatRequestV2 request, {$grpc.CallOptions? options}) {
    return $createStreamingCall(_$streamChat, $async.Stream.fromIterable([request]), options: options);
  }

  $grpc.ResponseFuture<$1.ProfileResponseV2> getUserProfile($1.ProfileRequestV2 request, {$grpc.CallOptions? options}) {
    return $createUnaryCall(_$getUserProfile, request, options: options);
  }

  $grpc.ResponseFuture<$1.WeeklyReport> getWeeklyReport($1.WeeklyReportRequest request, {$grpc.CallOptions? options}) {
    return $createUnaryCall(_$getWeeklyReport, request, options: options);
  }
}

@$pb.GrpcServiceName('sparkle.agent.v2.AgentServiceV2')
abstract class AgentServiceV2ServiceBase extends $grpc.Service {
  $core.String get $name => 'sparkle.agent.v2.AgentServiceV2';

  AgentServiceV2ServiceBase() {
    $addMethod($grpc.ServiceMethod<$1.ChatRequestV2, $1.ChatResponseV2>(
        'StreamChat',
        streamChat_Pre,
        false,
        true,
        ($core.List<$core.int> value) => $1.ChatRequestV2.fromBuffer(value),
        ($1.ChatResponseV2 value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$1.ProfileRequestV2, $1.ProfileResponseV2>(
        'GetUserProfile',
        getUserProfile_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $1.ProfileRequestV2.fromBuffer(value),
        ($1.ProfileResponseV2 value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$1.WeeklyReportRequest, $1.WeeklyReport>(
        'GetWeeklyReport',
        getWeeklyReport_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $1.WeeklyReportRequest.fromBuffer(value),
        ($1.WeeklyReport value) => value.writeToBuffer()));
  }

  $async.Stream<$1.ChatResponseV2> streamChat_Pre($grpc.ServiceCall call, $async.Future<$1.ChatRequestV2> request) async* {
    yield* streamChat(call, await request);
  }

  $async.Future<$1.ProfileResponseV2> getUserProfile_Pre($grpc.ServiceCall call, $async.Future<$1.ProfileRequestV2> request) async {
    return getUserProfile(call, await request);
  }

  $async.Future<$1.WeeklyReport> getWeeklyReport_Pre($grpc.ServiceCall call, $async.Future<$1.WeeklyReportRequest> request) async {
    return getWeeklyReport(call, await request);
  }

  $async.Stream<$1.ChatResponseV2> streamChat($grpc.ServiceCall call, $1.ChatRequestV2 request);
  $async.Future<$1.ProfileResponseV2> getUserProfile($grpc.ServiceCall call, $1.ProfileRequestV2 request);
  $async.Future<$1.WeeklyReport> getWeeklyReport($grpc.ServiceCall call, $1.WeeklyReportRequest request);
}
