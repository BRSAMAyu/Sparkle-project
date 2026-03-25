import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/community/data/models/accountability_model.dart';
import 'package:sparkle/features/community/data/repositories/mock_community_repository.dart';
import 'package:sparkle/shared/entities/user_brief.dart';

final accountabilityRepositoryProvider =
    Provider<AccountabilityRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return AccountabilityRepository(apiClient);
});

class AccountabilityRepository {
  AccountabilityRepository(this._apiClient);
  final ApiClient _apiClient;

  static const _demoCurrentUserId = MockCommunityRepository.currentUserId;
  static List<AccountabilityPartnershipInfo>? _demoPartnerships;
  static Map<String, List<AccountabilityCheckinInfo>>? _demoTimelineByPartnership;

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

    final activePartnership = AccountabilityPartnershipInfo(
      id: 'demo_core_partner',
      initiatorId: _demoCurrentUserId,
      partnerId: alice.id,
      initiatorGoal: '每天同步一个主任务和一个轻复盘动作',
      partnerGoal: '每天给伙伴一句具体反馈，帮助对方稳住节奏',
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
      initiatorGoal: '一起把周末节律和复盘稳定下来',
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
          content: '上午把英语自我介绍改短了一版，顺手把你昨天说的“关键词提纲”做成了卡片。',
          mood: 5,
          minutes: 50,
          createdAt: now.subtract(const Duration(hours: 2)),
          likes: 1,
          encouragements: [
            EncouragementMessage(
              id: 'demo_encourage_1',
              userId: _demoCurrentUserId,
              message: '这条复盘很扎实，晚上我也按这个模板跟进。',
              createdAt: now.subtract(const Duration(hours: 1, minutes: 30)),
            ),
          ],
          author: alice,
        ),
        AccountabilityCheckinInfo(
          id: 'demo_checkin_me',
          partnershipId: activePartnership.id,
          userId: _demoCurrentUserId,
          content: '完成了积分换元复盘和一轮英语跟说，今天没有追求做很多，但节奏比较稳。',
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
          response.data, action: 'requestPartnership',);
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
      final index = _demoPartnerships?.indexWhere((item) => item.id == partnershipId) ?? -1;
      if (index < 0) {
        throw Exception('Demo partnership not found');
      }
      final current = _demoPartnerships![index];
      final updated = AccountabilityPartnershipInfo(
        id: current.id,
        initiatorId: current.initiatorId,
        partnerId: current.partnerId,
        initiatorGoal: current.initiatorGoal,
        partnerGoal: accept ? partnerGoal ?? current.partnerGoal : current.partnerGoal,
        checkInDays: current.checkInDays,
        slotType: current.slotType,
        status: accept ? AccountabilityStatus.active : AccountabilityStatus.ended,
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
          response.data, action: 'respondToPartnership',);
      return AccountabilityPartnershipInfo.fromJson(data);
    }
    throw Exception('Failed to respond to partnership');
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
          response.data, action: 'getMyPartnerships',);
      return data
          .map((e) =>
              AccountabilityPartnershipInfo.fromJson(e as Map<String, dynamic>),)
          .toList();
    }
    throw Exception('Failed to load partnerships');
  }

  Future<AccountabilityOverviewInfo> getOverview() async {
    if (DemoDataService.isDemoMode) {
      final partnerships = _demoActiveFirstPartnerships();
      final active = partnerships.cast<AccountabilityPartnershipInfo?>().firstWhere(
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
        leaderboardSummary: const {
          'friends': {
            'title': '好友榜',
            'my_rank': 4,
            'partner_rank': 2,
            'my_score_label': '1,280 火苗',
            'partner_score_label': '1,420 火苗',
          },
          'weekly': {
            'title': '本周进步榜',
            'my_rank': 5,
            'partner_rank': 3,
          },
          'streak': {
            'title': '连续打卡榜',
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
                'partner_name': active.partner?.displayName ?? '责任伙伴',
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
      _ensureDemoState();
      final partnership = _demoPartnerships?.firstWhere(
        (item) => item.id == partnershipId,
        orElse: () => throw Exception('Demo partnership not found'),
      );
      final demoService = DemoDataService();
      return AccountabilityDashboardInfo(
        partnership: partnership!,
        stats: _statsFromPartnership(partnership),
        timeline: [...?_demoTimelineByPartnership?[partnershipId]],
        heatmap: {
          'year': DateTime.now().year,
          'heatmap': demoService.demoAccountabilityHeatmap,
        },
        achievements: const {
          'achievements': [
            {
              'id': 'accountability_first_partnership',
              'name': '第一次并肩前进',
              'description': '成功建立第一个责任伙伴关系',
              'icon': '🤝',
              'points': 20,
              'unlocked': true,
              'partner_unlocked': true,
            },
            {
              'id': 'accountability_streak_7',
              'name': '七日共进',
              'description': '在责任伙伴关系中连续7天打卡',
              'icon': '🔥',
              'points': 50,
              'unlocked': true,
              'partner_unlocked': false,
            },
          ],
          'my_achievements': ['accountability_first_partnership', 'accountability_streak_7'],
          'partner_achievements': ['accountability_first_partnership'],
          'my_total_unlocked': 2,
          'partner_total_unlocked': 1,
        },
        leaderboardSummary: const {
          'friends': {'title': '好友榜', 'my_rank': 4, 'partner_rank': 2},
          'weekly': {'title': '本周进步榜', 'my_rank': 5, 'partner_rank': 3},
          'streak': {'title': '连续打卡榜', 'my_rank': 6, 'partner_rank': 4},
        },
        relationshipSummary: {
          'slot_type': 'core',
          'status': partnership.status.name,
          'partner_id': partnership.partnerId,
          'partner_name': partnership.partner?.displayName ?? '责任伙伴',
          'days_together': 18,
          'my_streak_days': partnership.myStreakDays ?? 0,
          'partner_streak_days': partnership.partnerStreakDays ?? 0,
          'total_checkins':
              (_demoTimelineByPartnership?[partnershipId] ?? const []).length,
          'last_checkin_at': partnership.lastCheckinAt?.toIso8601String(),
        },
        recentShares: const [
          {
            'id': 'demo_share_1',
            'resource_type': 'achievement',
            'title': '7 天连续打卡成就',
            'comment': '今晚一起把 14 天也拿下',
          },
          {
            'id': 'demo_share_2',
            'resource_type': 'plan',
            'title': '本周英语冲刺计划',
            'comment': '我把复盘节奏也塞进去了',
          },
        ],
        quickActions: {
          'can_check_in': partnership.status == AccountabilityStatus.active &&
              !(partnership.myCheckedInToday ?? false),
          'can_nudge': partnership.status == AccountabilityStatus.active,
          'can_share': partnership.status != AccountabilityStatus.ended,
          'can_chat': partnership.status != AccountabilityStatus.ended,
          'can_open_dashboard': partnership.status == AccountabilityStatus.active,
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
      _demoPartnerships = _demoPartnerships
          ?.where((item) => item.id != partnershipId)
          .toList();
      _demoTimelineByPartnership?.remove(partnershipId);
      return;
    }

    await _apiClient.delete<dynamic>(
        ApiEndpoints.accountabilityEnd(partnershipId),);
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
          _demoPartnerships?.indexWhere((item) => item.id == partnershipId) ?? -1;
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
          response.data, action: 'dailyCheckin',);
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
      return [...?_demoTimelineByPartnership?[partnershipId]].take(limit).toList();
    }

    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.accountabilityTimeline(partnershipId),
      queryParameters: {'limit': limit},
    );
    if (response.statusCode == 200) {
      final data = ApiResponseParser.unwrapList(
          response.data, action: 'getTimeline',);
      return data
          .map((e) =>
              AccountabilityCheckinInfo.fromJson(e as Map<String, dynamic>),)
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
          response.data, action: 'getHeatmap',);
    }
    throw Exception('Failed to load heatmap');
  }

  Future<Map<String, dynamic>> likeCheckin(String checkinId) async {
    if (DemoDataService.isDemoMode) {
      _ensureDemoState();
      final entries =
          _demoTimelineByPartnership?.entries.toList() ??
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
          response.data, action: 'likeCheckin',);
    }
    throw Exception('Failed to like checkin');
  }

  Future<Map<String, dynamic>> encourageCheckin(
    String checkinId,
    String message,
  ) async {
    if (DemoDataService.isDemoMode) {
      _ensureDemoState();
      final entries =
          _demoTimelineByPartnership?.entries.toList() ??
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
          response.data, action: 'encourageCheckin',);
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
            ? '已提醒伙伴：$trimmedMessage'
            : '已提醒伙伴查看今天的目标',
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

  Future<Map<String, dynamic>> getAchievements() async {
    if (DemoDataService.isDemoMode) {
      return const {
        'achievements': [
          {
            'id': 'accountability_first_partnership',
            'name': '第一次并肩前进',
            'description': '成功建立第一个责任伙伴关系',
            'icon': '🤝',
            'points': 20,
          },
          {
            'id': 'accountability_streak_7',
            'name': '七日共进',
            'description': '在责任伙伴关系中连续7天打卡',
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
          response.data, action: 'getAchievements',);
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
          response.data, action: 'getPartnershipAchievements',);
    }
    throw Exception('Failed to load partnership achievements');
  }
}
