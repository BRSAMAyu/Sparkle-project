// This is a generated file - do not edit.
//
// Generated from galaxy_service.proto.

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

import 'galaxy_service.pb.dart' as $0;

export 'galaxy_service.pb.dart';

/// GalaxyService defines the interface for Knowledge Galaxy operations.
@$pb.GrpcServiceName('galaxy.v1.GalaxyService')
class GalaxyServiceClient extends $grpc.Client {
  /// The hostname for this service.
  static const $core.String defaultHost = '';

  /// OAuth scopes needed for the client.
  static const $core.List<$core.String> oauthScopes = [
    '',
  ];

  GalaxyServiceClient(super.channel, {super.options, super.interceptors});

  /// UpdateNodeMastery updates the mastery level of a node for a user.
  $grpc.ResponseFuture<$0.UpdateNodeMasteryResponse> updateNodeMastery(
    $0.UpdateNodeMasteryRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$updateNodeMastery, request, options: options);
  }

  /// SyncCollaborativeGalaxy syncs CRDT updates for a collaborative galaxy.
  $grpc.ResponseFuture<$0.SyncCollaborativeGalaxyResponse>
      syncCollaborativeGalaxy(
    $0.SyncCollaborativeGalaxyRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$syncCollaborativeGalaxy, request,
        options: options);
  }

  // method descriptors

  static final _$updateNodeMastery = $grpc.ClientMethod<
          $0.UpdateNodeMasteryRequest, $0.UpdateNodeMasteryResponse>(
      '/galaxy.v1.GalaxyService/UpdateNodeMastery',
      ($0.UpdateNodeMasteryRequest value) => value.writeToBuffer(),
      $0.UpdateNodeMasteryResponse.fromBuffer);
  static final _$syncCollaborativeGalaxy = $grpc.ClientMethod<
          $0.SyncCollaborativeGalaxyRequest,
          $0.SyncCollaborativeGalaxyResponse>(
      '/galaxy.v1.GalaxyService/SyncCollaborativeGalaxy',
      ($0.SyncCollaborativeGalaxyRequest value) => value.writeToBuffer(),
      $0.SyncCollaborativeGalaxyResponse.fromBuffer);
}

@$pb.GrpcServiceName('galaxy.v1.GalaxyService')
abstract class GalaxyServiceBase extends $grpc.Service {
  $core.String get $name => 'galaxy.v1.GalaxyService';

  GalaxyServiceBase() {
    $addMethod($grpc.ServiceMethod<$0.UpdateNodeMasteryRequest,
            $0.UpdateNodeMasteryResponse>(
        'UpdateNodeMastery',
        updateNodeMastery_Pre,
        false,
        false,
        ($core.List<$core.int> value) =>
            $0.UpdateNodeMasteryRequest.fromBuffer(value),
        ($0.UpdateNodeMasteryResponse value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.SyncCollaborativeGalaxyRequest,
            $0.SyncCollaborativeGalaxyResponse>(
        'SyncCollaborativeGalaxy',
        syncCollaborativeGalaxy_Pre,
        false,
        false,
        ($core.List<$core.int> value) =>
            $0.SyncCollaborativeGalaxyRequest.fromBuffer(value),
        ($0.SyncCollaborativeGalaxyResponse value) => value.writeToBuffer()));
  }

  $async.Future<$0.UpdateNodeMasteryResponse> updateNodeMastery_Pre(
      $grpc.ServiceCall $call,
      $async.Future<$0.UpdateNodeMasteryRequest> $request) async {
    return updateNodeMastery($call, await $request);
  }

  $async.Future<$0.UpdateNodeMasteryResponse> updateNodeMastery(
      $grpc.ServiceCall call, $0.UpdateNodeMasteryRequest request);

  $async.Future<$0.SyncCollaborativeGalaxyResponse> syncCollaborativeGalaxy_Pre(
      $grpc.ServiceCall $call,
      $async.Future<$0.SyncCollaborativeGalaxyRequest> $request) async {
    return syncCollaborativeGalaxy($call, await $request);
  }

  $async.Future<$0.SyncCollaborativeGalaxyResponse> syncCollaborativeGalaxy(
      $grpc.ServiceCall call, $0.SyncCollaborativeGalaxyRequest request);
}
