import 'package:sparkle/l10n/app_localizations.dart';

/// 错误消息映射工具类
class ErrorMessages {
  /// 获取本地化错误消息
  static String getLocalizedMessage(
    AppLocalizations l10n,
    String errorCode,
    String? technicalMessage,
  ) {
    // 1. 尝试基于技术消息（可能是后端返回的中文）进行匹配映射
    if (technicalMessage != null) {
      if (technicalMessage.contains('没有找到') ||
          technicalMessage.contains('不存在')) {
        return l10n.errorNotFound;
      }
      if (technicalMessage.contains('登录信息已过期') ||
          technicalMessage.contains('令牌无效') ||
          technicalMessage.contains('重新登录')) {
        return l10n.errorTokenExpired;
      }
      if (technicalMessage.contains('网络') || technicalMessage.contains('连接')) {
        return l10n.errorConnectionFailed;
      }
      if (technicalMessage.contains('服务器') || technicalMessage.contains('打盹')) {
        return l10n.errorServerIssue;
      }
      if (technicalMessage.contains('太频繁') || technicalMessage.contains('休息一下')) {
        return l10n.errorRateLimit;
      }
      if (technicalMessage.contains('权限') || technicalMessage.contains('管理员')) {
        return l10n.errorAuthRequired;
      }
    }

    // 2. 基于错误代码进行匹配映射
    switch (errorCode.toUpperCase()) {
      // 连接相关错误
      case 'CONNECTION_ERROR':
      case 'WEBSOCKET_ERROR':
        return l10n.errorConnectionFailed;

      case 'CONNECTION_TIMEOUT':
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
        if (technicalMessage != null && technicalMessage.startsWith('Exception: ')) {
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

    // 回退到默认中文逻辑
    if (technicalMessage != null &&
        (technicalMessage.contains('Exception: ') ||
            technicalMessage.contains('~') ||
            technicalMessage.contains('啦'))) {
      // 看起来已经是中文友好文案或包含异常前缀
      return technicalMessage.replaceFirst('Exception: ', '');
    }

    switch (errorCode.toUpperCase()) {
      case 'CONNECTION_ERROR':
      case 'WEBSOCKET_ERROR':
        return '网络似乎有些不给力，请检查一下连接~';
      case 'CONNECTION_TIMEOUT':
        return '连接超时啦，请稍后再试';
      case 'MAX_RETRIES_EXCEEDED':
        return '服务器可能暂时打盹了，检查一下网络再试试吧';
      case 'UNAUTHORIZED':
      case 'AUTH_REQUIRED':
        return '请先登录后再使用这个功能哦';
      case 'TOKEN_EXPIRED':
        return '登录信息已过期，请重新登录~';
      case 'SERVER_ERROR':
      case 'INTERNAL_ERROR':
        return '服务器正在打盹，请稍后再试';
      case 'SERVICE_UNAVAILABLE':
        return '服务暂时不可用，请稍后再试';
      case 'RATE_LIMIT_EXCEEDED':
        return '操作太频繁啦，休息一下再试吧~';
      case 'LLM_ERROR':
      case 'AI_ERROR':
        return 'AI 服务暂时不可用，请稍后再试';
      case 'CONTEXT_LENGTH_EXCEEDED':
        return '对话内容太长啦，开始新的对话吧';
      default:
        return technicalMessage ?? '遇到未预料的问题，我们正在处理~';
    }
  }

  /// 判断错误是否可重试
  static bool isRetryable(String errorCode) {
    switch (errorCode.toUpperCase()) {
      case 'CONNECTION_ERROR':
      case 'WEBSOCKET_ERROR':
      case 'CONNECTION_TIMEOUT':
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
  static String getActionSuggestion(String errorCode, {AppLocalizations? l10n}) {
    // 建议操作也可以根据 l10n 进一步细化，目前保持简单
    switch (errorCode.toUpperCase()) {
      case 'CONNECTION_ERROR':
      case 'WEBSOCKET_ERROR':
      case 'CONNECTION_TIMEOUT':
        return '请检查网络连接后点击重试';
      case 'UNAUTHORIZED':
      case 'AUTH_REQUIRED':
      case 'TOKEN_EXPIRED':
        return '请重新登录';
      default:
        return '请稍后重试';
    }
  }
}
