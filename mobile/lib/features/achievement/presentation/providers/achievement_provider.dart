import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/achievement/data/repositories/achievement_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart' as chat;
import 'package:sparkle/shared/entities/achievement_model.dart';

// ========== Achievement State ==========

class AchievementState {
  AchievementState({
    required this.achievements,
    required this.stats,
    required this.streakStats,
    this.galaxySkins = const [],
    this.titles = const [],
    this.activeContract,
    this.isLoading = false,
    this.error,
  });

  AchievementState.loading()
      : achievements = [],
        stats = AchievementStats(
          totalAchievements: 0,
          unlockedCount: 0,
          unlockedPercentage: 0,
          commonCount: 0,
          rareCount: 0,
          epicCount: 0,
          legendaryCount: 0,
          hiddenFound: 0,
          currentStreak: 0,
          totalPhotons: 0,
        ),
        streakStats = StreakStats(
          currentStreak: 0,
          maxStreak: 0,
          longestStreak: 0,
          freezeCharges: 0,
          maxFreezeCharges: 3,
          totalCheckinDays: 0,
        ),
        galaxySkins = [],
        titles = [],
        activeContract = null,
        isLoading = true,
        error = null;

  AchievementState.error(String errorMessage)
      : achievements = [],
        stats = AchievementStats(
          totalAchievements: 0,
          unlockedCount: 0,
          unlockedPercentage: 0,
          commonCount: 0,
          rareCount: 0,
          epicCount: 0,
          legendaryCount: 0,
          hiddenFound: 0,
          currentStreak: 0,
          totalPhotons: 0,
        ),
        streakStats = StreakStats(
          currentStreak: 0,
          maxStreak: 0,
          longestStreak: 0,
          freezeCharges: 0,
          maxFreezeCharges: 3,
          totalCheckinDays: 0,
        ),
        galaxySkins = [],
        titles = [],
        activeContract = null,
        isLoading = false,
        error = errorMessage;

  final List<AchievementWithProgress> achievements;
  final AchievementStats stats;
  final StreakStats streakStats;
  final List<GalaxySkin> galaxySkins;
  final List<UserTitle> titles;
  final SparkContract? activeContract;
  final bool isLoading;
  final String? error;

  AchievementState copyWith({
    List<AchievementWithProgress>? achievements,
    AchievementStats? stats,
    StreakStats? streakStats,
    List<GalaxySkin>? galaxySkins,
    List<UserTitle>? titles,
    SparkContract? activeContract,
    bool? isLoading,
    String? error,
  }) =>
      AchievementState(
        achievements: achievements ?? this.achievements,
        stats: stats ?? this.stats,
        streakStats: streakStats ?? this.streakStats,
        galaxySkins: galaxySkins ?? this.galaxySkins,
        titles: titles ?? this.titles,
        activeContract: activeContract ?? this.activeContract,
        isLoading: isLoading ?? this.isLoading,
        error: error ?? this.error,
      );
}

// ========== Achievement Map State ==========

class AchievementMapState {
  AchievementMapState({
    required this.nodes,
    this.connections = const [],
    this.categories = const [],
    this.isLoading = false,
    this.error,
  });

  AchievementMapState.loading()
      : nodes = [],
        connections = [],
        categories = [],
        isLoading = true,
        error = null;

  AchievementMapState.error(String errorMessage)
      : nodes = [],
        connections = [],
        categories = [],
        isLoading = false,
        error = errorMessage;

  final List<AchievementMapNode> nodes;
  final List<Map<String, dynamic>> connections;
  final List<Map<String, dynamic>> categories;
  final bool isLoading;
  final String? error;

  AchievementMapState copyWith({
    List<AchievementMapNode>? nodes,
    List<Map<String, dynamic>>? connections,
    List<Map<String, dynamic>>? categories,
    bool? isLoading,
    String? error,
  }) =>
      AchievementMapState(
        nodes: nodes ?? this.nodes,
        connections: connections ?? this.connections,
        categories: categories ?? this.categories,
        isLoading: isLoading ?? this.isLoading,
        error: error ?? this.error,
      );
}

// ========== Providers ==========

/// Achievement Repository Provider
final achievementRepositoryProvider = Provider<AchievementRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return AchievementRepository(apiClient);
});

/// Main Achievement Provider
final achievementProvider =
    StateNotifierProvider<AchievementNotifier, AchievementState>(
  (ref) => AchievementNotifier(ref.watch(achievementRepositoryProvider), ref),
);

/// Achievement Map Provider
final achievementMapProvider =
    StateNotifierProvider<AchievementMapNotifier, AchievementMapState>(
  (ref) => AchievementMapNotifier(ref.watch(achievementRepositoryProvider)),
);

/// Streak Stats Provider (for quick access)
final streakStatsProvider = Provider<StreakStats>((ref) {
  final state = ref.watch(achievementProvider);
  return state.streakStats;
});

/// Galaxy Skins Provider
final galaxySkinsProvider = Provider<List<GalaxySkin>>((ref) {
  final state = ref.watch(achievementProvider);
  return state.galaxySkins;
});

/// Titles Provider
final titlesProvider = Provider<List<UserTitle>>((ref) {
  final state = ref.watch(achievementProvider);
  return state.titles;
});

/// Global provider for pending achievement unlock dialog
/// 全局成就解锁弹窗队列，由 MainNavigationShell 监听
final pendingAchievementUnlockProvider = StateNotifierProvider<
    PendingAchievementUnlockNotifier,
    ({chat.AchievementUnlockEvent event, int? comboCount})?>(
  (ref) => PendingAchievementUnlockNotifier(),
);

class PendingAchievementUnlockNotifier extends StateNotifier<
    ({chat.AchievementUnlockEvent event, int? comboCount})?> {
  PendingAchievementUnlockNotifier() : super(null);

  void setPending({
    required chat.AchievementUnlockEvent event,
    int? comboCount,
  }) {
    state = (event: event, comboCount: comboCount);
  }

  void clear() {
    state = null;
  }
}

// ========== Notifiers ==========

class AchievementNotifier extends StateNotifier<AchievementState> {
  AchievementNotifier(this._repository, this._ref)
      : super(AchievementState.loading()) {
    unawaited(loadInitialData());
  }

  final AchievementRepository _repository;
  final Ref _ref;

  /// Load all initial achievement data
  Future<void> loadInitialData() async {
    try {
      state = AchievementState.loading();

      // Load all data in parallel
      final results = await Future.wait([
        _repository.getAchievements(),
        _repository.getAchievementStats(),
        _repository.getStreakStats(),
        _repository.getGalaxySkins(),
        _repository.getTitles(),
        _repository.getContractStatus(),
      ]);

      final achievementsResponse = results[0] as AchievementListResponse;
      final stats = results[1] as AchievementStats;
      final streakStats = results[2] as StreakStats;
      final galaxySkinsResponse = results[3] as GalaxySkinListResponse;
      final titles = results[4] as List<UserTitle>;
      final contract = results[5] as SparkContract?;

      state = AchievementState(
        achievements: achievementsResponse.achievements,
        stats: stats,
        streakStats: streakStats,
        galaxySkins: galaxySkinsResponse.skins,
        titles: titles,
        activeContract: contract,
      );
    } catch (e) {
      debugPrint('Error loading achievement data: $e');
      state = AchievementState.error(e.toString());
    }
  }

  /// Refresh achievements list
  Future<void> refreshAchievements({
    String? category,
    AchievementRarity? rarity,
    bool includeHidden = false,
  }) async {
    try {
      final response = await _repository.getAchievements(
        category: category,
        rarity: rarity,
        includeHidden: includeHidden,
      );

      state = state.copyWith(achievements: response.achievements);
    } catch (e) {
      debugPrint('Error refreshing achievements: $e');
    }
  }

  /// Refresh stats
  Future<void> refreshStats() async {
    try {
      final stats = await _repository.getAchievementStats();
      state = state.copyWith(stats: stats);
    } catch (e) {
      debugPrint('Error refreshing stats: $e');
    }
  }

  /// Refresh streak stats
  Future<void> refreshStreakStats() async {
    try {
      final streakStats = await _repository.getStreakStats();
      state = state.copyWith(streakStats: streakStats);
    } catch (e) {
      debugPrint('Error refreshing streak stats: $e');
    }
  }

  /// Refresh galaxy skins
  Future<void> refreshGalaxySkins() async {
    try {
      final response = await _repository.getGalaxySkins();
      state = state.copyWith(galaxySkins: response.skins);
    } catch (e) {
      debugPrint('Error refreshing galaxy skins: $e');
    }
  }

  /// Refresh titles
  Future<void> refreshTitles() async {
    try {
      final titles = await _repository.getTitles();
      state = state.copyWith(titles: titles);
    } catch (e) {
      debugPrint('Error refreshing titles: $e');
    }
  }

  /// Equip galaxy skin
  Future<bool> equipSkin(String skinId) async {
    try {
      final success = await _repository.equipGalaxySkin(skinId);
      if (success) {
        await refreshGalaxySkins();
        await _ref.read(authProvider.notifier).refreshUser();
      }
      return success;
    } catch (e) {
      debugPrint('Error equipping skin: $e');
      return false;
    }
  }

  /// Equip title
  Future<bool> equipTitle(String titleId) async {
    try {
      final success = await _repository.equipTitle(titleId);
      if (success) {
        await refreshTitles();
        await _ref.read(authProvider.notifier).refreshUser();
      }
      return success;
    } catch (e) {
      debugPrint('Error equipping title: $e');
      return false;
    }
  }

  /// Pin/Unpin achievement
  Future<void> pinAchievement(String achievementId, bool pinned) async {
    try {
      await _repository.pinAchievement(achievementId, pinned);
      await refreshAchievements();
    } catch (e) {
      debugPrint('Error pinning achievement: $e');
    }
  }

  /// Generate achievement share card metadata
  Future<AchievementShareCard?> shareAchievement(
    String achievementId, {
    String templateId = 'cosmic',
    ShareCardPrivacySettings? privacySettings,
  }) async {
    try {
      return await _repository.shareAchievement(
        achievementId,
        templateId: templateId,
        privacySettings: privacySettings,
      );
    } catch (e) {
      debugPrint('Error sharing achievement: $e');
      return null;
    }
  }

  /// Get available share card templates
  Future<List<ShareTemplateInfo>> getShareTemplates() async {
    try {
      return await _repository.getShareTemplates();
    } catch (e) {
      debugPrint('Error getting share templates: $e');
      return [];
    }
  }

  /// Create contract
  Future<SparkContract?> createContract({
    required int targetStudyMinutes,
    required int targetDays,
    required int photonStake,
  }) async {
    try {
      final contract = await _repository.createContract(
        targetStudyMinutes: targetStudyMinutes,
        targetDays: targetDays,
        photonStake: photonStake,
      );
      state = state.copyWith(activeContract: contract);
      return contract;
    } catch (e) {
      debugPrint('Error creating contract: $e');
      return null;
    }
  }

  /// Cancel contract
  Future<bool> cancelContract() async {
    try {
      final success = await _repository.cancelContract();
      if (success) {
        state = state.copyWith();
      }
      return success;
    } catch (e) {
      debugPrint('Error canceling contract: $e');
      return false;
    }
  }

  /// Process achievement event
  Future<List<AchievementUnlockEvent>> processEvent({
    required String eventType,
    Map<String, dynamic>? eventData,
  }) async {
    try {
      final unlocked = await _repository.processEvent(
        eventType: eventType,
        eventData: eventData,
      );

      // Refresh data if any achievements were unlocked
      if (unlocked.isNotEmpty) {
        await refreshAchievements();
        await refreshStats();
      }

      return unlocked;
    } catch (e) {
      debugPrint('Error processing event: $e');
      return [];
    }
  }

  /// Get achievements close to unlocking (80%+ progress)
  /// 获取接近解锁的成就（用于临界提示）
  Future<List<AchievementWithProgress>> getCloseToUnlockAchievements({
    String? category,
    double threshold = 0.8,
  }) async {
    try {
      return await _repository.getCloseToUnlockAchievements(
        category: category,
        threshold: threshold,
      );
    } catch (e) {
      debugPrint('Error getting close to unlock achievements: $e');
      return [];
    }
  }

  // ========== Phase 1A: Combo Queue Management ==========

  Timer? _comboTimer;
  static const _comboWindow = Duration(seconds: 3);
  final List<chat.AchievementUnlockEvent> _unlockQueue = [];
  int _currentComboCount = 0;
  DateTime? _lastUnlockTime;

  /// Handle achievement unlock event with combo queue management
  /// Returns (event, comboCount) if dialog should be shown, null otherwise
  /// 处理成就解锁事件，支持连击队列管理
  /// 返回 (event, comboCount) 如果应该显示弹窗，否则返回 null
  ({chat.AchievementUnlockEvent event, int? comboCount})? handleAchievementUnlock(
    chat.AchievementUnlockEvent wsEvent,
  ) {
    final now = DateTime.now();

    // Check if backend already calculated combo
    final comboInfo = wsEvent.achievementData['combo_info'] as Map<String, dynamic>?;
    final backendComboCount = comboInfo != null ? comboInfo['combo'] as int? : null;

    if (backendComboCount != null && backendComboCount > 1) {
      // Backend already calculated combo, show immediately
      // Also clear any local queue
      _unlockQueue.clear();
      _currentComboCount = 0;
      return (event: wsEvent, comboCount: backendComboCount);
    }

    // Client-side combo management
    if (_lastUnlockTime != null &&
        now.difference(_lastUnlockTime!) < _comboWindow) {
      // Within combo window, add to queue
      _comboTimer?.cancel();
      _unlockQueue.add(wsEvent);
      _currentComboCount++;
      _lastUnlockTime = now;

      // Reset timer to show combo dialog after window expires
      _comboTimer = Timer(_comboWindow, _showComboDialog);

      return null; // Don't show yet, waiting for combo window
    } else {
      // Outside combo window or first unlock
      // Show any pending combo first
      if (_unlockQueue.isNotEmpty) {
        _comboTimer?.cancel();
        final pendingResult = _showComboDialog();
        // Add current to queue for next time
        _unlockQueue.add(wsEvent);
        _currentComboCount++;
        _lastUnlockTime = now;
        return pendingResult;
      }

      // Show current unlock immediately
      _unlockQueue.clear();
      _currentComboCount = 1;
      _lastUnlockTime = now;
      return (event: wsEvent, comboCount: null);
    }
  }

  /// Show combo dialog with queued achievements
  /// Returns the event and combo count to display
  /// 显示连击弹窗，包含队列中的所有成就
  ({chat.AchievementUnlockEvent event, int? comboCount})? _showComboDialog() {
    if (_unlockQueue.isEmpty || _currentComboCount < 2) {
      _unlockQueue.clear();
      _currentComboCount = 0;
      return null;
    }

    final lastEvent = _unlockQueue.last;
    final comboCount = _currentComboCount;

    // Clear queue
    _unlockQueue.clear();
    _currentComboCount = 0;
    _comboTimer?.cancel();

    return (event: lastEvent, comboCount: comboCount);
  }

  @override
  void dispose() {
    _comboTimer?.cancel();
    super.dispose();
  }
}

class AchievementMapNotifier extends StateNotifier<AchievementMapState> {
  AchievementMapNotifier(this._repository)
      : super(AchievementMapState.loading()) {
    unawaited(loadMap());
  }

  final AchievementRepository _repository;

  Future<void> loadMap() async {
    try {
      state = AchievementMapState.loading();
      final mapData = await _repository.getAchievementMap();

      state = AchievementMapState(
        nodes: mapData.nodes,
        connections: mapData.connections,
        categories: mapData.categories,
      );
    } catch (e) {
      debugPrint('Error loading achievement map: $e');
      state = AchievementMapState.error(e.toString());
    }
  }

  Future<void> refresh() async {
    await loadMap();
  }
}
