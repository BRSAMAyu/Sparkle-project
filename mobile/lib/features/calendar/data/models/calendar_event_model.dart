class CalendarEventModel {
  CalendarEventModel({
    required this.id,
    required this.title,
    required this.startTime,
    required this.endTime,
    required this.createdAt,
    required this.updatedAt,
    this.description,
    this.isAllDay = false,
    this.location,
    this.colorValue = 0xFF2196F3,
    this.reminderMinutes = const [],
    this.recurrenceRule,
    this.recurrenceEndDate,
    this.source = 'manual',
    this.sourceMetadata,
    this.taskId,
    this.planId,
    this.isSynced = false,
    this.isDeleted = false,
  });

  factory CalendarEventModel.fromJson(Map<String, dynamic> json) =>
      CalendarEventModel(
        id: json['id'] as String,
        title: json['title'] as String,
        description: _stringOrNull(json['description']),
        startTime: _parseDateTime(_valueForKeys(json, ['startTime', 'start_time'])),
        endTime: _parseDateTime(_valueForKeys(json, ['endTime', 'end_time'])),
        isAllDay: (_valueForKeys(json, ['isAllDay', 'is_all_day']) as bool?) ?? false,
        location: _stringOrNull(json['location']),
        colorValue: (_valueForKeys(json, ['colorValue', 'color_value']) as int?) ??
            (_valueForKeys(json, ['color']) != null
                ? _parseColor(_valueForKeys(json, ['color']))
                : 0xFF2196F3),
        reminderMinutes: (_valueForKeys(json, ['reminderMinutes', 'reminder_minutes']) as List<dynamic>?)
                ?.map((e) => e as int)
                .toList() ??
            [],
        recurrenceRule: _stringOrNull(_valueForKeys(json, ['recurrenceRule', 'recurrence_rule'])),
        recurrenceEndDate: _valueForKeys(json, ['recurrenceEndDate', 'recurrence_end_date']) != null
            ? _parseDateTime(_valueForKeys(json, ['recurrenceEndDate', 'recurrence_end_date']))
            : null,
        source: _stringOrNull(json['source']) ?? 'manual',
        sourceMetadata: _mapOrNull(_valueForKeys(json, ['sourceMetadata', 'source_metadata'])),
        taskId: _stringOrNull(_valueForKeys(json, ['taskId', 'task_id'])),
        planId: _stringOrNull(_valueForKeys(json, ['planId', 'plan_id'])),
        isSynced: (_valueForKeys(json, ['isSynced', 'is_synced']) as bool?) ?? false,
        isDeleted: (_valueForKeys(json, ['isDeleted', 'is_deleted']) as bool?) ?? false,
        createdAt: _parseDateTime(_valueForKeys(json, ['createdAt', 'created_at'])),
        updatedAt: _parseDateTime(_valueForKeys(json, ['updatedAt', 'updated_at'])),
      );

  final String id;
  final String title;
  final String? description;
  final DateTime startTime;
  final DateTime endTime;
  final bool isAllDay;
  final String? location;
  final int colorValue;
  final List<int> reminderMinutes;
  final String? recurrenceRule;
  final DateTime? recurrenceEndDate;
  final String source;
  final Map<String, dynamic>? sourceMetadata;
  final String? taskId;
  final String? planId;
  final bool isSynced;
  final bool isDeleted;
  final DateTime createdAt;
  final DateTime updatedAt;

  /// 本地存储格式 (Hive)
  Map<String, dynamic> toJson() => {
        'id': id,
        'title': title,
        'description': description,
        'startTime': startTime.toIso8601String(),
        'endTime': endTime.toIso8601String(),
        'isAllDay': isAllDay,
        'location': location,
        'colorValue': colorValue,
        'reminderMinutes': reminderMinutes,
        'recurrenceRule': recurrenceRule,
        'recurrenceEndDate': recurrenceEndDate?.toIso8601String(),
        'source': source,
        'sourceMetadata': sourceMetadata,
        'taskId': taskId,
        'planId': planId,
        'isSynced': isSynced,
        'isDeleted': isDeleted,
        'createdAt': createdAt.toIso8601String(),
        'updatedAt': updatedAt.toIso8601String(),
      };

  /// API 格式 (发送到后端)
  Map<String, dynamic> toApiJson() => {
        'title': title,
        'description': description,
        'start_time': startTime.toIso8601String(),
        'end_time': endTime.toIso8601String(),
        'is_all_day': isAllDay,
        'location': location,
        'color': _colorToHex(colorValue),
        'recurrence_rule': recurrenceRule,
        'recurrence_end_date': recurrenceEndDate?.toIso8601String(),
        'reminder_minutes': reminderMinutes,
        'source': source,
        'source_metadata': sourceMetadata,
        'task_id': taskId,
        'plan_id': planId,
      };

  CalendarEventModel copyWith({
    String? id,
    String? title,
    String? description,
    DateTime? startTime,
    DateTime? endTime,
    bool? isAllDay,
    String? location,
    int? colorValue,
    List<int>? reminderMinutes,
    String? recurrenceRule,
    DateTime? recurrenceEndDate,
    String? source,
    Map<String, dynamic>? sourceMetadata,
    String? taskId,
    String? planId,
    bool? isSynced,
    bool? isDeleted,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) =>
      CalendarEventModel(
        id: id ?? this.id,
        title: title ?? this.title,
        description: description ?? this.description,
        startTime: startTime ?? this.startTime,
        endTime: endTime ?? this.endTime,
        isAllDay: isAllDay ?? this.isAllDay,
        location: location ?? this.location,
        colorValue: colorValue ?? this.colorValue,
        reminderMinutes: reminderMinutes ?? this.reminderMinutes,
        recurrenceRule: recurrenceRule ?? this.recurrenceRule,
        recurrenceEndDate: recurrenceEndDate ?? this.recurrenceEndDate,
        source: source ?? this.source,
        sourceMetadata: sourceMetadata ?? this.sourceMetadata,
        taskId: taskId ?? this.taskId,
        planId: planId ?? this.planId,
        isSynced: isSynced ?? this.isSynced,
        isDeleted: isDeleted ?? this.isDeleted,
        createdAt: createdAt ?? this.createdAt,
        updatedAt: updatedAt ?? this.updatedAt,
      );

  /// 颜色值转换辅助方法
  static int _parseColor(dynamic color) {
    if (color is int) return color;
    if (color is String) {
      if (color.startsWith('#')) {
        return int.parse(color.substring(1), radix: 16) + 0xFF000000;
      }
      // 尝试解析命名颜色
      return _namedColorToValue(color) ?? 0xFF2196F3;
    }
    return 0xFF2196F3;
  }

  static dynamic _valueForKeys(Map<String, dynamic> json, List<String> keys) {
    for (final key in keys) {
      if (json.containsKey(key)) {
        return json[key];
      }
    }
    return null;
  }

  static DateTime _parseDateTime(dynamic value) {
    if (value is String) {
      return DateTime.parse(value);
    }
    throw FormatException('Invalid datetime payload: $value');
  }

  static String? _stringOrNull(dynamic value) => value is String ? value : null;

  static Map<String, dynamic>? _mapOrNull(dynamic value) {
    if (value is Map<String, dynamic>) {
      return value;
    }
    if (value is Map) {
      return value.map((key, entry) => MapEntry('$key', entry));
    }
    return null;
  }

  static String _colorToHex(int colorValue) {
    return '#${(colorValue & 0xFFFFFF).toRadixString(16).padLeft(6, '0')}';
  }

  static int? _namedColorToValue(String name) {
    const colorMap = {
      'blue': 0xFF2196F3,
      'red': 0xFFF44336,
      'green': 0xFF4CAF50,
      'yellow': 0xFFFFEB3B,
      'purple': 0xFF9C27B0,
      'orange': 0xFFFF9800,
      'pink': 0xFFE91E63,
      'cyan': 0xFF00BCD4,
    };
    return colorMap[name.toLowerCase()];
  }

  /// 事件时长（分钟）
  int get durationMinutes {
    return endTime.difference(startTime).inMinutes;
  }

  /// 是否为重复事件
  bool get isRecurring => recurrenceRule != null;
}
