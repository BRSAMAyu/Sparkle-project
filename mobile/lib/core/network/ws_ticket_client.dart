import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/constants/api_constants.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/api_timeouts.dart';
import 'package:sparkle/core/network/http_client_pinning.dart';

/// 全局 WS ticket 签发客户端（WebSocket 各入口共享）。
final wsTicketClientProvider =
    Provider<WsTicketClient>((ref) => WsTicketClient());

/// 一次成功的 WS ticket 签发结果（网关 POST /api/v1/ws/ticket 响应体）。
class WsTicketGrant {
  const WsTicketGrant({required this.ticket, required this.expiresIn});

  /// 单次核销的 opaque 票（Redis `ws:ticket:<uuid>`，TTL [expiresIn] 秒）。
  final String ticket;

  /// 服务端宣告的有效期（秒）。
  final int expiresIn;
}

/// WS ticket 签发客户端（WS-TICKET-DESIGN §3.1 签发口契约）。
///
/// 移动端规约（设计 §3.2）：
/// - `expires_in - 5s` 内视为不可用（[minUsableTtlSeconds] 余量，覆盖握手耗时
///   与网络时延）；余量不足的票按签发失败处理。
/// - ticket 单次核销（Redis GET+DEL 原子），**每次（重）建连都必须重新签发**，
///   不可缓存复用。
/// - 签发失败不抛出、返回 null，调用方回退 Authorization 头直连——网关在
///   WS_TICKET_REQUIRED 收紧前接受该过渡形态；ticket 可用时双带无害。
class WsTicketClient {
  WsTicketClient({Dio? dio}) : _dioOverride = dio;

  final Dio? _dioOverride;
  Dio? _dio;

  /// 设计规约：有效期余量 ≤5s 的票视为不可用。
  static const int minUsableTtlSeconds = 5;

  Dio get _effectiveDio {
    final override = _dioOverride;
    if (override != null) {
      return override;
    }
    return _dio ??= _buildDefaultDio();
  }

  // 与 AuthInterceptor._getRetryDio 同构：pinning + N37 超时口径，不挂
  // AuthInterceptor——本客户端显式携带调用方传入的新鲜 JWT，避免再经过
  // 拦截器的刷新协调路径（WS 建连前换票是短同步步骤，不该触发刷新单飞）。
  static Dio _buildDefaultDio() {
    final dio = Dio(
      BaseOptions(
        baseUrl: ApiEndpoints.baseUrl,
        // N37 单一事实源：core/network/api_timeouts.dart（数值守恒 10s/30s）。
        connectTimeout: ApiTimeouts.defaultConnectTimeout,
        receiveTimeout: ApiTimeouts.defaultReceiveTimeout,
        contentType: 'application/json',
      ),
    );
    configureDioForPinning(dio, ApiConstants.apiCertSha256);
    return dio;
  }

  /// 用 JWT 换一张单次 WS 握手票。
  ///
  /// 返回 null 表示签发失败（未认证 / 限流 429 / 网络故障 / 响应不可用），
  /// 调用方应回退 Authorization 头；本方法永不抛出。
  Future<WsTicketGrant?> issue({required String authToken}) async {
    try {
      final response = await _effectiveDio.post<dynamic>(
        '/ws/ticket',
        options: Options(headers: {'Authorization': 'Bearer $authToken'}),
      );
      final data = response.data;
      if (data is! Map<String, dynamic>) {
        return null;
      }
      final ticket = data['ticket']?.toString();
      if (ticket == null || ticket.isEmpty) {
        return null;
      }
      final expiresIn = (data['expires_in'] as num?)?.toInt() ?? 0;
      if (expiresIn <= minUsableTtlSeconds) {
        // 余量不足：等握完手票已过期，按签发失败处理（设计 §3.2 规约）。
        return null;
      }
      return WsTicketGrant(ticket: ticket, expiresIn: expiresIn);
    } catch (_) {
      // 签发失败一律回退（401/429/5xx/网络/解析），不向上抛——WS 建连
      // 流程不应因换票失败而中断（设计 §3.2 过渡期双带语义）。
      return null;
    }
  }
}
