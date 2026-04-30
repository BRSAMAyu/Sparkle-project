import 'package:sparkle/core/services/i18n_service.dart';

class WeeklyGrowthNarrative {
  const WeeklyGrowthNarrative({
    required this.period,
    required this.weekStart,
    required this.weekEnd,
    required this.body,
    required this.sentences,
    required this.highlights,
    required this.biggestImprovement,
    required this.nextWeekSuggestion,
    required this.dataPoints,
    required this.sourceCounts,
    required this.isPlaceholder,
    required this.generatedAt,
  });

  factory WeeklyGrowthNarrative.fromJson(Map<String, dynamic> json) =>
      WeeklyGrowthNarrative(
        period: json['period']?.toString() ?? (I18nService.instance.isChinese ? '本周成长故事' : 'This Week\'s Growth Story'),
        weekStart: json['week_start']?.toString() ?? '',
        weekEnd: json['week_end']?.toString() ?? '',
        body: json['body']?.toString() ?? (I18nService.instance.isChinese ? '这是你的第一周，先开始吧。' : 'Your first week — let\'s get started.'),
        sentences: _stringList(json['sentences']),
        highlights: _stringList(json['highlights']),
        biggestImprovement: _stringMap(json['biggest_improvement']),
        nextWeekSuggestion: json['next_week_suggestion']?.toString() ?? '',
        dataPoints: Map<String, dynamic>.from(
          json['data_points'] as Map? ?? const <String, dynamic>{},
        ),
        sourceCounts: _intMap(json['source_counts']),
        isPlaceholder: json['is_placeholder'] == true,
        generatedAt: json['generated_at']?.toString() ?? '',
      );

  factory WeeklyGrowthNarrative.placeholder() {
    final zh = I18nService.instance.isChinese;
    return WeeklyGrowthNarrative(
      period: zh ? '本周成长故事' : 'This Week\'s Growth Story',
      weekStart: '',
      weekEnd: '',
      body: zh
          ? '这是你的第一周，先开始吧。完成一次学习任务、记录一道错题，或者写下一句复盘后，这里就会开始把你的成长线索连起来。'
          : 'Your first week — let\'s get started. After you complete a learning task, log an error, or write a reflection, your growth threads will start connecting here.',
      sentences: <String>[
        zh ? '这是你的第一周，先开始吧。' : 'Your first week — let\'s get started.',
        zh
            ? '完成一次学习任务、记录一道错题，或者写下一句复盘后，这里就会开始把你的成长线索连起来。'
            : 'After a learning task, error log, or reflection, growth threads will connect here.',
      ],
      highlights: <String>[zh ? '开始留下第一条成长线索。' : 'Start leaving your first growth thread.'],
      biggestImprovement: <String, dynamic>{},
      nextWeekSuggestion: zh
          ? '先完成一个最小的学习动作，比如学 15 分钟或记录一道错题。'
          : 'Start with a small action — study 15 minutes or log one error.',
      dataPoints: <String, dynamic>{},
      sourceCounts: <String, int>{},
      isPlaceholder: true,
      generatedAt: '',
    );
  }

  final String period;
  final String weekStart;
  final String weekEnd;
  final String body;
  final List<String> sentences;
  final List<String> highlights;
  final Map<String, dynamic> biggestImprovement;
  final String nextWeekSuggestion;
  final Map<String, dynamic> dataPoints;
  final Map<String, int> sourceCounts;
  final bool isPlaceholder;
  final String generatedAt;

  bool get hasData => !isPlaceholder;

  int get studyDays => _intValue(dataPoints['study_days']);
  int get tasksCompleted => _intValue(dataPoints['tasks_completed']);
  int get errorsFixed =>
      _intValue(dataPoints['errors_fixed'] ?? dataPoints['error_records']);
  int get reflectionRecords => _intValue(dataPoints['reflection_records']);
  double get masteryDelta => _doubleValue(dataPoints['mastery_delta']);
  String get biggestImprovementNode =>
      biggestImprovement['node_name']?.toString() ?? '';
  double get biggestImprovementBefore =>
      _doubleValue(biggestImprovement['before_mastery']);
  double get biggestImprovementAfter =>
      _doubleValue(biggestImprovement['after_mastery']);
  bool get hasBiggestImprovement => biggestImprovementNode.isNotEmpty;

  String get dateRangeLabel {
    if (weekStart.isEmpty || weekEnd.isEmpty) {
      return I18nService.instance.isChinese ? '这一周' : 'This Week';
    }
    return I18nService.instance.isChinese ? '$weekStart 至 $weekEnd' : '$weekStart – $weekEnd';
  }

  static List<String> _stringList(dynamic value) {
    if (value is! List) {
      return const <String>[];
    }
    return value
        .map((item) => item?.toString().trim() ?? '')
        .where((item) => item.isNotEmpty)
        .toList(growable: false);
  }

  static Map<String, dynamic> _stringMap(dynamic value) {
    if (value is! Map) {
      return const <String, dynamic>{};
    }
    return value.map(
      (key, item) => MapEntry(key.toString(), item),
    );
  }

  static Map<String, int> _intMap(dynamic value) {
    if (value is! Map) {
      return const <String, int>{};
    }
    return value.map(
      (key, item) => MapEntry(key.toString(), _intValue(item)),
    );
  }

  static int _intValue(dynamic value) {
    if (value is int) {
      return value;
    }
    if (value is num) {
      return value.toInt();
    }
    return int.tryParse(value?.toString() ?? '') ?? 0;
  }

  static double _doubleValue(dynamic value) {
    if (value is num) {
      return value.toDouble();
    }
    return double.tryParse(value?.toString() ?? '') ?? 0;
  }
}
