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
  static const String taskSuggestions = '/tasks/suggestions';

  // Plans
  static const String plans = '/plans';
  static String plan(String id) => '/plans/$id';
  static String planTasks(String id) => '/plans/$id/tasks';
  static String generateTasks(String planId) => '/plans/$planId/generate-tasks';

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

  // Focus Sessions (P0.3)
  static const String focusSessions = '/focus/sessions';
  static const String focusStats = '/focus/stats';
  static const String focusLlmGuide = '/focus/llm/guide';
  static const String focusLlmBreakdown = '/focus/llm/breakdown';
}
