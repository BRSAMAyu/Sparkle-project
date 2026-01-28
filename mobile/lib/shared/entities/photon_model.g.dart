// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'photon_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

PhotonBalance _$PhotonBalanceFromJson(Map<String, dynamic> json) =>
    PhotonBalance(
      userId: json['userId'] as String,
      balance: (json['balance'] as num).toInt(),
      updatedAt: json['updatedAt'] == null
          ? null
          : DateTime.parse(json['updatedAt'] as String),
    );

Map<String, dynamic> _$PhotonBalanceToJson(PhotonBalance instance) =>
    <String, dynamic>{
      'userId': instance.userId,
      'balance': instance.balance,
      'updatedAt': instance.updatedAt?.toIso8601String(),
    };

PhotonTransaction _$PhotonTransactionFromJson(Map<String, dynamic> json) =>
    PhotonTransaction(
      id: json['id'] as String,
      transactionType:
          $enumDecode(_$PhotonTransactionTypeEnumMap, json['transactionType']),
      amount: (json['amount'] as num).toInt(),
      balanceBefore: (json['balanceBefore'] as num).toInt(),
      balanceAfter: (json['balanceAfter'] as num).toInt(),
      source: json['source'] as String?,
      relatedItemId: json['relatedItemId'] as String?,
      metadata: json['metadata'] as Map<String, dynamic>?,
      createdAt: DateTime.parse(json['createdAt'] as String),
    );

Map<String, dynamic> _$PhotonTransactionToJson(PhotonTransaction instance) =>
    <String, dynamic>{
      'id': instance.id,
      'transactionType':
          _$PhotonTransactionTypeEnumMap[instance.transactionType]!,
      'amount': instance.amount,
      'balanceBefore': instance.balanceBefore,
      'balanceAfter': instance.balanceAfter,
      'source': instance.source,
      'relatedItemId': instance.relatedItemId,
      'metadata': instance.metadata,
      'createdAt': instance.createdAt.toIso8601String(),
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
      totalIncome: (json['totalIncome'] as num).toInt(),
      totalExpense: (json['totalExpense'] as num).toInt(),
      netChange: (json['netChange'] as num).toInt(),
      transactionCount: (json['transactionCount'] as num).toInt(),
      byType: Map<String, int>.from(json['byType'] as Map),
    );

Map<String, dynamic> _$TransactionSummaryToJson(TransactionSummary instance) =>
    <String, dynamic>{
      'totalIncome': instance.totalIncome,
      'totalExpense': instance.totalExpense,
      'netChange': instance.netChange,
      'transactionCount': instance.transactionCount,
      'byType': instance.byType,
    };
