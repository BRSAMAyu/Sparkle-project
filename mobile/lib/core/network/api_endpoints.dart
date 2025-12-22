class ApiEndpoints {
  // TODO: Move to environment variables
  static const String baseUrl = 'http://localhost:8000/api/v1';
  
  // Auth
  static const String register = '/auth/register';
  static const String login = '/auth/login';
  static const String refresh = '/auth/refresh';
  static const String me = '/users/me';
  
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

  // Plans
  static const String plans = '/plans';
  static String plan(String id) => '/plans/$id';
  static String planTasks(String id) => '/plans/$id/tasks';
  static String generateTasks(String planId) => '/plans/$planId/generate-tasks';
  
  // Chat
  static const String chat = '/chat';
  static const String chatStream = '/chat/stream';  // SSE 流式聊天端点
  static const String chatSessions = '/chat/sessions';
  static String sessionMessages(String id) => '/chat/sessions/$id/messages';
  
  // Statistics
  static const String statsOverview = '/statistics/overview';
  static const String statsWeekly = '/statistics/weekly';
  static const String statsFlame = '/statistics/flame';

  // Galaxy
  static const String galaxyGraph = '/galaxy/graph';
  static String sparkNode(String id) => '/galaxy/node/$id/spark';

  // Community - Friends
  static const String friends = '/community/friends';
  static const String friendRequest = '/community/friends/request';
  static const String friendRespond = '/community/friends/respond';
  static const String friendsPending = '/community/friends/pending';
  static const String friendsRecommendations = '/community/friends/recommendations';

  // Community - Groups
  static const String groups = '/community/groups';
  static const String groupsSearch = '/community/groups/search';
  static String group(String id) => '/community/groups/$id';
  static String groupJoin(String id) => '/community/groups/$id/join';
  static String groupLeave(String id) => '/community/groups/$id/leave';
  static String groupMessages(String id) => '/community/groups/$id/messages';
  static String groupTasks(String id) => '/community/groups/$id/tasks';
  static String groupFlame(String id) => '/community/groups/$id/flame';

  // Community - Tasks & Checkin
  static String claimTask(String id) => '/community/tasks/$id/claim';
  static const String checkin = '/community/checkin';

  // Cognitive Prism
  static const String cognitiveFragments = '/cognitive/fragments';
}
