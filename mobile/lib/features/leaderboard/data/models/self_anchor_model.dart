/// D-COMM-1：自我 7 日锚视图（`GET /leaderboards/self-anchor`）响应模型。
///
/// 后端契约（app/schemas/leaderboard.py · SelfAnchorViewResponse）：
/// 窗口固定 7 天（UTC 日界，含今天），无数据日如实补零，不内插不估算；
/// `hasAnyData == false` 表示窗口内完全无任何记录（诚实空态，全零必为真零）。
/// 手写 fromJson（一次性只读视图契约，非资源模型，对齐 PlanConfirmResult
/// 的手写解析风格，不进 build_runner）。
class SelfAnchorDayPoint {
  const SelfAnchorDayPoint({
    required this.date,
    required this.tasksCompleted,
    required this.masteryDelta,
  });

  factory SelfAnchorDayPoint.fromJson(Map<String, dynamic> json) {
    final dateRaw = json['date'];
    return SelfAnchorDayPoint(
      date: dateRaw is String
          ? (DateTime.tryParse(dateRaw)?.toUtc() ?? _utcToday())
          : _utcToday(),
      tasksCompleted: (json['tasks_completed'] as num?)?.toInt() ?? 0,
      masteryDelta: (json['mastery_delta'] as num?)?.toDouble() ?? 0.0,
    );
  }

  final DateTime date;
  final int tasksCompleted;
  final double masteryDelta;
}

DateTime _utcToday() {
  final now = DateTime.now().toUtc();
  return DateTime.utc(now.year, now.month, now.day);
}

class SelfAnchorView {
  const SelfAnchorView({
    required this.windowStart,
    required this.windowEnd,
    required this.series,
    required this.totalTasksCompleted,
    required this.totalMasteryDelta,
    required this.hasAnyData,
  });

  factory SelfAnchorView.fromJson(Map<String, dynamic> json) {
    final series = (json['series'] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(SelfAnchorDayPoint.fromJson)
        .toList();
    final windowEnd = _parseDate(json['window_end']) ?? _utcToday();
    return SelfAnchorView(
      windowStart:
          _parseDate(json['window_start']) ?? windowEnd, // 防御：缺失时退化为单日窗
      windowEnd: windowEnd,
      series: series,
      totalTasksCompleted: (json['total_tasks_completed'] as num?)?.toInt() ?? 0,
      totalMasteryDelta:
          (json['total_mastery_delta'] as num?)?.toDouble() ?? 0.0,
      hasAnyData: json['has_any_data'] == true,
    );
  }

  static DateTime? _parseDate(Object? raw) =>
      raw is String ? DateTime.tryParse(raw)?.toUtc() : null;

  /// 窗口起始日（含）。
  final DateTime windowStart;

  /// 窗口结束日（含，今天）。
  final DateTime windowEnd;

  /// 每日序列，旧→新，无数据日如实补零。
  final List<SelfAnchorDayPoint> series;

  /// 窗口内完成任务总数。
  final int totalTasksCompleted;

  /// 窗口内掌握度增量总和。
  final double totalMasteryDelta;

  /// 窗口内是否完全无记录（诚实空态，False=真零）。
  final bool hasAnyData;
}
