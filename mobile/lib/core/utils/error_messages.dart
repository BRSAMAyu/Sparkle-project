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
      if (technicalMessage.contains('太频繁') ||
          technicalMessage.contains('休息一下')) {
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
        return '连接中断了，我没法继续拿到后续结果。';
      case 'CONNECTION_TIMEOUT':
        return '这轮等待超时了，我只拿到部分结果。';
      case 'MAX_RETRIES_EXCEEDED':
        return '重试次数已经用完，这轮链路没有稳定恢复。';
      case 'UNAUTHORIZED':
      case 'AUTH_REQUIRED':
        return '当前登录状态无效，这轮请求没有被服务端接受。';
      case 'TOKEN_EXPIRED':
        return '登录已过期，需要重新建立会话。';
      case 'SERVER_ERROR':
      case 'INTERNAL_ERROR':
        return '服务端处理这轮请求时出错了。';
      case 'SERVICE_UNAVAILABLE':
        return '当前能力暂时不可用，这轮只能中断。';
      case 'RATE_LIMIT_EXCEEDED':
        return '请求过于频繁，这轮被限流了。';
      case 'LLM_ERROR':
      case 'AI_ERROR':
        return '模型服务这轮没有稳定返回结果。';
      case 'CONTEXT_LENGTH_EXCEEDED':
        return '上下文太长，这轮无法继续带着全部历史处理。';
      default:
        return technicalMessage ?? '这轮请求遇到了未分类错误。';
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
  static String getActionSuggestion(String errorCode,
      {AppLocalizations? l10n,}) {
    // 建议操作也可以根据 l10n 进一步细化，目前保持简单
    switch (errorCode.toUpperCase()) {
      case 'CONNECTION_ERROR':
      case 'WEBSOCKET_ERROR':
      case 'CONNECTION_TIMEOUT':
        return '检查网络后重试，或先看当前已返回的部分结果';
      case 'UNAUTHORIZED':
      case 'AUTH_REQUIRED':
      case 'TOKEN_EXPIRED':
        return '请重新登录';
      case 'LLM_ERROR':
      case 'AI_ERROR':
      case 'SERVICE_UNAVAILABLE':
        return '稍后重试，或切换到标准模式先拿主结论';
      case 'CONTEXT_LENGTH_EXCEEDED':
        return '新开一个会话，或把问题缩短后再发';
      default:
        return '请稍后重试';
    }
  }
}
