import 'package:dio/dio.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

/// Achievement Repository
/// 成就数据仓库
class AchievementRepository {
  AchievementRepository(this._apiClient);
  final ApiClient _apiClient;

  /// Handle Dio exceptions
  T _handleDioError<T>(DioException e, String functionName) {
    final responseData = e.response?.data;
    final detail = switch (responseData) {
      final Map<String, dynamic> map => map['detail'] as String?,
      final Map<dynamic, dynamic> map => map['detail'] as String?,
      _ => null,
    };
    final errorMessage = detail ?? 'An unknown error occurred in $functionName';
    throw Exception(errorMessage);
  }

  /// Get achievements list
  Future<AchievementListResponse> getAchievements({
    String? category,
    AchievementRarity? rarity,
    bool includeHidden = false,
    bool includeInactive = false,
  }) async {
    if (DemoDataService.isDemoMode) {
      // Return demo achievements
      return _getDemoAchievements();
    }

    try {
      final locale = I18nService.instance.currentLocale.languageCode;
      final queryParams = <String, dynamic>{
        'locale': locale,
        if (category != null) 'category': category,
        if (rarity != null) 'rarity': rarity.name,
        'include_hidden': includeHidden,
        'include_inactive': includeInactive,
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
          .map(
            (json) => AchievementWithProgress.fromJson(
              json as Map<String, dynamic>,
            ),
          )
          .toList();

      final meta = payload['meta'] as Map<String, dynamic>? ?? {};

      return AchievementListResponse(
        achievements: achievements,
        totalAchievements:
            (meta['total_achievements'] as int?) ?? achievements.length,
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

      final payload = ApiResponseParser.unwrapMap(
        response.data,
        action: 'getAchievementStats',
      );
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
      final locale = I18nService.instance.currentLocale.languageCode;
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.achievementsMap,
        queryParameters: {'locale': locale},
      );

      final payload = ApiResponseParser.unwrapMap(
        response.data,
        action: 'getAchievementMap',
      );
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

      final payload =
          ApiResponseParser.unwrapMap(response.data, action: 'getStreakStats');
      return StreakStats.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, 'getStreakStats');
    }
  }

  /// Get streak history for calendar (default 90 days)
  Future<List<StreakDayRecord>> getStreakHistory({int days = 90}) async {
    if (DemoDataService.isDemoMode) {
      return _getDemoStreakHistory(days);
    }

    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.achievementsStreakHistory,
        queryParameters: {'days': days},
      );

      final payload = response.data;
      if (payload == null) {
        throw Exception('getStreakHistory response is empty');
      }

      final history = StreakHistoryResponse.fromJson(payload);
      return history.days;
    } on DioException catch (e) {
      return _handleDioError(e, 'getStreakHistory');
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

      final payload = ApiResponseParser.unwrapMap(
        response.data,
        action: 'getContractStatus',
      );
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

      // Backend returns {"success": true, "data": {...}}
      // unwrapMap extracts the "data" dict directly, so parse it directly
      final payload =
          ApiResponseParser.unwrapMap(response.data, action: 'createContract');
      return SparkContract.fromJson(payload);
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

      final payload =
          ApiResponseParser.unwrapMap(response.data, action: 'getGalaxySkins');
      final dataList = payload['data'] as List<dynamic>?;

      final skins = dataList
              ?.map(
                (json) => GalaxySkin.fromJson(
                  json as Map<String, dynamic>,
                ),
              )
              .toList() ??
          [];

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

      final payload =
          ApiResponseParser.unwrapMap(response.data, action: 'getTitles');
      final dataList = payload['data'] as List<dynamic>?;

      return dataList
              ?.map(
                (json) => UserTitle.fromJson(json as Map<String, dynamic>),
              )
              .toList() ??
          [];
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

  /// Generate achievement share card
  Future<AchievementShareCard> shareAchievement(
    String achievementId, {
    String templateId = 'cosmic',
    ShareCardPrivacySettings? privacySettings,
  }) async {
    if (DemoDataService.isDemoMode) {
      final achievement = _getDemoAchievements()
          .achievements
          .firstWhere((item) => item.achievement.id == achievementId)
          .achievement;
      return AchievementShareCard(
        cardUrl: '',
        width: 1080,
        height: 1440,
        generatedAt: DateTime.now(),
        templateId: templateId,
        privacySettings: privacySettings,
        achievement: achievement,
      );
    }

    try {
      final locale = I18nService.instance.currentLocale.languageCode;
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.achievementShare(achievementId),
        queryParameters: {'locale': locale},
        data: {
          'template_id': templateId,
          'privacy': privacySettings?.toJson(),
        },
      );

      final payload = ApiResponseParser.unwrapMap(
        response.data,
        action: 'shareAchievement',
      );
      return AchievementShareCard.fromJson(payload);
    } on DioException catch (e) {
      return _handleDioError(e, 'shareAchievement');
    }
  }

  /// Get available share card templates
  Future<List<ShareTemplateInfo>> getShareTemplates() async {
    if (DemoDataService.isDemoMode) {
      return [
        ShareTemplateInfo(id: 'cosmic', name: '星空'),
        ShareTemplateInfo(id: 'minimal', name: '简约'),
        ShareTemplateInfo(id: 'neon', name: '霓虹'),
        ShareTemplateInfo(id: 'elegant', name: '典雅'),
      ];
    }

    try {
      final locale = I18nService.instance.currentLocale.languageCode;
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.achievementShareTemplates,
        queryParameters: {'locale': locale},
      );

      final payload = ApiResponseParser.unwrapMap(
        response.data,
        action: 'getShareTemplates',
      );
      final templates = payload['templates'] as List<dynamic>?;
      return templates
              ?.map(
                (json) => ShareTemplateInfo.fromJson(
                  json as Map<String, dynamic>,
                ),
              )
              .toList() ??
          [];
    } on DioException catch (e) {
      return _handleDioError(e, 'getShareTemplates');
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

      final payload =
          ApiResponseParser.unwrapMap(response.data, action: 'processEvent');
      final unlockedList = payload['unlocked'] as List<dynamic>?;

      return unlockedList
              ?.map(
                (json) => AchievementUnlockEvent.fromJson(
                  json as Map<String, dynamic>,
                ),
              )
              .toList() ??
          [];
    } on DioException catch (e) {
      return _handleDioError(e, 'processEvent');
    }
  }

  /// Get achievements close to unlocking (80%+ progress)
  /// 获取接近解锁的成就（80%以上进度）
  Future<List<AchievementWithProgress>> getCloseToUnlockAchievements({
    String? category,
    double threshold = 0.8,
  }) async {
    if (DemoDataService.isDemoMode) {
      // Return demo close-to-unlock achievements
      return _getDemoCloseToUnlockAchievements();
    }

    try {
      final locale = I18nService.instance.currentLocale.languageCode;
      final queryParams = <String, dynamic>{
        'threshold': threshold,
        'locale': locale,
        if (category != null) 'category': category,
      };

      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiEndpoints.achievementsCloseToUnlock,
        queryParameters: queryParams,
      );

      final payload = ApiResponseParser.unwrapMap(
        response.data,
        action: 'getCloseToUnlockAchievements',
      );
      final dataList = payload['data'] as List<dynamic>?;

      return dataList
              ?.map(
                (json) => AchievementWithProgress.fromJson(
                  json as Map<String, dynamic>,
                ),
              )
              .toList() ??
          [];
    } on DioException catch (e) {
      return _handleDioError(e, 'getCloseToUnlockAchievements');
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

  AchievementMapData _getDemoAchievementMap() {
    // 使用更大的画布尺寸和更分散的节点布局
    // 模拟一个真实的成就地图，多个类别分布在不同的区域
    final nodes = <AchievementMapNode>[
      // === Streak Achievements (左上区域) ===
      AchievementMapNode(
        id: 'streak_3',
        name: '起步启航',
        rarity: AchievementRarity.common,
        category: 'streak',
        position: {'x': 80, 'y': 150},
        isUnlocked: true,
        prerequisites: [],
      ),
      AchievementMapNode(
        id: 'streak_7',
        name: '一周坚持',
        rarity: AchievementRarity.common,
        category: 'streak',
        position: {'x': 80, 'y': 280},
        isUnlocked: true,
        prerequisites: ['streak_3'],
        parentId: 'streak_3',
      ),
      AchievementMapNode(
        id: 'streak_14',
        name: '双周达人',
        rarity: AchievementRarity.rare,
        category: 'streak',
        position: {'x': 80, 'y': 410},
        isUnlocked: false,
        prerequisites: ['streak_7'],
        parentId: 'streak_7',
      ),
      AchievementMapNode(
        id: 'streak_30',
        name: '月度冠军',
        rarity: AchievementRarity.rare,
        category: 'streak',
        position: {'x': 80, 'y': 540},
        isUnlocked: false,
        prerequisites: ['streak_14'],
        parentId: 'streak_14',
      ),
      AchievementMapNode(
        id: 'streak_100',
        name: '百日传奇',
        rarity: AchievementRarity.epic,
        category: 'streak',
        position: {'x': 80, 'y': 670},
        isUnlocked: false,
        prerequisites: ['streak_30'],
        parentId: 'streak_30',
      ),

      // === Mastery Achievements (中间区域) ===
      AchievementMapNode(
        id: 'mastery_first',
        name: '初窥门径',
        rarity: AchievementRarity.common,
        category: 'mastery',
        position: {'x': 280, 'y': 150},
        isUnlocked: true,
        prerequisites: [],
      ),
      AchievementMapNode(
        id: 'mastery_10',
        name: '小有所成',
        rarity: AchievementRarity.rare,
        category: 'mastery',
        position: {'x': 280, 'y': 280},
        isUnlocked: false,
        prerequisites: ['mastery_first'],
        parentId: 'mastery_first',
      ),
      AchievementMapNode(
        id: 'mastery_50',
        name: '炉火纯青',
        rarity: AchievementRarity.epic,
        category: 'mastery',
        position: {'x': 280, 'y': 410},
        isUnlocked: false,
        prerequisites: ['mastery_10'],
        parentId: 'mastery_10',
      ),
      AchievementMapNode(
        id: 'mastery_100',
        name: '登峰造极',
        rarity: AchievementRarity.legendary,
        category: 'mastery',
        position: {'x': 280, 'y': 540},
        isUnlocked: false,
        prerequisites: ['mastery_50'],
        parentId: 'mastery_50',
      ),

      // === Exploration Achievements (右侧区域) ===
      AchievementMapNode(
        id: 'explore_10',
        name: '初探星海',
        rarity: AchievementRarity.common,
        category: 'exploration',
        position: {'x': 480, 'y': 150},
        isUnlocked: true,
        prerequisites: [],
      ),
      AchievementMapNode(
        id: 'explore_50',
        name: '星图漫游',
        rarity: AchievementRarity.rare,
        category: 'exploration',
        position: {'x': 480, 'y': 280},
        isUnlocked: false,
        prerequisites: ['explore_10'],
        parentId: 'explore_10',
      ),
      AchievementMapNode(
        id: 'explore_100',
        name: '星图探索者',
        rarity: AchievementRarity.epic,
        category: 'exploration',
        position: {'x': 480, 'y': 410},
        isUnlocked: false,
        prerequisites: ['explore_50'],
        parentId: 'explore_50',
      ),
      AchievementMapNode(
        id: 'explore_500',
        name: '宇宙开拓者',
        rarity: AchievementRarity.legendary,
        category: 'exploration',
        position: {'x': 480, 'y': 540},
        isUnlocked: false,
        prerequisites: ['explore_100'],
        parentId: 'explore_100',
      ),

      // === Hidden/Special Achievements (底部隐藏区域) ===
      AchievementMapNode(
        id: 'night_owl',
        name: '深夜学者',
        rarity: AchievementRarity.epic,
        category: 'hidden',
        position: {'x': 180, 'y': 700},
        isUnlocked: false,
        isHidden: true,
        prerequisites: ['streak_30', 'mastery_10'],
      ),
      AchievementMapNode(
        id: 'early_bird',
        name: '早起鸟儿',
        rarity: AchievementRarity.rare,
        category: 'hidden',
        position: {'x': 380, 'y': 700},
        isUnlocked: false,
        isHidden: true,
        prerequisites: ['streak_14'],
      ),
    ];

    final connections = <Map<String, dynamic>>[
      // Streak chain
      {'from': 'streak_3', 'to': 'streak_7', 'type': 'parent'},
      {'from': 'streak_7', 'to': 'streak_14', 'type': 'parent'},
      {'from': 'streak_14', 'to': 'streak_30', 'type': 'parent'},
      {'from': 'streak_30', 'to': 'streak_100', 'type': 'parent'},

      // Mastery chain
      {'from': 'mastery_first', 'to': 'mastery_10', 'type': 'parent'},
      {'from': 'mastery_10', 'to': 'mastery_50', 'type': 'parent'},
      {'from': 'mastery_50', 'to': 'mastery_100', 'type': 'parent'},

      // Exploration chain
      {'from': 'explore_10', 'to': 'explore_50', 'type': 'parent'},
      {'from': 'explore_50', 'to': 'explore_100', 'type': 'parent'},
      {'from': 'explore_100', 'to': 'explore_500', 'type': 'parent'},

      // Hidden prerequisites (cross-category)
      {'from': 'streak_30', 'to': 'night_owl', 'type': 'prerequisite'},
      {'from': 'mastery_10', 'to': 'night_owl', 'type': 'prerequisite'},
      {'from': 'streak_14', 'to': 'early_bird', 'type': 'prerequisite'},
    ];

    final categories = <Map<String, dynamic>>[
      {'id': 'streak', 'name': '连胜', 'count': 5},
      {'id': 'mastery', 'name': '精通', 'count': 4},
      {'id': 'exploration', 'name': '探索', 'count': 4},
      {'id': 'hidden', 'name': '隐藏', 'count': 2},
    ];

    return AchievementMapData(
      nodes: nodes,
      connections: connections,
      categories: categories,
    );
  }

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
          ),
          GalaxySkin(
            id: 'cyberpunk',
            name: '赛博朋克',
            description: '霓虹闪烁的赛博朋克风格',
            rarity: AchievementRarity.legendary,
            sortOrder: 2,
            createdAt: DateTime.now(),
            updatedAt: DateTime.now(),
          ),
        ],
        equippedSkinId: 'default',
      );

  List<UserTitle> _getDemoTitles() => [
        UserTitle(
          titleId: 'early_explorer',
          titleName: '星际探索者',
          titleDisplay: '星际探索者',
          unlockedAt: DateTime.now().subtract(const Duration(days: 7)),
          isEquipped: true,
        ),
        UserTitle(
          titleId: 'week_warrior',
          titleName: '周常战士',
          titleDisplay: '周常战士',
          unlockedAt: DateTime.now().subtract(const Duration(days: 1)),
        ),
      ];

  List<StreakDayRecord> _getDemoStreakHistory(int days) {
    final today = DateTime.now();
    final start = today.subtract(Duration(days: days - 1));
    final history = <StreakDayRecord>[];

    for (var i = 0; i < days; i++) {
      final day = DateTime(start.year, start.month, start.day)
          .add(Duration(days: i));
      final status = i % 10 == 0
          ? StreakDayStatus.frozen
          : i % 7 == 0
              ? StreakDayStatus.missed
              : StreakDayStatus.active;
      history.add(
        StreakDayRecord(
          day: day,
          status: status,
          usedFreeze: status == StreakDayStatus.frozen,
        ),
      );
    }
    return history;
  }

  List<AchievementWithProgress> _getDemoCloseToUnlockAchievements() => [
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
          progressPercentage: 90,
          userProgress: UserAchievementProgress(
            achievementId: 'streak_30',
            progress: 0.9,
            progressValue: 27,
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
          progressPercentage: 85,
          userProgress: UserAchievementProgress(
            achievementId: 'nodes_100',
            progress: 0.85,
            progressValue: 85,
            progressTarget: 100,
          ),
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
