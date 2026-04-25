import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// 深链接导航服务
/// 处理 sparkle:// 协议的路由跳转
class DeepLinkService {
  DeepLinkService._();

  /// 深链接类型到路由的映射（基于现有路由配置）
  /// 路由来源: achievement_routes.dart, task_routes.dart, plan_routes.dart, etc.
  static const _routeMapping = {
    'achievement': '/achievements',
    'milestone': '/achievements/milestone',
    'task': '/tasks',
    'plan': '/plans',
    'capsule': '/curiosity-capsule',
    'node': '/galaxy/node',
    'prism': '/cognitive/patterns',
    'openclaw': '/openclaw',
    'openclaw-settings': '/profile/openclaw-settings',
  };

  /// 解析 sparkle:// 协议并导航
  /// deepLink 格式: sparkle://achievement/abc123
  /// 返回 true 表示导航成功，false 表示无法处理
  static bool handleDeepLink(BuildContext context, String deepLink) {
    final route = resolveRoute(deepLink);
    if (route == null) return false;

    if (!context.mounted) return false;

    try {
      unawaited(context.push(route));
      return true;
    } catch (e) {
      debugPrint('DeepLink navigation failed: $e');
      return false;
    }
  }

  /// 根据资源类型和 ID 导航到对应页面
  static String? resolveRoute(String deepLink) {
    final uri = Uri.tryParse(deepLink);
    if (uri == null || uri.scheme != 'sparkle') return null;

    final type = _resolveResourceType(uri);
    if (type == null) return null;
    final id = _resolveResourceId(uri, type);

    final baseRoute = _routeMapping[type];
    if (baseRoute == null) return null;

    // 构建完整路由路径
    final route = switch (type) {
      // 使用路径参数的类型
      'achievement' => id != null ? '$baseRoute/$id' : null,
      'milestone' => id != null
          ? _appendQueryParameters('$baseRoute/$id', uri.queryParameters)
          : _appendQueryParameters(baseRoute, uri.queryParameters),
      'task' => id != null ? '$baseRoute/$id' : null,
      'plan' => id != null ? '$baseRoute/$id' : null,
      'node' => id != null ? '$baseRoute/$id' : null,
      // 使用 query 参数的类型
      'capsule' => id != null ? '$baseRoute?highlight=$id' : baseRoute,
      'prism' => id != null ? '$baseRoute?highlight=$id' : baseRoute,
      'openclaw' => _appendQueryParameters(baseRoute, uri.queryParameters),
      'openclaw-settings' => _appendQueryParameters(
          baseRoute,
          uri.queryParameters,
        ),
      _ => null,
    };
    return route;
  }

  /// 检查深链接是否有效
  static bool isValidDeepLink(String deepLink) {
    final uri = Uri.tryParse(deepLink);
    if (uri == null || uri.scheme != 'sparkle') return false;

    final type = _resolveResourceType(uri);
    return type != null && _routeMapping.containsKey(type);
  }

  /// 获取深链接中的资源类型
  static String? getResourceType(String deepLink) {
    final uri = Uri.tryParse(deepLink);
    if (uri == null || uri.scheme != 'sparkle') return null;

    final type = _resolveResourceType(uri);
    if (type == null) return null;
    return _routeMapping.containsKey(type) ? type : null;
  }

  /// 获取深链接中的资源 ID
  static String? getResourceId(String deepLink) {
    final uri = Uri.tryParse(deepLink);
    if (uri == null || uri.scheme != 'sparkle') return null;
    final type = _resolveResourceType(uri);
    if (type == null) return null;
    return _resolveResourceId(uri, type);
  }

  static String? _resolveResourceType(Uri uri) {
    if (uri.host.isNotEmpty) {
      return uri.host;
    }
    if (uri.pathSegments.isEmpty) {
      return null;
    }
    return uri.pathSegments.first;
  }

  static String? _resolveResourceId(Uri uri, String type) {
    final segments = uri.pathSegments;
    if (uri.host.isNotEmpty) {
      return segments.isNotEmpty ? segments.first : null;
    }
    if (segments.length < 2) {
      return null;
    }
    return segments[1];
  }

  static String _appendQueryParameters(
    String route,
    Map<String, String> queryParameters,
  ) {
    if (queryParameters.isEmpty) {
      return route;
    }
    final query = Uri(queryParameters: queryParameters).query;
    return '$route?$query';
  }
}
