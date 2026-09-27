import 'package:sparkle/core/display/lexicon/error_lexicon.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// 错误消息映射工具类
///
/// V3-FIX-360（wt692 收口）：默认分支不再直出/剥前缀透传 technicalMessage——
/// 未命中模式与错误码映射的语义未知，按 N16 单源纪律落
/// [uiErrorMessage] 类别人话兜底（判定走全库唯一字符串判定表
/// [categorizeUiError]），技术细节永不直达用户面。
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
        // V3-FIX-360（wt692）：语义未知不透传 technicalMessage（原实现
        // 剥「Exception: 」前缀或原样直出，后端技术细节直达用户面）——
        // 经共享判定表尽力归类，归类不中落最笼统兜底词条（N16 口径）。
        return uiErrorMessage(l10n, categorizeUiError(technicalMessage));
      }
  }

  /// 将技术性错误代码映射为用户友好的消息 (无 BuildContext 场景的兜底入口)。
  ///
  /// V3-FIX-360（wt692）：l10n 缺省时改走 [I18nService]（zh 优先解析，
  /// 见 W-7 裁决）统一进 [getLocalizedMessage] 单路径；原「Exception: /
  /// ~/啦」剥前缀透传与英文私有映射表退役——私有「异常→文案」映射违反
  /// N16 单源条款，且透传面同属技术信息泄漏。
  static String getUserFriendlyMessage(
    String errorCode,
    String? technicalMessage, {
    AppLocalizations? l10n,
  }) =>
      getLocalizedMessage(
        l10n ?? I18nService.instance.l10n,
        errorCode,
        technicalMessage,
      );

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
