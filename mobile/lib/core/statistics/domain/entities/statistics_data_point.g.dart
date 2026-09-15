// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'statistics_data_point.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$StatisticsDataPointImpl _$$StatisticsDataPointImplFromJson(
        Map<String, dynamic> json) =>
    _$StatisticsDataPointImpl(
      timestamp: DateTime.parse(json['timestamp'] as String),
      value: (json['value'] as num).toDouble(),
      secondaryValue: (json['secondaryValue'] as num?)?.toDouble(),
      label: json['label'] as String?,
      metadata: json['metadata'] as Map<String, dynamic>? ?? const {},
    );

Map<String, dynamic> _$$StatisticsDataPointImplToJson(
        _$StatisticsDataPointImpl instance) =>
    <String, dynamic>{
      'timestamp': instance.timestamp.toIso8601String(),
      'value': instance.value,
      'secondaryValue': instance.secondaryValue,
      'label': instance.label,
      'metadata': instance.metadata,
    };

_$StatisticsDataSeriesImpl _$$StatisticsDataSeriesImplFromJson(
        Map<String, dynamic> json) =>
    _$StatisticsDataSeriesImpl(
      id: json['id'] as String,
      name: json['name'] as String,
      points: (json['points'] as List<dynamic>)
          .map((e) => StatisticsDataPoint.fromJson(e as Map<String, dynamic>))
          .toList(),
      color: json['color'] as String?,
      unit: json['unit'] as String?,
      maxValue: (json['maxValue'] as num?)?.toDouble(),
      minValue: (json['minValue'] as num?)?.toDouble(),
      averageValue: (json['averageValue'] as num?)?.toDouble(),
      totalValue: (json['totalValue'] as num?)?.toDouble(),
    );

Map<String, dynamic> _$$StatisticsDataSeriesImplToJson(
        _$StatisticsDataSeriesImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'points': instance.points,
      'color': instance.color,
      'unit': instance.unit,
      'maxValue': instance.maxValue,
      'minValue': instance.minValue,
      'averageValue': instance.averageValue,
      'totalValue': instance.totalValue,
    };
