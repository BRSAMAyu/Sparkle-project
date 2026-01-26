//
//  Generated code. Do not modify.
//  source: sparkle/signals/v1/signals.proto
//
// @dart = 2.12

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_final_fields
// ignore_for_file: unnecessary_import, unnecessary_this, unused_import

import 'dart:convert' as $convert;
import 'dart:core' as $core;
import 'dart:typed_data' as $typed_data;

@$core.Deprecated('Use candidateActionDescriptor instead')
const CandidateAction$json = {
  '1': 'CandidateAction',
  '2': [
    {'1': 'id', '3': 1, '4': 1, '5': 9, '10': 'id'},
    {'1': 'type', '3': 2, '4': 1, '5': 9, '10': 'type'},
    {'1': 'trigger', '3': 3, '4': 1, '5': 9, '10': 'trigger'},
    {'1': 'content_seed', '3': 4, '4': 1, '5': 9, '10': 'contentSeed'},
    {'1': 'priority', '3': 5, '4': 1, '5': 2, '10': 'priority'},
    {'1': 'metadata', '3': 6, '4': 3, '5': 11, '6': '.sparkle.signals.v1.CandidateAction.MetadataEntry', '10': 'metadata'},
  ],
  '3': [CandidateAction_MetadataEntry$json],
};

@$core.Deprecated('Use candidateActionDescriptor instead')
const CandidateAction_MetadataEntry$json = {
  '1': 'MetadataEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {'1': 'value', '3': 2, '4': 1, '5': 9, '10': 'value'},
  ],
  '7': {'7': true},
};

/// Descriptor for `CandidateAction`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List candidateActionDescriptor = $convert.base64Decode(
    'Cg9DYW5kaWRhdGVBY3Rpb24SDgoCaWQYASABKAlSAmlkEhIKBHR5cGUYAiABKAlSBHR5cGUSGA'
    'oHdHJpZ2dlchgDIAEoCVIHdHJpZ2dlchIhCgxjb250ZW50X3NlZWQYBCABKAlSC2NvbnRlbnRT'
    'ZWVkEhoKCHByaW9yaXR5GAUgASgCUghwcmlvcml0eRJNCghtZXRhZGF0YRgGIAMoCzIxLnNwYX'
    'JrbGUuc2lnbmFscy52MS5DYW5kaWRhdGVBY3Rpb24uTWV0YWRhdGFFbnRyeVIIbWV0YWRhdGEa'
    'OwoNTWV0YWRhdGFFbnRyeRIQCgNrZXkYASABKAlSA2tleRIUCgV2YWx1ZRgCIAEoCVIFdmFsdW'
    'U6AjgB');

@$core.Deprecated('Use nextActionsCandidateSetDescriptor instead')
const NextActionsCandidateSet$json = {
  '1': 'NextActionsCandidateSet',
  '2': [
    {'1': 'request_id', '3': 1, '4': 1, '5': 9, '10': 'requestId'},
    {'1': 'trace_id', '3': 2, '4': 1, '5': 9, '10': 'traceId'},
    {'1': 'user_id', '3': 3, '4': 1, '5': 9, '10': 'userId'},
    {'1': 'schema_version', '3': 4, '4': 1, '5': 9, '10': 'schemaVersion'},
    {'1': 'idempotency_key', '3': 5, '4': 1, '5': 9, '10': 'idempotencyKey'},
    {'1': 'candidates', '3': 6, '4': 3, '5': 11, '6': '.sparkle.signals.v1.CandidateAction', '10': 'candidates'},
    {'1': 'metadata', '3': 7, '4': 3, '5': 11, '6': '.sparkle.signals.v1.NextActionsCandidateSet.MetadataEntry', '10': 'metadata'},
  ],
  '3': [NextActionsCandidateSet_MetadataEntry$json],
};

@$core.Deprecated('Use nextActionsCandidateSetDescriptor instead')
const NextActionsCandidateSet_MetadataEntry$json = {
  '1': 'MetadataEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {'1': 'value', '3': 2, '4': 1, '5': 9, '10': 'value'},
  ],
  '7': {'7': true},
};

/// Descriptor for `NextActionsCandidateSet`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List nextActionsCandidateSetDescriptor = $convert.base64Decode(
    'ChdOZXh0QWN0aW9uc0NhbmRpZGF0ZVNldBIdCgpyZXF1ZXN0X2lkGAEgASgJUglyZXF1ZXN0SW'
    'QSGQoIdHJhY2VfaWQYAiABKAlSB3RyYWNlSWQSFwoHdXNlcl9pZBgDIAEoCVIGdXNlcklkEiUK'
    'DnNjaGVtYV92ZXJzaW9uGAQgASgJUg1zY2hlbWFWZXJzaW9uEicKD2lkZW1wb3RlbmN5X2tleR'
    'gFIAEoCVIOaWRlbXBvdGVuY3lLZXkSQwoKY2FuZGlkYXRlcxgGIAMoCzIjLnNwYXJrbGUuc2ln'
    'bmFscy52MS5DYW5kaWRhdGVBY3Rpb25SCmNhbmRpZGF0ZXMSVQoIbWV0YWRhdGEYByADKAsyOS'
    '5zcGFya2xlLnNpZ25hbHMudjEuTmV4dEFjdGlvbnNDYW5kaWRhdGVTZXQuTWV0YWRhdGFFbnRy'
    'eVIIbWV0YWRhdGEaOwoNTWV0YWRhdGFFbnRyeRIQCgNrZXkYASABKAlSA2tleRIUCgV2YWx1ZR'
    'gCIAEoCVIFdmFsdWU6AjgB');

@$core.Deprecated('Use contextEnvelopeDescriptor instead')
const ContextEnvelope$json = {
  '1': 'ContextEnvelope',
  '2': [
    {'1': 'context_version', '3': 1, '4': 1, '5': 9, '10': 'contextVersion'},
    {'1': 'window', '3': 2, '4': 1, '5': 9, '10': 'window'},
    {'1': 'focus', '3': 3, '4': 1, '5': 11, '6': '.sparkle.signals.v1.FocusMetrics', '10': 'focus'},
    {'1': 'comprehension', '3': 4, '4': 1, '5': 11, '6': '.sparkle.signals.v1.ComprehensionMetrics', '10': 'comprehension'},
    {'1': 'time', '3': 5, '4': 1, '5': 11, '6': '.sparkle.signals.v1.TimeContext', '10': 'time'},
    {'1': 'content', '3': 6, '4': 1, '5': 11, '6': '.sparkle.signals.v1.ContentContext', '10': 'content'},
    {'1': 'pii_scrubbed', '3': 7, '4': 1, '5': 8, '10': 'piiScrubbed'},
  ],
};

/// Descriptor for `ContextEnvelope`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List contextEnvelopeDescriptor = $convert.base64Decode(
    'Cg9Db250ZXh0RW52ZWxvcGUSJwoPY29udGV4dF92ZXJzaW9uGAEgASgJUg5jb250ZXh0VmVyc2'
    'lvbhIWCgZ3aW5kb3cYAiABKAlSBndpbmRvdxI2CgVmb2N1cxgDIAEoCzIgLnNwYXJrbGUuc2ln'
    'bmFscy52MS5Gb2N1c01ldHJpY3NSBWZvY3VzEk4KDWNvbXByZWhlbnNpb24YBCABKAsyKC5zcG'
    'Fya2xlLnNpZ25hbHMudjEuQ29tcHJlaGVuc2lvbk1ldHJpY3NSDWNvbXByZWhlbnNpb24SMwoE'
    'dGltZRgFIAEoCzIfLnNwYXJrbGUuc2lnbmFscy52MS5UaW1lQ29udGV4dFIEdGltZRI8Cgdjb2'
    '50ZW50GAYgASgLMiIuc3BhcmtsZS5zaWduYWxzLnYxLkNvbnRlbnRDb250ZXh0Ugdjb250ZW50'
    'EiEKDHBpaV9zY3J1YmJlZBgHIAEoCFILcGlpU2NydWJiZWQ=');

@$core.Deprecated('Use focusMetricsDescriptor instead')
const FocusMetrics$json = {
  '1': 'FocusMetrics',
  '2': [
    {'1': 'planned_min', '3': 1, '4': 1, '5': 5, '10': 'plannedMin'},
    {'1': 'actual_min', '3': 2, '4': 1, '5': 5, '10': 'actualMin'},
    {'1': 'interruptions', '3': 3, '4': 1, '5': 5, '10': 'interruptions'},
    {'1': 'completion', '3': 4, '4': 1, '5': 2, '10': 'completion'},
  ],
};

/// Descriptor for `FocusMetrics`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List focusMetricsDescriptor = $convert.base64Decode(
    'CgxGb2N1c01ldHJpY3MSHwoLcGxhbm5lZF9taW4YASABKAVSCnBsYW5uZWRNaW4SHQoKYWN0dW'
    'FsX21pbhgCIAEoBVIJYWN0dWFsTWluEiQKDWludGVycnVwdGlvbnMYAyABKAVSDWludGVycnVw'
    'dGlvbnMSHgoKY29tcGxldGlvbhgEIAEoAlIKY29tcGxldGlvbg==');

@$core.Deprecated('Use comprehensionMetricsDescriptor instead')
const ComprehensionMetrics$json = {
  '1': 'ComprehensionMetrics',
  '2': [
    {'1': 'translation_requests', '3': 1, '4': 1, '5': 5, '10': 'translationRequests'},
    {'1': 'translation_granularity', '3': 2, '4': 1, '5': 9, '10': 'translationGranularity'},
    {'1': 'unknown_terms_saved', '3': 3, '4': 1, '5': 5, '10': 'unknownTermsSaved'},
  ],
};

/// Descriptor for `ComprehensionMetrics`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List comprehensionMetricsDescriptor = $convert.base64Decode(
    'ChRDb21wcmVoZW5zaW9uTWV0cmljcxIxChR0cmFuc2xhdGlvbl9yZXF1ZXN0cxgBIAEoBVITdH'
    'JhbnNsYXRpb25SZXF1ZXN0cxI3Chd0cmFuc2xhdGlvbl9ncmFudWxhcml0eRgCIAEoCVIWdHJh'
    'bnNsYXRpb25HcmFudWxhcml0eRIuChN1bmtub3duX3Rlcm1zX3NhdmVkGAMgASgFUhF1bmtub3'
    'duVGVybXNTYXZlZA==');

@$core.Deprecated('Use timeContextDescriptor instead')
const TimeContext$json = {
  '1': 'TimeContext',
  '2': [
    {'1': 'local_hour', '3': 1, '4': 1, '5': 5, '10': 'localHour'},
    {'1': 'day_of_week', '3': 2, '4': 1, '5': 9, '10': 'dayOfWeek'},
  ],
};

/// Descriptor for `TimeContext`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List timeContextDescriptor = $convert.base64Decode(
    'CgtUaW1lQ29udGV4dBIdCgpsb2NhbF9ob3VyGAEgASgFUglsb2NhbEhvdXISHgoLZGF5X29mX3'
    'dlZWsYAiABKAlSCWRheU9mV2Vlaw==');

@$core.Deprecated('Use contentContextDescriptor instead')
const ContentContext$json = {
  '1': 'ContentContext',
  '2': [
    {'1': 'language', '3': 1, '4': 1, '5': 9, '10': 'language'},
    {'1': 'domain', '3': 2, '4': 1, '5': 9, '10': 'domain'},
  ],
};

/// Descriptor for `ContentContext`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List contentContextDescriptor = $convert.base64Decode(
    'Cg5Db250ZW50Q29udGV4dBIaCghsYW5ndWFnZRgBIAEoCVIIbGFuZ3VhZ2USFgoGZG9tYWluGA'
    'IgASgJUgZkb21haW4=');

@$core.Deprecated('Use featureExtractResultDescriptor instead')
const FeatureExtractResult$json = {
  '1': 'FeatureExtractResult',
  '2': [
    {'1': 'version', '3': 1, '4': 1, '5': 9, '10': 'version'},
    {'1': 'rhythm', '3': 2, '4': 1, '5': 11, '6': '.sparkle.signals.v1.LearningRhythm', '10': 'rhythm'},
    {'1': 'friction', '3': 3, '4': 1, '5': 11, '6': '.sparkle.signals.v1.UnderstandingFriction', '10': 'friction'},
    {'1': 'energy', '3': 4, '4': 1, '5': 11, '6': '.sparkle.signals.v1.EnergyState', '10': 'energy'},
    {'1': 'risk', '3': 5, '4': 1, '5': 11, '6': '.sparkle.signals.v1.TaskRisk', '10': 'risk'},
  ],
};

/// Descriptor for `FeatureExtractResult`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List featureExtractResultDescriptor = $convert.base64Decode(
    'ChRGZWF0dXJlRXh0cmFjdFJlc3VsdBIYCgd2ZXJzaW9uGAEgASgJUgd2ZXJzaW9uEjoKBnJoeX'
    'RobRgCIAEoCzIiLnNwYXJrbGUuc2lnbmFscy52MS5MZWFybmluZ1JoeXRobVIGcmh5dGhtEkUK'
    'CGZyaWN0aW9uGAMgASgLMikuc3BhcmtsZS5zaWduYWxzLnYxLlVuZGVyc3RhbmRpbmdGcmljdG'
    'lvblIIZnJpY3Rpb24SNwoGZW5lcmd5GAQgASgLMh8uc3BhcmtsZS5zaWduYWxzLnYxLkVuZXJn'
    'eVN0YXRlUgZlbmVyZ3kSMAoEcmlzaxgFIAEoCzIcLnNwYXJrbGUuc2lnbmFscy52MS5UYXNrUm'
    'lza1IEcmlzaw==');

@$core.Deprecated('Use learningRhythmDescriptor instead')
const LearningRhythm$json = {
  '1': 'LearningRhythm',
  '2': [
    {'1': 'deviating_from_plan', '3': 1, '4': 1, '5': 8, '10': 'deviatingFromPlan'},
    {'1': 'interruption_frequency', '3': 2, '4': 1, '5': 5, '10': 'interruptionFrequency'},
  ],
};

/// Descriptor for `LearningRhythm`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List learningRhythmDescriptor = $convert.base64Decode(
    'Cg5MZWFybmluZ1JoeXRobRIuChNkZXZpYXRpbmdfZnJvbV9wbGFuGAEgASgIUhFkZXZpYXRpbm'
    'dGcm9tUGxhbhI1ChZpbnRlcnJ1cHRpb25fZnJlcXVlbmN5GAIgASgFUhVpbnRlcnJ1cHRpb25G'
    'cmVxdWVuY3k=');

@$core.Deprecated('Use understandingFrictionDescriptor instead')
const UnderstandingFriction$json = {
  '1': 'UnderstandingFriction',
  '2': [
    {'1': 'translation_density', '3': 1, '4': 1, '5': 5, '10': 'translationDensity'},
    {'1': 'escalating_granularity', '3': 2, '4': 1, '5': 8, '10': 'escalatingGranularity'},
  ],
};

/// Descriptor for `UnderstandingFriction`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List understandingFrictionDescriptor = $convert.base64Decode(
    'ChVVbmRlcnN0YW5kaW5nRnJpY3Rpb24SLwoTdHJhbnNsYXRpb25fZGVuc2l0eRgBIAEoBVISdH'
    'JhbnNsYXRpb25EZW5zaXR5EjUKFmVzY2FsYXRpbmdfZ3JhbnVsYXJpdHkYAiABKAhSFWVzY2Fs'
    'YXRpbmdHcmFudWxhcml0eQ==');

@$core.Deprecated('Use energyStateDescriptor instead')
const EnergyState$json = {
  '1': 'EnergyState',
  '2': [
    {'1': 'late_night_fatigue', '3': 1, '4': 1, '5': 8, '10': 'lateNightFatigue'},
    {'1': 'short_session_trend', '3': 2, '4': 1, '5': 8, '10': 'shortSessionTrend'},
  ],
};

/// Descriptor for `EnergyState`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List energyStateDescriptor = $convert.base64Decode(
    'CgtFbmVyZ3lTdGF0ZRIsChJsYXRlX25pZ2h0X2ZhdGlndWUYASABKAhSEGxhdGVOaWdodEZhdG'
    'lndWUSLgoTc2hvcnRfc2Vzc2lvbl90cmVuZBgCIAEoCFIRc2hvcnRTZXNzaW9uVHJlbmQ=');

@$core.Deprecated('Use taskRiskDescriptor instead')
const TaskRisk$json = {
  '1': 'TaskRisk',
  '2': [
    {'1': 'consecutive_failures', '3': 1, '4': 1, '5': 8, '10': 'consecutiveFailures'},
    {'1': 'procrastination_detected', '3': 2, '4': 1, '5': 8, '10': 'procrastinationDetected'},
  ],
};

/// Descriptor for `TaskRisk`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List taskRiskDescriptor = $convert.base64Decode(
    'CghUYXNrUmlzaxIxChRjb25zZWN1dGl2ZV9mYWlsdXJlcxgBIAEoCFITY29uc2VjdXRpdmVGYW'
    'lsdXJlcxI5Chhwcm9jcmFzdGluYXRpb25fZGV0ZWN0ZWQYAiABKAhSF3Byb2NyYXN0aW5hdGlv'
    'bkRldGVjdGVk');

@$core.Deprecated('Use signalsDescriptor instead')
const Signals$json = {
  '1': 'Signals',
  '2': [
    {'1': 'version', '3': 1, '4': 1, '5': 9, '10': 'version'},
    {'1': 'signals', '3': 2, '4': 3, '5': 11, '6': '.sparkle.signals.v1.Signal', '10': 'signals'},
  ],
};

/// Descriptor for `Signals`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List signalsDescriptor = $convert.base64Decode(
    'CgdTaWduYWxzEhgKB3ZlcnNpb24YASABKAlSB3ZlcnNpb24SNAoHc2lnbmFscxgCIAMoCzIaLn'
    'NwYXJrbGUuc2lnbmFscy52MS5TaWduYWxSB3NpZ25hbHM=');

@$core.Deprecated('Use signalDescriptor instead')
const Signal$json = {
  '1': 'Signal',
  '2': [
    {'1': 'type', '3': 1, '4': 1, '5': 9, '10': 'type'},
    {'1': 'confidence', '3': 2, '4': 1, '5': 2, '10': 'confidence'},
    {'1': 'reason', '3': 3, '4': 1, '5': 9, '10': 'reason'},
    {'1': 'metadata', '3': 4, '4': 3, '5': 11, '6': '.sparkle.signals.v1.Signal.MetadataEntry', '10': 'metadata'},
  ],
  '3': [Signal_MetadataEntry$json],
};

@$core.Deprecated('Use signalDescriptor instead')
const Signal_MetadataEntry$json = {
  '1': 'MetadataEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {'1': 'value', '3': 2, '4': 1, '5': 9, '10': 'value'},
  ],
  '7': {'7': true},
};

/// Descriptor for `Signal`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List signalDescriptor = $convert.base64Decode(
    'CgZTaWduYWwSEgoEdHlwZRgBIAEoCVIEdHlwZRIeCgpjb25maWRlbmNlGAIgASgCUgpjb25maW'
    'RlbmNlEhYKBnJlYXNvbhgDIAEoCVIGcmVhc29uEkQKCG1ldGFkYXRhGAQgAygLMiguc3Bhcmts'
    'ZS5zaWduYWxzLnYxLlNpZ25hbC5NZXRhZGF0YUVudHJ5UghtZXRhZGF0YRo7Cg1NZXRhZGF0YU'
    'VudHJ5EhAKA2tleRgBIAEoCVIDa2V5EhQKBXZhbHVlGAIgASgJUgV2YWx1ZToCOAE=');

@$core.Deprecated('Use candidateActionV2Descriptor instead')
const CandidateActionV2$json = {
  '1': 'CandidateActionV2',
  '2': [
    {'1': 'id', '3': 1, '4': 1, '5': 9, '10': 'id'},
    {'1': 'action_type', '3': 2, '4': 1, '5': 9, '10': 'actionType'},
    {'1': 'title', '3': 3, '4': 1, '5': 9, '10': 'title'},
    {'1': 'reason', '3': 4, '4': 1, '5': 9, '10': 'reason'},
    {'1': 'confidence', '3': 5, '4': 1, '5': 2, '10': 'confidence'},
    {'1': 'timing_hint', '3': 6, '4': 1, '5': 9, '10': 'timingHint'},
    {'1': 'payload_seed', '3': 7, '4': 1, '5': 9, '10': 'payloadSeed'},
    {'1': 'metadata', '3': 8, '4': 3, '5': 11, '6': '.sparkle.signals.v1.CandidateActionV2.MetadataEntry', '10': 'metadata'},
  ],
  '3': [CandidateActionV2_MetadataEntry$json],
};

@$core.Deprecated('Use candidateActionV2Descriptor instead')
const CandidateActionV2_MetadataEntry$json = {
  '1': 'MetadataEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {'1': 'value', '3': 2, '4': 1, '5': 9, '10': 'value'},
  ],
  '7': {'7': true},
};

/// Descriptor for `CandidateActionV2`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List candidateActionV2Descriptor = $convert.base64Decode(
    'ChFDYW5kaWRhdGVBY3Rpb25WMhIOCgJpZBgBIAEoCVICaWQSHwoLYWN0aW9uX3R5cGUYAiABKA'
    'lSCmFjdGlvblR5cGUSFAoFdGl0bGUYAyABKAlSBXRpdGxlEhYKBnJlYXNvbhgEIAEoCVIGcmVh'
    'c29uEh4KCmNvbmZpZGVuY2UYBSABKAJSCmNvbmZpZGVuY2USHwoLdGltaW5nX2hpbnQYBiABKA'
    'lSCnRpbWluZ0hpbnQSIQoMcGF5bG9hZF9zZWVkGAcgASgJUgtwYXlsb2FkU2VlZBJPCghtZXRh'
    'ZGF0YRgIIAMoCzIzLnNwYXJrbGUuc2lnbmFscy52MS5DYW5kaWRhdGVBY3Rpb25WMi5NZXRhZG'
    'F0YUVudHJ5UghtZXRhZGF0YRo7Cg1NZXRhZGF0YUVudHJ5EhAKA2tleRgBIAEoCVIDa2V5EhQK'
    'BXZhbHVlGAIgASgJUgV2YWx1ZToCOAE=');

