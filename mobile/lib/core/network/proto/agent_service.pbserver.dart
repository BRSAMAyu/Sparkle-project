//
//  Generated code. Do not modify.
//  source: agent_service.proto
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

import 'agent_service.pb.dart' as $3;
import 'agent_service.pbjson.dart';

export 'agent_service.pb.dart';

abstract class AgentServiceBase extends $pb.GeneratedService {
  $async.Future<$3.ChatResponse> streamChat($pb.ServerContext ctx, $3.ChatRequest request);
  $async.Future<$3.MemoryResult> retrieveMemory($pb.ServerContext ctx, $3.MemoryQuery request);
  $async.Future<$3.UserProfile> getUserProfile($pb.ServerContext ctx, $3.ProfileRequest request);
  $async.Future<$3.WeeklyReport> getWeeklyReport($pb.ServerContext ctx, $3.WeeklyReportRequest request);

  $pb.GeneratedMessage createRequest($core.String methodName) {
    switch (methodName) {
      case 'StreamChat': return $3.ChatRequest();
      case 'RetrieveMemory': return $3.MemoryQuery();
      case 'GetUserProfile': return $3.ProfileRequest();
      case 'GetWeeklyReport': return $3.WeeklyReportRequest();
      default: throw $core.ArgumentError('Unknown method: $methodName');
    }
  }

  $async.Future<$pb.GeneratedMessage> handleCall($pb.ServerContext ctx, $core.String methodName, $pb.GeneratedMessage request) {
    switch (methodName) {
      case 'StreamChat': return this.streamChat(ctx, request as $3.ChatRequest);
      case 'RetrieveMemory': return this.retrieveMemory(ctx, request as $3.MemoryQuery);
      case 'GetUserProfile': return this.getUserProfile(ctx, request as $3.ProfileRequest);
      case 'GetWeeklyReport': return this.getWeeklyReport(ctx, request as $3.WeeklyReportRequest);
      default: throw $core.ArgumentError('Unknown method: $methodName');
    }
  }

  $core.Map<$core.String, $core.dynamic> get $json => AgentServiceBase$json;
  $core.Map<$core.String, $core.Map<$core.String, $core.dynamic>> get $messageJson => AgentServiceBase$messageJson;
}

