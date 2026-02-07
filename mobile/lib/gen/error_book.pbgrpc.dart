// This is a generated file - do not edit.
//
// Generated from error_book.proto.

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

import 'error_book.pb.dart' as $0;

export 'error_book.pb.dart';

@$pb.GrpcServiceName('error_book.ErrorBookService')
class ErrorBookServiceClient extends $grpc.Client {
  /// The hostname for this service.
  static const $core.String defaultHost = '';

  /// OAuth scopes needed for the client.
  static const $core.List<$core.String> oauthScopes = [
    '',
  ];

  ErrorBookServiceClient(super.channel, {super.options, super.interceptors});

  /// Create a new error record
  $grpc.ResponseFuture<$0.ErrorRecord> createError(
    $0.CreateErrorRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$createError, request, options: options);
  }

  /// List errors with filtering
  $grpc.ResponseFuture<$0.ListErrorsResponse> listErrors(
    $0.ListErrorsRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$listErrors, request, options: options);
  }

  /// Get a single error detail
  $grpc.ResponseFuture<$0.ErrorRecord> getError(
    $0.GetErrorRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$getError, request, options: options);
  }

  /// Update an error record
  $grpc.ResponseFuture<$0.ErrorRecord> updateError(
    $0.UpdateErrorRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$updateError, request, options: options);
  }

  /// Delete an error record
  $grpc.ResponseFuture<$0.DeleteErrorResponse> deleteError(
    $0.DeleteErrorRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$deleteError, request, options: options);
  }

  /// Trigger re-analysis
  $grpc.ResponseFuture<$0.AnalyzeErrorResponse> analyzeError(
    $0.AnalyzeErrorRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$analyzeError, request, options: options);
  }

  /// Submit review performance
  $grpc.ResponseFuture<$0.ErrorRecord> submitReview(
    $0.SubmitReviewRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$submitReview, request, options: options);
  }

  /// Get review statistics
  $grpc.ResponseFuture<$0.ReviewStatsResponse> getReviewStats(
    $0.GetReviewStatsRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$getReviewStats, request, options: options);
  }

  /// Get today's review list
  $grpc.ResponseFuture<$0.ListErrorsResponse> getTodayReviews(
    $0.GetTodayReviewsRequest request, {
    $grpc.CallOptions? options,
  }) {
    return $createUnaryCall(_$getTodayReviews, request, options: options);
  }

  // method descriptors

  static final _$createError =
      $grpc.ClientMethod<$0.CreateErrorRequest, $0.ErrorRecord>(
          '/error_book.ErrorBookService/CreateError',
          ($0.CreateErrorRequest value) => value.writeToBuffer(),
          $0.ErrorRecord.fromBuffer);
  static final _$listErrors =
      $grpc.ClientMethod<$0.ListErrorsRequest, $0.ListErrorsResponse>(
          '/error_book.ErrorBookService/ListErrors',
          ($0.ListErrorsRequest value) => value.writeToBuffer(),
          $0.ListErrorsResponse.fromBuffer);
  static final _$getError =
      $grpc.ClientMethod<$0.GetErrorRequest, $0.ErrorRecord>(
          '/error_book.ErrorBookService/GetError',
          ($0.GetErrorRequest value) => value.writeToBuffer(),
          $0.ErrorRecord.fromBuffer);
  static final _$updateError =
      $grpc.ClientMethod<$0.UpdateErrorRequest, $0.ErrorRecord>(
          '/error_book.ErrorBookService/UpdateError',
          ($0.UpdateErrorRequest value) => value.writeToBuffer(),
          $0.ErrorRecord.fromBuffer);
  static final _$deleteError =
      $grpc.ClientMethod<$0.DeleteErrorRequest, $0.DeleteErrorResponse>(
          '/error_book.ErrorBookService/DeleteError',
          ($0.DeleteErrorRequest value) => value.writeToBuffer(),
          $0.DeleteErrorResponse.fromBuffer);
  static final _$analyzeError =
      $grpc.ClientMethod<$0.AnalyzeErrorRequest, $0.AnalyzeErrorResponse>(
          '/error_book.ErrorBookService/AnalyzeError',
          ($0.AnalyzeErrorRequest value) => value.writeToBuffer(),
          $0.AnalyzeErrorResponse.fromBuffer);
  static final _$submitReview =
      $grpc.ClientMethod<$0.SubmitReviewRequest, $0.ErrorRecord>(
          '/error_book.ErrorBookService/SubmitReview',
          ($0.SubmitReviewRequest value) => value.writeToBuffer(),
          $0.ErrorRecord.fromBuffer);
  static final _$getReviewStats =
      $grpc.ClientMethod<$0.GetReviewStatsRequest, $0.ReviewStatsResponse>(
          '/error_book.ErrorBookService/GetReviewStats',
          ($0.GetReviewStatsRequest value) => value.writeToBuffer(),
          $0.ReviewStatsResponse.fromBuffer);
  static final _$getTodayReviews =
      $grpc.ClientMethod<$0.GetTodayReviewsRequest, $0.ListErrorsResponse>(
          '/error_book.ErrorBookService/GetTodayReviews',
          ($0.GetTodayReviewsRequest value) => value.writeToBuffer(),
          $0.ListErrorsResponse.fromBuffer);
}

@$pb.GrpcServiceName('error_book.ErrorBookService')
abstract class ErrorBookServiceBase extends $grpc.Service {
  $core.String get $name => 'error_book.ErrorBookService';

  ErrorBookServiceBase() {
    $addMethod($grpc.ServiceMethod<$0.CreateErrorRequest, $0.ErrorRecord>(
        'CreateError',
        createError_Pre,
        false,
        false,
        ($core.List<$core.int> value) =>
            $0.CreateErrorRequest.fromBuffer(value),
        ($0.ErrorRecord value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.ListErrorsRequest, $0.ListErrorsResponse>(
        'ListErrors',
        listErrors_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $0.ListErrorsRequest.fromBuffer(value),
        ($0.ListErrorsResponse value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.GetErrorRequest, $0.ErrorRecord>(
        'GetError',
        getError_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $0.GetErrorRequest.fromBuffer(value),
        ($0.ErrorRecord value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.UpdateErrorRequest, $0.ErrorRecord>(
        'UpdateError',
        updateError_Pre,
        false,
        false,
        ($core.List<$core.int> value) =>
            $0.UpdateErrorRequest.fromBuffer(value),
        ($0.ErrorRecord value) => value.writeToBuffer()));
    $addMethod(
        $grpc.ServiceMethod<$0.DeleteErrorRequest, $0.DeleteErrorResponse>(
            'DeleteError',
            deleteError_Pre,
            false,
            false,
            ($core.List<$core.int> value) =>
                $0.DeleteErrorRequest.fromBuffer(value),
            ($0.DeleteErrorResponse value) => value.writeToBuffer()));
    $addMethod(
        $grpc.ServiceMethod<$0.AnalyzeErrorRequest, $0.AnalyzeErrorResponse>(
            'AnalyzeError',
            analyzeError_Pre,
            false,
            false,
            ($core.List<$core.int> value) =>
                $0.AnalyzeErrorRequest.fromBuffer(value),
            ($0.AnalyzeErrorResponse value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$0.SubmitReviewRequest, $0.ErrorRecord>(
        'SubmitReview',
        submitReview_Pre,
        false,
        false,
        ($core.List<$core.int> value) =>
            $0.SubmitReviewRequest.fromBuffer(value),
        ($0.ErrorRecord value) => value.writeToBuffer()));
    $addMethod(
        $grpc.ServiceMethod<$0.GetReviewStatsRequest, $0.ReviewStatsResponse>(
            'GetReviewStats',
            getReviewStats_Pre,
            false,
            false,
            ($core.List<$core.int> value) =>
                $0.GetReviewStatsRequest.fromBuffer(value),
            ($0.ReviewStatsResponse value) => value.writeToBuffer()));
    $addMethod(
        $grpc.ServiceMethod<$0.GetTodayReviewsRequest, $0.ListErrorsResponse>(
            'GetTodayReviews',
            getTodayReviews_Pre,
            false,
            false,
            ($core.List<$core.int> value) =>
                $0.GetTodayReviewsRequest.fromBuffer(value),
            ($0.ListErrorsResponse value) => value.writeToBuffer()));
  }

  $async.Future<$0.ErrorRecord> createError_Pre($grpc.ServiceCall $call,
      $async.Future<$0.CreateErrorRequest> $request) async {
    return createError($call, await $request);
  }

  $async.Future<$0.ErrorRecord> createError(
      $grpc.ServiceCall call, $0.CreateErrorRequest request);

  $async.Future<$0.ListErrorsResponse> listErrors_Pre($grpc.ServiceCall $call,
      $async.Future<$0.ListErrorsRequest> $request) async {
    return listErrors($call, await $request);
  }

  $async.Future<$0.ListErrorsResponse> listErrors(
      $grpc.ServiceCall call, $0.ListErrorsRequest request);

  $async.Future<$0.ErrorRecord> getError_Pre($grpc.ServiceCall $call,
      $async.Future<$0.GetErrorRequest> $request) async {
    return getError($call, await $request);
  }

  $async.Future<$0.ErrorRecord> getError(
      $grpc.ServiceCall call, $0.GetErrorRequest request);

  $async.Future<$0.ErrorRecord> updateError_Pre($grpc.ServiceCall $call,
      $async.Future<$0.UpdateErrorRequest> $request) async {
    return updateError($call, await $request);
  }

  $async.Future<$0.ErrorRecord> updateError(
      $grpc.ServiceCall call, $0.UpdateErrorRequest request);

  $async.Future<$0.DeleteErrorResponse> deleteError_Pre($grpc.ServiceCall $call,
      $async.Future<$0.DeleteErrorRequest> $request) async {
    return deleteError($call, await $request);
  }

  $async.Future<$0.DeleteErrorResponse> deleteError(
      $grpc.ServiceCall call, $0.DeleteErrorRequest request);

  $async.Future<$0.AnalyzeErrorResponse> analyzeError_Pre(
      $grpc.ServiceCall $call,
      $async.Future<$0.AnalyzeErrorRequest> $request) async {
    return analyzeError($call, await $request);
  }

  $async.Future<$0.AnalyzeErrorResponse> analyzeError(
      $grpc.ServiceCall call, $0.AnalyzeErrorRequest request);

  $async.Future<$0.ErrorRecord> submitReview_Pre($grpc.ServiceCall $call,
      $async.Future<$0.SubmitReviewRequest> $request) async {
    return submitReview($call, await $request);
  }

  $async.Future<$0.ErrorRecord> submitReview(
      $grpc.ServiceCall call, $0.SubmitReviewRequest request);

  $async.Future<$0.ReviewStatsResponse> getReviewStats_Pre(
      $grpc.ServiceCall $call,
      $async.Future<$0.GetReviewStatsRequest> $request) async {
    return getReviewStats($call, await $request);
  }

  $async.Future<$0.ReviewStatsResponse> getReviewStats(
      $grpc.ServiceCall call, $0.GetReviewStatsRequest request);

  $async.Future<$0.ListErrorsResponse> getTodayReviews_Pre(
      $grpc.ServiceCall $call,
      $async.Future<$0.GetTodayReviewsRequest> $request) async {
    return getTodayReviews($call, await $request);
  }

  $async.Future<$0.ListErrorsResponse> getTodayReviews(
      $grpc.ServiceCall call, $0.GetTodayReviewsRequest request);
}
