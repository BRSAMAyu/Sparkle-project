// This is a generated file - do not edit.
//
// Generated from stt_service.proto.

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

import 'stt_service.pb.dart' as $0;

export 'stt_service.pb.dart';

/// STTService defines the interface for Speech-to-Text operations.
/// Supports both streaming (real-time) and batch (file-based) transcription.
@$pb.GrpcServiceName('stt.v1.STTService')
class STTServiceClient extends $grpc.Client {
  /// The hostname for this service.
  static const $core.String defaultHost = '';

  /// OAuth scopes needed for the client.
  static const $core.List<$core.String> oauthScopes = [
    '',
  ];

  STTServiceClient(super.channel, {super.options, super.interceptors});

  /// StreamSpeechToText handles bi-directional streaming for real-time transcription.
  /// Client streams audio chunks, server streams transcription results.
  /// Use case: Live voice input, real-time captioning.
  $grpc.ResponseStream<$0.TranscriptionResult> streamSpeechToText(
    $async.Stream<$0.AudioChunk> request, {
    $grpc.CallOptions? options,
  }) {
    return $createStreamingCall(_$streamSpeechToText, request,
        options: options);
  }

  /// TranscribeAudio transcribes a complete audio file.
  /// Use case: Voice messages, recorded audio notes.
  $grpc.ResponseFuture<$0.TranscribeResponse> transcribeAudio(
    $0.TranscribeRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$transcribeAudio, request, options: options);
  }

  /// EnhanceTranscript improves transcript quality using LLM post-processing.
  /// Adds punctuation, corrects typos, and formats speaker turns.
  $grpc.ResponseFuture<$0.EnhanceResponse> enhanceTranscript(
    $0.EnhanceRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$enhanceTranscript, request, options: options);
  }

  // method descriptors

  static final _$streamSpeechToText =
      $grpc.ClientMethod<$0.AudioChunk, $0.TranscriptionResult>(
          '/stt.v1.STTService/StreamSpeechToText',
          ($0.AudioChunk value) => value.writeToBuffer(),
          $0.TranscriptionResult.fromBuffer);
  static final _$transcribeAudio =
      $grpc.ClientMethod<$0.TranscribeRequest, $0.TranscribeResponse>(
          '/stt.v1.STTService/TranscribeAudio',
          ($0.TranscribeRequest value) => value.writeToBuffer(),
          $0.TranscribeResponse.fromBuffer);
  static final _$enhanceTranscript =
      $grpc.ClientMethod<$0.EnhanceRequest, $0.EnhanceResponse>(
          '/stt.v1.STTService/EnhanceTranscript',
          ($0.EnhanceRequest value) => value.writeToBuffer(),
          $0.EnhanceResponse.fromBuffer);
}

@$pb.GrpcServiceName('stt.v1.STTService')
abstract class STTServiceBase extends $grpc.Service {
  $core.String get $name => 'stt.v1.STTService';

  STTServiceBase() {
    $addMethod($grpc.ServiceMethod<$0.AudioChunk, $0.TranscriptionResult>(
        'StreamSpeechToText',
        streamSpeechToText,
        true,
        true,
        ($core.List<$core.int> value) => $0.AudioChunk.fromBuffer(value),
        ($0.TranscriptionResult value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.TranscribeRequest, $0.TranscribeResponse>(
        'TranscribeAudio',
        transcribeAudio_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $0.TranscribeRequest.fromBuffer(value),
        ($0.TranscribeResponse value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.EnhanceRequest, $0.EnhanceResponse>(
        'EnhanceTranscript',
        enhanceTranscript_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $0.EnhanceRequest.fromBuffer(value),
        ($0.EnhanceResponse value) => value.writeToBuffer()));
  }

  $async.Stream<$0.TranscriptionResult> streamSpeechToText(
      $grpc.ServiceCall call, $async.Stream<$0.AudioChunk> request);

  $async.Future<$0.TranscribeResponse> transcribeAudio_Pre(
      $grpc.ServiceCall $call,
      $async.Future<$0.TranscribeRequest> $request) async {
    return transcribeAudio($call, await $request);
  }

  $async.Future<$0.TranscribeResponse> transcribeAudio(
      $grpc.ServiceCall call, $0.TranscribeRequest request);

  $async.Future<$0.EnhanceResponse> enhanceTranscript_Pre(
      $grpc.ServiceCall $call,
      $async.Future<$0.EnhanceRequest> $request) async {
    return enhanceTranscript($call, await $request);
  }

  $async.Future<$0.EnhanceResponse> enhanceTranscript(
      $grpc.ServiceCall call, $0.EnhanceRequest request);
}
