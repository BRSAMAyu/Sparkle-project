import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/community/data/models/accountability_model.dart';
import 'package:sparkle/features/community/data/repositories/mock_community_repository.dart';
import 'package:sparkle/shared/entities/user_brief.dart';

/// Structured error types for accountability operations.
/// These enum values are used for localization at the UI layer.
enum AccountabilityErrorType {
  requestFailed,
  operationFailed,
  partnerNudged,
  partnerNudgedWithMessage,
  notFound,
  alreadyCheckedIn,
}

/// Thrown when accountability operations fail.
class AccountabilityException implements Exception {
  AccountabilityException(this.type, [this.detail]);
  final AccountabilityErrorType type;
  final String? detail;

  @override
  String toString() => 'AccountabilityException($type, $detail)';
}

final accountabilityRepositoryProvider =
    Provider<AccountabilityRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return AccountabilityRepository(apiClient);
});

class AccountabilityRepository {
  AccountabilityRepository(this._apiClient);
  final ApiClient _apiClient;

  String _extractApiErrorString(Object error, {String? fallback}) {
    if (error is DioException) {
      final data = error.response?.data;
      if (data is Map<String, dynamic>) {
        final detail = data['detail']?.toString().trim();
        if (detail != null && detail.isNotEmpty) {
          return detail;
        }
        final message = data['message']?.toString().trim();
        if (message != null && message.isNotEmpty) {
          return message;
        }
        final err = data['error']?.toString().trim();
        if (err != null && err.isNotEmpty) {
          return err;
        }
      }
      if (error.message != null && error.message!.trim().isNotEmpty) {
        return error.message!.trim();
      }
    }
    return fallback ?? '';
  }

  AccountabilityException _toException(Object error, AccountabilityErrorType type) {
    final detail = _extractApiErrorString(error);
    return detail.isNotEmpty ? AccountabilityException(type, detail) : AccountabilityException(type);
  }

  static const _demoCurrentUserId = MockCommunityRepository.currentUserId;
  static List<AccountabilityPartnershipInfo>? _demoPartnerships;
  static Map<String, List<AccountabilityCheckinInfo>>?
      _demoTimelineByPartnership;

  static void _ensureDemoState() {
    if (_demoPartnerships != null && _demoTimelineByPartnership != null) {
      return;
    }

    final now = DateTime.now();
    final alice = UserBrief(
      id: 'user_alice',
      username: 'Lena',
      nickname: 'Lena',
      flameLevel: 8,
    );
    final charlie = UserBrief(
      id: 'user_charlie',
      username: 'Nora',
      nickname: 'Nora',
      flameLevel: 12,
    );
    final me = UserBrief(
      id: _demoCurrentUserId,
      username: 'AI_Learner_02',
      nickname: 'Mika',
      flameLevel: 15,
    );

    final zh = I18nService.instance.isChinese;
    final activePartnership = AccountabilityPartnershipInfo(
      id: 'demo_core_partner',
      initiatorId: _demoCurrentUserId,
      partnerId: alice.id,
      initiatorGoal: zh ? '每天同步一个主任务和一个轻复盘动作' : 'Sync one main task and a quick reflection each day',
      partnerGoal: zh ? '每天给伙伴一句具体反馈，帮助对方稳住节奏' : 'Give your partner specific feedback daily to help them stay on track',
      checkInDays: 1,
      status: AccountabilityStatus.active,
      createdAt: now.subtract(const Duration(days: 18)),
      startedAt: now.subtract(const Duration(days: 18)),
      initiator: me,
      partner: alice,
      myStreakDays: 7,
      partnerStreakDays: 5,
      myCheckedInToday: false,
      partnerCheckedInToday: true,
      lastCheckinAt: now.subtract(const Duration(hours: 2)),
    );
    final pendingPartnership = AccountabilityPartnershipInfo(
      id: 'demo_pending_partner',
      initiatorId: charlie.id,
      partnerId: _demoCurrentUserId,
      initiatorGoal: zh ? '一起把周末节律和复盘稳定下来' : 'Let\'s stabilize weekend routines and reflections together',
      checkInDays: 2,
      status: AccountabilityStatus.pending,
      createdAt: now.subtract(const Duration(days: 1)),
      initiator: charlie,
      partner: me,
    );

    _demoPartnerships = [activePartnership, pendingPartnership];
    _demoTimelineByPartnership = {
      activePartnership.id: [
        AccountabilityCheckinInfo(
          id: 'demo_checkin_partner',
          partnershipId: activePartnership.id,
          userId: alice.id,
          content: zh ? '上午把英语自我介绍改短了一版，顺手把你昨天说的”关键词提纲”做成了卡片。' : 'Shortened the English self-intro this morning, and turned your “keyword outline” into cards.',
          mood: 5,
          minutes: 50,
          createdAt: now.subtract(const Duration(hours: 2)),
          likes: 1,
          encouragements: [
            EncouragementMessage(
              id: 'demo_encourage_1',
              userId: _demoCurrentUserId,
              message: zh ? '这条复盘很扎实，晚上我也按这个模板跟进。' : 'Solid reflection — I\'ll follow the same template tonight.',
              createdAt: now.subtract(const Duration(hours: 1, minutes: 30)),
            ),
          ],
          author: alice,
        ),
        AccountabilityCheckinInfo(
          id: 'demo_checkin_me',
          partnershipId: activePartnership.id,
          userId: _demoCurrentUserId,
          content: zh ? '完成了积分换元复盘和一轮英语跟说，今天没有追求做很多，但节奏比较稳。' : 'Finished integration review and one round of English speaking. Didn\'t push for volume today, but the rhythm felt solid.',
          mood: 4,
          minutes: 65,
          createdAt: now.subtract(const Duration(hours: 5)),
          likes: 2,
          author: me,
        ),
      ],
      pendingPartnership.id: const [],
    };
  }

  List<AccountabilityPartnershipInfo> _demoActiveFirstPartnerships() {
    _ensureDemoState();
    return [...?_demoPartnerships]..sort((a, b) {
        int priority(AccountabilityPartnershipInfo item) {
          switch (item.status) {
            case AccountabilityStatus.active:
              return 0;
            case AccountabilityStatus.pending:
              return 1;
            case AccountabilityStatus.paused:
              return 2;
            case AccountabilityStatus.ended:
              return 3;
          }
        }

        final priorityCompare = priority(a).compareTo(priority(b));
        if (priorityCompare != 0) return priorityCompare;
        return b.createdAt.compareTo(a.createdAt);
      });
  }

  AccountabilityStatsInfo _statsFromPartnership(
    AccountabilityPartnershipInfo partnership,
  ) {
    final timeline = _demoTimelineByPartnership?[partnership.id] ?? const [];
    return AccountabilityStatsInfo(
      myStreakDays: partnership.myStreakDays ?? 0,
      partnerStreakDays: partnership.partnerStreakDays ?? 0,
      myCheckedInToday: partnership.myCheckedInToday ?? false,
      partnerCheckedInToday: partnership.partnerCheckedInToday ?? false,
      totalCheckins: timeline.length,
    );
  }

  Future<AccountabilityPartnershipInfo> requestPartnership({
    required String partnerId,
    required String initiatorGoal,
    int checkInDays = 1,
  }) async {
    if (DemoDataService.isDemoMode) {
      _ensureDemoState();
      final partnership = AccountabilityPartnershipInfo(
        id: 'demo_requested_$partnerId',
        initiatorId: _demoCurrentUserId,
        partnerId: partnerId,
        initiatorGoal: initiatorGoal,
        checkInDays: checkInDays,
        status: AccountabilityStatus.pending,
        createdAt: DateTime.now(),
      );
      _demoPartnerships = [
        partnership,
        ...?_demoPartnerships
            ?.where((item) => item.status != AccountabilityStatus.pending),
      ];
      _demoTimelineByPartnership?[partnership.id] = const [];
      return partnership;
    }

    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.accountabilityRequest,
      data: {
        'partner_id': partnerId,
        'initiator_goal': initiatorGoal,
        'check_in_days': checkInDays,
      },
    );
    if (response.statusCode == 201) {
      final data = ApiResponseParser.unwrapMap(
        response.data,
        action: 'requestPartnership',
      );
      return AccountabilityPartnershipInfo.fromJson(data);
    }
    throw Exception('Failed to request partnership');
  }

  Future<AccountabilityPartnershipInfo> respondToPartnership(
    String partnershipId, {
    required bool accept,
    String? partnerGoal,
  }) async {
    if (DemoDataService.isDemoMode) {
      _ensureDemoState();
      final index =
          _demoPartnerships?.indexWhere((item) => item.id == partnershipId) ??
              -1;
      if (index < 0) {
        throw Exception('Demo partnership not found');
      }
      final current = _demoPartnerships![index];
      final updated = AccountabilityPartnershipInfo(
        id: current.id,
        initiatorId: current.initiatorId,
        partnerId: current.partnerId,
        initiatorGoal: current.initiatorGoal,
        partnerGoal:
            accept ? partnerGoal ?? current.partnerGoal : current.partnerGoal,
        checkInDays: current.checkInDays,
        slotType: current.slotType,
        status:
            accept ? AccountabilityStatus.active : AccountabilityStatus.ended,
        createdAt: current.createdAt,
        startedAt: accept ? DateTime.now() : current.startedAt,
        endedAt: accept ? null : DateTime.now(),
        initiator: current.initiator,
        partner: current.partner,
        myStreakDays: accept ? 0 : current.myStreakDays,
        partnerStreakDays: accept ? 0 : current.partnerStreakDays,
        myCheckedInToday: accept ? false : current.myCheckedInToday,
        partnerCheckedInToday: accept ? false : current.partnerCheckedInToday,
      );
      _demoPartnerships![index] = updated;
      return updated;
    }

    try {
      final response = await _apiClient.post<dynamic>(
        ApiEndpoints.accountabilityRespond(partnershipId),
        data: {
          'accept': accept,
          if (partnerGoal != null && partnerGoal.isNotEmpty)
            'partner_goal': partnerGoal,
        },
      );
      if (response.statusCode == 200) {
        final data = ApiResponseParser.unwrapMap(
          response.data,
          action: 'respondToPartnership',
        );
        return AccountabilityPartnershipInfo.fromJson(data);
      }
      throw AccountabilityException(AccountabilityErrorType.operationFailed);
    } on DioException catch (error) {
      throw _toException(error, AccountabilityErrorType.operationFailed);
    }
  }

  Future<List<AccountabilityPartnershipInfo>> getMyPartnerships() async {
    if (DemoDataService.isDemoMode) {
      return _demoActiveFirstPartnerships()
          .where((item) => item.status != AccountabilityStatus.ended)
          .toList();
    }

    final response =
        await _apiClient.get<dynamic>(ApiEndpoints.accountabilityMine);
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(
        response.data,
        action: 'getMyPartnerships',
      );
      return data
          .map(
            (e) => AccountabilityPartnershipInfo.fromJson(
                e as Map<String, dynamic>,),
          )
          .toList();
    }
    throw Exception('Failed to load partnerships');
  }

  Future<AccountabilityOverviewInfo> getOverview() async {
    if (DemoDataService.isDemoMode) {
      final zh = I18nService.instance.isChinese;
      final partnerships = _demoActiveFirstPartnerships();
      final active =
          partnerships.cast<AccountabilityPartnershipInfo?>().firstWhere(
                (item) => item?.status == AccountabilityStatus.active,
                orElse: () => null,
              );
      final pending = partnerships
          .where((item) => item.status == AccountabilityStatus.pending)
          .toList();
      return AccountabilityOverviewInfo(
        slotType: 'core',
        activePartnership: active,
        pendingPartnerships: pending,
        achievementsSummary: const {
          'total_unlocked': 2,
          'partner_total_unlocked': 1,
        },
        leaderboardSummary: {
          'friends': {
            'title': zh ? '好友榜' : 'Friends',
            'my_rank': 4,
            'partner_rank': 2,
            'my_score_label': zh ? '1,280 火苗' : '1,280 Sparks',
            'partner_score_label': zh ? '1,420 火苗' : '1,420 Sparks',
          },
          'weekly': {
            'title': zh ? '本周进步榜' : 'Weekly Progress',
            'my_rank': 5,
            'partner_rank': 3,
          },
          'streak': {
            'title': zh ? '连续打卡榜' : 'Streak Board',
            'my_rank': 6,
            'partner_rank': 4,
          },
        },
        relationshipSummary: active == null
            ? null
            : {
                'slot_type': 'core',
                'status': 'active',
                'partner_id': active.partnerId,
                'partner_name': active.partner?.displayName ?? (zh ? '责任伙伴' : 'Accountability Partner'),
                'days_together': 18,
                'my_streak_days': active.myStreakDays ?? 0,
                'partner_streak_days': active.partnerStreakDays ?? 0,
                'total_checkins':
                    (_demoTimelineByPartnership?[active.id] ?? const []).length,
                'last_checkin_at': active.lastCheckinAt?.toIso8601String(),
              },
        quickActions: {
          'can_check_in': active != null && !(active.myCheckedInToday ?? false),
          'can_nudge': active != null,
          'can_share': active != null,
          'can_chat': active != null,
          'can_open_dashboard': active != null,
        },
        inAppHints: active == null
            ? const []
            : [
                AccountabilityInAppHintInfo(
                  id: 'demo_hint_partner_watch',
                  message: '${active.partner?.displayName ?? (zh ? '责任伙伴' : 'Accountability Partner')} ${zh ? '正在看着你，加油' : 'is watching — keep going!'}',
                  senderName: active.partner?.displayName ?? (zh ? '责任伙伴' : 'Accountability Partner'),
                  senderId: active.partnerId,
                  partnershipId: active.id,
                  createdAt:
                      DateTime.now().subtract(const Duration(minutes: 18)),
                ),
              ],
      );
    }

    final response =
        await _apiClient.get<dynamic>(ApiEndpoints.accountabilityOverview);
    if (response.statusCode == 200) {
      final data =
          ApiResponseParser.unwrapMap(response.data, action: 'getOverview');
      return AccountabilityOverviewInfo.fromJson(data);
    }
    throw Exception('Failed to load accountability overview');
  }

  Future<AccountabilityDashboardInfo> getDashboard(String partnershipId) async {
    if (DemoDataService.isDemoMode) {
      final zh = I18nService.instance.isChinese;
      _ensureDemoState();
      final partnership = _demoPartnerships?.firstWhere(
        (item) => item.id == partnershipId,
        orElse: () => throw Exception('Demo partnership not found'),
      );
      final demoService = DemoDataService();
      return AccountabilityDashboardInfo(
        partnership: partnership!,
        stats: _statsFromPartnership(partnership),
        pendingPolicies: PendingPoliciesSummaryInfo(
          count: partnership.status == AccountabilityStatus.active ? 3 : 0,
          nextTriggerAt: partnership.status == AccountabilityStatus.active
              ? DateTime.now().add(const Duration(hours: 12))
              : null,
          policyIds: partnership.status == AccountabilityStatus.active
              ? const ['demo-policy-1', 'demo-policy-2', 'demo-policy-3']
              : const <String>[],
        ),
        recentReflections: RecentReflectionsSummaryInfo(
          count: partnership.status == AccountabilityStatus.active ? 2 : 0,
          lastCategory: partnership.status == AccountabilityStatus.active
              ? 'plan_stall'
              : null,
          lastAt: partnership.status == AccountabilityStatus.active
              ? DateTime.now().subtract(const Duration(hours: 6))
              : null,
        ),
        timeline: [...?_demoTimelineByPartnership?[partnershipId]],
        heatmap: {
          'year': DateTime.now().year,
          'heatmap': demoService.demoAccountabilityHeatmap,
        },
        achievements: {
          'achievements': [
            {
              'id': 'accountability_first_partnership',
              'name': zh ? '第一次并肩前进' : 'First Side by Side',
              'description': zh ? '成功建立第一个责任伙伴关系' : 'Successfully established your first accountability partnership',
              'icon': '🤝',
              'points': 20,
              'unlocked': true,
              'partner_unlocked': true,
            },
            {
              'id': 'accountability_streak_7',
              'name': zh ? '七日共进' : '7-Day Streak Together',
              'description': zh ? '在责任伙伴关系中连续7天打卡' : 'Check in for 7 consecutive days in a partnership',
              'icon': '🔥',
              'points': 50,
              'unlocked': true,
              'partner_unlocked': false,
            },
          ],
          'my_achievements': [
            'accountability_first_partnership',
            'accountability_streak_7',
          ],
          'partner_achievements': ['accountability_first_partnership'],
          'my_total_unlocked': 2,
          'partner_total_unlocked': 1,
        },
        leaderboardSummary: {
          'friends': {'title': zh ? '好友榜' : 'Friends', 'my_rank': 4, 'partner_rank': 2},
          'weekly': {'title': zh ? '本周进步榜' : 'Weekly Progress', 'my_rank': 5, 'partner_rank': 3},
          'streak': {'title': zh ? '连续打卡榜' : 'Streak Board', 'my_rank': 6, 'partner_rank': 4},
        },
        relationshipSummary: {
          'slot_type': 'core',
          'status': partnership.status.name,
          'partner_id': partnership.partnerId,
          'partner_name': partnership.partner?.displayName ?? (zh ? '责任伙伴' : 'Accountability Partner'),
          'days_together': 18,
          'my_streak_days': partnership.myStreakDays ?? 0,
          'partner_streak_days': partnership.partnerStreakDays ?? 0,
          'total_checkins':
              (_demoTimelineByPartnership?[partnershipId] ?? const []).length,
          'last_checkin_at': partnership.lastCheckinAt?.toIso8601String(),
        },
        recentShares: [
          {
            'id': 'demo_share_1',
            'resource_type': 'achievement',
            'title': zh ? '7 天连续打卡成就' : '7-Day Check-in Streak',
            'comment': zh ? '今晚一起把 14 天也拿下' : 'Let\'s hit 14 days tonight',
          },
          {
            'id': 'demo_share_2',
            'resource_type': 'plan',
            'title': zh ? '本周英语冲刺计划' : 'This Week\'s English Sprint Plan',
            'comment': zh ? '我把复盘节奏也塞进去了' : 'I added reflection rhythm into it too',
          },
        ],
        quickActions: {
          'can_check_in': partnership.status == AccountabilityStatus.active &&
              !(partnership.myCheckedInToday ?? false),
          'can_nudge': partnership.status == AccountabilityStatus.active,
          'can_share': partnership.status != AccountabilityStatus.ended,
          'can_chat': partnership.status != AccountabilityStatus.ended,
          'can_open_dashboard':
              partnership.status == AccountabilityStatus.active,
        },
      );
    }

    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.accountabilityDashboard(partnershipId),
    );
    if (response.statusCode == 200) {
      final data =
          ApiResponseParser.unwrapMap(response.data, action: 'getDashboard');
      return AccountabilityDashboardInfo.fromJson(data);
    }
    throw Exception('Failed to load accountability dashboard');
  }

  Future<void> endPartnership(String partnershipId) async {
    if (DemoDataService.isDemoMode) {
      _ensureDemoState();
      _demoPartnerships =
          _demoPartnerships?.where((item) => item.id != partnershipId).toList();
      _demoTimelineByPartnership?.remove(partnershipId);
      return;
    }

    await _apiClient.delete<dynamic>(
      ApiEndpoints.accountabilityEnd(partnershipId),
    );
  }

  Future<AccountabilityCheckinInfo> dailyCheckin(
    String partnershipId, {
    required String content,
    required int mood,
    required int minutes,
  }) async {
    if (DemoDataService.isDemoMode) {
      _ensureDemoState();
      final partnershipIndex =
          _demoPartnerships?.indexWhere((item) => item.id == partnershipId) ??
              -1;
      if (partnershipIndex < 0) {
        throw Exception('Demo partnership not found');
      }
      final partnership = _demoPartnerships![partnershipIndex];
      if (partnership.myCheckedInToday ?? false) {
        throw Exception('You have already checked in today');
      }
      final now = DateTime.now();
      final checkin = AccountabilityCheckinInfo(
        id: 'demo_checkin_${now.millisecondsSinceEpoch}',
        partnershipId: partnershipId,
        userId: _demoCurrentUserId,
        content: content,
        mood: mood,
        minutes: minutes,
        createdAt: now,
        author: partnership.initiator,
      );
      _demoTimelineByPartnership?[partnershipId] = [
        checkin,
        ...?_demoTimelineByPartnership?[partnershipId],
      ];
      _demoPartnerships![partnershipIndex] = partnership.copyWithStats(
        myStreakDays: (partnership.myStreakDays ?? 0) + 1,
        partnerStreakDays: partnership.partnerStreakDays,
        myCheckedInToday: true,
        partnerCheckedInToday: partnership.partnerCheckedInToday,
        lastCheckinAt: now,
      );
      return checkin;
    }

    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.accountabilityCheckin(partnershipId),
      data: {
        'content': content,
        'mood': mood,
        'minutes': minutes,
      },
    );
    if (response.statusCode == 201) {
      final data = ApiResponseParser.unwrapMap(
        response.data,
        action: 'dailyCheckin',
      );
      return AccountabilityCheckinInfo.fromJson(data);
    }
    throw Exception('Failed to check in');
  }

  Future<AccountabilityStatsInfo> getStats(String partnershipId) async {
    if (DemoDataService.isDemoMode) {
      _ensureDemoState();
      final partnership = _demoPartnerships?.firstWhere(
        (item) => item.id == partnershipId,
        orElse: () => throw Exception('Demo partnership not found'),
      );
      return _statsFromPartnership(partnership!);
    }

    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.accountabilityStats(partnershipId),
    );
    if (response.statusCode == 200) {
      final data =
          ApiResponseParser.unwrapMap(response.data, action: 'getStats');
      return AccountabilityStatsInfo.fromJson(data);
    }
    throw Exception('Failed to load stats');
  }

  Future<List<AccountabilityCheckinInfo>> getTimeline(
    String partnershipId, {
    int limit = 30,
  }) async {
    if (DemoDataService.isDemoMode) {
      _ensureDemoState();
      return [...?_demoTimelineByPartnership?[partnershipId]]
          .take(limit)
          .toList();
    }

    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.accountabilityTimeline(partnershipId),
      queryParameters: {'limit': limit},
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(
        response.data,
        action: 'getTimeline',
      );
      return data
          .map(
            (e) =>
                AccountabilityCheckinInfo.fromJson(e as Map<String, dynamic>),
          )
          .toList();
    }
    throw Exception('Failed to load timeline');
  }

  Future<Map<String, dynamic>> getHeatmap(
    String partnershipId, {
    int? year,
  }) async {
    if (DemoDataService.isDemoMode) {
      return {
        'year': DateTime.now().year,
        'heatmap': DemoDataService().demoAccountabilityHeatmap,
      };
    }

    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.accountabilityHeatmap(partnershipId),
      queryParameters: year != null ? {'year': year} : null,
    );
    if (response.statusCode == 200) {
      return ApiResponseParser.unwrapMap(
        response.data,
        action: 'getHeatmap',
      );
    }
    throw Exception('Failed to load heatmap');
  }

  Future<Map<String, dynamic>> likeCheckin(String checkinId) async {
    if (DemoDataService.isDemoMode) {
      _ensureDemoState();
      final entries = _demoTimelineByPartnership?.entries.toList() ??
          <MapEntry<String, List<AccountabilityCheckinInfo>>>[];
      for (final entry in entries) {
        final index = entry.value.indexWhere((item) => item.id == checkinId);
        if (index >= 0) {
          final current = entry.value[index];
          entry.value[index] = AccountabilityCheckinInfo(
            id: current.id,
            partnershipId: current.partnershipId,
            userId: current.userId,
            content: current.content,
            mood: current.mood,
            minutes: current.minutes,
            createdAt: current.createdAt,
            likes: current.likes + 1,
            encouragements: current.encouragements,
            author: current.author,
          );
          return {'likes': entry.value[index].likes};
        }
      }
      throw Exception('Demo checkin not found');
    }

    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.accountabilityCheckinLike(checkinId),
    );
    if (response.statusCode == 200) {
      return ApiResponseParser.unwrapMap(
        response.data,
        action: 'likeCheckin',
      );
    }
    throw Exception('Failed to like checkin');
  }

  Future<Map<String, dynamic>> encourageCheckin(
    String checkinId,
    String message,
  ) async {
    if (DemoDataService.isDemoMode) {
      _ensureDemoState();
      final entries = _demoTimelineByPartnership?.entries.toList() ??
          <MapEntry<String, List<AccountabilityCheckinInfo>>>[];
      for (final entry in entries) {
        final index = entry.value.indexWhere((item) => item.id == checkinId);
        if (index >= 0) {
          final current = entry.value[index];
          final encouragement = EncouragementMessage(
            id: 'demo_encourage_${DateTime.now().millisecondsSinceEpoch}',
            userId: _demoCurrentUserId,
            message: message,
            createdAt: DateTime.now(),
          );
          entry.value[index] = AccountabilityCheckinInfo(
            id: current.id,
            partnershipId: current.partnershipId,
            userId: current.userId,
            content: current.content,
            mood: current.mood,
            minutes: current.minutes,
            createdAt: current.createdAt,
            likes: current.likes,
            encouragements: [...current.encouragements, encouragement],
            author: current.author,
          );
          return {
            'encouragement': {
              'id': encouragement.id,
              'user_id': encouragement.userId,
              'message': encouragement.message,
              'created_at': encouragement.createdAt.toIso8601String(),
            },
          };
        }
      }
      throw Exception('Demo checkin not found');
    }

    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.accountabilityCheckinEncourage(checkinId),
      data: {'message': message},
    );
    if (response.statusCode == 200) {
      return ApiResponseParser.unwrapMap(
        response.data,
        action: 'encourageCheckin',
      );
    }
    throw Exception('Failed to send encouragement');
  }

  Future<Map<String, dynamic>> nudgePartner(
    String partnershipId, {
    String? message,
  }) async {
    if (DemoDataService.isDemoMode) {
      final trimmedMessage = message?.trim();
      return {
        'success': true,
        'partnership_id': partnershipId,
        'partner_id': 'user_alice',
        'cooldown_seconds': 7200,
        'message': trimmedMessage?.isNotEmpty ?? false
            ? (I18nService.instance.isChinese ? '已提醒伙伴：$trimmedMessage' : 'Partner nudged: $trimmedMessage')
            : (I18nService.instance.isChinese ? '已提醒伙伴查看今天的目标' : 'Partner nudged to check today\'s goals'),
      };
    }

    final response = await _apiClient.post<dynamic>(
      ApiEndpoints.accountabilityNudge(partnershipId),
      data: {
        if (message != null && message.trim().isNotEmpty) 'message': message,
      },
    );
    if (response.statusCode == 200) {
      return ApiResponseParser.unwrapMap(
        response.data,
        action: 'nudgePartner',
      );
    }
    throw Exception('Failed to nudge partner');
  }

  Future<void> dismissInAppHint(String notificationId) async {
    if (DemoDataService.isDemoMode) {
      return;
    }

    await _apiClient.post<dynamic>(
      ApiEndpoints.accountabilityHintDismiss(notificationId),
    );
  }

  Future<Map<String, dynamic>> getAchievements() async {
    if (DemoDataService.isDemoMode) {
      final zh = I18nService.instance.isChinese;
      return {
        'achievements': [
          {
            'id': 'accountability_first_partnership',
            'name': zh ? '第一次并肩前进' : 'First Side by Side',
            'description': zh ? '成功建立第一个责任伙伴关系' : 'Successfully established your first accountability partnership',
            'icon': '🤝',
            'points': 20,
          },
          {
            'id': 'accountability_streak_7',
            'name': zh ? '七日共进' : '7-Day Streak Together',
            'description': zh ? '在责任伙伴关系中连续7天打卡' : 'Check in for 7 consecutive days in a partnership',
            'icon': '🔥',
            'points': 50,
          },
        ],
        'total_available': 2,
      };
    }

    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.accountabilityAchievements,
    );
    if (response.statusCode == 200) {
      return ApiResponseParser.unwrapMap(
        response.data,
        action: 'getAchievements',
      );
    }
    throw Exception('Failed to load achievements');
  }

  Future<Map<String, dynamic>> getPartnershipAchievements(
    String partnershipId,
  ) async {
    if (DemoDataService.isDemoMode) {
      return const {
        'my_achievements': [
          'accountability_first_partnership',
          'accountability_streak_7',
        ],
        'partner_achievements': ['accountability_first_partnership'],
      };
    }

    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.accountabilityPartnershipAchievements(partnershipId),
    );
    if (response.statusCode == 200) {
      return ApiResponseParser.unwrapMap(
        response.data,
        action: 'getPartnershipAchievements',
      );
    }
    throw Exception('Failed to load partnership achievements');
  }
}
