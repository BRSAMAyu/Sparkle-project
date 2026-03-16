import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';

/// Time slot for scheduling
/// 排程时间槽
class TimeSlot {
  const TimeSlot({
    required this.startHour,
    required this.startMinute,
    required this.endHour,
    required this.endMinute,
    required this.quality,
    this.label,
  });

  final int startHour;
  final int startMinute;
  final int endHour;
  final int endMinute;
  final TimeSlotQuality quality;
  final String? label;

  /// Duration in minutes
  int get durationMinutes =>
      (endHour * 60 + endMinute) - (startHour * 60 + startMinute);

  /// Format as HH:MM
  String get startTimeString =>
      '${startHour.toString().padLeft(2, '0')}:${startMinute.toString().padLeft(2, '0')}';

  /// Format as HH:MM
  String get endTimeString =>
      '${endHour.toString().padLeft(2, '0')}:${endMinute.toString().padLeft(2, '0')}';

  /// Display string (e.g., "09:00 - 10:30")
  String get displayString => '$startTimeString - $endTimeString';

  TimeSlot copyWith({
    int? startHour,
    int? startMinute,
    int? endHour,
    int? endMinute,
    TimeSlotQuality? quality,
    String? label,
  }) =>
      TimeSlot(
        startHour: startHour ?? this.startHour,
        startMinute: startMinute ?? this.startMinute,
        endHour: endHour ?? this.endHour,
        endMinute: endMinute ?? this.endMinute,
        quality: quality ?? this.quality,
        label: label ?? this.label,
      );
}

/// Quality rating for time slots
/// 时间槽质量评级
enum TimeSlotQuality {
  /// Peak productivity hours (high energy, focus)
  /// 高效能时段（高能量、高专注）
  peak,

  /// Normal productive hours
  /// 正常生产时段
  normal,

  /// Low energy periods (good for routine tasks)
  /// 低能量时段（适合常规任务）
  low,

  /// Blocked periods (commute, lunch, etc.)
  /// 阻塞时段（通勤、午餐等）
  blocked,
}

/// Schedule preferences from user settings
/// 用户日程偏好
class SchedulePreferences {
  const SchedulePreferences({
    this.commuteStart,
    this.commuteEnd,
    this.lunchStart,
    this.lunchEnd,
    this.focusPeriod = FocusPeriod.morning,
    this.preferredTaskDuration = 45,
    this.preferredBreakDuration = 15,
  });

  factory SchedulePreferences.fromJson(Map<String, dynamic>? json) {
    if (json == null) return const SchedulePreferences();

    String? commuteStart;
    String? commuteEnd;
    String? lunchStart;
    String? lunchEnd;

    final commute = json['commute'] as List<dynamic>?;
    if (commute != null && commute.length == 2) {
      commuteStart = commute[0] as String?;
      commuteEnd = commute[1] as String?;
    }

    final lunch = json['lunch'] as List<dynamic>?;
    if (lunch != null && lunch.length == 2) {
      lunchStart = lunch[0] as String?;
      lunchEnd = lunch[1] as String?;
    }

    return SchedulePreferences(
      commuteStart: commuteStart,
      commuteEnd: commuteEnd,
      lunchStart: lunchStart,
      lunchEnd: lunchEnd,
      focusPeriod: _parseFocusPeriod(json['focus_period'] as String?),
      preferredTaskDuration: json['preferred_task_duration'] as int? ?? 45,
      preferredBreakDuration: json['preferred_break_duration'] as int? ?? 15,
    );
  }

  final String? commuteStart;
  final String? commuteEnd;
  final String? lunchStart;
  final String? lunchEnd;
  final FocusPeriod focusPeriod;
  final int preferredTaskDuration;
  final int preferredBreakDuration;

  /// Whether user has set commute times
  bool get hasCommuteSettings =>
      commuteStart != null && commuteEnd != null;

  /// Whether user has set lunch times
  bool get hasLunchSettings =>
      lunchStart != null && lunchEnd != null;

  static FocusPeriod _parseFocusPeriod(String? value) {
    switch (value) {
      case 'morning':
        return FocusPeriod.morning;
      case 'afternoon':
        return FocusPeriod.afternoon;
      case 'evening':
        return FocusPeriod.evening;
      default:
        return FocusPeriod.morning;
    }
  }

  Map<String, dynamic> toJson() => {
        'commute': [commuteStart, commuteEnd],
        'lunch': [lunchStart, lunchEnd],
        'focus_period': focusPeriod.name,
        'preferred_task_duration': preferredTaskDuration,
        'preferred_break_duration': preferredBreakDuration,
      };
}

/// Focus period preference
/// 专注时段偏好
enum FocusPeriod {
  morning, // 6:00 - 12:00
  afternoon, // 12:00 - 18:00
  evening, // 18:00 - 23:00
}

/// Suggested time for a task
/// 任务建议时间
class SuggestedTime {
  const SuggestedTime({
    required this.timeSlot,
    required this.reason,
    required this.confidence,
  });

  final TimeSlot timeSlot;
  final String reason;
  final double confidence; // 0.0 - 1.0

  /// Display string for the suggested time
  String get displayString => timeSlot.displayString;
}

/// Smart Schedule Service
/// 智能排程服务
///
/// Analyzes user preferences and cognitive patterns to suggest optimal
/// time slots for tasks.
class SmartScheduleService {
  SmartScheduleService(this._ref);

  final Ref _ref;

  /// Get suggested time slots for a task
  /// 获取任务的建议时间槽
  Future<List<SuggestedTime>> suggestTimeSlots({
    required int estimatedMinutes,
    required int energyCost,
    required int difficulty,
    DateTime? preferredDate,
  }) async {
    final preferences = await _loadPreferences();
    final cognitiveState = _ref.read(dashboardProvider).cognitive;

    // Generate available time slots for the day
    final slots = _generateAvailableSlots(
      preferences: preferences,
      date: preferredDate ?? DateTime.now(),
      excludeBlocked: true,
    );

    // Score each slot based on task requirements and preferences
    final suggestions = <SuggestedTime>[];
    for (final slot in slots) {
      // Skip slots that are too short
      if (slot.durationMinutes < estimatedMinutes) continue;

      final score = _scoreTimeSlot(
        slot: slot,
        preferences: preferences,
        energyCost: energyCost,
        difficulty: difficulty,
        cognitiveState: cognitiveState,
      );

      if (score.confidence > 0.3) {
        suggestions.add(score);
      }
    }

    // Sort by confidence (highest first)
    suggestions.sort((a, b) => b.confidence.compareTo(a.confidence));

    // Return top 3 suggestions
    return suggestions.take(3).toList();
  }

  /// Get the best time slot for a task
  /// 获取任务的最佳时间槽
  Future<SuggestedTime?> getBestTimeSlot({
    required int estimatedMinutes,
    required int energyCost,
    required int difficulty,
    DateTime? preferredDate,
  }) async {
    final suggestions = await suggestTimeSlots(
      estimatedMinutes: estimatedMinutes,
      energyCost: energyCost,
      difficulty: difficulty,
      preferredDate: preferredDate,
    );
    return suggestions.isNotEmpty ? suggestions.first : null;
  }

  /// Generate available time slots for a day
  /// 生成一天中的可用时间槽
  List<TimeSlot> _generateAvailableSlots({
    required SchedulePreferences preferences,
    required DateTime date,
    bool excludeBlocked = true,
  }) {
    final slots = <TimeSlot>[];

    // Define base time periods
    // Morning: 6:00 - 12:00
    // Afternoon: 12:00 - 18:00
    // Evening: 18:00 - 23:00

    // Generate slots based on focus period preference
    switch (preferences.focusPeriod) {
      case FocusPeriod.morning:
        slots.addAll(_generateSlotsForPeriod(6, 0, 12, 0, TimeSlotQuality.peak));
        slots.addAll(_generateSlotsForPeriod(12, 0, 18, 0, TimeSlotQuality.normal));
        slots.addAll(_generateSlotsForPeriod(18, 0, 23, 0, TimeSlotQuality.low));
      case FocusPeriod.afternoon:
        slots.addAll(_generateSlotsForPeriod(6, 0, 12, 0, TimeSlotQuality.normal));
        slots.addAll(_generateSlotsForPeriod(12, 0, 18, 0, TimeSlotQuality.peak));
        slots.addAll(_generateSlotsForPeriod(18, 0, 23, 0, TimeSlotQuality.low));
      case FocusPeriod.evening:
        slots.addAll(_generateSlotsForPeriod(6, 0, 12, 0, TimeSlotQuality.low));
        slots.addAll(_generateSlotsForPeriod(12, 0, 18, 0, TimeSlotQuality.normal));
        slots.addAll(_generateSlotsForPeriod(18, 0, 23, 0, TimeSlotQuality.peak));
    }

    // Mark blocked periods
    if (preferences.hasCommuteSettings && excludeBlocked) {
      slots = _markBlockedPeriods(slots, preferences.commuteStart!, preferences.commuteEnd!);
    }

    if (preferences.hasLunchSettings && excludeBlocked) {
      slots = _markBlockedPeriods(slots, preferences.lunchStart!, preferences.lunchEnd!);
    }

    return slots;
  }

  /// Generate time slots for a period
  /// 为特定时段生成时间槽
  List<TimeSlot> _generateSlotsForPeriod(
    int startHour,
    int startMinute,
    int endHour,
    int endMinute,
    TimeSlotQuality quality,
  ) {
    final slots = <TimeSlot>[];
    const slotDuration = 60; // 1-hour slots

    var currentHour = startHour;
    var currentMinute = startMinute;

    while (currentHour < endHour || (currentHour == endHour && currentMinute < endMinute)) {
      final nextHour = currentHour + (currentMinute + slotDuration) ~/ 60;
      final nextMinute = (currentMinute + slotDuration) % 60;

      if (nextHour > endHour || (nextHour == endHour && nextMinute > endMinute)) {
        break;
      }

      slots.add(TimeSlot(
        startHour: currentHour,
        startMinute: currentMinute,
        endHour: nextHour,
        endMinute: nextMinute,
        quality: quality,
      ));

      currentHour = nextHour;
      currentMinute = nextMinute;
    }

    return slots;
  }

  /// Mark blocked periods in time slots
  /// 在时间槽中标记阻塞时段
  List<TimeSlot> _markBlockedPeriods(
    List<TimeSlot> slots,
    String blockStart,
    String blockEnd,
  ) {
    final blockedStart = _parseTime(blockStart);
    final blockedEnd = _parseTime(blockEnd);

    return slots.map((slot) {
      final slotStart = slot.startHour * 60 + slot.startMinute;
      final slotEnd = slot.endHour * 60 + slot.endMinute;

      // Check if slot overlaps with blocked period
      if (slotStart < blockedEnd && slotEnd > blockedStart) {
        return slot.copyWith(quality: TimeSlotQuality.blocked);
      }
      return slot;
    }).toList();
  }

  /// Score a time slot based on task requirements
  /// 根据任务需求对时间槽评分
  SuggestedTime _scoreTimeSlot({
    required TimeSlot slot,
    required SchedulePreferences preferences,
    required int energyCost,
    required int difficulty,
    required CognitiveData cognitiveState,
  }) {
    var confidence = 0.5;
    final reasons = <String>[];

    // Skip blocked slots
    if (slot.quality == TimeSlotQuality.blocked) {
      return SuggestedTime(
        timeSlot: slot,
        reason: '该时段不可用',
        confidence: 0.0,
      );
    }

    // High energy cost tasks benefit from peak hours
    if (energyCost >= 3) {
      if (slot.quality == TimeSlotQuality.peak) {
        confidence += 0.25;
        reasons.add('高能量任务适合高效能时段');
      } else if (slot.quality == TimeSlotQuality.low) {
        confidence -= 0.2;
      }
    }

    // High difficulty tasks benefit from peak hours
    if (difficulty >= 3) {
      if (slot.quality == TimeSlotQuality.peak) {
        confidence += 0.2;
        reasons.add('高难度任务适合高效能时段');
      }
    }

    // Low energy tasks can be scheduled in low periods
    if (energyCost <= 1 && slot.quality == TimeSlotQuality.low) {
      confidence += 0.1;
      reasons.add('轻量任务适合低能量时段');
    }

    // Consider cognitive state
    if (cognitiveState.status != 'empty') {
      // If user has cognitive insights, slightly boost confidence
      confidence += 0.05;
    }

    // Match focus period preference
    if (slot.quality == TimeSlotQuality.peak) {
      reasons.add('符合您的专注时段偏好');
    }

    // Clamp confidence to 0.0 - 1.0
    confidence = confidence.clamp(0.0, 1.0);

    return SuggestedTime(
      timeSlot: slot,
      reason: reasons.isNotEmpty ? reasons.first : '推荐时段',
      confidence: confidence,
    );
  }

  /// Parse time string (HH:mm) to minutes since midnight
  /// 解析时间字符串（HH:mm）为午夜以来的分钟数
  int _parseTime(String time) {
    final parts = time.split(':');
    if (parts.length != 2) return 0;
    final hours = int.tryParse(parts[0]) ?? 0;
    final minutes = int.tryParse(parts[1]) ?? 0;
    return hours * 60 + minutes;
  }

  /// Load user preferences
  /// 加载用户偏好
  Future<SchedulePreferences> _loadPreferences() async {
    try {
      final user = _ref.read(currentUserProvider);
      if (user?.schedulePreferences != null) {
        return SchedulePreferences.fromJson(user!.schedulePreferences);
      }
    } catch (e) {
      // Return default preferences on error
    }
    return const SchedulePreferences();
  }
}

/// Provider for SmartScheduleService
/// 智能排程服务 Provider
final smartScheduleServiceProvider = Provider<SmartScheduleService>((ref) {
  return SmartScheduleService(ref);
});

/// Provider for suggested time slots for a task
/// 任务建议时间槽的 Provider
final suggestedTimeSlotsProvider =
    FutureProvider.family<List<SuggestedTime>, TaskScheduleParams>(
  (ref, params) async {
    final service = ref.watch(smartScheduleServiceProvider);
    return service.suggestTimeSlots(
      estimatedMinutes: params.estimatedMinutes,
      energyCost: params.energyCost,
      difficulty: params.difficulty,
      preferredDate: params.preferredDate,
    );
  },
);

/// Parameters for scheduling a task
/// 任务排程参数
class TaskScheduleParams {
  const TaskScheduleParams({
    required this.estimatedMinutes,
    this.energyCost = 2,
    this.difficulty = 2,
    this.preferredDate,
  });

  final int estimatedMinutes;
  final int energyCost;
  final int difficulty;
  final DateTime? preferredDate;
}
