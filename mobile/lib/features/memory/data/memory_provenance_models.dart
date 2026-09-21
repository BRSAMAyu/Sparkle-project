/// U-03「Sparkle 对我的理解」数据模型。
///
/// 形状与 M-08 后端契约一一对应（backend/app/api/v1/memory_provenance.py →
/// MemoryProvenanceService 的 user-language projection），不重定义语义：
/// bucket/bucket_label/confidence_tier_label/source_label/actions 全部由
/// 服务端给出，客户端只做展示与操作分发。
library;

DateTime? _parseDate(dynamic value) {
  if (value == null) {
    return null;
  }
  if (value is DateTime) {
    return value;
  }
  return DateTime.tryParse(value.toString());
}

Map<String, dynamic> _asMap(dynamic value) =>
    value is Map<String, dynamic> ? value : const <String, dynamic>{};

/// U-03 四组（MEMORY_AURORA_UI.md）：你告诉我的 / 我从你的行动中观察到的 /
/// 我还不确定的 / 对你有效过的方法。与服务端 PROVENANCE_BUCKETS 冻结词表一致。
enum UnderstandingBucket { told, observed, uncertain, effective }

UnderstandingBucket? understandingBucketFromName(String? name) =>
    switch (name) {
      'told' => UnderstandingBucket.told,
      'observed' => UnderstandingBucket.observed,
      'uncertain' => UnderstandingBucket.uncertain,
      'effective' => UnderstandingBucket.effective,
      _ => null,
    };

/// 服务端 bucket_label 缺失时的客户端兜底（与后端 BUCKET_LABELS 同文案）。
const Map<UnderstandingBucket, String> kBucketFallbackLabels = {
  UnderstandingBucket.told: '你告诉我的',
  UnderstandingBucket.observed: '我从你的行动中观察到的',
  UnderstandingBucket.uncertain: '我还不确定的',
  UnderstandingBucket.effective: '对你有效过的方法',
};

/// 服务端 scope.level → 用户语言（derive_scope 契约：global/goal/domain/session）。
String understandingScopeLabel(Map<String, dynamic> scope) =>
    switch (scope['level']) {
      'goal' => '仅在此目标中',
      'domain' => '相关话题中',
      'session' => '当前会话中',
      _ => '所有场景可用',
    };

/// GET /memory/provenance/items 的单条条目（_item_payload 形状）。
class ProvenanceMemoryItem {
  const ProvenanceMemoryItem({
    required this.kind,
    required this.id,
    required this.ref,
    required this.bucket,
    required this.bucketLabel,
    required this.content,
    required this.status,
    required this.scope,
    required this.correctionCount,
    required this.evidenceMissing,
    required this.confidenceTier,
    required this.confidenceTierLabel,
    required this.sourceLabel,
    required this.sourceKnown,
    required this.actions,
    this.updatedAt,
    this.createdAt,
    this.occurredAt,
    this.prefKey,
    this.version,
    this.title,
  });

  factory ProvenanceMemoryItem.fromJson(Map<String, dynamic> json) {
    final scopeRaw = _asMap(json['scope']);
    return ProvenanceMemoryItem(
      kind: json['kind'] as String? ?? 'episodic',
      id: json['id'] as String? ?? '',
      ref: json['ref'] as String? ?? '',
      bucket: understandingBucketFromName(json['bucket'] as String?) ??
          UnderstandingBucket.uncertain,
      bucketLabel: json['bucket_label'] as String? ?? '',
      content: json['content'] as String? ?? '',
      status: json['status'] as String? ?? 'active',
      scope: scopeRaw,
      correctionCount: (json['correction_count'] as num?)?.toInt() ?? 0,
      evidenceMissing: json['evidence_missing'] as bool? ?? false,
      confidenceTier: json['confidence_tier'] as String? ?? 'tentative',
      confidenceTierLabel: json['confidence_tier_label'] as String? ?? '',
      sourceLabel: json['source_label'] as String? ?? '',
      sourceKnown: json['source_known'] as bool? ?? false,
      actions: (json['actions'] as List<dynamic>? ?? const [])
          .whereType<String>()
          .toList(),
      updatedAt: _parseDate(json['updated_at']),
      createdAt: _parseDate(json['created_at']),
      occurredAt: _parseDate(json['occurred_at']),
      prefKey: json['pref_key'] as String?,
      version: (json['version'] as num?)?.toInt(),
      title: json['title'] as String?,
    );
  }

  final String kind;
  final String id;
  final String ref;
  final UnderstandingBucket bucket;
  final String bucketLabel;
  final String content;
  final String status;
  final Map<String, dynamic> scope;
  final int correctionCount;
  final bool evidenceMissing;
  final String confidenceTier;
  final String confidenceTierLabel;
  final String sourceLabel;
  final bool sourceKnown;
  final List<String> actions;
  final DateTime? updatedAt;
  final DateTime? createdAt;
  final DateTime? occurredAt;
  final String? prefKey;
  final int? version;
  final String? title;

  bool get isActive => status == 'active';

  bool get isPaused => status == 'archived';

  bool get isDeleted =>
      status == 'revoked' || status == 'retracted' || status == 'superseded';

  bool can(String action) => actions.contains(action);

  /// 卡片主文案：goal 用 title，其余用 content。
  String get displayContent =>
      content.isNotEmpty ? content : (title ?? prefKey ?? '');
}

/// GET /memory/provenance/items 的列表载荷（含诚实 scan_capped 标记）。
class ProvenanceListResult {
  const ProvenanceListResult({
    required this.items,
    required this.total,
    required this.hasMore,
    required this.scanCapped,
  });

  factory ProvenanceListResult.fromJson(Map<String, dynamic> json) {
    final items = (json['items'] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(ProvenanceMemoryItem.fromJson)
        .toList();
    return ProvenanceListResult(
      items: items,
      total: (json['total'] as num?)?.toInt() ?? items.length,
      hasMore: json['has_more'] as bool? ?? false,
      scanCapped: json['scan_capped'] as bool? ?? false,
    );
  }

  final List<ProvenanceMemoryItem> items;
  final int total;
  final bool hasMore;
  final bool scanCapped;

  bool get isEmpty => items.isEmpty;
}

/// GET /memory/provenance/items/{kind}/{id}/source（Work 2 user-language
/// provenance metadata；honest-unknown 契约由 source_known 承载）。
class ProvenanceSourceInfo {
  const ProvenanceSourceInfo({
    required this.sourceKnown,
    required this.sourceLabel,
    required this.evidenceCount,
    required this.evidenceMissing,
    required this.correctionCount,
    required this.confidenceTierLabel,
    required this.governanceHistory,
    this.writtenAt,
    this.occurredAt,
    this.updatedAt,
    this.lastUsedAt,
    this.sourceLaneHint,
  });

  factory ProvenanceSourceInfo.fromJson(Map<String, dynamic> json) =>
      ProvenanceSourceInfo(
        sourceKnown: json['source_known'] as bool? ?? false,
        sourceLabel: json['source_label'] as String? ?? '',
        evidenceCount: (json['evidence_count'] as num?)?.toInt() ?? 0,
        evidenceMissing: json['evidence_missing'] as bool? ?? false,
        correctionCount: (json['correction_count'] as num?)?.toInt() ?? 0,
        confidenceTierLabel: json['confidence_tier_label'] as String? ?? '',
        governanceHistory:
            (json['governance_history'] as List<dynamic>? ?? const [])
                .whereType<Map<String, dynamic>>()
                .map(
                  (row) => GovernanceEvent(
                    action: row['action'] as String? ?? '',
                    at: _parseDate(row['at']),
                    hasReason: row['has_reason'] as bool? ?? false,
                  ),
                )
                .toList(),
        writtenAt: _parseDate(json['written_at']),
        occurredAt: _parseDate(json['occurred_at']),
        updatedAt: _parseDate(json['updated_at']),
        lastUsedAt: _parseDate(json['last_used_at']),
        sourceLaneHint: json['source_lane_hint'] as String?,
      );

  final bool sourceKnown;
  final String sourceLabel;
  final int evidenceCount;
  final bool evidenceMissing;
  final int correctionCount;
  final String confidenceTierLabel;
  final List<GovernanceEvent> governanceHistory;
  final DateTime? writtenAt;
  final DateTime? occurredAt;
  final DateTime? updatedAt;
  final DateTime? lastUsedAt;
  final String? sourceLaneHint;
}

/// 来源历史里的一次治理事件（action 是冻结词表成员，客户端不翻译语义，
/// 只按 has_reason 展示"带说明"）。
class GovernanceEvent {
  const GovernanceEvent({
    required this.action,
    required this.at,
    required this.hasReason,
  });

  final String action;
  final DateTime? at;
  final bool hasReason;
}

/// POST /memory/provenance/why-this 的响应（Work 3 契约）。
class WhyThisResult {
  const WhyThisResult({
    required this.kind,
    required this.id,
    required this.ref,
    required this.content,
    required this.statusNow,
    required this.stillInUse,
    required this.paused,
    required this.whyIncluded,
    required this.internalOnly,
    required this.recentUses,
    required this.source,
    required this.correctionUpdatePath,
    required this.correctionRevokePath,
    required this.correctionScopePath,
    this.replacedByRef,
    this.usedAt,
    this.runPackId,
    this.runIntent,
    this.runCreatedAt,
    this.receiptVersion,
    this.receiptVersionKnown = true,
  });

  factory WhyThisResult.fromJson(Map<String, dynamic> json) {
    final memory = _asMap(json['memory']);
    final run = _asMap(json['run']);
    final usage = _asMap(json['usage_decision']);
    final correction = _asMap(json['correction']);
    final source = _asMap(json['source']);
    return WhyThisResult(
      kind: memory['kind'] as String? ?? '',
      id: memory['id'] as String? ?? '',
      ref: memory['ref'] as String? ?? '',
      content: memory['content'] as String? ?? '',
      statusNow: memory['status_now'] as String? ?? '',
      stillInUse: memory['still_in_use'] as bool? ?? false,
      paused: memory['paused'] as bool? ?? false,
      replacedByRef: memory['replaced_by_ref'] as String?,
      usedAt: _parseDate(json['used_at']),
      runPackId: run['pack_id'] as String?,
      runIntent: run['intent'] as String?,
      runCreatedAt: _parseDate(run['created_at']),
      whyIncluded: (json['why_included'] as List<dynamic>? ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(WhyReason.fromJson)
          .toList(),
      internalOnly: (usage['internal_only'] as List<dynamic>? ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(
            (entry) => WhyReason(
              reason: entry['reason'] as String? ?? '',
              known: entry['reason_known'] as bool? ?? false,
              label: entry['reason_label'] as String?,
              section: entry['section'] as String?,
              id: entry['id'] as String?,
            ),
          )
          .toList(),
      receiptVersion: usage['receipt_version'] as String?,
      receiptVersionKnown: usage['receipt_version_known'] as bool? ?? true,
      recentUses: (json['recent_uses'] as List<dynamic>? ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(
            (row) => RecentUse(
              action: row['action'] as String? ?? '',
              at: _parseDate(row['at']),
            ),
          )
          .toList(),
      source: ProvenanceSourceInfo.fromJson(source),
      correctionUpdatePath: correction['update'] as String? ?? '',
      correctionRevokePath: correction['revoke'] as String? ?? '',
      correctionScopePath: correction['scope'] as String? ?? '',
    );
  }

  final String kind;
  final String id;
  final String ref;
  final String content;
  final String statusNow;
  final bool stillInUse;
  final bool paused;
  final String? replacedByRef;
  final DateTime? usedAt;
  final String? runPackId;
  final String? runIntent;
  final DateTime? runCreatedAt;
  final List<WhyReason> whyIncluded;
  final List<WhyReason> internalOnly;
  final String? receiptVersion;
  final bool receiptVersionKnown;
  final List<RecentUse> recentUses;
  final ProvenanceSourceInfo source;
  final String correctionUpdatePath;
  final String correctionRevokePath;
  final String correctionScopePath;
}

/// 翻译后的原因（known=false = 诚实未知，绝不猜标签）。
class WhyReason {
  const WhyReason({
    required this.reason,
    required this.known,
    required this.label,
    this.section,
    this.id,
  });

  factory WhyReason.fromJson(Map<String, dynamic> json) => WhyReason(
        reason: json['reason'] as String? ?? '',
        known: json['known'] as bool? ?? false,
        label: json['label'] as String?,
        section: json['section'] as String?,
        id: json['id'] as String?,
      );

  final String reason;
  final bool known;
  final String? label;
  final String? section;
  final String? id;
}

class RecentUse {
  const RecentUse({required this.action, required this.at});

  final String action;
  final DateTime? at;
}
