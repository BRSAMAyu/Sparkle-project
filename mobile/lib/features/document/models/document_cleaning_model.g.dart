// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'document_cleaning_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$CleaningTaskStatusImpl _$$CleaningTaskStatusImplFromJson(
        Map<String, dynamic> json) =>
    _$CleaningTaskStatusImpl(
      status: json['status'] as String,
      percent: (json['percent'] as num).toInt(),
      message: json['message'] as String,
      result: json['result'] == null
          ? null
          : CleaningResult.fromJson(json['result'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$$CleaningTaskStatusImplToJson(
        _$CleaningTaskStatusImpl instance) =>
    <String, dynamic>{
      'status': instance.status,
      'percent': instance.percent,
      'message': instance.message,
      'result': instance.result,
    };

_$CleaningResultImpl _$$CleaningResultImplFromJson(Map<String, dynamic> json) =>
    _$CleaningResultImpl(
      status: json['status'] as String,
      mode: json['mode'] as String,
      summary: json['summary'] as String,
      fullText: json['full_text'] as String?,
      fullTextPreview: json['full_text_preview'] as String?,
      charCount: (json['char_count'] as num?)?.toInt(),
    );

Map<String, dynamic> _$$CleaningResultImplToJson(
        _$CleaningResultImpl instance) =>
    <String, dynamic>{
      'status': instance.status,
      'mode': instance.mode,
      'summary': instance.summary,
      'full_text': instance.fullText,
      'full_text_preview': instance.fullTextPreview,
      'char_count': instance.charCount,
    };
