//
//  Generated code. Do not modify.
//  source: error_book.proto
//
// @dart = 2.12

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_final_fields
// ignore_for_file: unnecessary_import, unnecessary_this, unused_import

import 'dart:convert' as $convert;
import 'dart:core' as $core;
import 'dart:typed_data' as $typed_data;

import 'google/protobuf/timestamp.pbjson.dart' as $2;

@$core.Deprecated('Use errorRecordDescriptor instead')
const ErrorRecord$json = {
  '1': 'ErrorRecord',
  '2': [
    {'1': 'id', '3': 1, '4': 1, '5': 9, '10': 'id'},
    {'1': 'user_id', '3': 2, '4': 1, '5': 9, '10': 'userId'},
    {'1': 'subject_code', '3': 3, '4': 1, '5': 9, '10': 'subjectCode'},
    {'1': 'chapter', '3': 4, '4': 1, '5': 9, '10': 'chapter'},
    {'1': 'question_text', '3': 5, '4': 1, '5': 9, '10': 'questionText'},
    {'1': 'question_image_url', '3': 6, '4': 1, '5': 9, '10': 'questionImageUrl'},
    {'1': 'user_answer', '3': 7, '4': 1, '5': 9, '10': 'userAnswer'},
    {'1': 'correct_answer', '3': 8, '4': 1, '5': 9, '10': 'correctAnswer'},
    {'1': 'mastery_level', '3': 9, '4': 1, '5': 1, '10': 'masteryLevel'},
    {'1': 'review_count', '3': 10, '4': 1, '5': 5, '10': 'reviewCount'},
    {'1': 'next_review_at', '3': 11, '4': 1, '5': 11, '6': '.google.protobuf.Timestamp', '10': 'nextReviewAt'},
    {'1': 'last_reviewed_at', '3': 12, '4': 1, '5': 11, '6': '.google.protobuf.Timestamp', '10': 'lastReviewedAt'},
    {'1': 'latest_analysis', '3': 13, '4': 1, '5': 11, '6': '.error_book.ErrorAnalysisResult', '10': 'latestAnalysis'},
    {'1': 'knowledge_links', '3': 14, '4': 3, '5': 11, '6': '.error_book.KnowledgeLinkBrief', '10': 'knowledgeLinks'},
    {'1': 'created_at', '3': 15, '4': 1, '5': 11, '6': '.google.protobuf.Timestamp', '10': 'createdAt'},
    {'1': 'updated_at', '3': 16, '4': 1, '5': 11, '6': '.google.protobuf.Timestamp', '10': 'updatedAt'},
  ],
};

/// Descriptor for `ErrorRecord`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List errorRecordDescriptor = $convert.base64Decode(
    'CgtFcnJvclJlY29yZBIOCgJpZBgBIAEoCVICaWQSFwoHdXNlcl9pZBgCIAEoCVIGdXNlcklkEi'
    'EKDHN1YmplY3RfY29kZRgDIAEoCVILc3ViamVjdENvZGUSGAoHY2hhcHRlchgEIAEoCVIHY2hh'
    'cHRlchIjCg1xdWVzdGlvbl90ZXh0GAUgASgJUgxxdWVzdGlvblRleHQSLAoScXVlc3Rpb25faW'
    '1hZ2VfdXJsGAYgASgJUhBxdWVzdGlvbkltYWdlVXJsEh8KC3VzZXJfYW5zd2VyGAcgASgJUgp1'
    'c2VyQW5zd2VyEiUKDmNvcnJlY3RfYW5zd2VyGAggASgJUg1jb3JyZWN0QW5zd2VyEiMKDW1hc3'
    'RlcnlfbGV2ZWwYCSABKAFSDG1hc3RlcnlMZXZlbBIhCgxyZXZpZXdfY291bnQYCiABKAVSC3Jl'
    'dmlld0NvdW50EkAKDm5leHRfcmV2aWV3X2F0GAsgASgLMhouZ29vZ2xlLnByb3RvYnVmLlRpbW'
    'VzdGFtcFIMbmV4dFJldmlld0F0EkQKEGxhc3RfcmV2aWV3ZWRfYXQYDCABKAsyGi5nb29nbGUu'
    'cHJvdG9idWYuVGltZXN0YW1wUg5sYXN0UmV2aWV3ZWRBdBJICg9sYXRlc3RfYW5hbHlzaXMYDS'
    'ABKAsyHy5lcnJvcl9ib29rLkVycm9yQW5hbHlzaXNSZXN1bHRSDmxhdGVzdEFuYWx5c2lzEkcK'
    'D2tub3dsZWRnZV9saW5rcxgOIAMoCzIeLmVycm9yX2Jvb2suS25vd2xlZGdlTGlua0JyaWVmUg'
    '5rbm93bGVkZ2VMaW5rcxI5CgpjcmVhdGVkX2F0GA8gASgLMhouZ29vZ2xlLnByb3RvYnVmLlRp'
    'bWVzdGFtcFIJY3JlYXRlZEF0EjkKCnVwZGF0ZWRfYXQYECABKAsyGi5nb29nbGUucHJvdG9idW'
    'YuVGltZXN0YW1wUgl1cGRhdGVkQXQ=');

@$core.Deprecated('Use errorAnalysisResultDescriptor instead')
const ErrorAnalysisResult$json = {
  '1': 'ErrorAnalysisResult',
  '2': [
    {'1': 'error_type', '3': 1, '4': 1, '5': 9, '10': 'errorType'},
    {'1': 'error_type_label', '3': 2, '4': 1, '5': 9, '10': 'errorTypeLabel'},
    {'1': 'root_cause', '3': 3, '4': 1, '5': 9, '10': 'rootCause'},
    {'1': 'correct_approach', '3': 4, '4': 1, '5': 9, '10': 'correctApproach'},
    {'1': 'similar_traps', '3': 5, '4': 3, '5': 9, '10': 'similarTraps'},
    {'1': 'recommended_knowledge', '3': 6, '4': 3, '5': 9, '10': 'recommendedKnowledge'},
    {'1': 'study_suggestion', '3': 7, '4': 1, '5': 9, '10': 'studySuggestion'},
    {'1': 'ocr_text', '3': 8, '4': 1, '5': 9, '10': 'ocrText'},
  ],
};

/// Descriptor for `ErrorAnalysisResult`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List errorAnalysisResultDescriptor = $convert.base64Decode(
    'ChNFcnJvckFuYWx5c2lzUmVzdWx0Eh0KCmVycm9yX3R5cGUYASABKAlSCWVycm9yVHlwZRIoCh'
    'BlcnJvcl90eXBlX2xhYmVsGAIgASgJUg5lcnJvclR5cGVMYWJlbBIdCgpyb290X2NhdXNlGAMg'
    'ASgJUglyb290Q2F1c2USKQoQY29ycmVjdF9hcHByb2FjaBgEIAEoCVIPY29ycmVjdEFwcHJvYW'
    'NoEiMKDXNpbWlsYXJfdHJhcHMYBSADKAlSDHNpbWlsYXJUcmFwcxIzChVyZWNvbW1lbmRlZF9r'
    'bm93bGVkZ2UYBiADKAlSFHJlY29tbWVuZGVkS25vd2xlZGdlEikKEHN0dWR5X3N1Z2dlc3Rpb2'
    '4YByABKAlSD3N0dWR5U3VnZ2VzdGlvbhIZCghvY3JfdGV4dBgIIAEoCVIHb2NyVGV4dA==');

@$core.Deprecated('Use knowledgeLinkBriefDescriptor instead')
const KnowledgeLinkBrief$json = {
  '1': 'KnowledgeLinkBrief',
  '2': [
    {'1': 'id', '3': 1, '4': 1, '5': 9, '10': 'id'},
    {'1': 'name', '3': 2, '4': 1, '5': 9, '10': 'name'},
    {'1': 'relevance', '3': 3, '4': 1, '5': 1, '10': 'relevance'},
    {'1': 'is_primary', '3': 4, '4': 1, '5': 8, '10': 'isPrimary'},
  ],
};

/// Descriptor for `KnowledgeLinkBrief`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List knowledgeLinkBriefDescriptor = $convert.base64Decode(
    'ChJLbm93bGVkZ2VMaW5rQnJpZWYSDgoCaWQYASABKAlSAmlkEhIKBG5hbWUYAiABKAlSBG5hbW'
    'USHAoJcmVsZXZhbmNlGAMgASgBUglyZWxldmFuY2USHQoKaXNfcHJpbWFyeRgEIAEoCFIJaXNQ'
    'cmltYXJ5');

@$core.Deprecated('Use createErrorRequestDescriptor instead')
const CreateErrorRequest$json = {
  '1': 'CreateErrorRequest',
  '2': [
    {'1': 'user_id', '3': 1, '4': 1, '5': 9, '10': 'userId'},
    {'1': 'question_text', '3': 2, '4': 1, '5': 9, '10': 'questionText'},
    {'1': 'question_image_url', '3': 3, '4': 1, '5': 9, '10': 'questionImageUrl'},
    {'1': 'user_answer', '3': 4, '4': 1, '5': 9, '10': 'userAnswer'},
    {'1': 'correct_answer', '3': 5, '4': 1, '5': 9, '10': 'correctAnswer'},
    {'1': 'subject_code', '3': 6, '4': 1, '5': 9, '10': 'subjectCode'},
    {'1': 'chapter', '3': 7, '4': 1, '5': 9, '10': 'chapter'},
  ],
};

/// Descriptor for `CreateErrorRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List createErrorRequestDescriptor = $convert.base64Decode(
    'ChJDcmVhdGVFcnJvclJlcXVlc3QSFwoHdXNlcl9pZBgBIAEoCVIGdXNlcklkEiMKDXF1ZXN0aW'
    '9uX3RleHQYAiABKAlSDHF1ZXN0aW9uVGV4dBIsChJxdWVzdGlvbl9pbWFnZV91cmwYAyABKAlS'
    'EHF1ZXN0aW9uSW1hZ2VVcmwSHwoLdXNlcl9hbnN3ZXIYBCABKAlSCnVzZXJBbnN3ZXISJQoOY2'
    '9ycmVjdF9hbnN3ZXIYBSABKAlSDWNvcnJlY3RBbnN3ZXISIQoMc3ViamVjdF9jb2RlGAYgASgJ'
    'UgtzdWJqZWN0Q29kZRIYCgdjaGFwdGVyGAcgASgJUgdjaGFwdGVy');

@$core.Deprecated('Use listErrorsRequestDescriptor instead')
const ListErrorsRequest$json = {
  '1': 'ListErrorsRequest',
  '2': [
    {'1': 'user_id', '3': 1, '4': 1, '5': 9, '10': 'userId'},
    {'1': 'subject_code', '3': 2, '4': 1, '5': 9, '10': 'subjectCode'},
    {'1': 'chapter', '3': 3, '4': 1, '5': 9, '10': 'chapter'},
    {'1': 'error_type', '3': 4, '4': 1, '5': 9, '10': 'errorType'},
    {'1': 'mastery_min', '3': 5, '4': 1, '5': 1, '9': 0, '10': 'masteryMin', '17': true},
    {'1': 'mastery_max', '3': 6, '4': 1, '5': 1, '9': 1, '10': 'masteryMax', '17': true},
    {'1': 'need_review', '3': 7, '4': 1, '5': 8, '9': 2, '10': 'needReview', '17': true},
    {'1': 'keyword', '3': 8, '4': 1, '5': 9, '10': 'keyword'},
    {'1': 'page', '3': 9, '4': 1, '5': 5, '10': 'page'},
    {'1': 'page_size', '3': 10, '4': 1, '5': 5, '10': 'pageSize'},
  ],
  '8': [
    {'1': '_mastery_min'},
    {'1': '_mastery_max'},
    {'1': '_need_review'},
  ],
};

/// Descriptor for `ListErrorsRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List listErrorsRequestDescriptor = $convert.base64Decode(
    'ChFMaXN0RXJyb3JzUmVxdWVzdBIXCgd1c2VyX2lkGAEgASgJUgZ1c2VySWQSIQoMc3ViamVjdF'
    '9jb2RlGAIgASgJUgtzdWJqZWN0Q29kZRIYCgdjaGFwdGVyGAMgASgJUgdjaGFwdGVyEh0KCmVy'
    'cm9yX3R5cGUYBCABKAlSCWVycm9yVHlwZRIkCgttYXN0ZXJ5X21pbhgFIAEoAUgAUgptYXN0ZX'
    'J5TWluiAEBEiQKC21hc3RlcnlfbWF4GAYgASgBSAFSCm1hc3RlcnlNYXiIAQESJAoLbmVlZF9y'
    'ZXZpZXcYByABKAhIAlIKbmVlZFJldmlld4gBARIYCgdrZXl3b3JkGAggASgJUgdrZXl3b3JkEh'
    'IKBHBhZ2UYCSABKAVSBHBhZ2USGwoJcGFnZV9zaXplGAogASgFUghwYWdlU2l6ZUIOCgxfbWFz'
    'dGVyeV9taW5CDgoMX21hc3RlcnlfbWF4Qg4KDF9uZWVkX3Jldmlldw==');

@$core.Deprecated('Use listErrorsResponseDescriptor instead')
const ListErrorsResponse$json = {
  '1': 'ListErrorsResponse',
  '2': [
    {'1': 'items', '3': 1, '4': 3, '5': 11, '6': '.error_book.ErrorRecord', '10': 'items'},
    {'1': 'total', '3': 2, '4': 1, '5': 3, '10': 'total'},
    {'1': 'page', '3': 3, '4': 1, '5': 5, '10': 'page'},
    {'1': 'page_size', '3': 4, '4': 1, '5': 5, '10': 'pageSize'},
    {'1': 'has_next', '3': 5, '4': 1, '5': 8, '10': 'hasNext'},
  ],
};

/// Descriptor for `ListErrorsResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List listErrorsResponseDescriptor = $convert.base64Decode(
    'ChJMaXN0RXJyb3JzUmVzcG9uc2USLQoFaXRlbXMYASADKAsyFy5lcnJvcl9ib29rLkVycm9yUm'
    'Vjb3JkUgVpdGVtcxIUCgV0b3RhbBgCIAEoA1IFdG90YWwSEgoEcGFnZRgDIAEoBVIEcGFnZRIb'
    'CglwYWdlX3NpemUYBCABKAVSCHBhZ2VTaXplEhkKCGhhc19uZXh0GAUgASgIUgdoYXNOZXh0');

@$core.Deprecated('Use getErrorRequestDescriptor instead')
const GetErrorRequest$json = {
  '1': 'GetErrorRequest',
  '2': [
    {'1': 'error_id', '3': 1, '4': 1, '5': 9, '10': 'errorId'},
    {'1': 'user_id', '3': 2, '4': 1, '5': 9, '10': 'userId'},
  ],
};

/// Descriptor for `GetErrorRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List getErrorRequestDescriptor = $convert.base64Decode(
    'Cg9HZXRFcnJvclJlcXVlc3QSGQoIZXJyb3JfaWQYASABKAlSB2Vycm9ySWQSFwoHdXNlcl9pZB'
    'gCIAEoCVIGdXNlcklk');

@$core.Deprecated('Use updateErrorRequestDescriptor instead')
const UpdateErrorRequest$json = {
  '1': 'UpdateErrorRequest',
  '2': [
    {'1': 'error_id', '3': 1, '4': 1, '5': 9, '10': 'errorId'},
    {'1': 'user_id', '3': 2, '4': 1, '5': 9, '10': 'userId'},
    {'1': 'question_text', '3': 3, '4': 1, '5': 9, '9': 0, '10': 'questionText', '17': true},
    {'1': 'user_answer', '3': 4, '4': 1, '5': 9, '9': 1, '10': 'userAnswer', '17': true},
    {'1': 'correct_answer', '3': 5, '4': 1, '5': 9, '9': 2, '10': 'correctAnswer', '17': true},
    {'1': 'subject_code', '3': 6, '4': 1, '5': 9, '9': 3, '10': 'subjectCode', '17': true},
    {'1': 'chapter', '3': 7, '4': 1, '5': 9, '9': 4, '10': 'chapter', '17': true},
    {'1': 'question_image_url', '3': 8, '4': 1, '5': 9, '9': 5, '10': 'questionImageUrl', '17': true},
  ],
  '8': [
    {'1': '_question_text'},
    {'1': '_user_answer'},
    {'1': '_correct_answer'},
    {'1': '_subject_code'},
    {'1': '_chapter'},
    {'1': '_question_image_url'},
  ],
};

/// Descriptor for `UpdateErrorRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List updateErrorRequestDescriptor = $convert.base64Decode(
    'ChJVcGRhdGVFcnJvclJlcXVlc3QSGQoIZXJyb3JfaWQYASABKAlSB2Vycm9ySWQSFwoHdXNlcl'
    '9pZBgCIAEoCVIGdXNlcklkEigKDXF1ZXN0aW9uX3RleHQYAyABKAlIAFIMcXVlc3Rpb25UZXh0'
    'iAEBEiQKC3VzZXJfYW5zd2VyGAQgASgJSAFSCnVzZXJBbnN3ZXKIAQESKgoOY29ycmVjdF9hbn'
    'N3ZXIYBSABKAlIAlINY29ycmVjdEFuc3dlcogBARImCgxzdWJqZWN0X2NvZGUYBiABKAlIA1IL'
    'c3ViamVjdENvZGWIAQESHQoHY2hhcHRlchgHIAEoCUgEUgdjaGFwdGVyiAEBEjEKEnF1ZXN0aW'
    '9uX2ltYWdlX3VybBgIIAEoCUgFUhBxdWVzdGlvbkltYWdlVXJsiAEBQhAKDl9xdWVzdGlvbl90'
    'ZXh0Qg4KDF91c2VyX2Fuc3dlckIRCg9fY29ycmVjdF9hbnN3ZXJCDwoNX3N1YmplY3RfY29kZU'
    'IKCghfY2hhcHRlckIVChNfcXVlc3Rpb25faW1hZ2VfdXJs');

@$core.Deprecated('Use deleteErrorRequestDescriptor instead')
const DeleteErrorRequest$json = {
  '1': 'DeleteErrorRequest',
  '2': [
    {'1': 'error_id', '3': 1, '4': 1, '5': 9, '10': 'errorId'},
    {'1': 'user_id', '3': 2, '4': 1, '5': 9, '10': 'userId'},
  ],
};

/// Descriptor for `DeleteErrorRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List deleteErrorRequestDescriptor = $convert.base64Decode(
    'ChJEZWxldGVFcnJvclJlcXVlc3QSGQoIZXJyb3JfaWQYASABKAlSB2Vycm9ySWQSFwoHdXNlcl'
    '9pZBgCIAEoCVIGdXNlcklk');

@$core.Deprecated('Use deleteErrorResponseDescriptor instead')
const DeleteErrorResponse$json = {
  '1': 'DeleteErrorResponse',
  '2': [
    {'1': 'success', '3': 1, '4': 1, '5': 8, '10': 'success'},
  ],
};

/// Descriptor for `DeleteErrorResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List deleteErrorResponseDescriptor = $convert.base64Decode(
    'ChNEZWxldGVFcnJvclJlc3BvbnNlEhgKB3N1Y2Nlc3MYASABKAhSB3N1Y2Nlc3M=');

@$core.Deprecated('Use analyzeErrorRequestDescriptor instead')
const AnalyzeErrorRequest$json = {
  '1': 'AnalyzeErrorRequest',
  '2': [
    {'1': 'error_id', '3': 1, '4': 1, '5': 9, '10': 'errorId'},
    {'1': 'user_id', '3': 2, '4': 1, '5': 9, '10': 'userId'},
  ],
};

/// Descriptor for `AnalyzeErrorRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List analyzeErrorRequestDescriptor = $convert.base64Decode(
    'ChNBbmFseXplRXJyb3JSZXF1ZXN0EhkKCGVycm9yX2lkGAEgASgJUgdlcnJvcklkEhcKB3VzZX'
    'JfaWQYAiABKAlSBnVzZXJJZA==');

@$core.Deprecated('Use analyzeErrorResponseDescriptor instead')
const AnalyzeErrorResponse$json = {
  '1': 'AnalyzeErrorResponse',
  '2': [
    {'1': 'message', '3': 1, '4': 1, '5': 9, '10': 'message'},
  ],
};

/// Descriptor for `AnalyzeErrorResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List analyzeErrorResponseDescriptor = $convert.base64Decode(
    'ChRBbmFseXplRXJyb3JSZXNwb25zZRIYCgdtZXNzYWdlGAEgASgJUgdtZXNzYWdl');

@$core.Deprecated('Use submitReviewRequestDescriptor instead')
const SubmitReviewRequest$json = {
  '1': 'SubmitReviewRequest',
  '2': [
    {'1': 'error_id', '3': 1, '4': 1, '5': 9, '10': 'errorId'},
    {'1': 'user_id', '3': 2, '4': 1, '5': 9, '10': 'userId'},
    {'1': 'performance', '3': 3, '4': 1, '5': 9, '10': 'performance'},
    {'1': 'time_spent_seconds', '3': 4, '4': 1, '5': 5, '10': 'timeSpentSeconds'},
  ],
};

/// Descriptor for `SubmitReviewRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List submitReviewRequestDescriptor = $convert.base64Decode(
    'ChNTdWJtaXRSZXZpZXdSZXF1ZXN0EhkKCGVycm9yX2lkGAEgASgJUgdlcnJvcklkEhcKB3VzZX'
    'JfaWQYAiABKAlSBnVzZXJJZBIgCgtwZXJmb3JtYW5jZRgDIAEoCVILcGVyZm9ybWFuY2USLAoS'
    'dGltZV9zcGVudF9zZWNvbmRzGAQgASgFUhB0aW1lU3BlbnRTZWNvbmRz');

@$core.Deprecated('Use getReviewStatsRequestDescriptor instead')
const GetReviewStatsRequest$json = {
  '1': 'GetReviewStatsRequest',
  '2': [
    {'1': 'user_id', '3': 1, '4': 1, '5': 9, '10': 'userId'},
  ],
};

/// Descriptor for `GetReviewStatsRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List getReviewStatsRequestDescriptor = $convert.base64Decode(
    'ChVHZXRSZXZpZXdTdGF0c1JlcXVlc3QSFwoHdXNlcl9pZBgBIAEoCVIGdXNlcklk');

@$core.Deprecated('Use reviewStatsResponseDescriptor instead')
const ReviewStatsResponse$json = {
  '1': 'ReviewStatsResponse',
  '2': [
    {'1': 'total_errors', '3': 1, '4': 1, '5': 3, '10': 'totalErrors'},
    {'1': 'mastered_count', '3': 2, '4': 1, '5': 3, '10': 'masteredCount'},
    {'1': 'need_review_count', '3': 3, '4': 1, '5': 3, '10': 'needReviewCount'},
    {'1': 'review_streak_days', '3': 4, '4': 1, '5': 5, '10': 'reviewStreakDays'},
    {'1': 'subject_distribution', '3': 5, '4': 3, '5': 11, '6': '.error_book.ReviewStatsResponse.SubjectDistributionEntry', '10': 'subjectDistribution'},
  ],
  '3': [ReviewStatsResponse_SubjectDistributionEntry$json],
};

@$core.Deprecated('Use reviewStatsResponseDescriptor instead')
const ReviewStatsResponse_SubjectDistributionEntry$json = {
  '1': 'SubjectDistributionEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {'1': 'value', '3': 2, '4': 1, '5': 3, '10': 'value'},
  ],
  '7': {'7': true},
};

/// Descriptor for `ReviewStatsResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List reviewStatsResponseDescriptor = $convert.base64Decode(
    'ChNSZXZpZXdTdGF0c1Jlc3BvbnNlEiEKDHRvdGFsX2Vycm9ycxgBIAEoA1ILdG90YWxFcnJvcn'
    'MSJQoObWFzdGVyZWRfY291bnQYAiABKANSDW1hc3RlcmVkQ291bnQSKgoRbmVlZF9yZXZpZXdf'
    'Y291bnQYAyABKANSD25lZWRSZXZpZXdDb3VudBIsChJyZXZpZXdfc3RyZWFrX2RheXMYBCABKA'
    'VSEHJldmlld1N0cmVha0RheXMSawoUc3ViamVjdF9kaXN0cmlidXRpb24YBSADKAsyOC5lcnJv'
    'cl9ib29rLlJldmlld1N0YXRzUmVzcG9uc2UuU3ViamVjdERpc3RyaWJ1dGlvbkVudHJ5UhNzdW'
    'JqZWN0RGlzdHJpYnV0aW9uGkYKGFN1YmplY3REaXN0cmlidXRpb25FbnRyeRIQCgNrZXkYASAB'
    'KAlSA2tleRIUCgV2YWx1ZRgCIAEoA1IFdmFsdWU6AjgB');

@$core.Deprecated('Use getTodayReviewsRequestDescriptor instead')
const GetTodayReviewsRequest$json = {
  '1': 'GetTodayReviewsRequest',
  '2': [
    {'1': 'user_id', '3': 1, '4': 1, '5': 9, '10': 'userId'},
    {'1': 'page', '3': 2, '4': 1, '5': 5, '10': 'page'},
    {'1': 'page_size', '3': 3, '4': 1, '5': 5, '10': 'pageSize'},
  ],
};

/// Descriptor for `GetTodayReviewsRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List getTodayReviewsRequestDescriptor = $convert.base64Decode(
    'ChZHZXRUb2RheVJldmlld3NSZXF1ZXN0EhcKB3VzZXJfaWQYASABKAlSBnVzZXJJZBISCgRwYW'
    'dlGAIgASgFUgRwYWdlEhsKCXBhZ2Vfc2l6ZRgDIAEoBVIIcGFnZVNpemU=');

const $core.Map<$core.String, $core.dynamic> ErrorBookServiceBase$json = {
  '1': 'ErrorBookService',
  '2': [
    {'1': 'CreateError', '2': '.error_book.CreateErrorRequest', '3': '.error_book.ErrorRecord'},
    {'1': 'ListErrors', '2': '.error_book.ListErrorsRequest', '3': '.error_book.ListErrorsResponse'},
    {'1': 'GetError', '2': '.error_book.GetErrorRequest', '3': '.error_book.ErrorRecord'},
    {'1': 'UpdateError', '2': '.error_book.UpdateErrorRequest', '3': '.error_book.ErrorRecord'},
    {'1': 'DeleteError', '2': '.error_book.DeleteErrorRequest', '3': '.error_book.DeleteErrorResponse'},
    {'1': 'AnalyzeError', '2': '.error_book.AnalyzeErrorRequest', '3': '.error_book.AnalyzeErrorResponse'},
    {'1': 'SubmitReview', '2': '.error_book.SubmitReviewRequest', '3': '.error_book.ErrorRecord'},
    {'1': 'GetReviewStats', '2': '.error_book.GetReviewStatsRequest', '3': '.error_book.ReviewStatsResponse'},
    {'1': 'GetTodayReviews', '2': '.error_book.GetTodayReviewsRequest', '3': '.error_book.ListErrorsResponse'},
  ],
};

@$core.Deprecated('Use errorBookServiceDescriptor instead')
const $core.Map<$core.String, $core.Map<$core.String, $core.dynamic>> ErrorBookServiceBase$messageJson = {
  '.error_book.CreateErrorRequest': CreateErrorRequest$json,
  '.error_book.ErrorRecord': ErrorRecord$json,
  '.google.protobuf.Timestamp': $2.Timestamp$json,
  '.error_book.ErrorAnalysisResult': ErrorAnalysisResult$json,
  '.error_book.KnowledgeLinkBrief': KnowledgeLinkBrief$json,
  '.error_book.ListErrorsRequest': ListErrorsRequest$json,
  '.error_book.ListErrorsResponse': ListErrorsResponse$json,
  '.error_book.GetErrorRequest': GetErrorRequest$json,
  '.error_book.UpdateErrorRequest': UpdateErrorRequest$json,
  '.error_book.DeleteErrorRequest': DeleteErrorRequest$json,
  '.error_book.DeleteErrorResponse': DeleteErrorResponse$json,
  '.error_book.AnalyzeErrorRequest': AnalyzeErrorRequest$json,
  '.error_book.AnalyzeErrorResponse': AnalyzeErrorResponse$json,
  '.error_book.SubmitReviewRequest': SubmitReviewRequest$json,
  '.error_book.GetReviewStatsRequest': GetReviewStatsRequest$json,
  '.error_book.ReviewStatsResponse': ReviewStatsResponse$json,
  '.error_book.ReviewStatsResponse.SubjectDistributionEntry': ReviewStatsResponse_SubjectDistributionEntry$json,
  '.error_book.GetTodayReviewsRequest': GetTodayReviewsRequest$json,
};

/// Descriptor for `ErrorBookService`. Decode as a `google.protobuf.ServiceDescriptorProto`.
final $typed_data.Uint8List errorBookServiceDescriptor = $convert.base64Decode(
    'ChBFcnJvckJvb2tTZXJ2aWNlEkYKC0NyZWF0ZUVycm9yEh4uZXJyb3JfYm9vay5DcmVhdGVFcn'
    'JvclJlcXVlc3QaFy5lcnJvcl9ib29rLkVycm9yUmVjb3JkEksKCkxpc3RFcnJvcnMSHS5lcnJv'
    'cl9ib29rLkxpc3RFcnJvcnNSZXF1ZXN0Gh4uZXJyb3JfYm9vay5MaXN0RXJyb3JzUmVzcG9uc2'
    'USQAoIR2V0RXJyb3ISGy5lcnJvcl9ib29rLkdldEVycm9yUmVxdWVzdBoXLmVycm9yX2Jvb2su'
    'RXJyb3JSZWNvcmQSRgoLVXBkYXRlRXJyb3ISHi5lcnJvcl9ib29rLlVwZGF0ZUVycm9yUmVxdW'
    'VzdBoXLmVycm9yX2Jvb2suRXJyb3JSZWNvcmQSTgoLRGVsZXRlRXJyb3ISHi5lcnJvcl9ib29r'
    'LkRlbGV0ZUVycm9yUmVxdWVzdBofLmVycm9yX2Jvb2suRGVsZXRlRXJyb3JSZXNwb25zZRJRCg'
    'xBbmFseXplRXJyb3ISHy5lcnJvcl9ib29rLkFuYWx5emVFcnJvclJlcXVlc3QaIC5lcnJvcl9i'
    'b29rLkFuYWx5emVFcnJvclJlc3BvbnNlEkgKDFN1Ym1pdFJldmlldxIfLmVycm9yX2Jvb2suU3'
    'VibWl0UmV2aWV3UmVxdWVzdBoXLmVycm9yX2Jvb2suRXJyb3JSZWNvcmQSVAoOR2V0UmV2aWV3'
    'U3RhdHMSIS5lcnJvcl9ib29rLkdldFJldmlld1N0YXRzUmVxdWVzdBofLmVycm9yX2Jvb2suUm'
    'V2aWV3U3RhdHNSZXNwb25zZRJVCg9HZXRUb2RheVJldmlld3MSIi5lcnJvcl9ib29rLkdldFRv'
    'ZGF5UmV2aWV3c1JlcXVlc3QaHi5lcnJvcl9ib29rLkxpc3RFcnJvcnNSZXNwb25zZQ==');

