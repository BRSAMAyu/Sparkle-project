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
  });

  factory CalendarEventModel.fromJson(Map<String, dynamic> json) =>
      CalendarEventModel(
        id: json['id'] as String,
        title: json['title'] as String,
        description: json['description'] as String?,
        startTime: DateTime.parse(json['startTime'] as String),
        endTime: DateTime.parse(json['endTime'] as String),
        isAllDay: json['isAllDay'] as bool? ?? false,
        location: json['location'] as String?,
        colorValue: json['colorValue'] as int? ?? 0xFF2196F3,
        reminderMinutes: (json['reminderMinutes'] as List<dynamic>?)
                ?.map((e) => e as int)
                .toList() ??
            [],
        recurrenceRule: json['recurrenceRule'] as String?,
        createdAt: DateTime.parse(json['createdAt'] as String),
        updatedAt: DateTime.parse(json['updatedAt'] as String),
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
  final DateTime createdAt;
  final DateTime updatedAt;

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
        'createdAt': createdAt.toIso8601String(),
        'updatedAt': updatedAt.toIso8601String(),
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
        createdAt: createdAt ?? this.createdAt,
        updatedAt: updatedAt ?? this.updatedAt,
      );
}
