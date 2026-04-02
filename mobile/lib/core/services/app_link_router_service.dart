import 'dart:async';

import 'package:app_links/app_links.dart';
import 'package:flutter/widgets.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/services/deep_link_service.dart';
import 'package:sparkle/core/services/notification_service.dart';

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
      _scheduleHandle(
        initialUri,
        delay: const Duration(milliseconds: 1400),
      );
    }

    _subscription = _appLinks.uriLinkStream.listen(
      _scheduleHandle,
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
    final route = DeepLinkService.resolveRoute(uri.toString());
    if (route == null) {
      return;
    }
    GoRouter.of(context).go(route);
  }
}
