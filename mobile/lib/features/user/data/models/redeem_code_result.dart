import 'package:dio/dio.dart';

/// D-REDEEM · 兑换码核销结果（有界词表，与引擎 RedeemOutcome 对齐）。
enum RedeemCodeStatus { success, invalid, expired, exhausted, error }

class RedeemCodeResult {
  const RedeemCodeResult({
    required this.status,
    this.tier,
    this.expiresAt,
  });

  final RedeemCodeStatus status;
  final String? tier;
  final DateTime? expiresAt;

  bool get isSuccess => status == RedeemCodeStatus.success;

  /// 引擎 RedeemResponse → 结果对象。
  static RedeemCodeResult parse(Map<String, dynamic> payload) {
    final statusRaw = payload['status'] as String?;
    final tier = payload['tier'] as String?;
    final expiresRaw = payload['entitlement_expires_at'] as String?;
    final expiresAt = expiresRaw == null ? null : DateTime.tryParse(expiresRaw);
    switch (statusRaw) {
      case 'ok':
        return RedeemCodeResult(
          status: RedeemCodeStatus.success,
          tier: tier,
          expiresAt: expiresAt,
        );
      case 'invalid':
        return const RedeemCodeResult(status: RedeemCodeStatus.invalid);
      case 'expired':
        return const RedeemCodeResult(status: RedeemCodeStatus.expired);
      case 'exhausted':
        return const RedeemCodeResult(status: RedeemCodeStatus.exhausted);
      default:
        return const RedeemCodeResult(status: RedeemCodeStatus.error);
    }
  }

  /// 业务失败 HTTP 状态（gateway 代理透传引擎 4xx）→ 结果对象。
  static RedeemCodeResult fromDioError(Object error) {
    if (error is! DioException) {
      return const RedeemCodeResult(status: RedeemCodeStatus.error);
    }
    switch (error.response?.statusCode) {
      case 404:
        return const RedeemCodeResult(status: RedeemCodeStatus.invalid);
      case 410:
        return const RedeemCodeResult(status: RedeemCodeStatus.expired);
      case 409:
        return const RedeemCodeResult(status: RedeemCodeStatus.exhausted);
      default:
        return const RedeemCodeResult(status: RedeemCodeStatus.error);
    }
  }
}
