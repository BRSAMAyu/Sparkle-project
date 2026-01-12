//
//  Generated code. Do not modify.
//  source: agent_service_v2.proto
//
// @dart = 2.12

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names
// ignore_for_file: deprecated_member_use_from_same_package, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_final_fields
// ignore_for_file: unnecessary_import, unnecessary_this, unused_import

import 'dart:async' as $async;
import 'dart:core' as $core;

import 'package:protobuf/protobuf.dart' as $pb;

import 'agent_service_v2.pb.dart' as $0;
import 'agent_service_v2.pbjson.dart';

export 'agent_service_v2.pb.dart';

abstract class AgentServiceV2ServiceBase extends $pb.GeneratedService {
  $async.Future<$0.ChatResponseV2> streamChat($pb.ServerContext ctx, $0.ChatRequestV2 request);
  $async.Future<$0.ProfileResponseV2> getUserProfile($pb.ServerContext ctx, $0.ProfileRequestV2 request);
  $async.Future<$0.WeeklyReport> getWeeklyReport($pb.ServerContext ctx, $0.WeeklyReportRequest request);

  $pb.GeneratedMessage createRequest($core.String methodName) {
    switch (methodName) {
      case 'StreamChat': return $0.ChatRequestV2();
      case 'GetUserProfile': return $0.ProfileRequestV2();
      case 'GetWeeklyReport': return $0.WeeklyReportRequest();
      default: throw $core.ArgumentError('Unknown method: $methodName');
    }
  }

  $async.Future<$pb.GeneratedMessage> handleCall($pb.ServerContext ctx, $core.String methodName, $pb.GeneratedMessage request) {
    switch (methodName) {
      case 'StreamChat': return this.streamChat(ctx, request as $0.ChatRequestV2);
      case 'GetUserProfile': return this.getUserProfile(ctx, request as $0.ProfileRequestV2);
      case 'GetWeeklyReport': return this.getWeeklyReport(ctx, request as $0.WeeklyReportRequest);
      default: throw $core.ArgumentError('Unknown method: $methodName');
    }
  }

  $core.Map<$core.String, $core.dynamic> get $json => AgentServiceV2ServiceBase$json;
  $core.Map<$core.String, $core.Map<$core.String, $core.dynamic>> get $messageJson => AgentServiceV2ServiceBase$messageJson;
}

