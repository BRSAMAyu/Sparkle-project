import 'package:json_annotation/json_annotation.dart';
import 'package:sparkle/core/services/i18n_service.dart';

part 'capsule_stats_model.g.dart';

@JsonSerializable()
class CapsuleStatsModel {
  CapsuleStatsModel({
    required this.totalReceived,
    required this.totalRead,
    required this.totalFavorited,
    required this.totalFeedbackGiven,
    this.averageRatingGiven,
  });

  factory CapsuleStatsModel.fromJson(Map<String, dynamic> json) =>
      _$CapsuleStatsModelFromJson(json);

  @JsonKey(name: 'total_received')
  final int totalReceived;

  @JsonKey(name: 'total_read')
  final int totalRead;

  @JsonKey(name: 'total_favorited')
  final int totalFavorited;

  @JsonKey(name: 'total_feedback_given')
  final int totalFeedbackGiven;

  @JsonKey(name: 'average_rating_given')
  final double? averageRatingGiven;

  Map<String, dynamic> toJson() => _$CapsuleStatsModelToJson(this);

  /// 阅读率
  double get readRate => totalReceived > 0
      ? totalRead / totalReceived
      : 0.0;

  /// 阅读率百分比
  int get readRatePercent => (readRate * 100).round();

  /// 平均评分显示
  String get averageRatingDisplay =>
      averageRatingGiven?.toStringAsFixed(1) ??
      I18nService.instance.l10n.commonNoData;
}
