import 'package:sparkle/l10n/app_localizations.dart';

/// 错误消息映射工具类
class ErrorMessages {
  /// 获取本地化错误消息
  static String getLocalizedMessage(
    AppLocalizations l10n,
    String errorCode,
    String? technicalMessage,
  ) {
    // 1. Try matching based on technical message (backend may return Chinese or English)
    if (technicalMessage != null) {
      final msg = technicalMessage.toLowerCase();
      // Not-found patterns (CN + EN)
      if (msg.contains('没有找到') ||
          msg.contains('不存在') ||
          msg.contains('not found')) {
        return l10n.errorNotFound;
      }
      // Auth/token expired patterns (CN + EN)
      if (msg.contains('登录信息已过期') ||
          msg.contains('令牌无效') ||
          msg.contains('重新登录') ||
          msg.contains('登录已失效') ||
          msg.contains('token') ||
          msg.contains('expired') ||
          msg.contains('unauthorized') ||
          msg.contains('invalid or expired')) {
        return l10n.errorTokenExpired;
      }
      // Network/connection patterns (CN + EN)
      if (msg.contains('网络') ||
          msg.contains('连接') ||
          msg.contains('network') ||
          msg.contains('connection')) {
        return l10n.errorConnectionFailed;
      }
      // Server error patterns (CN + EN)
      if (msg.contains('服务器') ||
          msg.contains('打盹') ||
          msg.contains('server') ||
          msg.contains('internal') ||
          msg.contains('upstream') ||
          msg.contains('unavailable')) {
        return l10n.errorServerIssue;
      }
      // Rate limit patterns (CN + EN)
      if (msg.contains('太频繁') ||
          msg.contains('休息一下') ||
          msg.contains('too many') ||
          msg.contains('rate limit')) {
        return l10n.errorRateLimit;
      }
      // Permission patterns (CN + EN)
      if (msg.contains('权限') ||
          msg.contains('管理员') ||
          msg.contains('forbidden') ||
          msg.contains('permission') ||
          msg.contains('admin')) {
        return l10n.errorAuthRequired;
      }
    }

    // 2. 基于错误代码进行匹配映射
    switch (errorCode.toUpperCase()) {
      // 连接相关错误
      case 'OFFLINE':
      case 'NO_INTERNET':
        return l10n.errorConnectionFailed;

      case 'CONNECTION_ERROR':
      case 'WEBSOCKET_ERROR':
        return l10n.errorConnectionFailed;

      case 'CONNECTION_TIMEOUT':
      case 'STREAM_TIMEOUT':
        return l10n.errorConnectionTimeout;

      case 'MAX_RETRIES_EXCEEDED':
        return l10n.errorServerIssue;

      // 认证相关错误
      case 'UNAUTHORIZED':
      case 'AUTH_REQUIRED':
        return l10n.errorAuthRequired;

      case 'TOKEN_EXPIRED':
        return l10n.errorTokenExpired;

      // 服务端错误
      case 'SERVER_ERROR':
      case 'INTERNAL_ERROR':
        return l10n.errorServerIssue;

      case 'SERVICE_UNAVAILABLE':
        return l10n.errorServerIssue;

      // 请求相关错误
      case 'INVALID_REQUEST':
      case 'BAD_REQUEST':
      case 'VALIDATION_ERROR':
        return l10n.errorServerIssue;

      case 'RATE_LIMIT_EXCEEDED':
        return l10n.errorRateLimit;

      // AI 相关错误
      case 'LLM_ERROR':
      case 'AI_ERROR':
        return l10n.errorServerIssue;

      case 'CONTEXT_LENGTH_EXCEEDED':
        return l10n.errorServerIssue;

      // 其他错误
      case 'UNKNOWN':
      default:
        // 如果是英文环境，且没有匹配到已知模式，则尝试剥离 "Exception: " 前缀
        if (technicalMessage != null &&
            technicalMessage.startsWith('Exception: ')) {
          return technicalMessage.substring(11);
        }
        return technicalMessage ?? l10n.errorServerIssue;
    }
  }

  /// 将技术性错误代码映射为用户友好的消息 (保留作为兜底，默认中文)
  static String getUserFriendlyMessage(
    String errorCode,
    String? technicalMessage, {
    AppLocalizations? l10n,
  }) {
    if (l10n != null) {
      return getLocalizedMessage(l10n, errorCode, technicalMessage);
    }

    // Fallback to English when l10n is unavailable
    if (technicalMessage != null &&
        (technicalMessage.contains('Exception: ') ||
            technicalMessage.contains('~') ||
            technicalMessage.contains('啦'))) {
      return technicalMessage.replaceFirst('Exception: ', '');
    }

    switch (errorCode.toUpperCase()) {
      case 'CONNECTION_ERROR':
      case 'WEBSOCKET_ERROR':
        return 'Connection lost. Could not receive the full response.';
      case 'OFFLINE':
      case 'NO_INTERNET':
        return 'You appear to be offline. Content has been saved locally.';
      case 'CONNECTION_TIMEOUT':
      case 'STREAM_TIMEOUT':
        return 'The request timed out. Only partial results were received.';
      case 'MAX_RETRIES_EXCEEDED':
        return 'Maximum retries exceeded. The connection did not stabilize.';
      case 'UNAUTHORIZED':
      case 'AUTH_REQUIRED':
        return 'Authentication is invalid. Please sign in again.';
      case 'TOKEN_EXPIRED':
        return 'Session expired. Please sign in again.';
      case 'SERVER_ERROR':
      case 'INTERNAL_ERROR':
        return 'The server encountered an error processing this request.';
      case 'SERVICE_UNAVAILABLE':
        return 'This service is temporarily unavailable.';
      case 'RATE_LIMIT_EXCEEDED':
        return 'Too many requests. Please try again later.';
      case 'LLM_ERROR':
      case 'AI_ERROR':
        return 'The AI service did not return a stable response.';
      case 'CONTEXT_LENGTH_EXCEEDED':
        return 'Context is too long to process with full history.';
      default:
        return technicalMessage ?? 'An unexpected error occurred.';
    }
  }

  /// 判断错误是否可重试
  static bool isRetryable(String errorCode) {
    switch (errorCode.toUpperCase()) {
      case 'CONNECTION_ERROR':
      case 'WEBSOCKET_ERROR':
      case 'CONNECTION_TIMEOUT':
      case 'STREAM_TIMEOUT':
      case 'OFFLINE':
      case 'NO_INTERNET':
      case 'MAX_RETRIES_EXCEEDED':
      case 'SERVER_ERROR':
      case 'INTERNAL_ERROR':
      case 'SERVICE_UNAVAILABLE':
      case 'LLM_ERROR':
      case 'AI_ERROR':
      case 'RATE_LIMIT_EXCEEDED':
        return true;
      default:
        return false;
    }
  }

  /// 获取错误对应的建议操作
  static String getActionSuggestion(
    String errorCode, {
    AppLocalizations? l10n,
  }) {
    // 建议操作也可以根据 l10n 进一步细化，目前保持简单
    switch (errorCode.toUpperCase()) {
      case 'CONNECTION_ERROR':
      case 'WEBSOCKET_ERROR':
      case 'CONNECTION_TIMEOUT':
      case 'STREAM_TIMEOUT':
      case 'OFFLINE':
      case 'NO_INTERNET':
        return 'Check your connection and retry, or view partial results';
      case 'UNAUTHORIZED':
      case 'AUTH_REQUIRED':
      case 'TOKEN_EXPIRED':
        return 'Please sign in again';
      case 'LLM_ERROR':
      case 'AI_ERROR':
      case 'SERVICE_UNAVAILABLE':
        return 'Retry later, or switch to standard mode';
      case 'CONTEXT_LENGTH_EXCEEDED':
        return 'Start a new session or shorten your message';
      default:
        return 'Please try again later';
    }
  }
}
