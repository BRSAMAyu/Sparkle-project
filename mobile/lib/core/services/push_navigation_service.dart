import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logger/logger.dart';
import 'package:sparkle/core/navigation/route_resilience.dart';
import 'package:sparkle/core/services/deep_link_service.dart';
import 'package:sparkle/core/services/intervention_action_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/features/plan/plan_routes.dart';

class PushNavigationService {
  PushNavigationService(this._ref);

  final Ref _ref;
  final Logger _logger = Logger();

  Future<void> handleOpenedPayload({
    required Map<String, dynamic> payload,
    required String source,
    String surface = 'push_open',
  }) async {
    await _ref.read(interventionActionServiceProvider).reportActionFromPayload(
      payload: payload,
      action: 'seen',
      surface: surface,
      extraPayload: <String, dynamic>{
        'source': source,
      },
    );

    _navigate(payload);
  }

  Future<bool> handleDebugUri(Uri uri) async {
    if (!canHandleDebugUri(uri)) {
      return false;
    }

    final payload = payloadFromDebugUri(uri);
    await handleOpenedPayload(
      payload: payload,
      source: 'debug_deep_link',
      surface: 'push_open_debug',
    );
    return true;
  }

  bool canHandleDebugUri(Uri uri) =>
      uri.scheme == 'sparkle' && uri.host == 'push-open';

  Map<String, dynamic> payloadFromDebugUri(Uri uri) {
    final payload = <String, dynamic>{};
    for (final entry in uri.queryParameters.entries) {
      if (entry.value.isNotEmpty) {
        payload[entry.key] = entry.value;
      }
    }
    return payload;
  }

  void _navigate(Map<String, dynamic> payload) {
    final context = navigatorKey.currentContext;
    if (context == null || !context.mounted) {
      _logger.w('Navigator context not available for push navigation');
      return;
    }

    final destinationRoute = payload['destination_route']?.toString();
    if (destinationRoute != null && destinationRoute.isNotEmpty) {
      unawaited(
        RouteResilience.openExternalRoute(
          context,
          destinationRoute,
          currentContextLookup: () => navigatorKey.currentContext,
        ),
      );
      return;
    }

    final deepLink = payload['deep_link']?.toString();
    if (deepLink != null && deepLink.isNotEmpty) {
      if (DeepLinkService.handleExternalDeepLink(
        context,
        deepLink,
        currentContextLookup: () => navigatorKey.currentContext,
      )) {
        return;
      }
      final uri = Uri.tryParse(deepLink);
      if (uri != null && uri.scheme == 'sparkle') {
        final entityType = uri.host;
        final entityId =
            uri.pathSegments.isNotEmpty ? uri.pathSegments.first : null;

        switch (entityType) {
          case 'task':
            if (entityId != null) {
              unawaited(
                RouteResilience.openExternalRoute(
                  context,
                  '/tasks/$entityId/execute',
                  currentContextLookup: () => navigatorKey.currentContext,
                ),
              );
            }
            return;
          case 'achievement':
            if (entityId != null) {
              unawaited(
                RouteResilience.openExternalRoute(
                  context,
                  '/achievements/$entityId',
                  currentContextLookup: () => navigatorKey.currentContext,
                ),
              );
            }
            return;
          case 'chat':
            if (entityId != null) {
              unawaited(
                RouteResilience.openExternalRoute(
                  context,
                  Uri(
                    path: '/chat',
                    queryParameters: {'session_id': entityId},
                  ).toString(),
                  currentContextLookup: () => navigatorKey.currentContext,
                ),
              );
            }
            return;
          case 'plan':
            if (entityId != null &&
                uri.pathSegments.length > 1 &&
                uri.pathSegments[1] == 'review') {
              unawaited(
                RouteResilience.openExternalRoute(
                  context,
                  Uri(
                    path: PlanRoutes.examSprintReview,
                    queryParameters: {'plan_id': entityId},
                  ).toString(),
                  currentContextLookup: () => navigatorKey.currentContext,
                ),
              );
            } else if (entityId != null) {
              unawaited(
                RouteResilience.openExternalRoute(
                  context,
                  '/plans/$entityId',
                  currentContextLookup: () => navigatorKey.currentContext,
                ),
              );
            }
            return;
          default:
            _logger.w('Unknown push deep link entity type: $entityType');
            return;
        }
      }
    }

    final entityId = payload['entity_id']?.toString();
    if (entityId != null && entityId.isNotEmpty) {
      unawaited(
        RouteResilience.openExternalRoute(
          context,
          '/tasks/$entityId/execute',
          currentContextLookup: () => navigatorKey.currentContext,
        ),
      );
    }
  }
}

final pushNavigationServiceProvider =
    Provider<PushNavigationService>(PushNavigationService.new);
