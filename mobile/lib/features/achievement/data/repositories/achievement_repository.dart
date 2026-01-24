import 'package:dio/dio.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';
import 'package:sparkle/shared/models/api_response_model.dart';

/// Achievement Repository
/// 成就数据仓库
class AchievementRepository {
  AchievementRepository(this._apiClient);
  final ApiClient _apiClient;

  /// Handle Dio exceptions
  T _handleDioError<T>(DioException e, String functionName) {
    final errorMessage = e.response?.data?['detail'] ??
        'An unknown error occurred in $functionName';
    throw Exception(errorMessage);
  }

  Map<String, dynamic> _unwrapResponseMap(dynamic data, {String? action}) {
    if (data is Map<String, dynamic>) {
      return data;
    }
    if (data == null) {
      throw Exception('${action ?? "Operation"} response is empty');
    }
    throw Exception('Unexpected response format');
  }

  List<dynamic> _unwrapResponseList(dynamic data) {
    if (data is List) {
      return data;
    }
    if (data is Map<String, dynamic>) {
      final listData = data['data'];
      if (listData is List) {
        return listData;
      }
    }
    throw Exception('Unexpected response format, expected List');
  }

  /// Get achievements list
  Future<AchievementListResponse> getAchievements({
    String? category,
    AchievementRarity? rarity,
    bool includeHidden = false,
  }) async {
    if (DemoDataService.isDemoMode) {
      // Return demo achievements
      return _getDemoAchievements();
    }

    try {
      final queryParams = <String, dynamic>{
        if (category != null) 'category': category,
        if (rarity != null) 'rarity': rarity.name,
        'include_hidden': includeHidden,
      };

      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.achievements,
        queryParameters: queryParams,
      );

      final payload = response.data;
      if (payload == null) {
        throw Exception('getAchievements response is empty');
      }

      final dataList = payload['data'] as List<dynamic>?;
      if (dataList == null) {
        return AchievementListResponse(
          achievements: [],
          totalAchievements: 0,
          totalUnlocked: 0,
          categories: const {},
        );
      }

      final achievements = dataList
          .map((json) => AchievementWithProgress.fromJson(
              json as Map<String, dynamic>,),)
          .toList();

      final meta = payload['meta'] as Map<String, dynamic>? ?? {};

      return AchievementListResponse(
        achievements: achievements,
        totalAchievements: (meta['total_achievements'] as int?) ?? achievements.length,
        totalUnlocked: (meta['total_unlocked'] as int?) ?? 0,
        categories: Map<String, dynamic>.from(
          meta['categories'] as Map? ?? {},
        ),
      );
    } on DioException catch (e) {
      return _handleDioError(e, 'getAchievements');
    }
  }

  /// Get achievement statistics
  Future<AchievementStats> getAchievementStats() async {
    if (DemoDataService.isDemoMode) {
      return AchievementStats(
        totalAchievements: 50,
        unlockedCount: 12,
        unlockedPercentage: 24.0,
        commonCount: 8,
        rareCount: 3,
        epicCount: 1,
        legendaryCount: 0,
        hiddenFound: 1,
        currentStreak: 7,
        totalPhotons: 500,
      );
    }

    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.achievementsStats,
      );

      final payload = _unwrapResponseMap(response.data, action: 'getAchievementStats');
      return AchievementStats.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, 'getAchievementStats');
    }
  }

  /// Get achievement map
  Future<AchievementMapData> getAchievementMap() async {
    if (DemoDataService.isDemoMode) {
      return _getDemoAchievementMap();
    }

    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.achievementsMap,
      );

      final payload = _unwrapResponseMap(response.data, action: 'getAchievementMap');
      return AchievementMapData.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, 'getAchievementMap');
    }
  }

  /// Get streak statistics
  Future<StreakStats> getStreakStats() async {
    if (DemoDataService.isDemoMode) {
      return StreakStats(
        currentStreak: 7,
        maxStreak: 30,
        longestStreak: 30,
        lastActivityDate: DateTime.now(),
        freezeCharges: 2,
        maxFreezeCharges: 3,
        totalCheckinDays: 45,
        longestStreakStart: DateTime.now().subtract(const Duration(days: 30)),
        longestStreakEnd: DateTime.now(),
      );
    }

    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.achievementsStreak,
      );

      final payload = _unwrapResponseMap(response.data, action: 'getStreakStats');
      return StreakStats.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, 'getStreakStats');
    }
  }

  /// Get contract status
  Future<SparkContract?> getContractStatus() async {
    if (DemoDataService.isDemoMode) {
      return null; // No active contract in demo mode
    }

    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.contractsStatus,
      );

      final payload = _unwrapResponseMap(response.data, action: 'getContractStatus');
      if (payload['has_active_contract'] == false) {
        return null;
      }

      final contractData = payload['contract'] as Map<String, dynamic>?;
      if (contractData == null) return null;

      return SparkContract.fromJson(contractData);
    } on DioException catch (e) {
      return _handleDioError(e, 'getContractStatus');
    }
  }

  /// Create contract
  Future<SparkContract> createContract({
    required int targetStudyMinutes,
    required int targetDays,
    required int photonStake,
  }) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.contracts,
        data: {
          'target_study_minutes': targetStudyMinutes,
          'target_days': targetDays,
          'photon_stake': photonStake,
        },
      );

      final payload = _unwrapResponseMap(response.data, action: 'createContract');
      final contractData = payload['data'] as Map<String, dynamic>?;
      if (contractData == null) {
        throw Exception('createContract: data is null');
      }

      return SparkContract.fromJson(contractData);
    } on DioException catch (e) {
      return _handleDioError(e, 'createContract');
    }
  }

  /// Cancel contract
  Future<bool> cancelContract() async {
    try {
      await _apiClient.delete<Map<String, dynamic>>(
        ApiEndpoints.contracts,
      );
      return true;
    } on DioException catch (e) {
      return _handleDioError(e, 'cancelContract');
    }
  }

  /// Get galaxy skins
  Future<GalaxySkinListResponse> getGalaxySkins() async {
    if (DemoDataService.isDemoMode) {
      return _getDemoGalaxySkins();
    }

    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.galaxySkins,
      );

      final payload = _unwrapResponseMap(response.data, action: 'getGalaxySkins');
      final dataList = payload['data'] as List<dynamic>?;

      final skins = dataList?.map((json) => GalaxySkin.fromJson(
        json as Map<String, dynamic>,
      ),).toList() ?? [];

      return GalaxySkinListResponse(
        skins: skins,
        equippedSkinId: payload['equipped_skin_id'] as String?,
      );
    } on DioException catch (e) {
      return _handleDioError(e, 'getGalaxySkins');
    }
  }

  /// Equip galaxy skin
  Future<bool> equipGalaxySkin(String skinId) async {
    try {
      await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.skinEquip(skinId),
      );
      return true;
    } on DioException catch (e) {
      return _handleDioError(e, 'equipGalaxySkin');
    }
  }

  /// Get user titles
  Future<List<UserTitle>> getTitles() async {
    if (DemoDataService.isDemoMode) {
      return _getDemoTitles();
    }

    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.titles,
      );

      final payload = _unwrapResponseMap(response.data, action: 'getTitles');
      final dataList = payload['data'] as List<dynamic>?;

      return dataList?.map((json) => UserTitle.fromJson(
        json as Map<String, dynamic>,
      ),).toList() ?? [];
    } on DioException catch (e) {
      return _handleDioError(e, 'getTitles');
    }
  }

  /// Equip title
  Future<bool> equipTitle(String titleId) async {
    try {
      await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.titleEquip(titleId),
      );
      return true;
    } on DioException catch (e) {
      return _handleDioError(e, 'equipTitle');
    }
  }

  /// Pin/Unpin achievement
  Future<bool> pinAchievement(String achievementId, bool pinned) async {
    try {
      await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.achievementPin(achievementId),
        queryParameters: {'pinned': pinned},
      );
      return true;
    } on DioException catch (e) {
      return _handleDioError(e, 'pinAchievement');
    }
  }

  /// Process achievement event (internal)
  Future<List<AchievementUnlockEvent>> processEvent({
    required String eventType,
    Map<String, dynamic>? eventData,
  }) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.achievementEventsProcess,
        queryParameters: {'event_type': eventType},
        data: eventData,
      );

      final payload = _unwrapResponseMap(response.data, action: 'processEvent');
      final unlockedList = payload['unlocked'] as List<dynamic>?;

      return unlockedList?.map((json) => AchievementUnlockEvent.fromJson(
        json as Map<String, dynamic>,
      ),).toList() ?? [];
    } on DioException catch (e) {
      return _handleDioError(e, 'processEvent');
    }
  }

  // ========== Demo Data ==========

  AchievementListResponse _getDemoAchievements() => AchievementListResponse(
      achievements: [
        AchievementWithProgress(
          achievement: AchievementModel(
            id: 'streak_7',
            name: '一周坚持',
            description: '连续学习7天',
            iconUrl: '/icons/streak_7.png',
            type: AchievementType.streak,
            rarity: AchievementRarity.common,
            category: 'streak',
            triggerCode: 'STREAK_DAYS',
            triggerConfig: {'days': 7},
            createdAt: DateTime.now(),
            updatedAt: DateTime.now(),
          ),
          isUnlocked: true,
          progressPercentage: 100,
          userProgress: UserAchievementProgress(
            achievementId: 'streak_7',
            progress: 1.0,
            progressValue: 7,
            progressTarget: 7,
            unlockedAt: DateTime.now().subtract(const Duration(days: 1)),
          ),
        ),
        AchievementWithProgress(
          achievement: AchievementModel(
            id: 'streak_30',
            name: '月度冠军',
            description: '连续学习30天',
            iconUrl: '/icons/streak_30.png',
            type: AchievementType.streak,
            rarity: AchievementRarity.rare,
            category: 'streak',
            triggerCode: 'STREAK_DAYS',
            triggerConfig: {'days': 30},
            createdAt: DateTime.now(),
            updatedAt: DateTime.now(),
          ),
          isUnlocked: false,
          progressPercentage: 23,
          userProgress: UserAchievementProgress(
            achievementId: 'streak_30',
            progress: 0.23,
            progressValue: 7,
            progressTarget: 30,
          ),
        ),
        AchievementWithProgress(
          achievement: AchievementModel(
            id: 'nodes_100',
            name: '星图探索者',
            description: '解锁100个知识点',
            iconUrl: '/icons/nodes_100.png',
            type: AchievementType.nodeExplore,
            rarity: AchievementRarity.rare,
            category: 'exploration',
            triggerCode: 'NODES_UNLOCKED',
            triggerConfig: {'count': 100},
            createdAt: DateTime.now(),
            updatedAt: DateTime.now(),
          ),
          isUnlocked: false,
          progressPercentage: 45,
          userProgress: UserAchievementProgress(
            achievementId: 'nodes_100',
            progress: 0.45,
            progressValue: 45,
            progressTarget: 100,
          ),
        ),
      ],
      totalAchievements: 50,
      totalUnlocked: 12,
      categories: {
        'streak': {'total': 5, 'unlocked': 2},
        'exploration': {'total': 10, 'unlocked': 3},
        'mastery': {'total': 15, 'unlocked': 4},
        'hidden': {'total': 5, 'unlocked': 1},
      },
    );

  AchievementMapData _getDemoAchievementMap() => AchievementMapData(
      nodes: [
        AchievementMapNode(
          id: 'streak_7',
          name: '一周坚持',
          rarity: AchievementRarity.common,
          category: 'streak',
          position: {'x': 100, 'y': 100},
          isUnlocked: true,
          prerequisites: [],
        ),
        AchievementMapNode(
          id: 'streak_30',
          name: '月度冠军',
          rarity: AchievementRarity.rare,
          category: 'streak',
          position: {'x': 100, 'y': 200},
          isUnlocked: false,
          prerequisites: ['streak_7'],
          parentId: 'streak_7',
        ),
        AchievementMapNode(
          id: 'night_owl',
          name: '深夜学者',
          rarity: AchievementRarity.epic,
          category: 'hidden',
          position: {'x': 300, 'y': 100},
          isUnlocked: false,
          isHidden: true,
          prerequisites: [],
        ),
      ],
      connections: [
        {'from': 'streak_7', 'to': 'streak_30', 'type': 'parent'},
      ],
      categories: [
        {'id': 'streak', 'name': 'streak', 'count': 5},
        {'id': 'hidden', 'name': 'hidden', 'count': 3},
      ],
    );

  GalaxySkinListResponse _getDemoGalaxySkins() => GalaxySkinListResponse(
      skins: [
        GalaxySkin(
          id: 'default',
          name: '经典星系',
          description: '默认的星系主题',
          rarity: AchievementRarity.common,
          sortOrder: 0,
          createdAt: DateTime.now(),
          updatedAt: DateTime.now(),
          isUnlocked: true,
          isEquipped: true,
        ),
        GalaxySkin(
          id: 'nebula_purple',
          name: '紫色星云',
          description: '神秘的紫色星云主题',
          rarity: AchievementRarity.rare,
          sortOrder: 1,
          createdAt: DateTime.now(),
          updatedAt: DateTime.now(),
          isUnlocked: false,
        ),
        GalaxySkin(
          id: 'cyberpunk',
          name: '赛博朋克',
          description: '霓虹闪烁的赛博朋克风格',
          rarity: AchievementRarity.legendary,
          sortOrder: 2,
          createdAt: DateTime.now(),
          updatedAt: DateTime.now(),
          isUnlocked: false,
        ),
      ],
      equippedSkinId: 'default',
    );

  List<UserTitle> _getDemoTitles() => [
      UserTitle(
        userId: 'demo_user',
        titleId: 'early_explorer',
        titleName: '星际探索者',
        titleDisplay: '星际探索者',
        unlockedAt: DateTime.now().subtract(const Duration(days: 7)),
        isEquipped: true,
      ),
      UserTitle(
        userId: 'demo_user',
        titleId: 'week_warrior',
        titleName: '周常战士',
        titleDisplay: '周常战士',
        unlockedAt: DateTime.now().subtract(const Duration(days: 1)),
        isEquipped: false,
      ),
    ];
}

// ========== Response Models ==========

class AchievementListResponse {
  AchievementListResponse({
    required this.achievements,
    required this.totalAchievements,
    required this.totalUnlocked,
    required this.categories,
  });

  final List<AchievementWithProgress> achievements;
  final int totalAchievements;
  final int totalUnlocked;
  final Map<String, dynamic> categories;
}

class GalaxySkinListResponse {
  GalaxySkinListResponse({
    required this.skins,
    this.equippedSkinId,
  });

  final List<GalaxySkin> skins;
  final String? equippedSkinId;
}
