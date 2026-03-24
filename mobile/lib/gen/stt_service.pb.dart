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

import 'package:fixnum/fixnum.dart' as $fixnum;
import 'package:protobuf/protobuf.dart' as $pb;
import 'package:protobuf/well_known_types/google/protobuf/timestamp.pb.dart'
    as $1;

export 'package:protobuf/protobuf.dart' show GeneratedMessageGenericExtensions;

export 'stt_service.pbenum.dart';

/// AudioChunk represents a chunk of audio data for streaming.
class AudioChunk extends $pb.GeneratedMessage {
  factory AudioChunk({
    $core.List<$core.int>? data,
    $core.int? sampleRate,
    $core.String? format,
    $core.String? language,
    $core.String? userId,
    $core.String? sessionId,
    $core.bool? endOfStream,
  }) {
    final result = create();
    if (data != null) result.data = data;
    if (sampleRate != null) result.sampleRate = sampleRate;
    if (format != null) result.format = format;
    if (language != null) result.language = language;
    if (userId != null) result.userId = userId;
    if (sessionId != null) result.sessionId = sessionId;
    if (endOfStream != null) result.endOfStream = endOfStream;
    return result;
  }

  AudioChunk._();

  factory AudioChunk.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory AudioChunk.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'AudioChunk',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'stt.v1'),
      createEmptyInstance: create)
    ..a<$core.List<$core.int>>(
        1, _omitFieldNames ? '' : 'data', $pb.PbFieldType.OY)
    ..aI(2, _omitFieldNames ? '' : 'sampleRate')
    ..aOS(3, _omitFieldNames ? '' : 'format')
    ..aOS(4, _omitFieldNames ? '' : 'language')
    ..aOS(5, _omitFieldNames ? '' : 'userId')
    ..aOS(6, _omitFieldNames ? '' : 'sessionId')
    ..aOB(7, _omitFieldNames ? '' : 'endOfStream')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  AudioChunk clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  AudioChunk copyWith(void Function(AudioChunk) updates) =>
      super.copyWith((message) => updates(message as AudioChunk)) as AudioChunk;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static AudioChunk create() => AudioChunk._();
  @$core.override
  AudioChunk createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static AudioChunk getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<AudioChunk>(create);
  static AudioChunk? _defaultInstance;

  /// Audio data in binary format (PCM, Opus, etc.)
  @$pb.TagNumber(1)
  $core.List<$core.int> get data => $_getN(0);
  @$pb.TagNumber(1)
  set data($core.List<$core.int> value) => $_setBytes(0, value);
  @$pb.TagNumber(1)
  $core.bool hasData() => $_has(0);
  @$pb.TagNumber(1)
  void clearData() => $_clearField(1);

  /// Sample rate in Hz (e.g., 16000, 44100)
  @$pb.TagNumber(2)
  $core.int get sampleRate => $_getIZ(1);
  @$pb.TagNumber(2)
  set sampleRate($core.int value) => $_setSignedInt32(1, value);
  @$pb.TagNumber(2)
  $core.bool hasSampleRate() => $_has(1);
  @$pb.TagNumber(2)
  void clearSampleRate() => $_clearField(2);

  /// Audio format: "pcm", "opus", "wav", "mp3"
  @$pb.TagNumber(3)
  $core.String get format => $_getSZ(2);
  @$pb.TagNumber(3)
  set format($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasFormat() => $_has(2);
  @$pb.TagNumber(3)
  void clearFormat() => $_clearField(3);

  /// Language code (e.g., "zh-CN", "en-US")
  @$pb.TagNumber(4)
  $core.String get language => $_getSZ(3);
  @$pb.TagNumber(4)
  set language($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasLanguage() => $_has(3);
  @$pb.TagNumber(4)
  void clearLanguage() => $_clearField(4);

  /// Optional: User ID for session tracking
  @$pb.TagNumber(5)
  $core.String get userId => $_getSZ(4);
  @$pb.TagNumber(5)
  set userId($core.String value) => $_setString(4, value);
  @$pb.TagNumber(5)
  $core.bool hasUserId() => $_has(4);
  @$pb.TagNumber(5)
  void clearUserId() => $_clearField(5);

  /// Optional: Session ID for multi-turn transcription
  @$pb.TagNumber(6)
  $core.String get sessionId => $_getSZ(5);
  @$pb.TagNumber(6)
  set sessionId($core.String value) => $_setString(5, value);
  @$pb.TagNumber(6)
  $core.bool hasSessionId() => $_has(5);
  @$pb.TagNumber(6)
  void clearSessionId() => $_clearField(6);

  /// Control signal: true indicates end of stream
  @$pb.TagNumber(7)
  $core.bool get endOfStream => $_getBF(6);
  @$pb.TagNumber(7)
  set endOfStream($core.bool value) => $_setBool(6, value);
  @$pb.TagNumber(7)
  $core.bool hasEndOfStream() => $_has(6);
  @$pb.TagNumber(7)
  void clearEndOfStream() => $_clearField(7);
}

/// TranscriptionResult represents a transcription result from the server.
class TranscriptionResult extends $pb.GeneratedMessage {
  factory TranscriptionResult({
    $core.String? text,
    $core.bool? isFinal,
    $core.double? confidence,
    $core.int? sequence,
    $1.Timestamp? timestamp,
    $core.String? sessionId,
    TranscriptionError? error,
  }) {
    final result = create();
    if (text != null) result.text = text;
    if (isFinal != null) result.isFinal = isFinal;
    if (confidence != null) result.confidence = confidence;
    if (sequence != null) result.sequence = sequence;
    if (timestamp != null) result.timestamp = timestamp;
    if (sessionId != null) result.sessionId = sessionId;
    if (error != null) result.error = error;
    return result;
  }

  TranscriptionResult._();

  factory TranscriptionResult.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory TranscriptionResult.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'TranscriptionResult',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'stt.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'text')
    ..aOB(2, _omitFieldNames ? '' : 'isFinal')
    ..aD(3, _omitFieldNames ? '' : 'confidence', fieldType: $pb.PbFieldType.OF)
    ..aI(4, _omitFieldNames ? '' : 'sequence')
    ..aOM<$1.Timestamp>(5, _omitFieldNames ? '' : 'timestamp',
        subBuilder: $1.Timestamp.create)
    ..aOS(6, _omitFieldNames ? '' : 'sessionId')
    ..aOM<TranscriptionError>(7, _omitFieldNames ? '' : 'error',
        subBuilder: TranscriptionError.create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TranscriptionResult clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TranscriptionResult copyWith(void Function(TranscriptionResult) updates) =>
      super.copyWith((message) => updates(message as TranscriptionResult))
          as TranscriptionResult;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static TranscriptionResult create() => TranscriptionResult._();
  @$core.override
  TranscriptionResult createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static TranscriptionResult getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<TranscriptionResult>(create);
  static TranscriptionResult? _defaultInstance;

  /// Transcribed text (partial or final)
  @$pb.TagNumber(1)
  $core.String get text => $_getSZ(0);
  @$pb.TagNumber(1)
  set text($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasText() => $_has(0);
  @$pb.TagNumber(1)
  void clearText() => $_clearField(1);

  /// Whether this is the final result for this segment
  @$pb.TagNumber(2)
  $core.bool get isFinal => $_getBF(1);
  @$pb.TagNumber(2)
  set isFinal($core.bool value) => $_setBool(1, value);
  @$pb.TagNumber(2)
  $core.bool hasIsFinal() => $_has(1);
  @$pb.TagNumber(2)
  void clearIsFinal() => $_clearField(2);

  /// Confidence score (0.0-1.0), may be unset if not available
  @$pb.TagNumber(3)
  $core.double get confidence => $_getN(2);
  @$pb.TagNumber(3)
  set confidence($core.double value) => $_setFloat(2, value);
  @$pb.TagNumber(3)
  $core.bool hasConfidence() => $_has(2);
  @$pb.TagNumber(3)
  void clearConfidence() => $_clearField(3);

  /// Sequence number for ordering (optional)
  @$pb.TagNumber(4)
  $core.int get sequence => $_getIZ(3);
  @$pb.TagNumber(4)
  set sequence($core.int value) => $_setSignedInt32(3, value);
  @$pb.TagNumber(4)
  $core.bool hasSequence() => $_has(3);
  @$pb.TagNumber(4)
  void clearSequence() => $_clearField(4);

  /// Timestamp when this segment was transcribed
  @$pb.TagNumber(5)
  $1.Timestamp get timestamp => $_getN(4);
  @$pb.TagNumber(5)
  set timestamp($1.Timestamp value) => $_setField(5, value);
  @$pb.TagNumber(5)
  $core.bool hasTimestamp() => $_has(4);
  @$pb.TagNumber(5)
  void clearTimestamp() => $_clearField(5);
  @$pb.TagNumber(5)
  $1.Timestamp ensureTimestamp() => $_ensure(4);

  /// Session ID for correlation
  @$pb.TagNumber(6)
  $core.String get sessionId => $_getSZ(5);
  @$pb.TagNumber(6)
  set sessionId($core.String value) => $_setString(5, value);
  @$pb.TagNumber(6)
  $core.bool hasSessionId() => $_has(5);
  @$pb.TagNumber(6)
  void clearSessionId() => $_clearField(6);

  /// Error information if transcription failed
  @$pb.TagNumber(7)
  TranscriptionError get error => $_getN(6);
  @$pb.TagNumber(7)
  set error(TranscriptionError value) => $_setField(7, value);
  @$pb.TagNumber(7)
  $core.bool hasError() => $_has(6);
  @$pb.TagNumber(7)
  void clearError() => $_clearField(7);
  @$pb.TagNumber(7)
  TranscriptionError ensureError() => $_ensure(6);
}

/// TranscriptionError represents an error during transcription.
class TranscriptionError extends $pb.GeneratedMessage {
  factory TranscriptionError({
    $core.String? code,
    $core.String? message,
    $core.bool? recoverable,
  }) {
    final result = create();
    if (code != null) result.code = code;
    if (message != null) result.message = message;
    if (recoverable != null) result.recoverable = recoverable;
    return result;
  }

  TranscriptionError._();

  factory TranscriptionError.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory TranscriptionError.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'TranscriptionError',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'stt.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'code')
    ..aOS(2, _omitFieldNames ? '' : 'message')
    ..aOB(3, _omitFieldNames ? '' : 'recoverable')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TranscriptionError clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TranscriptionError copyWith(void Function(TranscriptionError) updates) =>
      super.copyWith((message) => updates(message as TranscriptionError))
          as TranscriptionError;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static TranscriptionError create() => TranscriptionError._();
  @$core.override
  TranscriptionError createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static TranscriptionError getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<TranscriptionError>(create);
  static TranscriptionError? _defaultInstance;

  /// Error code for programmatic handling
  @$pb.TagNumber(1)
  $core.String get code => $_getSZ(0);
  @$pb.TagNumber(1)
  set code($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasCode() => $_has(0);
  @$pb.TagNumber(1)
  void clearCode() => $_clearField(1);

  /// Human-readable error message
  @$pb.TagNumber(2)
  $core.String get message => $_getSZ(1);
  @$pb.TagNumber(2)
  set message($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasMessage() => $_has(1);
  @$pb.TagNumber(2)
  void clearMessage() => $_clearField(2);

  /// Whether the error is recoverable (streaming can continue)
  @$pb.TagNumber(3)
  $core.bool get recoverable => $_getBF(2);
  @$pb.TagNumber(3)
  set recoverable($core.bool value) => $_setBool(2, value);
  @$pb.TagNumber(3)
  $core.bool hasRecoverable() => $_has(2);
  @$pb.TagNumber(3)
  void clearRecoverable() => $_clearField(3);
}

/// TranscribeRequest contains the audio file to transcribe.
class TranscribeRequest extends $pb.GeneratedMessage {
  factory TranscribeRequest({
    $core.List<$core.int>? audioData,
    $core.String? filename,
    $core.String? language,
    $core.String? format,
    $core.String? userId,
    $core.bool? enableEnhancement,
    $core.int? sampleRate,
  }) {
    final result = create();
    if (audioData != null) result.audioData = audioData;
    if (filename != null) result.filename = filename;
    if (language != null) result.language = language;
    if (format != null) result.format = format;
    if (userId != null) result.userId = userId;
    if (enableEnhancement != null) result.enableEnhancement = enableEnhancement;
    if (sampleRate != null) result.sampleRate = sampleRate;
    return result;
  }

  TranscribeRequest._();

  factory TranscribeRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory TranscribeRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'TranscribeRequest',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'stt.v1'),
      createEmptyInstance: create)
    ..a<$core.List<$core.int>>(
        1, _omitFieldNames ? '' : 'audioData', $pb.PbFieldType.OY)
    ..aOS(2, _omitFieldNames ? '' : 'filename')
    ..aOS(3, _omitFieldNames ? '' : 'language')
    ..aOS(4, _omitFieldNames ? '' : 'format')
    ..aOS(5, _omitFieldNames ? '' : 'userId')
    ..aOB(6, _omitFieldNames ? '' : 'enableEnhancement')
    ..aI(7, _omitFieldNames ? '' : 'sampleRate')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TranscribeRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TranscribeRequest copyWith(void Function(TranscribeRequest) updates) =>
      super.copyWith((message) => updates(message as TranscribeRequest))
          as TranscribeRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static TranscribeRequest create() => TranscribeRequest._();
  @$core.override
  TranscribeRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static TranscribeRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<TranscribeRequest>(create);
  static TranscribeRequest? _defaultInstance;

  /// Audio file content in binary format
  @$pb.TagNumber(1)
  $core.List<$core.int> get audioData => $_getN(0);
  @$pb.TagNumber(1)
  set audioData($core.List<$core.int> value) => $_setBytes(0, value);
  @$pb.TagNumber(1)
  $core.bool hasAudioData() => $_has(0);
  @$pb.TagNumber(1)
  void clearAudioData() => $_clearField(1);

  /// Original filename (for format detection)
  @$pb.TagNumber(2)
  $core.String get filename => $_getSZ(1);
  @$pb.TagNumber(2)
  set filename($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasFilename() => $_has(1);
  @$pb.TagNumber(2)
  void clearFilename() => $_clearField(2);

  /// Language code (e.g., "zh-CN", "en-US")
  /// If not specified, auto-detection will be attempted
  @$pb.TagNumber(3)
  $core.String get language => $_getSZ(2);
  @$pb.TagNumber(3)
  set language($core.String value) => $_setString(2, value);
  @$pb.TagNumber(3)
  $core.bool hasLanguage() => $_has(2);
  @$pb.TagNumber(3)
  void clearLanguage() => $_clearField(3);

  /// Audio format hint: "wav", "mp3", "m4a", "ogg", "webm"
  @$pb.TagNumber(4)
  $core.String get format => $_getSZ(3);
  @$pb.TagNumber(4)
  set format($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasFormat() => $_has(3);
  @$pb.TagNumber(4)
  void clearFormat() => $_clearField(4);

  /// User ID for tracking and rate limiting
  @$pb.TagNumber(5)
  $core.String get userId => $_getSZ(4);
  @$pb.TagNumber(5)
  set userId($core.String value) => $_setString(4, value);
  @$pb.TagNumber(5)
  $core.bool hasUserId() => $_has(4);
  @$pb.TagNumber(5)
  void clearUserId() => $_clearField(5);

  /// Whether to apply LLM enhancement (punctuation, correction)
  @$pb.TagNumber(6)
  $core.bool get enableEnhancement => $_getBF(5);
  @$pb.TagNumber(6)
  set enableEnhancement($core.bool value) => $_setBool(5, value);
  @$pb.TagNumber(6)
  $core.bool hasEnableEnhancement() => $_has(5);
  @$pb.TagNumber(6)
  void clearEnableEnhancement() => $_clearField(6);

  /// Sample rate if known (helps with processing)
  @$pb.TagNumber(7)
  $core.int get sampleRate => $_getIZ(6);
  @$pb.TagNumber(7)
  set sampleRate($core.int value) => $_setSignedInt32(6, value);
  @$pb.TagNumber(7)
  $core.bool hasSampleRate() => $_has(6);
  @$pb.TagNumber(7)
  void clearSampleRate() => $_clearField(7);
}

/// TranscribeResponse contains the transcription result.
class TranscribeResponse extends $pb.GeneratedMessage {
  factory TranscribeResponse({
    $core.String? text,
    $core.double? durationSeconds,
    $core.double? confidence,
    $core.String? detectedLanguage,
    $core.String? enhancedText,
    $core.Iterable<WordTimestamp>? words,
    TranscriptionMetadata? metadata,
    TranscriptionError? error,
  }) {
    final result = create();
    if (text != null) result.text = text;
    if (durationSeconds != null) result.durationSeconds = durationSeconds;
    if (confidence != null) result.confidence = confidence;
    if (detectedLanguage != null) result.detectedLanguage = detectedLanguage;
    if (enhancedText != null) result.enhancedText = enhancedText;
    if (words != null) result.words.addAll(words);
    if (metadata != null) result.metadata = metadata;
    if (error != null) result.error = error;
    return result;
  }

  TranscribeResponse._();

  factory TranscribeResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory TranscribeResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'TranscribeResponse',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'stt.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'text')
    ..aD(2, _omitFieldNames ? '' : 'durationSeconds',
        fieldType: $pb.PbFieldType.OF)
    ..aD(3, _omitFieldNames ? '' : 'confidence', fieldType: $pb.PbFieldType.OF)
    ..aOS(4, _omitFieldNames ? '' : 'detectedLanguage')
    ..aOS(5, _omitFieldNames ? '' : 'enhancedText')
    ..pPM<WordTimestamp>(6, _omitFieldNames ? '' : 'words',
        subBuilder: WordTimestamp.create)
    ..aOM<TranscriptionMetadata>(7, _omitFieldNames ? '' : 'metadata',
        subBuilder: TranscriptionMetadata.create)
    ..aOM<TranscriptionError>(8, _omitFieldNames ? '' : 'error',
        subBuilder: TranscriptionError.create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TranscribeResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TranscribeResponse copyWith(void Function(TranscribeResponse) updates) =>
      super.copyWith((message) => updates(message as TranscribeResponse))
          as TranscribeResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static TranscribeResponse create() => TranscribeResponse._();
  @$core.override
  TranscribeResponse createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static TranscribeResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<TranscribeResponse>(create);
  static TranscribeResponse? _defaultInstance;

  /// Full transcribed text
  @$pb.TagNumber(1)
  $core.String get text => $_getSZ(0);
  @$pb.TagNumber(1)
  set text($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasText() => $_has(0);
  @$pb.TagNumber(1)
  void clearText() => $_clearField(1);

  /// Duration of the audio in seconds
  @$pb.TagNumber(2)
  $core.double get durationSeconds => $_getN(1);
  @$pb.TagNumber(2)
  set durationSeconds($core.double value) => $_setFloat(1, value);
  @$pb.TagNumber(2)
  $core.bool hasDurationSeconds() => $_has(1);
  @$pb.TagNumber(2)
  void clearDurationSeconds() => $_clearField(2);

  /// Overall confidence score (0.0-1.0)
  @$pb.TagNumber(3)
  $core.double get confidence => $_getN(2);
  @$pb.TagNumber(3)
  set confidence($core.double value) => $_setFloat(2, value);
  @$pb.TagNumber(3)
  $core.bool hasConfidence() => $_has(2);
  @$pb.TagNumber(3)
  void clearConfidence() => $_clearField(3);

  /// Detected language (if auto-detection was used)
  @$pb.TagNumber(4)
  $core.String get detectedLanguage => $_getSZ(3);
  @$pb.TagNumber(4)
  set detectedLanguage($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasDetectedLanguage() => $_has(3);
  @$pb.TagNumber(4)
  void clearDetectedLanguage() => $_clearField(4);

  /// Enhanced text (if enhancement was enabled)
  @$pb.TagNumber(5)
  $core.String get enhancedText => $_getSZ(4);
  @$pb.TagNumber(5)
  set enhancedText($core.String value) => $_setString(4, value);
  @$pb.TagNumber(5)
  $core.bool hasEnhancedText() => $_has(4);
  @$pb.TagNumber(5)
  void clearEnhancedText() => $_clearField(5);

  /// Word-level timestamps (optional, for subtitle generation)
  @$pb.TagNumber(6)
  $pb.PbList<WordTimestamp> get words => $_getList(5);

  /// Processing metadata
  @$pb.TagNumber(7)
  TranscriptionMetadata get metadata => $_getN(6);
  @$pb.TagNumber(7)
  set metadata(TranscriptionMetadata value) => $_setField(7, value);
  @$pb.TagNumber(7)
  $core.bool hasMetadata() => $_has(6);
  @$pb.TagNumber(7)
  void clearMetadata() => $_clearField(7);
  @$pb.TagNumber(7)
  TranscriptionMetadata ensureMetadata() => $_ensure(6);

  /// Error if transcription failed
  @$pb.TagNumber(8)
  TranscriptionError get error => $_getN(7);
  @$pb.TagNumber(8)
  set error(TranscriptionError value) => $_setField(8, value);
  @$pb.TagNumber(8)
  $core.bool hasError() => $_has(7);
  @$pb.TagNumber(8)
  void clearError() => $_clearField(8);
  @$pb.TagNumber(8)
  TranscriptionError ensureError() => $_ensure(7);
}

/// WordTimestamp provides word-level timing information.
class WordTimestamp extends $pb.GeneratedMessage {
  factory WordTimestamp({
    $core.String? word,
    $core.double? startTime,
    $core.double? endTime,
    $core.double? confidence,
  }) {
    final result = create();
    if (word != null) result.word = word;
    if (startTime != null) result.startTime = startTime;
    if (endTime != null) result.endTime = endTime;
    if (confidence != null) result.confidence = confidence;
    return result;
  }

  WordTimestamp._();

  factory WordTimestamp.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory WordTimestamp.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'WordTimestamp',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'stt.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'word')
    ..aD(2, _omitFieldNames ? '' : 'startTime', fieldType: $pb.PbFieldType.OF)
    ..aD(3, _omitFieldNames ? '' : 'endTime', fieldType: $pb.PbFieldType.OF)
    ..aD(4, _omitFieldNames ? '' : 'confidence', fieldType: $pb.PbFieldType.OF)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  WordTimestamp clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  WordTimestamp copyWith(void Function(WordTimestamp) updates) =>
      super.copyWith((message) => updates(message as WordTimestamp))
          as WordTimestamp;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static WordTimestamp create() => WordTimestamp._();
  @$core.override
  WordTimestamp createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static WordTimestamp getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<WordTimestamp>(create);
  static WordTimestamp? _defaultInstance;

  /// The word text
  @$pb.TagNumber(1)
  $core.String get word => $_getSZ(0);
  @$pb.TagNumber(1)
  set word($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasWord() => $_has(0);
  @$pb.TagNumber(1)
  void clearWord() => $_clearField(1);

  /// Start time in seconds
  @$pb.TagNumber(2)
  $core.double get startTime => $_getN(1);
  @$pb.TagNumber(2)
  set startTime($core.double value) => $_setFloat(1, value);
  @$pb.TagNumber(2)
  $core.bool hasStartTime() => $_has(1);
  @$pb.TagNumber(2)
  void clearStartTime() => $_clearField(2);

  /// End time in seconds
  @$pb.TagNumber(3)
  $core.double get endTime => $_getN(2);
  @$pb.TagNumber(3)
  set endTime($core.double value) => $_setFloat(2, value);
  @$pb.TagNumber(3)
  $core.bool hasEndTime() => $_has(2);
  @$pb.TagNumber(3)
  void clearEndTime() => $_clearField(3);

  /// Confidence for this word
  @$pb.TagNumber(4)
  $core.double get confidence => $_getN(3);
  @$pb.TagNumber(4)
  set confidence($core.double value) => $_setFloat(3, value);
  @$pb.TagNumber(4)
  $core.bool hasConfidence() => $_has(3);
  @$pb.TagNumber(4)
  void clearConfidence() => $_clearField(4);
}

/// TranscriptionMetadata contains processing information.
class TranscriptionMetadata extends $pb.GeneratedMessage {
  factory TranscriptionMetadata({
    $core.String? provider,
    $core.String? model,
    $fixnum.Int64? processingTimeMs,
    $fixnum.Int64? fileSizeBytes,
    $core.int? channels,
    $core.int? sampleRate,
  }) {
    final result = create();
    if (provider != null) result.provider = provider;
    if (model != null) result.model = model;
    if (processingTimeMs != null) result.processingTimeMs = processingTimeMs;
    if (fileSizeBytes != null) result.fileSizeBytes = fileSizeBytes;
    if (channels != null) result.channels = channels;
    if (sampleRate != null) result.sampleRate = sampleRate;
    return result;
  }

  TranscriptionMetadata._();

  factory TranscriptionMetadata.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory TranscriptionMetadata.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'TranscriptionMetadata',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'stt.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'provider')
    ..aOS(2, _omitFieldNames ? '' : 'model')
    ..aInt64(3, _omitFieldNames ? '' : 'processingTimeMs')
    ..aInt64(4, _omitFieldNames ? '' : 'fileSizeBytes')
    ..aI(5, _omitFieldNames ? '' : 'channels')
    ..aI(6, _omitFieldNames ? '' : 'sampleRate')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TranscriptionMetadata clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  TranscriptionMetadata copyWith(
          void Function(TranscriptionMetadata) updates) =>
      super.copyWith((message) => updates(message as TranscriptionMetadata))
          as TranscriptionMetadata;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static TranscriptionMetadata create() => TranscriptionMetadata._();
  @$core.override
  TranscriptionMetadata createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static TranscriptionMetadata getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<TranscriptionMetadata>(create);
  static TranscriptionMetadata? _defaultInstance;

  /// Provider used for transcription (e.g., "zhipu", "whisper")
  @$pb.TagNumber(1)
  $core.String get provider => $_getSZ(0);
  @$pb.TagNumber(1)
  set provider($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasProvider() => $_has(0);
  @$pb.TagNumber(1)
  void clearProvider() => $_clearField(1);

  /// Model used
  @$pb.TagNumber(2)
  $core.String get model => $_getSZ(1);
  @$pb.TagNumber(2)
  set model($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasModel() => $_has(1);
  @$pb.TagNumber(2)
  void clearModel() => $_clearField(2);

  /// Processing time in milliseconds
  @$pb.TagNumber(3)
  $fixnum.Int64 get processingTimeMs => $_getI64(2);
  @$pb.TagNumber(3)
  set processingTimeMs($fixnum.Int64 value) => $_setInt64(2, value);
  @$pb.TagNumber(3)
  $core.bool hasProcessingTimeMs() => $_has(2);
  @$pb.TagNumber(3)
  void clearProcessingTimeMs() => $_clearField(3);

  /// Audio file size in bytes
  @$pb.TagNumber(4)
  $fixnum.Int64 get fileSizeBytes => $_getI64(3);
  @$pb.TagNumber(4)
  set fileSizeBytes($fixnum.Int64 value) => $_setInt64(3, value);
  @$pb.TagNumber(4)
  $core.bool hasFileSizeBytes() => $_has(3);
  @$pb.TagNumber(4)
  void clearFileSizeBytes() => $_clearField(4);

  /// Number of audio channels
  @$pb.TagNumber(5)
  $core.int get channels => $_getIZ(4);
  @$pb.TagNumber(5)
  set channels($core.int value) => $_setSignedInt32(4, value);
  @$pb.TagNumber(5)
  $core.bool hasChannels() => $_has(4);
  @$pb.TagNumber(5)
  void clearChannels() => $_clearField(5);

  /// Sample rate used for processing
  @$pb.TagNumber(6)
  $core.int get sampleRate => $_getIZ(5);
  @$pb.TagNumber(6)
  set sampleRate($core.int value) => $_setSignedInt32(5, value);
  @$pb.TagNumber(6)
  $core.bool hasSampleRate() => $_has(5);
  @$pb.TagNumber(6)
  void clearSampleRate() => $_clearField(6);
}

/// EnhanceRequest contains the raw transcript to enhance.
class EnhanceRequest extends $pb.GeneratedMessage {
  factory EnhanceRequest({
    $core.String? text,
    $core.String? userId,
    EnhancementOptions? options,
  }) {
    final result = create();
    if (text != null) result.text = text;
    if (userId != null) result.userId = userId;
    if (options != null) result.options = options;
    return result;
  }

  EnhanceRequest._();

  factory EnhanceRequest.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory EnhanceRequest.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'EnhanceRequest',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'stt.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'text')
    ..aOS(2, _omitFieldNames ? '' : 'userId')
    ..aOM<EnhancementOptions>(3, _omitFieldNames ? '' : 'options',
        subBuilder: EnhancementOptions.create)
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  EnhanceRequest clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  EnhanceRequest copyWith(void Function(EnhanceRequest) updates) =>
      super.copyWith((message) => updates(message as EnhanceRequest))
          as EnhanceRequest;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static EnhanceRequest create() => EnhanceRequest._();
  @$core.override
  EnhanceRequest createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static EnhanceRequest getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<EnhanceRequest>(create);
  static EnhanceRequest? _defaultInstance;

  /// Raw transcript text
  @$pb.TagNumber(1)
  $core.String get text => $_getSZ(0);
  @$pb.TagNumber(1)
  set text($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasText() => $_has(0);
  @$pb.TagNumber(1)
  void clearText() => $_clearField(1);

  /// User ID for personalization
  @$pb.TagNumber(2)
  $core.String get userId => $_getSZ(1);
  @$pb.TagNumber(2)
  set userId($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasUserId() => $_has(1);
  @$pb.TagNumber(2)
  void clearUserId() => $_clearField(2);

  /// Enhancement options
  @$pb.TagNumber(3)
  EnhancementOptions get options => $_getN(2);
  @$pb.TagNumber(3)
  set options(EnhancementOptions value) => $_setField(3, value);
  @$pb.TagNumber(3)
  $core.bool hasOptions() => $_has(2);
  @$pb.TagNumber(3)
  void clearOptions() => $_clearField(3);
  @$pb.TagNumber(3)
  EnhancementOptions ensureOptions() => $_ensure(2);
}

/// EnhancementOptions configures the enhancement behavior.
class EnhancementOptions extends $pb.GeneratedMessage {
  factory EnhancementOptions({
    $core.bool? addPunctuation,
    $core.bool? correctTypos,
    $core.bool? formatSpeakers,
    $core.String? language,
  }) {
    final result = create();
    if (addPunctuation != null) result.addPunctuation = addPunctuation;
    if (correctTypos != null) result.correctTypos = correctTypos;
    if (formatSpeakers != null) result.formatSpeakers = formatSpeakers;
    if (language != null) result.language = language;
    return result;
  }

  EnhancementOptions._();

  factory EnhancementOptions.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory EnhancementOptions.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'EnhancementOptions',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'stt.v1'),
      createEmptyInstance: create)
    ..aOB(1, _omitFieldNames ? '' : 'addPunctuation')
    ..aOB(2, _omitFieldNames ? '' : 'correctTypos')
    ..aOB(3, _omitFieldNames ? '' : 'formatSpeakers')
    ..aOS(4, _omitFieldNames ? '' : 'language')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  EnhancementOptions clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  EnhancementOptions copyWith(void Function(EnhancementOptions) updates) =>
      super.copyWith((message) => updates(message as EnhancementOptions))
          as EnhancementOptions;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static EnhancementOptions create() => EnhancementOptions._();
  @$core.override
  EnhancementOptions createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static EnhancementOptions getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<EnhancementOptions>(create);
  static EnhancementOptions? _defaultInstance;

  /// Add punctuation
  @$pb.TagNumber(1)
  $core.bool get addPunctuation => $_getBF(0);
  @$pb.TagNumber(1)
  set addPunctuation($core.bool value) => $_setBool(0, value);
  @$pb.TagNumber(1)
  $core.bool hasAddPunctuation() => $_has(0);
  @$pb.TagNumber(1)
  void clearAddPunctuation() => $_clearField(1);

  /// Correct typos and homophones
  @$pb.TagNumber(2)
  $core.bool get correctTypos => $_getBF(1);
  @$pb.TagNumber(2)
  set correctTypos($core.bool value) => $_setBool(1, value);
  @$pb.TagNumber(2)
  $core.bool hasCorrectTypos() => $_has(1);
  @$pb.TagNumber(2)
  void clearCorrectTypos() => $_clearField(2);

  /// Format speaker turns (detect multiple speakers)
  @$pb.TagNumber(3)
  $core.bool get formatSpeakers => $_getBF(2);
  @$pb.TagNumber(3)
  set formatSpeakers($core.bool value) => $_setBool(2, value);
  @$pb.TagNumber(3)
  $core.bool hasFormatSpeakers() => $_has(2);
  @$pb.TagNumber(3)
  void clearFormatSpeakers() => $_clearField(3);

  /// Language for enhancement
  @$pb.TagNumber(4)
  $core.String get language => $_getSZ(3);
  @$pb.TagNumber(4)
  set language($core.String value) => $_setString(3, value);
  @$pb.TagNumber(4)
  $core.bool hasLanguage() => $_has(3);
  @$pb.TagNumber(4)
  void clearLanguage() => $_clearField(4);
}

/// EnhanceResponse contains the enhanced transcript.
class EnhanceResponse extends $pb.GeneratedMessage {
  factory EnhanceResponse({
    $core.String? enhancedText,
    $core.String? originalText,
    $core.int? changesCount,
    $fixnum.Int64? processingTimeMs,
  }) {
    final result = create();
    if (enhancedText != null) result.enhancedText = enhancedText;
    if (originalText != null) result.originalText = originalText;
    if (changesCount != null) result.changesCount = changesCount;
    if (processingTimeMs != null) result.processingTimeMs = processingTimeMs;
    return result;
  }

  EnhanceResponse._();

  factory EnhanceResponse.fromBuffer($core.List<$core.int> data,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromBuffer(data, registry);
  factory EnhanceResponse.fromJson($core.String json,
          [$pb.ExtensionRegistry registry = $pb.ExtensionRegistry.EMPTY]) =>
      create()..mergeFromJson(json, registry);

  static final $pb.BuilderInfo _i = $pb.BuilderInfo(
      _omitMessageNames ? '' : 'EnhanceResponse',
      package: const $pb.PackageName(_omitMessageNames ? '' : 'stt.v1'),
      createEmptyInstance: create)
    ..aOS(1, _omitFieldNames ? '' : 'enhancedText')
    ..aOS(2, _omitFieldNames ? '' : 'originalText')
    ..aI(3, _omitFieldNames ? '' : 'changesCount')
    ..aInt64(4, _omitFieldNames ? '' : 'processingTimeMs')
    ..hasRequiredFields = false;

  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  EnhanceResponse clone() => deepCopy();
  @$core.Deprecated('See https://github.com/google/protobuf.dart/issues/998.')
  EnhanceResponse copyWith(void Function(EnhanceResponse) updates) =>
      super.copyWith((message) => updates(message as EnhanceResponse))
          as EnhanceResponse;

  @$core.override
  $pb.BuilderInfo get info_ => _i;

  @$core.pragma('dart2js:noInline')
  static EnhanceResponse create() => EnhanceResponse._();
  @$core.override
  EnhanceResponse createEmptyInstance() => create();
  @$core.pragma('dart2js:noInline')
  static EnhanceResponse getDefault() => _defaultInstance ??=
      $pb.GeneratedMessage.$_defaultFor<EnhanceResponse>(create);
  static EnhanceResponse? _defaultInstance;

  /// Enhanced text
  @$pb.TagNumber(1)
  $core.String get enhancedText => $_getSZ(0);
  @$pb.TagNumber(1)
  set enhancedText($core.String value) => $_setString(0, value);
  @$pb.TagNumber(1)
  $core.bool hasEnhancedText() => $_has(0);
  @$pb.TagNumber(1)
  void clearEnhancedText() => $_clearField(1);

  /// Original text (for comparison)
  @$pb.TagNumber(2)
  $core.String get originalText => $_getSZ(1);
  @$pb.TagNumber(2)
  set originalText($core.String value) => $_setString(1, value);
  @$pb.TagNumber(2)
  $core.bool hasOriginalText() => $_has(1);
  @$pb.TagNumber(2)
  void clearOriginalText() => $_clearField(2);

  /// Number of changes made
  @$pb.TagNumber(3)
  $core.int get changesCount => $_getIZ(2);
  @$pb.TagNumber(3)
  set changesCount($core.int value) => $_setSignedInt32(2, value);
  @$pb.TagNumber(3)
  $core.bool hasChangesCount() => $_has(2);
  @$pb.TagNumber(3)
  void clearChangesCount() => $_clearField(3);

  /// Processing time in milliseconds
  @$pb.TagNumber(4)
  $fixnum.Int64 get processingTimeMs => $_getI64(3);
  @$pb.TagNumber(4)
  set processingTimeMs($fixnum.Int64 value) => $_setInt64(3, value);
  @$pb.TagNumber(4)
  $core.bool hasProcessingTimeMs() => $_has(3);
  @$pb.TagNumber(4)
  void clearProcessingTimeMs() => $_clearField(4);
}

const $core.bool _omitFieldNames =
    $core.bool.fromEnvironment('protobuf.omit_field_names');
const $core.bool _omitMessageNames =
    $core.bool.fromEnvironment('protobuf.omit_message_names');
