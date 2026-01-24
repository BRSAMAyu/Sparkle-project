//
//  Generated code. Do not modify.
//  source: galaxy_service.proto
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

import 'package:sparkle/gen/galaxy_service.pb.dart' as $3;

export 'galaxy_service.pb.dart';

@$pb.GrpcServiceName('galaxy.v1.GalaxyService')
class GalaxyServiceClient extends $grpc.Client {

  GalaxyServiceClient($grpc.ClientChannel channel,
      {$grpc.CallOptions? options,
      $core.Iterable<$grpc.ClientInterceptor>? interceptors})
      : super(channel, options: options,
        interceptors: interceptors);
  static final _$updateNodeMastery = $grpc.ClientMethod<$3.UpdateNodeMasteryRequest, $3.UpdateNodeMasteryResponse>(
      '/galaxy.v1.GalaxyService/UpdateNodeMastery',
      ($3.UpdateNodeMasteryRequest value) => value.writeToBuffer(),
      ($core.List<$core.int> value) => $3.UpdateNodeMasteryResponse.fromBuffer(value),);
  static final _$syncCollaborativeGalaxy = $grpc.ClientMethod<$3.SyncCollaborativeGalaxyRequest, $3.SyncCollaborativeGalaxyResponse>(
      '/galaxy.v1.GalaxyService/SyncCollaborativeGalaxy',
      ($3.SyncCollaborativeGalaxyRequest value) => value.writeToBuffer(),
      ($core.List<$core.int> value) => $3.SyncCollaborativeGalaxyResponse.fromBuffer(value),);

  $grpc.ResponseFuture<$3.UpdateNodeMasteryResponse> updateNodeMastery($3.UpdateNodeMasteryRequest request, {$grpc.CallOptions? options}) => $createUnaryCall(_$updateNodeMastery, request, options: options);

  $grpc.ResponseFuture<$3.SyncCollaborativeGalaxyResponse> syncCollaborativeGalaxy($3.SyncCollaborativeGalaxyRequest request, {$grpc.CallOptions? options}) => $createUnaryCall(_$syncCollaborativeGalaxy, request, options: options);
}

@$pb.GrpcServiceName('galaxy.v1.GalaxyService')
abstract class GalaxyServiceBase extends $grpc.Service {

  GalaxyServiceBase() {
    $addMethod($grpc.ServiceMethod<$3.UpdateNodeMasteryRequest, $3.UpdateNodeMasteryResponse>(
        'UpdateNodeMastery',
        updateNodeMastery_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $3.UpdateNodeMasteryRequest.fromBuffer(value),
        ($3.UpdateNodeMasteryResponse value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$3.SyncCollaborativeGalaxyRequest, $3.SyncCollaborativeGalaxyResponse>(
        'SyncCollaborativeGalaxy',
        syncCollaborativeGalaxy_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $3.SyncCollaborativeGalaxyRequest.fromBuffer(value),
        ($3.SyncCollaborativeGalaxyResponse value) => value.writeToBuffer()));
  }
  $core.String get $name => 'galaxy.v1.GalaxyService';

  $async.Future<$3.UpdateNodeMasteryResponse> updateNodeMastery_Pre($grpc.ServiceCall call, $async.Future<$3.UpdateNodeMasteryRequest> request) async => updateNodeMastery(call, await request);

  $async.Future<$3.SyncCollaborativeGalaxyResponse> syncCollaborativeGalaxy_Pre($grpc.ServiceCall call, $async.Future<$3.SyncCollaborativeGalaxyRequest> request) async => syncCollaborativeGalaxy(call, await request);

  $async.Future<$3.UpdateNodeMasteryResponse> updateNodeMastery($grpc.ServiceCall call, $3.UpdateNodeMasteryRequest request);
  $async.Future<$3.SyncCollaborativeGalaxyResponse> syncCollaborativeGalaxy($grpc.ServiceCall call, $3.SyncCollaborativeGalaxyRequest request);
}
