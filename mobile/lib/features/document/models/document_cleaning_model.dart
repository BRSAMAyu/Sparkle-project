import 'package:freezed_annotation/freezed_annotation.dart';

part 'document_cleaning_model.freezed.dart';
part 'document_cleaning_model.g.dart';

@freezed
class CleaningTaskStatus with _$CleaningTaskStatus {
  const factory CleaningTaskStatus({
    required String status, // queued, processing, completed, failed
    required int percent,
    required String message,
    CleaningResult? result,
  }) = _CleaningTaskStatus;

  factory CleaningTaskStatus.fromJson(Map<String, dynamic> json) =>
      _$CleaningTaskStatusFromJson(json);
}

@freezed
class CleaningResult with _$CleaningResult {
  const factory CleaningResult({
    required String status,
    required String mode, // full_text, map_reduce
    required String summary,
    @JsonKey(name: 'full_text') String? fullText,
    @JsonKey(name: 'full_text_preview') String? fullTextPreview,
    @JsonKey(name: 'char_count') int? charCount,
  }) = _CleaningResult;

  factory CleaningResult.fromJson(Map<String, dynamic> json) =>
      _$CleaningResultFromJson(json);
}
