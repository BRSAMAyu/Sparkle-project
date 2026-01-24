// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'edge_state_schema.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$RawStateVectorImpl _$$RawStateVectorImplFromJson(Map<String, dynamic> json) =>
    _$RawStateVectorImpl(
      attention: (json['a'] as num).toInt(),
      fatigue: (json['f'] as num).toInt(),
      stress: (json['s'] as num).toInt(),
      procrastination: (json['p'] as num).toInt(),
      interruptScore: (json['i'] as num).toInt(),
      windowMinutes: (json['w'] as num).toInt(),
      toneEnum: (json['t'] as num).toInt(),
    );

Map<String, dynamic> _$$RawStateVectorImplToJson(
        _$RawStateVectorImpl instance) =>
    <String, dynamic>{
      'a': instance.attention,
      'f': instance.fatigue,
      's': instance.stress,
      'p': instance.procrastination,
      'i': instance.interruptScore,
      'w': instance.windowMinutes,
      't': instance.toneEnum,
    };

_$EdgeStateImpl _$$EdgeStateImplFromJson(Map<String, dynamic> json) =>
    _$EdgeStateImpl(
      attentionScore: (json['attentionScore'] as num).toDouble(),
      fatigueScore: (json['fatigueScore'] as num).toDouble(),
      stressScore: (json['stressScore'] as num).toDouble(),
      shouldInterrupt: json['shouldInterrupt'] as bool,
      nudgeTone: json['nudgeTone'] as String,
      bestWindow: Duration(microseconds: (json['bestWindow'] as num).toInt()),
      timestamp: (json['timestamp'] as num).toInt(),
    );

Map<String, dynamic> _$$EdgeStateImplToJson(_$EdgeStateImpl instance) =>
    <String, dynamic>{
      'attentionScore': instance.attentionScore,
      'fatigueScore': instance.fatigueScore,
      'stressScore': instance.stressScore,
      'shouldInterrupt': instance.shouldInterrupt,
      'nudgeTone': instance.nudgeTone,
      'bestWindow': instance.bestWindow.inMicroseconds,
      'timestamp': instance.timestamp,
    };
