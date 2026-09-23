import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/errors/failures.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';

/// AUTH-DEEP B-1 三单飞口收敛：全 app 唯一的 token 刷新协调器。
///
/// 背景（AUTH-DEEP 深审）：移动端曾有三处互相独立的 refresh 实现——
/// `api_interceptor.dart`（Completer 单飞）、`websocket_chat_service_v2.dart`
/// （独立 Completer）、`community_provider.dart`（布尔旗标，并发请求被静默
/// 丢弃）。一次后端抖动会被放大为三口各自为政的重复刷新乃至全 app 强登出。
/// 本协调器是唯一的刷新执行入口：
///
/// - **单飞**：并发调用者共享同一次 [AuthRepository.refreshToken] 的
///   Future（含 community 的等待者——不再静默丢弃）；
/// - **分级**：失败按「会话终局 vs 可重试」分类，调用方据此决定是否登出，
///   网络/5xx 抖动不再触发强登出（B-3 放大链的消费端收口）；
/// - **唯一执行体**：刷新本身复用 [AuthRepository.refreshToken]
///   （已修为仅 401/403 清 token），协调器只管单飞、等待队列与分级。
final tokenRefreshCoordinatorProvider = Provider<TokenRefreshCoordinator>(
  TokenRefreshCoordinator.new,
);

/// 刷新失败的分级。
enum TokenRefreshFailureClass {
  /// 服务端明确拒绝会话（401/403；或本地凭据已不存在）。仓库层已清
  /// token，调用方应执行登出善后。
  sessionTerminal,

  /// 网络抖动/超时/5xx 等可重试失败。会话仍然有效（仓库层未清 token），
  /// 调用方禁止登出，应走各自的连接级退避重试。
  retryable,
}

/// 协调器抛出的已分级刷新失败。
class TokenRefreshException implements Exception {
  const TokenRefreshException(
    this.message, {
    required this.failureClass,
    this.code,
    this.originalError,
  });

  final String message;
  final TokenRefreshFailureClass failureClass;
  final String? code;
  final Object? originalError;

  bool get isSessionTerminal =>
      failureClass == TokenRefreshFailureClass.sessionTerminal;

  bool get isRetryable => !isSessionTerminal;

  @override
  String toString() =>
      'TokenRefreshException(${failureClass.name}${code == null ? '' : '/$code'}): $message';
}

class TokenRefreshCoordinator {
  TokenRefreshCoordinator(this._ref);

  final Ref _ref;

  /// 在途刷新的唯一 Future；null = 空闲。并发等待者全部 join 它。
  Future<String>? _inFlight;

  /// 是否有刷新在途。
  bool get isRefreshing => _inFlight != null;

  /// 返回当前可用的 access token（无则尝试单飞刷新）。
  ///
  /// - token 存在且可用（若为 JWT 则 exp 未过期；非 JWT 形态按可用处理）→
  ///   直接返回，不发网络请求；
  /// - token 缺失/已过期但 refresh token 存在 → 触发单飞刷新（并发等待者
  ///   共享同一 Future）并返回新 token；
  /// - 无任何会话 → 返回 null，不抛错（不制造登出循环）；
  /// - 刷新失败 → 抛 [TokenRefreshException]（已分级）。
  Future<String?> getValidAccessToken({String? reason}) async {
    final repo = _ref.read(authRepositoryProvider);
    final access = await repo.getAccessToken();
    if (_isAccessTokenUsable(access)) {
      return access;
    }
    final refresh = await repo.getRefreshToken();
    if (refresh != null && refresh.isNotEmpty) {
      return refreshOnce(reason: reason ?? 'proactive');
    }
    return access;
  }

  /// 强制单飞刷新（401 反应路径）：并发调用者共享同一次
  /// [AuthRepository.refreshToken] 的结果，全 app 任一时刻至多一个刷新
  /// 在途。失败以 [TokenRefreshException] 抛出（含分级）。
  Future<String> refreshOnce({String? reason}) {
    final inFlight = _inFlight;
    if (inFlight != null) {
      debugPrint(
        '🔄 TokenRefreshCoordinator: joining in-flight refresh '
        '(${reason ?? '-'})',
      );
      return inFlight;
    }
    final completer = Completer<String>();
    // 与旧 api_interceptor 同款保险：当不存在任何等待者时，刷新失败的
    // Future 不得升级为未处理异步异常；真实等待者仍照常收到错误。
    final future = completer.future..ignore();
    _inFlight = future;
    unawaited(_executeRefresh(completer, reason: reason));
    return future;
  }

  Future<void> _executeRefresh(
    Completer<String> completer, {
    String? reason,
  }) async {
    try {
      debugPrint(
        '🔑 TokenRefreshCoordinator: refreshing token (${reason ?? '-'})',
      );
      final response = await _ref.read(authRepositoryProvider).refreshToken();
      completer.complete(response.accessToken);
    } catch (e, st) {
      completer.completeError(_classify(e), st);
    } finally {
      // 立即清位：失败后的新调用者开启新一轮（沿用旧 #1 语义，由后端
      // refresh rate limit 兜底刷新频率）。
      _inFlight = null;
    }
  }

  /// 失败分级：复用 [AppFailure.isRetryable] 语义——network/offline/server
  /// （含 5xx）→ retryable；auth/validation/unknown → sessionTerminal。
  /// 与仓库层 B-3 修复（仅 401/403 清 token）互补：可重试失败保 token、
  /// 保会话；仅服务端明确拒绝才升级为登出。
  TokenRefreshException _classify(Object error) {
    final failure = error is AppFailure ? error : AppFailureMapper.from(error);
    return TokenRefreshException(
      failure.message,
      failureClass: failure.isRetryable
          ? TokenRefreshFailureClass.retryable
          : TokenRefreshFailureClass.sessionTerminal,
      code: failure.errorCode,
      originalError: error,
    );
  }

  /// access token 是否可直接使用：存在，且若为 JWT 则 exp 未过期
  /// （留 30s 时钟余量）。非 JWT（如 demo token）解析不出 exp 时按可用
  /// 处理——不改变既有行为。
  static bool _isAccessTokenUsable(String? token) {
    if (token == null || token.isEmpty) {
      return false;
    }
    final expiry = jwtExpiry(token);
    if (expiry == null) {
      return true;
    }
    return expiry.isAfter(DateTime.now().add(const Duration(seconds: 30)));
  }

  /// 解析 JWT payload 的 `exp`（epoch 秒）；非 JWT / 解析失败返回 null。
  @visibleForTesting
  static DateTime? jwtExpiry(String token) {
    final parts = token.split('.');
    if (parts.length != 3) {
      return null;
    }
    try {
      final payload = json.decode(
        utf8.decode(base64Url.decode(base64Url.normalize(parts[1]))),
      ) as Map<String, dynamic>;
      final exp = payload['exp'];
      if (exp is num) {
        return DateTime.fromMillisecondsSinceEpoch((exp * 1000).toInt());
      }
      return null;
    } catch (_) {
      return null;
    }
  }
}
