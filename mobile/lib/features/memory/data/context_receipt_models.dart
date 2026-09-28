/// V4-U03 · 「这次的理解」数据模型——I06 `context_selection_receipt.v1`
/// 读面（`GET /experience/context-receipts/latest`）的移动端消费投影。
///
/// 真源纪律（B05 合同 §7.1 / V4-I06）：本模型**只**投影服务端回执，不造第二
/// 理解真源——回执说什么就显示什么：
/// - rejected 候选只有 ref/reason_code（无内容），用户面只显示归因标签；
///   `note` 是 debug-only（合同 §2），**结构性不进入**任何用户可见字段；
/// - 来源验证 `resolution=unresolved` =「来源已不可定位」，显式 unattributed，
///   绝不把不可定位的条目渲染成已理解内容；
/// - `candidates` 缺失 = 旧生产者 → [ContextReceiptView.candidatesUnknown]
///   （合同读侧语义：不得渲染为「无依据可用」或「有依据」任一）；
/// - `schema_version` 非当前版本 → 整体降级 unsupported（诚实「暂不支持」，
///   不当数据渲染）；
/// - mode off/shadow → receipt=null（写先行读未开），modeGated 诚实态。
///
/// 词表与 backend `app/core/context_selection_receipt.py` 冻结词表逐字对齐
/// （8 归因码 / 4 生效角色 / 4 置信档 / 3 候选状态 / 2 resolution）；扩展 =
/// 后端契约变更，本表随 bump 同步。
library;

/// 当前支持的回执契约版本（冻结；与 backend CONTEXT_SELECTION_RECEIPT_SCHEMA_VERSION 逐字一致）。
const String kContextSelectionReceiptSchemaVersion = 'context_selection_receipt.v1';

/// 候选状态封闭三元集（backend CANDIDATE_STATUSES）。
const Set<String> kCandidateStatuses = <String>{'selected', 'rejected', 'unavailable'};

/// 归因码封闭八元集（backend REJECTION_REASON_CODES；冻结）。
const Set<String> kRejectionReasonCodes = <String>{
  'out_of_scope_memory',
  'stale_epoch',
  'utility_gate_rejected',
  'conflicts_confirmed_preference',
  'permission_denied',
  'budget_exhausted',
  'duplicate',
  'expired',
};

/// 生效角色封闭四元集（backend SELECTION_ROLES）。
const Set<String> kSelectionRoles = <String>{
  'chat_context',
  'proposal_basis',
  'resume_view',
  'intervention_targeting',
};

/// why-now 置信档封闭四元集（backend WHY_NOW_CONFIDENCE_BANDS）。
const Set<String> kWhyNowConfidenceBands = <String>{'high', 'medium', 'low', 'unknown'};

/// 来源验证 resolution 封闭二元集（backend SOURCE_RESOLUTIONS）。
const Set<String> kSourceResolutions = <String>{'resolved', 'unresolved'};

/// 归因码 → 用户语言（改黑话：回执说什么就显示什么，词表外不猜标签）。
const Map<String, String> kRejectionReasonLabels = <String, String>{
  'out_of_scope_memory': '不在这次的范围里',
  'stale_epoch': '已删除或已被新内容替代',
  'utility_gate_rejected': '这次判断帮助不大',
  'conflicts_confirmed_preference': '与你确认过的偏好不一致',
  'permission_denied': '你设置过不让使用',
  'budget_exhausted': '这次能带上的内容有限',
  'duplicate': '和其他内容重复',
  'expired': '已过时效',
};

/// 生效角色 → 用户语言（「这次」= 最近一次理解发生的地方）。
const Map<String, String> kSelectionRoleLabels = <String, String>{
  'chat_context': '一次对话的回答',
  'proposal_basis': '一个提案的依据',
  'resume_view': '接续进度的视图',
  'intervention_targeting': '一次关心的定向',
};

/// 置信档 → 审慎标签（对齐既有审慎词，不造精度百分比）。
const Map<String, String> kWhyNowBandLabels = <String, String>{
  'high': '把握较高',
  'medium': '把握一般',
  'low': '把握较低',
  'unknown': '还不确定',
};

/// 记忆 ref scheme（ACTION_SOURCE_REF_SCHEMES 中用户记忆域；仅此域提供校准动作）。
const String kMemoryRefScheme = 'memory';

/// 用户可校准的记忆 kind（backend `MemoryProvenanceService._parse_kind`
/// 封闭三元集；其余 memory:// path 只作来源显示，不提供操作）。
const Set<String> kUserCalibratableKinds = <String>{'episodic', 'preference', 'goal'};

/// `scheme://path` → scheme（与 backend parse_ref_scheme 同判：无 `://` 或空 scheme → null）。
String? parseRefScheme(String ref) {
  final index = ref.indexOf('://');
  if (index <= 0) {
    return null;
  }
  return ref.substring(0, index);
}

/// `memory://<kind>/<id>` → (kind, id)；scheme 非 memory 或路径不完整 → null
/// （消费纪律：校准动作只绑定真实记忆 ref，不猜其他 scheme 的操作语义）。
({String kind, String id})? parseMemoryRef(String ref) {
  if (parseRefScheme(ref) != kMemoryRefScheme) {
    return null;
  }
  final parts = ref.substring('$kMemoryRefScheme://'.length).split('/');
  if (parts.length != 2 || parts[0].isEmpty || parts[1].isEmpty) {
    return null;
  }
  return (kind: parts[0], id: parts[1]);
}

/// 读面响应的封闭解析结果（fail-safe：结构损坏降级不炸）。
///
/// [unsupported]：schema_version 非当前版本（读门 fail-closed 同语义）；
/// [candidatesUnknown]：candidates 缺失（旧生产者，合同读侧 unknown 语义）。
class ContextReceiptView {
  const ContextReceiptView._({
    required this.mode,
    required this.receiptId,
    required this.selectionRole,
    required this.candidates,
    required this.sourceVerifications,
    required this.resolvedSelectedCount,
    required this.selectedCount,
    required this.rejectedByReason,
    required this.unknownReasonCount,
    required this.candidatesUnknown,
    this.whyNowStatement,
    this.whyNowBand,
  });

  /// 读面模式（off/shadow/live；词表外原样保留供诚实显示，不猜语义）。
  final String mode;

  /// 回执 id（`csr_` 前缀；透传用于诊断与去重对照，不是用户文案）。
  final String receiptId;

  /// 这次理解生效在哪（kSelectionRoles 成员；词表外为空串=不显示）。
  final String selectionRole;

  /// 候选集（回执说什么就有什么；note 永不进入本模型任何字段）。
  final List<ReceiptCandidateView> candidates;

  /// 来源验证逐条（ref → resolution/status_code；metadata-only，无正文）。
  final List<ReceiptSourceVerification> sourceVerifications;

  /// 服务端读面如实计数：resolution=resolved 且 ∈ selected 的条数。
  final int resolvedSelectedCount;

  /// selected 候选数（服务端权威，客户端不重算语义）。
  final int selectedCount;

  /// rejected/unavailable 按归因码分组计数（词表外码不进组， honesty 由
  /// [unknownReasonCount] 承载——不静默丢弃）。
  final Map<String, int> rejectedByReason;

  /// 词表外归因码条数（显式 unknown，不拼标签）。
  final int unknownReasonCount;

  /// why-now 用户可读一句话（null = 回执未携带）。
  final String? whyNowStatement;

  /// why-now 置信档（kWhyNowConfidenceBands 成员；词表外归 unknown）。
  final String? whyNowBand;

  /// candidates 缺失（旧生产者）：显示「这次回执暂缺候选明细」，不当空集渲染。
  final bool candidatesUnknown;

  /// 解析 ref 后可校准的选中记忆（resolution=resolved 的 selected memory://）。
  ///
  /// 消费纪律（合同 §7.1）：只有 resolved 的 selected ref 可绑定操作；
  /// unresolved 一律显示「来源已不可定位」，无操作。
  List<CalibratableMemory> calibratableMemories() {
    final byRef = <String, ReceiptSourceVerification>{
      for (final entry in sourceVerifications) entry.ref: entry,
    };
    final result = <CalibratableMemory>[];
    for (final candidate in candidates) {
      if (candidate.status != 'selected') {
        continue;
      }
      final target = parseMemoryRef(candidate.ref);
      if (target == null || !kUserCalibratableKinds.contains(target.kind)) {
        continue;
      }
      final verification = byRef[candidate.ref];
      if (verification == null || verification.resolution != 'resolved') {
        continue;
      }
      result.add(CalibratableMemory(kind: target.kind, id: target.id, ref: candidate.ref));
    }
    return result;
  }

  /// 是否存在「这次能带上的内容有限」归因（验收③的解释预算面：只作如实
  /// 说明，绝不禁用下方的更改/忘记操作）。
  bool get budgetLimited => (rejectedByReason['budget_exhausted'] ?? 0) > 0;

  /// 读面 payload → 视图。版本门 fail-closed（同 backend 读侧）：
  /// schema_version 不符 → null（调用方进 unsupported 态）。
  static ContextReceiptView? tryParse({
    required String mode,
    required Map<String, dynamic>? receipt,
    required List<Map<String, dynamic>> sourceVerifications,
    required int resolvedSelectedCount,
  }) {
    if (receipt == null) {
      return null;
    }
    final schemaVersion = receipt['schema_version']?.toString();
    if (schemaVersion != kContextSelectionReceiptSchemaVersion) {
      return null;
    }
    final receiptId = receipt['receipt_id']?.toString() ?? '';
    final role = receipt['selection_role']?.toString() ?? '';
    if (receiptId.isEmpty || role.isEmpty) {
      return null;
    }
    final candidatesRaw = receipt['candidates'];
    final candidatesUnknown = candidatesRaw == null;
    final candidates = <ReceiptCandidateView>[];
    var unknownReasonCount = 0;
    final rejectedByReason = <String, int>{};
    var selectedCount = 0;
    if (candidatesRaw is List) {
      for (final entry in candidatesRaw.whereType<Map<dynamic, dynamic>>()) {
        final status = entry['status']?.toString() ?? '';
        final ref = entry['ref']?.toString() ?? '';
        if (!kCandidateStatuses.contains(status) || ref.isEmpty) {
          continue; // 词表外条目不渲染也不计数（结构损坏面，如实降级）
        }
        candidates.add(
          ReceiptCandidateView(
            ref: ref,
            status: status,
            reasonCode: kRejectionReasonCodes.contains(entry['reason_code']?.toString())
                ? entry['reason_code']?.toString()
                : null,
          ),
        );
        if (status == 'selected') {
          selectedCount++;
        } else {
          final code = entry['reason_code']?.toString();
          if (code != null && kRejectionReasonCodes.contains(code)) {
            rejectedByReason[code] = (rejectedByReason[code] ?? 0) + 1;
          } else {
            unknownReasonCount++;
          }
        }
      }
    }
    String? whyStatement;
    String? whyBand;
    final whyRaw = receipt['why_now'];
    if (whyRaw is Map<dynamic, dynamic>) {
      final statement = whyRaw['statement']?.toString() ?? '';
      if (statement.trim().isNotEmpty) {
        whyStatement = statement;
        final band = whyRaw['confidence_band']?.toString();
        whyBand = kWhyNowConfidenceBands.contains(band) ? band : 'unknown';
      }
    }
    return ContextReceiptView._(
      mode: mode,
      receiptId: receiptId,
      selectionRole: kSelectionRoles.contains(role) ? role : '',
      candidates: candidates,
      sourceVerifications: sourceVerifications
          .map(ReceiptSourceVerification.fromJson)
          .whereType<ReceiptSourceVerification>()
          .toList(growable: false),
      resolvedSelectedCount: resolvedSelectedCount,
      selectedCount: selectedCount,
      rejectedByReason: Map.unmodifiable(rejectedByReason),
      unknownReasonCount: unknownReasonCount,
      whyNowStatement: whyStatement,
      whyNowBand: whyBand,
      candidatesUnknown: candidatesUnknown,
    );
  }
}

/// 单个候选（回执行投影；note debug-only 不落本模型）。
class ReceiptCandidateView {
  const ReceiptCandidateView({
    required this.ref,
    required this.status,
    this.reasonCode,
  });

  final String ref;
  final String status;

  /// selected 恒 null；rejected/unavailable 为封闭词表成员或 null（unknown 面）。
  final String? reasonCode;
}

/// 来源验证条目（metadata-only：kind/id/resolution，永不携带正文）。
class ReceiptSourceVerification {
  const ReceiptSourceVerification({
    required this.ref,
    required this.resolution,
    required this.statusCode,
  });

  factory ReceiptSourceVerification.fromJson(Map<dynamic, dynamic> json) {
    final resolution = json['resolution']?.toString() ?? '';
    return ReceiptSourceVerification(
      ref: json['ref']?.toString() ?? '',
      resolution: kSourceResolutions.contains(resolution) ? resolution : 'unresolved',
      statusCode: json['status_code']?.toString() ?? 'unknown',
    );
  }

  final String ref;

  /// resolved / unresolved（词表外从严归 unresolved，不猜）。
  final String resolution;

  /// ok / unknown / deleted（未定位时明确 unknown，不编时间/quote——I06 契约）。
  final String statusCode;
}

/// 可校准的选中记忆（resolved selected memory:// ref；仅携带真实身份）。
class CalibratableMemory {
  const CalibratableMemory({
    required this.kind,
    required this.id,
    required this.ref,
  });

  /// episodic / preference / goal（backend _parse_kind 词表；其余 kind 只显示）。
  final String kind;
  final String id;
  final String ref;
}
