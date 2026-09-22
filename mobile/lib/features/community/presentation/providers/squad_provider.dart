import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/community/data/models/shared_error_models.dart';
import 'package:sparkle/features/community/data/models/squad_board_models.dart';
import 'package:sparkle/features/community/data/models/squad_models.dart';
import 'package:sparkle/features/community/data/models/study_room_models.dart';
import 'package:sparkle/features/community/data/repositories/squad_repository.dart';

/// D-COMM-3/4/5：冲刺小队域 providers。
///
/// 全部只读快照面走 autoDispose（照 SelfAnchorProvider 先例：看一眼型，
/// 离开即释放、重进重取，无缓存失效协议）；参数化读取用
/// `FutureProvider.autoDispose.family`（groupId 为路径参数）。
/// 进出/分享/创建等动作为一次性调用，直接走 repository 后 invalidate
/// 相关 provider，不另设 notifier 状态机。

final squadRepositoryProvider = Provider<SquadRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return SquadRepository(apiClient);
});

/// 我的小队列表（小队列表屏 + 分享选队弹窗共用）。
final squadListProvider = FutureProvider.autoDispose<List<SquadListItem>>(
  (ref) => ref.watch(squadRepositoryProvider).listMySquads(),
);

/// 小队详情（小队详情屏头部元信息）。
final squadDetailProvider =
    FutureProvider.autoDispose.family<SquadInfo, String>(
  (ref, groupId) => ref.watch(squadRepositoryProvider).getSquad(groupId),
);

/// 小队榜（并列名次 + <3 人降级标记）。
final squadLeaderboardProvider =
    FutureProvider.autoDispose.family<SquadLeaderboard, String>(
  (ref, groupId) => ref.watch(squadRepositoryProvider).getLeaderboard(groupId),
);

/// 小队自习室在场聚合。
final squadPresenceProvider =
    FutureProvider.autoDispose.family<StudyRoomPresence, String>(
  (ref, groupId) => ref.watch(squadRepositoryProvider).getPresence(groupId),
);

/// 本人自习室状态（心跳端点的诚实上报，不在场不自动重开）。
final squadMyRoomStatusProvider =
    FutureProvider.autoDispose.family<StudyRoomMyStatus, String>(
  (ref, groupId) =>
      ref.watch(squadRepositoryProvider).heartbeatStudyRoom(groupId),
);

/// 小队错题分享列表（白名单投影，无答案字段）。
final squadSharedErrorsProvider =
    FutureProvider.autoDispose.family<SharedErrorList, String>(
  (ref, groupId) =>
      ref.watch(squadRepositoryProvider).listSharedErrors(groupId),
);
