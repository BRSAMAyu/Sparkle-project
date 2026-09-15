import 'package:json_annotation/json_annotation.dart';
import 'package:sparkle/core/services/i18n_service.dart';

part 'photon_model.g.dart';

// ========== Photon System Models ==========
//
// NOTE: All photon models use snake_case JSON serialization via fieldRename:
// FieldRename.snake to match the backend API contract. This means toJson()
// will emit snake_case JSON (e.g., "user_id", "transaction_type") rather than
// camelCase. Ensure any local storage or caching layers handle this correctly.
//
// Backend field mapping: PhotonTransaction.metadata is stored as "extra_data"
// in the API response, mapped via @JsonKey(name: 'extra_data').
//
// ==========

/// 光子交易类型
enum PhotonTransactionType {
  @JsonValue('grant_achievement')
  grantAchievement,
  @JsonValue('grant_daily_first')
  grantDailyFirst,
  @JsonValue('grant_contract')
  grantContract,
  @JsonValue('grant_contract_bonus')
  grantContractBonus,
  @JsonValue('deduct_contract_stake')
  deductContractStake,
  @JsonValue('purchase')
  purchase,
  @JsonValue('transfer_out')
  transferOut,
  @JsonValue('transfer_in')
  transferIn,
  @JsonValue('refund')
  refund,
  @JsonValue('penalty')
  penalty,
  @JsonValue('admin_adjustment')
  adminAdjustment,
}

// ========== 光子余额实体 ==========

@JsonSerializable(fieldRename: FieldRename.snake)
class PhotonBalance {

  PhotonBalance({
    required this.userId,
    required this.balance,
    this.updatedAt,
  });

  factory PhotonBalance.fromJson(Map<String, dynamic> json) =>
      _$PhotonBalanceFromJson(json);
  final String userId;
  final int balance;
  final DateTime? updatedAt;

  Map<String, dynamic> toJson() => _$PhotonBalanceToJson(this);

  PhotonBalance copyWith({
    String? userId,
    int? balance,
    DateTime? updatedAt,
  }) => PhotonBalance(
      userId: userId ?? this.userId,
      balance: balance ?? this.balance,
      updatedAt: updatedAt ?? this.updatedAt,
    );

  @override
  String toString() => 'PhotonBalance(userId: $userId, balance: $balance, updatedAt: $updatedAt)';
}

// ========== 光子交易记录实体 ==========

@JsonSerializable(fieldRename: FieldRename.snake)
class PhotonTransaction {

  PhotonTransaction({
    required this.id,
    required this.transactionType,
    required this.amount,
    required this.balanceBefore,
    required this.balanceAfter,
    required this.createdAt, this.source,
    this.relatedItemId,
    this.metadata,
  });

  factory PhotonTransaction.fromJson(Map<String, dynamic> json) =>
      _$PhotonTransactionFromJson(json);
  final String id;
  final PhotonTransactionType transactionType;
  final int amount;
  final int balanceBefore;
  final int balanceAfter;
  final String? source;
  final String? relatedItemId;

  /// Backend field: extra_data
  @JsonKey(name: 'extra_data')
  final Map<String, dynamic>? metadata;

  final DateTime createdAt;

  Map<String, dynamic> toJson() => _$PhotonTransactionToJson(this);

  /// 是否为收入交易
  bool get isIncome => amount > 0;

  /// 是否为支出交易
  bool get isExpense => amount < 0;

  /// 获取交易类型的显示名称
  String get transactionTypeName {
    final l10n = I18nService.instance.l10n;
    switch (transactionType) {
      case PhotonTransactionType.grantAchievement:
        return l10n.photonTransactionGrantAchievement;
      case PhotonTransactionType.grantDailyFirst:
        return l10n.photonTransactionGrantDailyFirst;
      case PhotonTransactionType.grantContract:
        return l10n.photonTransactionGrantContract;
      case PhotonTransactionType.grantContractBonus:
        return l10n.photonTransactionGrantContractBonus;
      case PhotonTransactionType.deductContractStake:
        return l10n.photonTransactionDeductContractStake;
      case PhotonTransactionType.purchase:
        return l10n.photonTransactionPurchase;
      case PhotonTransactionType.transferOut:
        return l10n.photonTransactionTransferOut;
      case PhotonTransactionType.transferIn:
        return l10n.photonTransactionTransferIn;
      case PhotonTransactionType.refund:
        return l10n.photonTransactionRefund;
      case PhotonTransactionType.penalty:
        return l10n.photonTransactionPenalty;
      case PhotonTransactionType.adminAdjustment:
        return l10n.photonTransactionAdminAdjustment;
    }
  }

  PhotonTransaction copyWith({
    String? id,
    PhotonTransactionType? transactionType,
    int? amount,
    int? balanceBefore,
    int? balanceAfter,
    String? source,
    String? relatedItemId,
    Map<String, dynamic>? metadata,
    DateTime? createdAt,
  }) => PhotonTransaction(
      id: id ?? this.id,
      transactionType: transactionType ?? this.transactionType,
      amount: amount ?? this.amount,
      balanceBefore: balanceBefore ?? this.balanceBefore,
      balanceAfter: balanceAfter ?? this.balanceAfter,
      source: source ?? this.source,
      relatedItemId: relatedItemId ?? this.relatedItemId,
      metadata: metadata ?? this.metadata,
      createdAt: createdAt ?? this.createdAt,
    );

  @override
  String toString() => 'PhotonTransaction(id: $id, type: $transactionType, amount: $amount, balanceAfter: $balanceAfter)';
}

// ========== 交易汇总统计实体 ==========

@JsonSerializable(fieldRename: FieldRename.snake)
class TransactionSummary {

  TransactionSummary({
    required this.totalIncome,
    required this.totalExpense,
    required this.netChange,
    required this.transactionCount,
    required this.byType,
  });

  factory TransactionSummary.fromJson(Map<String, dynamic> json) =>
      _$TransactionSummaryFromJson(json);
  final int totalIncome;
  final int totalExpense;
  final int netChange;
  final int transactionCount;
  final Map<String, int> byType;

  Map<String, dynamic> toJson() => _$TransactionSummaryToJson(this);

  TransactionSummary copyWith({
    int? totalIncome,
    int? totalExpense,
    int? netChange,
    int? transactionCount,
    Map<String, int>? byType,
  }) => TransactionSummary(
      totalIncome: totalIncome ?? this.totalIncome,
      totalExpense: totalExpense ?? this.totalExpense,
      netChange: netChange ?? this.netChange,
      transactionCount: transactionCount ?? this.transactionCount,
      byType: byType ?? this.byType,
    );

  @override
  String toString() => 'TransactionSummary(income: $totalIncome, expense: $totalExpense, net: $netChange, count: $transactionCount)';
}
