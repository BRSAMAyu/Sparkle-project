// This is a generated file - do not edit.
//
// Generated from stt_service.proto.

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

@$core.Deprecated('Use audioFormatDescriptor instead')
const AudioFormat$json = {
  '1': 'AudioFormat',
  '2': [
    {'1': 'AUDIO_FORMAT_UNSPECIFIED', '2': 0},
    {'1': 'AUDIO_FORMAT_PCM', '2': 1},
    {'1': 'AUDIO_FORMAT_WAV', '2': 2},
    {'1': 'AUDIO_FORMAT_MP3', '2': 3},
    {'1': 'AUDIO_FORMAT_M4A', '2': 4},
    {'1': 'AUDIO_FORMAT_OGG', '2': 5},
    {'1': 'AUDIO_FORMAT_WEBM', '2': 6},
    {'1': 'AUDIO_FORMAT_OPUS', '2': 7},
  ],
};

/// Descriptor for `AudioFormat`. Decode as a `google.protobuf.EnumDescriptorProto`.
final $typed_data.Uint8List audioFormatDescriptor = $convert.base64Decode(
    'CgtBdWRpb0Zvcm1hdBIcChhBVURJT19GT1JNQVRfVU5TUEVDSUZJRUQQABIUChBBVURJT19GT1'
    'JNQVRfUENNEAESFAoQQVVESU9fRk9STUFUX1dBVhACEhQKEEFVRElPX0ZPUk1BVF9NUDMQAxIU'
    'ChBBVURJT19GT1JNQVRfTTRBEAQSFAoQQVVESU9fRk9STUFUX09HRxAFEhUKEUFVRElPX0ZPUk'
    '1BVF9XRUJNEAYSFQoRQVVESU9fRk9STUFUX09QVVMQBw==');

@$core.Deprecated('Use languageCodeDescriptor instead')
const LanguageCode$json = {
  '1': 'LanguageCode',
  '2': [
    {'1': 'LANGUAGE_CODE_UNSPECIFIED', '2': 0},
    {'1': 'LANGUAGE_CODE_ZH_CN', '2': 1},
    {'1': 'LANGUAGE_CODE_ZH_TW', '2': 2},
    {'1': 'LANGUAGE_CODE_EN_US', '2': 3},
    {'1': 'LANGUAGE_CODE_EN_GB', '2': 4},
    {'1': 'LANGUAGE_CODE_JA_JP', '2': 5},
    {'1': 'LANGUAGE_CODE_KO_KR', '2': 6},
  ],
};

/// Descriptor for `LanguageCode`. Decode as a `google.protobuf.EnumDescriptorProto`.
final $typed_data.Uint8List languageCodeDescriptor = $convert.base64Decode(
    'CgxMYW5ndWFnZUNvZGUSHQoZTEFOR1VBR0VfQ09ERV9VTlNQRUNJRklFRBAAEhcKE0xBTkdVQU'
    'dFX0NPREVfWkhfQ04QARIXChNMQU5HVUFHRV9DT0RFX1pIX1RXEAISFwoTTEFOR1VBR0VfQ09E'
    'RV9FTl9VUxADEhcKE0xBTkdVQUdFX0NPREVfRU5fR0IQBBIXChNMQU5HVUFHRV9DT0RFX0pBX0'
    'pQEAUSFwoTTEFOR1VBR0VfQ09ERV9LT19LUhAG');

@$core.Deprecated('Use sTTErrorCodeDescriptor instead')
const STTErrorCode$json = {
  '1': 'STTErrorCode',
  '2': [
    {'1': 'STT_ERROR_CODE_UNSPECIFIED', '2': 0},
    {'1': 'STT_ERROR_CODE_AUDIO_TOO_LARGE', '2': 1},
    {'1': 'STT_ERROR_CODE_UNSUPPORTED_FORMAT', '2': 2},
    {'1': 'STT_ERROR_CODE_INVALID_SAMPLE_RATE', '2': 3},
    {'1': 'STT_ERROR_CODE_NO_SPEECH_DETECTED', '2': 4},
    {'1': 'STT_ERROR_CODE_RECOGNITION_FAILED', '2': 5},
    {'1': 'STT_ERROR_CODE_PROVIDER_UNAVAILABLE', '2': 6},
    {'1': 'STT_ERROR_CODE_RATE_LIMITED', '2': 7},
    {'1': 'STT_ERROR_CODE_UNAUTHORIZED', '2': 8},
    {'1': 'STT_ERROR_CODE_INTERNAL_ERROR', '2': 9},
  ],
};

/// Descriptor for `STTErrorCode`. Decode as a `google.protobuf.EnumDescriptorProto`.
final $typed_data.Uint8List sTTErrorCodeDescriptor = $convert.base64Decode(
    'CgxTVFRFcnJvckNvZGUSHgoaU1RUX0VSUk9SX0NPREVfVU5TUEVDSUZJRUQQABIiCh5TVFRfRV'
    'JST1JfQ09ERV9BVURJT19UT09fTEFSR0UQARIlCiFTVFRfRVJST1JfQ09ERV9VTlNVUFBPUlRF'
    'RF9GT1JNQVQQAhImCiJTVFRfRVJST1JfQ09ERV9JTlZBTElEX1NBTVBMRV9SQVRFEAMSJQohU1'
    'RUX0VSUk9SX0NPREVfTk9fU1BFRUNIX0RFVEVDVEVEEAQSJQohU1RUX0VSUk9SX0NPREVfUkVD'
    'T0dOSVRJT05fRkFJTEVEEAUSJwojU1RUX0VSUk9SX0NPREVfUFJPVklERVJfVU5BVkFJTEFCTE'
    'UQBhIfChtTVFRfRVJST1JfQ09ERV9SQVRFX0xJTUlURUQQBxIfChtTVFRfRVJST1JfQ09ERV9V'
    'TkFVVEhPUklaRUQQCBIhCh1TVFRfRVJST1JfQ09ERV9JTlRFUk5BTF9FUlJPUhAJ');

@$core.Deprecated('Use audioChunkDescriptor instead')
const AudioChunk$json = {
  '1': 'AudioChunk',
  '2': [
    {'1': 'data', '3': 1, '4': 1, '5': 12, '10': 'data'},
    {'1': 'sample_rate', '3': 2, '4': 1, '5': 5, '10': 'sampleRate'},
    {'1': 'format', '3': 3, '4': 1, '5': 9, '10': 'format'},
    {'1': 'language', '3': 4, '4': 1, '5': 9, '10': 'language'},
    {'1': 'user_id', '3': 5, '4': 1, '5': 9, '10': 'userId'},
    {'1': 'session_id', '3': 6, '4': 1, '5': 9, '10': 'sessionId'},
    {'1': 'end_of_stream', '3': 7, '4': 1, '5': 8, '10': 'endOfStream'},
  ],
};

/// Descriptor for `AudioChunk`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List audioChunkDescriptor = $convert.base64Decode(
    'CgpBdWRpb0NodW5rEhIKBGRhdGEYASABKAxSBGRhdGESHwoLc2FtcGxlX3JhdGUYAiABKAVSCn'
    'NhbXBsZVJhdGUSFgoGZm9ybWF0GAMgASgJUgZmb3JtYXQSGgoIbGFuZ3VhZ2UYBCABKAlSCGxh'
    'bmd1YWdlEhcKB3VzZXJfaWQYBSABKAlSBnVzZXJJZBIdCgpzZXNzaW9uX2lkGAYgASgJUglzZX'
    'NzaW9uSWQSIgoNZW5kX29mX3N0cmVhbRgHIAEoCFILZW5kT2ZTdHJlYW0=');

@$core.Deprecated('Use transcriptionResultDescriptor instead')
const TranscriptionResult$json = {
  '1': 'TranscriptionResult',
  '2': [
    {'1': 'text', '3': 1, '4': 1, '5': 9, '10': 'text'},
    {'1': 'is_final', '3': 2, '4': 1, '5': 8, '10': 'isFinal'},
    {'1': 'confidence', '3': 3, '4': 1, '5': 2, '10': 'confidence'},
    {'1': 'sequence', '3': 4, '4': 1, '5': 5, '10': 'sequence'},
    {
      '1': 'timestamp',
      '3': 5,
      '4': 1,
      '5': 11,
      '6': '.google.protobuf.Timestamp',
      '10': 'timestamp'
    },
    {'1': 'session_id', '3': 6, '4': 1, '5': 9, '10': 'sessionId'},
    {
      '1': 'error',
      '3': 7,
      '4': 1,
      '5': 11,
      '6': '.stt.v1.TranscriptionError',
      '10': 'error'
    },
  ],
};

/// Descriptor for `TranscriptionResult`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List transcriptionResultDescriptor = $convert.base64Decode(
    'ChNUcmFuc2NyaXB0aW9uUmVzdWx0EhIKBHRleHQYASABKAlSBHRleHQSGQoIaXNfZmluYWwYAi'
    'ABKAhSB2lzRmluYWwSHgoKY29uZmlkZW5jZRgDIAEoAlIKY29uZmlkZW5jZRIaCghzZXF1ZW5j'
    'ZRgEIAEoBVIIc2VxdWVuY2USOAoJdGltZXN0YW1wGAUgASgLMhouZ29vZ2xlLnByb3RvYnVmLl'
    'RpbWVzdGFtcFIJdGltZXN0YW1wEh0KCnNlc3Npb25faWQYBiABKAlSCXNlc3Npb25JZBIwCgVl'
    'cnJvchgHIAEoCzIaLnN0dC52MS5UcmFuc2NyaXB0aW9uRXJyb3JSBWVycm9y');

@$core.Deprecated('Use transcriptionErrorDescriptor instead')
const TranscriptionError$json = {
  '1': 'TranscriptionError',
  '2': [
    {'1': 'code', '3': 1, '4': 1, '5': 9, '10': 'code'},
    {'1': 'message', '3': 2, '4': 1, '5': 9, '10': 'message'},
    {'1': 'recoverable', '3': 3, '4': 1, '5': 8, '10': 'recoverable'},
  ],
};

/// Descriptor for `TranscriptionError`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List transcriptionErrorDescriptor = $convert.base64Decode(
    'ChJUcmFuc2NyaXB0aW9uRXJyb3ISEgoEY29kZRgBIAEoCVIEY29kZRIYCgdtZXNzYWdlGAIgAS'
    'gJUgdtZXNzYWdlEiAKC3JlY292ZXJhYmxlGAMgASgIUgtyZWNvdmVyYWJsZQ==');

@$core.Deprecated('Use transcribeRequestDescriptor instead')
const TranscribeRequest$json = {
  '1': 'TranscribeRequest',
  '2': [
    {'1': 'audio_data', '3': 1, '4': 1, '5': 12, '10': 'audioData'},
    {'1': 'filename', '3': 2, '4': 1, '5': 9, '10': 'filename'},
    {'1': 'language', '3': 3, '4': 1, '5': 9, '10': 'language'},
    {'1': 'format', '3': 4, '4': 1, '5': 9, '10': 'format'},
    {'1': 'user_id', '3': 5, '4': 1, '5': 9, '10': 'userId'},
    {
      '1': 'enable_enhancement',
      '3': 6,
      '4': 1,
      '5': 8,
      '10': 'enableEnhancement'
    },
    {'1': 'sample_rate', '3': 7, '4': 1, '5': 5, '10': 'sampleRate'},
  ],
};

/// Descriptor for `TranscribeRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List transcribeRequestDescriptor = $convert.base64Decode(
    'ChFUcmFuc2NyaWJlUmVxdWVzdBIdCgphdWRpb19kYXRhGAEgASgMUglhdWRpb0RhdGESGgoIZm'
    'lsZW5hbWUYAiABKAlSCGZpbGVuYW1lEhoKCGxhbmd1YWdlGAMgASgJUghsYW5ndWFnZRIWCgZm'
    'b3JtYXQYBCABKAlSBmZvcm1hdBIXCgd1c2VyX2lkGAUgASgJUgZ1c2VySWQSLQoSZW5hYmxlX2'
    'VuaGFuY2VtZW50GAYgASgIUhFlbmFibGVFbmhhbmNlbWVudBIfCgtzYW1wbGVfcmF0ZRgHIAEo'
    'BVIKc2FtcGxlUmF0ZQ==');

@$core.Deprecated('Use transcribeResponseDescriptor instead')
const TranscribeResponse$json = {
  '1': 'TranscribeResponse',
  '2': [
    {'1': 'text', '3': 1, '4': 1, '5': 9, '10': 'text'},
    {'1': 'duration_seconds', '3': 2, '4': 1, '5': 2, '10': 'durationSeconds'},
    {'1': 'confidence', '3': 3, '4': 1, '5': 2, '10': 'confidence'},
    {
      '1': 'detected_language',
      '3': 4,
      '4': 1,
      '5': 9,
      '10': 'detectedLanguage'
    },
    {'1': 'enhanced_text', '3': 5, '4': 1, '5': 9, '10': 'enhancedText'},
    {
      '1': 'words',
      '3': 6,
      '4': 3,
      '5': 11,
      '6': '.stt.v1.WordTimestamp',
      '10': 'words'
    },
    {
      '1': 'metadata',
      '3': 7,
      '4': 1,
      '5': 11,
      '6': '.stt.v1.TranscriptionMetadata',
      '10': 'metadata'
    },
    {
      '1': 'error',
      '3': 8,
      '4': 1,
      '5': 11,
      '6': '.stt.v1.TranscriptionError',
      '10': 'error'
    },
  ],
};

/// Descriptor for `TranscribeResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List transcribeResponseDescriptor = $convert.base64Decode(
    'ChJUcmFuc2NyaWJlUmVzcG9uc2USEgoEdGV4dBgBIAEoCVIEdGV4dBIpChBkdXJhdGlvbl9zZW'
    'NvbmRzGAIgASgCUg9kdXJhdGlvblNlY29uZHMSHgoKY29uZmlkZW5jZRgDIAEoAlIKY29uZmlk'
    'ZW5jZRIrChFkZXRlY3RlZF9sYW5ndWFnZRgEIAEoCVIQZGV0ZWN0ZWRMYW5ndWFnZRIjCg1lbm'
    'hhbmNlZF90ZXh0GAUgASgJUgxlbmhhbmNlZFRleHQSKwoFd29yZHMYBiADKAsyFS5zdHQudjEu'
    'V29yZFRpbWVzdGFtcFIFd29yZHMSOQoIbWV0YWRhdGEYByABKAsyHS5zdHQudjEuVHJhbnNjcm'
    'lwdGlvbk1ldGFkYXRhUghtZXRhZGF0YRIwCgVlcnJvchgIIAEoCzIaLnN0dC52MS5UcmFuc2Ny'
    'aXB0aW9uRXJyb3JSBWVycm9y');

@$core.Deprecated('Use wordTimestampDescriptor instead')
const WordTimestamp$json = {
  '1': 'WordTimestamp',
  '2': [
    {'1': 'word', '3': 1, '4': 1, '5': 9, '10': 'word'},
    {'1': 'start_time', '3': 2, '4': 1, '5': 2, '10': 'startTime'},
    {'1': 'end_time', '3': 3, '4': 1, '5': 2, '10': 'endTime'},
    {'1': 'confidence', '3': 4, '4': 1, '5': 2, '10': 'confidence'},
  ],
};

/// Descriptor for `WordTimestamp`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List wordTimestampDescriptor = $convert.base64Decode(
    'Cg1Xb3JkVGltZXN0YW1wEhIKBHdvcmQYASABKAlSBHdvcmQSHQoKc3RhcnRfdGltZRgCIAEoAl'
    'IJc3RhcnRUaW1lEhkKCGVuZF90aW1lGAMgASgCUgdlbmRUaW1lEh4KCmNvbmZpZGVuY2UYBCAB'
    'KAJSCmNvbmZpZGVuY2U=');

@$core.Deprecated('Use transcriptionMetadataDescriptor instead')
const TranscriptionMetadata$json = {
  '1': 'TranscriptionMetadata',
  '2': [
    {'1': 'provider', '3': 1, '4': 1, '5': 9, '10': 'provider'},
    {'1': 'model', '3': 2, '4': 1, '5': 9, '10': 'model'},
    {
      '1': 'processing_time_ms',
      '3': 3,
      '4': 1,
      '5': 3,
      '10': 'processingTimeMs'
    },
    {'1': 'file_size_bytes', '3': 4, '4': 1, '5': 3, '10': 'fileSizeBytes'},
    {'1': 'channels', '3': 5, '4': 1, '5': 5, '10': 'channels'},
    {'1': 'sample_rate', '3': 6, '4': 1, '5': 5, '10': 'sampleRate'},
  ],
};

/// Descriptor for `TranscriptionMetadata`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List transcriptionMetadataDescriptor = $convert.base64Decode(
    'ChVUcmFuc2NyaXB0aW9uTWV0YWRhdGESGgoIcHJvdmlkZXIYASABKAlSCHByb3ZpZGVyEhQKBW'
    '1vZGVsGAIgASgJUgVtb2RlbBIsChJwcm9jZXNzaW5nX3RpbWVfbXMYAyABKANSEHByb2Nlc3Np'
    'bmdUaW1lTXMSJgoPZmlsZV9zaXplX2J5dGVzGAQgASgDUg1maWxlU2l6ZUJ5dGVzEhoKCGNoYW'
    '5uZWxzGAUgASgFUghjaGFubmVscxIfCgtzYW1wbGVfcmF0ZRgGIAEoBVIKc2FtcGxlUmF0ZQ==');

@$core.Deprecated('Use enhanceRequestDescriptor instead')
const EnhanceRequest$json = {
  '1': 'EnhanceRequest',
  '2': [
    {'1': 'text', '3': 1, '4': 1, '5': 9, '10': 'text'},
    {'1': 'user_id', '3': 2, '4': 1, '5': 9, '10': 'userId'},
    {
      '1': 'options',
      '3': 3,
      '4': 1,
      '5': 11,
      '6': '.stt.v1.EnhancementOptions',
      '10': 'options'
    },
  ],
};

/// Descriptor for `EnhanceRequest`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List enhanceRequestDescriptor = $convert.base64Decode(
    'Cg5FbmhhbmNlUmVxdWVzdBISCgR0ZXh0GAEgASgJUgR0ZXh0EhcKB3VzZXJfaWQYAiABKAlSBn'
    'VzZXJJZBI0CgdvcHRpb25zGAMgASgLMhouc3R0LnYxLkVuaGFuY2VtZW50T3B0aW9uc1IHb3B0'
    'aW9ucw==');

@$core.Deprecated('Use enhancementOptionsDescriptor instead')
const EnhancementOptions$json = {
  '1': 'EnhancementOptions',
  '2': [
    {'1': 'add_punctuation', '3': 1, '4': 1, '5': 8, '10': 'addPunctuation'},
    {'1': 'correct_typos', '3': 2, '4': 1, '5': 8, '10': 'correctTypos'},
    {'1': 'format_speakers', '3': 3, '4': 1, '5': 8, '10': 'formatSpeakers'},
    {'1': 'language', '3': 4, '4': 1, '5': 9, '10': 'language'},
  ],
};

/// Descriptor for `EnhancementOptions`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List enhancementOptionsDescriptor = $convert.base64Decode(
    'ChJFbmhhbmNlbWVudE9wdGlvbnMSJwoPYWRkX3B1bmN0dWF0aW9uGAEgASgIUg5hZGRQdW5jdH'
    'VhdGlvbhIjCg1jb3JyZWN0X3R5cG9zGAIgASgIUgxjb3JyZWN0VHlwb3MSJwoPZm9ybWF0X3Nw'
    'ZWFrZXJzGAMgASgIUg5mb3JtYXRTcGVha2VycxIaCghsYW5ndWFnZRgEIAEoCVIIbGFuZ3VhZ2'
    'U=');

@$core.Deprecated('Use enhanceResponseDescriptor instead')
const EnhanceResponse$json = {
  '1': 'EnhanceResponse',
  '2': [
    {'1': 'enhanced_text', '3': 1, '4': 1, '5': 9, '10': 'enhancedText'},
    {'1': 'original_text', '3': 2, '4': 1, '5': 9, '10': 'originalText'},
    {'1': 'changes_count', '3': 3, '4': 1, '5': 5, '10': 'changesCount'},
    {
      '1': 'processing_time_ms',
      '3': 4,
      '4': 1,
      '5': 3,
      '10': 'processingTimeMs'
    },
  ],
};

/// Descriptor for `EnhanceResponse`. Decode as a `google.protobuf.DescriptorProto`.
final $typed_data.Uint8List enhanceResponseDescriptor = $convert.base64Decode(
    'Cg9FbmhhbmNlUmVzcG9uc2USIwoNZW5oYW5jZWRfdGV4dBgBIAEoCVIMZW5oYW5jZWRUZXh0Ei'
    'MKDW9yaWdpbmFsX3RleHQYAiABKAlSDG9yaWdpbmFsVGV4dBIjCg1jaGFuZ2VzX2NvdW50GAMg'
    'ASgFUgxjaGFuZ2VzQ291bnQSLAoScHJvY2Vzc2luZ190aW1lX21zGAQgASgDUhBwcm9jZXNzaW'
    '5nVGltZU1z');
