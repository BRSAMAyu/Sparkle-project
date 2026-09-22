/// D-COMM-2：光子兑 Pro（「学出会员」）移动端契约模型。
///
/// 后端契约（app/api/v1/photons.py `POST /photons/redeem-pro` + photon_redeem_service
/// 有界词表）：成功 200 返回 `{success, message, status, data:{...}}`；业务失败
/// 返回 4xx/5xx，结构化终态在 `detail.{status, message, cost_photons, pro_days,
/// redeemable_base}`。手写解析（一次性动作契约，对齐 RedeemCodeResult /
/// PlanConfirmResult 手写风格，不进 build_runner）。
///
/// 诚实性口径：可兑换基数（redeemable_base）只能来自服务端（审计流水重放，
/// transfer_in 排除）——动作前经 `GET /photons/redeem-pro/status` 快照揭示，
/// 兑换响应再次带回校验；本模型不做任何本地推算，未揭示时不产出该数字。
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

/// 展示用常量，对齐引擎 `settings.PHOTON_REDEEM_PRO_COST/DAYS`（2026-09-22
/// 校准 3000→1500，依据 TOUR 活栈全旅程实测：诚实日均光子收入 30-80）。
///
/// 仅作动作前展示；兑换响应返回服务端实际值后以响应值覆盖展示（诚实优先于
/// 本地常量，避免双源漂移）。
const int photonRedeemProDisplayCost = 1500;
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

/// 兑换面总览快照：混桶余额 + 可兑换基数 + 当月兑换资格（PHOTON-STATUS 真数）。
///
/// 数据源 = `GET /photons/redeem-pro/status`（与引擎 `POST /redeem-pro` 同一
/// service 判定函数：基数审计流水重放、月顶流水 + UTC 月窗、settings 常量）——
/// 客户端零本地推算，月顶窗口判定也交还引擎（原客户端 UTC 月窗自算已移除，
/// 杜绝双端漂移）。`redeemableBase`（可兑换口径）与 `balance`（混桶总余额）
/// 并列诚实区分。
class PhotonRedeemProOverview {
  const PhotonRedeemProOverview({
    required this.balance,
    required this.redeemedThisMonth,
    this.redeemableBase,
    this.costPhotons,
    this.proDays,
    this.monthlyCap,
    this.nextWindowAt,
    this.canRedeem = false,
  });

  /// status 响应（`{success, status, data:{...}}` 的 data）→ 快照。
  ///
  /// 手写解析（对齐 [PhotonRedeemProResult] 风格）；字段缺失不猜——
  /// `redeemableBase` 恒 nullable，缺失时 UI 走「由服务端核算」诚实空态。
  factory PhotonRedeemProOverview.fromStatusJson(Map<String, dynamic> json) {
    final nextRaw = json['next_window_at'] as String?;
    return PhotonRedeemProOverview(
      balance: (json['balance'] as num?)?.toInt() ?? 0,
      // 引擎 `monthly_cap_used` → 客户端 `redeemedThisMonth`（同义不改名，少 churn）。
      redeemedThisMonth: json['monthly_cap_used'] as bool? ?? false,
      redeemableBase: (json['redeemable_base'] as num?)?.toInt(),
      costPhotons: (json['cost_photons'] as num?)?.toInt(),
      proDays: (json['pro_days'] as num?)?.toInt(),
      monthlyCap: (json['monthly_cap'] as num?)?.toInt(),
      nextWindowAt: nextRaw == null ? null : DateTime.tryParse(nextRaw),
      canRedeem: json['can_redeem'] as bool? ?? false,
    );
  }

  final int balance;

  /// 当月是否已兑换（引擎 `monthly_cap_used`，真源 = redeem_pro 流水 + UTC 月窗）。
  final bool redeemedThisMonth;

  /// 可兑换基数（审计流水重放，transfer_in 不计入）；null = 服务端未揭示。
  final int? redeemableBase;

  /// 服务端单次兑换价（settings 常量）。
  final int? costPhotons;

  /// 服务端单次兑换 Pro 天数。
  final int? proDays;

  /// 自然月兑换硬顶次数。
  final int? monthlyCap;

  /// 下一 UTC 自然月起点（月顶重置边界）。
  final DateTime? nextWindowAt;

  /// 服务端预判能否兑换（月顶未用 ∧ 基数够 ∧ 余额够）；最终以兑换终态为准。
  final bool canRedeem;
}
