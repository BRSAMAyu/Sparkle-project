import 'package:dio/dio.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/photon/data/models/photon_redeem_pro_model.dart';

/// D-COMM-2：光子兑 Pro 仓库。
///
/// 读面 = 快照（`GET /photons/redeem-pro/status`，autoDispose 重进即重取）；
/// 动作面 = `POST /photons/redeem-pro`（有界终态，业务失败映射为
/// [PhotonRedeemProResult]，不向 UI 泄漏原始异常结构——照 RedeemCodeResult 先例）。
///
/// 诚实性（PHOTON-STATUS）：可兑换基数/月顶状态一律来自 status 快照（与引擎
/// `POST /redeem-pro` 同一 service 判定函数的服务端读取），本仓库不做任何本地
/// 推算——原客户端 UTC 月窗自算已随 status 端点上线移除，判定交还引擎同源。
class PhotonRedeemProRepository {
  PhotonRedeemProRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<PhotonRedeemProOverview> getOverview() async {
    if (DemoDataService.isDemoMode) {
      // 演示态同走诚实口径：空账本真值（零余额/零基数/未兑换），不造假资产。
      return const PhotonRedeemProOverview(
        balance: 0,
        redeemedThisMonth: false,
        redeemableBase: 0,
      );
    }

    // PHOTON-STATUS：一次请求取回余额 + 基数 + 月顶 + 常量（原「余额 + 流水
    // 过滤」两读合一），数字全部由服务端核算。
    final response = await _apiClient.get<Map<String, dynamic>>(
      ApiEndpoints.photonRedeemProStatus,
    );
    final payload = ApiResponseParser.unwrapMap(
      response.data,
      action: 'getRedeemOverview',
    );
    return PhotonRedeemProOverview.fromStatusJson(payload);
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
