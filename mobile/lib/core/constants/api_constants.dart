/// API Constants
class ApiConstants {
  // Base URL (HTTP)
  static const String baseUrl = 'http://localhost:8080';
  static const String apiVersion = 'v1';
  static const String apiBasePath = '/api/$apiVersion';

  // WebSocket URL (Go Gateway)
  static const String wsBaseUrl = 'ws://localhost:8080';
  static const String wsChat = '/ws/chat';

  // Endpoints
  static const String auth = '/auth';
  static const String login = '$auth/login';
  static const String register = '$auth/register';
  static const String logout = '$auth/logout';
  static const String refreshToken = '$auth/refresh';

  static const String users = '/users';
  static const String tasks = '/tasks';
  static const String chat = '/chat';
  static const String plans = '/plans';
  static const String statistics = '/statistics';

  // Timeout
  static const Duration connectTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);
  static const Duration sendTimeout = Duration(seconds: 30);
}
