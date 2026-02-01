// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'photon_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

PhotonBalance _$PhotonBalanceFromJson(Map<String, dynamic> json) =>
    PhotonBalance(
      userId: json['user_id'] as String,
      balance: (json['balance'] as num).toInt(),
      updatedAt: json['updated_at'] == null
          ? null
          : DateTime.parse(json['updated_at'] as String),
    );

Map<String, dynamic> _$PhotonBalanceToJson(PhotonBalance instance) =>
    <String, dynamic>{
      'user_id': instance.userId,
      'balance': instance.balance,
      'updated_at': instance.updatedAt?.toIso8601String(),
    };

PhotonTransaction _$PhotonTransactionFromJson(Map<String, dynamic> json) =>
    PhotonTransaction(
      id: json['id'] as String,
      transactionType:
          $enumDecode(_$PhotonTransactionTypeEnumMap, json['transaction_type']),
      amount: (json['amount'] as num).toInt(),
      balanceBefore: (json['balance_before'] as num).toInt(),
      balanceAfter: (json['balance_after'] as num).toInt(),
      createdAt: DateTime.parse(json['created_at'] as String),
      source: json['source'] as String?,
      relatedItemId: json['related_item_id'] as String?,
      metadata: json['extra_data'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$PhotonTransactionToJson(PhotonTransaction instance) =>
    <String, dynamic>{
      'id': instance.id,
      'transaction_type':
          _$PhotonTransactionTypeEnumMap[instance.transactionType]!,
      'amount': instance.amount,
      'balance_before': instance.balanceBefore,
      'balance_after': instance.balanceAfter,
      'source': instance.source,
      'related_item_id': instance.relatedItemId,
      'extra_data': instance.metadata,
      'created_at': instance.createdAt.toIso8601String(),
    };

const _$PhotonTransactionTypeEnumMap = {
  PhotonTransactionType.grantAchievement: 'grant_achievement',
  PhotonTransactionType.grantDailyFirst: 'grant_daily_first',
  PhotonTransactionType.grantContract: 'grant_contract',
  PhotonTransactionType.grantContractBonus: 'grant_contract_bonus',
  PhotonTransactionType.deductContractStake: 'deduct_contract_stake',
  PhotonTransactionType.purchase: 'purchase',
  PhotonTransactionType.transferOut: 'transfer_out',
  PhotonTransactionType.transferIn: 'transfer_in',
  PhotonTransactionType.refund: 'refund',
  PhotonTransactionType.penalty: 'penalty',
  PhotonTransactionType.adminAdjustment: 'admin_adjustment',
};

TransactionSummary _$TransactionSummaryFromJson(Map<String, dynamic> json) =>
    TransactionSummary(
      totalIncome: (json['total_income'] as num).toInt(),
      totalExpense: (json['total_expense'] as num).toInt(),
      netChange: (json['net_change'] as num).toInt(),
      transactionCount: (json['transaction_count'] as num).toInt(),
      byType: Map<String, int>.from(json['by_type'] as Map),
    );

Map<String, dynamic> _$TransactionSummaryToJson(TransactionSummary instance) =>
    <String, dynamic>{
      'total_income': instance.totalIncome,
      'total_expense': instance.totalExpense,
      'net_change': instance.netChange,
      'transaction_count': instance.transactionCount,
      'by_type': instance.byType,
    };
