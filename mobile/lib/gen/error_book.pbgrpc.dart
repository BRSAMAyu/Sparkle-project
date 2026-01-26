//
//  Generated code. Do not modify.
//  source: error_book.proto
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

import 'error_book.pb.dart' as $2;

export 'error_book.pb.dart';

@$pb.GrpcServiceName('error_book.ErrorBookService')
class ErrorBookServiceClient extends $grpc.Client {
  static final _$createError = $grpc.ClientMethod<$2.CreateErrorRequest, $2.ErrorRecord>(
      '/error_book.ErrorBookService/CreateError',
      ($2.CreateErrorRequest value) => value.writeToBuffer(),
      ($core.List<$core.int> value) => $2.ErrorRecord.fromBuffer(value));
  static final _$listErrors = $grpc.ClientMethod<$2.ListErrorsRequest, $2.ListErrorsResponse>(
      '/error_book.ErrorBookService/ListErrors',
      ($2.ListErrorsRequest value) => value.writeToBuffer(),
      ($core.List<$core.int> value) => $2.ListErrorsResponse.fromBuffer(value));
  static final _$getError = $grpc.ClientMethod<$2.GetErrorRequest, $2.ErrorRecord>(
      '/error_book.ErrorBookService/GetError',
      ($2.GetErrorRequest value) => value.writeToBuffer(),
      ($core.List<$core.int> value) => $2.ErrorRecord.fromBuffer(value));
  static final _$updateError = $grpc.ClientMethod<$2.UpdateErrorRequest, $2.ErrorRecord>(
      '/error_book.ErrorBookService/UpdateError',
      ($2.UpdateErrorRequest value) => value.writeToBuffer(),
      ($core.List<$core.int> value) => $2.ErrorRecord.fromBuffer(value));
  static final _$deleteError = $grpc.ClientMethod<$2.DeleteErrorRequest, $2.DeleteErrorResponse>(
      '/error_book.ErrorBookService/DeleteError',
      ($2.DeleteErrorRequest value) => value.writeToBuffer(),
      ($core.List<$core.int> value) => $2.DeleteErrorResponse.fromBuffer(value));
  static final _$analyzeError = $grpc.ClientMethod<$2.AnalyzeErrorRequest, $2.AnalyzeErrorResponse>(
      '/error_book.ErrorBookService/AnalyzeError',
      ($2.AnalyzeErrorRequest value) => value.writeToBuffer(),
      ($core.List<$core.int> value) => $2.AnalyzeErrorResponse.fromBuffer(value));
  static final _$submitReview = $grpc.ClientMethod<$2.SubmitReviewRequest, $2.ErrorRecord>(
      '/error_book.ErrorBookService/SubmitReview',
      ($2.SubmitReviewRequest value) => value.writeToBuffer(),
      ($core.List<$core.int> value) => $2.ErrorRecord.fromBuffer(value));
  static final _$getReviewStats = $grpc.ClientMethod<$2.GetReviewStatsRequest, $2.ReviewStatsResponse>(
      '/error_book.ErrorBookService/GetReviewStats',
      ($2.GetReviewStatsRequest value) => value.writeToBuffer(),
      ($core.List<$core.int> value) => $2.ReviewStatsResponse.fromBuffer(value));
  static final _$getTodayReviews = $grpc.ClientMethod<$2.GetTodayReviewsRequest, $2.ListErrorsResponse>(
      '/error_book.ErrorBookService/GetTodayReviews',
      ($2.GetTodayReviewsRequest value) => value.writeToBuffer(),
      ($core.List<$core.int> value) => $2.ListErrorsResponse.fromBuffer(value));

  ErrorBookServiceClient($grpc.ClientChannel channel,
      {$grpc.CallOptions? options,
      $core.Iterable<$grpc.ClientInterceptor>? interceptors})
      : super(channel, options: options,
        interceptors: interceptors);

  $grpc.ResponseFuture<$2.ErrorRecord> createError($2.CreateErrorRequest request, {$grpc.CallOptions? options}) {
    return $createUnaryCall(_$createError, request, options: options);
  }

  $grpc.ResponseFuture<$2.ListErrorsResponse> listErrors($2.ListErrorsRequest request, {$grpc.CallOptions? options}) {
    return $createUnaryCall(_$listErrors, request, options: options);
  }

  $grpc.ResponseFuture<$2.ErrorRecord> getError($2.GetErrorRequest request, {$grpc.CallOptions? options}) {
    return $createUnaryCall(_$getError, request, options: options);
  }

  $grpc.ResponseFuture<$2.ErrorRecord> updateError($2.UpdateErrorRequest request, {$grpc.CallOptions? options}) {
    return $createUnaryCall(_$updateError, request, options: options);
  }

  $grpc.ResponseFuture<$2.DeleteErrorResponse> deleteError($2.DeleteErrorRequest request, {$grpc.CallOptions? options}) {
    return $createUnaryCall(_$deleteError, request, options: options);
  }

  $grpc.ResponseFuture<$2.AnalyzeErrorResponse> analyzeError($2.AnalyzeErrorRequest request, {$grpc.CallOptions? options}) {
    return $createUnaryCall(_$analyzeError, request, options: options);
  }

  $grpc.ResponseFuture<$2.ErrorRecord> submitReview($2.SubmitReviewRequest request, {$grpc.CallOptions? options}) {
    return $createUnaryCall(_$submitReview, request, options: options);
  }

  $grpc.ResponseFuture<$2.ReviewStatsResponse> getReviewStats($2.GetReviewStatsRequest request, {$grpc.CallOptions? options}) {
    return $createUnaryCall(_$getReviewStats, request, options: options);
  }

  $grpc.ResponseFuture<$2.ListErrorsResponse> getTodayReviews($2.GetTodayReviewsRequest request, {$grpc.CallOptions? options}) {
    return $createUnaryCall(_$getTodayReviews, request, options: options);
  }
}

@$pb.GrpcServiceName('error_book.ErrorBookService')
abstract class ErrorBookServiceBase extends $grpc.Service {
  $core.String get $name => 'error_book.ErrorBookService';

  ErrorBookServiceBase() {
    $addMethod($grpc.ServiceMethod<$2.CreateErrorRequest, $2.ErrorRecord>(
        'CreateError',
        createError_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $2.CreateErrorRequest.fromBuffer(value),
        ($2.ErrorRecord value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$2.ListErrorsRequest, $2.ListErrorsResponse>(
        'ListErrors',
        listErrors_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $2.ListErrorsRequest.fromBuffer(value),
        ($2.ListErrorsResponse value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$2.GetErrorRequest, $2.ErrorRecord>(
        'GetError',
        getError_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $2.GetErrorRequest.fromBuffer(value),
        ($2.ErrorRecord value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$2.UpdateErrorRequest, $2.ErrorRecord>(
        'UpdateError',
        updateError_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $2.UpdateErrorRequest.fromBuffer(value),
        ($2.ErrorRecord value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$2.DeleteErrorRequest, $2.DeleteErrorResponse>(
        'DeleteError',
        deleteError_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $2.DeleteErrorRequest.fromBuffer(value),
        ($2.DeleteErrorResponse value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$2.AnalyzeErrorRequest, $2.AnalyzeErrorResponse>(
        'AnalyzeError',
        analyzeError_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $2.AnalyzeErrorRequest.fromBuffer(value),
        ($2.AnalyzeErrorResponse value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$2.SubmitReviewRequest, $2.ErrorRecord>(
        'SubmitReview',
        submitReview_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $2.SubmitReviewRequest.fromBuffer(value),
        ($2.ErrorRecord value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$2.GetReviewStatsRequest, $2.ReviewStatsResponse>(
        'GetReviewStats',
        getReviewStats_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $2.GetReviewStatsRequest.fromBuffer(value),
        ($2.ReviewStatsResponse value) => value.writeToBuffer()));
    $addMethod($grpc.ServiceMethod<$2.GetTodayReviewsRequest, $2.ListErrorsResponse>(
        'GetTodayReviews',
        getTodayReviews_Pre,
        false,
        false,
        ($core.List<$core.int> value) => $2.GetTodayReviewsRequest.fromBuffer(value),
        ($2.ListErrorsResponse value) => value.writeToBuffer()));
  }

  $async.Future<$2.ErrorRecord> createError_Pre($grpc.ServiceCall call, $async.Future<$2.CreateErrorRequest> request) async {
    return createError(call, await request);
  }

  $async.Future<$2.ListErrorsResponse> listErrors_Pre($grpc.ServiceCall call, $async.Future<$2.ListErrorsRequest> request) async {
    return listErrors(call, await request);
  }

  $async.Future<$2.ErrorRecord> getError_Pre($grpc.ServiceCall call, $async.Future<$2.GetErrorRequest> request) async {
    return getError(call, await request);
  }

  $async.Future<$2.ErrorRecord> updateError_Pre($grpc.ServiceCall call, $async.Future<$2.UpdateErrorRequest> request) async {
    return updateError(call, await request);
  }

  $async.Future<$2.DeleteErrorResponse> deleteError_Pre($grpc.ServiceCall call, $async.Future<$2.DeleteErrorRequest> request) async {
    return deleteError(call, await request);
  }

  $async.Future<$2.AnalyzeErrorResponse> analyzeError_Pre($grpc.ServiceCall call, $async.Future<$2.AnalyzeErrorRequest> request) async {
    return analyzeError(call, await request);
  }

  $async.Future<$2.ErrorRecord> submitReview_Pre($grpc.ServiceCall call, $async.Future<$2.SubmitReviewRequest> request) async {
    return submitReview(call, await request);
  }

  $async.Future<$2.ReviewStatsResponse> getReviewStats_Pre($grpc.ServiceCall call, $async.Future<$2.GetReviewStatsRequest> request) async {
    return getReviewStats(call, await request);
  }

  $async.Future<$2.ListErrorsResponse> getTodayReviews_Pre($grpc.ServiceCall call, $async.Future<$2.GetTodayReviewsRequest> request) async {
    return getTodayReviews(call, await request);
  }

  $async.Future<$2.ErrorRecord> createError($grpc.ServiceCall call, $2.CreateErrorRequest request);
  $async.Future<$2.ListErrorsResponse> listErrors($grpc.ServiceCall call, $2.ListErrorsRequest request);
  $async.Future<$2.ErrorRecord> getError($grpc.ServiceCall call, $2.GetErrorRequest request);
  $async.Future<$2.ErrorRecord> updateError($grpc.ServiceCall call, $2.UpdateErrorRequest request);
  $async.Future<$2.DeleteErrorResponse> deleteError($grpc.ServiceCall call, $2.DeleteErrorRequest request);
  $async.Future<$2.AnalyzeErrorResponse> analyzeError($grpc.ServiceCall call, $2.AnalyzeErrorRequest request);
  $async.Future<$2.ErrorRecord> submitReview($grpc.ServiceCall call, $2.SubmitReviewRequest request);
  $async.Future<$2.ReviewStatsResponse> getReviewStats($grpc.ServiceCall call, $2.GetReviewStatsRequest request);
  $async.Future<$2.ListErrorsResponse> getTodayReviews($grpc.ServiceCall call, $2.GetTodayReviewsRequest request);
}
