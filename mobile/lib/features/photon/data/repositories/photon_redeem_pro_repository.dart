import 'package:dio/dio.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/photon/data/models/photon_redeem_pro_model.dart';
import 'package:sparkle/shared/entities/photon_model.dart';

/// D-COMM-2：光子兑 Pro 仓库。
///
/// 读面 = 快照（余额 + 当月兑换资格，autoDispose 重进即重取）；
/// 动作面 = `POST /photons/redeem-pro`（有界终态，业务失败映射为
/// [PhotonRedeemProResult]，不向 UI 泄漏原始异常结构——照 RedeemCodeResult 先例）。
///
/// 诚实性：可兑换基数不在本仓库做任何本地推算（审计流水重放是引擎侧职责），
/// 只随兑换响应由服务端揭示；月顶判定复用引擎同款真源（本通道流水 + UTC 自然月）。
class PhotonRedeemProRepository {
  PhotonRedeemProRepository(this._apiClient);

  final ApiClient _apiClient;

  /// 本通道月顶判定的流水类型（对齐引擎 `REDEEM_PRO_TX_TYPE`）。
  static const String _redeemTxType = 'redeem_pro';

  Future<PhotonRedeemProOverview> getOverview() async {
    if (DemoDataService.isDemoMode) {
      // 演示态同走诚实口径：零余额 + 未兑换，不造假资产。
      return const PhotonRedeemProOverview(
        balance: 0,
        redeemedThisMonth: false,
      );
    }

    final balanceResponse = await _apiClient.get<Map<String, dynamic>>(
      ApiEndpoints.photonBalance,
    );
    final balancePayload = ApiResponseParser.unwrapMap(
      balanceResponse.data,
      action: 'getRedeemOverview',
    );
    final balance = PhotonBalance.fromJson(balancePayload).balance;
    final redeemedThisMonth = await _hasRedeemedThisMonth();
    return PhotonRedeemProOverview(
      balance: balance,
      redeemedThisMonth: redeemedThisMonth,
    );
  }

  /// 当月是否已有本通道兑换流水（引擎同款真源：审计流水 + UTC 自然月窗）。
  Future<bool> _hasRedeemedThisMonth() async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      ApiEndpoints.photonTransactions,
      queryParameters: <String, dynamic>{
        'transaction_type': _redeemTxType,
        'limit': 100,
        'offset': 0,
      },
    );
    final payload = response.data;
    final rows = payload is Map<String, dynamic>
        ? (payload['data'] as List<dynamic>? ?? const [])
        : const <dynamic>[];
    final now = DateTime.now().toUtc();
    final monthStart = DateTime.utc(now.year, now.month);
    for (final row in rows) {
      if (row is! Map<String, dynamic>) continue;
      final createdRaw = row['created_at'];
      final created =
          createdRaw is String ? DateTime.tryParse(createdRaw)?.toUtc() : null;
      if (created != null && !created.isBefore(monthStart)) {
        return true;
      }
    }
    return false;
  }

  /// 发起兑换。业务失败（400/409/5xx）映射为有界 [PhotonRedeemProResult]。
  Future<PhotonRedeemProResult> redeem() async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.photonRedeemPro,
      );
      final body = response.data;
      if (body is! Map<String, dynamic>) {
        throw Exception('redeemPro response is empty');
      }
      return PhotonRedeemProResult.fromJson(body);
    } on DioException catch (e) {
      return PhotonRedeemProResult.fromDioError(e);
    } catch (_) {
      return const PhotonRedeemProResult(status: PhotonRedeemProStatus.error);
    }
  }
}
