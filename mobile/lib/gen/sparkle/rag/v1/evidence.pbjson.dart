//
//  Generated code. Do not modify.
//  source: sparkle/rag/v1/evidence.proto
//
// @dart = 2.12

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_final_fields
// ignore_for_file: unnecessary_import, unnecessary_this, unused_import

import 'dart:convert' as $convert;
import 'dart:core' as $core;
import 'dart:typed_data' as $typed_data;

@$core.Deprecated('Use evidenceNodeDescriptor instead')
const EvidenceNode$json = {
  '1': 'EvidenceNode',
  '2': [
    {'1': 'node_id', '3': 1, '4': 1, '5': 9, '10': 'nodeId'},
    {'1': 'source_id', '3': 2, '4': 1, '5': 9, '10': 'sourceId'},
    {'1': 'snippet', '3': 3, '4': 1, '5': 9, '10': 'snippet'},
    {'1': 'score', '3': 4, '4': 1, '5': 2, '10': 'score'},
    {'1': 'source_uri', '3': 5, '4': 1, '5': 9, '10': 'sourceUri'},
    {'1': 'metadata', '3': 6, '4': 3, '5': 11, '6': '.sparkle.rag.v1.EvidenceNode.MetadataEntry', '10': 'metadata'},
    {'1': 'source_type', '3': 7, '4': 1, '5': 9, '10': 'sourceType'},
  ],
  '3': [EvidenceNode_MetadataEntry$json],
};

@$core.Deprecated('Use evidenceNodeDescriptor instead')
const EvidenceNode_MetadataEntry$json = {
  '1': 'MetadataEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {'1': 'value', '3': 2, '4': 1, '5': 9, '10': 'value'},
  ],
  '7': {'7': true},
};

/// Descriptor for `EvidenceNode`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List evidenceNodeDescriptor = $convert.base64Decode(
    'CgxFdmlkZW5jZU5vZGUSFwoHbm9kZV9pZBgBIAEoCVIGbm9kZUlkEhsKCXNvdXJjZV9pZBgCIA'
    'EoCVIIc291cmNlSWQSGAoHc25pcHBldBgDIAEoCVIHc25pcHBldBIUCgVzY29yZRgEIAEoAlIF'
    'c2NvcmUSHQoKc291cmNlX3VyaRgFIAEoCVIJc291cmNlVXJpEkYKCG1ldGFkYXRhGAYgAygLMi'
    'ouc3BhcmtsZS5yYWcudjEuRXZpZGVuY2VOb2RlLk1ldGFkYXRhRW50cnlSCG1ldGFkYXRhEh8K'
    'C3NvdXJjZV90eXBlGAcgASgJUgpzb3VyY2VUeXBlGjsKDU1ldGFkYXRhRW50cnkSEAoDa2V5GA'
    'EgASgJUgNrZXkSFAoFdmFsdWUYAiABKAlSBXZhbHVlOgI4AQ==');

@$core.Deprecated('Use evidencePackDescriptor instead')
const EvidencePack$json = {
  '1': 'EvidencePack',
  '2': [
    {'1': 'request_id', '3': 1, '4': 1, '5': 9, '10': 'requestId'},
    {'1': 'trace_id', '3': 2, '4': 1, '5': 9, '10': 'traceId'},
    {'1': 'nodes', '3': 3, '4': 3, '5': 11, '6': '.sparkle.rag.v1.EvidenceNode', '10': 'nodes'},
    {'1': 'metadata', '3': 4, '4': 3, '5': 11, '6': '.sparkle.rag.v1.EvidencePack.MetadataEntry', '10': 'metadata'},
  ],
  '3': [EvidencePack_MetadataEntry$json],
};

@$core.Deprecated('Use evidencePackDescriptor instead')
const EvidencePack_MetadataEntry$json = {
  '1': 'MetadataEntry',
  '2': [
    {'1': 'key', '3': 1, '4': 1, '5': 9, '10': 'key'},
    {'1': 'value', '3': 2, '4': 1, '5': 9, '10': 'value'},
  ],
  '7': {'7': true},
};

/// Descriptor for `EvidencePack`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List evidencePackDescriptor = $convert.base64Decode(
    'CgxFdmlkZW5jZVBhY2sSHQoKcmVxdWVzdF9pZBgBIAEoCVIJcmVxdWVzdElkEhkKCHRyYWNlX2'
    'lkGAIgASgJUgd0cmFjZUlkEjIKBW5vZGVzGAMgAygLMhwuc3BhcmtsZS5yYWcudjEuRXZpZGVu'
    'Y2VOb2RlUgVub2RlcxJGCghtZXRhZGF0YRgEIAMoCzIqLnNwYXJrbGUucmFnLnYxLkV2aWRlbm'
    'NlUGFjay5NZXRhZGF0YUVudHJ5UghtZXRhZGF0YRo7Cg1NZXRhZGF0YUVudHJ5EhAKA2tleRgB'
    'IAEoCVIDa2V5EhQKBXZhbHVlGAIgASgJUgV2YWx1ZToCOAE=');

