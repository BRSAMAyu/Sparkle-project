/// D-07 证据洞察卡数据模型。
///
/// 与后端 `GET /insights/evidence-cards`（insights.evidence_cards.v1）对齐：
/// 每张卡 fact → interpretation → uncertainty → evidence → implication 五要素。
/// 后端只出结构化字段与定性档位（无置信百分比/无定义分数），用户可见文案
/// 全部在本侧 l10n 组合。
///
/// V4-U13（消费 D05 `insight.presentation.v1` 契约出口）：原始数值与推断
/// 拆开——[uncertainty] 全部是真实计数（样本/未观察/无法判定/撤回排除），
/// [understanding] 是后端理解宣称门的档位（无数据/证据不足显式），
/// [nextStep] 信封钉「可拒绝且零惩罚」；呈现语义不在本侧另立第二权威。
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
    this.understanding = const EvidenceUnderstandingBlock.empty(),
    this.nextStep,
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
        understanding: EvidenceUnderstandingBlock.fromJson(
          _mapOf(json['understanding']),
        ),
        nextStep: json['next_step'] is Map
            ? SuggestionEnvelope.fromJson(
                Map<String, dynamic>.from(json['next_step'] as Map),
              )
            : null,
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

  /// 不会有可判定结果的暴露数（窗口已关/用户流失/无法判定；V3-FIX-357-A
  /// 拆分口径——不得与「还在观察窗口内，结果未到期」混同渲染）。
  int get notDeterminable => _intOf(uncertainty['not_determinable']);
  int get samples => _intOf(uncertainty['samples']);

  // ---- V4-U13 呈现契约字段（真实计数/封闭档位；缺失=不可得，不编造）------
  /// 已删除/撤回并被排除的来源记录数（真实计数；0 = 无撤回）。
  int get withdrawnRefsExcluded => _intOf(uncertainty['withdrawn_refs_excluded']);

  /// 重放投递如实计 raw（去重前）；与 [samples]（去重后）成对呈现。
  int get outcomeSamplesRaw => _intOf(uncertainty['outcome_samples_raw']);

  /// 重放投递去重丢弃数（D02-R1 C-3 审计可见）。
  int get duplicateOutcomeSamplesDropped =>
      _intOf(uncertainty['duplicate_outcome_samples_dropped']);

  /// 理解宣称门档位（D05 契约出口；缺失=旧契约降级为 unknown）。
  final EvidenceUnderstandingBlock understanding;

  /// 单主建议信封（D05 契约出口；缺失=不渲染零惩罚宣称）。
  final SuggestionEnvelope? nextStep;

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

/// 理解宣称门档位（后端 `understanding_claim_gate` 出口，封闭词表）。
///
/// - [bandAllowed]：只有定性结论资格（qualitative_only）；
/// - [bandIncomplete]：有 missing/censored，证据不足，不下充分结论；
/// - [bandNoData]：无数据，不出任何结论。
///
/// 词表外值降级为 [bandUnknown]（fail-closed：不渲染、不臆测档位）。
enum EvidenceUnderstandingBand {
  allowed('qualitative_only'),
  incomplete('incomplete_evidence'),
  noData('no_data'),
  unknown('');

  const EvidenceUnderstandingBand(this.wire);

  final String wire;

  static EvidenceUnderstandingBand fromWire(Object? value) {
    final normalized = '$value'.trim();
    for (final band in EvidenceUnderstandingBand.values) {
      if (band.wire == normalized && band != unknown) {
        return band;
      }
    }
    return unknown;
  }
}

class EvidenceUnderstandingBlock {
  const EvidenceUnderstandingBlock({
    required this.claimAllowed,
    required this.band,
    required this.samples,
    required this.missing,
    required this.censored,
  });

  const EvidenceUnderstandingBlock.empty()
      : this(
          claimAllowed: false,
          band: EvidenceUnderstandingBand.unknown,
          samples: 0,
          missing: 0,
          censored: 0,
        );

  factory EvidenceUnderstandingBlock.fromJson(Map<String, dynamic> json) =>
      EvidenceUnderstandingBlock(
        claimAllowed: json['claim_allowed'] == true,
        band: EvidenceUnderstandingBand.fromWire(json['band']),
        samples: EvidenceInsightCardData._intOf(json['samples']),
        missing: EvidenceInsightCardData._intOf(json['missing']),
        censored: EvidenceInsightCardData._intOf(json['censored']),
      );

  /// 「充分理解」资格（D05：无数据/有 missing+censored 恒 false）。
  final bool claimAllowed;
  final EvidenceUnderstandingBand band;
  final int samples;
  final int missing;
  final int censored;
}

/// 单主建议信封（D05 `build_suggestion_envelope` 出口）。
///
/// 零惩罚宣称只在后端冻结常量成立时渲染（`user_can_reject=true` 且
/// `reject_penalty="none"`）；契约漂移一律降级为不渲染，绝不替后端撒谎。
class SuggestionEnvelope {
  const SuggestionEnvelope({
    required this.observationId,
    required this.userCanReject,
    required this.rejectPenalty,
  });

  factory SuggestionEnvelope.fromJson(Map<String, dynamic> json) =>
      SuggestionEnvelope(
        observationId: json['observation_id']?.toString() ?? '',
        userCanReject: json['user_can_reject'] == true,
        rejectPenalty: json['reject_penalty']?.toString() ?? '',
      );

  final String observationId;
  final bool userCanReject;
  final String rejectPenalty;

  /// 结构冻结常量核验：只有真实零惩罚才允许渲染「可忽略且无影响」文案。
  bool get zeroPenaltyRejectable => userCanReject && rejectPenalty == 'none';
}

/// 回访相关性（D05 七态封闭词表；词表外值 = unknown，不渲染）。
enum EvidenceRevisitRelevance {
  noPrior('no_prior_suggestion'),
  rejectedByUser('rejected_by_user'),
  relatedOutcome('related_outcome_observed'),
  actedAwaiting('acted_awaiting_outcome'),
  awaitingUser('awaiting_user'),
  censoredWindowClosed('censored_window_closed'),
  censoredUserChurned('censored_user_churned'),
  unknown('');

  const EvidenceRevisitRelevance(this.wire);

  final String wire;

  static EvidenceRevisitRelevance fromWire(Object? value) {
    final normalized = '$value'.trim();
    for (final state in EvidenceRevisitRelevance.values) {
      if (state.wire == normalized && state != unknown) {
        return state;
      }
    }
    return unknown;
  }
}

class EvidenceRevisitRecord {
  const EvidenceRevisitRecord({
    required this.relevance,
    required this.provesRelevance,
    required this.nOutcomeSamplesUnique,
    required this.rewardConsequence,
  });

  factory EvidenceRevisitRecord.fromJson(Map<String, dynamic> json) =>
      EvidenceRevisitRecord(
        relevance: EvidenceRevisitRelevance.fromWire(json['relevance']),
        provesRelevance: json['proves_relevance'] == true,
        nOutcomeSamplesUnique: EvidenceInsightCardData._intOf(json['n_outcome_samples_unique']),
        rewardConsequence: json['reward_consequence']?.toString() ?? '',
      );

  final EvidenceRevisitRelevance relevance;
  final bool provesRelevance;
  final int nOutcomeSamplesUnique;
  final String rewardConsequence;
}

/// D-07 洞察 feed（payload 根级）：卡列表 + 呈现契约版本门 + meta。
///
/// 版本门 fail-closed：`presentation_schema` 缺失或非
/// `insight.presentation.v1` → [statusUnsupported]（不渲染、不臆测、不降级
/// 伪造契约字段）。schema 合法但零卡 → [statusNoData]（无数据显式呈现，
/// 不静默隐藏——SCREEN_FAMILIES「没有数据就说明尚未形成结论」）。
class EvidenceInsightFeedData {
  const EvidenceInsightFeedData({
    required this.status,
    required this.cards,
    this.emptyNote,
    this.gateDroppedCount = 0,
    this.revisit,
  });

  factory EvidenceInsightFeedData.fromJson(
    Map<String, dynamic> payload, {
    Map<String, dynamic>? meta,
  }) {
    final schema = payload['presentation_schema']?.toString() ?? '';
    if (schema != 'insight.presentation.v1') {
      return const EvidenceInsightFeedData(
        status: _statusUnsupported,
        cards: [],
      );
    }
    final windowDays = payload['window_days'] is num
        ? (payload['window_days'] as num).toInt()
        : 30;
    final cards = ((payload['cards'] as List?) ?? const <dynamic>[])
        .whereType<Map<dynamic, dynamic>>()
        .map((item) {
      final json = Map<String, dynamic>.from(item);
      json['window_days'] = windowDays;
      return EvidenceInsightCardData.fromJson(json);
    }).toList(growable: false);
    final metaMap = meta ?? const <String, dynamic>{};
    final gateDropped = (metaMap['presentation_gate_dropped'] as List?) ?? const <dynamic>[];
    final revisitRaw = payload['revisit'];
    return EvidenceInsightFeedData(
      status: cards.isEmpty ? _statusNoData : _statusReady,
      cards: cards,
      emptyNote: metaMap['note']?.toString(),
      gateDroppedCount: gateDropped.length,
      revisit: revisitRaw is Map
          ? EvidenceRevisitRecord.fromJson(
              Map<String, dynamic>.from(revisitRaw),
            )
          : null,
    );
  }

  static const String _statusReady = 'ready';
  static const String _statusNoData = 'no_data';
  static const String _statusUnsupported = 'unsupported';

  /// ready | no_data | unsupported（互斥；error/offline 在 provider 层）。
  final String status;
  final List<EvidenceInsightCardData> cards;

  /// 后端诚实空态 note（原样保留语义 ID，不进用户面文案拼接）。
  final String? emptyNote;

  /// 被夸大表述门扣下的卡数（响亮失败登记；绝不作为卡渲染）。
  final int gateDroppedCount;
  final EvidenceRevisitRecord? revisit;

  bool get isReady => status == _statusReady;
  bool get isNoData => status == _statusNoData;
  bool get isUnsupported => status == _statusUnsupported;
}
