import 'package:json_annotation/json_annotation.dart';

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
  final String userId;
  final int balance;
  final DateTime? updatedAt;

  PhotonBalance({
    required this.userId,
    required this.balance,
    this.updatedAt,
  });

  factory PhotonBalance.fromJson(Map<String, dynamic> json) =>
      _$PhotonBalanceFromJson(json);

  Map<String, dynamic> toJson() => _$PhotonBalanceToJson(this);

  PhotonBalance copyWith({
    String? userId,
    int? balance,
    DateTime? updatedAt,
  }) {
    return PhotonBalance(
      userId: userId ?? this.userId,
      balance: balance ?? this.balance,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  @override
  String toString() {
    return 'PhotonBalance(userId: $userId, balance: $balance, updatedAt: $updatedAt)';
  }
}

// ========== 光子交易记录实体 ==========

@JsonSerializable(fieldRename: FieldRename.snake)
class PhotonTransaction {
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

  PhotonTransaction({
    required this.id,
    required this.transactionType,
    required this.amount,
    required this.balanceBefore,
    required this.balanceAfter,
    this.source,
    this.relatedItemId,
    this.metadata,
    required this.createdAt,
  });

  factory PhotonTransaction.fromJson(Map<String, dynamic> json) =>
      _$PhotonTransactionFromJson(json);

  Map<String, dynamic> toJson() => _$PhotonTransactionToJson(this);

  /// 是否为收入交易
  bool get isIncome => amount > 0;

  /// 是否为支出交易
  bool get isExpense => amount < 0;

  /// 获取交易类型的显示名称
  String get transactionTypeName {
    switch (transactionType) {
      case PhotonTransactionType.grantAchievement:
        return '成就奖励';
      case PhotonTransactionType.grantDailyFirst:
        return '每日首胜';
      case PhotonTransactionType.grantContract:
        return '契约完成';
      case PhotonTransactionType.grantContractBonus:
        return '契约加成';
      case PhotonTransactionType.deductContractStake:
        return '契约失败';
      case PhotonTransactionType.purchase:
        return '商城购买';
      case PhotonTransactionType.transferOut:
        return '转账-转出';
      case PhotonTransactionType.transferIn:
        return '转账-转入';
      case PhotonTransactionType.refund:
        return '退款';
      case PhotonTransactionType.penalty:
        return '惩罚';
      case PhotonTransactionType.adminAdjustment:
        return '管理员调整';
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
  }) {
    return PhotonTransaction(
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
  }

  @override
  String toString() {
    return 'PhotonTransaction(id: $id, type: $transactionType, amount: $amount, balanceAfter: $balanceAfter)';
  }
}

// ========== 交易汇总统计实体 ==========

@JsonSerializable(fieldRename: FieldRename.snake)
class TransactionSummary {
  final int totalIncome;
  final int totalExpense;
  final int netChange;
  final int transactionCount;
  final Map<String, int> byType;

  TransactionSummary({
    required this.totalIncome,
    required this.totalExpense,
    required this.netChange,
    required this.transactionCount,
    required this.byType,
  });

  factory TransactionSummary.fromJson(Map<String, dynamic> json) =>
      _$TransactionSummaryFromJson(json);

  Map<String, dynamic> toJson() => _$TransactionSummaryToJson(this);

  TransactionSummary copyWith({
    int? totalIncome,
    int? totalExpense,
    int? netChange,
    int? transactionCount,
    Map<String, int>? byType,
  }) {
    return TransactionSummary(
      totalIncome: totalIncome ?? this.totalIncome,
      totalExpense: totalExpense ?? this.totalExpense,
      netChange: netChange ?? this.netChange,
      transactionCount: transactionCount ?? this.transactionCount,
      byType: byType ?? this.byType,
    );
  }

  @override
  String toString() {
    return 'TransactionSummary(income: $totalIncome, expense: $totalExpense, net: $netChange, count: $transactionCount)';
  }
}
