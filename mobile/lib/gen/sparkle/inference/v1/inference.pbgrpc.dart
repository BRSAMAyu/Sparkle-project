//
//  Generated code. Do not modify.
//  source: sparkle/inference/v1/inference.proto
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

import 'inference.pb.dart' as $0;

export 'inference.pb.dart';

@$pb.GrpcServiceName('sparkle.inference.v1.InferenceService')
class InferenceServiceClient extends $grpc.Client {
  static final _$runInference = $grpc.ClientMethod<$0.InferenceRequest, $0.InferenceResponse>(
      '/sparkle.inference.v1.InferenceService/RunInference',
      ($0.InferenceRequest value) => value.writeToBuffer(),
      ($core.List<$core.int> value) => $0.InferenceResponse.fromBuffer(value));

  InferenceServiceClient($grpc.ClientChannel channel,
      {$grpc.CallOptions? options,
      $core.Iterable<$grpc.ClientInterceptor>? interceptors})
      : super(channel, options: options,
        interceptors: interceptors);

  $grpc.ResponseFuture<$0.InferenceResponse> runInference($0.InferenceRequest request, {$grpc.CallOptions? options}) {
    return $createUnaryCall(_$runInference, request, options: options);
  }
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

  $async.Future<$0.InferenceResponse> runInference_Pre($grpc.ServiceCall call, $async.Future<$0.InferenceRequest> request) async {
    return runInference(call, await request);
  }

  $async.Future<$0.InferenceResponse> runInference($grpc.ServiceCall call, $0.InferenceRequest request);
}
