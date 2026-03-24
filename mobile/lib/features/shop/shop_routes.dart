import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/features/shop/presentation/screens/shop_screen.dart';

/// Shop routes
class ShopRoutes {
  ShopRoutes._();

  static const String basePath = '/shop';

  static List<RouteBase> routes = [
    GoRoute(
      path: basePath,
      pageBuilder: (context, state) => MaterialPage<void>(
        key: state.pageKey,
        child: const ShopScreen(),
      ),
    ),
  ];
}
