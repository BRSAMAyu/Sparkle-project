import 'package:sparkle/core/constants/api_constants.dart';

class ApiEndpoints {
  // Use platform-aware base URL from ApiConstants (points to Gateway 8080)
  static String get baseUrl =>
      '${ApiConstants.baseUrl}${ApiConstants.apiBasePath}';

  // Auth
  static const String register = '/auth/register';
  static const String login = '/auth/login';
  static const String refresh = '/auth/refresh';
  static const String forgotPassword = '/auth/forgot-password';
  static const String resetPassword = '/auth/reset-password';
  static const String sendVerification = '/auth/send-verification';
  static const String verifyEmail = '/auth/verify-email';
  static const String logout = '/auth/logout';
  static const String upgradeGuest = '/auth/upgrade-guest';
  static const String upgradeGuestSocial = '/auth/upgrade-guest/social';
  static const String me = '/users/me';
  static const String setPassword = '/users/me/set-password';
  static const String deleteAccount = '/users/me/delete-account';
  static const String socialAccounts = '/users/me/social-accounts';
  static const String linkSocial = '/users/me/link-social';
  static const String unlinkSocial = '/users/me/unlink-social';
  static const String userSessions = '/users/me/sessions';
  static const String securityLog = '/users/me/security-log';

  // Files
  static const String filesPrepareUpload = '/files/upload/prepare';
  static const String filesCompleteUpload = '/files/upload/complete';
  static String file(String id) => '/files/$id';
  static String fileDownload(String id) => '/files/$id/download';
  static String fileThumbnail(String id) => '/files/$id/thumbnail';
  static const String myFiles = '/me/files';
  static const String myFilesSearch = '/me/files/search';

  // Vocabulary / Dictionary
  static const String vocabularyLookup = '/vocabulary/lookup';
  static const String vocabularyWordbook = '/vocabulary/wordbook';
  static const String dictionaryPackages = '/vocabulary/dictionary/packages';
  static String dictionaryPackageDownload(String packageId) =>
      '/vocabulary/dictionary/packages/$packageId/download';

  // Users
  static String user(String id) => '/users/$id';

  // Tasks
  static const String tasks = '/tasks';
  static const String tasksReorder = '/tasks/reorder';
  static String task(String id) => '/tasks/$id';
  static const String todayTasks = '/tasks/today';
  static const String recommendedTasks = '/tasks/recommended';
  static String startTask(String id) => '/tasks/$id/start';
  static String completeTask(String id) => '/tasks/$id/complete';
  static String abandonTask(String id) => '/tasks/$id/abandon';
  static String taskGenerateGuide(String id) => '/tasks/$id/generate-guide';
  static String taskFeedback(String id) => '/tasks/$id/feedback';
  static String taskFeedbackReflection(String feedbackId) =>
      '/tasks/feedback/$feedbackId/reflection';
  static String nextActionSelection(String id) =>
      '/tasks/$id/next-action-selection';
  static const String taskSuggestions = '/tasks/suggestions';

  // Subtasks
  static const String subtasks = '/subtasks';
  static String subtask(String id) => '/subtasks/$id';

  // Plans
  static const String plans = '/plans';
  static String plan(String id) => '/plans/$id';
  static String planTasks(String id) => '/plans/$id/tasks';
  static String generateTasks(String planId) => '/plans/$planId/generate-tasks';
  static String planArchive(String id) => '/plans/$id/archive';
  static String planRestore(String id) => '/plans/$id/restore';
  static const String planPrimary = '/plans/primary';

  // Chat
  static const String chat = '/chat';
  static const String chatStream = '/chat/stream'; // SSE 流式聊天端点
  static const String chatConfirm = '/chat/confirm'; // 确认聊天结果
  static const String chatSessions = '/chat/sessions';
  static String chatHistory(String sessionId) => '/chat/history/$sessionId';
  static String sessionMessages(String id) => '/chat/sessions/$id/messages';
  static const String clientTelemetryEvents = '/client-telemetry/events';
  static const String clientTelemetryEventsBatch =
      '/client-telemetry/events/batch';
  static const String clientTelemetrySummary = '/client-telemetry/summary';
  static const String eventsIngest = '/events/ingest';
  static const String healthCapacity = '/health/capacity';
  static const String healthPrometheusAlerts = '/health/prometheus/alerts';

  // Statistics
  static const String statsOverview = '/statistics/overview';
  static const String statsWeekly = '/statistics/weekly';
  static const String statsFlame = '/statistics/flame';

  // Galaxy
  static const String galaxyGraph = '/galaxy/graph';
  static const String galaxyViewport = '/galaxy/nodes/viewport';
  static const String galaxyPositions = '/galaxy/nodes/positions';
  static String galaxyUpdateMastery(String id) =>
      '/galaxy/nodes/$id/update-mastery';
  static const String galaxyPredictNext = '/galaxy/predict-next';
  static const String galaxySearch = '/galaxy/search';
  static String sparkNode(String id) => '/galaxy/node/$id/spark';
  static const String galaxyEvents = '/galaxy/events';
  static String galaxyNodeDetail(String id) => '/galaxy/node/$id';
  static String galaxyNodeFavorite(String id) => '/galaxy/node/$id/favorite';
  static String galaxyNodeDecayPause(String id) =>
      '/galaxy/node/$id/decay/pause';

  // Learning Paths
  static String learningPath(String targetNodeId) =>
      '/learning-paths/$targetNodeId';
  static String learningPathPlan(String targetNodeId) =>
      '/learning-paths/$targetNodeId/plan';

  static String learningPathFullPlan(String targetNodeId) =>
      '/learning-paths/$targetNodeId/full-plan';

  static String learningPathProgress(String planId) =>
      '/plans/$planId/learning-path-progress';

  // Community - Friends
  static const String communityFeed = '/community/feed';
  static const String communityPosts = '/community/posts';
  static String communityPostLike(String id) => '/community/posts/$id/like';
  static const String friends = '/community/friends';
  static const String friendRequest = '/community/friends/request';
  static const String friendRespond = '/community/friends/respond';
  static const String friendsPending = '/community/friends/pending';
  static const String friendsRecommendations =
      '/community/friends/recommendations';
  static const String friendsRecommendationsFeedback =
      '/community/friends/recommendations/feedback';
  static const String recommendationsFeedbackPrompts =
      '/community/recommendations/feedback/prompts';
  static const String recommendationsFeedbackInsights =
      '/community/recommendations/feedback/insights';
  static String privateMessages(String friendId) =>
      '/community/friends/$friendId/messages';
  static String revokePrivateMessage(String messageId) =>
      '/community/messages/$messageId/revoke';
  static String editPrivateMessage(String messageId) =>
      '/community/messages/$messageId';
  static String privateMessageReactions(String messageId) =>
      '/community/messages/$messageId/reactions';
  static String privateMessagesSearch(String friendId) =>
      '/community/friends/$friendId/messages/search';
  static const String sendPrivateMessage = '/community/messages';
  static const String communityShare = '/community/share';
  static String adoptSharedResource(String id) =>
      '/community/shared-resources/$id/adopt';
  static const String searchUsers = '/community/users/search';
  static const String userStatus = '/community/status';

  // Community - Groups
  static const String groups = '/community/groups';
  static const String groupsRecommendations =
      '/community/groups/recommendations';
  static const String groupsRecommendationsFeedback =
      '/community/groups/recommendations/feedback';
  static const String groupsDirectory = '/community/groups/directory';
  static const String groupsSearch = '/community/groups/search';
  static String group(String id) => '/community/groups/$id';
  static String groupJoin(String id) => '/community/groups/$id/join';
  static String groupLeave(String id) => '/community/groups/$id/leave';
  static String groupMembers(String id) => '/community/groups/$id/members';
  static String groupMemberKick(String groupId, String userId) =>
      '/community/groups/$groupId/members/$userId/kick';
  static String groupMemberPromote(String groupId, String userId) =>
      '/community/groups/$groupId/members/$userId/promote';
  static String groupMemberDemote(String groupId, String userId) =>
      '/community/groups/$groupId/members/$userId/demote';
  static String groupTransferOwnership(String groupId, String userId) =>
      '/community/groups/$groupId/members/$userId/transfer-ownership';
  static String groupMessages(String id) => '/community/groups/$id/messages';
  static String groupMessageRevoke(String groupId, String messageId) =>
      '/community/groups/$groupId/messages/$messageId/revoke';
  static String groupMessageEdit(String groupId, String messageId) =>
      '/community/groups/$groupId/messages/$messageId';
  static String groupMessageReactions(String groupId, String messageId) =>
      '/community/groups/$groupId/messages/$messageId/reactions';
  static String groupMessagesRead(String groupId) =>
      '/community/groups/$groupId/messages/read';
  static String groupThreadMessages(String groupId, String threadRootId) =>
      '/community/groups/$groupId/threads/$threadRootId';
  static String groupMessagesSearch(String groupId) =>
      '/community/groups/$groupId/messages/search';
  static String groupTasks(String id) => '/community/groups/$id/tasks';
  static String groupFlame(String id) => '/community/groups/$id/flame';
  static String groupFiles(String groupId) =>
      '/community/groups/$groupId/files';
  static String groupFileShare(String groupId, String fileId) =>
      '/community/groups/$groupId/files/$fileId/share';
  static String groupFilePermissions(String groupId, String fileId) =>
      '/community/groups/$groupId/files/$fileId/permissions';
  static String groupFileCategories(String groupId) =>
      '/community/groups/$groupId/files/categories';

  // Community - Tasks & Checkin
  static String claimTask(String id) => '/community/tasks/$id/claim';
  static const String checkin = '/community/checkin';

  // Community - Encryption
  static const String encryptionKeys = '/community/encryption/keys';
  static String encryptionKey(String keyId) =>
      '/community/encryption/keys/$keyId';
  static String encryptionKeyRevoke(String keyId) =>
      '/community/encryption/keys/$keyId/revoke';
  static String userPublicKey(String userId) =>
      '/community/encryption/keys/user/$userId';

  // Community - Group Moderation
  static String groupAnnouncement(String groupId) =>
      '/community/groups/$groupId/announcement';
  static String groupModerationSettings(String groupId) =>
      '/community/groups/$groupId/moderation';
  static String groupMemberMute(String groupId, String userId) =>
      '/community/groups/$groupId/members/$userId/mute';
  static String groupMemberUnmute(String groupId, String userId) =>
      '/community/groups/$groupId/members/$userId/unmute';
  static String groupMemberWarn(String groupId, String userId) =>
      '/community/groups/$groupId/members/$userId/warn';
  static String groupReports(String groupId) =>
      '/community/groups/$groupId/reports';

  // Community - Message Reports
  static const String messageReports = '/community/reports';
  static String messageReport(String reportId) =>
      '/community/reports/$reportId';
  static String messageReportReview(String reportId) =>
      '/community/reports/$reportId/review';

  // Community - Message Favorites
  static const String messageFavorites = '/community/favorites';
  static String messageFavorite(String favoriteId) =>
      '/community/favorites/$favoriteId';

  // Community - Message Forwarding
  static const String messageForward = '/community/messages/forward';

  // Community - Friend Management (Phase 4)
  static const String friendsBlocked = '/community/users/blocked';
  static String friendDelete(String friendshipId) =>
      '/community/friends/$friendshipId';
  static const String userBlock = '/community/users/block';
  static String userUnblock(String userId) => '/community/users/block/$userId';

  // Community - Privacy Settings
  static const String userPrivacy = '/community/users/privacy';

  // Community - Shared Resources
  static String groupResources(String groupId) =>
      '/community/groups/$groupId/resources';

  // Community - Broadcast
  static const String broadcast = '/community/broadcast';

  // Community - Advanced Search
  static const String messagesAdvancedSearch = '/community/messages/search';

  // Community - Offline Queue
  static const String offlineQueuePending = '/community/offline/pending';
  static const String offlineQueueFailed = '/community/offline/failed';
  static const String offlineQueueRetry = '/community/offline/retry';

  // Cognitive Prism
  static const String cognitiveFragments = '/cognitive/fragments';
  static const String cognitivePatterns = '/cognitive/patterns';

  // OmniBar
  static const String omnibarDispatch = '/omnibar/dispatch';

  // Dashboard
  static const String dashboardStatus = '/dashboard/status';
  static const String predictiveDashboard = '/predictive/dashboard';
  static const String predictiveNextIntent = '/predictive/next-intent';
  static const String predictiveRealtimeNextStep =
      '/predictive/realtime-next-step';
  static const String predictiveAnalytics = '/predictive/analytics';

  // Nightly Reviews
  static const String nightlyReviewLatest = '/reviews/nightly/latest';
  static String nightlyReviewFeedback(String id) =>
      '/reviews/nightly/$id/feedback';

  // Focus Sessions (P0.3)
  static const String focusSessions = '/focus/sessions';
  static const String focusStats = '/focus/stats';
  static const String focusLlmGuide = '/focus/llm/guide';
  static const String focusLlmBreakdown = '/focus/llm/breakdown';

  // Push Interactions
  static const String pushInteraction = '/push/interaction';

  // Translation
  static const String translationTranslate = '/translation/translate';
  static const String translationLanguages = '/translation/languages';

  // Interventions
  static const String interventionsRequest = '/interventions/request';
  static const String interventionsPassiveSignals =
      '/interventions/passive-signals';
  static const String interventionsOutcomes = '/interventions/outcomes';
  static String interventionFeedback(String id) =>
      '/interventions/requests/$id/feedback';

  // Intent Prediction
  static const String intentPredict = '/prediction/intent/predict';
  static const String intentTypes = '/prediction/intent/types';

  // Achievements
  static const String achievements = '/achievements';
  static const String achievementsStats = '/achievements/stats';
  static const String achievementsMap = '/achievements/map';
  static const String achievementsStreak = '/achievements/streak';
  static const String achievementsStreakHistory =
      '/achievements/streak/history';
  static String achievementDetail(String id) => '/achievements/$id';
  static String achievementShare(String id) => '/achievements/$id/share';
  static String achievementPin(String id) => '/achievements/$id/pin';
  static const String achievementShareTemplates =
      '/achievements/share-templates';

  // Contracts
  static const String contracts = '/achievements/contracts';
  static const String contractsStatus = '/achievements/contracts';

  // Galaxy Skins
  static const String galaxySkins = '/achievements/skins';
  static String skinEquip(String id) => '/achievements/skins/$id/equip';

  // Titles
  static const String titles = '/achievements/titles';
  static String titleEquip(String id) => '/achievements/titles/$id/equip';

  // Achievement Events (internal)
  static const String achievementEventsProcess = '/achievements/events/process';
  static const String achievementsCloseToUnlock =
      '/achievements/close-to-unlock';

  // Multi-Intent
  static const String multiIntentParse = '/multi-intent/parse';
  static const String multiIntentPreview = '/multi-intent/preview';
  static const String multiIntentExecute = '/multi-intent/execute';
  static const String multiIntentAnalyzeExecute =
      '/multi-intent/analyze-and-execute';
  static const String multiIntentTypes = '/multi-intent/intent-types';

  // Recommendations
  static const String recommendationsCollaborative =
      '/recommendations/collaborative';
  static const String recommendationsSimilarUsers =
      '/recommendations/similar-users';
  static const String recommendationsSimilarItems =
      '/recommendations/similar-items';
  static const String recommendationsMyInteractions =
      '/recommendations/my-interactions';
  static const String recommendationsRecord =
      '/recommendations/record-interaction';
  static const String recommendationsStats = '/recommendations/stats';

  // Leaderboards
  static const String leaderboards = '/leaderboards';
  static const String leaderboardsSummary = '/leaderboards/summary';
  static const String leaderboardsMyRank = '/leaderboards/my-rank';
  static const String leaderboardsTypes = '/leaderboards/types';
  static String leaderboardsTopThree(String type) =>
      '/leaderboards/top-three/$type';
  static const String leaderboardsRefreshCache = '/leaderboards/refresh-cache';

  // Seed Libraries
  static const String seedLibraries = '/seed-libraries';
  static String seedLibrary(String id) => '/seed-libraries/$id';
  static String seedLibraryItems(String id) => '/seed-libraries/$id/items';
  static String seedLibraryItem(String libraryId, String itemId) =>
      '/seed-libraries/$libraryId/items/$itemId';
  static String seedLibraryImportItems(String id) =>
      '/seed-libraries/$id/items/import';
  static String seedLibrarySubscribe(String id) =>
      '/seed-libraries/subscribe/$id';
  static String seedLibraryUnsubscribe(String id) =>
      '/seed-libraries/subscribe/$id';
  static String seedLibrarySubscriptions = '/seed-libraries/subscriptions/me';
  static String seedLibraryCrossQuery = '/seed-libraries/query';
  static String seedLibraryFewShot = '/seed-libraries/examples/few-shot';
  static String seedLibraryReplyTemplate =
      '/seed-libraries/query/reply-template';

  // Shop System
  static const String shopItems = '/shop/items';
  static const String shopPurchase = '/shop/purchase';
  static const String shopPurchases = '/shop/purchases';

  // Photon System
  static const String photonBalance = '/photons/balance';
  static const String photonTransactions = '/photons/transactions';
  static const String photonTransfer = '/photons/transfer';

  // Inventory System
  static const String inventory = '/inventory';
  static const String inventoryEquip = '/inventory/equip';
  static String inventoryConsumablesUse(String consumableId) =>
      '/inventory/consumables/$consumableId/use';

  // Visual Elements
  static const String visualElements = '/visual-elements';
  static const String visualElementsUnlocked = '/visual-elements/unlocked';
  static const String visualElementsConfig = '/visual-elements/config';
  static const String visualElementsDefaults = '/visual-elements/defaults';
  static String visualElementEquip(String id) => '/visual-elements/$id/equip';
  static String visualElementUnequip(String type) =>
      '/visual-elements/$type/unequip';
  static const String visualElementsUnlockByAchievement =
      '/visual-elements/unlock-by-achievement';

  // Device Registration (Push Notifications)
  static const String registerDevice = '/devices/register';
  static const String unregisterDevice = '/devices/unregister';

  // Accountability Partners (Phase 3)
  static const String accountabilityMine = '/accountability/mine';
  static const String accountabilityOverview = '/accountability/overview';
  static const String accountabilityRequest = '/accountability/request';
  static String accountabilityRespond(String id) =>
      '/accountability/$id/respond';
  static String accountabilityEnd(String id) => '/accountability/$id';
  static String accountabilityCheckin(String id) =>
      '/accountability/$id/checkin';
  static String accountabilityNudge(String id) => '/accountability/$id/nudge';
  static String accountabilityDashboard(String id) =>
      '/accountability/$id/dashboard';
  static String accountabilityStats(String id) => '/accountability/$id/stats';
  static String accountabilityTimeline(String id) =>
      '/accountability/$id/timeline';
  static String accountabilityHeatmap(String id) =>
      '/accountability/$id/heatmap';
  static String accountabilityCheckinLike(String id) =>
      '/accountability/checkin/$id/like';
  static String accountabilityCheckinEncourage(String id) =>
      '/accountability/checkin/$id/encourage';
  static const String accountabilityAchievements =
      '/accountability/achievements';
  static String accountabilityPartnershipAchievements(String id) =>
      '/accountability/$id/achievements';
  static String friendProfile(String id) => '/community/friends/$id/profile';

  // Calendar Events
  static const String calendarEvents = '/calendar';
  static String calendarEvent(String id) => '/calendar/$id';
  static const String calendarEventsSummary = '/calendar/summary';
  static const String calendarEventsBatch = '/calendar/batch';
  static String calendarEventRestore(String id) => '/calendar/$id/restore';
  static const String calendarSuggestTime = '/calendar/suggest-time';
}
