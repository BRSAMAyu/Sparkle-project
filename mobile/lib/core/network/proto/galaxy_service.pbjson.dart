//
//  Generated code. Do not modify.
//  source: galaxy_service.proto
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

@$core.Deprecated('Use collaborativeGalaxyUpdateDescriptor instead')
const CollaborativeGalaxyUpdate$json = {
  '1': 'CollaborativeGalaxyUpdate',
  '2': [
    {'1': 'galaxy_id', '3': 1, '4': 1, '5': 9, '10': 'galaxyId'},
    {'1': 'yjs_update', '3': 2, '4': 1, '5': 12, '10': 'yjsUpdate'},
    {'1': 'user_id', '3': 3, '4': 1, '5': 9, '10': 'userId'},
    {'1': 'timestamp', '3': 4, '4': 1, '5': 3, '10': 'timestamp'},
  ],
};

/// Descriptor for `CollaborativeGalaxyUpdate`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List collaborativeGalaxyUpdateDescriptor = $convert.base64Decode(
    'ChlDb2xsYWJvcmF0aXZlR2FsYXh5VXBkYXRlEhsKCWdhbGF4eV9pZBgBIAEoCVIIZ2FsYXh5SW'
    'QSHQoKeWpzX3VwZGF0ZRgCIAEoDFIJeWpzVXBkYXRlEhcKB3VzZXJfaWQYAyABKAlSBnVzZXJJ'
    'ZBIcCgl0aW1lc3RhbXAYBCABKANSCXRpbWVzdGFtcA==');

@$core.Deprecated('Use syncCollaborativeGalaxyRequestDescriptor instead')
const SyncCollaborativeGalaxyRequest$json = {
  '1': 'SyncCollaborativeGalaxyRequest',
  '2': [
    {'1': 'galaxy_id', '3': 1, '4': 1, '5': 9, '10': 'galaxyId'},
    {'1': 'partial_update', '3': 2, '4': 1, '5': 12, '10': 'partialUpdate'},
    {'1': 'user_id', '3': 3, '4': 1, '5': 9, '10': 'userId'},
  ],
};

/// Descriptor for `SyncCollaborativeGalaxyRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List syncCollaborativeGalaxyRequestDescriptor = $convert.base64Decode(
    'Ch5TeW5jQ29sbGFib3JhdGl2ZUdhbGF4eVJlcXVlc3QSGwoJZ2FsYXh5X2lkGAEgASgJUghnYW'
    'xheHlJZBIlCg5wYXJ0aWFsX3VwZGF0ZRgCIAEoDFINcGFydGlhbFVwZGF0ZRIXCgd1c2VyX2lk'
    'GAMgASgJUgZ1c2VySWQ=');

@$core.Deprecated('Use syncCollaborativeGalaxyResponseDescriptor instead')
const SyncCollaborativeGalaxyResponse$json = {
  '1': 'SyncCollaborativeGalaxyResponse',
  '2': [
    {'1': 'success', '3': 1, '4': 1, '5': 8, '10': 'success'},
    {'1': 'server_update', '3': 2, '4': 1, '5': 12, '10': 'serverUpdate'},
  ],
};

/// Descriptor for `SyncCollaborativeGalaxyResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List syncCollaborativeGalaxyResponseDescriptor = $convert.base64Decode(
    'Ch9TeW5jQ29sbGFib3JhdGl2ZUdhbGF4eVJlc3BvbnNlEhgKB3N1Y2Nlc3MYASABKAhSB3N1Y2'
    'Nlc3MSIwoNc2VydmVyX3VwZGF0ZRgCIAEoDFIMc2VydmVyVXBkYXRl');

@$core.Deprecated('Use updateNodeMasteryRequestDescriptor instead')
const UpdateNodeMasteryRequest$json = {
  '1': 'UpdateNodeMasteryRequest',
  '2': [
    {'1': 'user_id', '3': 1, '4': 1, '5': 9, '10': 'userId'},
    {'1': 'node_id', '3': 2, '4': 1, '5': 9, '10': 'nodeId'},
    {'1': 'mastery', '3': 3, '4': 1, '5': 5, '10': 'mastery'},
    {'1': 'version', '3': 4, '4': 1, '5': 11, '6': '.google.protobuf.Timestamp', '10': 'version'},
    {'1': 'reason', '3': 5, '4': 1, '5': 9, '10': 'reason'},
    {'1': 'request_id', '3': 6, '4': 1, '5': 9, '10': 'requestId'},
    {'1': 'revision', '3': 7, '4': 1, '5': 3, '10': 'revision'},
  ],
};

/// Descriptor for `UpdateNodeMasteryRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List updateNodeMasteryRequestDescriptor = $convert.base64Decode(
    'ChhVcGRhdGVOb2RlTWFzdGVyeVJlcXVlc3QSFwoHdXNlcl9pZBgBIAEoCVIGdXNlcklkEhcKB2'
    '5vZGVfaWQYAiABKAlSBm5vZGVJZBIYCgdtYXN0ZXJ5GAMgASgFUgdtYXN0ZXJ5EjQKB3ZlcnNp'
    'b24YBCABKAsyGi5nb29nbGUucHJvdG9idWYuVGltZXN0YW1wUgd2ZXJzaW9uEhYKBnJlYXNvbh'
    'gFIAEoCVIGcmVhc29uEh0KCnJlcXVlc3RfaWQYBiABKAlSCXJlcXVlc3RJZBIaCghyZXZpc2lv'
    'bhgHIAEoA1IIcmV2aXNpb24=');

@$core.Deprecated('Use updateNodeMasteryResponseDescriptor instead')
const UpdateNodeMasteryResponse$json = {
  '1': 'UpdateNodeMasteryResponse',
  '2': [
    {'1': 'success', '3': 1, '4': 1, '5': 8, '10': 'success'},
    {'1': 'old_mastery', '3': 2, '4': 1, '5': 5, '10': 'oldMastery'},
    {'1': 'new_mastery', '3': 3, '4': 1, '5': 5, '10': 'newMastery'},
    {'1': 'reason', '3': 4, '4': 1, '5': 9, '10': 'reason'},
    {'1': 'request_id', '3': 5, '4': 1, '5': 9, '10': 'requestId'},
    {'1': 'current_revision', '3': 6, '4': 1, '5': 3, '10': 'currentRevision'},
  ],
};

/// Descriptor for `UpdateNodeMasteryResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List updateNodeMasteryResponseDescriptor = $convert.base64Decode(
    'ChlVcGRhdGVOb2RlTWFzdGVyeVJlc3BvbnNlEhgKB3N1Y2Nlc3MYASABKAhSB3N1Y2Nlc3MSHw'
    'oLb2xkX21hc3RlcnkYAiABKAVSCm9sZE1hc3RlcnkSHwoLbmV3X21hc3RlcnkYAyABKAVSCm5l'
    'd01hc3RlcnkSFgoGcmVhc29uGAQgASgJUgZyZWFzb24SHQoKcmVxdWVzdF9pZBgFIAEoCVIJcm'
    'VxdWVzdElkEikKEGN1cnJlbnRfcmV2aXNpb24YBiABKANSD2N1cnJlbnRSZXZpc2lvbg==');

const $core.Map<$core.String, $core.dynamic> GalaxyServiceBase$json = {
  '1': 'GalaxyService',
  '2': [
    {'1': 'UpdateNodeMastery', '2': '.galaxy.v1.UpdateNodeMasteryRequest', '3': '.galaxy.v1.UpdateNodeMasteryResponse'},
    {'1': 'SyncCollaborativeGalaxy', '2': '.galaxy.v1.SyncCollaborativeGalaxyRequest', '3': '.galaxy.v1.SyncCollaborativeGalaxyResponse'},
  ],
};

@$core.Deprecated('Use galaxyServiceDescriptor instead')
const $core.Map<$core.String, $core.Map<$core.String, $core.dynamic>> GalaxyServiceBase$messageJson = {
  '.galaxy.v1.UpdateNodeMasteryRequest': UpdateNodeMasteryRequest$json,
  '.google.protobuf.Timestamp': $2.Timestamp$json,
  '.galaxy.v1.UpdateNodeMasteryResponse': UpdateNodeMasteryResponse$json,
  '.galaxy.v1.SyncCollaborativeGalaxyRequest': SyncCollaborativeGalaxyRequest$json,
  '.galaxy.v1.SyncCollaborativeGalaxyResponse': SyncCollaborativeGalaxyResponse$json,
};

/// Descriptor for `GalaxyService`. Decode as a `google.protobuf.ServiceDescriptorProto`.
final $typed_data.Uint8List galaxyServiceDescriptor = $convert.base64Decode(
    'Cg1HYWxheHlTZXJ2aWNlEl4KEVVwZGF0ZU5vZGVNYXN0ZXJ5EiMuZ2FsYXh5LnYxLlVwZGF0ZU'
    '5vZGVNYXN0ZXJ5UmVxdWVzdBokLmdhbGF4eS52MS5VcGRhdGVOb2RlTWFzdGVyeVJlc3BvbnNl'
    'EnAKF1N5bmNDb2xsYWJvcmF0aXZlR2FsYXh5EikuZ2FsYXh5LnYxLlN5bmNDb2xsYWJvcmF0aX'
    'ZlR2FsYXh5UmVxdWVzdBoqLmdhbGF4eS52MS5TeW5jQ29sbGFib3JhdGl2ZUdhbGF4eVJlc3Bv'
    'bnNl');

