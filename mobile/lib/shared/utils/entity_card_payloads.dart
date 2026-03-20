import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class PlanCardPayload {
  const PlanCardPayload({
    required this.title,
    required this.type,
    this.id,
    this.description,
    this.subject,
    this.planStage,
    this.targetDate,
    this.progress,
    this.taskCount,
    this.targetMastery,
    this.isActive,
    this.isPrimary,
    this.source,
  });

  factory PlanCardPayload.fromMap(Map<String, dynamic> raw) {
    final normalizedType = _normalizePlanType(
      raw['type'] ?? raw['plan_type'] ?? raw['category'],
    );
    return PlanCardPayload(
      id: _asString(raw['id'] ?? raw['plan_id']),
      title: _asString(raw['title'] ?? raw['name']) ?? '未命名计划',
      type: normalizedType,
      description: _asString(raw['description']),
      subject: _asString(raw['subject']),
      planStage: _asString(raw['plan_stage']),
      targetDate: _parseDate(raw['target_date']),
      progress: _asDouble(raw['progress']),
      taskCount: _asInt(raw['task_count']),
      targetMastery: _asDouble(raw['target_mastery']),
      isActive: _asBool(raw['is_active']),
      isPrimary: _asBool(raw['is_primary']),
      source: _asString(raw['source']),
    );
  }

  final String? id;
  final String title;
  final String type;
  final String? description;
  final String? subject;
  final String? planStage;
  final DateTime? targetDate;
  final double? progress;
  final int? taskCount;
  final double? targetMastery;
  final bool? isActive;
  final bool? isPrimary;
  final String? source;

  PlanType? get planType {
    switch (type) {
      case 'growth':
        return PlanType.growth;
      case 'sprint':
        return PlanType.sprint;
      default:
        return null;
    }
  }
}

TaskModel? taskModelFromEntityPayload(Map<String, dynamic> raw) {
  try {
    final now = DateTime.now().toIso8601String();
    final normalized = <String, dynamic>{
      ...raw,
      'id': _asString(raw['id']) ?? '',
      'user_id': _asString(raw['user_id']) ?? 'current_user',
      'plan_id': _asString(raw['plan_id']),
      'title': _asString(raw['title']) ?? '未命名任务',
      'type': _normalizeTaskType(raw['type']),
      'tags': (raw['tags'] as List<dynamic>? ?? const <dynamic>[])
          .map((item) => item.toString())
          .toList(),
      'estimated_minutes': _asInt(raw['estimated_minutes']) ?? 30,
      'difficulty': _asInt(raw['difficulty']) ?? 1,
      'energy_cost': _asInt(raw['energy_cost']) ?? 1,
      'guide_content':
          _asString(raw['guide_content']) ?? _asString(raw['description']),
      'status': _normalizeTaskStatus(raw['status']),
      'started_at': _parseDate(raw['started_at'])?.toIso8601String(),
      'completed_at': _parseDate(raw['completed_at'])?.toIso8601String(),
      'actual_minutes': _asInt(raw['actual_minutes']),
      'user_note': _asString(raw['user_note']),
      'priority': _asInt(raw['priority']) ?? 2,
      'due_date': _parseDate(raw['due_date'])?.toIso8601String(),
      'knowledge_node_id': _asString(raw['knowledge_node_id']),
      'subtasks_total': _asInt(raw['subtasks_total']) ?? 0,
      'subtasks_completed': _asInt(raw['subtasks_completed']) ?? 0,
      'created_at': _parseDate(raw['created_at'])?.toIso8601String() ?? now,
      'updated_at':
          _parseDate(raw['updated_at'] ?? raw['created_at'])?.toIso8601String() ??
              now,
    };
    if ((normalized['id'] as String).isEmpty) {
      return null;
    }
    return TaskModel.fromJson(normalized);
  } catch (_) {
    return null;
  }
}

String _normalizeTaskType(dynamic raw) {
  final value = _asString(raw)?.trim().toLowerCase();
  switch (value) {
    case 'learning':
      return 'LEARNING';
    case 'training':
    case 'practice':
      return 'TRAINING';
    case 'error_fix':
    case 'errorfix':
      return 'ERROR_FIX';
    case 'reflection':
    case 'review':
      return 'REFLECTION';
    case 'social':
      return 'SOCIAL';
    case 'planning':
      return 'PLANNING';
    case 'ocr':
      return 'OCR';
    default:
      return 'LEARNING';
  }
}

String _normalizeTaskStatus(dynamic raw) {
  final value = _asString(raw)?.trim().toLowerCase();
  switch (value) {
    case 'pending':
      return 'PENDING';
    case 'in_progress':
    case 'inprogress':
      return 'IN_PROGRESS';
    case 'completed':
      return 'COMPLETED';
    case 'abandoned':
      return 'ABANDONED';
    default:
      return 'PENDING';
  }
}

String _normalizePlanType(dynamic raw) {
  final value = _asString(raw)?.trim().toLowerCase();
  switch (value) {
    case 'growth':
      return 'growth';
    case 'sprint':
      return 'sprint';
    default:
      return 'growth';
  }
}

String? _asString(dynamic value) {
  if (value == null) return null;
  final text = value.toString().trim();
  return text.isEmpty ? null : text;
}

int? _asInt(dynamic value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  return int.tryParse(value?.toString() ?? '');
}

double? _asDouble(dynamic value) {
  if (value is double) return value;
  if (value is num) return value.toDouble();
  return double.tryParse(value?.toString() ?? '');
}

bool? _asBool(dynamic value) {
  if (value is bool) return value;
  final text = value?.toString().toLowerCase();
  switch (text) {
    case 'true':
    case '1':
      return true;
    case 'false':
    case '0':
      return false;
    default:
      return null;
  }
}

DateTime? _parseDate(dynamic value) {
  if (value is DateTime) return value;
  final text = _asString(value);
  if (text == null) return null;
  return DateTime.tryParse(text);
}
