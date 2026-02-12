// This is a generated file - do not edit.
//
// Generated from sparkle/inference/v1/inference.proto.

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

import 'inference.pb.dart' as $0;

export 'inference.pb.dart';

/// Authorization is required for all RPCs. Clients must send either:
/// - authorization: Bearer <token>
/// - x-internal-api-key: <key>
@$pb.GrpcServiceName('sparkle.inference.v1.InferenceService')
class InferenceServiceClient extends $grpc.Client {
  /// The hostname for this service.
  static const $core.String defaultHost = '';

  /// OAuth scopes needed for the client.
  static const $core.List<$core.String> oauthScopes = [
    '',
  ];

  InferenceServiceClient(super.channel, {super.options, super.interceptors});

  $grpc.ResponseFuture<$0.InferenceResponse> runInference(
    $0.InferenceRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$runInference, request, options: options);
  }

  // method descriptors

  static final _$runInference =
      $grpc.ClientMethod<$0.InferenceRequest, $0.InferenceResponse>(
          '/sparkle.inference.v1.InferenceService/RunInference',
          ($0.InferenceRequest value) => value.writeToBuffer(),
          $0.InferenceResponse.fromBuffer);
}

@$pb.GrpcServiceName('sparkle.inference.v1.InferenceService')
abstract class InferenceServiceBase extends $grpc.Service {
  $core.String get $name => 'sparkle.inference.v1.InferenceService';

  InferenceServiceBase() {
    $addMethod($grpc.ServiceMethod<$0.InferenceRequest, $0.InferenceResponse>(
        'RunInference',
        runInference_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $0.InferenceRequest.fromBuffer(value),
        ($0.InferenceResponse value) => value.writeToBuffer()));
  }

  $async.Future<$0.InferenceResponse> runInference_Pre($grpc.ServiceCall $call,
      $async.Future<$0.InferenceRequest> $request) async {
    return runInference($call, await $request);
  }

  $async.Future<$0.InferenceResponse> runInference(
      $grpc.ServiceCall call, $0.InferenceRequest request);
}
