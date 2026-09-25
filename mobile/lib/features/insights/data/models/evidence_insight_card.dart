/// D-07 证据洞察卡数据模型。
///
/// 与后端 `GET /insights/evidence-cards`（insights.evidence_cards.v1）对齐：
/// 每张卡 fact → interpretation → uncertainty → evidence → implication 五要素。
/// 后端只出结构化字段与定性档位（无置信百分比/无定义分数），用户可见文案
/// 全部在本侧 l10n 组合。
class EvidenceInsightCardData {
  const EvidenceInsightCardData({
    required this.id,
    required this.kind,
    required this.fact,
    required this.interpretation,
    required this.uncertainty,
    required this.evidence,
    required this.implication,
    this.windowDays = 30,
  });

  factory EvidenceInsightCardData.fromJson(Map<String, dynamic> json) =>
      EvidenceInsightCardData(
        id: json['id']?.toString() ?? '',
        kind: json['kind']?.toString() ?? '',
        windowDays: json['window_days'] is num
            ? (json['window_days'] as num).toInt()
            : 30,
        fact: _mapOf(json['fact']),
        interpretation: _mapOf(json['interpretation']),
        uncertainty: _mapOf(json['uncertainty']),
        evidence: ((json['evidence'] as List?) ?? const <dynamic>[])
            .whereType<Map<dynamic, dynamic>>()
            .map(
              (item) =>
                  EvidenceLink.fromJson(Map<String, dynamic>.from(item)),
            )
            .toList(growable: false),
        implication: _mapOf(json['implication']),
      );

  final String id;

  /// friction_pattern | interventions_that_helped | goal_progress
  final String kind;

  /// 证据回看窗口（天）；来自响应根级 window_days（缺省 30）。
  final int windowDays;

  final Map<String, dynamic> fact;
  final Map<String, dynamic> interpretation;
  final Map<String, dynamic> uncertainty;
  final List<EvidenceLink> evidence;
  final Map<String, dynamic> implication;

  static Map<String, dynamic> _mapOf(Object? raw) => raw is Map
      ? Map<String, dynamic>.from(raw)
      : const <String, dynamic>{};

  static int _intOf(Object? value) =>
      value is num ? value.toInt() : int.tryParse('$value') ?? 0;

  // ---- kind 判别（呈现层只认封闭词表，不做字符串透传渲染）----------------
  bool get isFrictionPattern => kind == 'friction_pattern';
  bool get isHelpedInterventions => kind == 'interventions_that_helped';
  bool get isGoalProgress => kind == 'goal_progress';

  // ---- fact 字段便捷读取（全部是真实计数/标题，不是分数）-----------------
  String get frictionTag => '${fact['friction_tag'] ?? ''}';
  int get exposures => _intOf(fact['exposures']);
  int get acceptedCount => _intOf(fact['accepted']);
  int get editedCount => _intOf(fact['edited']);
  int get rejectedCount => _intOf(fact['rejected']);

  int get nObserved => _intOf(fact['n_observed']);
  int get nPositive => _intOf(fact['n_positive']);

  String get goalTitle => '${fact['title'] ?? ''}';
  int get ledgerCompleted => _intOf((fact['ledger'] as Map?)?['completed']);
  int get ledgerTotal => _intOf((fact['ledger'] as Map?)?['total']);
  String get goalId => '${fact['goal_id'] ?? ''}';

  // ---- interpretation / uncertainty / implication -------------------------
  String get frictionRole => '${interpretation['role'] ?? ''}';
  String get evidenceStrength => '${interpretation['evidence_strength'] ?? ''}';
  String get goalBand => '${interpretation['band'] ?? ''}';

  List<String> get uncertaintyQualifiers =>
      ((uncertainty['qualifiers'] as List?) ?? const <dynamic>[])
          .map((item) => '$item')
          .toList(growable: false);
  int get notYetObserved => _intOf(uncertainty['not_yet_observed']);
  int get samples => _intOf(uncertainty['samples']);

  String get actionKey => '${implication['action_key'] ?? ''}';
  String? get actionDeepLink {
    final raw = implication['deep_link']?.toString() ?? '';
    return raw.isEmpty ? null : raw;
  }
}

/// 证据深链：label_key 是封闭词表（呈现层映射到本地化文案），deep_link 是
/// 应用内可达路由。
class EvidenceLink {
  const EvidenceLink({
    required this.labelKey,
    required this.deepLink,
    required this.refs,
  });

  factory EvidenceLink.fromJson(Map<String, dynamic> json) => EvidenceLink(
        labelKey: json['label_key']?.toString() ?? '',
        deepLink: json['deep_link']?.toString() ?? '',
        refs: ((json['refs'] as List?) ?? const <dynamic>[])
            .map((item) => '$item')
            .toList(growable: false),
      );

  final String labelKey;
  final String deepLink;
  final List<String> refs;
}
