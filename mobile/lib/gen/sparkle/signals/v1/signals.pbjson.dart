// This is a generated file - do not edit.
//
// Generated from sparkle/signals/v1/signals.proto.

// @dart = 3.3

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names
// ignore_for_file: curly_braces_in_flow_control_structures
// ignore_for_file: deprecated_member_use_from_same_package, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_relative_imports
// ignore_for_file: unused_import

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
    {
      '1': 'metadata',
      '3': 6,
      '4': 3,
      '5': 11,
      '6': '.sparkle.signals.v1.CandidateAction.MetadataEntry',
      '10': 'metadata'
    },
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
    {
      '1': 'candidates',
      '3': 6,
      '4': 3,
      '5': 11,
      '6': '.sparkle.signals.v1.CandidateAction',
      '10': 'candidates'
    },
    {
      '1': 'metadata',
      '3': 7,
      '4': 3,
      '5': 11,
      '6': '.sparkle.signals.v1.NextActionsCandidateSet.MetadataEntry',
      '10': 'metadata'
    },
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
