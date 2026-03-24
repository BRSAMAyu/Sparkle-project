import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/features/visual_elements/presentation/screens/visual_elements_screen.dart';

/// 视觉元素系统路由配置
class VisualElementsRoutes {
  VisualElementsRoutes._();

  static const String basePath = '/visual-elements';

  static List<RouteBase> routes = [
    GoRoute(
      path: basePath,
      pageBuilder: (context, state) => MaterialPage<void>(
        key: state.pageKey,
        child: const VisualElementsScreen(),
      ),
    ),
  ];
}
