import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// V3-FIX-120（auth 双测网络互扰）：单测进程内任何 dart:io HttpClient（含 dio
/// 的 IOHttpClientAdapter，经 HttpOverrides 创建）一律拿到 stub 传输——请求
/// 立即以 SocketException 完结，零 socket、零 timer、确定性失败。
///
/// 根因：register_screen_o3_submit / login_screen_submit 等 widget 测试只覆盖了
/// authRepositoryProvider，未覆盖 userRepositoryProvider——屏内 guest/accessibility
/// 等 provider 初始化会经真实 ApiClient（dio → 10.0.2.2:8080）发 GET
/// /user/settings。单跑/无网关时连接被拒、异常被吞，表现为稳定绿；开发机常驻
/// 网关在时真发网络成功，负载时序敏感 → 双测合并跑偶发互扰。
///
/// 修在 transport 层而非 repo provider 覆盖（ApiClient 构造期 ref 依赖 +
/// container 自引用两坑）：HttpOverrides.global 是 dio 无全局 adapter 注入面时
/// 唯一的进程级传输缝。失败形态取 SocketException——与「网关不在场」的
/// baseline 同形（provider 既有失败路径已吞此形态），不产生 pending timer
/// 挂死 fake-async。
class _NoNetworkHttpOverrides extends HttpOverrides {
  @override
  HttpClient createHttpClient(SecurityContext? context) =>
      _NoNetworkHttpClient();
}

class _NoNetworkHttpClient implements HttpClient {
  @override
  Future<HttpClientRequest> openUrl(String method, Uri url) async =>
      _NoNetworkRequest(url);

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      null; // dio 的 connectionTimeout 等写口安静吞掉
}

class _NoNetworkRequest implements HttpClientRequest {
  _NoNetworkRequest(this.uri);

  @override
  final Uri uri;

  @override
  Future<HttpClientResponse> close() =>
      Future<HttpClientResponse>.error(
        // 与「网关不在场」同形的连接失败（baseline 下 provider 已吞此形态）。
        const SocketException(
          'network disabled by test transport guard (V3-FIX-120)',
        ),
      );

  @override
  Future<HttpClientResponse> get done => close();

  @override
  void write(Object? object) {}

  @override
  void add(List<int> data) {}

  @override
  Future<void> addStream(Stream<List<int>> stream) async {}

  @override
  dynamic noSuchMethod(Invocation invocation) => null;
}

/// 在 setUp 调用（`setUp(installNoNetworkHttpOverrides)`）；恢复走 addTearDown。
// ignore: prefer_expression_function_bodies
void installNoNetworkHttpOverrides() {
  final previous = HttpOverrides.current;
  HttpOverrides.global = _NoNetworkHttpOverrides();
  addTearDown(() {
    HttpOverrides.global = previous;
  });
}
