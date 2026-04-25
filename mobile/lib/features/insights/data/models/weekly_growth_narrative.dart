class WeeklyGrowthNarrative {
  const WeeklyGrowthNarrative({
    required this.period,
    required this.weekStart,
    required this.weekEnd,
    required this.body,
    required this.sentences,
    required this.dataPoints,
    required this.sourceCounts,
    required this.isPlaceholder,
    required this.generatedAt,
  });

  factory WeeklyGrowthNarrative.fromJson(Map<String, dynamic> json) =>
      WeeklyGrowthNarrative(
        period: json['period']?.toString() ?? '本周成长故事',
        weekStart: json['week_start']?.toString() ?? '',
        weekEnd: json['week_end']?.toString() ?? '',
        body: json['body']?.toString() ?? '这是你的第一周，先开始吧。',
        sentences: _stringList(json['sentences']),
        dataPoints: Map<String, dynamic>.from(
          json['data_points'] as Map? ?? const <String, dynamic>{},
        ),
        sourceCounts: _intMap(json['source_counts']),
        isPlaceholder: json['is_placeholder'] == true,
        generatedAt: json['generated_at']?.toString() ?? '',
      );

  factory WeeklyGrowthNarrative.placeholder() => const WeeklyGrowthNarrative(
        period: '本周成长故事',
        weekStart: '',
        weekEnd: '',
        body: '这是你的第一周，先开始吧。完成一次学习任务、记录一道错题，或者写下一句复盘后，这里就会开始把你的成长线索连起来。',
        sentences: <String>[
          '这是你的第一周，先开始吧。',
          '完成一次学习任务、记录一道错题，或者写下一句复盘后，这里就会开始把你的成长线索连起来。',
        ],
        dataPoints: <String, dynamic>{},
        sourceCounts: <String, int>{},
        isPlaceholder: true,
        generatedAt: '',
      );

  final String period;
  final String weekStart;
  final String weekEnd;
  final String body;
  final List<String> sentences;
  final Map<String, dynamic> dataPoints;
  final Map<String, int> sourceCounts;
  final bool isPlaceholder;
  final String generatedAt;

  bool get hasData => !isPlaceholder;

  int get tasksCompleted => _intValue(dataPoints['tasks_completed']);
  int get errorRecords => _intValue(dataPoints['error_records']);
  int get reflectionRecords => _intValue(dataPoints['reflection_records']);
  double get masteryDelta => _doubleValue(dataPoints['mastery_delta']);

  String get dateRangeLabel {
    if (weekStart.isEmpty || weekEnd.isEmpty) {
      return '这一周';
    }
    return '$weekStart 至 $weekEnd';
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
