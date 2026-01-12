//
//  Generated code. Do not modify.
//  source: galaxy_service.proto
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

import 'galaxy_service.pb.dart' as $5;
import 'galaxy_service.pbjson.dart';

export 'galaxy_service.pb.dart';

abstract class GalaxyServiceBase extends $pb.GeneratedService {
  $async.Future<$5.UpdateNodeMasteryResponse> updateNodeMastery($pb.ServerContext ctx, $5.UpdateNodeMasteryRequest request);
  $async.Future<$5.SyncCollaborativeGalaxyResponse> syncCollaborativeGalaxy($pb.ServerContext ctx, $5.SyncCollaborativeGalaxyRequest request);

  $pb.GeneratedMessage createRequest($core.String methodName) {
    switch (methodName) {
      case 'UpdateNodeMastery': return $5.UpdateNodeMasteryRequest();
      case 'SyncCollaborativeGalaxy': return $5.SyncCollaborativeGalaxyRequest();
      default: throw $core.ArgumentError('Unknown method: $methodName');
    }
  }

  $async.Future<$pb.GeneratedMessage> handleCall($pb.ServerContext ctx, $core.String methodName, $pb.GeneratedMessage request) {
    switch (methodName) {
      case 'UpdateNodeMastery': return this.updateNodeMastery(ctx, request as $5.UpdateNodeMasteryRequest);
      case 'SyncCollaborativeGalaxy': return this.syncCollaborativeGalaxy(ctx, request as $5.SyncCollaborativeGalaxyRequest);
      default: throw $core.ArgumentError('Unknown method: $methodName');
    }
  }

  $core.Map<$core.String, $core.dynamic> get $json => GalaxyServiceBase$json;
  $core.Map<$core.String, $core.Map<$core.String, $core.dynamic>> get $messageJson => GalaxyServiceBase$messageJson;
}

