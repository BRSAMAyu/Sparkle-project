import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/community/data/models/shared_error_models.dart';
import 'package:sparkle/features/community/data/models/squad_board_models.dart';
import 'package:sparkle/features/community/data/models/squad_models.dart';
import 'package:sparkle/features/community/data/models/study_room_models.dart';

/// D-COMM-3/4/5：冲刺小队域仓库（列表/详情/加入 + 小队榜 + 自习室 + 错题分享）。
///
/// 解析/错误语义照 house style：`unwrapList`/`unwrapMap`（兼容 {data:…} 包裹
/// 与直接对象两种格式），缺失/失败抛 [Exception] 由上层错误面呈现。
/// 自习室 enter/exit 为幂等端点（重复进入/重复退出不报错、诚实上报）。
class SquadRepository {
  SquadRepository(this._apiClient);

  final ApiClient _apiClient;

  // ---------------------------------------------------------------------------
  // D-COMM-3：小队 CRUD（mobile 侧只读列表 + 加入；创建见 createSquad）
  // ---------------------------------------------------------------------------

  /// 我的小队列表（仅冲刺周期内的小队可见）。
  Future<List<SquadListItem>> listMySquads() async {
    if (DemoDataService.isDemoMode) {
      // 演示态同走诚实空态口径：没有真实小队就不造假队。
      return const [];
    }
    final response = await _apiClient.get<dynamic>(ApiEndpoints.squads);
    final data =
        ApiResponseParser.unwrapList(response.data, action: 'listMySquads');
    return data
        .whereType<Map<String, dynamic>>()
        .map(SquadListItem.fromJson)
        .toList();
  }

  /// 小队详情（公开小队可见；私密小队非成员 403 → 错误面呈现）。
  Future<SquadInfo> getSquad(String groupId) async {
    final response =
        await _apiClient.get<dynamic>(ApiEndpoints.squadDetail(groupId));
    final payload =
        ApiResponseParser.unwrapMap(response.data, action: 'getSquad');
    return SquadInfo.fromJson(payload);
  }

  /// 创建冲刺小队（deadline 必填且须为未来；返回创建后的详情）。
  Future<SquadInfo> createSquad(SquadCreateInput input) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.squads,
      data: input.toJson(),
    );
    final payload =
        ApiResponseParser.unwrapMap(response.data, action: 'createSquad');
    return SquadInfo.fromJson(payload);
  }

  /// 加入小队（仅冲刺周期内；3-8 人上限；满员/过期为业务错误 → 上层呈现）。
  Future<void> joinSquad(String groupId) async {
    await _apiClient.post<dynamic>(ApiEndpoints.squadJoin(groupId));
  }

  // ---------------------------------------------------------------------------
  // D-COMM-4：小队榜（冲刺完成度口径）+ 共学自习室
  // ---------------------------------------------------------------------------

  /// 小队榜（rank 并列名次 1,1,3；<3 人 self_view_only=true 客户端切自我锚）。
  Future<SquadLeaderboard> getLeaderboard(String groupId) async {
    final response =
        await _apiClient.get<dynamic>(ApiEndpoints.squadLeaderboard(groupId));
    final payload = ApiResponseParser.unwrapMap(
      response.data,
      action: 'getSquadLeaderboard',
    );
    return SquadLeaderboard.fromJson(payload);
  }

  /// 小队自习室在场聚合（全体成员 + 在室/今日累计；未入场如实列 0）。
  Future<StudyRoomPresence> getPresence(String groupId) async {
    final response = await _apiClient
        .get<dynamic>(ApiEndpoints.squadStudyRoomPresence(groupId));
    final payload =
        ApiResponseParser.unwrapMap(response.data, action: 'getSquadPresence');
    return StudyRoomPresence.fromJson(payload);
  }

  /// 进入自习室（幂等：已在场则刷新心跳并返回既有会话）。
  Future<StudyRoomMyStatus> enterStudyRoom(String groupId) async {
    final response = await _apiClient
        .post<dynamic>(ApiEndpoints.squadStudyRoomEnter(groupId));
    final payload =
        ApiResponseParser.unwrapMap(response.data, action: 'enterStudyRoom');
    return StudyRoomMyStatus(
      inRoom: true,
      todayMinutes: (payload['today_minutes'] as num?)?.toInt() ?? 0,
    );
  }

  /// 退出自习室（幂等诚实：无开放会话 already_out 不报错）。
  Future<StudyRoomMyStatus> exitStudyRoom(String groupId) async {
    final response = await _apiClient
        .post<dynamic>(ApiEndpoints.squadStudyRoomExit(groupId));
    final payload =
        ApiResponseParser.unwrapMap(response.data, action: 'exitStudyRoom');
    return StudyRoomMyStatus(
      inRoom: false,
      todayMinutes: (payload['today_minutes'] as num?)?.toInt() ?? 0,
    );
  }

  /// 心跳（兜底崩溃恢复）。屏内用其诚实上报的 in_room 作本人状态查询：
  /// 不在场时绝不自动重开（显式进出为准），在场时仅刷新心跳（无副作用歧义）。
  Future<StudyRoomMyStatus> heartbeatStudyRoom(String groupId) async {
    final response = await _apiClient
        .post<dynamic>(ApiEndpoints.squadStudyRoomHeartbeat(groupId));
    final payload = ApiResponseParser.unwrapMap(
      response.data,
      action: 'heartbeatStudyRoom',
    );
    return StudyRoomMyStatus.fromJson(payload);
  }

  // ---------------------------------------------------------------------------
  // D-COMM-5：错题卡分享（只传 error_id，内容服务端取）
  // ---------------------------------------------------------------------------

  /// 小队错题分享列表（新→旧；白名单投影，无答案字段）。
  Future<SharedErrorList> listSharedErrors(String groupId) async {
    final response =
        await _apiClient.get<dynamic>(ApiEndpoints.squadSharedErrors(groupId));
    final payload = ApiResponseParser.unwrapMap(
      response.data,
      action: 'listSharedErrors',
    );
    return SharedErrorList.fromJson(payload);
  }

  /// 分享一张自己的错题到小队——**只传 error_id**（附言可空不传）。
  /// 幂等：同错题已在册则原样返回既有分享。
  Future<SharedErrorEntry> shareError(String groupId, String errorId) async {
    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.squadSharedErrors(groupId),
      data: <String, dynamic>{'error_id': errorId},
    );
    final payload =
        ApiResponseParser.unwrapMap(response.data, action: 'shareError');
    return SharedErrorEntry.fromJson(payload);
  }
}
