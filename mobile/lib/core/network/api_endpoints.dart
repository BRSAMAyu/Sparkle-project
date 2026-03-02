import 'package:sparkle/core/constants/api_constants.dart';

class ApiEndpoints {
  // Use platform-aware base URL from ApiConstants (points to Gateway 8080)
  static String get baseUrl =>
      '${ApiConstants.baseUrl}${ApiConstants.apiBasePath}';

  // Auth
  static const String register = '/auth/register';
  static const String login = '/auth/login';
  static const String refresh = '/auth/refresh';
  static const String me = '/users/me';

  // Files
  static const String filesPrepareUpload = '/files/upload/prepare';
  static const String filesCompleteUpload = '/files/upload/complete';
  static String file(String id) => '/files/$id';
  static String fileDownload(String id) => '/files/$id/download';
  static String fileThumbnail(String id) => '/files/$id/thumbnail';
  static const String myFiles = '/me/files';
  static const String myFilesSearch = '/me/files/search';

  // Users
  static String user(String id) => '/users/$id';

  // Tasks
  static const String tasks = '/tasks';
  static String task(String id) => '/tasks/$id';
  static const String todayTasks = '/tasks/today';
  static const String recommendedTasks = '/tasks/recommended';
  static String startTask(String id) => '/tasks/$id/start';
  static String completeTask(String id) => '/tasks/$id/complete';
  static String abandonTask(String id) => '/tasks/$id/abandon';
  static String taskFeedback(String id) => '/tasks/$id/feedback';
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
  static String executionCopilot(String planId) => '/execution/copilot/$planId';
  static String executionCopilotCheckpoint(String planId) =>
      '/execution/copilot/$planId/checkpoint';
  static String executionCopilotTimeline(String planId) =>
      '/execution/copilot/$planId/timeline';

  // Chat
  static const String chat = '/chat';
  static const String chatStream = '/chat/stream'; // SSE 流式聊天端点
  static const String chatSessions = '/chat/sessions';
  static String sessionMessages(String id) => '/chat/sessions/$id/messages';

  // Statistics
  static const String statsOverview = '/statistics/overview';
  static const String statsWeekly = '/statistics/weekly';
  static const String statsFlame = '/statistics/flame';

  // Galaxy
  static const String galaxyGraph = '/galaxy/graph';
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
  static const String searchUsers = '/community/users/search';
  static const String userStatus = '/community/status';

  // Community - Groups
  static const String groups = '/community/groups';
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

  // Nightly Reviews
  static const String nightlyReviewLatest = '/reviews/nightly/latest';
  static String nightlyReviewFeedback(String id) =>
      '/reviews/nightly/$id/feedback';

  // Focus Sessions (P0.3)
  static const String focusSessions = '/focus/sessions';
  static const String focusStats = '/focus/stats';
  static const String focusLlmGuide = '/focus/llm/guide';
  static const String focusLlmBreakdown = '/focus/llm/breakdown';

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
  static String achievementDetail(String id) =>
      '/achievements/achievements/$id';
  static String achievementShare(String id) =>
      '/achievements/achievements/$id/share';
  static String achievementPin(String id) =>
      '/achievements/achievements/$id/pin';

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
  static String seedLibrarySubscribe(String id) =>
      '/seed-libraries/subscribe/$id';
  static String seedLibraryUnsubscribe(String id) =>
      '/seed-libraries/subscribe/$id';
  static String seedLibrarySubscriptions = '/seed-libraries/subscriptions/me';
  static String seedLibraryCrossQuery = '/seed-libraries/query';
  static String seedLibraryFewShot = '/seed-libraries/examples/few-shot';
  static String seedLibraryReplyTemplate =
      '/seed-libraries/query/reply-template';

  // Seed Templates 2.0
  static const String seedTemplatePacks = '/seed-templates/packs';
  static String seedTemplatePackTemplates(String packId) =>
      '/seed-templates/packs/$packId/templates';
  static String seedTemplate(String id) => '/seed-templates/$id';
  static String seedTemplateFork(String id) => '/seed-templates/$id/fork';
  static String seedTemplateVersions(String id) =>
      '/seed-templates/$id/versions';
  static String seedTemplatePublish(String id) => '/seed-templates/$id/publish';
  static String seedTemplateSignals(String id) => '/seed-templates/$id/signals';
  static String seedTemplateSubscribe(String id) =>
      '/seed-templates/$id/subscribe';
  static const String seedTemplateSubscriptionsMe =
      '/seed-templates/subscriptions/me';
  static String seedTemplateInstantiate(String id) =>
      '/seed-templates/$id/instantiate';
  static const String adminSeedTemplateReviewQueue =
      '/admin/seed-templates/review-queue';
  static String adminSeedTemplateApprove(String versionId) =>
      '/admin/seed-templates/$versionId/approve';
  static String adminSeedTemplateReject(String versionId) =>
      '/admin/seed-templates/$versionId/reject';
  static const String adminSeedTemplateDashboard =
      '/admin/seed-templates/promotion-dashboard';

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
}
