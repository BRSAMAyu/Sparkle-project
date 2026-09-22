import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/leaderboard/data/models/self_anchor_model.dart';

/// D-COMM-1：自我 7 日锚视图仓库。
///
/// 只读单端点（`GET /leaderboards/self-anchor`）；解析/错误语义照既有惯例：
/// `unwrapMap` 取 `data`，缺失抛 [Exception]，由上层错误面呈现。
class SelfAnchorRepository {
  SelfAnchorRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<SelfAnchorView> getSelfAnchor() async {
    if (DemoDataService.isDemoMode) {
      // 演示态同走诚实空态口径：无账本数据就给真零窗口，不造假曲线。
      final today = _utcToday();
      return SelfAnchorView(
        windowStart: today.subtract(const Duration(days: 6)),
        windowEnd: today,
        series: List.generate(
          7,
          (i) => SelfAnchorDayPoint(
            date: today.subtract(Duration(days: 6 - i)),
            tasksCompleted: 0,
            masteryDelta: 0,
          ),
        ),
        totalTasksCompleted: 0,
        totalMasteryDelta: 0,
        hasAnyData: false,
      );
    }

    final response = await _apiClient
        .get<Map<String, dynamic>>(ApiEndpoints.leaderboardsSelfAnchor);
    final payload =
        ApiResponseParser.unwrapMap(response.data, action: 'getSelfAnchor');
    final data = payload['data'] as Map<String, dynamic>?;
    if (data == null) {
      throw Exception('getSelfAnchor: data field is missing');
    }
    return SelfAnchorView.fromJson(data);
  }

  static DateTime _utcToday() {
    final now = DateTime.now().toUtc();
    return DateTime.utc(now.year, now.month, now.day);
  }
}
