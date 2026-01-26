//
//  Generated code. Do not modify.
//  source: sparkle/inference/v1/inference.proto
//
// @dart = 2.12

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_final_fields
// ignore_for_file: unnecessary_import, unnecessary_this, unused_import

import 'dart:convert' as $convert;
import 'dart:core' as $core;
import 'dart:typed_data' as $typed_data;

@$core.Deprecated('Use taskTypeDescriptor instead')
const TaskType$json = {
  '1': 'TaskType',
  '2': [
    {'1': 'TASK_TYPE_UNSPECIFIED', '2': 0},
    {'1': 'SHORT_INFERENCE', '2': 1},
    {'1': 'HEAVY_JOB', '2': 2},
    {'1': 'SIGNAL_EXTRACTION', '2': 3},
    {'1': 'OCR', '2': 4},
    {'1': 'TRANSLATE', '2': 5},
    {'1': 'EMBEDDING', '2': 6},
    {'1': 'RERANK', '2': 7},
    {'1': 'PREDICT_NEXT_ACTIONS', '2': 8},
    {'1': 'VERIFY_PLAN', '2': 9},
  ],
};

/// Descriptor for `TaskType`. Decode as a `google.protobuf.EnumDescriptorProto`.
final $typed_data.Uint8List taskTypeDescriptor = $convert.base64Decode(
    'CghUYXNrVHlwZRIZChVUQVNLX1RZUEVfVU5TUEVDSUZJRUQQABITCg9TSE9SVF9JTkZFUkVOQ0'
    'UQARINCglIRUFWWV9KT0IQAhIVChFTSUdOQUxfRVhUUkFDVElPThADEgcKA09DUhAEEg0KCVRS'
    'QU5TTEFURRAFEg0KCUVNQkVERElORxAGEgoKBlJFUkFOSxAHEhgKFFBSRURJQ1RfTkVYVF9BQ1'
    'RJT05TEAgSDwoLVkVSSUZZX1BMQU4QCQ==');

@$core.Deprecated('Use priorityDescriptor instead')
const Priority$json = {
  '1': 'Priority',
  '2': [
    {'1': 'PRIORITY_UNSPECIFIED', '2': 0},
    {'1': 'P0', '2': 1},
    {'1': 'P1', '2': 2},
    {'1': 'P2', '2': 3},
  ],
};

/// Descriptor for `Priority`. Decode as a `google.protobuf.EnumDescriptorProto`.
final $typed_data.Uint8List priorityDescriptor = $convert.base64Decode(
    'CghQcmlvcml0eRIYChRQUklPUklUWV9VTlNQRUNJRklFRBAAEgYKAlAwEAESBgoCUDEQAhIGCg'
    'JQMhAD');

@$core.Deprecated('Use responseFormatDescriptor instead')
const ResponseFormat$json = {
  '1': 'ResponseFormat',
  '2': [
    {'1': 'RESPONSE_FORMAT_UNSPECIFIED', '2': 0},
    {'1': 'JSON_OBJECT', '2': 1},
    {'1': 'TEXT', '2': 2},
  ],
};

/// Descriptor for `ResponseFormat`. Decode as a `google.protobuf.EnumDescriptorProto`.
final $typed_data.Uint8List responseFormatDescriptor = $convert.base64Decode(
    'Cg5SZXNwb25zZUZvcm1hdBIfChtSRVNQT05TRV9GT1JNQVRfVU5TUEVDSUZJRUQQABIPCgtKU0'
    '9OX09CSkVDVBABEggKBFRFWFQQAg==');

@$core.Deprecated('Use errorReasonDescriptor instead')
const ErrorReason$json = {
  '1': 'ErrorReason',
  '2': [
    {'1': 'ERROR_REASON_UNSPECIFIED', '2': 0},
    {'1': 'QUOTA_EXCEEDED', '2': 1},
    {'1': 'PROVIDER_UNAVAILABLE', '2': 2},
    {'1': 'SCHEMA_VIOLATION', '2': 3},
    {'1': 'BUDGET_EXHAUSTED', '2': 4},
    {'1': 'TIMEOUT', '2': 5},
  ],
};

/// Descriptor for `ErrorReason`. Decode as a `google.protobuf.EnumDescriptorProto`.
final $typed_data.Uint8List errorReasonDescriptor = $convert.base64Decode(
    'CgtFcnJvclJlYXNvbhIcChhFUlJPUl9SRUFTT05fVU5TUEVDSUZJRUQQABISCg5RVU9UQV9FWE'
    'NFRURFRBABEhgKFFBST1ZJREVSX1VOQVZBSUxBQkxFEAISFAoQU0NIRU1BX1ZJT0xBVElPThAD'
    'EhQKEEJVREdFVF9FWEhBVVNURUQQBBILCgdUSU1FT1VUEAU=');

@$core.Deprecated('Use artifactScopeDescriptor instead')
const ArtifactScope$json = {
  '1': 'ArtifactScope',
  '2': [
    {'1': 'ARTIFACT_SCOPE_UNSPECIFIED', '2': 0},
    {'1': 'PRIVATE', '2': 1},
    {'1': 'SHARED', '2': 2},
    {'1': 'PUBLIC', '2': 3},
  ],
};

/// Descriptor for `ArtifactScope`. Decode as a `google.protobuf.EnumDescriptorProto`.
final $typed_data.Uint8List artifactScopeDescriptor = $convert.base64Decode(
    'Cg1BcnRpZmFjdFNjb3BlEh4KGkFSVElGQUNUX1NDT1BFX1VOU1BFQ0lGSUVEEAASCwoHUFJJVk'
    'FURRABEgoKBlNIQVJFRBACEgoKBlBVQkxJQxAD');

@$core.Deprecated('Use messageDescriptor instead')
const Message$json = {
  '1': 'Message',
  '2': [
    {'1': 'role', '3': 1, '4': 1, '5': 9, '10': 'role'},
    {'1': 'content', '3': 2, '4': 1, '5': 9, '10': 'content'},
  ],
};

/// Descriptor for `Message`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List messageDescriptor = $convert.base64Decode(
    'CgdNZXNzYWdlEhIKBHJvbGUYASABKAlSBHJvbGUSGAoHY29udGVudBgCIAEoCVIHY29udGVudA'
    '==');

@$core.Deprecated('Use toolDefinitionDescriptor instead')
const ToolDefinition$json = {
  '1': 'ToolDefinition',
  '2': [
    {'1': 'name', '3': 1, '4': 1, '5': 9, '10': 'name'},
    {'1': 'description', '3': 2, '4': 1, '5': 9, '10': 'description'},
    {'1': 'schema_json', '3': 3, '4': 1, '5': 9, '10': 'schemaJson'},
  ],
};

/// Descriptor for `ToolDefinition`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List toolDefinitionDescriptor = $convert.base64Decode(
    'Cg5Ub29sRGVmaW5pdGlvbhISCgRuYW1lGAEgASgJUgRuYW1lEiAKC2Rlc2NyaXB0aW9uGAIgAS'
    'gJUgtkZXNjcmlwdGlvbhIfCgtzY2hlbWFfanNvbhgDIAEoCVIKc2NoZW1hSnNvbg==');

@$core.Deprecated('Use budgetsDescriptor instead')
const Budgets$json = {
  '1': 'Budgets',
  '2': [
    {'1': 'max_output_tokens', '3': 1, '4': 1, '5': 13, '10': 'maxOutputTokens'},
    {'1': 'max_input_tokens', '3': 2, '4': 1, '5': 13, '10': 'maxInputTokens'},
    {'1': 'max_cost_level', '3': 3, '4': 1, '5': 9, '10': 'maxCostLevel'},
  ],
};

/// Descriptor for `Budgets`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List budgetsDescriptor = $convert.base64Decode(
    'CgdCdWRnZXRzEioKEW1heF9vdXRwdXRfdG9rZW5zGAEgASgNUg9tYXhPdXRwdXRUb2tlbnMSKA'
    'oQbWF4X2lucHV0X3Rva2VucxgCIAEoDVIObWF4SW5wdXRUb2tlbnMSJAoObWF4X2Nvc3RfbGV2'
    'ZWwYAyABKAlSDG1heENvc3RMZXZlbA==');

@$core.Deprecated('Use inferenceRequestDescriptor instead')
const InferenceRequest$json = {
  '1': 'InferenceRequest',
  '2': [
    {'1': 'request_id', '3': 1, '4': 1, '5': 9, '10': 'requestId'},
    {'1': 'trace_id', '3': 2, '4': 1, '5': 9, '10': 'traceId'},
    {'1': 'user_id', '3': 3, '4': 1, '5': 9, '10': 'userId'},
    {'1': 'task_type', '3': 4, '4': 1, '5': 14, '6': '.sparkle.inference.v1.TaskType', '10': 'taskType'},
    {'1': 'priority', '3': 5, '4': 1, '5': 14, '6': '.sparkle.inference.v1.Priority', '10': 'priority'},
    {'1': 'schema_version', '3': 6, '4': 1, '5': 9, '10': 'schemaVersion'},
    {'1': 'output_schema', '3': 7, '4': 1, '5': 9, '10': 'outputSchema'},
    {'1': 'prompt_version', '3': 8, '4': 1, '5': 9, '10': 'promptVersion'},
    {'1': 'idempotency_key', '3': 9, '4': 1, '5': 9, '10': 'idempotencyKey'},
    {'1': 'budgets', '3': 10, '4': 1, '5': 11, '6': '.sparkle.inference.v1.Budgets', '10': 'budgets'},
    {'1': 'messages', '3': 11, '4': 3, '5': 11, '6': '.sparkle.inference.v1.Message', '10': 'messages'},
    {'1': 'tools', '3': 12, '4': 3, '5': 11, '6': '.sparkle.inference.v1.ToolDefinition', '10': 'tools'},
    {'1': 'response_format', '3': 13, '4': 1, '5': 14, '6': '.sparkle.inference.v1.ResponseFormat', '10': 'responseFormat'},
    {'1': 'metadata', '3': 14, '4': 3, '5': 11, '6': '.sparkle.inference.v1.InferenceRequest.MetadataEntry', '10': 'metadata'},
    {'1': 'file_ids', '3': 15, '4': 3, '5': 9, '10': 'fileIds'},
    {'1': 'artifact_scope', '3': 16, '4': 1, '5': 14, '6': '.sparkle.inference.v1.ArtifactScope', '10': 'artifactScope'},
  ],
  '3': [InferenceRequest_MetadataEntry$json],
};

@$core.Deprecated('Use inferenceRequestDescriptor instead')
const InferenceRequest_MetadataEntry$json = {
  '1': 'MetadataEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {'1': 'value', '3': 2, '4': 1, '5': 9, '10': 'value'},
  ],
  '7': {'7': true},
};

/// Descriptor for `InferenceRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List inferenceRequestDescriptor = $convert.base64Decode(
    'ChBJbmZlcmVuY2VSZXF1ZXN0Eh0KCnJlcXVlc3RfaWQYASABKAlSCXJlcXVlc3RJZBIZCgh0cm'
    'FjZV9pZBgCIAEoCVIHdHJhY2VJZBIXCgd1c2VyX2lkGAMgASgJUgZ1c2VySWQSOwoJdGFza190'
    'eXBlGAQgASgOMh4uc3BhcmtsZS5pbmZlcmVuY2UudjEuVGFza1R5cGVSCHRhc2tUeXBlEjoKCH'
    'ByaW9yaXR5GAUgASgOMh4uc3BhcmtsZS5pbmZlcmVuY2UudjEuUHJpb3JpdHlSCHByaW9yaXR5'
    'EiUKDnNjaGVtYV92ZXJzaW9uGAYgASgJUg1zY2hlbWFWZXJzaW9uEiMKDW91dHB1dF9zY2hlbW'
    'EYByABKAlSDG91dHB1dFNjaGVtYRIlCg5wcm9tcHRfdmVyc2lvbhgIIAEoCVINcHJvbXB0VmVy'
    'c2lvbhInCg9pZGVtcG90ZW5jeV9rZXkYCSABKAlSDmlkZW1wb3RlbmN5S2V5EjcKB2J1ZGdldH'
    'MYCiABKAsyHS5zcGFya2xlLmluZmVyZW5jZS52MS5CdWRnZXRzUgdidWRnZXRzEjkKCG1lc3Nh'
    'Z2VzGAsgAygLMh0uc3BhcmtsZS5pbmZlcmVuY2UudjEuTWVzc2FnZVIIbWVzc2FnZXMSOgoFdG'
    '9vbHMYDCADKAsyJC5zcGFya2xlLmluZmVyZW5jZS52MS5Ub29sRGVmaW5pdGlvblIFdG9vbHMS'
    'TQoPcmVzcG9uc2VfZm9ybWF0GA0gASgOMiQuc3BhcmtsZS5pbmZlcmVuY2UudjEuUmVzcG9uc2'
    'VGb3JtYXRSDnJlc3BvbnNlRm9ybWF0ElAKCG1ldGFkYXRhGA4gAygLMjQuc3BhcmtsZS5pbmZl'
    'cmVuY2UudjEuSW5mZXJlbmNlUmVxdWVzdC5NZXRhZGF0YUVudHJ5UghtZXRhZGF0YRIZCghmaW'
    'xlX2lkcxgPIAMoCVIHZmlsZUlkcxJKCg5hcnRpZmFjdF9zY29wZRgQIAEoDjIjLnNwYXJrbGUu'
    'aW5mZXJlbmNlLnYxLkFydGlmYWN0U2NvcGVSDWFydGlmYWN0U2NvcGUaOwoNTWV0YWRhdGFFbn'
    'RyeRIQCgNrZXkYASABKAlSA2tleRIUCgV2YWx1ZRgCIAEoCVIFdmFsdWU6AjgB');

@$core.Deprecated('Use inferenceResponseDescriptor instead')
const InferenceResponse$json = {
  '1': 'InferenceResponse',
  '2': [
    {'1': 'request_id', '3': 1, '4': 1, '5': 9, '10': 'requestId'},
    {'1': 'trace_id', '3': 2, '4': 1, '5': 9, '10': 'traceId'},
    {'1': 'ok', '3': 3, '4': 1, '5': 8, '10': 'ok'},
    {'1': 'provider', '3': 4, '4': 1, '5': 9, '10': 'provider'},
    {'1': 'model_id', '3': 5, '4': 1, '5': 9, '10': 'modelId'},
    {'1': 'content', '3': 6, '4': 1, '5': 9, '10': 'content'},
    {'1': 'error_reason', '3': 7, '4': 1, '5': 14, '6': '.sparkle.inference.v1.ErrorReason', '10': 'errorReason'},
    {'1': 'error_message', '3': 8, '4': 1, '5': 9, '10': 'errorMessage'},
    {'1': 'prompt_tokens', '3': 9, '4': 1, '5': 13, '10': 'promptTokens'},
    {'1': 'completion_tokens', '3': 10, '4': 1, '5': 13, '10': 'completionTokens'},
  ],
};

/// Descriptor for `InferenceResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List inferenceResponseDescriptor = $convert.base64Decode(
    'ChFJbmZlcmVuY2VSZXNwb25zZRIdCgpyZXF1ZXN0X2lkGAEgASgJUglyZXF1ZXN0SWQSGQoIdH'
    'JhY2VfaWQYAiABKAlSB3RyYWNlSWQSDgoCb2sYAyABKAhSAm9rEhoKCHByb3ZpZGVyGAQgASgJ'
    'Ughwcm92aWRlchIZCghtb2RlbF9pZBgFIAEoCVIHbW9kZWxJZBIYCgdjb250ZW50GAYgASgJUg'
    'djb250ZW50EkQKDGVycm9yX3JlYXNvbhgHIAEoDjIhLnNwYXJrbGUuaW5mZXJlbmNlLnYxLkVy'
    'cm9yUmVhc29uUgtlcnJvclJlYXNvbhIjCg1lcnJvcl9tZXNzYWdlGAggASgJUgxlcnJvck1lc3'
    'NhZ2USIwoNcHJvbXB0X3Rva2VucxgJIAEoDVIMcHJvbXB0VG9rZW5zEisKEWNvbXBsZXRpb25f'
    'dG9rZW5zGAogASgNUhBjb21wbGV0aW9uVG9rZW5z');

@$core.Deprecated('Use translationSegmentDescriptor instead')
const TranslationSegment$json = {
  '1': 'TranslationSegment',
  '2': [
    {'1': 'id', '3': 1, '4': 1, '5': 9, '10': 'id'},
    {'1': 'text', '3': 2, '4': 1, '5': 9, '10': 'text'},
  ],
};

/// Descriptor for `TranslationSegment`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List translationSegmentDescriptor = $convert.base64Decode(
    'ChJUcmFuc2xhdGlvblNlZ21lbnQSDgoCaWQYASABKAlSAmlkEhIKBHRleHQYAiABKAlSBHRleH'
    'Q=');

@$core.Deprecated('Use translationInputDescriptor instead')
const TranslationInput$json = {
  '1': 'TranslationInput',
  '2': [
    {'1': 'segments', '3': 1, '4': 3, '5': 11, '6': '.sparkle.inference.v1.TranslationSegment', '10': 'segments'},
    {'1': 'source_lang', '3': 2, '4': 1, '5': 9, '10': 'sourceLang'},
    {'1': 'target_lang', '3': 3, '4': 1, '5': 9, '10': 'targetLang'},
    {'1': 'domain', '3': 4, '4': 1, '5': 9, '10': 'domain'},
    {'1': 'style', '3': 5, '4': 1, '5': 9, '10': 'style'},
    {'1': 'glossary_id', '3': 6, '4': 1, '5': 9, '10': 'glossaryId'},
    {'1': 'segmenter_version', '3': 7, '4': 1, '5': 9, '10': 'segmenterVersion'},
  ],
};

/// Descriptor for `TranslationInput`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List translationInputDescriptor = $convert.base64Decode(
    'ChBUcmFuc2xhdGlvbklucHV0EkQKCHNlZ21lbnRzGAEgAygLMiguc3BhcmtsZS5pbmZlcmVuY2'
    'UudjEuVHJhbnNsYXRpb25TZWdtZW50UghzZWdtZW50cxIfCgtzb3VyY2VfbGFuZxgCIAEoCVIK'
    'c291cmNlTGFuZxIfCgt0YXJnZXRfbGFuZxgDIAEoCVIKdGFyZ2V0TGFuZxIWCgZkb21haW4YBC'
    'ABKAlSBmRvbWFpbhIUCgVzdHlsZRgFIAEoCVIFc3R5bGUSHwoLZ2xvc3NhcnlfaWQYBiABKAlS'
    'Cmdsb3NzYXJ5SWQSKwoRc2VnbWVudGVyX3ZlcnNpb24YByABKAlSEHNlZ21lbnRlclZlcnNpb2'
    '4=');

@$core.Deprecated('Use alignmentSpanDescriptor instead')
const AlignmentSpan$json = {
  '1': 'AlignmentSpan',
  '2': [
    {'1': 'source_start', '3': 1, '4': 1, '5': 5, '10': 'sourceStart'},
    {'1': 'source_end', '3': 2, '4': 1, '5': 5, '10': 'sourceEnd'},
    {'1': 'target_start', '3': 3, '4': 1, '5': 5, '10': 'targetStart'},
    {'1': 'target_end', '3': 4, '4': 1, '5': 5, '10': 'targetEnd'},
    {'1': 'type', '3': 5, '4': 1, '5': 9, '10': 'type'},
  ],
};

/// Descriptor for `AlignmentSpan`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List alignmentSpanDescriptor = $convert.base64Decode(
    'Cg1BbGlnbm1lbnRTcGFuEiEKDHNvdXJjZV9zdGFydBgBIAEoBVILc291cmNlU3RhcnQSHQoKc2'
    '91cmNlX2VuZBgCIAEoBVIJc291cmNlRW5kEiEKDHRhcmdldF9zdGFydBgDIAEoBVILdGFyZ2V0'
    'U3RhcnQSHQoKdGFyZ2V0X2VuZBgEIAEoBVIJdGFyZ2V0RW5kEhIKBHR5cGUYBSABKAlSBHR5cG'
    'U=');

@$core.Deprecated('Use translatedSegmentDescriptor instead')
const TranslatedSegment$json = {
  '1': 'TranslatedSegment',
  '2': [
    {'1': 'id', '3': 1, '4': 1, '5': 9, '10': 'id'},
    {'1': 'translation', '3': 2, '4': 1, '5': 9, '10': 'translation'},
    {'1': 'notes', '3': 3, '4': 3, '5': 9, '10': 'notes'},
    {'1': 'spans', '3': 4, '4': 3, '5': 11, '6': '.sparkle.inference.v1.AlignmentSpan', '10': 'spans'},
  ],
};

/// Descriptor for `TranslatedSegment`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List translatedSegmentDescriptor = $convert.base64Decode(
    'ChFUcmFuc2xhdGVkU2VnbWVudBIOCgJpZBgBIAEoCVICaWQSIAoLdHJhbnNsYXRpb24YAiABKA'
    'lSC3RyYW5zbGF0aW9uEhQKBW5vdGVzGAMgAygJUgVub3RlcxI5CgVzcGFucxgEIAMoCzIjLnNw'
    'YXJrbGUuaW5mZXJlbmNlLnYxLkFsaWdubWVudFNwYW5SBXNwYW5z');

@$core.Deprecated('Use translationOutputDescriptor instead')
const TranslationOutput$json = {
  '1': 'TranslationOutput',
  '2': [
    {'1': 'segments', '3': 1, '4': 3, '5': 11, '6': '.sparkle.inference.v1.TranslatedSegment', '10': 'segments'},
    {'1': 'provider', '3': 2, '4': 1, '5': 9, '10': 'provider'},
    {'1': 'model_id', '3': 3, '4': 1, '5': 9, '10': 'modelId'},
    {'1': 'cache_hit', '3': 4, '4': 1, '5': 8, '10': 'cacheHit'},
    {'1': 'latency_ms', '3': 5, '4': 1, '5': 5, '10': 'latencyMs'},
  ],
};

/// Descriptor for `TranslationOutput`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List translationOutputDescriptor = $convert.base64Decode(
    'ChFUcmFuc2xhdGlvbk91dHB1dBJDCghzZWdtZW50cxgBIAMoCzInLnNwYXJrbGUuaW5mZXJlbm'
    'NlLnYxLlRyYW5zbGF0ZWRTZWdtZW50UghzZWdtZW50cxIaCghwcm92aWRlchgCIAEoCVIIcHJv'
    'dmlkZXISGQoIbW9kZWxfaWQYAyABKAlSB21vZGVsSWQSGwoJY2FjaGVfaGl0GAQgASgIUghjYW'
    'NoZUhpdBIdCgpsYXRlbmN5X21zGAUgASgFUglsYXRlbmN5TXM=');

