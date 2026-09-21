/// U-04 · Action Proposal 统一交互组件的视图模型与幂等 UI 面.
///
/// 真源对齐（不重建，只做投影）：
/// - 状态/终态词表：`backend/app/core/action_command.py`（X-03 ProposalStatus
///   PENDING/COMMITTED/CANCELLED/EXPIRED/REJECTED；本组件把 PENDING + expired
///   标志投为 [ProposalCardStatus.expired]，其余一一对应）；
/// - 服务端幂等：X-09 `(user_id, idempotency_key)` / `(proposal_id,
///   idempotency_key)` 唯一 + approve 重放返回原 receipt。本文件只提供
///   **UI 侧防抖**（[ProposalActionGuard]）与**稳定幂等键推导**
///   （[proposalActionIdempotencyKey]），不重建服务端幂等语义。
library;

import 'package:flutter/foundation.dart';

/// 这一步轮到谁（HUMAN_AGENT_HYBRID.md §4：UI 应清楚显示"现在轮到谁"）。
///
/// 文案刻意非技术化：「你做 / Sparkle做 / 一起做」。
enum ProposalTurnOwnership {
  /// 你做——此步骤本身是用户要获得的能力/判断/创作。
  human,

  /// Sparkle 做——已授予自动权限或纯机械步骤，用户无需介入。
  agent,

  /// 一起做——Agent 准备 → 用户决定 → Agent 执行 的 hybrid handoff。
  hybrid,
}

/// Proposal 卡片状态（STATE_MATRIX「用户永远知道现在发生什么、能做什么」）.
///
/// 覆盖 U-04 要求的 awaiting user / partial / unknown / cancel / conflict，
/// 并对齐 X-03 后端词表的 committed / expired / rejected。
enum ProposalCardStatus {
  /// awaiting user——等你确认（唯一可执行 确认/拒绝 的状态）。
  awaitingUser,

  /// executing——Sparkle 正在做（run 进行中）。
  running,

  /// partial——部分完成：一部分效果已生效，剩余仍需确认。
  partial,

  /// unknown——结果未知（X-08 P2：委托路径可能不发完成事件）。
  /// 诚实展示"等待确认"，**不得**呈现为成功。
  unknown,

  /// committed——已落账（receipt 权威）。
  committed,

  /// cancelled——用户显式取消（terminal_reason=user_cancelled / cancel 端点）。
  cancelled,

  /// expired——过期作废（PENDING + expired 即时标志，或 terminal_reason=expired）。
  expired,

  /// rejected——用户在确认卡上拒绝。
  rejected,

  /// conflict——版本/内容冲突（409 VERSION_CONFLICT；需重新查看再决定）。
  conflict,
}

/// 一条 diff（前后对照；CORE_INTERACTION_PATTERNS #2「Propose before mutate」）.
@immutable
class ProposalDiffEntry {
  const ProposalDiffEntry({
    required this.field,
    this.before,
    this.after,
  });

  factory ProposalDiffEntry.fromJson(Map<String, dynamic> json) => ProposalDiffEntry(
      field: (json['field'] ?? json['label'] ?? '').toString(),
      before: json['before']?.toString(),
      after: json['after']?.toString(),
    );

  /// 兼容 `{"before": ..., "after": ..., "changed_fields": [...]}` 结构中
  /// changed_fields 为字符串数组（无 before/after 细节）的形态。
  factory ProposalDiffEntry.fromChangedField(Object? raw) {
    if (raw is Map) {
      return ProposalDiffEntry.fromJson(Map<String, dynamic>.from(raw));
    }
    return ProposalDiffEntry(field: '$raw');
  }

  final String field;
  final String? before;
  final String? after;
}

/// [ActionProposalCard] 的输入视图模型（纯展示数据，不含行为）.
@immutable
class ActionProposalCardData {
  const ActionProposalCardData({
    required this.proposalId,
    required this.status,
    this.ownership = ProposalTurnOwnership.hybrid,
    this.title,
    this.summary,
    this.diff = const <ProposalDiffEntry>[],
    this.receiptSummary,
    this.idempotencyKey,
  });

  /// 从 X-03 `GET /action-proposals` 投影（proposal_projection）构造.
  ///
  /// ownership 推导（保守、可被 [ownershipHint] 覆盖）：
  /// - authorization.mode == "auto" → agent（用户已授予自动权限）；
  /// - 其余 → hybrid（Agent 准备 → 人决定 → Agent 执行）。
  factory ActionProposalCardData.fromProjection(
    Map<String, dynamic> json, {
    ProposalTurnOwnership? ownershipHint,
  }) {
    final statusRaw = (json['status'] ?? '').toString().toUpperCase();
    final expiredFlag = json['expired'] == true;
    final terminalReason = (json['terminal_reason'] ?? '').toString();
    final diffJson = json['diff'];
    final diff = <ProposalDiffEntry>[];
    if (diffJson is Map) {
      final map = Map<String, dynamic>.from(diffJson);
      final changed = map['changed_fields'];
      final before = map['before'];
      final after = map['after'];
      if (changed is List && changed.isNotEmpty) {
        diff.addAll(changed.map(ProposalDiffEntry.fromChangedField));
      } else if (before != null || after != null) {
        diff.add(ProposalDiffEntry(
          field: '',
          before: before?.toString(),
          after: after?.toString(),
        ),);
      }
    }
    final authorization = json['authorization'];
    final authMode = authorization is Map
        ? (authorization['mode'] ?? '').toString()
        : '';

    ProposalCardStatus status;
    switch (statusRaw) {
      case 'PENDING':
        status = expiredFlag || terminalReason == 'expired'
            ? ProposalCardStatus.expired
            : ProposalCardStatus.awaitingUser;
      case 'COMMITTED':
        status = ProposalCardStatus.committed;
      case 'CANCELLED':
        status = ProposalCardStatus.cancelled;
      case 'EXPIRED':
        status = ProposalCardStatus.expired;
      case 'REJECTED':
        status = ProposalCardStatus.rejected;
      default:
        // 未知词表值按"结果待确认"诚实展示，不臆造成功。
        status = ProposalCardStatus.unknown;
    }

    final receipt = json['receipt'];
    final receiptSummary = receipt is Map
        ? ((receipt['summary'] ?? receipt['headline'] ?? '').toString())
        : null;

    return ActionProposalCardData(
      proposalId: (json['proposal_id'] ?? json['id'] ?? '').toString(),
      status: status,
      ownership: ownershipHint ??
          (authMode == 'auto'
              ? ProposalTurnOwnership.agent
              : ProposalTurnOwnership.hybrid),
      summary: json['summary']?.toString(),
      diff: diff,
      receiptSummary:
          receiptSummary != null && receiptSummary.isNotEmpty ? receiptSummary : null,
      idempotencyKey: json['idempotency_key']?.toString(),
    );
  }

  /// 从聊天 widget payload（`type: "action_proposal"`）构造.
  ///
  /// payload 约定字段：`proposal_id`、`status`（卡片状态词表，见
  /// [proposalStatusFromWire]）、`ownership`（"human"/"agent"/"hybrid"，缺省
  /// hybrid）、`title`/`summary`、`diff`（数组）、`receipt_summary`。
  factory ActionProposalCardData.fromChatPayload(Map<String, dynamic> data) {
    final diffRaw = data['diff'];
    final diff = diffRaw is List
        ? diffRaw
            .whereType<Map<dynamic, dynamic>>()
            .map((e) => ProposalDiffEntry.fromJson(Map<String, dynamic>.from(e)))
            .toList()
        : <ProposalDiffEntry>[];
    return ActionProposalCardData(
      proposalId: (data['proposal_id'] ?? data['id'] ?? '').toString(),
      status: proposalStatusFromWire(data['status']?.toString()),
      ownership: proposalOwnershipFromWire(data['ownership']?.toString()),
      title: data['title']?.toString(),
      summary: data['summary']?.toString(),
      diff: diff,
      receiptSummary: data['receipt_summary']?.toString(),
      idempotencyKey: data['idempotency_key']?.toString(),
    );
  }

  final String proposalId;
  final ProposalCardStatus status;
  final ProposalTurnOwnership ownership;
  final String? title;
  final String? summary;

  /// 前后对照（可空：不是所有 proposal 都有 diff）。
  final List<ProposalDiffEntry> diff;

  /// COMMITTED 后的权威回执摘要（receipt）。
  final String? receiptSummary;

  /// 调用方已持有的幂等键（如服务端下发）；为空时按 proposalId+动作推导。
  final String? idempotencyKey;

  /// 稳定幂等键：调用方显式携带 > 按 proposalId+动作推导。
  ///
  /// 同一 proposal 的同一动作在重建/重进后仍得到同一个键，服务端据此保证
  /// "重复点击恰一次 command"（X-09），UI 只需透传 + 防抖。
  String idempotencyKeyFor(String action) =>
      idempotencyKey ?? proposalActionIdempotencyKey(proposalId, action);
}

/// 稳定幂等键推导（UI 透传给服务端 command path 的键）.
String proposalActionIdempotencyKey(String proposalId, String action) =>
    'u04:$proposalId:$action';

/// wire → [ProposalCardStatus]（聊天 payload / 通用字符串形态）.
ProposalCardStatus proposalStatusFromWire(String? raw) {
  switch ((raw ?? '').toLowerCase()) {
    case 'awaiting_user':
    case 'pending':
    case 'pending_confirmation':
      return ProposalCardStatus.awaitingUser;
    case 'running':
    case 'executing':
      return ProposalCardStatus.running;
    case 'partial':
    case 'partial_data':
      return ProposalCardStatus.partial;
    case 'unknown':
    case 'unknown_outcome':
      return ProposalCardStatus.unknown;
    case 'committed':
    case 'success':
      return ProposalCardStatus.committed;
    case 'cancelled':
    case 'canceled':
      return ProposalCardStatus.cancelled;
    case 'expired':
      return ProposalCardStatus.expired;
    case 'rejected':
      return ProposalCardStatus.rejected;
    case 'conflict':
    case 'version_conflict':
      return ProposalCardStatus.conflict;
    default:
      return ProposalCardStatus.unknown;
  }
}

/// wire → [ProposalTurnOwnership].
ProposalTurnOwnership proposalOwnershipFromWire(String? raw) {
  switch ((raw ?? '').toLowerCase()) {
    case 'human':
      return ProposalTurnOwnership.human;
    case 'agent':
      return ProposalTurnOwnership.agent;
    case 'hybrid':
    default:
      return ProposalTurnOwnership.hybrid;
  }
}

/// UI 侧命令防抖：同一时刻至多一个在途命令；在途期间的重入（双击/连点）
/// 复用同一 Future，不产生第二次调用——"重复点击不产生重复 command"的
/// UI 保证面（服务端幂等由 X-09 真源承担，这里不重建）。
class ProposalActionGuard {
  final Map<String, Future<void>> _inFlight = <String, Future<void>>{};

  /// 是否有[action]在途。
  bool isInFlight(String action) => _inFlight.containsKey(action);

  /// 是否有任意命令在途（用于禁用全部操作按钮）。
  bool get isBusy => _inFlight.isNotEmpty;

  /// 以[action]为键运行[op]；在途期间的重入返回**同一个** Future。
  Future<void> run(String action, Future<void> Function() op) {
    final existing = _inFlight[action];
    if (existing != null) {
      return existing;
    }
    // 注意：回调必须用块体丢弃 Map.remove 的返回值——remove 返回的正是
    // map 中存下的这个 future，箭体写法会让 whenComplete 等待它自身而死锁。
    final future = op().whenComplete(() {
      _inFlight.remove(action);
    });
    _inFlight[action] = future;
    return future;
  }

  /// 测试与 dispose 用。
  void reset() => _inFlight.clear();
}
