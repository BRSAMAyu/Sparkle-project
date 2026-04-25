import 'dart:async';

import 'package:app_links/app_links.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/navigation/route_resilience.dart';
import 'package:sparkle/core/services/deep_link_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/push_navigation_service.dart';

class AppLinkRouterService {
  AppLinkRouterService._();

  static final AppLinkRouterService instance = AppLinkRouterService._();

  final AppLinks _appLinks = AppLinks();
  StreamSubscription<Uri>? _subscription;
  bool _initialized = false;

  Future<void> initialize() async {
    if (_initialized) {
      return;
    }
    _initialized = true;

    final initialUri = await _appLinks.getInitialLink();
    if (initialUri != null) {
      debugPrint('AppLinkRouterService initial link: $initialUri');
      _scheduleHandle(
        initialUri,
        delay: const Duration(milliseconds: 1400),
      );
    } else {
      debugPrint('AppLinkRouterService initial link: <none>');
    }

    _subscription = _appLinks.uriLinkStream.listen(
      (uri) {
        debugPrint('AppLinkRouterService stream link: $uri');
        _scheduleHandle(uri);
      },
      onError: (Object error, StackTrace stackTrace) {
        debugPrint('AppLinkRouterService error: $error');
      },
    );
  }

  Future<void> dispose() async {
    await _subscription?.cancel();
    _subscription = null;
    _initialized = false;
  }

  void _scheduleHandle(Uri uri, {Duration delay = Duration.zero}) {
    Future<void>.delayed(delay, () {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _handleUri(uri);
      });
    });
  }

  void _handleUri(Uri uri) {
    final context = navigatorKey.currentContext;
    if (context == null || !context.mounted) {
      Future<void>.delayed(
        const Duration(milliseconds: 250),
        () => _scheduleHandle(uri),
      );
      return;
    }
    final container = ProviderScope.containerOf(context, listen: false);
    if (container.read(pushNavigationServiceProvider).canHandleDebugUri(uri)) {
      unawaited(
        container.read(pushNavigationServiceProvider).handleDebugUri(uri),
      );
      return;
    }
    final route = DeepLinkService.resolveRoute(uri.toString());
    if (route == null) {
      debugPrint('AppLinkRouterService ignored uri: $uri');
      return;
    }
    debugPrint('AppLinkRouterService navigating to: $route');
    unawaited(
      RouteResilience.openExternalRoute(
        context,
        route,
        currentContextLookup: () => navigatorKey.currentContext,
      ),
    );
  }
}
