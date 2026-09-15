import 'dart:async';
import 'dart:convert';

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

    _navigate(normalizePayload(payload));
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

  Map<String, dynamic> normalizePayload(Map<String, dynamic> payload) {
    final normalized = <String, dynamic>{};
    for (final entry in payload.entries) {
      normalized[entry.key] = _decodeStructuredValue(entry.value);
    }
    return normalized;
  }

  String? resolveRouteForPayload(Map<String, dynamic> payload) {
    final normalized = normalizePayload(payload);

    final destinationRoute = _stringValue(normalized, 'destination_route');
    if (destinationRoute != null) {
      return destinationRoute;
    }

    final directLink = _routeFromLink(_stringValue(normalized, 'deep_link'));
    if (directLink != null) {
      return directLink;
    }

    final suggestedAction = _mapValue(normalized['suggested_action']);
    final actionRoute = _routeFromSuggestedAction(suggestedAction);
    if (actionRoute != null) {
      return actionRoute;
    }

    final goalContext = _mapValue(normalized['goal_context']);
    final taskId = _firstString(normalized, goalContext, const [
      'task_id',
      'taskId',
      'entity_id',
      'entityId',
    ]);
    if (taskId != null) {
      return '/tasks/$taskId/execute';
    }

    final planId = _firstString(normalized, goalContext, const [
      'plan_id',
      'planId',
      'goal_id',
      'goalId',
    ]);
    if (planId != null) {
      return '/plans/$planId';
    }

    final notificationId = _stringValue(normalized, 'notification_id') ??
        _stringValue(normalized, 'notificationId');
    if (notificationId != null) {
      return Uri(
        path: '/notification-center',
        queryParameters: <String, String>{'highlight': notificationId},
      ).toString();
    }

    final type = _stringValue(normalized, 'type');
    final recallType = _stringValue(normalized, 'recall_type') ??
        _stringValue(normalized, 'recallType');
    if (type == 'recall' || recallType != null) {
      return Uri(
        path: '/chat',
        queryParameters: <String, String>{
          'entry': 'recall',
          if (recallType != null) 'recall_type': recallType,
        },
      ).toString();
    }

    return null;
  }

  void _navigate(Map<String, dynamic> payload) {
    final context = navigatorKey.currentContext;
    if (context == null || !context.mounted) {
      _logger.w('Navigator context not available for push navigation');
      return;
    }

    final route = resolveRouteForPayload(payload);
    if (route != null) {
      unawaited(
        RouteResilience.openExternalRoute(
          context,
          route,
          currentContextLookup: () => navigatorKey.currentContext,
        ),
      );
    }
  }

  dynamic _decodeStructuredValue(dynamic value) {
    if (value is! String) {
      return value;
    }
    final trimmed = value.trim();
    if (trimmed.isEmpty) {
      return value;
    }
    if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) {
      return value;
    }
    try {
      return jsonDecode(trimmed);
    } catch (_) {
      return value;
    }
  }

  String? _routeFromLink(String? link) {
    if (link == null) {
      return null;
    }
    final uri = Uri.tryParse(link);
    if (uri != null && uri.scheme == 'sparkle') {
      final entityType = uri.host;
      final entityId =
          uri.pathSegments.isNotEmpty ? uri.pathSegments.first : null;

      switch (entityType) {
        case 'task':
          return entityId != null ? '/tasks/$entityId/execute' : null;
        case 'chat':
          if (entityId != null) {
            return Uri(
              path: '/chat',
              queryParameters: <String, String>{'session_id': entityId},
            ).toString();
          }
          return '/chat';
        case 'plan':
          if (entityId != null &&
              uri.pathSegments.length > 1 &&
              uri.pathSegments[1] == 'review') {
            return Uri(
              path: PlanRoutes.examSprintReview,
              queryParameters: <String, String>{'plan_id': entityId},
            ).toString();
          }
      }
    }
    return DeepLinkService.resolveRoute(link);
  }

  String? _routeFromSuggestedAction(Map<String, dynamic>? action) {
    if (action == null) {
      return null;
    }
    final targetRoute = _stringValue(action, 'destination_route') ??
        _stringValue(action, 'target_route') ??
        _stringValue(action, 'route');
    if (targetRoute != null) {
      return targetRoute;
    }
    final deepLink = _routeFromLink(_stringValue(action, 'deep_link'));
    if (deepLink != null) {
      return deepLink;
    }

    final actionType =
        _stringValue(action, 'type') ?? _stringValue(action, 'action');
    final taskId =
        _stringValue(action, 'task_id') ?? _stringValue(action, 'taskId');
    if (taskId != null &&
        const {'open_task', 'start_task', 'execute_task', 'open_next_task'}
            .contains(actionType)) {
      return '/tasks/$taskId/execute';
    }

    final planId = _stringValue(action, 'plan_id') ??
        _stringValue(action, 'planId') ??
        _stringValue(action, 'goal_id') ??
        _stringValue(action, 'goalId');
    if (planId != null &&
        const {'open_plan', 'open_goal', 'review_plan'}.contains(actionType)) {
      return '/plans/$planId';
    }

    return null;
  }

  Map<String, dynamic>? _mapValue(dynamic value) {
    if (value is Map<String, dynamic>) {
      return value;
    }
    if (value is Map) {
      return Map<String, dynamic>.from(value);
    }
    return null;
  }

  String? _firstString(
    Map<String, dynamic> payload,
    Map<String, dynamic>? context,
    List<String> keys,
  ) {
    for (final key in keys) {
      final payloadValue = _stringValue(payload, key);
      if (payloadValue != null) {
        return payloadValue;
      }
      if (context != null) {
        final contextValue = _stringValue(context, key);
        if (contextValue != null) {
          return contextValue;
        }
      }
    }
    return null;
  }

  String? _stringValue(Map<String, dynamic> map, String key) {
    final value = map[key];
    if (value == null) {
      return null;
    }
    final text = value.toString().trim();
    return text.isEmpty ? null : text;
  }
}

final pushNavigationServiceProvider =
    Provider<PushNavigationService>(PushNavigationService.new);
