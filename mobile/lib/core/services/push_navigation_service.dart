import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:logger/logger.dart';
import 'package:sparkle/core/services/intervention_action_service.dart';
import 'package:sparkle/core/services/notification_service.dart';

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
      unawaited(GoRouter.of(context).push(destinationRoute));
      return;
    }

    final deepLink = payload['deep_link']?.toString();
    if (deepLink != null && deepLink.isNotEmpty) {
      final uri = Uri.tryParse(deepLink);
      if (uri != null && uri.scheme == 'sparkle') {
        final entityType = uri.host;
        final entityId =
            uri.pathSegments.isNotEmpty ? uri.pathSegments.first : null;

        switch (entityType) {
          case 'task':
            if (entityId != null) {
              unawaited(
                GoRouter.of(context).pushNamed(
                  'taskExecution',
                  pathParameters: {'id': entityId},
                ),
              );
            }
            return;
          case 'achievement':
            if (entityId != null) {
              unawaited(
                GoRouter.of(context).pushNamed(
                  'achievementDetail',
                  pathParameters: {'id': entityId},
                ),
              );
            }
            return;
          case 'chat':
            if (entityId != null) {
              unawaited(
                GoRouter.of(context).pushNamed(
                  'chat',
                  queryParameters: {'session_id': entityId},
                ),
              );
            }
            return;
          case 'plan':
            if (entityId != null &&
                uri.pathSegments.length > 1 &&
                uri.pathSegments[1] == 'review') {
              unawaited(
                GoRouter.of(context).pushNamed(
                  'planReview',
                  pathParameters: {'id': entityId},
                ),
              );
            } else if (entityId != null) {
              unawaited(
                GoRouter.of(context).pushNamed(
                  'planDetail',
                  pathParameters: {'id': entityId},
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
        GoRouter.of(context).pushNamed(
          'taskExecution',
          pathParameters: {'id': entityId},
        ),
      );
    }
  }
}

final pushNavigationServiceProvider =
    Provider<PushNavigationService>(PushNavigationService.new);
