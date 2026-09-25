import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';

/// P-04 · 低风险 auto-execute 预授权面（授权设置面）数据层.
///
/// 真源是引擎 `/api/v1/action-permissions`（网关纯代理 → Python 引擎
/// `app.services.action_permission_service`）：授权判定、revoke 时序、风险门
/// 全在服务端；本仓库只做投影查询与 grant/revoke 转发，**不缓存授权状态**
/// （UI 每次进设置页重读真源，与服务端「授权不缓存，revoke 即时生效」同口径）。
class ActionPermissionCategoryState {
  const ActionPermissionCategoryState({
    required this.category,
    required this.eligible,
    required this.allowed,
    this.grantedAt,
    this.revokedAt,
  });

  factory ActionPermissionCategoryState.fromJson(Map<String, dynamic> json) =>
      ActionPermissionCategoryState(
        category: (json['category'] ?? '').toString(),
        eligible: json['eligible'] as bool? ?? false,
        allowed: json['allowed'] as bool? ?? false,
        grantedAt: json['granted_at']?.toString(),
        revokedAt: json['revoked_at']?.toString(),
      );

  /// 命令域类别（如 task.update_fields；封闭词表）
  final String category;

  /// 是否可被授予（不可逆类别/词表外 = false，服务端入口即拒）
  final bool eligible;

  /// 合成真值：总开关 ∧ 类别授予（操作级风险门仍在服务端其上）
  final bool allowed;
  final String? grantedAt;
  final String? revokedAt;
}

class ActionPermissionState {
  const ActionPermissionState({
    required this.masterGrant,
    required this.categories,
  });

  factory ActionPermissionState.fromJson(Map<String, dynamic> json) =>
      ActionPermissionState(
        masterGrant: json['master_grant'] as bool? ?? false,
        categories: (json['categories'] as List? ?? const <dynamic>[])
            .whereType<Map<dynamic, dynamic>>()
            .map((e) => ActionPermissionCategoryState.fromJson(
                  Map<String, dynamic>.from(e),
                ),)
            .toList(),
      );

  /// 总开关（UserSettings.low_risk_auto_execute；既有 settings 面权威，此处只读）
  final bool masterGrant;
  final List<ActionPermissionCategoryState> categories;

  List<ActionPermissionCategoryState> get grantable => categories
      .where((c) => c.eligible)
      .toList(growable: false);
}

class ActionPermissionRepository {
  ActionPermissionRepository(this._apiClient);

  final ApiClient _apiClient;

  /// 授权面全量投影（设置页数据源）.
  Future<ActionPermissionState> getState() async {
    final response = await _apiClient.get<dynamic>(
      ApiEndpoints.actionPermissions,
    );
    final data = ApiResponseParser.unwrapMap(
      response.data,
      action: 'getActionPermissions',
    );
    return ActionPermissionState.fromJson(data);
  }

  /// 授予类别（词表外/不可逆类别 → 服务端 422，原样上抛不吞）.
  Future<ActionPermissionState> grant(String category) =>
      _mutate(ApiEndpoints.actionPermissionGrant(category));

  /// 撤销类别（同类操作即时回退 proposal；幂等）.
  Future<ActionPermissionState> revoke(String category) =>
      _mutate(ApiEndpoints.actionPermissionRevoke(category));

  Future<ActionPermissionState> _mutate(String path) async {
    await _apiClient.post<dynamic>(path);
    // mutation 响应只含单类别记录；授权面真相以 GET 投影为准（重读，不本地合成）。
    return getState();
  }
}

final actionPermissionRepositoryProvider =
    Provider<ActionPermissionRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return ActionPermissionRepository(apiClient);
});

/// 授权面状态（设置页每次进入重读；真源权威在服务端）.
final actionPermissionStateProvider = FutureProvider<ActionPermissionState>(
  (ref) => ref.watch(actionPermissionRepositoryProvider).getState(),
);

/// grant/revoke 的 DioException 透传（UI 据 statusCode 提示；服务端 422=不可授）.
bool isPermissionRejected(DioException e) => e.response?.statusCode == 422;
