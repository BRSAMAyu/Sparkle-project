import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';

/// A-06 · Calibration Receipt 四动作纠偏 API（/aurora/receipts/respond）。
///
/// 独立于 ``MemoryApiService``（其接口被 11+ 测试 fake 冻结，新增方法会
/// 全量破坏既有实现）；回执纠偏是 Aurora 域面，单独成类与后端
/// ``/aurora/receipts`` 路由对称。
class AuroraReceiptApiService {
  AuroraReceiptApiService(this._apiClient);

  final ApiClient _apiClient;

  /// 四动作纠偏（not_relevant/wrong/change_scope/delete）。真实生效在服务端
  /// 既有权威（引用降噪/supersede/暂停召回/撤销链）；失败如实抛出。
  Future<void> respond({
    required String type,
    required String id,
    required String action,
    String? correctedContent,
    String? reason,
    String? responseId,
  }) async {
    await _apiClient.post<void>(
      '/aurora/receipts/respond',
      data: {
        'memory_type': type,
        'memory_id': id,
        'action': action,
        if (correctedContent != null && correctedContent.trim().isNotEmpty)
          'corrected_content': correctedContent,
        if (reason != null && reason.trim().isNotEmpty) 'reason': reason,
        if (responseId != null && responseId.trim().isNotEmpty)
          'response_id': responseId,
      },
    );
  }
}

final auroraReceiptApiServiceProvider =
    Provider<AuroraReceiptApiService>(
  (ref) => AuroraReceiptApiService(ref.read(apiClientProvider)),
);
