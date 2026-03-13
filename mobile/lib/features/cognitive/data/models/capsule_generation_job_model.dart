import 'package:json_annotation/json_annotation.dart';
import 'package:sparkle/core/services/i18n_service.dart';

part 'capsule_generation_job_model.g.dart';

/// 生成任务状态
enum JobStatus {
  pending('pending', 'Pending', '⏳'),
  generating('generating', 'Generating', '🔄'),
  completed('completed', 'Completed', '✅'),
  failed('failed', 'Failed', '❌');

  const JobStatus(this.value, this.label, this.emoji);

  final String value;
  final String label;
  final String emoji;

  static JobStatus fromValue(String? value) => JobStatus.values.firstWhere(
      (e) => e.value == value,
      orElse: () => JobStatus.pending,
    );
}

/// 生成类型
enum GenerationType {
  daily('daily', 'Daily capsule'),
  weekly('weekly', 'Weekly capsule'),
  manual('manual', 'Manual'),
  pushTriggered('push_triggered', 'Push-triggered');

  const GenerationType(this.value, this.label);

  final String value;
  final String label;

  static GenerationType fromValue(String? value) => GenerationType.values.firstWhere(
      (e) => e.value == value,
      orElse: () => GenerationType.manual,
    );
}

@JsonSerializable()
class CapsuleGenerationJobModel {
  CapsuleGenerationJobModel({
    required this.id,
    required this.status,
    required this.generationType,
    required this.depthPreference,
    required this.curiosityPreference,
    required this.requestedCount,
    required this.createdAt,
    this.actualCount,
    this.capsuleIds,
    this.progress = 0.0,
    this.errorMessage,
    this.durationMs,
    this.completedAt,
  });

  factory CapsuleGenerationJobModel.fromJson(Map<String, dynamic> json) =>
      _$CapsuleGenerationJobModelFromJson(json);

  final String id;

  final String status;

  @JsonKey(name: 'generation_type')
  final String generationType;

  @JsonKey(name: 'depth_preference')
  final double depthPreference;

  @JsonKey(name: 'curiosity_preference')
  final double curiosityPreference;

  @JsonKey(name: 'requested_count')
  final int requestedCount;

  @JsonKey(name: 'actual_count')
  final int? actualCount;

  @JsonKey(name: 'capsule_ids')
  final List<String>? capsuleIds;

  final double progress;

  @JsonKey(name: 'error_message')
  final String? errorMessage;

  @JsonKey(name: 'duration_ms')
  final int? durationMs;

  @JsonKey(name: 'created_at')
  final DateTime createdAt;

  @JsonKey(name: 'completed_at')
  final DateTime? completedAt;

  Map<String, dynamic> toJson() => _$CapsuleGenerationJobModelToJson(this);

  /// 获取状态枚举
  JobStatus get statusEnum => JobStatus.fromValue(status);

  /// 获取生成类型枚举
  GenerationType get typeEnum => GenerationType.fromValue(generationType);

  /// 是否已完成
  bool get isCompleted => statusEnum == JobStatus.completed;

  /// 是否失败
  bool get isFailed => statusEnum == JobStatus.failed;

  /// 是否进行中
  bool get isGenerating => statusEnum == JobStatus.generating;

  /// 进度百分比
  int get progressPercent => (progress * 100).round();

  /// 状态emoji
  String get statusEmoji => statusEnum.emoji;

  String get statusLabel {
    final l10n = I18nService.instance.l10n;
    switch (statusEnum) {
      case JobStatus.pending:
        return l10n.capsuleJobStatusPending;
      case JobStatus.generating:
        return l10n.capsuleJobStatusGenerating;
      case JobStatus.completed:
        return l10n.capsuleJobStatusCompleted;
      case JobStatus.failed:
        return l10n.capsuleJobStatusFailed;
    }
  }

  String get generationTypeLabel {
    final l10n = I18nService.instance.l10n;
    switch (typeEnum) {
      case GenerationType.daily:
        return l10n.capsuleGenerationTypeDaily;
      case GenerationType.weekly:
        return l10n.capsuleGenerationTypeWeekly;
      case GenerationType.manual:
        return l10n.capsuleGenerationTypeManual;
      case GenerationType.pushTriggered:
        return l10n.capsuleGenerationTypePushTriggered;
    }
  }
}
