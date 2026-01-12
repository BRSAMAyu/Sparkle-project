//
//  Generated code. Do not modify.
//  source: error_book.proto
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

import 'error_book.pb.dart' as $4;
import 'error_book.pbjson.dart';

export 'error_book.pb.dart';

abstract class ErrorBookServiceBase extends $pb.GeneratedService {
  $async.Future<$4.ErrorRecord> createError($pb.ServerContext ctx, $4.CreateErrorRequest request);
  $async.Future<$4.ListErrorsResponse> listErrors($pb.ServerContext ctx, $4.ListErrorsRequest request);
  $async.Future<$4.ErrorRecord> getError($pb.ServerContext ctx, $4.GetErrorRequest request);
  $async.Future<$4.ErrorRecord> updateError($pb.ServerContext ctx, $4.UpdateErrorRequest request);
  $async.Future<$4.DeleteErrorResponse> deleteError($pb.ServerContext ctx, $4.DeleteErrorRequest request);
  $async.Future<$4.AnalyzeErrorResponse> analyzeError($pb.ServerContext ctx, $4.AnalyzeErrorRequest request);
  $async.Future<$4.ErrorRecord> submitReview($pb.ServerContext ctx, $4.SubmitReviewRequest request);
  $async.Future<$4.ReviewStatsResponse> getReviewStats($pb.ServerContext ctx, $4.GetReviewStatsRequest request);
  $async.Future<$4.ListErrorsResponse> getTodayReviews($pb.ServerContext ctx, $4.GetTodayReviewsRequest request);

  $pb.GeneratedMessage createRequest($core.String methodName) {
    switch (methodName) {
      case 'CreateError': return $4.CreateErrorRequest();
      case 'ListErrors': return $4.ListErrorsRequest();
      case 'GetError': return $4.GetErrorRequest();
      case 'UpdateError': return $4.UpdateErrorRequest();
      case 'DeleteError': return $4.DeleteErrorRequest();
      case 'AnalyzeError': return $4.AnalyzeErrorRequest();
      case 'SubmitReview': return $4.SubmitReviewRequest();
      case 'GetReviewStats': return $4.GetReviewStatsRequest();
      case 'GetTodayReviews': return $4.GetTodayReviewsRequest();
      default: throw $core.ArgumentError('Unknown method: $methodName');
    }
  }

  $async.Future<$pb.GeneratedMessage> handleCall($pb.ServerContext ctx, $core.String methodName, $pb.GeneratedMessage request) {
    switch (methodName) {
      case 'CreateError': return this.createError(ctx, request as $4.CreateErrorRequest);
      case 'ListErrors': return this.listErrors(ctx, request as $4.ListErrorsRequest);
      case 'GetError': return this.getError(ctx, request as $4.GetErrorRequest);
      case 'UpdateError': return this.updateError(ctx, request as $4.UpdateErrorRequest);
      case 'DeleteError': return this.deleteError(ctx, request as $4.DeleteErrorRequest);
      case 'AnalyzeError': return this.analyzeError(ctx, request as $4.AnalyzeErrorRequest);
      case 'SubmitReview': return this.submitReview(ctx, request as $4.SubmitReviewRequest);
      case 'GetReviewStats': return this.getReviewStats(ctx, request as $4.GetReviewStatsRequest);
      case 'GetTodayReviews': return this.getTodayReviews(ctx, request as $4.GetTodayReviewsRequest);
      default: throw $core.ArgumentError('Unknown method: $methodName');
    }
  }

  $core.Map<$core.String, $core.dynamic> get $json => ErrorBookServiceBase$json;
  $core.Map<$core.String, $core.Map<$core.String, $core.dynamic>> get $messageJson => ErrorBookServiceBase$messageJson;
}

