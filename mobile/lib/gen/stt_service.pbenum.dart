// This is a generated file - do not edit.
//
// Generated from stt_service.proto.

// @dart = 3.3

// ignore_for_file: annotate_overrides, camel_case_types, comment_references
// ignore_for_file: constant_identifier_names
// ignore_for_file: curly_braces_in_flow_control_structures
// ignore_for_file: deprecated_member_use_from_same_package, library_prefixes
// ignore_for_file: non_constant_identifier_names, prefer_relative_imports

import 'dart:core' as $core;

import 'package:protobuf/protobuf.dart' as $pb;

/// AudioFormat enumerates supported audio formats.
class AudioFormat extends $pb.ProtobufEnum {
  static const AudioFormat AUDIO_FORMAT_UNSPECIFIED =
      AudioFormat._(0, _omitEnumNames ? '' : 'AUDIO_FORMAT_UNSPECIFIED');
  static const AudioFormat AUDIO_FORMAT_PCM =
      AudioFormat._(1, _omitEnumNames ? '' : 'AUDIO_FORMAT_PCM');
  static const AudioFormat AUDIO_FORMAT_WAV =
      AudioFormat._(2, _omitEnumNames ? '' : 'AUDIO_FORMAT_WAV');
  static const AudioFormat AUDIO_FORMAT_MP3 =
      AudioFormat._(3, _omitEnumNames ? '' : 'AUDIO_FORMAT_MP3');
  static const AudioFormat AUDIO_FORMAT_M4A =
      AudioFormat._(4, _omitEnumNames ? '' : 'AUDIO_FORMAT_M4A');
  static const AudioFormat AUDIO_FORMAT_OGG =
      AudioFormat._(5, _omitEnumNames ? '' : 'AUDIO_FORMAT_OGG');
  static const AudioFormat AUDIO_FORMAT_WEBM =
      AudioFormat._(6, _omitEnumNames ? '' : 'AUDIO_FORMAT_WEBM');
  static const AudioFormat AUDIO_FORMAT_OPUS =
      AudioFormat._(7, _omitEnumNames ? '' : 'AUDIO_FORMAT_OPUS');

  static const $core.List<AudioFormat> values = <AudioFormat>[
    AUDIO_FORMAT_UNSPECIFIED,
    AUDIO_FORMAT_PCM,
    AUDIO_FORMAT_WAV,
    AUDIO_FORMAT_MP3,
    AUDIO_FORMAT_M4A,
    AUDIO_FORMAT_OGG,
    AUDIO_FORMAT_WEBM,
    AUDIO_FORMAT_OPUS,
  ];

  static final $core.List<AudioFormat?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 7);
  static AudioFormat? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const AudioFormat._(super.value, super.name);
}

/// LanguageCode enumerates supported languages.
class LanguageCode extends $pb.ProtobufEnum {
  static const LanguageCode LANGUAGE_CODE_UNSPECIFIED =
      LanguageCode._(0, _omitEnumNames ? '' : 'LANGUAGE_CODE_UNSPECIFIED');
  static const LanguageCode LANGUAGE_CODE_ZH_CN =
      LanguageCode._(1, _omitEnumNames ? '' : 'LANGUAGE_CODE_ZH_CN');
  static const LanguageCode LANGUAGE_CODE_ZH_TW =
      LanguageCode._(2, _omitEnumNames ? '' : 'LANGUAGE_CODE_ZH_TW');
  static const LanguageCode LANGUAGE_CODE_EN_US =
      LanguageCode._(3, _omitEnumNames ? '' : 'LANGUAGE_CODE_EN_US');
  static const LanguageCode LANGUAGE_CODE_EN_GB =
      LanguageCode._(4, _omitEnumNames ? '' : 'LANGUAGE_CODE_EN_GB');
  static const LanguageCode LANGUAGE_CODE_JA_JP =
      LanguageCode._(5, _omitEnumNames ? '' : 'LANGUAGE_CODE_JA_JP');
  static const LanguageCode LANGUAGE_CODE_KO_KR =
      LanguageCode._(6, _omitEnumNames ? '' : 'LANGUAGE_CODE_KO_KR');

  static const $core.List<LanguageCode> values = <LanguageCode>[
    LANGUAGE_CODE_UNSPECIFIED,
    LANGUAGE_CODE_ZH_CN,
    LANGUAGE_CODE_ZH_TW,
    LANGUAGE_CODE_EN_US,
    LANGUAGE_CODE_EN_GB,
    LANGUAGE_CODE_JA_JP,
    LANGUAGE_CODE_KO_KR,
  ];

  static final $core.List<LanguageCode?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 6);
  static LanguageCode? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const LanguageCode._(super.value, super.name);
}

/// STTErrorCode enumerates possible error codes.
class STTErrorCode extends $pb.ProtobufEnum {
  static const STTErrorCode STT_ERROR_CODE_UNSPECIFIED =
      STTErrorCode._(0, _omitEnumNames ? '' : 'STT_ERROR_CODE_UNSPECIFIED');
  static const STTErrorCode STT_ERROR_CODE_AUDIO_TOO_LARGE =
      STTErrorCode._(1, _omitEnumNames ? '' : 'STT_ERROR_CODE_AUDIO_TOO_LARGE');
  static const STTErrorCode STT_ERROR_CODE_UNSUPPORTED_FORMAT = STTErrorCode._(
      2, _omitEnumNames ? '' : 'STT_ERROR_CODE_UNSUPPORTED_FORMAT');
  static const STTErrorCode STT_ERROR_CODE_INVALID_SAMPLE_RATE = STTErrorCode._(
      3, _omitEnumNames ? '' : 'STT_ERROR_CODE_INVALID_SAMPLE_RATE');
  static const STTErrorCode STT_ERROR_CODE_NO_SPEECH_DETECTED = STTErrorCode._(
      4, _omitEnumNames ? '' : 'STT_ERROR_CODE_NO_SPEECH_DETECTED');
  static const STTErrorCode STT_ERROR_CODE_RECOGNITION_FAILED = STTErrorCode._(
      5, _omitEnumNames ? '' : 'STT_ERROR_CODE_RECOGNITION_FAILED');
  static const STTErrorCode STT_ERROR_CODE_PROVIDER_UNAVAILABLE =
      STTErrorCode._(
          6, _omitEnumNames ? '' : 'STT_ERROR_CODE_PROVIDER_UNAVAILABLE');
  static const STTErrorCode STT_ERROR_CODE_RATE_LIMITED =
      STTErrorCode._(7, _omitEnumNames ? '' : 'STT_ERROR_CODE_RATE_LIMITED');
  static const STTErrorCode STT_ERROR_CODE_UNAUTHORIZED =
      STTErrorCode._(8, _omitEnumNames ? '' : 'STT_ERROR_CODE_UNAUTHORIZED');
  static const STTErrorCode STT_ERROR_CODE_INTERNAL_ERROR =
      STTErrorCode._(9, _omitEnumNames ? '' : 'STT_ERROR_CODE_INTERNAL_ERROR');

  static const $core.List<STTErrorCode> values = <STTErrorCode>[
    STT_ERROR_CODE_UNSPECIFIED,
    STT_ERROR_CODE_AUDIO_TOO_LARGE,
    STT_ERROR_CODE_UNSUPPORTED_FORMAT,
    STT_ERROR_CODE_INVALID_SAMPLE_RATE,
    STT_ERROR_CODE_NO_SPEECH_DETECTED,
    STT_ERROR_CODE_RECOGNITION_FAILED,
    STT_ERROR_CODE_PROVIDER_UNAVAILABLE,
    STT_ERROR_CODE_RATE_LIMITED,
    STT_ERROR_CODE_UNAUTHORIZED,
    STT_ERROR_CODE_INTERNAL_ERROR,
  ];

  static final $core.List<STTErrorCode?> _byValue =
      $pb.ProtobufEnum.$_initByValueList(values, 9);
  static STTErrorCode? valueOf($core.int value) =>
      value < 0 || value >= _byValue.length ? null : _byValue[value];

  const STTErrorCode._(super.value, super.name);
}

const $core.bool _omitEnumNames =
    $core.bool.fromEnvironment('protobuf.omit_enum_names');
