//
//  Generated code. Do not modify.
//  source: google/protobuf/java_features.proto
//
// @dart = 2.12

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_final_fields
// ignore_for_file: unnecessary_import, unnecessary_this, unused_import

import 'dart:convert' as $convert;
import 'dart:core' as $core;
import 'dart:typed_data' as $typed_data;

@$core.Deprecated('Use javaFeaturesDescriptor instead')
const JavaFeatures$json = {
  '1': 'JavaFeatures',
  '2': [
    {'1': 'legacy_closed_enum', '3': 1, '4': 1, '5': 8, '8': {}, '10': 'legacyClosedEnum'},
    {'1': 'utf8_validation', '3': 2, '4': 1, '5': 14, '6': '.pb.JavaFeatures.Utf8Validation', '8': {}, '10': 'utf8Validation'},
    {'1': 'large_enum', '3': 3, '4': 1, '5': 8, '8': {}, '10': 'largeEnum'},
    {'1': 'use_old_outer_classname_default', '3': 4, '4': 1, '5': 8, '8': {}, '10': 'useOldOuterClassnameDefault'},
    {'1': 'nest_in_file_class', '3': 5, '4': 1, '5': 14, '6': '.pb.JavaFeatures.NestInFileClassFeature.NestInFileClass', '8': {}, '10': 'nestInFileClass'},
  ],
  '3': [JavaFeatures_NestInFileClassFeature$json],
  '4': [JavaFeatures_Utf8Validation$json],
  '9': [
    {'1': 6, '2': 7},
  ],
};

@$core.Deprecated('Use javaFeaturesDescriptor instead')
const JavaFeatures_NestInFileClassFeature$json = {
  '1': 'NestInFileClassFeature',
  '4': [JavaFeatures_NestInFileClassFeature_NestInFileClass$json],
  '9': [
    {'1': 1, '2': 536870912},
  ],
};

@$core.Deprecated('Use javaFeaturesDescriptor instead')
const JavaFeatures_NestInFileClassFeature_NestInFileClass$json = {
  '1': 'NestInFileClass',
  '2': [
    {'1': 'NEST_IN_FILE_CLASS_UNKNOWN', '2': 0},
    {'1': 'NO', '2': 1},
    {'1': 'YES', '2': 2},
    {'1': 'LEGACY', '2': 3, '3': {}},
  ],
};

@$core.Deprecated('Use javaFeaturesDescriptor instead')
const JavaFeatures_Utf8Validation$json = {
  '1': 'Utf8Validation',
  '2': [
    {'1': 'UTF8_VALIDATION_UNKNOWN', '2': 0},
    {'1': 'DEFAULT', '2': 1},
    {'1': 'VERIFY', '2': 2},
  ],
};

/// Descriptor for `JavaFeatures`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List javaFeaturesDescriptor = $convert.base64Decode(
    'CgxKYXZhRmVhdHVyZXMSkAIKEmxlZ2FjeV9jbG9zZWRfZW51bRgBIAEoCELhAYgBAZgBBJgBAa'
    'IBCRIEdHJ1ZRiEB6IBChIFZmFsc2UY5weyAbsBCOgHEOgHGrIBVGhlIGxlZ2FjeSBjbG9zZWQg'
    'ZW51bSBiZWhhdmlvciBpbiBKYXZhIGlzIGRlcHJlY2F0ZWQgYW5kIGlzIHNjaGVkdWxlZCB0by'
    'BiZSByZW1vdmVkIGluIGVkaXRpb24gMjAyNS4gIFNlZSBodHRwOi8vcHJvdG9idWYuZGV2L3By'
    'b2dyYW1taW5nLWd1aWRlcy9lbnVtLyNqYXZhIGZvciBtb3JlIGluZm9ybWF0aW9uLlIQbGVnYW'
    'N5Q2xvc2VkRW51bRKvAgoPdXRmOF92YWxpZGF0aW9uGAIgASgOMh8ucGIuSmF2YUZlYXR1cmVz'
    'LlV0ZjhWYWxpZGF0aW9uQuQBiAEBmAEEmAEBogEMEgdERUZBVUxUGIQHsgHIAQjoBxDpBxq/AV'
    'RoZSBKYXZhLXNwZWNpZmljIHV0ZjggdmFsaWRhdGlvbiBmZWF0dXJlIGlzIGRlcHJlY2F0ZWQg'
    'YW5kIGlzIHNjaGVkdWxlZCB0byBiZSByZW1vdmVkIGluIGVkaXRpb24gMjAyNS4gIFV0Zjggdm'
    'FsaWRhdGlvbiBiZWhhdmlvciBzaG91bGQgdXNlIHRoZSBnbG9iYWwgY3Jvc3MtbGFuZ3VhZ2Ug'
    'dXRmOF92YWxpZGF0aW9uIGZlYXR1cmUuUg51dGY4VmFsaWRhdGlvbhI7CgpsYXJnZV9lbnVtGA'
    'MgASgIQhyIAQGYAQaYAQGiAQoSBWZhbHNlGIQHsgEDCOkHUglsYXJnZUVudW0SbgofdXNlX29s'
    'ZF9vdXRlcl9jbGFzc25hbWVfZGVmYXVsdBgEIAEoCEIoiAEBmAEBogEJEgR0cnVlGIQHogEKEg'
    'VmYWxzZRjpB7IBBgjpByDpB1IbdXNlT2xkT3V0ZXJDbGFzc25hbWVEZWZhdWx0EpABChJuZXN0'
    'X2luX2ZpbGVfY2xhc3MYBSABKA4yNy5wYi5KYXZhRmVhdHVyZXMuTmVzdEluRmlsZUNsYXNzRm'
    'VhdHVyZS5OZXN0SW5GaWxlQ2xhc3NCKogBAZgBA5gBBpgBCKIBCxIGTEVHQUNZGIQHogEHEgJO'
    'TxjpB7IBAwjpB1IPbmVzdEluRmlsZUNsYXNzGnwKFk5lc3RJbkZpbGVDbGFzc0ZlYXR1cmUiWA'
    'oPTmVzdEluRmlsZUNsYXNzEh4KGk5FU1RfSU5fRklMRV9DTEFTU19VTktOT1dOEAASBgoCTk8Q'
    'ARIHCgNZRVMQAhIUCgZMRUdBQ1kQAxoIIgYI6Qcg6QdKCAgBEICAgIACIkYKDlV0ZjhWYWxpZG'
    'F0aW9uEhsKF1VURjhfVkFMSURBVElPTl9VTktOT1dOEAASCwoHREVGQVVMVBABEgoKBlZFUklG'
    'WRACSgQIBhAH');

