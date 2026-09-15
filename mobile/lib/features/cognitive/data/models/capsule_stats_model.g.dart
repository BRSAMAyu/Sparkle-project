// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'capsule_stats_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

CapsuleStatsModel _$CapsuleStatsModelFromJson(Map<String, dynamic> json) =>
    CapsuleStatsModel(
      totalReceived: (json['total_received'] as num).toInt(),
      totalRead: (json['total_read'] as num).toInt(),
      totalFavorited: (json['total_favorited'] as num).toInt(),
      totalFeedbackGiven: (json['total_feedback_given'] as num).toInt(),
      averageRatingGiven: (json['average_rating_given'] as num?)?.toDouble(),
    );

Map<String, dynamic> _$CapsuleStatsModelToJson(CapsuleStatsModel instance) =>
    <String, dynamic>{
      'total_received': instance.totalReceived,
      'total_read': instance.totalRead,
      'total_favorited': instance.totalFavorited,
      'total_feedback_given': instance.totalFeedbackGiven,
      'average_rating_given': instance.averageRatingGiven,
    };
