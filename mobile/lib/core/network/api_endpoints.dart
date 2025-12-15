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
  static const String chatSessions = '/chat/sessions';
  static String sessionMessages(String id) => '/chat/sessions/$id/messages';
  
  // Statistics
  static const String statsOverview = '/statistics/overview';
  static const String statsWeekly = '/statistics/weekly';
  static const String statsFlame = '/statistics/flame';
}
