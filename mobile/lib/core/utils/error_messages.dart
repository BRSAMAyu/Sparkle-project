/// 错误消息映射工具类
class ErrorMessages {
  /// 将技术性错误代码映射为用户友好的消息
  static String getUserFriendlyMessage(
      String errorCode, String? technicalMessage,) {
    switch (errorCode.toUpperCase()) {
      // 连接相关错误
      case 'CONNECTION_ERROR':
      case 'WEBSOCKET_ERROR':
        return '网络似乎有些不给力，请检查一下连接~';

      case 'CONNECTION_TIMEOUT':
        return '连接超时啦，请稍后再试';

      case 'MAX_RETRIES_EXCEEDED':
        return '服务器可能暂时打盹了，检查一下网络再试试吧';

      // 认证相关错误
      case 'UNAUTHORIZED':
      case 'AUTH_REQUIRED':
        return '请先登录后再使用这个功能哦';

      case 'TOKEN_EXPIRED':
        return '登录信息已过期，请重新登录~';

      // 服务端错误
      case 'SERVER_ERROR':
      case 'INTERNAL_ERROR':
        return '服务器正在打盹，请稍后再试';

      case 'SERVICE_UNAVAILABLE':
        return '服务暂时不可用，请稍后再试';

      // 请求相关错误
      case 'INVALID_REQUEST':
      case 'BAD_REQUEST':
        return '请求格式好像有问题，请重试';

      case 'RATE_LIMIT_EXCEEDED':
        return '操作太频繁啦，休息一下再试吧~';

      // AI 相关错误
      case 'LLM_ERROR':
      case 'AI_ERROR':
        return 'AI 服务暂时不可用，请稍后再试';

      case 'CONTEXT_LENGTH_EXCEEDED':
        return '对话内容太长啦，开始新的对话吧';

      // 其他错误
      case 'UNKNOWN':
      default:
        return technicalMessage ?? '遇到未预料的问题，我们正在处理~';
    }
  }

  /// 判断错误是否可重试
  static bool isRetryable(String errorCode) {
    switch (errorCode.toUpperCase()) {
      // 可重试的错误
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

      // 不可重试的错误（需要用户干预）
      case 'UNAUTHORIZED':
      case 'AUTH_REQUIRED':
      case 'TOKEN_EXPIRED':
      case 'INVALID_REQUEST':
      case 'BAD_REQUEST':
      case 'CONTEXT_LENGTH_EXCEEDED':
        return false;

      // 默认不可重试
      default:
        return false;
    }
  }

  /// 获取错误对应的建议操作
  static String getActionSuggestion(String errorCode) {
    switch (errorCode.toUpperCase()) {
      case 'CONNECTION_ERROR':
      case 'WEBSOCKET_ERROR':
      case 'CONNECTION_TIMEOUT':
        return '请检查网络连接后点击重试';

      case 'MAX_RETRIES_EXCEEDED':
        return '请检查网络设置，确保网络畅通';

      case 'UNAUTHORIZED':
      case 'AUTH_REQUIRED':
      case 'TOKEN_EXPIRED':
        return '请重新登录';

      case 'SERVER_ERROR':
      case 'INTERNAL_ERROR':
      case 'SERVICE_UNAVAILABLE':
        return '服务器维护中，请稍后再试';

      case 'RATE_LIMIT_EXCEEDED':
        return '请稍等片刻后再试';

      case 'CONTEXT_LENGTH_EXCEEDED':
        return '请开始新的对话';

      case 'LLM_ERROR':
      case 'AI_ERROR':
        return '请稍后重试或联系客服';

      default:
        return '请稍后重试';
    }
  }
}
