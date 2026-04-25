/// Nudge suggestion for task creation
class TaskNudge {
  TaskNudge({
    required this.type,
    required this.title,
    required this.message,
    this.suggestedValue,
    this.patternId,
    this.confidence,
  });

  factory TaskNudge.fromJson(Map<String, dynamic> json) {
    dynamic valueForKeys(List<String> keys) {
      for (final key in keys) {
        if (json.containsKey(key)) {
          return json[key];
        }
      }
      return null;
    }

    String readString(List<String> keys, {String fallback = ''}) {
      final value = valueForKeys(keys);
      return value?.toString() ?? fallback;
    }

    int? readInt(List<String> keys) {
      final value = valueForKeys(keys);
      if (value is int) {
        return value;
      }
      if (value is num) {
        return value.toInt();
      }
      return int.tryParse(value?.toString() ?? '');
    }

    return TaskNudge(
      type: readString(['type']),
      title: readString(['title']),
      message: readString(['message', 'description']),
      suggestedValue: readInt(['suggested_value', 'suggestedValue']),
      patternId: valueForKeys(['pattern_id', 'patternId'])?.toString(),
      confidence: (valueForKeys(['confidence']) as num?)?.toDouble(),
    );
  }

  final String type;
  final String title;
  final String message;
  final int? suggestedValue;
  final String? patternId;
  final double? confidence;
}

/// Result from task creation API including nudges
class TaskCreateResult {
  TaskCreateResult({
    required this.task,
    this.nudges = const [],
  });

  final dynamic task; // TaskModel
  final List<TaskNudge> nudges;
}
