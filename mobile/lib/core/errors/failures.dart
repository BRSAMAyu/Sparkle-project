import 'package:dio/dio.dart';
import 'package:sparkle/core/services/i18n_service.dart';

enum FailureKind {
  network,
  offline,
  auth,
  server,
  validation,
  unknown,
}

extension FailureKindCode on FailureKind {
  String get code => switch (this) {
        FailureKind.network => 'NETWORK_ERROR',
        FailureKind.offline => 'OFFLINE',
        FailureKind.auth => 'AUTH_REQUIRED',
        FailureKind.server => 'SERVER_ERROR',
        FailureKind.validation => 'VALIDATION_ERROR',
        FailureKind.unknown => 'UNKNOWN',
      };

  static FailureKind fromCode(String? code) {
    switch (code?.toUpperCase()) {
      case 'CONNECTION_ERROR':
      case 'CONNECTION_TIMEOUT':
      case 'NETWORK_ERROR':
      case 'WEBSOCKET_ERROR':
      case 'STREAM_TIMEOUT':
        return FailureKind.network;
      case 'OFFLINE':
      case 'NO_INTERNET':
        return FailureKind.offline;
      case 'UNAUTHORIZED':
      case 'AUTH_REQUIRED':
      case 'TOKEN_EXPIRED':
        return FailureKind.auth;
      case 'SERVER_ERROR':
      case 'INTERNAL_ERROR':
      case 'SERVICE_UNAVAILABLE':
      case 'LLM_ERROR':
      case 'AI_ERROR':
        return FailureKind.server;
      case 'BAD_REQUEST':
      case 'INVALID_REQUEST':
      case 'VALIDATION_ERROR':
        return FailureKind.validation;
      default:
        return FailureKind.unknown;
    }
  }
}

sealed class AppFailure implements Exception {
  const AppFailure({
    required this.kind,
    required this.message,
    this.code,
    this.statusCode,
    this.originalError,
  });

  final FailureKind kind;
  final String message;
  final String? code;
  final int? statusCode;
  final Object? originalError;

  String get errorCode => code ?? kind.code;

  bool get isRetryable => switch (kind) {
        FailureKind.network ||
        FailureKind.offline ||
        FailureKind.server =>
          true,
        FailureKind.auth ||
        FailureKind.validation ||
        FailureKind.unknown =>
          false,
      };

  bool get requiresLogin => kind == FailureKind.auth;

  String get userMessage {
    final zh = I18nService.instance.isChinese;
    return switch (kind) {
      FailureKind.offline => zh
          ? '当前像是离线状态。已保留本地内容，重新连网后再试一次。'
          : 'You appear to be offline. Your local work is safe; reconnect and try again.',
      FailureKind.auth => zh
          ? '登录状态已失效，请重新登录后继续。'
          : 'Your session has expired. Sign in again to continue.',
      FailureKind.server => zh
          ? 'Sparkle 服务暂时不稳定，稍后重试通常就能恢复。'
          : 'Sparkle is having trouble right now. Try again in a moment.',
      FailureKind.validation => message,
      FailureKind.network => zh
          ? '网络连接不稳定，这次请求没有完整送达。'
          : 'The connection is unstable, so this request did not complete.',
      FailureKind.unknown => message,
    };
  }

  String get recoveryLabel {
    final zh = I18nService.instance.isChinese;
    return switch (kind) {
      FailureKind.auth => zh ? '去登录' : 'Sign in',
      FailureKind.validation => zh ? '检查输入' : 'Review input',
      FailureKind.offline => zh ? '连网后重试' : 'Retry online',
      FailureKind.network ||
      FailureKind.server ||
      FailureKind.unknown =>
        zh ? '重试' : 'Retry',
    };
  }

  @override
  String toString() => userMessage;
}

class NetworkFailure extends AppFailure {
  const NetworkFailure({
    required super.message,
    super.code,
    super.statusCode,
    super.originalError,
  }) : super(kind: FailureKind.network);
}

class OfflineFailure extends AppFailure {
  const OfflineFailure({
    required super.message,
    super.code,
    super.statusCode,
    super.originalError,
  }) : super(kind: FailureKind.offline);
}

class AuthFailure extends AppFailure {
  const AuthFailure({
    required super.message,
    super.code,
    super.statusCode,
    super.originalError,
  }) : super(kind: FailureKind.auth);
}

class ServerFailure extends AppFailure {
  const ServerFailure({
    required super.message,
    super.code,
    super.statusCode,
    super.originalError,
  }) : super(kind: FailureKind.server);
}

class ValidationFailure extends AppFailure {
  const ValidationFailure({
    required super.message,
    super.code,
    super.statusCode,
    super.originalError,
  }) : super(kind: FailureKind.validation);
}

class UnknownFailure extends AppFailure {
  const UnknownFailure({
    required super.message,
    super.code,
    super.statusCode,
    super.originalError,
  }) : super(kind: FailureKind.unknown);
}

class AppFailureMapper {
  const AppFailureMapper._();

  static AppFailure from(
    Object error, {
    StackTrace? stackTrace,
    String fallbackMessage = 'Something went wrong.',
  }) {
    if (error is AppFailure) {
      return error;
    }
    if (error is DioException) {
      return fromDio(error, fallbackMessage: fallbackMessage);
    }

    final raw = error.toString();
    final lower = raw.toLowerCase();
    if (_looksLikeAuth(lower)) {
      return AuthFailure(
        message: _stripExceptionPrefix(raw),
        originalError: error,
      );
    }
    if (_looksLikeOffline(lower)) {
      return OfflineFailure(
        message: _stripExceptionPrefix(raw),
        originalError: error,
      );
    }
    if (_looksLikeServer(lower)) {
      return ServerFailure(
        message: _stripExceptionPrefix(raw),
        originalError: error,
      );
    }
    if (_looksLikeValidation(lower)) {
      return ValidationFailure(
        message: _stripExceptionPrefix(raw),
        originalError: error,
      );
    }
    return UnknownFailure(
      message: _stripExceptionPrefix(raw).isEmpty
          ? fallbackMessage
          : _stripExceptionPrefix(raw),
      originalError: error,
    );
  }

  static AppFailure fromDio(
    DioException error, {
    String fallbackMessage = 'Request failed.',
  }) {
    final statusCode = error.response?.statusCode;
    final message = _extractResponseMessage(error.response?.data) ??
        error.message ??
        fallbackMessage;
    final code = _extractResponseCode(error.response?.data);

    if (statusCode == 401 || statusCode == 403) {
      return AuthFailure(
        message: message,
        code: code ?? (statusCode == 401 ? 'UNAUTHORIZED' : 'AUTH_REQUIRED'),
        statusCode: statusCode,
        originalError: error,
      );
    }
    if (statusCode == 400 || statusCode == 422) {
      return ValidationFailure(
        message: message,
        code: code ?? 'VALIDATION_ERROR',
        statusCode: statusCode,
        originalError: error,
      );
    }
    if (statusCode != null && statusCode >= 500) {
      return ServerFailure(
        message: message,
        code: code ?? 'SERVER_ERROR',
        statusCode: statusCode,
        originalError: error,
      );
    }

    switch (error.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return NetworkFailure(
          message: message,
          code: 'CONNECTION_TIMEOUT',
          statusCode: statusCode,
          originalError: error,
        );
      case DioExceptionType.connectionError:
        return OfflineFailure(
          message: message,
          code: 'OFFLINE',
          statusCode: statusCode,
          originalError: error,
        );
      case DioExceptionType.badCertificate:
      case DioExceptionType.badResponse:
        return ServerFailure(
          message: message,
          code: code ?? 'SERVER_ERROR',
          statusCode: statusCode,
          originalError: error,
        );
      case DioExceptionType.cancel:
        return NetworkFailure(
          message: message,
          code: 'REQUEST_CANCELLED',
          statusCode: statusCode,
          originalError: error,
        );
      case DioExceptionType.unknown:
        final lower = '${error.error} ${error.message}'.toLowerCase();
        if (_looksLikeOffline(lower)) {
          return OfflineFailure(
            message: message,
            code: 'OFFLINE',
            statusCode: statusCode,
            originalError: error,
          );
        }
        return NetworkFailure(
          message: message,
          code: 'NETWORK_ERROR',
          statusCode: statusCode,
          originalError: error,
        );
    }
  }

  static String? _extractResponseMessage(dynamic data) {
    if (data == null) return null;
    if (data is String) return data;
    if (data is Map) {
      final detail = data['detail'] ?? data['message'] ?? data['error'];
      if (detail is String) return detail;
      if (detail is List) {
        return detail
            .map((item) => item is Map ? item['msg'] ?? item : item)
            .join('\n');
      }
      if (detail != null) return detail.toString();
    }
    return data.toString();
  }

  static String? _extractResponseCode(dynamic data) {
    if (data is Map) {
      final code = data['code'] ?? data['error_code'];
      if (code != null) return code.toString();
    }
    return null;
  }

  static bool _looksLikeAuth(String value) =>
      value.contains('401') ||
      value.contains('unauthorized') ||
      value.contains('token') ||
      value.contains('session expired') ||
      value.contains('重新登录') ||
      value.contains('登录已过期');

  static bool _looksLikeOffline(String value) =>
      value.contains('offline') ||
      value.contains('socketexception') ||
      value.contains('failed host lookup') ||
      value.contains('network is unreachable') ||
      value.contains('connection failed') ||
      value.contains('no internet') ||
      value.contains('网络连接中断');

  static bool _looksLikeServer(String value) =>
      value.contains('500') ||
      value.contains('502') ||
      value.contains('503') ||
      value.contains('504') ||
      value.contains('server') ||
      value.contains('service unavailable') ||
      value.contains('服务器');

  static bool _looksLikeValidation(String value) =>
      value.contains('400') ||
      value.contains('422') ||
      value.contains('validation') ||
      value.contains('invalid request') ||
      value.contains('bad request');

  static String _stripExceptionPrefix(String value) =>
      value.replaceFirst(RegExp(r'^Exception:\s*'), '').trim();
}
