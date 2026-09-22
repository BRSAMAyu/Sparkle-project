/// D-COMM-2：光子兑 Pro（「学出会员」）移动端契约模型。
///
/// 后端契约（app/api/v1/photons.py `POST /photons/redeem-pro` + photon_redeem_service
/// 有界词表）：成功 200 返回 `{success, message, status, data:{...}}`；业务失败
/// 返回 4xx/5xx，结构化终态在 `detail.{status, message, cost_photons, pro_days,
/// redeemable_base}`。手写解析（一次性动作契约，对齐 RedeemCodeResult /
/// PlanConfirmResult 手写风格，不进 build_runner）。
///
/// 诚实性口径：可兑换基数（redeemable_base）只能来自服务端响应（审计流水重放，
/// transfer_in 排除），本模型不做任何本地推算；未揭示时不产出该数字。
library;

import 'package:dio/dio.dart';

/// 兑换业务终态（对齐 photon_redeem_service 有界词表）。
enum PhotonRedeemProStatus {
  ok,
  insufficientBalance,
  insufficientBase,
  monthlyCapReached,
  error,
}

/// 展示用常量，对齐引擎 `settings.PHOTON_REDEEM_PRO_COST/DAYS`【待产品校准】。
///
/// 仅作动作前展示；兑换响应返回服务端实际值后以响应值覆盖展示（诚实优先于
/// 本地常量，避免双源漂移）。
const int photonRedeemProDisplayCost = 3000;
const int photonRedeemProDisplayDays = 7;

PhotonRedeemProStatus _statusFromRaw(String? raw) {
  switch (raw) {
    case 'ok':
      return PhotonRedeemProStatus.ok;
    case 'insufficient_balance':
      return PhotonRedeemProStatus.insufficientBalance;
    case 'insufficient_base':
      return PhotonRedeemProStatus.insufficientBase;
    case 'monthly_cap_reached':
      return PhotonRedeemProStatus.monthlyCapReached;
    default:
      return PhotonRedeemProStatus.error;
  }
}

class PhotonRedeemProResult {
  const PhotonRedeemProResult({
    required this.status,
    this.costPhotons,
    this.proDays,
    this.redeemableBase,
    this.balanceAfter,
    this.entitlementExpiresAt,
  });

  /// 成功响应 envelope（`{success, message, status, data:{...}}`）→ 结果。
  factory PhotonRedeemProResult.fromJson(Map<String, dynamic> envelope) {
    final data = envelope['data'];
    final dataMap =
        data is Map<String, dynamic> ? data : const <String, dynamic>{};
    final expiresRaw = dataMap['entitlement_expires_at'] as String?;
    return PhotonRedeemProResult(
      status: _statusFromRaw(envelope['status'] as String?),
      costPhotons: (dataMap['cost_photons'] as num?)?.toInt(),
      proDays: (dataMap['pro_days'] as num?)?.toInt(),
      redeemableBase: (dataMap['redeemable_base'] as num?)?.toInt(),
      balanceAfter: (dataMap['balance_after'] as num?)?.toInt(),
      entitlementExpiresAt:
          expiresRaw == null ? null : DateTime.tryParse(expiresRaw),
    );
  }

  /// 业务失败 HTTP 响应（detail 为结构化终态 dict）→ 结果。
  ///
  /// detail 缺失或不可解析时退化为 [PhotonRedeemProStatus.error]——不猜状态、
  /// 不给假文案（409 同时承载 insufficient_base 与 monthly_cap，无 body 不可分）。
  factory PhotonRedeemProResult.fromDioError(Object error) {
    if (error is! DioException) {
      return const PhotonRedeemProResult(status: PhotonRedeemProStatus.error);
    }
    final body = error.response?.data;
    if (body is! Map<String, dynamic>) {
      return const PhotonRedeemProResult(status: PhotonRedeemProStatus.error);
    }
    final detail = body['detail'];
    if (detail is! Map<String, dynamic>) {
      return const PhotonRedeemProResult(status: PhotonRedeemProStatus.error);
    }
    return PhotonRedeemProResult(
      status: _statusFromRaw(detail['status'] as String?),
      costPhotons: (detail['cost_photons'] as num?)?.toInt(),
      proDays: (detail['pro_days'] as num?)?.toInt(),
      redeemableBase: (detail['redeemable_base'] as num?)?.toInt(),
    );
  }

  final PhotonRedeemProStatus status;

  /// 服务端实际扣减价（可能为 null——仅动作前展示常量兜底）。
  final int? costPhotons;

  /// 服务端实际授予天数。
  final int? proDays;

  /// 服务端揭示的可兑换基数（审计流水重放；未揭示恒 null，不本地推算）。
  final int? redeemableBase;

  /// 兑换后的混桶余额（仅 ok）。
  final int? balanceAfter;

  /// Pro 到期时间（仅 ok）。
  final DateTime? entitlementExpiresAt;

  bool get isOk => status == PhotonRedeemProStatus.ok;
}

/// 兑换面总览快照：混桶余额 + 当月兑换资格。
///
/// 月顶判定真源与引擎一致 = 审计流水（`GET /photons/transactions` 按
/// `transaction_type=redeem_pro` 服务端过滤，客户端只做「是否落在本 UTC 月」
/// 的窗口判定，不推算基数）。
class PhotonRedeemProOverview {
  const PhotonRedeemProOverview({
    required this.balance,
    required this.redeemedThisMonth,
  });

  final int balance;
  final bool redeemedThisMonth;
}
