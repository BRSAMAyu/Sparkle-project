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
    'task': '/tasks',
    'plan': '/plans',
    'capsule': '/curiosity-capsule',
    'node': '/galaxy/node',
    'prism': '/cognitive/patterns',
  };

  /// 解析 sparkle:// 协议并导航
  /// deepLink 格式: sparkle://achievement/abc123
  /// 返回 true 表示导航成功，false 表示无法处理
  static bool handleDeepLink(BuildContext context, String deepLink) {
    final uri = Uri.tryParse(deepLink);
    if (uri == null || uri.scheme != 'sparkle') return false;

    final segments = uri.pathSegments;
    if (segments.isEmpty) return false;

    final type = segments[0];
    final id = segments.length > 1 ? segments[1] : null;

    return _navigateToResource(context, type, id);
  }

  /// 根据资源类型和 ID 导航到对应页面
  static bool _navigateToResource(
    BuildContext context,
    String type,
    String? id,
  ) {
    final baseRoute = _routeMapping[type];
    if (baseRoute == null) return false;

    // 构建完整路由路径
    final route = switch (type) {
      // 使用路径参数的类型
      'achievement' => id != null ? '$baseRoute/$id' : null,
      'task' => id != null ? '$baseRoute/$id' : null,
      'plan' => id != null ? '$baseRoute/$id' : null,
      'node' => id != null ? '$baseRoute/$id' : null,
      // 使用 query 参数的类型
      'capsule' => id != null ? '$baseRoute?highlight=$id' : baseRoute,
      'prism' => id != null ? '$baseRoute?highlight=$id' : baseRoute,
      _ => null,
    };

    if (route == null) return false;

    // 检查 context 是否仍然有效
    if (!context.mounted) return false;

    try {
      context.push(route);
      return true;
    } catch (e) {
      debugPrint('DeepLink navigation failed: $e');
      return false;
    }
  }

  /// 检查深链接是否有效
  static bool isValidDeepLink(String deepLink) {
    final uri = Uri.tryParse(deepLink);
    if (uri == null || uri.scheme != 'sparkle') return false;

    final segments = uri.pathSegments;
    if (segments.isEmpty) return false;

    final type = segments[0];
    return _routeMapping.containsKey(type);
  }

  /// 获取深链接中的资源类型
  static String? getResourceType(String deepLink) {
    final uri = Uri.tryParse(deepLink);
    if (uri == null || uri.scheme != 'sparkle') return null;

    final segments = uri.pathSegments;
    if (segments.isEmpty) return null;

    final type = segments[0];
    return _routeMapping.containsKey(type) ? type : null;
  }

  /// 获取深链接中的资源 ID
  static String? getResourceId(String deepLink) {
    final uri = Uri.tryParse(deepLink);
    if (uri == null || uri.scheme != 'sparkle') return null;

    final segments = uri.pathSegments;
    if (segments.length < 2) return null;

    return segments[1];
  }
}
